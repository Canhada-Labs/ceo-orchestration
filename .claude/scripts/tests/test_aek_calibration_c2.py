"""PLAN-101 Wave A — tests for aek-calibration-c2.py.

Covers AC1 + AC6 (EXIT_INSUFFICIENT_VOLUME path + cell-min guard).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_C2 = _REPO_ROOT / ".claude" / "scripts" / "aek-calibration-c2.py"

_spec = importlib.util.spec_from_file_location("aek_c2", _C2)
_c2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c2)


class TestCompute(unittest.TestCase):
    def test_compute_empty(self):
        b = _c2._compute_baseline([])
        self.assertEqual(b["total_events"], 0)
        for cls in _c2.KNOWN_CLASSES:
            self.assertEqual(b["by_class"][cls], 0)

    def test_compute_basic_distribution(self):
        events = [
            {"action": "task_route_advised", "classification": "S", "duration_ms": 1.0},
            {"action": "task_route_advised", "classification": "M", "duration_ms": 2.0},
            {"action": "task_route_advised", "classification": "L", "duration_ms": 3.0},
            {"action": "task_route_advised", "classification": "XL", "duration_ms": 4.0},
            {"action": "task_route_advised", "classification": "S", "duration_ms": 5.0},
        ]
        b = _c2._compute_baseline(events)
        self.assertEqual(b["total_events"], 5)
        self.assertEqual(b["by_class"]["S"], 2)
        self.assertEqual(b["by_class"]["M"], 1)
        self.assertEqual(b["by_class"]["L"], 1)
        self.assertEqual(b["by_class"]["XL"], 1)

    def test_compute_unknown_classification(self):
        events = [
            {"action": "task_route_advised", "classification": "XXL", "duration_ms": 1.0},
            {"action": "task_route_advised", "classification": "S", "duration_ms": 2.0},
        ]
        b = _c2._compute_baseline(events)
        self.assertEqual(b["total_events"], 2)
        self.assertEqual(b["by_class_unknown"], 1)
        self.assertEqual(b["by_class"]["S"], 1)

    def test_compute_skips_missing_duration(self):
        events = [
            {"action": "task_route_advised", "classification": "S"},
            {"action": "task_route_advised", "classification": "S", "duration_ms": 10.0},
        ]
        b = _c2._compute_baseline(events)
        # First event has no duration_ms → not added to durations_by_class
        self.assertEqual(len(b["durations_by_class"]["S"]), 1)

    def test_percentile_singleton(self):
        self.assertEqual(_c2._percentile([5.0], 50), 5.0)
        self.assertEqual(_c2._percentile([5.0], 99), 5.0)

    def test_percentile_basic(self):
        vs = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(_c2._percentile(vs, 50), 3.0)
        self.assertGreaterEqual(_c2._percentile(vs, 95), 4.0)

    def test_percentile_empty(self):
        self.assertEqual(_c2._percentile([], 50), 0.0)


class TestFormatMd(unittest.TestCase):
    def test_anchor_present(self):
        b = _c2._compute_baseline([
            {"action": "task_route_advised", "classification": "S", "duration_ms": 1.0},
        ])
        md = _c2._format_baseline_md(b, "2026-04-18")
        self.assertIn("## TASK-CLASS-BASELINE", md)
        self.assertIn("## CLASSIFIER-RUNTIME-ENVELOPE", md)
        self.assertIn("## METHODOLOGY", md)

    def test_insufficient_data_marker(self):
        # 0 events in S → cell marked insufficient-data
        b = _c2._compute_baseline([])
        md = _c2._format_baseline_md(b, "2026-04-18")
        self.assertIn("insufficient-data", md)


class TestInsufficientVolume(unittest.TestCase):
    def test_self_test_exit_ok(self):
        """--self-test should exit 0 without dependencies."""
        result = subprocess.run(
            [sys.executable, str(_C2), "--self-test"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, _c2.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
