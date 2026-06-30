"""PLAN-017 Phase 1+3 — kill switch + circuit breakers.

Pure-function layer. The coordinator calls ``evaluate_kill_switch``
every iteration tick; the function returns a ``KillSwitchState`` the
coordinator acts on (halt all / pause / continue).

Layers implemented here (1-3, 5 — purely in-process):
1. Env var (CEO_SWARM=0 OR CEO_AUTONOMOUS_LOOPS_DISABLE=1)
2. File sentinel presence
3. Iteration counter (coordinator-owned monotonic)
5. OS-level cgroups/ulimit — scaffolded stub (returns None);
   real implementation deferred to PLAN-017 follow-up.

Layers 4 + 6 (SIGKILL-escalation + parent-process-death) require
subprocess supervision and land in the follow-up sprint alongside
worktree orchestration.

Circuit breakers implemented here (1-5 — pure predicates):
1. Budget (token)
2. Convergence (Jaccard via coordinator.detect_convergence)
3. Error rate (strike count per loop)
4. Noise floor (placeholder — returns None; MAD ratio lands in
   follow-up when actual iteration metric streams land)
5. Manual kill (file sentinel — same as layer-2 kill switch)

Circuit breakers 6-9 (disk, FDs, wall-clock, parent-death) are
coordinator-wired in the follow-up.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .coordinator import (
    LoopState,
    budget_exceeded,
    detect_convergence,
    optimizer_switch_state,
)
from ._parent_death import parent_still_alive


# PLAN-050 Phase 7a (C4) — CB 6-9 defaults.
# CB #6 disk free floor: 1 GiB default — aborts swarm if disk fills.
DEFAULT_MIN_DISK_FREE_BYTES = 1 * 1024 * 1024 * 1024
# CB #7 FD ceiling: 80% of soft rlimit (leaves headroom for teardown).
DEFAULT_FD_CEILING_RATIO = 0.80
# CB #8 wall-clock: 1h per swarm by default. Tunable.
DEFAULT_MAX_WALL_CLOCK_SECONDS = 3600.0


# Decision enum — plain strings to keep JSON-serializable.
DECISION_CONTINUE = "continue"
DECISION_PAUSE = "pause"  # graceful; Owner can resume
DECISION_HALT = "halt"  # hard stop; no resume


@dataclass
class KillSwitchState:
    """Result of ``evaluate_kill_switch``.

    ``decision`` is one of continue / pause / halt. ``reasons`` is the
    ordered list of circuit breakers / kill layers that triggered;
    empty when decision == continue.

    ``loops_to_kill`` is the subset of loop ids the coordinator must
    transition to status=killed (e.g. convergence losers). Separate
    from ``decision=halt`` which kills the entire swarm.
    """

    decision: str = DECISION_CONTINUE
    reasons: List[str] = field(default_factory=list)
    loops_to_kill: List[str] = field(default_factory=list)

    def add_reason(self, reason: str) -> None:
        if reason not in self.reasons:
            self.reasons.append(reason)

    def escalate(self, new_decision: str) -> None:
        """Upgrade decision precedence: continue < pause < halt."""

        order = {DECISION_CONTINUE: 0, DECISION_PAUSE: 1, DECISION_HALT: 2}
        if new_decision not in order:
            raise ValueError(f"unknown decision {new_decision!r}")
        if order[new_decision] > order[self.decision]:
            self.decision = new_decision

    def to_dict(self) -> Dict[str, object]:
        return {
            "decision": self.decision,
            "reasons": list(self.reasons),
            "loops_to_kill": list(self.loops_to_kill),
        }


def _disk_free_bytes(path: Path) -> Optional[int]:
    """Return free bytes available at `path`. None on lookup failure (fail-open)."""
    try:
        return shutil.disk_usage(str(path)).free
    except (OSError, FileNotFoundError):
        return None


def _open_fd_count() -> Optional[int]:
    """Return current open FD count for the process. None if unavailable.

    Linux uses `/proc/self/fd`; Darwin uses `/dev/fd`. On Windows + missing
    /proc, returns None and CB #7 becomes a no-op (fail-open).
    """
    for candidate in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(candidate):
            try:
                return len(os.listdir(candidate))
            except OSError:
                continue
    return None


def _fd_soft_limit() -> Optional[int]:
    """Return the soft rlimit for open FDs. None if unavailable."""
    if sys.platform == "win32":
        return None
    try:
        import resource
        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        return int(soft) if soft > 0 else None
    except Exception:
        return None


def evaluate_kill_switch(
    loops: Dict[str, LoopState],
    *,
    budget_tokens: int,
    jaccard_threshold: float = 0.7,
    max_strikes: int = 3,
    sentinel_path: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    iteration_limit: Optional[int] = None,
    disk_check_path: Optional[Path] = None,
    min_disk_free_bytes: int = DEFAULT_MIN_DISK_FREE_BYTES,
    fd_ceiling_ratio: float = DEFAULT_FD_CEILING_RATIO,
    swarm_start_monotonic: Optional[float] = None,
    max_wall_clock_seconds: float = DEFAULT_MAX_WALL_CLOCK_SECONDS,
    expected_parent_pid: Optional[int] = None,
) -> KillSwitchState:
    """Evaluate all in-process kill-switch + circuit-breaker conditions.

    Returns ``KillSwitchState``. Halt-level conditions short-circuit
    (once a halt is registered, further reasons may still append, but
    the decision cannot downgrade).
    """

    result = KillSwitchState()

    # Layer 1 — env var.
    src_env = env if env is not None else os.environ
    if src_env.get("CEO_SWARM", "0") != "1":
        result.escalate(DECISION_HALT)
        result.add_reason("kill_layer_1_env: CEO_SWARM!=1")
    if src_env.get("CEO_AUTONOMOUS_LOOPS_DISABLE", "0") == "1":
        result.escalate(DECISION_HALT)
        result.add_reason("kill_layer_1_env: CEO_AUTONOMOUS_LOOPS_DISABLE=1")

    # PLAN-122 §6 — OPTIMIZER switch (partitioned from the SAFETY gate above).
    # Advisory ONLY: an optimizer switch being OFF narrows the optimizer's
    # recommendations but MUST NOT change the decision (it can never halt the
    # swarm, nor turn dispatch back on). We record the reason for forensic
    # clarity so a refusal/recommendation can surface why fan-out was skipped.
    optimizer_state = optimizer_switch_state(src_env)
    if optimizer_state["reason"]:
        result.add_reason(str(optimizer_state["reason"]))

    # Layer 2 / CB #5 — file sentinel.
    if sentinel_path is not None and sentinel_path.exists():
        result.escalate(DECISION_HALT)
        result.add_reason("kill_layer_2_sentinel: kill_file_present")

    # Layer 3 — iteration counter ceiling (if provided).
    if iteration_limit is not None:
        if any(state.iteration >= iteration_limit for state in loops.values()):
            result.escalate(DECISION_PAUSE)
            result.add_reason("kill_layer_3_iteration_ceiling")

    # CB #1 — budget.
    if loops and budget_exceeded(loops, budget_tokens):
        result.escalate(DECISION_HALT)
        result.add_reason("cb_1_budget_exceeded")

    # CB #2 — convergence. Losers go into loops_to_kill; swarm keeps running.
    if loops:
        converged = detect_convergence(loops, jaccard_threshold)
        if converged:
            result.loops_to_kill.extend(converged)
            result.add_reason(f"cb_2_convergence: {','.join(converged)}")

    # CB #3 — error-rate (per-loop 3-strike).
    for lid, state in loops.items():
        if state.strikes >= max_strikes and lid not in result.loops_to_kill:
            result.loops_to_kill.append(lid)
            result.add_reason(f"cb_3_strikes: {lid}")

    # PLAN-050 Phase 7a (C4) — CB 6-9 additions.

    # CB #6 — disk free floor.
    if disk_check_path is not None:
        free = _disk_free_bytes(disk_check_path)
        if free is not None and free < min_disk_free_bytes:
            result.escalate(DECISION_HALT)
            result.add_reason(
                f"cb_6_disk_floor: free={free} < min={min_disk_free_bytes}"
            )

    # CB #7 — file-descriptor ceiling (relative to soft rlimit).
    open_fds = _open_fd_count()
    soft_limit = _fd_soft_limit()
    if open_fds is not None and soft_limit is not None:
        ceiling = int(soft_limit * fd_ceiling_ratio)
        if open_fds >= ceiling:
            result.escalate(DECISION_HALT)
            result.add_reason(
                f"cb_7_fd_ceiling: open={open_fds} >= {ceiling}/{soft_limit}"
            )

    # CB #8 — wall-clock ceiling.
    if swarm_start_monotonic is not None and max_wall_clock_seconds > 0:
        elapsed = time.monotonic() - swarm_start_monotonic
        if elapsed >= max_wall_clock_seconds:
            result.escalate(DECISION_HALT)
            result.add_reason(
                f"cb_8_wall_clock: elapsed={elapsed:.1f}s >= {max_wall_clock_seconds}s"
            )

    # CB #9 — parent-death watchdog.
    if expected_parent_pid is not None and expected_parent_pid > 0:
        if not parent_still_alive(expected_parent_pid):
            result.escalate(DECISION_HALT)
            result.add_reason(
                f"cb_9_parent_death: expected_ppid={expected_parent_pid} gone"
            )

    return result


def default_sentinel_path(project_root: Optional[Path] = None) -> Path:
    """Return the conventional kill-sentinel path.

    Matches the ``autonomous_loops.kill_switch_path`` setting in
    PLAN-017 0.13. Adopter can override via settings.json; this helper
    returns the default ``<project_root>/.claude/swarm-kill``.
    """

    root = project_root or Path.cwd()
    return root / ".claude" / "swarm-kill"
