"""PLAN-017 Phase 3 tests — recovery + checkpoint + swarm_killed event."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..coordinator import LoopState
from ..kill_switch import KillSwitchState, DECISION_HALT
from ..recovery import (
    CHECKPOINT_SCHEMA_VERSION,
    SwarmCheckpoint,
    build_checkpoint,
    emit_swarm_killed_event,
    load_checkpoint,
    save_checkpoint,
)


def test_checkpoint_roundtrip_json() -> None:
    cp = SwarmCheckpoint(
        swarm_id="S1",
        created_at="2026-04-21T12:00:00Z",
        goal="bench",
        n_loops=2,
        budget_tokens=1000,
        loops={"L1": {"loop_id": "L1", "iteration": 3}},
    )
    restored = SwarmCheckpoint.from_json(cp.to_json())
    assert restored == cp


def test_checkpoint_rejects_unknown_schema_version() -> None:
    payload = json.dumps(
        {
            "swarm_id": "S1",
            "created_at": "2026-04-21T12:00:00Z",
            "schema_version": 99,
        }
    )
    with pytest.raises(ValueError, match="schema_version"):
        SwarmCheckpoint.from_json(payload)


def test_build_checkpoint_from_live_state() -> None:
    loops = {"L1": LoopState(loop_id="L1", iteration=2, tokens_consumed=500)}
    ks = KillSwitchState(
        decision=DECISION_HALT,
        reasons=["cb_1_budget_exceeded"],
        loops_to_kill=["L1"],
    )
    cp = build_checkpoint(
        swarm_id="S1",
        goal="bench",
        budget_tokens=1000,
        loops=loops,
        kill_state=ks,
        worktrees_preserved=["/tmp/wt-L1"],
    )
    assert cp.swarm_id == "S1"
    assert cp.n_loops == 1
    assert cp.budget_tokens == 1000
    assert cp.loops["L1"]["iteration"] == 2
    assert cp.last_decision == DECISION_HALT
    assert cp.last_reasons == ["cb_1_budget_exceeded"]
    assert cp.loops_to_kill == ["L1"]
    assert cp.worktrees_preserved == ["/tmp/wt-L1"]
    assert cp.schema_version == CHECKPOINT_SCHEMA_VERSION


def test_save_and_load_checkpoint(tmp_path: Path) -> None:
    cp = SwarmCheckpoint(
        swarm_id="S1",
        created_at="2026-04-21T12:00:00Z",
        goal="bench",
    )
    path = tmp_path / "checkpoint.json"
    save_checkpoint(cp, path)
    restored = load_checkpoint(path)
    assert restored == cp


def test_save_checkpoint_atomic_rename(tmp_path: Path) -> None:
    # After save, no stray .tmp files remain.
    cp = SwarmCheckpoint(
        swarm_id="S1",
        created_at="2026-04-21T12:00:00Z",
    )
    path = tmp_path / "checkpoint.json"
    save_checkpoint(cp, path)
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftovers == []


def test_save_checkpoint_rejects_missing_parent(tmp_path: Path) -> None:
    cp = SwarmCheckpoint(swarm_id="S1", created_at="2026-04-21T12:00:00Z")
    target = tmp_path / "subdir-missing" / "checkpoint.json"
    with pytest.raises(FileNotFoundError):
        save_checkpoint(cp, target)


def test_load_checkpoint_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_checkpoint(tmp_path / "nope.json")


def test_emit_swarm_killed_event_returns_record() -> None:
    record = emit_swarm_killed_event(
        swarm_id="S1", reasons=["cb_1_budget_exceeded"], loops_killed=["L1", "L2"]
    )
    assert record["action"] == "swarm_killed"
    assert record["swarm_id"] == "S1"
    assert record["reasons"] == ["cb_1_budget_exceeded"]
    assert record["loops_killed"] == ["L1", "L2"]
    assert "ts" in record


def test_emit_swarm_killed_event_appends_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    emit_swarm_killed_event(
        swarm_id="S1",
        reasons=["cb_2_convergence"],
        loops_killed=["L2"],
        event_log_path=log,
    )
    emit_swarm_killed_event(
        swarm_id="S1",
        reasons=["manual"],
        loops_killed=[],
        event_log_path=log,
    )
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert record["action"] == "swarm_killed"


def test_emit_swarm_killed_event_missing_parent_noop(tmp_path: Path) -> None:
    # Log path whose parent does not exist → no write, but record still returned.
    log = tmp_path / "missing" / "events.jsonl"
    record = emit_swarm_killed_event(
        swarm_id="S1", reasons=["x"], loops_killed=[], event_log_path=log
    )
    assert record["action"] == "swarm_killed"
    assert not log.exists()


def test_checkpoint_default_worktrees_preserved_empty() -> None:
    cp = SwarmCheckpoint(swarm_id="S1", created_at="2026-04-21T12:00:00Z")
    assert cp.worktrees_preserved == []


def test_build_checkpoint_without_kill_state() -> None:
    cp = build_checkpoint(
        swarm_id="S1",
        goal="bench",
        budget_tokens=1000,
        loops={},
    )
    assert cp.last_decision == "continue"
    assert cp.last_reasons == []
    assert cp.loops_to_kill == []
