"""Tests for runner.py — cost projection + budget + concurrency + kill-switch.

Round 1 C-P0-4 + C-P0-5 + C-P0-8 closures verified here.
~30 tests covering:
- cost projection arithmetic (empirical $40-120 range)
- budget dual-gate (startup + cumulative)
- concurrency semaphore bounded
- two-factor kill-switch (env + sentinel)
- streaming JSONL output shape
- fail-open on errors + timeouts (covered in test_runner_fail_open.py)
- CLI --estimate-cost mode
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import runner
from ..loader import Fixture
from ._fake_dispatcher import FakeLLMDispatcher, FakeRateLimitError


def _make_fixture(
    fixture_id: str = "fx-001",
    task_type: str = "security-review",
    prompt: str = "a" * 100,
    max_tokens: int = 2000,
    seed: int = 42,
) -> Fixture:
    return Fixture(
        fixture_id=fixture_id,
        task_type=task_type,
        prompt=prompt,
        acceptance_strict=["token not logged"],
        acceptance_llm_judge="Does the review cover OWASP?",
        expected_tier="opus",
        max_tokens=max_tokens,
        seed=seed,
    )


class TestPricingTable(unittest.TestCase):
    def test_all_three_tiers_present(self):
        self.assertIn("claude-opus-4-8", runner.PRICING_USD_PER_M)
        self.assertIn("claude-sonnet-4-6", runner.PRICING_USD_PER_M)
        self.assertIn("claude-haiku-4-5-20251001", runner.PRICING_USD_PER_M)

    def test_opus_input_rate_matches_ceo_cost(self):
        # ADR-052 pricing table / ceo-cost.py line ~61
        self.assertEqual(runner.PRICING_USD_PER_M["claude-opus-4-8"]["in"], 5.00)
        self.assertEqual(runner.PRICING_USD_PER_M["claude-opus-4-8"]["out"], 25.00)

    def test_sonnet_rate(self):
        self.assertEqual(runner.PRICING_USD_PER_M["claude-sonnet-4-6"]["in"], 3.00)
        self.assertEqual(runner.PRICING_USD_PER_M["claude-sonnet-4-6"]["out"], 15.00)

    def test_haiku_rate(self):
        self.assertEqual(runner.PRICING_USD_PER_M["claude-haiku-4-5-20251001"]["in"], 1.00)
        self.assertEqual(runner.PRICING_USD_PER_M["claude-haiku-4-5-20251001"]["out"], 5.00)

    def test_default_budget_is_75(self):
        # Round 1 C-P0-4 recalibration
        self.assertEqual(runner.DEFAULT_BUDGET_USD, 75.0)


class TestProjectCost(unittest.TestCase):
    def test_projection_50_fixtures_3_models_3_judge_runs(self):
        # Round 1 F-PERF1 empirical: ~$61 total
        projected = runner.project_cost(fixture_count=50, judge_runs=3)
        self.assertEqual(projected["fixture_count"], 50)
        self.assertEqual(len(projected["models"]), 3)
        self.assertEqual(projected["judge_runs"], 3)
        # Opus 4.8 pricing ($5/$25, S186 model bump): contestant ~$4.27,
        # judges ~$16.88, total ~$21.15 (was ~$61 under Opus 4.7 $15/$75).
        self.assertGreater(projected["grand_total_usd"], 15.0)
        self.assertLess(projected["grand_total_usd"], 30.0)

    def test_projection_judges_dominate_cost(self):
        projected = runner.project_cost(fixture_count=50, judge_runs=3)
        # Judge cost should be > contestant cost (judges are all Opus × 3 runs)
        self.assertGreater(
            projected["judge_total_usd"], projected["contestant_total_usd"]
        )

    def test_projection_reducing_judge_runs_drops_cost_roughly_linear(self):
        p1 = runner.project_cost(fixture_count=50, judge_runs=1)
        p3 = runner.project_cost(fixture_count=50, judge_runs=3)
        # judge_runs=1 vs 3 — judge portion scales 3×
        ratio = p3["judge_total_usd"] / p1["judge_total_usd"]
        self.assertAlmostEqual(ratio, 3.0, places=1)

    def test_projection_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            runner.project_cost(fixture_count=10, models=["fake-model"])

    def test_projection_judge_call_count_correct(self):
        # 50 fixtures × 3 models × 3 judge_runs = 450 judge calls
        projected = runner.project_cost(fixture_count=50, judge_runs=3)
        self.assertEqual(projected["judge_call_count"], 50 * 3 * 3)


class TestEnforceBudget(unittest.TestCase):
    def test_under_budget_passes(self):
        projected = {"grand_total_usd": 20.0}
        runner.enforce_budget(projected, cap_usd=75.0)  # no raise

    def test_over_budget_raises(self):
        projected = {"grand_total_usd": 100.0}
        with self.assertRaises(runner.BudgetExceededError) as ctx:
            runner.enforce_budget(projected, cap_usd=75.0)
        self.assertEqual(ctx.exception.projected_usd, 100.0)
        self.assertEqual(ctx.exception.cap_usd, 75.0)

    def test_exactly_at_cap_passes(self):
        projected = {"grand_total_usd": 75.0}
        runner.enforce_budget(projected, cap_usd=75.0)  # exactly at cap, passes


class TestKillSwitch(unittest.TestCase):
    def test_disabled_by_default_env(self):
        with self.assertRaises(runner.KillswitchError) as ctx:
            runner.check_killswitch(env={})
        self.assertIn("CEO_TOURNAMENT", str(ctx.exception))

    def test_env_set_but_sentinel_absent_disabled(self):
        # Use a tempdir sentinel override by mocking Path.home
        # For this test, we just assert the error message mentions sentinel.
        env = {"CEO_TOURNAMENT": "1"}
        # We can't easily mock Path.home here without intrusion, so we check
        # that the error surfaces when sentinel doesn't exist. Assumes the
        # current test env has no sentinel file at ~/.ceo-orchestration/tournament/.enabled.
        sentinel = runner._home_sentinel_path()
        if not sentinel.exists():
            with self.assertRaises(runner.KillswitchError) as ctx:
                runner.check_killswitch(env=env)
            self.assertIn("sentinel", str(ctx.exception).lower())
        else:
            # Sentinel exists on this box → skip this test
            self.skipTest("sentinel exists on dev box; can't test absence")

    def test_ci_mode_enables(self):
        # CEO_TOURNAMENT_CI=1 bypasses sentinel file check
        runner.check_killswitch(env={"CEO_TOURNAMENT_CI": "1"})

    def test_env_zero_disabled(self):
        with self.assertRaises(runner.KillswitchError):
            runner.check_killswitch(env={"CEO_TOURNAMENT": "0"})


class TestRunTournamentSmoke(unittest.TestCase):
    def test_minimal_run_produces_aggregate(self):
        # Single fixture × single model × 1 judge_run = cheap test
        fixtures = [_make_fixture(fixture_id="fx-001")]
        dispatcher = FakeLLMDispatcher()
        dispatcher.set_default_response(content="some review output")

        with TemporaryDirectory() as d:
            out = Path(d) / "report.jsonl"
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=out,
                models=["claude-haiku-4-5-20251001"],  # cheapest tier for smoke
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            self.assertEqual(aggregate["fixtures_count"], 1)
            self.assertEqual(aggregate["models_count"], 1)
            self.assertEqual(aggregate["judge_runs"], 1)
            self.assertFalse(aggregate["partial"])
            self.assertEqual(aggregate["tasks_completed"], 1)

    def test_jsonl_output_has_task_record_then_aggregate(self):
        fixtures = [_make_fixture(fixture_id="fx-001")]
        dispatcher = FakeLLMDispatcher()
        dispatcher.set_default_response(content="output text")

        with TemporaryDirectory() as d:
            out = Path(d) / "report.jsonl"
            runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=out,
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            lines = out.read_text(encoding="utf-8").strip().split("\n")
            # One task record + one aggregate
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            last = json.loads(lines[1])
            self.assertEqual(first["type"], "task")
            self.assertEqual(first["fixture_id"], "fx-001")
            self.assertEqual(last["type"], "aggregate")

    def test_dispatcher_called_once_per_fixture_model_pair(self):
        fixtures = [
            _make_fixture(fixture_id="fx-001"),
            _make_fixture(fixture_id="fx-002"),
        ]
        dispatcher = FakeLLMDispatcher()
        dispatcher.set_default_response(content="out")

        with TemporaryDirectory() as d:
            runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=Path(d) / "r.jsonl",
                models=["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=2,
                check_killswitch_flag=False,
            )
            # 2 fixtures × 2 models = 4 dispatches
            self.assertEqual(dispatcher.call_count, 4)

    def test_concurrency_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            runner.run_tournament(
                fixtures=[_make_fixture()],
                dispatcher=FakeLLMDispatcher(),
                output_path=Path("/tmp/x.jsonl"),
                concurrency=0,
                check_killswitch_flag=False,
            )
        with self.assertRaises(ValueError):
            runner.run_tournament(
                fixtures=[_make_fixture()],
                dispatcher=FakeLLMDispatcher(),
                output_path=Path("/tmp/x.jsonl"),
                concurrency=runner.MAX_CONCURRENCY + 1,
                check_killswitch_flag=False,
            )

    def test_budget_exceeded_raises_before_dispatch(self):
        # Projection for 50 × 3 × 3 is ~$61; cap $1 will always fail
        fixtures = [_make_fixture(fixture_id=f"fx-{i}") for i in range(50)]
        dispatcher = FakeLLMDispatcher()
        dispatcher.set_default_response(content="x")

        with TemporaryDirectory() as d:
            with self.assertRaises(runner.BudgetExceededError) as ctx:
                runner.run_tournament(
                    fixtures=fixtures,
                    dispatcher=dispatcher,
                    output_path=Path(d) / "r.jsonl",
                    judge_runs=3,
                    budget_usd=1.0,
                    concurrency=1,
                    check_killswitch_flag=False,
                )
            self.assertGreater(ctx.exception.projected_usd, 1.0)
            # No dispatches should have happened
            self.assertEqual(dispatcher.call_count, 0)


class TestCLIEstimateCost(unittest.TestCase):
    def test_estimate_cost_outputs_json(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = runner._cli(
                [
                    "--estimate-cost",
                    "--fixtures-count",
                    "10",
                    "--judge-runs",
                    "1",
                    "--budget-usd",
                    "100",
                ]
            )
        self.assertEqual(rc, 0)
        # First line of stdout should be valid JSON projection
        output = stdout.getvalue()
        # It's indented JSON — just parse the whole thing
        projected = json.loads(output)
        self.assertEqual(projected["fixture_count"], 10)
        self.assertEqual(projected["judge_runs"], 1)

    def test_estimate_cost_exits_2_when_over_budget(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = runner._cli(
                [
                    "--estimate-cost",
                    "--fixtures-count",
                    "100",  # large
                    "--judge-runs",
                    "5",
                    "--budget-usd",
                    "1",  # guaranteed over
                ]
            )
        self.assertEqual(rc, 2)
        self.assertIn("EXCEEDS", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
