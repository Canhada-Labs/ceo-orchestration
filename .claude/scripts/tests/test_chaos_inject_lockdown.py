"""Unit tests for `chaos-inject.py` 3-gate lockdown (PLAN-011 Phase 10).

The chaos-injection utility is weaponizable — it can generate scripts
that break a hook's stdout contract. To prevent abuse it enforces a
3-gate AND at module entry (ADR-037 §Decision §1):

1. `CEO_CHAOS_ALLOWED=1` in env
2. Parent process command contains `pytest`
3. `os.getcwd()` contains `tests/chaos/`

These tests verify EACH gate independently closes the door, then the
positive case where all three are open the script proceeds. Also
exercises the argparse branches (unknown hook/mode → exit 3) and the
wrapper-generation helper (runs without gates — pure I/O).
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Load the chaos-inject module (it has a dash in its name so we cannot
# `import chaos_inject`; use importlib instead — same pattern as
# test_hook_profiler.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "chaos-inject.py"

_spec = importlib.util.spec_from_file_location("chaos_inject", _SCRIPT)
ci = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ci)


def _run_cli(argv, env=None, cwd=None):
    """Run chaos-inject.main(argv) capturing stdout+stderr.

    We must patch os.getcwd() and os.environ at the module level
    because gate evaluation reads them directly. We also need to
    override os.getppid()'s effect via the private helper APIs —
    the gate helpers accept explicit `env`, `ppid`, `cwd` kwargs
    so tests can call them deterministically, but the CLI entry
    reads the live state. So for CLI-level tests we use env+chdir
    snapshots.
    """
    out = io.StringIO()
    err = io.StringIO()
    saved_env = os.environ.copy()
    saved_cwd = os.getcwd()
    try:
        if env is not None:
            # Replace entirely so absence of a var can be tested.
            for k in list(os.environ.keys()):
                if k.startswith("CEO_"):
                    del os.environ[k]
            for k, v in env.items():
                os.environ[k] = v
        if cwd is not None:
            os.chdir(cwd)
        with redirect_stdout(out), redirect_stderr(err):
            rc = ci.main(argv)
        return rc, out.getvalue(), err.getvalue()
    finally:
        try:
            os.chdir(saved_cwd)
        except OSError:
            pass
        # Restore env
        for k in list(os.environ.keys()):
            if k.startswith("CEO_"):
                del os.environ[k]
        for k, v in saved_env.items():
            if k.startswith("CEO_"):
                os.environ[k] = v


# -----------------------------------------------------------------------------
# Gate helpers (unit-tested in isolation — deterministic, no subprocess)
# -----------------------------------------------------------------------------


class TestGate1EnvFlag(unittest.TestCase):
    """Gate 1 — CEO_CHAOS_ALLOWED must equal '1'."""

    def test_missing_env_fails(self):
        ok, reason = ci._gate_env_flag(env={})
        self.assertFalse(ok)
        self.assertIn("CEO_CHAOS_ALLOWED", reason)

    def test_wrong_value_fails(self):
        for v in ["0", "true", "yes", "", " 1 "]:
            ok, reason = ci._gate_env_flag(env={"CEO_CHAOS_ALLOWED": v})
            # Whitespace is trimmed — " 1 " → "1" → pass.
            if v.strip() == "1":
                self.assertTrue(ok, f"expected pass for {v!r}")
            else:
                self.assertFalse(ok, f"expected fail for {v!r}")

    def test_explicit_one_passes(self):
        ok, reason = ci._gate_env_flag(env={"CEO_CHAOS_ALLOWED": "1"})
        self.assertTrue(ok)
        self.assertEqual(reason, "")


class TestGate2ParentPytest(unittest.TestCase):
    """Gate 2 — parent process cmd contains 'pytest'.

    We cannot easily spawn a real pytest parent in a unit test, so we
    test the platform-specific readers instead: feed them a pid that
    exists (our own) and assert the detection works either way. Then
    feed a pid that definitely doesn't exist and assert the gate fails.
    """

    def test_fake_ppid_fails_closed(self):
        # Use a pid unlikely to exist (subject to PID-wraparound, but
        # picking a value above 4,000,000 works on every mainstream OS).
        ok, reason = ci._gate_parent_is_pytest(ppid=4_000_001)
        self.assertFalse(ok)
        self.assertIn("parent cmdline", reason)

    def test_reader_returns_none_for_nonexistent_linux(self):
        # Unit-test the Linux reader directly. On non-Linux it will
        # return None because /proc doesn't exist; that's also a valid
        # "fail-closed" outcome for the gate.
        result = ci._read_parent_cmdline_linux(4_000_001)
        self.assertIsNone(result)

    def test_reader_ps_returns_none_for_nonexistent(self):
        result = ci._read_parent_cmdline_ps(4_000_001)
        self.assertIsNone(result)


class TestGate3CwdChaos(unittest.TestCase):
    """Gate 3 — cwd contains 'tests/chaos/' substring."""

    def test_explicit_chaos_path_passes(self):
        ok, _ = ci._gate_cwd_is_chaos(cwd="/tmp/x/tests/chaos/nested")
        self.assertTrue(ok)

    def test_trailing_without_slash_passes(self):
        ok, _ = ci._gate_cwd_is_chaos(cwd="/tmp/x/tests/chaos")
        self.assertTrue(ok)

    def test_unrelated_cwd_fails(self):
        for cwd in ["/tmp/x", "/", "/Users/foo", "/tmp/tests/load/xx"]:
            ok, reason = ci._gate_cwd_is_chaos(cwd=cwd)
            self.assertFalse(ok, f"expected fail for {cwd!r}")
            self.assertIn("cwd", reason)


# -----------------------------------------------------------------------------
# Combined gates
# -----------------------------------------------------------------------------


class TestCombinedGates(unittest.TestCase):
    def test_all_three_closed_surfaces_all_reasons(self):
        ok, reasons = ci.check_all_gates(
            env={}, ppid=4_000_001, cwd="/tmp/not-chaos"
        )
        self.assertFalse(ok)
        # All three gates should report their own failure.
        joined = " | ".join(reasons)
        self.assertIn("GATE-1", joined)
        self.assertIn("GATE-2", joined)
        self.assertIn("GATE-3", joined)

    def test_only_gate1_closed_reports_only_gate1(self):
        # We cannot pass gate 2 without a real pytest parent, so use
        # a pid whose cmdline will be detectable but not contain
        # 'pytest'. Use PID 1 (init/launchd) — guaranteed to exist.
        ok, reasons = ci.check_all_gates(
            env={}, ppid=1, cwd="/tmp/tests/chaos/x"
        )
        self.assertFalse(ok)
        # At minimum GATE-1 must be in the failures.
        joined = " | ".join(reasons)
        self.assertIn("GATE-1", joined)

    def test_positive_path_all_open(self):
        # Fake a "pytest" parent by using THIS process's ppid and
        # hoping its command contains 'pytest' when run under pytest,
        # OR we skip this test if not running under pytest.
        ppid = os.getppid()
        # Check parent cmdline ourselves — if pytest is in it, great;
        # otherwise skip (we can't manufacture a pytest parent).
        raw = ci._read_parent_cmdline_ps(ppid)
        if raw is None or "pytest" not in raw:
            raw2 = ci._read_parent_cmdline_linux(ppid)
            if raw2 is None or "pytest" not in raw2:
                self.skipTest(
                    "parent process does not contain 'pytest'; "
                    "positive-path gate-2 test only runs under pytest"
                )
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tests" / "chaos" / "run"
            target.mkdir(parents=True)
            ok, reasons = ci.check_all_gates(
                env={"CEO_CHAOS_ALLOWED": "1"},
                ppid=ppid,
                cwd=str(target),
            )
            self.assertTrue(ok, f"expected all gates open, got {reasons}")


# -----------------------------------------------------------------------------
# CLI entry point — exit codes
# -----------------------------------------------------------------------------


class TestCLIExitCodes(unittest.TestCase):
    def test_ceo_chaos_allowed_unset_exits_2(self):
        # CLI reads live env + cwd. With CEO_CHAOS_ALLOWED unset,
        # gate 1 fails and the script exits 2 before doing anything.
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "wrapper.py"
            rc, _, err = _run_cli(
                [
                    "--hook", "check_agent_spawn",
                    "--mode", "exit1",
                    "--output", str(out_path),
                ],
                env={},  # explicitly no CEO_CHAOS_ALLOWED
                cwd=td,  # intentionally NOT a tests/chaos/ path
            )
            self.assertEqual(rc, ci.EXIT_GATE_FAIL)
            self.assertIn("lockdown engaged", err)
            self.assertIn("GATE-1", err)
            self.assertFalse(out_path.exists())

    def test_cwd_outside_chaos_exits_2(self):
        # Even WITH CEO_CHAOS_ALLOWED=1, a cwd outside tests/chaos/
        # closes gate 3.
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "wrapper.py"
            rc, _, err = _run_cli(
                [
                    "--hook", "check_agent_spawn",
                    "--mode", "exit1",
                    "--output", str(out_path),
                ],
                env={"CEO_CHAOS_ALLOWED": "1"},
                cwd=td,  # not a tests/chaos/ path
            )
            self.assertEqual(rc, ci.EXIT_GATE_FAIL)
            self.assertIn("GATE-3", err)

    def test_unknown_hook_exits_3(self):
        # argparse rejects a bad --hook with SystemExit; we remap to 3.
        rc, _, err = _run_cli(
            [
                "--hook", "not_a_real_hook",
                "--mode", "exit1",
                "--output", "/tmp/nope.py",
            ],
            env={"CEO_CHAOS_ALLOWED": "1"},
            cwd="/tmp",
        )
        self.assertEqual(rc, ci.EXIT_ARGS_FAIL)

    def test_invalid_mode_exits_3(self):
        rc, _, _ = _run_cli(
            [
                "--hook", "check_agent_spawn",
                "--mode", "not_a_real_mode",
                "--output", "/tmp/nope.py",
            ],
            env={"CEO_CHAOS_ALLOWED": "1"},
            cwd="/tmp",
        )
        self.assertEqual(rc, ci.EXIT_ARGS_FAIL)

    def test_missing_required_args_exits_3(self):
        rc, _, _ = _run_cli(
            ["--hook", "check_agent_spawn"],  # missing --mode and --output
            env={"CEO_CHAOS_ALLOWED": "1"},
            cwd="/tmp",
        )
        self.assertEqual(rc, ci.EXIT_ARGS_FAIL)


# -----------------------------------------------------------------------------
# Wrapper-source generation (no gates — pure I/O helper)
# -----------------------------------------------------------------------------


class TestWrapperGeneration(unittest.TestCase):
    def test_generate_wrapper_writes_script(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "wrapper.py"
            ci.generate_wrapper("check_agent_spawn", "exit1", out)
            self.assertTrue(out.is_file())
            content = out.read_text()
            self.assertIn("sys.exit(1)", content)
            self.assertIn("Auto-generated chaos wrapper", content)

    def test_generate_wrapper_all_modes(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in ci.ALL_MODES:
                out = Path(td) / f"w-{mode}.py"
                ci.generate_wrapper("audit_log", mode, out)
                self.assertTrue(out.is_file())
                content = out.read_text()
                # Every wrapper must have a main()+entry stanza.
                self.assertIn("def main()", content)
                self.assertIn("if __name__ == '__main__':", content)

    def test_wrapper_modes_behave_correctly_when_executed(self):
        """Execute each generated wrapper in subprocess; check behaviour."""
        with tempfile.TemporaryDirectory() as td:
            # exit1
            w = Path(td) / "exit1.py"
            ci.generate_wrapper("audit_log", "exit1", w)
            r = subprocess.run(
                [sys.executable, str(w)],
                input="", capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(r.returncode, 1)

            # exit99
            w = Path(td) / "exit99.py"
            ci.generate_wrapper("audit_log", "exit99", w)
            r = subprocess.run(
                [sys.executable, str(w)],
                input="", capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(r.returncode, 99)

            # garbage_stdout
            w = Path(td) / "garbage.py"
            ci.generate_wrapper("audit_log", "garbage_stdout", w)
            r = subprocess.run(
                [sys.executable, str(w)],
                input="", capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(r.returncode, 0)
            self.assertIn("not-json-", r.stdout)

            # stderr_spam
            w = Path(td) / "spam.py"
            ci.generate_wrapper("audit_log", "stderr_spam", w)
            r = subprocess.run(
                [sys.executable, str(w)],
                input="", capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(r.returncode, 0)
            # 100 spam lines on stderr.
            spam_lines = [line for line in r.stderr.splitlines() if "spam line" in line]
            self.assertEqual(len(spam_lines), 100)
            # stdout contains valid allow decision.
            self.assertIn('"decision":"allow"', r.stdout)

            # timeout — short timeout for test speed.
            w = Path(td) / "timeout.py"
            ci.generate_wrapper("audit_log", "timeout", w, timeout_seconds=0.2)
            r = subprocess.run(
                [sys.executable, str(w)],
                input="", capture_output=True, text=True, timeout=5,
            )
            # Timeout mode just sleeps then exits 0 — successful if
            # we don't hit the subprocess timeout.
            self.assertEqual(r.returncode, 0)

    def test_generate_wrapper_rejects_unknown_hook(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "w.py"
            with self.assertRaises(ValueError):
                ci.generate_wrapper("not_a_hook", "exit1", out)

    def test_generate_wrapper_rejects_unknown_mode(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "w.py"
            with self.assertRaises(ValueError):
                ci.generate_wrapper("audit_log", "not_a_mode", out)


if __name__ == "__main__":
    unittest.main()
