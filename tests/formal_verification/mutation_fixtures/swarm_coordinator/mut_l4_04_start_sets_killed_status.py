"""Mutation L4-04: Start transition sets status=killed directly.

Anchor: ``_coordinator_sim.py:176-177`` — Start transition body.
Axis: typo-class bug — wrong literal in an assignment.
Killed-by: L4 random walk — across the 200-seed sweep, in ~23% of
initial-step cases Start fires before TripKill, producing a state
with status=killed while kill=False.

Baseline Start flips a pending loop to ``running``. Mutant mis-
assigns ``killed`` instead. The action is enabled only while
``not state.kill``, so when Start fires before any TripKill the
resulting state has a loop with status=killed and kill=False —
the L4 violation predicate. Trip's weight-10 priority under the
L4 bias means only a subset of seeds exercise this path, but in
practice it fires on dozens of seeds per 200-seed sweep.

Semantic distinction from sibling L4 mutations:
- mut_l4_01: trip no-op + propagate without kill gate.
- mut_l4_02: propagate clears kill atomically.
- mut_l4_03: trip kills loops instead of setting flag.
- mut_l4_04 (this): a NON-KILL transition — Start — mis-assigns
  status=killed. Distinct code anchor (start body, not any kill
  transition). Classic refactoring hazard when copy-pasting
  terminal assignments.
"""

from __future__ import annotations

PROPERTY = "L4"
DESCRIPTION = (
    "Start transition mis-assigns status=killed instead of "
    "status=running; because Start is gated on NOT state.kill, "
    "the resulting state has status=killed AND kill=False."
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
                # MUTATION: status=killed typo in Start.
                s.status = "killed"
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

    Mutant.__name__ = "SwarmSimulatorMut_L4_04"
    return Mutant
