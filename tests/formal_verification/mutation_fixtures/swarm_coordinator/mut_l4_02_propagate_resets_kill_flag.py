"""Mutation L4-02: PropagateKill atomically resets the kill flag.

Anchor: ``_coordinator_sim.py:188-189`` — PropagateKill transition.
Axis: transition-side side-effect — kill flag cleared in the same
step as the status transition, leaving a state with status=killed
and kill=False.
Killed-by: L4 random walk under kill-heavy bias (trip fires early
setting kill=True; propagate then fires and the mutation clears
kill while setting status=killed).

The L4 invariant ``[](status=killed ⇒ kill)`` requires the kill
flag to still be set whenever any loop observes the ``killed``
terminal status. The mutant breaks this by clearing kill during
the same transition that sets the killed status — a single
reachable state between the post-propagate moment and the next
trip (if any) satisfies the violation predicate.

Semantic distinction from sibling L4 mutations:
- mut_l4_01: trip_kill is a no-op (kill never goes True) AND
  propagate fires without kill gate. This produces killed + !kill
  via a different mechanism (trip path broken, propagate path
  bypassed).
- mut_l4_02 (this): trip_kill works normally; propagate fires
  normally (gate intact); but the transition CLEARS kill as it
  kills the loop, creating the violation in one atomic step.
"""

from __future__ import annotations

PROPERTY = "L4"
DESCRIPTION = (
    "PropagateKill transition sets status=killed AND clears "
    "state.kill atomically; the resulting state satisfies "
    "status=killed AND NOT state.kill."
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
            elif action == "propagate_kill":
                s.status = "killed"
                # MUTATION: propagate also clears kill. The state
                # now has killed loop + kill=False in one step.
                next_state.kill = False
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L4_02"
    return Mutant
