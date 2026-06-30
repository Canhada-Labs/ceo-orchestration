"""Mutation L2-04: Iterate gate inverted to require iter > 0 (catch-22).

Anchor: ``_coordinator_sim.py:119-125`` — Iterate enable clause's
``iter < max_iter`` replaced by ``iter > 0``.
Axis: gate-side catch-22 (new prerequisite that the action is the
ONLY way to satisfy).
Killed-by: ``_mutations_fail`` L2 bias — with every terminal + kill
weight zeroed AND the enable list omitting them entirely, Start
brings the loops into running and then no action can fire. The
walk stops with three loops stuck at running, iter=0.

Semantic distinction from sibling L2 mutations:
- mut_l2_01: transition no-op.
- mut_l2_02: transition drops iter increment (tokens still advance).
- mut_l2_03: transition conditional on loop_id.
- mut_l2_04 (this): GATE inverted — iterate cannot fire until iter
  has already advanced, which only iterate itself can cause. Models
  a classic "bootstrap" bug.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L2"
DESCRIPTION = (
    "Iterate enable gate requires `iteration > 0` (instead of "
    "`iteration < max_iter`); the loop can never bootstrap its "
    "iter counter above zero because the only increment path is "
    "gated on the increment having already happened."
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
                # MUTATION: iterate requires iter > 0 (catch-22).
                if (
                    s.status == "running"
                    and s.iteration > 0
                    and s.iteration < self.cfg.max_iter
                    and state.consumed < self.cfg.budget
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
            # Terminal + kill actions OMITTED to prevent the 0-weight
            # fallback escape via trip/propagate_kill.
            return enabled

        def _apply(self, state, action, loop_id):
            # Bypass baseline's enabled-set re-check.
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
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_L2_04"
    return Mutant
