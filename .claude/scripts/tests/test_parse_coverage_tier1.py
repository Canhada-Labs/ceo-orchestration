"""Tests for the ADR-139 Tier-1 per-module mode of parse-coverage.py.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157). The Tier-1 gate is
the real enforcing mechanism for the coverage doctrine; these tests pin
its semantics: pass when all listed modules ≥ min, fail when any is
below, fail when a listed module is absent (typo guard), and advisory
under the CEO_TIER1_COVERAGE_ENFORCING=0 kill-switch.
"""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

_REPO = Path(__file__).resolve().parents[3]
_PC = _REPO / ".github" / "scripts" / "parse-coverage.py"
_spec = importlib.util.spec_from_file_location("parse_coverage", _PC)
pc = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(pc)  # type: ignore[union-attr]


def _cov_json(modules):
    """Build a minimal coverage.json data dict with given module percents."""
    files = {}
    for path, pct in modules.items():
        files[path] = {"summary": {"percent_covered": pct}}
    return {"files": files, "totals": {"percent_covered": 80.0}}


class Tier1FailuresTest(TestEnvContext):

    def test_all_above_min_no_failures(self):
        data = _cov_json({
            ".claude/hooks/audit_log.py": 87.0,
            ".claude/hooks/check_read_injection.py": 98.0,
        })
        failures = pc.tier1_failures(
            data, ["audit_log.py", "check_read_injection.py"], 86.0)
        self.assertEqual(failures, [])

    def test_below_min_is_failure(self):
        data = _cov_json({".claude/hooks/check_agent_spawn.py": 79.5})
        failures = pc.tier1_failures(data, ["check_agent_spawn.py"], 86.0)
        self.assertEqual(len(failures), 1)
        self.assertIn("check_agent_spawn.py", failures[0])

    def test_missing_module_is_failure(self):
        # Typo guard: a listed module that matches no production file fails.
        data = _cov_json({".claude/hooks/audit_log.py": 90.0})
        failures = pc.tier1_failures(data, ["does_not_exist.py"], 86.0)
        self.assertEqual(len(failures), 1)
        self.assertIn("not found", failures[0])

    def test_test_tree_paths_excluded(self):
        # A test-tree file with the same basename must not satisfy the gate.
        data = _cov_json({
            ".claude/hooks/tests/audit_log.py": 100.0,  # not production
        })
        failures = pc.tier1_failures(data, ["audit_log.py"], 86.0)
        self.assertEqual(len(failures), 1)
        self.assertIn("not found", failures[0])


class Tier1CliTest(TestEnvContext):

    def _write_json(self, tmp, modules):
        p = Path(tmp) / "coverage.json"
        p.write_text(json.dumps(_cov_json(modules)), encoding="utf-8")
        return p

    def test_cli_pass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cj = self._write_json(td, {".claude/hooks/audit_log.py": 90.0})
            with mock.patch("sys.argv", [
                    "parse-coverage.py", "--coverage-json", str(cj),
                    "--tier1-modules", "audit_log.py", "--tier1-min", "86"]):
                self.assertEqual(pc.main(), 0)

    def test_cli_fail_when_below(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cj = self._write_json(td, {".claude/hooks/audit_log.py": 50.0})
            with mock.patch("sys.argv", [
                    "parse-coverage.py", "--coverage-json", str(cj),
                    "--tier1-modules", "audit_log.py", "--tier1-min", "86"]):
                self.assertEqual(pc.main(), 1)

    def test_cli_advisory_kill_switch(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cj = self._write_json(td, {".claude/hooks/audit_log.py": 50.0})
            with mock.patch.dict(os.environ, {"CEO_TIER1_COVERAGE_ENFORCING": "0"}), \
                    mock.patch("sys.argv", [
                        "parse-coverage.py", "--coverage-json", str(cj),
                        "--tier1-modules", "audit_log.py", "--tier1-min", "86"]):
                self.assertEqual(pc.main(), 0)


if __name__ == "__main__":
    unittest.main()
