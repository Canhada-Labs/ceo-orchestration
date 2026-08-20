"""PLAN-159 / ADR-163 — unit tests for the hook-latency gate hardening.

Covers the three Wave-1 profiler changes:

1. **Percentile precondition** — ``run_hook_latency`` refuses to gate on a
   collapsed nearest-rank index (``idx_p95 == idx_p99``, true for every
   ``iterations < 22``): it returns ``passed=False`` with the
   ``percentile_indices_collapsed`` error WITHOUT spawning a single
   subprocess. This is the machine-enforced invariant the debate round-1
   performance critique demanded (a future edit lowering N can never
   silently re-create the S272/S273 flake class).
2. **Index separation math** — the documented rank table of ADR-163.
3. **TimeoutExpired fold** — a >10s hook stall is folded into the
   fail-closed ``hook_failed`` sink (clean ``passed=False`` report), never
   an uncaught traceback.

No test here runs the real N=200 profile (cost); the profiling loop is
exercised with subprocess mocked out.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude" / "scripts" / "profile-opus-4-7.py"

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation
# (env-hygiene gate: bare unittest.TestCase is a violation in this tree).
_HOOKS_DIR = str(_REPO / ".claude" / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("profile_opus_4_7", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


class TestPercentileIndexMath(TestEnvContext):
    """ADR-163 rank table for the nearest-rank truncation int((n-1)*p/100)."""

    @staticmethod
    def _indices(n: int):
        return int((n - 1) * 95 / 100.0), int((n - 1) * 99 / 100.0)

    def test_collapse_at_n20_and_n21(self):
        for n in (2, 5, 10, 20, 21):
            i95, i99 = self._indices(n)
            self.assertEqual(i95, i99, f"expected collapse at n={n}")

    def test_first_separation_at_n22(self):
        i95, i99 = self._indices(22)
        self.assertEqual((i95, i99), (19, 20))
        # and 21 still collapses — 22 is the exact boundary
        self.assertEqual(self._indices(21)[0], self._indices(21)[1])

    def test_gate_standard_n200(self):
        i95, i99 = self._indices(200)
        self.assertEqual((i95, i99), (189, 197))
        # p95 tolerates 10 outliers, p99 tolerates 2 (documented in ADR-163)
        self.assertEqual(200 - 1 - i95, 10)
        self.assertEqual(200 - 1 - i99, 2)

    def test_pct_of_sorted_agrees_with_table(self):
        lst = sorted(float(i) for i in range(20))
        self.assertEqual(MOD._pct_of_sorted(lst, 95), MOD._pct_of_sorted(lst, 99))
        lst200 = sorted(float(i) for i in range(200))
        self.assertEqual(MOD._pct_of_sorted(lst200, 95), 189.0)
        self.assertEqual(MOD._pct_of_sorted(lst200, 99), 197.0)


class TestPercentilePrecondition(TestEnvContext):
    def test_n20_fails_loudly_without_spawning(self):
        def _forbidden(*a, **k):  # pragma: no cover — failure path
            raise AssertionError("precondition must fire BEFORE any subprocess")

        with mock.patch.object(MOD.subprocess, "run", side_effect=_forbidden):
            report = MOD.run_hook_latency(_REPO, iterations=20)
        self.assertFalse(report["passed"])
        self.assertIn("percentile_indices_collapsed", report["error"])
        self.assertIn("iterations=20", report["error"])

    def test_n21_also_collapses(self):
        report = MOD.run_hook_latency(_REPO, iterations=21)
        self.assertFalse(report["passed"])
        self.assertIn("percentile_indices_collapsed", report["error"])

    def test_n22_passes_the_precondition(self):
        # Point at an empty repo_root: the NEXT check ("hook not found")
        # must fire, proving the precondition let n=22 through without
        # profiling anything.
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            report = MOD.run_hook_latency(Path(td), iterations=22)
        self.assertFalse(report["passed"])
        self.assertIn("hook not found", report.get("error", ""))
        self.assertNotIn("percentile_indices_collapsed", report.get("error", ""))

    def test_default_iterations_is_gate_standard(self):
        import inspect

        sig = inspect.signature(MOD.run_hook_latency)
        self.assertEqual(sig.parameters["iterations"].default, 200)


class TestP99Advisory(TestEnvContext):
    """ADR-163 S318 amendment — p99 demoted to advisory (opt-in flag).

    Mechanism-level positive control: a synthetic p99 breach is created
    with an impossible ceiling (``p99_ceiling_ms=-1`` — any measured p99,
    including the ~0ms of a mocked subprocess, breaches it) so the test
    exercises the exact gate predicate, not wall-clock luck. The fake
    repo_root carries the three corpus hooks as stub files and NO
    tool_lifecycle.py, so ``observe_rail_present`` is False and both
    observe controls are structurally green — the verdict under test is
    the latency predicate alone.
    """

    @staticmethod
    def _fake_repo(td: str) -> Path:
        hooks = Path(td) / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        for name in (
            "check_agent_spawn.py",
            "check_anti_ceo_overhead.py",
            "check_output_secrets.py",
        ):
            (hooks / name).write_text("# stub corpus hook (test)\n")
        return Path(td)

    def _run(self, p99_advisory: bool):
        import tempfile

        ok = mock.Mock(returncode=0, stdout=b"", stderr=b"")
        with tempfile.TemporaryDirectory() as td:
            root = self._fake_repo(td)
            with mock.patch.object(MOD.subprocess, "run", return_value=ok):
                return MOD.run_hook_latency(
                    root,
                    iterations=22,
                    p95_ceiling_ms=1e9,
                    p99_ceiling_ms=-1.0,
                    p99_advisory=p99_advisory,
                )

    def test_p99_breach_fails_hard_by_default(self):
        report = self._run(p99_advisory=False)
        self.assertFalse(report["passed"])
        for name, entry in report["hooks"].items():
            self.assertFalse(entry["p99_within"], name)
            self.assertFalse(entry["passed"], name)

    def test_p99_breach_passes_under_advisory_and_stays_reported(self):
        report = self._run(p99_advisory=True)
        self.assertTrue(report["passed"])
        self.assertTrue(report["p99_advisory"])
        for name, entry in report["hooks"].items():
            # The breach never gates — but it is NEVER silent either:
            self.assertFalse(entry["p99_within"], name)
            self.assertTrue(entry["passed"], name)

    def test_default_ceilings_are_the_s318_recalibration(self):
        import inspect

        sig = inspect.signature(MOD.run_hook_latency)
        self.assertEqual(sig.parameters["p95_ceiling_ms"].default, 180.0)
        self.assertEqual(sig.parameters["p99_ceiling_ms"].default, 160.0)
        self.assertFalse(sig.parameters["p99_advisory"].default)


class TestTimeoutExpiredFold(TestEnvContext):
    def test_stall_reads_as_hook_failed_not_traceback(self):
        def _stall(*a, **k):
            raise subprocess.TimeoutExpired(cmd="hook", timeout=10)

        with mock.patch.object(MOD.subprocess, "run", side_effect=_stall):
            # iterations=22: smallest N past the precondition; subprocess is
            # mocked so nothing real is spawned and the run is instant.
            report = MOD.run_hook_latency(_REPO, iterations=22)

        self.assertFalse(report["passed"])
        hooks = report.get("hooks", {})
        self.assertTrue(hooks, "expected per-hook entries in the report")
        for name, entry in hooks.items():
            self.assertTrue(
                entry.get("hook_failed"),
                f"{name}: a TimeoutExpired stall must fold into hook_failed",
            )
            self.assertFalse(entry.get("passed"), name)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(unittest.main())
