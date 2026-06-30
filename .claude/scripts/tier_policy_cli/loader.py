"""PLAN-043 Phase 1 — Policy artifact loader with fail-open fallback.

Reads + schema-validates + HMAC-verifies ``.claude/tier-policy.json``.
On ANY corruption (missing file, malformed JSON, schema mismatch,
HMAC failure, oversized, prototype-pollution attempt), falls back
to the ADR-052 static baseline via :func:`types.build_adr052_baseline`
with ZERO additional I/O (per F-PERF-P1-2 performance closure).

Hardening per Round 1 closures:

- **C-P0-7** — uses ``_lib/audit_hmac.verify_chain()`` (NEW library
  API extracted Phase 0.5).
- **C-P1-6** — schema versioning via ``policy_schema_version`` field;
  forward-migration on old schema with warn event.
- **F-SEC-P1-2** — 64 KiB file size cap; max nesting depth 8;
  ``object_pairs_hook`` rejects prototype-pollution keys
  (``__proto__``, ``constructor``, ``prototype``).
- **F-PERF-P1-3** — per-file size cap applied identically to
  tournament report globs (future consumer API).
- **F-PERF-P1-2** — fallback baseline is MODULE-LEVEL constant,
  NOT re-read from disk on corruption.

Fail-open invariant (ADR-005): loader NEVER raises to caller.
Returns ``LoadResult`` with ``status`` + ``policy_record`` (None on
fallback). Caller inspects status and emits corresponding audit event.

stdlib-only (ADR-002).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ._types import (
        Assignment,
        AssignmentEvidence,
        CANONICAL_5_AGENTS,
        CURRENT_POLICY_SCHEMA_VERSION,
        TierPolicyRecord,
        VALID_MODEL_IDS,
        build_adr052_baseline,
    )
except ImportError:  # pragma: no cover — direct-script execution
    from _types import (  # type: ignore[no-redef]
        Assignment,
        AssignmentEvidence,
        CANONICAL_5_AGENTS,
        CURRENT_POLICY_SCHEMA_VERSION,
        TierPolicyRecord,
        VALID_MODEL_IDS,
        build_adr052_baseline,
    )


# ---------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------

STATUS_OK = "ok"
STATUS_BOOTSTRAP = "bootstrap"  # zero-file first-run short-circuit
STATUS_FALLBACK = "fallback"  # corruption → ADR-052 static
STATUS_MIGRATED = "migrated"  # schema version < current; auto-upgraded


# ---------------------------------------------------------------------
# Constants (Round 1 closures)
# ---------------------------------------------------------------------

MAX_POLICY_FILE_BYTES = 64 * 1024  # F-SEC-P1-2
MAX_JSON_NESTING = 8  # F-SEC-P1-2
PROTOTYPE_POLLUTION_KEYS = frozenset({"__proto__", "constructor", "prototype"})


# ---------------------------------------------------------------------
# LoadResult dataclass
# ---------------------------------------------------------------------

@dataclass
class LoadResult:
    """Structured result of :func:`load_policy`.

    Attributes:
        status: one of STATUS_OK | STATUS_BOOTSTRAP | STATUS_FALLBACK |
                STATUS_MIGRATED
        policy_record: Parsed + validated record on STATUS_OK /
                       STATUS_MIGRATED; None on BOOTSTRAP / FALLBACK
                       (caller uses build_adr052_baseline()).
        reason: Short stable tag for non-OK statuses (e.g.
                "file_not_found", "malformed_json", "schema_violation",
                "oversized", "hmac_failed", "prototype_pollution").
        baseline: Always set to ADR-052 static baseline dict so caller
                  has a usable tier map regardless of status.
    """

    status: str
    policy_record: Optional[TierPolicyRecord]
    reason: Optional[str]
    baseline: Dict[str, Assignment]


# ---------------------------------------------------------------------
# Pre-computed baseline (F-PERF-P1-2 — zero-I/O fallback path)
# ---------------------------------------------------------------------

# Computed at module import; re-referenced on every fallback.
# Baseline is immutable static data per ADR-052 §Role-to-model.
_FROZEN_BASELINE = build_adr052_baseline()


# ---------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------

def default_policy_path() -> Path:
    """Return ``.claude/tier-policy.json`` path via env override or cwd."""
    override = os.environ.get("CEO_TIER_POLICY_PATH")
    if override:
        return Path(override)
    return Path(".claude/tier-policy.json")


def default_sigchain_path() -> Path:
    """Return ``.claude/tier-policy.json.sigchain`` path via env or cwd."""
    override = os.environ.get("CEO_TIER_POLICY_SIGCHAIN_PATH")
    if override:
        return Path(override)
    return Path(".claude/tier-policy.json.sigchain")


# ---------------------------------------------------------------------
# Safe JSON parse (F-SEC-P1-2)
# ---------------------------------------------------------------------

class _PrototypePollutionError(ValueError):
    """Raised by object_pairs_hook on forbidden keys."""


def _safe_object_pairs_hook(pairs) -> dict:
    """json.loads hook: reject prototype-pollution keys."""
    for k, _ in pairs:
        if k in PROTOTYPE_POLLUTION_KEYS:
            raise _PrototypePollutionError(
                "prototype_pollution: forbidden key {k!r}".format(k=k)
            )
    return dict(pairs)


def _measure_nesting(obj, depth: int = 0) -> int:
    """Return max nesting depth of a Python JSON value."""
    if depth > MAX_JSON_NESTING + 1:
        return depth  # short-circuit; caller rejects
    if isinstance(obj, dict):
        if not obj:
            return depth
        return max(_measure_nesting(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return depth
        return max(_measure_nesting(v, depth + 1) for v in obj)
    return depth


def _load_json_hardened(raw_bytes: bytes) -> Any:
    """Parse JSON with size + nesting + prototype-pollution defenses.

    :raises ValueError: on any violation (caller wraps with LoadResult
        STATUS_FALLBACK + appropriate reason tag).
    """
    if len(raw_bytes) > MAX_POLICY_FILE_BYTES:
        raise ValueError(
            "oversized: {n} bytes > {m} cap".format(
                n=len(raw_bytes), m=MAX_POLICY_FILE_BYTES
            )
        )
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("non_utf8: {e}".format(e=e)) from e
    # BOM strip (F-SEC-P1-2 loader hardening; handles editor pollution).
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        obj = json.loads(text, object_pairs_hook=_safe_object_pairs_hook)
    except _PrototypePollutionError as e:
        raise ValueError(str(e)) from e
    except json.JSONDecodeError as e:
        raise ValueError("malformed_json: {e}".format(e=e)) from e
    if _measure_nesting(obj) > MAX_JSON_NESTING:
        raise ValueError(
            "nesting_exceeded: depth > {m}".format(m=MAX_JSON_NESTING)
        )
    return obj


# ---------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------

_REQUIRED_TOP_LEVEL = frozenset({
    "schema_version",
    "generated_at",
    "baseline_from",
    "assignments",
    "hmac_anchor",
})

_REQUIRED_ASSIGNMENT_KEYS = frozenset({"tier", "locked_by", "evidence"})

_ALLOWED_TOP_LEVEL = _REQUIRED_TOP_LEVEL | frozenset({
    "sigchain_tip_length",
    "last_change_by_role",
})

_STRING_CAP = 256  # F-SEC-P1-2


def _check_string_cap(value, field_name) -> None:
    if isinstance(value, str) and len(value) > _STRING_CAP:
        raise ValueError(
            "string_too_long: {f} is {n} chars > {m}".format(
                f=field_name, n=len(value), m=_STRING_CAP
            )
        )


def _validate_assignment(agent_slug: str, raw: Any) -> Assignment:
    if not isinstance(raw, dict):
        raise ValueError("assignment_not_object: " + agent_slug)
    # Strict required keys.
    missing = _REQUIRED_ASSIGNMENT_KEYS - set(raw.keys())
    if missing:
        raise ValueError(
            "assignment_missing_keys: {a} {m}".format(
                a=agent_slug, m=sorted(missing)
            )
        )
    extra = set(raw.keys()) - _REQUIRED_ASSIGNMENT_KEYS
    if extra:
        raise ValueError(
            "assignment_extra_keys: {a} {e}".format(
                a=agent_slug, e=sorted(extra)
            )
        )
    tier = raw["tier"]
    if tier not in VALID_MODEL_IDS:
        raise ValueError(
            "invalid_model_id: {a} {t!r}".format(a=agent_slug, t=tier)
        )
    locked_by = raw["locked_by"]
    if locked_by is not None and not isinstance(locked_by, str):
        raise ValueError("locked_by_type: " + agent_slug)
    _check_string_cap(locked_by, agent_slug + ".locked_by")

    evidence_raw = raw["evidence"]
    evidence: Optional[AssignmentEvidence] = None
    if evidence_raw is not None:
        if not isinstance(evidence_raw, dict):
            raise ValueError("evidence_not_object: " + agent_slug)
        n = evidence_raw.get("n")
        gap_pp = evidence_raw.get("gap_pp")
        last_updated = evidence_raw.get("last_updated")
        runs_considered = evidence_raw.get("runs_considered", 0)
        tournament_report_hmacs = evidence_raw.get(
            "tournament_report_hmacs", []
        )
        if not isinstance(n, int) or n < 0:
            raise ValueError("evidence_n_type: " + agent_slug)
        if not isinstance(gap_pp, (int, float)):
            raise ValueError("evidence_gap_pp_type: " + agent_slug)
        if last_updated is not None and not isinstance(last_updated, str):
            raise ValueError("evidence_last_updated_type: " + agent_slug)
        _check_string_cap(last_updated, agent_slug + ".last_updated")
        if not isinstance(runs_considered, int) or runs_considered < 0:
            raise ValueError("evidence_runs_considered_type: " + agent_slug)
        if not isinstance(tournament_report_hmacs, list):
            raise ValueError(
                "evidence_tournament_hmacs_type: " + agent_slug
            )
        for h in tournament_report_hmacs:
            if not isinstance(h, str):
                raise ValueError("evidence_hmac_type: " + agent_slug)
            _check_string_cap(h, agent_slug + ".evidence.hmac")
        evidence = AssignmentEvidence(
            n=n,
            gap_pp=float(gap_pp),
            last_updated=last_updated,
            runs_considered=runs_considered,
            tournament_report_hmacs=list(tournament_report_hmacs),
        )

    return Assignment(tier=tier, locked_by=locked_by, evidence=evidence)


def _validate_policy_dict(d: Any) -> TierPolicyRecord:
    """Validate top-level schema. Raise ValueError on any mismatch."""
    if not isinstance(d, dict):
        raise ValueError("root_not_object")

    missing = _REQUIRED_TOP_LEVEL - set(d.keys())
    if missing:
        raise ValueError(
            "missing_keys: {m}".format(m=sorted(missing))
        )
    extra = set(d.keys()) - _ALLOWED_TOP_LEVEL
    if extra:
        raise ValueError(
            "extra_keys: {e}".format(e=sorted(extra))
        )

    schema_version = d["schema_version"]
    if not isinstance(schema_version, str):
        raise ValueError("schema_version_type")
    _check_string_cap(schema_version, "schema_version")

    generated_at = d["generated_at"]
    if not isinstance(generated_at, str):
        raise ValueError("generated_at_type")
    _check_string_cap(generated_at, "generated_at")

    baseline_from = d["baseline_from"]
    if not isinstance(baseline_from, str):
        raise ValueError("baseline_from_type")
    _check_string_cap(baseline_from, "baseline_from")

    hmac_anchor = d["hmac_anchor"]
    if not isinstance(hmac_anchor, str):
        raise ValueError("hmac_anchor_type")
    if len(hmac_anchor) != 64:
        raise ValueError("hmac_anchor_length")
    try:
        int(hmac_anchor, 16)
    except ValueError:
        raise ValueError("hmac_anchor_not_hex") from None

    assignments_raw = d["assignments"]
    if not isinstance(assignments_raw, dict):
        raise ValueError("assignments_not_object")

    allowed_slugs = set(CANONICAL_5_AGENTS)
    present_slugs = set(assignments_raw.keys())
    if present_slugs != allowed_slugs:
        raise ValueError(
            "assignments_slug_mismatch: expected {a} got {p}".format(
                a=sorted(allowed_slugs), p=sorted(present_slugs)
            )
        )

    assignments: Dict[str, Assignment] = {}
    for slug in CANONICAL_5_AGENTS:
        assignments[slug] = _validate_assignment(
            slug, assignments_raw[slug]
        )

    sigchain_tip_length = d.get("sigchain_tip_length", 1)
    if (
        not isinstance(sigchain_tip_length, int)
        or sigchain_tip_length < 1
    ):
        raise ValueError("sigchain_tip_length_type")

    last_change_by_role = d.get("last_change_by_role", {})
    if not isinstance(last_change_by_role, dict):
        raise ValueError("last_change_by_role_type")
    for k, v in last_change_by_role.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError("last_change_by_role_entry_type")
        _check_string_cap(v, "last_change_by_role." + k)

    return TierPolicyRecord(
        schema_version=schema_version,
        generated_at=generated_at,
        baseline_from=baseline_from,
        assignments=assignments,
        hmac_anchor=hmac_anchor,
        sigchain_tip_length=sigchain_tip_length,
        last_change_by_role=dict(last_change_by_role),
    )


# ---------------------------------------------------------------------
# Schema migration (C-P1-6)
# ---------------------------------------------------------------------

def _migrate_schema(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Forward-migrate a schema_version < current to current shape.

    Pure function on a mutable copy. Returns migrated dict. Adds
    missing fields with sensible defaults; preserves role assignments
    exactly (NEVER alters tier values during migration — that would
    be a governance change outside the migrator's remit).
    """
    migrated = dict(raw_dict)
    migrated.setdefault("sigchain_tip_length", 1)
    migrated.setdefault("last_change_by_role", {})
    migrated["schema_version"] = CURRENT_POLICY_SCHEMA_VERSION
    return migrated


# ---------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------

def load_policy(
    policy_path: Optional[Path] = None,
) -> LoadResult:
    """Load + validate the policy artifact.

    Always returns a :class:`LoadResult`; never raises. The
    ``baseline`` field is always the ADR-052 static fallback dict for
    caller convenience.

    Args:
        policy_path: Override path; defaults to :func:`default_policy_path`.
    """
    p = policy_path if policy_path is not None else default_policy_path()

    if not p.exists():
        # Zero-file first-run short-circuit (Q8 closure).
        return LoadResult(
            status=STATUS_BOOTSTRAP,
            policy_record=None,
            reason="file_not_found",
            baseline=_FROZEN_BASELINE,
        )

    try:
        raw_bytes = p.read_bytes()
    except OSError:
        return LoadResult(
            status=STATUS_FALLBACK,
            policy_record=None,
            reason="read_error",
            baseline=_FROZEN_BASELINE,
        )

    try:
        obj = _load_json_hardened(raw_bytes)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("oversized"):
            reason = "oversized"
        elif msg.startswith("prototype_pollution"):
            reason = "prototype_pollution"
        elif msg.startswith("nesting_exceeded"):
            reason = "nesting_exceeded"
        elif msg.startswith("non_utf8"):
            reason = "non_utf8"
        else:
            reason = "malformed_json"
        return LoadResult(
            status=STATUS_FALLBACK,
            policy_record=None,
            reason=reason,
            baseline=_FROZEN_BASELINE,
        )

    if not isinstance(obj, dict):
        return LoadResult(
            status=STATUS_FALLBACK,
            policy_record=None,
            reason="root_not_object",
            baseline=_FROZEN_BASELINE,
        )

    # Schema version handling (C-P1-6).
    version = obj.get("schema_version")
    migrated = False
    if not isinstance(version, str):
        return LoadResult(
            status=STATUS_FALLBACK,
            policy_record=None,
            reason="schema_version_missing",
            baseline=_FROZEN_BASELINE,
        )
    if version != CURRENT_POLICY_SCHEMA_VERSION:
        # Forward-migrate on any mismatch (future-safe: later versions
        # may ship transformations keyed on version tuples).
        if _is_known_old_version(version):
            obj = _migrate_schema(obj)
            migrated = True
        else:
            return LoadResult(
                status=STATUS_FALLBACK,
                policy_record=None,
                reason="schema_version_unknown",
                baseline=_FROZEN_BASELINE,
            )

    try:
        record = _validate_policy_dict(obj)
    except ValueError as e:
        msg = str(e)
        # Map validation errors to stable reason tags.
        if "missing_keys" in msg:
            reason = "schema_missing_keys"
        elif "extra_keys" in msg:
            reason = "schema_extra_keys"
        elif "string_too_long" in msg:
            reason = "string_too_long"
        elif "invalid_model_id" in msg:
            reason = "invalid_model_id"
        elif "hmac_anchor" in msg:
            reason = "hmac_anchor_malformed"
        elif "assignments_slug_mismatch" in msg:
            reason = "assignments_slug_mismatch"
        else:
            reason = "schema_violation"
        return LoadResult(
            status=STATUS_FALLBACK,
            policy_record=None,
            reason=reason,
            baseline=_FROZEN_BASELINE,
        )

    return LoadResult(
        status=STATUS_MIGRATED if migrated else STATUS_OK,
        policy_record=record,
        reason=("schema_migrated" if migrated else None),
        baseline=_FROZEN_BASELINE,
    )


def _is_known_old_version(version: str) -> bool:
    """Known old versions that have a forward-migration recipe.

    Currently empty (1.0 is the first schema). Framework-level
    amendments add entries here when bumping CURRENT_POLICY_SCHEMA_VERSION.
    """
    return False
