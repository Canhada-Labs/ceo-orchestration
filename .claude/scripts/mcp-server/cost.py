"""Thin adapter over ``_lib/adapters/live/_cost.py`` for the MCP server.

Per ADR-042 §Cost the MCP ``spawn_agent`` handler MUST inherit
``LiveCallPolicy`` verbatim — no parallel budget surface at the MCP
layer. This module provides a single entry point
:func:`check_spawn_budget` that the handler calls BEFORE emitting
``live_adapter_call_started``.

Design contract:

- **Re-use**, not reimplementation — the cost machinery lives in
  ``_lib/adapters/live/_cost.py`` (SpawnCostTracker, PlanCostTracker,
  BudgetHardStop). This module is a stable reason-mapping layer.
- **Deny reasons** match ADR-042 §Cost.1 verbatim:
  ``budget_hard_stop_per_spawn`` | ``budget_hard_stop_per_plan_5min`` |
  ``debate_max_rounds``.
- **No side effects on deny** — this checker inspects; it does NOT
  add to the tracker. Real spawn dispatch (Sprint 14+) is the site
  that applies ``tracker.add()``.
- **Pre-flight** — the estimated cost is fed through
  :func:`_lib.adapters.live._cost.estimate_cost_usd` indirectly via
  the handler, so zero-pricing edge (local provider, TBD pricing)
  still trips the guard via the fallback estimator.

## Public surface

:func:`check_spawn_budget` returns ``(allow, reason)``:

- ``(True, None)`` — both trackers under ceiling; spawn proceeds.
- ``(False, "budget_hard_stop_per_spawn")`` — per-spawn ceiling
  would be crossed.
- ``(False, "budget_hard_stop_per_plan_5min")`` — plan 5-min window
  ceiling would be crossed.

``debate_max_rounds`` enforcement happens inside
``debate-orchestrate.py`` — the MCP layer does NOT invoke debate
directly, so that reason is defined in the error enum but never
returned by this function. (It surfaces to MCP clients via the audit
log when debate is invoked indirectly.)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

# Make _lib importable — hooks live under .claude/hooks/, adapter
# at .claude/hooks/_lib/adapters/live/_cost.py. mcp-server package
# is at .claude/scripts/mcp-server — six levels from here to
# ``.claude/hooks/`` after normalising.
_HOOKS_DIR = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.adapters.live._cost import (  # noqa: E402
    PlanCostTracker,
    SpawnCostTracker,
)


def check_spawn_budget(
    *,
    estimated_usd: float,
    spawn_tracker: SpawnCostTracker,
    plan_tracker: PlanCostTracker,
) -> Tuple[bool, Optional[str]]:
    """Return ``(allow, reason)`` for an MCP spawn cost pre-flight check.

    Args:
        estimated_usd: the pre-flight cost estimate from
            :func:`_lib.adapters.live._cost.estimate_cost_usd`. Zero
            for local provider.
        spawn_tracker: per-spawn rolling tally (ceiling 0.50 USD
            default; ADR-040 §3).
        plan_tracker: per-plan 5-minute window tracker (ceiling
            2.00 USD default; ADR-040 §3).

    Returns:
        ``(True, None)`` on allow; ``(False, reason)`` on deny with
        ``reason`` ∈ the closed enum from ADR-042 §Cost.1.

    The trackers are NOT mutated by this function. Callers add real
    charges via ``tracker.add()`` after a successful spawn completes.
    """
    if estimated_usd < 0:
        # Defensive: negative estimate is nonsense; treat as deny for
        # per-spawn (safer to fail closed than to skip the check).
        return False, "budget_hard_stop_per_spawn"

    # Check per-spawn ceiling first (tightest bound, fastest to compute).
    if spawn_tracker.would_exceed(estimated_usd):
        return False, "budget_hard_stop_per_spawn"

    # Check per-plan 5-minute window ceiling.
    current_plan_total = plan_tracker.total_usd()
    projected_plan_total = current_plan_total + float(estimated_usd)
    if projected_plan_total > plan_tracker.ceiling_usd:
        return False, "budget_hard_stop_per_plan_5min"

    return True, None


__all__ = [
    "check_spawn_budget",
    "SpawnCostTracker",
    "PlanCostTracker",
]
