"""Tests for ``check-substrate-watch.py`` — PLAN-135 W5 unit o8o11o12 (O12).

Covers the substrate drift watch (Claude Code + Agent-SDK changelog ledger):
- the seeded ledger reports ``stale-ledger`` until an Owner --refresh;
- a fresh ledger with matching installed versions reports ``current``;
- an installed version differing from ``last_seen`` reports ``drift``;
- ``--refresh`` PRINTS the recipe and never fetches/writes;
- a missing/corrupt ledger fails OPEN (advisory, exit 0);
- ``--check`` returns 1 on stale/drift, 0 on current;
- the version probe is fail-soft (missing binary -> note, never raises).

All assertions hold WITHOUT any network and WITHOUT the framework ceremony.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-substrate-watch.py"
LIVE_LEDGER = REPO_ROOT / ".claude" / "scripts" / "substrate-watch.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_substrate_watch", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_ledger(path: Path, *, source_stale: bool, last_seen_version: str,
                  key: str = "claude_code") -> None:
    path.write_text(json.dumps({
        "_meta": {
            "schema": 1, "source_stale": source_stale,
            "refresh_recipe": "RECIPE-HERE",
        },
        "components": [{
            "key": key, "label": "Claude Code CLI",
            "last_seen": {"version": last_seen_version, "date": "2026-06-01"},
        }],
    }), encoding="utf-8")


class _FakeProc:
    """Stand-in for subprocess.CompletedProcess at the _run_version_cmd seam."""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@contextlib.contextmanager
def _patched_probe(mod, result):
    """Patch mod._run_version_cmd to return `result` (a _FakeProc) or, if it is
    an Exception, raise it. NO real binary is ever executed (Codex R2 P0: the
    probe argv is code-defined; tests script its OUTPUT, never inject a command)."""
    orig = mod._run_version_cmd

    def fake(argv):
        if isinstance(result, Exception):
            raise result
        return result

    mod._run_version_cmd = fake
    try:
        yield
    finally:
        mod._run_version_cmd = orig


class SubstrateWatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_script_exists_and_help(self):
        self.assertTrue(SCRIPT.is_file())
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)

    def test_live_seeded_ledger_is_stale(self):
        # The shipped ledger is seeded source_stale=true (no network at build).
        ledger = self.mod.load_ledger(str(LIVE_LEDGER))
        self.assertIsNotNone(ledger)
        report = self.mod.build_report(ledger, probe_installed=False)
        self.assertEqual(report["status"], "stale-ledger")
        self.assertTrue(report["source_stale"])
        # PLAN-142 added the 4th component (codex_cli) to substrate-watch.json.
        self.assertEqual(len(report["components"]), 4)

    def test_missing_ledger_fails_open_exit_zero(self):
        report = self.mod.build_report(None)
        self.assertTrue(report["fail_open"])
        self.assertEqual(report["status"], "current")
        rc = self.mod.main(["--ledger", "/nonexistent-xyz/substrate.json", "--check"])
        self.assertEqual(rc, 0)  # fail-open: infra problem is not a maintenance flag

    def test_corrupt_ledger_fails_open(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            report = self.mod.build_report(self.mod.load_ledger(str(bad)))
        self.assertTrue(report["fail_open"])

    def test_fresh_ledger_matching_install_is_current(self):
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "led.json"
            _write_ledger(led, source_stale=False, last_seen_version="9.9.9")
            # code-defined probe resolves installed=9.9.9 == last_seen.
            with _patched_probe(self.mod, _FakeProc(0, "claude 9.9.9 (abc)")):
                report = self.mod.build_report(
                    self.mod.load_ledger(str(led)), probe_installed=True
                )
        self.assertEqual(report["status"], "current")
        self.assertEqual(report["components"][0]["installed_version"], "9.9.9")
        self.assertFalse(report["components"][0]["drift"])

    def test_fresh_ledger_mismatched_install_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "led.json"
            _write_ledger(led, source_stale=False, last_seen_version="1.0.0")
            with _patched_probe(self.mod, _FakeProc(0, "2.0.0")):
                report = self.mod.build_report(
                    self.mod.load_ledger(str(led)), probe_installed=True
                )
        self.assertEqual(report["status"], "drift")
        self.assertTrue(report["components"][0]["drift"])

    def test_check_returns_one_on_stale_or_drift(self):
        rc = self.mod.main(["--ledger", str(LIVE_LEDGER), "--check"])
        self.assertEqual(rc, 1)  # seeded ledger is stale

    def test_check_returns_zero_on_current(self):
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "led.json"
            _write_ledger(led, source_stale=False, last_seen_version="3.3.3")
            with _patched_probe(self.mod, _FakeProc(0, "3.3.3")):
                rc = self.mod.main(["--ledger", str(led), "--probe-installed", "--check"])
        self.assertEqual(rc, 0)

    def test_refresh_prints_recipe_and_exits_zero_no_write(self):
        before = LIVE_LEDGER.read_bytes()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--refresh"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("PENDING-OWNER", result.stdout)
        # --refresh must NOT mutate the ledger (it only prints).
        self.assertEqual(LIVE_LEDGER.read_bytes(), before)

    def test_probe_failsoft_on_unknown_key(self):
        # An unregistered component key resolves NO probe (never executes).
        version, note = self.mod._probe_installed("not-a-registered-component")
        self.assertIsNone(version)
        self.assertIn("no probe registered", note)

    def test_probe_failsoft_on_missing_binary(self):
        # Registered key, binary absent -> _run_version_cmd raises OSError ->
        # _probe_installed degrades to (None, note), never raises.
        with _patched_probe(self.mod, FileNotFoundError("claude")):
            version, note = self.mod._probe_installed("claude_code")
        self.assertIsNone(version)
        self.assertTrue(note)

    def test_ledger_local_probe_is_never_executed(self):
        # Codex R2 P0 regression guard: a malicious ledger CANNOT inject a
        # command. The probe argv is taken from code (_PROBE_ARGV[key]); the
        # ledger's `local_probe` field is ignored entirely.
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "led.json"
            led.write_text(json.dumps({
                "_meta": {"schema": 1, "source_stale": False, "refresh_recipe": "x"},
                "components": [{
                    "key": "claude_code", "label": "CC",
                    "last_seen": {"version": "9.9.9", "date": "2026-06-01"},
                    "local_probe": "python3 -c \"import os; os.system('touch /tmp/PWNED-substrate')\"",
                }],
            }), encoding="utf-8")
            captured = {}

            def fake(argv):
                captured["argv"] = list(argv)
                return _FakeProc(0, "9.9.9")

            orig = self.mod._run_version_cmd
            self.mod._run_version_cmd = fake
            try:
                report = self.mod.build_report(
                    self.mod.load_ledger(str(led)), probe_installed=True
                )
            finally:
                self.mod._run_version_cmd = orig
        # the code-defined probe ran — NOT the ledger's injected local_probe
        self.assertEqual(captured["argv"], self.mod._PROBE_ARGV["claude_code"])
        self.assertNotIn("os.system", " ".join(captured["argv"]))
        self.assertEqual(report["components"][0]["installed_version"], "9.9.9")

    def test_no_probe_when_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "led.json"
            _write_ledger(led, source_stale=False, last_seen_version="1.0.0")
            report = self.mod.build_report(
                self.mod.load_ledger(str(led)), probe_installed=False
            )
        # Probe off -> installed stays None, no false drift flagged.
        self.assertIsNone(report["components"][0]["installed_version"])
        self.assertFalse(report["components"][0]["drift"])
        self.assertEqual(report["status"], "current")

    def test_json_mode_is_valid_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json", "--ledger", str(LIVE_LEDGER)],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(result.stdout)
        self.assertIn("status", data)
        self.assertIn("components", data)


if __name__ == "__main__":
    unittest.main()
