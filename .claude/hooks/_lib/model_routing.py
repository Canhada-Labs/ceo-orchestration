"""Model-routing resolver — PLAN-086 Wave B (R-019) + PLAN-088 W2.2 extension.

Maps ``task_class`` strings to model slugs. PLAN-086 Wave B shipped the
74 LoC STUB; PLAN-088 W2.2 (S114) extends with full ``resolve_full(
task_class, archetype, context_size)`` returning dict per spec.

## Backward compatibility

The pre-existing ``resolve(task_class) -> Optional[str]`` signature is
preserved for backward compatibility with PLAN-086 callers. The new
``resolve_full()`` overlay is the PLAN-088 W2.2 god-mode dispatch
contract returning ``{"model": str, "thinking": bool, "thinking_budget_tokens": int, "rationale": str}``.

## Contract (frozen for PLAN-088 W2.2 inheritance)

    resolve(task_class) -> Optional[str]

Returns the recommended model slug for the given task class. Returns
``None`` when task_class is unknown or non-str.

## Canonical 7 task classes

  - ``file_read``   — Haiku floor (read-only)
  - ``line_audit``  — Haiku floor (mechanical scan)
  - ``debate``      — Opus floor (synthesis)
  - ``arch``        — Opus floor (architectural decisions)
  - ``code_gen``    — Sonnet floor (bounded implementation)
  - ``finops``      — Sonnet floor (cost-arithmetic)
  - ``digest``      — Haiku floor (summarization)

## References

- ADR-052 §Role-to-model dispatch
- PLAN-086 Wave B handoff §3 — file-ownership matrix
- `_lib/mcp_routing.py` — sibling pattern (server → name)

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

from typing import Dict, Optional


#: Canonical task classes (frozen across PLAN-086 + PLAN-088 W2.2).
TASK_CLASSES = (
    "file_read",
    "line_audit",
    "debate",
    "arch",
    "code_gen",
    "finops",
    "digest",
)


#: STUB routing table — static floor per task class.
_ROUTING_TABLE: Dict[str, str] = {
    "file_read": "claude-haiku-4-5",
    "line_audit": "claude-haiku-4-5",
    "debate": "claude-opus-4-8",
    "arch": "claude-opus-4-8",
    "code_gen": "claude-sonnet-4-6",
    "finops": "claude-sonnet-4-6",
    "digest": "claude-haiku-4-5",
}


def resolve(task_class: str) -> Optional[str]:
    """Return the recommended model slug for ``task_class``, or None.

    STUB per PLAN-086 Wave B. Full resolver overlays tier-policy
    lookups (PLAN-088 W2.2).
    """
    if not isinstance(task_class, str) or not task_class:
        return None
    return _ROUTING_TABLE.get(task_class)


#: Public alias mirroring _lib/mcp_routing.py.
route = resolve


# =============================================================================
# PLAN-088 W2.2 extension — full resolve_full() returning dict per spec.
# =============================================================================

import os

# Per-task-class thinking budget cap-table (M-22 / Perf-2).
# Stored as (default_budget_tokens, max_budget_tokens) tuples.
_THINKING_BUDGET_CAP_TABLE = {
    "architect":           (4096, 16384),
    "debate-R2-synthesis": (8192, 32768),
    "audit-class":         (8192, 32768),
    "general":             (0,    0),
}

# Slash-command override budget table (PLAN-086 Wave A owns the slash
# command authoring; W2.2 honors values at dispatch time).
# LEGACY-MODEL-ONLY (pre-4.6 ids): the {"type": "enabled", "budget_tokens"}
# request shape is removed (HTTP 400) on the current API generation —
# adaptive-only models consume _SLASH_EFFORT_TABLE below instead
# (PLAN-134 W0 E6-F2).
# ``xhigh`` (PLAN-135 W1 K8b): legacy ids have no native xhigh tier — the
# budget is the high↔max interpolation (16384 < 24576 < 32768) so the
# keyword stays monotonic on this surface and inside the --budget-tokens
# clamp range (1024..32768). Both tables MUST share the same keyword set
# (test_canonical_tables_share_keywords).
_SLASH_BUDGET_TABLE = {
    "off":   0,
    "low":   1024,
    "med":   4096,
    "high":  16384,
    "xhigh": 24576,
    "max":   32768,
}

# Slash-command override effort table (PLAN-134 W0 E6-F2). On the
# adaptive-only generation (Opus 4.6+/Sonnet 4.6/Opus 4.7/4.8/Fable 5) the
# `/effort` level maps to ``output_config: {"effort": <value>}`` alongside
# ``thinking: {"type": "adaptive"}``. ``"off"`` maps to None = OMIT the
# thinking param entirely (an explicit {"type": "disabled"} is an HTTP 400
# on Fable 5). Consumed by
# `_lib/adapters/live/claude.py:_resolve_effort_config`.
# ``xhigh`` (PLAN-135 W1 K8b): API effort tier between ``high`` and
# ``max``, introduced with Opus 4.7 (supported on Opus 4.7/4.8 + Fable 5;
# the recommended setting for most coding/agentic work and the Claude
# Code default). Completes the 5-active-level ladder
# low < medium < high < xhigh < max.
_SLASH_EFFORT_TABLE = {
    "off":   None,
    "low":   "low",
    "med":   "medium",
    "high":  "high",
    "xhigh": "xhigh",
    "max":   "max",
}


def _opt_out_kill_switch() -> bool:
    """Return True if CEO_MULTI_MODEL_MANUAL=1 (reverts to manual model)."""
    return os.environ.get("CEO_MULTI_MODEL_MANUAL", "").strip() == "1"


def _thinking_kill_switch() -> bool:
    """Return True if CEO_THINKING_AUTO_DISABLE=1 (per M-11 / Sec-2)."""
    return os.environ.get("CEO_THINKING_AUTO_DISABLE", "").strip() == "1"


def _slash_effort_override() -> Optional[int]:
    """Return integer budget if CEO_EFFORT_OVERRIDE env-var present.

    Slash-command `<effort>` overrides are propagated to the dispatch
    layer via this env-var (set by the slash handler in PLAN-086 Wave A).
    Accepted values: off / low / med / high / xhigh / max.
    """
    raw = os.environ.get("CEO_EFFORT_OVERRIDE", "").strip().lower()
    if not raw:
        return None
    return _SLASH_BUDGET_TABLE.get(raw)


def resolve_full(
    task_class: str = "",
    archetype: str = "",
    context_size: int = 0,
) -> Dict[str, object]:
    """PLAN-088 W2.2 full resolver — returns dict with model + thinking config.

    Returns:
        {
          "model":                  str (model slug; "" when opt-out),
          "thinking":               bool (True iff thinking budget > 0),
          "thinking_budget_tokens": int (0 means thinking off),
          "rationale":              str (bounded slug),
        }

    NOTE (PLAN-134 W0 E6-F2): the ``thinking_budget_tokens`` field is the
    LEGACY (pre-4.6) request shape and is kept for the frozen W2.2
    contract only. On adaptive-only models the live adapter translates
    the `/effort` level via ``_SLASH_EFFORT_TABLE`` into
    ``output_config.effort`` instead — it does not consume this field.

    Opt-out env-vars:
      - CEO_MULTI_MODEL_MANUAL=1 → model="" rationale="opted_out"
      - CEO_THINKING_AUTO_DISABLE=1 → thinking=False budget=0
      - CEO_EFFORT_OVERRIDE={off,low,med,high,xhigh,max} → budget overrides
        task-class default
    """
    # Kill switch: manual model selection
    if _opt_out_kill_switch():
        return {
            "model": "",
            "thinking": False,
            "thinking_budget_tokens": 0,
            "rationale": "opted_out_multi_model_manual",
        }

    # Model selection via canonical task_class lookup
    model = resolve(task_class) or ""

    # Thinking budget per task_class (M-22 cap table)
    default_budget, _max_budget = _THINKING_BUDGET_CAP_TABLE.get(
        task_class, _THINKING_BUDGET_CAP_TABLE["general"]
    )

    # Slash-command effort override (PLAN-086 Wave A propagation)
    override = _slash_effort_override()
    if override is not None:
        budget = override
        rationale = "effort_override"
    else:
        budget = default_budget
        rationale = "task_class_default"

    # Kill switch: thinking-auto-disable
    if _thinking_kill_switch():
        budget = 0
        rationale = "opted_out_thinking_auto_disable"

    return {
        "model": model,
        "thinking": budget > 0,
        "thinking_budget_tokens": budget,
        "rationale": rationale,
    }
