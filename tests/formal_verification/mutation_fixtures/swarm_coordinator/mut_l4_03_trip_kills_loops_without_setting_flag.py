"""Mutation L4-03: TripKill marks all loops as killed without setting the flag.

Anchor: ``_coordinator_sim.py:171-173`` — TripKill transition.
Axis: transition-side action-confusion (trip does what propagate
should do, and vice-versa).
Killed-by: L4 random walk under kill-heavy bias — trip_kill has
weight 10 and fires early in most seeds; on the very first fire,
the state post-trip has N loops in status=killed and kill=False.

Baseline TripKill simply sets ``state.kill = True`` and lets
PropagateKill propagate the signal to each loop. Mutant inverts
the contract: trip iterates over all non-terminal loops and
marks them as killed directly, WITHOUT setting the global kill
flag. The L4 invariant is violated immediately: multiple loops
have status=killed and state.kill=False.

Semantic distinction from sibling L4 mutations:
- mut_l4_01: trip is a no-op (kill never True) + propagate bypasses
  kill gate (killed without kill is observable).
- mut_l4_02: propagate clears kill atomically.
- mut_l4_03 (this): trip_kill does the WRONG thing — it kills loops
  instead of setting the flag. Distinct code anchor (trip transition
  body, not propagate).
"""

from __future__ import annotations

PROPERTY = "L4"
DESCRIPTION = (
    "TripKill transition marks every non-terminal loop as "
    "status=killed and leaves state.kill=False; the resulting "
    "state has N killed loops with no kill flag set."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _apply(self, state, action, loop_id):
            next_state = state.clone()
            if action == "trip_kill":
                # MUTATION: trip marks loops as killed but does NOT
                # set the kill flag.
                for lid, ls in next_state.loops.items():
                    if ls.status in {"running", "pending"}:
                        ls.status = "killed"
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
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L4_03"
    return Mutant
