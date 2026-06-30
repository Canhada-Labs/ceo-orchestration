"""Mutation I2-02: Iterate increments ``iter`` by 2 instead of 1.

Combined with a tight budget, this blows past MaxIter even if the
gate check still holds on the previous step.
"""

from __future__ import annotations

PROPERTY = "I2"
DESCRIPTION = (
    "Iterate action increments `iteration` by 2 per call; the next "
    "Iterate can exceed MaxIter without re-checking the guard."
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
                # MUTATION: jump iter straight past the ceiling.
                # Original: iter += 1. Mutant: iter += (max_iter + 1)
                # so a single Iterate produces iter > MaxIter and
                # violates the I2 safety invariant on the very first
                # step. The Iterate guard's `iter < max_iter` pre-check
                # still admits the action (iter was 0), but the
                # transition itself breaks the invariant.
                s.iteration += self.cfg.max_iter + 1
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

    Mutant.__name__ = "SwarmSimulatorMut_I2_02"
    return Mutant
