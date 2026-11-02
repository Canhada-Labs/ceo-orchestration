"""Governance.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_ESTIMATE_DRIFT_DETECTED_ALLOWLIST', '_ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST', '_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST', '_PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST', '_DISPATCHER_ROUTE_EMIT_ALLOWLIST', '_PAIR_RAIL_CASE_EMIT_ALLOWLIST', '_PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST', '_TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST', '_ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST', '_ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST', '_SMART_LOADING_RESOLVED_ALLOWLIST')

# PLAN-078 Wave 2 — `estimate_drift_detected` field allowlist (deny-by-default).
# 6 caller fields per plan §4 Wave 2 + auto-baseline. NO commit SHAs (raw),
# NO file paths, NO plan body text, NO CSV row body. plan_id is Owner-
# visible per ADR-033 §plan-budget precedent.
#
# Codex W1+W2 fix-pack #2: drift_factor_*_basis_points are int (multiplier
# × 1000). 1.234× → 1234; 0.500× → 500. Float forbidden by canonical_json
# (HMAC-covered field constraint). Severity classification + reality-ledger
# in-memory math still uses float for precision; only emission converts
# to int basis-points. systematic_bias_direction enum is
# "" | "underestimate" | "overestimate" (we under-estimated when actual
# span > estimated upper bound, factor > 1.2 = "overrun" semantically;
# we over-estimated when actual span < estimated lower bound,
# factor < 0.83 = "underrun" semantically). Codex S89 call #4 alignment.
_ESTIMATE_DRIFT_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "plan_id", "drift_factor_compute_basis_points",
    "drift_factor_owner_basis_points",
    "severity", "plan_count_in_run", "systematic_bias_direction",
})


# PLAN-078 Wave 2 — `estimate_drift_systematic_bias` recommendation event.
# Strict 4-caller-field contract: bias_direction, plans_affected_count,
# avg_drift_factor_compute_basis_points, avg_drift_factor_owner_basis_points.
# Codex W1+W2 fix-pack #2: avg factors emitted as int basis-points to
# preserve HMAC chain (canonical_json no-floats invariant).
_ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "bias_direction", "plans_affected_count",
    "avg_drift_factor_compute_basis_points",
    "avg_drift_factor_owner_basis_points",
})


# PLAN-078 Wave 5 — `ceo_boot_task_candidate_emitted` field allowlist
# (deny-by-default). 4 caller fields per plan §4 Wave 5 Layer A + auto-baseline.
# Sec MF-3 enforcement: NO subject text body, NO recommendation text body,
# NO check name, NO check stderr/detail, NO env values, NO file paths.
# `subject_hash` is a 12-hex-char prefix of sha256(canonicalized subject) for
# dedup state-file bookkeeping; `rank` is 1..3 (top-3 cap); `severity` is the
# recommendation engine bucket {low, medium, high} bound to ASCII a-z; and
# `awaiting_confirm` is a bool reserved for a future "Owner-must-confirm"
# escape (default False — Claude orchestrator auto-creates the task in
# the v1.15.0 baseline without confirmation). Dispatch-gate in emit_generic
# re-enforces the allowlist defensively for any direct caller drift.
_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "rank", "severity", "subject_hash", "awaiting_confirm",
})


# PLAN-081 Phase 1-full / R1 S-Sec-5 / Sec MF-3 — pair_rail_codex_injection_detected
# allowlist. Codex stdout pattern matches MUST emit ONLY the pattern family +
# match count + length-bucketed first offset; NEVER raw matched content nor raw
# offset values (LLM06 side-channel guard — raw offset leaks prompt prefix length).
# Dispatch-gate in emit_generic re-enforces this allowlist defensively for any
# direct caller drift.
_PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tool_name", "family_ids", "match_count", "first_offset_bucket",
})


# PLAN-081 Phase 2 / Sec MF-3 — dispatcher_route allowlist.
# Carries dispatcher decision metadata for audit forensics + perf metric
# extraction (`codex_latency_p95_s` predicate aggregator reads
# wall_clock_s from this action). NEVER persists raw archetype profile,
# task description, skill content, or matrix YAML body — those would
# duplicate canonical-guarded sources or leak prompt content (LLM06
# side-channel). Only:
#   - archetype: which archetype was dispatched
#   - rail: "pair_rail" | "fallback_claude_only" | "fallback_codex_only"
#   - reason_code: "ok" | "predicate_<id>_fired" | "matrix_sha_mismatch" |
#       "health_prereq_unmet_<u-id>"
#   - matrix_sha256_prefix: 16-hex prefix of loaded matrix sha (never raw)
#   - matrix_sha256_match: bool (vs CEO_PAIR_RAIL_MATRIX_SHA256 env)
#   - coder / reviewer: provider names from routing-matrix.yaml
#   - coder_model: model floor (sonnet/opus/haiku)
#   - reviewer_sandbox: sandbox mode for the reviewer
#   - wall_clock_s: dispatcher-side resolution wall-clock (perf metric
#       source; bounded float ≥0)
#   - retry_at_timeout_s: present when the dispatcher hit a fallback
#       retry path (R1 C7 codex.py timeout classifier)
# Dispatch-gate in emit_generic re-enforces this allowlist defensively
# for any direct caller drift.
_DISPATCHER_ROUTE_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "rail", "reason_code",
    "matrix_sha256_prefix", "matrix_sha256_match",
    "coder", "reviewer", "coder_model", "reviewer_sandbox",
    "fallback_provider",
    # Codex iter 1 P0-1: wall-clock + retry timing carried as **integer
    # milliseconds**, NOT float seconds, because canonical_json forbids
    # floats in HMAC-covered fields per `_lib/canonical_json.py:85`.
    # Float emit would fail HMAC chain with `hmac_error=CanonicalJsonError`,
    # silently dropping the audit-trail signal needed by the
    # `codex_latency_p95_s` predicate aggregator. Aggregator divides by
    # 1000 to recover seconds for p95 percentile comparison.
    "wall_clock_ms", "retry_at_timeout_ms",
})


# PLAN-081 Phase 3 / Sec MF-3 — pair_rail_case allowlist.
# Carries asymmetric VETO matrix Cases A-F decision metadata. NEVER
# persists raw Codex review body / proposed-content / raw file path.
_PAIR_RAIL_CASE_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "case", "claude_verdict", "codex_verdict",
    "precondition_met", "rubric_violation_id", "severity",
    "jaccard_similarity_bucket", "file_path_hash_prefix",
    "tool_name", "human_triage_grace_h",
    # PLAN-161 C5 r5 F2 — per-invocation correlation id (16-hex, minted
    # at review entry; identical on this case emit and its own
    # `pair_rail_review_expected`). Shape-gated in the typed wrapper AND
    # re-coerced in the emit_generic dispatch branch.
    "review_id",
    # ADR-110-AMEND-2 §1.6 — the EFFECTIVE post-clamp codex budget this
    # invocation ran under, as INTEGER MILLISECONDS (canonical_json
    # no-float invariant; same encoding as `dispatcher_route.wall_clock_ms`).
    # Disambiguates a case F caused by a sub-floor CEO_PAIR_RAIL_TIMEOUT_S
    # export from a genuine Codex outage (§4(i) residual). Bounded in the
    # typed wrapper AND re-coerced in the emit_generic dispatch branch.
    "timeout_ms",
})


# PLAN-081 Phase 4 / Sec MF-3 — pair_rail_promotion allowlist.
_PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "run_id", "verdict", "corpus_n", "corpus_manifest_sha",
    "catch_rate_num", "catch_rate_den",
    "fp_rate_bucket", "schema_adherence_pct_bucket", "rubric_gap_pp_bucket",
    "codex_cli_version", "python_version", "git_head_sha_prefix",
    "pass_2_retry_used", "manual_triage",
})


# PLAN-083 Wave 0b sub-agent 0.4 (S106 ceremony) — Sec MF-3
# field allowlist for token_budget_guard_paused.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by token-budget-guard.py when cumulative plan tokens cross threshold × estimate. Volume cap ≤10/hr.
_TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST = frozenset({
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
    "plan_id", "estimate_tokens", "actual_tokens", "ratio_basis_points", "threshold_basis_points",
})


# PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony) — Sec MF-3
# field allowlist for anti_ceo_overhead_block.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by check_anti_ceo_overhead.py PreToolUse hook when CEO-overhead anti-pattern detected. Emit budget ≤20/day sliding window.
_ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST = frozenset({
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
    "anti_pattern_id", "count_in_window", "override_recommended_subagent_type",
})


# PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony) — Sec MF-3
# field allowlist for anti_ceo_overhead_override_used.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by check_anti_ceo_overhead.py when CEO_OVERHEAD_ACK=1 env override bypasses a block.
_ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST = frozenset({
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
    "anti_pattern_id", "override_justification_sha",
})


# PLAN-083 Wave 0b sub-agent 0.7d (S106 ceremony) — Sec MF-3
# field allowlist for smart_loading_resolved.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by smart-loading-resolver.py per resolution. Carries profile + active/suppressed counts + context budget total + arbitration dropped count.
_SMART_LOADING_RESOLVED_ALLOWLIST = frozenset({
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
    "profile", "active_count", "suppressed_count", "context_total_tokens", "arbitration_dropped_count",
})
