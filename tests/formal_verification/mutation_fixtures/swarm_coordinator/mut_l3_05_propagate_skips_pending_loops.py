"""Mutation L3-05: PropagateKill enable gate excludes pending loops.

Anchor: ``_coordinator_sim.py:137`` — PropagateKill enable clause
``state.kill and s.status in {"running", "pending"}``.
Axis: gate-side scope regression (one status removed from the
enable set).
Killed-by: ``_mutations_fail`` L3 bias (trip fires early; some
seeds trip BEFORE all loops start, leaving pending loops that
can neither start (``not state.kill``) nor propagate (mutated
gate)).

Once TripKill sets ``state.kill = True``, Start is disabled (the
baseline Start gate requires ``not state.kill``) AND the mutated
PropagateKill only fires on running loops. Pending loops are left
with no enabled transition at all and are stranded at ``pending``
forever. ``pending`` is not in the Terminal set, so the final-state
unterminated check inside ``test_l3_mutations_fail`` raises.

Semantic distinction from sibling L3 mutations:
- mut_l3_01: propagate bypasses kill flag.
- mut_l3_02: kill flag ignored by Start/Iterate; propagate disabled.
- mut_l3_03: propagate partial by loop_id (scope by identity).
- mut_l3_04: transition sets running instead of killed.
- mut_l3_05 (this): gate scope regression — propagate's status
  filter loses "pending". Distinct from l3_02 (which disables
  propagate entirely) because l3_05 keeps propagate firing on
  running loops; only pending loops are stranded.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

PROPERTY = "L3"
DESCRIPTION = (
    "PropagateKill enable gate only accepts status=running (drops "
    "pending); once kill trips, pending loops become unreachable "
    "(Start blocked by kill, PropagateKill no longer fires for "
    "them) and stay pending forever."
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
                # MUTATION: propagate only on running (drops pending).
                if state.kill and s.status == "running":
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

    Mutant.__name__ = "SwarmSimulatorMut_L3_05"
    return Mutant
