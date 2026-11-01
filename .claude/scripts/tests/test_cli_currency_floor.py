"""PLAN-196: stable Codex package currency is not payload attestation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _lib import cli_currency
from _lib.testing import TestEnvContext
from _subprocess_helpers import run_in_process_group


_HOOKS = Path(__file__).resolve().parents[2] / "hooks"


class TestCliCurrencyFloor(TestEnvContext):
    def test_fu144_compare_semver_accepts_floor_and_newer_stable(self):
        self.assertEqual(cli_currency.compare_semver("0.160.0", "0.160.0"), 0)
        self.assertEqual(cli_currency.compare_semver("0.166.0", "0.160.0"), 1)
        self.assertEqual(cli_currency.compare_semver("1.0.0", "0.160.0"), 1)

    def test_fu144_compare_semver_rejects_prerelease_and_malformed(self):
        for version in ("0.166.0-rc.1", "0.166", "version 0.166.0", ""):
            self.assertIsNone(cli_currency.compare_semver(version, "0.160.0"))

    def test_fu144_qualified_package_only_meets_currency_floor(self):
        payload = self.project_dir / "vendor" / "codex"
        payload.parent.mkdir(parents=True)
        payload.write_bytes(b"payload")
        package = payload.parent / "package.json"
        package.write_text(json.dumps({"name": "@openai/codex", "version": "0.166.0"}), encoding="utf-8")
        self.assertEqual(cli_currency.compatible_package_version(payload, None), "0.166.0")
        package.write_text(json.dumps({"name": "other", "version": "1.0.0"}), encoding="utf-8")
        self.assertIsNone(cli_currency.compatible_package_version(payload, None))

    def test_fu144_process_group_observes_stable_parse_contract(self):
        env = self.subprocess_env(PYTHONPATH=str(_HOOKS))
        result = run_in_process_group(
            [sys.executable, "-c", "from _lib.cli_currency import parse_semver; print(parse_semver('0.166.0-rc.1'))"],
            timeout=30, capture_output=True, text=True, env=env,
        )
        self.assertEqual((result.returncode, result.stdout.strip(), result.stderr), (0, "None", ""))
