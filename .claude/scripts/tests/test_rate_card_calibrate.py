"""Tests for ``rate-card-calibrate.py`` — PLAN-135 W5 unit o8o11o12 (O8).

Covers the rate-card drift calibrator:
- the LIVE tree is clean (S227 rates ratified across both files);
- a simulated S227 stale pin (opus-4-7 still at $15/$75) is caught as drift;
- a fixture model absent from a rate-card file is an ``absent`` coverage gap;
- the per-1k -> per-Mtok unit bridge is applied (provider-pricing comparison);
- ``--live`` PRINTS the PENDING-OWNER recipe and never touches the network;
- a missing/corrupt fixtures file fails OPEN (advisory, exit 0);
- ``--check`` returns 1 on drift/absent, 0 on clean.

All assertions hold WITHOUT network and WITHOUT any framework ceremony.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "rate-card-calibrate.py"
LIVE_FIXTURES = REPO_ROOT / ".claude" / "scripts" / "rate-card-fixtures.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("rate_card_calibrate", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixtures(rates: dict, tol: float = 0.005) -> dict:
    return {"_meta": {"schema": 1, "tolerance_per_mtok": tol}, "rates": rates}


def _cost_table_text(rows: dict) -> str:
    lines = ["schema_version: 3", "models:"]
    for model, (i, o) in rows.items():
        lines += [f"  {model}:",
                  f"    input_per_mtok: {i:.2f}",
                  f"    output_per_mtok: {o:.2f}",
                  "    tier: x"]
    return "\n".join(lines) + "\n"


def _pricing_text(rows: dict) -> str:
    # rows are per-Mtok; the table is per-1k -> divide by 1000.
    lines = ["| Provider | Model | Input $/1k | Output $/1k |",
             "|---|---|---|---|"]
    for model, (i, o) in rows.items():
        lines.append(f"| Anthropic | {model} | {i / 1000.0} | {o / 1000.0} |")
    return "\n".join(lines) + "\n"


class RateCardCalibrateTest(unittest.TestCase):
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

    def test_live_tree_is_clean(self):
        # The shipped fixtures must match the live rate-card pair (S227 ratified).
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_clean_when_all_match(self):
        rates = {"claude-fable-5": {"input_per_mtok": 10.0, "output_per_mtok": 50.0}}
        with tempfile.TemporaryDirectory() as td:
            fx = self.mod.load_fixtures(self._write(td, "fx.json", json.dumps(
                _fixtures({k: v for k, v in rates.items()}))))
            ct = self.mod.parse_cost_table(self._write(
                td, "ct.yaml", _cost_table_text({"claude-fable-5": (10.0, 50.0)})))
            pp = self.mod.parse_provider_pricing(self._write(
                td, "pp.md", _pricing_text({"claude-fable-5": (10.0, 50.0)})))
            report = self.mod.calibrate(fx, ct, pp)
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["drift_count"], 0)

    def test_s227_stale_pin_is_drift(self):
        # The exact S227 class: opus-4-7 ratified at 5/25 but on-disk still 15/75.
        with tempfile.TemporaryDirectory() as td:
            fx = self.mod.load_fixtures(self._write(td, "fx.json", json.dumps(
                _fixtures({"claude-opus-4-7": {"input_per_mtok": 5.0, "output_per_mtok": 25.0}}))))
            ct = self.mod.parse_cost_table(self._write(
                td, "ct.yaml", _cost_table_text({"claude-opus-4-7": (15.0, 75.0)})))
            pp = self.mod.parse_provider_pricing(self._write(
                td, "pp.md", _pricing_text({"claude-opus-4-7": (15.0, 75.0)})))
            report = self.mod.calibrate(fx, ct, pp)
        self.assertEqual(report["status"], "drift")
        self.assertGreaterEqual(report["drift_count"], 1)
        self.assertIn("claude-opus-4-7", report["summary"])

    def test_unit_bridge_catches_per1k_confusion(self):
        # If provider-pricing accidentally held the per-Mtok number in the
        # per-1k column, the *1000 bridge surfaces a huge drift (not a match).
        with tempfile.TemporaryDirectory() as td:
            fx = self.mod.load_fixtures(self._write(td, "fx.json", json.dumps(
                _fixtures({"claude-fable-5": {"input_per_mtok": 10.0, "output_per_mtok": 50.0}}))))
            ct = self.mod.parse_cost_table(self._write(
                td, "ct.yaml", _cost_table_text({"claude-fable-5": (10.0, 50.0)})))
            # Wrong: 10.0 in the $/1k column => parsed as 10000 per-Mtok.
            pp_text = ("| Provider | Model | Input $/1k | Output $/1k |\n"
                       "|---|---|---|---|\n"
                       "| Anthropic | claude-fable-5 | 10.0 | 50.0 |\n")
            pp = self.mod.parse_provider_pricing(self._write(td, "pp.md", pp_text))
            report = self.mod.calibrate(fx, ct, pp)
        self.assertEqual(report["status"], "drift")

    def test_absent_model_is_coverage_gap(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self.mod.load_fixtures(self._write(td, "fx.json", json.dumps(
                _fixtures({"claude-ghost-9": {"input_per_mtok": 1.0, "output_per_mtok": 2.0}}))))
            ct = self.mod.parse_cost_table(self._write(
                td, "ct.yaml", _cost_table_text({"claude-fable-5": (10.0, 50.0)})))
            pp = self.mod.parse_provider_pricing(self._write(
                td, "pp.md", _pricing_text({"claude-fable-5": (10.0, 50.0)})))
            report = self.mod.calibrate(fx, ct, pp)
        self.assertEqual(report["status"], "absent")
        self.assertGreaterEqual(report["absent_count"], 1)

    def test_missing_fixtures_fails_open(self):
        report = self.mod.calibrate(None, {}, {})
        self.assertTrue(report["fail_open"])
        self.assertEqual(report["status"], "clean")
        rc = self.mod.main(["--fixtures", "/nonexistent-xyz/fx.json", "--check"])
        self.assertEqual(rc, 0)

    def test_corrupt_fixtures_fails_open(self):
        with tempfile.TemporaryDirectory() as td:
            bad = self._write(td, "bad.json", "{not json")
            self.assertIsNone(self.mod.load_fixtures(bad))

    def test_check_returns_one_on_drift(self):
        with tempfile.TemporaryDirectory() as td:
            fxp = self._write(td, "fx.json", json.dumps(
                _fixtures({"claude-opus-4-7": {"input_per_mtok": 5.0, "output_per_mtok": 25.0}})))
            ctp = self._write(td, "ct.yaml", _cost_table_text({"claude-opus-4-7": (15.0, 75.0)}))
            ppp = self._write(td, "pp.md", _pricing_text({"claude-opus-4-7": (15.0, 75.0)}))
            rc = self.mod.main(["--fixtures", fxp, "--cost-table", ctp,
                                "--pricing", ppp, "--check"])
        self.assertEqual(rc, 1)

    def test_live_prints_recipe_no_network(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--live"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("PENDING-OWNER", result.stdout)
        self.assertIn("Usage/Cost API", result.stdout)

    def test_json_mode_valid(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
        )
        data = json.loads(result.stdout)
        self.assertIn("status", data)
        self.assertIn("models", data)

    @staticmethod
    def _write(td: str, name: str, content: str) -> str:
        p = Path(td) / name
        p.write_text(content, encoding="utf-8")
        return str(p)


if __name__ == "__main__":
    unittest.main()
