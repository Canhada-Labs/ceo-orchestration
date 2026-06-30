"""Tests for ``audit-telemetry.py`` (PLAN-061 / ADR-082 monitoring)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "audit-telemetry.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_telemetry", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk_event(action: str, ts_offset_seconds: int, **extra) -> dict:
    """Build a synthetic audit-log event with an offset from now."""
    ts = (datetime.now(timezone.utc) + timedelta(seconds=ts_offset_seconds)).isoformat()
    base = {"action": action, "ts": ts, "event_schema": "v2"}
    base.update(extra)
    return base


def _write_log(path: Path, events: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


class AuditTelemetryUnitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_parse_window_24h(self):
        self.assertEqual(self.mod.parse_window("24h"), 24 * 3600)

    def test_parse_window_7d(self):
        self.assertEqual(self.mod.parse_window("7d"), 7 * 86400)

    def test_parse_window_30m(self):
        self.assertEqual(self.mod.parse_window("30m"), 30 * 60)

    def test_parse_window_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.mod.parse_window("foo")
        with self.assertRaises(ValueError):
            self.mod.parse_window("1y")

    def test_iso_to_epoch_handles_z_suffix(self):
        ts = "2026-04-27T12:34:56Z"
        result = self.mod.iso_to_epoch(ts)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)

    def test_iso_to_epoch_invalid_returns_none(self):
        self.assertIsNone(self.mod.iso_to_epoch("not-a-date"))
        self.assertIsNone(self.mod.iso_to_epoch(""))

    def test_percentile_basic(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(self.mod.percentile(values, 50), 30.0)
        # p95 of 5 values: index round(0.95 * 4) = round(3.8) = 4 → 50.0
        self.assertAlmostEqual(self.mod.percentile(values, 95), 50.0)

    def test_percentile_empty_returns_none(self):
        self.assertIsNone(self.mod.percentile([], 50))


class AuditTelemetryCollectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_collect_aggregates_within_window(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [
                _mk_event("agent_spawn", -3600, archetype="qa-architect", dispatch_mode="mitigated", hook_duration_ms=42),
                _mk_event("agent_spawn", -1800, archetype="qa-architect", dispatch_mode="mitigated", hook_duration_ms=55),
                _mk_event("agent_spawn", -900, archetype="code-reviewer", dispatch_mode="native", hook_duration_ms=120),
                _mk_event("agent_spawn", -100, archetype="security-engineer", dispatch_mode="mitigated", hook_duration_ms=18),
            ]
            _write_log(log, events)
            report = self.mod.collect_telemetry(log, window_seconds=2 * 3600)
            self.assertEqual(report["totals"]["spawns"], 4)
            self.assertEqual(report["by_mode"]["mitigated"], 3)
            self.assertEqual(report["by_mode"]["native"], 1)
            self.assertIn("qa-architect", report["by_archetype"])
            qa = report["by_archetype"]["qa-architect"]
            self.assertEqual(qa["total"], 2)
            self.assertEqual(qa["by_mode"]["mitigated"], 2)
            self.assertIsNotNone(qa["p50_ms"])

    def test_collect_excludes_events_outside_window(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [
                _mk_event("agent_spawn", -100, archetype="qa-architect", dispatch_mode="mitigated"),
                _mk_event("agent_spawn", -86400 * 30, archetype="qa-architect", dispatch_mode="mitigated"),
            ]
            _write_log(log, events)
            report = self.mod.collect_telemetry(log, window_seconds=3600)
            self.assertEqual(report["totals"]["spawns"], 1)

    def test_collect_handles_unknown_dispatch_mode(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [
                _mk_event("agent_spawn", -60, archetype="qa-architect"),  # no dispatch_mode
            ]
            _write_log(log, events)
            report = self.mod.collect_telemetry(log, window_seconds=3600)
            self.assertEqual(report["by_mode"].get("unknown"), 1)

    def test_collect_counts_fabrication_events(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [
                _mk_event("agent_spawn", -100, archetype="qa-architect", dispatch_mode="native"),
                _mk_event("subagent_fabrication", -90, archetype="qa-architect"),
                _mk_event("agent_spawn", -80, archetype="qa-architect", dispatch_mode="native"),
            ]
            _write_log(log, events)
            report = self.mod.collect_telemetry(log, window_seconds=3600)
            self.assertEqual(report["totals"]["fabrication_events"], 1)
            self.assertEqual(report["totals"]["spawns"], 2)
            self.assertGreater(report["totals"]["fabrication_rate_pct"], 0)

    def test_collect_archetype_filter(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [
                _mk_event("agent_spawn", -100, archetype="qa-architect", dispatch_mode="mitigated"),
                _mk_event("agent_spawn", -90, archetype="code-reviewer", dispatch_mode="native"),
            ]
            _write_log(log, events)
            report = self.mod.collect_telemetry(log, window_seconds=3600, archetype_filter="qa-architect")
            self.assertEqual(len(report["by_archetype"]), 1)
            self.assertIn("qa-architect", report["by_archetype"])
            self.assertNotIn("code-reviewer", report["by_archetype"])

    def test_collect_handles_corrupt_lines_gracefully(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            with log.open("w") as f:
                f.write("not-json-at-all\n")
                f.write(json.dumps(_mk_event("agent_spawn", -60, archetype="qa-architect", dispatch_mode="mitigated")) + "\n")
                f.write("\n")  # blank line
                f.write('{"action":"agent_spawn","ts":"invalid-ts"}\n')
            report = self.mod.collect_telemetry(log, window_seconds=3600)
            self.assertEqual(report["totals"]["spawns"], 1)


class AuditTelemetryCliTest(unittest.TestCase):

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0)

    def test_invalid_window_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            log.write_text("")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--window", "foo", "--log-path", str(log)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(REPO_ROOT),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid window", (result.stdout + result.stderr).lower())

    def test_json_output_is_valid(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit.jsonl"
            events = [_mk_event("agent_spawn", -60, archetype="qa-architect", dispatch_mode="mitigated")]
            _write_log(log, events)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--log-path", str(log), "--json"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(result.returncode, 0)
            parsed = json.loads(result.stdout)
            # audit-v2 Wave B C3-P0-02 (2026-04-27) — schema bumped v1 → v2
            # to add per-archetype cost rollup fields.
            self.assertEqual(parsed["schema"], "audit-telemetry-v2")


if __name__ == "__main__":
    unittest.main()
