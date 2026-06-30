"""Mutation L3-03: propagate_kill only affects first loop, not all.

Original L3 invariant: once state.kill is tripped, propagate_kill
fires for every non-terminal loop in sequence, eventually halting
all running loops. Mutant makes propagate_kill a no-op for any loop
except the lexicographically-first one, so other loops continue to
run even with state.kill = True.

Axis: propagation scope (vs l3_01 no-trip-required / l3_02 kill ignored).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L3"
DESCRIPTION = (
    "propagate_kill is a no-op for all loops except the first "
    "(by lexicographic loop_id); kill switch halts only one loop."
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
                # MUTATION: only act on the lexicographically first
                # loop_id. Other loops' propagate_kill is a silent
                # no-op — they stay running forever even with kill
                # tripped.
                first_lid = sorted(next_state.loops.keys())[0]
                if loop_id == first_lid:
                    s.status = "killed"
                # else: no-op. Loop stays running despite kill.
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L3_03"
    return Mutant
