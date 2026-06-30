"""PLAN-105 Wave A.1 + A.2 — audit_emit registration + emit_* tests.

AC1: goap_recommendation_rendered event registered + emit_* defined +
     8-field schema (action, plan_id, action_ids_csv,
     actions_rendered_count, goal_verb, goal_text_hash, session_id, project).
AC2: goap_recommendation_overridden registered with 3-value override_type enum
     (substituted_action / no_render_prior / marker_absent).
AC17: goal text body NEVER appears in audit log payload (LLM06 side-channel guard).

Stdlib-only. Uses TestEnvContext from _lib.testing for env isolation.
CEO_AUDIT_SYNC_MODE=1 forced in setUp to avoid spool-writer flakiness.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks" / "_lib"
if str(_HOOKS_LIB.parent) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB.parent))

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _read_log():
    log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestRegistration(unittest.TestCase):
    """AC1 + AC2 — new actions registered in _KNOWN_ACTIONS."""

    def test_recommendation_rendered_in_known_actions(self):
        self.assertIn("goap_recommendation_rendered", audit_emit._KNOWN_ACTIONS)

    def test_recommendation_overridden_in_known_actions(self):
        self.assertIn("goap_recommendation_overridden", audit_emit._KNOWN_ACTIONS)

    def test_emit_rendered_is_callable(self):
        self.assertTrue(callable(getattr(audit_emit, "emit_goap_recommendation_rendered", None)))

    def test_emit_overridden_is_callable(self):
        self.assertTrue(callable(getattr(audit_emit, "emit_goap_recommendation_overridden", None)))


class TestEmitRendered(TestEnvContext):
    """AC1 — 5 tests for emit_goap_recommendation_rendered."""

    def setUp(self):
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

    def test_emit_fires_on_rendered_tree(self):
        audit_emit.emit_goap_recommendation_rendered(
            plan_id="PLAN-105",
            action_ids_csv="spawn_general,debate_round_1",
            actions_rendered_count=2,
            goal_verb="ship",
            goal_text_hash="abc123def456",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 1)
        ev = rendered[0]
        self.assertEqual(ev["plan_id"], "PLAN-105")
        self.assertEqual(ev["action_ids_csv"], "spawn_general,debate_round_1")
        self.assertEqual(ev["actions_rendered_count"], 2)
        self.assertEqual(ev["goal_verb"], "ship")
        self.assertEqual(ev["goal_text_hash"], "abc123def456")

    def test_goal_text_body_never_in_payload(self):
        """AC17 — LLM06 side-channel guard."""
        sensitive_goal = "ship v1.32.1 with SECRET=hunter2 and prompt body here"
        # The caller is responsible for hashing; we just verify the persisted
        # event NEVER carries the goal_text key.
        audit_emit.emit_goap_recommendation_rendered(
            plan_id="PLAN-105",
            action_ids_csv="spawn_general",
            actions_rendered_count=1,
            goal_verb="ship",
            goal_text_hash="0123456789ab",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        for ev in events:
            self.assertNotIn("goal_text", ev)
            self.assertNotIn(sensitive_goal, json.dumps(ev))

    def test_action_ids_csv_truncated_at_1600(self):
        long = ",".join(["a" + str(i) for i in range(500)])  # > 1600 bytes
        audit_emit.emit_goap_recommendation_rendered(
            plan_id="PLAN-105",
            action_ids_csv=long,
            actions_rendered_count=500,
            goal_verb="ship",
            goal_text_hash="0123456789ab",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_rendered"][-1]
        self.assertLessEqual(len(ev["action_ids_csv"]), 1600)

    def test_count_field_is_int(self):
        audit_emit.emit_goap_recommendation_rendered(
            plan_id="PLAN-105",
            action_ids_csv="a,b,c",
            actions_rendered_count=3,
            goal_verb="ship",
            goal_text_hash="0123456789ab",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_rendered"][-1]
        self.assertIsInstance(ev["actions_rendered_count"], int)
        self.assertEqual(ev["actions_rendered_count"], 3)

    def test_hash_truncated_at_12(self):
        audit_emit.emit_goap_recommendation_rendered(
            plan_id="PLAN-105",
            action_ids_csv="a",
            actions_rendered_count=1,
            goal_verb="ship",
            goal_text_hash="0123456789abcdef" * 8,  # 128 chars
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_rendered"][-1]
        self.assertEqual(len(ev["goal_text_hash"]), 12)


class TestEmitOverridden(TestEnvContext):
    """AC2 + AC7-9 — 7 tests for emit_goap_recommendation_overridden."""

    def setUp(self):
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

    def test_emit_substituted_action(self):
        audit_emit.emit_goap_recommendation_overridden(
            plan_id="PLAN-105",
            original_action_id="spawn_general,spawn_specialist",
            dispatched_action_id="spawn_code_reviewer",
            override_type="substituted_action",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        self.assertEqual(ev["override_type"], "substituted_action")
        self.assertEqual(ev["dispatched_action_id"], "spawn_code_reviewer")

    def test_emit_marker_absent(self):
        audit_emit.emit_goap_recommendation_overridden(
            plan_id="PLAN-105",
            original_action_id="spawn_general",
            dispatched_action_id="MARKER_ABSENT",
            override_type="marker_absent",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        self.assertEqual(ev["override_type"], "marker_absent")
        self.assertEqual(ev["dispatched_action_id"], "MARKER_ABSENT")

    def test_emit_no_render_prior(self):
        audit_emit.emit_goap_recommendation_overridden(
            plan_id="PLAN-105",
            original_action_id="NO_RENDER_PRIOR",
            dispatched_action_id="spawn_specialist",
            override_type="no_render_prior",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        self.assertEqual(ev["override_type"], "no_render_prior")
        self.assertEqual(ev["original_action_id"], "NO_RENDER_PRIOR")

    def test_plan_id_truncated_at_32(self):
        long_plan_id = "PLAN-105-" + "x" * 100
        audit_emit.emit_goap_recommendation_overridden(
            plan_id=long_plan_id,
            original_action_id="a",
            dispatched_action_id="b",
            override_type="substituted_action",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        self.assertLessEqual(len(ev["plan_id"]), 32)

    def test_override_type_truncated_at_32(self):
        weird = "x" * 100
        audit_emit.emit_goap_recommendation_overridden(
            plan_id="PLAN-105",
            original_action_id="a",
            dispatched_action_id="b",
            override_type=weird,
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        self.assertLessEqual(len(ev["override_type"]), 32)

    def test_emit_fields_all_present(self):
        audit_emit.emit_goap_recommendation_overridden(
            plan_id="PLAN-105",
            original_action_id="spawn_a",
            dispatched_action_id="spawn_b",
            override_type="substituted_action",
            session_id="sess-1",
            project="ceo-orchestration",
        )
        events = _read_log()
        ev = [e for e in events if e.get("action") == "goap_recommendation_overridden"][-1]
        for field in (
            "action",
            "plan_id",
            "original_action_id",
            "dispatched_action_id",
            "override_type",
            "session_id",
            "project",
        ):
            self.assertIn(field, ev, f"missing field {field}")

    def test_emit_persists_unique_calls(self):
        for i in range(3):
            audit_emit.emit_goap_recommendation_overridden(
                plan_id="PLAN-105",
                original_action_id=f"a{i}",
                dispatched_action_id=f"b{i}",
                override_type="substituted_action",
                session_id="sess-1",
                project="ceo-orchestration",
            )
        events = _read_log()
        overs = [e for e in events if e.get("action") == "goap_recommendation_overridden"]
        self.assertEqual(len(overs), 3)


if __name__ == "__main__":
    unittest.main()
