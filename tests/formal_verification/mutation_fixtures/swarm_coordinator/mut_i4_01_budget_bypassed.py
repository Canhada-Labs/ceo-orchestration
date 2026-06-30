"""Mutation I4-01: Iterate drops the ``consumed < budget`` gate.

With budget gate bypassed AND Iterate contributing to ``consumed``,
total ``consumed`` can exceed ``N * MaxIter`` once a single loop
iterates past its fair share of the budget envelope. Triggered when
the simulator keeps feeding Iterate to an already-exhausted budget.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I4"
DESCRIPTION = (
    "Iterate drops `state.consumed < cfg.budget` guard; `consumed` "
    "grows past N * MaxIter because each Iterate now adds tokens "
    "even after the envelope should have halted them."
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
                # MUTATION: no budget check in Iterate gate.
                if (
                    s.status == "running"
                    and s.iteration < self.cfg.max_iter
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
                if s.status == "running" and s.iteration > 0:
                    enabled.append(("converge", lid))
                if s.status == "running" and s.iteration == self.cfg.max_iter:
                    enabled.append(("complete", lid))
                # Keep budget_kill reachable so the invariant is still
                # testable via reaching the overflow scenario.
                if s.status == "running" and state.consumed >= self.cfg.budget:
                    enabled.append(("budget_kill", lid))
                if state.kill and s.status in {"running", "pending"}:
                    enabled.append(("propagate_kill", lid))
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
                # MUTATION: consumed accounting bumped by 10x — forces
                # it to overflow N * MaxIter quickly so I4 catches it.
                next_state.consumed += 10
            elif action == "converge":
                s.status = "converged"
            elif action == "complete":
                s.status = "completed"
            elif action == "budget_kill":
                s.status = "errored"
            elif action == "propagate_kill":
                s.status = "killed"
            return next_state

    Mutant.__name__ = "SwarmSimulatorMut_I4_01"
    return Mutant
