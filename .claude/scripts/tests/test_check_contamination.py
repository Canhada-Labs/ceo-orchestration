"""Unit tests for check_contamination.py (Python port, Sprint 3 E.2)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_contamination as cc  # noqa: E402


class ContaminationTestBase(unittest.TestCase):
    """Builds a tiny git repo + runs scan() against it."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ceo-contam-test-")).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=self.root, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "t"],
            cwd=self.root, check=True, capture_output=True,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_and_commit(self, rel: str, content: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        subprocess.run(
            ["git", "add", "-A"], cwd=self.root, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "x", "-q"],
            cwd=self.root, check=True, capture_output=True,
        )


class TestScan(ContaminationTestBase):

    def test_clean_repo_returns_empty(self):
        self._write_and_commit("README.md", "nothing sensitive here")
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_project_name_contamination_found(self):
        self._write_and_commit("src/foo.md", "mentions example owner in prose")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].name, "foo.md")

    def test_underscore_variant(self):
        """example_owner also matches."""
        self._write_and_commit("src/foo.md", "hi @example_owner")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)

    def test_hyphen_variant(self):
        self._write_and_commit("src/foo.md", "hi @example-owner")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)

    def test_acmeledger_variant(self):
        self._write_and_commit("src/foo.md", "in our acmeLedger dashboard")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)

    def test_acme_ledger_with_space(self):
        self._write_and_commit("src/foo.md", "it's acme Ledger's dashboard")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)

    def test_allowlist_license_exact(self):
        self._write_and_commit("LICENSE", "Copyright 2024 example owner")
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_plan_001(self):
        self._write_and_commit(
            ".claude/plans/PLAN-001-evolution.md",
            "historical context includes example owner handle",
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_plan_glob_any_number(self):
        """PLAN-*.md glob covers all plan files, including future PLAN-005+."""
        self._write_and_commit(
            ".claude/plans/PLAN-007-some-future-sprint.md",
            "references example owner handle in planning notes",
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_domain_glob(self):
        self._write_and_commit(
            ".claude/skills/domains/fintech/SKILL.md",
            "example uses example owner as placeholder",
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_claude_md(self):
        self._write_and_commit("CLAUDE.md", "path references example owner home")
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_release_md(self):
        self._write_and_commit(
            "RELEASE.md",
            "cd /Users/devuser/ceo-orchestration && git tag -s v1.0.0",
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_allowlist_docs_quickstart(self):
        self._write_and_commit(
            "docs/QUICKSTART.md",
            "curl https://raw.githubusercontent.com/Canhada-Labs/ceo-orchestration/main/install.sh",
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_untracked_files_ignored(self):
        """Untracked files (not git add'd) should not be scanned."""
        # First: seed the repo with a committed file (so git ls-files has output)
        self._write_and_commit("tracked.md", "clean")
        # Then: write an untracked file directly, do NOT add it
        (self.root / "untracked.md").write_text(
            "example owner here", encoding="utf-8"
        )
        # (no git add)
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_binary_files_skipped(self):
        p = self.root / "image.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n example owner embedded in binary")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "x", "-q"],
            cwd=self.root, check=True, capture_output=True,
        )
        violations = cc.scan(self.root)
        self.assertEqual(violations, [])

    def test_nfkc_normalization_catches_fullwidth(self):
        """Full-width characters should normalize to ASCII and match."""
        # Full-width: "ａｃｍｅｌｅｄｇｅｒ" normalizes to ASCII "acmeledger"
        self._write_and_commit("src/foo.md", "ａｃｍｅｌｅｄｇｅｒ attempt")
        violations = cc.scan(self.root)
        self.assertEqual(len(violations), 1)
