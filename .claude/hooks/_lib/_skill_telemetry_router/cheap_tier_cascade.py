"""Pure advisory cascade; execution and financial verification stay elsewhere."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


_TIERS = ("haiku", "sonnet", "opus")
_MAX_TIER = {"low": "haiku", "medium": "sonnet", "high": "opus"}


def select_cheap_tier_cascade(task_complexity: str, budget_remaining_usd: float) -> dict:
    """Plan a possible tier order without asserting cost or executing a model.

    The positive budget is a *ceiling*, not evidence of affordability: token
    counts and live prices are unavailable. Independent verification is required
    before any model transition or acceptance. Financial/safety tasks must be
    governed by separate policy and cannot be downgraded by this advisor.
    """
    plan = {
        "status": "blocked",
        "task_complexity": task_complexity if isinstance(task_complexity, str) else None,
        "budget_cap_usd": None,
        "tiers": [],
        "max_tier": None,
        "estimated_cost_usd": None,
        "requires_independent_verification": True,
        "requires_price_and_token_check": True,
        "executes_models": False,
        "reason": "invalid_input",
    }
    if not isinstance(task_complexity, str) or task_complexity not in _MAX_TIER:
        plan["reason"] = "invalid_complexity"
        return plan
    if isinstance(budget_remaining_usd, bool):
        plan["reason"] = "invalid_budget"
        return plan
    try:
        amount = Decimal(str(budget_remaining_usd))
    except (InvalidOperation, ValueError, TypeError):
        plan["reason"] = "invalid_budget"
        return plan
    if not amount.is_finite() or amount < 0:
        plan["reason"] = "invalid_budget"
        return plan
    plan["budget_cap_usd"] = str(amount)
    if amount == 0:
        plan["reason"] = "budget_exhausted"
        return plan

    max_tier = _MAX_TIER[task_complexity]
    plan.update(
        status="advisory_only",
        tiers=list(_TIERS[: _TIERS.index(max_tier) + 1]),
        max_tier=max_tier,
        reason="cost_and_quality_unverified; escalate_only_after_independent_failure",
    )
    return plan
