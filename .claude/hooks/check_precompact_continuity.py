#!/usr/bin/env python3
"""PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PreCompact governance
snapshot.

Compaction is the OTHER way a session's protocol state dies — the
closeout-guard (S228) covers only Stop. When the Claude Code harness fires
``PreCompact`` (manual ``/compact`` or auto context-window threshold), this
hook snapshots, into the plan-scoped scratchpad, the governance state the
post-compaction transcript would otherwise forget:

  - ``plan_id`` — the PLAN-NNN currently scoped to the session (derived from
    the audit-log ``plan_transition`` events, NOT an env var — agent-spoofable;
    scratchpad_lib.resolve_plan_id doctrine);
  - ``execution_unit`` — the active execution-unit position (the first
    unchecked ``- [ ]`` checkbox in the current plan file, repo-relative path
    + line + sanitized label);
  - ``ceremony_flags`` — pending Owner-GPG ceremony breadcrumbs (executable
    ``finish-*.sh`` under ``staged/**`` / ``scripts/local/`` newer than the
    last git tag — the closeout-guard's signal, reused);
  - ``hmac_chain`` — a READ-ONLY breadcrumb of the audit HMAC-chain state
    (last-hmac hex PREFIX + chain-length counter) so a post-compaction
    integrity check has the pre-compaction anchor.

The matching ``PostCompact`` hook (``check_postcompact_reinject.py``) reads
this snapshot back and reinjects governance POINTERS (not the snapshot body)
via ``additionalContext``.

## Contract

- ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing files /
  derivation failures / timeouts → stderr breadcrumb + emit ``{}``). NEVER
  blocks — a crashed snapshot must not stop a compaction.
- Time budget ``TIME_BUDGET_S`` (subprocess git capped; budget-blown → snapshot
  what we have, never noise).
- Emits ONE closed-enum ``compaction_continuity_snapshot`` audit event
  (registered in BOTH ``_KNOWN_ACTIONS`` and SPEC v2.43) carrying ONLY closed
  enums + counters: ``trigger`` (manual/auto/other), ``snapshot_outcome``
  (written/scratchpad_unavailable/error/other), ``plan_id`` (PLAN-NNN or
  ``unknown``), ``chain_length`` (clamped int). The snapshot BODY (plan path
  text, checkbox label, ceremony paths, last-hmac hex) is written to the
  plan-scoped scratchpad — NEVER to the audit wire.
- Snapshot privacy: the scratchpad write is plan-scoped + secrets-redacted by
  scratchpad_lib; the audit emit carries no path/label text.
- Kill-switch: ``CEO_COMPACTION_CONTINUITY=0`` (shared with the PostCompact
  reinjection half).
- Stdlib only, Python >= 3.9.

## Scratchpad key

``compaction_continuity`` (single JSON blob, <64 KiB; ``set`` overwrites). The
PostCompact half reads this exact key.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Make the local `_lib` importable (matches the pattern of existing hooks).
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

TIME_BUDGET_S = 2.5
SCRATCHPAD_KEY = "compaction_continuity"
MAX_CEREMONY_FLAGS = 5
# Snapshot blob is capped well under the scratchpad 64 KiB per-key limit; the
# label/path clamps below keep it small regardless.
_LABEL_CLAMP = 160
_PATH_CLAMP = 200


def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_precompact_continuity: %s\n" % msg[:160])


def _sanitize_text(raw: str, clamp: int) -> str:
    """Disk-sourced strings written into the snapshot are kept printable-ASCII
    + clamped — the snapshot blob is later read by the PostCompact half and a
    control char / newline could distort downstream rendering. Mirrors the
    closeout-guard ``_sanitize_path`` hardening (Codex S228 P0)."""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in raw)
    return cleaned[:clamp]


def _git(args: List[str], cwd: str) -> str:
    """stdout on success, '' on any failure (fail-open)."""
    try:
        p = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=2
        )
        return p.stdout.strip() if p.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _trigger_class(event: Dict[str, Any]) -> str:
    """Map the harness PreCompact trigger to the closed enum.

    The documented PreCompact hook input carries a ``trigger`` field with
    ``manual`` (user ran /compact) or ``auto`` (context-window threshold).
    Anything else (incl. a missing field on a future harness change) is
    ``other`` — the audit_emit scrub re-coerces too (defense in depth)."""
    val = event.get("trigger")
    if val in ("manual", "auto"):
        return val
    return "other"


def _resolve_plan_id(event: Dict[str, Any]) -> str:
    """Derive PLAN-NNN from the audit log (NOT env — agent-spoofable).

    Returns ``unknown`` on any derivation failure (fail-open; the snapshot is
    still written with what we have)."""
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("scratchpad_lib import failed (%s)" % str(exc)[:60])
        return "unknown"
    session_id = None
    sid = event.get("session_id") or event.get("sessionId")
    if isinstance(sid, str) and sid.strip():
        session_id = sid.strip()
    try:
        return scratchpad_lib.resolve_plan_id(session_id)
    except Exception as exc:
        _breadcrumb("plan_id derivation failed (%s)" % str(exc)[:80])
        return "unknown"


def _plan_file_for(plan_id: str, cwd: str) -> Optional[str]:
    """Absolute path of the plan markdown file for ``plan_id``, or None.

    Matches ``PLAN-NNN-*.md`` directly under ``.claude/plans/`` (PLAN-SCHEMA
    naming). Returns the first match in sorted order (deterministic)."""
    if not plan_id.startswith("PLAN-"):
        return None
    pattern = os.path.join(cwd, ".claude", "plans", plan_id + "-*.md")
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None


def _execution_unit(plan_path: Optional[str], cwd: str, deadline: float) -> Dict[str, Any]:
    """First unchecked ``- [ ]`` checkbox in the plan file (the active unit).

    Returns ``{}`` when no plan file / no unchecked unit / budget blown.
    Path is repo-relative + sanitized; label is sanitized + clamped. The
    snapshot records position only — never the plan body."""
    if not plan_path:
        return {}
    try:
        rel = _sanitize_text(os.path.relpath(plan_path, cwd), _PATH_CLAMP)
    except (OSError, ValueError):
        rel = _sanitize_text(plan_path, _PATH_CLAMP)
    try:
        with open(plan_path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, start=1):
                if time.monotonic() > deadline:
                    return {}
                stripped = line.lstrip()
                # Unchecked checkbox, tolerant of leading list whitespace.
                if stripped.startswith("- [ ]"):
                    label = stripped[len("- [ ]"):].strip()
                    return {
                        "plan_path": rel,
                        "line": lineno,
                        "label": _sanitize_text(label, _LABEL_CLAMP),
                    }
    except OSError as exc:
        _breadcrumb("plan file read failed (%s)" % str(exc)[:60])
        return {"plan_path": rel}
    # All checkboxes checked (or none): record the file, no active unit.
    return {"plan_path": rel}


def _last_tag_time(cwd: str) -> float:
    out = _git(
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--count=1",
            "--format=%(creatordate:unix)",
            "refs/tags",
        ],
        cwd,
    )
    try:
        return float(out)
    except ValueError:
        return 0.0


def _ceremony_flags(cwd: str, deadline: float) -> List[str]:
    """Pending Owner-GPG ceremonies — executable finish-*.sh newer than the
    last tag (the closeout-guard's signal). Repo-relative, sanitized, sorted,
    bounded. These are POINTERS the operator must act on post-compaction."""
    tag_time = _last_tag_time(cwd)
    found = set()
    patterns = (
        os.path.join(cwd, ".claude", "plans", "PLAN-*", "staged", "**", "finish-*.sh"),
        os.path.join(cwd, "scripts", "local", "finish-*.sh"),
    )
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if time.monotonic() > deadline:
                break
            try:
                if os.access(path, os.X_OK) and os.path.getmtime(path) > tag_time:
                    found.add(
                        _sanitize_text(os.path.relpath(path, cwd), _PATH_CLAMP)
                    )
            except OSError:
                continue
    return sorted(found)[:MAX_CEREMONY_FLAGS]


def _hmac_chain_breadcrumb() -> Dict[str, Any]:
    """READ-ONLY snapshot of the HMAC-chain anchor: last-hmac hex PREFIX +
    chain-length counter.

    Lock-respecting (audit_hmac readers MUST hold the audit filelock — we take
    a best-effort shared lock; on unavailability we still read, since these are
    advisory sidecars and a one-event race is harmless for a snapshot anchor).
    Returns ``{"chain_length": 0}`` on any failure (fail-open). Only the FIRST
    12 hex chars of the last-hmac are kept — enough to detect a post-compaction
    chain divergence, not enough to be a forgery oracle."""
    out: Dict[str, Any] = {"chain_length": 0, "last_hmac_prefix": ""}
    try:
        from _lib import audit_hmac  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("audit_hmac import failed (%s)" % str(exc)[:60])
        return out
    try:
        from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
        _have_lock = True
    except Exception:  # pragma: no cover
        FileLock = None  # type: ignore[assignment]
        FileLockTimeout = Exception  # type: ignore[assignment, misc]
        _have_lock = False

    def _read() -> None:
        try:
            out["chain_length"] = int(audit_hmac.read_chain_length())
        except Exception:
            out["chain_length"] = 0
        try:
            prev = audit_hmac.read_prev_hmac()
            out["last_hmac_prefix"] = audit_hmac.hex_digest(prev)[:12]
        except Exception:
            out["last_hmac_prefix"] = ""

    if _have_lock and FileLock is not None:
        try:
            lock_path = audit_hmac.last_hmac_path().with_name("audit-log.lock")
            with FileLock(lock_path, timeout=0.5):
                _read()
            return out
        except FileLockTimeout:
            _breadcrumb("hmac sidecar lock timeout — lockless best-effort read")
        except Exception as exc:
            _breadcrumb("hmac sidecar lock error (%s) — lockless read" % str(exc)[:60])
    _read()
    return out


def _emit_snapshot_event(
    trigger: str, plan_id: str, chain_length: int, snapshot_outcome: str
) -> None:
    """Emit the closed-enum compaction_continuity_snapshot breadcrumb.

    Carries ONLY closed enums + the chain_length counter — never the snapshot
    body. Import-guarded; any failure is swallowed (the hook NEVER blocks on
    audit infra). Mirrors the check_protocol_semver_cascade emit idiom."""
    try:
        from _lib import audit_emit  # noqa: E402
    except Exception:
        return
    try:
        audit_emit.emit_generic(
            action="compaction_continuity_snapshot",
            trigger=trigger,
            plan_id=plan_id,
            chain_length=chain_length,
            snapshot_outcome=snapshot_outcome,
        )
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("audit emit failed (%s)" % str(exc)[:80])


def _write_snapshot(plan_id: str, blob: Dict[str, Any]) -> str:
    """Persist the snapshot blob to the plan-scoped scratchpad.

    Returns the closed-enum snapshot_outcome: ``written`` /
    ``scratchpad_unavailable`` / ``error``. Plan-scoped + secrets-redacted by
    scratchpad_lib; ``set`` overwrites the prior snapshot."""
    if plan_id == "unknown" or not plan_id.startswith("PLAN-"):
        # No plan scope to write into — the audit event still records the
        # attempt, the scratchpad write is skipped (PostCompact degrades to
        # snapshot_found=False).
        return "scratchpad_unavailable"
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:
        _breadcrumb("scratchpad_lib import failed at write (%s)" % str(exc)[:60])
        return "scratchpad_unavailable"
    try:
        payload = json.dumps(blob, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        _breadcrumb("snapshot serialize failed (%s)" % str(exc)[:60])
        return "error"
    try:
        with scratchpad_lib.open_scratchpad(plan_id=plan_id) as store:
            store.set(SCRATCHPAD_KEY, payload.encode("utf-8"))
        return "written"
    except Exception as exc:
        _breadcrumb("scratchpad write failed (%s)" % str(exc)[:80])
        return "error"


def gate(event: Dict[str, Any], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Build + persist the snapshot; emit the closed-enum event. Always allows.

    Returns ``{}`` (PreCompact hooks have no governance output channel — the
    snapshot is the side effect; PostCompact does the reinjection)."""
    if os.environ.get("CEO_COMPACTION_CONTINUITY", "1") == "0":
        return {}
    deadline = time.monotonic() + TIME_BUDGET_S
    cwd = os.path.realpath(cwd or os.getcwd())
    trigger = _trigger_class(event)
    plan_id = _resolve_plan_id(event)
    plan_path = _plan_file_for(plan_id, cwd)
    blob: Dict[str, Any] = {
        "schema": "compaction-continuity/v1",
        "ts": time.time(),
        "trigger": trigger,
        "plan_id": plan_id,
        "execution_unit": _execution_unit(plan_path, cwd, deadline),
        "ceremony_flags": _ceremony_flags(cwd, deadline),
        "hmac_chain": _hmac_chain_breadcrumb(),
    }
    chain_length = 0
    try:
        chain_length = int(blob["hmac_chain"].get("chain_length", 0))
    except (TypeError, ValueError, AttributeError):
        chain_length = 0
    outcome = _write_snapshot(plan_id, blob)
    _emit_snapshot_event(trigger, plan_id, chain_length, outcome)
    return {}


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: parse error is infra → breadcrumb + schema-compliant allow.
        sys.stderr.write(
            "# check_precompact_continuity fail-open (stdin): %s\n" % str(exc)[:120]
        )
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input, hook_input.get("cwd"))))
    except Exception as exc:
        sys.stderr.write(
            "# check_precompact_continuity fail-open: %s\n" % str(exc)[:120]
        )
        print("{}")


if __name__ == "__main__":
    main()
