"""Unit tests for mcp-server/cost.py — LiveCallPolicy budget pre-flight.

ADR-042 §Cost.1 + ADR-040 §3. Tests cover:
- Happy path (both ceilings clear → allow)
- Per-spawn ceiling crossed → deny with budget_hard_stop_per_spawn
- Per-plan 5min ceiling crossed → deny with budget_hard_stop_per_plan_5min
- Zero-cost (local provider) edge
- Negative estimate (defensive deny)
- Mixed trackers (per-spawn fresh + per-plan loaded)

Every test subclasses TestEnvContext (xdist-safe). Trackers are NOT
mutated by check_spawn_budget — verified explicitly.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Bootstrap sys.path so mcp-server modules import cleanly.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import cost  # type: ignore[import-not-found]  # noqa: E402
from _lib.adapters.live._cost import (  # noqa: E402
    PlanCostTracker,
    SpawnCostTracker,
)


class TestCheckSpawnBudget(TestEnvContext):
    """Pre-flight gate against per-spawn + per-plan ceilings."""

    def test_happy_path_allows(self):
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        allow, reason = cost.check_spawn_budget(
            estimated_usd=0.10,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertTrue(allow)
        self.assertIsNone(reason)
        # Verify trackers NOT mutated by the checker.
        self.assertEqual(spawn.total_usd, 0.0)
        self.assertEqual(plan.total_usd(), 0.0)

    def test_per_spawn_ceiling_denies(self):
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        # 0.51 crosses 0.50 ceiling on its own.
        allow, reason = cost.check_spawn_budget(
            estimated_usd=0.51,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertFalse(allow)
        self.assertEqual(reason, "budget_hard_stop_per_spawn")

    def test_per_plan_5min_ceiling_denies(self):
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        # Pre-load plan with 1.90 USD so a 0.20 estimate trips
        # the per-plan ceiling (1.90 + 0.20 = 2.10 > 2.00) but
        # not the per-spawn ceiling (0.20 < 0.50).
        plan.add(1.90)
        allow, reason = cost.check_spawn_budget(
            estimated_usd=0.20,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertFalse(allow)
        self.assertEqual(reason, "budget_hard_stop_per_plan_5min")

    def test_zero_cost_local_provider_allows(self):
        # estimate=0 (e.g. ollama / llama.cpp).
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        allow, reason = cost.check_spawn_budget(
            estimated_usd=0.0,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertTrue(allow)
        self.assertIsNone(reason)

    def test_negative_estimate_fails_closed(self):
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        allow, reason = cost.check_spawn_budget(
            estimated_usd=-1.0,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertFalse(allow)
        self.assertEqual(reason, "budget_hard_stop_per_spawn")

    def test_per_spawn_checked_first(self):
        # Both ceilings would trip; spec says per-spawn checked first.
        spawn = SpawnCostTracker(ceiling_usd=0.50)
        plan = PlanCostTracker(ceiling_usd=2.00)
        plan.add(1.99)
        allow, reason = cost.check_spawn_budget(
            estimated_usd=0.60,
            spawn_tracker=spawn,
            plan_tracker=plan,
        )
        self.assertFalse(allow)
        self.assertEqual(reason, "budget_hard_stop_per_spawn")


if __name__ == "__main__":
    unittest.main()
