"""PLAN-105 Wave A.4 + A.5 — goap-planner.py instrumentation tests.

AC4: goap_replan_triggered schema accepts plan_id field (None default; keyword-only param).
AC5: /goap invocation emits exactly one goap_recommendation_rendered per call
     with non-empty action_ids_csv and matching actions_rendered_count.

Stdlib-only. Loads .claude/scripts/goap-planner.py via importlib.util.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from _lib.testing import TestEnvContext  # noqa: E402


_GOAP_PLANNER_PATH = _REPO_ROOT / ".claude" / "scripts" / "goap-planner.py"


def _load_goap_planner():
    spec = importlib.util.spec_from_file_location("goap_planner", _GOAP_PLANNER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load goap-planner from {_GOAP_PLANNER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["goap_planner"] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_log():
    log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestReplanPlanIdField(TestEnvContext):
    """AC4 — plan_id keyword param on replan_from."""

    def setUp(self):
        super().setUp()
        # Restore CLAUDE_PROJECT_DIR to real repo so action-cost-baseline.json
        # resolves; audit log isolation still works via CEO_AUDIT_LOG_PATH.
        os.environ["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "1"
        self.goap = _load_goap_planner()

    def test_replan_omitted_plan_id_byte_identical(self):
        """Backward-compat: no plan_id kwarg → behavior identical to v1.31.0."""
        current = self.goap.State(predicates=frozenset({"plan_status=draft"}))
        goal = frozenset({"plan_status=executing"})
        actions, _ = self.goap.load_action_library()
        result = self.goap.replan_from(current, goal, actions, attempt=1, audit_session="s1")
        # Should produce a SearchResult — no exception.
        self.assertIsNotNone(result)
        events = _read_log()
        replans = [e for e in events if e.get("action") == "goap_replan_triggered"]
        self.assertEqual(len(replans), 1)
        # plan_id field should NOT be present when omitted (byte-identical).
        self.assertNotIn("plan_id", replans[0])

    def test_replan_with_plan_id_propagates(self):
        current = self.goap.State(predicates=frozenset({"plan_status=draft"}))
        goal = frozenset({"plan_status=executing"})
        actions, _ = self.goap.load_action_library()
        self.goap.replan_from(
            current, goal, actions,
            attempt=1, audit_session="s1", plan_id="PLAN-105",
        )
        events = _read_log()
        replans = [e for e in events if e.get("action") == "goap_replan_triggered"]
        self.assertEqual(len(replans), 1)
        self.assertEqual(replans[0].get("plan_id"), "PLAN-105")

    def test_replan_exhausted_carries_plan_id(self):
        current = self.goap.State(predicates=frozenset({"plan_status=draft"}))
        goal = frozenset({"plan_status=executing"})
        actions, _ = self.goap.load_action_library()
        self.goap.replan_from(
            current, goal, actions,
            attempt=99, audit_session="s1", plan_id="PLAN-105",
        )
        events = _read_log()
        exhausted = [e for e in events if e.get("action") == "goap_replan_exhausted"]
        self.assertEqual(len(exhausted), 1)
        self.assertEqual(exhausted[0].get("plan_id"), "PLAN-105")


class TestRenderedEmit(TestEnvContext):
    """AC5 — plan_for_goal emits exactly one _rendered per call."""

    def setUp(self):
        super().setUp()
        os.environ["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "1"
        self.goap = _load_goap_planner()

    def test_plan_for_goal_emits_exactly_one_rendered(self):
        digest = self.goap.plan_for_goal("ship v1.32.1", audit_session="s1")
        self.assertNotEqual(digest.get("plan_depth", 0), 0,
                            "plan_for_goal should produce a non-empty plan for 'ship'")
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 1, "exactly one _rendered event expected")
        ev = rendered[0]
        self.assertGreater(len(ev["action_ids_csv"]), 0)
        # The csv count must match the rendered count.
        csv_count = len([t for t in ev["action_ids_csv"].split(",") if t.strip()])
        self.assertEqual(csv_count, ev["actions_rendered_count"])

    def test_no_rendered_when_kill_switch_engaged(self):
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "0"
        # Reload module so kill-switch is picked up if read at import.
        self.goap = _load_goap_planner()
        self.goap.plan_for_goal("ship v1.32.1", audit_session="s1")
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 0,
                         "kill-switch must suppress _rendered emit")

    def test_no_rendered_when_no_plan_found(self):
        # Unknown verb → plan parse fails → no plan emitted.
        self.goap.plan_for_goal("frobnicate the widget", audit_session="s1")
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 0)

    def test_rendered_plan_id_hint_extracted(self):
        self.goap.plan_for_goal("ship PLAN-105 v1.32.1", audit_session="s1")
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 1)
        self.assertEqual(rendered[0]["plan_id"], "PLAN-105")

    def test_rendered_plan_id_sentinel_when_no_hint(self):
        # Goal text with no PLAN-NNN hint.
        digest = self.goap.plan_for_goal("ship the release", audit_session="s1")
        if digest.get("plan_depth", 0) == 0:
            self.skipTest("ship verb produced no plan in this fixture")
        events = _read_log()
        rendered = [e for e in events if e.get("action") == "goap_recommendation_rendered"]
        self.assertEqual(len(rendered), 1)
        self.assertEqual(rendered[0]["plan_id"], "NO_PLAN_HINT")


if __name__ == "__main__":
    unittest.main()
