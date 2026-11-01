"""Federation schemas.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_FEDERATION_ENVELOPE', '_FEDERATION_CONNECTION_ACCEPTED_ALLOWLIST', '_FEDERATION_CONNECTION_REJECTED_ALLOWLIST', '_FEDERATION_CONNECTION_REPLAY_SUSPECTED_ALLOWLIST', '_FEDERATION_CERT_EXPIRY_WARNED_ALLOWLIST', '_FEDERATION_CERT_REVOKED_ALLOWLIST', '_FEDERATION_CERT_VALIDITY_WINDOW_TOO_LARGE_ALLOWLIST', '_FEDERATION_ENABLE_SENTINEL_INVALID_ALLOWLIST', '_FEDERATION_LAN_BIND_DENIED_ALLOWLIST', '_FEDERATION_WRITE_ATTEMPT_BLOCKED_ALLOWLIST', '_FEDERATION_WRITE_ENDPOINT_DENIED_ALLOWLIST', '_FEDERATION_WRITE_DISABLED_SENTINEL_INVALID_ALLOWLIST', '_FEDERATION_SCOPE_DENIED_ALLOWLIST', '_FEDERATION_EVENT_ACTION_BLOCKED_ALLOWLIST', '_FEDERATION_AUDIT_EVENT_PUSHED_ALLOWLIST', '_FEDERATION_AUDIT_EVENT_PUSHED_BATCH_ALLOWLIST', '_FEDERATION_PEER_REGISTERED_ALLOWLIST', '_FEDERATION_PEER_REGISTERED_COLLISION_ALLOWLIST', '_FEDERATION_PEER_REVOKED_REMOTE_ALLOWLIST', '_FEDERATION_PEER_INVALID_NO_FINGERPRINT_ALLOWLIST', '_FEDERATION_PEER_LIST_RELOADED_ALLOWLIST', '_FEDERATION_PIN_LEGACY_USED_ALLOWLIST', '_FEDERATION_SPKI_FINGERPRINT_MISMATCH_ALLOWLIST', '_FEDERATION_MESSAGE_STORM_DETECTED_ALLOWLIST', '_FEDERATION_AUDIT_LOG_BACKPRESSURE_ALLOWLIST', '_FEDERATION_TAMPER_DETECTED_ALLOWLIST', '_RESERVED_ACTIONS', '_EMIT_GENERIC_PASSTHROUGH', '_FEDERATION_AUTONOMOUS_CALL_BLOCKED_ALLOWLIST', '_FEDERATION_HMAC_SECRET_ROTATED_ALLOWLIST', '_FEDERATION_KEY_FLOOR_REJECTED_ALLOWLIST', '_FEDERATION_KEY_FLOOR_STALE_ALLOWLIST', '_BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST', '_SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST', '_SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST', '_SPEC_CONTEXT_SANITIZED_ALLOWLIST', '_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST', '_ADMIN_KEY_OPERATIONS', '_ADMIN_KEY_REASONS', '_STATUSLINE_SIDECAR_WRITE_ALLOWLIST', '_STATUSLINE_SIDECAR_PATH_CAP', '_STATUSLINE_STR_CAP', '_MODEL_REFUSAL_OBSERVED_ALLOWLIST', '_INVISIBLE_UNICODE_BLOCKED_ALLOWLIST', '_INVISIBLE_UNICODE_CLASSES', '_INVISIBLE_UNICODE_SURFACES')

# PLAN-113 Phase B B-STRUCTURAL — federation emit_generic Sec MF-3 field
# allowlists (deny-by-default). Closes the "ghost-action leak" finding: the
# ~25 `federation_*` actions reach `emit_generic` via
# `_lib.federation.*._safe_emit(action, **fields)` but had NO dispatch-gate
# branch — so before this plan their caller kwargs were written VERBATIM into
# the HMAC audit log (no allowlist scrub). Each allowlist below is the union
# of the framework envelope (`_FEDERATION_ENVELOPE`) + the per-action SAFE
# fields taken BYTE-FOR-BYTE from SPEC/v1/audit-log.schema.md v2.29/v2.33.
#
# LLM06 / GDPR hold preserved per the SPEC rows: full SPKI/DER fingerprints
# are never logged (only `*_prefix` 16-hex), full IPs are /24-truncated
# (`ip_prefix`) where the producer truncates, and the two filesystem-path
# fields (`source_path`, `sentinel_path`) are NEVER persisted raw — the
# dispatch-gate re-hashes them via `_federation_safe_path_hash` (12-hex)
# BEFORE write, so an accidental caller cannot leak a host path into the
# chained log.
_FEDERATION_ENVELOPE = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# Read-path connection lifecycle (PLAN-099 MVP / ADR-129 / ADR-135). `client_ip`
# is persisted per the SPEC v2.27 rows (read-path connection forensics; the
# LLM06 drop applies to the WRITE-handler emits, not these).
_FEDERATION_CONNECTION_ACCEPTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "client_ip", "fed_correlation_id",
}


_FEDERATION_CONNECTION_REJECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id_cert_fingerprint", "client_ip", "reason",
}


_FEDERATION_CONNECTION_REPLAY_SUSPECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "client_ip", "reason",
}


_FEDERATION_CERT_EXPIRY_WARNED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "days_remaining",
}


_FEDERATION_CERT_REVOKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "reason",
}


_FEDERATION_CERT_VALIDITY_WINDOW_TOO_LARGE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "window_days", "max_days",
    # SPEC v2.29 also carries the ISO bounds + duration_days for the
    # advisory; allow them (no PII — cert validity window is public).
    "not_before_iso", "not_after_iso", "duration_days",
}


_FEDERATION_ENABLE_SENTINEL_INVALID_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "sentinel_kind", "reason",
}


_FEDERATION_LAN_BIND_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "bind_host", "resolved_ip", "reason",
}


# Write-mode surface (PLAN-099-FOLLOWUP Wave E/F.2 / ADR-135-AMEND-1).
_FEDERATION_WRITE_ATTEMPT_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id_cert_fingerprint", "client_ip", "fed_correlation_id",
    "method", "path",
}


_FEDERATION_WRITE_ENDPOINT_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "gate_failed", "reason_code",
}


_FEDERATION_WRITE_DISABLED_SENTINEL_INVALID_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "reason_code", "sentinel_path",  # sentinel_path re-hashed in dispatch-gate
}


_FEDERATION_SCOPE_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "required_scope", "peer_scopes_count",
}


_FEDERATION_EVENT_ACTION_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "event_action", "reason_code",
}


_FEDERATION_AUDIT_EVENT_PUSHED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "event_action", "hmac_ok", "origin_overwritten",
}


_FEDERATION_AUDIT_EVENT_PUSHED_BATCH_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "batch_size", "accepted_count", "rejected_count",
}


_FEDERATION_PEER_REGISTERED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "scopes_count", "spki_fingerprint_prefix",
}


_FEDERATION_PEER_REGISTERED_COLLISION_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "attempted_by_origin_peer_id",
}


_FEDERATION_PEER_REVOKED_REMOTE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "revoked_by_origin_peer_id", "reason_code",
}


_FEDERATION_PEER_INVALID_NO_FINGERPRINT_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "source_path",  # source_path re-hashed in dispatch-gate
}


_FEDERATION_PEER_LIST_RELOADED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "peer_count", "reload_reason",
    "source_path",  # source_path re-hashed in dispatch-gate
}


_FEDERATION_PIN_LEGACY_USED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "der_fingerprint_prefix",
}


_FEDERATION_SPKI_FINGERPRINT_MISMATCH_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "expected_prefix", "presented_prefix", "route",
}


# T1499 DoS surface (PLAN-099-FOLLOWUP Wave E.1 / ADR-135-AMEND-1 §2.4).
_FEDERATION_MESSAGE_STORM_DETECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "ip_prefix", "hits_in_window", "window_seconds",
}


_FEDERATION_AUDIT_LOG_BACKPRESSURE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "p99_latency_ms", "window_seconds", "action_taken",
}


# T1565 tamper surface (PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6).
_FEDERATION_TAMPER_DETECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "tamper_type", "prev_hash_prefix",
}


# PLAN-113 Phase B B5 — RESERVED-no-producer registry. Each maps a registered
# `_KNOWN_ACTIONS` member that has ZERO production caller today to its gating
# ADR. The CI-guard test (test_audit_emit_ghost_action_guard.py) asserts (a)
# every member here is truly producer-less and (b) if a member ever GROWS a
# production caller, its gating ADR MUST be in ACCEPTED state — else fail.
# Verified against SPEC/v1/audit-log.schema.md governing-ADR columns:
#   - execution_context_* : ADR-133 §D (cross-process wiring DEFERRED, F-1.2)
#   - federation_autonomous_call_blocked : ADR-135 (PLAN-099 import-graph
#     denylist surface; AC18 helper exists but is never invoked)
#   - federation_hmac_secret_rotated : ADR-135-AMEND-1 §6 (Owner co-sign
#     rotate path not wired to a producer)
#   - federation_key_floor_rejected / _stale : ADR-129-AMEND-1 §3/§4
#     (key-floor enforcement is advisory-staged; no emit producer yet)
# NOTE: federation_tamper_detected / federation_message_storm_detected /
# federation_audit_log_backpressure are NOT reserved — they have live
# `_safe_emit` producers (audit_chain_ext.py / rate_limit.py) and get explicit
# dispatch-gate branches above.
_RESERVED_ACTIONS = {
    "execution_context_signed": "ADR-133",
    "execution_context_validation_failed": "ADR-133",
    "federation_autonomous_call_blocked": "ADR-135",
    "federation_hmac_secret_rotated": "ADR-135-AMEND-1",
    "federation_key_floor_rejected": "ADR-129-AMEND-1",
    "federation_key_floor_stale": "ADR-129-AMEND-1",
}


# PLAN-113 Phase B B-STRUCTURAL — emit_generic verbatim-passthrough registry.
# These `_KNOWN_ACTIONS` members are emitted via emit_generic by TRUSTED
# in-repo producers (their own typed wrappers in this module, or first-party
# hook/script producers) with controlled, pre-scrubbed field sets. They have
# no dedicated dispatch-gate scrub branch and their verbatim pass-through is
# the ACCEPTED pre-existing contract (each has direct field-presence coverage
# in test_audit_emit_coverage.py). They are explicitly enumerated here so the
# default-deny `else` in emit_generic can distinguish them from a genuinely
# unhandled / future / unexpected producer.
#
# INVARIANT (enforced by test_audit_emit_ghost_action_guard.py): every
# `_KNOWN_ACTIONS` member is EXACTLY ONE of: (a) has an explicit `action ==`
# dispatch-gate branch, (b) is in `_RESERVED_ACTIONS`, or (c) is in this
# passthrough set. Any member matching NONE of the three reaches the
# default-deny `else` (all caller kwargs dropped). A NEW action added to
# `_KNOWN_ACTIONS` therefore defaults to fail-closed (default-deny) until the
# author either gives it a scrub branch or consciously lists it here — the
# leak class cannot silently reopen.
_EMIT_GENERIC_PASSTHROUGH = frozenset({
    # admin_key_lifecycle_event MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST scrub
    # branch in emit_generic: Sec MF-3 deny-by-default + operation/reason
    # enum-value coercion enforced even against a direct emit_generic caller.
    "agent_spawn",
    "audit_flush_dropped_count",
    "audit_spool_duplicate_tuple_rejected",
    "audit_spool_intentionally_deleted",
    "audit_spool_partial_line_discarded",
    "audit_spool_stale_recovered",
    "audit_spool_tamper_detected",
    "audit_spool_unexpected_skip",
    "audit_tokens_emitted",
    "audit_tokens_key_dropped",
    "audit_tokens_timeout",
    # bash_canonical_bypass_invoked REMOVED from passthrough (PLAN-113 Codex P1):
    # routed through explicit _BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST scrub branch
    # so target_path_hash (12-hex sha256) is the ONLY path representation in the log
    # (replaces the old target_path_preview raw-path field; Sec MF-3 P1 fix).
    "benchmark_run",
    "breaker_closed",
    "breaker_opened",
    "budget_bypass_used",
    "budget_exceeded",
    "canonical_edit_attempted",
    "canonical_edit_blocked",
    "capability_rollout_complete",
    "chain_reset_marker",
    "codex-reply",
    "confidence_gate",
    "confidence_gate_baseline_emitted",
    "credential_rotation_due",
    "debate_event",
    "escalation_baseline_recorded",
    "escalation_detected",
    "escalation_dispatched",
    "escalation_suppressed",
    "estimate_refined",
    "federation_cert_rotated",
    "fluency_nudge",
    "goap_cycle_detected",
    "goap_depth_exceeded",
    "goap_disabled_by_env",
    "goap_edge_explored",
    "goap_recommendation_accepted",
    "goap_recommendation_overridden",
    "goap_recommendation_rendered",
    "goap_replan_exhausted",
    "goap_replan_triggered",
    "goap_search_aborted",
    "goap_search_summary",
    "gpg_signed",
    "gpg_verified",
    "injection_flag",
    "kernel_extension_landed",
    "kill_switch_invoked",
    "lesson_archived",
    "lesson_outcome",
    "lesson_outcome_undone",
    "lesson_read",
    "lesson_restored",
    "lesson_write",
    "live_adapter_call_failed",
    "live_adapter_call_started",
    "live_adapter_call_succeeded",
    "mcp_bearer_friction_observed",
    "mcp_canonical_guard_internal_error",
    "mcp_cross_tenant_denied",
    "mcp_handler_denied",
    "mcp_handler_invoked",
    # mcp_injection_finding REMOVED from passthrough (PLAN-113 Codex B3 P1):
    # it carries MCP-controlled snippet_preview → routed through an explicit
    # scrub branch with allowlist + _preview() re-truncation instead.
    "mcp_server_disabled_by_kill_switch",
    "mcp_server_started",
    "mcp_soak_fpr_breach",
    # model_refusal_observed MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _MODEL_REFUSAL_OBSERVED_ALLOWLIST scrub
    # branch in emit_generic (stop_reason/stop_category/http_status/duration_ms
    # value-bounded against a direct caller).
    "otel_export_dropped",
    "output_safety_flag",
    "output_scan_finding",
    "pair_rail_codex_unavailable",
    "pair_rail_codex_violation",
    "pair_rail_review_passed",
    "pair_rail_sentinel_bypass",
    "pattern_evicted",
    "pattern_queried",
    "pattern_stored",
    "persona_auto_decision_emitted",
    "persona_auto_rate_capped",
    "phase_c_enforcing_flipped",
    "plan_transition",
    "policy_denied",
    "policy_error",
    "policy_evaluated",
    "prediction_queried",
    "prompt_submitted",
    "protocol_edit_missing_amend_paired",
    "rag_auto_wire_skipped_sidecar_down",
    "rag_false_large_demoted",
    "rag_hit_rate_degraded",
    "rag_index_redacted",
    "rag_profile_recommended",
    "rag_query_fallback",
    "rag_query_issued",
    "rag_query_redacted",
    "rag_query_returned",
    "rag_query_routed",
    "reality_ledger_key_dropped",
    "replay_capture_completed",
    "replay_capture_started",
    "replay_completed",
    "replay_diff_produced",
    "replay_started",
    "repo_profile_confirmed",
    "sentinel_created",
    "sentinel_signer_expiry_warned",
    "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed",
    "sentinel_signer_revoked",
    "sentinel_signer_rotated",
    "sentinel_verified",
    "session_end",
    "session_start",
    "session_stop",
    "skill_bootstrap_post_hash",
    "skill_bootstrap_used",
    "skill_cache_stats",
    "skill_patch_applied",
    "skill_reference_never_read",
    "skill_reference_read_mismatch",
    "skill_reference_read_stale",
    # spawn_confidence_advisory + spec_context_sanitized REMOVED from passthrough
    # (PLAN-113 Codex P2): moved to explicit per-action allowlist branches so
    # Sec MF-3 deny-by-default is structurally enforced even if a future
    # callsite adds unexpected fields. See _SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST
    # and _SPEC_CONTEXT_SANITIZED_ALLOWLIST below + dispatch branches in
    # emit_generic.
    "squad_imported",
    "state_store_pruned",
    "state_store_read",
    "state_store_write",
    # statusline_sidecar_write MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _STATUSLINE_SIDECAR_WRITE_ALLOWLIST scrub
    # branch in emit_generic (numeric/id/digest fields type-bounded; sidecar_path
    # length-capped against a direct caller).
    "streaming_rate_capped",
    "streaming_token_yielded",
    "swarm_aborted_error",
    "swarm_finalize_committed",
    "swarm_finalize_grouped",
    "swarm_halted_budget",
    "swarm_halted_convergence",
    "swarm_halted_kill",
    "swarm_iteration",
    "swarm_killed",
    "swarm_started",
    "swarm_tournament_selected",
    "task_route_key_dropped",
    "thinking_budget_set",
    "threat_model_freshness_breach",
    "threat_model_promoted",
    "tier_policy_adopter_override_respected",
    "tier_policy_demote_requested",
    "tier_policy_derived",
    "tier_policy_dry_run_complete",
    "tier_policy_hmac_verify_failed",
    "tier_policy_killswitch_triggered",
    "tier_policy_promote_applied",
    "tier_policy_promote_cost_gated",
    "tier_policy_rejected",
    "tournament_aborted",
    "tournament_budget_exceeded",
    "tournament_budget_projected",
    "tournament_fixture_rejected",
    "tournament_judge_hijack_suspected",
    "tournament_run_completed",
    "tournament_run_started",
    "tournament_task_scored",
    "veto_triggered",
    "wave_artifact_written",
    "wave_readonly_violation",
})


# Defense-in-depth allowlists for the 3 destructive RESERVED federation
# actions (no producer today; if an accidental caller appears, fields are
# allowlist-bounded not raw). Fields per SPEC v2.29 rows.
_FEDERATION_AUTONOMOUS_CALL_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "call_site",
}


_FEDERATION_HMAC_SECRET_ROTATED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "rotation_reason_code",
}


_FEDERATION_KEY_FLOOR_REJECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "key_type", "key_bits", "curve_name", "reason_code",
}


_FEDERATION_KEY_FLOOR_STALE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "key_floor_verified_at_iso", "advisory_only",
}


# PLAN-113 Codex P1 — bash_canonical_bypass_invoked field allowlist.
# target_path_preview REMOVED (raw filesystem path → Sec MF-3 violation).
# Replaced by target_path_hash (12-hex sha256 prefix; no path body leaks).
_BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "token_hash_prefix",
    "target_path_hash",
    "ticket_expires_in_s",
    "atlas_technique",
}


# PLAN-113 Codex P2 — spawn_confidence_advisory explicit allowlist.
# Moved from _EMIT_GENERIC_PASSTHROUGH so Sec MF-3 deny-by-default is
# structurally enforced. Fields: bounded enums/labels from
# check_agent_spawn._emit_spawn_confidence_advisory() per SPEC v2.34.
_SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "action_type",
    "confidence_level",
    "confidence_marker",
    "reason_code",
    "is_named_spawn",
}


# PLAN-153 Wave E item 7 (ADR-175) — spawn_prompt_defense_gate explicit allowlist.
# Sec MF-3 deny-by-default: only the 3 caller-supplied fields from
# check_agent_spawn._emit_prompt_defense_event() persist. `keyword` is a
# closed-enum untrusted-content hint (bounded + 32-char capped in the dispatch
# branch below); `present`/`enforced` are 0/1 flags. NO prompt/description body.
_SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "keyword",
    "present",
    "enforced",
}


# PLAN-113 Codex P2 — spec_context_sanitized explicit allowlist.
# Moved from _EMIT_GENERIC_PASSTHROUGH so Sec MF-3 deny-by-default is
# structurally enforced. Fields: bounded counters/flags from
# check_agent_spawn._maybe_sanitize_spec_context() per SPEC v2.34.
# No prompt content is persisted — all fields are derived byte/count metrics.
_SPEC_CONTEXT_SANITIZED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "original_bytes",
    "cleaned_bytes",
    "truncated",
    "sentinel_violations",
    "control_chars_stripped",
    "bidi_zw_chars_stripped",
    "tag_chars_stripped",
    "header_escape_count",
}


# PLAN-135-FOLLOWUP (Codex R5 P1-2) — the 3 W5 ops actions move OFF
# _EMIT_GENERIC_PASSTHROUGH into dedicated deny-by-default scrub branches so the
# Sec MF-3 field-allowlist + enum-value-coercion boundary holds against a direct /
# future emit_generic caller that bypasses the trusted producer. Field sets are
# byte-accurate to the live producers AND to SPEC/v1/audit-log.schema.md L480-482.
#
# o9 — Anthropic Admin API key-lifecycle (.claude/scripts/key-hygiene.py
# `_audit_emit`). Producer passes operation + a per-call-site subset of
# {key_count | key_id | reason | rotation_log_appended}; rotated_by/notes go to
# docs/rotation-log.md, NEVER the emit. `reason` is a REQUIRED credential-forensic
# field (the WHY of a key deactivation) — kept + enum-coerced, never dropped.
_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "operation",
    "key_id",
    "key_count",
    "reason",
    "rotation_log_appended",
}


# Closed enums for VALUE re-coercion (mirror key-hygiene.py: the operation
# discriminator + VALID_REASONS). Out-of-set → "other" (S172 coerce-to-safe-
# sentinel) so a direct caller cannot smuggle free text through an allowed key.
_ADMIN_KEY_OPERATIONS = frozenset({"list", "deactivate", "incident"})


_ADMIN_KEY_REASONS = frozenset({"compromise", "suspicion", "scheduled"})


# o4 — statusLine sidecar-write (.claude/scripts/statusline-ceo.py `maybe_emit`).
# session_id is already in _FEDERATION_ENVELOPE; sidecar_path is an abs path SPEC
# L481 explicitly permits — length-capped to bound log-line bloat / oversized-field
# log-injection (Codex R5 P1-2 sec must-fix).
_STATUSLINE_SIDECAR_WRITE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "sidecar_path",
    "plan_id",
    # PLAN-135-FOLLOWUP-2 (S234): percentage fields are HMAC-covered ->
    # integer basis-points (pct * 100), NEVER float. The canonical encoder
    # forbids float (S181 / ADR-055-AMEND-2); the float form was written
    # with hmac=null on every emit since v2.44. Producer converts pct->bps;
    # the scrub branch below clamps to int authoritatively.
    "context_pct_bps",
    "bucket_count",
    "buckets_used_pct_max_bps",
    "digest",
}


_STATUSLINE_SIDECAR_PATH_CAP = 512


_STATUSLINE_STR_CAP = 256


# o7 — model-refusal observability (.claude/hooks/_lib/adapters/live/claude.py
# `_on_response`). stop_reason is the const "refusal"; stop_category is the closed
# provider vocabulary (<=64); http_status/duration_ms are bounded non-negative ints
# (no float in the HMAC-covered chain — S181 doctrine).
_MODEL_REFUSAL_OBSERVED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "provider",
    "model",
    "stop_reason",
    "stop_category",
    "http_status",
    "duration_ms",
}


# PLAN-133 A2 — Sec field allowlist for invisible_unicode_blocked. Deny-by-default.
# The ONLY caller-supplied payload fields are the closed-enum `surface` +
# `unicode_class`, the bounded int `char_count`, and the flag `enforced`. The
# prompt / skill text, the matched characters, and any var/value are NEVER allowed
# fields, so smuggled content can never reach the signed chain.
_INVISIBLE_UNICODE_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "surface",
    "unicode_class",
    "char_count",
    "enforced",
}


# PLAN-133 A2 — closed unicode_class enum. MUST mirror
# _lib/spec_context_sanitizer.INVISIBLE_UNICODE_CLASSES. Kept as a literal frozenset
# here (NOT imported) so audit_emit has zero import-time dependency on the sanitizer;
# a drift is caught by a dedicated test (the two frozensets MUST be equal). A value
# outside this set is COERCED to "control" before emit (defense-in-depth).
_INVISIBLE_UNICODE_CLASSES = frozenset({
    "tag_block", "bidi_zw", "control", "none",
})


# PLAN-133 A2 — closed surface enum (origin of the detection). Out-of-set → "spawn".
_INVISIBLE_UNICODE_SURFACES = frozenset({
    "spawn", "skill_write", "skill_read",
})
