"""Mutation I4-03: BudgetKill transition inflates consumed counter.

Anchor: ``_coordinator_sim.py:186-187`` — BudgetKill transition
(status → errored; no counter side effects in baseline).
Axis: terminal-transition side-effect (budget-kill bleeds consumed).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate;
budget_kill enables once consumed >= budget, then fires via the
fallthrough-weight-1 selection).

The TLA+ invariant ``consumed <= N * MaxIter`` (I4) treats consumed
as a monotonically-accumulated envelope. Mutant bumps consumed by
20 on BudgetKill — under the iterate-heavy bias, consumed reaches
budget=6 after six iterates, BudgetKill fires, consumed jumps to
26 > N*MaxIter=12 on that successor state.

Semantic distinction from sibling I4 mutations:
- mut_i4_01: gate dropped, per-iter inflated.
- mut_i4_02: single large Iterate bump.
- mut_i4_03 (this): a DIFFERENT transition — BudgetKill — bumps
  consumed. Exercises the terminal side of the state machine.
"""

from __future__ import annotations

PROPERTY = "I4"
DESCRIPTION = (
    "BudgetKill transition bumps `next_state.consumed` by 20; once "
    "budget is exhausted the kill fires and consumed jumps past "
    "N * MaxIter."
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
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
                # MUTATION: BudgetKill leaks into consumed.
                next_state.consumed += 20
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I4_03"
    return Mutant
