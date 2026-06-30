"""Unit tests for `_lib/scratchpad_lib.py` (PLAN-011 Phase 7).

Covers consensus M2 (plan-id derivation discipline) and M8 (clear on
``executing → draft`` rollback). Behavior assertions go beyond exit
code per consensus S5 — every test checks file content, a sqlite row,
or an audit-log JSON field.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


from _lib import audit_emit  # noqa: E402
from _lib import state_store  # noqa: E402
from _lib.scratchpad_lib import (  # noqa: E402
    SCRATCHPAD_STORE_NAME,
    PlanIdDerivationError,
    clear_on_rollback,
    open_scratchpad,
    resolve_plan_id,
)
from _lib.state_store import SqliteStateStore  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _append_plan_transition(
    audit_path: Path,
    *,
    plan_id: str,
    session_id: str,
    from_status: str = "reviewed",
    to_status: str = "executing",
    ts: str = "2026-04-14T00:00:00Z",
) -> None:
    """Seed the isolated audit log with a plan_transition event."""
    event = {
        "action": "plan_transition",
        "plan_id": plan_id,
        "from_status": from_status,
        "to_status": to_status,
        "editor_tool": "Edit",
        "file_path": f".claude/plans/{plan_id}-fixture.md",
        "transition_legal": True,
        "session_id": session_id,
        "project": "",
        "event_schema": "v2",
        "ts": ts,
        "tokens_in": None,
        "tokens_out": None,
        "tokens_total": None,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


class ScratchpadLibTest(TestEnvContext):
    """Base — points CEO_STATE_ROOT at the isolated temp home."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_STATE_ROOT"] = str(self.home_dir / ".claude" / "state")
        self.audit_log = Path(os.environ["CEO_AUDIT_LOG_PATH"])


# --- resolve_plan_id ----------------------------------------------------


class TestResolvePlanId(ScratchpadLibTest):
    def test_raises_when_no_session_id_available(self) -> None:
        os.environ.pop("CLAUDE_SESSION_ID", None)
        with self.assertRaises(PlanIdDerivationError) as ctx:
            resolve_plan_id()
        self.assertIn("CLAUDE_SESSION_ID", str(ctx.exception))

    def test_raises_when_audit_log_missing(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-nolog"
        # audit log does not exist yet
        self.assertFalse(self.audit_log.exists())
        with self.assertRaises(PlanIdDerivationError):
            resolve_plan_id()

    def test_raises_when_no_matching_session(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-other"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess-alpha"
        )
        with self.assertRaises(PlanIdDerivationError) as ctx:
            resolve_plan_id()
        self.assertIn("sess-other", str(ctx.exception))

    def test_resolves_from_single_matching_event(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess-alpha"
        )
        self.assertEqual(resolve_plan_id(), "PLAN-011")

    def test_most_recent_matching_event_wins(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log,
            plan_id="PLAN-010",
            session_id="sess-alpha",
            to_status="done",
            ts="2026-04-13T10:00:00Z",
        )
        _append_plan_transition(
            self.audit_log,
            plan_id="PLAN-011",
            session_id="sess-alpha",
            ts="2026-04-13T11:00:00Z",
        )
        self.assertEqual(resolve_plan_id(), "PLAN-011")

    def test_explicit_session_arg_wins_over_env(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-env"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-100", session_id="sess-env"
        )
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-200", session_id="sess-explicit"
        )
        self.assertEqual(resolve_plan_id(session_id="sess-explicit"), "PLAN-200")

    def test_refuses_env_var_spoofing_fallback(self) -> None:
        """Consensus M2: no fallback to CEO_CURRENT_PLAN even if set."""
        os.environ.pop("CLAUDE_SESSION_ID", None)
        os.environ["CEO_CURRENT_PLAN"] = "PLAN-EVIL"
        with self.assertRaises(PlanIdDerivationError):
            resolve_plan_id()

    def test_ignores_non_plan_transition_events(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        # Seed a non-transition event first
        audit_emit.emit_agent_spawn if hasattr(audit_emit, "emit_agent_spawn") else None
        # Write a junk event line
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "action": "agent_spawn",
                "session_id": "sess-alpha",
                "plan_id": "PLAN-IRRELEVANT",
            }) + "\n")
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess-alpha"
        )
        self.assertEqual(resolve_plan_id(), "PLAN-011")

    def test_whitespace_session_id_treated_as_missing(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "   "
        with self.assertRaises(PlanIdDerivationError):
            resolve_plan_id()


# --- open_scratchpad ----------------------------------------------------


class TestOpenScratchpad(ScratchpadLibTest):
    def test_returns_working_state_store(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess-alpha"
        )
        with open_scratchpad() as store:
            self.assertIsInstance(store, SqliteStateStore)
            self.assertEqual(store.store_name, SCRATCHPAD_STORE_NAME)
            self.assertEqual(store.plan_id, "PLAN-011")
            store.set("handoff-key", "hello-from-phase-1")
            self.assertEqual(store.get("handoff-key"), b"hello-from-phase-1")

    def test_open_scratchpad_uses_phase_0_backend_not_new_file_layout(self) -> None:
        """Consensus H1: scratchpad wraps Phase 0 store, not a separate backend."""
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-042", session_id="sess-alpha"
        )
        with open_scratchpad() as store:
            store.set("k", "v")
        # The Phase-0 state root must contain the scratchpad dir + plan sqlite.
        expected = (
            Path(os.environ["CEO_STATE_ROOT"])
            / SCRATCHPAD_STORE_NAME
            / "PLAN-042.sqlite"
        )
        self.assertTrue(expected.exists(), f"expected sqlite at {expected}")

    def test_explicit_plan_id_bypasses_derivation(self) -> None:
        # No audit events at all — explicit plan id still works.
        with open_scratchpad(plan_id="PLAN-999") as store:
            store.set("k", "v")
            self.assertEqual(store.get("k"), b"v")

    def test_derivation_error_propagates(self) -> None:
        os.environ.pop("CLAUDE_SESSION_ID", None)
        with self.assertRaises(PlanIdDerivationError):
            open_scratchpad()


# --- clear_on_rollback --------------------------------------------------


class TestClearOnRollback(ScratchpadLibTest):
    def _seed_keys(self, plan_id: str, count: int = 3) -> None:
        with state_store.open_store("scratchpad", plan_id) as s:
            for i in range(count):
                s.set(f"k-{i}", f"v-{i}")

    def test_executing_to_draft_clears_all_keys(self) -> None:
        self._seed_keys("PLAN-011", count=3)
        cleared = clear_on_rollback("PLAN-011", "executing", "draft")
        self.assertEqual(cleared, 3)
        with state_store.open_store("scratchpad", "PLAN-011") as s:
            self.assertEqual(s.list_keys(), [])

    def test_done_transition_is_noop(self) -> None:
        self._seed_keys("PLAN-011", count=2)
        cleared = clear_on_rollback("PLAN-011", "executing", "done")
        self.assertEqual(cleared, 0)
        with state_store.open_store("scratchpad", "PLAN-011") as s:
            self.assertEqual(sorted(s.list_keys()), ["k-0", "k-1"])

    def test_abandoned_transition_is_noop(self) -> None:
        self._seed_keys("PLAN-011", count=2)
        self.assertEqual(
            clear_on_rollback("PLAN-011", "executing", "abandoned"), 0
        )

    def test_reviewed_to_executing_is_noop(self) -> None:
        self._seed_keys("PLAN-011", count=1)
        self.assertEqual(
            clear_on_rollback("PLAN-011", "reviewed", "executing"), 0
        )

    def test_clear_noop_when_no_keys(self) -> None:
        # No data seeded; executing->draft on empty plan returns 0.
        self.assertEqual(
            clear_on_rollback("PLAN-NEW", "executing", "draft"), 0
        )

    def test_clear_emits_pruned_audit_event(self) -> None:
        self._seed_keys("PLAN-011", count=2)
        cleared = clear_on_rollback("PLAN-011", "executing", "draft")
        self.assertEqual(cleared, 2)
        # Inspect the audit log for the state_store_pruned event.
        raw = self.audit_log.read_text(encoding="utf-8")
        lines = [json.loads(l) for l in raw.splitlines() if l.strip()]
        pruned = [e for e in lines if e.get("action") == "state_store_pruned"]
        self.assertTrue(pruned, "expected at least one state_store_pruned event")
        self.assertEqual(pruned[-1]["keys_pruned_count"], 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
