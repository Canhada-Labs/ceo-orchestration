"""Mutation L3-04: PropagateKill transition flips loop to running instead of killed.

Anchor: ``_coordinator_sim.py:188-189`` — PropagateKill transition.
Axis: transition-side "cosmetic kill" — the gate fires, but the
transition body doesn't actually kill the loop.
Killed-by: ``_mutations_fail`` L3 bias (kill-then-propagate — trip
fires early; propagate fires on each pending+running loop).

Under the L3 bias, trip_kill fires early and state.kill becomes
True. PropagateKill is then enabled on every pending+running loop
with weight 10. Under the mutation, PropagateKill reassigns the
loop to ``running`` (or leaves a pending loop as pending-via-
running, depending on prior state). The kill switch has
tripped but no loop ever reaches the "killed" terminal. After
the step_ceiling, the final state has loops stuck at running
without any terminal transition available (iterate/start gated on
``not state.kill``, converge needs iter>0 which requires iterate
which is kill-gated, complete needs iter==max same), so L3
``KillSwitchHalts`` is violated.

Semantic distinction from sibling L3 mutations:
- mut_l3_01: propagate fires without kill flag (L4 violation too).
- mut_l3_02: kill flag ignored by Start/Iterate guards + propagate
  gate disabled.
- mut_l3_03: propagate partial — only first loop.
- mut_l3_04 (this): propagate gate fires correctly, but transition
  sets status=running (i.e., kill signal was "seen" but no terminal
  action was applied).
"""

from __future__ import annotations

PROPERTY = "L3"
DESCRIPTION = (
    "PropagateKill transition sets status=running instead of "
    "status=killed; kill signal is observed but no loop ever "
    "reaches a terminal via propagation."
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
                # MUTATION: propagate flips to running instead of
                # killing. Kill signal is "absorbed" without effect.
                s.status = "running"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L3_04"
    return Mutant
