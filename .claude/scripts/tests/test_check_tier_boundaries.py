"""Unit tests for check-tier-boundaries.py."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

_spec = importlib.util.spec_from_file_location(
    "check_tier_boundaries", str(SCRIPTS_DIR / "check-tier-boundaries.py")
)
ctb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctb)


class TierBoundaryTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tier-test-"))
        self.repo_root = self.tmp / "repo"
        (self.repo_root / ".claude" / "skills" / "core" / "example-skill").mkdir(parents=True)
        (self.repo_root / ".claude" / "skills" / "frontend" / "fe-skill").mkdir(parents=True)
        (self.repo_root / ".claude" / "skills" / "domains" / "fintech" / "skills" / "trading").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel: str, content: str) -> Path:
        p = self.repo_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p


class TestFenceStateMachine(TierBoundaryTestBase):
    def test_clean_core_skill(self):
        self.write(
            ".claude/skills/core/example-skill/SKILL.md",
            "# Example\n\nThis is a test. No domain refs here.\n",
        )
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(violations, [])

    def test_detects_domain_ref_in_prose(self):
        self.write(
            ".claude/skills/core/example-skill/SKILL.md",
            "See domains/fintech/skills/trading/SKILL.md for an example.\n",
        )
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("domains/fintech/skills/trading", violations[0][2])

    def test_domain_ref_inside_fenced_block_ignored(self):
        content = (
            "# Example\n\n"
            "Normal prose.\n"
            "```\n"
            "Code: domains/fintech/skills/trading/SKILL.md\n"
            "```\n"
            "More prose.\n"
        )
        self.write(".claude/skills/core/example-skill/SKILL.md", content)
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(violations, [])

    def test_domain_ref_inside_tilde_fence_ignored(self):
        content = (
            "# Example\n\n"
            "~~~\n"
            "Code: domains/fintech/skills/trading/SKILL.md\n"
            "~~~\n"
        )
        self.write(".claude/skills/core/example-skill/SKILL.md", content)
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(violations, [])

    def test_relative_path_domain_ref_detected(self):
        self.write(
            ".claude/skills/core/example-skill/SKILL.md",
            "Link: ../../domains/fintech/skills/trading\n",
        )
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(len(violations), 1)

    def test_detects_on_line_2_after_fence(self):
        content = (
            "```\nfenced\n```\n"
            "plain domains/fintech/skills/trading/SKILL.md reference\n"
        )
        self.write(".claude/skills/core/example-skill/SKILL.md", content)
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/SKILL.md"
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][0], 4)


class TestYamlBlockScalarHandling(TierBoundaryTestBase):
    def test_yaml_content_block_ignored(self):
        yaml_text = (
            "skill: example\n"
            "scenarios:\n"
            "  - id: X\n"
            "    input:\n"
            "      content: |\n"
            "        def q(u):\n"
            "          return domains/fintech/skills/trading/SKILL.md\n"
            "    expected: true\n"
        )
        self.write(
            ".claude/skills/core/example-skill/benchmarks/demo.yaml", yaml_text
        )
        # Benchmarks dir is excluded entirely from discovery, but let's
        # also verify the preprocess function works
        pre = ctb.preprocess_yaml(yaml_text)
        self.assertNotIn("domains/fintech/skills/trading", pre)

    def test_yaml_outside_content_block_still_detected(self):
        yaml_text = (
            "skill: example\n"
            "description: See domains/fintech/skills/trading for context\n"
            "scenarios: []\n"
        )
        # Write directly under skills/core (not benchmarks/) so it IS checked
        self.write(".claude/skills/core/example-skill/meta.yaml", yaml_text)
        violations = ctb.find_violations(
            self.repo_root / ".claude/skills/core/example-skill/meta.yaml"
        )
        self.assertEqual(len(violations), 1)


class TestDiscovery(TierBoundaryTestBase):
    def test_benchmarks_excluded_from_discovery(self):
        self.write(
            ".claude/skills/core/example-skill/benchmarks/a.yaml",
            "content: |\n  domains/fintech/skills/trading/SKILL.md\n",
        )
        files = ctb.discover_files(self.repo_root)
        # benchmarks/a.yaml should NOT be in the list
        self.assertFalse(
            any("/benchmarks/" in str(f) for f in files),
            f"benchmarks should be excluded, got: {files}",
        )

    def test_domains_not_walked(self):
        self.write(
            ".claude/skills/domains/fintech/skills/trading/SKILL.md",
            "# trading skill content\n",
        )
        files = ctb.discover_files(self.repo_root)
        self.assertFalse(
            any("/domains/" in str(f) for f in files),
            f"domains should be excluded, got: {files}",
        )

    def test_core_and_frontend_walked(self):
        self.write(".claude/skills/core/example-skill/SKILL.md", "core")
        self.write(".claude/skills/frontend/fe-skill/SKILL.md", "fe")
        files = ctb.discover_files(self.repo_root)
        paths = [str(f) for f in files]
        self.assertTrue(any("core/example-skill" in p for p in paths))
        self.assertTrue(any("frontend/fe-skill" in p for p in paths))


class TestMainCLI(TierBoundaryTestBase):
    def _run(self, argv):
        import io
        from contextlib import redirect_stdout, redirect_stderr

        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            try:
                rc = ctb.main(argv)
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 1
        return buf.getvalue(), err.getvalue(), rc

    def test_cli_clean_exit_0(self):
        self.write(".claude/skills/core/example-skill/SKILL.md", "# clean\n")
        out, err, rc = self._run(["--repo-root", str(self.repo_root)])
        self.assertEqual(rc, 0)
        self.assertIn("clean", out)

    def test_cli_violation_exit_1(self):
        self.write(
            ".claude/skills/core/example-skill/SKILL.md",
            "Oops: domains/fintech/skills/trading/SKILL.md\n",
        )
        out, err, rc = self._run(["--repo-root", str(self.repo_root)])
        self.assertEqual(rc, 1)
        self.assertIn("violation", err)

    def test_cli_missing_skills_dir_exit_2(self):
        out, err, rc = self._run(["--repo-root", str(self.tmp)])
        self.assertEqual(rc, 2)

    def test_allowlisted_file_ignored(self):
        self.write(
            ".claude/skills/frontend/frontend-data-layer/SKILL.md",
            "Extension: domains/fintech/skills/trading/SKILL.md is legit here\n",
        )
        out, err, rc = self._run(["--repo-root", str(self.repo_root)])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
