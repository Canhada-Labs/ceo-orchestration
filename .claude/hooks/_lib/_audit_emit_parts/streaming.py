"""Streaming.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
import time

__all__ = ('is_audit_stream_verbose', 'streaming_rate_admit', 'persona_auto_decision_rate_admit', '_PHASE_C_ENFORCING_FLIPPED_ALLOWLIST', 'emit_phase_c_enforcing_flipped', '_KILL_SWITCH_INVOKED_ALLOWLIST', 'emit_kill_switch_invoked', '_PERSONA_AUTO_DECISION_EMITTED_ALLOWLIST', 'emit_persona_auto_decision_emitted', '_PERSONA_AUTO_RATE_CAPPED_ALLOWLIST', 'emit_persona_auto_rate_capped', '_STREAMING_TOKEN_YIELDED_ALLOWLIST', 'emit_streaming_token_yielded', '_STREAMING_RATE_CAPPED_ALLOWLIST', 'emit_streaming_rate_capped', '_MCP_BEARER_FRICTION_OBSERVED_ALLOWLIST', 'emit_mcp_bearer_friction_observed', '_CONFIDENCE_GATE_BASELINE_EMITTED_ALLOWLIST', 'emit_confidence_gate_baseline_emitted', '_CAPABILITY_ROLLOUT_COMPLETE_ALLOWLIST', 'emit_capability_rollout_complete')

def is_audit_stream_verbose() -> bool:
    """ADR-123 §4 — EXACT MATCH ``CEO_AUDIT_STREAM_VERBOSE=1`` only."""
    return os.environ.get(_VERBOSE_STREAM_ENV) == _VERBOSE_STREAM_ARMED_VALUE


def streaming_rate_admit(persona: str, _now: Callable[[], float] = time.monotonic) -> bool:
    """Per-persona token bucket for streaming_token_yielded."""
    now = _now()
    with _PLAN090_BUCKET_LOCK:
        last_ts, tokens = _PLAN090_STREAM_BUCKETS.get(persona, (now, _PLAN090_STREAM_BURST))
        elapsed_min = (now - last_ts) / 60.0
        refill = int(elapsed_min * _PLAN090_STREAM_REFILL_PER_MIN)
        if refill > 0:
            tokens = min(_PLAN090_STREAM_BURST, tokens + refill)
            last_ts = now
        if tokens <= 0:
            _PLAN090_STREAM_BUCKETS[persona] = (last_ts, tokens)
            return False
        _PLAN090_STREAM_BUCKETS[persona] = (last_ts, tokens - 1)
        return True


def persona_auto_decision_rate_admit(
    persona: str, _now: Callable[[], float] = time.monotonic
) -> bool:
    """Per-persona token bucket for persona_auto_decision_emitted."""
    now = _now()
    with _PLAN090_BUCKET_LOCK:
        last_ts, tokens = _PLAN090_PERSONA_BUCKETS.get(persona, (now, _PLAN090_PERSONA_BURST))
        elapsed_min = (now - last_ts) / 60.0
        refill = int(elapsed_min * _PLAN090_PERSONA_REFILL_PER_MIN)
        if refill > 0:
            tokens = min(_PLAN090_PERSONA_BURST, tokens + refill)
            last_ts = now
        if tokens <= 0:
            _PLAN090_PERSONA_BUCKETS[persona] = (last_ts, tokens)
            return False
        _PLAN090_PERSONA_BUCKETS[persona] = (last_ts, tokens - 1)
        return True


_PHASE_C_ENFORCING_FLIPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "migration_phase", "ts_unix",
})


def emit_phase_c_enforcing_flipped(
    *,
    migration_phase: str = "first_session",
    ts_unix: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit phase_c_enforcing_flipped (PLAN-090 Wave A.4 / ADR-118-AMEND-1 §4)."""
    raw_event: Dict[str, Any] = {
        "action": "phase_c_enforcing_flipped",
        "session_id": session_id,
        "project": project,
        "migration_phase": (migration_phase or "")[:32],
        "ts_unix": int(ts_unix),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PHASE_C_ENFORCING_FLIPPED_ALLOWLIST)
    _write_event(cleaned)


_KILL_SWITCH_INVOKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "env_value",
})


def emit_kill_switch_invoked(
    *,
    env_value: str = "0",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit kill_switch_invoked (PLAN-090 Wave A.4 / ADR-118-AMEND-1 §3)."""
    raw_event: Dict[str, Any] = {
        "action": "kill_switch_invoked",
        "session_id": session_id,
        "project": project,
        "env_value": (env_value or "")[:8],
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _KILL_SWITCH_INVOKED_ALLOWLIST)
    _write_event(cleaned)


_PERSONA_AUTO_DECISION_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "persona", "primitive", "decision", "decision_rationale",
})


def emit_persona_auto_decision_emitted(
    *,
    persona: str = "",
    primitive: str = "",
    decision: str = "",
    decision_rationale: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit persona_auto_decision_emitted (PLAN-090 Wave A.4)."""
    if not persona_auto_decision_rate_admit(persona):
        return
    raw_event: Dict[str, Any] = {
        "action": "persona_auto_decision_emitted",
        "session_id": session_id,
        "project": project,
        "atlas_technique": atlas_technique or "T1059",
        "persona": (persona or "")[:64],
        "primitive": (primitive or "")[:32],
        "decision": (decision or "")[:32],
        "decision_rationale": _plan088_payload_cap((decision_rationale or "")[:256]),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PERSONA_AUTO_DECISION_EMITTED_ALLOWLIST)
    _write_event(cleaned)


_PERSONA_AUTO_RATE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "persona", "dropped_count",
})


def emit_persona_auto_rate_capped(
    *,
    persona: str = "",
    dropped_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_auto_rate_capped (PLAN-090 Wave A.4)."""
    raw_event: Dict[str, Any] = {
        "action": "persona_auto_rate_capped",
        "session_id": session_id,
        "project": project,
        "persona": (persona or "")[:64],
        "dropped_count": max(0, int(dropped_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PERSONA_AUTO_RATE_CAPPED_ALLOWLIST)
    _write_event(cleaned)


_STREAMING_TOKEN_YIELDED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "persona", "token_preview", "token_length",
})


def emit_streaming_token_yielded(
    *,
    persona: str = "",
    token: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit streaming_token_yielded (PLAN-090 Wave B.5 / ADR-123 §4)."""
    if not is_audit_stream_verbose():
        return
    if not streaming_rate_admit(persona):
        return
    preview = (token or "")[:16]
    raw_event: Dict[str, Any] = {
        "action": "streaming_token_yielded",
        "session_id": session_id,
        "project": project,
        "atlas_technique": atlas_technique or _ATLAS_REGISTRY.get(
            "streaming_token_yielded", "T1071"
        ),
        "persona": (persona or "")[:64],
        "token_preview": preview,
        "token_length": len(token or ""),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _STREAMING_TOKEN_YIELDED_ALLOWLIST)
    _write_event(cleaned)


_STREAMING_RATE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "persona", "dropped_count",
})


def emit_streaming_rate_capped(
    *,
    persona: str = "",
    dropped_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit streaming_rate_capped (PLAN-090 Wave B.5)."""
    raw_event: Dict[str, Any] = {
        "action": "streaming_rate_capped",
        "session_id": session_id,
        "project": project,
        "persona": (persona or "")[:64],
        "dropped_count": max(0, int(dropped_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _STREAMING_RATE_CAPPED_ALLOWLIST)
    _write_event(cleaned)


_MCP_BEARER_FRICTION_OBSERVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "mcp_server", "failure_reason", "replay_suspected",
})


def emit_mcp_bearer_friction_observed(
    *,
    mcp_server: str = "",
    failure_reason: str = "",
    replay_suspected: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_bearer_friction_observed (PLAN-090 Wave C.2 §B / ADR-122 §B.3)."""
    raw_event: Dict[str, Any] = {
        "action": "mcp_bearer_friction_observed",
        "session_id": session_id,
        "project": project,
        "mcp_server": (mcp_server or "")[:64],
        "failure_reason": (failure_reason or "")[:128],
        "replay_suspected": bool(replay_suspected),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _MCP_BEARER_FRICTION_OBSERVED_ALLOWLIST)
    _write_event(cleaned)


_CONFIDENCE_GATE_BASELINE_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "distinct_classes", "insufficient_data_classes", "rows_total",
})


def emit_confidence_gate_baseline_emitted(
    *,
    distinct_classes: int = 0,
    insufficient_data_classes: int = 0,
    rows_total: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit confidence_gate_baseline_emitted (PLAN-090 AMENDMENT-1 / Wave A.10)."""
    raw_event: Dict[str, Any] = {
        "action": "confidence_gate_baseline_emitted",
        "session_id": session_id,
        "project": project,
        "distinct_classes": max(0, int(distinct_classes)),
        "insufficient_data_classes": max(0, int(insufficient_data_classes)),
        "rows_total": max(0, int(rows_total)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _CONFIDENCE_GATE_BASELINE_EMITTED_ALLOWLIST)
    _write_event(cleaned)


_CAPABILITY_ROLLOUT_COMPLETE_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tag", "auto_primitives_enforcing", "semi_primitives_advisory",
    "ac_pass_count",
})


def emit_capability_rollout_complete(
    *,
    tag: str = "",
    auto_primitives_enforcing: int = 10,
    semi_primitives_advisory: int = 3,
    ac_pass_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit capability_rollout_complete (PLAN-090 Wave D closeout)."""
    raw_event: Dict[str, Any] = {
        "action": "capability_rollout_complete",
        "session_id": session_id,
        "project": project,
        "tag": (tag or "")[:32],
        "auto_primitives_enforcing": max(0, int(auto_primitives_enforcing)),
        "semi_primitives_advisory": max(0, int(semi_primitives_advisory)),
        "ac_pass_count": max(0, int(ac_pass_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _CAPABILITY_ROLLOUT_COMPLETE_ALLOWLIST)
    _write_event(cleaned)
