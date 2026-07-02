"""PLAN-102-FOLLOWUP — sentinel revocation SLO test (AC10 / AC17).

Created by apply-patches.py (Codex R2 iter-1 P0 #3 fold).

SLO: time-to-revocation < 30s from the moment Owner revokes sentinel
(state change visible to `is_class_enabled`) to the next gate-blocked
step. The plan body §B.7 cites the ADR-133 contract of ≤60s; we gate
at the tighter 30s here because ADR-121 §6 no-cache mandate means
propagation is bounded by a single `is_class_enabled` call (sub-second
in practice — gpg p99=23.7ms per S145 empirical baseline).

Strategy: simulate the revocation by flipping a mutable holder that the
fake `is_class_enabled` reads. Measure wall-clock time from flip to
the gate-blocked step. Asserts well under 30s.
"""
from __future__ import annotations

import os
import sys
import time
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


def _iter_green(_state: LoopState) -> IterationResult:
    return IterationResult(
        metric=1.0, tokens_delta=10, files_touched=[], kept=True, error=None,
    )


# Tightened SLO (Codex R2 iter-1 P0 #3 DECISION): plan §B.7 quotes ≤60s
# from ADR-133; we gate at 30s because ADR-121 §6 no-cache + S145 gpg
# p99=23.7ms make sub-second propagation the empirical norm. If the
# threshold proves too tight in CI, bump back to 60s — but it should
# never be exceeded outside pathological infra failures.
_SLO_SECONDS = 30.0


class TestSentinelRevocationSLO(TestEnvContext):

    def setUp(self):
        super().setUp()
        # PLAN-102-FOLLOWUP S145 Fix #3 (Codex triage 019e42fc): Layer-1
        # swarm-on env required for gate to fire (Fix #1 early-return guard).
        # patch.dict started here, stopped in tearDown before
        # super().tearDown() so the base-class env restore stays the last
        # write (never re-clobbered by the isolated-env snapshot).
        self._swarm_env_patch = mock.patch.dict(os.environ, {"CEO_SWARM": "1"})
        self._swarm_env_patch.start()

    def tearDown(self):
        self._swarm_env_patch.stop()
        super().tearDown()

    def test_revocation_propagates_under_slo(self):
        # Mutable holder simulating Owner's sentinel state. Flip from
        # enabled -> revoked at t0 and measure to the next gate-blocked
        # step() call.
        state = {"enabled": True, "reason": ""}

        fake_mod = types.ModuleType("_lib.swarm_enable_gate")

        def _stub(_class_tier: str):
            return (state["enabled"], state["reason"])

        fake_mod.is_class_enabled = _stub  # type: ignore[attr-defined]

        with mock.patch.dict(
            sys.modules, {"_lib.swarm_enable_gate": fake_mod}, clear=False,
        ):
            with mock.patch(
                "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
            ) as emit_mock:
                runner = LoopRunner(
                    loop_id="L_slo",
                    goal="g",
                    max_iterations=10,
                    max_strikes=3,
                    budget_tokens=1000,
                    direction=DIRECTION_MINIMIZE,
                    iterate=_iter_green,
                    class_tier="vibecoder",
                )
                # Pre-revocation: gate allows, iterate runs.
                first = runner.step()
                self.assertIsNone(first.error)
                # Owner revokes the sentinel.
                state["enabled"] = False
                state["reason"] = "sentinel_absent"
                t0 = time.monotonic()
                blocked = runner.step()
                elapsed = time.monotonic() - t0
                self.assertEqual(runner.state.status, "killed")
                self.assertTrue(blocked.error.startswith("layer_3_4_"))
                self.assertLess(
                    elapsed, _SLO_SECONDS,
                    f"revocation took {elapsed:.3f}s — SLO is {_SLO_SECONDS}s",
                )
                emit_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
