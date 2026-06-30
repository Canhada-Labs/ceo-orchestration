"""PLAN-122 WS-2 — swarm fan-out governors (pure functions).

Two pure, deterministic governors that let the coordinator scale a
fan-out width to the budget envelope AND back off as the observed
token RATE approaches the account's per-minute ITPM/OTPM ceiling
(PLAN-122 §0.1.b / §0.1.c "budget-aware width governor + token-RATE
concurrency governor"). stdlib-only, no I/O, no audit emission.

Boundary (mechanism only — NO benchmark claim):
- ``compute_dispatch_width`` answers "how many of the requested loops
  can the remaining token quota actually fund?" and clamps to the
  same ``MAX_PARALLEL_CEILING`` (ADR-051) the coordinator enforces.
- ``rate_backoff`` answers "given the observed ITPM/OTPM vs the
  account ceiling (and any 429s already seen), how long should the
  next dispatch wait and by how much should width shrink?" It is the
  CONSUMER of the framework's existing ``anthropic_429_observed``
  audit signal — it counts 429s, it never emits them.

Both functions are conservative (fail toward LESS parallelism), pure,
and monotonic in the documented direction. They NEVER raise on the
happy path — out-of-range or absurd inputs clamp rather than throw, so
a governor bug can only ever slow the swarm down, never crash it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from .coordinator import MAX_PARALLEL_CEILING


# Per-loop token reserve used by the width governor. A loop must be
# able to fund at least this many tokens of work before we are willing
# to spend a parallel slot on it. Deliberately conservative: it is
# better to under-dispatch (and refill next tick) than to start a loop
# the quota cannot carry to a useful checkpoint. Tunable by callers via
# the ``per_loop_reserve_tokens`` argument; this is the default floor.
DEFAULT_PER_LOOP_RESERVE_TOKENS = 20_000


# Rate-backoff tuning constants (PLAN-122 §0.1.b — token-RATE governor).
# The governor starts easing off once the observed rate crosses this
# fraction of the ceiling, and applies a hard, maximal backoff once it
# reaches the ceiling. Below the soft knee there is no backoff and no
# width reduction — light load keeps full fan-out.
RATE_SOFT_KNEE = 0.75
# Largest single backoff we will ask for from rate pressure alone, in
# milliseconds. Roughly one per-minute rate window so an over-rate
# burst has a chance to drain. A 429 escalates beyond this (see below).
RATE_BACKOFF_CEILING_MS = 60_000
# A real 429 from the API is ground truth that we already exceeded the
# limit; it forces at least this backoff regardless of the rate ratio,
# and grows with the number of 429s observed.
RATE_429_BASE_BACKOFF_MS = 5_000
RATE_429_PER_EVENT_BACKOFF_MS = 5_000
# Floor on the width factor — even under maximal pressure we keep a
# sliver of forward progress (one loop) rather than stalling to zero,
# so the swarm self-heals once the rate drains. A 429 can still drive
# the effective width lower via the caller re-running compute width.
RATE_MIN_WIDTH_FACTOR = 0.10


class RateBackoff(NamedTuple):
    """Result of :func:`rate_backoff`.

    ``backoff_after_ms`` — how long the coordinator should wait before
    the next dispatch wave (0 means "no backoff; dispatch now").
    ``reduced_width_factor`` — multiplier in [RATE_MIN_WIDTH_FACTOR, 1.0]
    the caller applies to the *desired* fan-out width before dispatch.
    1.0 means "full width"; smaller means "shrink the wave".

    A plain NamedTuple (not a mutable dataclass) so the result is
    frozen + JSON-friendly + cheap to compare in tests.
    """

    backoff_after_ms: int
    reduced_width_factor: float


@dataclass(frozen=True)
class _RatePressure:
    """Internal: the normalized rate pressure on each axis.

    Kept private — callers only ever see :class:`RateBackoff`. Frozen
    so it is hashable + cannot drift after construction.
    """

    itpm_ratio: float
    otpm_ratio: float

    @property
    def worst(self) -> float:
        """The binding axis — the swarm is gated by whichever rate is
        closest to (or past) its ceiling."""

        return max(self.itpm_ratio, self.otpm_ratio)


def _safe_ratio(observed: int, ceiling: int) -> float:
    """observed/ceiling clamped to >= 0.0, fail-open on a bad ceiling.

    A non-positive ceiling means "ceiling unknown / unmeasured"; we
    treat that as zero pressure (0.0) rather than dividing by zero —
    the BLOCKING WS-0 pre-flight is what actually measures the ceiling,
    and an unmeasured ceiling must not by itself force a backoff here.
    Negative observed (nonsense) clamps to 0.0.
    """

    if ceiling <= 0:
        return 0.0
    if observed <= 0:
        return 0.0
    return observed / ceiling


def compute_dispatch_width(
    remaining_quota_tokens: int,
    n_loops_requested: int,
    max_parallel_ceiling: int = MAX_PARALLEL_CEILING,
    per_loop_reserve_tokens: int = DEFAULT_PER_LOOP_RESERVE_TOKENS,
) -> int:
    """Scale fan-out width to the remaining token quota.

    Returns the number of loops to dispatch this wave, clamped to
    ``[0, min(n_loops_requested, max_parallel_ceiling)]``:

    - ``remaining_quota_tokens <= 0`` → ``0`` (no quota, no dispatch).
    - Otherwise width is capped by how many ``per_loop_reserve_tokens``
      chunks the quota can fund: ``quota // reserve``. A quota that
      cannot fund even one full reserve → ``0`` (we wait for a refill
      rather than start a loop we cannot carry).
    - The quota-funded width is then clamped to both the requested loop
      count and the hard parallel ceiling (ADR-051).

    Pure + deterministic; identical inputs → identical output. Never
    raises — absurd inputs (negative request, zero ceiling) clamp to a
    safe 0 rather than throwing.
    """

    # Conservative clamps on the bounds themselves first.
    if n_loops_requested <= 0:
        return 0
    ceiling = max_parallel_ceiling if max_parallel_ceiling > 0 else 0
    if ceiling <= 0:
        return 0
    if remaining_quota_tokens <= 0:
        return 0

    # Guard a non-positive reserve (caller misuse) by falling back to
    # the default floor — we never divide by zero and never let the
    # quota fund an unbounded width.
    reserve = (
        per_loop_reserve_tokens
        if per_loop_reserve_tokens > 0
        else DEFAULT_PER_LOOP_RESERVE_TOKENS
    )

    quota_funded_width = remaining_quota_tokens // reserve

    # Clamp: requested, ceiling, and what the quota can fund all bind.
    width = min(quota_funded_width, n_loops_requested, ceiling)
    # Lower-bound at 0 (quota_funded_width could be 0 when the quota is
    # below one reserve chunk).
    if width < 0:
        width = 0
    return width


def _measure_rate_pressure(
    observed_itpm: int,
    observed_otpm: int,
    ceiling_itpm: int,
    ceiling_otpm: int,
) -> _RatePressure:
    """Normalize observed vs ceiling on both rate axes (pure)."""

    return _RatePressure(
        itpm_ratio=_safe_ratio(observed_itpm, ceiling_itpm),
        otpm_ratio=_safe_ratio(observed_otpm, ceiling_otpm),
    )


def rate_backoff(
    observed_itpm: int,
    observed_otpm: int,
    ceiling_itpm: int,
    ceiling_otpm: int,
    anthropic_429_count: int,
) -> RateBackoff:
    """Compute backoff + width reduction from observed token rate.

    PLAN-122 §0.1.b token-RATE concurrency governor. As the observed
    per-minute rate (input OR output, whichever binds) approaches its
    ceiling, the returned backoff grows and the width factor shrinks.
    Any ``anthropic_429_count > 0`` is ground truth that we already
    crossed the limit and forces a real, non-zero backoff regardless of
    the rate ratio.

    Monotonicity (conservative, in the documented direction):
    - ``backoff_after_ms`` is non-decreasing in the worst rate ratio and
      non-decreasing in ``anthropic_429_count``.
    - ``reduced_width_factor`` is non-increasing in the worst rate ratio
      and non-increasing in ``anthropic_429_count``.

    Returns a frozen :class:`RateBackoff`. Never raises — a non-positive
    ceiling is treated as "unmeasured → zero rate pressure" (the WS-0
    pre-flight is what measures the ceiling), so an unknown ceiling
    cannot by itself force a backoff; only a real 429 can in that case.

    The output is always SAFE-biased: rate pressure can only ever add
    backoff and shrink width, never the reverse.
    """

    pressure = _measure_rate_pressure(
        observed_itpm, observed_otpm, ceiling_itpm, ceiling_otpm
    )
    worst = pressure.worst

    # --- Rate-driven backoff ------------------------------------------
    # No backoff below the soft knee — light load keeps full fan-out.
    # Between the knee and the ceiling, scale linearly up to the rate
    # backoff ceiling. At/above the ceiling, apply the full rate ceiling.
    if worst <= RATE_SOFT_KNEE:
        rate_backoff_ms = 0
    elif worst >= 1.0:
        rate_backoff_ms = RATE_BACKOFF_CEILING_MS
    else:
        # Fraction of the way from the knee to the ceiling, in [0, 1).
        span = 1.0 - RATE_SOFT_KNEE
        frac = (worst - RATE_SOFT_KNEE) / span if span > 0 else 1.0
        rate_backoff_ms = int(round(frac * RATE_BACKOFF_CEILING_MS))

    # --- 429-driven backoff (ground truth) ----------------------------
    # A real 429 means we already exceeded the limit. Force at least a
    # base backoff, growing with each additional 429 observed. Clamp the
    # 429 count to a sane non-negative value so a nonsense negative count
    # can never subtract from the backoff.
    n_429 = anthropic_429_count if anthropic_429_count > 0 else 0
    if n_429 > 0:
        forced_429_ms = (
            RATE_429_BASE_BACKOFF_MS + (n_429 - 1) * RATE_429_PER_EVENT_BACKOFF_MS
        )
    else:
        forced_429_ms = 0

    # The effective backoff is the larger of the rate-driven and the
    # 429-forced backoff — whichever pressure is greater wins.
    backoff_after_ms = max(rate_backoff_ms, forced_429_ms)

    # --- Width reduction ----------------------------------------------
    # Below the knee with no 429s → full width (1.0). Otherwise shrink
    # linearly toward the floor as the worst ratio climbs to the
    # ceiling. A 429 forces the width factor down to the floor (we have
    # concrete evidence the wave was too wide).
    if n_429 > 0:
        reduced_width_factor = RATE_MIN_WIDTH_FACTOR
    elif worst <= RATE_SOFT_KNEE:
        reduced_width_factor = 1.0
    elif worst >= 1.0:
        reduced_width_factor = RATE_MIN_WIDTH_FACTOR
    else:
        span = 1.0 - RATE_SOFT_KNEE
        frac = (worst - RATE_SOFT_KNEE) / span if span > 0 else 1.0
        # frac=0 → 1.0 (no reduction), frac=1 → floor.
        reduced_width_factor = 1.0 - frac * (1.0 - RATE_MIN_WIDTH_FACTOR)

    # Final clamp — defensive; the branches above already stay in range.
    if reduced_width_factor > 1.0:
        reduced_width_factor = 1.0
    elif reduced_width_factor < RATE_MIN_WIDTH_FACTOR:
        reduced_width_factor = RATE_MIN_WIDTH_FACTOR

    return RateBackoff(
        backoff_after_ms=backoff_after_ms,
        reduced_width_factor=reduced_width_factor,
    )
