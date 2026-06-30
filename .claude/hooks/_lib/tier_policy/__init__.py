"""tier_policy — Adaptive Execution Kernel policy package (advisory-only).

PLAN-071 Phase 1 deliverable. Read `.claude/plans/PLAN-071-adaptive-execution-kernel.md`
for the full design; this docstring is the authoritative public-API map.

Public API
----------

Constants (eagerly available — used by the import-floor benchmark):

* :data:`VETO_HARDCODE` — frozen **2-role** local-floor mapping
  (``code-reviewer`` + ``security-engineer``) per ADR-052 binding floor
  and PLAN-071 §4.2 line 380. These are the two roles enforceable
  purely from this module without crossing the ``_lib/`` boundary
  (defense-in-depth: agent definition files are on disk).
* :data:`EXPECTED_VETO_FLOOR_UNION` — frozenset of the **6 spec floor
  roles** per PLAN-071 §3.1 line 151 (the 2 hardcode roles above plus
  4 forward-looking roles: ``threat-detection-engineer``,
  ``identity-trust-architect``, ``incident-commander``,
  ``llm-finops-architect``). At runtime ``task-route.py`` UNIONS
  ``VETO_HARDCODE.keys()`` with ``_lib/agent_frontmatter.VETO_FLOOR_ROLES``
  and asserts the result is a superset of this constant.
* :data:`FROZEN_BASELINE_SHA256` — sha256 of stable-ordered
  ``VETO_HARDCODE`` + ``EXPECTED_VETO_FLOOR_UNION`` payload (P1-10
  drift detector covers BOTH structures).
* :data:`CLASSIFICATION_MODES` — closed enum of S/M/L/XL slugs.

Types (lazy-loaded; first attribute access triggers ``_types`` import):

* :class:`MODEL_ID` — closed enum of canonical Anthropic model slugs.
* :class:`TaskTypeRequest` — frozen dataclass; classifier input.
* :class:`TaskTypeResponse` — frozen dataclass; classifier output.
* :class:`ClassificationResult` — alias of :class:`TaskTypeResponse`.

Loader (lazy-loaded; first call triggers ``loader`` import):

* :func:`load_policy` — read ``$CLAUDE_PROJECT_DIR/.claude/policy/
  tier-policy.json`` and return a :class:`ClassificationResult`. Never
  raises; falls back to ``FROZEN_BASELINE`` on any error.

Stdlib only. Python ≥ 3.9. No third-party imports anywhere in the
package — confirmed by Phase 0.5 import-floor benchmark.

Design notes (PLAN-071 §3 must-fix coverage)
--------------------------------------------

* R-CR1 — exact symbol paths preserved. ``task-route.py`` reads
  ``tier_policy._constants::VETO_HARDCODE`` and
  ``tier_policy._types::ROLE_TO_TASK_TYPES`` via
  ``open().read()`` + ``re.search()``. NOT via ``importlib``.
  The package is also nominally importable for unit tests.
* R-PERF2 — lazy submodule imports keep the constants-only
  baseline ≤ 5ms p50. ``_agent_frontmatter`` and ``loader`` only
  pay their import cost when first accessed.
* R-CR Unseen #2 — every public Mapping uses ``MappingProxyType``;
  every dataclass is ``frozen=True``. Runtime mutation raises.
* R-SEC4 / P0-03 — the 6-role spec floor is encoded as
  ``EXPECTED_VETO_FLOOR_UNION``; ``VETO_HARDCODE`` is the strict
  2-role hardcode subset. Runtime UNION yields the spec floor.
"""

from __future__ import annotations

# Eager imports: constants only. Pure-data, no I/O, no clock.
from ._constants import (
    CLASSIFICATION_MODES,
    EXPECTED_VETO_FLOOR_UNION,
    FROZEN_BASELINE_SHA256,
    VETO_HARDCODE,
)

# Names exported lazily — populated on first ``__getattr__`` hit.
_LAZY_NAMES = frozenset({
    "MODEL_ID",
    "TaskTypeRequest",
    "TaskTypeResponse",
    "ClassificationResult",
    "load_policy",
})


def __getattr__(name: str):
    """PEP 562 lazy attribute loader.

    Submodule imports only happen when a caller actually touches
    the lazy symbols. Constants-only consumers (e.g. the Phase 0.5
    micro-benchmark) never pay the ``_types`` / ``loader`` cost.
    """
    if name in {
        "MODEL_ID",
        "TaskTypeRequest",
        "TaskTypeResponse",
        "ClassificationResult",
    }:
        from . import _types as _t
        return getattr(_t, name)
    if name == "load_policy":
        from .loader import load_policy as _load
        return _load
    raise AttributeError(
        f"module 'tier_policy' has no attribute {name!r}"
    )


def __dir__():
    """Stable ``dir()`` listing — eager + lazy union."""
    return sorted(set(__all__) | _LAZY_NAMES)


__all__ = [
    # Eager constants
    "VETO_HARDCODE",
    "EXPECTED_VETO_FLOOR_UNION",
    "FROZEN_BASELINE_SHA256",
    "CLASSIFICATION_MODES",
    # Lazy types
    "MODEL_ID",
    "TaskTypeRequest",
    "TaskTypeResponse",
    "ClassificationResult",
    # Lazy loader
    "load_policy",
]
