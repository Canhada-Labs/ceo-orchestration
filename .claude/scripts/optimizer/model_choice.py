"""WS-2(a) — the per-sub-task model-choice BRAIN.

NEW code, because ``_lib.model_routing.resolve_full`` is a static dict keyed only
by ``task_class`` — it consumes neither archetype nor context size, and no hook
ever writes a model back onto a spawn (``updatedInput`` = 0). This brain actually
maps a sub-task's ``complexity`` + ``context_size`` + ``archetype`` to
Haiku/Sonnet/Opus. It best-effort overlays the ``_lib.model_routing`` static
floor as a *backstop* only when the brain has no archetype signal; the brain is
the authority. Pure + deterministic; no IO beyond the best-effort backstop import.
``choose`` never raises.
"""

from __future__ import annotations

from typing import Optional

from ._skeleton import kill_switch_off, repo_hooks_lib
from .model_normalize import normalize_model_name
from .types import (
    COMPLEXITY_COMPLEX,
    COMPLEXITY_MODERATE,
    COMPLEXITY_SIMPLE,
    COMPLEXITY_TRIVIAL,
    MODEL_HAIKU,
    MODEL_OPUS,
    MODEL_SONNET,
    ModelChoice,
    VALID_MODELS,
)

# Context size (estimated input tokens) at/above which we escalate to Opus
# regardless of complexity bucket — a large context needs the strongest model.
LARGE_CONTEXT_TOKENS = 60000

# Archetypes whose blast radius / criticality always warrants Opus.
_OPUS_ARCHETYPES = frozenset({
    "debate", "arch", "architect", "security", "security-engineer",
    "identity-trust-architect", "incident-commander", "threat-detection-engineer",
})
# Standard code-gen / engineering archetypes — at least Sonnet.
_SONNET_ARCHETYPES = frozenset({
    "code_gen", "code-gen", "codegen", "devops", "performance-engineer",
    "qa-architect", "qa", "frontend", "llm-finops-architect",
})

_BASE_BY_COMPLEXITY = {
    COMPLEXITY_TRIVIAL: MODEL_HAIKU,
    COMPLEXITY_SIMPLE: MODEL_HAIKU,
    COMPLEXITY_MODERATE: MODEL_SONNET,
    COMPLEXITY_COMPLEX: MODEL_OPUS,
}

# Rank for "escalate-only" comparisons (never downgrade past an Opus archetype).
_MODEL_RANK = {MODEL_HAIKU: 0, MODEL_SONNET: 1, MODEL_OPUS: 2}


def _static_floor(task_class: str) -> Optional[str]:
    """Best-effort ``_lib.model_routing.resolve(task_class)``; None on failure.

    Backstop only — does NOT drive selection. Imported lazily so the optimizer
    has no hard dependency on the hooks ``_lib`` being importable.
    """
    try:
        from pathlib import Path
        repo_hooks_lib(Path(__file__).resolve().parents[3])
        from _lib import model_routing  # type: ignore[import]
        # B2: canonicalize the static-floor slug (alias/case ONLY — preserves
        # major.minor) so an aliased/date-stamped floor id still matches a
        # VALID_MODELS slug. normalize_model_name NEVER collapses two distinct
        # versions (opus-4-1 != opus-4-8).
        model = normalize_model_name(model_routing.resolve(task_class) or "")
        return model if model in VALID_MODELS else None
    except Exception:
        return None


def choose(
    task_class: str = "",
    archetype: str = "",
    context_size: int = 0,
    complexity: str = COMPLEXITY_SIMPLE,
) -> ModelChoice:
    """Deterministic per-sub-task model selection. Never raises.

    ``CEO_MODEL_ROUTING`` off → ``model=''`` (defer to harness default),
    ``cost_governed=True``. Otherwise pick a base model from ``complexity``,
    escalate for an Opus-class archetype, a code-gen archetype, or a large
    context, and — only when no archetype signal is present but a ``task_class``
    is — fall back to the static ``_lib`` floor (``fell_back_to_static=True``).
    ``confidence_basis_points`` is an int in 0..1000 (NEVER a float).
    """
    try:
        if kill_switch_off("CEO_MODEL_ROUTING"):
            return ModelChoice(
                model="",
                confidence_basis_points=1000,
                cost_governed=True,
                fell_back_to_static=False,
            )

        arche = (archetype or "").strip().lower()
        bucket = complexity if complexity in _BASE_BY_COMPLEXITY else COMPLEXITY_SIMPLE
        model = _BASE_BY_COMPLEXITY[bucket]
        fell_back = False
        confidence = 700  # complexity-only default

        # Escalate for code-gen archetypes (Haiku → Sonnet floor).
        if arche in _SONNET_ARCHETYPES and _MODEL_RANK[model] < _MODEL_RANK[MODEL_SONNET]:
            model = MODEL_SONNET
            confidence = 900
        # Escalate for Opus-class archetypes (always Opus).
        if arche in _OPUS_ARCHETYPES:
            model = MODEL_OPUS
            confidence = 950
        # Escalate for a large context regardless of bucket. Accept int OR float
        # (a float context_size from a future caller must not silently no-op),
        # but never bool (multi-lens review P2).
        if (
            isinstance(context_size, (int, float))
            and not isinstance(context_size, bool)
            and context_size >= LARGE_CONTEXT_TOKENS
        ):
            if _MODEL_RANK[model] < _MODEL_RANK[MODEL_OPUS]:
                model = MODEL_OPUS
            confidence = max(confidence, 900)

        # Backstop: weak signal (no archetype, mild complexity) but a known
        # task_class → consult the static floor.
        if not arche and bucket in (COMPLEXITY_TRIVIAL, COMPLEXITY_SIMPLE):
            floor = _static_floor(task_class)
            if floor is not None and floor != model:
                model = floor
                fell_back = True
                confidence = 800

        if arche in _OPUS_ARCHETYPES or arche in _SONNET_ARCHETYPES:
            confidence = max(confidence, 900)

        return ModelChoice(
            model=model,
            confidence_basis_points=int(confidence),
            cost_governed=False,
            fell_back_to_static=fell_back,
        )
    except Exception:
        return ModelChoice(
            model=MODEL_SONNET,
            confidence_basis_points=500,
            cost_governed=False,
            fell_back_to_static=False,
        )
