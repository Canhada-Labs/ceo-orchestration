"""PLAN-020 Phase 2 — inject-agent-context.sh --mode=reference tests."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "inject-agent-context.sh"


def _run(*args, env_extra=None):
    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


class ReferenceModeTest(unittest.TestCase):

    def test_default_mode_emits_skill_reference(self):
        # PLAN-059 / ADR-090 #1 (Session 67, 2026-04-27): default flipped
        # from inline (Format A) to reference (Format B) per the
        # framework activation defaults bundle. CEO_SKILL_REFERENCE_MODE=0
        # or --mode=inline reverts.
        result = _run("Staff Code Reviewer", "review changes")
        self.assertIn("## SKILL REFERENCE", result.stdout)
        self.assertNotIn("## SKILL CONTENT", result.stdout)

    def test_reference_mode_emits_skill_reference(self):
        result = _run(
            "--mode=reference", "Staff Code Reviewer", "review changes"
        )
        self.assertIn("## SKILL REFERENCE", result.stdout)
        # Expect the @path sha256= pattern
        self.assertRegex(
            result.stdout,
            r"@\.claude/skills/core/[\w-]+/SKILL\.md sha256=[0-9a-f]{64}",
        )

    def test_reference_mode_includes_summary_line(self):
        result = _run(
            "--mode=reference", "Staff Code Reviewer", "review changes"
        )
        # Summary text follows the reference line
        self.assertIn("Sub-agent: Read this file", result.stdout)

    def test_inline_mode_explicit(self):
        result = _run(
            "--mode=inline", "Staff Code Reviewer", "review changes"
        )
        self.assertIn("## SKILL CONTENT", result.stdout)
        self.assertNotIn("## SKILL REFERENCE", result.stdout)

    def test_ceo_sota_disable_forces_inline(self):
        result = _run(
            "--mode=reference",
            "Staff Code Reviewer",
            "review changes",
            env_extra={"CEO_SOTA_DISABLE": "1"},
        )
        # Master kill — even with --mode=reference, output is inline
        self.assertIn("## SKILL CONTENT", result.stdout)
        self.assertNotIn("## SKILL REFERENCE", result.stdout)

    def test_ceo_skill_reference_mode_zero_forces_inline(self):
        result = _run(
            "--mode=reference",
            "Staff Code Reviewer",
            "review changes",
            env_extra={"CEO_SKILL_REFERENCE_MODE": "0"},
        )
        self.assertIn("## SKILL CONTENT", result.stdout)
        self.assertNotIn("## SKILL REFERENCE", result.stdout)

    def test_reference_mode_hash_is_valid_sha256(self):
        result = _run(
            "--mode=reference", "Staff Code Reviewer", "review changes"
        )
        # Extract hash from output and verify it matches actual file
        m = re.search(
            r"@(\.claude/skills/core/[\w-]+/SKILL\.md) sha256=([0-9a-f]{64})",
            result.stdout,
        )
        self.assertIsNotNone(m, msg=f"reference line not found in: {result.stdout[:500]}")
        path = REPO_ROOT / m.group(1)
        ref_hash = m.group(2)
        if path.is_file():
            import hashlib
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, ref_hash, "hash mismatch in injector output")


if __name__ == "__main__":
    unittest.main()
