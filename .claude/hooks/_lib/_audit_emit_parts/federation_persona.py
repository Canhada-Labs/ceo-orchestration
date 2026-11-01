"""Federation persona.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_federation_connection_accepted', 'emit_federation_connection_rejected', 'emit_federation_connection_replay_suspected', 'emit_federation_cert_expiry_warned', 'emit_federation_cert_rotated', 'emit_federation_cert_revoked', 'emit_federation_write_attempt_blocked', 'emit_federation_lan_bind_denied', 'emit_federation_autonomous_call_blocked', 'emit_federation_enable_sentinel_invalid', '_persona_demand_safe_hash', '_PERSONA_DEMAND_OPENED_ALLOWLIST', '_PERSONA_DEMAND_MATCHED_ALLOWLIST', '_PERSONA_DEMAND_UNMET_ALLOWLIST', '_PERSONA_DEMAND_WAIVED_ALLOWLIST', '_PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST', '_PERSONA_COVERAGE_ARCHETYPES', '_PERSONA_COVERAGE_TASK_TYPES', '_PERSONA_COVERAGE_SOURCES', '_PERSONA_WAIVE_REASONS', 'emit_persona_demand_opened', 'emit_persona_demand_matched', 'emit_persona_demand_unmet', 'emit_persona_demand_waived')

# ---------------------------------------------------------------------------
# PLAN-099 (ADR-129 / ADR-135) — federation cross-machine MVP emit functions.
# Sec MF-3 caller-field whitelist (deny-by-default). 10 actions total.
# ATT&CK technique bindings: T1071.001 / T1573 / T1556.
# ---------------------------------------------------------------------------


def emit_federation_connection_accepted(
    peer_id: str,
    client_ip: str = "",
    fed_correlation_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_accepted (PLAN-099 AC2)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_accepted",
        "peer_id": str(peer_id)[:64],
        "client_ip": str(client_ip)[:64],
        "fed_correlation_id": str(fed_correlation_id)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_connection_rejected(
    reason: str,
    peer_id_cert_fingerprint: str = "",
    client_ip: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_rejected (PLAN-099 AC2)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_rejected",
        "reason": str(reason)[:64],
        "peer_id_cert_fingerprint": str(peer_id_cert_fingerprint)[:64],
        "client_ip": str(client_ip)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_connection_replay_suspected(
    peer_id: str,
    reason: str,
    client_ip: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_replay_suspected (PLAN-099 AC13)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_replay_suspected",
        "peer_id": str(peer_id)[:64],
        "reason": str(reason)[:64],
        "client_ip": str(client_ip)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_expiry_warned(
    peer_id: str,
    days_remaining: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_expiry_warned (PLAN-099 AC11 — 14d before expiry)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_expiry_warned",
        "peer_id": str(peer_id)[:64],
        "days_remaining": int(days_remaining),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_rotated(
    peer_id: str,
    old_fingerprint_prefix: str = "",
    new_fingerprint_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_rotated (PLAN-099 AC11)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_rotated",
        "peer_id": str(peer_id)[:64],
        "old_fingerprint_prefix": str(old_fingerprint_prefix)[:16],
        "new_fingerprint_prefix": str(new_fingerprint_prefix)[:16],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_revoked(
    peer_id: str,
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_revoked (PLAN-099 AC11)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_revoked",
        "peer_id": str(peer_id)[:64],
        "reason": str(reason)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_write_attempt_blocked(
    method: str,
    path: str,
    peer_id_cert_fingerprint: str = "",
    client_ip: str = "",
    fed_correlation_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_write_attempt_blocked (PLAN-099 AC15 — method allowlist)."""
    event: Dict[str, Any] = {
        "action": "federation_write_attempt_blocked",
        "method": str(method)[:16],
        "path": str(path)[:128],
        "peer_id_cert_fingerprint": str(peer_id_cert_fingerprint)[:64],
        "client_ip": str(client_ip)[:64],
        "fed_correlation_id": str(fed_correlation_id)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_lan_bind_denied(
    bind_host: str,
    resolved_ip: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_lan_bind_denied (PLAN-099 AC3 — non-loopback bind gate)."""
    event: Dict[str, Any] = {
        "action": "federation_lan_bind_denied",
        "bind_host": str(bind_host)[:64],
        "resolved_ip": str(resolved_ip)[:64],
        "reason": str(reason)[:96],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_autonomous_call_blocked(
    call_site: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_autonomous_call_blocked (PLAN-099 AC18 — import-graph denylist)."""
    event: Dict[str, Any] = {
        "action": "federation_autonomous_call_blocked",
        "call_site": str(call_site)[:128],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_enable_sentinel_invalid(
    sentinel_kind: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_enable_sentinel_invalid (PLAN-099 AC22 — 2-stage failure modes)."""
    event: Dict[str, Any] = {
        "action": "federation_enable_sentinel_invalid",
        "sentinel_kind": str(sentinel_kind)[:32],
        "reason": str(reason)[:96],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# PLAN-104 Wave A.3 + A.4 — persona-demand ledger emit functions + allowlists.
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-104-WAVE-A-
# AUDIT-EMIT-EXTENSION + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT (S123 pattern).
# Sec MF-3 caller-field deny-by-default per action.
# Field bodies NEVER persist raw target paths or branch refs.
# Codex iter-1 P0 #4 fold: target_ref_hash is re-derived defensively
# from a 12-hex check (strip + ascii-only); caller-supplied non-hex
# values fall back to sha256[:12] of the input. This blocks an LLM06
# side-channel where a hostile caller passes raw text as
# `target_ref_hash`.
# -----------------------------------------------------------------------------

def _persona_demand_safe_hash(raw: str) -> str:
    """Return 12-hex target_ref_hash. Re-hashes if caller value not valid hex."""
    import hashlib
    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:12]


_PERSONA_DEMAND_OPENED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "target_ref_hash", "match_window_hours",
})


_PERSONA_DEMAND_MATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "actual_persona", "latency_ms",
    "match_modality",  # PLAN-132 / ADR-145 — {native_spawn, codex_review}
})


_PERSONA_DEMAND_UNMET_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "target_ref_hash", "window_expired_at",
})


_PERSONA_DEMAND_WAIVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "waive_reason",
})


# PLAN-106 Wave C — Sec MF-3 deny-by-default allowlist for
# persona_coverage_synthesized. Caller-supplied: archetype, task_type,
# cell_id (≤32 byte sha256[:8] hash for stable 4×4 cell index),
# source ("dispatch" | "canonical_edit"). NO raw prompt body, NO file
# path, NO description preview — LLM06 side-channel hold.
_PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "task_type", "cell_id", "source",
})


# Closed enums for archetype + task_type (deny free-text per PLAN-093
# Wave C.5 4-persona × 4-task matrix). Mirrors ceo-boot.py:
# _VETO_FLOOR_PERSONAS + _PERSONA_TASK_TYPES at module-level so the
# allowlist scrub stays self-contained.
_PERSONA_COVERAGE_ARCHETYPES = frozenset({
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer",
})


_PERSONA_COVERAGE_TASK_TYPES = frozenset({
    "review", "vet", "test", "detect",
})


_PERSONA_COVERAGE_SOURCES = frozenset({
    "dispatch", "canonical_edit",
})


# Closed enum for waive_reason. Free-text values rejected pre-emit.
_PERSONA_WAIVE_REASONS = frozenset({
    "docs-only",
    "generated-or-vendored",
    "emergency-hotfix",
    "explicit-skip",
})


def emit_persona_demand_opened(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    target_ref_hash: str,
    match_window_hours: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_opened (PLAN-104 Wave A; S134 R2 ACCEPT).

    Fired by persona_demand_scan.py when a new demand_id is detected
    within the bounded scan horizon. target_ref_hash is pre-computed
    sha256[:12] of the NFKC-normalized target_ref (path OR branch_ref);
    raw value NEVER persisted (LLM06 hold).
    """
    event: Dict[str, Any] = {
        "action": "persona_demand_opened",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "target_ref_hash": _persona_demand_safe_hash(target_ref_hash),
        "match_window_hours": int(match_window_hours),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_matched(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    actual_persona: str,
    latency_ms: int,
    session_id: str = "",
    project: str = "",
    match_modality: str = "native_spawn",
) -> None:
    """Emit persona_demand_matched (PLAN-104 Wave A; S134 R2 P1 #3 fold).

    Native strict-match: actual_persona == expected_persona (S134 R2 Q4 — no peer
    substitution). PLAN-132 / ADR-145 adds ONE recognized exception: a cross-model
    Codex review may satisfy a `code-reviewer` demand, emitted with
    match_modality="codex_review" and actual_persona="code-reviewer" (so the
    published SPEC invariant actual_persona == expected_persona still HOLDS). The
    relaxation is code-reviewer-ONLY and is enforced by the resolver's literal
    guard; this emitter only records the modality. An invalid modality coerces to
    the safe default "native_spawn" (S172: never echo a rejected value).
    """
    mm = match_modality if match_modality in _PERSONA_MATCH_MODALITY_ENUM else "native_spawn"
    event: Dict[str, Any] = {
        "action": "persona_demand_matched",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "actual_persona": str(actual_persona)[:64],
        "latency_ms": int(latency_ms),
        "match_modality": mm,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_unmet(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    target_ref_hash: str,
    window_expired_at: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_unmet (PLAN-104 Wave A).

    Idempotency contract: at most ONE per demand_id (dedup at
    persona_demand_resolver scan time via terminal-event index).
    """
    event: Dict[str, Any] = {
        "action": "persona_demand_unmet",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "target_ref_hash": _persona_demand_safe_hash(target_ref_hash),
        "window_expired_at": str(window_expired_at)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_waived(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    waive_reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_waived (PLAN-104 Wave A; S134 R2 P1 #2 fold).

    waive_reason MUST be one of the closed enum
    `_PERSONA_WAIVE_REASONS` (free-text rejected pre-emit; invalid
    values dropped to a known-bad sentinel for forensic trace
    without polluting the enum surface).
    """
    reason = str(waive_reason)[:32]
    if reason not in _PERSONA_WAIVE_REASONS:
        reason = "invalid-enum"
    event: Dict[str, Any] = {
        "action": "persona_demand_waived",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "waive_reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
