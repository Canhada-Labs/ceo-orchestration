"""Mutation I3-03: Start transition charges one token.

Anchor: ``_coordinator_sim.py:176-177`` — Start transition (sets
status to running; no token/iteration side effects in baseline).
Axis: wrong-transition-side-effect (a non-iterate action mutates
the token counter).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate;
start weight 1 still fires often enough in 200-seed sweep).

Baseline Start only flips status pending→running. Mutant charges
one token on Start too, so immediately after StartLoop a loop has
tokens=1 while iter=0 — I3 violation on the first reachable
post-start state.

Semantic distinction from sibling I3 mutations:
- mut_i3_01: iterate over-charges (per-step multiplier wrong).
- mut_i3_02: iterate skips iter increment (decoupling via missing
  increment).
- mut_i3_03 (this): a DIFFERENT transition — Start — accidentally
  bumps tokens. Captures a real refactoring hazard: a shared
  "account" helper called from multiple transitions.
"""

from __future__ import annotations

PROPERTY = "I3"
DESCRIPTION = (
    "Start transition increments `tokens_consumed` by 1 as a spurious "
    "side-effect; a loop that has just started has tokens=1 while "
    "iter=0."
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
                # MUTATION: Start also charges a token.
                s.tokens_consumed += 1
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

    Mutant.__name__ = "SwarmSimulatorMut_I3_03"
    return Mutant
