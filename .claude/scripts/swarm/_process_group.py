"""PLAN-050 Phase 7a (C4) + PLAN-051 Phase 6 — process group kill helpers.

Two-tier kill escalation per C4:
- Tier 1 (resource cap):   SIGTERM + 5s grace → SIGKILL + 2s reap grace
- Tier 2 (VETO/kill-file): immediate SIGKILL + 2s reap grace

Use `os.setsid()` in subprocess `preexec_fn` so the swarm's children
form a fresh process group independent of the coordinator's tty.
Then `os.killpg(pgid, SIG)` delivers signal to the whole tree (child
+ any grandchildren a loop spawned).

PLAN-051 Phase 6 Performance Risk #5 contract (event-driven, NOT
fixed-sleep): the poll loop uses `os.waitpid(pid, os.WNOHANG)` at
50ms intervals to detect child death immediately, and falls back
to `os.kill(pid, 0)` when the pid is not a direct child of the
caller. After SIGKILL a second 50ms-interval reap loop runs for
up to `POST_KILL_REAP_SECONDS` (2s) before the helper logs and
abandons — fail-open on infra per PROTOCOL §Fail-open.

Latency gates (PLAN-051 Phase 6 acceptance):
- Already-exited child: p99 ≤ 50ms (single poll-tick)
- Cooperative SIGTERM-responsive child: p99 ≤ 200ms (4 poll-ticks)
- Stuck child: hard cap = 5s SIGTERM + 2s SIGKILL reap = 7s

PID-namespace option on Linux (fork-race defense) is deferred to
Phase 7b kernel-batch when worktree isolation lands.

Windows unsupported; helpers return False without raising so a
Windows adopter's tests still pass.
"""
from __future__ import annotations

import os
import signal
import sys
import time
from typing import Optional

# Grace budget between SIGTERM and SIGKILL on Tier 1 escalation.
DEFAULT_GRACE_SECONDS = 5.0

# Poll interval for the event-driven death-watch loop. Tighter than
# the PLAN-050 baseline (100ms) per PLAN-051 Phase 6 Performance
# Risk #5 — 50ms gives p99 latency headroom under the Tier 1 gate.
DEFAULT_POLL_INTERVAL_SECONDS = 0.05

# Hard cap on post-SIGKILL reap wait. Exceeding this indicates a
# zombie/kernel-stuck child — helper logs to stderr (no stdout side
# channel in hooks) and returns, letting the coordinator decide
# whether to retry or escalate further.
POST_KILL_REAP_SECONDS = 2.0


def new_session_preexec() -> None:
    """`preexec_fn` for subprocess.Popen that creates a new session+pgid.

    Must be called inside the child process (after fork, before exec).
    On POSIX: `os.setsid()` makes the child a session leader; its pid
    becomes the pgid. On Windows: no-op.

    Example::

        p = subprocess.Popen(
            cmd,
            preexec_fn=new_session_preexec,
            start_new_session=True,  # redundant on POSIX but clear intent
        )
    """
    if sys.platform == "win32":
        return
    try:
        os.setsid()
    except OSError:
        # Already a session leader (e.g. ran under nohup) — not fatal.
        pass


def pgid_for(pid: int) -> Optional[int]:
    """Return process-group ID for `pid`, or None if lookup fails.

    Fail-open: returns None on any OSError so the caller can fall back
    to single-PID signalling. Windows returns None.
    """
    if sys.platform == "win32":
        return None
    try:
        return os.getpgid(pid)
    except (OSError, ProcessLookupError):
        return None


def kill_process_group(pid: int, sig: int = signal.SIGTERM) -> bool:
    """Send `sig` to the process group containing `pid`. Returns True on delivery.

    If the group lookup fails, falls back to a single-PID `os.kill`.
    Fail-open: returns False on unrecoverable errors (process gone,
    no permission, etc.) — caller decides whether to retry.
    """
    if sys.platform == "win32":
        try:
            os.kill(pid, sig)
            return True
        except (OSError, ProcessLookupError):
            return False
    pgid = pgid_for(pid)
    try:
        if pgid is not None:
            os.killpg(pgid, sig)
        else:
            os.kill(pid, sig)
        return True
    except (OSError, ProcessLookupError):
        return False


def escalated_kill(
    pid: int,
    *,
    tier: int = 1,
    grace_seconds: float = DEFAULT_GRACE_SECONDS,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_SECONDS,
    post_kill_reap_seconds: float = POST_KILL_REAP_SECONDS,
) -> str:
    """Kill process `pid` (or its group) with tiered, event-driven escalation.

    Uses `waitpid(pid, WNOHANG)` (when `pid` is a direct child) or
    `os.kill(pid, 0)` fallback polling at ``poll_interval_s``
    (default 50ms) to exit the grace window as soon as the process
    dies — no fixed-sleep timing.

    - Tier 1: SIGTERM, wait up to `grace_seconds` (polling 50ms),
      escalate to SIGKILL if still alive, then reap-poll for up
      to `post_kill_reap_seconds` before logging and abandoning.
    - Tier 2: SIGKILL immediately; reap-poll for up to
      `post_kill_reap_seconds`.

    Returns the escalation tier slug actually used:
    - ``"sigterm"`` — SIGTERM succeeded and process exited during grace.
    - ``"sigkill_tier1"`` — SIGTERM sent, grace elapsed, SIGKILL delivered.
    - ``"sigkill_tier2"`` — immediate SIGKILL.
    - ``"sigkill_abandoned"`` — SIGKILL delivered but reap-poll timed
      out (kernel-stuck / zombie). Logged to stderr; coordinator
      decides next action.
    - ``"gone"`` — process already absent when we tried (no-op).
    """
    if tier not in (1, 2):
        raise ValueError(f"tier must be 1 or 2; got {tier!r}")
    # Tier 2 — immediate SIGKILL.
    if tier == 2:
        if not kill_process_group(pid, signal.SIGKILL):
            return "gone"
        reaped = _wait_for_death(pid, post_kill_reap_seconds, poll_interval_s)
        if not reaped:
            _log_abandoned(pid, "sigkill_tier2", post_kill_reap_seconds)
            return "sigkill_abandoned"
        return "sigkill_tier2"
    # Tier 1 — SIGTERM → event-driven grace → SIGKILL → reap
    if not kill_process_group(pid, signal.SIGTERM):
        return "gone"
    if _wait_for_death(pid, grace_seconds, poll_interval_s):
        return "sigterm"
    # SIGTERM grace elapsed — escalate.
    if not kill_process_group(pid, signal.SIGKILL):
        # Between the grace expiry and our SIGKILL attempt the
        # process vanished — treat as successful cooperative shutdown.
        return "sigterm"
    reaped = _wait_for_death(pid, post_kill_reap_seconds, poll_interval_s)
    if not reaped:
        _log_abandoned(pid, "sigkill_tier1", post_kill_reap_seconds)
        return "sigkill_abandoned"
    return "sigkill_tier1"


def _wait_for_death(
    pid: int, deadline_seconds: float, poll_interval_s: float
) -> bool:
    """Poll until `pid` is dead OR `deadline_seconds` elapses.

    Event-driven: uses `waitpid(pid, WNOHANG)` first (reaps zombies
    when the target is a direct child) and falls back to
    `os.kill(pid, 0)` when waitpid reports ECHILD (pid not our
    child). Returns True if death observed, False if deadline hit.

    `poll_interval_s` is the *worst-case* latency between the child
    dying and our observation — 50ms default gives p99 latency well
    within PLAN-051 Phase 6 gate (cooperative child ≤200ms).
    """
    if deadline_seconds <= 0:
        return not _is_alive(pid)
    deadline = time.monotonic() + deadline_seconds
    while True:
        if _reap_or_check_gone(pid):
            return True
        if time.monotonic() >= deadline:
            # One final check without a sleep so the common-case
            # "child died right at deadline" doesn't false-negative.
            return _reap_or_check_gone(pid)
        time.sleep(poll_interval_s)


def _reap_or_check_gone(pid: int) -> bool:
    """True if `pid` is gone (reaped, exited, or never our child).

    Prefers `waitpid(pid, WNOHANG)` so direct-child zombies are
    reaped atomically with the death detection. Falls back to
    `os.kill(pid, 0)` when the pid is not a direct child (ECHILD).
    """
    if sys.platform == "win32":
        return not _is_alive(pid)
    try:
        reaped_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        # pid is not (or no longer) our child — fall back to the
        # signal-0 probe. Still fail-open if that also errors.
        return not _is_alive(pid)
    except OSError:
        return not _is_alive(pid)
    if reaped_pid == pid:
        return True
    # reaped_pid == 0 means child is still alive AND unreaped.
    return False


def _log_abandoned(pid: int, tier_slug: str, reap_seconds: float) -> None:
    """Emit a single-line stderr breadcrumb when reap-poll times out.

    Hooks never block on infra failures (PROTOCOL §Fail-open), so the
    coordinator logs and continues. A dedicated audit_emit event
    would require a dependency on hooks/_lib which this module does
    not import — breadcrumb to stderr is sufficient for CI forensics.
    """
    try:
        sys.stderr.write(
            f"kill_switch.escalated_kill: pid={pid} tier={tier_slug} "
            f"still alive after {reap_seconds}s reap-poll; abandoning "
            f"(possibly zombie or kernel-stuck)\n"
        )
    except Exception:
        # Never raise from a log helper.
        pass


def _is_alive(pid: int) -> bool:
    """Return True if the PID is still running. Fail-open to False."""
    try:
        # Signal 0 never delivers; raises ProcessLookupError if gone.
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
