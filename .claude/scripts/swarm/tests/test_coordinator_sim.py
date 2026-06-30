"""PLAN-050 Phase 7 final — tests for the TLA+ reference simulator.

Sanity tests ensure the simulator's Next-state relation is internally
consistent. These are separate from the conformance harness (which
asserts the full invariant suite via property tests).
"""
from __future__ import annotations

import random

import pytest

from .._coordinator_sim import (
    SimConfig,
    SwarmSimulator,
    TERMINAL_STATUSES,
    apply_action,
    enabled_actions,
    init_state,
    summarize_sim_state,
)


def test_init_state_starts_all_pending() -> None:
    cfg = SimConfig(n=3)
    state = init_state(cfg)
    assert len(state.loops) == 3
    for s in state.loops.values():
        assert s.status == "pending"
        assert s.iteration == 0
        assert s.tokens_consumed == 0
    assert state.kill is False
    assert state.consumed == 0


def test_enabled_actions_initial_state_only_start_and_trip() -> None:
    cfg = SimConfig(n=2)
    state = init_state(cfg)
    enabled = enabled_actions(state, cfg)
    start_ids = {lid for act, lid in enabled if act == "start"}
    assert start_ids == {"L0", "L1"}
    assert ("trip_kill", None) in enabled


def test_enabled_actions_respects_max_parallel() -> None:
    cfg = SimConfig(n=3, max_parallel=1)
    state = init_state(cfg)
    state.loops["L0"].status = "running"
    enabled = enabled_actions(state, cfg)
    # Only L1, L2 are pending; neither can start because active_count=1
    # is already at max_parallel=1.
    start_actions = [(a, lid) for a, lid in enabled if a == "start"]
    assert start_actions == []


def test_apply_action_rejects_disabled_action() -> None:
    cfg = SimConfig()
    state = init_state(cfg)
    # Iterate on a pending loop is not enabled.
    with pytest.raises(ValueError, match="not enabled"):
        apply_action(state, "iterate", "L0", cfg)


def test_apply_action_rejects_unknown_action() -> None:
    cfg = SimConfig()
    state = init_state(cfg)
    with pytest.raises(ValueError, match="unknown action"):
        apply_action(state, "bogus", "L0", cfg)


def test_apply_action_start_transitions_to_running() -> None:
    cfg = SimConfig()
    state = init_state(cfg)
    new_state = apply_action(state, "start", "L0", cfg)
    assert new_state.loops["L0"].status == "running"
    # Original untouched — apply_action clones.
    assert state.loops["L0"].status == "pending"


def test_apply_action_iterate_advances_iter_tokens_consumed() -> None:
    cfg = SimConfig()
    state = init_state(cfg)
    state = apply_action(state, "start", "L0", cfg)
    state = apply_action(state, "iterate", "L0", cfg)
    s = state.loops["L0"]
    assert s.iteration == 1
    assert s.tokens_consumed == 1
    assert state.consumed == 1


def test_apply_action_trip_kill_sets_flag() -> None:
    cfg = SimConfig()
    state = init_state(cfg)
    state = apply_action(state, "trip_kill", None, cfg)
    assert state.kill is True


def test_walk_terminates_within_step_ceiling() -> None:
    cfg = SimConfig(n=3, max_parallel=2, max_iter=4, budget=6, step_ceiling=500)
    rng = random.Random(42)
    sim = SwarmSimulator(cfg=cfg, rng=rng)
    trace = sim.walk()
    assert len(trace) <= cfg.step_ceiling + 1
    # All loops terminal in final state.
    final = trace[-1]
    assert all(s.status in TERMINAL_STATUSES for s in final.loops.values())


def test_walk_is_deterministic_with_same_seed() -> None:
    cfg = SimConfig()
    sim_a = SwarmSimulator(cfg=cfg, rng=random.Random(123))
    sim_b = SwarmSimulator(cfg=cfg, rng=random.Random(123))
    trace_a = sim_a.walk()
    trace_b = sim_b.walk()
    assert len(trace_a) == len(trace_b)
    for a, b in zip(trace_a, trace_b):
        assert summarize_sim_state(a) == summarize_sim_state(b)


def test_walk_with_action_bias_influences_outcome() -> None:
    """A bias favoring TripKill makes the kill flag trip quickly."""
    cfg = SimConfig(step_ceiling=50)

    def kill_bias(action: str, _loop_id) -> float:
        return 100.0 if action == "trip_kill" else 1.0

    rng = random.Random(7)
    sim = SwarmSimulator(cfg=cfg, rng=rng, action_bias=kill_bias)
    trace = sim.walk()
    # Kill should have been tripped at some point.
    assert any(state.kill for state in trace)


def test_summarize_sim_state_shape() -> None:
    cfg = SimConfig(n=2)
    state = init_state(cfg)
    summary = summarize_sim_state(state)
    assert set(summary.keys()) == {"kill", "consumed", "loops"}
    assert summary["kill"] is False
    assert summary["consumed"] == 0
    assert set(summary["loops"].keys()) == {"L0", "L1"}


def test_sim_subclass_can_override_enabled() -> None:
    """Mutation pattern: subclass overrides ``_enabled`` to inject a bug."""
    cfg = SimConfig(n=2)

    class NoStart(SwarmSimulator):
        def _enabled(self, state):
            # Exactly mimics the baseline but drops Start entirely.
            # Return trip_kill only when not yet kill; no other actions.
            return [] if state.kill else [("trip_kill", None)]

    rng = random.Random(0)
    sim = NoStart(cfg=cfg, rng=rng)
    trace = sim.walk()
    # After one TripKill, kill=True → _enabled returns [] → walk ends.
    final = trace[-1]
    assert final.kill is True
    for s in final.loops.values():
        assert s.status == "pending"


def test_sim_subclass_can_override_apply() -> None:
    """Mutation pattern: subclass overrides ``_apply`` to inject a bug."""
    cfg = SimConfig()
    state = init_state(cfg)

    class DoubleIter(SwarmSimulator):
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
                s.iteration += 2  # bug
                s.tokens_consumed += 1
                next_state.consumed += 1
            else:
                return next_state
            return next_state

    rng = random.Random(0)
    sim = DoubleIter(cfg=cfg, rng=rng)
    # Drive one iterate manually.
    state = sim._apply(state, "start", "L0")
    state = sim._apply(state, "iterate", "L0")
    assert state.loops["L0"].iteration == 2  # mutation fired
