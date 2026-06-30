"""Mutation L2-02: Iterate advances tokens + consumed but not iter.

Anchor: ``_coordinator_sim.py:178-180`` — Iterate transition's
``s.iteration += 1`` AND ``_coordinator_sim.py:119-125`` — Iterate's
``consumed < budget`` enable clause.
Axis: per-loop iter counter decoupled from token/consumed counters
(iter increment DROPPED, others intact) + iterate gate relaxed so
the walk exercises the decoupled state until step_ceiling.
Killed-by: ``_mutations_fail`` L2 bias (weight 20 iterate, 5 start,
terminal+kill all zeroed).

Unlike mut_l2_01 which makes Iterate a total no-op, this mutation
advances tokens and consumed on every Iterate while leaving iter
stuck at 0. The iterate enable gate also drops the budget check so
iterate keeps firing across the step_ceiling — otherwise once
consumed exceeds budget the walk would escape via the zero-weight
budget_kill / propagate path (pytest ``_pick`` falls back to
uniform-over-enabled when every enabled action has bias 0).

Semantic distinction from sibling L2 mutations:
- mut_l2_01: Iterate completely no-ops (nothing advances).
- mut_l2_02 (this): partial bug — only the iter counter is dropped,
  so tokens/consumed keep climbing while iter stays at 0. Harder
  to spot in a single-counter trace but caught by the "running +
  not ever_iterated" invariant.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L2"
DESCRIPTION = (
    "Iterate transition advances `tokens_consumed` + "
    "`next_state.consumed` but leaves `iteration` at its previous "
    "value; iterate gate also drops the budget check so the walk "
    "stays in the iterate loop across step_ceiling."
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
                # MUTATION: iterate gate drops the budget check so
                # iterate keeps firing past the consumed ceiling.
                if (
                    s.status == "running"
                    and s.iteration < self.cfg.max_iter
                    and not state.kill
                ):
                    enabled.append(("iterate", lid))
            # Terminal and kill actions are intentionally OMITTED so
            # the walk cannot escape via the 0-weight uniform fallback.
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
                # MUTATION: iter increment dropped. Tokens and
                # consumed still advance.
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

    Mutant.__name__ = "SwarmSimulatorMut_L2_02"
    return Mutant
