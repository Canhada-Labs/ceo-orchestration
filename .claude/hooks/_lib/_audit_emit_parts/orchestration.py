"""Orchestration.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_audit_producer_path_pollution_detected', '_COOKBOOK_PATTERN_ADVISED_ALLOWLIST', 'emit_cookbook_pattern_advised', '_PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST', 'emit_pair_rail_phase_advanced', '_BATCH_DISPATCHED_ALLOWLIST', 'emit_batch_dispatched', '_MCP_ROUTE_ADVISED_ALLOWLIST', 'emit_mcp_route_advised', '_try_rate_admit', 'emit_kernel_extension_landed', 'emit_bash_canonical_bypass_invoked', 'emit_sentinel_signer_rotated', 'emit_sentinel_signer_expiry_warned', 'emit_sentinel_signer_revoked', 'emit_sentinel_signer_quorum_failed', 'emit_sentinel_signer_quorum_attempted', '_PLAN090_STREAM_BUCKETS', '_PLAN090_STREAM_BURST', '_PLAN090_STREAM_REFILL_PER_MIN', '_PLAN090_PERSONA_BUCKETS', '_PLAN090_PERSONA_BURST', '_PLAN090_PERSONA_REFILL_PER_MIN', '_VERBOSE_STREAM_ENV', '_VERBOSE_STREAM_ARMED_VALUE')

def emit_audit_producer_path_pollution_detected(
    *,
    chokepoint: str,
    reason_code: str,
    path_sha256_prefix: str,
    expected_canonical_prefix: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """PLAN-118 AC-B5 — emit ``audit_producer_path_pollution_detected``.

    Closed-enum forensic breadcrumb invoked from the marker chokepoint
    (3) AND the spool-drain chokepoint (5) when the canonical-resolution
    check (audit_hmac._ensure_canonical_lib_modules) detects a stale
    `_lib` copy on sys.path. Both enums are deny-by-default; out-of-enum
    values DROP the event with a length-only breadcrumb (NO free-text
    into errors sidecar per
    [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    The two 8-hex-prefix fields are validated for shape too.

    Safe from recursion: this typed wrapper writes via ``_write_event``
    which itself goes through HMAC computation — and the producer is
    polluted. The recursion-safety pattern (per PLAN-118 §Producer
    runtime fail-CLOSED layer) is that the marker chokepoint (case 3)
    writes the breadcrumb via the fast-path ``open(path, 'a')`` directly
    (NOT this wrapper); spool_drain (case 5) uses this wrapper, accepting
    that its OWN HMAC will land as ``hmac:null`` + the same
    ``hmac_error`` channel — which is exactly the breadcrumb's purpose.
    """
    cp = str(chokepoint)
    if cp not in _AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS:
        _breadcrumb(
            "emit_audit_producer_path_pollution_detected dropped: "
            f"chokepoint not in closed enum (len={len(cp)})"
        )
        return
    rc = str(reason_code)
    if rc not in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
        _breadcrumb(
            "emit_audit_producer_path_pollution_detected dropped: "
            f"reason_code not in closed enum (len={len(rc)})"
        )
        return
    psp = str(path_sha256_prefix)
    ecp = str(expected_canonical_prefix)
    for name, val in (("path_sha256_prefix", psp), ("expected_canonical_prefix", ecp)):
        if len(val) != 8 or not all(c in "0123456789abcdef" for c in val):
            _breadcrumb(
                "emit_audit_producer_path_pollution_detected dropped: "
                f"{name} not 8 hex chars (len={len(val)})"
            )
            return
    raw_event: Dict[str, Any] = {
        "action": "audit_producer_path_pollution_detected",
        "session_id": session_id,
        "project": project,
        "chokepoint": cp,
        "reason_code": rc,
        "path_sha256_prefix": psp,
        "expected_canonical_prefix": ecp,
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W3.2 SEMI-11: cookbook_pattern_advised (UX hint) ------------------

_COOKBOOK_PATTERN_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "task_signature", "top_pattern_keys", "pattern_count",
})


def emit_cookbook_pattern_advised(
    *,
    session_id: str = "",
    task_signature: str = "",
    top_pattern_keys: str = "",
    pattern_count: int = 0,
    project: str = "",
) -> None:
    """Emit cookbook_pattern_advised (PLAN-088 W3.2 SEMI-11).

    UX hint telemetry. task_signature ∈ {skill-author, plan-draft, other}.
    top_pattern_keys is a comma-joined list bounded to 128 chars.
    """
    if not _plan088_rate_admit("cookbook_pattern_advised"):
        return
    raw_event: Dict[str, Any] = {
        "action": "cookbook_pattern_advised",
        "session_id": session_id,
        "project": project,
        "task_signature": (task_signature or "")[:32],
        "top_pattern_keys": _plan088_payload_cap((top_pattern_keys or "")[:128]),
        "pattern_count": max(0, int(pattern_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _COOKBOOK_PATTERN_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W4.1 AUTO-07: pair_rail_phase_advanced (dual-rail check) ----------

_PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "from_phase", "to_phase", "samples_observed", "signal_source",
    "time_elapsed_seconds",
})


def emit_pair_rail_phase_advanced(
    *,
    session_id: str = "",
    from_phase: str = "",
    to_phase: str = "",
    samples_observed: int = 0,
    signal_source: str = "",
    time_elapsed_seconds: int = 0,
    project: str = "",
) -> None:
    """Emit pair_rail_phase_advanced (PLAN-088 W4.1 AUTO-07).

    ATLAS: AML.T0050 (LLM Plugin Compromise dual-rail check). Fires on
    Pair-Rail phase transition SHADOW → DRY_RUN (Phase C is
    [DEFERRED-TO-PLAN-090] per M-6 scope amendment).

    signal_source carries persona-detection telemetry per M-10
    (env-var / cli-flag / heuristic). The dedicated `persona_detected`
    action was STRICKEN per R2 iter-1 C2 strict-13 cardinality fold;
    persona is now implicit in this payload field.
    """
    if not _plan088_rate_admit("pair_rail_phase_advanced"):
        return
    raw_event: Dict[str, Any] = {
        "action": "pair_rail_phase_advanced",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("pair_rail_phase_advanced", "AML.T0050"),
        "from_phase": (from_phase or "")[:32],
        "to_phase": (to_phase or "")[:32],
        "samples_observed": max(0, int(samples_observed)),
        "signal_source": (signal_source or "")[:32],
        "time_elapsed_seconds": max(0, int(time_elapsed_seconds)),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W4.2 AUTO-08: batch_dispatched (cost-optimization telemetry) ------

_BATCH_DISPATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "phase", "request_count", "estimated_savings_basis_points",
    "trigger_source",
})


def emit_batch_dispatched(
    *,
    session_id: str = "",
    phase: str = "dispatched",
    request_count: int = 0,
    estimated_savings_basis_points: int = 0,
    trigger_source: str = "",
    project: str = "",
) -> None:
    """Emit batch_dispatched (PLAN-088 W4.2 AUTO-08).

    Single canonical-13 action covers BOTH endpoint phases via the
    `phase` field: `dispatched` (request submitted) / `completed`
    (response received). The earlier `batch_completed` separate-action
    framing was STRICKEN per R2 iter-1 C2 strict-13 cardinality fold.
    """
    if not _plan088_rate_admit("batch_dispatched"):
        return
    sav_bp = max(0, min(1000, int(estimated_savings_basis_points)))
    raw_event: Dict[str, Any] = {
        "action": "batch_dispatched",
        "session_id": session_id,
        "project": project,
        "phase": (phase or "")[:32],
        "request_count": max(0, int(request_count)),
        "estimated_savings_basis_points": sav_bp,
        "trigger_source": (trigger_source or "")[:32],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _BATCH_DISPATCHED_ALLOWLIST
    )
    _write_event(cleaned)


# Wave 2.2 + Wave 3.1 — production callsite wires for pre-existing stubs.
# `model_routing_advised` (PLAN-078) + `mcp_route_advised` (PLAN-086 Wave D)
# are already registered; PLAN-088 attaches ATLAS-bound telemetry by
# extending allowlists in-place. The wrappers `emit_model_routing_advised`
# (line ~3484) + future `emit_mcp_route_advised` retain existing semantics.
# The W3.1 wrapper is added next to keep ADR-114 egress symmetry intact.

_MCP_ROUTE_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "task_class", "suggested_servers", "kill_switch_overrides",
    "signal_source",
})


def emit_mcp_route_advised(
    *,
    session_id: str = "",
    task_class: str = "",
    suggested_servers: str = "",
    kill_switch_overrides: str = "",
    signal_source: str = "",
    project: str = "",
) -> None:
    """Emit mcp_route_advised (PLAN-088 W3.1 / W3.3 AUTO-06 / AUTO-10).

    ATLAS: AML.T0050 (LLM Plugin / supply-chain signal). Single canonical-13
    action covers both AUTO-06 MCP routing AND AUTO-10 general→specialized
    promotion via `signal_source` payload discriminator (per R2 iter-2
    strict-13 cardinality — `specialization_promoted` separate action was
    STRICKEN).

    `signal_source` ∈ {mcp_task_class, specialization_promoted}.
    `suggested_servers` is a comma-joined list of MCP server names (bounded
    to 128 chars); `kill_switch_overrides` enumerates env-vars currently
    overriding routing decisions (bounded to 128 chars).
    """
    if not _plan088_rate_admit("mcp_route_advised"):
        return
    raw_event: Dict[str, Any] = {
        "action": "mcp_route_advised",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("mcp_route_advised", "AML.T0050"),
        "task_class": (task_class or "")[:32],
        "suggested_servers": _plan088_payload_cap((suggested_servers or "")[:128]),
        "kill_switch_overrides": _plan088_payload_cap((kill_switch_overrides or "")[:128]),
        "signal_source": (signal_source or "")[:32],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _MCP_ROUTE_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)


# === End PLAN-088 canonical-13 god-mode auto-activation block =================



# ---------------------------------------------------------------------
# PLAN-089 Wave C.5 — kernel + auth hardening emit helpers
# ---------------------------------------------------------------------
#
# ATT&CK bindings (Enterprise, not ATLAS) per ADR-121 §7:
#   T1556       — Modify Authentication Process (signer lifecycle)
#   T1565.001   — Stored Data Manipulation (canonical kernel surface)
#   T1584       — Compromise Infrastructure (IR scenario; not single-event)
#
# Rate-cap: `sentinel_signer_expiry_warned` 1×/hour throttled at the
# caller via the standard `_plan088_rate_admit` helper (best-effort —
# falls open if missing).


def _try_rate_admit(action: str) -> bool:
    """Best-effort rate gate. Returns True (admit) if no gate available."""
    try:
        gate = globals().get("_plan088_rate_admit")
        if callable(gate):
            return bool(gate(action))
    except Exception:  # pragma: no cover
        pass
    return True


def emit_kernel_extension_landed(
    *,
    plan_id: str = "",
    wave: str = "",
    entries_added: int = 0,
    cardinality_after: int = 0,
    ceremony_sha: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit kernel_extension_landed (PLAN-089 Wave A.4 / T1565.001)."""
    emit_generic(
        "kernel_extension_landed",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "kernel_extension_landed", "T1565.001"
        ),
        plan_id=plan_id,
        wave=wave,
        entries_added=int(entries_added),
        cardinality_after=int(cardinality_after),
        ceremony_sha=ceremony_sha[:64],
    )


def emit_bash_canonical_bypass_invoked(
    *,
    token_hash_prefix: str = "",
    target_path_hash: str = "",
    ticket_expires_in_s: int = 0,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit bash_canonical_bypass_invoked (PLAN-089 Wave B.4 / T1565.001).

    NEVER persist raw token. ``token_hash_prefix`` is the first 8 hex
    chars of sha256(token). FPR budget ≤3/week per ADR-121 §4.
    Sec MF-3: ``target_path_hash`` is the first 12 hex chars of
    sha256(normalized_target) — no raw filesystem path is persisted.
    """
    emit_generic(
        "bash_canonical_bypass_invoked",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "bash_canonical_bypass_invoked", "T1565.001"
        ),
        token_hash_prefix=token_hash_prefix[:16],
        target_path_hash=target_path_hash[:12],
        ticket_expires_in_s=int(ticket_expires_in_s),
    )


def emit_sentinel_signer_rotated(
    *,
    key_id: str = "",
    key_type: str = "",
    rotated_from_key_id: str = "",
    rotated_by: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_rotated (PLAN-089 Wave C.5 / T1556)."""
    emit_generic(
        "sentinel_signer_rotated",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_rotated", "T1556"
        ),
        key_id=key_id[:80],
        key_type=key_type[:16],
        rotated_from_key_id=rotated_from_key_id[:80],
        rotated_by=rotated_by[:80],
    )


def emit_sentinel_signer_expiry_warned(
    *,
    key_id: str = "",
    days_remaining: int = 0,
    expires_at_iso: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_expiry_warned (PLAN-089 Wave C.5 / T1556).

    Rate-capped 1×/hour via best-effort `_plan088_rate_admit` helper.
    """
    if not _try_rate_admit("sentinel_signer_expiry_warned"):
        return
    emit_generic(
        "sentinel_signer_expiry_warned",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_expiry_warned", "T1556"
        ),
        key_id=key_id[:80],
        days_remaining=int(days_remaining),
        expires_at_iso=expires_at_iso[:40],
    )


def emit_sentinel_signer_revoked(
    *,
    key_id: str = "",
    key_type: str = "",
    revoked_by: str = "",
    reason: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_revoked (PLAN-089 Wave C.5 / T1556).

    Separate from _rotated per R1 IDA P0 — explicit revocation channel
    for compromised-but-not-expired keys.
    """
    emit_generic(
        "sentinel_signer_revoked",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_revoked", "T1556"
        ),
        key_id=key_id[:80],
        key_type=key_type[:16],
        revoked_by=revoked_by[:80],
        reason=reason[:200],
    )


def emit_sentinel_signer_quorum_failed(
    *,
    key_id: str = "",
    reason: str = "",
    source: str = "",
    distinct_signers: int = 0,
    threshold_required: int = 0,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_quorum_failed (PLAN-089 Wave C.5 / T1556).

    R1 TDE P0 fold — SOC consumption canary. Without this, cold-key
    compromise scenarios are undetectable until a successful rotation
    completes.
    """
    emit_generic(
        "sentinel_signer_quorum_failed",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_quorum_failed", "T1556"
        ),
        key_id=key_id[:80],
        reason=reason[:200],
        source=source[:80],
        distinct_signers=int(distinct_signers),
        threshold_required=int(threshold_required),
    )


def emit_sentinel_signer_quorum_attempted(
    *,
    distinct_signers: int = 0,
    threshold_required: int = 0,
    outcome: str = "",
    source: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_quorum_attempted (PLAN-089 Wave C.5 / T1556).

    R1 IDA P2 fold — forensic completeness regardless of outcome.
    Fires for ALL quorum invocations (success + failure), enabling
    detection of brute-force quorum probing.
    """
    emit_generic(
        "sentinel_signer_quorum_attempted",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_quorum_attempted", "T1556"
        ),
        distinct_signers=int(distinct_signers),
        threshold_required=int(threshold_required),
        outcome=outcome[:32],
        source=source[:80],
    )


# =============================================================================
# PLAN-090 Wave A.4 + B.5 + C.2 §B + A.10 — typed emit wrappers + helpers.
# =============================================================================

_PLAN090_STREAM_BUCKETS: Dict[str, Tuple[float, int]] = {}


_PLAN090_STREAM_BURST = 10


_PLAN090_STREAM_REFILL_PER_MIN = 5


_PLAN090_PERSONA_BUCKETS: Dict[str, Tuple[float, int]] = {}


_PLAN090_PERSONA_BURST = 10


_PLAN090_PERSONA_REFILL_PER_MIN = 5


_VERBOSE_STREAM_ENV = "CEO_AUDIT_STREAM_VERBOSE"


_VERBOSE_STREAM_ARMED_VALUE = "1"
