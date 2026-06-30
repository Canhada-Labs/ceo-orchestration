"""Tests for reporter.py — schema + hashes + win-rate matrix + ADR-052 validation.

Round 1 C-P0-3 closures.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import reporter


class TestSha256Text(unittest.TestCase):
    def test_known_digest(self):
        # sha256("") is e3b0...
        self.assertEqual(
            reporter.sha256_text(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_handles_none(self):
        self.assertEqual(
            reporter.sha256_text(None),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_deterministic(self):
        self.assertEqual(
            reporter.sha256_text("hello"), reporter.sha256_text("hello")
        )

    def test_unicode(self):
        h = reporter.sha256_text("café")
        self.assertEqual(len(h), 64)


class TestMakeTaskRecord(unittest.TestCase):
    def test_minimal_record(self):
        rec = reporter.make_task_record(
            fixture_id="fx-001",
            fixture_content="some prompt",
            task_type="security-review",
            model="claude-opus-4-8",
            verdict="pass",
            output_text="some output",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            wall_clock_ms=2500,
        )
        self.assertEqual(rec["type"], "task")
        self.assertEqual(rec["fixture_id"], "fx-001")
        self.assertEqual(len(rec["fixture_sha256"]), 64)
        self.assertEqual(len(rec["output_sha256"]), 64)
        self.assertEqual(rec["verdict"], "pass")
        # No raw content fields
        self.assertNotIn("prompt", rec)
        self.assertNotIn("output", rec)
        self.assertNotIn("rationale", rec)

    def test_invalid_verdict_maps_to_errored(self):
        rec = reporter.make_task_record(
            fixture_id="fx-001",
            fixture_content="x",
            task_type="security-review",
            model="claude-haiku-4-5-20251001",
            verdict="weird-verdict",
            output_text=None,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
        )
        self.assertEqual(rec["verdict"], "errored")

    def test_rationale_only_hash_and_length(self):
        rec = reporter.make_task_record(
            fixture_id="fx-001",
            fixture_content="x",
            task_type="security-review",
            model="claude-opus-4-8",
            verdict="pass",
            output_text="out",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.001,
            wall_clock_ms=100,
            rationale="some rationale text",
            confidence=0.8,
        )
        self.assertIn("rationale_sha256", rec)
        self.assertIn("rationale_length", rec)
        self.assertEqual(rec["rationale_length"], len("some rationale text"))
        self.assertNotIn("rationale", rec)  # raw text MUST NOT appear

    def test_fixture_id_truncated_at_256(self):
        rec = reporter.make_task_record(
            fixture_id="x" * 500,
            fixture_content="x",
            task_type="t",
            model="m",
            verdict="pass",
            output_text="o",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
        )
        self.assertLessEqual(len(rec["fixture_id"]), 256)

    def test_error_reason_truncated_at_256(self):
        rec = reporter.make_task_record(
            fixture_id="x",
            fixture_content="x",
            task_type="t",
            model="m",
            verdict="errored",
            output_text=None,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
            error_reason="err " * 200,
        )
        self.assertLessEqual(len(rec["error_reason"]), 256)


class TestValidateAdr052(unittest.TestCase):
    def test_opus_policy_change_worthy_on_large_gap(self):
        """PLAN-045 F-12-03: ≥25pp gap emits the ACTIONABLE signal."""
        wr = {"security-review": {"claude-opus-4-8": 0.9, "claude-sonnet-4-6": 0.6}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_policy_change_worthy")

    def test_opus_confirmed_on_advisory_gap(self):
        """PLAN-045 F-12-03: 15-24pp gap emits the ADVISORY signal
        (directionally meaningful at n=10 but below learn.py 25pp gate)."""
        wr = {"security-review": {"claude-opus-4-8": 0.82, "claude-sonnet-4-6": 0.65}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_confirmed")

    def test_opus_mid_surprise_on_noise_gap(self):
        wr = {"code-review": {"claude-opus-4-8": 0.72, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["code-review"], "opus_mid_surprise")

    def test_opus_marginal_between_thresholds(self):
        wr = {"security-review": {"claude-opus-4-8": 0.80, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_marginal")

    def test_sonnet_underperforms_on_performance_triage(self):
        wr = {"performance-triage": {"claude-opus-4-8": 0.90, "claude-sonnet-4-6": 0.60}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["performance-triage"], "sonnet_underperforms")

    def test_parity_confirmed_on_performance_triage(self):
        wr = {"performance-triage": {"claude-opus-4-8": 0.80, "claude-sonnet-4-6": 0.75}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["performance-triage"], "parity_confirmed")

    def test_haiku_sufficient_on_docs_writing(self):
        wr = {"docs-writing": {"claude-haiku-4-5-20251001": 0.75}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["docs-writing"], "haiku_sufficient")

    def test_haiku_insufficient_on_docs_writing(self):
        wr = {"docs-writing": {"claude-haiku-4-5-20251001": 0.5}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["docs-writing"], "haiku_insufficient")

    def test_no_data_on_missing_task_type(self):
        signals = reporter.validate_adr052({})
        for tt in ("security-review", "code-review", "performance-triage", "docs-writing"):
            self.assertEqual(signals[tt], "no_data")

    def test_incomplete_data_when_model_missing(self):
        wr = {"security-review": {"claude-opus-4-8": 0.9}}  # no sonnet
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "incomplete_data")

    # ─── Mutation-killing boundary tests ───

    def test_opus_confirmed_exactly_at_15pp_gap(self):
        # gap = 0.15 exactly — threshold test: `gap >= _PP_SIGNIFICANT` vs `gap >`
        wr = {"security-review": {"claude-opus-4-8": 0.85, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_confirmed")

    def test_opus_marginal_just_below_15pp(self):
        # gap = 0.14 — below 15pp significance
        wr = {"security-review": {"claude-opus-4-8": 0.84, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_marginal")

    def test_opus_mid_surprise_exactly_at_5pp_gap(self):
        # gap = 0.05 exactly — threshold `gap < _PP_STATS_NOISE` — should NOT fire mid_surprise
        wr = {"security-review": {"claude-opus-4-8": 0.75, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_marginal")

    def test_opus_mid_surprise_just_below_5pp(self):
        # gap = 0.04 — below noise threshold → mid_surprise fires
        wr = {"security-review": {"claude-opus-4-8": 0.74, "claude-sonnet-4-6": 0.70}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["security-review"], "opus_mid_surprise")

    def test_haiku_sufficient_exactly_at_threshold(self):
        # haiku_wr = 0.70 exactly — threshold `>= 0.7` vs `> 0.7`
        wr = {"docs-writing": {"claude-haiku-4-5-20251001": 0.7}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["docs-writing"], "haiku_sufficient")

    def test_haiku_insufficient_just_below_threshold(self):
        wr = {"docs-writing": {"claude-haiku-4-5-20251001": 0.69}}
        signals = reporter.validate_adr052(wr)
        self.assertEqual(signals["docs-writing"], "haiku_insufficient")


class TestComputeWinRateMatrix(unittest.TestCase):
    def test_basic_pass_fail(self):
        records = [
            {"type": "task", "task_type": "security-review", "model": "claude-opus-4-8", "verdict": "pass"},
            {"type": "task", "task_type": "security-review", "model": "claude-opus-4-8", "verdict": "pass"},
            {"type": "task", "task_type": "security-review", "model": "claude-opus-4-8", "verdict": "fail"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # 2 pass / 3 non-errored = 0.6667
        self.assertAlmostEqual(
            matrix["security-review"]["claude-opus-4-8"], 0.6667, places=3
        )

    def test_errored_excluded_from_denominator(self):
        # QA P5 — errored tasks MUST NOT inflate win-rate
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # 1 pass / 1 non-errored = 1.0 (NOT 0.5)
        self.assertEqual(matrix["t"]["m"], 1.0)

    def test_all_errored_zero(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 0.0)

    def test_aggregate_records_ignored(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "aggregate", "task_type": "ignored", "win_rate": {}},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(set(matrix.keys()), {"t"})

    def test_missing_fields_skipped(self):
        records = [
            {"type": "task", "model": "m", "verdict": "pass"},  # missing task_type
            {"type": "task", "task_type": "t", "verdict": "pass"},  # missing model
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # Only the third record is valid; matrix has one cell
        self.assertEqual(matrix, {"t": {"m": 1.0}})


class TestWinRateEdgeCases(unittest.TestCase):
    """Edge-case coverage targeting mutation survivors."""

    def test_unknown_verdict_string_not_counted(self):
        # A record with verdict "maybe" should not inflate any bucket
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "maybe"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        # Only pass counted; 1 pass / 1 valid = 1.0
        self.assertEqual(matrix["t"]["m"], 1.0)

    def test_non_task_type_entries_not_counted(self):
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "malformed", "task_type": "t", "model": "m", "verdict": "pass"},
            {"type": "summary", "task_type": "t", "model": "m", "verdict": "fail"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 1.0)

    def test_non_errored_zero_returns_zero_not_divide_error(self):
        # All records errored — non_errored = 0; must not crash
        records = [
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
            {"type": "task", "task_type": "t", "model": "m", "verdict": "errored"},
        ]
        matrix = reporter.compute_win_rate_matrix(records)
        self.assertEqual(matrix["t"]["m"], 0.0)


class TestMakeTaskRecordBranchCoverage(unittest.TestCase):
    """Cover the optional-field branches."""

    def test_rationale_only_present_when_passed(self):
        rec = reporter.make_task_record(
            fixture_id="f",
            fixture_content="c",
            task_type="t",
            model="m",
            verdict="pass",
            output_text="o",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
            rationale=None,  # explicitly None
        )
        self.assertNotIn("rationale_sha256", rec)
        self.assertNotIn("rationale_length", rec)

    def test_confidence_exact_bounds(self):
        rec_zero = reporter.make_task_record(
            fixture_id="f",
            fixture_content="c",
            task_type="t",
            model="m",
            verdict="pass",
            output_text="o",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
            confidence=0.0,
        )
        self.assertEqual(rec_zero["confidence"], 0.0)

        rec_one = reporter.make_task_record(
            fixture_id="f",
            fixture_content="c",
            task_type="t",
            model="m",
            verdict="pass",
            output_text="o",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
            confidence=1.0,
        )
        self.assertEqual(rec_one["confidence"], 1.0)

    def test_error_reason_omitted_when_none(self):
        rec = reporter.make_task_record(
            fixture_id="f",
            fixture_content="c",
            task_type="t",
            model="m",
            verdict="pass",
            output_text="o",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            wall_clock_ms=0,
            error_reason=None,
        )
        self.assertNotIn("error_reason", rec)


class TestLoadReport(unittest.TestCase):
    def test_round_trip(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "r.jsonl"
            with path.open("w", encoding="utf-8") as h:
                h.write(
                    json.dumps(
                        reporter.make_task_record(
                            fixture_id="fx-001",
                            fixture_content="c",
                            task_type="t",
                            model="m",
                            verdict="pass",
                            output_text="o",
                            tokens_in=0,
                            tokens_out=0,
                            cost_usd=0.0,
                            wall_clock_ms=0,
                        )
                    )
                    + "\n"
                )
                h.write(
                    json.dumps(
                        {
                            "type": "aggregate",
                            "run_id": "run-1",
                            "fixtures_count": 1,
                        }
                    )
                    + "\n"
                )
            report = reporter.load_report(path)
            self.assertEqual(len(report["tasks"]), 1)
            self.assertIsNotNone(report["aggregate"])
            self.assertEqual(report["parse_errors"], 0)

    def test_skip_malformed_lines(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "r.jsonl"
            path.write_text(
                '{"type": "task", "fixture_id": "x"}\n{malformed}\n',
                encoding="utf-8",
            )
            report = reporter.load_report(path)
            self.assertEqual(report["parse_errors"], 1)
            self.assertEqual(len(report["tasks"]), 1)


class TestHMACAnchor(unittest.TestCase):
    def test_empty_report_returns_hmac_or_none(self):
        # If audit_hmac is unavailable (no key), returns None (fail-open)
        # If available, returns 64-hex string
        with TemporaryDirectory() as d:
            path = Path(d) / "r.jsonl"
            path.write_text("", encoding="utf-8")
            result = reporter.compute_report_hmac(path)
            # Either 64-hex or None — both valid per fail-open contract
            if result is not None:
                self.assertEqual(len(result), 64)

    def test_anchor_companion_file(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "r.jsonl"
            path.write_text(
                json.dumps({"type": "task", "id": 1}) + "\n", encoding="utf-8"
            )
            anchor_path = reporter.write_report_anchor(path)
            # Either created or None (fail-open if HMAC infra absent)
            if anchor_path is not None:
                self.assertTrue(anchor_path.exists())
                self.assertTrue(str(anchor_path).endswith(".hmac"))
                # File content is a hex digest + newline
                content = anchor_path.read_text(encoding="utf-8").strip()
                self.assertEqual(len(content), 64)


if __name__ == "__main__":
    unittest.main()
