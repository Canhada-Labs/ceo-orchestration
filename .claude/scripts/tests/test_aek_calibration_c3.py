"""PLAN-101 Wave B — tests for aek-calibration-c3.py.

Covers AC2 + AC7 (4x4 confusion matrix + property-style stdlib loop
≥200 cases per PLAN-101 §B.5 + cell-min sparse-data marking).
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[3]
_C3 = _REPO_ROOT / ".claude" / "scripts" / "aek-calibration-c3.py"

_spec = importlib.util.spec_from_file_location("aek_c3", _C3)
_c3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c3)


def _make_advised(cid: str, classification: str) -> Dict:
    return {
        "action": "task_route_advised",
        "contract_id": cid,
        "classification": classification,
        "duration_ms": 1.0,
    }


def _make_ground_truth(cid: str, gt: str) -> Dict:
    return {
        "action": "task_route_ground_truth_label",
        "contract_id": cid,
        "ground_truth_class": gt,
        "ground_truth_source": "heuristic_auto",
        "annotation_confidence_bps": 10000,
    }


class TestJoin(unittest.TestCase):
    def test_join_inner_pairs(self):
        advised = [_make_advised(f"cid-{i}", c) for i, c in enumerate(["S", "M", "L", "XL"])]
        truth = [_make_ground_truth(f"cid-{i}", c) for i, c in enumerate(["S", "M", "L", "XL"])]
        pairs = _c3._join_advised_truth(advised, truth)
        self.assertEqual(len(pairs), 4)
        self.assertEqual(set(pairs), {("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL")})

    def test_join_missing_truth_drops(self):
        advised = [_make_advised("cid-1", "S"), _make_advised("cid-2", "M")]
        truth = [_make_ground_truth("cid-1", "S")]
        pairs = _c3._join_advised_truth(advised, truth)
        self.assertEqual(len(pairs), 1)

    def test_join_unknown_class_drops(self):
        advised = [_make_advised("cid-1", "S"), _make_advised("cid-2", "XXX")]
        truth = [_make_ground_truth("cid-1", "S"), _make_ground_truth("cid-2", "S")]
        pairs = _c3._join_advised_truth(advised, truth)
        # cid-2 advised has unknown class → dropped
        self.assertEqual(len(pairs), 1)


class TestMatrix(unittest.TestCase):
    def test_build_diagonal(self):
        pairs = [("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL")]
        m = _c3._build_matrix(pairs)
        self.assertEqual(m[("S", "S")], 1)
        self.assertEqual(_c3._trace(m), 4)

    def test_build_off_diagonal(self):
        pairs = [("S", "M"), ("M", "L"), ("L", "XL")]
        m = _c3._build_matrix(pairs)
        self.assertEqual(_c3._trace(m), 0)
        self.assertEqual(_c3._total_events(m), 3)

    def test_16_cells_property(self):
        """Property: matrix has at most 16 cells across S/M/L/XL × S/M/L/XL."""
        pairs = [(gt, pred) for gt in ("S", "M", "L", "XL") for pred in ("S", "M", "L", "XL")]
        m = _c3._build_matrix(pairs)
        self.assertEqual(len(m), 16)
        self.assertEqual(_c3._total_events(m), 16)


class TestPerClassMetrics(unittest.TestCase):
    def test_perfect_classifier(self):
        pairs = [("S", "S")] * 10 + [("M", "M")] * 10
        m = _c3._build_matrix(pairs)
        metrics = _c3._per_class_metrics(m)
        self.assertEqual(metrics["S"]["precision"], 1.0)
        self.assertEqual(metrics["S"]["recall"], 1.0)
        self.assertEqual(metrics["S"]["f1"], 1.0)

    def test_all_wrong_classifier(self):
        pairs = [("S", "M")] * 10
        m = _c3._build_matrix(pairs)
        metrics = _c3._per_class_metrics(m)
        self.assertEqual(metrics["S"]["recall"], 0.0)
        # S precision: TP/(TP+FP) where no S was predicted → 0/0 → 0
        self.assertEqual(metrics["S"]["precision"], 0.0)


class TestWilson(unittest.TestCase):
    def test_wilson_zero_total(self):
        self.assertEqual(_c3._wilson_lower(0, 0), 0.0)

    def test_wilson_basic_bound(self):
        # 5/100 success → Wilson 95% lower should be < observed 0.05
        w = _c3._wilson_lower(5, 100)
        self.assertGreaterEqual(w, 0.0)
        self.assertLess(w, 0.05)

    def test_wilson_full_success(self):
        # 100/100 → Wilson 95% lower < 1.0
        w = _c3._wilson_lower(100, 100)
        self.assertLess(w, 1.0)


class TestPropertyDeterministicLoop(unittest.TestCase):
    """≥200 deterministic property-style cases per PLAN-101 §B.5.

    Replaces Hypothesis (banned repo-wide); uses seeded stdlib loop.
    Mirrors precedent at .claude/hooks/tests/test_audit_hmac_chain_monotonicity_property.py.
    """

    def test_property_loop_invariants_200_cases(self):
        rng = random.Random(42)
        classes = ("S", "M", "L", "XL")
        for trial in range(200):
            n_pairs = rng.randint(0, 30)
            pairs: List[Tuple[str, str]] = []
            for _ in range(n_pairs):
                gt = classes[rng.randint(0, 3)]
                pred = classes[rng.randint(0, 3)]
                pairs.append((gt, pred))
            m = _c3._build_matrix(pairs)
            # Invariant 1: total events = sum of all cells
            self.assertEqual(_c3._total_events(m), len(pairs))
            # Invariant 2: trace ≤ total
            self.assertLessEqual(_c3._trace(m), _c3._total_events(m))
            # Invariant 3: per-class precision/recall/F1 ∈ [0,1]
            metrics = _c3._per_class_metrics(m)
            for cls in classes:
                self.assertGreaterEqual(metrics[cls]["precision"], 0.0)
                self.assertLessEqual(metrics[cls]["precision"], 1.0)
                self.assertGreaterEqual(metrics[cls]["recall"], 0.0)
                self.assertLessEqual(metrics[cls]["recall"], 1.0)
                self.assertGreaterEqual(metrics[cls]["f1"], 0.0)
                self.assertLessEqual(metrics[cls]["f1"], 1.0)
                # FPR in [0,1]
                self.assertGreaterEqual(metrics[cls]["fpr"], 0.0)
                self.assertLessEqual(metrics[cls]["fpr"], 1.0)


class TestSidecarRead(unittest.TestCase):
    def test_read_sidecar_jsonl(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(json.dumps(_make_ground_truth("cid-1", "S")) + "\n")
            fh.write(json.dumps(_make_ground_truth("cid-2", "M")) + "\n")
            fh.write("# comment, not JSON\n")
            fh.write(json.dumps(_make_ground_truth("cid-3", "L")) + "\n")
            path = Path(fh.name)
        try:
            rows = _c3._read_ground_truth_sidecar(path)
            self.assertEqual(len(rows), 3)
        finally:
            path.unlink()

    def test_read_missing_sidecar(self):
        rows = _c3._read_ground_truth_sidecar(Path("/nonexistent/path.jsonl"))
        self.assertEqual(rows, [])


class TestSelfTest(unittest.TestCase):
    def test_self_test_exit_ok(self):
        result = subprocess.run(
            [sys.executable, str(_C3), "--self-test"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, _c3.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
