"""Tests for ``env-inventory-check.py`` — PLAN-135 W5 unit o8o11o12 (O8).

Covers:
- the token scanner finds CLAUDE_*/ANTHROPIC_*/CEO_* names deterministically,
  skips test/fixture trees, and rejects concatenation fragments (trailing _);
- --generate writes a valid inventory; a follow-up --check is clean;
- drift classes: NEW (consumed-not-inventoried) and STALE (inventoried-only);
- exit-code contract: report mode always 0; --check 1 on drift or missing
  inventory; corrupt inventory fail-opens to 0 (infra);
- live-tree smoke: the script runs against this checkout and emits valid JSON.

Env-hygiene: mutates environment never; all scans run in temp trees.
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
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "env-inventory-check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("env_inventory_check", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk_tree(td: str) -> str:
    """Build a minimal fake repo tree with known env tokens."""
    root = Path(td)
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "check_thing.py").write_text(
        'import os\n'
        'A = os.environ.get("CEO_FAKE_FLAG")\n'
        'B = os.environ.get("ANTHROPIC_API_KEY")\n'
        '# fragment must NOT be collected: "CEO_AUDIT_" + name\n'
        'PREFIX = "CEO_AUDIT_"\n',
        encoding="utf-8",
    )
    tests_dir = hooks / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text(
        'os.environ["CEO_TESTS_ONLY_VAR"] = "1"\n', encoding="utf-8"
    )
    scripts = root / ".claude" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "tool.sh").write_text(
        'echo "${CLAUDE_PROJECT_DIR:-}" "$CEO_FAKE_FLAG"\n', encoding="utf-8"
    )
    return str(root)


class EnvInventoryScanTest(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_scan_finds_known_vars_and_skips_tests(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            consumed = self.mod.scan_consumed(root)
        self.assertIn("CEO_FAKE_FLAG", consumed)
        self.assertIn("ANTHROPIC_API_KEY", consumed)
        self.assertIn("CLAUDE_PROJECT_DIR", consumed)
        # tests/ pruned
        self.assertNotIn("CEO_TESTS_ONLY_VAR", consumed)
        # trailing-underscore concatenation fragment rejected
        self.assertNotIn("CEO_AUDIT_", consumed)

    def test_scan_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            a = self.mod.scan_consumed(root)
            b = self.mod.scan_consumed(root)
        self.assertEqual(json.dumps(a, sort_keys=False), json.dumps(b, sort_keys=False))

    def test_evidence_paths_are_relative_and_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            consumed = self.mod.scan_consumed(root)
        for paths in consumed.values():
            self.assertEqual(paths, sorted(paths))
            for p in paths:
                self.assertFalse(os.path.isabs(p))


class EnvInventoryDiffTest(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_clean_diff(self):
        consumed = {"CEO_A": ["x.py"], "CEO_B": ["y.py"]}
        inv = self.mod.build_inventory(consumed, "2026-06-12")
        report = self.mod.diff_inventory(consumed, inv)
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["counts"]["new"], 0)
        self.assertEqual(report["counts"]["stale"], 0)

    def test_new_and_stale_classes(self):
        inv = self.mod.build_inventory({"CEO_OLD": ["x.py"]}, "2026-06-12")
        report = self.mod.diff_inventory({"CEO_NEW": ["z.py"]}, inv)
        self.assertEqual(report["status"], "drift")
        self.assertEqual([r["name"] for r in report["new"]], ["CEO_NEW"])
        self.assertEqual([r["name"] for r in report["stale"]], ["CEO_OLD"])


class EnvInventoryCliTest(TestEnvContext):
    """Exit-code contract via main() in-process (no subprocess churn)."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def _run(self, argv):
        return self.mod.main(argv)

    def test_generate_then_check_is_clean_exit_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            inv = str(Path(td) / "inv.json")
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", inv, "--generate"]), 0)
            data = json.loads(Path(inv).read_text(encoding="utf-8"))
            self.assertIn("CEO_FAKE_FLAG", data["vars"])
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", inv, "--check"]), 0)

    def test_check_exits_one_on_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            inv = str(Path(td) / "inv.json")
            self._run(["--repo-root", root, "--inventory", inv, "--generate"])
            # add a new consumed var AFTER generation
            extra = Path(root) / ".claude" / "scripts" / "new.py"
            extra.write_text('os.environ.get("CEO_BRAND_NEW_VAR")\n', encoding="utf-8")
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", inv, "--check"]), 1)
            # report mode stays advisory exit 0 on the same drift
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", inv]), 0)

    def test_check_exits_one_when_inventory_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            inv = str(Path(td) / "absent.json")
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", inv, "--check"]), 1)
            self.assertEqual(self._run(["--repo-root", root, "--inventory", inv]), 0)

    def test_corrupt_inventory_fails_open_exit_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(td)
            inv = Path(td) / "corrupt.json"
            inv.write_text("{not json", encoding="utf-8")
            self.assertEqual(self._run(
                ["--repo-root", root, "--inventory", str(inv), "--check"]), 0)


class EnvInventoryLiveSmokeTest(TestEnvContext):
    """The script runs against THIS checkout and the shipped inventory."""

    def test_live_tree_json_report(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT),
        )
        # advisory report mode: always exit 0 (drift is data, not failure)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(report["status"],
                      ("clean", "drift", "no-inventory", "corrupt-inventory"))
        self.assertIn("counts", report)

    def test_shipped_inventory_exists_and_is_valid(self):
        inv = REPO_ROOT / ".claude" / "scripts" / "env-inventory.json"
        self.assertTrue(inv.is_file(), "shipped env-inventory.json missing")
        data = json.loads(inv.read_text(encoding="utf-8"))
        self.assertIsInstance(data.get("vars"), dict)
        self.assertGreater(len(data["vars"]), 100)


if __name__ == "__main__":
    unittest.main()
