"""Unit tests for _lib/contract.py + _lib/adapters/claude.py.

Behavior-identical wrappers of payload parsing — tests lock the
contract so future refactors of decide() functions stay equivalent.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path


from _lib import contract  # noqa: E402
from _lib.adapters import claude as claude_adapter  # noqa: E402


class TestNormalizedEvent(unittest.TestCase):
    def test_defaults(self):
        e = contract.NormalizedEvent()
        self.assertEqual(e.session_id, "")
        self.assertEqual(e.tool_name, "")
        self.assertEqual(e.tool_input, {})
        self.assertEqual(e.tool_response, {})
        self.assertFalse(e.replace_all)
        self.assertIsNone(e.parse_error)

    def test_phase_accessors(self):
        self.assertTrue(contract.NormalizedEvent(phase="PreToolUse").is_pretooluse())
        self.assertFalse(contract.NormalizedEvent(phase="PreToolUse").is_posttooluse())
        self.assertTrue(contract.NormalizedEvent(phase="PostToolUse").is_posttooluse())


class TestDecisionBuilders(unittest.TestCase):
    def test_allow(self):
        d = contract.allow()
        self.assertTrue(d.allow)
        self.assertIsNone(d.reason)

    def test_block_requires_reason(self):
        d = contract.block("missing skill content")
        self.assertFalse(d.allow)
        self.assertEqual(d.reason, "missing skill content")

    def test_with_reason_flips_allow(self):
        d = contract.allow().with_reason("nope")
        self.assertFalse(d.allow)
        self.assertEqual(d.reason, "nope")

    def test_as_allow_drops_reason(self):
        d = contract.block("nope").as_allow()
        self.assertTrue(d.allow)
        self.assertIsNone(d.reason)


class TestClaudeAdapterRead(unittest.TestCase):
    def _make_stdin(self, payload: dict) -> io.StringIO:
        return io.StringIO(json.dumps(payload))

    def test_agent_spawn_payload(self):
        stdin = self._make_stdin({
            "session_id": "sess-42",
            "tool_name": "Agent",
            "tool_input": {
                "description": "Spawn VP Engineering",
                "prompt": "## AGENT PROFILE\n## SKILL CONTENT\nfoo",
                "subagent_type": "general-purpose",
            },
        })
        event = claude_adapter.read_event(stdin)
        self.assertEqual(event.session_id, "sess-42")
        self.assertEqual(event.tool_name, "Agent")
        self.assertEqual(event.description, "Spawn VP Engineering")
        self.assertIn("## SKILL CONTENT", event.prompt)
        self.assertEqual(event.subagent_type, "general-purpose")
        self.assertIsNone(event.parse_error)

    def test_edit_payload(self):
        stdin = self._make_stdin({
            "session_id": "s1",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": ".claude/plans/PLAN-004-foo.md",
                "old_string": "draft",
                "new_string": "reviewed",
                "replace_all": False,
            },
        })
        event = claude_adapter.read_event(stdin)
        self.assertEqual(event.file_path, ".claude/plans/PLAN-004-foo.md")
        self.assertEqual(event.old_string, "draft")
        self.assertEqual(event.new_string, "reviewed")
        self.assertFalse(event.replace_all)

    def test_bash_payload(self):
        stdin = self._make_stdin({
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la", "description": "List files"},
        })
        event = claude_adapter.read_event(stdin)
        self.assertEqual(event.command, "ls -la")
        self.assertEqual(event.tool_name, "Bash")

    def test_malformed_stdin_sets_parse_error(self):
        stdin = io.StringIO("not json")
        event = claude_adapter.read_event(stdin)
        self.assertIsNotNone(event.parse_error)
        self.assertEqual(event.tool_name, "")

    def test_empty_stdin_returns_empty_event(self):
        """Empty stdin isn't malformed — it's treated as empty payload."""
        stdin = io.StringIO("")
        event = claude_adapter.read_event(stdin)
        # Either parse_error or empty fields — key invariant: no crash
        self.assertEqual(event.tool_name, "")
        self.assertEqual(event.tool_input, {})


class TestClaudeAdapterWrite(unittest.TestCase):
    def _parse(self, out: str) -> dict:
        return json.loads(out)

    def test_allow_simple(self):
        # Schema-compliant allow: Claude Code hook schema rejects top-level
        # {"decision":"allow"} (enum is "approve"|"block"). Adapter emits {}.
        out = claude_adapter.write_decision(contract.allow())
        self.assertEqual(self._parse(out), {})

    def test_block_with_reason(self):
        out = claude_adapter.write_decision(contract.block("must have skill content"))
        d = self._parse(out)
        self.assertEqual(d["decision"], "block")
        self.assertEqual(d["reason"], "must have skill content")

    def test_allow_with_system_message(self):
        dec = contract.Decision(allow=True, system_message="POST-AGENT: check diff")
        d = self._parse(claude_adapter.write_decision(dec))
        self.assertEqual(d.get("decision", "allow"), "allow")
        self.assertEqual(d["systemMessage"], "POST-AGENT: check diff")

    def test_block_without_reason_still_valid(self):
        dec = contract.Decision(allow=False, reason=None)
        d = self._parse(claude_adapter.write_decision(dec))
        self.assertEqual(d["decision"], "block")
        self.assertNotIn("reason", d)

    def test_single_line_output(self):
        out = claude_adapter.write_decision(contract.block("x"))
        self.assertEqual(out.count("\n"), 0)

    def test_ensure_ascii_false_preserves_unicode(self):
        dec = contract.block("razão: política de governança 🛡")
        out = claude_adapter.write_decision(dec)
        # Should NOT be ASCII-escaped
        self.assertIn("razão", out)

    def test_emit_decision_adds_newline(self):
        stream = io.StringIO()
        claude_adapter.emit_decision(contract.allow(), stream=stream)
        self.assertTrue(stream.getvalue().endswith("\n"))


class TestRoundTrip(unittest.TestCase):
    """Reading a payload then writing a decision doesn't corrupt state."""

    def test_read_then_allow_write(self):
        stdin = io.StringIO(json.dumps({"tool_name": "Agent", "tool_input": {}}))
        event = claude_adapter.read_event(stdin)
        self.assertEqual(event.tool_name, "Agent")
        # Schema-compliant allow: adapter emits {} (no "decision" field).
        out = claude_adapter.write_decision(contract.allow())
        self.assertEqual(json.loads(out), {})


class TestKnownAdapters(unittest.TestCase):
    def test_claude_is_default(self):
        self.assertEqual(contract.DEFAULT_ADAPTER, "claude")

    def test_known_adapters_includes_claude(self):
        self.assertIn("claude", contract.KNOWN_ADAPTERS)


class TestPhaseParameter(unittest.TestCase):
    """PLAN-006 Phase 1 pre-work (ADR-014, R-SB1)."""

    def _make_stdin(self, payload: dict) -> io.StringIO:
        return io.StringIO(json.dumps(payload))

    def test_read_event_default_phase_is_pretooluse(self):
        stdin = self._make_stdin({"tool_name": "Bash"})
        event = claude_adapter.read_event(stdin)
        self.assertEqual(event.phase, "PreToolUse")
        self.assertTrue(event.is_pretooluse())

    def test_read_event_explicit_pretooluse(self):
        stdin = self._make_stdin({"tool_name": "Bash"})
        event = claude_adapter.read_event(stdin, phase="PreToolUse")
        self.assertEqual(event.phase, "PreToolUse")

    def test_read_event_explicit_posttooluse(self):
        stdin = self._make_stdin({"tool_name": "Task", "tool_response": {"ok": True}})
        event = claude_adapter.read_event(stdin, phase="PostToolUse")
        self.assertEqual(event.phase, "PostToolUse")
        self.assertTrue(event.is_posttooluse())

    def test_read_event_unknown_phase_fails_open_to_pretooluse(self):
        stdin = self._make_stdin({"tool_name": "Bash"})
        event = claude_adapter.read_event(stdin, phase="BogusPhase")
        self.assertEqual(event.phase, "PreToolUse")

    def test_read_post_event_convenience(self):
        stdin = self._make_stdin({"tool_name": "Task", "tool_response": {"ok": True}})
        event = claude_adapter.read_post_event(stdin)
        self.assertEqual(event.phase, "PostToolUse")
        self.assertTrue(event.is_posttooluse())

    def test_phase_preserved_on_parse_error(self):
        """Malformed stdin at PostToolUse must still report PostToolUse phase."""
        stdin = io.StringIO("not json")
        event = claude_adapter.read_event(stdin, phase="PostToolUse")
        self.assertIsNotNone(event.parse_error)
        self.assertEqual(event.phase, "PostToolUse")

    def test_post_event_preserves_tool_response(self):
        stdin = self._make_stdin({
            "tool_name": "Task",
            "tool_response": {"totalTokens": 500, "usage": {"input_tokens": 300}},
        })
        event = claude_adapter.read_post_event(stdin)
        self.assertEqual(event.tool_response.get("totalTokens"), 500)
        self.assertEqual(event.tool_response["usage"]["input_tokens"], 300)


if __name__ == "__main__":
    unittest.main()
