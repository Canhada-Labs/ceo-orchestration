"""PLAN-017 Phase 1 + PLAN-051 Phase 6 — swarm coordinator.

Orchestrates N parallel autonomous loops with convergence detection +
budget envelope + kill switch. stdlib-only. CLI + library import both
supported.

Scaffold. The actual worktree-per-loop orchestration (ADR-049a
decision, deferred) + policy engine wiring land in PLAN-017 follow-up
sprints. This module ships the pure functions + dataclasses +
argparse CLI skeleton so the control-flow contract is reviewable.

Kill switch: 6 layers per PLAN-017 Design Principle #2 (C-04
consensus). This module enforces layers 1-3 (env var, file sentinel,
iteration counter) directly AND exposes ``tick()`` — the per-
iteration wire point that composes layers 4-6 (SIGKILL escalation
via ``_process_group.escalated_kill``, cgroups via future
``_resource_limits``, parent-death via ``_parent_death``). PLAN-051
Phase 6 acceptance: ``parent_still_alive(`` has a defined call site
in this module so the watchdog is not wrapper-only.

Circuit breakers: 9 mandatory per PLAN-017 Design Principle #3 (C-05
consensus). This module enforces categories 1-5 (budget, convergence,
error rate, noise floor, manual kill) via pure helpers; categories
6-9 (disk, FDs, wall-clock, parent-death) are coordinator-wired via
``tick()`` delegating to ``kill_switch.evaluate_kill_switch``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Numeric ceilings per ADR-051 (consensus C-11). Enterprise profile
# can raise with ops review + documented hardware requirements.
MAX_PARALLEL_CEILING = 8

# Default Jaccard threshold for convergence detection. Tunable via
# SwarmConfig.jaccard_threshold; bounded [0.0, 1.0].
DEFAULT_JACCARD_THRESHOLD = 0.7

# Default max iterations per loop before wall-clock circuit breaker
# trips (CB #8 per consensus C-05 N-02).
DEFAULT_MAX_ITERATIONS = 20

# Default max strikes per loop before 3-strike kill (CB #3 error rate).
DEFAULT_MAX_STRIKES = 3


@dataclass
class LoopState:
    """Per-loop state snapshot emitted on each iteration event.

    Deliberately keeps file paths as ``List[str]`` (not Set) for
    deterministic JSONL serialization. Set conversion happens at
    comparison time inside ``jaccard``/``detect_convergence``.
    """

    loop_id: str
    iteration: int = 0
    tokens_consumed: int = 0
    files_touched: List[str] = field(default_factory=list)
    kept_changes: int = 0
    strikes: int = 0
    status: str = "running"  # running | converged | killed | completed | errored

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "LoopState":
        return cls(
            loop_id=str(payload["loop_id"]),
            iteration=int(payload.get("iteration", 0) or 0),
            tokens_consumed=int(payload.get("tokens_consumed", 0) or 0),
            files_touched=list(payload.get("files_touched") or []),
            kept_changes=int(payload.get("kept_changes", 0) or 0),
            strikes=int(payload.get("strikes", 0) or 0),
            status=str(payload.get("status", "running")),
        )


@dataclass
class SwarmConfig:
    """Swarm-level configuration.

    ``n_loops`` is clamped at construction time to ``MAX_PARALLEL_CEILING``
    (ADR-051). ``jaccard_threshold`` is clamped to [0.0, 1.0].
    ``budget_tokens`` MUST be strictly positive — zero/negative raises
    ValueError (CB #1 can't trip meaningfully below 0).
    """

    n_loops: int
    budget_tokens: int
    goal: str
    jaccard_threshold: float = DEFAULT_JACCARD_THRESHOLD
    max_strikes: int = DEFAULT_MAX_STRIKES
    max_iterations: int = DEFAULT_MAX_ITERATIONS

    def __post_init__(self) -> None:
        if self.n_loops < 1:
            raise ValueError("n_loops must be >= 1")
        if self.n_loops > MAX_PARALLEL_CEILING:
            # Clamp rather than reject so CLI misuse is non-fatal; the
            # actual loop runner emits an audit event noting the clamp.
            self.n_loops = MAX_PARALLEL_CEILING
        if self.budget_tokens <= 0:
            raise ValueError("budget_tokens must be > 0")
        if not 0.0 <= self.jaccard_threshold <= 1.0:
            raise ValueError("jaccard_threshold must be in [0.0, 1.0]")
        if self.max_strikes < 1:
            raise ValueError("max_strikes must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if not self.goal or not self.goal.strip():
            raise ValueError("goal must be a non-empty string")


def jaccard(a: set, b: set) -> float:
    """Pure Jaccard similarity. ``J(A,B) = |A∩B| / |A∪B|``.

    Corner cases:
    - Both empty → 1.0 (vacuously identical, matches PLAN-011 M1
      convergence gate semantics).
    - Exactly one empty → 0.0.
    """

    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def detect_convergence(
    loops: Dict[str, LoopState], threshold: float = DEFAULT_JACCARD_THRESHOLD
) -> List[str]:
    """Return ids of loops that have converged with an earlier loop.

    Pairwise compare ``files_touched`` sets. When pair (A,B) exceeds
    threshold, the later-indexed loop (B) is marked for kill — the
    earlier loop keeps running so at least one representative survives.
    Returned list is deterministic (insertion order of ``loops`` dict).
    """

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0.0, 1.0]")
    converged: List[str] = []
    ids = list(loops.keys())
    for i, a_id in enumerate(ids):
        if a_id in converged:
            continue
        for b_id in ids[i + 1 :]:
            if b_id in converged:
                continue
            a_files = set(loops[a_id].files_touched)
            b_files = set(loops[b_id].files_touched)
            if jaccard(a_files, b_files) >= threshold:
                converged.append(b_id)
    return converged


def budget_exceeded(loops: Dict[str, LoopState], budget: int) -> bool:
    """True iff Σ tokens_consumed across all loops > budget."""

    if budget <= 0:
        raise ValueError("budget must be > 0")
    total = sum(loop.tokens_consumed for loop in loops.values())
    return total > budget


def env_kill_switch_tripped(env: Optional[Dict[str, str]] = None) -> bool:
    """Layer-1 kill switch: ``CEO_SWARM=0`` OR ``CEO_AUTONOMOUS_LOOPS_DISABLE=1``.

    Either condition alone trips the switch. Reads ``os.environ`` by
    default; unit tests pass an explicit dict.
    """

    src = env if env is not None else os.environ
    if src.get("CEO_SWARM", "0") == "0":
        # Default-OFF per Design Principle #1 — ABSENT CEO_SWARM=1
        # means the swarm is disabled, regardless of sentinel file.
        return True
    if src.get("CEO_AUTONOMOUS_LOOPS_DISABLE", "0") == "1":
        return True
    return False


# ---------------------------------------------------------------------------
# PLAN-122 §6 — OPTIMIZER kill-switch fabric (partitioned from the SAFETY gate).
#
# The SAFETY gate above (CEO_SWARM / CEO_AUTONOMOUS_LOOPS_DISABLE) is
# default-OFF: it gates whether the swarm may dispatch AT ALL, and absence
# means "disabled". The OPTIMIZER switches below are the inverse posture —
# the optimizer layer is default-ON, and ``=0`` (case-insensitive OFF value)
# disables a feature. They are read from ``os.environ`` ONLY (never a settings
# file or in-repo sentinel) so a prompt-injected sub-agent cannot flip the
# optimizer by writing config — mirrors ``UserPromptSubmit._kill_switch_active``
# and ``optimizer._skeleton.kill_switch_off``.
#
# These NEVER relax the SAFETY gate: tripping an optimizer switch only narrows
# the optimizer's recommendations, it can never turn dispatch back on.
# ---------------------------------------------------------------------------

# Values that mean "switch is OFF" (case-insensitive, stripped). Matches
# optimizer._skeleton._OFF_VALUES so the partition reads identically on both
# sides of the recommender boundary.
_OPTIMIZER_OFF_VALUES = frozenset({"0", "false", "off", "no"})

# Group switch — disables the whole optimizer layer when OFF.
OPTIMIZER_GROUP_SWITCH = "CEO_OPTIMIZER"
# Individual feature switch — disables fan-out width expansion when OFF.
OPTIMIZER_FANOUT_SWITCH = "CEO_FANOUT"


def _optimizer_switch_off(var: str, env: Optional[Dict[str, str]] = None) -> bool:
    """True iff ``env[var]`` (default 'on') is an OFF value (default-ON switch).

    ``os.environ`` ONLY by default — never reads a file. Unit tests pass an
    explicit dict. Absent var → ON (returns False). Never raises.
    """

    src = env if env is not None else os.environ
    try:
        return src.get(var, "1").strip().lower() in _OPTIMIZER_OFF_VALUES
    except Exception:
        # Fail-open: a malformed env value must not crash the coordinator,
        # and must not silently disable the optimizer either — treat as ON.
        return False


def optimizer_layer_disabled(env: Optional[Dict[str, str]] = None) -> bool:
    """Group OPTIMIZER switch: ``CEO_OPTIMIZER=0`` disables the whole layer.

    Default-ON (absent ⇒ enabled). Partitioned from the SAFETY gate — this
    only governs the optimizer recommendations, never swarm dispatch.
    """

    return _optimizer_switch_off(OPTIMIZER_GROUP_SWITCH, env)


def optimizer_fanout_disabled(env: Optional[Dict[str, str]] = None) -> bool:
    """Individual OPTIMIZER switch: fan-out width expansion is disabled.

    True when ``CEO_FANOUT=0`` (individual) OR ``CEO_OPTIMIZER=0`` (group
    dominates — disabling the whole layer also disables fan-out). Default-ON.
    """

    if optimizer_layer_disabled(env):
        return True
    return _optimizer_switch_off(OPTIMIZER_FANOUT_SWITCH, env)


def optimizer_switch_state(env: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Resolved OPTIMIZER switch snapshot + a human reason if anything is off.

    Returns a JSON-clean dict the coordinator can surface alongside a refusal
    or recommendation. ``reason`` is "" when the optimizer is fully enabled.
    The group switch is reported as dominating fan-out (group OFF ⇒ fan-out OFF).
    """

    group_off = optimizer_layer_disabled(env)
    fanout_off = optimizer_fanout_disabled(env)
    if group_off:
        reason = "optimizer_kill_switch: CEO_OPTIMIZER=0 (group; optimizer layer disabled)"
    elif fanout_off:
        reason = "optimizer_kill_switch: CEO_FANOUT=0 (individual; fan-out width expansion disabled)"
    else:
        reason = ""
    return {
        "optimizer_enabled": not group_off,
        "fanout_enabled": not fanout_off,
        "reason": reason,
    }


def sentinel_file_kill_switch_tripped(sentinel_path: Path) -> bool:
    """Layer-2 kill switch: file sentinel presence.

    Matches the ``autonomous_loops.kill_switch_path`` setting in
    PLAN-017 0.13. Presence of the file = kill (regardless of content).
    """

    return sentinel_path.exists()


def enumerate_active_loops(
    loops: Dict[str, LoopState],
) -> List[str]:
    """Ids of loops whose status is 'running' (not converged/killed/done)."""

    return [lid for lid, state in loops.items() if state.status == "running"]


def summarize(loops: Dict[str, LoopState]) -> Dict[str, object]:
    """Aggregate snapshot for audit-dashboard consumption."""

    total_tokens = sum(loop.tokens_consumed for loop in loops.values())
    total_iters = sum(loop.iteration for loop in loops.values())
    status_counts: Dict[str, int] = {}
    for loop in loops.values():
        status_counts[loop.status] = status_counts.get(loop.status, 0) + 1
    return {
        "n_loops": len(loops),
        "total_tokens_consumed": total_tokens,
        "total_iterations": total_iters,
        "status_counts": status_counts,
        "active": enumerate_active_loops(loops),
    }


def tick(
    loops: Dict[str, LoopState],
    *,
    cfg: SwarmConfig,
    sentinel_path: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    iteration_limit: Optional[int] = None,
    swarm_start_monotonic: Optional[float] = None,
    expected_parent_pid: Optional[int] = None,
    disk_check_path: Optional[Path] = None,
) -> "Any":  # -> "swarm.kill_switch.KillSwitchState"
    """Per-iteration kill-switch + watchdog wire point.

    PLAN-051 Phase 6 acceptance: this function has ≥1 DIRECT call
    site to :func:`_parent_death.parent_still_alive` — the parent-
    death watchdog is not wrapper-only. The coordinator calls
    ``tick()`` on every iteration; the returned ``KillSwitchState``
    tells the coordinator whether to continue, pause, or halt the
    swarm, and which individual loops to transition to killed.

    Parent-death check ordering:
    1. If ``expected_parent_pid`` is supplied, ``parent_still_alive``
       is invoked directly BEFORE the broader ``evaluate_kill_switch``
       sweep so the fastest infra-level kill fires first.
    2. ``evaluate_kill_switch`` then runs the full layer 1-3 + CB
       1-9 sweep (including its own CB #9 parent-death check for
       belt-and-suspenders coverage).

    Fail-open on infra: if the parent-death check itself raises an
    unexpected error, we log a breadcrumb but do not halt — the
    coordinator's other kill layers still cover the normal failure
    modes.
    """
    # PLAN-051 Phase 6 direct call site — harness mapper greps for
    # this; DO NOT refactor into a helper without updating
    # .claude/scripts/check-swarm-harness-mapping.py.
    from ._parent_death import parent_still_alive
    from .kill_switch import (
        DECISION_HALT,
        KillSwitchState,
        evaluate_kill_switch,
    )

    parent_dead_fast_path: Optional[str] = None
    if expected_parent_pid is not None and expected_parent_pid > 0:
        try:
            if not parent_still_alive(expected_parent_pid):
                parent_dead_fast_path = (
                    f"coordinator_tick_parent_death: "
                    f"expected_ppid={expected_parent_pid} gone"
                )
        except Exception as exc:  # pragma: no cover — fail-open path
            sys.stderr.write(
                f"coordinator.tick: parent_still_alive raised "
                f"{type(exc).__name__}: {exc}; continuing with "
                f"full evaluate_kill_switch sweep\n"
            )

    result = evaluate_kill_switch(
        loops,
        budget_tokens=cfg.budget_tokens,
        jaccard_threshold=cfg.jaccard_threshold,
        max_strikes=cfg.max_strikes,
        sentinel_path=sentinel_path,
        env=env,
        iteration_limit=iteration_limit,
        swarm_start_monotonic=swarm_start_monotonic,
        expected_parent_pid=expected_parent_pid,
        disk_check_path=disk_check_path,
    )

    if parent_dead_fast_path is not None:
        # Our fast-path detection wins over evaluate's own check —
        # they should agree, but our breadcrumb lists the tick
        # origin explicitly for forensic clarity.
        result.escalate(DECISION_HALT)
        result.add_reason(parent_dead_fast_path)

    return result


def finalize_swarm(
    loops: Dict[str, LoopState],
    swarm_id: str = "",
    winner_loop_id: str = "",
    commit_sha: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit swarm_finalize_grouped + swarm_finalize_committed audit events.

    Called by the coordinator after tournament selection and git commit.
    PLAN-113 WIRE-AUDIT: previously these events were registered in
    _KNOWN_ACTIONS but never fired. This function is the production
    callsite.

    Fail-open: any import or emit error is silently breadcrumbed.
    """
    try:
        from pathlib import Path as _P
        import sys as _sys2
        _hooks = str(_P(__file__).resolve().parent.parent.parent / "hooks")
        if _hooks not in _sys2.path:
            _sys2.path.insert(0, _hooks)
        from _lib import audit_emit as _ae  # type: ignore[import]
        non_winner = [lid for lid in loops if lid != winner_loop_id]
        _ae.emit_swarm_finalize_grouped(
            swarm_id=swarm_id,
            groups=len(non_winner),
            session_id=session_id,
            project=project,
        )
        _ae.emit_swarm_finalize_committed(
            swarm_id=swarm_id,
            commit=commit_sha[:16],
            session_id=session_id,
            project=project,
        )
    except Exception:  # pragma: no cover
        pass


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coordinator",
        description=(
            "PLAN-017 swarm coordinator — scaffold. Default OFF; "
            "requires CEO_SWARM=1 + sentinel file to dispatch real loops."
        ),
    )
    parser.add_argument(
        "--loops", type=int, required=True, help="Number of parallel loops (1..8)."
    )
    parser.add_argument(
        "--budget-tokens",
        type=int,
        required=True,
        help="Aggregate token budget across all loops.",
    )
    parser.add_argument(
        "--goal", type=str, required=True, help="Optimization goal (benchmark command)."
    )
    parser.add_argument(
        "--jaccard-threshold",
        type=float,
        default=DEFAULT_JACCARD_THRESHOLD,
        help="Convergence Jaccard threshold [0.0, 1.0].",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help="Max iterations per loop (wall-clock CB).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config + emit would-dispatch JSON; no loops spawn.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    try:
        cfg = SwarmConfig(
            n_loops=args.loops,
            budget_tokens=args.budget_tokens,
            goal=args.goal,
            jaccard_threshold=args.jaccard_threshold,
            max_iterations=args.max_iterations,
        )
    except ValueError as e:
        print(f"config_error: {e}", file=sys.stderr)
        return 2

    if env_kill_switch_tripped():
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": "env_kill_switch: CEO_SWARM!=1 or CEO_AUTONOMOUS_LOOPS_DISABLE=1",
                }
            )
        )
        return 0

    # PLAN-122 §6 — resolve the OPTIMIZER switch snapshot. Advisory only:
    # surfaced in the JSON below so a caller can see why fan-out was narrowed,
    # but it NEVER changes the scaffold's dispatch posture (still refuses).
    optimizer_state = optimizer_switch_state()

    # Dry-run path: surface the resolved config without spawning anything.
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "config": asdict(cfg),
                    "optimizer": optimizer_state,
                }
            )
        )
        return 0

    # Actual dispatch is deferred to PLAN-017 follow-up sprints. This
    # scaffold intentionally refuses to spawn real loops even when
    # CEO_SWARM=1 — the sentinel file must ALSO be present AND the
    # worktree orchestration lands in a separate sprint.
    print(
        json.dumps(
            {
                "status": "refused",
                "reason": "scaffold_only: worktree_orchestration_deferred_to_follow_up",
                "config": asdict(cfg),
                "optimizer": optimizer_state,
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
