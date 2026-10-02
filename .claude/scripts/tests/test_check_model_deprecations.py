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
- repo-default scan of the CURRENT tree: its non-inert BREAK/WARN set equals
  the DECLARED W3b.1 debt exactly (dogfood probe; PLAN-194 W3b.0+W3b.3)
- matcher precision (left guard, no prefix match), npm stage out of scan,
  check-model-currency family-prefix table INERT (PLAN-194 W3b.0)
- OpenAI ledger refresh from the primary source (PLAN-194 W3b.3)
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from collections import Counter
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

    def test_fastmode_entries_parse_and_classify_break_by_date(self):
        """PLAN-152 fastmode-deprecation: per-model_id fast-mode fuses.

        The checker has NO class/mode concept, so the fast-mode retirements
        ride ordinary per-id ledger entries: claude-opus-4-6-fast (retired
        2026-06-29 — the API silently falls back to standard speed) and
        claude-opus-4-7-fast (retires 2026-07-24 — hard API error after
        removal). Both must parse and classify BREAK once their date passes.
        """
        ledger = _mod.load_ledger(str(REAL_LEDGER))
        by_id = {m["model_id"]: m for m in ledger["models"]}
        self.assertEqual(by_id["claude-opus-4-6-fast"]["retirement"],
                         "2026-06-29")
        self.assertEqual(by_id["claude-opus-4-7-fast"]["retirement"],
                         "2026-07-24")
        # deprecated dates pinned too (Codex Wave F review caught a wrong
        # guess here — the official fast-mode doc says 2026-06-25).
        self.assertIsNone(by_id["claude-opus-4-6-fast"]["deprecated"])
        self.assertEqual(by_id["claude-opus-4-7-fast"]["deprecated"],
                         "2026-06-25")
        self.assertEqual(by_id["claude-opus-4-6-fast"]["replacement"],
                         "claude-opus-4-8-fast")
        self.assertEqual(by_id["claude-opus-4-7-fast"]["replacement"],
                         "claude-opus-4-8-fast")
        # classify BREAK by date (deterministic injected today)
        today = _mod.parse_iso_date("2026-07-25")
        for mid in ("claude-opus-4-6-fast", "claude-opus-4-7-fast"):
            sev, _label = _mod.classify_entry(by_id[mid], today, 60)
            self.assertEqual(sev, "BREAK",
                             "%s must classify BREAK past retirement" % mid)
        # 4-6-fast is already BREAK at the 4-7-fast deprecation date
        sev, _ = _mod.classify_entry(
            by_id["claude-opus-4-6-fast"], _mod.parse_iso_date("2026-07-02"), 60)
        self.assertEqual(sev, "BREAK")

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

    def test_repo_default_scan_matches_declared_w3b1_debt(self):
        """Dogfood probe: the CURRENT tree's non-inert BREAK/WARN set is
        EXACTLY the declared debt (empty means `--check` exits 0).

        Was `--check --today 2026-06-12` exits 0. PLAN-194 W3b.3 refreshed
        the OpenAI rows from the primary source, and ids retired on
        2026-07-23 (or retiring 2026-12-11) still sit in live code until
        W3b.1 removes them. The probe date moved to the W3b control date
        (2026-10-13), which sees every id the old date saw (each one that
        warned on 2026-06-12 is BREAK by then) plus the December fuse.
        """
        rc, out, _ = self.run_main(["--json", "--today", W3B0_TODAY])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        observed = Counter(
            (h["path"], h["matched"], h["severity"])
            for h in report["hits"] if h["severity"] in ("BREAK", "WARN"))
        self.assertEqual(dict(observed), W3B1_DECLARED_DEBT)
        rc, _, _ = self.run_main(["--check", "--today", W3B0_TODAY])
        self.assertEqual(rc, 1 if W3B1_DECLARED_DEBT else 0)


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


# ---------------------------------------------------------------------------
# PLAN-194 W3b.0 — matcher precision (Codex review S359, P2; measured
# 2026-09-30). The matcher had a RIGHT guard only, so `gpt-5` matched inside
# `gpt-5-mini`/`gpt-5-codex`, `o3` inside `o3-mini` and even inside
# `lib2to3`: of the 28 WARNs of `--check --today 2026-10-13`, most were not
# ids the ledger retires. NEGATIVE controls pin the three measured
# false-positive classes; POSITIVE controls pin `gpt-5`/`o3` loose in a model
# list, which MUST keep matching. Every control below was run RED against the
# pre-cure matcher before the cure landed (positive ones that are behaviour
# the cure must PRESERVE are marked as such).
# ---------------------------------------------------------------------------

# Same dates as the real ledger's gpt-5/o3 entries (retire 2026-12-11, so
# --today 2026-10-13 is inside the 60-day WARN window).
OPENAI_LEDGER = {
    "_meta": {"schema": 1, "fetched": "2026-06-12", "source_stale": False},
    "models": [
        {"model_id": "gpt-5", "aliases": [], "deprecated": "2026-12-11",
         "retirement": "2026-12-11", "replacement": "gpt-5.6-sol"},
        {"model_id": "o3", "aliases": ["o3-2025-04-16"],
         "deprecated": "2026-12-11", "retirement": "2026-12-11",
         "replacement": "gpt-5.6-sol"},
        {"model_id": "claude-test-old-1-20240101",
         "aliases": ["claude-test-old-1"], "deprecated": "2025-01-01",
         "retirement": "2026-01-01", "replacement": "claude-test-new"},
    ],
    "inert_path_rules": [],
}

W3B0_TODAY = "2026-10-13"

#: PLAN-194 — DECLARED DEBT, the input of W3b.1: the exact non-inert
#: BREAK/WARN hits of the CURRENT tree at --today 2026-10-13 with the
#: refreshed ledger (measured 2026-10-02 on main 6a9abb10), keyed by
#: (path, matched literal, severity) -> count; line-free so an unrelated edit
#: does not churn it. W3b.1 removes these ids and SHRINKS this map in the
#: same patch, down to EMPTY (then --check at the control date exits 0).
#: Never widen it without a primary source (PLAN-194/LEDGER.md §W3b.3).
#: Widened ONCE, with a primary source: the 2026-10-02 re-check of the page
#: (LEDGER §W3b.3, raw HTML) gave `o3-mini`/`o4-mini` rows (2026-10-23).
#: Shrunk by the free half of W3b.1 (the non-canonical `codex_invoke.py`
#: docstring and `optimizer/codex_phase_gate.py` label: 3 hits); what is
#: left lives in the canonical `codex_cli_shape.py` and goes with its
#: ceremony.
W3B1_DECLARED_DEBT = {
    (".claude/hooks/_lib/codex_cli_shape.py", "gpt-5-codex", "BREAK"): 4,
    (".claude/hooks/_lib/codex_cli_shape.py", "gpt-5.1-codex", "BREAK"): 1,
    (".claude/hooks/_lib/codex_cli_shape.py", "gpt-5", "WARN"): 2,
    (".claude/hooks/_lib/codex_cli_shape.py", "gpt-5-mini", "WARN"): 1,
    (".claude/hooks/_lib/codex_cli_shape.py", "o3", "WARN"): 1,
    (".claude/hooks/_lib/codex_cli_shape.py", "o3-mini", "WARN"): 1,
    (".claude/hooks/_lib/codex_cli_shape.py", "o4-mini", "WARN"): 1,
}

# The exact line shapes measured on 2026-09-30 (check-stdlib-only.py:63 and
# the `_VALID_MODELS` / docstring / default-slug shapes of codex_cli_shape.py,
# codex_invoke.py and optimizer/codex_phase_gate.py).
NEG_LEFT_GUARD = (
    '        "inspect", "io", "ipaddress", "itertools", "json", '
    '"keyword", "lib2to3",\n'
    "use_o3 = False\n"
)
NEG_PREFIX = (
    '    "gpt-5-mini",\n'
    '    "gpt-5-codex",\n'
    '    "o3-mini",\n'
    "        --model gpt-5-codex \\\n"
    'DEFAULT_CODEX_MODEL: str = "gpt-5-codex"\n'
    "    # coerced to `gpt-5-codex`\n"
)
POS_MODEL_LIST = (
    "_VALID_MODELS = (\n"
    '    "gpt-5.5",\n'
    '    "gpt-5",\n'
    '    "gpt-5-mini",\n'
    '    "gpt-5-codex",\n'
    '    "o3",\n'
    '    "o3-mini",\n'
    '    "o4-mini",\n'
    ")\n"
)


class TestMatcherPrecisionW3b0(_CheckerTestBase):
    """PLAN-194 W3b.0: left guard + a retired id is never a PREFIX match."""

    def _scan(self, files, ledger_data=OPENAI_LEDGER, extra=()):
        ledger = self.write_ledger(ledger_data)
        root = self.make_root("w3b0", files)
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--json", "--today", W3B0_TODAY]
            + list(extra) + [root])
        return rc, json.loads(out)

    def _pairs(self, report):
        return sorted((h["path"], h["line"], h["matched"])
                      for h in report["hits"])

    # -- NEGATIVE controls (RED before the cure) ----------------------------

    def test_left_guard_lib2to3_is_not_o3(self):
        rc, report = self._scan({"stdlib.py": NEG_LEFT_GUARD})
        self.assertEqual(rc, 0)
        self.assertEqual(self._pairs(report), [],
                         "an id inside a longer identifier must not match")

    def test_retired_id_is_not_a_prefix_of_another_id(self):
        rc, report = self._scan({"shape.py": NEG_PREFIX})
        self.assertEqual(rc, 0)
        self.assertEqual(self._pairs(report), [],
                         "gpt-5/o3 must not match inside gpt-5-mini/"
                         "gpt-5-codex/o3-mini")

    def test_negatives_alone_keep_check_green(self):
        ledger = self.write_ledger(OPENAI_LEDGER)
        root = self.make_root("w3b0neg", {
            "stdlib.py": NEG_LEFT_GUARD, "shape.py": NEG_PREFIX})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", W3B0_TODAY, root])
        self.assertEqual(rc, 0, out)

    def test_unlisted_variant_does_not_match(self):
        rc, report = self._scan({"v.py": 'M = "o3-pro"\nN = "gpt-5-nano"\n'})
        self.assertEqual(self._pairs(report), [])

    # -- POSITIVE controls ---------------------------------------------------

    def test_loose_ids_in_a_model_list_still_match(self):
        """PRESERVED behaviour: exactly the two loose ids, nothing else."""
        rc, report = self._scan({"shape.py": POS_MODEL_LIST})
        self.assertEqual(self._pairs(report), [
            ("shape.py", 3, "gpt-5"), ("shape.py", 6, "o3")])
        for hit in report["hits"]:
            self.assertEqual(hit["severity"], "WARN", hit)

    def test_loose_ids_in_a_model_list_fail_the_check(self):
        """PRESERVED behaviour: the cure must not silence the real WARN."""
        ledger = self.write_ledger(OPENAI_LEDGER)
        root = self.make_root("w3b0pos", {"shape.py": POS_MODEL_LIST})
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--check", "--today", W3B0_TODAY, root])
        self.assertEqual(rc, 1, out)

    def test_listed_variant_matches_as_its_entry(self):
        """A variant enters only when the ledger lists it (here an alias)."""
        rc, report = self._scan({"v.py": 'M = "o3-2025-04-16"\n'})
        self.assertEqual(self._pairs(report), [("v.py", 1, "o3-2025-04-16")])
        self.assertEqual(report["hits"][0]["model_id"], "o3")

    def test_qualified_and_delimited_ids_still_match(self):
        """PRESERVED behaviour: separators that are not id continuations."""
        text = (
            "--model gpt-5\n"                       # line start / space
            "MODEL=o3\n"                            # '='
            "route = 'openai/gpt-5'\n"              # '/' qualifier
            "id = 'anthropic.claude-test-old-1'\n"  # dotted qualifier
            "pick(o3, gpt-5)\n"                     # '(' ',' ')'
            "tail gpt-5-\n"                          # '-' that opens nothing
            "o3:latest\n"                           # ':' tag
        )
        rc, report = self._scan({"q.py": text})
        self.assertEqual(self._pairs(report), [
            ("q.py", 1, "gpt-5"), ("q.py", 2, "o3"), ("q.py", 3, "gpt-5"),
            ("q.py", 4, "claude-test-old-1"), ("q.py", 5, "gpt-5"),
            ("q.py", 5, "o3"), ("q.py", 6, "gpt-5"), ("q.py", 7, "o3")])

    def test_claude_full_id_still_wins_and_suffix_variant_drops(self):
        """Longest-first is unchanged; an unlisted `-<x>` variant no longer
        rides on the bare alias (variants enter only via the ledger)."""
        rc, report = self._scan({"c.py": (
            "a = 'claude-test-old-1-20240101'\n"
            "b = 'claude-test-old-1-latest'\n")})
        self.assertEqual(self._pairs(report), [
            ("c.py", 1, "claude-test-old-1-20240101")])

    def test_real_ledger_openai_entries_get_the_cure(self):
        """The shipped ledger's gpt-5/o3 rows: negatives silent, positives
        WARN. Filtered to those two ids so a future ledger row (e.g. a
        gpt-5.5 retirement) does not turn this into a ledger snapshot."""
        root = self.make_root("w3b0real", {
            "stdlib.py": NEG_LEFT_GUARD, "shape.py": NEG_PREFIX,
            "list.py": POS_MODEL_LIST})
        rc, out, _ = self.run_main(
            ["--json", "--today", W3B0_TODAY, root])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        mine = sorted((h["path"], h["line"], h["matched"], h["severity"])
                      for h in report["hits"]
                      if h["model_id"] in ("gpt-5", "o3"))
        self.assertEqual(mine, [
            ("list.py", 3, "gpt-5", "WARN"), ("list.py", 6, "o3", "WARN")])


class TestNpmStageMirrorOutOfScan(_CheckerTestBase):
    """PLAN-194 W3b.0 decision: the npm stage mirror is OUT of the scan.

    `npm/.claude/`, `npm/SPEC/`, `npm/scripts/` and `npm/templates/` at the
    scan ROOT are the gitignored stage of the npm tarball (.gitignore:47-50,
    written by scripts/install-npm.sh / scripts/npm-rebuild.sh): byte copies
    of trees already scanned at their source, which doubled every WARN.
    Tracked files under `npm/` and any `npm/` dir that is NOT at the root
    stay in scope.
    """

    def test_stage_subtrees_at_root_are_pruned(self):
        ledger = self.write_ledger(OPENAI_LEDGER)
        root = self.make_root("npmroot", {
            "npm/.claude/hooks/_lib/shape.py": '"o3",\n',
            "npm/SPEC/v1/x.py": '"o3",\n',
            "npm/scripts/y.py": '"o3",\n',
            "npm/templates/z.py": '"o3",\n',
            "npm/bin/init.js": '"o3",\n',
            "pkg/npm/.claude/w.py": '"o3",\n',
            ".claude/hooks/_lib/shape.py": '"o3",\n',
        })
        rc, out, _ = self.run_main(
            ["--ledger", ledger, "--json", "--today", W3B0_TODAY, root])
        report = json.loads(out)
        self.assertEqual(sorted(h["path"] for h in report["hits"]), [
            ".claude/hooks/_lib/shape.py", "npm/bin/init.js",
            "pkg/npm/.claude/w.py"])


class TestModelCurrencyFamilyPrefixesInert(_CheckerTestBase):
    """PLAN-194 W3b.0: `check-model-currency.py`'s `_FAMILIES` table holds
    vendor id PREFIXES (`"gpt-", "o3", "o4"`), not model ids — no matcher
    rule can tell that `"o3"` from a loose `"o3"` in a model list, so the
    shipped ledger classifies the file INERT (rule
    `model-currency-family-prefixes`). A loose `"o3"` anywhere else stays
    WARN (positive control)."""

    def test_family_prefix_table_is_inert_with_real_ledger(self):
        root = self.make_root("mc", {
            ".claude/scripts/check-model-currency.py":
                '    ("openai", ("gpt-", "o3", "o4"), '
                '"codex_cli_shape:_VALID_MODELS"),\n',
            ".claude/hooks/_lib/codex_cli_shape.py": '    "o3",\n',
        })
        rc, out, _ = self.run_main(
            ["--json", "--today", W3B0_TODAY, root])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        by_path = {h["path"]: h for h in report["hits"]
                   if h["model_id"] == "o3"}
        table = by_path[".claude/scripts/check-model-currency.py"]
        self.assertEqual(table["severity"], "INERT", table)
        self.assertEqual(table["inert_rule"],
                         "model-currency-family-prefixes")
        self.assertEqual(
            by_path[".claude/hooks/_lib/codex_cli_shape.py"]["severity"],
            "WARN")


# PLAN-194 W3b.3 — OpenAI rows refreshed from the primary source (the
# deprecations page read on 2026-10-02 and recorded in
# .claude/plans/PLAN-194/LEDGER.md §W3b.3). With the precise matcher a variant
# is seen ONLY when the ledger lists it, so every id the page retires must be
# a model_id or alias. RED before the refresh: none of the July ids and none
# of the dated/undated December variants below matched.
JULY_2026_SHUTDOWN = (
    "gpt-5-codex", "gpt-5-chat-latest", "gpt-5.1-codex",
    "gpt-5.1-codex-max", "gpt-5.1-codex-mini", "gpt-5.2-codex",
    "gpt-5.1-chat-latest", "o3-deep-research-2025-06-26",
)
#: literal -> ledger model_id (dated snapshots from the page + the undated
#: ids that ride them, as the pre-existing gpt-5/o3 rows already did).
DECEMBER_2026_SHUTDOWN = {
    "gpt-5-2025-08-07": "gpt-5", "gpt-5": "gpt-5",
    "gpt-5-mini-2025-08-07": "gpt-5-mini", "gpt-5-mini": "gpt-5-mini",
    "gpt-5-nano-2025-08-07": "gpt-5-nano", "gpt-5-nano": "gpt-5-nano",
    "gpt-5-pro-2025-10-06": "gpt-5-pro", "gpt-5-pro": "gpt-5-pro",
    "o3-2025-04-16": "o3", "o3": "o3",
    "o3-pro-2025-06-10": "o3-pro", "o3-pro": "o3-pro",
}


class TestOpenAILedgerRefreshW3b3(_CheckerTestBase):
    """The shipped ledger sees every id the primary source retires."""

    def _scan_ids(self, ids):
        root = self.make_root("w3b3", {
            "ids.py": "".join('M = "%s"\n' % i for i in ids)})
        rc, out, _ = self.run_main(["--json", "--today", W3B0_TODAY, root])
        self.assertEqual(rc, 0)
        return json.loads(out)["hits"]

    def test_july_shutdown_ids_are_break(self):
        hits = self._scan_ids(JULY_2026_SHUTDOWN)
        got = sorted((h["line"], h["matched"], h["model_id"],
                      h["retirement"], h["severity"]) for h in hits)
        self.assertEqual(got, [
            (n + 1, mid, mid, "2026-07-23", "BREAK")
            for n, mid in enumerate(JULY_2026_SHUTDOWN)])

    def test_december_snapshots_and_undated_ids_warn(self):
        ids = list(DECEMBER_2026_SHUTDOWN)
        hits = self._scan_ids(ids)
        got = sorted((h["line"], h["matched"], h["model_id"],
                      h["retirement"], h["severity"]) for h in hits)
        self.assertEqual(got, [
            (n + 1, lit, DECEMBER_2026_SHUTDOWN[lit], "2026-12-11", "WARN")
            for n, lit in enumerate(ids)])

    def test_unconfirmed_ids_have_no_row(self):
        """Declared decision (LEDGER §W3b.3): `gpt-5.5` is NOT on the page —
        no row (a future row needs a primary source and must update this
        test on purpose)."""
        self.assertEqual(self._scan_ids(("gpt-5.5",)), [])

    def test_october_shutdown_reviewer_ids_warn(self):
        """Re-check 2026-10-02 (LEDGER §W3b.3, raw HTML of the page): the
        2026-04-22 section without the July parenthetical shuts
        `o3-mini-2025-01-31 | o3-mini` and `o4-mini-2025-04-16 | o4-mini`
        down on 2026-10-23 — the two reviewer ids `_VALID_MODELS` carried.
        RED before the rows: none of the four literals matched."""
        ids = ("o3-mini", "o3-mini-2025-01-31", "o4-mini",
               "o4-mini-2025-04-16")
        want = {"o3-mini": "o3-mini", "o3-mini-2025-01-31": "o3-mini",
                "o4-mini": "o4-mini", "o4-mini-2025-04-16": "o4-mini"}
        hits = self._scan_ids(ids)
        got = sorted((h["line"], h["matched"], h["model_id"],
                      h["retirement"], h["severity"]) for h in hits)
        self.assertEqual(got, [
            (n + 1, lit, want[lit], "2026-10-23", "WARN")
            for n, lit in enumerate(ids)])

    def test_openai_replacement_stays_inside_one_target(self):
        """Every OpenAI row names gpt-5.6-sol, so the refresh adds NO new id
        to check-model-currency.py's red set (expected-reds unchanged; a
        per-tier target is a W3b.2/W5c decision)."""
        ledger = _mod.load_ledger(str(REAL_LEDGER))
        targets = {m["replacement"] for m in ledger["models"]
                   if not m["model_id"].startswith("claude-")}
        self.assertEqual(targets, {"gpt-5.6-sol"})


if __name__ == "__main__":
    unittest.main()
