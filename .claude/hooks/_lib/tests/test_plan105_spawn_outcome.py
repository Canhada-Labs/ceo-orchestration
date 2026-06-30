"""PLAN-105 Wave A.3 + A.6 — spawn-hook deferred-emit outcome detection tests.

AC3: emit_goap_recommendation_accepted call site wired in check_agent_spawn.py
     allow-path immediately-before-final-allow-return.
AC6: Spawn hook emits _accepted on goap-action-id ∈ action_ids_csv match path.
AC7: Spawn hook emits _overridden:substituted_action when goap-action-id NOT in csv.
AC8: Spawn hook emits _overridden:marker_absent when goap-action-id marker missing.
AC9: Spawn hook emits _overridden:no_render_prior when no recent _rendered event.
AC10: Kill-switch suppresses all 3 paths.

Stdlib-only. Uses TestEnvContext + _audit_log_emit-pre-population pattern.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _read_log():
    log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_rendered_event(plan_id: str, action_ids_csv: str):
    """Pre-populate audit log with a _rendered event so A.6 lookup finds it."""
    from _lib import audit_emit
    audit_emit.emit_goap_recommendation_rendered(
        plan_id=plan_id,
        action_ids_csv=action_ids_csv,
        actions_rendered_count=len([s for s in action_ids_csv.split(",") if s.strip()]),
        goal_verb="ship",
        goal_text_hash="0123456789ab",
        session_id="sess-1",
        project="test",
    )


_NAMES_RE = re.compile(r"Staff Code Reviewer", re.IGNORECASE)

_SKILL_BLOCK = "\n".join([
    "## SKILL CONTENT",
    "",
    "This is a stub skill content block for the PLAN-105 Wave A.6 hook integration",
    "test. The real skill body in production includes the agent persona description,",
    "responsibilities, primary outputs, and any pitfalls. For the unit test we only",
    "need >=256 non-whitespace bytes (per `_SKILL_CONTENT_MIN_BYTES`) so the spawn",
    "hook's `_has_skill_content()` check returns True without bypassing the new",
    "goap_advisory_without_owner_confirm sentinel logic that we are exercising in",
    "this test module. Lorem ipsum filler to reach the byte minimum threshold: foo",
    "bar baz qux quux corge grault garply waldo fred plugh xyzzy thud.",
])

_CONFIRM_BLOCK = "## GOAP CONFIRM\nOwner approves this rendered action for dispatch.\n"


class TestSpawnOutcome(TestEnvContext):
    """A.3 + A.6 — accepted vs overridden classification."""

    def setUp(self):
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "1"
        # Lazy import so env vars hit module init.
        import importlib
        if "check_agent_spawn" in sys.modules:
            importlib.reload(sys.modules["check_agent_spawn"])
        import check_agent_spawn  # noqa: F401
        self.check_agent_spawn = sys.modules["check_agent_spawn"]

    def _decide(self, prompt: str, env: dict):
        merged = {**os.environ, **env}
        return self.check_agent_spawn.decide(
            description="Staff Code Reviewer",
            prompt=prompt,
            names_regex=_NAMES_RE,
            env=merged,
            subagent_type="code-reviewer",
        )

    def test_accepted_on_exact_match(self):
        """AC6 — goap-action-id in action_ids_csv → emit_accepted."""
        _seed_rendered_event("PLAN-105", "spawn_general,spawn_code_reviewer,debate_round_1")
        prompt = (
            "goap-plan-id: PLAN-105\n"
            "goap-action-id: spawn_code_reviewer\n\n"
            f"{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        decision = self._decide(prompt, {"CEO_GOAP_CONFIRMED": "1"})
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        accepts = [e for e in events if e.get("action") == "goap_recommendation_accepted"]
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(accepts), 1)
        self.assertEqual(len(overs), 0)
        self.assertEqual(accepts[0]["plan_id"], "PLAN-105")
        self.assertEqual(accepts[0]["action_id"], "spawn_code_reviewer")

    def test_overridden_substituted_action(self):
        """AC7 — goap-action-id NOT in csv → emit_overridden:substituted_action."""
        _seed_rendered_event("PLAN-105", "spawn_general,debate_round_1")
        prompt = (
            "goap-plan-id: PLAN-105\n"
            "goap-action-id: spawn_security_engineer\n\n"
            f"{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        decision = self._decide(prompt, {"CEO_GOAP_CONFIRMED": "1"})
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        accepts = [e for e in events if e.get("action") == "goap_recommendation_accepted"]
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(accepts), 0)
        self.assertEqual(len(overs), 1)
        self.assertEqual(overs[0]["override_type"], "substituted_action")
        self.assertEqual(overs[0]["dispatched_action_id"], "spawn_security_engineer")

    def test_overridden_marker_absent(self):
        """AC8 — missing goap-action-id marker → emit_overridden:marker_absent."""
        _seed_rendered_event("PLAN-105", "spawn_general")
        prompt = (
            "goap-plan-id: PLAN-105\n"
            # no goap-action-id marker!
            f"\n{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        decision = self._decide(prompt, {"CEO_GOAP_CONFIRMED": "1"})
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(overs), 1)
        self.assertEqual(overs[0]["override_type"], "marker_absent")
        self.assertEqual(overs[0]["dispatched_action_id"], "MARKER_ABSENT")

    def test_overridden_no_render_prior(self):
        """AC9 — no recent _rendered → emit_overridden:no_render_prior."""
        # NO seeded _rendered event.
        prompt = (
            "goap-plan-id: PLAN-105\n"
            "goap-action-id: spawn_general\n\n"
            f"{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        decision = self._decide(prompt, {"CEO_GOAP_CONFIRMED": "1"})
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(overs), 1)
        self.assertEqual(overs[0]["override_type"], "no_render_prior")
        self.assertEqual(overs[0]["original_action_id"], "NO_RENDER_PRIOR")

    def test_kill_switch_silences_all_emits(self):
        """AC10 — CEO_GOAP_ADVISORY_ENABLED=0 silences A.6 deferred-emit paths.

        IMPORTANT: per PLAN-098 doctrine, kill-switch silences emits but
        does NOT disable the GOAP confirm-block enforcement. The block-path
        gates at check_agent_spawn.py:1276 continue to require both env +
        block regardless of kill-switch (defense-in-depth). PLAN-105 R2 P2
        clarifies test comment to match shipped behavior.
        """
        _seed_rendered_event("PLAN-105", "spawn_general")
        prompt = (
            "goap-plan-id: PLAN-105\n"
            "goap-action-id: spawn_general\n\n"
            f"{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        # Kill-switch=0 silences ONLY the A.6 _accepted/_overridden emits.
        # The existing PLAN-098 block-path enforcement is independent — it
        # still requires CEO_GOAP_CONFIRMED=1 + ## GOAP CONFIRM block,
        # which are present in this test prompt so spawn allows.
        decision = self._decide(prompt, {
            "CEO_GOAP_CONFIRMED": "1",
            "CEO_GOAP_ADVISORY_ENABLED": "0",
        })
        # Spawn allowed (kill-switch doesn't change allow-path classification).
        self.assertTrue(decision.allow, decision.reason)
        # Pre-existing rendered count = 1 (seeded above). Post-decide count
        # for _accepted + _overridden should be ZERO (kill-switch suppresses).
        events = _read_log()
        accepts = [e for e in events if e.get("action") == "goap_recommendation_accepted"]
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(accepts), 0)
        self.assertEqual(len(overs), 0)

    def test_diag_override_disable_forces_accepted(self):
        """Kill-switch CEO_GOAP_OVERRIDE_DETECTION_DISABLED=1 → always _accepted."""
        # NO seeded _rendered event — would normally emit no_render_prior.
        prompt = (
            "goap-plan-id: PLAN-105\n"
            "goap-action-id: spawn_general\n\n"
            f"{_CONFIRM_BLOCK}\n"
            + _SKILL_BLOCK
        )
        decision = self._decide(prompt, {
            "CEO_GOAP_CONFIRMED": "1",
            "CEO_GOAP_OVERRIDE_DETECTION_DISABLED": "1",
        })
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        accepts = [e for e in events if e.get("action") == "goap_recommendation_accepted"]
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(accepts), 1)
        self.assertEqual(len(overs), 0)
        self.assertEqual(accepts[0]["plan_id"], "PLAN-105")

    def test_non_goap_spawn_emits_nothing(self):
        """No goap-plan-id marker → no _accepted / _overridden emit."""
        prompt = _SKILL_BLOCK
        decision = self._decide(prompt, {})
        self.assertTrue(decision.allow, decision.reason)
        events = _read_log()
        accepts = [e for e in events if e.get("action") == "goap_recommendation_accepted"]
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(accepts), 0)
        self.assertEqual(len(overs), 0)


if __name__ == "__main__":
    unittest.main()
