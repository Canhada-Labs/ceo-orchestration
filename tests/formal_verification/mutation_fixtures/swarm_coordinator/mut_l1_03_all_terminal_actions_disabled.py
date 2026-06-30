"""Mutation L1-03: every terminal-producing action disabled in the gate.

Anchor: ``_coordinator_sim.py:127-138`` — the enable clauses for
Converge, Complete, BudgetKill, PropagateKill (the four terminal
transitions).
Axis: gate-level terminal blackout (distinct from mut_l1_01 which
ALSO zeros TripKill and BudgetKill via the removal of the inner
terminal block).
Killed-by: ``_mutations_fail`` L1 bias suite — both
_mutation_l1_a_bias (start-heavy, kill-zeroed) and
_mutation_l1_b_bias (extreme start, complete-allowed, kill-zeroed)
expose the missing-exit condition. Under bias `a`, iterate runs
until iter==max_iter then blocks; under bias `b`, complete is
unreachable because of the mutated enable list. Either way, the
final state contains non-terminal loops.

Semantic distinction from sibling L1 mutations:
- mut_l1_01: ALL terminal actions disabled + TripKill disabled.
  Leaves enable set = {start, iterate}. Same observable behaviour
  as l1_03, but through the "enable list is truncated" vector.
- mut_l1_02: terminal IS a sink but Start re-enables a terminal
  loop (loop escapes Terminal — different L1 failure mode).
- mut_l1_03 (this): enable list keeps TripKill and Start+Iterate,
  but denies the FOUR non-TripKill terminal paths. Different
  code path from l1_01 — Tests exercise TripKill-reachability,
  which is zero under the bias anyway, so the behavior matches
  l1_01 on observable outcome but the mutation diff is scoped
  narrowly to terminal clauses (smaller blast radius).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L1"
DESCRIPTION = (
    "Enable gate drops Converge + Complete + BudgetKill + "
    "PropagateKill clauses (keeps Start, Iterate, TripKill); running "
    "loops cannot reach a terminal via non-kill paths."
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
                # MUTATION: Converge / Complete / BudgetKill /
                # PropagateKill enable clauses dropped.
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

    Mutant.__name__ = "SwarmSimulatorMut_L1_03"
    return Mutant
