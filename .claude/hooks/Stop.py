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
try:
    from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver
except Exception:  # pragma: no cover — partial upgrade: hook stays FAIL-OPEN (rail r1 P1-4)
    _rp = None  # type: ignore[assignment]


def _rp_state_dir():
    """Resolver com fallback de partial-upgrade (arquivo novo ausente).

    Fail-open: o hook NUNCA crasha por falta do resolvedor; degrada ao
    comportamento legado com aviso em stderr.
    """
    if _rp is not None:
        return _rp.runtime_state_dir()
    import sys as _s
    _s.stderr.write("# hook: _lib/runtime_paths ausente — fallback legado (partial upgrade)\n")
    from pathlib import Path as _P
    import os as _o
    _h = _o.environ.get("HOME") or str(_P.home())
    return _P(_h) / ".claude" / "projects" / "ceo-orchestration"  # rp-allow: partial-upgrade-fallback

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
            _rp_state_dir()
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

    # PLAN-179-FOLLOWUP (S338): PAYLOAD-first — payload > env > timestamp.
    # The SPEC threads the id "from the harness event" and CLAUDE_SESSION_ID
    # is agent-spoofable; the US8 consumer (SessionEnd._session_start_ts)
    # and every session-partitioning reader match rows by the PAYLOAD id, so
    # an env-first producer stranded every divergent session in
    # start_unknown (rail r6 P2-b of wave-179close) and split one lifecycle
    # across two ids. The FOUR lifecycle producers (SessionStart /
    # UserPromptSubmit / Stop / SessionEnd) flip in the SAME patch (S337 P2
    # sweep + pair-rail r1 of this wave). Env stays the fallback for a
    # payload without an id; the timestamp fallback is unchanged.
    session_id = (
        (getattr(event, "session_id", "") or "")
        or os.environ.get("CLAUDE_SESSION_ID", "")
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
