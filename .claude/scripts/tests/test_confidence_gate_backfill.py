"""PLAN-090 AMENDMENT-1 Wave A.10 — confidence-gate-backfill tests.

12 tests covering grouping, FPR calc, insufficient-data handling, and
AC18/AC19/AC20 invariants.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))

# Module under test (hyphen → underscore for import).
_BACKFILL_PATH = _REPO_ROOT / ".claude" / "scripts" / "confidence-gate-backfill.py"


def _import_backfill():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "confidence_gate_backfill", str(_BACKFILL_PATH),
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ev_claim(claim_type: str, claim_id: str, ts: str) -> dict:
    return {
        "action": "claim_emitted",
        "claim_type": claim_type,
        "claim_id": claim_id,
        "ts": ts,
    }


def _ev_verdict(claim_id: str, verdict: str, ts: str) -> dict:
    return {
        "action": "confidence_gate_verdict",
        "claim_id": claim_id,
        "verdict": verdict,
        "ts": ts,
    }


class TestBackfill(unittest.TestCase):

    def setUp(self) -> None:
        self.mod = _import_backfill()
        self.tmpdir = tempfile.mkdtemp(prefix="conf-gate-bf-")
        self.log_path = Path(self.tmpdir) / "audit-log.jsonl"

    def _write_events(self, events) -> None:
        with self.log_path.open("w", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev) + "\n")

    def _now_iso(self, offset_days: int = 0) -> str:
        return (
            dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(days=offset_days)
        ).isoformat()

    def test_empty_log_returns_no_rows(self) -> None:
        self._write_events([])
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, verdicts = self.mod._scan_log(self.log_path, cutoff)
        self.assertEqual(claims, {})
        self.assertEqual(verdicts, {})

    def test_three_distinct_classes(self) -> None:
        events = [
            _ev_claim("perf-claim", "c1", self._now_iso(1)),
            _ev_claim("sec-claim", "c2", self._now_iso(1)),
            _ev_claim("qa-claim", "c3", self._now_iso(1)),
        ]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, _ = self.mod._scan_log(self.log_path, cutoff)
        self.assertEqual(set(claims.keys()), {"perf-claim", "sec-claim", "qa-claim"})

    def test_cutoff_filters_old_events(self) -> None:
        events = [
            _ev_claim("perf", "c1", self._now_iso(60)),  # outside 30d
            _ev_claim("perf", "c2", self._now_iso(2)),    # inside
        ]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, _ = self.mod._scan_log(self.log_path, cutoff)
        self.assertEqual(len(claims["perf"]), 1)

    def test_fpr_calculation_basic(self) -> None:
        events = [_ev_claim("perf", f"c{i}", self._now_iso(1)) for i in range(10)]
        events += [_ev_verdict(f"c{i}", "refuted", self._now_iso(1)) for i in range(3)]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, verdicts = self.mod._scan_log(self.log_path, cutoff)
        rows = self.mod._compute_fpr_per_class(claims, verdicts, min_samples=5)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["class"], "perf")
        self.assertEqual(row["n"], 10)
        self.assertEqual(row["false_positives"], 3)
        # 3000 bps = 30%
        self.assertEqual(row["fpr_basis_points"], 3000)

    def test_insufficient_data_rows(self) -> None:
        events = [
            _ev_claim("rare-class", "c1", self._now_iso(1)),
            _ev_claim("rare-class", "c2", self._now_iso(1)),
        ]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, verdicts = self.mod._scan_log(self.log_path, cutoff)
        rows = self.mod._compute_fpr_per_class(claims, verdicts, min_samples=5)
        self.assertEqual(rows[0]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(rows[0]["fpr_basis_points"])

    def test_unclassified_fallback_class(self) -> None:
        events = [
            {"action": "claim_emitted", "claim_id": "x", "ts": self._now_iso(1)},
        ]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, _ = self.mod._scan_log(self.log_path, cutoff)
        self.assertIn("unclassified", claims)

    def test_was_false_positive_field_also_counts(self) -> None:
        events = [
            _ev_claim("perf", "c1", self._now_iso(1)),
            {
                "action": "confidence_gate_verdict",
                "claim_id": "c1",
                "was_false_positive": True,
                "ts": self._now_iso(1),
            },
        ]
        events += [_ev_claim("perf", f"c{i}", self._now_iso(1)) for i in range(2, 11)]
        self._write_events(events)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, verdicts = self.mod._scan_log(self.log_path, cutoff)
        rows = self.mod._compute_fpr_per_class(claims, verdicts, min_samples=5)
        self.assertEqual(rows[0]["false_positives"], 1)

    def test_render_report_lists_distinct_count(self) -> None:
        rows = [
            {"class": "a", "n": 10, "false_positives": 0, "fpr_basis_points": 0, "status": "OK"},
            {"class": "b", "n": 5, "false_positives": 1, "fpr_basis_points": 2000, "status": "BELOW_PROMOTION_GATE"},
            {"class": "c", "n": 0, "false_positives": 0, "fpr_basis_points": None, "status": "INSUFFICIENT_DATA"},
        ]
        now = dt.datetime.now(dt.timezone.utc)
        cutoff = now - dt.timedelta(days=30)
        md = self.mod._render_report(rows, 30, cutoff, now)
        self.assertIn("Distinct claim-classes observed: 2", md)
        self.assertIn("`a`", md)
        self.assertIn("ADVISORY", md)

    def test_malformed_json_lines_skipped(self) -> None:
        with self.log_path.open("w", encoding="utf-8") as fh:
            fh.write("not json\n")
            fh.write(json.dumps(_ev_claim("perf", "c1", self._now_iso(1))) + "\n")
            fh.write("\n")  # empty line
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, _ = self.mod._scan_log(self.log_path, cutoff)
        self.assertEqual(len(claims.get("perf", [])), 1)

    def test_missing_log_file_returns_empty(self) -> None:
        nonexistent = Path(self.tmpdir) / "nope.jsonl"
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        claims, verdicts = self.mod._scan_log(nonexistent, cutoff)
        self.assertEqual(claims, {})
        self.assertEqual(verdicts, {})

    def test_main_writes_report(self) -> None:
        events = [_ev_claim("perf", f"c{i}", self._now_iso(1)) for i in range(10)]
        self._write_events(events)
        report = Path(self.tmpdir) / "report.md"
        rc = self.mod.main([
            "--audit-log", str(self.log_path),
            "--report-path", str(report),
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(report.is_file())
        content = report.read_text(encoding="utf-8")
        self.assertIn("PLAN-090", content)

    def test_ac20_no_block_decision_invariant(self) -> None:
        # AC20: NO mode flip — report itself contains the
        # invariant assertion language; we verify the literal phrase
        # appears so a future code-reviewer cannot silently strip it.
        events = [_ev_claim("perf", f"c{i}", self._now_iso(1)) for i in range(10)]
        self._write_events(events)
        report = Path(self.tmpdir) / "report.md"
        rc = self.mod.main([
            "--audit-log", str(self.log_path),
            "--report-path", str(report),
        ])
        self.assertEqual(rc, 0)
        content = report.read_text(encoding="utf-8")
        self.assertIn("ADVISORY", content)
        self.assertIn("No mode flip applied", content)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
