"""PLAN-088 W6.1 — beta-distribution posterior update for estimation calibration.

Stdlib-only Bayesian update math using `math.lgamma` for log-likelihood
stability on small N. Empirical prior from S82-S107 cohort per R6
mitigation (~42 GPG events / 75 closed plans).

Beta distribution conjugate prior for binomial success rate:
  posterior(alpha, beta) = prior(alpha, beta) + observations(successes, failures)

For estimation accuracy, "success" = actual hours within
[lower_bound, upper_bound] of frontmatter estimate; "failure" = outside.

Stored as integer basis-points (x 1000) per canonical_json no-float
invariant. The HMAC-chained audit log forbids float-valued fields.

References:
- PLAN-084 Wave 0.5 calibration-baseline.yaml fixture schema
- PLAN-086 Wave 6.1 nightly cron expectation
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


# Empirical prior from S82-S107 cohort observation per R6.
# (alpha=successes+1, beta=failures+1; Jeffreys is 0.5+0.5 but we use
# the empirical bias toward over-estimation per PLAN-084 finding.)
_PRIOR_ALPHA_DEFAULT = 30
_PRIOR_BETA_DEFAULT = 12


def _init_priors() -> Tuple[int, int]:
    """Return (alpha, beta) for empirical S82-S107 prior.

    Empirical, documented explicitly per R6 mitigation. Revisit at v2.0
    trigger (>=10 friction findings) per PLAN-088 Q3 tentative.
    """
    return _PRIOR_ALPHA_DEFAULT, _PRIOR_BETA_DEFAULT


def update_posterior(
    prior_alpha: int,
    prior_beta: int,
    new_successes: int,
    new_failures: int,
) -> Tuple[int, int]:
    """Update beta-distribution conjugate posterior.

    Args:
        prior_alpha: alpha parameter (successes + 1) at prior step
        prior_beta:  beta parameter (failures + 1) at prior step
        new_successes: observed successes since prior
        new_failures:  observed failures since prior

    Returns:
        (posterior_alpha, posterior_beta) as integers >= 1
    """
    a = max(1, int(prior_alpha))
    b = max(1, int(prior_beta))
    s = max(0, int(new_successes))
    f = max(0, int(new_failures))
    return a + s, b + f


def posterior_mean_basis_points(alpha: int, beta: int) -> int:
    """Return posterior mean as integer basis-points (0..1000).

    Beta distribution mean = alpha / (alpha + beta). Multiplied by 1000
    and rounded to int for HMAC-safe persistence per canonical_json
    no-float invariant.
    """
    a = max(1, int(alpha))
    b = max(1, int(beta))
    return int(round((a / (a + b)) * 1000))


def posterior_log_likelihood(alpha: int, beta: int) -> float:
    """Beta log-pdf normalization log B(alpha, beta) via math.lgamma.

    Used for posterior-vs-prior divergence comparison. Returns float
    (this is NOT persisted; used in-memory for telemetry stats only).
    """
    a = max(1, int(alpha))
    b = max(1, int(beta))
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def classify_estimate_accuracy(
    estimated_hours_lower: float,
    estimated_hours_upper: float,
    actual_hours: float,
) -> str:
    """Classify a single plan close as success / fail for the posterior.

    Returns 'success' if actual is within [lower, upper] of estimate;
    'failure' otherwise. NaN / negative inputs return 'unknown'.
    """
    try:
        lo = float(estimated_hours_lower)
        up = float(estimated_hours_upper)
        act = float(actual_hours)
    except (TypeError, ValueError):
        return "unknown"
    if math.isnan(lo) or math.isnan(up) or math.isnan(act):
        return "unknown"
    if act < 0 or lo < 0 or up < 0:
        return "unknown"
    if lo <= act <= up:
        return "success"
    return "failure"


def batch_update_from_plans(
    plans: List[Dict[str, float]],
    prior_alpha: Optional[int] = None,
    prior_beta: Optional[int] = None,
) -> Tuple[int, int, int, int]:
    """Compute posterior from a list of closed plans.

    Args:
        plans: list of dicts with keys
            'estimated_hours_lower' / 'estimated_hours_upper' / 'actual_hours'
        prior_alpha / prior_beta: optional override of the empirical prior

    Returns:
        (posterior_alpha, posterior_beta, successes_observed,
         failures_observed)
    """
    a = prior_alpha if prior_alpha is not None else _PRIOR_ALPHA_DEFAULT
    b = prior_beta if prior_beta is not None else _PRIOR_BETA_DEFAULT
    s = 0
    f = 0
    for p in plans:
        outcome = classify_estimate_accuracy(
            p.get("estimated_hours_lower", -1),
            p.get("estimated_hours_upper", -1),
            p.get("actual_hours", -1),
        )
        if outcome == "success":
            s += 1
        elif outcome == "failure":
            f += 1
        # 'unknown' contributes nothing
    pa, pb = update_posterior(a, b, s, f)
    return pa, pb, s, f
