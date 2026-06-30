"""PLAN-017 Phase 2 — tournament best-of-N selection.

Each loop produces a ``Candidate`` patch. The scorer evaluates per
metric (test pass count, LoC delta, benchmark metric). The best-
scoring candidate is "promoted" (applied to main); others are saved
as ``.rejected`` in the worktree history.

Opt-in integration with the PLAN-032 tournament framework
(`.claude/scripts/tournament/`) for learned weighting is deferred to
PLAN-017 follow-up — this scaffold ships a simple deterministic
weighted-sum scorer the coordinator can consume synchronously.

ADR-049b decision (best-final-metric / Bayesian / multi-armed-bandit)
defers to follow-up; this module implements *best-final-metric* only,
which is Phase 2's simple-first algorithm per the plan.
"""

from __future__ import annotations

import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Dict, List, Optional, Tuple

# PLAN-113 WIRE-AUDIT: best-effort import of audit_emit for tournament events.
_HOOKS_DIR = str(_Path(__file__).resolve().parent.parent.parent / "hooks")
if _HOOKS_DIR not in _sys.path:
    _sys.path.insert(0, _HOOKS_DIR)

try:
    from _lib import audit_emit as _audit_emit  # type: ignore[import]
    _AUDIT_EMIT_OK = True
except Exception:
    _audit_emit = None  # type: ignore[assignment]
    _AUDIT_EMIT_OK = False


def _safe_emit(fn_name: str, **kwargs: object) -> None:
    """Best-effort emit via audit_emit — never raises."""
    if not _AUDIT_EMIT_OK or _audit_emit is None:
        return
    try:
        fn = getattr(_audit_emit, fn_name, None)
        if fn is not None:
            fn(**kwargs)
    except Exception:  # pragma: no cover
        pass


# Direction enum (same convention as loop_runner.py — plain strings).
DIRECTION_MINIMIZE = "minimize"
DIRECTION_MAXIMIZE = "maximize"
_VALID_DIRECTIONS = {DIRECTION_MINIMIZE, DIRECTION_MAXIMIZE}


@dataclass
class Candidate:
    """One loop's submitted patch + measured metrics.

    ``metric`` is the primary benchmark result; ``secondary_metrics``
    is an optional dict of auxiliary scalars (test pass count, LoC
    delta, wall-clock ms, etc.) the scorer weights.
    """

    loop_id: str
    metric: float
    secondary_metrics: Dict[str, float] = field(default_factory=dict)
    tests_passed: int = 0
    tests_failed: int = 0
    loc_delta: int = 0
    patch_ref: Optional[str] = None  # e.g. git hash / worktree path

    @property
    def has_regressions(self) -> bool:
        return self.tests_failed > 0


@dataclass
class ScoreWeights:
    """Scorer weights. Tunable via constructor; defaults match the
    plan's "simple first" intent.

    Weights are relative; any positive number works. Zero disables a
    factor entirely.
    """

    metric: float = 1.0
    tests_passed: float = 0.1
    tests_failed_penalty: float = 10.0
    loc_delta_penalty: float = 0.001

    def __post_init__(self) -> None:
        for name, value in (
            ("metric", self.metric),
            ("tests_passed", self.tests_passed),
            ("tests_failed_penalty", self.tests_failed_penalty),
            ("loc_delta_penalty", self.loc_delta_penalty),
        ):
            if value < 0:
                raise ValueError(f"{name} weight must be >= 0")


def score_candidate(
    cand: Candidate,
    *,
    direction: str = DIRECTION_MINIMIZE,
    weights: Optional[ScoreWeights] = None,
) -> float:
    """Deterministic scalar score for one candidate.

    Higher is always better (regardless of direction — we flip signs
    internally for minimize). The returned value is comparable only
    within one tournament run; cross-tournament comparisons require
    shared weights + normalization.

    Returns ``-inf`` for candidates with test regressions — they are
    disqualified. This keeps the sort stable while guaranteeing a
    regressed patch never wins.
    """

    if direction not in _VALID_DIRECTIONS:
        raise ValueError(
            f"direction must be in {sorted(_VALID_DIRECTIONS)}; got {direction!r}"
        )
    w = weights or ScoreWeights()

    if cand.has_regressions:
        return float("-inf")

    # Metric orientation: for minimize, invert so lower metric → higher score.
    metric_component = (
        -cand.metric if direction == DIRECTION_MINIMIZE else cand.metric
    )
    score = w.metric * metric_component
    score += w.tests_passed * cand.tests_passed
    score -= w.loc_delta_penalty * max(cand.loc_delta, 0)

    # Secondary metrics are summed with weight 1.0 unless the caller
    # extended ScoreWeights — intentional defer until real benchmark
    # shapes inform the weighting schema.
    for value in cand.secondary_metrics.values():
        score += value

    return score


@dataclass
class TournamentResult:
    """Outcome of ``Tournament.run``.

    ``winner`` is None iff every candidate had regressions (all were
    disqualified). ``rejected`` lists the losers in deterministic
    rank order (highest-scoring losers first).
    """

    winner: Optional[Candidate]
    rejected: List[Candidate]
    scores: Dict[str, float]

    def is_decisive(self) -> bool:
        return self.winner is not None


@dataclass
class Tournament:
    """Best-of-N selector.

    Construct with a list of ``Candidate`` + direction + optional
    weights. Call ``run()`` once; multiple ``run()`` calls return the
    same result (deterministic).
    """

    candidates: List[Candidate]
    direction: str = DIRECTION_MINIMIZE
    weights: ScoreWeights = field(default_factory=ScoreWeights)

    def __post_init__(self) -> None:
        if self.direction not in _VALID_DIRECTIONS:
            raise ValueError(
                f"direction must be in {sorted(_VALID_DIRECTIONS)}; got {self.direction!r}"
            )
        # Detect duplicate loop_ids — the coordinator shouldn't produce
        # them, but fail loud rather than silently dedup.
        ids = [c.loop_id for c in self.candidates]
        if len(set(ids)) != len(ids):
            dups = sorted({lid for lid in ids if ids.count(lid) > 1})
            raise ValueError(f"duplicate loop_ids in candidates: {dups}")

    def run(
        self,
        swarm_id: str = "",
        session_id: str = "",
        project: str = "",
    ) -> TournamentResult:
        """Run the tournament and return the result.

        Optional ``swarm_id``, ``session_id``, ``project`` are passed
        through to audit-emit calls for correlation (PLAN-113 WIRE-AUDIT).
        """
        # Emit run-started event.
        _safe_emit(
            "emit_tournament_run_started",
            swarm_id=swarm_id,
            candidate_count=len(self.candidates),
            direction=self.direction,
            session_id=session_id,
            project=project,
        )

        if not self.candidates:
            _safe_emit(
                "emit_tournament_aborted",
                swarm_id=swarm_id,
                reason="no_candidates",
                session_id=session_id,
                project=project,
            )
            return TournamentResult(winner=None, rejected=[], scores={})

        scored: List[Tuple[float, Candidate]] = []
        for cand in self.candidates:
            s = score_candidate(cand, direction=self.direction, weights=self.weights)
            scored.append((s, cand))
            # Emit per-candidate score.
            _safe_emit(
                "emit_tournament_task_scored",
                swarm_id=swarm_id,
                loop_id=cand.loop_id,
                score_bps=int(s * 1000) if s > float("-inf") else -999999,
                tests_passed=cand.tests_passed,
                tests_failed=cand.tests_failed,
                session_id=session_id,
                project=project,
            )

        # Sort by score desc, then by loop_id asc (tiebreaker → deterministic).
        scored.sort(key=lambda item: (-item[0], item[1].loop_id))

        scores: Dict[str, float] = {c.loop_id: s for s, c in scored}

        # Winner = highest-scoring non-disqualified candidate.
        winner: Optional[Candidate] = None
        rejected: List[Candidate] = []
        for score, cand in scored:
            if winner is None and score > float("-inf"):
                winner = cand
            else:
                rejected.append(cand)

        # Emit run-completed event.
        _safe_emit(
            "emit_tournament_run_completed",
            swarm_id=swarm_id,
            winner_loop_id=winner.loop_id if winner else "",
            rejected_count=len(rejected),
            decisive=winner is not None,
            session_id=session_id,
            project=project,
        )

        return TournamentResult(winner=winner, rejected=rejected, scores=scores)
