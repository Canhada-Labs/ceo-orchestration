"""PLAN-050 Phase 7 final — TLA+ Next-state relation reference simulator.

Pure-Python bounded re-implementation of the state-machine specified in
``docs/formal-verification/swarm-coordinator.tla``. Every action
(StartLoop, Iterate, Converge, Complete, BudgetKill, TripKill,
PropagateKill) mirrors its TLA+ counterpart exactly — with the
simplifying modeling abstractions acknowledged in
``properties-proved.md`` §9.3.

## Why a separate module

The conformance harness (``tests/formal_verification/
test_swarm_coordinator_conformance.py``) and the mutation fixtures
(``tests/formal_verification/mutation_fixtures/swarm_coordinator/``)
both need to share the simulator code. Keeping it here:

- avoids circular imports between the test and its mutation set,
- makes the simulator independently unit-testable, and
- lets the coordinator ship a reference-sim for adopters who want to
  prove properties of their own variant invariants without reaching
  into the test tree.

## Contract

- Stdlib-only + Python 3.9 compatible.
- Every action is a pure transition; no I/O, no threading, no sleep.
- ``_SwarmSimulator.walk()`` is deterministic given the RNG seed and
  the action-bias callable.
- The module emits zero audit events — that's for ``coordinator.py``
  and the adapter layer, not the simulator.

## Separation from `coordinator.py`

``coordinator.py`` is the production scaffold; it owns dataclasses,
CLI argparse, kill-switch integration, and audit hooks. This module
is the *spec-level* reference — it reuses ``LoopState`` from
``coordinator.py`` for type compatibility but models its own bounded
state space (the TLA+ concepts of ``kill`` + ``consumed`` as
first-class state variables).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .coordinator import LoopState


# Terminal statuses mirror TLA+ ``Terminal`` set.
TERMINAL_STATUSES = frozenset({"converged", "killed", "completed", "errored"})


@dataclass
class SimConfig:
    """TLC bounds for the simulator. Analogous to CONSTANTS in the .cfg.

    Defaults match the small-model configuration in
    ``docs/formal-verification/swarm-coordinator.cfg`` so the
    conformance harness asserts the same bounds TLC checks.
    """

    n: int = 3
    max_parallel: int = 2
    max_iter: int = 4
    budget: int = 6
    # Fairness bound — hard ceiling on total simulation steps so any
    # single walk terminates even if fairness heuristic stalls.
    step_ceiling: int = 200


@dataclass
class SimState:
    """Concrete state matching TLA+ variables ``loops``, ``kill``, ``consumed``."""

    loops: Dict[str, LoopState] = field(default_factory=dict)
    kill: bool = False
    consumed: int = 0

    def clone(self) -> "SimState":
        cloned_loops = {
            lid: LoopState.from_dict(state.to_dict())
            for lid, state in self.loops.items()
        }
        return SimState(
            loops=cloned_loops, kill=self.kill, consumed=self.consumed
        )


def init_state(cfg: SimConfig) -> SimState:
    """Build the initial state: N pending loops, no kill, zero consumed."""
    loops = {
        f"L{i}": LoopState(loop_id=f"L{i}", status="pending") for i in range(cfg.n)
    }
    return SimState(loops=loops)


def enabled_actions(
    state: SimState, cfg: SimConfig
) -> List[Tuple[str, Optional[str]]]:
    """Return the set of enabled (action_name, loop_id|None) pairs.

    Mirrors the disjunction in TLA+ ``Next`` but enumerates concretely.
    A loop id of ``None`` is used for the single global ``TripKill``.
    """
    enabled: List[Tuple[str, Optional[str]]] = []
    active_count = len(
        [lid for lid, s in state.loops.items() if s.status == "running"]
    )
    for lid, s in state.loops.items():
        # StartLoop — pending + cap + no kill
        if (
            s.status == "pending"
            and active_count < cfg.max_parallel
            and not state.kill
        ):
            enabled.append(("start", lid))
        # Iterate — running + room + budget + no kill
        if (
            s.status == "running"
            and s.iteration < cfg.max_iter
            and state.consumed < cfg.budget
            and not state.kill
        ):
            enabled.append(("iterate", lid))
        # Converge — running + at least 1 iteration
        if s.status == "running" and s.iteration > 0:
            enabled.append(("converge", lid))
        # Complete — running + at ceiling
        if s.status == "running" and s.iteration == cfg.max_iter:
            enabled.append(("complete", lid))
        # BudgetKill — running + budget exhausted
        if s.status == "running" and state.consumed >= cfg.budget:
            enabled.append(("budget_kill", lid))
        # PropagateKill — kill set + running/pending
        if state.kill and s.status in {"running", "pending"}:
            enabled.append(("propagate_kill", lid))
    # TripKill — only when not yet tripped
    if not state.kill:
        enabled.append(("trip_kill", None))
    return enabled


def apply_action(
    state: SimState,
    action: str,
    loop_id: Optional[str],
    cfg: SimConfig,
) -> SimState:
    """Apply one action to produce the successor state.

    Raises ValueError if the action is not enabled in ``state`` — we
    do not want silent no-ops to mask a simulator bug.
    """
    if action not in {
        "start",
        "iterate",
        "converge",
        "complete",
        "budget_kill",
        "trip_kill",
        "propagate_kill",
    }:
        raise ValueError(f"unknown action {action!r}")
    enabled_set = {(a, lid) for a, lid in enabled_actions(state, cfg)}
    if (action, loop_id) not in enabled_set:
        raise ValueError(f"action {action}({loop_id}) not enabled in state")

    next_state = state.clone()
    if action == "trip_kill":
        next_state.kill = True
        return next_state
    assert loop_id is not None  # enabled-set guarantees this
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


class SwarmSimulator:
    """Random-walk simulator over the TLA+ Next relation.

    Instantiate with a deterministic RNG; ``walk()`` yields every
    state visited (including the initial state). The walk terminates
    when no action is enabled OR the step_ceiling is reached.

    Subclass hooks (for mutation fixtures):

    - ``_enabled(state)`` — override to inject enable-guard bugs.
    - ``_apply(state, action, loop_id)`` — override to inject
      transition-bugs.
    - ``_pick(enabled)`` — override to change action selection policy.

    Defaults preserve the spec's Next-state relation faithfully.
    """

    def __init__(
        self,
        cfg: Optional[SimConfig] = None,
        rng: Optional[random.Random] = None,
        action_bias: Optional[Callable[[str, Optional[str]], float]] = None,
    ) -> None:
        self.cfg = cfg or SimConfig()
        self.rng = rng or random.Random(0)
        self._action_bias = action_bias

    # ---- public ---------------------------------------------------------

    def walk(self, initial: Optional[SimState] = None) -> List[SimState]:
        """Run until no enabled action OR step_ceiling; return full trace."""
        state = initial if initial is not None else init_state(self.cfg)
        trace: List[SimState] = [state]
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

    # ---- override hooks -------------------------------------------------

    def _enabled(
        self, state: SimState
    ) -> List[Tuple[str, Optional[str]]]:
        """Return enabled actions in ``state``. Override to inject bugs."""
        return enabled_actions(state, self.cfg)

    def _apply(
        self,
        state: SimState,
        action: str,
        loop_id: Optional[str],
    ) -> SimState:
        """Apply transition. Override to inject bugs."""
        return apply_action(state, action, loop_id, self.cfg)

    def _pick(
        self, enabled: List[Tuple[str, Optional[str]]]
    ) -> Tuple[str, Optional[str]]:
        """Pick an enabled action. Override to change selection policy."""
        if self._action_bias is None:
            return self.rng.choice(enabled)
        weights = [max(self._action_bias(a, lid), 0.0) for a, lid in enabled]
        total = sum(weights)
        if total == 0:
            return self.rng.choice(enabled)
        r = self.rng.random() * total
        running = 0.0
        for (a, lid), w in zip(enabled, weights):
            running += w
            if r <= running:
                return (a, lid)
        return enabled[-1]

    @staticmethod
    def _is_all_terminal(state: SimState) -> bool:
        return all(s.status in TERMINAL_STATUSES for s in state.loops.values())


# ---------------------------------------------------------------------------
# Summarization helpers (shared by conformance tests + audit emission)
# ---------------------------------------------------------------------------
def summarize_sim_state(state: SimState) -> Dict[str, object]:
    """Compact dict view of simulator state for assertion failure output."""
    return {
        "kill": state.kill,
        "consumed": state.consumed,
        "loops": {
            lid: {
                "status": s.status,
                "iter": s.iteration,
                "tokens": s.tokens_consumed,
            }
            for lid, s in state.loops.items()
        },
    }
