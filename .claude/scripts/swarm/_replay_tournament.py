"""PLAN-050 Phase 7 final — replay-tournament wiring.

Bridges ``_benchmark_replay.BenchmarkResult`` → ``tournament.Candidate``
→ ``tournament.Tournament``. This module is the glue that lets the
coordinator evaluate N autonomous-loop outputs against a shared
benchmark manifest, convert each loop's aggregate into a Candidate,
and elect a winner via the existing deterministic scorer.

## Contract

- **Inputs:** one ``BenchmarkResult`` per loop_id, produced by running
  the same manifest against each loop's output (the caller owns the
  per-loop ``task_fn`` — typically a closure over the patched code
  or worktree from that loop).
- **Output:** a ``TournamentResult`` whose ``winner.patch_ref`` points
  at the loop_id's patched worktree / SHA.

## Regression-gate fast path

If a loop's ``BenchmarkResult.pass_regression_gate()`` is False (any
task regressed beyond tolerance), the loop's Candidate is constructed
with ``tests_failed=1`` so the scorer disqualifies it (score=-inf).
This keeps the C4 invariant "regressed patch never wins" regardless
of raw mean_score — a local win on one task cannot paper over a
regression on another.

## Secondary metrics

The scorer weights ``Candidate.secondary_metrics`` by 1.0 per value.
We map them so the tournament considers speed + improvement count
alongside raw score:

- ``benchmark.n_improved``       — contributes positively
- ``benchmark.mean_work_latency_ms`` — negated so slower → lower score
- ``benchmark.n_regressed``      — negated × large factor (redundant
  with the disqualification above, but useful for score ordering
  among also-qualified candidates)

The caller can override the mapping via ``secondary_mapper`` if the
default shape doesn't match the plan's optimization axes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from ._benchmark_replay import BenchmarkResult
from .tournament import (
    Candidate,
    DIRECTION_MAXIMIZE,
    ScoreWeights,
    Tournament,
    TournamentResult,
)


# Default factor scaling regressed-task count into secondary_metrics.
# Redundant with the -inf disqualification path, but kept positive so
# tournaments including no-regression candidates still rank by severity.
_REGRESSED_PENALTY_FACTOR = -100.0


@dataclass
class ReplayTournamentResult:
    """Wrap a TournamentResult with the originating BenchmarkResults.

    Carrying both sides of the bridge lets the coordinator emit audit
    events with per-loop metrics + promotion decision in a single
    payload.
    """

    tournament: TournamentResult
    benchmarks: Dict[str, BenchmarkResult]

    @property
    def winner_loop_id(self) -> Optional[str]:
        w = self.tournament.winner
        return None if w is None else w.loop_id

    @property
    def has_winner(self) -> bool:
        return self.tournament.is_decisive()

    def rejected_loop_ids(self) -> list:
        return [c.loop_id for c in self.tournament.rejected]

    def to_dict(self) -> dict:
        return {
            "winner_loop_id": self.winner_loop_id,
            "rejected_loop_ids": self.rejected_loop_ids(),
            "scores": dict(self.tournament.scores),
            "benchmarks": {
                lid: br.to_dict() for lid, br in self.benchmarks.items()
            },
        }


# ---------------------------------------------------------------------------
# Default secondary-metrics mapper
# ---------------------------------------------------------------------------
def _default_secondary_mapper(br: BenchmarkResult) -> Dict[str, float]:
    """Map benchmark aggregates into Candidate.secondary_metrics.

    Convention: higher is better after applying signs. Scorer then sums
    these with weight 1.0 in ``score_candidate``.
    """
    return {
        "n_improved": float(br.n_improved),
        # Negate latency so a slower benchmark produces a LOWER score.
        "neg_work_latency_ms": -float(br.mean_work_latency_ms),
        # Signed penalty on regressions — large factor so this
        # dominates small mean-score differences when comparing two
        # borderline candidates. (-inf disqualification is a
        # stricter gate; this is a soft ranking signal.)
        "regressed_penalty": _REGRESSED_PENALTY_FACTOR * float(br.n_regressed),
    }


# ---------------------------------------------------------------------------
# Bridge: BenchmarkResult -> Candidate
# ---------------------------------------------------------------------------
def benchmark_to_candidate(
    loop_id: str,
    br: BenchmarkResult,
    *,
    patch_ref: Optional[str] = None,
    secondary_mapper: Optional[
        Callable[[BenchmarkResult], Dict[str, float]]
    ] = None,
) -> Candidate:
    """Convert one loop's BenchmarkResult into a tournament Candidate.

    The Candidate's primary ``metric`` is the benchmark's mean_score.
    ``tests_failed`` is set to ``n_regressed`` so the scorer
    disqualifies any candidate with a regression (via -inf path).
    ``tests_passed`` reflects the non-regressed task count.

    Raises ``ValueError`` for empty loop_id or non-finite score.
    """
    if not loop_id or not isinstance(loop_id, str):
        raise ValueError("loop_id must be a non-empty string")

    mean_score = float(br.mean_score)
    # NaN / inf from a pathological task callable → treat as catastrophic.
    # We don't want a bogus NaN to silently become the top candidate.
    if mean_score != mean_score or mean_score in (float("inf"), float("-inf")):
        mean_score = 0.0
        regressions = max(br.n_regressed, 1)
    else:
        regressions = br.n_regressed

    mapper = secondary_mapper or _default_secondary_mapper
    secondary = mapper(br)

    # Tests-passed semantics: tasks that did NOT regress (strict).
    passed = br.n_tasks - regressions

    return Candidate(
        loop_id=loop_id,
        metric=mean_score,
        secondary_metrics=secondary,
        tests_passed=max(passed, 0),
        tests_failed=regressions,
        loc_delta=0,  # LoC delta is out of scope for benchmark-based ranking
        patch_ref=patch_ref,
    )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------
def run_benchmark_tournament(
    benchmarks: Dict[str, BenchmarkResult],
    *,
    patch_refs: Optional[Dict[str, str]] = None,
    direction: str = DIRECTION_MAXIMIZE,
    weights: Optional[ScoreWeights] = None,
    secondary_mapper: Optional[
        Callable[[BenchmarkResult], Dict[str, float]]
    ] = None,
) -> ReplayTournamentResult:
    """Run the best-of-N tournament over per-loop BenchmarkResults.

    Direction defaults to MAXIMIZE because benchmark scores are
    higher-is-better by convention — the opposite of tournament's
    MINIMIZE default (kept for raw-metric minimization use cases).

    Raises:
        ValueError — if ``benchmarks`` is empty or any loop_id is empty.
    """
    if not benchmarks:
        raise ValueError("benchmarks must be non-empty")

    patch_refs = patch_refs or {}
    candidates = [
        benchmark_to_candidate(
            loop_id=lid,
            br=br,
            patch_ref=patch_refs.get(lid),
            secondary_mapper=secondary_mapper,
        )
        for lid, br in benchmarks.items()
    ]

    tournament = Tournament(
        candidates=candidates,
        direction=direction,
        weights=weights or ScoreWeights(),
    )
    result = tournament.run()
    return ReplayTournamentResult(
        tournament=result,
        benchmarks=dict(benchmarks),
    )
