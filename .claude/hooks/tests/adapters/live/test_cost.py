"""Behavior tests for ``_lib/adapters/live/_cost.py``."""

from __future__ import annotations

import os
import sys
import threading
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[3]

from _lib.adapters.live import _cost as costmod  # noqa: E402
from _lib.adapters.live._cost import (  # noqa: E402
    BudgetHardStop,
    PlanCostTracker,
    SpawnCostTracker,
    actual_cost_usd,
    estimate_cost_usd,
)


def _patch_pricing(tmpdir, table_md):
    p = tmpdir / "provider-pricing.md"
    p.write_text(table_md, encoding="utf-8")
    os.environ["CEO_PRICING_PATH"] = str(p)
    costmod._reset_pricing_cache()


_PRICING_TABLE = """\
# pricing

| Provider   | Model                | Input $/1k | Output $/1k |
|------------|----------------------|------------|-------------|
| Anthropic  | claude-sonnet-4-6    | 0.003      | 0.015       |
| Anthropic  | claude-haiku-4-5     | 0.001      | 0.005       |
| Google     | gemini-2.5-flash     | 0.0003     | 0.0025      |
| OpenAI     | gpt-4o               | 0.0025     | 0.010       |
| OpenAI     | gpt-mystery          | TBD        | TBD         |
| Local      | ollama-any           | 0.00       | 0.00        |
"""


class _PricingMixin(unittest.TestCase):
    def setUp(self):
        super().setUp()
        import tempfile
        self._tmp = Path(tempfile.mkdtemp(prefix="ceo-cost-test-"))
        _patch_pricing(self._tmp, _PRICING_TABLE)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        import shutil
        os.environ.pop("CEO_PRICING_PATH", None)
        costmod._reset_pricing_cache()
        shutil.rmtree(self._tmp, ignore_errors=True)


class TestEstimate(_PricingMixin):
    def test_local_always_zero(self):
        self.assertEqual(
            estimate_cost_usd("local", "ollama-any", [{"role": "user", "content": "hi"}], 100),
            0.0,
        )

    def test_anthropic_estimate_positive(self):
        cost = estimate_cost_usd(
            "anthropic", "claude-sonnet-4-6",
            [{"role": "user", "content": "hello world " * 100}],
            500,
        )
        self.assertGreater(cost, 0)
        self.assertLess(cost, 1.0)  # sanity bound

    def test_gemini_provider_alias_resolves(self):
        cost = estimate_cost_usd(
            "gemini", "gemini-2.5-flash",
            [{"role": "user", "content": "hi"}],
            100,
        )
        self.assertGreater(cost, 0)

    def test_unknown_model_falls_back_to_conservative_default(self):
        cost = estimate_cost_usd(
            "anthropic", "unknown-model",
            [{"role": "user", "content": "x"}],
            100,
        )
        # Conservative fallback rate is _FALLBACK_OUTPUT_PER_1K=0.10/1k → 0.01 for 100 tokens
        self.assertGreater(cost, 0.005)

    def test_tbd_row_treated_as_fallback(self):
        cost = estimate_cost_usd(
            "openai", "gpt-mystery",
            [{"role": "user", "content": "x"}],
            100,
        )
        # TBD → fallback rate kicks in (>0)
        self.assertGreater(cost, 0.005)


class TestActualCost(_PricingMixin):
    def test_actual_cost_uses_real_tokens(self):
        cost = actual_cost_usd("anthropic", "claude-sonnet-4-6", 1000, 500)
        # 1000/1k * 0.003 + 500/1k * 0.015 = 0.003 + 0.0075 = 0.0105
        self.assertAlmostEqual(cost, 0.0105, places=5)

    def test_actual_cost_local_zero(self):
        self.assertEqual(actual_cost_usd("local", "ollama-any", 5000, 5000), 0.0)

    def test_actual_cost_handles_none_tokens(self):
        cost = actual_cost_usd("anthropic", "claude-sonnet-4-6", None, None)
        self.assertEqual(cost, 0.0)


class TestSpawnTracker(_PricingMixin):
    def test_under_ceiling_does_not_raise(self):
        t = SpawnCostTracker(ceiling_usd=0.50)
        t.add(0.10)
        t.add(0.20)
        self.assertAlmostEqual(t.total_usd, 0.30)

    def test_exceeding_ceiling_raises_budget_hard_stop(self):
        t = SpawnCostTracker(ceiling_usd=0.50)
        t.add(0.40)
        with self.assertRaises(BudgetHardStop) as ctx:
            t.add(0.20)
        self.assertEqual(ctx.exception.scope, "per_spawn")
        self.assertEqual(ctx.exception.ceiling_usd, 0.50)

    def test_would_exceed_predictive_check(self):
        t = SpawnCostTracker(ceiling_usd=0.50)
        t.add(0.40)
        self.assertTrue(t.would_exceed(0.20))
        self.assertFalse(t.would_exceed(0.05))

    def test_negative_charge_rejected(self):
        t = SpawnCostTracker(ceiling_usd=0.50)
        with self.assertRaises(ValueError):
            t.add(-1.0)

    def test_zero_ceiling_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            SpawnCostTracker(ceiling_usd=0.0)


class TestPlanTracker(_PricingMixin):
    def test_rolling_window_drops_old_entries(self):
        clock = [0.0]
        def tick():
            return clock[0]
        t = PlanCostTracker(ceiling_usd=2.0, window_s=300, clock=tick)
        t.add(0.50)
        t.add(0.50)
        clock[0] = 301.0  # past window
        t.add(0.50)
        # Only the 0.50 in current window
        self.assertAlmostEqual(t.total_usd(), 0.50)

    def test_window_total_triggers_hard_stop(self):
        clock = [0.0]
        def tick():
            return clock[0]
        t = PlanCostTracker(ceiling_usd=2.0, window_s=300, clock=tick)
        t.add(1.0)
        t.add(0.5)
        with self.assertRaises(BudgetHardStop):
            t.add(0.8)


class TestThreadSafety(_PricingMixin):
    def test_concurrent_spawn_adds_atomic(self):
        t = SpawnCostTracker(ceiling_usd=10.0)
        barrier = threading.Barrier(4)

        def worker():
            barrier.wait()
            for _ in range(100):
                t.add(0.001)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thr in threads:
            thr.start()
        for thr in threads:
            thr.join()
        # 4 * 100 * 0.001 = 0.4
        self.assertAlmostEqual(t.total_usd, 0.4, places=4)


if __name__ == "__main__":
    unittest.main()
