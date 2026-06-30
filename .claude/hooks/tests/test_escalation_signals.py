"""Tests for `_lib/escalation_signals.py` — PLAN-048 detector library.

Mirrors the 6-detector contract from `ceo-escalation-detector.py`,
this time exercising the in-package `_lib.escalation_signals` module
(canonical-promoted at PLAN-048 Phase 2). Each detector gets:

- One positive case (signal fires)
- One negative case (signal stays silent)
- One edge case (empty / malformed input)

Plus DETECTORS-tuple sanity to guard against accidental drop.

Stdlib only. No real audit-log read; all events are inline dicts.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))

from _lib import escalation_signals as es  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _evt(action: str, **kwargs: Any) -> Dict[str, Any]:
    """Build a minimal audit-log event."""
    base: Dict[str, Any] = {"action": action}
    if "ts" not in kwargs:
        base["ts"] = "2026-04-27T10:00:00Z"
    base.update(kwargs)
    return base


class TestDetectGateSkip(TestEnvContext):
    def test_fires_when_work_event_first_with_no_gate_read(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="code-reviewer"),
            _evt("plan_transition", plan_id="PLAN-099"),
        ]
        signals = es.detect_gate_skip(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "gate_skip")
        self.assertEqual(signals[0]["severity"], "high")
        self.assertEqual(signals[0]["ts"], "2026-04-27T10:00:00Z")

    def test_silent_when_gate_read_present(self) -> None:
        events = [
            _evt("file_read", files_read=["CLAUDE.md"]),
            _evt("file_read", files_read=["PROTOCOL.md"]),
            _evt("agent_spawn", subagent_type="code-reviewer"),
        ]
        signals = es.detect_gate_skip(events)
        self.assertEqual(signals, [])

    def test_gate_read_via_string_files_hint(self) -> None:
        events = [
            _evt("file_read", read_paths="CLAUDE.md"),
            _evt("agent_spawn", subagent_type="code-reviewer"),
        ]
        self.assertEqual(es.detect_gate_skip(events), [])

    def test_silent_when_no_work_event(self) -> None:
        events = [
            _evt("file_read"),
            _evt("session_start"),
        ]
        self.assertEqual(es.detect_gate_skip(events), [])

    def test_empty_events_returns_empty(self) -> None:
        self.assertEqual(es.detect_gate_skip([]), [])

    def test_canonical_edit_blocked_counts_as_work_trigger(self) -> None:
        events = [
            _evt("canonical_edit_blocked"),
        ]
        signals = es.detect_gate_skip(events)
        self.assertEqual(len(signals), 1)


class TestDetectCanonicalEditBlock(TestEnvContext):
    def test_fires_on_action_canonical_edit_blocked(self) -> None:
        events = [
            _evt("canonical_edit_blocked", path=".claude/hooks/check_x.py"),
        ]
        signals = es.detect_canonical_edit_block(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "canonical_edit_block")
        self.assertEqual(signals[0]["details"]["path"],
                         ".claude/hooks/check_x.py")

    def test_fires_on_response_kind_block(self) -> None:
        events = [
            _evt("hook_response", response_kind="block_canonical_edit",
                 tool_file_path="src/foo.py"),
        ]
        signals = es.detect_canonical_edit_block(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["details"]["path"], "src/foo.py")

    def test_silent_on_unrelated_actions(self) -> None:
        events = [
            _evt("agent_spawn"),
            _evt("plan_transition"),
        ]
        self.assertEqual(es.detect_canonical_edit_block(events), [])


class TestDetectDebateSkipL3(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.td = Path(tempfile.mkdtemp(prefix="ceo-esc-"))

    def _write_plan(self, plan_id: str, level: str) -> None:
        p = self.td / f"{plan_id}-test.md"
        p.write_text(
            f"---\nstatus: draft\nlevel: {level}\n---\n# Plan\n",
            encoding="utf-8",
        )

    def test_fires_when_l3_executes_without_debate(self) -> None:
        self._write_plan("PLAN-101", "L3")
        events = [
            _evt("agent_spawn", plan_id="PLAN-101", ts="2026-04-27T10:00:00Z"),
        ]
        signals = es.detect_debate_skip_l3(events, plans_dir=self.td)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "debate_skip_l3")
        self.assertEqual(signals[0]["details"]["plan_id"], "PLAN-101")
        self.assertEqual(signals[0]["details"]["level"], "L3")

    def test_silent_when_debate_precedes_exec(self) -> None:
        self._write_plan("PLAN-102", "L3")
        events = [
            _evt("debate_event", plan_id="PLAN-102", ts="2026-04-27T09:00:00Z"),
            _evt("agent_spawn", plan_id="PLAN-102", ts="2026-04-27T10:00:00Z"),
        ]
        self.assertEqual(es.detect_debate_skip_l3(events, self.td), [])

    def test_silent_when_l1_or_l2(self) -> None:
        self._write_plan("PLAN-103", "L2")
        events = [
            _evt("agent_spawn", plan_id="PLAN-103", ts="2026-04-27T10:00:00Z"),
        ]
        self.assertEqual(es.detect_debate_skip_l3(events, self.td), [])

    def test_silent_when_plans_dir_missing(self) -> None:
        bogus = self.td / "does_not_exist"
        events = [_evt("agent_spawn", plan_id="PLAN-104")]
        self.assertEqual(es.detect_debate_skip_l3(events, bogus), [])

    def test_l4_plus_also_fires(self) -> None:
        self._write_plan("PLAN-105", "L4+")
        events = [_evt("agent_spawn", plan_id="PLAN-105")]
        signals = es.detect_debate_skip_l3(events, self.td)
        self.assertEqual(len(signals), 1)

    def test_quoted_level_string_parsed(self) -> None:
        p = self.td / "PLAN-106-test.md"
        p.write_text(
            "---\nstatus: draft\nlevel: \"L3\"\n---\n",
            encoding="utf-8",
        )
        events = [_evt("agent_spawn", plan_id="PLAN-106")]
        signals = es.detect_debate_skip_l3(events, self.td)
        self.assertEqual(len(signals), 1)


class TestDetectStrikeCounter(TestEnvContext):
    def test_fires_at_third_strike(self) -> None:
        events = [
            _evt("strike_recorded", agent="security-engineer", ts="2026-04-27T10:00:00Z"),
            _evt("strike_recorded", agent="security-engineer", ts="2026-04-27T11:00:00Z"),
            _evt("strike_recorded", agent="security-engineer", ts="2026-04-27T12:00:00Z"),
        ]
        signals = es.detect_strike_counter(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "strike_counter")
        self.assertEqual(signals[0]["details"]["cumulative_strikes"], 3)
        self.assertEqual(signals[0]["details"]["agent"], "security-engineer")

    def test_silent_at_two_strikes(self) -> None:
        events = [
            _evt("strike_recorded", agent="qa-architect"),
            _evt("strike_recorded", agent="qa-architect"),
        ]
        self.assertEqual(es.detect_strike_counter(events), [])

    def test_no_strikes(self) -> None:
        events = [_evt("agent_spawn"), _evt("agent_spawn")]
        self.assertEqual(es.detect_strike_counter(events), [])


class TestDetectVetoNonOpus(TestEnvContext):
    def test_fires_when_code_reviewer_on_sonnet(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="code-reviewer",
                 model="claude-sonnet-4-6"),
        ]
        signals = es.detect_veto_non_opus(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "veto_non_opus")
        self.assertEqual(signals[0]["details"]["role"], "code-reviewer")
        self.assertEqual(signals[0]["details"]["model"], "claude-sonnet-4-6")

    def test_fires_when_security_engineer_on_haiku(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="security-engineer",
                 model="claude-haiku-4-5"),
        ]
        signals = es.detect_veto_non_opus(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["details"]["role"], "security-engineer")

    def test_silent_when_opus(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="code-reviewer",
                 model="claude-opus-4-8"),
        ]
        self.assertEqual(es.detect_veto_non_opus(events), [])

    def test_silent_for_non_veto_role(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="qa-architect",
                 model="claude-sonnet-4-6"),
        ]
        self.assertEqual(es.detect_veto_non_opus(events), [])

    def test_unset_model_marked_unset(self) -> None:
        events = [
            _evt("agent_spawn", subagent_type="code-reviewer", model=""),
        ]
        signals = es.detect_veto_non_opus(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["details"]["model"], "<unset>")

    def test_role_via_agent_type_alias(self) -> None:
        events = [
            _evt("agent_spawn", agent_type="code-reviewer",
                 model="claude-sonnet-4-6"),
        ]
        signals = es.detect_veto_non_opus(events)
        self.assertEqual(len(signals), 1)


class TestDetectShortcutLanguage(TestEnvContext):
    def test_fires_on_quick_fix_phrase(self) -> None:
        events = [
            _evt("prompt_submitted",
                 preview="Let me just push a quick fix to main"),
        ]
        signals = es.detect_shortcut_language(events)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "shortcut_language")
        self.assertEqual(signals[0]["severity"], "low")
        self.assertIn("quick fix", signals[0]["details"]["phrases"])

    def test_fires_on_skip_debate(self) -> None:
        events = [
            _evt("output_scan_finding",
                 text_preview="i'll skip debate this time"),
        ]
        signals = es.detect_shortcut_language(events)
        self.assertEqual(len(signals), 1)
        self.assertIn("skip debate", signals[0]["details"]["phrases"])

    def test_silent_for_unrelated_text(self) -> None:
        events = [
            _evt("prompt_submitted",
                 preview="Please review the auth.ts module carefully."),
        ]
        self.assertEqual(es.detect_shortcut_language(events), [])

    def test_silent_for_unrelated_action(self) -> None:
        events = [
            _evt("agent_spawn", preview="quick fix"),
        ]
        self.assertEqual(es.detect_shortcut_language(events), [])

    def test_case_insensitive_match(self) -> None:
        events = [
            _evt("prompt_submitted", preview="TRUST ME, this is one-liner"),
        ]
        signals = es.detect_shortcut_language(events)
        self.assertEqual(len(signals), 1)
        # both "trust me" and "one-liner" matched
        self.assertGreaterEqual(len(signals[0]["details"]["phrases"]), 2)

    def test_empty_preview_silent(self) -> None:
        events = [_evt("prompt_submitted", preview="")]
        self.assertEqual(es.detect_shortcut_language(events), [])


class TestDetectorsTupleSanity(TestEnvContext):
    def test_all_six_detectors_exposed(self) -> None:
        self.assertEqual(len(es.DETECTORS), 6)

    def test_all_callable(self) -> None:
        for d in es.DETECTORS:
            self.assertTrue(callable(d))

    def test_naming_convention_detect_prefix(self) -> None:
        for d in es.DETECTORS:
            self.assertTrue(d.__name__.startswith("detect_"),
                            f"{d.__name__} missing detect_ prefix")


class TestHelpers(TestEnvContext):
    def test_event_ts_uses_ts_first(self) -> None:
        e = {"ts": "2026-04-27T10:00:00Z", "timestamp": "fallback"}
        self.assertEqual(es._event_ts(e), "2026-04-27T10:00:00Z")

    def test_event_ts_falls_back_to_timestamp(self) -> None:
        e = {"timestamp": "2026-04-27T11:00:00Z"}
        self.assertEqual(es._event_ts(e), "2026-04-27T11:00:00Z")

    def test_event_ts_empty(self) -> None:
        self.assertEqual(es._event_ts({}), "")

    def test_is_opus_true(self) -> None:
        self.assertTrue(es._is_opus("claude-opus-4-8"))
        self.assertTrue(es._is_opus("CLAUDE-OPUS-4-6"))

    def test_is_opus_false(self) -> None:
        self.assertFalse(es._is_opus("claude-sonnet-4-6"))
        self.assertFalse(es._is_opus(""))
        self.assertFalse(es._is_opus("opus"))  # missing claude- prefix

    def test_extract_plan_level_returns_none_for_missing_file(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="ceo-esc-"))
        bogus = td / "PLAN-999-missing.md"
        self.assertIsNone(es._extract_plan_level(bogus))

    def test_extract_plan_level_returns_none_when_no_frontmatter(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="ceo-esc-"))
        p = td / "PLAN-998.md"
        p.write_text("# Just a body\nno frontmatter here", encoding="utf-8")
        self.assertIsNone(es._extract_plan_level(p))

    def test_extract_plan_level_from_frontmatter(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="ceo-esc-"))
        p = td / "PLAN-997.md"
        p.write_text(
            "---\nstatus: draft\nlevel: L3\n---\n# body\n",
            encoding="utf-8",
        )
        self.assertEqual(es._extract_plan_level(p), "L3")


if __name__ == "__main__":
    unittest.main()
