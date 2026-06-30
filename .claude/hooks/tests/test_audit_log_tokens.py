"""Tests for tokens wiring in audit_log.py (Phase 5b / ADR-016)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


import audit_log as _audit_log  # noqa: E402
from _lib import contract  # noqa: E402


def _build(tool_response):
    """Helper: construct a NormalizedEvent + invoke build_entry."""
    event = contract.NormalizedEvent(
        session_id="s1",
        phase="PostToolUse",
        tool_name="Agent",
        subagent_type="general-purpose",
        description="Test spawn",
        prompt="## AGENT PROFILE\n## SKILL CONTENT\nSKILL: architecture-decisions\n",
        tool_response=tool_response,
    )
    return _audit_log.build_entry(
        event=event, project_dir="/tmp/proj", hook_duration_ms=42
    )


class TestTokensInEntry(unittest.TestCase):
    def test_claude_shape_extracts_tokens(self):
        entry = _build({"usage": {"input_tokens": 100, "output_tokens": 200}})
        self.assertEqual(entry["tokens_in"], 100)
        self.assertEqual(entry["tokens_out"], 200)
        self.assertEqual(entry["tokens_total"], 300)

    def test_gemini_shape_extracts_tokens(self):
        entry = _build({"usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 75}})
        self.assertEqual(entry["tokens_in"], 50)
        self.assertEqual(entry["tokens_out"], 75)
        self.assertEqual(entry["tokens_total"], 125)

    def test_unknown_shape_emits_null_keys(self):
        entry = _build({"weird_field": 999})
        # Keys MUST be present (ADR-016 §Emitter contract)
        self.assertIn("tokens_in", entry)
        self.assertIn("tokens_out", entry)
        self.assertIn("tokens_total", entry)
        # Values MUST be None
        self.assertIsNone(entry["tokens_in"])
        self.assertIsNone(entry["tokens_out"])
        self.assertIsNone(entry["tokens_total"])

    def test_empty_response_emits_null_keys(self):
        entry = _build({})
        self.assertIn("tokens_in", entry)
        self.assertIsNone(entry["tokens_in"])
        self.assertIsNone(entry["tokens_out"])

    def test_totalTokens_legacy_populates_out_only(self):
        entry = _build({"totalTokens": 777})
        self.assertIsNone(entry["tokens_in"])
        self.assertEqual(entry["tokens_out"], 777)
        self.assertEqual(entry["tokens_total"], 777)

    def test_malformed_tokens_emit_null(self):
        entry = _build({"usage": {"input_tokens": -1, "output_tokens": "bogus"}})
        self.assertIsNone(entry["tokens_in"])
        self.assertIsNone(entry["tokens_out"])

    def test_null_tool_response_emits_null_keys(self):
        event = contract.NormalizedEvent(
            session_id="s2",
            phase="PostToolUse",
            tool_name="Agent",
            tool_response={},
        )
        entry = _audit_log.build_entry(
            event=event, project_dir="/tmp", hook_duration_ms=1
        )
        self.assertIsNone(entry["tokens_in"])
        self.assertIsNone(entry["tokens_out"])

    def test_partial_tokens_sum_is_output(self):
        entry = _build({"usage": {"output_tokens": 42}})
        self.assertIsNone(entry["tokens_in"])
        self.assertEqual(entry["tokens_out"], 42)
        self.assertEqual(entry["tokens_total"], 42)


if __name__ == "__main__":
    unittest.main()
