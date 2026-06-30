"""Smoke tests for `.claude/scripts/generate-skill-inventory.sh --check`.

PLAN-019 VP-F7. Stdlib-only; Python >=3.9 compatible. The bash script
itself is tested via subprocess invocation rather than module import.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "generate-skill-inventory.sh"


class TestGenerateSkillInventoryCheck(unittest.TestCase):
    def test_script_is_executable(self) -> None:
        self.assertTrue(
            SCRIPT.is_file(),
            f"script missing: {SCRIPT}",
        )

    def test_emit_mode_produces_begin_end_markers(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->", result.stdout)
        self.assertIn("<!-- END AUTO-GENERATED SKILL INVENTORY -->", result.stdout)

    def test_check_mode_passes_on_clean_tree(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Clean tree should pass. If it fails here, the committed block
        # drifted from the skill tree — run `generate-skill-inventory.sh`
        # and paste the output between BEGIN/END markers.
        # (S156: xfail removed — L8 regen via S156 mega-sentinel resolved the
        # cookbook-advisor/coverage-audit/requirement-quality-checklist/
        # spec-clarify drift; Core total now 41.)
        self.assertEqual(
            result.returncode,
            0,
            f"drift detected:\nstdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn("PASS", result.stdout)

    def test_unknown_flag_exits_two(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--bogus"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)

    def test_help_flag_exits_zero(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
