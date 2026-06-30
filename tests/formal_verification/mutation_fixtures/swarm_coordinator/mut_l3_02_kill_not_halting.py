"""Mutation L3-02: kill flag does NOT halt Start/Iterate/BudgetKill.

Once TripKill fires, the original guard ``not state.kill`` on Start
and Iterate + the absence of kill-propagation paths means running
loops WILL terminate. The mutant drops the `not state.kill` guards
on Start and Iterate AND disables PropagateKill entirely — so once
kill trips, running loops can keep iterating indefinitely and never
reach a terminal status. Violates L3 (KillSwitchHalts).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L3"
DESCRIPTION = (
    "Kill flag is ignored by Start and Iterate guards, AND "
    "PropagateKill is disabled; once tripped, loops continue "
    "iterating and never transition to `killed`."
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
                # MUTATION: no `not state.kill` guard on Start.
                if (
                    s.status == "pending"
                    and active_count < self.cfg.max_parallel
                ):
                    enabled.append(("start", lid))
                # MUTATION: no `not state.kill` guard on Iterate.
                if (
                    s.status == "running"
                    and s.iteration < self.cfg.max_iter
                    and state.consumed < self.cfg.budget
                ):
                    enabled.append(("iterate", lid))
                if s.status == "running" and s.iteration > 0:
                    enabled.append(("converge", lid))
                if s.status == "running" and s.iteration == self.cfg.max_iter:
                    enabled.append(("complete", lid))
                if s.status == "running" and state.consumed >= self.cfg.budget:
                    enabled.append(("budget_kill", lid))
                # MUTATION: PropagateKill disabled entirely.
            if not state.kill:
                enabled.append(("trip_kill", None))
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

    Mutant.__name__ = "SwarmSimulatorMut_L3_02"
    return Mutant
