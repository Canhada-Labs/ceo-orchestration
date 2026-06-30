"""tier_policy._constants — frozen invariants for the Adaptive Execution Kernel.

Pure-data module. Imported BEFORE every other ``tier_policy`` submodule so
the import-floor micro-benchmark (PLAN-071 §4.1b Phase 0.5) measures a
constants-only baseline (no I/O, no AST scan, stdlib only).

Public symbols
--------------

* ``VETO_HARDCODE`` — **2-role** local-floor mapping, role -> frozenset
  (task_types). Per PLAN-071 §4.2 line 380 this is the **hardcode core**;
  the 5-role spec floor (PLAN-074 Wave 1c amendment) is the UNION of
  these 2 with ``_lib/agent_frontmatter.VETO_FLOOR_ROLES`` at runtime in
  ``task-route.py``. Defense-in-depth: the 2 roles here have on-disk
  agent definition files at ``.claude/agents/<role>.md`` and ALWAYS
  bind even if ``_lib/agent_frontmatter`` is missing or corrupted.

* ``EXPECTED_VETO_FLOOR_UNION`` — frozenset of the 5 spec-named roles
  (PLAN-074 Wave 1c reduced 6→5; ``llm-finops-architect`` excluded per
  matrix). Used for invariant assertions ("any computed floor MUST be a
  superset of these 5 names"). After Wave 1c shipped (S93), every role
  in this union has an on-disk agent definition file at
  ``.claude/agents/<role>.md`` AND a matching frozenset entry in
  ``_lib/agent_frontmatter.VETO_FLOOR_ROLES`` — atomic-add invariant
  per S90 P0-01 lesson, enforced bidirectionally by
  ``test_veto_floor_bijection.py``.

  Wave-1c-staged note: the 4 forward-looking roles documented in older
  revisions of this docstring (incident-commander, identity-trust-
  architect, threat-detection-engineer, llm-finops-architect) are
  resolved as of S93 — three landed atomically in ``VETO_FLOOR_ROLES``
  with their agent files; ``llm-finops-architect`` ships as advisory
  archetype only (`veto_floor: false`).

* ``FROZEN_BASELINE_SHA256`` — sha256 over a stable-ordered JSON of the
  ``VETO_HARDCODE`` mapping AND ``EXPECTED_VETO_FLOOR_UNION``; computed
  at module import. Hardcoded ``_EXPECTED_FROZEN_BASELINE_SHA256``
  asserted at import for drift detection (R-CR2 + P1-10 fix).

* ``CLASSIFICATION_MODES`` — closed enum of S/M/L/XL tier slugs.

* ``_ALLOWED_FRONTMATTER_KEYS`` — closed key allowlist for
  ``_agent_frontmatter.parse_agent_frontmatter`` (defense-in-depth against
  prototype-pollution / unknown-field smuggling).

* ``FROZEN_BASELINE`` — minimal fallback policy returned by
  ``loader.load_policy`` when the on-disk policy is missing / invalid.
  Advisory-only: confidence is 0.0, mode falls to safe-default ``"M"``.
  ``veto_floor_roles`` field projects ``EXPECTED_VETO_FLOOR_UNION`` sorted.

Stdlib-only. Python ≥ 3.9. PEP 604 `X | Y` is NOT used (runtime-typed
references are ``typing.Optional`` / ``typing.Union``).

PLAN-071 §3 must-fix coverage:

* R-CR1 — exact symbol path ``tier_policy._constants.VETO_HARDCODE``;
  no import from ``_lib/policy.py``.
* R-SEC4 — 5 spec-named roles enumerated via ``EXPECTED_VETO_FLOOR_UNION``
  (PLAN-074 Wave 1c reduced 6→5; ``llm-finops-architect`` excluded)
  + 2 hardcode local-floor roles in ``VETO_HARDCODE``; runtime UNION
  yields the 5-role floor invariant.
* R-CR2 / P1-10 — ``FROZEN_BASELINE_SHA256`` provides AST-scan target
  for Reality Ledger detector #1; hardcoded expected digest + module-load
  assertion detects mutation of the backing dict.
* R-CR Unseen #2 — ``MappingProxyType`` makes runtime mutation raise.

Wave 1c roles (PLAN-074, S93 — ALL agent files now on-disk)
-----------------------------------------------------------

The 5 roles in ``EXPECTED_VETO_FLOOR_UNION`` each have a deployed
``.claude/agents/<role>.md`` file as of S93 Wave 1c. The frozenset
entry in ``_lib/agent_frontmatter.VETO_FLOOR_ROLES`` and the agent
file landed atomically per S90 P0-01 atomic-add invariant:

  - ``code-reviewer``              (general merge VETO)
  - ``security-engineer``          (auth/crypto VETO)
  - ``threat-detection-engineer``  (Sec-floor — SIEM/ATT&CK detection)
  - ``identity-trust-architect``   (Sec-floor — trust boundary owner)
  - ``incident-commander``         (Sec-floor — live-incident authority)

The 4th candidate from earlier revisions (``llm-finops-architect``)
ships at S93 as an **advisory** archetype with ``veto_floor: false``
in its agent frontmatter. Wave 1c VETO-floor matrix + ADR-052
amendment rationale: cost governance is operational doctrine and
mechanical enforcement (ADR-064), NOT a sub-domain trust boundary
that justifies a dedicated VETO authority.

The 2-role hardcode floor below remains the strict subset that is
enforceable purely from this module without crossing the ``_lib/``
boundary.
"""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Dict, Final, FrozenSet, Mapping, Tuple


# ---------------------------------------------------------------------------
# Closed enums
# ---------------------------------------------------------------------------

#: Tier slugs in monotonically-increasing-ceremony order. Position is
#: load-bearing (index() used as numeric tier in classifier promotions).
CLASSIFICATION_MODES: Final[Tuple[str, ...]] = ("S", "M", "L", "XL")


#: Allowed top-level keys in an ``.claude/agents/<name>.md`` frontmatter
#: payload. Anything outside this set raises ``FrontmatterError`` from
#: ``_agent_frontmatter.parse_agent_frontmatter``. The set is intentionally
#: tiny — agent files are config, not generic YAML.
_ALLOWED_FRONTMATTER_KEYS: Final[FrozenSet[str]] = frozenset({
    "name",
    "description",
    "model",
    "role",
    "tools",
    "veto_floor",
    "task_types",
    "skill",
    "skills",
    "tier",
    "version",
})


# ---------------------------------------------------------------------------
# EXPECTED_VETO_FLOOR_UNION — 5-role spec contract (PLAN-074 Wave 1c)
# ---------------------------------------------------------------------------
#
# The 5 role slugs the framework's VETO floor must converge on at runtime
# (UNION of VETO_HARDCODE.keys() and _lib/agent_frontmatter.VETO_FLOOR_ROLES).
# This constant is the spec source-of-truth; ``task-route.py`` asserts
# its computed floor is a superset of these 5 names at script init.
#
# Wave 1c (PLAN-074, S93) reduced this set from 6 → 5 by EXCLUDING
# ``llm-finops-architect``: cost governance is operational doctrine +
# mechanical enforcement (ADR-064), NOT a sub-domain trust boundary that
# justifies a dedicated VETO authority. ADR-052 amendment + Wave 1c
# matrix (`.claude/plans/PLAN-074/staging/wave-1c-veto-floor-matrix.md`)
# document the exclusion. The agent file
# ``.claude/agents/llm-finops-architect.md`` ships with
# ``veto_floor: false`` so the exclusion is bidirectionally verifiable
# via ``test_veto_floor_bijection.py``.
#
# Mutation requires a KERNEL-class git diff AND an ADR amendment. The
# tuple form is for stable serialisation into FROZEN_BASELINE.
_EXPECTED_VETO_FLOOR_UNION_TUPLE: Final[Tuple[str, ...]] = (
    "code-reviewer",
    "identity-trust-architect",
    "incident-commander",
    "security-engineer",
    "threat-detection-engineer",
)

EXPECTED_VETO_FLOOR_UNION: Final[FrozenSet[str]] = frozenset(
    _EXPECTED_VETO_FLOOR_UNION_TUPLE
)


# ---------------------------------------------------------------------------
# VETO_HARDCODE — 2-role hardcode floor (§4.2 line 380)
# ---------------------------------------------------------------------------
#
# The local-floor subset that ``tier_policy`` enforces WITHOUT importing
# ``_lib/agent_frontmatter``. These 2 roles:
#   1. have on-disk agent definition files at ``.claude/agents/<role>.md``,
#   2. map to the ADR-052 binding floor (the original "Opus or VETO"
#      contract from PLAN-043),
#   3. are enforceable from this module alone (no _lib dependency).
#
# At runtime ``task-route.py`` reads BOTH this dict's keys AND
# ``_lib/agent_frontmatter.VETO_FLOOR_ROLES`` and unions them; the
# resulting set MUST equal ``EXPECTED_VETO_FLOOR_UNION``. The other 3
# spec roles (forward-looking) are sourced from ``_lib`` only.
#
# The VALUES feed the ``ROLE_TO_TASK_TYPES`` reverse-index used by the
# classifier when it needs to escalate S → M for VETO-protected domains.
#
# DO NOT add a role here without:
#   1. matching addition to ``_lib/agent_frontmatter.VETO_FLOOR_ROLES``;
#   2. matching addition to ``EXPECTED_VETO_FLOOR_UNION``;
#   3. KERNEL-class git diff;
#   4. ADR amendment citing the new role's authority.
#
# DO NOT remove a role without an ADR amendment AND a 60-day moratorium
# notice (per ADR-093 §per-plan-cap protections; ADR-103 §moratorium-
# clause supersedes the calendar gate but the per-plan-cap survives).
#
# P1-10 fix: backing values use tuple-of-tuples then promote to frozensets
# at module level. The intermediate _RAW_HARDCODE structure is hashable
# and not exposed; only the MappingProxyType view is public.

_VETO_HARDCODE_RAW: Final[Tuple[Tuple[str, Tuple[str, ...]], ...]] = (
    (
        "code-reviewer",
        (
            "complexity-review",
            "diff-review",
            "naming-review",
            "regression-check",
            "test-coverage-audit",
        ),
    ),
    (
        "security-engineer",
        (
            "auth",
            "crypto",
            "injection",
            "secrets",
            "supply-chain",
            "threat-model",
        ),
    ),
)


def _build_veto_hardcode() -> Dict[str, FrozenSet[str]]:
    """Materialise the immutable raw tuples into the runtime dict.

    Pure: no I/O, no clock. Called ONCE at module import. The returned
    dict is wrapped in ``MappingProxyType`` and never re-assigned; the
    raw tuple structure above is the long-term provenance source for
    drift detection (P1-10 fix).
    """
    return {
        role: frozenset(task_types)
        for role, task_types in _VETO_HARDCODE_RAW
    }


_VETO_HARDCODE_MUTABLE: Dict[str, FrozenSet[str]] = _build_veto_hardcode()

#: Frozen public view. Runtime mutation (``VETO_HARDCODE["x"] = ...``)
#: raises ``TypeError``. Use ``MappingProxyType`` so ``isinstance(...,
#: Mapping)`` still works for downstream consumers.
VETO_HARDCODE: Final[Mapping[str, FrozenSet[str]]] = MappingProxyType(
    _VETO_HARDCODE_MUTABLE
)


# ---------------------------------------------------------------------------
# FROZEN_BASELINE_SHA256 — drift / tamper detector
# ---------------------------------------------------------------------------


def _compute_baseline_sha() -> str:
    """Return sha256(stable-ordered JSON of VETO_HARDCODE + UNION).

    Stable order = role keys sorted; task-type values sorted as a list;
    UNION roles sorted. The hex digest is the wire-format identity for
    KERNEL ceremony pins and Reality Ledger detector #1 assertions.

    Pure: no I/O, no clock, no env. Determinism is the whole point.

    P1-10 fix: hash both the 2-role hardcode mapping AND the 5-role
    expected-union list (Wave 1c reduced 6→5), so drift in EITHER
    source trips the assertion.
    """
    payload: Dict[str, Any] = {
        "veto_hardcode": {
            role: sorted(task_types)
            for role, task_types in sorted(_VETO_HARDCODE_RAW)
        },
        "expected_veto_floor_union": sorted(_EXPECTED_VETO_FLOOR_UNION_TUPLE),
    }
    blob = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


#: SHA256 hex of the stable-ordered ``VETO_HARDCODE`` + UNION payload.
#: Computed ONCE at module import; constant for the life of the process.
FROZEN_BASELINE_SHA256: Final[str] = _compute_baseline_sha()

#: Hardcoded expected digest. Module-load assertion below catches drift
#: (P1-10 fix: detects mutation of the backing structures by anyone who
#: bypasses MappingProxyType via the raw tuples or _build_veto_hardcode).
#: To regenerate: run this module, read FROZEN_BASELINE_SHA256, paste here.
_EXPECTED_FROZEN_BASELINE_SHA256: Final[str] = (
    # PLAN-074 Wave 1c (S93): 5-role union; 6→5 transition removed
    # ``llm-finops-architect`` per matrix exclusion. Recompute via
    # `python3 -c "import json,hashlib; ..."` if the union or
    # VETO_HARDCODE_RAW changes again.
    "cde3dbc8b609731b82c67ca24b56202734597f3cb2b409069fec28b04087e0d8"
)

# Module-load assertion. If this trips, somebody mutated VETO_HARDCODE_RAW
# or EXPECTED_VETO_FLOOR_UNION_TUPLE without updating the expected digest;
# the diff is forensic evidence visible in git history.
assert FROZEN_BASELINE_SHA256 == _EXPECTED_FROZEN_BASELINE_SHA256, (
    "tier_policy._constants drift detected: "
    f"computed={FROZEN_BASELINE_SHA256!r} "
    f"expected={_EXPECTED_FROZEN_BASELINE_SHA256!r}. "
    "If this change is intentional, regenerate "
    "_EXPECTED_FROZEN_BASELINE_SHA256 from FROZEN_BASELINE_SHA256."
)


# ---------------------------------------------------------------------------
# FROZEN_BASELINE — loader fallback policy
# ---------------------------------------------------------------------------
#
# Minimal advisory-only payload returned by ``loader.load_policy`` when
# the on-disk file is missing / oversized / corrupt / schema-mismatched.
# All consumers MUST treat this as zero-confidence guidance — it is the
# safe-default that lets a script keep producing a digest instead of
# crashing the CEO.
#
# ``veto_floor_roles`` projects EXPECTED_VETO_FLOOR_UNION (sorted, list)
# rather than VETO_HARDCODE keys — the fallback shape MUST advertise the
# spec contract, not the local-floor subset.

_FROZEN_BASELINE_MUTABLE: Dict[str, Any] = {
    "schema_version": 2,
    "default_mode": "M",
    "default_model": "claude-opus-4-8",
    "veto_floor_roles": sorted(_EXPECTED_VETO_FLOOR_UNION_TUPLE),
    "modes": list(CLASSIFICATION_MODES),
    "confidence": 0.0,
    "source": "frozen_baseline",
}

FROZEN_BASELINE: Final[Mapping[str, Any]] = MappingProxyType(
    _FROZEN_BASELINE_MUTABLE
)


# ---------------------------------------------------------------------------
# Hard limits (mirror _lib/policy.py limits SPEC §3.3 — kept local to
# avoid an import dependency on _lib.policy per R-CR1).
# ---------------------------------------------------------------------------

#: Maximum on-disk policy file size (raw bytes).
LIMIT_FILE_BYTES: Final[int] = 64 * 1024  # 64 KiB

#: Maximum nested-dict depth tolerated by loader / frontmatter parser.
LIMIT_DEPTH: Final[int] = 8

#: Maximum number of keys at any single level (defense against fan-out
#: attacks on the YAML subset parser).
LIMIT_KEY_COUNT: Final[int] = 2000

#: Maximum scalar string length.
LIMIT_SCALAR_LEN: Final[int] = 16 * 1024  # 16 KiB

#: Maximum number of items in any single list / array (defense against
#: fan-out attacks via list payloads — P1-09 follow-on).
LIMIT_ARRAY_LEN: Final[int] = 10000

#: Schema version exposed by ``_types.SCHEMA_VERSION``; loader migrates
#: v1 → v2 by zero-defaulting additive fields.
CURRENT_SCHEMA_VERSION: Final[int] = 2


__all__ = [
    "CLASSIFICATION_MODES",
    "VETO_HARDCODE",
    "EXPECTED_VETO_FLOOR_UNION",
    "FROZEN_BASELINE_SHA256",
    "FROZEN_BASELINE",
    "LIMIT_FILE_BYTES",
    "LIMIT_DEPTH",
    "LIMIT_KEY_COUNT",
    "LIMIT_SCALAR_LEN",
    "LIMIT_ARRAY_LEN",
    "CURRENT_SCHEMA_VERSION",
    "_ALLOWED_FRONTMATTER_KEYS",
]
