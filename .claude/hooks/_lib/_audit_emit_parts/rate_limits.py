"""Rate limits.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
import time

__all__ = ('_FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST', '_CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST', '_LIVE_ADAPTER_BLOCKED_ALLOWLIST', '_PROMPT_INJECTION_DETECTED_ALLOWLIST', '_MCP_INJECTION_FINDING_ALLOWLIST', '_SECRET_LEAK_DETECTED_ALLOWLIST', '_PII_REDACTED_OUTGOING_ALLOWLIST', '_CODEX_EGRESS_REDACTED_ALLOWLIST', '_PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST', '_CANONICAL_EDIT_COMPLETED_ALLOWLIST', '_CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST', '_CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST', '_CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST', '_MCP_BEARER_REPLAY_REJECTED_ALLOWLIST', '_MCP_NON_LOOPBACK_REJECTED_ALLOWLIST', '_VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST', '_TRADING_WRITE_OVERRIDE_USED_ALLOWLIST', '_TRADING_KILL_SWITCH_INVOKED_ALLOWLIST', '_TRADING_KILL_SWITCH_DISABLED_ALLOWLIST', '_PLAN088_RATE_CAP_PER_MIN', '_PLAN088_PAYLOAD_MAX_BYTES', '_PLAN088_RATE_STATE', '_plan088_rate_state_clear', '_plan088_rate_admit', '_plan088_payload_cap', '_CACHE_DISCIPLINE_ALERTED_ALLOWLIST')

# PLAN-083 Wave 2 sub-agent 2.1 — Sec MF-3 allowlist for first_run_wizard_completed.
_FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "profile", "recommendation_count", "user_action",
})


# PLAN-083 Wave 2 sub-agent 2.2 — Sec MF-3 allowlist for contextual_recommendation_emitted.
_CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "profile", "recommendation_count", "top_score", "suppressed_count",
})


# PLAN-083 Wave 2 sub-agent 2.4 — Sec MF-3 allowlist for value_dashboard_summarized.
# PLAN-085 Wave C.1 — Sec MF-3 allowlist for live_adapter_blocked.
_LIVE_ADAPTER_BLOCKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "reason",
    "atlas_technique",  # PLAN-085 Wave G.1b
})


# PLAN-085 Wave G.1b — ATLAS technique-ID allowlists (4 NEW actions).
# Each carries `atlas_technique` (AML.T<NNNN>) + detector context fields.

_PROMPT_INJECTION_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "snippet_preview", "match_count", "bytes_scanned",
    "triggered_by_tool",
})


# PLAN-113 Codex B3 P1 — mcp_injection_finding carries MCP-controlled
# snippet_preview; route through an explicit scrub branch (was passthrough)
# + re-truncate snippet_preview via _preview() so a DIRECT emit_generic
# caller cannot bypass the named-emitter's [:120] cap and leak secrets.
_MCP_INJECTION_FINDING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "server_id", "mcp_tool_name", "source_kind", "family_counts",
    "match_count", "bytes_scanned", "severity",
    "snippet_preview", "scanner_action",
})


_SECRET_LEAK_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "snippet_preview", "match_count", "bytes_scanned",
    "triggered_by_tool",
})


_PII_REDACTED_OUTGOING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned",
})


_CODEX_EGRESS_REDACTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned", "callsite",
})


# PLAN-112-FOLLOWUP-codex-egress-proof-telemetry — Sec MF-3 allowlist for
# pair_rail_outgoing_redaction_applied (ADR-114 outbound pair-rail vector).
# Content-field-free BY CONSTRUCTION: deliberately NO text / prompt /
# match_value — wiring an emit without this gate would write caller fields
# verbatim into the HMAC-chained log (the F-7.9 W1 hard-prerequisite).
_PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned", "callsite",
})


# PLAN-085 Wave E.4 piggyback — canonical_edit_completed allowlist.
# Emitted by check_bash_canonical_forensic.py PostToolUse hook.
_CANONICAL_EDIT_COMPLETED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "path", "sentinel_hint",
})


# PLAN-085 Wave C.2 — Sec MF-3 allowlist for credential_blocked_due_to_age.
_CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "age_days", "max_age_days",
})


# PLAN-085 Wave C.2 — Sec MF-3 allowlist for credential_emergency_override_used.
_CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "ticket_id", "age_days", "max_age_days",
})


# PLAN-117 WS-A — Sec MF-3 allowlist for credential_override_late_set_ignored.
# Forensic-only fields; the rejected override VALUE is intentionally absent
# (closed-enum-breadcrumb-must-not-echo-rejected-value).
_CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "attempted_var_name", "provenance_hint",
})


# PLAN-085 Wave C.3 — Sec MF-3 allowlist for mcp_bearer_replay_rejected.
_MCP_BEARER_REPLAY_REJECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "reason", "nonce_prefix",
})


# PLAN-085 Wave C.3 — Sec MF-3 allowlist for mcp_non_loopback_rejected.
_MCP_NON_LOOPBACK_REJECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "remote_addr_family",
})


_VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "period_days", "cost_usd_int_cents", "bugs_count", "dispatches_count", "plans_count",
})


# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_write_override_used.
_TRADING_WRITE_OVERRIDE_USED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    # PLAN-083 Wave 3 P0 fix (2026-05-11): align with caller fields in
    # .claude/scripts/trading-readonly-guardrails.py:_check_write_override.
    # Sec MF-3 deny-by-default — these are hashed prefixes + length only;
    # raw target_path / justification text NEVER persisted.
    "allowed", "reason",
    "target_path_sha256_prefix",  # 16-hex sha256 prefix
    "justification_sha256_prefix",  # 16-hex sha256 prefix
    "justification_length",  # int — bounded length only, no content
    "err_preview",  # str ≤80 — exception preview from path resolution failure (NO raw paths)
})


# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_kill_switch_invoked.
_TRADING_KILL_SWITCH_INVOKED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "reason",
})


# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_kill_switch_disabled.
_TRADING_KILL_SWITCH_DISABLED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    # PLAN-083 Wave 3 P0 fix (2026-05-11): align with caller fields in
    # scripts/local/trading-readonly-escape-hatch.sh emit_generic call.
    # All hashed prefixes — raw justification body NEVER persisted.
    "justification_sha256_prefix",  # 16-hex sha256 prefix
    "signer_fingerprint_prefix",  # 16-hex GPG fingerprint prefix
    "signed_new",  # bool — true if .asc freshly created vs reused
    "justification_length",  # int — bounded length
})


# =============================================================================
# PLAN-088 canonical-13 god-mode auto-activation (S114 / qa-architect-reviewed).
# Per W0 ATLAS-binding table + M-12/Sec-3 (rate-cap 100/min/action +
# payload_max_bytes=4096) + Sec MF-3 (deny-by-default allowlists).
#
# 11 net-new typed emitters + 11 allowlists + 11 emit_generic dispatch gates.
# The 2 remaining canonical-13 (`model_routing_advised` + `mcp_route_advised`)
# are pre-existing stubs registered by PLAN-078 / PLAN-086.
#
# QA fixes from S114 dispatch verdict ACCEPT-WITH-FIXES (4 P0):
#   1. `time` + `threading` moved to top-of-file imports (unaliased)
#   2. `_PLAN088_RATE_STATE` cleared via _plan088_rate_state_clear() in tests;
#      injectable clock via `_clock` parameter for test-time advance
#   3. `emit_generic` dispatch gates added for all 11 new actions (Sec MF-3
#      defense-in-depth — see emit_generic body for the 11 elif branches)
#   4. `_plan088_payload_cap` uses errors='ignore' + strip-continuation-byte
#      loop (utf-8 mid-codepoint boundary safe; no � overflow)
# =============================================================================

_PLAN088_RATE_CAP_PER_MIN = 100


_PLAN088_PAYLOAD_MAX_BYTES = 4096


_PLAN088_RATE_STATE: Dict[str, Tuple[float, int, int]] = {}  # action -> (window_start_ts, count, dropped)


def _plan088_rate_state_clear() -> None:
    """Reset PLAN-088 rate-cap state. Test helper for cross-test isolation
    (qa-architect P0-2 fix: module-level mutable singleton needs explicit
    reset to avoid test order dependence)."""
    with _PLAN088_RATE_LOCK:
        _PLAN088_RATE_STATE.clear()


def _plan088_rate_admit(action: str, _clock: Callable[[], float] = time.time) -> bool:
    """Return True if action emit is within the 100/min/action cap.

    Sliding 60s window; on rollover, resets count. Increments `dropped`
    counter when over-budget WITHOUT re-emitting (M-12 anti-recursive-flood
    invariant — never call `_write_event` or `_breadcrumb` from this path).

    `_clock` is injectable for tests (advance simulated time without
    `time.sleep`).
    """
    now = _clock()
    with _PLAN088_RATE_LOCK:
        window_start, count, dropped = _PLAN088_RATE_STATE.get(action, (now, 0, 0))
        if now - window_start >= 60.0:
            window_start, count, dropped = now, 0, 0
        if count >= _PLAN088_RATE_CAP_PER_MIN:
            _PLAN088_RATE_STATE[action] = (window_start, count, dropped + 1)
            return False
        _PLAN088_RATE_STATE[action] = (window_start, count + 1, dropped)
        return True


def _plan088_payload_cap(value: str, max_bytes: int = _PLAN088_PAYLOAD_MAX_BYTES) -> str:
    """Truncate a utf-8 string to ``max_bytes`` without breaking codepoint.

    M-12 anti-traceback-leak guard. qa-architect P0-4 fix: use ``errors='ignore'``
    + strip-continuation-byte loop so the cut point lands on a valid utf-8
    boundary (no \\ufffd replacement-char overflow that would push past
    max_bytes by 1-2 bytes).

    Only accepts str input (P1 fix: do not coerce None / non-str types
    silently — let caller's typed default handle missing values).
    """
    if not isinstance(value, str):
        return ""
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return value
    # Strip trailing continuation bytes (0b10xxxxxx) to land on a valid
    # codepoint boundary, then decode with errors='ignore' as belt+suspenders.
    cut = encoded[:max_bytes]
    while cut and (cut[-1] & 0xC0) == 0x80:
        cut = cut[:-1]
    return cut.decode("utf-8", errors="ignore")


# --- W1.1 AUTO-01: cache_discipline_alerted (telemetry-only) -----------

_CACHE_DISCIPLINE_ALERTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "hit_rate_basis_points", "floor_basis_points", "session_count_24h",
    "below_floor", "opted_out",
})
