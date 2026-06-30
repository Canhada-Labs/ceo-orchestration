"""Mutation I1-03: active_count constant zero (gate never trips).

Anchor: ``_coordinator_sim.py:108-110`` — the list-comprehension that
builds ``active_count`` by filtering status=="running".
Axis: counter-short-circuit (active-set stuck at 0).
Killed-by: ``_mutations_fail`` start-heavy bias (weight 10 on start).

Original ``active_count`` sums the running loops to gate StartLoop.
Mutant forces active_count=0 always, so StartLoop fires regardless
of how many loops are already running. Under the start-heavy bias
used by ``test_i1_mutations_fail``, all N pending loops transition
to running concurrently, producing ``|active| = N > MaxParallel``.

Semantic distinction from sibling I1 mutations:
- mut_i1_01: removes the active-count cap check from the gate entirely.
- mut_i1_02: off-by-one on the gate comparator (``<=`` vs ``<``).
- mut_i1_03 (this): the comparator is intact but the counter feeding
  it is always 0 — a different failure mode (upstream vs gate).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I1"
DESCRIPTION = (
    "StartLoop active-count counter forced to 0 regardless of how "
    "many loops are running; gate comparator intact but always "
    "admits."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def _enabled(
            self, state
        ) -> List[Tuple[str, Optional[str]]]:
            enabled: List[Tuple[str, Optional[str]]] = []
            # MUTATION: active_count always 0 — gate never trips.
            active_count = 0
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
            # Bypass baseline's enabled-set re-check so the mutated
            # enable-set can actually fire transitions.
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

    Mutant.__name__ = "SwarmSimulatorMut_I1_03"
    return Mutant
