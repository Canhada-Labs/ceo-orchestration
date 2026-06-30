#!/usr/bin/env python3
"""replay-session — deterministic replay of a plan's session.

SPEC/v1/replay.schema.md v1.0.0-rc.1 (experimental). ADR-046 §Decision:
Option C (hybrid). Dry-run default (event-sourced parse); ``--execute``
opts into real-harness invocation with stub adapters + OTEL disabled +
clean-worktree pre-flight + acknowledgment flag.

## Usage

    replay-session.py --plan PLAN-014
    replay-session.py --plan PLAN-014 --json
    replay-session.py --plan PLAN-014 --execute --i-understand-this-reexecutes
    replay-session.py --plan PLAN-014 --as-user alice

## Invariants (SPEC §2.2)

- Dry-run is the default mode (event-sourced).
- ``--execute`` requires clean git worktree + ack flag + sets stub
  adapters + disables OTEL.
- Live-adapter-touching spawns are advisory-only in execute mode
  (SKIPPED + ``live_adapter_skipped`` divergence emitted).
- Every replay emits ``replay_started`` + ``replay_completed`` audit
  events. No silent replays.

Stdlib only. Python >= 3.9 compatible. Determinism surface: sorted
iteration, stable hash-of-content, no ``time.sleep`` in logic paths.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Path bootstrap for _lib import (match audit-query.py pattern)
# -----------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _SCRIPT_DIR.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import audit_emit as _audit_emit  # type: ignore
except Exception:  # noqa: BLE001
    _audit_emit = None  # fallback; emissions become no-ops

# PLAN-069 Phase 1 — R9 LIVE LGPD leak fix (replay_redact).
# Wave D promoted the helper to canonical .claude/hooks/_lib/replay_redact.py.
# `from _lib import ...` is on sys.path via the audit_emit import dance above.
from _lib import replay_redact as _redact_lib  # noqa: E402


def _redact_spawn_for_artifact(spawn: Dict[str, Any]) -> Dict[str, Any]:
    """R9 fix — redact a spawn dict before raw-write to state/replay-out/.

    Round 1 P0-SEC-01: replay-session.py:354 + :477 wrote `spawn_copy: spawn`
    verbatim, leaking OS-username paths + free-form audit fields. This helper
    routes the spawn through replay_redact_lib (SCANNER_PIPELINE + thin
    OS-username preprocessor). nonce=None — dry_run/execute artifacts are
    per-run, not committed; the rebind layer is reserved for capture mode.

    Fail-CLOSED: on RedactionFailure, returns a sentinel envelope rather
    than the raw spawn. The artifact still exists (for forensic continuity)
    but does NOT carry verbatim PII.
    """
    try:
        return _redact_lib.redact_event(spawn, nonce=None)
    except _redact_lib.RedactionFailure as exc:
        return {
            "_redaction_failed": True,
            "_failure_class": type(exc).__name__,
            "_failure_detail": str(exc)[:200],
        }


# -----------------------------------------------------------------------------
# Exit codes (SPEC §4)
# -----------------------------------------------------------------------------
EXIT_OK = 0
EXIT_DIRTY = 2
EXIT_MISSING_ACK = 3
EXIT_CROSS_USER_NO_FLAG = 4
EXIT_AS_USER_MISMATCH = 5
EXIT_UNKNOWN_PLAN = 6
EXIT_MISSING_INPUT = 7
EXIT_EMPTY_SESSION = 8
EXIT_MAX_SPAWNS = 9
EXIT_TIMEOUT = 10
EXIT_LIVE_DISALLOWED = 11
EXIT_DIFF_DETECTED = 12
EXIT_AUDIT_PARSE = 13
EXIT_GRAPH_PARSE = 14
EXIT_IO = 15
# PLAN-069 Phase 1 — capture / replay-fixture modes
EXIT_USAGE = 16
EXIT_REDACTION_FAILED = 17
EXIT_FIXTURE_INVALID = 18
EXIT_FIXTURE_DEFENSE_LEAK = 19


# -----------------------------------------------------------------------------
# Defaults (SPEC §5)
# -----------------------------------------------------------------------------
DEFAULT_MAX_SPAWNS = 500
MAX_SPAWN_CAP = 5000
DEFAULT_TIMEOUT_S = 600
MAX_TIMEOUT_S = 3600
PLAN_FILE_MAX_BYTES = 1 * 1024 * 1024
AUDIT_SCAN_LINE_CAP = 1_000_000


# -----------------------------------------------------------------------------
# Error reporting
# -----------------------------------------------------------------------------


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit_started(
    original_sid: str,
    mode: str,
    redacted_count: int,
    as_user: str,
) -> None:
    if _audit_emit is None:
        return
    try:
        # PLAN-069 Phase 1 / ADR-101 — capture mode emits its own action.
        if mode == "capture" and hasattr(_audit_emit, "emit_replay_capture_started"):
            _audit_emit.emit_replay_capture_started(
                original_session_id=original_sid,
                redacted_fragments_count=redacted_count,
                as_user=as_user,
            )
        else:
            _audit_emit.emit_replay_started(
                original_session_id=original_sid,
                mode=mode,
                redacted_fragments_count=redacted_count,
                as_user=as_user,
            )
    except Exception:  # noqa: BLE001
        pass


def _emit_completed(
    original_sid: str,
    mode: str,
    duration_ms: int,
    spawn_count: int,
    diff_summary: str,
    fixture_path: str = "",
) -> None:
    if _audit_emit is None:
        return
    try:
        # PLAN-069 Phase 1 / ADR-101 — capture mode emits its own action.
        if mode == "capture" and hasattr(_audit_emit, "emit_replay_capture_completed"):
            _audit_emit.emit_replay_capture_completed(
                original_session_id=original_sid,
                duration_ms=duration_ms,
                event_count=spawn_count,
                fixture_path=fixture_path,
            )
        else:
            _audit_emit.emit_replay_completed(
                original_session_id=original_sid,
                mode=mode,
                duration_ms=duration_ms,
                spawn_count=spawn_count,
                diff_summary=diff_summary,
            )
    except Exception:  # noqa: BLE001
        pass


def _emit_diff(
    original_sid: str,
    ordinal: int,
    kind: str,
    artifact_path: str = "",
) -> None:
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_replay_diff_produced(
            original_session_id=original_sid,
            spawn_ordinal=ordinal,
            divergence_kind=kind,
            artifact_path=artifact_path,
        )
    except Exception:  # noqa: BLE001
        pass


def _fail(code: int, name: str, detail: str = "", args: Optional[argparse.Namespace] = None) -> int:
    payload = {"error": name, "exit": code, "detail": detail}
    if args is not None and getattr(args, "json", False):
        sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        sys.stderr.write(f"[replay-session] ERROR {name} (exit {code}): {detail}\n")
    return code


# -----------------------------------------------------------------------------
# Audit log reader (stream; tolerates missing)
# -----------------------------------------------------------------------------


def _default_audit_log() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _read_events(
    path: Path,
    line_cap: int = AUDIT_SCAN_LINE_CAP,
) -> Iterator[Dict[str, Any]]:
    if not path.is_file():
        return
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                if lineno > line_cap:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    raise _AuditParseError(f"line {lineno}: malformed JSONL") from None
    except OSError as e:
        raise _AuditParseError(f"cannot read {path}: {e}") from e


class _AuditParseError(Exception):
    pass


# -----------------------------------------------------------------------------
# Plan existence check
# -----------------------------------------------------------------------------


def plan_exists_in_audit(events: Iterable[Dict[str, Any]], plan_id: str) -> bool:
    for e in events:
        if e.get("plan_id") == plan_id or plan_id in str(e.get("desc_preview", "")):
            return True
    return False


def collect_spawns_for_plan(
    events: Iterable[Dict[str, Any]],
    plan_id: str,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return ordered list of agent_spawn events for the given plan.

    If session_id is None, ALL sessions for that plan are included, ordered
    by ts; caller may slice to the most-recent session if desired.
    """
    out: List[Dict[str, Any]] = []
    for e in events:
        if e.get("action") != "agent_spawn":
            continue
        pid = e.get("plan_id")
        # Some older events don't populate plan_id; fallback: desc_preview
        if pid != plan_id and plan_id not in str(e.get("desc_preview", "")):
            continue
        if session_id is not None and e.get("session_id", "") != session_id:
            continue
        out.append(dict(e))
    out.sort(key=lambda ev: (ev.get("ts", ""), ev.get("spawn_ordinal", 0)))
    return out


def collect_live_adapter_spawns(
    events: Iterable[Dict[str, Any]],
    plan_id: str,
    session_id: str,
) -> set:
    """Return set of spawn identifiers for spawns that touched live adapters."""
    touched: set = set()
    for e in events:
        action = e.get("action", "")
        if not action.startswith("live_adapter_call_"):
            continue
        if session_id and e.get("session_id", "") != session_id:
            continue
        spawn_id = e.get("spawn_id") or e.get("spawn_ordinal")
        if spawn_id is not None:
            touched.add(spawn_id)
    return touched


# -----------------------------------------------------------------------------
# Git worktree check
# -----------------------------------------------------------------------------


def is_worktree_clean(repo_root: Optional[Path] = None) -> bool:
    """Return True if git working tree is clean (no porcelain output).

    Resolves via ``git status --porcelain``. Absence of git → returns True
    (not a repo = clean).
    """
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(repo_root) if repo_root else None,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    if cp.returncode != 0:
        # Not a repo — treat as clean; execution gate is FS-only
        return True
    return not cp.stdout.strip()


# -----------------------------------------------------------------------------
# Determinism helpers
# -----------------------------------------------------------------------------


def canonical_payload_hash(payload: Dict[str, Any]) -> str:
    """Return sha256 hex[:16] of a canonical JSON of an event payload.

    Drops nondeterministic fields (``ts``, ``duration_ms``, ``session_id``,
    ``tokens_*``) before hashing to keep cross-run hashes stable for the
    same logical replay.
    """
    drop_keys = {"ts", "duration_ms", "session_id", "tokens_in", "tokens_out", "tokens_total"}
    clean = {k: v for k, v in sorted(payload.items()) if k not in drop_keys}
    s = json.dumps(clean, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def build_replay_id(original_sid: str) -> str:
    """Deterministic replay id = SID + utc iso second."""
    return f"{original_sid or 'unknown-session'}-{_utc_iso()}"


# -----------------------------------------------------------------------------
# Dry-run engine
# -----------------------------------------------------------------------------


def dry_run(
    spawns: List[Dict[str, Any]],
    live_touch_ids: set,
    plan_id: str,
    original_sid: str,
    out_dir: Optional[Path],
    as_user: str,
    json_out: bool,
    quiet: bool,
) -> Dict[str, Any]:
    """Walk spawns, emit per-spawn diff records (artifact paths), summarize.

    Never invokes any hook or adapter. Pure parse + compute.
    """
    started = time.monotonic()
    lines = []
    skipped_live = 0

    for ordinal, spawn in enumerate(spawns):
        sid_ident = spawn.get("spawn_id") or spawn.get("spawn_ordinal") or ordinal
        is_live = sid_ident in live_touch_ids
        payload_hash = canonical_payload_hash(spawn)
        artifact_path = ""
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(out_dir, 0o700)
            except OSError:
                pass
            artifact_path = str(out_dir / f"spawn-{ordinal:04d}.json")
            try:
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "ordinal": ordinal,
                        "payload_hash": payload_hash,
                        "was_live_adapter": is_live,
                        "spawn_copy": _redact_spawn_for_artifact(spawn),
                    }, f, sort_keys=True, ensure_ascii=False, indent=2)
                try:
                    os.chmod(artifact_path, 0o600)
                except OSError:
                    pass
            except OSError:
                artifact_path = ""
        if is_live:
            skipped_live += 1
            _emit_diff(original_sid, ordinal, "live_adapter_skipped", artifact_path)
        lines.append({
            "ordinal": ordinal,
            "skill": spawn.get("skill", "unknown"),
            "subagent_type": spawn.get("subagent_type", ""),
            "desc_preview": spawn.get("desc_preview", ""),
            "payload_hash": payload_hash,
            "was_live_adapter": is_live,
        })

    duration_ms = int((time.monotonic() - started) * 1000)
    summary = {
        "mode": "dry_run",
        "plan_id": plan_id,
        "original_session_id": original_sid,
        "as_user": as_user,
        "spawn_count": len(spawns),
        "live_adapter_skipped": skipped_live,
        "duration_ms": duration_ms,
        "spawns": lines,
    }

    if not quiet:
        if json_out:
            sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(
                f"[replay-session] DRY-RUN plan={plan_id} sid={original_sid} "
                f"spawns={len(spawns)} live_skipped={skipped_live} "
                f"duration_ms={duration_ms}\n"
            )
            for row in lines:
                sys.stdout.write(
                    f"  [{row['ordinal']:04d}] skill={row['skill']} "
                    f"hash={row['payload_hash']} live={row['was_live_adapter']}\n"
                )

    return summary


# -----------------------------------------------------------------------------
# Execute engine (advisory-only; no real harness invocation in v1.0.0-rc.1)
# -----------------------------------------------------------------------------


def execute_run(
    spawns: List[Dict[str, Any]],
    live_touch_ids: set,
    plan_id: str,
    original_sid: str,
    out_dir: Optional[Path],
    as_user: str,
    allow_live: bool,
    timeout_s: int,
    json_out: bool,
    quiet: bool,
) -> Tuple[Dict[str, Any], int]:
    """Execute-mode replay.

    SPEC §2.1/§2.2 mandates:
    - Set CEO_LIVE_ADAPTER_STUB=1 + CEO_OTEL_DISABLED=1 unconditionally
      (even if caller overrode — we overwrite in this process)
    - Live-adapter-touching spawns SKIPPED unless ``--allow-live
      --owner-confirm`` were passed (the caller validates acks)
    - Each spawn attempted under ``timeout_s`` total wallclock budget

    v1.0.0-rc.1 policy: in absence of a stub harness binding, execute
    emits the same artifacts as dry_run PLUS records would-invoke metadata.
    Real-harness binding is future work (out of v1 scope per ADR-046 §Negative 3).
    The spawn-SKIP for live adapters is HARD (never calls real provider).
    """
    # Defense-in-depth: overwrite env at execute time
    os.environ["CEO_LIVE_ADAPTER_STUB"] = "1"
    os.environ["CEO_OTEL_DISABLED"] = "1"

    started = time.monotonic()
    lines = []
    skipped_live = 0
    live_disallowed_attempts = 0

    for ordinal, spawn in enumerate(spawns):
        if (time.monotonic() - started) > timeout_s:
            # Timeout mid-replay
            return {
                "mode": "execute",
                "plan_id": plan_id,
                "original_session_id": original_sid,
                "spawn_count": ordinal,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "timed_out": True,
                "spawns": lines,
            }, EXIT_TIMEOUT

        sid_ident = spawn.get("spawn_id") or spawn.get("spawn_ordinal") or ordinal
        is_live = sid_ident in live_touch_ids
        payload_hash = canonical_payload_hash(spawn)
        artifact_path = ""
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(out_dir, 0o700)
            except OSError:
                pass
            artifact_path = str(out_dir / f"spawn-{ordinal:04d}.json")
            try:
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "ordinal": ordinal,
                        "payload_hash": payload_hash,
                        "was_live_adapter": is_live,
                        "mode": "execute",
                        "stub_adapters": True,
                        "otel_disabled": True,
                        "spawn_copy": _redact_spawn_for_artifact(spawn),
                    }, f, sort_keys=True, ensure_ascii=False, indent=2)
                try:
                    os.chmod(artifact_path, 0o600)
                except OSError:
                    pass
            except OSError:
                artifact_path = ""

        if is_live and not allow_live:
            # Skip live-touching spawns (SPEC §2.2 invariant)
            skipped_live += 1
            _emit_diff(original_sid, ordinal, "live_adapter_skipped", artifact_path)
            lines.append({
                "ordinal": ordinal,
                "status": "skipped_live",
                "payload_hash": payload_hash,
            })
            continue

        if is_live and allow_live:
            # The operator passed --allow-live --owner-confirm. In v1.0.0-rc.1
            # we STILL do not call real providers — the environment is forced
            # to stub. Record the intention for audit purposes.
            live_disallowed_attempts += 1

        lines.append({
            "ordinal": ordinal,
            "status": "replayed_stub",
            "payload_hash": payload_hash,
        })

    duration_ms = int((time.monotonic() - started) * 1000)
    summary = {
        "mode": "execute",
        "plan_id": plan_id,
        "original_session_id": original_sid,
        "as_user": as_user,
        "spawn_count": len(spawns),
        "live_adapter_skipped": skipped_live,
        "live_allow_noop_count": live_disallowed_attempts,
        "duration_ms": duration_ms,
        "spawns": lines,
    }

    if not quiet:
        if json_out:
            sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(
                f"[replay-session] EXECUTE plan={plan_id} sid={original_sid} "
                f"spawns={len(spawns)} live_skipped={skipped_live} "
                f"duration_ms={duration_ms}\n"
            )

    return summary, EXIT_OK


# -----------------------------------------------------------------------------
# Owner resolution
# -----------------------------------------------------------------------------


def _current_user() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"


def find_original_owner(
    events: List[Dict[str, Any]],
    plan_id: str,
    original_sid: Optional[str],
) -> Tuple[str, str]:
    """Return (session_id, owner) for the target session. Owner may be empty."""
    # Find the most-recent session for the plan, or the specified one
    sessions: Dict[str, str] = {}
    last_ts: Dict[str, str] = {}
    for e in events:
        pid = e.get("plan_id")
        if pid != plan_id and plan_id not in str(e.get("desc_preview", "")):
            continue
        sid = e.get("session_id") or ""
        if not sid:
            continue
        owner = e.get("user") or e.get("owner") or e.get("as_user") or ""
        if sid not in sessions or (e.get("ts", "") > last_ts.get(sid, "")):
            sessions[sid] = owner
            last_ts[sid] = e.get("ts", "")

    if original_sid:
        return original_sid, sessions.get(original_sid, "")
    if not sessions:
        return "", ""
    # Pick most-recent session
    sid = max(sessions.keys(), key=lambda s: last_ts.get(s, ""))
    return sid, sessions[sid]


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# PLAN-069 Phase 1 — capture / replay-fixture handlers
# -----------------------------------------------------------------------------


def _resolve_under_project(path_str: str, kind: str) -> Tuple[Optional[Path], str]:
    """Resolve ``path_str`` and refuse if it escapes $CLAUDE_PROJECT_DIR.

    Returns ``(path, "")`` on success or ``(None, reason)`` on refusal.
    Symlinks are rejected at any path component (P1-SEC-04, ADR-051 §6
    TOCTOU precedent).
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if not project:
        return None, f"{kind}: CLAUDE_PROJECT_DIR not set"
    try:
        project_path = Path(project).resolve(strict=False)
    except OSError as exc:
        return None, f"{kind}: cannot resolve CLAUDE_PROJECT_DIR ({exc})"

    raw = Path(path_str)
    # Walk parent components looking for symlinks
    cursor = raw if raw.is_absolute() else (project_path / raw)
    try:
        resolved = cursor.resolve(strict=False)
    except OSError as exc:
        return None, f"{kind}: cannot resolve path ({exc})"

    # Refuse if any existing parent component is a symlink
    parent = cursor
    while parent != parent.parent:
        if parent.exists() and parent.is_symlink():
            return None, f"{kind}: symlink rejected at {parent}"
        parent = parent.parent

    # Refuse if final resolved path escapes project root
    try:
        resolved.relative_to(project_path)
    except ValueError:
        return None, f"{kind}: resolved path {resolved} outside CLAUDE_PROJECT_DIR"
    return resolved, ""


def capture_run(
    spawns: List[Dict[str, Any]],
    all_events: List[Dict[str, Any]],
    plan_id: str,
    original_sid: str,
    as_user: str,
    out_path: Path,
    quiet: bool,
    json_out: bool,
) -> Tuple[Dict[str, Any], int]:
    """Capture-mode handler — produce a redacted JSONL fixture.

    Round 1 lift conditions wired:
    - #1: every string leaf passes through replay_redact_lib (SCANNER_PIPELINE
      + OS-username preprocessor); fail-CLOSED via RedactionFailure.
    - #3: per-fixture HMAC nonce (32 bytes os.urandom) rebinds prompt_sha256 /
      desc_hash / payload_hash. Nonce stored in `_meta.salt_b64`.
    - #6: `_meta.captured_by_hash` = SHA-256 over ordered redacted lines
      (P1-SEC-01 fixture-forgery defense).
    """
    started = time.monotonic()
    nonce = _redact_lib.new_fixture_salt()
    stats = _redact_lib.RedactionStats()

    # Collect events to capture: spawns + plan-relevant supporting events.
    # For Phase 1 minimum-viable capture, mirror what dry_run would replay.
    events_to_capture = list(spawns)

    redacted_lines: List[str] = []
    for ev in events_to_capture:
        try:
            redacted = _redact_lib.redact_event(ev, nonce=nonce, stats=stats)
        except _redact_lib.RedactionFailure as exc:
            return ({
                "mode": "capture",
                "plan_id": plan_id,
                "error": "redaction_failed",
                "detail": str(exc)[:200],
            }, EXIT_REDACTION_FAILED)
        redacted_lines.append(_redact_lib.serialize_event(redacted))

    content_sha = _redact_lib.fixture_content_sha256(redacted_lines)
    meta = _redact_lib.build_meta(
        nonce=nonce,
        captured_at_iso=_utc_iso(),
        plan_id=plan_id,
        original_session_id=original_sid,
        event_count=len(events_to_capture),
        pre_meta_content_sha256=content_sha,
    )

    # Write atomically — temp file in same dir, then rename. Mode 0o600.
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(_redact_lib.serialize_event(meta) + "\n")
            for line in redacted_lines:
                fh.write(line + "\n")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, out_path)
    except OSError as exc:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return ({
            "mode": "capture",
            "plan_id": plan_id,
            "error": "io_error",
            "detail": str(exc)[:200],
        }, EXIT_IO)

    duration_ms = int((time.monotonic() - started) * 1000)
    summary = {
        "mode": "capture",
        "plan_id": plan_id,
        "original_session_id": original_sid,
        "as_user": as_user,
        "fixture_path": str(out_path),
        "fixture_schema": _redact_lib.FIXTURE_SCHEMA,
        "fixture_sha256_content": content_sha,
        "event_count": len(events_to_capture),
        "fields_redacted": stats.fields_redacted,
        "fields_rebound": stats.fields_rebound,
        "pipeline_calls": stats.pipeline_calls,
        "family_counts": stats.family_counts,
        "duration_ms": duration_ms,
    }

    if not quiet:
        if json_out:
            sys.stdout.write(
                json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2)
                + "\n"
            )
        else:
            sys.stdout.write(
                f"[replay-session] CAPTURE plan={plan_id} sid={original_sid} "
                f"events={len(events_to_capture)} "
                f"redacted={stats.fields_redacted} rebound={stats.fields_rebound} "
                f"out={out_path} duration_ms={duration_ms}\n"
            )

    return summary, EXIT_OK


def replay_fixture_run(
    fixture_path: Path,
    plan_id: str,
    quiet: bool,
    json_out: bool,
    strict: bool,
) -> Tuple[Dict[str, Any], int]:
    """Replay-fixture mode — read a committed fixture and verify trust boundary.

    Round 1 condition #6 wired:
    - HMAC chain verify (delegated to existing audit-hmac toolchain — out of
      scope for v1 capture; future extension)
    - Salt-nonce presence + length verify (`verify_fixture_meta`)
    - Schema-version-not-newer guard
    - Post-load `pii_patterns.scan(mode='flag')` defense-in-depth — leaks
      → EXIT_FIXTURE_DEFENSE_LEAK
    """
    started = time.monotonic()
    if not fixture_path.is_file():
        return ({"mode": "replay-fixture", "error": "fixture_not_found",
                 "path": str(fixture_path)}, EXIT_MISSING_INPUT)

    try:
        with open(fixture_path, "r", encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    except OSError as exc:
        return ({"mode": "replay-fixture", "error": "io_error",
                 "detail": str(exc)[:200]}, EXIT_IO)

    if not lines:
        return ({"mode": "replay-fixture", "error": "empty_fixture"},
                EXIT_FIXTURE_INVALID)

    try:
        meta = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        return ({"mode": "replay-fixture", "error": "meta_parse_error",
                 "detail": str(exc)[:200]}, EXIT_FIXTURE_INVALID)

    ok, reason = _redact_lib.verify_fixture_meta(meta)
    if not ok:
        return ({"mode": "replay-fixture", "error": "meta_invalid",
                 "detail": reason}, EXIT_FIXTURE_INVALID)

    # Recompute content hash over events (lines[1..]) and compare to meta.
    content_sha = _redact_lib.fixture_content_sha256(lines[1:])
    if meta.get("captured_by_hash") and meta["captured_by_hash"] != content_sha:
        return ({"mode": "replay-fixture", "error": "content_hash_mismatch",
                 "expected": meta.get("captured_by_hash"),
                 "actual": content_sha}, EXIT_FIXTURE_INVALID)

    events: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines[1:], start=1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            return ({"mode": "replay-fixture", "error": "event_parse_error",
                     "line": idx, "detail": str(exc)[:200]},
                    EXIT_FIXTURE_INVALID)

    # Post-load defense-in-depth (Round 1 condition #6 final clause)
    leaks_per_event: List[Tuple[int, List[str]]] = []
    for idx, ev in enumerate(events):
        clean, leaks = _redact_lib.post_load_defense_in_depth(ev)
        if not clean:
            leaks_per_event.append((idx, leaks))

    duration_ms = int((time.monotonic() - started) * 1000)
    summary = {
        "mode": "replay-fixture",
        "plan_id": plan_id,
        "fixture_path": str(fixture_path),
        "fixture_schema": meta.get("schema"),
        "pii_patterns_version": meta.get("pii_patterns_version"),
        "replay_redact_version": meta.get("replay_redact_version"),
        "event_count": len(events),
        "leaks_post_load": [
            {"event_index": i, "families": fams} for i, fams in leaks_per_event
        ],
        "duration_ms": duration_ms,
    }

    if not quiet:
        if json_out:
            sys.stdout.write(
                json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2)
                + "\n"
            )
        else:
            sys.stdout.write(
                f"[replay-session] REPLAY-FIXTURE plan={plan_id} "
                f"events={len(events)} leaks={len(leaks_per_event)} "
                f"out={fixture_path} duration_ms={duration_ms}\n"
            )

    if leaks_per_event:
        return summary, EXIT_FIXTURE_DEFENSE_LEAK
    return summary, EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the session-replay CLI."""
    p = argparse.ArgumentParser(
        prog="replay-session.py",
        description="Deterministic replay of a plan's session (SPEC/v1/replay.schema.md)",
    )
    p.add_argument("--plan", required=True, help="PLAN-NNN identifier")
    p.add_argument("--original-session-id", default="", help="Target session (default: most recent)")
    p.add_argument(
        "--mode",
        choices=["dry_run", "execute", "capture", "replay-fixture"],
        default="dry_run",
        help=(
            "Mode: dry_run (default), execute (real-harness with stub adapters), "
            "capture (PLAN-069 Phase 1 — emit redacted JSONL fixture), "
            "replay-fixture (PLAN-069 Phase 1 — replay against committed fixture)"
        ),
    )
    p.add_argument("--execute", action="store_true", help="Alias for --mode=execute")
    p.add_argument("--as-user", default="")
    p.add_argument("--audit-log", default=None)
    p.add_argument("--graph", default=None)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--i-understand-this-reexecutes", dest="ack", action="store_true")
    p.add_argument("--allow-live", action="store_true")
    p.add_argument("--owner-confirm", action="store_true")
    p.add_argument("--max-spawns", type=int, default=DEFAULT_MAX_SPAWNS)
    p.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="Treat any divergence as exit 12")
    # PLAN-069 Phase 1 — capture / replay-fixture additions
    p.add_argument(
        "--redact-pii",
        default=None,
        help=(
            "Single literal 'enforced' (Round 1 condition #2). Required for "
            "--mode=capture. Any other token → EXIT_USAGE."
        ),
    )
    p.add_argument(
        "--out",
        default=None,
        help=(
            "Output fixture path for --mode=capture. MUST resolve under "
            "$CLAUDE_PROJECT_DIR (P1-SEC-04 path-traversal guard)."
        ),
    )
    p.add_argument(
        "--fixture",
        default=None,
        help="Input fixture path for --mode=replay-fixture.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — replay a recorded session via the debate harness."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Mode normalization
    mode = "execute" if args.execute else args.mode

    # PLAN-069 Phase 1 — capture/replay-fixture pre-flight gates
    if mode in ("capture", "replay-fixture"):
        # Round 1 P0-SEC-04: --allow-live + --owner-confirm HARD-IGNORED;
        # passing them in capture/replay-fixture → EXIT_USAGE before any FS write.
        if args.allow_live or args.owner_confirm:
            return _fail(
                EXIT_USAGE, "live_flags_forbidden_in_capture_modes",
                "--allow-live / --owner-confirm are not valid in "
                f"--mode={mode}", args,
            )
        # Round 1 condition #2: --redact-pii must be exactly 'enforced'
        if mode == "capture":
            if args.redact_pii != "enforced":
                return _fail(
                    EXIT_USAGE, "redact_pii_not_enforced",
                    "--mode=capture requires --redact-pii=enforced "
                    "(single literal token; any other value rejected)",
                    args,
                )
            if not args.out:
                return _fail(
                    EXIT_USAGE, "missing_out_path",
                    "--mode=capture requires --out <path>", args,
                )
            out_resolved, reason = _resolve_under_project(args.out, "out")
            if out_resolved is None:
                return _fail(EXIT_USAGE, "out_path_refused", reason, args)
            args._out_resolved = out_resolved  # type: ignore[attr-defined]

            # P1-SEC-02 (extended Codex S81 P2#3 fix): --audit-log flag OR
            # CEO_AUDIT_LOG_PATH env-var fallback MUST resolve under
            # $CLAUDE_PROJECT_DIR/.claude/projects/ OR $HOME/.claude/projects/
            # in capture mode (allows the canonical default location AND the
            # in-project location). The original flag-only guard let an
            # attacker set CEO_AUDIT_LOG_PATH to /tmp/random/path and
            # capture a fixture from it (Codex repro 2026-05-03 P2#3).
            effective_audit_log = (
                args.audit_log
                or os.environ.get("CEO_AUDIT_LOG_PATH")
            )
            if effective_audit_log:
                # Resolve path + walk parents for symlinks (P1-SEC-04).
                try:
                    resolved = Path(effective_audit_log).resolve(strict=False)
                except OSError as exc:
                    return _fail(
                        EXIT_USAGE, "audit_log_unresolvable",
                        f"cannot resolve audit-log path ({exc})",
                        args,
                    )
                # Symlink rejection at any existing parent component
                cursor = Path(effective_audit_log)
                if not cursor.is_absolute():
                    project = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
                    if project:
                        cursor = Path(project) / cursor
                parent = cursor
                while parent != parent.parent:
                    if parent.exists() and parent.is_symlink():
                        return _fail(
                            EXIT_USAGE, "audit_log_symlink_rejected",
                            f"audit-log: symlink rejected at {parent}",
                            args,
                        )
                    parent = parent.parent
                # Allowed roots: $CLAUDE_PROJECT_DIR/.claude/projects/
                # OR $HOME/.claude/projects/.
                project = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
                home = os.environ.get("HOME") or str(Path.home())
                allowed_roots = []
                if project:
                    allowed_roots.append(
                        Path(project).resolve() / ".claude" / "projects"
                    )
                allowed_roots.append(
                    Path(home).resolve() / ".claude" / "projects"
                )
                matched_root = None
                for root in allowed_roots:
                    try:
                        resolved.relative_to(root)
                        matched_root = root
                        break
                    except ValueError:
                        continue
                if matched_root is None:
                    roots_str = " OR ".join(str(r) for r in allowed_roots)
                    return _fail(
                        EXIT_USAGE, "audit_log_outside_allowed_roots",
                        f"audit-log path {resolved} must resolve under "
                        f"{roots_str} (Codex S81 P2#3: env var fallback "
                        "is also gated)",
                        args,
                    )
                # Override args.audit_log so _read_events uses validated path
                # (and skips the env-var fallback in _default_audit_log).
                args.audit_log = str(resolved)

        if mode == "replay-fixture":
            if not args.fixture:
                return _fail(
                    EXIT_USAGE, "missing_fixture_path",
                    "--mode=replay-fixture requires --fixture <path>", args,
                )
            fix_resolved, reason = _resolve_under_project(
                args.fixture, "fixture"
            )
            if fix_resolved is None:
                return _fail(EXIT_USAGE, "fixture_path_refused", reason, args)
            args._fixture_resolved = fix_resolved  # type: ignore[attr-defined]

    # Bounds enforcement
    if args.max_spawns < 1 or args.max_spawns > MAX_SPAWN_CAP:
        return _fail(EXIT_MAX_SPAWNS, "max_spawns_out_of_range",
                     f"--max-spawns must be in [1, {MAX_SPAWN_CAP}]", args)
    if args.timeout_seconds < 1 or args.timeout_seconds > MAX_TIMEOUT_S:
        return _fail(EXIT_TIMEOUT, "timeout_out_of_range",
                     f"--timeout-seconds must be in [1, {MAX_TIMEOUT_S}]", args)

    # PLAN-069 Phase 1 — replay-fixture short-circuit (no audit log read)
    if mode == "replay-fixture":
        fix = getattr(args, "_fixture_resolved", None) or Path(args.fixture)
        summary, code = replay_fixture_run(
            fixture_path=fix,
            plan_id=args.plan,
            quiet=args.quiet,
            json_out=args.json,
            strict=args.strict,
        )
        return code

    # Execute pre-flights
    if mode == "execute":
        if not args.ack:
            return _fail(EXIT_MISSING_ACK, "missing_ack",
                         "--execute requires --i-understand-this-reexecutes", args)
        if not is_worktree_clean():
            return _fail(EXIT_DIRTY, "dirty_worktree",
                         "git worktree is not clean; commit or stash first", args)

    # Audit log resolution
    log_path = Path(args.audit_log) if args.audit_log else _default_audit_log()
    if not log_path.is_file():
        # Missing audit log: empty session, soft warning unless --strict
        _emit_started("", mode, 0, args.as_user)
        _emit_completed("", mode, 0, 0, "empty_session:no_audit_log")
        if args.strict:
            return _fail(EXIT_MISSING_INPUT, "missing_input",
                         f"audit log not found: {log_path}", args)
        if not args.quiet:
            msg = {"warning": "empty_session", "detail": "no audit log"}
            sys.stdout.write(
                json.dumps(msg) if args.json else
                "[replay-session] WARN empty_session: no audit log\n"
            )
            if not args.json:
                sys.stdout.write("\n")
        return EXIT_OK

    try:
        all_events = list(_read_events(log_path))
    except _AuditParseError as e:
        return _fail(EXIT_AUDIT_PARSE, "audit_parse_error", str(e), args)

    if not plan_exists_in_audit(all_events, args.plan):
        return _fail(EXIT_UNKNOWN_PLAN, "unknown_plan",
                     f"plan_id not in audit log: {args.plan}", args)

    # Find target session + owner
    sid, owner = find_original_owner(all_events, args.plan, args.original_session_id or None)

    # Cross-user gate
    current = _current_user()
    if owner and owner != current and not args.as_user:
        return _fail(EXIT_CROSS_USER_NO_FLAG, "cross_user_replay_requires_flag",
                     f"original owner={owner} != current={current}; pass --as-user", args)
    if args.as_user and owner and args.as_user != owner:
        return _fail(EXIT_AS_USER_MISMATCH, "as_user_mismatch",
                     f"--as-user={args.as_user} != original owner={owner}", args)

    spawns = collect_spawns_for_plan(all_events, args.plan, sid or None)

    if not spawns:
        _emit_started(sid, mode, 0, args.as_user)
        _emit_completed(sid, mode, 0, 0, "empty_session:no_spawns")
        if args.strict:
            return _fail(EXIT_EMPTY_SESSION, "empty_session",
                         "plan has no spawn events", args)
        if not args.quiet:
            msg = {"warning": "empty_session", "plan_id": args.plan, "session_id": sid}
            sys.stdout.write(
                (json.dumps(msg) if args.json else
                 f"[replay-session] WARN empty_session plan={args.plan} sid={sid}") + "\n"
            )
        return EXIT_OK

    if len(spawns) > args.max_spawns:
        return _fail(EXIT_MAX_SPAWNS, "max_spawns_exceeded",
                     f"plan has {len(spawns)} spawns > --max-spawns={args.max_spawns}", args)

    live_touch_ids = collect_live_adapter_spawns(all_events, args.plan, sid)

    # Out dir
    replay_id = build_replay_id(sid)
    out_dir: Optional[Path] = None
    if args.out_dir:
        out_dir = Path(args.out_dir) / replay_id
    else:
        project = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if project:
            out_dir = Path(project) / "state" / "replay-out" / replay_id

    # Redaction count (advisory: count audit-log events with known-redactable payloads)
    redacted_count = sum(
        1 for e in all_events
        if e.get("action") in {"injection_flag", "output_safety_flag", "otel_export_dropped"}
        and e.get("session_id") == sid
    )

    _emit_started(sid, mode, redacted_count, args.as_user)

    if mode == "capture":
        out_path = getattr(args, "_out_resolved", None) or Path(args.out)
        summary, code = capture_run(
            spawns=spawns,
            all_events=all_events,
            plan_id=args.plan,
            original_sid=sid,
            as_user=args.as_user,
            out_path=out_path,
            quiet=args.quiet,
            json_out=args.json,
        )
        # PLAN-069 Phase 1 / ADR-101 — capture mode emits replay_capture_completed
        # via _emit_completed mode-aware dispatch. fixture_path is the resolved
        # $CLAUDE_PROJECT_DIR out path.
        diff = ("capture_ok"
                if code == EXIT_OK else f"capture_error:{summary.get('error', 'unknown')}")
        _emit_completed(sid, mode, summary.get("duration_ms", 0),
                        summary.get("event_count", 0), diff,
                        fixture_path=str(out_path))
        return code

    if mode == "dry_run":
        summary = dry_run(
            spawns=spawns,
            live_touch_ids=live_touch_ids,
            plan_id=args.plan,
            original_sid=sid,
            out_dir=out_dir,
            as_user=args.as_user,
            json_out=args.json,
            quiet=args.quiet,
        )
        _emit_completed(sid, mode, summary["duration_ms"],
                        summary["spawn_count"], "dry_run_ok")
        return EXIT_OK

    # Execute
    allow_live = args.allow_live and args.owner_confirm
    summary, code = execute_run(
        spawns=spawns,
        live_touch_ids=live_touch_ids,
        plan_id=args.plan,
        original_sid=sid,
        out_dir=out_dir,
        as_user=args.as_user,
        allow_live=allow_live,
        timeout_s=args.timeout_seconds,
        json_out=args.json,
        quiet=args.quiet,
    )
    diff_summary = f"execute_ok:skipped_live={summary.get('live_adapter_skipped', 0)}"
    if code == EXIT_TIMEOUT:
        diff_summary = "error:timeout"
    _emit_completed(sid, mode, summary["duration_ms"],
                    summary["spawn_count"], diff_summary)
    return code


if __name__ == "__main__":  # pragma: no cover — exercised via tests with main(argv)
    sys.exit(main())
