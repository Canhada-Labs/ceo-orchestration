"""Mutation L3-01: PropagateKill enabled even when ``kill`` is False.

Violates L4 ordering (killed status requires TripKill first). Under a
kill-biased policy this lets a loop reach status=killed without the
global kill flag being set — the ``test_l4_random_walks`` invariant
check detects it directly.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L3"
DESCRIPTION = (
    "PropagateKill enabled without requiring kill=True; loops can be "
    "killed even when the kill switch has not tripped."
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
                if (
                    s.status == "running"
                    and s.iteration < self.cfg.max_iter
                    and state.consumed < self.cfg.budget
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
                if s.status == "running" and s.iteration > 0:
                    enabled.append(("converge", lid))
                if s.status == "running" and s.iteration == self.cfg.max_iter:
                    enabled.append(("complete", lid))
                if s.status == "running" and state.consumed >= self.cfg.budget:
                    enabled.append(("budget_kill", lid))
                # MUTATION: PropagateKill fires without kill flag.
                if s.status in {"running", "pending"}:
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

    Mutant.__name__ = "SwarmSimulatorMut_L3_01"
    return Mutant
