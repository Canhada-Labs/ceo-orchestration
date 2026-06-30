"""Mutation I1-05: active_count excludes a specific loop_id from the count.

Anchor: ``_coordinator_sim.py:108-110`` active-count filter scope.
Axis: scope-exclusion (specific loop never counts against cap).
Killed-by: ``_mutations_fail`` start-heavy bias (weight 10 on start).

A real-world bug pattern: an exclusion list (for admin loops,
debug loops, etc.) leaks into the MaxParallel gate. Here ``L0``
never contributes to active_count, so once L0 is running the gate
still admits two more starts — producing 3 running loops for
MaxParallel=2.

Semantic distinction from sibling I1 mutations:
- mut_i1_01: gate predicate removed.
- mut_i1_02: comparator off-by-one.
- mut_i1_03: counter hard-zero.
- mut_i1_04: wrong predicate (iter>0).
- mut_i1_05 (this): correct predicate but scope has an exclusion.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I1"
DESCRIPTION = (
    "StartLoop active-count filter silently excludes loop_id `L0` "
    "from the cap computation; an exclusion-list bug leaking into "
    "the parallelism gate."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            # MUTATION: L0 excluded from the running-count.
            active_count = len(
                [
                    lid
                    for lid, s in state.loops.items()
                    if s.status == "running" and lid != "L0"
                ]
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
                if state.kill and s.status in {"running", "pending"}:
                    enabled.append(("propagate_kill", lid))
            if not state.kill:
                enabled.append(("trip_kill", None))
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

    Mutant.__name__ = "SwarmSimulatorMut_I1_05"
    return Mutant
