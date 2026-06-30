"""Tests for audit_emit.emit_veto_triggered v2.14 caller + session_id fields.

Closes audit-v2 P1 #6 (D track): forensic traceability for kernel override
events. Tests run against the post-ceremony state where emit_veto_triggered
accepts a `caller: str = ""` parameter.

Pre-ceremony: tests are SKIPPED via `_signature_supports_caller()` probe.
Post-ceremony: tests EXERCISE the new field.

Schema v2.14 contract:
- `caller` is optional (default empty string).
- When non-empty, the event dict carries a `caller` key.
- When empty, the key is OMITTED (not `"caller": ""`) so consumers can
  distinguish "caller not tracked" (old emitter) from "caller is ceo".
- `session_id` was already accepted but not documented; v2.14 promotes
  it to documented field.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _signature_supports_caller() -> bool:
    """Probe whether emit_veto_triggered accepts the new `caller` kwarg."""
    try:
        sig = inspect.signature(audit_emit.emit_veto_triggered)
        return "caller" in sig.parameters
    except (ValueError, TypeError):
        return False


_CALLER_FIELD_LANDED = _signature_supports_caller()


@unittest.skipUnless(_CALLER_FIELD_LANDED, "Schema v2.14 caller field not yet landed (pre-ceremony)")
class TestEmitVetoTriggeredV214(TestEnvContext):
    """Tests asserting v2.14 contract on emit_veto_triggered."""

    def _read_last_event(self) -> dict:
        """Read the most-recent event from the test audit log."""
        # TestEnvContext sets up CLAUDE_PROJECT_DIR + audit_dir; the emitter
        # writes to audit_dir/audit-log.jsonl by environment convention.
        audit_log = self.audit_dir / "audit-log.jsonl"
        self.assertTrue(audit_log.is_file(), f"audit log not at {audit_log}")
        lines = audit_log.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreater(len(lines), 0, "no events written")
        return json.loads(lines[-1])

    def test_caller_kwarg_accepted(self) -> None:
        """The function signature now accepts caller=str."""
        sig = inspect.signature(audit_emit.emit_veto_triggered)
        self.assertIn("caller", sig.parameters)
        param = sig.parameters["caller"]
        self.assertEqual(param.default, "")

    def test_caller_present_in_event_when_supplied(self) -> None:
        audit_emit.emit_veto_triggered(
            hook="check_arbitration_kernel",
            reason_code="kernel_override_used",
            reason_preview="kernel override on _lib/policy.py",
            blocked_tool="Edit",
            session_id="sess-test-001",
            caller="security-engineer",
        )
        event = self._read_last_event()
        self.assertEqual(event.get("caller"), "security-engineer")
        self.assertEqual(event.get("session_id"), "sess-test-001")
        self.assertEqual(event.get("reason_code"), "kernel_override_used")

    def test_caller_omitted_when_empty(self) -> None:
        """Empty caller → key absent (distinguishable from 'tracked but empty')."""
        audit_emit.emit_veto_triggered(
            hook="check_arbitration_kernel",
            reason_code="kernel_edit_blocked",
            reason_preview="blocked kernel edit on policy.yaml",
            blocked_tool="Write",
            caller="",
        )
        event = self._read_last_event()
        self.assertNotIn("caller", event)
        self.assertEqual(event.get("reason_code"), "kernel_edit_blocked")

    def test_caller_default_omits_key(self) -> None:
        """Not passing caller at all → key absent (backwards compat with pre-v2.14)."""
        audit_emit.emit_veto_triggered(
            hook="check_plan_edit",
            reason_code="transition_illegal",
            reason_preview="invalid transition draft → done",
            blocked_tool="Edit",
        )
        event = self._read_last_event()
        self.assertNotIn("caller", event)

    def test_session_id_documented_in_v214(self) -> None:
        """session_id is documented in v2.14; behaviorally already accepted."""
        sig = inspect.signature(audit_emit.emit_veto_triggered)
        self.assertIn("session_id", sig.parameters)

    def test_caller_string_preserved_unicode_safe(self) -> None:
        """Caller string with unicode is preserved (NFC normalization handled by emitter)."""
        audit_emit.emit_veto_triggered(
            hook="check_arbitration_kernel",
            reason_code="kernel_override_used",
            reason_preview="kernel edit on _lib/policy.py",
            blocked_tool="Edit",
            caller="agent-écu-naïve",
        )
        event = self._read_last_event()
        # Either preserved verbatim OR NFC-normalized — both acceptable.
        self.assertIn("caller", event)
        caller = event["caller"]
        self.assertTrue(
            caller in {"agent-écu-naïve", "agent-écu-naïve"},
            f"unexpected caller normalization: {caller!r}",
        )

    def test_caller_with_strike_count(self) -> None:
        """Caller field is independent of strike_count (both v2.14 + pre-v2.14 paths)."""
        audit_emit.emit_veto_triggered(
            hook="check_agent_spawn",
            reason_code="missing_skill_content",
            reason_preview="spawn missing SKILL CONTENT",
            blocked_tool="Task",
            strike_count=2,
            caller="ceo",
        )
        event = self._read_last_event()
        self.assertEqual(event.get("strike_count"), 2)
        self.assertEqual(event.get("caller"), "ceo")

    def test_caller_long_string_handled(self) -> None:
        """Caller longer than 200 chars: emitter does not truncate (preview field is the truncated one)."""
        long_caller = "a" * 300
        audit_emit.emit_veto_triggered(
            hook="check_arbitration_kernel",
            reason_code="kernel_override_used",
            reason_preview="kernel override",
            blocked_tool="Edit",
            caller=long_caller,
        )
        event = self._read_last_event()
        # Caller is preserved as-is (consumers can choose to truncate display).
        self.assertEqual(event.get("caller"), long_caller)


class TestEmitVetoTriggeredBackwardsCompat(TestEnvContext):
    """v2.14 must not regress old call sites — these tests run on every commit."""

    def _read_last_event(self) -> dict:
        audit_log = self.audit_dir / "audit-log.jsonl"
        if not audit_log.is_file():
            return {}
        lines = audit_log.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return {}
        return json.loads(lines[-1])

    def test_pre_v214_call_site_still_works(self) -> None:
        """The old 6-positional-arg call signature continues to function."""
        audit_emit.emit_veto_triggered(
            hook="check_plan_edit",
            reason_code="frontmatter_missing",
            reason_preview="plan frontmatter missing required fields",
            blocked_tool="Edit",
        )
        event = self._read_last_event()
        self.assertEqual(event.get("action"), "veto_triggered")
        self.assertEqual(event.get("hook"), "check_plan_edit")

    def test_old_consumers_unaffected_when_caller_absent(self) -> None:
        """Consumer parsing veto_triggered without expecting caller still works."""
        audit_emit.emit_veto_triggered(
            hook="check_bash_safety",
            reason_code="dangerous_command",
            reason_preview="rm -rf /",
            blocked_tool="Bash",
        )
        event = self._read_last_event()
        # All required v2.0 fields present:
        for required in (
            "action", "hook", "reason_code", "reason_preview",
            "blocked_tool", "event_schema", "ts",
        ):
            self.assertIn(required, event, f"missing required field: {required}")


if __name__ == "__main__":
    unittest.main()
