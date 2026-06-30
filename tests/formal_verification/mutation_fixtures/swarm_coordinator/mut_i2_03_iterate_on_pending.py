"""Mutation I2-03: iterate fires on pending loops (wrong status gate).

Original ``iterate`` is gated on ``status == "running"``. Mutant
extends the gate to include "pending", so a loop can iterate before
Start fires. This allows iteration counts to grow past max_iter
because the loop stays in "pending" longer than expected.

Axis: status-gate error (vs i2_01 no-ceiling / i2_02 double-increment).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I2"
DESCRIPTION = (
    "iterate enable gate accepts pending status in addition to "
    "running; iteration can advance before start transitions the "
    "loop to running."
)


def apply(sim_cls: type) -> type:
    """Return a _SwarmSimulator subclass with I2-03 applied."""

    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            active_count = len(
                [
                    lid
                    for lid, s in state.loops.items()
                    if s.status == "running"
                ]
            )
            for lid, s in state.loops.items():
                if (
                    s.status == "pending"
                    and active_count < self.cfg.max_parallel
                    and not state.kill
                ):
                    enabled.append(("start", lid))
                # MUTATION: iterate fires on pending too — and drops
                # the max_iter ceiling check for pending loops.
                if (
                    s.status in {"running", "pending"}
                    and state.consumed < self.cfg.budget
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
                if s.status == "running" and s.iteration > 0:
                    enabled.append(("converge", lid))
                if s.status == "running" and s.iteration == self.cfg.max_iter:
                    enabled.append(("complete", lid))
                if s.status == "running" and state.consumed >= self.cfg.budget:
                    enabled.append(("budget_kill", lid))
                if state.kill and s.status in {"running", "pending"}:
                    enabled.append(("propagate_kill", lid))
            if not state.kill:
                enabled.append(("trip_kill", None))
            return enabled

        def _apply(self, state, action, loop_id):
            next_state = state.clone()
            if action == "trip_kill":
                next_state.kill = True
                return next_state
            assert loop_id is not None
            s = next_state.loops[loop_id]
            if action == "start":
                s.status = "running"
            elif action == "iterate":
                # MUTATION: no ceiling check; iteration grows past
                # max_iter freely when combined with pending-gate.
                s.iteration += 1
                s.tokens_consumed += 1
                next_state.consumed += 1
            elif action == "converge":
                s.status = "converged"
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I2_03"
    return Mutant
