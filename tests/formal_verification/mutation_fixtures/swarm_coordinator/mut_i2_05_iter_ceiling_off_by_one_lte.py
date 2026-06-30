"""Mutation I2-05: Iterate guard uses ``<=`` instead of ``<``.

Anchor: ``_coordinator_sim.py:121`` Iterate ``iter < max_iter`` guard.
Axis: off-by-one (comparator swapped strict vs non-strict).
Killed-by: ``_mutations_fail`` iterate-heavy bias (weight 10 iterate).

Classic off-by-one: the guard should be ``iter < max_iter`` (at
most ``max_iter`` iterations); the mutant uses ``iter <= max_iter``
(one extra iteration allowed). At iter == max_iter the gate admits
one more Iterate, producing iter == max_iter + 1 — a direct I2
violation.

Semantic distinction from sibling I2 mutations:
- mut_i2_01: guard removed entirely.
- mut_i2_02: transition overshoots by max_iter+1 per call.
- mut_i2_03: wrong status gate (pending too).
- mut_i2_04: ceiling stretched by factor 2 (different magnitude).
- mut_i2_05 (this): single step over (off-by-one).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "I2"
DESCRIPTION = (
    "Iterate enable gate uses `<=` instead of `<`; at iter == "
    "max_iter the gate admits one more Iterate, producing "
    "iter == max_iter + 1."
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
                # MUTATION: `<=` instead of `<`.
                if (
                    s.status == "running"
                    and s.iteration <= self.cfg.max_iter
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

    Mutant.__name__ = "SwarmSimulatorMut_I2_05"
    return Mutant
