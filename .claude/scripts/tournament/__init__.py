"""Agent-eval tournament framework — PLAN-032 / ADR-063.

Empirical ADR-052 tier dispatch validation. See:
- `.claude/adr/ADR-063-agent-eval-empirical-dispatch-validation.md`
- `.claude/plans/PLAN-032-agent-eval-tournament.md`

Kill-switch (two-factor per ADR-063 §Invariants):
1. env `CEO_TOURNAMENT=1`
2. sentinel file `~/.ceo-orchestration/tournament/.enabled` (0600)

CI mode: `CEO_TOURNAMENT_CI=1` + `github.event.repository.fork == false`
assertion replaces sentinel.

Budget (Round 1 recalibrated from miscalibrated $10 default):
- `CEO_TOURNAMENT_BUDGET_USD=75` per-run cap
- `CEO_TOURNAMENT_CONCURRENCY=10` semaphore bound (max 50)
- `CEO_TOURNAMENT_CALL_TIMEOUT_S=60` per-call API timeout
- `CEO_TOURNAMENT_JUDGE_RUNS=3` multi-run median
"""
from __future__ import annotations

__version__ = "0.1.0-plan032-phase1"
