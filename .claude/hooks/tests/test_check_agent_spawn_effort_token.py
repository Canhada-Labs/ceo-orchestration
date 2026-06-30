"""PLAN-020 Phase 3 — `_has_effort_token` rejection tests.

`/effort` slash-command tokens are CEO-only. They MUST NOT appear in
spawn prompts. `check_agent_spawn.py::_has_effort_token` rejects any
spawn whose prompt contains `/effort [low|default|high|max]` token.

Tests skip until Phase 3 lands.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import check_agent_spawn  # noqa: E402

HAS_PHASE_3 = hasattr(check_agent_spawn, "_has_effort_token")


@unittest.skipUnless(HAS_PHASE_3, "PLAN-020 Phase 3 not yet landed")
class HasEffortTokenTest(unittest.TestCase):
    """Direct tests of `_has_effort_token`."""

    def test_effort_low_detected(self):
        self.assertTrue(check_agent_spawn._has_effort_token("Use /effort low"))

    def test_effort_default_detected(self):
        self.assertTrue(
            check_agent_spawn._has_effort_token("Run /effort default for this")
        )

    def test_effort_high_detected(self):
        self.assertTrue(check_agent_spawn._has_effort_token("/effort high"))

    def test_effort_max_detected(self):
        self.assertTrue(
            check_agent_spawn._has_effort_token("Set /effort max please")
        )

    def test_effort_no_tier_detected(self):
        # Just `/effort` alone is also a violation
        self.assertTrue(check_agent_spawn._has_effort_token("/effort"))

    def test_effort_case_insensitive(self):
        self.assertTrue(check_agent_spawn._has_effort_token("/EFFORT high"))

    def test_no_effort_token_returns_false(self):
        self.assertFalse(
            check_agent_spawn._has_effort_token("Just regular text here")
        )

    def test_url_with_effort_in_path_not_detected(self):
        # URLs containing /effort/ should NOT match (preceded by alphanumeric/slash)
        self.assertFalse(
            check_agent_spawn._has_effort_token(
                "See https://example.com/effort/v1 for spec"
            )
        )

    def test_effort_inside_fence_ignored(self):
        # Code fences masked
        prompt = "```\n/effort high\n```\n\nactual content"
        self.assertFalse(check_agent_spawn._has_effort_token(prompt))

    def test_effort_inside_html_comment_ignored(self):
        prompt = "<!-- /effort high -->\nactual content"
        self.assertFalse(check_agent_spawn._has_effort_token(prompt))


if __name__ == "__main__":
    unittest.main()
