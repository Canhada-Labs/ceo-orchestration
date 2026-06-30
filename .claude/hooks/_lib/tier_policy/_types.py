"""tier_policy._types — typed contract surface for the AEK classifier.

Frozen dataclasses + closed enums. Stdlib-only. PEP 604 ``X | Y`` is
NOT used at runtime; we use ``typing.Optional`` / ``typing.Union`` per
the dogfood Python ≥ 3.9 contract.

Public symbols
--------------

* ``MODEL_ID`` — closed enum of the model slugs the framework recognises.
  Values are the canonical Anthropic model IDs ("claude-opus-4-8",
  "claude-sonnet-4-6", "claude-haiku-4-5"). Membership is closed; new
  models require an ADR + KERNEL edit here.

* ``TaskTypeRequest`` — frozen dataclass passed by the classifier.
  Fields: ``task_type``, ``role``, ``context_tokens``, ``risk_level``.

* ``TaskTypeResponse`` — frozen dataclass returned by the classifier.
  Fields: ``mode`` (one of ``CLASSIFICATION_MODES``), ``suggested_model``
  (a ``MODEL_ID`` value), ``reason`` (free-text), ``confidence`` (0.0..1.0).

* ``ClassificationResult`` — alias of ``TaskTypeResponse`` for callers
  that prefer the policy-domain noun ("classify a request → result")
  over the type-domain noun. Identical shape.

* ``ROLE_TO_TASK_TYPES`` — frozen reverse-index from role-slug to
  ``frozenset(task_type)``. Strict superset of
  ``_constants.EXPECTED_VETO_FLOOR_UNION`` (6 spec-named VETO floor
  roles per §3.1 line 151) plus non-VETO archetypes the team uses.

* ``SCHEMA_VERSION`` — int constant; bumped when the dataclass shape
  changes in a non-additive way. Loader migrates v1 → v2 by zero-
  defaulting additive fields.

PLAN-071 §3 must-fix coverage:

* R-CR1 — exact symbol path ``tier_policy._types.ROLE_TO_TASK_TYPES``;
  no shadow under ``_lib/policy.py``.
* R-CR Unseen #2 — ``frozen=True`` + ``MappingProxyType`` make
  runtime mutation raise.
* R-CR R2-2 — ``MODEL_ID.OPUS47`` is the canonical "claude-opus-4-8"
  symbol used by the VETO floor (not the legacy ``opus-4-1`` slug).
* R-SEC4 / P0-03 — keys are a strict superset of the 6 spec VETO floor
  roles named in PLAN-071 §3.1 line 151. The 4 forward-looking roles
  (threat-detection-engineer, identity-trust-architect, incident-
  commander, llm-finops-architect) appear here even though their
  ``.claude/agents/<role>.md`` files do not yet exist on disk; the
  classifier still needs to recognise their task-type ownership for
  routing purposes.
"""

from __future__ import annotations

import dataclasses
import enum
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

from ._constants import (
    CLASSIFICATION_MODES,
    CURRENT_SCHEMA_VERSION,
    EXPECTED_VETO_FLOOR_UNION,
)


# ---------------------------------------------------------------------------
# SCHEMA_VERSION
# ---------------------------------------------------------------------------

#: Wire-format schema version for ``TaskTypeRequest`` / ``TaskTypeResponse``
#: dataclasses AND the on-disk ``tier-policy.json`` payload. Bumped on
#: non-additive shape changes. Loader migrates additive v1 → v2 silently;
#: a non-additive change requires an ADR.
SCHEMA_VERSION: int = CURRENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# MODEL_ID — closed enum
# ---------------------------------------------------------------------------


class MODEL_ID(enum.Enum):
    """Canonical Anthropic model IDs recognised by the AEK.

    Values are exactly the strings the SDK accepts as ``model=`` arguments.
    Membership is closed: adding a model requires an ADR (cost / capability
    envelope) AND a KERNEL edit here.

    The enum is intentionally NOT a ``str`` subclass — callers that need
    the wire string use ``model.value`` (explicit) so accidental
    string-comparison silently coercing the enum is impossible.
    """

    OPUS47 = "claude-opus-4-8"
    SONNET46 = "claude-sonnet-4-6"
    HAIKU45 = "claude-haiku-4-5"

    def __str__(self) -> str:  # pragma: no cover — convenience
        return self.value


# ---------------------------------------------------------------------------
# Dataclasses — TaskTypeRequest / TaskTypeResponse
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TaskTypeRequest:
    """Input to the classifier.

    Frozen — instances are pickled into audit fixtures and re-loaded by
    Reality Ledger detector #3. Mutation post-construction would corrupt
    the replay invariant.

    Fields
    ------
    task_type : str
        Free-form slug describing the work (e.g. ``"diff-review"``,
        ``"crypto-implementation"``). Caller normalises to lowercase.
    role : str
        Persona slug (e.g. ``"code-reviewer"``). Lookup against
        ``ROLE_TO_TASK_TYPES`` validates coherence.
    context_tokens : int
        Estimated input-context size in tokens. Drives mode promotions
        (very-long context → L regardless of role).
    risk_level : str
        One of ``"low"``, ``"medium"``, ``"high"``, ``"critical"``.
        VETO-floor roles default to ``"high"`` even when the caller
        passes a softer slug.
    """

    task_type: str
    role: str
    context_tokens: int = 0
    risk_level: str = "medium"


@dataclasses.dataclass(frozen=True)
class TaskTypeResponse:
    """Output of the classifier.

    Fields
    ------
    mode : str
        One of ``CLASSIFICATION_MODES`` ("S" / "M" / "L" / "XL").
    suggested_model : str
        Wire string of a ``MODEL_ID`` value. Stored as ``str`` (not
        ``MODEL_ID``) so the dataclass round-trips through JSON cleanly.
    reason : str
        Free-text explanation. May reference the rule that fired.
    confidence : float
        0.0 .. 1.0. ``0.0`` is the sentinel for "fallback / I don't know"
        — the loader returns this when on-disk policy is missing.
    """

    mode: str
    suggested_model: str
    reason: str
    confidence: float = 0.0


#: Alias for callers that prefer the policy-domain noun.
ClassificationResult = TaskTypeResponse


# ---------------------------------------------------------------------------
# ROLE_TO_TASK_TYPES — reverse-index over the 6-role spec floor + non-VETO
# archetypes that exist in team.md ROUTING TABLE.
# ---------------------------------------------------------------------------
#
# Keys MUST be a strict superset of ``_constants.EXPECTED_VETO_FLOOR_UNION``
# (the 6 spec roles per PLAN-071 §3.1 line 151). The classifier reads this
# table AND ``_lib/agent_frontmatter.VETO_FLOOR_ROLES`` and asserts
# ``classifier_floor >= union(...)`` at script init.
#
# Forward-looking note: 4 of the 6 spec roles
# (``threat-detection-engineer``, ``identity-trust-architect``,
# ``incident-commander``, ``llm-finops-architect``) do NOT yet have
# ``.claude/agents/<role>.md`` files on disk; this table still lists
# their task-type ownership so the classifier can route work to them
# once the agent files ship in PLAN-074 Wave 0.
#
# Values are intentionally NOT identical to ``_constants.VETO_HARDCODE``
# — that table is the local-floor hardcode (defence-in-depth, 2 roles),
# this one is the "what does this archetype actually own" routing table
# spanning the full 6-role spec union plus non-VETO team archetypes.

_ROLE_TO_TASK_TYPES_MUTABLE: Dict[str, FrozenSet[str]] = {
    # 6-role VETO floor (mirrors _constants.EXPECTED_VETO_FLOOR_UNION)
    # ---- 2 hardcode-floor roles (have on-disk agent files) ----
    "code-reviewer": frozenset({
        "diff-review",
        "regression-check",
        "test-coverage-audit",
        "complexity-review",
        "naming-review",
        "veto-arbitration",
    }),
    "security-engineer": frozenset({
        "auth",
        "crypto",
        "secrets",
        "injection",
        "supply-chain",
        "threat-model",
        "veto-arbitration",
    }),
    # ---- 4 forward-looking floor roles (no on-disk agent files yet;
    # ship in PLAN-074 Wave 0 ADJ-B3 BLOCKER 6 cluster) ----
    "threat-detection-engineer": frozenset({
        "threat-model",
        "attack-surface-mapping",
        "ioc-design",
        "detection-rule-authoring",
        "tabletop-exercise",
        "veto-arbitration",
    }),
    "identity-trust-architect": frozenset({
        "identity-federation",
        "trust-boundary-design",
        "session-management",
        "iam-policy-review",
        "consent-flow-audit",
        "veto-arbitration",
    }),
    "incident-commander": frozenset({
        "incident-response",
        "runbook-authoring",
        "post-mortem",
        "live-debug-coordination",
        "rollback-decision",
        "veto-arbitration",
    }),
    "llm-finops-architect": frozenset({
        "cost-envelope-review",
        "model-routing-policy",
        "kill-switch-authoring",
        "token-budget-audit",
        "vendor-lock-in-assessment",
        "veto-arbitration",
    }),
    # Non-VETO archetypes (team.md ROUTING TABLE — line 207+).
    # These DO NOT participate in the VETO floor union but DO
    # participate in classifier routing.
    "qa-architect": frozenset({
        "test-strategy",
        "fixture-design",
        "mutation-coverage",
        "regression-suite",
        "harness-design",
    }),
    "performance-engineer": frozenset({
        "latency",
        "memory",
        "event-loop",
        "gc-tuning",
        "profiling",
        "load-test",
    }),
    "devops": frozenset({
        "ci-cd",
        "docker",
        "deployment",
        "observability",
        "release-pipeline",
        "secrets-rotation",
    }),
    "ceo": frozenset({
        "orchestration",
        "spawn-decision",
        "escalation",
        "veto-arbitration",
        "plan-authoring",
    }),
    "staff-backend-engineer": frozenset({
        "feature-implementation",
        "bug-fix",
        "refactor",
        "schema-migration",
        "api-contract",
    }),
    "staff-frontend-engineer": frozenset({
        "ui-component",
        "page-implementation",
        "design-system-adopt",
        "a11y-audit",
    }),
    "data-engineer": frozenset({
        "etl",
        "warehouse-schema",
        "data-quality",
        "pipeline-orchestration",
    }),
    "ml-engineer": frozenset({
        "model-training",
        "feature-engineering",
        "evaluation-harness",
        "deployment-serving",
    }),
}

#: Frozen public view. Mutating a value (``ROLE_TO_TASK_TYPES["x"] =
#: ...``) raises ``TypeError``.
ROLE_TO_TASK_TYPES: Mapping[str, FrozenSet[str]] = MappingProxyType(
    _ROLE_TO_TASK_TYPES_MUTABLE
)

# Defensive structural assertion: ROLE_TO_TASK_TYPES MUST be a strict
# superset of EXPECTED_VETO_FLOOR_UNION. If this trips somebody removed
# a spec floor role; the diff is forensic evidence in git history.
assert EXPECTED_VETO_FLOOR_UNION.issubset(ROLE_TO_TASK_TYPES.keys()), (
    "ROLE_TO_TASK_TYPES missing spec VETO floor roles: "
    f"{sorted(EXPECTED_VETO_FLOOR_UNION - set(ROLE_TO_TASK_TYPES.keys()))}"
)


# ---------------------------------------------------------------------------
# Helpers (cheap, pure)
# ---------------------------------------------------------------------------


def task_types_for_role(role: str) -> FrozenSet[str]:
    """Return the task-type frozenset for ``role``, or empty if unknown.

    Pure, O(1), no exception. Callers use this to sanity-check whether
    a (role, task_type) pairing is coherent before classification.
    """
    return ROLE_TO_TASK_TYPES.get(role, frozenset())


def is_known_mode(mode: str) -> bool:
    """``True`` iff ``mode`` is in ``CLASSIFICATION_MODES``."""
    return mode in CLASSIFICATION_MODES


def is_known_model(model: str) -> bool:
    """``True`` iff ``model`` is a wire string of a ``MODEL_ID`` value."""
    try:
        MODEL_ID(model)
    except ValueError:
        return False
    return True


__all__ = [
    "MODEL_ID",
    "TaskTypeRequest",
    "TaskTypeResponse",
    "ClassificationResult",
    "ROLE_TO_TASK_TYPES",
    "SCHEMA_VERSION",
    "task_types_for_role",
    "is_known_mode",
    "is_known_model",
]
