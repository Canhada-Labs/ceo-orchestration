"""Tests for check_arbitration_kernel._audit_block v2.14 caller + session_id.

Closes audit-v2 P1 #6 (D track): when the arbitration kernel emits a
kernel_override_used or kernel_edit_blocked event, it must include both
session_id and caller for forensic traceability.

Pre-ceremony: tests SKIPPED via signature probe.
Post-ceremony: tests EXERCISE the new env-resolved fields.

Caller resolution rule (kernel hook):
1. CLAUDE_AGENT_NAME — set on sub-agent process tree
2. CLAUDE_PARENT_AGENT — set on nested spawns
3. "ceo" — top-of-session default

Session_id: CLAUDE_SESSION_ID env var (always set by Claude Code runtime).
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


def _emit_veto_supports_caller() -> bool:
    try:
        sig = inspect.signature(audit_emit.emit_veto_triggered)
        return "caller" in sig.parameters
    except Exception:
        return False


def _audit_block_resolves_caller() -> bool:
    """Probe: does check_arbitration_kernel._audit_block read CLAUDE_AGENT_NAME?

    Source-level inspection — looks for the resolution pattern in the
    function body. Returns False pre-ceremony; True post-ceremony.
    """
    try:
        from check_arbitration_kernel import _audit_block
        src = inspect.getsource(_audit_block)
        return "CLAUDE_AGENT_NAME" in src
    except Exception:
        return False


_PATCH_LANDED = _emit_veto_supports_caller() and _audit_block_resolves_caller()


@unittest.skipUnless(_PATCH_LANDED, "Schema v2.14 patches not yet landed (pre-ceremony)")
class TestAuditBlockCallerResolution(TestEnvContext):
    """Tests asserting _audit_block forwards caller + session_id correctly."""

    def setUp(self) -> None:
        super().setUp()
        # Reload module so env-var changes take effect.
        from check_arbitration_kernel import _audit_block  # noqa: F401
        self._audit_block = _audit_block

    def _read_last_event(self) -> dict:
        audit_log = self.audit_dir / "audit-log.jsonl"
        self.assertTrue(audit_log.is_file(), f"audit log not at {audit_log}")
        lines = audit_log.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreater(len(lines), 0)
        return json.loads(lines[-1])

    def test_caller_falls_back_to_ceo_when_env_unset(self) -> None:
        # No CLAUDE_AGENT_NAME, no CLAUDE_PARENT_AGENT → "ceo"
        for var in ("CLAUDE_AGENT_NAME", "CLAUDE_PARENT_AGENT"):
            os.environ.pop(var, None)
        os.environ.update({"CLAUDE_SESSION_ID": "sess-fallback"})
        self._audit_block(rel=".claude/hooks/_lib/policy.py", override_used=True)
        event = self._read_last_event()
        self.assertEqual(event.get("caller"), "ceo")
        self.assertEqual(event.get("session_id"), "sess-fallback")

    def test_caller_uses_claude_agent_name_when_set(self) -> None:
        os.environ.update({
            "CLAUDE_AGENT_NAME": "security-engineer",
            "CLAUDE_SESSION_ID": "sess-spawn-007",
        })
        self._audit_block(rel=".claude/hooks/_lib/audit_emit.py", override_used=True)
        event = self._read_last_event()
        self.assertEqual(event.get("caller"), "security-engineer")
        self.assertEqual(event.get("session_id"), "sess-spawn-007")

    def test_caller_falls_back_to_parent_when_agent_name_empty(self) -> None:
        os.environ.pop("CLAUDE_AGENT_NAME", None)
        os.environ.update({
            "CLAUDE_PARENT_AGENT": "code-reviewer",
            "CLAUDE_SESSION_ID": "sess-nested-001",
        })
        self._audit_block(rel=".claude/policies/main.yaml", override_used=False)
        event = self._read_last_event()
        self.assertEqual(event.get("caller"), "code-reviewer")
        self.assertEqual(event.get("reason_code"), "kernel_edit_blocked")

    def test_session_id_empty_when_env_unset(self) -> None:
        for var in ("CLAUDE_SESSION_ID", "CLAUDE_AGENT_NAME", "CLAUDE_PARENT_AGENT"):
            os.environ.pop(var, None)
        self._audit_block(rel=".claude/hooks/policy_dispatch.py", override_used=False)
        event = self._read_last_event()
        # session_id present (default "") + caller = "ceo"
        self.assertEqual(event.get("session_id"), "")
        self.assertEqual(event.get("caller"), "ceo")

    def test_caller_strip_whitespace(self) -> None:
        # Tab + newline padding — emitter / hook normalizes to stripped form.
        os.environ.update({
            "CLAUDE_AGENT_NAME": "  qa-architect\t\n",
            "CLAUDE_SESSION_ID": "sess-trim",
        })
        self._audit_block(rel=".claude/hooks/check_canonical_edit.py", override_used=True)
        event = self._read_last_event()
        self.assertEqual(event.get("caller"), "qa-architect")


@unittest.skipUnless(_PATCH_LANDED, "Schema v2.14 patches not yet landed (pre-ceremony)")
class TestAuditBlockNeverRaises(TestEnvContext):
    """The _audit_block contract is best-effort; must not raise on any path."""

    def setUp(self) -> None:
        super().setUp()
        from check_arbitration_kernel import _audit_block
        self._audit_block = _audit_block

    def test_does_not_raise_on_missing_audit_emit(self) -> None:
        # Even if audit_emit import fails, the function returns silently.
        with mock.patch.dict(sys.modules, {"_lib": None, "_lib.audit_emit": None}):
            try:
                self._audit_block(rel="x.py", override_used=False)
            except Exception as e:
                self.fail(f"_audit_block raised: {e!r}")

    def test_does_not_raise_on_audit_emit_emit_failing(self) -> None:
        with mock.patch.object(
            audit_emit, "emit_veto_triggered", side_effect=RuntimeError("boom")
        ):
            try:
                self._audit_block(rel="y.py", override_used=True)
            except Exception as e:
                self.fail(f"_audit_block raised on emit failure: {e!r}")


if __name__ == "__main__":
    unittest.main()
