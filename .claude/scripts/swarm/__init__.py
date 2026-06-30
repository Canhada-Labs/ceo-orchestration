"""PLAN-017 swarm package — autonomous-loop parallelism (opt-in, default OFF).

Scaffold for the SOTA opt-in capability defined in
`.claude/plans/PLAN-017-autonomous-loop-parallelism.md`. WAR-ROOM P06
compresses the plan's 6 full phases (9 weeks) into a reviewable
scaffold + tests; adopter-facing wiring (swarm kill-switch primitives
into hooks, audit-log v2.7 emitters, worktree orchestration) follows
in PLAN-017 follow-up sprints.

Default OFF (see PLAN-017 design principle #1). Two-factor activation:
`CEO_SWARM=1` env var AND `.claude/swarm-enabled` file sentinel.

Public exports:
- LoopState, SwarmConfig (coordinator.py dataclasses)
- jaccard, detect_convergence, budget_exceeded (coordinator.py pure helpers)
- assign_files (file_assignment.py disjoint-set computation)
- KillSwitchState, evaluate_kill_switch (kill_switch.py)
- Tournament, score_candidate (tournament.py, Phase 2)
"""

from __future__ import annotations

__all__ = [
    "LoopState",
    "SwarmConfig",
    "jaccard",
    "detect_convergence",
    "budget_exceeded",
    "assign_files",
    "KillSwitchState",
    "evaluate_kill_switch",
]

from .coordinator import (
    LoopState,
    SwarmConfig,
    jaccard,
    detect_convergence,
    budget_exceeded,
)
from .file_assignment import assign_files
from .kill_switch import KillSwitchState, evaluate_kill_switch
