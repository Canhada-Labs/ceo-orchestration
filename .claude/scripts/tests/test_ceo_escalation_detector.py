"""Unit tests for ceo-escalation-detector — PLAN-048 Phase 2 harness.

Covers each of the 6 detection signals with positive, negative, and
boundary cases; plus fail-open paths and format routines.

Stdlib only. Imports the detector as a module via importlib (script
filename has hyphens, so a normal `import` does not work).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# PLAN-019 P1-QA-3 — tests must subclass TestEnvContext for env isolation.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "hooks"),
)
from _lib.testing import TestEnvContext as _TestBase  # noqa: E402


_SCRIPT = (
    Path(__file__).resolve().parents[1] / "ceo-escalation-detector.py"
)


def _load_module():
    """Load the hyphenated script file as a Python module."""
    spec = importlib.util.spec_from_file_location(
        "ceo_escalation_detector", str(_SCRIPT)
    )
    assert spec and spec.loader, f"cannot load {_SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


ced = _load_module()


def _evt(**kw) -> dict:
    """Build an audit-log event with sensible defaults."""
    e = {
        "ts": "2026-04-21T10:00:00Z",
        "action": kw.pop("action", "agent_spawn"),
        "session_id": kw.pop("session_id", "s-test"),
    }
    e.update(kw)
    return e


class TestLoadJsonl(_TestBase):
    """load_jsonl: missing, valid, malformed, empty lines."""

    def test_missing_file_returns_empty(self):
        self.assertEqual(ced.load_jsonl(Path("/nonexistent/path.jsonl")), [])

    def test_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as fh:
            fh.write('{"a": 1}\n{"b": 2}\n')
            path = Path(fh.name)
        try:
            rows = ced.load_jsonl(path)
            self.assertEqual(rows, [{"a": 1}, {"b": 2}])
        finally:
            path.unlink(missing_ok=True)

    def test_malformed_line_skipped(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as fh:
            fh.write('{"a": 1}\nnot json\n{"b": 2}\n')
            path = Path(fh.name)
        try:
            rows = ced.load_jsonl(path)
            self.assertEqual(rows, [{"a": 1}, {"b": 2}])
        finally:
            path.unlink(missing_ok=True)

    def test_empty_lines_skipped(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as fh:
            fh.write('\n{"a": 1}\n\n\n')
            path = Path(fh.name)
        try:
            self.assertEqual(ced.load_jsonl(path), [{"a": 1}])
        finally:
            path.unlink(missing_ok=True)


class TestAutoDetectSession(_TestBase):
    """auto_detect_recent_session: empty, single, tied, reserved placeholders."""

    def test_empty_returns_none(self):
        self.assertIsNone(ced.auto_detect_recent_session([]))

    def test_single_session(self):
        evts = [_evt(session_id="s1"), _evt(session_id="s1")]
        self.assertEqual(ced.auto_detect_recent_session(evts), "s1")

    def test_picks_most_frequent(self):
        evts = [
            _evt(session_id="s1"),
            _evt(session_id="s2"),
            _evt(session_id="s2"),
        ]
        self.assertEqual(ced.auto_detect_recent_session(evts), "s2")

    def test_skips_placeholder_session_ids(self):
        evts = [
            _evt(session_id="unknown"),
            _evt(session_id=""),
            _evt(session_id="t"),
            _evt(session_id="real-session"),
        ]
        self.assertEqual(ced.auto_detect_recent_session(evts), "real-session")


class TestFilterBySession(_TestBase):
    """filter_by_session: positive + negative."""

    def test_filters_matching(self):
        evts = [_evt(session_id="a"), _evt(session_id="b"), _evt(session_id="a")]
        self.assertEqual(len(ced.filter_by_session(evts, "a")), 2)

    def test_no_match_returns_empty(self):
        evts = [_evt(session_id="a")]
        self.assertEqual(ced.filter_by_session(evts, "z"), [])


class TestGateSkip(_TestBase):
    """Signal 1 — gate_skip."""

    def test_no_work_no_incident(self):
        events = [_evt(action="session_start"), _evt(action="prompt_submitted")]
        self.assertEqual(ced.detect_gate_skip(events), [])

    def test_work_without_protocol_read_flags(self):
        events = [
            _evt(action="session_start"),
            _evt(action="agent_spawn"),
            _evt(action="plan_transition"),
        ]
        incidents = ced.detect_gate_skip(events)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["signal"], "gate_skip")
        self.assertEqual(incidents[0]["severity"], "high")

    def test_work_with_protocol_read_suppresses(self):
        events = [
            _evt(action="session_start", files_read=["CLAUDE.md", "PROTOCOL.md"]),
            _evt(action="agent_spawn"),
        ]
        self.assertEqual(ced.detect_gate_skip(events), [])

    def test_protocol_read_as_string_hint(self):
        events = [
            _evt(action="prompt_submitted", read_paths="CLAUDE.md"),
            _evt(action="agent_spawn"),
        ]
        self.assertEqual(ced.detect_gate_skip(events), [])

    def test_empty_events_returns_empty(self):
        self.assertEqual(ced.detect_gate_skip([]), [])


class TestCanonicalEditBlock(_TestBase):
    """Signal 2 — canonical_edit_block."""

    def test_action_canonical_edit_blocked(self):
        events = [_evt(action="canonical_edit_blocked", path=".claude/team.md")]
        incidents = ced.detect_canonical_edit_block(events)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["severity"], "high")
        self.assertEqual(incidents[0]["details"]["path"], ".claude/team.md")

    def test_response_kind_block_canonical_edit(self):
        events = [_evt(response_kind="block_canonical_edit")]
        incidents = ced.detect_canonical_edit_block(events)
        self.assertEqual(len(incidents), 1)

    def test_unrelated_block_ignored(self):
        events = [_evt(response_kind="block_missing_skill")]
        self.assertEqual(ced.detect_canonical_edit_block(events), [])

    def test_multiple_blocks_all_reported(self):
        events = [
            _evt(action="canonical_edit_blocked"),
            _evt(action="canonical_edit_blocked"),
        ]
        self.assertEqual(len(ced.detect_canonical_edit_block(events)), 2)


class TestDebateSkipL3(_TestBase):
    """Signal 3 — debate_skip_l3 (requires plans dir with frontmatter)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plans_dir = Path(self.tmpdir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_plan(self, plan_id: str, level: str):
        p = self.plans_dir / f"{plan_id}-test.md"
        p.write_text(
            f"---\nid: {plan_id}\nlevel: {level}\nstatus: draft\n---\n# body\n",
            encoding="utf-8",
        )

    def test_l3_plan_with_debate_no_incident(self):
        self._write_plan("PLAN-200", "L3")
        events = [
            _evt(action="debate_event", plan_id="PLAN-200", ts="2026-04-21T10:00:00Z"),
            _evt(action="agent_spawn", plan_id="PLAN-200", ts="2026-04-21T11:00:00Z"),
        ]
        self.assertEqual(
            ced.detect_debate_skip_l3(events, self.plans_dir), []
        )

    def test_l3_plan_without_debate_flags(self):
        self._write_plan("PLAN-201", "L3")
        events = [_evt(action="agent_spawn", plan_id="PLAN-201")]
        incidents = ced.detect_debate_skip_l3(events, self.plans_dir)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["signal"], "debate_skip_l3")
        self.assertEqual(incidents[0]["details"]["plan_id"], "PLAN-201")

    def test_l2_plan_no_incident(self):
        self._write_plan("PLAN-202", "L2")
        events = [_evt(action="agent_spawn", plan_id="PLAN-202")]
        self.assertEqual(
            ced.detect_debate_skip_l3(events, self.plans_dir), []
        )

    def test_l4_plan_flags_without_debate(self):
        self._write_plan("PLAN-203", "L4")
        events = [_evt(action="plan_transition", plan_id="PLAN-203")]
        self.assertEqual(
            len(ced.detect_debate_skip_l3(events, self.plans_dir)), 1
        )

    def test_debate_after_exec_still_flags(self):
        self._write_plan("PLAN-204", "L3")
        events = [
            _evt(action="agent_spawn", plan_id="PLAN-204", ts="2026-04-21T09:00:00Z"),
            _evt(action="debate_event", plan_id="PLAN-204", ts="2026-04-21T10:00:00Z"),
        ]
        # Debate came AFTER exec → still an incident.
        incidents = ced.detect_debate_skip_l3(events, self.plans_dir)
        self.assertEqual(len(incidents), 1)

    def test_missing_plan_file_skips(self):
        events = [_evt(action="agent_spawn", plan_id="PLAN-999")]
        self.assertEqual(
            ced.detect_debate_skip_l3(events, self.plans_dir), []
        )


class TestStrikeCounter(_TestBase):
    """Signal 4 — strike_counter."""

    def test_under_threshold_no_incident(self):
        events = [
            _evt(action="strike_recorded"),
            _evt(action="strike_recorded"),
        ]
        self.assertEqual(ced.detect_strike_counter(events), [])

    def test_threshold_triggers(self):
        events = [_evt(action="strike_recorded") for _ in range(3)]
        incidents = ced.detect_strike_counter(events)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["details"]["cumulative_strikes"], 3)

    def test_above_threshold_single_incident(self):
        events = [_evt(action="strike_recorded") for _ in range(5)]
        incidents = ced.detect_strike_counter(events)
        # Only one incident emitted at the threshold crossing.
        self.assertEqual(len(incidents), 1)

    def test_no_strikes_empty(self):
        events = [_evt(action="agent_spawn")]
        self.assertEqual(ced.detect_strike_counter(events), [])


class TestVetoNonOpus(_TestBase):
    """Signal 5 — veto_non_opus."""

    def test_veto_role_opus_no_incident(self):
        events = [
            _evt(
                action="agent_spawn",
                subagent_type="code-reviewer",
                model="claude-opus-4-7",
            )
        ]
        self.assertEqual(ced.detect_veto_non_opus(events), [])

    def test_veto_role_sonnet_flags(self):
        events = [
            _evt(
                action="agent_spawn",
                subagent_type="security-engineer",
                model="claude-sonnet-4-6",
            )
        ]
        incidents = ced.detect_veto_non_opus(events)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["details"]["role"], "security-engineer")

    def test_veto_role_empty_model_flags(self):
        events = [
            _evt(
                action="agent_spawn",
                subagent_type="code-reviewer",
                model="",
            )
        ]
        self.assertEqual(len(ced.detect_veto_non_opus(events)), 1)

    def test_non_veto_role_sonnet_ignored(self):
        events = [
            _evt(
                action="agent_spawn",
                subagent_type="general-purpose",
                model="claude-sonnet-4-6",
            )
        ]
        self.assertEqual(ced.detect_veto_non_opus(events), [])

    def test_case_insensitive_opus_prefix(self):
        events = [
            _evt(
                action="agent_spawn",
                subagent_type="code-reviewer",
                model="Claude-Opus-4-7",
            )
        ]
        self.assertEqual(ced.detect_veto_non_opus(events), [])

    def test_fallback_fields(self):
        events = [
            _evt(
                action="agent_spawn",
                agent_type="code-reviewer",  # alt field name
                model_id="claude-haiku-4-5",  # alt field name
            )
        ]
        self.assertEqual(len(ced.detect_veto_non_opus(events)), 1)


class TestShortcutLanguage(_TestBase):
    """Signal 6 — shortcut_language (advisory)."""

    def test_phrase_in_prompt_preview(self):
        events = [
            _evt(
                action="prompt_submitted",
                preview="Sure, I'll just ship it without tests.",
            )
        ]
        incidents = ced.detect_shortcut_language(events)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["severity"], "low")
        self.assertIn("i'll just", incidents[0]["details"]["phrases"])

    def test_no_phrase_no_incident(self):
        events = [_evt(action="prompt_submitted", preview="Let us plan carefully.")]
        self.assertEqual(ced.detect_shortcut_language(events), [])

    def test_case_insensitive_match(self):
        events = [_evt(action="prompt_submitted", preview="QUICK FIX incoming")]
        self.assertEqual(len(ced.detect_shortcut_language(events)), 1)

    def test_ignores_unrelated_action(self):
        events = [_evt(action="agent_spawn", preview="I'll just skip")]
        self.assertEqual(ced.detect_shortcut_language(events), [])

    def test_multiple_phrases_in_one_event(self):
        events = [
            _evt(
                action="output_scan_finding",
                text_preview="I'll just trust me on this one",
            )
        ]
        incidents = ced.detect_shortcut_language(events)
        self.assertEqual(len(incidents), 1)
        self.assertGreaterEqual(len(incidents[0]["details"]["phrases"]), 2)


class TestDetectAll(_TestBase):
    """detect_all + summarize."""

    def test_empty_events(self):
        self.assertEqual(ced.detect_all([]), [])

    def test_aggregates_signals(self):
        events = [
            _evt(action="canonical_edit_blocked"),
            _evt(action="strike_recorded"),
            _evt(action="strike_recorded"),
            _evt(action="strike_recorded"),
        ]
        incidents = ced.detect_all(events)
        signals = {i["signal"] for i in incidents}
        self.assertIn("canonical_edit_block", signals)
        self.assertIn("strike_counter", signals)

    def test_summarize_counts(self):
        incidents = [
            {"signal": "a", "severity": "high"},
            {"signal": "a", "severity": "high"},
            {"signal": "b", "severity": "low"},
        ]
        summ = ced.summarize(incidents)
        self.assertEqual(summ["total_incidents"], 3)
        self.assertEqual(summ["by_signal"], {"a": 2, "b": 1})
        self.assertEqual(summ["by_severity"], {"high": 2, "low": 1})


class TestFormatters(_TestBase):
    """Output format functions."""

    def test_format_count_empty(self):
        self.assertIn("total=0", ced.format_count([]))

    def test_format_markdown_empty(self):
        self.assertIn("No escalation incidents", ced.format_markdown([]))

    def test_format_jsonl_empty(self):
        self.assertEqual(ced.format_jsonl([]), "")

    def test_format_json_contains_summary(self):
        out = ced.format_json([{"signal": "x", "severity": "low", "ts": "", "details": {}}])
        parsed = json.loads(out)
        self.assertIn("summary", parsed)
        self.assertEqual(parsed["summary"]["total_incidents"], 1)

    def test_format_markdown_groups_by_signal(self):
        incs = [
            {"signal": "a", "severity": "high", "ts": "T", "details": {}},
            {"signal": "a", "severity": "high", "ts": "T", "details": {}},
            {"signal": "b", "severity": "low", "ts": "T", "details": {}},
        ]
        md = ced.format_markdown(incs)
        self.assertIn("## `a`", md)
        self.assertIn("## `b`", md)

    def test_format_jsonl_one_per_line(self):
        incs = [
            {"signal": "a", "severity": "high", "ts": "T", "details": {}},
            {"signal": "b", "severity": "low", "ts": "T", "details": {}},
        ]
        jsonl = ced.format_jsonl(incs)
        self.assertEqual(len(jsonl.strip().splitlines()), 2)


class TestBuildExperimentRecord(_TestBase):
    """build_experiment_record schema compliance."""

    def test_schema_version_stamped(self):
        rec = ced.build_experiment_record(
            session_id="s",
            incidents=[],
            ceo_model="claude-opus-4-7",
            session_tag_primary="L2-routine",
            notes="test",
        )
        self.assertEqual(rec["schema"], "plan-048-experiment-metrics.v1")
        self.assertEqual(rec["escalation_events_count"], 0)
        self.assertIn("collected_at_iso", rec)

    def test_incidents_embedded(self):
        incidents = [
            {"signal": "strike_counter", "severity": "high", "ts": "T", "details": {}}
        ]
        rec = ced.build_experiment_record(
            session_id="s",
            incidents=incidents,
            ceo_model="claude-sonnet-4-6",
            session_tag_primary="L3+-plan-execution",
            notes="",
        )
        self.assertEqual(rec["escalation_events_count"], 1)
        self.assertEqual(rec["escalation_by_signal"]["strike_counter"], 1)


class TestCliEndToEnd(_TestBase):
    """Exercise main() via argv + temp audit log."""

    def test_main_empty_audit_returns_zero(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-log.jsonl"
            audit.write_text("", encoding="utf-8")
            rc = ced.main(
                [
                    "--audit-log",
                    str(audit),
                    "--plans-dir",
                    td,
                    "--format",
                    "count",
                ]
            )
            self.assertEqual(rc, 0)

    def test_main_emit_metrics_appends_record(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-log.jsonl"
            # Include a Gate-1 read hint so only canonical_edit_block fires.
            audit.write_text(
                json.dumps(
                    _evt(
                        action="session_start",
                        session_id="S-E2E",
                        files_read=["CLAUDE.md", "PROTOCOL.md"],
                    )
                )
                + "\n"
                + json.dumps(
                    _evt(
                        action="canonical_edit_blocked",
                        session_id="S-E2E",
                        path=".claude/team.md",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            metrics_out = Path(td) / "experiment-metrics.jsonl"
            rc = ced.main(
                [
                    "--audit-log",
                    str(audit),
                    "--plans-dir",
                    td,
                    "--session-id",
                    "S-E2E",
                    "--format",
                    "count",
                    "--emit-metrics",
                    "--metrics-out",
                    str(metrics_out),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(metrics_out.is_file())
            rows = [
                json.loads(ln)
                for ln in metrics_out.read_text().splitlines()
                if ln.strip()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["escalation_events_count"], 1)
            self.assertEqual(
                rows[0]["escalation_by_signal"]["canonical_edit_block"], 1
            )


class TestFailOpen(_TestBase):
    """Fail-open invariant — detector never raises on bad data."""

    def test_malformed_event_does_not_crash(self):
        events = [
            {"action": None, "session_id": None},  # None action/session
            {"ts": 42},  # non-string ts
            {"action": "agent_spawn", "plan_id": None},
        ]
        # Should not raise.
        self.assertIsInstance(ced.detect_all(events), list)

    def test_detect_all_isolates_failures(self):
        # Inject a bogus event shape that could trip detectors.
        events = [{"action": "agent_spawn", "subagent_type": None, "model": None}]
        # detect_all catches and continues.
        self.assertIsInstance(ced.detect_all(events), list)


if __name__ == "__main__":
    unittest.main()
