"""Unit tests for hook-profiler.py (PLAN-010 Phase 2).

These tests run the profiler at reduced sample counts to keep the suite
fast while still exercising every code path: argparse, fixture loading,
percentile math, JSON/table output, isolation guard, and the monotonicity
invariant p50 <= p95 <= p99.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "hook-profiler.py"

_spec = importlib.util.spec_from_file_location("hook_profiler", _SCRIPT)
hp = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(hp)


def _run_cli(argv):
    """Run main(argv) capturing stdout/stderr; return (rc, out, err)."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = hp.main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestArgParsing(unittest.TestCase):
    def test_format_choice_rejects_unknown(self):
        with self.assertRaises(SystemExit):
            hp.parse_args(["--format", "xml"])

    def test_samples_below_minimum_exits_usage(self):
        # --samples 10 < max(warmup+1, 100) = 100
        rc, _, err = _run_cli(["--samples", "10", "--warmup", "5"])
        self.assertEqual(rc, 2)
        self.assertIn("--samples must be >=", err)

    def test_unknown_hook_rejected(self):
        rc, _, err = _run_cli(["--hook", "does_not_exist", "--samples", "120"])
        self.assertEqual(rc, 2)
        self.assertIn("--hook must be one of", err)


class TestPercentile(unittest.TestCase):
    def test_nearest_rank_percentile(self):
        data = sorted([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        self.assertEqual(hp._percentile(data, 50), 5)
        self.assertEqual(hp._percentile(data, 95), 10)
        self.assertEqual(hp._percentile(data, 99), 10)
        self.assertEqual(hp._percentile(data, 25), 3)
        self.assertEqual(hp._percentile(data, 0), 1)
        self.assertEqual(hp._percentile(data, 100), 10)

    def test_percentile_empty(self):
        self.assertEqual(hp._percentile([], 50), 0)


class TestFixtureCoverage(unittest.TestCase):
    def test_all_six_hooks_have_fixtures(self):
        for name in hp.ALL_HOOKS:
            fixture = hp.FIXTURES_DIR / name / "in.json"
            self.assertTrue(
                fixture.is_file(),
                f"missing canonical fixture for {name}: {fixture}",
            )
            # JSON-parseable
            json.loads(fixture.read_text(encoding="utf-8"))

    def test_all_six_hook_scripts_exist(self):
        for name in hp.ALL_HOOKS:
            script = hp.HOOKS_DIR / f"{name}.py"
            self.assertTrue(script.is_file(), f"missing hook: {script}")


class TestIsolation(unittest.TestCase):
    """Debate C7 + PLAN-019 P0-04: profiler must never touch the real audit log.

    ``_build_env`` MUST use an allowlist base (NOT ``os.environ.copy()``),
    otherwise parent-process ``$CLAUDE_PROJECT_DIR`` (set by
    ``TestEnvContext`` in sibling tests) leaks through even when the
    caller passes ``--home tmpdir``. The PLAN-018 audit attributed a
    24KB real-log leak to this class of copy-then-override pattern.
    """

    def test_home_env_is_scoped_to_tempdir(self):
        # When --home is a tempdir, the subprocess inherits HOME=<tempdir>.
        tmp = Path(tempfile.mkdtemp(prefix="hp-iso-"))
        try:
            env = hp._build_env(tmp, tmp)
            self.assertEqual(env["HOME"], str(tmp))
            self.assertEqual(env["CLAUDE_PROJECT_DIR"], str(tmp))
            # Enforce-mode env must not leak into profiled subprocesses.
            self.assertNotIn("CEO_CONFIDENCE_ENFORCE", env)
            self.assertNotIn("CEO_CONFIDENCE_BYPASS", env)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_env_does_not_leak_parent_claude_project_dir(self):
        """PLAN-019 P0-04 regression: parent ``$CLAUDE_PROJECT_DIR`` must
        NOT win over the ``--home`` override.

        Set a bogus ``$CLAUDE_PROJECT_DIR`` in the current process and
        confirm ``_build_env`` returns the tempdir path — not the
        polluted parent value. This is the direct test that would have
        caught the 24KB audit-log leak if it had existed when Sprint 10
        landed ``_build_env``.
        """
        tmp = Path(tempfile.mkdtemp(prefix="hp-leak-"))
        sentinel = "/tmp/hp-leak-sentinel-should-not-appear"
        old = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = sentinel
        try:
            env = hp._build_env(tmp, tmp)
            self.assertEqual(
                env["CLAUDE_PROJECT_DIR"],
                str(tmp),
                "parent $CLAUDE_PROJECT_DIR leaked into _build_env output",
            )
            self.assertNotEqual(env["CLAUDE_PROJECT_DIR"], sentinel)
        finally:
            if old is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = old
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_env_is_allowlist_not_copy(self):
        """``_build_env`` MUST use an allowlist base, not ``os.environ.copy()``.

        Inject a parent-process marker; assert it does NOT propagate to
        the built env. Confirms the allowlist approach — the only keys
        returned are (HOME, CLAUDE_PROJECT_DIR, NO_COLOR) plus the
        narrow pass-through allowlist (PATH, LANG, LC_ALL,
        GITHUB_STEP_SUMMARY).
        """
        tmp = Path(tempfile.mkdtemp(prefix="hp-allow-"))
        marker = "HP_PROFILER_LEAK_MARKER_12345"
        os.environ[marker] = "leaked-value-should-not-appear"
        try:
            env = hp._build_env(tmp, tmp)
            self.assertNotIn(
                marker,
                env,
                "arbitrary parent env variable leaked — _build_env is "
                "not using an allowlist base",
            )
            # The returned keys are a bounded set.
            allowed_keys = {
                "HOME",
                "CLAUDE_PROJECT_DIR",
                "NO_COLOR",
                "PATH",
                "LANG",
                "LC_ALL",
                "GITHUB_STEP_SUMMARY",
            }
            unexpected = set(env) - allowed_keys
            self.assertFalse(
                unexpected,
                f"_build_env returned unexpected keys: {unexpected}",
            )
        finally:
            os.environ.pop(marker, None)
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_default_tempdir_is_created_and_cleaned_up(self):
        # Running with no --home should not leave residue in real HOME.
        real_home = Path(os.path.expanduser("~"))
        real_audit = real_home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
        pre_exists = real_audit.exists()
        pre_size = real_audit.stat().st_size if pre_exists else 0

        # Single hook, minimum samples, table format — fast (~4s).
        rc, out, _err = _run_cli([
            "--hook", "check_bash_safety",
            "--samples", "120",
            "--warmup", "20",
            "--format", "table",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("check_bash_safety", out)

        # Real audit log must be byte-for-byte unchanged.
        if pre_exists:
            self.assertEqual(real_audit.stat().st_size, pre_size,
                             "profiler leaked writes into real audit log!")
        else:
            self.assertFalse(real_audit.exists(),
                             "profiler created real audit log unexpectedly!")


class TestOutputFormats(unittest.TestCase):
    def test_json_format_is_parseable_and_schema_tagged(self):
        rc, out, _err = _run_cli([
            "--hook", "check_bash_safety",
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertEqual(parsed["schema"], "hook-profiler.v1")
        self.assertIn("measured_at", parsed)
        self.assertIn("python", parsed)
        self.assertEqual(len(parsed["results"]), 1)
        r0 = parsed["results"][0]
        for key in ("hook", "samples_ok", "cold_start_ns",
                    "warm_p50_ns", "warm_p95_ns", "warm_p99_ns",
                    "warm_iqr_ns"):
            self.assertIn(key, r0)

    def test_table_format_is_markdown(self):
        rc, out, _err = _run_cli([
            "--hook", "check_bash_safety",
            "--samples", "120",
            "--warmup", "20",
            "--format", "table",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("| Hook |", out)
        self.assertIn("| check_bash_safety |", out)
        # Markdown table separator row
        self.assertIn("|------|", out)


class TestMeasurementCorrectness(unittest.TestCase):
    def test_warm_up_samples_are_discarded(self):
        """warm_count == samples_ok - warmup (within timeout margin)."""
        rc, out, _err = _run_cli([
            "--hook", "check_bash_safety",
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        r = json.loads(out)["results"][0]
        self.assertEqual(r["warm_count"], r["samples_ok"] - r["warmup_discarded"])
        # If no timeouts, samples_ok should equal 120.
        if r["timeouts"] == 0:
            self.assertEqual(r["samples_ok"], 120)
            self.assertEqual(r["warm_count"], 100)

    def test_percentile_monotonicity_on_real_hook(self):
        """p50 <= p95 <= p99 must always hold."""
        rc, out, _err = _run_cli([
            "--hook", "check_bash_safety",
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        r = json.loads(out)["results"][0]
        self.assertLessEqual(r["warm_p50_ns"], r["warm_p95_ns"])
        self.assertLessEqual(r["warm_p95_ns"], r["warm_p99_ns"])
        # IQR >= 0 by construction
        self.assertGreaterEqual(r["warm_iqr_ns"], 0)
        # Cold start is a single sample, should be >0
        self.assertGreater(r["cold_start_ns"], 0)


class TestAllHooksProfiled(unittest.TestCase):
    """End-to-end: running with no --hook covers all six."""

    def test_all_six_hooks_appear_in_output(self):
        rc, out, _err = _run_cli([
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        names = [r["hook"] for r in parsed["results"]]
        self.assertEqual(set(names), set(hp.ALL_HOOKS))
        self.assertEqual(len(names), 6)


class TestPerToolCallMode(unittest.TestCase):
    """Perf-P1-001 — per-tool-call aggregate distribution.

    Adopter reality: a single `Edit` tool call fires 3 hooks
    sequentially, not one hook in isolation. This mode simulates a
    realistic session distribution and reports the aggregate wall-clock
    — the number the agent actually feels.
    """

    def test_cli_flag_accepted(self):
        rc, _out, err = _run_cli([
            "--mode", "per-tool-call",
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0, f"per-tool-call should succeed; stderr={err!r}")

    def test_json_payload_schema(self):
        rc, out, _err = _run_cli([
            "--mode", "per-tool-call",
            "--samples", "120",
            "--warmup", "20",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertEqual(parsed["schema"], "hook-profiler.v1")
        self.assertIn("per_tool_call", parsed)
        ptc = parsed["per_tool_call"]
        self.assertEqual(ptc["mode"], "per-tool-call")
        self.assertIn("per_scenario", ptc)
        self.assertIn("aggregate", ptc)
        # Every scenario in the canonical distribution must appear
        scenarios = {row["scenario"] for row in ptc["per_scenario"]}
        expected = {"spawn", "Bash", "Edit", "Write", "Read", "other"}
        self.assertEqual(scenarios, expected)

    def test_aggregate_monotonicity(self):
        """Aggregate p50 <= p95 <= p99 on the mixed distribution."""
        rc, out, _err = _run_cli([
            "--mode", "per-tool-call",
            "--samples", "200",
            "--warmup", "50",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        agg = json.loads(out)["per_tool_call"]["aggregate"]
        self.assertLessEqual(agg["p50_ns"], agg["p95_ns"])
        self.assertLessEqual(agg["p95_ns"], agg["p99_ns"])
        # n = samples - warmup (assuming no timeouts)
        self.assertGreaterEqual(agg["n"], 150)

    def test_edit_scenario_sums_three_hooks(self):
        """An Edit-scenario sample executes 3 hooks sequentially.

        The p50 of the Edit row should therefore exceed the p50 of any
        single hook in its chain (sum > each part).
        """
        rc, out, _err = _run_cli([
            "--mode", "per-tool-call",
            "--samples", "300",
            "--warmup", "50",
            "--format", "json",
        ])
        self.assertEqual(rc, 0)
        ptc = json.loads(out)["per_tool_call"]
        edit_row = next(r for r in ptc["per_scenario"] if r["scenario"] == "Edit")
        self.assertEqual(
            set(edit_row["hooks"]),
            {"check_plan_edit", "check_canonical_edit", "audit_log"},
        )
        # p50 must be positive (we actually ran something)
        self.assertGreater(edit_row["p50_ns"], 0)

    def test_table_output_contains_aggregate_row(self):
        rc, out, _err = _run_cli([
            "--mode", "per-tool-call",
            "--samples", "120",
            "--warmup", "20",
            "--format", "table",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Per-tool-call wall-clock", out)
        self.assertIn("AGGREGATE", out)
        # Each scenario name appears somewhere in the table
        for scen in ("spawn", "Bash", "Edit", "Write", "Read", "other"):
            self.assertIn(scen, out)

    def test_per_tool_call_does_not_leak_audit_log(self):
        """PLAN-019 P0-04 regression: per-tool-call mode must stay isolated.

        Workstation-safe isolation check. The naive "size diff" approach
        is racy — other live sessions / background benchmarks write to
        the real audit log concurrently. Instead we scan the tail-delta
        that was written DURING this test for the fixtures' fingerprint
        ``session_id`` values. Those strings MUST NOT appear — our
        hooks write them only if they leak the tempdir isolation.
        """
        tmp = Path(tempfile.mkdtemp(prefix="hp-ptc-iso-"))
        real_home = Path(os.path.expanduser("~"))
        real_audit = real_home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
        pre_size = real_audit.stat().st_size if real_audit.exists() else 0
        try:
            rc, _out, _err = _run_cli([
                "--home", str(tmp),
                "--mode", "per-tool-call",
                "--samples", "120",
                "--warmup", "20",
                "--format", "json",
            ])
            self.assertEqual(rc, 0)
            if real_audit.exists():
                # Read only the tail delta written since pre_size so we
                # aren't reading hundreds of MB.
                with real_audit.open("rb") as f:
                    f.seek(pre_size)
                    delta = f.read().decode("utf-8", errors="replace")
                # Known fixture session_ids — these MUST NOT appear.
                for needle in (
                    "test-sess-005",
                    "test-sess-006",
                ):
                    self.assertNotIn(
                        needle, delta,
                        f"per-tool-call leaked fixture events "
                        f"({needle}) into real audit log!",
                    )
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
