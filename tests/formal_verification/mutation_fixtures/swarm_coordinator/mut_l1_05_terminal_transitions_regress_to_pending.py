"""Mutation L1-05: All three non-kill terminal transitions regress to pending.

Anchor: ``_coordinator_sim.py:182-187`` — Converge, Complete, and
BudgetKill transition bodies.
Axis: transition-side terminal-escape (three distinct terminal
transitions revert to pending instead of moving to a sink).
Killed-by: ``_mutations_fail`` L1 bias suite — under both biases
Converge / Complete / BudgetKill are reachable (fallthrough weight
1); all three now recycle loops through pending→running→pending
forever. The kill-bias paths (trip_kill, propagate_kill) are
zeroed in both biases, so no terminal path remains.

Semantic distinction from sibling L1 mutations:
- mut_l1_01: gate-side denial of all terminals.
- mut_l1_02: Start re-enables completed loops (escape via start).
- mut_l1_03: gate-side denial of four terminals (narrower).
- mut_l1_04: Start transition no-ops (loops stay pending from
  initial state).
- mut_l1_05 (this): THREE different transitions (Converge, Complete,
  BudgetKill) regress to pending — models the same class of bug
  that l1_02 exercises via Start, but from the success-terminal
  side AND the budget-exhaustion terminal side. Distinct code
  anchor (three transition bodies, not one Start enable).
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "Converge, Complete, and BudgetKill transitions assign "
    "status=pending instead of the terminal value; loops cycle "
    "pending→running→pending forever without reaching a terminal "
    "under bias suites that zero the kill paths."
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
                # MUTATION: converge regresses to pending.
                s.status = "pending"
            elif action == "complete":
                # MUTATION: complete regresses to pending.
                s.status = "pending"
            elif action == "budget_kill":
                # MUTATION: budget_kill also regresses to pending.
                s.status = "pending"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L1_05"
    return Mutant
