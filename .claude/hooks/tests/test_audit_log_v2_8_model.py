"""PLAN-021 ADR-052 — audit_log v2.8 `model` field capture tests.

Verifies:
- `_extract_model` handles multiple response shapes (top-level, nested
  under `response`, nested under `usage_metadata`, missing, non-dict,
  non-string values).
- `build_entry` emits the new `model` field additively without
  breaking existing v2.7 keys.
- Null-safe for legacy / non-Anthropic emitters.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import audit_log  # noqa: E402


class ExtractModelTest(unittest.TestCase):

    def test_top_level_model_field(self):
        for model_id in (
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ):
            resp = {"model": model_id, "content": "x"}
            self.assertEqual(audit_log._extract_model(resp), model_id)

    def test_nested_under_response(self):
        resp = {"response": {"model": "claude-sonnet-4-6"}}
        self.assertEqual(
            audit_log._extract_model(resp), "claude-sonnet-4-6"
        )

    def test_nested_under_usage_metadata(self):
        resp = {"usage_metadata": {"model": "claude-haiku-4-5-20251001"}}
        self.assertEqual(
            audit_log._extract_model(resp),
            "claude-haiku-4-5-20251001",
        )

    def test_missing_model_returns_none(self):
        self.assertIsNone(audit_log._extract_model({"text": "hello"}))

    def test_non_dict_response_returns_none(self):
        for bad in (None, "string", 42, [1, 2], True):
            self.assertIsNone(audit_log._extract_model(bad))

    def test_empty_string_model_returns_none(self):
        self.assertIsNone(audit_log._extract_model({"model": ""}))

    def test_non_string_model_value_returns_none(self):
        for bad in (42, True, {"nested": "value"}, ["list"]):
            self.assertIsNone(audit_log._extract_model({"model": bad}))

    def test_top_level_wins_over_nested(self):
        # Defensive: if both are present, prefer top-level
        resp = {
            "model": "claude-opus-4-8",
            "response": {"model": "claude-sonnet-4-6"},
        }
        self.assertEqual(
            audit_log._extract_model(resp), "claude-opus-4-8"
        )


class BuildEntryV28ModelTest(unittest.TestCase):
    """Integration: build_entry() emits `model` field additively."""

    def _stub_event(self, model: str = "claude-sonnet-4-6"):
        class Event:
            pass
        ev = Event()
        ev.tool_name = "Agent"
        ev.session_id = "sess-plan021"
        ev.subagent_type = "qa-architect"
        ev.tool_response = {
            "model": model,
            "usage_metadata": {
                "cache_read_input_tokens": 500,
                "cache_creation_input_tokens": 100,
                "uncached_input_tokens": 100,
                "output_tokens": 200,
                "thinking_tokens": 50,
            },
        }
        ev.description = "qa review of changes"
        ev.prompt = (
            "## AGENT PROFILE\nName: QA\n\n"
            "## SKILL REFERENCE\n"
            "@.claude/skills/core/testing-strategy/SKILL.md "
            "sha256=" + "a" * 64
        )
        return ev

    def test_entry_has_model_key(self):
        entry = audit_log.build_entry(
            event=self._stub_event(),
            project_dir="/tmp/test",
            hook_duration_ms=5,
        )
        self.assertIsNotNone(entry)
        self.assertIn("model", entry)
        self.assertEqual(entry["model"], "claude-sonnet-4-6")

    def test_entry_preserves_all_v2_7_keys(self):
        entry = audit_log.build_entry(
            event=self._stub_event(),
            project_dir="/tmp/test",
            hook_duration_ms=5,
        )
        self.assertIsNotNone(entry)
        # PLAN-118 WS-E (S181): cache_coverage (float) → cache_coverage_bps (int).
        for v2_7_key in ("usage_metadata", "cache_coverage_bps", "rail"):
            self.assertIn(v2_7_key, entry)
        self.assertNotIn("cache_coverage", entry)

    def test_entry_with_missing_model_emits_null(self):
        class Event:
            pass
        ev = Event()
        ev.tool_name = "Agent"
        ev.session_id = "sess-legacy"
        ev.subagent_type = ""
        ev.tool_response = {"text": "legacy adapter no model"}
        ev.description = "legacy spawn"
        ev.prompt = "## SKILL CONTENT\n" + "x" * 300
        entry = audit_log.build_entry(
            event=ev,
            project_dir="/tmp/test",
            hook_duration_ms=5,
        )
        self.assertIsNotNone(entry)
        self.assertIsNone(entry["model"])

    def test_all_three_canonical_models_captured(self):
        for model_id in (
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ):
            entry = audit_log.build_entry(
                event=self._stub_event(model=model_id),
                project_dir="/tmp/test",
                hook_duration_ms=5,
            )
            self.assertEqual(entry["model"], model_id)


class NativeAgentModelFieldTest(unittest.TestCase):
    """PLAN-021 sanity: verify each canonical-5 agent has a model field."""

    _REPO_ROOT = Path(__file__).resolve().parents[3]
    # PLAN-134 W0 (ADR-149): VETO holders moved to the running generation
    # (variant A, ceremony e1189f81).
    _EXPECTED = {
        "code-reviewer": "claude-fable-5",
        "security-engineer": "claude-fable-5",
        "qa-architect": "claude-sonnet-4-6",
        "performance-engineer": "claude-sonnet-4-6",
        "devops": "claude-sonnet-4-6",
    }

    def test_all_5_canonical_agents_have_model_field(self):
        import re
        for slug, expected_model in self._EXPECTED.items():
            path = self._REPO_ROOT / ".claude" / "agents" / f"{slug}.md"
            self.assertTrue(path.is_file(), f"agent file missing: {slug}")
            text = path.read_text(encoding="utf-8")
            m = re.search(r"^model:\s*(\S+)", text, flags=re.MULTILINE)
            self.assertIsNotNone(m, f"no model: field in {slug}")
            self.assertEqual(
                m.group(1),
                expected_model,
                f"{slug} expected {expected_model}, got {m.group(1)}",
            )

    def test_model_is_canonical_claude_4_x_id(self):
        import re
        # ADR-149: claude-fable-5 joined the legal set (generation unlock).
        _VALID_IDS = {
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "claude-fable-5",
        }
        for slug in self._EXPECTED:
            path = self._REPO_ROOT / ".claude" / "agents" / f"{slug}.md"
            text = path.read_text(encoding="utf-8")
            m = re.search(r"^model:\s*(\S+)", text, flags=re.MULTILINE)
            self.assertIsNotNone(m)
            self.assertIn(m.group(1), _VALID_IDS)


if __name__ == "__main__":
    unittest.main()
