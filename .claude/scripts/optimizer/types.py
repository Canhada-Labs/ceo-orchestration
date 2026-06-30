"""Shared types + constants for the PLAN-122 optimizer package.

Pure data: frozen dataclasses for every cross-module record + string constants
for routes, complexity buckets, and model slugs. ZERO logic, ZERO env reads, ZERO
IO. Imported by every leaf module so they agree on shapes without importing each
other.

Invariant (audit-chain safety): every numeric field that ends up in an audit
payload is an INT (e.g. ``confidence_basis_points`` in 0..1000, never a float);
every bool is emitted to audit as a 0/1 int by :func:`optimizer._skeleton.
safe_emit`. A float anywhere in an audit event nulls the HMAC and breaks the
chain (see PLAN-118 root-cause #2), so the dataclasses below keep all
audit-bound numbers integral.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# --- Route constants (WS-1 gate verdict) ------------------------------------
ROUTE_PASSTHROUGH: str = "passthrough"      # CEO_OPTIMIZER off OR trivial task
ROUTE_SINGLE: str = "single_agent"          # non-trivial but serial / not worth fan-out
ROUTE_FANOUT: str = "fanout"                # parallelizable + worth decomposing

# --- Complexity buckets ------------------------------------------------------
COMPLEXITY_TRIVIAL: str = "trivial"
COMPLEXITY_SIMPLE: str = "simple"
COMPLEXITY_MODERATE: str = "moderate"
COMPLEXITY_COMPLEX: str = "complex"

# Ordered low→high so a gate can compare bucket rank cheaply.
COMPLEXITY_ORDER: Tuple[str, ...] = (
    COMPLEXITY_TRIVIAL,
    COMPLEXITY_SIMPLE,
    COMPLEXITY_MODERATE,
    COMPLEXITY_COMPLEX,
)

# --- Model slugs (must match .claude/hooks/_lib/model_routing.py) -----------
MODEL_HAIKU: str = "claude-haiku-4-5"
MODEL_SONNET: str = "claude-sonnet-4-6"
MODEL_OPUS: str = "claude-opus-4-8"

VALID_MODELS: Tuple[str, ...] = (MODEL_HAIKU, MODEL_SONNET, MODEL_OPUS)

# --- Hard ceilings (mirror swarm MAX_PARALLEL constraints) ------------------
#: Maximum fan-out width the recommender will ever suggest. The native harness
#: caps concurrent agents at min(16, cores-2); we recommend conservatively.
MAX_FANOUT_WIDTH: int = 8
#: Bounded cap on the number of independently-parallelizable units the gate will
#: count before width governance (keeps all scans O(len) and bounded).
MAX_UNIT_COUNT: int = 32


@dataclass(frozen=True)
class GateResult:
    """WS-1 verdict for a single user prompt."""

    route: str               # one of ROUTE_*
    complexity: str          # one of COMPLEXITY_*
    parallelizable: bool
    suggested_width: int     # 1..MAX_FANOUT_WIDTH
    reason: str              # short human-readable rationale


@dataclass(frozen=True)
class SubTask:
    """One decomposed unit of a fan-out plan.

    Carries the model-choice telemetry (confidence/cost/fallback) so the
    recommender can forward REAL signal to the audit log instead of zeros.
    """

    index: int
    label: str
    model: str                     # one of VALID_MODELS (or '' = harness default)
    est_tokens_in: int
    confidence_basis_points: int = 0   # from ModelChoice — int 0..1000, never float
    cost_governed: bool = False
    fell_back_to_static: bool = False


@dataclass(frozen=True)
class FanoutPlan:
    """WS-2 fan-out recommendation (NEVER a dispatch command)."""

    subtasks: Tuple[SubTask, ...]
    suggested_width: int
    width_capped: bool
    budget_governed: bool
    rate_backoff_applied: bool


@dataclass(frozen=True)
class ModelChoice:
    """WS-2(a) per-sub-task model selection."""

    model: str               # '' means "defer to harness default" (routing off)
    confidence_basis_points: int   # 0..1000 int — NEVER a float
    cost_governed: bool
    fell_back_to_static: bool


@dataclass(frozen=True)
class RagHint:
    """WS-2(d) optional RAG context-trim hint."""

    available: bool
    router_decision: str
    context_block: str
    chunks_returned: int


@dataclass(frozen=True)
class Recommendation:
    """The full advisory the façade assembles for ``additionalContext``."""

    gate: GateResult
    fanout: Optional[FanoutPlan]
    rag: Optional[RagHint]
    context_block: str       # the bounded additionalContext string (<=4000 chars)
