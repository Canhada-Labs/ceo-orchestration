"""Mutation I3-05: Iterate token charge scales with current iteration.

Anchor: ``_coordinator_sim.py:179`` — Iterate ``tokens_consumed += 1``.
Axis: non-linear growth (tokens grow as O(iter), not O(1) per step).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate).

Real-world parallel: instrumentation that accidentally samples the
running iteration counter for cost attribution, so each iterate
charges proportionally more tokens than the last. Starts agreeing
with the baseline (iter=0→1 charges 1) and diverges from the second
iteration onward: iter=1→2 charges 2, leaving tokens=3, iter=2 →
I3 bound violated.

Semantic distinction from sibling I3 mutations:
- mut_i3_01: constant over-charge (tokens += 2).
- mut_i3_02: iter increment dropped.
- mut_i3_03: Start charges tokens.
- mut_i3_04: Converge charges tokens.
- mut_i3_05 (this): tokens += iteration+1 (non-linear dependence on
  the loop's own iter counter). First iterate matches baseline,
  second diverges — harder to catch with a single-step trace but
  caught by the per-state invariant sweep.
"""

from __future__ import annotations

PROPERTY = "I3"
DESCRIPTION = (
    "Iterate charges `iteration + 1` tokens instead of 1; first "
    "Iterate matches baseline, second overcharges (iter=1→2 adds 2 "
    "tokens), violating the I3 per-loop bound from step 2 onward."
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
                # MUTATION: tokens scale with the post-increment iter.
                # iter=0→1: tokens += 1 (matches baseline).
                # iter=1→2: tokens += 2 (first divergence).
                # iter=2→3: tokens += 3 (divergence grows).
                s.tokens_consumed += s.iteration
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

    Mutant.__name__ = "SwarmSimulatorMut_I3_05"
    return Mutant
