"""Mutation I3-04: Converge transition charges one token.

Anchor: ``_coordinator_sim.py:182-183`` — Converge transition (sets
status to converged; no token/iteration side effects in baseline).
Axis: wrong-transition-side-effect on terminal transition.
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate;
converge weight 1 fires eventually in 200-seed sweep once
iteration > 0 enables the gate).

Baseline Converge is a pure status flip running→converged. Mutant
bumps tokens on converge, so a loop that iterated K times (iter=K,
tokens=K) and then converges ends with tokens=K+1, iter=K —
K+1 > K violates the I3 per-loop bound.

Semantic distinction from sibling I3 mutations:
- mut_i3_01: iterate over-charges.
- mut_i3_02: iterate drops iter increment.
- mut_i3_03: Start charges tokens.
- mut_i3_04 (this): a DIFFERENT non-iterate transition — Converge —
  charges tokens. Exercises a distinct code anchor (terminal
  side, vs start side in i3_03).
"""

from __future__ import annotations

PROPERTY = "I3"
DESCRIPTION = (
    "Converge transition increments `tokens_consumed` by 1 as a "
    "spurious side-effect; tokens = iter + 1 after converge so the "
    "I3 per-loop bound is violated."
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
                # MUTATION: Converge also charges a token.
                s.tokens_consumed += 1
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I3_04"
    return Mutant
