"""Tests for check-flip-release-gate-consistency.py — Phase E.4 validator.

>=6 tests per acceptance criteria.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Optional

# --- bootstrap: add scripts dir to sys.path ---
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Use importlib to avoid hyphen in module name
import importlib.util

_MOD_PATH = Path(__file__).resolve().parent.parent / "check-flip-release-gate-consistency.py"
_spec = importlib.util.spec_from_file_location("check_flip_release_gate_consistency", _MOD_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_workflows_array = _mod.parse_workflows_array
check_consistency = _mod.check_consistency
get_enforcing_workflows = _mod.get_enforcing_workflows
main = _mod.main


class TestParseWorkflowsArray(unittest.TestCase):
    """Test WORKFLOWS array parsing from release.yml content."""

    def test_parses_standard_array(self):
        content = '          WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml)\n'
        result = parse_workflows_array(content)
        self.assertEqual(result, {"chaos.yml", "otel-smoke.yml", "perf-profile.yml", "adapter-live.yml"})

    def test_parses_array_with_extra_entries(self):
        content = '          WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml)\n'
        result = parse_workflows_array(content)
        self.assertIn("red-team.yml", result)
        self.assertIn("formal-verify.yml", result)
        self.assertEqual(len(result), 6)

    def test_empty_array(self):
        content = '          WORKFLOWS=()\n'
        result = parse_workflows_array(content)
        self.assertEqual(result, set())

    def test_no_workflows_line(self):
        content = 'name: Release\non:\n  push:\n    tags: ["v*"]\n'
        result = parse_workflows_array(content)
        self.assertEqual(result, set())

    def test_handles_quoted_entries(self):
        content = '          WORKFLOWS=("chaos.yml" "otel-smoke.yml")\n'
        result = parse_workflows_array(content)
        self.assertEqual(result, {"chaos.yml", "otel-smoke.yml"})


class TestCheckConsistency(unittest.TestCase):
    """Test consistency check logic."""

    def test_all_present_passes(self):
        content = '          WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml)\n'
        ok, missing, found = check_consistency(content)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_missing_workflows_detected(self):
        # Only original 4 — missing red-team.yml and formal-verify.yml
        content = '          WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml)\n'
        ok, missing, found = check_consistency(content)
        self.assertFalse(ok)
        self.assertIn("red-team.yml", missing)
        self.assertIn("formal-verify.yml", missing)

    def test_empty_array_fails(self):
        content = '          WORKFLOWS=()\n'
        ok, missing, found = check_consistency(content)
        self.assertFalse(ok)
        self.assertTrue(len(missing) > 0)

    def test_custom_enforcing_list(self):
        content = '          WORKFLOWS=(foo.yml bar.yml)\n'
        ok, missing, found = check_consistency(
            content,
            enforcing_workflows=[("foo.yml", "Foo"), ("bar.yml", "Bar"), ("baz.yml", "Baz")],
        )
        self.assertFalse(ok)
        self.assertEqual(missing, ["baz.yml"])
        self.assertEqual(found, {"foo.yml", "bar.yml"})

    def test_superset_passes(self):
        """Extra workflows in the array are fine — we only check enforcing ones are present."""
        content = '          WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml extra-check.yml)\n'
        ok, missing, found = check_consistency(content)
        self.assertTrue(ok)
        self.assertIn("extra-check.yml", found)

    def test_no_workflows_line_fails(self):
        content = 'name: Release\njobs:\n  test:\n    runs-on: ubuntu-latest\n'
        ok, missing, found = check_consistency(content)
        self.assertFalse(ok)


class TestGetEnforcingWorkflows(unittest.TestCase):
    """Test the enforcing workflows registry."""

    def test_returns_list_of_tuples(self):
        workflows = get_enforcing_workflows()
        self.assertIsInstance(workflows, list)
        for item in workflows:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_includes_original_four(self):
        names = {wf for wf, _ in get_enforcing_workflows()}
        self.assertIn("chaos.yml", names)
        self.assertIn("otel-smoke.yml", names)
        self.assertIn("perf-profile.yml", names)
        self.assertIn("adapter-live.yml", names)

    def test_includes_new_phase_e_additions(self):
        names = {wf for wf, _ in get_enforcing_workflows()}
        self.assertIn("red-team.yml", names)
        self.assertIn("formal-verify.yml", names)


class TestMainIntegration(unittest.TestCase):
    """Integration test for main() against a tmp directory."""

    def _run_main_with_release_content(self, content: str) -> int:
        """Create a temp project dir with .github/workflows/release.yml and run main()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wf_dir = Path(tmpdir) / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "release.yml").write_text(content, encoding="utf-8")
            old_env = os.environ.get("CLAUDE_PROJECT_DIR")
            try:
                os.environ["CLAUDE_PROJECT_DIR"] = tmpdir
                return main([])
            finally:
                if old_env is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = old_env

    def test_main_passes_with_all_workflows(self):
        content = textwrap.dedent("""\
            name: Release
            jobs:
              release-gate:
                steps:
                  - name: Weekly workflow status gate
                    run: |
                      WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml)
        """)
        exit_code = self._run_main_with_release_content(content)
        self.assertEqual(exit_code, 0)

    def test_main_fails_with_missing_workflows(self):
        content = textwrap.dedent("""\
            name: Release
            jobs:
              release-gate:
                steps:
                  - name: Weekly workflow status gate
                    run: |
                      WORKFLOWS=(chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml)
        """)
        exit_code = self._run_main_with_release_content(content)
        self.assertEqual(exit_code, 1)

    def test_main_returns_2_on_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("CLAUDE_PROJECT_DIR")
            try:
                os.environ["CLAUDE_PROJECT_DIR"] = tmpdir
                exit_code = main([])
                self.assertEqual(exit_code, 2)
            finally:
                if old_env is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = old_env


if __name__ == "__main__":
    unittest.main()
