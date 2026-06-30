"""Mutation L1-04: Start transition is a no-op — status stays pending.

Anchor: ``_coordinator_sim.py:176-177`` — Start transition's
``s.status = "running"`` assignment.
Axis: transition-side no-op (gate fires, transition doesn't mutate).
Killed-by: ``_mutations_fail`` L1 bias suite — both biases give
Start non-zero weight; under the mutation, StartLoop repeatedly
"succeeds" without actually flipping status, so loops stay in
pending forever. ``pending`` is not in the Terminal set, so the
final-state unterminated check catches the mutation.

Semantic distinction from sibling L1 mutations:
- mut_l1_01: all terminal enables removed (gate-side bug).
- mut_l1_02: Start ALSO works on completed (terminal escape).
- mut_l1_03: four terminal enables dropped (gate-side narrow).
- mut_l1_04 (this): transition-side bug on the ENTRY action —
  gate admits, transition does nothing. Loop forever pending.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "Start transition does not assign status; a loop's Start "
    "'succeeds' via the gate but the state field stays `pending`, "
    "so no loop ever reaches `running` or a terminal."
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
                # MUTATION: status assignment dropped; stays pending.
                pass
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

    Mutant.__name__ = "SwarmSimulatorMut_L1_04"
    return Mutant
