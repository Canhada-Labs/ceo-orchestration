"""Mutation I2-04: Iterate guard uses 2 * max_iter as the ceiling.

Anchor: ``_coordinator_sim.py:121`` — Iterate ``iter < max_iter`` guard.
Axis: ceiling-relaxed (constant stretched, not removed).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate).

The invariant ``\\A i : loops[i].iter <= MaxIter`` (I2) forbids any
loop from exceeding its per-loop ceiling. Mutant relaxes the gate
from ``iter < max_iter`` to ``iter < 2 * max_iter``, so a loop can
continue iterating past MaxIter until either the global budget
gate or the relaxed ceiling eventually blocks it. Under the
iterate-heavy bias (and default budget=6 = 1.5 × max_iter),
iteration counts climb to budget-equivalent and exceed MaxIter
well before the relaxed ceiling.

Semantic distinction from sibling I2 mutations:
- mut_i2_01: ceiling check removed entirely (no upper bound).
- mut_i2_02: transition jumps iter by max_iter+1 per call.
- mut_i2_03: wrong status gate (pending also iterates).
- mut_i2_04 (this): constant stretched — correct *shape* of guard,
  wrong *magnitude*. Models a typo (``*`` instead of ``<``, or a
  factor accidentally introduced during refactoring).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I2"
DESCRIPTION = (
    "Iterate enable gate relaxes the ceiling from `iter < max_iter` "
    "to `iter < 2 * max_iter`; iteration counts climb past MaxIter "
    "before either the budget gate or the relaxed ceiling blocks."
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
                # MUTATION: ceiling relaxed by factor 2.
                if (
                    s.status == "running"
                    and s.iteration < 2 * self.cfg.max_iter
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

    Mutant.__name__ = "SwarmSimulatorMut_I2_04"
    return Mutant
