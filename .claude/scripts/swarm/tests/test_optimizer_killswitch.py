"""PLAN-122 §6 (WS2-T6) — OPTIMIZER kill-switch fabric tests.

Covers the two os.environ-only OPTIMIZER switches added to the swarm
coordinator and verifies they stay PARTITIONED from the existing SAFETY
gate (CEO_SWARM default-OFF + CEO_AUTONOMOUS_LOOPS_DISABLE):

- CEO_FANOUT=0   -> individual: disables fan-out width expansion only.
- CEO_OPTIMIZER=0 -> group: disables the whole optimizer layer (dominates
                     CEO_FANOUT).

The OPTIMIZER switches are default-ON (absent => enabled); the SAFETY gate
is default-OFF (absent => disabled). The two partitions must never bleed:
an optimizer switch can never turn swarm dispatch on, and the SAFETY gate
can never be relaxed by an optimizer switch.

No hypothesis (no speed/cost/quality claims). stdlib + pytest only —
matches the rest of swarm/tests/.
"""
from __future__ import annotations

from ..coordinator import (
    OPTIMIZER_FANOUT_SWITCH,
    OPTIMIZER_GROUP_SWITCH,
    env_kill_switch_tripped,
    optimizer_fanout_disabled,
    optimizer_layer_disabled,
    optimizer_switch_state,
)
from ..kill_switch import DECISION_HALT, evaluate_kill_switch


# ---------------------------------------------------------------------------
# Group switch — CEO_OPTIMIZER (default-ON; =0 disables the whole layer)
# ---------------------------------------------------------------------------

def test_optimizer_enabled_by_default_absent() -> None:
    """Absent CEO_OPTIMIZER -> optimizer layer ENABLED (default-ON)."""
    assert optimizer_layer_disabled(env={}) is False


def test_optimizer_group_disabled_when_zero() -> None:
    """CEO_OPTIMIZER=0 -> whole optimizer layer disabled."""
    assert optimizer_layer_disabled(env={"CEO_OPTIMIZER": "0"}) is True


def test_optimizer_group_off_value_variants() -> None:
    """OFF values are case-insensitive / stripped (0/false/off/no)."""
    for val in ("0", "false", "FALSE", "off", "Off", "no", " 0 ", "No"):
        assert optimizer_layer_disabled(env={"CEO_OPTIMIZER": val}) is True, val


def test_optimizer_group_enabled_for_on_values() -> None:
    """Any non-OFF value (incl. '1', 'true', garbage) keeps the layer ON."""
    for val in ("1", "true", "on", "yes", "", "garbage"):
        assert optimizer_layer_disabled(env={"CEO_OPTIMIZER": val}) is False, val


# ---------------------------------------------------------------------------
# Individual switch — CEO_FANOUT (default-ON; =0 disables fan-out only)
# ---------------------------------------------------------------------------

def test_fanout_enabled_by_default_absent() -> None:
    """Absent CEO_FANOUT -> fan-out ENABLED (default-ON)."""
    assert optimizer_fanout_disabled(env={}) is False


def test_fanout_disabled_when_zero() -> None:
    """CEO_FANOUT=0 -> fan-out width expansion disabled."""
    assert optimizer_fanout_disabled(env={"CEO_FANOUT": "0"}) is True


def test_fanout_off_value_variants() -> None:
    for val in ("0", "false", "off", "no"):
        assert optimizer_fanout_disabled(env={"CEO_FANOUT": val}) is True, val


def test_group_switch_dominates_fanout() -> None:
    """CEO_OPTIMIZER=0 disables fan-out too, even if CEO_FANOUT is ON."""
    assert (
        optimizer_fanout_disabled(env={"CEO_OPTIMIZER": "0", "CEO_FANOUT": "1"})
        is True
    )


def test_fanout_off_does_not_disable_group() -> None:
    """CEO_FANOUT=0 narrows fan-out ONLY — the group layer stays enabled."""
    env = {"CEO_FANOUT": "0"}
    assert optimizer_fanout_disabled(env=env) is True
    assert optimizer_layer_disabled(env=env) is False


# ---------------------------------------------------------------------------
# Switch-name constants are the documented env vars
# ---------------------------------------------------------------------------

def test_switch_name_constants() -> None:
    assert OPTIMIZER_GROUP_SWITCH == "CEO_OPTIMIZER"
    assert OPTIMIZER_FANOUT_SWITCH == "CEO_FANOUT"


# ---------------------------------------------------------------------------
# optimizer_switch_state — the resolved snapshot + human reason
# ---------------------------------------------------------------------------

def test_switch_state_fully_enabled_has_empty_reason() -> None:
    state = optimizer_switch_state(env={})
    assert state["optimizer_enabled"] is True
    assert state["fanout_enabled"] is True
    assert state["reason"] == ""


def test_switch_state_group_off_reason_mentions_optimizer() -> None:
    state = optimizer_switch_state(env={"CEO_OPTIMIZER": "0"})
    assert state["optimizer_enabled"] is False
    assert state["fanout_enabled"] is False
    assert "CEO_OPTIMIZER=0" in str(state["reason"])
    assert "group" in str(state["reason"])


def test_switch_state_fanout_off_reason_mentions_fanout() -> None:
    state = optimizer_switch_state(env={"CEO_FANOUT": "0"})
    assert state["optimizer_enabled"] is True
    assert state["fanout_enabled"] is False
    assert "CEO_FANOUT=0" in str(state["reason"])
    assert "individual" in str(state["reason"])


def test_switch_state_group_off_dominates_reason() -> None:
    """Group OFF wins the reason line even if CEO_FANOUT is also set."""
    state = optimizer_switch_state(env={"CEO_OPTIMIZER": "0", "CEO_FANOUT": "0"})
    assert "CEO_OPTIMIZER=0" in str(state["reason"])


def test_switch_state_is_json_clean() -> None:
    import json

    json.dumps(optimizer_switch_state(env={"CEO_FANOUT": "0"}))


# ---------------------------------------------------------------------------
# PARTITION — OPTIMIZER switches MUST NOT relax / trip the SAFETY gate
# ---------------------------------------------------------------------------

def test_optimizer_off_does_not_enable_safety_gate() -> None:
    """CEO_OPTIMIZER=0 (no CEO_SWARM) -> SAFETY gate still tripped (disabled)."""
    # SAFETY gate is default-OFF: absent CEO_SWARM => tripped True.
    assert env_kill_switch_tripped(env={"CEO_OPTIMIZER": "0"}) is True
    assert env_kill_switch_tripped(env={"CEO_FANOUT": "0"}) is True


def test_optimizer_on_does_not_enable_safety_gate() -> None:
    """An ON optimizer cannot turn swarm dispatch on by itself."""
    assert env_kill_switch_tripped(env={"CEO_OPTIMIZER": "1", "CEO_FANOUT": "1"}) is True


def test_safety_gate_unaffected_by_optimizer_when_armed() -> None:
    """CEO_SWARM=1 alone disarms SAFETY gate regardless of optimizer switches."""
    assert (
        env_kill_switch_tripped(env={"CEO_SWARM": "1", "CEO_OPTIMIZER": "0"}) is False
    )
    assert (
        env_kill_switch_tripped(env={"CEO_SWARM": "1", "CEO_FANOUT": "0"}) is False
    )


# ---------------------------------------------------------------------------
# evaluate_kill_switch — optimizer reason is ADVISORY (never changes decision)
# ---------------------------------------------------------------------------

def test_evaluate_records_optimizer_reason_without_changing_decision() -> None:
    """CEO_OPTIMIZER=0 records a reason but the HALT decision is from the
    SAFETY gate (CEO_SWARM!=1), not from the optimizer switch."""
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        env={"CEO_OPTIMIZER": "0"},
    )
    # Decision is HALT because the SAFETY gate trips (CEO_SWARM absent), NOT
    # because of the optimizer switch.
    assert r.decision == DECISION_HALT
    assert any("optimizer_kill_switch" in reason for reason in r.reasons)
    assert any("kill_layer_1_env" in reason for reason in r.reasons)


def test_evaluate_optimizer_off_does_not_halt_when_safety_armed() -> None:
    """With SAFETY armed (CEO_SWARM=1), CEO_FANOUT=0 records an advisory
    reason but does NOT escalate to halt/pause on its own."""
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        env={"CEO_SWARM": "1", "CEO_FANOUT": "0"},
    )
    # No loops, SAFETY armed, no sentinel/budget/iteration trip -> continue.
    assert r.decision != DECISION_HALT
    assert any("CEO_FANOUT=0" in reason for reason in r.reasons)


def test_evaluate_no_optimizer_reason_when_fully_enabled() -> None:
    """When the optimizer is fully enabled, no optimizer reason is added."""
    r = evaluate_kill_switch(
        {},
        budget_tokens=1000,
        env={"CEO_SWARM": "1"},
    )
    assert not any("optimizer_kill_switch" in reason for reason in r.reasons)
