#!/usr/bin/env python3
"""PostToolUse observer hook: verify sub-agent SKILL.md re-hash post-Read.

PLAN-020 Phase 2 v1 (ADR-051 §Sub-agent obligation) — v1 baseline
emits `reference_postread_observed` breadcrumb on every SKILL.md
Read.

PLAN-045 F-10-07 v2 (Session 43 round-8) — extends v1 with:

- Spawn-correlation lookup: scans recent audit-log.jsonl events for
  the matching spawn event (by session_id + skill_path) and extracts
  the `claimed_sha` from the spawn prompt's `## SKILL REFERENCE` line.
- Reconciliation emits:
  - `skill_reference_read_mismatch` if pinned sha != read-time sha
  - `skill_reference_read_stale` if spawn event is >5min older than
    the Read (TOCTOU plausibility window)
- Session-state file at
  `~/.claude/projects/<slug>/state/skill-read-sessions/<session_id>.jsonl`
  tracks already-reconciled (session_id, skill_path) pairs so the
  same Read across multiple sub-agent spawns doesn't re-emit.

Kill-switch: `CEO_SKILL_READ_V2=0` disables the v2 layer, retains v1
baseline behavior.

## Threat model

The spawn-time hook `check_agent_spawn.py::_validate_skill_reference`
verifies the SKILL.md SHA-256 hash matches the pinned hex at SPAWN.
Between that check and the sub-agent's first Read of the file, an
attacker could swap the file (TOCTOU). v1 observer detected the Read
but did not COMPARE. v2 compares + flags + leaves forensic trail.

## Wire-up

Registered in `.claude/settings.json` PostToolUse Read.

## Fail-open

Any internal error → silent allow + breadcrumb. Observer must NEVER
block sub-agent execution.

## Limitations

- Never-read detection deferred (would require SessionEnd hook to
  walk pending entries).
- Audit-log lookup scans last N events (bounded at 500 for perf);
  very-long sessions may miss older spawns. Acceptable — TOCTOU is
  most plausible in the minutes-to-hours window, not days.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# ---------------------------------------------------------------------------
# v2 config
# ---------------------------------------------------------------------------

# Bound audit-log scan to the most recent N events for performance.
_AUDIT_SCAN_LIMIT = 500

# Staleness threshold — if the spawn event is older than this, the
# Read is treated as "stale_spawn" (TOCTOU plausibility ceiling).
_STALE_SECONDS = 300  # 5 minutes

# SKILL REFERENCE line pattern inside spawn prompt.
#   @.claude/skills/core/foo/SKILL.md sha256=<64-hex>
_SKILL_REF_RE = re.compile(
    r"@([^\s]+?/SKILL\.md)\s+sha256=([a-f0-9]{64})",
    re.MULTILINE,
)


def _emit_allow() -> str:
    # Allow: emit empty JSON (top-level "allow" fails Claude Code hook schema).
    return json.dumps({}, ensure_ascii=False)


def _is_skill_md_path(file_path: str, repo_root: Path) -> bool:
    """True iff file_path resolves under .claude/skills/**/SKILL.md."""
    if not file_path:
        return False
    try:
        resolved = Path(file_path).resolve()
        skills_root = (repo_root / ".claude" / "skills").resolve()
        resolved.relative_to(skills_root)
    except (ValueError, OSError):
        return False
    return resolved.name == "SKILL.md"


def _compute_hash(file_path: str) -> Optional[str]:
    """SHA-256 hex of file content. Returns None on any I/O error."""
    try:
        with open(file_path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except (FileNotFoundError, OSError):
        return None


def _emit_audit_breadcrumb(message: str) -> None:
    """Best-effort write to CEO_AUDIT_LOG_ERR. Never raises."""
    try:
        err_path = os.environ.get("CEO_AUDIT_LOG_ERR")
        if not err_path:
            home = os.environ.get("HOME") or str(Path.home())
            err_path = str(
                Path(home) / ".claude" / "projects" / "ceo-orchestration"
                / "audit-log.errors"
            )
        Path(err_path).parent.mkdir(parents=True, exist_ok=True)
        with open(err_path, "a", encoding="utf-8") as fh:
            fh.write(f"[check_skill_reference_read] {message}\n")
    except Exception:
        return


def _emit_veto_triggered(
    file_path: str, file_hash: str, project_dir: str
) -> None:
    """v1 baseline — post-read breadcrumb. Never raises."""
    try:
        from _lib import audit_emit
        audit_emit.emit_veto_triggered(
            hook="check_skill_reference_read",
            reason_code="reference_postread_observed",
            reason_preview=(
                f"sub-agent Read of SKILL.md {file_path} hash={file_hash[:8]}..."
            ),
            blocked_tool="Read",
            project=project_dir,
        )
    except Exception:
        return


# ---------------------------------------------------------------------------
# v2 helpers — audit-log lookup + session-state file
# ---------------------------------------------------------------------------


def _audit_log_path() -> Path:
    """Resolve the audit-log JSONL path (matches audit_log.audit_paths)."""
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    return (
        Path(home) / ".claude" / "projects" / "ceo-orchestration"
        / "audit-log.jsonl"
    )


def _session_state_path(session_id: str) -> Path:
    """Per-session reconciliation state file path."""
    env = os.environ.get("CEO_SKILL_READ_STATE_DIR")
    if env:
        base = Path(env)
    else:
        home = os.environ.get("HOME") or str(Path.home())
        base = (
            Path(home) / ".claude" / "projects" / "ceo-orchestration"
            / "state" / "skill-read-sessions"
        )
    # Sanitize session_id to filesystem-safe chars.
    safe = "".join(
        c for c in (session_id or "unknown")
        if c.isalnum() or c in ("-", "_", ".")
    )[:64] or "unknown"
    return base / f"{safe}.jsonl"


def _tail_audit_log(path: Path, limit: int) -> List[Dict[str, Any]]:
    """Return the last ``limit`` JSONL events from the audit log.

    Cheap O(N) read — caller bounds limit. Never raises.
    """
    if not path.is_file():
        return []
    try:
        # Simple approach: read all, split, take last N. For 10 MB cap
        # this is ~50K lines which is fine.
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    events: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except (ValueError, TypeError):
            continue
    return events


def _find_spawn_for_skill(
    events: Iterable[Dict[str, Any]],
    *,
    session_id: str,
    skill_path_rel: str,
) -> Optional[Tuple[str, str]]:
    """Find the most recent spawn event matching (session_id, skill_path).

    Returns (claimed_sha, spawn_ts_iso) or None if no match.

    Scans events in reverse (most recent first). Only considers
    ``agent_spawn`` events with a non-empty session_id match.
    """
    for event in reversed(list(events)):
        if event.get("action") != "agent_spawn":
            continue
        if event.get("session_id") != session_id:
            continue
        # The raw spawn prompt is not logged (desc_preview is truncated),
        # but ADR-051 native-rail spawns emit `rail: "native"` + the
        # SKILL REFERENCE line is in desc_preview for inline rail.
        # Best-effort: inspect desc_preview for the @<path> sha256=<hex>
        # pattern. If the claimed_sha is elsewhere, return None.
        preview = event.get("desc_preview") or ""
        for match in _SKILL_REF_RE.finditer(preview):
            claim_path = match.group(1)
            claim_sha = match.group(2)
            if claim_path.endswith(skill_path_rel) or claim_path == skill_path_rel:
                return (claim_sha, event.get("ts") or "")
    return None


def _load_session_state(state_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load per-(session, skill_path) reconciliation records.

    Returns a dict keyed by skill_path_rel → {claimed_sha, read_sha,
    verdict, reconciled_at}. Never raises.
    """
    records: Dict[str, Dict[str, Any]] = {}
    if not state_path.is_file():
        return records
    try:
        with open(state_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    continue
                key = rec.get("skill_path")
                if isinstance(key, str):
                    records[key] = rec
    except OSError:
        return records
    return records


def _append_session_state(state_path: Path, record: Dict[str, Any]) -> None:
    """Append a reconciliation record. Never raises."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(state_path.parent, 0o700)
        except OSError:
            pass
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with open(state_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        return


def _emit_v2_event(action: str, **fields: Any) -> None:
    """Emit a v2 reconciliation event via emit_generic. Never raises.

    The 3 v2 actions must be registered in _KNOWN_ACTIONS (wave-5
    kernel batch). Until that batch runs, the emit is silently
    dropped (emit_generic breadcrumbs + returns).
    """
    try:
        from _lib import audit_emit
        audit_emit.emit_generic(action=action, **fields)
    except Exception:
        return


def _parse_iso_utc(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 UTC timestamp. Returns None on parse error."""
    if not ts:
        return None
    try:
        # Strip trailing Z and parse
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# v2 reconciliation core
# ---------------------------------------------------------------------------


def _reconcile_read(
    *,
    file_path: str,
    file_hash: str,
    session_id: str,
    repo_root: Path,
    project_dir: str,
) -> None:
    """v2 reconciliation: look up spawn-time claim + emit event on delta.

    Non-blocking, non-raising.
    """
    try:
        # Relativize skill path for matching
        resolved = Path(file_path).resolve()
        try:
            skill_rel = str(resolved.relative_to(repo_root)).replace(
                os.sep, "/"
            )
        except ValueError:
            skill_rel = file_path

        # Dedupe via per-session state file
        state_path = _session_state_path(session_id)
        already = _load_session_state(state_path)
        if skill_rel in already:
            # Already reconciled this (session, skill) pair. Skip.
            return

        # Scan recent audit-log for spawn claim
        events = _tail_audit_log(_audit_log_path(), _AUDIT_SCAN_LIMIT)
        spawn = _find_spawn_for_skill(
            events, session_id=session_id, skill_path_rel=skill_rel,
        )

        if spawn is None:
            # No matching spawn found — could be (a) non-native-rail
            # spawn with inline SKILL CONTENT, (b) desc_preview truncated
            # the reference line, (c) audit-log tail too short. Just
            # record the read hash for forensic; don't emit mismatch.
            _append_session_state(
                state_path,
                {
                    "ts": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "session_id": session_id,
                    "skill_path": skill_rel,
                    "read_sha": file_hash,
                    "claimed_sha": None,
                    "verdict": "no_spawn_claim_found",
                },
            )
            return

        claimed_sha, spawn_ts_iso = spawn
        now_utc = datetime.now(timezone.utc)
        spawn_dt = _parse_iso_utc(spawn_ts_iso)

        # Stale check (v2 event 2): spawn event older than STALE_SECONDS
        is_stale = False
        if spawn_dt is not None:
            delta = (now_utc - spawn_dt).total_seconds()
            is_stale = delta > _STALE_SECONDS

        # Mismatch check (v2 event 1): sha delta
        is_mismatch = (claimed_sha != file_hash)

        verdict = "match"
        if is_mismatch:
            verdict = "mismatch"
            _emit_v2_event(
                "skill_reference_read_mismatch",
                session_id=session_id,
                project=project_dir,
                skill_path=skill_rel,
                claimed_sha=claimed_sha,
                read_sha=file_hash,
                spawn_ts=spawn_ts_iso,
                read_ts=now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        elif is_stale:
            verdict = "stale_spawn"
            _emit_v2_event(
                "skill_reference_read_stale",
                session_id=session_id,
                project=project_dir,
                skill_path=skill_rel,
                claimed_sha=claimed_sha,
                read_sha=file_hash,
                spawn_ts=spawn_ts_iso,
                read_ts=now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                delta_seconds=int((now_utc - spawn_dt).total_seconds())
                if spawn_dt else None,
            )

        # Persist reconciliation record
        _append_session_state(
            state_path,
            {
                "ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "session_id": session_id,
                "skill_path": skill_rel,
                "claimed_sha": claimed_sha,
                "read_sha": file_hash,
                "verdict": verdict,
            },
        )
    except Exception as exc:
        _emit_audit_breadcrumb(
            f"v2 reconcile failed: {type(exc).__name__}: {exc}"
        )


# ---------------------------------------------------------------------------
# Decision + main
# ---------------------------------------------------------------------------


def decide(
    *,
    file_path: str,
    repo_root: Path,
    project_dir: str,
    session_id: str = "",
) -> str:
    """Pure decision (always allow; PostToolUse observer)."""
    if not _is_skill_md_path(file_path, repo_root):
        return _emit_allow()

    file_hash = _compute_hash(file_path)
    if file_hash is None:
        _emit_audit_breadcrumb(
            f"could not hash SKILL.md {file_path} (read failed)"
        )
        return _emit_allow()

    # v1 baseline: informational breadcrumb.
    _emit_veto_triggered(file_path, file_hash, project_dir)

    # v2 (PLAN-045 F-10-07): reconciliation + event emission.
    if os.environ.get("CEO_SKILL_READ_V2") != "0":
        _reconcile_read(
            file_path=file_path,
            file_hash=file_hash,
            session_id=session_id,
            repo_root=repo_root,
            project_dir=project_dir,
        )

    return _emit_allow()


def main() -> int:
    """Hook entry point.

    Reads PostToolUse event via the Adapter Layer, extracts file_path,
    calls decide(), emits the JSON decision. Always exit 0.
    """
    try:
        from _lib import contract as _contract
        from _lib.adapters import claude as _claude_adapter
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="PostToolUse")
    except Exception:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    file_path = event.file_path or ""
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    project_dir = str(repo_root)
    session_id = getattr(event, "session_id", "") or ""

    try:
        out = decide(
            file_path=file_path,
            repo_root=repo_root,
            project_dir=project_dir,
            session_id=session_id,
        )
    except Exception as exc:
        print(
            f"[check_skill_reference_read] FATAL: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
