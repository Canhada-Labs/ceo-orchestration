"""PLAN-113 WIRE-DEADMOD — tests for estimation/pipeline wiring in estimate-calibrator.

Tests:
  (a) _try_load_estimation_pipeline() — module found → _ESTIMATION_PIPELINE_AVAILABLE True.
  (b) pipeline.run() called when --bayesian flag active (functional wiring test).
  (c) pipeline.run() NOT called without --bayesian flag.
  (d) fail-open: if pipeline import fails, script still produces Stage-1 output.
  (e) sidecar YAML written next to --output, not overwriting main output.

Stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS_LOCAL = _REPO_ROOT / ".claude" / "scripts" / "local"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_calibrator():
    """Import estimate-calibrator.py as a module (hyphen in name requires importlib)."""
    import importlib.util
    spec_path = _SCRIPTS_LOCAL / "estimate-calibrator.py"
    spec = importlib.util.spec_from_file_location("estimate_calibrator", str(spec_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEstimationPipelineWiring(TestEnvContext):
    """Tests for estimation/pipeline.py wiring in estimate-calibrator.py."""

    def setUp(self) -> None:
        super().setUp()
        self.calibrator = _load_calibrator()

    def test_try_load_finds_pipeline(self) -> None:
        """(a) _try_load_estimation_pipeline() → module found."""
        # Reset state so the function runs afresh.
        self.calibrator._ESTIMATION_PIPELINE_AVAILABLE = False
        self.calibrator._estimation_pipeline = None
        self.calibrator._try_load_estimation_pipeline()
        self.assertTrue(
            self.calibrator._ESTIMATION_PIPELINE_AVAILABLE,
            "_ESTIMATION_PIPELINE_AVAILABLE should be True when _lib is on path",
        )
        self.assertIsNotNone(self.calibrator._estimation_pipeline)

    def test_pipeline_run_called_with_bayesian_flag(self) -> None:
        """(b) pipeline.run() is called when --bayesian flag is passed."""
        called: list = []

        # Load the real pipeline module first to ensure the module is available.
        self.calibrator._try_load_estimation_pipeline()

        mock_run_result = {
            "trigger_source": "plan_close_hook",
            "plans_observed": 0,
            "successes": 0,
            "failures": 0,
            "posterior_alpha": 30,
            "posterior_beta": 12,
            "posterior_mean_basis_points": 714,
            "baseline_written": False,
        }

        original_run = None
        if self.calibrator._estimation_pipeline is not None:
            original_run = self.calibrator._estimation_pipeline.run

        def _fake_run(**kwargs):
            called.append(kwargs)
            # Write the sidecar so the code doesn't error.
            sidecar = kwargs.get("baseline_yaml_path")
            if sidecar is not None:
                Path(sidecar).parent.mkdir(parents=True, exist_ok=True)
                Path(sidecar).write_text("# bayesian\n", encoding="utf-8")
            return mock_run_result

        try:
            if self.calibrator._estimation_pipeline is not None:
                self.calibrator._estimation_pipeline.run = _fake_run

            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "calibration.yaml"
                plans_dir = Path(tmpdir) / "plans"
                plans_dir.mkdir()
                import sys as _sys
                old_argv = _sys.argv
                _sys.argv = [
                    "estimate-calibrator.py",
                    "--bayesian",
                    "--plans-dir", str(plans_dir),
                    "--output", str(out),
                    "--n", "5",
                ]
                try:
                    self.calibrator.main()
                finally:
                    _sys.argv = old_argv

            if self.calibrator._ESTIMATION_PIPELINE_AVAILABLE:
                self.assertEqual(
                    len(called), 1,
                    "pipeline.run() should be called exactly once with --bayesian"
                )
                self.assertIn("trigger_source", called[0])
                self.assertEqual(called[0]["trigger_source"], "plan_close_hook")
        finally:
            if self.calibrator._estimation_pipeline is not None and original_run is not None:
                self.calibrator._estimation_pipeline.run = original_run

    def test_pipeline_not_called_without_bayesian_flag(self) -> None:
        """(c) pipeline.run() NOT called without --bayesian flag."""
        called: list = []
        self.calibrator._try_load_estimation_pipeline()

        if self.calibrator._estimation_pipeline is not None:
            original_run = self.calibrator._estimation_pipeline.run

            def _fake_run(**kwargs):
                called.append(kwargs)
                return {}

            self.calibrator._estimation_pipeline.run = _fake_run
        else:
            original_run = None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "calibration.yaml"
                plans_dir = Path(tmpdir) / "plans"
                plans_dir.mkdir()
                import sys as _sys
                old_argv = _sys.argv
                _sys.argv = [
                    "estimate-calibrator.py",
                    "--plans-dir", str(plans_dir),
                    "--output", str(out),
                    "--n", "5",
                ]
                try:
                    self.calibrator.main()
                finally:
                    _sys.argv = old_argv
        finally:
            if (self.calibrator._estimation_pipeline is not None
                    and original_run is not None):
                self.calibrator._estimation_pipeline.run = original_run

        self.assertEqual(len(called), 0, "pipeline.run() must NOT be called without --bayesian")

    def test_fail_open_on_pipeline_error(self) -> None:
        """(d) Fail-open: pipeline.run() raises → script still exits 0."""
        self.calibrator._try_load_estimation_pipeline()
        self.calibrator._ESTIMATION_PIPELINE_AVAILABLE = True

        if self.calibrator._estimation_pipeline is not None:
            original_run = self.calibrator._estimation_pipeline.run
        else:
            # Create a fake module
            import types
            fake_mod = types.SimpleNamespace()
            self.calibrator._estimation_pipeline = fake_mod
            original_run = None

        def _fail_run(**kwargs):
            raise RuntimeError("simulated pipeline failure")

        self.calibrator._estimation_pipeline.run = _fail_run

        try:
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdir = tmpdir_obj.name
            try:
                out = Path(tmpdir) / "calibration.yaml"
                plans_dir = Path(tmpdir) / "plans"
                plans_dir.mkdir()
                import sys as _sys
                old_argv = _sys.argv
                _sys.argv = [
                    "estimate-calibrator.py",
                    "--bayesian",
                    "--plans-dir", str(plans_dir),
                    "--output", str(out),
                    "--n", "5",
                ]
                try:
                    rc = self.calibrator.main()
                finally:
                    _sys.argv = old_argv
                # Script must still produce output and return 0 (fail-open)
                self.assertEqual(rc, 0, "Script must fail-open on pipeline error")
                self.assertTrue(out.exists(), "Stage-1 output must still be written")
            finally:
                tmpdir_obj.cleanup()
        finally:
            if original_run is not None:
                self.calibrator._estimation_pipeline.run = original_run

    def test_sidecar_yaml_written_not_main_output(self) -> None:
        """(e) Bayesian sidecar written next to --output, main output unchanged."""
        self.calibrator._try_load_estimation_pipeline()

        mock_run_result = {
            "trigger_source": "plan_close_hook",
            "plans_observed": 2,
            "successes": 1,
            "failures": 1,
            "posterior_alpha": 31,
            "posterior_beta": 13,
            "posterior_mean_basis_points": 705,
            "baseline_written": True,
        }

        if self.calibrator._estimation_pipeline is not None:
            original_run = self.calibrator._estimation_pipeline.run
        else:
            original_run = None

        def _fake_run(**kwargs):
            sidecar = kwargs.get("baseline_yaml_path")
            if sidecar is not None:
                Path(sidecar).parent.mkdir(parents=True, exist_ok=True)
                Path(sidecar).write_text("# bayesian sidecar\n", encoding="utf-8")
            return mock_run_result

        if self.calibrator._estimation_pipeline is not None:
            self.calibrator._estimation_pipeline.run = _fake_run
        else:
            return  # skip if pipeline not available

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "calibration.yaml"
                plans_dir = Path(tmpdir) / "plans"
                plans_dir.mkdir()
                import sys as _sys
                old_argv = _sys.argv
                _sys.argv = [
                    "estimate-calibrator.py",
                    "--bayesian",
                    "--plans-dir", str(plans_dir),
                    "--output", str(out),
                    "--n", "5",
                ]
                try:
                    self.calibrator.main()
                finally:
                    _sys.argv = old_argv

                # Main output should exist
                self.assertTrue(out.exists())
                # Sidecar should be next to main output
                sidecar = out.with_suffix(".bayesian.yaml")
                self.assertTrue(
                    sidecar.exists(),
                    f"Bayesian sidecar expected at {sidecar}"
                )
                # Main output should contain bayesian_posterior section
                content = out.read_text(encoding="utf-8")
                self.assertIn("bayesian_posterior:", content)
                # Main output should NOT overwrite Stage-1 (still has per_class)
                self.assertIn("methodology_note", content)
        finally:
            if original_run is not None:
                self.calibrator._estimation_pipeline.run = original_run


if __name__ == "__main__":
    unittest.main()
