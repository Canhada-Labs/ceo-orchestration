#!/usr/bin/env python3
"""Stop lifecycle hook (PLAN-028 / ADR-056).

Fires when the session is interrupted (Ctrl+C, process kill signal,
timeout). Three responsibilities:

1. **Emit `session_stop` event** — session_id + interrupt reason
   (SIGINT / SIGTERM / timeout / user_stop) + partial_state_saved
   flag (true if SessionEnd already ran, false otherwise).
2. **Audit-log flush** — touch the filelock to drain pending
   writes before process exit. Same primitive as SessionEnd.
3. **Filelock release** — best-effort unlink of stale lock files
   in the session's scratch dir (prevents next session seeing
   a stuck lock).

## Fail-open contract (ADR-005)

Any internal exception → `{"decision":"allow"}`. Stop never
blocks; its job is graceful cleanup.

## Kill-switch

`CEO_EXTENDED_LIFECYCLE=0` disables this hook.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_KILL_SWITCH_ENV = "CEO_EXTENDED_LIFECYCLE"
_HOOK_VERSION = "1.0.0"


def _emit_observe(system_message: Optional[str] = None) -> str:
    """Schema-compliant lifecycle hook output (see SessionStart docstring)."""
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _kill_switch_active() -> bool:
    val = os.environ.get(_KILL_SWITCH_ENV, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _emit_session_stop(
    *,
    session_id: str,
    reason: str,
    partial_state_saved: bool,
    repo_root: Path,
) -> None:
    """Best-effort audit event. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is not None:
            emitter(
                action="session_stop",
                session_id=session_id,
                hook_version=_HOOK_VERSION,
                reason=reason,
                partial_state_saved=partial_state_saved,
                project=str(repo_root),
            )
    except Exception:
        return


def _flush_audit_log_filelock() -> None:
    """Drain pending audit-log writes. Same as SessionEnd."""
    try:
        from _lib.filelock import FileLock  # type: ignore
    except Exception:
        return
    try:
        lock_path = (
            Path.home() / ".claude" / "projects" / "ceo-orchestration"
            / "audit-log.jsonl.lock"
        )
        if lock_path.exists():
            with FileLock(str(lock_path), timeout=0.5):
                pass
    except Exception:
        return


def _release_stale_locks(repo_root: Path) -> int:
    """Best-effort: unlink *.lock files in scratch dir if older than 60s.

    Returns number of locks released.
    """
    released = 0
    try:
        import time
        scratch = repo_root / ".claude" / "scratch"
        if not scratch.is_dir():
            return 0
        cutoff = time.time() - 60
        for lock_path in scratch.glob("*.lock"):
            try:
                if lock_path.stat().st_mtime < cutoff:
                    lock_path.unlink()
                    released += 1
            except OSError:
                continue
    except Exception:
        return released
    return released


def decide(
    *, repo_root: Path, session_id: str, reason: str, end_already_ran: bool
) -> str:
    """Pure decision function."""
    if _kill_switch_active():
        return _emit_observe(system_message="Stop: kill-switch active, no-op")

    try:
        _flush_audit_log_filelock()
        released = _release_stale_locks(repo_root)
        _emit_session_stop(
            session_id=session_id,
            reason=reason,
            partial_state_saved=end_already_ran,
            repo_root=repo_root,
        )
        return _emit_observe(
            system_message=(
                f"Stop: reason={reason}, stale_locks_released={released}, "
                f"partial_saved={end_already_ran}"
            )
        )
    except Exception as e:
        sys.stderr.write(f"[Stop] FATAL: {type(e).__name__}: {e}\n")
        return _emit_observe()


def main() -> int:
    """Hook entry point. Emits schema-compliant lifecycle JSON output.

    Output shape: `{"continue": true, "systemMessage": "..."}` — no
    `decision` field (lifecycle schema does NOT accept "allow").
    """
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="Stop")
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    session_id = (
        os.environ.get("CLAUDE_SESSION_ID", "")
        or getattr(event, "session_id", "") or ""
    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    reason = os.environ.get("CLAUDE_STOP_REASON", "user_stop")
    end_already_ran = (
        os.environ.get("CLAUDE_SESSION_END_COMPLETED", "").strip().lower()
        in {"1", "true", "yes"}
    )
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    try:
        out = decide(
            repo_root=repo_root,
            session_id=session_id,
            reason=reason,
            end_already_ran=end_already_ran,
        )
    except Exception as e:
        sys.stderr.write(f"[Stop] FATAL: {type(e).__name__}: {e}\n")
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
