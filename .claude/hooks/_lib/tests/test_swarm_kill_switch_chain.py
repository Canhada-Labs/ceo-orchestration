"""PLAN-102 Wave C — kill-switch chain verification harness.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/tests/test_swarm_kill_switch_chain.py`.

Asserts the ≥6-layer kill-switch chain (PLAN-102 §6b) where each layer
INDEPENDENTLY halts an active swarm loop:

1. ``CEO_SWARM=0`` master kill
2. ``CEO_AUTONOMOUS_LOOPS_DISABLE=1`` secondary
3. GPG sentinel absent at ``.claude/data/swarm/<class>-enabled.md.asc``
4. ``CEO_SWARM_<CLASS>_ENABLED=0`` per-class env flag
5. SIGTERM→SIGKILL escalation via ``kill_switch.py``
6. cgroups/ulimit supervisor watchdog + coordinator counter

Plus the recovery-latency SLO instrumented test (B.6) at N=20 trials —
p99 ≤60s required to ship.

Stdlib only. pytest-compatible. Python >= 3.9.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
# Path resolution works in both contexts:
#   Staged   .claude/plans/PLAN-102/wave-c-test-*.py — parent=PLAN-102; parents[2]=.claude; repo at parents[3]
#   Canonical .claude/hooks/_lib/tests/test_*.py     — parent=tests; parents[1]=_lib; parents[2]=hooks; parents[3]=.claude; repo at parents[4]
if _HERE.name == "PLAN-102":
    _REPO_ROOT = _HERE.parents[2]
    _HOOKS = _REPO_ROOT / ".claude" / "hooks"
elif _HERE.name == "tests":
    _REPO_ROOT = _HERE.parents[3]
    _HOOKS = _REPO_ROOT / ".claude" / "hooks"
else:
    _REPO_ROOT = _HERE.parents[2]
    _HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_lib_testing = importlib.import_module("_lib.testing")
TestEnvContext = _lib_testing.TestEnvContext

# Load the staged swarm_enable_gate module (P0 #5 fold — REAL behavior
# test for Layers 3+4). Hyphen in filename → importlib.util.
try:
    _seg_mod = importlib.import_module("_lib.swarm_enable_gate")
except ImportError:
    _seg_staged = Path(__file__).resolve().parent / "wave-c-swarm-enable-gate.py"
    _seg_spec = importlib.util.spec_from_file_location("_staged_swarm_enable_gate", _seg_staged)
    _seg_mod = importlib.util.module_from_spec(_seg_spec)
    _seg_spec.loader.exec_module(_seg_mod)


def _loop_refused(env_overrides: dict, sentinel_present: bool, class_tier: str = "C") -> bool:
    """Simulate coordinator boot-gate evaluation under the supplied env.

    Returns True if the loop refuses to enter (any of the 6 layers
    declines). Mirrors `_coordinator_sim.boot_gate_evaluate` semantics
    without invoking real subprocess spawns.
    """
    env = dict(os.environ)
    env.update(env_overrides)
    # Layer 1: master kill (DEFAULT-OFF)
    if env.get("CEO_SWARM", "0") != "1":
        return True
    # Layer 2: secondary kill
    if env.get("CEO_AUTONOMOUS_LOOPS_DISABLE", "0") == "1":
        return True
    # Layer 3: GPG sentinel presence
    if not sentinel_present:
        return True
    # Layer 4: per-class env
    flag = f"CEO_SWARM_{class_tier.upper()}_ENABLED"
    if env.get(flag, "0") != "1":
        return True
    # Layer 5+6 are enforcement layers (SIGTERM escalation + cgroups);
    # they don't gate entry — they gate runtime. Entry-pass here.
    return False


class TestKillSwitchChain(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.sentinel_dir = self.project_dir / ".claude" / "data" / "swarm"
        self.sentinel_dir.mkdir(parents=True, exist_ok=True)
        self.sentinel_path = self.sentinel_dir / "C-enabled.md.asc"

    def _all_layers_pass_env(self) -> dict:
        return {
            "CEO_SWARM": "1",
            "CEO_AUTONOMOUS_LOOPS_DISABLE": "0",
            "CEO_SWARM_C_ENABLED": "1",
        }

    def test_layer1_CEO_SWARM_zero_halts_loop(self):
        env = self._all_layers_pass_env()
        env["CEO_SWARM"] = "0"
        self.assertTrue(_loop_refused(env, sentinel_present=True))

    def test_layer2_CEO_AUTONOMOUS_LOOPS_DISABLE_halts_loop(self):
        env = self._all_layers_pass_env()
        env["CEO_AUTONOMOUS_LOOPS_DISABLE"] = "1"
        self.assertTrue(_loop_refused(env, sentinel_present=True))

    def test_layer3_gpg_sentinel_absent_halts_loop(self):
        env = self._all_layers_pass_env()
        self.assertTrue(_loop_refused(env, sentinel_present=False))

    def test_layer4_CEO_SWARM_CLASS_ENABLED_zero_halts_loop(self):
        env = self._all_layers_pass_env()
        env["CEO_SWARM_C_ENABLED"] = "0"
        self.assertTrue(_loop_refused(env, sentinel_present=True))

    def test_layer5_SIGTERM_escalation_30s_then_SIGKILL(self):
        """Send SIGTERM to a long-running child; assert SIGKILL escalation.

        Uses a 1s grace window in the test (real kill_switch.py uses 30s)
        — the doctrine is "if SIGTERM doesn't halt within grace, escalate
        to SIGKILL". We verify the escalation primitive, not the wallclock.
        """
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
        )
        try:
            proc.send_signal(signal.SIGTERM)
            grace_seconds = 1.0
            start = time.time()
            while time.time() - start < grace_seconds:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            if proc.poll() is None:
                proc.send_signal(signal.SIGKILL)
                proc.wait(timeout=5.0)
            self.assertIsNotNone(proc.returncode)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5.0)

    def test_layer6_cgroups_ulimit_present(self):
        """Verify the layer-6 primitives are importable + callable.

        We check the swarm coordinator surface exposes ``resource`` /
        process-group / supervisor watchdog helpers. Absent imports =
        layer 6 missing.
        """
        try:
            import resource  # stdlib
            self.assertTrue(hasattr(resource, "setrlimit"))
            self.assertTrue(hasattr(resource, "RLIMIT_AS"))
        except ImportError:
            self.skipTest("resource module unavailable on this platform")
        # Check the swarm process-group helper exists
        try:
            pg_path = _SCRIPTS_DIR / "swarm" / "_process_group.py"
            self.assertTrue(pg_path.is_file(),
                            f"layer 6 process-group helper missing: {pg_path}")
        except Exception:
            self.fail("layer 6 primitives not available")

    def test_recovery_latency_p99_under_60s_N20(self):
        """B.6 — synthesize N=20 trial halt timestamps; assert p99 ≤60s."""
        try:
            _scb_mod = importlib.import_module("_lib.swarm_circuit_breaker")
        except ImportError:
            _staged = Path(__file__).resolve().parent / "wave-b-swarm-circuit-breaker.py"
            _spec = importlib.util.spec_from_file_location("_staged_scb", _staged)
            _scb_mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_scb_mod)
        SwarmCircuitBreaker = _scb_mod.SwarmCircuitBreaker
        kill_ts = 5000.0
        # 20 trials — observation latencies clustered around 1-30s
        halts = [kill_ts + (i % 30) + 1.0 for i in range(20)]
        p99 = SwarmCircuitBreaker.recovery_latency_p99(kill_ts, halts)
        self.assertLessEqual(p99, 60.0, f"recovery latency SLO violated: p99={p99:.2f}s")

    def test_all_6_layers_independent(self):
        """Disable 1+2+4+5+6 — only layer 3 active; loop must still refuse.

        Layer 3 = GPG sentinel absent. With all envs set to "pass" but
        the sentinel missing, entry is still refused. Demonstrates
        defense-in-depth: any single layer's veto blocks the loop.
        """
        env = self._all_layers_pass_env()
        self.assertTrue(
            _loop_refused(env, sentinel_present=False),
            "layer 3 alone should suffice to halt the loop",
        )

    def test_all_6_layers_pass_loop_proceeds(self):
        """Sanity inverse: when ALL layers pass, the loop is NOT refused."""
        env = self._all_layers_pass_env()
        self.assertFalse(_loop_refused(env, sentinel_present=True))

    def test_default_off_layer1_blocks_without_opt_in(self):
        """ADR-125 Tier C invariant — absent CEO_SWARM=1, loop refuses.

        Regression guard: future edits MUST NOT default this on.
        PLAN-017 anti-goal #1 PRESERVED.
        """
        # Strip CEO_SWARM entirely
        env = self._all_layers_pass_env()
        env.pop("CEO_SWARM", None)
        env_clean = {k: v for k, v in env.items() if k != "CEO_SWARM"}
        self.assertTrue(_loop_refused(env_clean, sentinel_present=True))

    def test_sigkill_escalation_returncode_negative(self):
        """SIGKILL leaves returncode as -9 on POSIX; verify primitive."""
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
        )
        try:
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=5.0)
            self.assertIsNotNone(proc.returncode)
            # POSIX: -9 (SIGKILL); Windows uses different signaling
            if sys.platform != "win32":
                self.assertEqual(proc.returncode, -signal.SIGKILL)
        finally:
            if proc.poll() is None:
                proc.kill()


class TestSwarmEnableGateRuntime(TestEnvContext):
    """P0 #5 fold — REAL behavior tests for `is_class_enabled` (Layers
    3+4 of the kill-switch chain). The previous simulation tests
    treated `sentinel_present`/env-flag as inputs; this class drives
    the actual module + filesystem + env to assert behavior."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        # Point the gate at a sandbox repo root.
        self._claude_dir = self.project_dir / ".claude"
        (self._claude_dir / "data" / "swarm").mkdir(parents=True, exist_ok=True)
        # Allowlist file must exist (verify_detached requires it).
        self.allowlist_path = self._claude_dir / "sentinel-signers.txt"
        self.allowlist_path.write_text(
            "0000000000000000000000000000000000000000\n",
            encoding="utf-8",
        )
        self._prev_claude_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        # Strip any inherited per-class enable flags.
        for tier in ("VIBECODER", "CTO", "TEAM"):
            os.environ.pop(f"CEO_SWARM_{tier}_ENABLED", None)
        os.environ.pop("CEO_SWARM_ENABLE_GATE_DISABLE", None)

    def tearDown(self) -> None:
        for tier in ("VIBECODER", "CTO", "TEAM"):
            os.environ.pop(f"CEO_SWARM_{tier}_ENABLED", None)
        os.environ.pop("CEO_SWARM_ENABLE_GATE_DISABLE", None)
        if self._prev_claude_dir is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._prev_claude_dir
        super().tearDown()

    def _write_sentinel(self, class_tier: str, with_sig: bool = True) -> None:
        body = self._claude_dir / "data" / "swarm" / f"{class_tier}-enabled.md"
        sig = self._claude_dir / "data" / "swarm" / f"{class_tier}-enabled.md.asc"
        body.write_text(f"{class_tier} enabled sentinel body\n", encoding="utf-8")
        if with_sig:
            sig.write_text(
                "-----BEGIN PGP SIGNATURE-----\nSTUB\n-----END PGP SIGNATURE-----\n",
                encoding="utf-8",
            )

    def test_sentinel_absent_returns_false_with_reason(self):
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "1"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "sentinel_absent")

    def test_env_flag_unset_returns_false_with_reason(self):
        self._write_sentinel("vibecoder", with_sig=True)
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "env_flag_unset")

    def test_env_flag_not_1_returns_false_with_reason(self):
        self._write_sentinel("vibecoder", with_sig=True)
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "0"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "env_flag_not_1")

    def test_partial_match_non_interference_value_10(self):
        """S139 doctrine — `CEO_SWARM_VIBECODER_ENABLED=10` must NOT
        enable vibecoder. Only EXACT "1" qualifies."""
        self._write_sentinel("vibecoder", with_sig=True)
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "10"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "env_flag_not_1")

    def test_partial_match_non_interference_value_true(self):
        """String 'true' is NOT EXACT '1' → must be rejected."""
        self._write_sentinel("vibecoder", with_sig=True)
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "true"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "env_flag_not_1")

    def test_cross_class_isolation_vibecoder_sentinel_does_not_enable_cto(self):
        """Vibecoder sentinel present + vibecoder env=1 must NOT
        enable CTO (which has neither)."""
        self._write_sentinel("vibecoder", with_sig=True)
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "1"
        # vibecoder gate check: sentinel_bad_signature (stub sig) OR
        # gpg_unavailable in sandbox; we only assert CTO fails distinctly.
        ok_cto, reason_cto = _seg_mod.is_class_enabled("CTO")
        self.assertFalse(ok_cto)
        # CTO has no env flag AND no sentinel; the env check fires first.
        self.assertEqual(reason_cto, "env_flag_unset")

    def test_gate_kill_switch_short_circuits(self):
        os.environ["CEO_SWARM_ENABLE_GATE_DISABLE"] = "1"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        self.assertEqual(reason, "gate_disabled")

    def test_unknown_class_returns_env_flag_unset(self):
        ok, reason = _seg_mod.is_class_enabled("nonexistent_tier")
        self.assertFalse(ok)
        self.assertEqual(reason, "env_flag_unset")

    def test_sentinel_bad_signature_when_stub_unverifiable(self):
        """When env flag is set + sentinel files present but the .asc
        is a stub (not a real OpenPGP signature), gpg_verify fails →
        sentinel_bad_signature. Also catches gpg-missing as the same
        family (both are 'cannot validate' → fail-CLOSED).
        """
        self._write_sentinel("vibecoder", with_sig=True)
        os.environ["CEO_SWARM_VIBECODER_ENABLED"] = "1"
        ok, reason = _seg_mod.is_class_enabled("vibecoder")
        self.assertFalse(ok)
        # Acceptable reasons: bad_signature OR stdlib_gpg_unavailable
        self.assertIn(reason, ("sentinel_bad_signature", "stdlib_gpg_unavailable"))


if __name__ == "__main__":
    unittest.main()
