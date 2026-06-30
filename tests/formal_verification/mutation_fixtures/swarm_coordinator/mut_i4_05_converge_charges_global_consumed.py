"""Mutation I4-05: Converge transition charges 15 tokens to global consumed.

Anchor: ``_coordinator_sim.py:182-183`` — Converge transition
(baseline flips status; no global counter effect).
Axis: non-iterate action writes the global envelope counter
(distinct transition from Start/BudgetKill variants).
Killed-by: ``_mutations_fail`` iterate-heavy bias; Converge gate
is ``iter > 0``, so a single Iterate enables Converge, and the
fallthrough weight-1 selection fires it across the 200-seed sweep.

Models the same refactor hazard as mut_i4_04 but on the success
side of the terminal set: a "record completion cost" helper that
leaks budget into the global envelope from the wrong transition.

Semantic distinction from sibling I4 mutations:
- mut_i4_01: iterate gate dropped + 10× per step.
- mut_i4_02: single large Iterate bump.
- mut_i4_03: BudgetKill charges consumed.
- mut_i4_04: Start charges consumed.
- mut_i4_05 (this): Converge charges consumed. Third distinct
  terminal/entry point for the same bug class.
"""

from __future__ import annotations

PROPERTY = "I4"
DESCRIPTION = (
    "Converge transition increments `next_state.consumed` by 15 "
    "as a spurious side-effect; a single Converge crosses "
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
            elif action == "iterate":
                s.iteration += 1
                s.tokens_consumed += 1
                next_state.consumed += 1
            elif action == "converge":
                s.status = "converged"
                # MUTATION: Converge also charges global consumed.
                next_state.consumed += 15
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I4_05"
    return Mutant
