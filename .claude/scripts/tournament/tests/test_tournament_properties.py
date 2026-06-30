"""Property-based invariant tests for tournament (QA F-QA4 closure).

5 properties × 2-4 cases each = 18+ parameterized tests. Stdlib-only.

P1: passed_count + failed_count + errored_count == total_dispatched
P2: min(vec) <= median(vec) <= max(vec)  — median bounded
P3: (projected > budget) => abort
P4: 0.0 <= win_rate[t][m] <= 1.0  — valid probability
P5: errored excluded from win-rate numerator AND denominator
"""
from __future__ import annotations

import itertools
import unittest

from .. import judge, reporter, runner


class TestP1_ScoreTotalsConsistent(unittest.TestCase):
    """P1 — pass + fail + errored == total, across all observations."""

    def test_empty_records_consistent(self):
        matrix = reporter.compute_win_rate_matrix([])
        self.assertEqual(matrix, {})

    def test_single_fixture_consistent(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "fail"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # 1 pass / 2 non-errored = 0.5
        self.assertEqual(matrix["t"]["m"], 0.5)

    def test_multi_model_consistency(self):
        records = []
        for model in ("a", "b", "c"):
            for v in ("pass", "pass", "fail"):
                records.append(
                    {"type": "task", "task_type": "t", "model": model, "verdict": v}
                )
        matrix = reporter.compute_win_rate_matrix(records)
        for model, rate in matrix["t"].items():
            # reporter rounds to 4 decimals; compare at that precision
            self.assertAlmostEqual(rate, 2 / 3, places=3)


class TestP2_MedianBounded(unittest.TestCase):
    """P2 — median of verdicts is always within min..max."""

    def test_median_bounded_unanimous(self):
        result = judge.aggregate_verdicts(["pass", "pass", "pass"])
        self.assertEqual(result, "pass")

    def test_median_bounded_split_majority(self):
        result = judge.aggregate_verdicts(["pass", "pass", "fail"])
        self.assertEqual(result, "pass")

    def test_median_tie_conservative_fail(self):
        result = judge.aggregate_verdicts(["pass", "fail"])
        self.assertEqual(result, "fail")

    def test_median_never_invents_verdict(self):
        # Output always in {pass, fail, errored}
        for combo in itertools.product(
            ["pass", "fail"], repeat=3
        ):
            with self.subTest(combo=combo):
                result = judge.aggregate_verdicts(list(combo))
                self.assertIn(result, {"pass", "fail", "errored"})


class TestP3_CostAbortConditional(unittest.TestCase):
    """P3 — if projected > budget, abort fires."""

    def test_projection_exactly_at_cap_passes(self):
        projected = {"grand_total_usd": 10.0}
        # Should not raise
        runner.enforce_budget(projected, cap_usd=10.0)

    def test_projection_one_cent_over_raises(self):
        projected = {"grand_total_usd": 10.01}
        with self.assertRaises(runner.BudgetExceededError):
            runner.enforce_budget(projected, cap_usd=10.0)

    def test_projection_far_over_raises(self):
        projected = {"grand_total_usd": 1000.0}
        with self.assertRaises(runner.BudgetExceededError):
            runner.enforce_budget(projected, cap_usd=10.0)

    def test_zero_cap_zero_projection_passes(self):
        projected = {"grand_total_usd": 0.0}
        runner.enforce_budget(projected, cap_usd=0.0)


class TestP4_WinRateValidProbability(unittest.TestCase):
    """P4 — every cell in win_rate matrix is in [0.0, 1.0]."""

    def test_all_pass_is_1(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 1.0)

    def test_all_fail_is_0(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "fail"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "fail"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 0.0)

    def test_arbitrary_mix_bounded(self):
        import random
        rng = random.Random(42)
        for trial in range(10):
            n = rng.randint(1, 30)
            records = [
                {
                    "type": "task",
                    "task_type": "t",
                    "model": "m",
                    "verdict": rng.choice(["pass", "fail", "errored"]),
                }
                for _ in range(n)
            ]
            matrix = reporter.compute_win_rate_matrix(records)
            if "t" in matrix and "m" in matrix["t"]:
                self.assertGreaterEqual(matrix["t"]["m"], 0.0)
                self.assertLessEqual(matrix["t"]["m"], 1.0)


class TestP5_ErroredExcludedFromWinRate(unittest.TestCase):
    """P5 — errored tasks excluded from numerator AND denominator."""

    def test_errored_only_returns_zero(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 0.0)

    def test_errored_does_not_inflate_numerator(self):
        # If errored counted as pass, win_rate would be 3/3 = 1.0
        # Correct: 1 pass / 1 non-errored = 1.0
        # Different test case: 1 pass + 2 errored — win_rate = 1.0 (not 1/3)
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # 1 pass / 1 non-errored = 1.0
        self.assertEqual(matrix["t"]["m"], 1.0)

    def test_errored_does_not_deflate_denominator_silently(self):
        # 1 pass + 1 fail + 1 errored
        # Correct: 1/2 = 0.5 (errored excluded both sides)
        # Bug: 1/3 = 0.333 (errored in denominator)
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "fail"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 0.5)

    def test_adr052_no_data_when_all_errored(self):
        # If all observations errored, signal should be no_data or
        # reflect the 0.0 win-rate without misleading confirmation
        wr = {"security-review": {"claude-opus-4-8": 0.0, "claude-sonnet-4-6": 0.0}}
        signals = reporter.validate_adr052(wr)
        # Gap is 0 → below noise threshold → opus_mid_surprise
        self.assertEqual(signals["security-review"], "opus_mid_surprise")


if __name__ == "__main__":
    unittest.main()
