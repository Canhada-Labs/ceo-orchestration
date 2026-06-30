"""PLAN-043 — Dataclasses + type aliases + mappings.

Per Round 1 closures C-P0-6 (ROLE_TO_TASK_TYPES mapping), C-P0-9
(full model IDs throughout), C-P1-6 (schema versioning).

All dataclasses are frozen=False (mutable) per stdlib convention for
serializable records; TypedDict-style immutability enforced via
module-level constants (MODEL_ID Literal, VETO_HARDCODE Final dict in
_constants.py).

stdlib-only (ADR-002). Python >= 3.9 compatible:
``from __future__ import annotations`` + ``typing.Optional/Union``
(no runtime PEP 604 or match statements).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Final, List, Literal, Optional, Tuple


# ---------------------------------------------------------------------
# Model ID type alias (C-P0-9 — full IDs only; no short names).
# Matches ADR-052 canonical form + .claude/agents/<slug>.md model: field.
# ---------------------------------------------------------------------
MODEL_ID = "Literal['claude-fable-5', 'claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001']"
# Runtime constant — used by loader.py / learn.py for allowlist checks.
# ADR-149: claude-fable-5 added (flagship generation bump, additive).
VALID_MODEL_IDS: "Final[Tuple[str, ...]]" = (
    "claude-fable-5",
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
)


# ---------------------------------------------------------------------
# Role ↔ task-type mapping (C-P0-6).
# Statistical power gate aggregates tournament win-rates per
# (role × task-type) cell; this mapping tells learn.py which ADR-063
# task-types count toward each canonical-5 role.
# Aggregation across cells for a role: MIN gap_pp (conservative).
# ---------------------------------------------------------------------
ROLE_TO_TASK_TYPES: "Final[Dict[str, List[str]]]" = {
    "code-reviewer": ["code-review", "security-review"],
    "security-engineer": ["security-review"],
    "qa-architect": ["test-design"],
    "performance-engineer": ["performance-triage"],
    "devops": ["docs-writing"],
}


# ---------------------------------------------------------------------
# Canonical-5 agent slugs (policy artifact assignments keys).
# ---------------------------------------------------------------------
CANONICAL_5_AGENTS: "Final[Tuple[str, ...]]" = (
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "devops",
)


# ---------------------------------------------------------------------
# ADR-063 tournament task-types (inverse lookup for mapping
# completeness tests).
# ---------------------------------------------------------------------
TOURNAMENT_TASK_TYPES: "Final[Tuple[str, ...]]" = (
    "security-review",
    "code-review",
    "performance-triage",
    "test-design",
    "docs-writing",
)


# ---------------------------------------------------------------------
# Schema version (C-P1-6 — enables adopter upgrade migration path).
# ---------------------------------------------------------------------
CURRENT_POLICY_SCHEMA_VERSION: "Final[str]" = "1.0"


# ---------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------

@dataclass
class AssignmentEvidence:
    """Statistical evidence backing an agent's tier assignment.

    Populated by learn.py aggregating tournament reports; null on
    baseline (n=0 first-run per Q8 closure).
    """

    n: int
    gap_pp: float
    last_updated: Optional[str]  # ISO8601; None on baseline
    runs_considered: int = 0
    tournament_report_hmacs: List[str] = field(default_factory=list)


@dataclass
class Assignment:
    """Per-agent tier assignment in the policy artifact.

    ``locked_by``:
      - ``"VETO_FLOOR"`` — agent is in VETO_HARDCODE; tier immutable by
        learned policy (only Owner ADR amendment changes it)
      - ``None`` — agent subject to learned-policy updates
    """

    tier: str  # MODEL_ID Literal value (runtime check via VALID_MODEL_IDS)
    locked_by: Optional[str]
    evidence: Optional[AssignmentEvidence]


@dataclass
class TierPolicyRecord:
    """In-memory representation of ``.claude/tier-policy.json``.

    Loaded + schema-validated + HMAC-verified by loader.py. Corrupt
    artifacts cause fail-open to ADR-052 static baseline (see
    :func:`build_adr052_baseline`).
    """

    schema_version: str
    generated_at: str  # ISO8601
    baseline_from: str
    assignments: Dict[str, Assignment]
    hmac_anchor: str  # hex-encoded 64 chars
    sigchain_tip_length: int = 1  # C-P0-5 truncation anchor
    last_change_by_role: Dict[str, str] = field(default_factory=dict)  # F-PERF-P1-1


@dataclass
class SigchainEntry:
    """Single entry in ``.claude/tier-policy.json.sigchain``.

    Each entry's HMAC covers all fields EXCEPT ``hmac`` + ``hmac_error``
    per ADR-055 pattern. ``chain_length`` + ``prior_commit_sha`` are
    C-P0-5 additions against truncation/rollback attacks.
    """

    timestamp: str  # ISO8601
    author: str  # git user.email (attribution via git commit signature,
                 # per C-P0-11; this field is advisory unless verified)
    sp_chain_id: str  # regex ^SP-\d{3}-[a-f0-9]{8}$
    action: str  # "promote" | "demote" | "baseline" | "rotate"
    agent_slug: str
    from_tier: str  # MODEL_ID
    to_tier: str  # MODEL_ID
    evidence_hmac: str  # hex
    prior_hash: str  # hex of prior entry's hmac (genesis = 64 zeros)
    chain_length: int  # C-P0-5 monotonic counter
    prior_commit_sha: str  # C-P0-5 rollback defense
    hmac: Optional[str] = None  # set by writer; None on pre-hash dict


@dataclass
class Recommendation:
    """Output of learn.py aggregation.

    ``signature_required`` is True when action is "demote" OR when
    ``action == "promote"`` and projected cost delta exceeds
    ``CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD`` (C-P0-4 3-way gate).
    ``rejection_reason`` is non-None when the gate rejected the
    candidate; `action` remains "hold" in that case.
    """

    agent_slug: str
    current_tier: str  # MODEL_ID
    recommended_tier: str  # MODEL_ID
    action: str  # "promote" | "demote" | "hold"
    evidence: AssignmentEvidence
    signature_required: bool
    cooldown_ok: bool
    rejection_reason: Optional[str] = None
    # Reasons (stable enum):
    #   "veto_floor" — agent in VETO_HARDCODE
    #   "statistical_power" — n < 30 or gap_pp < 25
    #   "cooldown" — <90 days since last_updated
    #   "insufficient_fresh_reports" — < 3 reports within age window
    #   "promote_cost_gated" — downgrade to signed (C-P0-4)


# ---------------------------------------------------------------------
# ADR-052 static baseline (C-P0-7 / fail-open target).
# Used by loader.py on corrupt artifact detection.
# ---------------------------------------------------------------------

def build_adr052_baseline() -> Dict[str, Assignment]:
    """Return the ADR-052 canonical static tier assignments.

    This is the fail-open fallback when tier-policy.json is missing,
    corrupt, HMAC-invalid, or fails schema validation. Matches
    ADR-052 §Role-to-model distribution exactly.

    Module-level constant per F-PERF-P1-2 — zero additional I/O on
    fallback path.
    """
    return {
        "code-reviewer": Assignment(
            tier="claude-fable-5",
            locked_by="VETO_FLOOR",
            evidence=None,
        ),
        "security-engineer": Assignment(
            tier="claude-fable-5",
            locked_by="VETO_FLOOR",
            evidence=None,
        ),
        "qa-architect": Assignment(
            tier="claude-sonnet-4-6",
            locked_by=None,
            evidence=None,
        ),
        "performance-engineer": Assignment(
            tier="claude-sonnet-4-6",
            locked_by=None,
            evidence=None,
        ),
        "devops": Assignment(
            tier="claude-haiku-4-5-20251001",
            locked_by=None,
            evidence=None,
        ),
    }
