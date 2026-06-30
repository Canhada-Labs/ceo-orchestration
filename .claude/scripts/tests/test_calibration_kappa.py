"""Unit tests for calibration-kappa.py — Cohen's κ computation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "calibration_kappa", str(_SCRIPTS_DIR / "calibration-kappa.py")
)
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)


class TestKappaMath(unittest.TestCase):
    """Cohen's κ invariants — perfect agreement, perfect disagreement, chance."""

    def test_perfect_agreement_unweighted_is_one(self):
        k = ck._unweighted_kappa([5, 7, 2, 9], [5, 7, 2, 9])
        self.assertAlmostEqual(k, 1.0, places=6)

    def test_perfect_agreement_weighted_is_one(self):
        k = ck._linear_weighted_kappa([5, 7, 2, 9], [5, 7, 2, 9])
        self.assertAlmostEqual(k, 1.0, places=6)

    def test_empty_returns_none(self):
        self.assertIsNone(ck._unweighted_kappa([], []))
        self.assertIsNone(ck._linear_weighted_kappa([], []))

    def test_weighted_penalizes_distant_disagreement_more(self):
        # Human with real variance; judge agrees nearby vs judge off by a lot.
        # Human: spread across 0-10. Judge nearby is off by ±1; judge distant is off by 5-10.
        h = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0, 5, 10, 3, 7, 2, 8, 4, 6]
        j_nearby = [1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 10, 1, 6, 9, 4, 6, 3, 7, 5, 5]
        j_distant = [10, 10, 10, 10, 10, 10, 10, 0, 0, 0, 0, 10, 10, 0, 10, 0, 10, 0, 10, 0]
        k_nearby = ck._linear_weighted_kappa(h, j_nearby)
        k_distant = ck._linear_weighted_kappa(h, j_distant)
        self.assertIsNotNone(k_nearby)
        self.assertIsNotNone(k_distant)
        self.assertGreater(k_nearby, k_distant)

    def test_confusion_matrix_sums_to_n(self):
        h = [0, 5, 10, 5, 5]
        j = [0, 5, 10, 4, 6]
        cm = ck._confusion_matrix(h, j)
        total = sum(sum(row) for row in cm)
        self.assertEqual(total, len(h))

    def test_confusion_matrix_records_each_pair(self):
        h = [0, 5, 10]
        j = [0, 6, 9]
        cm = ck._confusion_matrix(h, j)
        self.assertEqual(cm[0][0], 1)
        self.assertEqual(cm[5][6], 1)
        self.assertEqual(cm[10][9], 1)


class TestLoadGrades(unittest.TestCase):

    def _write_grades(self, lines):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        for ln in lines:
            f.write(ln + "\n")
        f.close()
        return Path(f.name)

    def test_empty_file_returns_empty_list(self):
        p = self._write_grades([])
        try:
            self.assertEqual(ck._load_grades(p), [])
        finally:
            os.unlink(p)

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(ck._load_grades(Path("/tmp/nonexistent-grades-xyz.jsonl")), [])

    def test_comment_lines_skipped(self):
        p = self._write_grades([
            "# this is a comment",
            "",
            json.dumps({"id": "g-1", "human": 7, "judge_fwd": 7}),
        ])
        try:
            rows = ck._load_grades(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "g-1")
        finally:
            os.unlink(p)

    def test_malformed_line_skipped_with_warning(self):
        p = self._write_grades([
            "{not json",
            json.dumps({"id": "g-1", "human": 5, "judge_fwd": 5}),
        ])
        try:
            rows = ck._load_grades(p)
            self.assertEqual(len(rows), 1)
        finally:
            os.unlink(p)

    def test_dedupe_by_id_last_wins(self):
        p = self._write_grades([
            json.dumps({"id": "g-1", "human": 5, "judge_fwd": 5, "note": "first"}),
            json.dumps({"id": "g-1", "human": 8, "judge_fwd": 8, "note": "correction"}),
        ])
        try:
            rows = ck._load_grades(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["note"], "correction")
        finally:
            os.unlink(p)

    def test_missing_id_skipped(self):
        p = self._write_grades([
            json.dumps({"human": 5, "judge_fwd": 5}),
        ])
        try:
            self.assertEqual(ck._load_grades(p), [])
        finally:
            os.unlink(p)


class TestReport(unittest.TestCase):

    def test_report_flags_unreportable_below_20(self):
        rows = [{"id": f"g-{i}", "human": 5, "judge_fwd": 5} for i in range(5)]
        r = ck.compute_report(rows)
        self.assertEqual(r["n_pairs"], 5)
        txt = ck.format_report(r)
        self.assertIn("UNREPORTABLE", txt)

    def test_report_flags_preliminary_at_20_to_49(self):
        rows = [{"id": f"g-{i}", "human": 5, "judge_fwd": 5} for i in range(25)]
        txt = ck.format_report(ck.compute_report(rows))
        self.assertIn("PRELIMINARY", txt)

    def test_report_flags_flip_ready_at_50_with_high_kappa(self):
        # 50 perfectly-agreeing pairs with some variance so marginals vary.
        scores = [i % 11 for i in range(50)]
        rows = [
            {"id": f"g-{i}", "human": scores[i], "judge_fwd": scores[i]}
            for i in range(50)
        ]
        r = ck.compute_report(rows)
        self.assertEqual(r["n_pairs"], 50)
        self.assertAlmostEqual(r["kappa_linear_weighted"], 1.0, places=6)
        txt = ck.format_report(r)
        self.assertIn("FLIP-READY", txt)

    def test_report_flags_flip_blocked_with_low_kappa(self):
        # 50 pairs with mostly random disagreement
        h = [i % 11 for i in range(50)]
        j = [(i * 7 + 3) % 11 for i in range(50)]
        rows = [{"id": f"g-{i}", "human": h[i], "judge_fwd": j[i]} for i in range(50)]
        r = ck.compute_report(rows)
        self.assertEqual(r["n_pairs"], 50)
        self.assertLess(r["kappa_linear_weighted"], 0.7)
        txt = ck.format_report(r)
        self.assertIn("FLIP-BLOCKED", txt)

    def test_refusal_metrics_computed(self):
        rows = [
            {"id": "g-1", "human": 5, "judge_fwd": 5},
            {"id": "g-2", "refused_human": True, "refused_judge": True},
            {"id": "g-3", "refused_human": True, "refused_judge": False, "human": None, "judge_fwd": None},
            {"id": "g-4", "refused_human": False, "refused_judge": True, "human": None, "judge_fwd": None},
        ]
        r = ck.compute_report(rows)
        rm = r["refusal_metrics"]
        self.assertEqual(rm["n_human_refused"], 2)
        self.assertEqual(rm["n_judge_refused"], 2)
        # Intersection = {g-2} only → precision = 1/2, recall = 1/2
        self.assertAlmostEqual(rm["precision"], 0.5, places=6)
        self.assertAlmostEqual(rm["recall"], 0.5, places=6)

    def test_out_of_range_scores_filtered(self):
        rows = [
            {"id": "g-1", "human": 5, "judge_fwd": 5},
            {"id": "g-2", "human": 15, "judge_fwd": 5},  # out of range
            {"id": "g-3", "human": -1, "judge_fwd": 5},  # out of range
            {"id": "g-4", "human": "eight", "judge_fwd": 5},  # wrong type
        ]
        r = ck.compute_report(rows)
        self.assertEqual(r["n_pairs"], 1)


class TestCLI(unittest.TestCase):

    def _run(self, args):
        return subprocess.run(
            ["python3", str(_SCRIPTS_DIR / "calibration-kappa.py")] + list(args),
            capture_output=True, text=True,
        )

    def test_help_exits_zero(self):
        res = self._run(["--help"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Cohen", res.stdout)

    def test_empty_seed_file_exits_2_below_min_n(self):
        # Point at real seed file which has no scorable rows
        res = self._run([
            "--grades", str(_SCRIPTS_DIR.parent / "benchmarks" / "calibration-grades.jsonl"),
        ])
        self.assertEqual(res.returncode, 2)
        self.assertIn("No scorable pairs", res.stdout)

    def test_json_output_is_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for i in range(3):
                f.write(json.dumps({"id": f"g-{i}", "human": 5, "judge_fwd": 5}) + "\n")
            path = f.name
        try:
            res = self._run(["--grades", path, "--json", "--min-n", "1"])
            self.assertEqual(res.returncode, 0)
            data = json.loads(res.stdout)
            self.assertEqual(data["n_pairs"], 3)
            self.assertEqual(data["threshold_flip"], 0.7)
        finally:
            os.unlink(path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
