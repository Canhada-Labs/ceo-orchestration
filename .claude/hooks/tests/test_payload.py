"""Tests for _lib.payload — stdin JSON parsing."""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Make `.claude/hooks/` importable so `from _lib import ...` works
# regardless of how the test is invoked.

from _lib import payload  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestPayloadParsing(TestEnvContext):
    def test_parse_valid_preuse_agent_payload(self):
        raw = (
            '{"session_id":"sess-1","tool_name":"Agent",'
            '"tool_input":{"description":"Review auth","prompt":"## AGENT PROFILE\\n..."}}'
        )
        p = payload.parse_text(raw)
        self.assertIsNone(p.raw_error)
        self.assertEqual(p.session_id, "sess-1")
        self.assertEqual(p.tool_name, "Agent")
        self.assertEqual(p.description, "Review auth")
        self.assertIn("## AGENT PROFILE", p.prompt)

    def test_parse_valid_postuse_payload_with_tool_response(self):
        raw = (
            '{"session_id":"s","tool_name":"Agent",'
            '"tool_input":{"description":"d","prompt":"p"},'
            '"tool_response":{"type":"summary","content":"ok"}}'
        )
        p = payload.parse_text(raw)
        self.assertIsNone(p.raw_error)
        self.assertEqual(payload.response_kind(p.tool_response), "summary")

    def test_parse_empty_stdin(self):
        p = payload.parse_text("")
        self.assertIsNone(p.raw_error)
        self.assertEqual(p.description, "")
        self.assertEqual(p.tool_name, "")

    def test_parse_malformed_json_sets_raw_error(self):
        p = payload.parse_text("{not: valid}")
        self.assertIsNotNone(p.raw_error)
        self.assertIn("JSON parse error", p.raw_error)
        self.assertEqual(p.description, "")  # fail-open defaults

    def test_parse_json_array_is_error(self):
        p = payload.parse_text("[1,2,3]")
        self.assertIsNotNone(p.raw_error)
        self.assertIn("must be a JSON object", p.raw_error)

    def test_missing_tool_input_defaults_to_empty(self):
        raw = '{"session_id":"s","tool_name":"Agent"}'
        p = payload.parse_text(raw)
        self.assertIsNone(p.raw_error)
        self.assertEqual(p.description, "")
        self.assertEqual(p.subagent_type, "")

    def test_parse_stdin_stream_argument(self):
        stream = io.StringIO(
            '{"session_id":"x","tool_name":"Agent",'
            '"tool_input":{"description":"d","prompt":"p"}}'
        )
        p = payload.parse_stdin(stream)
        self.assertIsNone(p.raw_error)
        self.assertEqual(p.session_id, "x")


class TestResponseKind(TestEnvContext):
    def test_none_response_is_absent(self):
        self.assertEqual(payload.response_kind(None), "absent")

    def test_string_response(self):
        self.assertEqual(payload.response_kind("hello"), "string")

    def test_object_without_type_is_object(self):
        self.assertEqual(payload.response_kind({"content": "x"}), "object")

    def test_object_with_type_uses_type(self):
        self.assertEqual(
            payload.response_kind({"type": "error", "msg": "bad"}), "error"
        )

    def test_list_response_is_type_name(self):
        self.assertEqual(payload.response_kind([1, 2, 3]), "list")
