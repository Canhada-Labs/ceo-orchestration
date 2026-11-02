"""Adapters.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_live_adapter_call_started', 'emit_live_adapter_call_succeeded', 'emit_live_adapter_call_failed', 'emit_breaker_opened', 'emit_breaker_closed', 'emit_live_adapter_blocked', 'emit_credential_blocked_due_to_age', 'emit_credential_emergency_override_used', '_CREDENTIAL_OVERRIDE_VAR_NAME', '_CREDENTIAL_OVERRIDE_PROVENANCE_HINTS', 'emit_credential_override_late_set_ignored', 'emit_mcp_bearer_replay_rejected', 'emit_mcp_non_loopback_rejected', '_ATLAS_REGISTRY', '_ATLAS_NAMESPACE_REGISTRY')

# -----------------------------------------------------------------------------
# Sprint 13 Phase A.0 (PLAN-013 Gap #3) — Live adapter / breaker / credential
# -----------------------------------------------------------------------------


def emit_live_adapter_call_started(
    provider: str,
    url: str,
    attempt: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_started event (ADR-040 §7).

    Fired by ``_lib/adapters/live/_transport.py::post_json`` on every
    attempt (initial + retries). ``url`` MUST be query-scrubbed by
    the caller (_scrub_url_query). Credential values never appear.
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_started",
        "provider": provider,
        "url": url,
        "attempt": int(attempt),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_live_adapter_call_succeeded(
    provider: str,
    url: str,
    status: int,
    duration_ms: int,
    retried: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_succeeded event (ADR-040 §7).

    Fired on any 2xx response. ``duration_ms`` is wall-clock including
    retry backoff. ``retried=True`` if this response came after at least
    one earlier attempt failed transiently.
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_succeeded",
        "provider": provider,
        "url": url,
        "status": int(status),
        "duration_ms": int(duration_ms),
        "retried": bool(retried),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_live_adapter_call_failed(
    provider: str,
    failure_mode: str,
    http_status: Optional[int] = None,
    duration_ms: int = 0,
    retry_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_failed event (ADR-040 §7).

    ``failure_mode`` is the closed enum from SPEC/v1/live-adapters-policy
    §3 (auth_permanent, rate_limit, server_error, connect_timeout,
    read_timeout, connection_refused, parse_error, breaker_open,
    budget_hard_stop, scope_misconfigured).
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_failed",
        "provider": provider,
        "failure_mode": failure_mode,
        "http_status": int(http_status) if http_status is not None else None,
        "duration_ms": int(duration_ms),
        "retry_count": int(retry_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_breaker_opened(
    provider: str,
    failures_in_window: int,
    threshold: int,
    reason: str = "server_error",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a breaker_opened event (ADR-040 §2).

    Fired when :class:`_lib.adapters.live._breaker.CircuitBreaker`
    transitions CLOSED → OPEN (threshold crossed) or HALF_OPEN → OPEN
    (probe failed). ``reason`` is the failure classification that
    triggered the transition.
    """
    event: Dict[str, Any] = {
        "action": "breaker_opened",
        "provider": provider,
        "failures_in_window": int(failures_in_window),
        "threshold": int(threshold),
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_breaker_closed(
    provider: str,
    from_state: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a breaker_closed event (ADR-040 §2).

    Fired when :class:`_lib.adapters.live._breaker.CircuitBreaker`
    transitions back to CLOSED (from HALF_OPEN after successful probe,
    or explicit reset). ``from_state`` ∈ {"open", "half_open", "reset"}.
    """
    event: Dict[str, Any] = {
        "action": "breaker_closed",
        "provider": provider,
        "from_state": from_state,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# Sprint 13 Phase A (PLAN-013) — MCP server events (ADR-042)
# -----------------------------------------------------------------------------


# ---------------------------------------------------------------------
# PLAN-085 Wave C.1 — live_adapter_blocked
# ---------------------------------------------------------------------


def emit_live_adapter_blocked(
    provider: str,
    reason: str,
    session_id: str = "",
    project: str = "",
    *,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit a live_adapter_blocked event (PLAN-085 C.1 / ADR-040 §6.3).

    PLAN-085 Wave G.1b — extended with optional ``atlas_technique``
    parameter. Defaults to AML.T0049 (Exploit Public-Facing
    Application) from the immutable registry.
    """
    emit_generic(
        "live_adapter_blocked",
        provider=provider,
        reason=reason,
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["live_adapter_blocked"],
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave C.2 — credential lifecycle blocking + override
# ---------------------------------------------------------------------


def emit_credential_blocked_due_to_age(
    provider: str,
    age_days: int,
    max_age_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_blocked_due_to_age (ADR-040 §4 + ADR-040-AMEND-2)."""
    emit_generic(
        "credential_blocked_due_to_age",
        provider=provider,
        age_days=int(age_days),
        max_age_days=int(max_age_days),
        session_id=session_id,
        project=project,
    )


def emit_credential_emergency_override_used(
    provider: str,
    ticket_id: str,
    age_days: int,
    max_age_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_emergency_override_used (ADR-040-AMEND-2)."""
    emit_generic(
        "credential_emergency_override_used",
        provider=provider,
        ticket_id=ticket_id,
        age_days=int(age_days),
        max_age_days=int(max_age_days),
        session_id=session_id,
        project=project,
    )


# PLAN-117 WS-A — closed-enum + constant for the late-set forensic emit. The
# rejected override VALUE must NEVER reach the payload, so the dispatch gate
# (below) forces the var name to this constant and coerces an out-of-enum
# provenance hint to "unspecified" — the no-value-echo invariant is enforced at
# the chokepoint, independent of the caller (defense-in-depth, mirrors the
# closed-enum reason_code precedent in tier_policy_loader_fallback_observed).
_CREDENTIAL_OVERRIDE_VAR_NAME = "CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE"


_CREDENTIAL_OVERRIDE_PROVENANCE_HINTS = frozenset({
    "late_os_environ_set", "spawn_payload_env", "subprocess_inherited",
})


def emit_credential_override_late_set_ignored(
    provider: str,
    provenance_hint: str = "late_os_environ_set",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_override_late_set_ignored (ADR-040-AMEND-2 §Layer-1).

    Forensic trace for an emergency-override value that was present in the
    LIVE environment but ABSENT from the import-time trust-root snapshot
    (set post-anchor) and therefore IGNORED — never honored. The rejected
    VALUE is never persisted: the emit_generic dispatch gate FORCES
    ``attempted_var_name`` to the constant variable name and COERCES an
    out-of-enum ``provenance_hint`` — so the no-value-echo invariant does not
    depend on the caller (closed-enum-breadcrumb-must-not-echo-rejected-value).
    There is intentionally no ``attempted_var_name`` parameter: a caller cannot
    inject it.
    """
    emit_generic(
        "credential_override_late_set_ignored",
        provider=provider,
        provenance_hint=provenance_hint,
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave C.3 — MCP bearer-token replay defense (loopback-only)
# ---------------------------------------------------------------------


def emit_mcp_bearer_replay_rejected(
    reason: str,
    nonce_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_bearer_replay_rejected (PLAN-085 C.3 / IDA-P0-03)."""
    emit_generic(
        "mcp_bearer_replay_rejected",
        reason=reason,
        nonce_prefix=nonce_prefix[:8] if nonce_prefix else "",
        session_id=session_id,
        project=project,
    )


def emit_mcp_non_loopback_rejected(
    remote_addr_family: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_non_loopback_rejected (PLAN-085 C.3 / ADR-040-MCP-Auth)."""
    emit_generic(
        "mcp_non_loopback_rejected",
        remote_addr_family=remote_addr_family,
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave G.1b — ATLAS technique-ID schema (5 mappings).
# Immutable v1.19.0 registry; G.1a authored docs + fixtures + test
# infrastructure; G.1b lands the production audit_emit wiring.
# Source of truth: docs/EXT-011-mitre-atlas.md §2 SHIPPED table.
#
# PLAN-095 Wave A (S128) — registry expanded to 19 entries / 11 unique
# technique IDs by PLAN-088/089/090 across multiple plan ships. PLAN-095
# Wave B ships OWASP LLM03:2025 Supply Chain detection in
# `_lib/output_scan.py::_LLM_PATTERN_GROUPS` (family LLM03_2025_supply_chain).
# That detection family is NOT bound to a row in this registry because
# supply-chain is a family-level concern over output payloads, not a
# single technique-ID bound to a single audit-action. Cross-reference
# only; see `.claude/plans/PLAN-095/honest-scope-correction.md` §A.2.
# ---------------------------------------------------------------------

_ATLAS_REGISTRY = {
    "prompt_injection_detected": "AML.T0051",
    # PLAN-095 Wave A LLM02:2025 retag — AML.T0024.001 (ATLAS Infer
    # Training Data Membership) maps to OWASP 2024 LLM06 Sensitive
    # Information Disclosure AND OWASP 2025 LLM02 Sensitive Information
    # Disclosure (renumbering only; semantic preserved across both).
    "secret_leak_detected": "AML.T0024.001",
    "pii_redacted_outgoing": "AML.T0048.004",
    "live_adapter_blocked": "AML.T0049",
    "codex_egress_redacted": "AML.T0054",
    # PLAN-088 canonical-13 ATLAS bindings (S114) — 6 actions with non-null
    # technique-IDs per W0 ATLAS-binding table. Remaining 7 canonical-13
    # actions have atlas_technique=null + atlas_rationale per PLAN-088 §1.5
    # (telemetry-only / UX-trigger / infra-error / cost-optimization).
    "subagent_findings_partial_drop": "AML.T0048",   # W1.4 SEMI-13 — Governance bypass observation
    "anthropic_429_observed":         "AML.T0029",   # W1.4 SEMI-13 — Denial of ML Service signal
    "codex_invoke_dispatched":        "AML.T0050",   # W1.4 SEMI-13 — LLM Plugin Compromise dual-rail
    "tier_policy_misrouting_advised": "AML.T0048",   # W2.1 AUTO-04 — Governance bypass
    "mcp_route_advised":              "AML.T0050",   # W3.1 AUTO-06 — LLM Plugin / supply-chain signal
    "pair_rail_phase_advanced":       "AML.T0050",   # W4.1 AUTO-07 — LLM Plugin Compromise dual-rail check
    # PLAN-089 Wave C.5 — ATT&CK Enterprise bindings (R1 TDE P0 fold +
    # R2 Codex iter-1 P1 taxonomy correction). T1556/T1565.001 are
    # ATT&CK Enterprise (not ATLAS); registry name is generic for
    # technique-ID storage despite historic ATLAS-only origin.
    "kernel_extension_landed":            "T1565.001",  # Stored Data Manipulation — canonical kernel surface
    "bash_canonical_bypass_invoked":      "T1565.001",  # Stored Data Manipulation — same surface, kill-switch path
    "sentinel_signer_rotated":            "T1556",      # Modify Authentication Process
    "sentinel_signer_expiry_warned":      "T1556",      # Modify Authentication Process (forward signal)
    "sentinel_signer_revoked":            "T1556",      # Modify Authentication Process
    "sentinel_signer_quorum_failed":      "T1556",      # Modify Authentication Process (negative path canary)
    "sentinel_signer_quorum_attempted":   "T1556",      # Modify Authentication Process (forensic completeness)
    # PLAN-090 Wave B.5 — streaming side-channel monitoring.
    "streaming_token_yielded":            "T1071",
    # Note: T1584 (Compromise Infrastructure) applies to cold-key
    # compromise SCENARIOS — captured at IR investigation time, not at
    # any single audit-event level. See ADR-121 §7.
}


# PLAN-095 Wave A.8 (S128) — explicit namespace metadata per unique
# technique-ID for `verify-atlas-binding.py --strict-namespace` gate.
# Maps each of the 11 unique technique IDs in `_ATLAS_REGISTRY` to its
# source namespace: `atlas` (MITRE ATLAS LLM-system surface) or
# `attack-enterprise` (MITRE ATT&CK Enterprise OS-level surface).
# Registry intentionally carries the namespace mix per ADR-049
# detection-as-code corpus expansion; strict-namespace gate makes the
# mix EXPLICIT rather than implicit.
_ATLAS_NAMESPACE_REGISTRY: Dict[str, str] = {
    "AML.T0024.001": "atlas",
    "AML.T0029":     "atlas",
    "AML.T0048":     "atlas",
    "AML.T0048.004": "atlas",
    "AML.T0049":     "atlas",
    "AML.T0050":     "atlas",
    "AML.T0051":     "atlas",
    "AML.T0054":     "atlas",
    "T1071":         "attack-enterprise",
    "T1556":         "attack-enterprise",
    "T1565.001":     "attack-enterprise",
}
