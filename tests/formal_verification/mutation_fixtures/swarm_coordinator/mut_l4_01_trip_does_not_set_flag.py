"""Mutation L4-01: TripKill action does not actually set the kill flag.

Combined with a kill-allowed PropagateKill guard (which reads kill
flag in the baseline simulator), TripKill fires but the flag stays
False. Under the L4 invariant, any appearance of status=killed
without kill=True is a violation — the mutant lifts the PropagateKill
guard so it can fire and get caught.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L4"
DESCRIPTION = (
    "TripKill action leaves kill flag False; simultaneously "
    "PropagateKill is permitted regardless of kill state — so a "
    "loop reaches status=killed while kill=False."
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
                # MUTATION: PropagateKill fires regardless of kill flag.
                if s.status in {"running", "pending"}:
                    enabled.append(("propagate_kill", lid))
            # MUTATION: TripKill always enabled (and no-op via _apply).
            enabled.append(("trip_kill", None))
            return enabled

        def _apply(self, state, action, loop_id):
            next_state = state.clone()
            if action == "trip_kill":
                # MUTATION: does NOT set kill = True.
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

    Mutant.__name__ = "SwarmSimulatorMut_L4_01"
    return Mutant
