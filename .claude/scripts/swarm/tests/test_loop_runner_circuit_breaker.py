"""PLAN-113 Phase C R1 — circuit-breaker wiring tests for LoopRunner.step().

Covers the B.4/B.5 SwarmCircuitBreaker integration wired in
_gate_step_check / _circuit_breaker_step_check:

  - Fires when B.4 (reverse-tripwire) threshold is exceeded
  - Fires when B.5 (weekend-burn) threshold is exceeded
  - Strict no-op when CEO_SWARM != "1" (default-OFF)
  - Strict no-op when CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1 (breaker disabled)
  - Fail-CLOSED when breaker module is unimportable (within gated path)
  - Fail-CLOSED when breaker raises on call (within gated path)
  - Correct audit actions emitted (swarm_runaway_suspected /
    swarm_paused_owner_absent) with no regression to swarm_layer_3_4_blocked

Uses stdlib unittest + unittest.mock. TestEnvContext from _lib.testing
provides HOME + env isolation so no real audit log is touched.
"""
from __future__ import annotations

import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

# Bootstrap sys.path so `_lib.testing` and swarm modules resolve.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_LIB_PARENT = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS = _REPO_ROOT / ".claude" / "scripts"
if str(_HOOKS_LIB_PARENT) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB_PARENT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _lib.testing import TestEnvContext  # noqa: E402

from swarm.coordinator import LoopState  # noqa: E402
from swarm.loop_runner import (  # noqa: E402
    DIRECTION_MINIMIZE,
    IterationResult,
    LoopRunner,
    _resolve_breaker_audit_log_path,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _green_iterate(_state: LoopState) -> IterationResult:
    return IterationResult(metric=1.0, tokens_delta=10, kept=True, error=None)


def _make_runner(class_tier: str = "vibecoder") -> LoopRunner:
    return LoopRunner(
        loop_id="L_cb_test",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_green_iterate,
        class_tier=class_tier,
    )


def _install_fake_gate_enabled() -> "mock._patch":
    """Install a stub swarm_enable_gate that always returns (True, '')."""
    fake_mod = types.ModuleType("_lib.swarm_enable_gate")
    fake_mod.is_class_enabled = lambda _ct: (True, "")  # type: ignore[attr-defined]
    return mock.patch.dict(sys.modules, {"_lib.swarm_enable_gate": fake_mod}, clear=False)


def _install_fake_breaker(b4: bool = False, b5: bool = False) -> "mock._patch":
    """Install a stub swarm_circuit_breaker returning configured booleans."""
    fake_mod = types.ModuleType("_lib.swarm_circuit_breaker")

    class _FakeBreaker:
        @staticmethod
        def should_pause_reverse_tripwire(_path, **_kw) -> bool:
            return b4

        @staticmethod
        def should_pause_weekend_burn(_path, **_kw) -> bool:
            return b5

    fake_mod.SwarmCircuitBreaker = _FakeBreaker  # type: ignore[attr-defined]
    return mock.patch.dict(
        sys.modules,
        {
            "_lib.swarm_circuit_breaker": fake_mod,
            "swarm._lib.swarm_circuit_breaker": fake_mod,
        },
        clear=False,
    )


class _FakeEmitContext:
    """Context manager that installs a fake audit_emit module and collects
    emit_generic calls.

    The `from _lib import audit_emit` pattern in loop_runner requires
    that BOTH sys.modules["_lib.audit_emit"] AND sys.modules["_lib"].audit_emit
    (the attribute on the _lib package object) are set to the fake — otherwise
    `from _lib import audit_emit` resolves from the cached package and misses
    the mock (verified against existing test_loop_runner_gate_enforcement.py
    pattern that sets sys.modules["_lib"].audit_emit explicitly).
    """

    def __init__(self) -> None:
        self.emitted: list = []
        self._saved_attr = None
        self._had_attr = False
        self._patch: "mock._patch" = None  # type: ignore[assignment]
        self._fake: "types.SimpleNamespace" = None  # type: ignore[assignment]

    def __enter__(self) -> "list":
        self._fake = types.SimpleNamespace(
            emit_generic=lambda action, **kw: self.emitted.append((action, kw))
        )
        lib_mod = sys.modules.get("_lib")
        if lib_mod is not None:
            self._had_attr = hasattr(lib_mod, "audit_emit")
            self._saved_attr = getattr(lib_mod, "audit_emit", None)
            lib_mod.audit_emit = self._fake  # type: ignore[attr-defined]
        self._patch = mock.patch.dict(
            sys.modules, {"_lib.audit_emit": self._fake}, clear=False
        )
        self._patch.start()
        return self.emitted

    def __exit__(self, *_exc) -> None:
        self._patch.stop()
        lib_mod = sys.modules.get("_lib")
        if lib_mod is not None:
            if self._had_attr:
                lib_mod.audit_emit = self._saved_attr  # type: ignore[attr-defined]
            elif hasattr(lib_mod, "audit_emit"):
                try:
                    delattr(lib_mod, "audit_emit")
                except AttributeError:
                    pass


# ---------------------------------------------------------------------------
# _resolve_breaker_audit_log_path
# ---------------------------------------------------------------------------

class TestResolveBreakerAuditLogPath(TestEnvContext):
    """Env-override logic mirrors audit_emit._log_path()."""

    def test_ceo_audit_log_path_env_wins(self):
        os.environ["CEO_AUDIT_LOG_PATH"] = "/tmp/test-audit.jsonl"
        p = _resolve_breaker_audit_log_path()
        self.assertEqual(str(p), "/tmp/test-audit.jsonl")

    def test_ceo_audit_log_dir_env_appends_filename(self):
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        os.environ["CEO_AUDIT_LOG_DIR"] = "/tmp/mydir"
        p = _resolve_breaker_audit_log_path()
        self.assertEqual(p.name, "audit-log.jsonl")
        self.assertTrue(str(p).startswith("/tmp/mydir"))

    def test_default_path_under_home(self):
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        os.environ.pop("CEO_AUDIT_LOG_DIR", None)
        p = _resolve_breaker_audit_log_path()
        self.assertIn("ceo-orchestration", str(p))
        self.assertTrue(str(p).endswith("audit-log.jsonl"))


# ---------------------------------------------------------------------------
# Default-OFF — no CEO_SWARM=1
# ---------------------------------------------------------------------------

class TestDefaultOff(TestEnvContext):
    """When CEO_SWARM != '1', _gate_step_check returns None immediately
    (before even touching the breaker). LoopRunner.step() proceeds normally."""

    def test_no_ceo_swarm_env_bypasses_gate_and_breaker(self):
        """Default env has no CEO_SWARM — gate + breaker must be silent no-ops."""
        os.environ.pop("CEO_SWARM", None)
        os.environ.pop("CEO_EXECUTION_CONTEXT_HOOKS_DISABLE", None)

        breaker_calls = []

        fake_mod = types.ModuleType("_lib.swarm_circuit_breaker")

        class _SpyBreaker:
            @staticmethod
            def should_pause_reverse_tripwire(_path, **_kw):
                breaker_calls.append("b4")
                return True  # would fire if reached

            @staticmethod
            def should_pause_weekend_burn(_path, **_kw):
                breaker_calls.append("b5")
                return True

        fake_mod.SwarmCircuitBreaker = _SpyBreaker  # type: ignore[attr-defined]

        with mock.patch.dict(sys.modules, {"_lib.swarm_circuit_breaker": fake_mod}):
            runner = _make_runner()
            result = runner.step()
            # Breaker was never called
            self.assertEqual(breaker_calls, [], "Breaker called when CEO_SWARM absent")
            # Step succeeded (iterate ran)
            self.assertEqual(result.metric, 1.0)
            self.assertEqual(runner.state.status, "running")


# ---------------------------------------------------------------------------
# Breaker disabled via CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1
# ---------------------------------------------------------------------------

class TestBreakerDisabledEnvFlag(TestEnvContext):
    """When CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1, the real
    SwarmCircuitBreaker methods return False — gate step-check passes through."""

    def test_breaker_disabled_flag_no_op(self):
        os.environ["CEO_SWARM"] = "1"
        os.environ["CEO_EXECUTION_CONTEXT_HOOKS_DISABLE"] = "1"

        with _install_fake_gate_enabled():
            # Use REAL breaker module — disabled=True → both return False.
            # (The real module's is_disabled() checks the env flag.)
            runner = _make_runner()
            result = runner.step()
            # iterate() ran — breaker was a no-op
            self.assertEqual(result.metric, 1.0)
            self.assertIsNone(result.error)
            self.assertEqual(runner.state.status, "running")


# ---------------------------------------------------------------------------
# B.4 reverse-tripwire fires
# ---------------------------------------------------------------------------

class TestBreakerB4Fires(TestEnvContext):
    """When B.4 fires: step() returns killed IterationResult + emits
    swarm_runaway_suspected + does NOT emit swarm_layer_3_4_blocked."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_b4_fires_kills_runner(self):
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=True, b5=False):
                runner = _make_runner()
                result = runner.step()

        self.assertTrue(math.isnan(result.metric))
        self.assertEqual(result.tokens_delta, 0)
        self.assertFalse(result.kept)
        self.assertEqual(result.error, "circuit_breaker_b4_runaway")
        self.assertEqual(runner.state.status, "killed")

    def test_b4_fires_emits_swarm_runaway_suspected(self):
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=True, b5=False):
                with _FakeEmitContext() as emitted:
                    runner = _make_runner()
                    runner.step()

        actions = [a for a, _ in emitted]
        self.assertIn("swarm_runaway_suspected", actions,
                      "Expected swarm_runaway_suspected to be emitted")
        self.assertNotIn("swarm_layer_3_4_blocked", actions,
                         "swarm_layer_3_4_blocked must NOT be emitted on breaker fire")
        self.assertNotIn("swarm_paused_owner_absent", actions,
                         "swarm_paused_owner_absent must NOT be emitted for B.4")

    def test_b4_fires_history_invariant(self):
        """Synthetic IterationResult is appended to history BEFORE early return."""
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=True, b5=False):
                runner = _make_runner()
                pre = len(runner.history)
                result = runner.step()
                self.assertEqual(len(runner.history), pre + 1)
                self.assertIs(runner.history[-1], result)

    def test_b4_fires_runaway_suspected_fields(self):
        """swarm_runaway_suspected emitted with correct domain fields."""
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=True, b5=False):
                with _FakeEmitContext() as emitted:
                    runner = _make_runner(class_tier="CTO")
                    runner.step()

        rows = [(a, kw) for a, kw in emitted if a == "swarm_runaway_suspected"]
        self.assertEqual(len(rows), 1)
        _action, kw = rows[0]
        self.assertIn("iteration_count_24h", kw)
        self.assertIn("threshold", kw)
        self.assertIn("triggering_class", kw)
        self.assertEqual(kw["triggering_class"], "CTO")


# ---------------------------------------------------------------------------
# B.5 weekend-burn fires
# ---------------------------------------------------------------------------

class TestBreakerB5Fires(TestEnvContext):
    """When B.5 fires: step() returns killed IterationResult + emits
    swarm_paused_owner_absent."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_b5_fires_kills_runner(self):
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=False, b5=True):
                runner = _make_runner()
                result = runner.step()

        self.assertTrue(math.isnan(result.metric))
        self.assertEqual(result.error, "circuit_breaker_b5_weekend_burn")
        self.assertEqual(runner.state.status, "killed")

    def test_b5_fires_emits_swarm_paused_owner_absent(self):
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=False, b5=True):
                with _FakeEmitContext() as emitted:
                    runner = _make_runner()
                    runner.step()

        actions = [a for a, _ in emitted]
        self.assertIn("swarm_paused_owner_absent", actions)
        self.assertNotIn("swarm_runaway_suspected", actions)

    def test_b5_fields_include_swarm_pid(self):
        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=False, b5=True):
                with _FakeEmitContext() as emitted:
                    runner = _make_runner()
                    runner.step()

        rows = [(a, kw) for a, kw in emitted if a == "swarm_paused_owner_absent"]
        self.assertEqual(len(rows), 1)
        _action, kw = rows[0]
        self.assertIn("swarm_pid", kw)
        self.assertIn("loop_duration_hours", kw)
        self.assertGreaterEqual(kw["loop_duration_hours"], 1)


# ---------------------------------------------------------------------------
# Fail-CLOSED on breaker import error (within gated path)
# ---------------------------------------------------------------------------

class TestBreakerImportFailedClosedGatedPath(TestEnvContext):
    """When the breaker module is unimportable and CEO_SWARM=1 (gated path),
    dispatch is DENIED (fail-CLOSED). This differs from the Layer 3+4 gate
    infra-unavailable path (fail-open there, fail-closed here)."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_breaker_import_failure_blocks_dispatch(self):
        # Inject a broken stub: module exists but SwarmCircuitBreaker attr missing
        # → AttributeError on access → caught by outer try/except → fail-CLOSED.
        broken = types.ModuleType("_lib.swarm_circuit_breaker")
        # Deliberately do NOT set SwarmCircuitBreaker on broken module.

        with _install_fake_gate_enabled():
            with mock.patch.dict(
                sys.modules,
                {
                    "_lib.swarm_circuit_breaker": broken,
                    "swarm._lib.swarm_circuit_breaker": broken,
                },
                clear=False,
            ):
                runner = _make_runner()
                result = runner.step()

        # Must be denied (fail-CLOSED): status killed, metric NaN
        self.assertTrue(math.isnan(result.metric))
        self.assertEqual(runner.state.status, "killed")
        self.assertIsNotNone(result.error)
        # error is one of the circuit_breaker_* variants
        self.assertIn("circuit_breaker", result.error)


# ---------------------------------------------------------------------------
# Fail-CLOSED on breaker call error (within gated path)
# ---------------------------------------------------------------------------

class TestBreakerCallRaisesClosedGatedPath(TestEnvContext):
    """When SwarmCircuitBreaker.should_pause_reverse_tripwire raises,
    dispatch is DENIED (fail-CLOSED within the gated path)."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_b4_raises_blocks_dispatch(self):
        fake_mod = types.ModuleType("_lib.swarm_circuit_breaker")

        class _RaisingBreaker:
            @staticmethod
            def should_pause_reverse_tripwire(_path, **_kw):
                raise RuntimeError("injected b4 failure")

            @staticmethod
            def should_pause_weekend_burn(_path, **_kw):
                return False

        fake_mod.SwarmCircuitBreaker = _RaisingBreaker  # type: ignore[attr-defined]

        with _install_fake_gate_enabled():
            with mock.patch.dict(
                sys.modules,
                {
                    "_lib.swarm_circuit_breaker": fake_mod,
                    "swarm._lib.swarm_circuit_breaker": fake_mod,
                },
                clear=False,
            ):
                runner = _make_runner()
                result = runner.step()

        self.assertTrue(math.isnan(result.metric))
        self.assertEqual(runner.state.status, "killed")
        self.assertEqual(result.error, "circuit_breaker_b4_error")

    def test_b5_raises_blocks_dispatch(self):
        fake_mod = types.ModuleType("_lib.swarm_circuit_breaker")

        class _RaisingB5Breaker:
            @staticmethod
            def should_pause_reverse_tripwire(_path, **_kw):
                return False  # B.4 passes

            @staticmethod
            def should_pause_weekend_burn(_path, **_kw):
                raise RuntimeError("injected b5 failure")

        fake_mod.SwarmCircuitBreaker = _RaisingB5Breaker  # type: ignore[attr-defined]

        with _install_fake_gate_enabled():
            with mock.patch.dict(
                sys.modules,
                {
                    "_lib.swarm_circuit_breaker": fake_mod,
                    "swarm._lib.swarm_circuit_breaker": fake_mod,
                },
                clear=False,
            ):
                runner = _make_runner()
                result = runner.step()

        self.assertTrue(math.isnan(result.metric))
        self.assertEqual(runner.state.status, "killed")
        self.assertEqual(result.error, "circuit_breaker_b5_error")


# ---------------------------------------------------------------------------
# Both breakers pass → iterate() runs normally
# ---------------------------------------------------------------------------

class TestBreakerPassThrough(TestEnvContext):
    """When both B.4+B.5 pass, step() proceeds to iterate() normally."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_both_pass_iterate_runs(self):
        called = []

        def _spy_iterate(state: LoopState) -> IterationResult:
            called.append(state.iteration)
            return IterationResult(metric=2.5, tokens_delta=20, kept=True)

        with _install_fake_gate_enabled():
            with _install_fake_breaker(b4=False, b5=False):
                runner = LoopRunner(
                    loop_id="L_pass",
                    goal="g",
                    max_iterations=5,
                    max_strikes=3,
                    budget_tokens=1000,
                    direction=DIRECTION_MINIMIZE,
                    iterate=_spy_iterate,
                    class_tier="vibecoder",
                )
                result = runner.step()

        self.assertEqual(len(called), 1)
        self.assertEqual(result.metric, 2.5)
        self.assertIsNone(result.error)
        self.assertEqual(runner.state.status, "running")


# ---------------------------------------------------------------------------
# Regression: Layer 3+4 block path still works (no regression)
# ---------------------------------------------------------------------------

class TestLayer34BlockPathRegression(TestEnvContext):
    """Ensure the original Layer 3+4 gate-block path still works after
    refactor — when gate returns (False, reason), swarm_layer_3_4_blocked
    is emitted and the breaker is NOT reached."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_SWARM"] = "1"

    def test_layer34_block_emits_correct_action_not_breaker_action(self):
        fake_gate = types.ModuleType("_lib.swarm_enable_gate")
        fake_gate.is_class_enabled = lambda _ct: (False, "sentinel_absent")  # type: ignore[attr-defined]

        breaker_calls = []
        fake_breaker = types.ModuleType("_lib.swarm_circuit_breaker")

        class _SpyBreaker:
            @staticmethod
            def should_pause_reverse_tripwire(_p, **_kw):
                breaker_calls.append("b4")
                return False

            @staticmethod
            def should_pause_weekend_burn(_p, **_kw):
                breaker_calls.append("b5")
                return False

        fake_breaker.SwarmCircuitBreaker = _SpyBreaker  # type: ignore[attr-defined]

        with mock.patch.dict(
            sys.modules,
            {
                "_lib.swarm_enable_gate": fake_gate,
                "_lib.swarm_circuit_breaker": fake_breaker,
            },
            clear=False,
        ):
            with _FakeEmitContext() as emitted:
                runner = _make_runner()
                result = runner.step()

        self.assertEqual(result.error, "layer_3_4_sentinel_absent")
        self.assertEqual(runner.state.status, "killed")
        actions = [a for a, _ in emitted]
        self.assertIn("swarm_layer_3_4_blocked", actions)
        # Breaker must NOT have been called (gate blocked first)
        self.assertEqual(breaker_calls, [], "Breaker was called after Layer 3+4 blocked")


if __name__ == "__main__":
    unittest.main()
