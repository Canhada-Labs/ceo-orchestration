"""Mutation L2-05: Iterate gate inverted on status (requires not-running).

Anchor: ``_coordinator_sim.py:119-125`` — Iterate enable's status
clause ``status == "running"`` replaced by ``status != "running"``.
Axis: gate-side status predicate inverted (``!=`` swap).
Killed-by: ``_mutations_fail`` L2 bias — under the L2 mutation bias
start still fires but iterate's gate rejects every running loop.
Loops enter running and immediately become unable to iterate, so
iter stays at 0 forever; terminal+kill actions are dropped so the
walk cannot escape via the 0-weight fallback.

Semantic distinction from sibling L2 mutations:
- mut_l2_01: transition no-op.
- mut_l2_02: transition drops iter increment.
- mut_l2_03: transition scoped to one loop.
- mut_l2_04: gate requires iter > 0 (catch-22 via numeric precondition).
- mut_l2_05 (this): gate requires status != "running" (status-
  predicate inversion). Distinct from l2_04 because l2_04's catch-22
  is numeric (iter has to have advanced), whereas l2_05 is a
  categorical mismatch (the action is enabled only for statuses
  where it produces no useful effect).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L2"
DESCRIPTION = (
    "Iterate enable gate requires `status != 'running'` instead of "
    "`status == 'running'`; no running loop can ever fire Iterate, "
    "so iter stays at 0 forever."
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
                # MUTATION: iterate gate status inverted.
                if (
                    s.status != "running"
                    and s.iteration < self.cfg.max_iter
                    and state.consumed < self.cfg.budget
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
            # Terminal + kill actions OMITTED to block the 0-weight
            # uniform-fallback escape path.
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

    Mutant.__name__ = "SwarmSimulatorMut_L2_05"
    return Mutant
