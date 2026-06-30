"""Mutation I1-04: active_count filter uses iter>0 instead of status.

Anchor: ``_coordinator_sim.py:108-110`` active-count filter predicate.
Axis: predicate-swap (status-based vs iteration-based counting).
Killed-by: ``_mutations_fail`` start-heavy bias (weight 10 on start).

Original active_count = ``len([s.status == "running"])``. Mutant
uses ``len([s.iteration > 0])``, which undercounts newly-started
loops that haven't iterated yet (iteration stays 0 until Iterate
fires). Under the start-heavy bias, three back-to-back Starts fire
before any Iterate, so active_count stays at 0 while three loops
become running — violating ``|active| <= MaxParallel`` with N=3,
MaxParallel=2.

Semantic distinction from sibling I1 mutations:
- mut_i1_01: gate predicate removed entirely.
- mut_i1_02: comparator off-by-one.
- mut_i1_03: active_count hard-coded to 0.
- mut_i1_04 (this): active_count uses a wrong predicate (iter>0),
  so it correctly counts but counts the wrong set.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I1"
DESCRIPTION = (
    "StartLoop active-count filter uses `iteration > 0` instead of "
    "`status == running`; newly-started (iter=0) loops are not "
    "counted against the parallel cap."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            # MUTATION: filter by iteration>0 instead of status=running.
            active_count = len(
                [lid for lid, s in state.loops.items() if s.iteration > 0]
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

    Mutant.__name__ = "SwarmSimulatorMut_I1_04"
    return Mutant
