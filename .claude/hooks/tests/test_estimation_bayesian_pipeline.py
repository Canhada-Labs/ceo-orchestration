"""Tests for PLAN-088 W6.1 Bayesian estimation calibrator (pipeline + bayesian)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parents[1]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.estimation import bayesian, pipeline


class TestBayesianMath(unittest.TestCase):
    def test_initial_prior_is_empirical(self) -> None:
        a, b = bayesian._init_priors()
        self.assertGreater(a, 0)
        self.assertGreater(b, 0)
        # Empirical prior should favor success (alpha > beta)
        self.assertGreater(a, b)

    def test_update_posterior_pure_function(self) -> None:
        pa, pb = bayesian.update_posterior(10, 5, 20, 3)
        self.assertEqual(pa, 30)
        self.assertEqual(pb, 8)

    def test_posterior_mean_basis_points(self) -> None:
        mean_bp = bayesian.posterior_mean_basis_points(30, 10)
        # 30/40 = 0.75 -> 750 bp
        self.assertEqual(mean_bp, 750)

    def test_classify_success(self) -> None:
        self.assertEqual(
            bayesian.classify_estimate_accuracy(8, 12, 10), "success",
        )
        self.assertEqual(
            bayesian.classify_estimate_accuracy(8, 12, 20), "failure",
        )

    def test_classify_unknown_on_nan(self) -> None:
        self.assertEqual(
            bayesian.classify_estimate_accuracy(-1, 10, 5), "unknown",
        )
        self.assertEqual(
            bayesian.classify_estimate_accuracy(float("nan"), 10, 5), "unknown",
        )

    def test_batch_update_aggregates(self) -> None:
        plans = [
            {"estimated_hours_lower": 8.0, "estimated_hours_upper": 12.0, "actual_hours": 10.0},  # success
            {"estimated_hours_lower": 5.0, "estimated_hours_upper": 7.0, "actual_hours": 20.0},   # failure
            {"estimated_hours_lower": 1.0, "estimated_hours_upper": 2.0, "actual_hours": 1.5},    # success
        ]
        pa, pb, s, f = bayesian.batch_update_from_plans(plans)
        self.assertEqual(s, 2)
        self.assertEqual(f, 1)
        prior_a, prior_b = bayesian._init_priors()
        self.assertEqual(pa, prior_a + 2)
        self.assertEqual(pb, prior_b + 1)


class TestPipelineEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="est-pipe-")
        self.audit_path = Path(self.tmp) / "audit-log.jsonl"
        self.baseline_path = Path(self.tmp) / "calibration-baseline.yaml"

    def tearDown(self) -> None:
        try:
            for p in [self.audit_path, self.baseline_path]:
                if p.exists():
                    p.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass

    def _write_audit_log(self, events) -> None:
        with self.audit_path.open("w", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev) + "\n")

    def test_pipeline_runs_on_empty_audit_log(self) -> None:
        # No events; pipeline returns prior unchanged
        self.audit_path.touch()
        result = pipeline.run(
            audit_log_path=self.audit_path,
            baseline_yaml_path=self.baseline_path,
            trigger_source="nightly_cron",
        )
        self.assertEqual(result["plans_observed"], 0)
        prior_a, prior_b = bayesian._init_priors()
        self.assertEqual(result["posterior_alpha"], prior_a)
        self.assertEqual(result["posterior_beta"], prior_b)
        self.assertTrue(result["baseline_written"])
        self.assertTrue(self.baseline_path.exists())

    def test_pipeline_consumes_plan_transition_events(self) -> None:
        events = [
            {"action": "plan_transition", "from_status": "executing", "to_status": "done",
             "estimated_hours_lower": 8.0, "estimated_hours_upper": 12.0,
             "actual_hours": 10.0},
            {"action": "plan_transition", "from_status": "executing", "to_status": "done",
             "estimated_hours_lower": 5.0, "estimated_hours_upper": 7.0,
             "actual_hours": 20.0},
        ]
        self._write_audit_log(events)
        result = pipeline.run(
            audit_log_path=self.audit_path,
            baseline_yaml_path=self.baseline_path,
            trigger_source="plan_close_hook",
        )
        self.assertEqual(result["plans_observed"], 2)
        self.assertEqual(result["successes"], 1)
        self.assertEqual(result["failures"], 1)
        self.assertTrue(result["baseline_written"])
        # Verify YAML emitted has expected keys
        body = self.baseline_path.read_text(encoding="utf-8")
        self.assertIn("posterior_alpha", body)
        self.assertIn("plans_observed: 2", body)

    def test_pipeline_skips_non_done_transitions(self) -> None:
        events = [
            {"action": "plan_transition", "from_status": "draft", "to_status": "reviewed"},
            {"action": "agent_spawn", "session_id": "abc"},
        ]
        self._write_audit_log(events)
        result = pipeline.run(
            audit_log_path=self.audit_path,
            baseline_yaml_path=self.baseline_path,
        )
        self.assertEqual(result["plans_observed"], 0)


if __name__ == "__main__":
    unittest.main()
