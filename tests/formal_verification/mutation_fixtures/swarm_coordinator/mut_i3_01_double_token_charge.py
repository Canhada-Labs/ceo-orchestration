"""Mutation I3-01: Iterate charges 2 tokens per iter step.

Per-loop ``tokens_consumed`` drifts above ``iteration`` count,
violating the TLA+ invariant ``\\A i : loops[i].tokens <= loops[i].iter``.
"""

from __future__ import annotations

PROPERTY = "I3"
DESCRIPTION = (
    "Iterate action increments `tokens_consumed` by 2 while "
    "`iteration` advances by 1; per-loop token bound violated."
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
                s.iteration += 1
                # MUTATION: charge 2 tokens per iter
                s.tokens_consumed += 2
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

    Mutant.__name__ = "SwarmSimulatorMut_I3_01"
    return Mutant
