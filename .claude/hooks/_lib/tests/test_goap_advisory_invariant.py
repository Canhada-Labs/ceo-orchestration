"""PLAN-098 Wave C.2 — advisory-only invariant hook integration (AC5, AC6).

Verifies check_agent_spawn.decide() blocks spawns referencing a
`goap-plan-id` reference UNLESS BOTH:
  1. prompt contains `## GOAP CONFIRM` block
  2. env var CEO_GOAP_CONFIRMED=1 set in host process

Stdlib-only. Uses TestEnvContext from `_lib.testing` for env isolation.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import check_agent_spawn  # noqa: E402

# Sentinel team names regex — minimal stub so the spawn hook treats names as
# matched. Real regex is loaded from team.md; for tests we use a compiled
# pattern covering the role name we use in fixtures.
_NAMES_RE = re.compile(r"Staff Code Reviewer", re.IGNORECASE)

_SKILL_CONTENT_BLOCK = "\n".join([
    "## SKILL CONTENT",
    "",
    "This is a stub skill content block for the PLAN-098 Wave C.2 hook integration",
    "test. The real skill body in production includes the agent persona description,",
    "responsibilities, primary outputs, and any pitfalls. For the unit test we only",
    "need >=256 non-whitespace bytes (per `_SKILL_CONTENT_MIN_BYTES`) so the spawn",
    "hook's `_has_skill_content()` check returns True without bypassing the new",
    "goap_advisory_without_owner_confirm sentinel logic that we are exercising in",
    "this test module. Lorem ipsum filler to reach the byte minimum threshold: foo",
    "bar baz qux quux corge grault garply waldo fred plugh xyzzy thud.",
])


class TestGoapAdvisoryInvariant(unittest.TestCase):
    """AC5 — spawn referencing goap-plan-id REQUIRES Owner confirmation."""

    def _decide(self, prompt: str, env: dict) -> "check_agent_spawn.Decision":
        return check_agent_spawn.decide(
            description="Staff Code Reviewer",
            prompt=prompt,
            names_regex=_NAMES_RE,
            env=env,
            subagent_type="code-reviewer",
        )

    def test_spawn_with_goap_id_no_markers_blocks(self):
        prompt = "goap-plan-id: PLAN-098\n" + _SKILL_CONTENT_BLOCK
        env = {"CEO_GOAP_CONFIRMED": ""}
        decision = self._decide(prompt, env)
        self.assertFalse(decision.allow)
        self.assertIn("goap_advisory_without_owner_confirm", decision.reason)
        self.assertIn("## GOAP CONFIRM block", decision.reason)
        self.assertIn("CEO_GOAP_CONFIRMED=1 env", decision.reason)

    def test_spawn_with_goap_id_only_confirm_block_no_env_blocks(self):
        prompt = (
            "goap-plan-id: PLAN-098\n\n"
            "## GOAP CONFIRM\n"
            "Owner approved this action manually.\n\n"
            + _SKILL_CONTENT_BLOCK
        )
        env = {"CEO_GOAP_CONFIRMED": ""}
        decision = self._decide(prompt, env)
        self.assertFalse(decision.allow)
        self.assertIn("goap_advisory_without_owner_confirm", decision.reason)
        self.assertIn("CEO_GOAP_CONFIRMED=1 env", decision.reason)

    def test_spawn_with_goap_id_only_env_no_block_blocks(self):
        prompt = "goap-plan-id: PLAN-098\n" + _SKILL_CONTENT_BLOCK
        env = {"CEO_GOAP_CONFIRMED": "1"}
        decision = self._decide(prompt, env)
        self.assertFalse(decision.allow)
        self.assertIn("goap_advisory_without_owner_confirm", decision.reason)
        self.assertIn("## GOAP CONFIRM block", decision.reason)

    def test_spawn_with_goap_id_both_markers_allows(self):
        prompt = (
            "goap-plan-id: PLAN-098\n\n"
            "## GOAP CONFIRM\n"
            "Owner approved this action manually.\n\n"
            + _SKILL_CONTENT_BLOCK
        )
        env = {"CEO_GOAP_CONFIRMED": "1"}
        decision = self._decide(prompt, env)
        self.assertTrue(decision.allow, f"unexpected block: {decision.reason}")

    def test_spawn_without_goap_id_unaffected_by_new_check(self):
        # Plain spawn (no GOAP reference) — env state irrelevant for new check.
        prompt = _SKILL_CONTENT_BLOCK
        env = {"CEO_GOAP_CONFIRMED": ""}
        decision = self._decide(prompt, env)
        # This should ALLOW (named spawn with skill content); the GOAP check
        # is purely additive and must not regress non-GOAP paths.
        self.assertTrue(decision.allow, f"non-GOAP spawn regressed: {decision.reason}")

    def test_block_reason_classification(self):
        reason = (
            "GOVERNANCE: goap_advisory_without_owner_confirm: "
            "spawn references a GOAP plan (description='Staff Code Reviewer') "
            "but lacks: CEO_GOAP_CONFIRMED=1 env, ## GOAP CONFIRM block."
        )
        code = check_agent_spawn._classify_block_reason(reason)
        self.assertEqual(code, "goap_advisory_without_owner_confirm")

    def test_case_insensitive_goap_plan_id_match(self):
        prompt = "GOAP-PLAN-ID: PLAN-098\n" + _SKILL_CONTENT_BLOCK
        env = {"CEO_GOAP_CONFIRMED": ""}
        decision = self._decide(prompt, env)
        self.assertFalse(decision.allow)
        self.assertIn("goap_advisory_without_owner_confirm", decision.reason)

    def test_case_insensitive_confirm_header_match(self):
        prompt = (
            "goap-plan-id: PLAN-098\n\n"
            "## goap confirm\n"
            "Owner approved.\n\n"
            + _SKILL_CONTENT_BLOCK
        )
        env = {"CEO_GOAP_CONFIRMED": "1"}
        decision = self._decide(prompt, env)
        self.assertTrue(decision.allow, f"unexpected block: {decision.reason}")


if __name__ == "__main__":
    unittest.main()
