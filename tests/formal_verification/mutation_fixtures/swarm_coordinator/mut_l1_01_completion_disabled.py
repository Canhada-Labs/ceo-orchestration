"""Mutation L1-01: all terminal paths disabled except natural exhaustion.

Disables Converge / Complete / TripKill / PropagateKill / BudgetKill.
A running loop has no exit — once started, it iterates until the
step_ceiling cuts the walk. L1 (NoDeadWorker) detects the unterminated
loops in the final state.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L1"
DESCRIPTION = (
    "Every terminal-producing action is disabled (Complete + Converge "
    "+ BudgetKill + TripKill + PropagateKill); running loops can "
    "never reach a terminal status."
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
                # MUTATION: Converge + Complete + BudgetKill +
                # PropagateKill all disabled.
            # MUTATION: TripKill disabled.
            return enabled

    Mutant.__name__ = "SwarmSimulatorMut_L1_01"
    return Mutant
