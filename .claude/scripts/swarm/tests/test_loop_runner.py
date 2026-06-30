"""PLAN-017 Phase 1 tests — loop runner wrapper."""

from __future__ import annotations

from typing import List

import pytest

from ..coordinator import LoopState
from ..loop_runner import (
    DIRECTION_MAXIMIZE,
    DIRECTION_MINIMIZE,
    IterationResult,
    LoopRunner,
)


def _stub_iterate_kept(metrics: List[float]):
    """Return an iterate callable that yields from ``metrics`` + marks kept."""

    it = iter(metrics)

    def _iterate(state: LoopState) -> IterationResult:
        return IterationResult(
            metric=next(it),
            tokens_delta=100,
            files_touched=[f"f{state.iteration}.py"],
            kept=True,
        )

    return _iterate


def test_loop_runner_rejects_bad_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        LoopRunner(
            loop_id="L1",
            goal="g",
            max_iterations=5,
            max_strikes=3,
            budget_tokens=1000,
            direction="bogus",
            iterate=_stub_iterate_kept([1.0]),
        )


def test_loop_runner_step_happy_path_minimize() -> None:
    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_stub_iterate_kept([10.0, 8.0, 9.0]),
    )
    for _ in range(3):
        runner.step()
    assert runner.state.iteration == 3
    assert runner.state.tokens_consumed == 300
    assert runner.state.kept_changes == 3
    # Best for minimize == min kept metric.
    assert runner.best_metric == pytest.approx(8.0)


def test_loop_runner_step_maximize_best_tracking() -> None:
    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MAXIMIZE,
        iterate=_stub_iterate_kept([1.0, 5.0, 3.0]),
    )
    for _ in range(3):
        runner.step()
    assert runner.best_metric == pytest.approx(5.0)


def test_loop_runner_strike_trips_errored_status() -> None:
    def _always_error(state: LoopState) -> IterationResult:
        return IterationResult(metric=0.0, tokens_delta=50, error="boom")

    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=2,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_always_error,
    )
    runner.step()
    runner.step()
    assert runner.state.strikes == 2
    assert runner.state.status == "errored"


def test_loop_runner_refuses_step_after_killed() -> None:
    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_stub_iterate_kept([1.0]),
    )
    runner.mark_killed("manual")
    assert runner.state.status == "killed"
    with pytest.raises(RuntimeError, match="cannot step"):
        runner.step()


def test_loop_runner_files_touched_dedup_preserves_order() -> None:
    seq = [
        IterationResult(metric=1.0, tokens_delta=10, files_touched=["a.py", "b.py"], kept=True),
        IterationResult(metric=1.0, tokens_delta=10, files_touched=["b.py", "c.py"], kept=True),
    ]
    it = iter(seq)

    def _iter(_state: LoopState) -> IterationResult:
        return next(it)

    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_iter,
    )
    runner.step()
    runner.step()
    assert runner.state.files_touched == ["a.py", "b.py", "c.py"]


def test_loop_runner_max_iterations_short_circuits() -> None:
    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=2,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_stub_iterate_kept([1.0, 2.0]),
    )
    runner.step()
    runner.step()
    result = runner.step()  # Should short-circuit.
    assert result.error == "max_iterations_reached"
    assert runner.state.status == "completed"


def test_loop_runner_mark_converged_transitions() -> None:
    runner = LoopRunner(
        loop_id="L1",
        goal="g",
        max_iterations=5,
        max_strikes=3,
        budget_tokens=1000,
        direction=DIRECTION_MINIMIZE,
        iterate=_stub_iterate_kept([1.0]),
    )
    runner.mark_converged()
    assert runner.state.status == "converged"
