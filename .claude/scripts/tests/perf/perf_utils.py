"""PLAN-087 Wave C — shared microbench utilities.

Methodology:

* ``timeit.repeat(number=1000, repeat=N)`` with ``N >= 30`` samples.
  Each sample is the total time of 1000 inner calls; per-call time is
  derived by dividing by 1000. The inner loop amortizes single-call
  variance from the OS scheduler.
* Per-call time is reported in nanoseconds (integer).
* Relative threshold: ``p99(post) <= 0.80 * p99(baseline)``. Absolute
  ms targets are NOT used (CI hardware variance ±30% per handoff §10.2).
* Baseline + post-fix runs happen in the same harness invocation, on
  the same machine, in alternating order to absorb scheduler bias.

Stdlib-only per ADR-002. Compatible with Python >= 3.9.
"""

from __future__ import annotations

import timeit
from typing import Callable, List, Tuple


def _percentile(data: List[float], pct: float) -> float:
    """Return the p-th percentile of ``data``.

    Args:
        data: List of non-negative floats. Empty input returns 0.0.
        pct: Percentile in 0.0-1.0 range (0.50 = median, 0.99 = p99).

    Uses nearest-rank with floor: ``idx = int(n * pct)`` (clamped to
    ``[0, n-1]``). NOTE: for a tiny sample with ``pct`` near 1.0 this
    collapses to ~the maximum — e.g. N=30 + p99 → ``idx=int(29.7)=29`` =
    ``sorted[29]`` = the **largest** of 30, which has zero resistance to a
    single scheduler-stall outlier. For a noise-robust tail on shared CI
    runners, prefer ``tail_pct<=0.95`` with ``repeat>=40`` (see
    ``measure_relative(tail_pct=...)``) so the estimator discards the top
    few outliers instead of latching onto the max.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    idx = int(n * pct)
    if idx >= n:
        idx = n - 1
    if idx < 0:
        idx = 0
    return sorted_data[idx]


def measure_relative(
    baseline_fn: Callable[[], None],
    post_fn: Callable[[], None],
    *,
    number: int = 1000,
    repeat: int = 30,
    tail_pct: float = 0.95,
) -> Tuple[float, float, float, float]:
    """Run baseline and post-fix functions in alternating fashion.

    Args:
        baseline_fn: Pre-fix code path. Called ``number * repeat`` times.
        post_fn: Post-fix code path. Called ``number * repeat`` times.
        number: Inner loop count per sample (default 1000 — amortizes
            single-call noise).
        repeat: Number of samples per pass (default 30 — handoff §10.2
            minimum). Each pass is one timeit.repeat run.
        tail_pct: Upper percentile for the tail estimate (default 0.95 —
            S155: was 0.99, which at repeat=30 collapses to max-of-30 and
            flakes intermittently on shared CI runners; p95 discards the
            single worst outlier). Use repeat>=60 for even more headroom
            (see ``_percentile``).

    Returns:
        ``(p50_baseline_ns, ptail_baseline_ns, p50_post_ns, ptail_post_ns)``
        — per-call time in nanoseconds; ``ptail`` is the ``tail_pct``
        percentile.
    """
    def _sample(fn: Callable[[], None]) -> List[float]:
        raw = timeit.repeat(fn, number=number, repeat=repeat)
        return [(t / number) * 1e9 for t in raw]

    b_samples = _sample(baseline_fn)
    p_samples = _sample(post_fn)

    return (
        _percentile(b_samples, 0.50),
        _percentile(b_samples, tail_pct),
        _percentile(p_samples, 0.50),
        _percentile(p_samples, tail_pct),
    )


def report_and_assert(
    item: str,
    p50_b: float,
    ptail_b: float,
    p50_p: float,
    ptail_p: float,
    *,
    threshold: float = 0.80,
    advisory: bool = False,
) -> str:
    """Build a one-line report string + assert relative threshold.

    Args:
        item: Short identifier (e.g., ``"C.4-plan-glob-cache"``).
        p50_b / ptail_b: Baseline percentiles in nanoseconds (``ptail`` is the
            ``tail_pct`` percentile from ``measure_relative``, default p95 —
            NOT p99; renamed S166/PLAN-114 C-2 to stop mislabelling the value).
        p50_p / ptail_p: Post-fix percentiles in nanoseconds.
        threshold: Maximum allowed ratio ``ptail(post) / ptail(baseline)``.
            Default 0.80 per handoff §10.2.
        advisory: When True, returns the report WITHOUT raising on miss
            (records to stdout instead). Use for items flagged as Tier-3
            no-op-in-subprocess context (e.g., C.2 sys.modules early-exit).

    Returns:
        Human-readable single-line summary suitable for progress_log.

    Raises:
        AssertionError when ``advisory=False`` and ratio > threshold.
    """
    ratio = (ptail_p / ptail_b) if ptail_b > 0 else 1.0
    verdict = "PASS" if ratio <= threshold else "MISS"
    report = (
        f"[{item}] {verdict} ptail ratio={ratio:.3f} "
        f"(baseline p50={p50_b:.0f}ns ptail={ptail_b:.0f}ns | "
        f"post p50={p50_p:.0f}ns ptail={ptail_p:.0f}ns; threshold<={threshold})"
    )
    if not advisory and ratio > threshold:
        raise AssertionError(report)
    return report
