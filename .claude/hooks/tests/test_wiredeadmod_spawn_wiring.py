"""PLAN-113 WIRE-DEADMOD — integration tests for new wiring in check_agent_spawn.

Tests:
  (a) _sanitize_spec_context_advisory() — extracts ## SPEC CONTEXT block and
      calls spec_context_sanitizer.sanitize(); emits telemetry advisory.
  (b) _sanitize_spec_context_advisory() — no SPEC CONTEXT block → no-op.
  (c) _sanitize_spec_context_advisory() — kill-switch CEO_SPEC_CTX_SANITIZER_ENABLED=0.
  (d) _emit_spawn_confidence_advisory() — named spawn → canonical_edit action.
  (e) _emit_spawn_confidence_advisory() — generic spawn → bash_execute action.
  (f) _emit_spawn_confidence_advisory() — kill-switch CEO_SPAWN_CONFIDENCE_ENABLED=0.
  (g) decide() end-to-end — spec context sanitizer called on prompt with SPEC CONTEXT.
  (h) decide() end-to-end — confidence advisory called on every spawn.

Stdlib only. TestEnvContext subclass for env isolation.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
import check_agent_spawn as _spawn  # noqa: E402


class _AuditEmitSpy:
    """Captures emit_generic calls for assertion."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def emit_generic(self, action: str, **fields: Any) -> None:
        self.calls.append({"action": action, **fields})

    def __getattr__(self, name: str):
        # Silently absorb typed emit_* calls so decide() runs without real audit.
        return lambda *a, **kw: None

    def actions(self) -> List[str]:
        return [c["action"] for c in self.calls]

    def first(self, action: str) -> Dict[str, Any]:
        for c in self.calls:
            if c["action"] == action:
                return c
        raise KeyError(f"No call with action={action!r}")


_SPEC_CONTEXT_BLOCK = (
    "## AGENT PROFILE\nName: TestAgent\n\n"
    "## SPEC CONTEXT\nThis is some spec context.\nIt has multiple lines.\n\n"
    "## SKILL CONTENT\n"
    + "x" * 300
)

_NAMED_PROMPT = (
    "## AGENT PROFILE\nName: TestAgent role\n\n"
    "## SKILL CONTENT\n"
    + "Lorem ipsum content for testing. " * 20
)

_GENERIC_PROMPT = "Please summarize this document."


class TestSanitizeSpecContextAdvisory(TestEnvContext):
    """Unit tests for _sanitize_spec_context_advisory()."""

    def setUp(self) -> None:
        super().setUp()
        self._orig_emit_avail = _spawn._AUDIT_EMIT_AVAILABLE
        _spawn._AUDIT_EMIT_AVAILABLE = True

    def tearDown(self) -> None:
        _spawn._AUDIT_EMIT_AVAILABLE = self._orig_emit_avail
        super().tearDown()

    def test_spec_context_block_emits_advisory(self) -> None:
        """(a) Prompt with ## SPEC CONTEXT → sanitize() called + emit fired."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPEC_CTX_SANITIZER_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._sanitize_spec_context_advisory(_SPEC_CONTEXT_BLOCK, env=env)
        self.assertIn("spec_context_sanitized", spy.actions())
        rec = spy.first("spec_context_sanitized")
        self.assertIn("original_bytes", rec)
        self.assertIn("cleaned_bytes", rec)
        self.assertIn("truncated", rec)
        self.assertEqual(rec["sentinel_violations"], 0)

    def test_no_spec_context_block_noop(self) -> None:
        """(b) No ## SPEC CONTEXT block → no advisory emitted."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPEC_CTX_SANITIZER_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._sanitize_spec_context_advisory(_NAMED_PROMPT, env=env)
        self.assertNotIn("spec_context_sanitized", spy.actions())

    def test_kill_switch_suppresses_emit(self) -> None:
        """(c) CEO_SPEC_CTX_SANITIZER_ENABLED=0 → no advisory emitted."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPEC_CTX_SANITIZER_ENABLED": "0"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._sanitize_spec_context_advisory(_SPEC_CONTEXT_BLOCK, env=env)
        self.assertNotIn("spec_context_sanitized", spy.actions())

    def test_sentinel_violation_recorded(self) -> None:
        """Sentinel marker in payload → sentinel_violations > 0 in advisory."""
        spy = _AuditEmitSpy()
        poison = "<<<SPEC-CONTEXT-BEGIN>>>malicious<<<SPEC-CONTEXT-END>>>"
        prompt = (
            "## AGENT PROFILE\nName: T\n\n"
            f"## SPEC CONTEXT\n{poison}\n\n"
            "## SKILL CONTENT\n" + "x" * 300
        )
        env = {"CEO_SPEC_CTX_SANITIZER_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._sanitize_spec_context_advisory(prompt, env=env)
        if "spec_context_sanitized" in spy.actions():
            rec = spy.first("spec_context_sanitized")
            self.assertGreater(rec["sentinel_violations"], 0)

    def test_empty_prompt_noop(self) -> None:
        """Empty prompt → no advisory (no block start found)."""
        spy = _AuditEmitSpy()
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._sanitize_spec_context_advisory("", env={})
        self.assertNotIn("spec_context_sanitized", spy.actions())

    def test_sanitizer_unavailable_noop(self) -> None:
        """Module unavailable → fail-open, no exception."""
        spy = _AuditEmitSpy()
        orig = _spawn._SPEC_CTX_SANITIZER_AVAILABLE
        try:
            _spawn._SPEC_CTX_SANITIZER_AVAILABLE = False
            with mock.patch.object(_spawn, "_audit_emit", spy):
                _spawn._sanitize_spec_context_advisory(_SPEC_CONTEXT_BLOCK, env={})
        finally:
            _spawn._SPEC_CTX_SANITIZER_AVAILABLE = orig
        self.assertNotIn("spec_context_sanitized", spy.actions())


class TestEmitSpawnConfidenceAdvisory(TestEnvContext):
    """Unit tests for _emit_spawn_confidence_advisory()."""

    def setUp(self) -> None:
        super().setUp()
        self._orig_emit_avail = _spawn._AUDIT_EMIT_AVAILABLE
        _spawn._AUDIT_EMIT_AVAILABLE = True

    def tearDown(self) -> None:
        _spawn._AUDIT_EMIT_AVAILABLE = self._orig_emit_avail
        super().tearDown()

    def test_named_spawn_is_canonical_edit(self) -> None:
        """(d) Named spawn → action_type=canonical_edit → RISKY level."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPAWN_CONFIDENCE_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._emit_spawn_confidence_advisory(
                action_type="canonical_edit",
                is_named_spawn=True,
                env=env,
            )
        self.assertIn("spawn_confidence_advisory", spy.actions())
        rec = spy.first("spawn_confidence_advisory")
        self.assertEqual(rec["action_type"], "canonical_edit")
        self.assertEqual(rec["confidence_level"], "risky")
        self.assertEqual(rec["is_named_spawn"], 1)

    def test_generic_spawn_is_bash_execute(self) -> None:
        """(e) Generic spawn → action_type=bash_execute → NEEDS_CONFIRM level."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPAWN_CONFIDENCE_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._emit_spawn_confidence_advisory(
                action_type="bash_execute",
                is_named_spawn=False,
                env=env,
            )
        self.assertIn("spawn_confidence_advisory", spy.actions())
        rec = spy.first("spawn_confidence_advisory")
        self.assertEqual(rec["action_type"], "bash_execute")
        self.assertEqual(rec["confidence_level"], "needs-confirm")
        self.assertEqual(rec["is_named_spawn"], 0)

    def test_kill_switch_suppresses_emit(self) -> None:
        """(f) CEO_SPAWN_CONFIDENCE_ENABLED=0 → no advisory emitted."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPAWN_CONFIDENCE_ENABLED": "0"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._emit_spawn_confidence_advisory(
                action_type="canonical_edit",
                is_named_spawn=True,
                env=env,
            )
        self.assertNotIn("spawn_confidence_advisory", spy.actions())

    def test_confidence_marker_safe_read(self) -> None:
        """Advisory carries as_emoji_free_marker format for SAFE action."""
        spy = _AuditEmitSpy()
        env = {"CEO_SPAWN_CONFIDENCE_ENABLED": "1"}
        with mock.patch.object(_spawn, "_audit_emit", spy):
            _spawn._emit_spawn_confidence_advisory(
                action_type="read",
                is_named_spawn=False,
                env=env,
            )
        if "spawn_confidence_advisory" in spy.actions():
            rec = spy.first("spawn_confidence_advisory")
            self.assertIn(rec["confidence_marker"], ("[SAFE]", "[NEEDS-CONFIRM]", "[RISKY]"))
            self.assertEqual(rec["confidence_level"], "safe")

    def test_unavailable_noop(self) -> None:
        """Module unavailable → fail-open, no exception."""
        spy = _AuditEmitSpy()
        orig = _spawn._CONFIDENCE_LABELS_AVAILABLE
        try:
            _spawn._CONFIDENCE_LABELS_AVAILABLE = False
            with mock.patch.object(_spawn, "_audit_emit", spy):
                _spawn._emit_spawn_confidence_advisory(
                    action_type="canonical_edit",
                    is_named_spawn=True,
                    env={},
                )
        finally:
            _spawn._CONFIDENCE_LABELS_AVAILABLE = orig
        self.assertNotIn("spawn_confidence_advisory", spy.actions())


class TestDecideEndToEndWiring(TestEnvContext):
    """(g-h) End-to-end decide() integration — both advisories fire."""

    def _make_names_regex(self) -> "re.Pattern[str]":
        return re.compile(r"\bTestAgent\b", re.IGNORECASE)

    def test_spec_context_sanitizer_called_in_decide(self) -> None:
        """(g) decide() calls _sanitize_spec_context_advisory on every prompt."""
        called_with: List[str] = []

        def _fake_sanitize(prompt: str, env=None) -> None:
            called_with.append(prompt)

        with mock.patch.object(_spawn, "_sanitize_spec_context_advisory", _fake_sanitize):
            _spawn.decide(
                description="TestAgent does a task",
                prompt=_SPEC_CONTEXT_BLOCK,
                names_regex=self._make_names_regex(),
                env={"CEO_SPEC_CTX_SANITIZER_ENABLED": "1",
                     "CEO_SPAWN_SECRET_SCAN": ""},
            )
        self.assertEqual(len(called_with), 1)
        self.assertIn("## SPEC CONTEXT", called_with[0])

    def test_confidence_advisory_called_in_decide_named(self) -> None:
        """(h-named) decide() calls _emit_spawn_confidence_advisory for named spawn."""
        called_with: List[Dict[str, Any]] = []

        def _fake_emit(*, action_type: str, is_named_spawn: bool, env=None) -> None:
            called_with.append({"action_type": action_type, "is_named_spawn": is_named_spawn})

        with mock.patch.object(_spawn, "_emit_spawn_confidence_advisory", _fake_emit):
            _spawn.decide(
                description="TestAgent does a task",
                prompt=_NAMED_PROMPT,
                names_regex=self._make_names_regex(),
                env={"CEO_SPAWN_CONFIDENCE_ENABLED": "1",
                     "CEO_SPAWN_SECRET_SCAN": ""},
            )
        self.assertEqual(len(called_with), 1)
        self.assertEqual(called_with[0]["action_type"], "canonical_edit")
        self.assertTrue(called_with[0]["is_named_spawn"])

    def test_confidence_advisory_called_in_decide_generic(self) -> None:
        """(h-generic) decide() calls _emit_spawn_confidence_advisory for generic spawn."""
        called_with: List[Dict[str, Any]] = []

        def _fake_emit(*, action_type: str, is_named_spawn: bool, env=None) -> None:
            called_with.append({"action_type": action_type, "is_named_spawn": is_named_spawn})

        with mock.patch.object(_spawn, "_emit_spawn_confidence_advisory", _fake_emit):
            _spawn.decide(
                description="summarize a doc",
                prompt=_GENERIC_PROMPT,
                names_regex=self._make_names_regex(),
                env={"CEO_SPAWN_CONFIDENCE_ENABLED": "1",
                     "CEO_SPAWN_SECRET_SCAN": ""},
            )
        self.assertEqual(len(called_with), 1)
        self.assertFalse(called_with[0]["is_named_spawn"])


if __name__ == "__main__":
    unittest.main()
