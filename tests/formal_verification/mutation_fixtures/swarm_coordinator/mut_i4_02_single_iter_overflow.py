"""Mutation I4-02: Single Iterate jumps consumed past the global ceiling.

Anchor: ``_coordinator_sim.py:180`` — Iterate's ``next_state.consumed += 1``.
Axis: single-step magnitude (one transition consumes the entire envelope).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate).

Unlike mut_i4_01 which drops the budget gate and bumps per-iterate
by 10, this mutation keeps the gate intact but lets a SINGLE
Iterate consume more than ``N * MaxIter``. The gate then latches
(consumed >= budget blocks subsequent Iterate), but the state
that records the overshoot is still on the trace and the per-
state sweep detects it.

Semantic distinction from mut_i4_01:
- mut_i4_01: gate dropped + 10× per step (slow drift into violation).
- mut_i4_02 (this): gate intact + single large step. Models a
  mis-scaled token-cost constant (e.g., a batch of N tokens
  charged as N² by accident).
"""

from __future__ import annotations

PROPERTY = "I4"
DESCRIPTION = (
    "Iterate increments `next_state.consumed` by 100 per call; a "
    "single Iterate crosses N * MaxIter and violates the global "
    "envelope even though the budget gate is intact."
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
                # MUTATION: consumed bumped by 100 per Iterate;
                # single step crosses N * MaxIter = 12.
                next_state.consumed += 100
            elif action == "converge":
                s.status = "converged"
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I4_02"
    return Mutant
