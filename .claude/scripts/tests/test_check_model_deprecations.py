"""test_check_model_deprecations.py — PLAN-135 W0/W1 unit w0r.

Covers the permanent model-deprecation checker
(.claude/scripts/check-model-deprecations.py):

- real sidecar ledger parses (entries, dates, inert rules, source_stale)
- <=60-day WARN math via --today injection (boundary inclusive)
- scan-root resolution precedence (argv > CEO_DEPRECATION_SCAN_ROOTS > repo)
- negative-fixture inertness (tier_policy claude-opus-4-1 pins -> INERT)
- --check exit codes (BREAK=1, WARN=1, clean=0, inert-only=0, report-mode=0)
- fail-open (missing/corrupt ledger -> advisory + exit 0, with or without
  --check; bad --today falls back to the real date)
- alias longest-first matching (no double count of full id vs bare alias)
- repo-default --check runs clean against the CURRENT tree (dogfood probe)
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-model-deprecations.py"
REAL_LEDGER = REPO_ROOT / ".claude" / "scripts" / "model-deprecations.json"


def _load_module():
    """Load check-model-deprecations.py (hyphenated filename) as a module."""
    spec = importlib.util.spec_from_file_location(
        "check_model_deprecations", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_model_deprecations"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


SYNTH_LEDGER = {
    "_meta": {"schema": 1, "fetched": "2026-01-01", "source_stale": False},
    "models": [
        {
            "model_id": "claude-test-old-1-20240101",
            "aliases": ["claude-test-old-1"],
            "deprecated": "2025-01-01",
            "retirement": "2026-01-01",
            "replacement": "claude-test-new",
        },
        {
            "model_id": "claude-test-soon-20250101",
            "aliases": [],
            "deprecated": "2026-05-01",
            "retirement": "2026-08-01",
            "replacement": "claude-test-new",
        },
    ],
    "inert_path_rules": [
        {
            "rule_id": "tier-policy-test-pins",
            "pattern": "(^|/)\\.claude/hooks/tests/test_tier_policy_[A-Za-z0-9_]+\\.py$",
            "reason": "negative fixtures",
        }
    ],
}


class _CheckerTestBase(TestEnvContext):
    """Shared scratch-root + run helpers on top of the isolated env."""

    def setUp(self):
        super().setUp()
        # TestEnvContext snapshots/restores CEO_* vars; make the scan-root
        # env var deterministic per test.
        os.environ.pop("CEO_DEPRECATION_SCAN_ROOTS", None)

    def write_ledger(self, data) -> str:
        path = Path(self.project_dir) / "ledger.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def make_root(self, name: str, files) -> str:
        """files: dict of rel-path -> content."""
        root = Path(self.project_dir) / name
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        root.mkdir(parents=True, exist_ok=True)
        return str(root)

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = _mod.main(argv)
        return rc, out.getvalue(), err.getvalue()


class TestRealLedgerParses(_CheckerTestBase):
    """The shipped sidecar ledger is well-formed and load-bearing."""

    def test_ledger_loads_and_has_known_fuses(self):
        ledger = _mod.load_ledger(str(REAL_LEDGER))
        self.assertIsNotNone(ledger)
        by_id = {m["model_id"]: m for m in ledger["models"]}
        self.assertEqual(
            by_id["claude-sonnet-4-20250514"]["retirement"], "2026-06-15")
        self.assertEqual(
            by_id["claude-opus-4-20250514"]["retirement"], "2026-06-15")
        self.assertEqual(
            by_id["claude-opus-4-1-20250805"]["retirement"], "2026-08-05")
        self.assertIn("claude-opus-4-1",
                      by_id["claude-opus-4-1-20250805"]["aliases"])
        # every retirement date parses
        for entry in ledger["models"]:
            self.assertIsNotNone(
                _mod.parse_iso_date(entry["retirement"]),
                "unparseable retirement on %s" % entry["model_id"])

    def test_ledger_meta_not_stale_and_rules_compile(self):
        ledger = _mod.load_ledger(str(REAL_LEDGER))
        self.assertFalse(ledger["_meta"]["source_stale"])
        rules = _mod.compile_inert_rules(ledger)
        rule_ids = [rid for rid, _ in rules]
        # spec-mandated negative-fixture rule must exist AND compile
        self.assertIn("tier-policy-test-pins", rule_ids)
        self.assertEqual(len(rules), len(ledger["inert_path_rules"]),
                         "an inert rule failed to compile")


class TestWarnMath(_CheckerTestBase):
    """<=60-day WARN window math, deterministic via injected today."""

    def _classify(self, retirement, today_s, warn_days=60):
        entry = {"retirement": retirement}
        today = _mod.parse_iso_date(today_s)
        return _mod.classify_entry(entry, today, warn_days)

    def test_inside_window_is_warn(self):
        sev, label = self._classify("2026-08-01", "2026-06-10")  # 52 days
        self.assertEqual(sev, "WARN")
        self.assertEqual(label, "RETIRE-2026-08-01")

    def test_exactly_60_days_is_warn(self):
        sev, _ = self._classify("2026-08-01", "2026-06-02")  # 60 days
        self.assertEqual(sev, "WARN")

    def test_61_days_is_info(self):
        sev, _ = self._classify("2026-08-01", "2026-06-01")  # 61 days
        self.assertEqual(sev, "INFO")

    def test_retirement_today_is_break(self):
        sev, label = self._classify("2026-06-12", "2026-06-12")
        self.assertEqual(sev, "BREAK")
        self.assertEqual(label, "ALREADY-RETIRED")

    def test_past_retirement_is_break(self):
        sev, _ = self._classify("2026-01-01", "2026-06-12")
        self.assertEqual(sev, "BREAK")

    def test_undated_entry_is_info(self):
        sev, label = self._classify(None, "2026-06-12")
        self.assertEqual(sev, "INFO")
        self.assertEqual(label, "DEPRECATED-NO-DATE")

    def test_custom_warn_days_respected(self):
        sev, _ = self._classify("2026-08-01", "2026-06-10", warn_days=10)
        self.assertEqual(sev, "INFO")


class TestRootResolution(_CheckerTestBase):
    """argv > CEO_DEPRECATION_SCAN_ROOTS > repo-root default."""

    def test_argv_beats_env(self):
        roots = _mod.resolve_roots(["/tmp/a"], "/tmp/b")
        self.assertEqual(roots, [os.path.abspath("/tmp/a")])

    def test_env_used_when_no_argv(self):
        env_val = os.pathsep.join(["/tmp/b", "/tmp/c"])
        roots = _mod.resolve_roots([], env_val)
        self.assertEqual(
            roots, [os.path.abspath("/tmp/b"), os.path.abspath("/tmp/c")])

    def test_default_is_repo_root(self):
        roots = _mod.resolve_roots([], None)
        self.assertEqual(roots, [str(REPO_ROOT)])
        self.assertEqual(os.path.abspath(_mod.REPO_ROOT), str(REPO_ROOT))

    def test_env_end_to_end(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("envroot", {"app.py": "claude-test-old-1\n"})
        os.environ["CEO_DEPRECATION_SCAN_ROOTS"] = root
        rc, out, _ = self.run_main(["--ledger", ledger, "--check",
                                    "--today", "2026-06-12"])
        self.assertEqual(rc, 1)
        self.assertIn("LIVE-BREAKS-REMAINING: 1", out)


class TestNegativeFixtureInertness(_CheckerTestBase):
    """tier_policy fixture pins classify INERT via ledger path rules."""

    def test_tier_policy_pin_is_inert_synth(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("repoish", {
            ".claude/hooks/tests/test_tier_policy_types.py":
                'PIN = "claude-test-old-1"\n',
        })
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", "2026-06-12", root])
        self.assertEqual(rc, 0)
        self.assertIn("INERT:tier-policy-test-pins", out)
        self.assertIn("LIVE-BREAKS-REMAINING: 0", out)

    def test_real_repo_tier_policy_pins_are_inert(self):
        """The dogfood tree's own claude-opus-4-1 fixtures must be INERT."""
        rc, out, _ = self.run_main(
            ["--json", "--today", "2026-06-12", str(REPO_ROOT)])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        tier_hits = [h for h in report["hits"]
                     if "test_tier_policy" in h["path"]]
        self.assertTrue(tier_hits, "expected tier_policy fixture hits")
        for hit in tier_hits:
            self.assertEqual(hit["severity"], "INERT", hit)

    def test_repo_default_check_is_clean(self):
        """Dogfood probe: --check against the CURRENT tree exits 0."""
        rc, out, _ = self.run_main(["--check", "--today", "2026-06-12"])
        self.assertEqual(rc, 0)
        self.assertIn("LIVE-BREAKS-REMAINING: 0", out)


class TestCheckExitCodes(_CheckerTestBase):
    def test_break_exits_1(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("r1", {"call.py": "m = 'claude-test-old-1'\n"})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", "2026-06-12", root])
        self.assertEqual(rc, 1)
        self.assertIn("LIVE-BREAKS-REMAINING: 1", out)

    def test_warn_exits_1(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root(
            "r2", {"call.py": "m = 'claude-test-soon-20250101'\n"})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", "2026-07-30", root])
        self.assertEqual(rc, 1)  # 2 days to retirement = WARN
        self.assertIn("LIVE-BREAKS-REMAINING: 0", out)

    def test_far_retirement_exits_0(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root(
            "r3", {"call.py": "m = 'claude-test-soon-20250101'\n"})
        rc, _, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", "2026-01-02", root])
        self.assertEqual(rc, 0)  # 211 days out = INFO

    def test_report_mode_never_exits_1(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("r4", {"call.py": "m = 'claude-test-old-1'\n"})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--today", "2026-06-12", root])
        self.assertEqual(rc, 0)
        self.assertIn("LIVE-BREAKS-REMAINING: 1", out)

    def test_missing_root_is_skipped_not_fatal(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", "2026-06-12",
             str(Path(self.project_dir) / "no-such-dir")])
        self.assertEqual(rc, 0)
        self.assertIn("-- skip (missing):", out)


class TestFailOpen(_CheckerTestBase):
    def test_missing_ledger_advisory_exit_0(self):
        rc, out, err = self.run_main(
            ["--ledger", str(Path(self.project_dir) / "nope.json")])
        self.assertEqual(rc, 0)
        self.assertIn("advisory", err)
        self.assertIn("LIVE-BREAKS-REMAINING: UNKNOWN", out)

    def test_missing_ledger_with_check_still_exit_0(self):
        rc, _, err = self.run_main(
            ["--ledger", str(Path(self.project_dir) / "nope.json"),
             "--check"])
        self.assertEqual(rc, 0)
        self.assertIn("fail-open", err)

    def test_corrupt_ledger_advisory_exit_0(self):
        bad = Path(self.project_dir) / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        rc, _, err = self.run_main(["--ledger", str(bad), "--check"])
        self.assertEqual(rc, 0)
        self.assertIn("advisory", err)

    def test_bad_today_falls_back_fail_open(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("r5", {"clean.py": "no ids here\n"})
        rc, _, err = self.run_main(
            ["--ledger", ledger, "--today", "garbage", root])
        self.assertEqual(rc, 0)
        self.assertIn("unparseable", err)

    def test_bad_inert_rule_skipped_with_advisory(self):
        data = json.loads(json.dumps(SYNTH_LEDGER))
        data["inert_path_rules"].append(
            {"rule_id": "broken", "pattern": "([", "reason": "bad regex"})
        ledger = self.write_ledger(data)
        root = self.make_root("r6", {"clean.py": "no ids here\n"})
        rc, _, err = self.run_main(["--ledger", ledger, root])
        self.assertEqual(rc, 0)
        self.assertIn("broken", err)


class TestMatcher(_CheckerTestBase):
    def test_full_id_wins_over_alias_no_double_count(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root(
            "r7", {"one.py": "m = 'claude-test-old-1-20240101'\n"})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--json", "--today", "2026-06-12", root])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["hits"][0]["matched"],
                         "claude-test-old-1-20240101")
        self.assertEqual(report["hits"][0]["model_id"],
                         "claude-test-old-1-20240101")

    def test_guard_blocks_id_continuation(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root(
            "r8", {"one.py": "m = 'claude-test-old-1x'\n"})  # x continues id
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--json", "--today", "2026-06-12", root])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["summary"]["total"], 0)

    def test_json_shape(self):
        ledger = self.write_ledger(SYNTH_LEDGER)
        root = self.make_root("r9", {"a.py": "claude-test-old-1\n"})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--json", "--today", "2026-06-12", root])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        for key in ("schema", "today", "warn_days", "ledger", "source_stale",
                    "roots", "summary", "hits"):
            self.assertIn(key, report)
        self.assertEqual(report["today"], "2026-06-12")
        hit = report["hits"][0]
        for key in ("root", "path", "line", "matched", "model_id",
                    "retirement", "label", "severity"):
            self.assertIn(key, hit)


if __name__ == "__main__":
    unittest.main()
