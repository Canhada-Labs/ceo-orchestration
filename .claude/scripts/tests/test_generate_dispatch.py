"""PLAN-020 Phase 1 — generate-dispatch.py auto-gen tests."""

from __future__ import annotations

import json
import os
import sys
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "generate-dispatch.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(REPO_ROOT),
    )


class GenerateDispatchTest(unittest.TestCase):

    def test_default_emits_to_stdout(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("# `.claude/agents/_dispatch.md`", result.stdout)

    def test_check_passes_when_in_sync(self):
        # Assumes _dispatch.md was generated and committed
        result = _run("--check")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_output_contains_table_header(self):
        result = _run()
        # PLAN-021: Model column added between Version and Tools
        self.assertIn(
            "| Slug | Name | Version | Model | Tools | Skill ref hash | Description |",
            result.stdout,
        )

    def test_output_model_column_values(self):
        # PLAN-021 ADR-052 + ADR-149 (W0): verify per-role distribution
        result = _run()
        self.assertIn("`claude-fable-5`", result.stdout)  # code-reviewer + security (W0 variant A)
        self.assertIn("`sonnet-4.6`", result.stdout)  # qa + performance
        self.assertNotIn("`haiku-4.5`", result.stdout)  # devops lifted to sonnet floor (S220)

    def test_critical_archetypes_use_opus(self):
        # Security-critical VETO holders MUST stay on a floor-tier model
        # (ADR-149 allowlist: opus-4-8 or fable-5; W0 variant A = fable-5).
        result = _run()
        floor = ("`claude-opus-4-8`", "`claude-fable-5`")
        for line in result.stdout.splitlines():
            if "`code-reviewer`" in line or "`security-engineer`" in line:
                self.assertTrue(
                    any(f in line for f in floor),
                    msg=f"critical VETO holder not floor-tier: {line}",
                )

    def test_output_contains_5_canonical_agents(self):
        result = _run()
        for name in (
            "code-reviewer",
            "security-engineer",
            "qa-architect",
            "performance-engineer",
            "devops",
        ):
            self.assertIn(f"`{name}`", result.stdout, msg=f"missing {name}")

    def test_output_excludes_probe_agents(self):
        result = _run()
        # _probe_*.md files have leading underscore, should be excluded
        self.assertNotIn("_probe_missing_skill", result.stdout)
        self.assertNotIn("_probe_canonical_edit", result.stdout)
        self.assertNotIn("_probe_architect", result.stdout)

    def test_provenance_section_present(self):
        result = _run()
        self.assertIn("## Provenance", result.stdout)
        self.assertIn("Total agents:", result.stdout)


if __name__ == "__main__":
    unittest.main()
