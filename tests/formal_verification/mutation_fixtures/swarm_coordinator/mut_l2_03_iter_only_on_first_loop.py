"""Mutation L2-03: Iterate is a no-op for every loop except L0.

Anchor: ``_coordinator_sim.py:178-180`` — Iterate transition body,
scoped by loop_id, plus ``_coordinator_sim.py:119-125`` iterate
gate's ``consumed < budget`` clause (dropped to prevent the
0-weight-fallback escape via budget_kill).
Axis: loop-scope regression (progress works for one privileged loop;
others are stranded) combined with a gate relaxation so the non-
privileged loops never exit running via terminal paths.
Killed-by: ``_mutations_fail`` L2 bias (high iterate weight, zero
terminal/kill). L1 and L2 enter ``running`` via Start but never
advance their per-loop iter because the transition silently no-ops
for loop_id != "L0".

Under the L2 bias, iterate picks among enabled loops weighted; when
L1 or L2 is picked the mutation silently drops the iteration. The
walk cannot escape via the zero-weight fallback because the enable
list also omits terminal/kill actions.

Semantic distinction from sibling L2 mutations:
- mut_l2_01: Iterate no-ops for ALL loops.
- mut_l2_02: Iterate drops iter increment for all loops (counters
  decoupled).
- mut_l2_03 (this): Iterate works for one loop, fails for others
  (scope bug — real-world pattern where a fast path is optimized
  for the "primary" loop and other loops regress).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L2"
DESCRIPTION = (
    "Iterate transition only runs its increments when loop_id == "
    "'L0'; other loops' Iterate is silently a no-op, so they "
    "remain running with iter=0 forever."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            active_count = len(
                [lid for lid, s in state.loops.items() if s.status == "running"]
            )
            for lid, s in state.loops.items():
                if (
                    s.status == "pending"
                    and active_count < self.cfg.max_parallel
                    and not state.kill
                ):
                    enabled.append(("start", lid))
                # Iterate gate drops budget check to keep iterate
                # firing across step_ceiling (L0 advances iter, L1/L2
                # no-op but stay enabled).
                if (
                    s.status == "running"
                    and s.iteration < self.cfg.max_iter
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
            # Terminal and kill actions OMITTED to block uniform-
            # fallback escapes.
            return enabled

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
                # MUTATION: only L0 advances; other loops no-op.
                if loop_id == "L0":
                    s.iteration += 1
                    s.tokens_consumed += 1
                    next_state.consumed += 1
                # else: silent no-op.
            elif action == "converge":
                s.status = "converged"
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L2_03"
    return Mutant
