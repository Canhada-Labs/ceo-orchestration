"""Mutation I4-04: Start transition charges 5 tokens to global consumed.

Anchor: ``_coordinator_sim.py:176-177`` — Start transition (baseline
flips status; no global counter effect).
Axis: non-iterate action writes the global envelope counter.
Killed-by: ``_mutations_fail`` iterate-heavy bias; across the 200-seed
sweep the Start weight-1 fallthrough fires for all three loops in
most seeds, and three starts × 5 = 15 > N * MaxIter = 12.

Models a refactoring hazard: a shared "budget debit" helper called
from multiple transitions, not just Iterate. The I4 invariant
breaks the moment cumulative Start charges exceed 12, regardless
of subsequent Iterate behavior.

Semantic distinction from sibling I4 mutations:
- mut_i4_01: iterate gate dropped + 10× per step.
- mut_i4_02: single large Iterate bump.
- mut_i4_03: BudgetKill transition charges consumed.
- mut_i4_04 (this): a third transition — Start — charges consumed.
  Different code anchor (entry side, vs terminal side in i4_03).
"""

from __future__ import annotations

PROPERTY = "I4"
DESCRIPTION = (
    "Start transition increments `next_state.consumed` by 5 as a "
    "spurious side-effect; three starts × 5 = 15 exceeds "
    "N * MaxIter = 12."
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
                # MUTATION: Start also charges global consumed.
                next_state.consumed += 5
            elif action == "iterate":
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

    Mutant.__name__ = "SwarmSimulatorMut_I4_04"
    return Mutant
