"""Test that run-skill-benchmark emits benchmark_run audit event.

Sprint 5 A.1. We exercise only `_emit_benchmark_audit_event` (the
helper) because the full runner requires a real Anthropic client.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))

_RSB_PATH = _SCRIPTS / "run-skill-benchmark.py"
_spec = importlib.util.spec_from_file_location("run_skill_benchmark", _RSB_PATH)
rsb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rsb)


class BenchmarkEmitTest(unittest.TestCase):

    def setUp(self):
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmp = Path(tempfile.mkdtemp(prefix="bench-emit-test-"))
        self.log_path = self.tmp / "audit-log.jsonl"
        self._snap = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_LOG_LOCK",
                "CEO_AUDIT_LOG_ERR",
                "CEO_AUDIT_LOG_DIR",
                "CEO_AUDIT_SYNC_MODE",
            )
        }
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log_path)
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.tmp / "audit.lock")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.tmp / "audit.err")
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.tmp)

    def tearDown(self):
        for k, v in self._snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_events(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _fake_results(self, passed=8, total=10, skill="testing-strategy"):
        return {
            "benchmark": {"skill": skill, "version": "1.0.0", "owner": "qa"},
            "model": "claude-opus-4-6",
            "repetitions": 3,
            "overall": {"passed": passed, "total": total, "score": passed / total, "health": "OK"},
            "scenarios": [
                {"id": f"s{i}", "passed": i < passed, "median_score": 1.0 if i < passed else 0.0}
                for i in range(total)
            ],
            "timestamp": "2026-04-13T12:00:00Z",
        }

    def test_emit_writes_benchmark_run_event(self):
        args = argparse.Namespace(floor=0.6)
        rsb._emit_benchmark_audit_event(
            self._fake_results(),
            args,
            duration_s=1.234,
            lessons_written=2,
        )
        events = self._read_events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["action"], "benchmark_run")
        self.assertEqual(ev["skill"], "testing-strategy")
        self.assertEqual(ev["pass_count"], 8)
        self.assertEqual(ev["fail_count"], 2)
        # Float fields are now int-encoded per canonical_json no-float invariant.
        self.assertEqual(ev["pass_rate_bps"], 800)
        self.assertEqual(ev["floor_bps"], 600)
        self.assertEqual(ev["duration_ms"], 1234)
        self.assertEqual(ev["lessons_written"], 2)

    def test_emit_is_fail_open_when_audit_unwritable(self):
        readonly = self.tmp / "ro"
        readonly.mkdir(mode=0o500)
        try:
            os.environ["CEO_AUDIT_LOG_PATH"] = str(readonly / "log.jsonl")
            args = argparse.Namespace(floor=None)
            # Must not raise
            rsb._emit_benchmark_audit_event(
                self._fake_results(),
                args,
                duration_s=0.1,
                lessons_written=0,
            )
        finally:
            readonly.chmod(0o700)

    def test_floor_none_becomes_zero(self):
        args = argparse.Namespace(floor=None)
        rsb._emit_benchmark_audit_event(
            self._fake_results(passed=5, total=5),
            args,
            duration_s=0.5,
            lessons_written=0,
        )
        events = self._read_events()
        # floor=None becomes 0.0 → 0 bps.
        self.assertEqual(events[0]["floor_bps"], 0)

    def test_median_score_calculation(self):
        """PLAN-133 C1 — `median_score_bps` now carries the WORST-of-N
        aggregation across scenarios (conservative floor), not the median.

        Default aggregation is "worst": min of [1.0,1.0,1.0,0.0,0.0] = 0.0.
        (Migrated from the legacy median-of-per-scenario assertion, which
        would have been 1.0 for the same fixture.)
        """
        # Ensure default (no env pin → worst).
        self._snap_agg = os.environ.pop("CEO_BENCH_AGGREGATION", None)
        try:
            results = self._fake_results(passed=3, total=5)
            # Scenarios 0-2 passed (score 1.0), scenarios 3-4 failed (0.0)
            # worst-of-N across scenarios = min([0,0,1,1,1]) = 0.0
            args = argparse.Namespace(floor=0.5)
            rsb._emit_benchmark_audit_event(
                results, args, duration_s=0.0, lessons_written=0
            )
            events = self._read_events()
            self.assertEqual(events[0]["median_score_bps"], 0)
            # Provenance fields are emitted (additive forward-compat).
            self.assertEqual(events[0]["aggregation"], "worst")
            self.assertIn("flaky_count", events[0])
        finally:
            if self._snap_agg is not None:
                os.environ["CEO_BENCH_AGGREGATION"] = self._snap_agg

    def test_median_aggregation_escape_hatch(self):
        """CEO_BENCH_AGGREGATION=median restores the legacy median floor."""
        snap = os.environ.get("CEO_BENCH_AGGREGATION")
        os.environ["CEO_BENCH_AGGREGATION"] = "median"
        try:
            results = self._fake_results(passed=3, total=5)
            # median of [0.0,0.0,1.0,1.0,1.0] = 1.0 → 1000 bps
            args = argparse.Namespace(floor=0.5)
            rsb._emit_benchmark_audit_event(
                results, args, duration_s=0.0, lessons_written=0
            )
            events = self._read_events()
            self.assertEqual(events[0]["median_score_bps"], 1000)
            self.assertEqual(events[0]["aggregation"], "median")
        finally:
            if snap is None:
                os.environ.pop("CEO_BENCH_AGGREGATION", None)
            else:
                os.environ["CEO_BENCH_AGGREGATION"] = snap

    def test_flaky_count_emitted(self):
        """`flaky_count` reflects scenarios flagged flaky in the results."""
        snap = os.environ.pop("CEO_BENCH_AGGREGATION", None)
        try:
            results = self._fake_results(passed=2, total=3)
            results["scenarios"][0]["flaky"] = True
            results["scenarios"][1]["flaky"] = True
            args = argparse.Namespace(floor=0.0)
            rsb._emit_benchmark_audit_event(
                results, args, duration_s=0.0, lessons_written=0
            )
            events = self._read_events()
            self.assertEqual(events[0]["flaky_count"], 2)
        finally:
            if snap is not None:
                os.environ["CEO_BENCH_AGGREGATION"] = snap


if __name__ == "__main__":
    unittest.main()
