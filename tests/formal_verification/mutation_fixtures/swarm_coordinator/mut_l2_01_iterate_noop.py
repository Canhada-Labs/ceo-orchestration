"""Mutation L2-01: Iterate is a no-op — iter and tokens never advance.

Violates L2 (ProgressGuaranteed) and the ``test_l2_iteration_is_monotonic``
trace-level check — a running loop can iterate indefinitely without
advancing ``iteration`` or ``tokens_consumed``.
"""

from __future__ import annotations

PROPERTY = "L2"
DESCRIPTION = (
    "Iterate action no-ops: iteration + tokens_consumed stay at 0; "
    "running loops cannot make progress."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
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
                # MUTATION: no-op. iter, tokens, consumed unchanged.
                pass
            elif action == "converge":
                s.status = "converged"
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L2_01"
    return Mutant
