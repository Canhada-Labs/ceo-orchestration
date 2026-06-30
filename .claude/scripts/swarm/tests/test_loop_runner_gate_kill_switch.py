"""PLAN-102-FOLLOWUP — kill-switch coverage for LoopRunner gate.

Created by apply-patches.py (Codex R2 iter-1 P0 #3 fold) — covers AC6
kill-switch BLOCKS contract across the 6-layer chain (ADR-133 §Part 1
§6). Each test mocks a distinct gate reason and asserts emit + state
transition. Stdlib unittest + unittest.mock.patch.
"""
from __future__ import annotations

import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT / ".claude" / "hooks") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
if str(_REPO_ROOT / ".claude" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))

from _lib.testing import TestEnvContext  # noqa: E402

from swarm.coordinator import LoopState  # noqa: E402
from swarm.loop_runner import (  # noqa: E402
    DIRECTION_MINIMIZE,
    IterationResult,
    LoopRunner,
)


def _stub_iterate(_state: LoopState) -> IterationResult:
    return IterationResult(
        metric=1.0, tokens_delta=10, files_touched=[], kept=True, error=None,
    )


def _fake_gate(enabled: bool, reason: str):
    fake_mod = types.ModuleType("_lib.swarm_enable_gate")
    fake_mod.is_class_enabled = lambda _t: (enabled, reason)  # type: ignore[attr-defined]
    return mock.patch.dict(
        sys.modules, {"_lib.swarm_enable_gate": fake_mod}, clear=False,
    )


class TestSixLayerKillSwitchChain(TestEnvContext):
    """6-layer chain (ADR-133 §Part 1 §6) — each independent gate reason
    blocks step() and emits with the collapsed reason_code."""

    def setUp(self):
        super().setUp()
        # PLAN-102-FOLLOWUP S145 Fix #3 (Codex triage 019e42fc): Layer-1
        # swarm-on env required for gate to fire (Fix #1 early-return guard).
        os.environ["CEO_SWARM"] = "1"

    def _make(self) -> LoopRunner:
        return LoopRunner(
            loop_id="L_kill_test",
            goal="g",
            max_iterations=3,
            max_strikes=3,
            budget_tokens=1000,
            direction=DIRECTION_MINIMIZE,
            iterate=_stub_iterate,
            class_tier="vibecoder",
        )

    def _assert_blocked(self, reason_internal: str, reason_emit: str) -> None:
        with _fake_gate(False, reason_internal):
            with mock.patch(
                "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
            ) as emit_mock:
                runner = self._make()
                result = runner.step()
                self.assertEqual(runner.state.status, "killed")
                self.assertTrue(math.isnan(result.metric))
                self.assertEqual(
                    emit_mock.call_args.kwargs.get("reason_code"),
                    reason_emit,
                    f"reason {reason_internal!r} should collapse to {reason_emit!r}",
                )

    def test_layer_1_2_env_disable_master(self):
        """CEO_AUTONOMOUS_LOOPS_DISABLE=1 (master kill) - represented
        here via gate_disabled short-circuit collapse."""
        self._assert_blocked("gate_disabled", "kill_switch")

    def test_layer_3_sentinel_absent(self):
        self._assert_blocked("sentinel_absent", "layer_3_unavailable")

    def test_layer_3_sentinel_bad_signature(self):
        self._assert_blocked("sentinel_bad_signature", "layer_3_unavailable")

    def test_layer_3_stdlib_gpg_unavailable(self):
        self._assert_blocked("stdlib_gpg_unavailable", "layer_3_unavailable")

    def test_layer_4_env_flag_unset(self):
        self._assert_blocked("env_flag_unset", "layer_4_unset")

    def test_layer_4_env_flag_not_1(self):
        self._assert_blocked("env_flag_not_1", "layer_4_unset")


class TestKillSwitchEnvShortCircuit(TestEnvContext):
    """CEO_SWARM_ENABLE_GATE_DISABLE=1 env short-circuit. The real
    `is_class_enabled` returns (False, "gate_disabled") immediately;
    this test patches the gate stub directly to mimic that path."""

    def setUp(self):
        super().setUp()
        # PLAN-102-FOLLOWUP S145 Fix #3 (Codex triage 019e42fc): Layer-1
        # swarm-on env required for gate to fire (Fix #1 early-return guard).
        os.environ["CEO_SWARM"] = "1"

    def test_env_short_circuit_blocks_with_kill_switch_reason(self):
        os.environ["CEO_SWARM_ENABLE_GATE_DISABLE"] = "1"
        try:
            with _fake_gate(False, "gate_disabled"):
                with mock.patch(
                    "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
                ) as emit_mock:
                    runner = LoopRunner(
                        loop_id="L_env_kill",
                        goal="g",
                        max_iterations=3,
                        max_strikes=3,
                        budget_tokens=1000,
                        direction=DIRECTION_MINIMIZE,
                        iterate=_stub_iterate,
                        class_tier="vibecoder",
                    )
                    pre = len(runner.history)
                    runner.step()
                    self.assertEqual(len(runner.history), pre + 1)
                    self.assertEqual(runner.state.status, "killed")
                    self.assertEqual(
                        emit_mock.call_args.kwargs.get("reason_code"),
                        "kill_switch",
                    )
        finally:
            os.environ.pop("CEO_SWARM_ENABLE_GATE_DISABLE", None)


if __name__ == "__main__":
    unittest.main()
