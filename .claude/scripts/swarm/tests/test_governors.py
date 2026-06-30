"""PLAN-122 WS-2 tests — swarm fan-out governors (pure functions)."""

from __future__ import annotations

import pytest

from .. import _governors as g
from ..coordinator import MAX_PARALLEL_CEILING


# ---------------------------------------------------------------------------
# compute_dispatch_width — quota scaling + clamps
# ---------------------------------------------------------------------------


def test_width_zero_quota_returns_zero() -> None:
    assert g.compute_dispatch_width(0, n_loops_requested=4) == 0


def test_width_negative_quota_returns_zero() -> None:
    assert g.compute_dispatch_width(-50_000, n_loops_requested=4) == 0


def test_width_quota_below_one_reserve_returns_zero() -> None:
    # Quota cannot fund even a single per-loop reserve → wait for refill.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    assert g.compute_dispatch_width(reserve - 1, n_loops_requested=4) == 0


def test_width_partial_quota_funds_fewer_than_requested() -> None:
    # Quota funds exactly 2 reserves; 4 requested → clamp to 2.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    width = g.compute_dispatch_width(reserve * 2, n_loops_requested=4)
    assert width == 2


def test_width_full_quota_meets_request_below_ceiling() -> None:
    # Quota funds plenty; request (3) is the binding clamp.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    width = g.compute_dispatch_width(reserve * 100, n_loops_requested=3)
    assert width == 3


def test_width_clamps_to_parallel_ceiling() -> None:
    # Quota + request both exceed the ADR-051 ceiling → clamp to ceiling.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    width = g.compute_dispatch_width(reserve * 1000, n_loops_requested=50)
    assert width == MAX_PARALLEL_CEILING


def test_width_request_at_ceiling_is_honored_when_funded() -> None:
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    width = g.compute_dispatch_width(
        reserve * MAX_PARALLEL_CEILING, n_loops_requested=MAX_PARALLEL_CEILING
    )
    assert width == MAX_PARALLEL_CEILING


def test_width_n_loops_below_ceiling_is_the_binding_clamp() -> None:
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    # Funds 6, requests 1 → 1.
    assert g.compute_dispatch_width(reserve * 6, n_loops_requested=1) == 1


def test_width_zero_requested_returns_zero() -> None:
    assert g.compute_dispatch_width(10_000_000, n_loops_requested=0) == 0


def test_width_negative_requested_returns_zero() -> None:
    assert g.compute_dispatch_width(10_000_000, n_loops_requested=-3) == 0


def test_width_non_positive_ceiling_returns_zero() -> None:
    assert (
        g.compute_dispatch_width(10_000_000, n_loops_requested=4, max_parallel_ceiling=0)
        == 0
    )


def test_width_non_positive_reserve_falls_back_to_default() -> None:
    # A 0 reserve must not divide by zero; it falls back to the default.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    width = g.compute_dispatch_width(
        reserve * 2, n_loops_requested=4, per_loop_reserve_tokens=0
    )
    assert width == 2


def test_width_custom_reserve_changes_funded_count() -> None:
    # Smaller reserve → quota funds MORE loops (still clamped by request).
    width = g.compute_dispatch_width(
        100_000, n_loops_requested=8, per_loop_reserve_tokens=10_000
    )
    assert width == 8  # 100_000 // 10_000 = 10, clamped to request 8


def test_width_is_deterministic() -> None:
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    a = g.compute_dispatch_width(reserve * 5, n_loops_requested=6)
    b = g.compute_dispatch_width(reserve * 5, n_loops_requested=6)
    assert a == b == 5


def test_width_monotonic_non_decreasing_in_quota() -> None:
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    widths = [
        g.compute_dispatch_width(reserve * k, n_loops_requested=MAX_PARALLEL_CEILING)
        for k in range(0, MAX_PARALLEL_CEILING + 3)
    ]
    assert widths == sorted(widths)
    assert widths[0] == 0
    assert widths[-1] == MAX_PARALLEL_CEILING


# ---------------------------------------------------------------------------
# rate_backoff — return shape
# ---------------------------------------------------------------------------


def test_rate_backoff_returns_namedtuple_fields() -> None:
    rb = g.rate_backoff(0, 0, 1000, 1000, 0)
    assert isinstance(rb, g.RateBackoff)
    assert hasattr(rb, "backoff_after_ms")
    assert hasattr(rb, "reduced_width_factor")
    # NamedTuple is frozen — cannot reassign a field.
    with pytest.raises(AttributeError):
        rb.backoff_after_ms = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# rate_backoff — far from ceiling (light load)
# ---------------------------------------------------------------------------


def test_rate_backoff_far_from_ceiling_no_backoff_full_width() -> None:
    # 10% of ceiling, no 429s → no backoff, full width.
    rb = g.rate_backoff(100, 100, 1000, 1000, 0)
    assert rb.backoff_after_ms == 0
    assert rb.reduced_width_factor == 1.0


def test_rate_backoff_at_soft_knee_still_no_backoff() -> None:
    # Exactly at the soft knee → no backoff yet (knee is inclusive).
    itpm = int(g.RATE_SOFT_KNEE * 1000)
    rb = g.rate_backoff(itpm, 0, 1000, 1000, 0)
    assert rb.backoff_after_ms == 0
    assert rb.reduced_width_factor == 1.0


def test_rate_backoff_unmeasured_ceiling_is_zero_pressure() -> None:
    # Ceiling 0 == "unmeasured" → zero pressure, no backoff (no 429).
    rb = g.rate_backoff(999_999, 999_999, 0, 0, 0)
    assert rb.backoff_after_ms == 0
    assert rb.reduced_width_factor == 1.0


# ---------------------------------------------------------------------------
# rate_backoff — near / at / over ceiling
# ---------------------------------------------------------------------------


def test_rate_backoff_near_ceiling_backs_off_and_reduces_width() -> None:
    # 90% of ceiling (above the 0.75 knee) → real backoff + shrink.
    rb = g.rate_backoff(900, 0, 1000, 1000, 0)
    assert rb.backoff_after_ms > 0
    assert rb.reduced_width_factor < 1.0
    assert rb.reduced_width_factor >= g.RATE_MIN_WIDTH_FACTOR


def test_rate_backoff_at_ceiling_is_maximal_rate_backoff() -> None:
    rb = g.rate_backoff(1000, 1000, 1000, 1000, 0)
    assert rb.backoff_after_ms == g.RATE_BACKOFF_CEILING_MS
    assert rb.reduced_width_factor == g.RATE_MIN_WIDTH_FACTOR


def test_rate_backoff_over_ceiling_clamped_to_maximal() -> None:
    # 200% of ceiling clamps to the same maximal rate backoff.
    rb = g.rate_backoff(2000, 2000, 1000, 1000, 0)
    assert rb.backoff_after_ms == g.RATE_BACKOFF_CEILING_MS
    assert rb.reduced_width_factor == g.RATE_MIN_WIDTH_FACTOR


def test_rate_backoff_otpm_axis_can_bind() -> None:
    # ITPM is calm but OTPM is hot → the worst axis (OTPM) drives backoff.
    rb = g.rate_backoff(0, 950, 10_000, 1000, 0)
    assert rb.backoff_after_ms > 0
    assert rb.reduced_width_factor < 1.0


# ---------------------------------------------------------------------------
# rate_backoff — 429 forces backoff
# ---------------------------------------------------------------------------


def test_rate_backoff_single_429_forces_backoff_even_when_calm() -> None:
    # Rate is calm (10%) but one 429 was observed → forced backoff + floor.
    rb = g.rate_backoff(100, 100, 1000, 1000, 1)
    assert rb.backoff_after_ms >= g.RATE_429_BASE_BACKOFF_MS
    assert rb.reduced_width_factor == g.RATE_MIN_WIDTH_FACTOR


def test_rate_backoff_more_429s_increase_backoff_monotonic() -> None:
    one = g.rate_backoff(100, 100, 1000, 1000, 1).backoff_after_ms
    two = g.rate_backoff(100, 100, 1000, 1000, 2).backoff_after_ms
    three = g.rate_backoff(100, 100, 1000, 1000, 3).backoff_after_ms
    assert one < two < three


def test_rate_backoff_negative_429_count_treated_as_zero() -> None:
    # Nonsense negative count must not subtract from the backoff.
    calm = g.rate_backoff(100, 100, 1000, 1000, 0)
    nonsense = g.rate_backoff(100, 100, 1000, 1000, -5)
    assert nonsense == calm


def test_rate_backoff_429_and_rate_pressure_takes_the_larger() -> None:
    # Many 429s should exceed the rate-only backoff at a mid ratio.
    rate_only = g.rate_backoff(900, 0, 1000, 1000, 0).backoff_after_ms
    with_many_429 = g.rate_backoff(900, 0, 1000, 1000, 20).backoff_after_ms
    assert with_many_429 >= rate_only
    assert with_many_429 > 0


# ---------------------------------------------------------------------------
# rate_backoff — monotonicity properties
# ---------------------------------------------------------------------------


def test_rate_backoff_monotonic_in_rate_ratio() -> None:
    # backoff non-decreasing, width factor non-increasing as ITPM climbs.
    ratios = range(0, 1100, 50)  # 0% .. 110% of a 1000 ceiling
    backoffs = []
    widths = []
    for obs in ratios:
        rb = g.rate_backoff(obs, 0, 1000, 1000, 0)
        backoffs.append(rb.backoff_after_ms)
        widths.append(rb.reduced_width_factor)
    assert backoffs == sorted(backoffs)
    assert widths == sorted(widths, reverse=True)


def test_rate_backoff_width_factor_within_bounds_across_sweep() -> None:
    for obs in range(0, 1200, 25):
        for n429 in (0, 1, 5):
            rb = g.rate_backoff(obs, 0, 1000, 1000, n429)
            assert g.RATE_MIN_WIDTH_FACTOR <= rb.reduced_width_factor <= 1.0
            assert rb.backoff_after_ms >= 0


def test_rate_backoff_is_deterministic() -> None:
    a = g.rate_backoff(880, 400, 1000, 1000, 0)
    b = g.rate_backoff(880, 400, 1000, 1000, 0)
    assert a == b


# ---------------------------------------------------------------------------
# governors compose — width then rate factor
# ---------------------------------------------------------------------------


def test_governors_compose_width_after_rate_reduction() -> None:
    # A caller scales the quota-funded width down by the rate factor.
    reserve = g.DEFAULT_PER_LOOP_RESERVE_TOKENS
    base_width = g.compute_dispatch_width(reserve * 8, n_loops_requested=8)
    assert base_width == 8
    rb = g.rate_backoff(1000, 1000, 1000, 1000, 0)  # maximal pressure
    effective = int(base_width * rb.reduced_width_factor)
    # Width shrinks but stays >= 0 and < base under maximal pressure.
    assert 0 <= effective < base_width
