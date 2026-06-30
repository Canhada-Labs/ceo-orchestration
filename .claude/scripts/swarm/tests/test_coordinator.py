"""PLAN-017 Phase 1 tests — coordinator pure functions + dataclasses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .. import coordinator as co


# ---------------------------------------------------------------------------
# LoopState
# ---------------------------------------------------------------------------


def test_loop_state_defaults() -> None:
    s = co.LoopState(loop_id="L1")
    assert s.loop_id == "L1"
    assert s.iteration == 0
    assert s.tokens_consumed == 0
    assert s.files_touched == []
    assert s.kept_changes == 0
    assert s.strikes == 0
    assert s.status == "running"


def test_loop_state_to_from_dict_roundtrip() -> None:
    s = co.LoopState(
        loop_id="L1",
        iteration=3,
        tokens_consumed=1200,
        files_touched=["a.py", "b.py"],
        kept_changes=1,
        strikes=1,
        status="running",
    )
    payload = s.to_dict()
    assert json.loads(json.dumps(payload)) == payload  # JSON-clean
    restored = co.LoopState.from_dict(payload)
    assert restored == s


def test_loop_state_from_dict_tolerates_missing_keys() -> None:
    restored = co.LoopState.from_dict({"loop_id": "L1"})
    assert restored.loop_id == "L1"
    assert restored.iteration == 0
    assert restored.files_touched == []


# ---------------------------------------------------------------------------
# SwarmConfig
# ---------------------------------------------------------------------------


def test_swarm_config_clamps_n_loops_to_ceiling() -> None:
    cfg = co.SwarmConfig(n_loops=20, budget_tokens=1000, goal="bench")
    assert cfg.n_loops == co.MAX_PARALLEL_CEILING  # ADR-051


def test_swarm_config_rejects_zero_loops() -> None:
    with pytest.raises(ValueError, match="n_loops"):
        co.SwarmConfig(n_loops=0, budget_tokens=1000, goal="g")


def test_swarm_config_rejects_nonpositive_budget() -> None:
    with pytest.raises(ValueError, match="budget_tokens"):
        co.SwarmConfig(n_loops=2, budget_tokens=0, goal="g")


def test_swarm_config_rejects_bad_jaccard_threshold() -> None:
    with pytest.raises(ValueError, match="jaccard_threshold"):
        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="g", jaccard_threshold=1.5)


def test_swarm_config_rejects_empty_goal() -> None:
    with pytest.raises(ValueError, match="goal"):
        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="   ")


def test_swarm_config_rejects_bad_max_strikes() -> None:
    with pytest.raises(ValueError, match="max_strikes"):
        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="g", max_strikes=0)


# ---------------------------------------------------------------------------
# jaccard
# ---------------------------------------------------------------------------


def test_jaccard_both_empty_is_one() -> None:
    assert co.jaccard(set(), set()) == 1.0


def test_jaccard_disjoint_is_zero() -> None:
    assert co.jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_identical_is_one() -> None:
    assert co.jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_half_overlap() -> None:
    assert co.jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# detect_convergence
# ---------------------------------------------------------------------------


def test_detect_convergence_kills_later_loop() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1", files_touched=["a.py", "b.py"]),
        "L2": co.LoopState(loop_id="L2", files_touched=["a.py", "b.py"]),
    }
    converged = co.detect_convergence(loops, threshold=0.9)
    assert converged == ["L2"]


def test_detect_convergence_no_overlap() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1", files_touched=["a.py"]),
        "L2": co.LoopState(loop_id="L2", files_touched=["b.py"]),
    }
    assert co.detect_convergence(loops, threshold=0.5) == []


def test_detect_convergence_skips_already_killed_loop() -> None:
    # When L2 is killed due to overlap with L1, a subsequent pair (L2, L3)
    # should not be considered — L2 is no longer in the running set.
    loops = {
        "L1": co.LoopState(loop_id="L1", files_touched=["a.py"]),
        "L2": co.LoopState(loop_id="L2", files_touched=["a.py"]),
        "L3": co.LoopState(loop_id="L3", files_touched=["a.py"]),
    }
    converged = co.detect_convergence(loops, threshold=0.9)
    # L2 killed by L1 overlap; L3 killed by L1 overlap (not by L2).
    assert converged == ["L2", "L3"]


def test_detect_convergence_bad_threshold() -> None:
    with pytest.raises(ValueError):
        co.detect_convergence({}, threshold=-0.1)


# ---------------------------------------------------------------------------
# budget_exceeded
# ---------------------------------------------------------------------------


def test_budget_exceeded_false_within_budget() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1", tokens_consumed=500),
        "L2": co.LoopState(loop_id="L2", tokens_consumed=400),
    }
    assert co.budget_exceeded(loops, budget=1000) is False


def test_budget_exceeded_true_over_budget() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1", tokens_consumed=600),
        "L2": co.LoopState(loop_id="L2", tokens_consumed=500),
    }
    assert co.budget_exceeded(loops, budget=1000) is True


def test_budget_exceeded_rejects_bad_budget() -> None:
    with pytest.raises(ValueError):
        co.budget_exceeded({}, budget=0)


# ---------------------------------------------------------------------------
# env_kill_switch_tripped
# ---------------------------------------------------------------------------


def test_env_kill_switch_default_off() -> None:
    # Default-OFF per Design Principle #1 — absent CEO_SWARM=1 trips.
    assert co.env_kill_switch_tripped(env={}) is True


def test_env_kill_switch_disable_takes_precedence() -> None:
    assert (
        co.env_kill_switch_tripped(
            env={"CEO_SWARM": "1", "CEO_AUTONOMOUS_LOOPS_DISABLE": "1"}
        )
        is True
    )


def test_env_kill_switch_allows_enabled() -> None:
    assert co.env_kill_switch_tripped(env={"CEO_SWARM": "1"}) is False


# ---------------------------------------------------------------------------
# sentinel_file_kill_switch_tripped
# ---------------------------------------------------------------------------


def test_sentinel_missing_returns_false(tmp_path: Path) -> None:
    assert co.sentinel_file_kill_switch_tripped(tmp_path / "nope") is False


def test_sentinel_present_returns_true(tmp_path: Path) -> None:
    sentinel = tmp_path / "swarm-kill"
    sentinel.write_text("")
    assert co.sentinel_file_kill_switch_tripped(sentinel) is True


# ---------------------------------------------------------------------------
# summarize + enumerate_active_loops
# ---------------------------------------------------------------------------


def test_summarize_structure() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1", iteration=2, tokens_consumed=100),
        "L2": co.LoopState(loop_id="L2", iteration=3, tokens_consumed=200, status="killed"),
    }
    snap = co.summarize(loops)
    assert snap["n_loops"] == 2
    assert snap["total_tokens_consumed"] == 300
    assert snap["total_iterations"] == 5
    assert snap["status_counts"] == {"running": 1, "killed": 1}
    assert snap["active"] == ["L1"]


def test_enumerate_active_loops_filters_non_running() -> None:
    loops = {
        "L1": co.LoopState(loop_id="L1"),
        "L2": co.LoopState(loop_id="L2", status="converged"),
        "L3": co.LoopState(loop_id="L3", status="completed"),
    }
    assert co.enumerate_active_loops(loops) == ["L1"]


# ---------------------------------------------------------------------------
# main CLI
# ---------------------------------------------------------------------------


def test_cli_refuses_without_env(capsys, monkeypatch) -> None:
    monkeypatch.delenv("CEO_SWARM", raising=False)
    rc = co.main(["--loops", "2", "--budget-tokens", "1000", "--goal", "bench"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert rc == 0
    assert payload["status"] == "refused"
    assert "env_kill_switch" in payload["reason"]


def test_cli_dry_run_with_env(capsys, monkeypatch) -> None:
    monkeypatch.setenv("CEO_SWARM", "1")
    rc = co.main(
        [
            "--loops",
            "2",
            "--budget-tokens",
            "1000",
            "--goal",
            "bench",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert rc == 0
    assert payload["status"] == "dry_run"
    assert payload["config"]["n_loops"] == 2


def test_cli_scaffold_refuses_real_dispatch(capsys, monkeypatch) -> None:
    monkeypatch.setenv("CEO_SWARM", "1")
    rc = co.main(["--loops", "2", "--budget-tokens", "1000", "--goal", "bench"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert rc == 0
    assert payload["status"] == "refused"
    assert "scaffold_only" in payload["reason"]


def test_cli_bad_config_returns_nonzero(capsys, monkeypatch) -> None:
    monkeypatch.setenv("CEO_SWARM", "1")
    rc = co.main(["--loops", "2", "--budget-tokens", "0", "--goal", "bench"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "config_error" in captured.err
