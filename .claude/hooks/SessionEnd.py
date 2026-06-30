#!/usr/bin/env python3
"""SessionEnd lifecycle hook (PLAN-028 / ADR-056 + PLAN-059 / ADR-080
 + ADR-090).

Fires at the end of every Claude Code session. Four responsibilities:

1. **Audit closeout** — emit `session_end` event with reason
   (normal / interrupted / error) and memory state breadcrumbs.
2. **Memory persistence verify** — assert the native memory dir
   (`~/.claude/projects/<slug>/memory/`) is writable and
   `MEMORY.md` index is readable. Drift signal: breadcrumb + event.
3. **Audit-log flush** — touch the audit-log filelock to ensure
   any pending writes are drained before process exit (best-effort;
   filelock guarantees append order within the session).
4. **Audit-tokens auto-run** — invoke `audit-tokens.py` subprocess
   with 1s wall-clock timeout (PLAN-059 SEC-P0-04 / ADR-080). Default
   ON since Session 67 / ADR-090 #6. Emits `audit_tokens_emitted`
   event when subprocess completes; `audit_tokens_timeout` when it
   exceeds the cap.

## Fail-open contract (ADR-005)

Any internal exception → `{"continue": true}` lifecycle output.
SessionEnd does not ever block the session end — the hook is
observational.

## Kill-switches

- `CEO_EXTENDED_LIFECYCLE=0` — disables the entire hook (no-op
  return). Highest priority.
- `CEO_AUDIT_TOKENS_AUTO=0` — disables responsibility #4 only.
  Responsibilities #1-#3 still run. Default is ON (per ADR-090 #6
  Session 67 default flip).
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

# PLAN-059 SEC-P0-04 / ADR-080 — audit-tokens auto-run.
# Default OFF (opt-in). Set CEO_AUDIT_TOKENS_AUTO=1 to enable per-session
# audit_tokens_emitted event emission via subprocess invocation.
_AUDIT_TOKENS_AUTO_ENV = "CEO_AUDIT_TOKENS_AUTO"
# Hard timeout per SEC-P0-04 §Performance budget. Subprocess wall-clock cap.
# PLAN-044 audit-v2 C3-P0-05 — bumped 0.05 → 1.0 (Wave B). Audit-v2 dim 22
# observed 92% timeout failure rate at 50ms; 1s leaves headroom for the
# audit-tokens.py subprocess startup + 6-detector pass over a 30-day window
# while still bounding worst-case session-close latency.
_AUDIT_TOKENS_TIMEOUT_SECONDS = 1.0


def _emit_observe(system_message: Optional[str] = None) -> str:
    """Schema-compliant lifecycle hook output (see SessionStart docstring)."""
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _kill_switch_active() -> bool:
    val = os.environ.get(_KILL_SWITCH_ENV, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _memory_dir_state(repo_root: Path) -> Dict[str, object]:
    """Check native memory dir health. Returns {writable, memory_md_present}.

    Uses ~/.claude/projects/<slug>/memory/ where slug is derived from
    the absolute repo path. Best-effort — never raises.
    """
    state: Dict[str, object] = {
        "writable": False,
        "memory_md_present": False,
        "slug": "",
    }
    try:
        slug = str(repo_root).replace("/", "-").lstrip("-")
        memory_dir = Path.home() / ".claude" / "projects" / f"-{slug}" / "memory"
        state["slug"] = slug
        if memory_dir.is_dir():
            state["writable"] = os.access(memory_dir, os.W_OK)
            state["memory_md_present"] = (memory_dir / "MEMORY.md").is_file()
    except Exception:
        pass
    return state


def _emit_session_end(
    *,
    session_id: str,
    reason: str,
    memory_state: Dict[str, object],
    repo_root: Path,
) -> None:
    """Best-effort audit event. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is not None:
            emitter(
                action="session_end",
                session_id=session_id,
                hook_version=_HOOK_VERSION,
                reason=reason,
                memory_writable=bool(memory_state.get("writable")),
                memory_index_present=bool(memory_state.get("memory_md_present")),
                project=str(repo_root),
            )
    except Exception:
        return


def _audit_tokens_auto_active() -> bool:
    """True unless CEO_AUDIT_TOKENS_AUTO=0 (default flipped to ON per
    PLAN-059 / ADR-090 #6, Session 67 2026-04-27).

    Default flip rationale: 24 unit tests + ~26ms smoke + 50ms wall
    timeout + content-ban allowlist enforced (SEC-P0-04). Adopters
    opt out via CEO_AUDIT_TOKENS_AUTO=0.
    """
    val = os.environ.get(_AUDIT_TOKENS_AUTO_ENV, "").strip().lower()
    if val in {"0", "false", "off", "no"}:
        return False
    # Empty / unset / any other value → ON (per ADR-090 #6 default flip).
    return True


def _invoke_audit_tokens_stub(*, repo_root: Path, session_id: str) -> None:
    """SEC-P0-04 / ADR-080 — invoke audit-tokens.py stub format with timeout.

    Runs `audit-tokens.py --window 1 --format stub --content-ban=strict
    --session-id <id>` as subprocess with `_AUDIT_TOKENS_TIMEOUT_SECONDS`
    wall clock. On TimeoutExpired: emit audit_tokens_timeout event +
    skip the audit_tokens_emitted event (subprocess writes the event
    itself when it succeeds; on timeout the writer never runs).

    Fail-open contract: any other exception → silent return. Hook is
    observational and MUST NOT block session-end on this path.
    """
    if not _audit_tokens_auto_active():
        return  # Kill-switch off (default OFF per opt-in policy)

    audit_tokens_script = repo_root / ".claude" / "scripts" / "audit-tokens.py"
    if not audit_tokens_script.is_file():
        return  # Script not present (some adopter configs)

    try:
        import subprocess as _sp
        _sp.run(
            [
                sys.executable,
                str(audit_tokens_script),
                "--window", "1",
                "--format", "stub",
                "--content-ban", "strict",
                "--session-id", session_id,
            ],
            timeout=_AUDIT_TOKENS_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
            check=False,
        )
    except _sp.TimeoutExpired:
        # SEC-P0-04 §Performance budget — emit timeout breadcrumb in
        # place of the audit_tokens_emitted event. The subprocess never
        # got to call emit_audit_tokens_emitted, so no allowlist event
        # was written; we record the timeout fact for forensic analysis.
        try:
            from _lib import audit_emit  # type: ignore
            emit_timeout = getattr(audit_emit, "emit_audit_tokens_timeout", None)
            if emit_timeout is not None:
                emit_timeout(
                    session_id=session_id,
                    timeout_seconds=_AUDIT_TOKENS_TIMEOUT_SECONDS,
                    project=str(repo_root),
                )
        except Exception:
            pass
    except Exception:
        # All other exceptions silently swallowed (fail-open).
        pass


def _invoke_value_dashboard_summarize(
    *,
    repo_root: Path,
    session_id: str,
) -> None:
    """Roll up per-session value dashboard summary + emit
    ``value_dashboard_summarized`` audit event (PLAN-085 Wave C.4)."""
    if os.environ.get("CEO_VALUE_DASHBOARD_AUTO", "1") == "0":
        return
    try:
        from _lib import audit_emit  # type: ignore
        from _lib import value_dashboard_summary  # type: ignore
    except Exception:
        return
    try:
        summary = value_dashboard_summary.rollup_for_session(
            repo_root=repo_root,
            session_id=session_id,
            period_days=1,
        )
        audit_emit.emit_generic(
            "value_dashboard_summarized",
            period_days=int(summary.get("period_days", 1)),
            cost_usd_int_cents=int(summary.get("cost_usd_int_cents", 0)),
            bugs_count=int(summary.get("bugs_count", 0)),
            dispatches_count=int(summary.get("dispatches_count", 0)),
            plans_count=int(summary.get("plans_count", 0)),
            session_id=session_id,
            project=str(repo_root),
        )
    except Exception:
        pass


def _cleanup_tool_lifecycle(session_id: str) -> None:
    """PLAN-125 WS-1 — flush orphans, then delete the per-session record file.

    At SessionEnd any tool that stamped a PreToolUse record but never produced
    a Post/Failure is, by definition, an orphan (the session is ending; it will
    never complete) — so sweep with ``timeout_s=0.0`` to emit
    ``tool_call_lifecycle_recorded`` with ``orphan=True`` for every survivor
    BEFORE evicting the file. This is the production trigger that makes orphan
    detection reachable (MF-PERF-3); without it the affirmative orphan branch
    was dead in production (perf-review must-fix). The sweep emit is the
    deny-by-default scrub-branch action, fail-OPEN.

    Then ``cleanup_session`` bounds the record-file lifecycle to a single
    session (MF-PERF-2). Best-effort + fail-open: SessionEnd is observational
    and MUST NOT block on this.
    """
    try:
        from _lib import tool_lifecycle  # type: ignore
        # Flush any in-flight (unpaired) Pre records as orphans first.
        tool_lifecycle.sweep_orphans(session_id, timeout_s=0.0)
        tool_lifecycle.cleanup_session(session_id)
    except Exception:
        return


def _flush_audit_log_filelock(repo_root: Path) -> None:
    """Touch + release the audit-log filelock as a drain barrier.

    This does not force a fsync; that is the writer's responsibility.
    The barrier primitive ensures any concurrent writer holding the
    lock finishes before this hook returns control to the harness.
    """
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


def decide(*, repo_root: Path, session_id: str, reason: str) -> str:
    """Pure decision function."""
    if _kill_switch_active():
        return _emit_observe(system_message="SessionEnd: kill-switch active, no-op")

    try:
        memory_state = _memory_dir_state(repo_root)
        # PLAN-125 WS-1 — evict the per-session lifecycle record file (MF-PERF-2).
        _cleanup_tool_lifecycle(session_id)
        _flush_audit_log_filelock(repo_root)
        # SEC-P0-04: audit-tokens stub auto-run BEFORE session_end emit
        # so the emitted event lands in the same session window.
        _invoke_audit_tokens_stub(
            repo_root=repo_root,
            session_id=session_id,
        )
        # PLAN-085 Wave C.4 — value_dashboard_summarized production callsite.
        _invoke_value_dashboard_summarize(
            repo_root=repo_root,
            session_id=session_id,
        )
        _emit_session_end(
            session_id=session_id,
            reason=reason,
            memory_state=memory_state,
            repo_root=repo_root,
        )
        return _emit_observe(
            system_message=(
                f"SessionEnd: reason={reason}, "
                f"memory_writable={memory_state.get('writable')}"
            )
        )
    except Exception as e:
        sys.stderr.write(f"[SessionEnd] FATAL: {type(e).__name__}: {e}\n")
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
        event = _claude_adapter.read_event(phase="SessionEnd")
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    session_id = (
        os.environ.get("CLAUDE_SESSION_ID", "")
        or getattr(event, "session_id", "") or ""
    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    reason = os.environ.get("CLAUDE_SESSION_END_REASON", "normal")
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    try:
        out = decide(repo_root=repo_root, session_id=session_id, reason=reason)
    except Exception as e:
        sys.stderr.write(f"[SessionEnd] FATAL: {type(e).__name__}: {e}\n")
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
