"""Mutation I1-01: MaxParallel cap bypassed in StartLoop guard.

Original ``enabled_actions`` gates StartLoop(i) on ``active_count <
max_parallel``. The mutant drops that gate, so StartLoop fires
regardless of how many loops are already running. The I1 sweep
assertion catches ``Cardinality(ActiveLoops) > MaxParallel`` on the
first seed that triggers concurrent starts.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I1"
DESCRIPTION = (
    "StartLoop enable guard drops the `active_count < max_parallel` "
    "check; more than MaxParallel loops can run simultaneously."
)


def apply(sim_cls: type) -> type:
    """Return a _SwarmSimulator subclass with I1-01 applied."""

    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            for lid, s in state.loops.items():
                # MUTATION: no active_count cap check.
                if s.status == "pending" and not state.kill:
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
                if state.kill and s.status in {"running", "pending"}:
                    enabled.append(("propagate_kill", lid))
            if not state.kill:
                enabled.append(("trip_kill", None))
            return enabled

        def _apply(self, state, action, loop_id):
            # Bypass the enabled-set check in the parent so the
            # mutated enable-set can actually fire transitions.
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

    Mutant.__name__ = "SwarmSimulatorMut_I1_01"
    return Mutant
