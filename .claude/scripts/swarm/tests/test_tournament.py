"""PLAN-017 Phase 2 tests — tournament best-of-N selector."""

from __future__ import annotations

import pytest

from ..tournament import (
    DIRECTION_MAXIMIZE,
    DIRECTION_MINIMIZE,
    Candidate,
    ScoreWeights,
    Tournament,
    score_candidate,
)


# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------


def test_score_regression_is_negative_infinity() -> None:
    cand = Candidate(loop_id="L1", metric=1.0, tests_passed=10, tests_failed=1)
    assert score_candidate(cand) == float("-inf")


def test_score_minimize_inverts_metric() -> None:
    low = Candidate(loop_id="L1", metric=1.0, tests_passed=0)
    high = Candidate(loop_id="L2", metric=10.0, tests_passed=0)
    assert score_candidate(low, direction=DIRECTION_MINIMIZE) > score_candidate(
        high, direction=DIRECTION_MINIMIZE
    )


def test_score_maximize_preserves_metric() -> None:
    low = Candidate(loop_id="L1", metric=1.0)
    high = Candidate(loop_id="L2", metric=10.0)
    assert score_candidate(high, direction=DIRECTION_MAXIMIZE) > score_candidate(
        low, direction=DIRECTION_MAXIMIZE
    )


def test_score_bad_direction_raises() -> None:
    with pytest.raises(ValueError, match="direction"):
        score_candidate(Candidate(loop_id="L1", metric=1.0), direction="bogus")


def test_score_respects_tests_passed_weight() -> None:
    a = Candidate(loop_id="L1", metric=1.0, tests_passed=100)
    b = Candidate(loop_id="L2", metric=1.0, tests_passed=0)
    assert score_candidate(a, direction=DIRECTION_MINIMIZE) > score_candidate(
        b, direction=DIRECTION_MINIMIZE
    )


def test_score_respects_loc_delta_penalty() -> None:
    small = Candidate(loop_id="L1", metric=1.0, loc_delta=10)
    huge = Candidate(loop_id="L2", metric=1.0, loc_delta=100000)
    assert score_candidate(small, direction=DIRECTION_MINIMIZE) > score_candidate(
        huge, direction=DIRECTION_MINIMIZE
    )


def test_score_includes_secondary_metrics() -> None:
    plain = Candidate(loop_id="L1", metric=1.0)
    bonus = Candidate(loop_id="L2", metric=1.0, secondary_metrics={"bonus": 50.0})
    assert score_candidate(bonus, direction=DIRECTION_MINIMIZE) > score_candidate(
        plain, direction=DIRECTION_MINIMIZE
    )


def test_score_weights_reject_negative() -> None:
    with pytest.raises(ValueError, match="metric"):
        ScoreWeights(metric=-1.0)


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------


def test_tournament_empty_returns_no_winner() -> None:
    result = Tournament(candidates=[]).run()
    assert result.winner is None
    assert result.rejected == []
    assert result.scores == {}
    assert result.is_decisive() is False


def test_tournament_single_candidate_wins() -> None:
    only = Candidate(loop_id="L1", metric=1.0, tests_passed=5)
    result = Tournament(candidates=[only]).run()
    assert result.winner is only
    assert result.rejected == []
    assert result.is_decisive() is True


def test_tournament_best_metric_wins_minimize() -> None:
    cands = [
        Candidate(loop_id="L1", metric=10.0, tests_passed=5),
        Candidate(loop_id="L2", metric=1.0, tests_passed=5),
        Candidate(loop_id="L3", metric=5.0, tests_passed=5),
    ]
    result = Tournament(candidates=cands, direction=DIRECTION_MINIMIZE).run()
    assert result.winner is not None
    assert result.winner.loop_id == "L2"
    # Rejected in score-descending order, tie-broken by loop_id asc.
    assert [c.loop_id for c in result.rejected] == ["L3", "L1"]


def test_tournament_best_metric_wins_maximize() -> None:
    cands = [
        Candidate(loop_id="L1", metric=10.0),
        Candidate(loop_id="L2", metric=1.0),
    ]
    result = Tournament(candidates=cands, direction=DIRECTION_MAXIMIZE).run()
    assert result.winner is not None
    assert result.winner.loop_id == "L1"


def test_tournament_regression_disqualifies_candidate() -> None:
    cands = [
        Candidate(loop_id="L1", metric=100.0, tests_passed=10),
        Candidate(loop_id="L2", metric=1.0, tests_passed=10, tests_failed=1),
    ]
    result = Tournament(candidates=cands, direction=DIRECTION_MINIMIZE).run()
    # L2 has the better metric but regression disqualifies it.
    assert result.winner is not None
    assert result.winner.loop_id == "L1"


def test_tournament_all_regressed_returns_no_winner() -> None:
    cands = [
        Candidate(loop_id="L1", metric=1.0, tests_failed=1),
        Candidate(loop_id="L2", metric=2.0, tests_failed=1),
    ]
    result = Tournament(candidates=cands, direction=DIRECTION_MINIMIZE).run()
    assert result.winner is None
    assert len(result.rejected) == 2
    assert result.is_decisive() is False


def test_tournament_duplicate_loop_ids_rejected() -> None:
    cands = [
        Candidate(loop_id="L1", metric=1.0),
        Candidate(loop_id="L1", metric=2.0),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        Tournament(candidates=cands)


def test_tournament_tiebreaker_loop_id_ascending() -> None:
    # Two candidates with identical score — loop_id ascending wins.
    cands = [
        Candidate(loop_id="L2", metric=1.0, tests_passed=5),
        Candidate(loop_id="L1", metric=1.0, tests_passed=5),
    ]
    result = Tournament(candidates=cands, direction=DIRECTION_MINIMIZE).run()
    assert result.winner is not None
    assert result.winner.loop_id == "L1"


def test_tournament_run_is_idempotent() -> None:
    cands = [
        Candidate(loop_id="L1", metric=5.0, tests_passed=5),
        Candidate(loop_id="L2", metric=1.0, tests_passed=5),
    ]
    t = Tournament(candidates=cands, direction=DIRECTION_MINIMIZE)
    first = t.run()
    second = t.run()
    assert first.winner is not None and second.winner is not None
    assert first.winner.loop_id == second.winner.loop_id
    assert first.scores == second.scores


def test_tournament_custom_weights_applied() -> None:
    # With zero weight on tests_passed, ties resolve by metric alone.
    cands = [
        Candidate(loop_id="L1", metric=1.0, tests_passed=0),
        Candidate(loop_id="L2", metric=1.0, tests_passed=100),
    ]
    t = Tournament(
        candidates=cands,
        direction=DIRECTION_MINIMIZE,
        weights=ScoreWeights(metric=1.0, tests_passed=0.0, tests_failed_penalty=0.0, loc_delta_penalty=0.0),
    )
    result = t.run()
    # Tied scores; tiebreaker on loop_id asc → L1.
    assert result.winner is not None
    assert result.winner.loop_id == "L1"


def test_tournament_bad_direction_at_construct_raises() -> None:
    with pytest.raises(ValueError, match="direction"):
        Tournament(candidates=[], direction="bogus")
