"""Security.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_prompt_injection_detected', 'emit_ledger_entry_rejected', 'emit_session_memory_delta_observed', 'emit_secret_leak_detected', 'emit_pii_redacted_outgoing', 'emit_codex_egress_redacted', 'emit_pair_rail_outgoing_redaction_applied', 'emit_mcp_handler_invoked', 'emit_mcp_handler_denied', 'emit_mcp_cross_tenant_denied', 'emit_mcp_soak_fpr_breach')

def emit_prompt_injection_detected(
    *,
    signal: str = "",
    family: str = "",
    snippet_preview: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    triggered_by_tool: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit prompt_injection_detected event (PLAN-085 G.1b / AML.T0051).

    Detection of LLM prompt-injection patterns at hook/scanner layer.
    ``atlas_technique`` defaults to the immutable registry value;
    callers may override for sub-technique disambiguation.
    """
    emit_generic(
        "prompt_injection_detected",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["prompt_injection_detected"],
        signal=signal,
        family=family,
        snippet_preview=snippet_preview[:200],
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        triggered_by_tool=triggered_by_tool,
        session_id=session_id,
        project=project,
    )


def emit_ledger_entry_rejected(
    *,
    signal: str = "",
    decision: str = "reject",
    reason: str = "",
    family: str = "",
    hits_count: int = 0,
    bytes_scanned: int = 0,
    scanned: int = 0,
    enforced: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit ledger_entry_rejected (PLAN-179 W4 / ADR-195).

    The ledger write-gate refused an externally-sourced entry fail-CLOSED.
    Called by ``_lib/ledger_provenance._emit_rejection``; the keyword names
    mirror ``GateVerdict.to_audit_fields()`` EXACTLY, because that caller
    splats the dict (``typed(**fields)``) and a signature mismatch would
    look like a raising emitter and degrade the rail silently.

    Deliberately NO ``int()`` coercion here: the scrub branch is TYPE-strict
    and a float must become 0, not be rounded into the signed chain. The
    rejected entry BODY is not a parameter of this function at all — the
    gate never forwards it, not even truncated.
    """
    emit_generic(
        "ledger_entry_rejected",
        signal=signal or _LEDGER_GATE_SIGNAL,
        decision=decision,
        reason=reason,
        family=family,
        hits_count=hits_count,
        bytes_scanned=bytes_scanned,
        scanned=scanned,
        enforced=enforced,
        session_id=session_id,
        project=project,
    )


def emit_session_memory_delta_observed(
    *,
    outcome: str = "",
    files_count: int = 0,
    modified_count: int = 0,
    index_modified: bool = False,
    anchor_source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit session_memory_delta_observed (PLAN-179 W2 US8, SPEC v2.60).

    One emit per session from ``SessionEnd.py``, immediately before the
    ``session_end`` emit: a stat-only observation of activity in the shared
    project memory directory during this session's window, without proof
    of which session wrote it. Deliberately NO ``int()``
    coercion here: the scrub branch is TYPE-strict and a float must become
    0, not be rounded into the signed chain. The memory file NAMES are not
    a parameter of this function at all — the producer never forwards them
    (the producer renders counts on ``systemMessage``; the wire denies
    basenames by contract).
    """
    emit_generic(
        "session_memory_delta_observed",
        outcome=outcome,
        files_count=files_count,
        modified_count=modified_count,
        index_modified=index_modified,
        anchor_source=anchor_source,
        session_id=session_id,
        project=project,
    )


def emit_secret_leak_detected(
    *,
    signal: str = "",
    family: str = "",
    snippet_preview: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    triggered_by_tool: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit secret_leak_detected event (PLAN-085 G.1b / AML.T0024.001).

    Detection of credential/secret patterns in payloads or egress.
    """
    emit_generic(
        "secret_leak_detected",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["secret_leak_detected"],
        signal=signal,
        family=family,
        snippet_preview=snippet_preview[:200],
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        triggered_by_tool=triggered_by_tool,
        session_id=session_id,
        project=project,
    )


def emit_pii_redacted_outgoing(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit pii_redacted_outgoing event (PLAN-085 G.1b / AML.T0048.004).

    PII categories detected + scrubbed in outgoing payload (egress
    redaction success). Audit forensic trail.
    """
    emit_generic(
        "pii_redacted_outgoing",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["pii_redacted_outgoing"],
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        session_id=session_id,
        project=project,
    )


def emit_codex_egress_redacted(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    callsite: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit codex_egress_redacted event (PLAN-085 G.1b / AML.T0054).

    Codex MCP egress redactor scrubbed canonical jailbreak/injection
    patterns from outgoing prompt. Composition with Wave B.4 fail-CLOSED
    inversion (RedactorImportFailed surfaces on import failure).
    """
    emit_generic(
        "codex_egress_redacted",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["codex_egress_redacted"],
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        callsite=callsite,
        session_id=session_id,
        project=project,
    )


def emit_pair_rail_outgoing_redaction_applied(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    callsite: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit pair_rail_outgoing_redaction_applied (ADR-114; F-7.9 positive proof).

    The OUTBOUND pair-rail egress redactor (framework → Codex/external LLM)
    scrubbed the outgoing prompt. Emitted on EVERY redaction call, INCLUDING
    when the findings list is empty (``match_count=0`` is positive proof the
    redaction path was exercised). Content-field-free per Sec MF-3 — the
    dispatch gate routes through _PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
    which excludes ``text``/``prompt``/``match_value``. Mirrors
    ``emit_codex_egress_redacted``'s signature.
    """
    emit_generic(
        "pair_rail_outgoing_redaction_applied",
        atlas_technique=atlas_technique or "AML.T0054",
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        callsite=callsite,
        session_id=session_id,
        project=project,
    )


def emit_mcp_handler_invoked(
    handler: str,
    client_id: str,
    transport: str,
    duration_ms: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_handler_invoked event (ADR-042 §Auth).

    Fired on every successful handler entry AFTER auth + ACL + rate-limit
    pass. ``client_id`` is the 16-hex opaque identifier (never the token
    itself). ``transport`` ∈ {"http", "stdio"}. ``handler`` ∈ the 7 handler
    names registered in ADR-042 §Auth.2 ACL.
    """
    event: Dict[str, Any] = {
        "action": "mcp_handler_invoked",
        "handler": handler,
        "client_id": client_id,
        "transport": transport,
        "duration_ms": int(duration_ms),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_handler_denied(
    handler: str,
    client_id: str,
    transport: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_handler_denied event (ADR-042 §Auth.5).

    ``reason`` is the closed enum: acl_missing_handler | rate_limit |
    timestamp_skew | cors_default_deny | auth_hmac_invalid |
    auth_token_malformed | budget_hard_stop_per_spawn |
    budget_hard_stop_per_plan_5min | debate_max_rounds | breaker_open |
    plan_id_unknown. Token value MUST NOT appear anywhere (ADR-042
    §Auth.6 hygiene).
    """
    event: Dict[str, Any] = {
        "action": "mcp_handler_denied",
        "handler": handler,
        "client_id": client_id,
        "transport": transport,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_cross_tenant_denied(
    handler: str,
    caller_client_id_hash: str,
    target_client_id_hash: str,
    transport: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_cross_tenant_denied event (ADR-042-AMEND-1 §6.2).

    Fires when a get_cost_budget call with scope=caller attempts to
    read a target_client_id different from the caller's own. The
    caller/target identifiers are HASHED via auth.hash_client_id
    before serialization (Sec MF-3 hygiene).
    """
    event: Dict[str, Any] = {
        "action": "mcp_cross_tenant_denied",
        "handler": handler,
        "caller_client_id_hash": caller_client_id_hash,
        "target_client_id_hash": target_client_id_hash,
        "transport": transport,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_soak_fpr_breach(
    window_days: int,
    fpr_observed: float,
    threshold: float,
    top_deny_reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_soak_fpr_breach event (ADR-042-AMEND-1 §6.2 / AC-F-4).

    Fires when 7-day rolling FPR > threshold (default 0.01 = 1%).
    Fires AT MOST once per breach day; the soak monitor enforces
    dedup against the most recent emit.

    Float fields are encoded as integers to satisfy the canonical_json
    no-float invariant on HMAC-covered audit events:

    - ``fpr_observed``  → ``fpr_observed_bps``  (rate × 10000, 0..10000+)
    - ``threshold``     → ``threshold_bps``     (rate × 10000, 0..10000+)

    Example: FPR 0.01 (1%) → 100 bps; threshold 0.01 → 100 bps.
    Readers must divide by 10000 to recover the original rate.
    """
    event: Dict[str, Any] = {
        "action": "mcp_soak_fpr_breach",
        "window_days": int(window_days),
        "fpr_observed_bps": max(0, int(round(float(fpr_observed) * 10000))),
        "threshold_bps": max(0, int(round(float(threshold) * 10000))),
        "top_deny_reason": str(top_deny_reason),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
