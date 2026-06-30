"""PLAN-050 Phase 7 final — replay-tournament wiring tests."""
from __future__ import annotations

from typing import Dict

import pytest

from .._benchmark_replay import BenchmarkResult, TaskResult
from .._replay_tournament import (
    ReplayTournamentResult,
    benchmark_to_candidate,
    run_benchmark_tournament,
)
from ..tournament import (
    DIRECTION_MAXIMIZE,
    DIRECTION_MINIMIZE,
    Candidate,
    ScoreWeights,
)


def _make_task(
    task_id: str,
    score: float,
    baseline: float,
    tolerance: float = 0.02,
    work_ms: float = 10.0,
    git_ms: float = 1.0,
) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        score=score,
        baseline_score=baseline,
        regression_tolerance=tolerance,
        work_latency_ms=work_ms,
        git_overhead_ms=git_ms,
    )


def _make_result(
    *tasks: TaskResult,
    baseline_sha: str = "abc123",
) -> BenchmarkResult:
    return BenchmarkResult(
        manifest_version=1,
        baseline_sha=baseline_sha,
        tasks=list(tasks),
    )


# ---------------------------------------------------------------------------
# benchmark_to_candidate
# ---------------------------------------------------------------------------
def test_benchmark_to_candidate_primary_metric_is_mean_score() -> None:
    br = _make_result(
        _make_task("t1", score=0.90, baseline=0.80),
        _make_task("t2", score=0.80, baseline=0.70),
    )
    cand = benchmark_to_candidate("loop-A", br)
    assert cand.loop_id == "loop-A"
    assert cand.metric == pytest.approx(0.85)
    assert cand.tests_failed == 0
    assert cand.tests_passed == 2


def test_benchmark_to_candidate_counts_regressions_as_test_failures() -> None:
    br = _make_result(
        _make_task("t1", score=0.50, baseline=0.80),  # regressed
        _make_task("t2", score=0.85, baseline=0.80),  # pass
    )
    cand = benchmark_to_candidate("loop-B", br)
    assert cand.tests_failed == 1
    assert cand.tests_passed == 1
    assert cand.has_regressions is True


def test_benchmark_to_candidate_populates_secondary_metrics() -> None:
    br = _make_result(
        _make_task("t1", score=0.95, baseline=0.80, work_ms=100.0),  # improved
        _make_task("t2", score=0.80, baseline=0.80, work_ms=50.0),  # neutral
    )
    cand = benchmark_to_candidate("loop-C", br)
    assert "n_improved" in cand.secondary_metrics
    assert cand.secondary_metrics["n_improved"] == 1.0
    assert cand.secondary_metrics["neg_work_latency_ms"] == pytest.approx(-75.0)
    assert cand.secondary_metrics["regressed_penalty"] == 0.0


def test_benchmark_to_candidate_custom_secondary_mapper() -> None:
    br = _make_result(_make_task("t1", score=0.7, baseline=0.7))

    def mapper(r: BenchmarkResult) -> Dict[str, float]:
        return {"custom": 42.0}

    cand = benchmark_to_candidate("loop-D", br, secondary_mapper=mapper)
    assert cand.secondary_metrics == {"custom": 42.0}


def test_benchmark_to_candidate_rejects_empty_loop_id() -> None:
    br = _make_result(_make_task("t1", score=0.8, baseline=0.8))
    with pytest.raises(ValueError, match="non-empty"):
        benchmark_to_candidate("", br)


def test_benchmark_to_candidate_patch_ref_roundtrip() -> None:
    br = _make_result(_make_task("t1", score=0.8, baseline=0.8))
    cand = benchmark_to_candidate("loop-E", br, patch_ref="worktree/loop-E")
    assert cand.patch_ref == "worktree/loop-E"


def test_benchmark_to_candidate_handles_nan_score_defensively() -> None:
    """A pathological task callable returning NaN becomes score=0 + regression."""
    nan = float("nan")
    tr = TaskResult(
        task_id="t1",
        score=nan,
        baseline_score=0.8,
        regression_tolerance=0.02,
        work_latency_ms=0.0,
    )
    br = _make_result(tr)
    cand = benchmark_to_candidate("loop-nan", br)
    # mean_score becomes nan but we zero it out.
    assert cand.metric == 0.0
    # Treated as if it had at least one regression.
    assert cand.tests_failed >= 1


def test_benchmark_to_candidate_handles_inf_score_defensively() -> None:
    """A task returning +inf also gets zeroed out — no silent top-of-leaderboard."""
    tr = TaskResult(
        task_id="t1",
        score=float("inf"),
        baseline_score=0.8,
        regression_tolerance=0.02,
        work_latency_ms=0.0,
    )
    br = _make_result(tr)
    cand = benchmark_to_candidate("loop-inf", br)
    assert cand.metric == 0.0
    assert cand.tests_failed >= 1


# ---------------------------------------------------------------------------
# run_benchmark_tournament
# ---------------------------------------------------------------------------
def test_run_benchmark_tournament_elects_highest_mean_score() -> None:
    benchmarks = {
        "low": _make_result(_make_task("t1", score=0.60, baseline=0.55)),
        "mid": _make_result(_make_task("t1", score=0.75, baseline=0.55)),
        "high": _make_result(_make_task("t1", score=0.90, baseline=0.55)),
    }
    outcome = run_benchmark_tournament(benchmarks)
    assert outcome.has_winner is True
    assert outcome.winner_loop_id == "high"
    assert sorted(outcome.rejected_loop_ids()) == ["low", "mid"]


def test_run_benchmark_tournament_disqualifies_regressors() -> None:
    """Regressed candidates must never win, even with higher raw mean_score."""
    benchmarks = {
        "regressor": _make_result(
            _make_task("t1", score=0.99, baseline=0.50),  # +0.49 ok
            _make_task("t2", score=0.05, baseline=0.80),  # -0.75 regression
        ),
        "steady": _make_result(
            _make_task("t1", score=0.72, baseline=0.50),
            _make_task("t2", score=0.81, baseline=0.80),
        ),
    }
    outcome = run_benchmark_tournament(benchmarks)
    assert outcome.winner_loop_id == "steady"
    # The regressor should still appear in scores but ranked last.
    assert outcome.tournament.scores["regressor"] == float("-inf")


def test_run_benchmark_tournament_patch_refs_propagate() -> None:
    benchmarks = {
        "alpha": _make_result(_make_task("t1", score=0.9, baseline=0.5)),
        "beta": _make_result(_make_task("t1", score=0.7, baseline=0.5)),
    }
    refs = {"alpha": "wt/alpha@deadbeef", "beta": "wt/beta@cafe"}
    outcome = run_benchmark_tournament(benchmarks, patch_refs=refs)
    assert outcome.tournament.winner is not None
    assert outcome.tournament.winner.patch_ref == "wt/alpha@deadbeef"


def test_run_benchmark_tournament_empty_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        run_benchmark_tournament({})


def test_run_benchmark_tournament_direction_minimize_flips_ranking() -> None:
    """Explicit MINIMIZE direction selects the LOWEST mean_score.

    Note: ``BenchmarkResult`` regression semantics is always "higher is
    better" (scores below baseline regress). A MINIMIZE-direction caller
    is expected to have already flipped sign on the raw metric at
    manifest-write time (e.g. store ``-latency_ms`` as score). In that
    world, ``score=10.0`` > ``baseline=5.0`` is NOT a regression; and
    the MINIMIZE direction tells the tournament that lower is better
    among non-regressed candidates. Testing this path here guards
    against accidental direction-flip bugs in the wrapper.
    """
    benchmarks = {
        "fast": _make_result(_make_task("t1", score=10.0, baseline=5.0)),
        "slow": _make_result(_make_task("t1", score=40.0, baseline=5.0)),
    }
    # Neither regresses (both above baseline=5). MINIMIZE picks the
    # lower metric among non-regressed candidates.
    outcome = run_benchmark_tournament(benchmarks, direction=DIRECTION_MINIMIZE)
    assert outcome.winner_loop_id == "fast"


def test_run_benchmark_tournament_deterministic_tiebreak_by_loop_id() -> None:
    """Two candidates with identical scores → lexicographic smallest wins."""
    br_a = _make_result(_make_task("t1", score=0.8, baseline=0.5))
    br_b = _make_result(_make_task("t1", score=0.8, baseline=0.5))
    benchmarks = {"z-loop": br_a, "a-loop": br_b}
    outcome = run_benchmark_tournament(benchmarks)
    # Tiebreak is loop_id asc after score desc.
    assert outcome.winner_loop_id == "a-loop"


def test_run_benchmark_tournament_secondary_metrics_break_ties_in_favor_of_faster() -> None:
    """Between equal mean_scores, the faster candidate wins via neg_work_latency."""
    benchmarks = {
        "fast": _make_result(
            _make_task("t1", score=0.80, baseline=0.50, work_ms=10.0),
        ),
        "slow": _make_result(
            _make_task("t1", score=0.80, baseline=0.50, work_ms=500.0),
        ),
    }
    outcome = run_benchmark_tournament(benchmarks)
    # loop_id tiebreak would pick "fast" lexically, but more importantly
    # the secondary metric neg_work_latency_ms is 10x more advantageous
    # for "fast", so fast wins via score margin.
    assert outcome.winner_loop_id == "fast"
    fast_score = outcome.tournament.scores["fast"]
    slow_score = outcome.tournament.scores["slow"]
    # fast_score - slow_score should reflect the 490ms latency differential
    assert fast_score - slow_score == pytest.approx(490.0)


# ---------------------------------------------------------------------------
# ReplayTournamentResult API
# ---------------------------------------------------------------------------
def test_replay_tournament_result_all_regressions_no_winner() -> None:
    """If every candidate regressed, winner is None (scorer disqualified all)."""
    benchmarks = {
        "a": _make_result(_make_task("t1", score=0.01, baseline=0.9)),
        "b": _make_result(_make_task("t1", score=0.02, baseline=0.9)),
    }
    outcome = run_benchmark_tournament(benchmarks)
    assert outcome.has_winner is False
    assert outcome.winner_loop_id is None
    # Both should appear in rejected_loop_ids.
    assert set(outcome.rejected_loop_ids()) == {"a", "b"}


def test_replay_tournament_result_to_dict_roundtrip() -> None:
    benchmarks = {
        "a": _make_result(_make_task("t1", score=0.85, baseline=0.8)),
        "b": _make_result(_make_task("t1", score=0.75, baseline=0.8)),
    }
    outcome = run_benchmark_tournament(benchmarks, patch_refs={"a": "ref-a"})
    d = outcome.to_dict()
    assert d["winner_loop_id"] == "a"
    assert "b" in d["rejected_loop_ids"]
    assert "scores" in d
    assert set(d["benchmarks"].keys()) == {"a", "b"}
    # The nested benchmark dict must contain the aggregated summary.
    assert "summary" in d["benchmarks"]["a"]


def test_replay_tournament_result_scores_include_all_loops() -> None:
    benchmarks = {
        "a": _make_result(_make_task("t1", score=0.85, baseline=0.8)),
        "b": _make_result(_make_task("t1", score=0.75, baseline=0.8)),
        "c": _make_result(_make_task("t1", score=0.90, baseline=0.8)),
    }
    outcome = run_benchmark_tournament(benchmarks)
    assert set(outcome.tournament.scores.keys()) == {"a", "b", "c"}
