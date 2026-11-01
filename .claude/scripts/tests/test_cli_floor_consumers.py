"""Onda6B floor-consumer contracts (fu144)."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REP = _module("repin_floor", ".claude/scripts/re-pin-codex.py")
DRIFT = _module("drift_floor", ".claude/scripts/check-substrate-drift.py")
WATCH = _module("watch_floor", ".claude/scripts/check-substrate-watch.py")


class TestCliFloorConsumers(TestEnvContext):
    def test_fu144_repin_preserves_unbounded_floor(self) -> None:
        prefix, lower, upper = REP.parse_pin("# current\n>=0.160.0\n")
        self.assertEqual((prefix, lower, upper), (["# current"], "0.160.0", None))
        self.assertEqual(
            REP.plan_range(lower, upper, (0, 166, 0)), (">=0.160.0,<0.167.0", True)
        )

    def test_fu144_drift_marks_newer_unbounded_release_info(self) -> None:
        findings = DRIFT._codex_installed_findings(
            self.project_dir,
            {"package_version": "0.160.0", "range": ">=0.160.0"},
            "0.166.0",
        )
        self.assertEqual([(row["kind"], row["severity"]) for row in findings], [
            ("CODEX_INSTALLED_COMPATIBLE", "info")
        ])
        self.assertEqual(findings[0]["floor"], ">=0.160.0")

    def test_fu144_watch_newer_codex_is_compatible_not_drift(self) -> None:
        ledger = {"_meta": {}, "components": [{
            "key": "codex_cli", "label": "Codex", "last_seen": {
                "version": "0.160.0", "date": "2026-10-01"
            }
        }]}
        with mock.patch.object(WATCH, "_probe_installed", return_value=("0.166.0", "ok")):
            report = WATCH.build_report(ledger, probe_installed=True)
        self.assertEqual(report["status"], "current")
        self.assertFalse(report["components"][0]["drift"])
        self.assertEqual(report["components"][0]["currency"], "compatible")

    def test_fu144_harness_uses_canonical_or_floor_only_fallback(self) -> None:
        harness = REPO_ROOT / "scripts" / "_codex_harness.sh"
        fallback = subprocess.run(
            ["bash", "-c", 'source "$1"; SOURCE_DIR="$2"; _codex_pin_range', "--",
             str(harness), str(self.project_dir)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertEqual(fallback.stdout.strip(), ">=0.160.0")

    def test_fu144_pair_gate_reports_compatible_without_hash_claim(self) -> None:
        gate = self.project_dir / ".claude/scripts/local/pair-rail-gate.sh"
        gate.parent.mkdir(parents=True)
        shutil.copy(REPO_ROOT / ".claude/scripts/local/pair-rail-gate.sh", gate)
        gov = self.project_dir / ".claude/governance"
        gov.mkdir(parents=True)
        (gov / "codex-cli-pin.txt").write_text(">=0.160.0\n", encoding="utf-8")
        (gov / "codex-cli-pin-manifest.json").write_text("{}\n", encoding="utf-8")
        hook = self.project_dir / ".claude/hooks/check_pair_rail.py"
        hook.parent.mkdir(parents=True)
        hook.write_text(
            "import json\nprint(json.dumps({'status': 'compatible'}))\n", encoding="utf-8"
        )
        fake_bin = self._tmp_root / "bin"
        fake_bin.mkdir()
        codex = fake_bin / "codex"
        codex.write_text("#!/bin/sh\necho 'codex 0.166.0'\n", encoding="utf-8")
        codex.chmod(0o755)
        auth = self.home_dir / ".codex"
        auth.mkdir(parents=True)
        (auth / "auth.json").write_text("{}\n", encoding="utf-8")
        env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"])
        proc = subprocess.run(["bash", str(gate), "--phase", "6"], cwd=self.project_dir,
                              env=env, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("version-floor compatible", proc.stdout)
        self.assertNotIn("payload sha256 matches", proc.stdout)


if __name__ == "__main__":
    unittest.main()
