"""Tests for ``ceo-diagnose.py`` (PLAN-059 / Round-2 P0).

Vibecoder-friendly health-check CLI; advisory-only; never blocks. Tests
focus on the probe contract: fail-open, status taxonomy, JSON shape.

W7-OPS additions (PLAN-113):
- probe_audit_log: sandbox-green fix (F-6.10-f6a7b8c9)
- probe_incident_signals: SEV/incident signals probe (F-6.10-c3d4e5f6)
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-diagnose.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ceo_diagnose", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CeoDiagnoseSmokeTest(unittest.TestCase):

    def test_script_exists_and_executable(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK), "ceo-diagnose.py must be executable")

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ceo-diagnose", (result.stdout + result.stderr).lower())

    def test_quick_run_completes_under_timeout(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--quick"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        # Exit code may be 0 / 1 / 2 depending on environment; we just
        # require it runs to completion without crashing.
        self.assertIn(result.returncode, (0, 1, 2))
        self.assertIn("ceo-orchestration", result.stdout)

    def test_json_mode_emits_valid_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--quick", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"--json output not valid JSON: {e}\noutput: {result.stdout[:500]}")
        self.assertEqual(parsed.get("schema"), "ceo-diagnose-v1")
        self.assertIn("probes", parsed)
        self.assertIsInstance(parsed["probes"], list)
        for probe in parsed["probes"]:
            self.assertIn(probe["status"], {"green", "yellow", "red", "unknown"})
            self.assertIn("name", probe)
            self.assertIn("summary", probe)


class CeoDiagnoseProbeUnitTest(unittest.TestCase):
    """Per-probe unit tests using direct imports — no subprocess."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_probe_open_plans_returns_tuple(self):
        result = self.mod.probe_open_plans()
        self.assertEqual(len(result), 3)
        status, summary, detail = result
        self.assertIn(status, {"green", "yellow", "red", "unknown"})
        self.assertIsInstance(summary, str)
        self.assertIsInstance(detail, dict)
        self.assertIn("open_count", detail)

    def test_probe_governance_returns_tuple(self):
        result = self.mod.probe_governance()
        self.assertEqual(len(result), 3)
        status, summary, detail = result
        self.assertIn(status, {"green", "yellow", "red", "unknown"})

    def test_probe_audit_log_returns_tuple(self):
        result = self.mod.probe_audit_log()
        self.assertEqual(len(result), 3)

    def test_probe_dispatch_modes_returns_tuple(self):
        result = self.mod.probe_dispatch_modes()
        self.assertEqual(len(result), 3)

    def test_probe_adr_082_acceptance(self):
        # ADR-082 was promoted to ACCEPTED in Session 67 (2026-04-27).
        result = self.mod.probe_adr_082_acceptance()
        status, summary, detail = result
        self.assertIn(status, {"green", "yellow", "red", "unknown"})

    def test_status_glyph_taxonomy(self):
        for k in ("green", "yellow", "red", "unknown"):
            self.assertIn(k, self.mod.STATUS_GLYPH)

    def test_overall_exit_code_red_dominates(self):
        report = [
            ("a", "green", "ok", {}),
            ("b", "red", "fail", {}),
            ("c", "yellow", "warn", {}),
        ]
        self.assertEqual(self.mod.overall_exit_code(report), 2)

    def test_overall_exit_code_yellow_when_no_red(self):
        report = [
            ("a", "green", "ok", {}),
            ("b", "yellow", "warn", {}),
        ]
        self.assertEqual(self.mod.overall_exit_code(report), 1)

    def test_overall_exit_code_green_when_all_green(self):
        report = [
            ("a", "green", "ok", {}),
            ("b", "green", "ok", {}),
        ]
        self.assertEqual(self.mod.overall_exit_code(report), 0)

    def test_probe_audit_log_sandbox_returns_green(self):
        """F-6.10-f6a7b8c9: missing log → green (not unknown) for sandbox/CI."""
        mod = _load_module()
        # Force all resolution candidates to miss by clearing env + patching home.
        with tempfile.TemporaryDirectory() as fake_home:
            old_env = {}
            for var in ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR", "CLAUDE_PROJECT_DIR"):
                old_env[var] = os.environ.pop(var, None)
            old_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = fake_home
                status, summary, detail = mod.probe_audit_log()
            finally:
                os.environ["HOME"] = old_home if old_home is not None else ""
                for var, val in old_env.items():
                    if val is not None:
                        os.environ[var] = val
                    else:
                        os.environ.pop(var, None)
        self.assertEqual(status, "green", f"Expected green for missing log; got {status!r}: {summary}")
        self.assertFalse(detail.get("found", True))

    def test_probe_incident_signals_returns_tuple(self):
        """probe_incident_signals always returns a 3-tuple."""
        mod = _load_module()
        result = mod.probe_incident_signals()
        self.assertEqual(len(result), 3)
        status, summary, detail = result
        self.assertIn(status, {"green", "yellow", "red", "unknown"})
        self.assertIsInstance(summary, str)
        self.assertIsInstance(detail, dict)

    def test_main_has_incident_signals_probe(self):
        """main() must include 'Incident signals' probe (F-6.10-c3d4e5f6 wired)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--quick", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        parsed = json.loads(result.stdout)
        names = [p["name"] for p in parsed["probes"]]
        self.assertIn("Incident signals", names)

    def test_main_has_eight_probes(self):
        """main() now has 8 probes after W7-OPS addition."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--quick", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        parsed = json.loads(result.stdout)
        self.assertEqual(len(parsed["probes"]), 8)


class TestProbeIncidentSignalsUnit(TestEnvContext):
    """Unit tests for probe_incident_signals() with controlled tmpdir fixtures."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.log_path = self.tmpdir / "audit-log.jsonl"
        self.errors_path = self.tmpdir / "audit-log.errors"
        # Point env vars to our tmpdir
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log_path)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.errors_path)
        self.mod = _load_module()

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def _write_log(self, events: list) -> None:
        """Write JSON-L events to the audit log."""
        with self.log_path.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

    def _ts_recent(self) -> str:
        """ISO-8601 timestamp within the last hour."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(time.time() - 300, tz=timezone.utc).isoformat()

    def _ts_old(self) -> str:
        """ISO-8601 timestamp older than 24h."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(time.time() - 25 * 3600, tz=timezone.utc).isoformat()

    def test_no_signals_returns_green(self):
        """Empty log + no errors sidecar → green."""
        self._write_log([])
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "green")
        self.assertEqual(detail["incident_events_24h"], 0)
        self.assertEqual(detail["errors_sidecar_lines"], 0)

    def test_errors_sidecar_present_returns_yellow(self):
        """Non-empty errors sidecar → yellow (write failures detected)."""
        self._write_log([])
        self.errors_path.write_text("error line 1\nerror line 2\n")
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "yellow")
        self.assertEqual(detail["errors_sidecar_lines"], 2)
        self.assertIn("audit write errors", summary)

    def test_incident_declared_event_returns_red(self):
        """incident_declared in last 24h → red."""
        self._write_log([
            {"action": "agent_spawn", "ts": self._ts_recent()},
            {"action": "incident_declared", "ts": self._ts_recent(), "severity": "SEV-1"},
        ])
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "red")
        self.assertGreater(detail["incident_events_24h"], 0)
        self.assertEqual(detail["active_sev"], "SEV-1")

    def test_sev_classified_event_returns_red(self):
        """sev_classified in last 24h → red."""
        self._write_log([
            {"action": "sev_classified", "ts": self._ts_recent(), "sev": "SEV-2"},
        ])
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "red")

    def test_old_incident_events_ignored(self):
        """incident_declared older than 24h → not counted."""
        self._write_log([
            {"action": "incident_declared", "ts": self._ts_old(), "severity": "SEV-1"},
        ])
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "green")
        self.assertEqual(detail["incident_events_24h"], 0)

    def test_incident_resolved_does_not_trigger_red(self):
        """incident_resolved is counted but does not set active_sev → not red."""
        self._write_log([
            {"action": "incident_resolved", "ts": self._ts_recent()},
        ])
        status, summary, detail = self.mod.probe_incident_signals()
        # incident_resolved increments count but active_sev stays None → not red
        self.assertNotEqual(status, "red")

    def test_detail_keys_always_present(self):
        """detail dict always has the three expected keys."""
        self._write_log([])
        _, _, detail = self.mod.probe_incident_signals()
        for key in ("errors_sidecar_lines", "incident_events_24h", "active_sev"):
            self.assertIn(key, detail)

    def test_missing_log_does_not_raise(self):
        """Absent audit-log → fail-open, returns green."""
        # log_path does not exist
        status, summary, detail = self.mod.probe_incident_signals()
        self.assertEqual(status, "green")


if __name__ == "__main__":
    unittest.main()
