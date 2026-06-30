"""Mutation L4-05: Initial state injects L0 into status=killed.

Anchor: ``_coordinator_sim.py:222-224`` — walk()'s initial-state
construction (``initial if initial is not None else init_state(cfg)``).
Axis: initialization-time corruption (the bug precedes any
transition firing).
Killed-by: EVERY seed of the L4 random walk — the initial state
itself already violates ``[](status=killed ⇒ kill)`` before any
action fires, so ``_invariant_holds`` on trace[0] raises.

Models the most dangerous L4 failure mode: the state machine
starts in an inconsistent state. The TLA+ Init predicate
requires every loop to begin pending and kill=False; a bug in
the initializer (e.g., shared mutable default, leaky state
from a prior run) can break L4 before the Next relation even
runs.

Semantic distinction from sibling L4 mutations:
- mut_l4_01: trip no-op + propagate bypass.
- mut_l4_02: propagate clears kill.
- mut_l4_03: trip kills loops.
- mut_l4_04: start mis-assigns killed.
- mut_l4_05 (this): walk() override corrupts the initial state
  directly. Distinct code anchor (walk() body, not any transition).
  100% reliable kill (every seed) — models a constructor bug that
  the harness must detect even before any Next step fires.
"""

from __future__ import annotations

from typing import List, Optional

PROPERTY = "L4"
DESCRIPTION = (
    "walk() constructs the initial state with L0 pre-marked as "
    "status=killed while state.kill=False; trace[0] already "
    "violates the L4 invariant before any transition fires."
)


def apply(sim_cls: type) -> type:
    class Mutant(sim_cls):  # type: ignore[misc,valid-type]
        def walk(self, initial=None):  # type: ignore[override]
            # MUTATION: inject L0 into killed status at init time
            # while leaving state.kill=False.
            from swarm._coordinator_sim import init_state
            state = initial if initial is not None else init_state(self.cfg)
            if "L0" in state.loops:
                state.loops["L0"].status = "killed"
            # Reuse the baseline loop from here on.
            trace = [state]
            for _ in range(self.cfg.step_ceiling):
                enabled = self._enabled(state)
                if not enabled:
                    break
                choice = self._pick(enabled)
                state = self._apply(state, choice[0], choice[1])
                trace.append(state)
                if self._is_all_terminal(state):
                    break
            return trace

    Mutant.__name__ = "SwarmSimulatorMut_L4_05"
    return Mutant
