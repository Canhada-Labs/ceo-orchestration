"""PLAN-051 Phase 6 — coordinator.tick() integration tests.

Covers the per-iteration kill-switch + watchdog wire point. The
acceptance spec (``PLAN-051 §Phase 6``) requires a DIRECT call to
``parent_still_alive`` in ``coordinator.py``; these tests exercise
that path + the fast-path halt + the fail-open on watchdog errors.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from .. import _parent_death as pd
from .. import coordinator as co
from ..kill_switch import DECISION_CONTINUE, DECISION_HALT, DECISION_PAUSE


def _cfg(**overrides):
    defaults = dict(
        n_loops=2, budget_tokens=100, goal="x",
        jaccard_threshold=0.7, max_strikes=3, max_iterations=20,
    )
    defaults.update(overrides)
    return co.SwarmConfig(**defaults)


# -----------------------------------------------------------------
# tick() delegates to evaluate_kill_switch — all layers reachable
# -----------------------------------------------------------------


def test_tick_returns_continue_when_nothing_trips() -> None:
    loops = {"L0": co.LoopState(loop_id="L0", iteration=1, status="running")}
    result = co.tick(
        loops,
        cfg=_cfg(),
        env={"CEO_SWARM": "1"},
    )
    assert result.decision == DECISION_CONTINUE
    assert result.reasons == []


def test_tick_halts_on_missing_ceo_swarm_env() -> None:
    """Default env (CEO_SWARM unset) must trip layer-1."""
    loops = {"L0": co.LoopState(loop_id="L0", iteration=0, status="running")}
    result = co.tick(loops, cfg=_cfg(), env={})
    assert result.decision == DECISION_HALT
    assert any("kill_layer_1_env" in r for r in result.reasons)


def test_tick_halts_on_sentinel_file(tmp_path: Path) -> None:
    sentinel = tmp_path / "swarm-kill"
    sentinel.write_text("")
    result = co.tick(
        {}, cfg=_cfg(),
        sentinel_path=sentinel, env={"CEO_SWARM": "1"},
    )
    assert result.decision == DECISION_HALT
    assert any("kill_layer_2_sentinel" in r for r in result.reasons)


def test_tick_pauses_on_iteration_ceiling() -> None:
    loops = {"L0": co.LoopState(loop_id="L0", iteration=5, status="running")}
    result = co.tick(
        loops, cfg=_cfg(),
        iteration_limit=5, env={"CEO_SWARM": "1"},
    )
    # Pause or halt both acceptable — non-continue signals the ceiling.
    assert result.decision in {DECISION_PAUSE, DECISION_HALT}
    assert any("kill_layer_3_iteration_ceiling" in r for r in result.reasons)


# -----------------------------------------------------------------
# PLAN-051 Phase 6 — direct parent_still_alive call site
# -----------------------------------------------------------------


def test_tick_halts_when_parent_gone_fast_path() -> None:
    """tick() calls parent_still_alive BEFORE evaluate — fast-path halt.

    Patching parent_still_alive to return False simulates reparenting
    to init. The tick's fast-path detects first; reason string
    names ``coordinator_tick_parent_death``.
    """
    loops = {"L0": co.LoopState(loop_id="L0", status="running")}
    with patch.object(pd, "parent_still_alive", return_value=False):
        result = co.tick(
            loops, cfg=_cfg(),
            env={"CEO_SWARM": "1"},
            expected_parent_pid=os.getppid(),
        )
    assert result.decision == DECISION_HALT
    assert any(
        "coordinator_tick_parent_death" in r for r in result.reasons
    )


def test_tick_fails_open_when_parent_check_raises() -> None:
    """tick() must not raise when parent_still_alive itself errors.

    Fail-open on infra per PROTOCOL §Fail-open. The full
    evaluate_kill_switch sweep still runs, but the tick's fast-path
    skips gracefully.
    """
    loops = {"L0": co.LoopState(loop_id="L0", iteration=1, status="running")}

    def _raise(*_a, **_kw):
        raise OSError("simulated kernel hiccup")

    with patch.object(pd, "parent_still_alive", side_effect=_raise):
        result = co.tick(
            loops, cfg=_cfg(),
            env={"CEO_SWARM": "1"},
            expected_parent_pid=os.getppid(),
        )
    # Not halted by the broken watchdog — continues with other layers.
    # Some other signal may or may not trip; assert the critical
    # contract: NO exception bubbled up.
    assert result is not None


def test_tick_skips_parent_check_when_pid_unset() -> None:
    """When expected_parent_pid is None or 0, fast-path is skipped entirely."""
    loops = {"L0": co.LoopState(loop_id="L0", iteration=1, status="running")}
    # None path.
    result_none = co.tick(loops, cfg=_cfg(), env={"CEO_SWARM": "1"})
    assert result_none.decision == DECISION_CONTINUE
    # Zero path.
    result_zero = co.tick(
        loops, cfg=_cfg(),
        env={"CEO_SWARM": "1"},
        expected_parent_pid=0,
    )
    assert result_zero.decision == DECISION_CONTINUE


def test_tick_wall_clock_ceiling_halts() -> None:
    """CB #8 — wall-clock ceiling surfaces via tick() delegation."""
    loops = {"L0": co.LoopState(loop_id="L0", iteration=1, status="running")}
    # Swarm started "an hour ago" → trips default 3600s ceiling.
    start = time.monotonic() - 3700.0
    result = co.tick(
        loops, cfg=_cfg(),
        env={"CEO_SWARM": "1"},
        swarm_start_monotonic=start,
    )
    assert result.decision == DECISION_HALT
    assert any("cb_8_wall_clock" in r for r in result.reasons)


def test_tick_budget_exceeded_halts() -> None:
    """CB #1 — budget envelope halts the swarm via tick()."""
    loops = {
        "L0": co.LoopState(loop_id="L0", tokens_consumed=120, status="running"),
    }
    result = co.tick(
        loops, cfg=_cfg(budget_tokens=100),
        env={"CEO_SWARM": "1"},
    )
    assert result.decision == DECISION_HALT
    assert any("cb_1_budget_exceeded" in r for r in result.reasons)
