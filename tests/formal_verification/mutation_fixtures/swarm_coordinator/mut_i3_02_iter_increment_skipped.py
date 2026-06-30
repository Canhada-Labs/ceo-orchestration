"""Mutation I3-02: Iterate bumps tokens but not iteration.

Anchor: ``_coordinator_sim.py:178-180`` — Iterate transition's
increments to iteration and tokens_consumed.
Axis: decoupling (per-loop iter counter and per-loop token counter
drift apart because one increment is dropped).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate).

The TLA+ invariant ``\\A i : loops[i].tokens <= loops[i].iter``
(I3) assumes tokens and iter march in lock-step per loop. Mutant
skips the iter increment, so after the first Iterate call
tokens=1 while iter stays at 0 — an immediate I3 violation.

Semantic distinction from sibling I3 mutations:
- mut_i3_01: tokens incremented by 2 per iterate (constant over-charge).
- mut_i3_02 (this): iter increment dropped entirely (decoupling).
"""

from __future__ import annotations

PROPERTY = "I3"
DESCRIPTION = (
    "Iterate transition increments `tokens_consumed` but leaves "
    "`iteration` at its previous value; after the first Iterate, "
    "tokens=1 and iter=0."
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
                # MUTATION: iter increment dropped. Only tokens +
                # consumed advance.
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

    Mutant.__name__ = "SwarmSimulatorMut_I3_02"
    return Mutant
