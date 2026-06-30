"""PLAN-050 Phase 7b (C4) — benchmark replay harness tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from .._benchmark_replay import (
    BenchmarkManifestError,
    BenchmarkResult,
    SCORE_DEFAULT_TOLERANCE,
    TaskResult,
    load_manifest,
    replay,
)


MINIMAL_MANIFEST = {
    "manifest_version": 1,
    "baseline_sha": "deadbeef",
    "tasks": [
        {"id": "t-01", "input": {"n": 10}, "baseline_score": 0.80},
        {"id": "t-02", "input": {"n": 20}, "baseline_score": 0.60, "regression_tolerance": 0.05},
    ],
}


# -----------------------------------------------------------------------
# Manifest loader
# -----------------------------------------------------------------------
def test_load_manifest_happy(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(MINIMAL_MANIFEST))
    loaded = load_manifest(path)
    assert loaded["manifest_version"] == 1
    assert len(loaded["tasks"]) == 2


def test_load_manifest_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json")
    with pytest.raises(BenchmarkManifestError, match="invalid JSON"):
        load_manifest(path)


def test_load_manifest_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkManifestError, match="cannot read"):
        load_manifest(tmp_path / "nope.json")


def test_load_manifest_wrong_version(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"manifest_version": 2, "tasks": [{"id": "x", "baseline_score": 0.5}]}))
    with pytest.raises(BenchmarkManifestError, match="manifest_version"):
        load_manifest(path)


def test_load_manifest_empty_tasks(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"manifest_version": 1, "tasks": []}))
    with pytest.raises(BenchmarkManifestError, match="non-empty"):
        load_manifest(path)


def test_load_manifest_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({
        "manifest_version": 1,
        "tasks": [
            {"id": "dup", "baseline_score": 0.5},
            {"id": "dup", "baseline_score": 0.6},
        ],
    }))
    with pytest.raises(BenchmarkManifestError, match="duplicated"):
        load_manifest(path)


def test_load_manifest_missing_baseline(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({
        "manifest_version": 1,
        "tasks": [{"id": "t1"}],
    }))
    with pytest.raises(BenchmarkManifestError, match="baseline_score"):
        load_manifest(path)


def test_load_manifest_non_numeric_baseline(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({
        "manifest_version": 1,
        "tasks": [{"id": "t1", "baseline_score": "not-a-number"}],
    }))
    with pytest.raises(BenchmarkManifestError, match="numeric"):
        load_manifest(path)


# -----------------------------------------------------------------------
# Replay driver
# -----------------------------------------------------------------------
def test_replay_records_scores() -> None:
    result = replay(MINIMAL_MANIFEST, task_fn=lambda inp: 0.90)
    assert result.n_tasks == 2
    for t in result.tasks:
        assert t.score == 0.90
    assert result.mean_score == 0.90


def test_replay_detects_regression() -> None:
    # Return below baseline - tolerance.
    result = replay(MINIMAL_MANIFEST, task_fn=lambda inp: 0.10)
    assert result.n_regressed == 2
    assert not result.pass_regression_gate()


def test_replay_detects_improvement() -> None:
    result = replay(MINIMAL_MANIFEST, task_fn=lambda inp: 0.99)
    assert result.n_improved == 2
    assert result.pass_regression_gate()


def test_replay_tolerance_per_task() -> None:
    # t-02 has tolerance 0.05, baseline 0.60 → scores >= 0.55 pass.
    # t-01 has default tolerance 0.02, baseline 0.80 → scores >= 0.78 pass.
    calls = {"count": 0}

    def task_fn(inp: dict) -> float:
        calls["count"] += 1
        # First call returns 0.79 (passes t-01); second returns 0.57 (passes t-02).
        return 0.79 if calls["count"] == 1 else 0.57

    result = replay(MINIMAL_MANIFEST, task_fn=task_fn)
    assert result.n_regressed == 0
    assert result.pass_regression_gate()


def test_replay_task_exception_is_recorded() -> None:
    def failing(inp: dict) -> float:
        raise ValueError("deterministic test failure")

    result = replay(MINIMAL_MANIFEST, task_fn=failing)
    assert result.n_regressed == 2  # Failures are regressions (score=0).
    for t in result.tasks:
        assert t.error is not None
        assert "ValueError" in t.error
        assert t.score == 0.0


def test_replay_measures_work_latency() -> None:
    import time

    def slow(inp: dict) -> float:
        time.sleep(0.01)
        return 0.90

    result = replay(MINIMAL_MANIFEST, task_fn=slow)
    assert result.mean_work_latency_ms >= 8.0  # Allow some jitter.
    assert result.mean_git_overhead_ms == 0.0  # No pool → no overhead.


def test_replay_measures_git_overhead_when_pool_used() -> None:
    """Stub pool acquire/release with measurable delay."""

    class FakePool:
        def __init__(self) -> None:
            self.acquired: list = []
            self.released: list = []

        def acquire(self, task_id: str) -> Path:
            import time
            time.sleep(0.005)
            p = Path(f"/tmp/fake-wt-{task_id}")
            self.acquired.append(p)
            return p

        def release(self, path: Path) -> None:
            import time
            time.sleep(0.005)
            self.released.append(path)

    pool = FakePool()
    result = replay(MINIMAL_MANIFEST, task_fn=lambda inp: 0.90, pool=pool)
    # Every task acquired + released once.
    assert len(pool.acquired) == 2
    assert len(pool.released) == 2
    # Overhead should be measurable but reported separately from work latency.
    assert result.mean_git_overhead_ms >= 8.0
    assert all(t.git_overhead_ms > 0.0 for t in result.tasks)


# -----------------------------------------------------------------------
# TaskResult / BenchmarkResult dataclass sanity
# -----------------------------------------------------------------------
def test_task_result_regressed_flag() -> None:
    tr = TaskResult(
        task_id="x",
        score=0.50,
        baseline_score=0.80,
        regression_tolerance=0.02,
        work_latency_ms=10.0,
    )
    assert tr.regressed is True
    assert tr.improved is False


def test_task_result_improved_flag() -> None:
    tr = TaskResult(
        task_id="x",
        score=0.99,
        baseline_score=0.80,
        regression_tolerance=0.02,
        work_latency_ms=10.0,
    )
    assert tr.improved is True
    assert tr.regressed is False


def test_task_result_within_tolerance_neither() -> None:
    tr = TaskResult(
        task_id="x",
        score=0.80,
        baseline_score=0.80,
        regression_tolerance=0.02,
        work_latency_ms=10.0,
    )
    assert tr.regressed is False
    assert tr.improved is False


def test_benchmark_result_to_dict_has_summary() -> None:
    result = replay(MINIMAL_MANIFEST, task_fn=lambda inp: 0.90)
    payload = result.to_dict()
    assert "summary" in payload
    assert payload["summary"]["n_tasks"] == 2
    assert payload["summary"]["passes_regression_gate"] is True
    assert len(payload["tasks"]) == 2


def test_default_tolerance_exported() -> None:
    assert SCORE_DEFAULT_TOLERANCE == 0.02


def test_empty_tasks_mean_is_zero() -> None:
    r = BenchmarkResult(manifest_version=1, baseline_sha="x")
    assert r.mean_score == 0.0
    assert r.mean_work_latency_ms == 0.0
    assert r.mean_git_overhead_ms == 0.0
