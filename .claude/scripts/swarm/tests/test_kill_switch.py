"""PLAN-017 Phase 1 + Phase 3 tests — kill switch + circuit breakers.

PLAN-050 Phase 7a (C4) — CBs 6-9 added (disk, FDs, wall-clock,
parent-death) covering extensions to `evaluate_kill_switch`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ..coordinator import LoopState
from ..kill_switch import (
    DECISION_CONTINUE,
    DECISION_HALT,
    DECISION_PAUSE,
    KillSwitchState,
    default_sentinel_path,
    evaluate_kill_switch,
)


def test_kill_switch_state_escalation_respects_order() -> None:
    state = KillSwitchState()
    state.escalate(DECISION_PAUSE)
    assert state.decision == DECISION_PAUSE
    state.escalate(DECISION_CONTINUE)
    # Cannot downgrade.
    assert state.decision == DECISION_PAUSE
    state.escalate(DECISION_HALT)
    assert state.decision == DECISION_HALT


def test_kill_switch_state_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError):
        KillSwitchState().escalate("annihilate")


def test_kill_switch_state_dedups_reasons() -> None:
    s = KillSwitchState()
    s.add_reason("cb_1_budget_exceeded")
    s.add_reason("cb_1_budget_exceeded")
    assert s.reasons == ["cb_1_budget_exceeded"]


def test_kill_switch_to_dict_is_json_clean() -> None:
    s = KillSwitchState(
        decision=DECISION_HALT, reasons=["cb_1_budget_exceeded"], loops_to_kill=["L2"]
    )
    payload = s.to_dict()
    assert payload == {
        "decision": DECISION_HALT,
        "reasons": ["cb_1_budget_exceeded"],
        "loops_to_kill": ["L2"],
    }


def test_evaluate_default_env_trips_halt(tmp_path: Path) -> None:
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        sentinel_path=tmp_path / "nope",
        env={},
    )
    assert r.decision == DECISION_HALT
    assert any("kill_layer_1_env" in reason for reason in r.reasons)


def test_evaluate_disable_env_trips_halt_even_when_enabled() -> None:
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        env={"CEO_SWARM": "1", "CEO_AUTONOMOUS_LOOPS_DISABLE": "1"},
    )
    assert r.decision == DECISION_HALT


def test_evaluate_sentinel_present_trips_halt(tmp_path: Path) -> None:
    sentinel = tmp_path / "swarm-kill"
    sentinel.write_text("")
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        sentinel_path=sentinel,
        env={"CEO_SWARM": "1"},
    )
    assert r.decision == DECISION_HALT
    assert any("kill_layer_2_sentinel" in reason for reason in r.reasons)


def test_evaluate_iteration_limit_pauses() -> None:
    loops = {"L1": LoopState(loop_id="L1", iteration=10)}
    r = evaluate_kill_switch(
        loops,
        budget_tokens=1000,
        iteration_limit=10,
        env={"CEO_SWARM": "1"},
    )
    assert r.decision == DECISION_PAUSE
    assert any("kill_layer_3_iteration_ceiling" in reason for reason in r.reasons)


def test_evaluate_budget_exceeded_trips_halt() -> None:
    loops = {
        "L1": LoopState(loop_id="L1", tokens_consumed=600),
        "L2": LoopState(loop_id="L2", tokens_consumed=500),
    }
    r = evaluate_kill_switch(
        loops, budget_tokens=1000, env={"CEO_SWARM": "1"}
    )
    assert r.decision == DECISION_HALT
    assert any("cb_1_budget_exceeded" in reason for reason in r.reasons)


def test_evaluate_convergence_kills_loser_swarm_continues() -> None:
    loops = {
        "L1": LoopState(loop_id="L1", files_touched=["a.py", "b.py"]),
        "L2": LoopState(loop_id="L2", files_touched=["a.py", "b.py"]),
    }
    r = evaluate_kill_switch(
        loops,
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        jaccard_threshold=0.9,
    )
    # No halt — just loser promoted to loops_to_kill.
    assert r.decision == DECISION_CONTINUE
    assert "L2" in r.loops_to_kill


def test_evaluate_strike_trips_loop_kill() -> None:
    loops = {"L1": LoopState(loop_id="L1", strikes=3)}
    r = evaluate_kill_switch(
        loops,
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        max_strikes=3,
    )
    assert "L1" in r.loops_to_kill


def test_evaluate_multiple_reasons_coexist() -> None:
    loops = {
        "L1": LoopState(loop_id="L1", tokens_consumed=2000, strikes=3),
    }
    r = evaluate_kill_switch(
        loops,
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        max_strikes=3,
    )
    # Budget-exceeded halt + strike-kill loop, both captured.
    assert r.decision == DECISION_HALT
    assert "L1" in r.loops_to_kill
    assert any("cb_1_budget_exceeded" in reason for reason in r.reasons)
    assert any("cb_3_strikes" in reason for reason in r.reasons)


def test_default_sentinel_path_uses_cwd(tmp_path: Path) -> None:
    p = default_sentinel_path(tmp_path)
    assert p == tmp_path / ".claude" / "swarm-kill"


# =========================================================================
# PLAN-050 Phase 7a (C4) — CBs 6-9 coverage
# =========================================================================


def test_cb_6_disk_floor_triggers_halt_when_below_floor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CB #6 — disk free below floor → HALT."""
    from .. import kill_switch as ks_mod

    monkeypatch.setattr(ks_mod, "_disk_free_bytes", lambda _p: 100)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        disk_check_path=tmp_path,
        min_disk_free_bytes=1024 * 1024,
    )
    assert r.decision == DECISION_HALT
    assert any("cb_6_disk_floor" in reason for reason in r.reasons)


def test_cb_6_disk_floor_no_op_when_path_none() -> None:
    """CB #6 is opt-in via disk_check_path; None = no check."""
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        disk_check_path=None,
    )
    assert r.decision == DECISION_CONTINUE
    assert not any("cb_6_disk" in reason for reason in r.reasons)


def test_cb_7_fd_ceiling_triggers_halt_when_over_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CB #7 — open FDs >= ceiling ratio of soft rlimit → HALT."""
    from .. import kill_switch as ks_mod

    monkeypatch.setattr(ks_mod, "_open_fd_count", lambda: 900)
    monkeypatch.setattr(ks_mod, "_fd_soft_limit", lambda: 1024)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        fd_ceiling_ratio=0.80,  # 900 >= 1024*0.80 = 819
    )
    assert r.decision == DECISION_HALT
    assert any("cb_7_fd_ceiling" in reason for reason in r.reasons)


def test_cb_7_fd_ceiling_ok_when_below_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .. import kill_switch as ks_mod

    monkeypatch.setattr(ks_mod, "_open_fd_count", lambda: 100)
    monkeypatch.setattr(ks_mod, "_fd_soft_limit", lambda: 1024)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        fd_ceiling_ratio=0.80,
    )
    assert r.decision == DECISION_CONTINUE


def test_cb_8_wall_clock_triggers_halt_when_elapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CB #8 — wall-clock elapsed >= max → HALT."""
    import time as _time
    from .. import kill_switch as ks_mod

    # Freeze ks_mod's time reference to simulate 2h passed against 1h cap.
    base_monotonic = _time.monotonic()
    monkeypatch.setattr(ks_mod.time, "monotonic", lambda: base_monotonic + 7200.0)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        swarm_start_monotonic=base_monotonic,
        max_wall_clock_seconds=3600.0,
    )
    assert r.decision == DECISION_HALT
    assert any("cb_8_wall_clock" in reason for reason in r.reasons)


def test_cb_8_wall_clock_no_op_without_start() -> None:
    """CB #8 is opt-in; without swarm_start_monotonic it's skipped."""
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        swarm_start_monotonic=None,
    )
    assert r.decision == DECISION_CONTINUE


def test_cb_9_parent_death_triggers_halt_when_ppid_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CB #9 — expected parent PID no longer our parent → HALT."""
    from .. import kill_switch as ks_mod

    monkeypatch.setattr(ks_mod, "parent_still_alive", lambda _pid: False)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        expected_parent_pid=999_999,
    )
    assert r.decision == DECISION_HALT
    assert any("cb_9_parent_death" in reason for reason in r.reasons)


def test_cb_9_parent_death_ok_when_parent_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .. import kill_switch as ks_mod

    monkeypatch.setattr(ks_mod, "parent_still_alive", lambda _pid: True)
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        expected_parent_pid=os.getpid(),
    )
    assert r.decision == DECISION_CONTINUE


def test_cb_9_parent_death_no_op_without_expected_pid() -> None:
    r = evaluate_kill_switch(
        loops={},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
        expected_parent_pid=None,
    )
    assert r.decision == DECISION_CONTINUE
