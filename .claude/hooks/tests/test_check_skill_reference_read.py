"""PLAN-020 Phase 2 — check_skill_reference_read.py PostToolUse observer tests."""

from __future__ import annotations

import json
import os
import sys
import subprocess
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import check_skill_reference_read as csrr  # noqa: E402

try:
    from _lib.testing import TestEnvContext  # noqa: E402
except ImportError:
    TestEnvContext = unittest.TestCase


class IsSkillMdPathTest(TestEnvContext):

    def test_skill_md_under_skills_root_is_recognized(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "test-skill"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text("body", encoding="utf-8")
        self.assertTrue(
            csrr._is_skill_md_path(str(skill_path), self.project_dir)
        )

    def test_non_skill_md_filename_not_recognized(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "test-skill"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        readme = skill_dir / "README.md"
        readme.write_text("body", encoding="utf-8")
        self.assertFalse(
            csrr._is_skill_md_path(str(readme), self.project_dir)
        )

    def test_path_outside_skills_root_not_recognized(self):
        outside = self.project_dir / "SKILL.md"
        outside.write_text("body", encoding="utf-8")
        self.assertFalse(
            csrr._is_skill_md_path(str(outside), self.project_dir)
        )

    def test_empty_path_returns_false(self):
        self.assertFalse(csrr._is_skill_md_path("", self.project_dir))

    def test_nonexistent_path_returns_false(self):
        self.assertFalse(
            csrr._is_skill_md_path(
                "/nonexistent/.claude/skills/core/x/SKILL.md",
                self.project_dir,
            )
        )


class ComputeHashTest(TestEnvContext):

    def test_hash_known_content(self):
        path = self.project_dir / "test.txt"
        path.write_bytes(b"hello world")
        h = csrr._compute_hash(str(path))
        # SHA-256 of "hello world"
        expected = (
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )
        self.assertEqual(h, expected)

    def test_hash_missing_file_returns_none(self):
        self.assertIsNone(csrr._compute_hash("/nonexistent/path"))

    def test_hash_empty_file(self):
        path = self.project_dir / "empty.txt"
        path.write_bytes(b"")
        h = csrr._compute_hash(str(path))
        # SHA-256 of empty
        expected = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        self.assertEqual(h, expected)


class DecideTest(TestEnvContext):

    def test_non_skill_path_returns_allow(self):
        path = self.project_dir / "src" / "foo.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# code", encoding="utf-8")
        result = csrr.decide(
            file_path=str(path),
            repo_root=self.project_dir,
            project_dir=str(self.project_dir),
        )
        decision = json.loads(result)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_skill_md_returns_allow_with_breadcrumb(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "test"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text("body content", encoding="utf-8")

        result = csrr.decide(
            file_path=str(skill_path),
            repo_root=self.project_dir,
            project_dir=str(self.project_dir),
        )
        decision = json.loads(result)
        # Must always allow (PostToolUse cannot block)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_decide_handles_missing_file_gracefully(self):
        # Path under skills/ but file deleted between hook fire + read
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "test"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        ghost = skill_dir / "SKILL.md"
        # Don't create the file
        result = csrr.decide(
            file_path=str(ghost),
            repo_root=self.project_dir,
            project_dir=str(self.project_dir),
        )
        decision = json.loads(result)
        # Always allow (fail-open for observer)
        self.assertEqual(decision.get("decision", "allow"), "allow")


class HookSubprocessTest(unittest.TestCase):
    """End-to-end subprocess invocation."""

    def test_hook_subprocess_emits_allow_on_garbage_input(self):
        proc = subprocess.run(
            [sys.executable, str(_HOOKS_DIR / "check_skill_reference_read.py")],
            input="garbage{{{",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": "/tmp"},
        )
        decision = json.loads(proc.stdout)
        # PostToolUse fails open silently
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_hook_subprocess_emits_allow_on_empty_input(self):
        proc = subprocess.run(
            [sys.executable, str(_HOOKS_DIR / "check_skill_reference_read.py")],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": "/tmp"},
        )
        decision = json.loads(proc.stdout)
        self.assertEqual(decision.get("decision", "allow"), "allow")


if __name__ == "__main__":
    unittest.main()
