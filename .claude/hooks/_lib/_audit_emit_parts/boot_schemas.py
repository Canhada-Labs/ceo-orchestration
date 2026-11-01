"""Boot schemas.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_CEO_BOOT_EMITTED_ALLOWLIST', '_CEO_BOOT_CHECK_SKIPPED_ALLOWLIST', '_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST', '_MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST', '_MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST', '_TASK_ROUTE_ADVISED_ALLOWLIST', '_REALITY_LEDGER_FINDING_ALLOWLIST', '_TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST', '_COST_ENVELOPE_CAPPED_ALLOWLIST', '_SWARM_RUNAWAY_SUSPECTED_ALLOWLIST', '_SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST', '_SWARM_LAYER_3_4_BLOCKED_ALLOWLIST', '_EXECUTION_CONTEXT_SIGNED_ALLOWLIST', '_EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST', '_MODEL_ROUTING_ADVISED_ALLOWLIST', '_OPTIMIZER_ENVELOPE', '_OPTIMIZER_ALLOWLISTS', '_ACCEL_LANG_ENUM', '_VERIFY_CHECKER_ENUM', '_ADEQUACY_REASON_ENUM', '_CODEX_REVIEW_STATUS_ENUM', '_CODEX_REVIEW_SOURCE_ENUM', '_PERSONA_MATCH_MODALITY_ENUM')

# PLAN-065 Phase 2 / ADR-098 — Sec MF-3 field allowlist for /ceo-boot events.
# Whitelist (deny-by-default). Forbidden fields stripped + breadcrumbed before
# emit. Caller passes ceo_boot_emitted/_check_skipped via the typed wrappers
# below; emit_generic dispatch is also gated by the allowlist (defense-in-
# depth on adopter or future-CEO drift). See PLAN-065 §4.3.4.
_CEO_BOOT_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",  # reserved nullable per v2 contract
    "hmac", "hmac_error",  # ADR-055 chain fields
    "gate_pass", "duration_ms", "checks_total", "checks_failed", "cache_hit",
})


_CEO_BOOT_CHECK_SKIPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "check_name", "timeout_ms",
})


_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST = frozenset({  # PLAN-093 Wave C.5 + PLAN-104 carry-over
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "score_x100", "cells_covered", "total_cells",
    # PLAN-104 Wave A.2 — S127 scope-(b) carry-over (3 fields).
    "window_hours", "events_with_target_archetype", "eligible_demand_events",
})


# PLAN-070 Round 6 / Codex R6-01 closure — Sec MF-3 field allowlist for
# Layer B MCP middleware events. Tightened to the agreed 6-field contract
# (Sec ACCEPT-CONDITIONAL R4 + Codex R6-01 P2 ratification, 2026-05-05):
#
#   caller-supplied: tool_name, target_path, reason
#   auto-baseline:   action, ts (==timestamp), session_id, project,
#                    event_schema, tokens_*, hmac, hmac_error
#
# Deny-by-default. NO raw params, NO content/patch body, NO sentinel
# body, NO error class names, NO reason_code (renamed -> reason), NO
# file_path (renamed -> target_path). Pre-R6-01 the allowlist included
# `reason_code`/`file_path`/`sentinel`/`error` as caller fields — Codex
# R6-01 flagged this as schema drift from the agreed Sec MF-3 contract;
# the canonical_guard.py emit call sites are simultaneously renamed.
_MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tool_name", "target_path", "reason",
})


_MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST = _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST


# PLAN-071 / ADR-104 — task-route + reality-ledger field allowlists
# (Sec MF-3 enforcement, deny-by-default). Forbidden fields stripped +
# breadcrumb action emitted. Token counts, cost, prompt content,
# SKILL.md content, file paths, recommendation text body, environment
# values are NEVER persisted to audit-log.
#
# S87 ceremony hot-fix (post Codex audit #15): the ceremony script's
# first injection pass skip-check matched on the dispatch-gate
# REFERENCE (audit_emit.py:2037+2046) instead of the definition,
# leaving these frozensets undefined. Codex MCP audit caught the
# runtime NameError pre-tag; injected directly via Bash python3
# inline (matches S80 ceremony pattern; arbitration-kernel hook
# matcher is Edit|Write|MultiEdit only).
_TASK_ROUTE_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "contract_id", "classification", "task_description_hmac",
    "duration_ms",
})


_REALITY_LEDGER_FINDING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "detector", "severity",
    # confidence_bps: integer basis-points (confidence × 1000, 0..1000).
    # canonical_json forbids floats; the old "confidence" float (0.0-1.0)
    # caused CanonicalJsonError on every reality_ledger_finding emit.
    "confidence_bps",
    "claim_source_sha256", "finding_count_in_run",
})


# PLAN-101 Wave B / ADR-104-AMEND-1 §E — task_route_ground_truth_label.
# Append-only ground-truth join-key for AEK calibration C3 FPR matrix.
# Sec MF-3 deny-by-default: only the 8 fields below persist; LLM06
# hold preserved (raw task descriptions never persisted via this row).
_TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "contract_id", "ground_truth_class", "ground_truth_source",
    "annotation_confidence_bps",
})


# PLAN-102 Wave A / ADR-133 §A — cost_envelope_capped.
# Emitted by check_cost_envelope.py on HARD CAP breach.
# Sec MF-3 deny-by-default: project_path raw, user_id raw, plan body,
# command text are NEVER persisted via this row.
_COST_ENVELOPE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "class_tier", "window_breached", "cap_cents", "current_cents",
})


# PLAN-102 Wave A / ADR-133 §B — swarm_runaway_suspected.
# Reverse-tripwire over 24h rolling iteration counter; advisory only.
_SWARM_RUNAWAY_SUSPECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "iteration_count_24h", "threshold", "triggering_class",
})


# PLAN-102 Wave A / ADR-133 §C — swarm_paused_owner_absent.
# Weekend-burn detector. loop_duration_hours bucketed (>=1h) to avoid
# wallclock side-channel leakage.
_SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "loop_duration_hours", "last_owner_read_iso", "swarm_pid",
})


# PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — swarm_layer_3_4_blocked.
# Per-iteration runtime gate event (distinct from swarm_paused_owner_absent
# which is the weekend-burn detector). LLM06 hold: NO command text, NO
# sentinel body, NO env values, NO file paths, NO error stack traces.
_SWARM_LAYER_3_4_BLOCKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "class_tier", "reason_code", "loop_id",
})


# PLAN-102 Wave B / ADR-133 §D — execution_context_signed.
# Emitted whenever an execution_context HMAC is recorded against an
# autonomous-loop iteration. NO command text, NO plan body.
_EXECUTION_CONTEXT_SIGNED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "context_hash", "key_id", "iteration",
})


# PLAN-102 Wave B / ADR-133 §D — execution_context_validation_failed.
# Emitted when execution_context HMAC verification fails (tamper signal).
# Sec MF-3 deny-by-default: forbid raw context body.
_EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "context_hash", "key_id", "iteration", "failure_reason",
})


# PLAN-078 Wave 1 — `model_routing_advised` field allowlist (deny-by-default).
# 6 caller fields per plan §4 Wave 1 + the auto-baseline (action, ts,
# session_id, project, event_schema, tokens_*, hmac, hmac_error) added by
# `_write_event`. NO prompt content, NO description, NO path of agent
# frontmatter file, NO classify rationale, NO env-var values.
#
# Codex W1+W2 fix-pack #2: confidence is integer basis-points (0..1000)
# instead of float — canonical_json forbids floats, otherwise HMAC chain
# breaks with `hmac=null` + `hmac_error=CanonicalJsonError` breadcrumb.
# 0.875 caller → 875 emitted; consumer divides by 1000 to recover ratio.
_MODEL_ROUTING_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "task_type", "model_recommended",
    "confidence_basis_points", "applied_or_skipped", "override_reason",
})


# PLAN-122 WS12 — Sec MF-3 deny-by-default field allowlists for the optimizer
# recommender actions. The allowlist gates only CALLER-supplied fields (the
# scrub runs in emit_generic BEFORE _write_event); _write_event adds the
# ts/event_schema/tokens_*/hmac/hmac_error envelope by setdefault AFTER the
# scrub, so those reserved fields are NOT (and must NOT be) allowlisted here —
# allowlisting tokens_* would let a caller inject a token-count side channel
# (Codex 019e7ebc P1). The optimizer caller passes only `action` + `session_id`
# + the per-action fields below. NO prompt body, NO file paths, NO label free
# text, NO secret/token side-channel.
_OPTIMIZER_ENVELOPE = ("action", "session_id")


_OPTIMIZER_ALLOWLISTS = {
    "optimizer_route_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "route", "complexity_bucket", "parallelizable", "suggested_width",
        "prompt_len_bucket", "kill_switch_state",
    )),
    "fanout_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "subtask_count", "suggested_width", "width_capped", "budget_governed",
        "rate_backoff_applied", "models_basis",
    )),
    "model_choice_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "subtask_index", "model_recommended", "confidence_basis_points",
        "cost_governed", "fell_back_to_static",
    )),
    "rag_context_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "router_decision", "chunks_returned", "kill_switch_state",
    )),
    "codex_review_disabled": frozenset(_OPTIMIZER_ENVELOPE + (
        "reason",
    )),
    # PLAN-122 WS3 — per-phase Codex review event. Caller-supplied fields ONLY
    # (PhaseReview-shaped, redacted). NO raw Codex text, NO tokens_* side channel,
    # NO review_disabled_signal bool.
    "codex_review_invoked": frozenset(_OPTIMIZER_ENVELOPE + (
        "phase_number", "review_status", "summary_hash", "thread_id_redacted",
        "codex_model", "duration_ms", "violations_found_count",
        "review_source", "target_ref_hash",  # PLAN-132 / ADR-145 (branch-binding)
    )),
}


# PLAN-128 §7 (S217) — accelerator catch-emit closed enums + allowlists (Sec MF-3).
# Invalid enum value is coerced to "other" in the dispatch-gate (S172: never echo the
# rejected value); the breadcrumb lists dropped KEY NAMES only. Counts clamped 0..99.
_ACCEL_LANG_ENUM = frozenset({"python", "js_ts", "go", "other"})


_VERIFY_CHECKER_ENUM = frozenset({"py_compile", "ruff", "eslint", "node_check", "go_build", "other"})


_ADEQUACY_REASON_ENUM = frozenset({"no_test_delta", "weak_assertion", "uncovered_change", "other"})


# PLAN-132 / ADR-145 — closed enums for cross-model review provenance + match
# modality. S172 doctrine: an invalid value coerces to a safe sentinel, never echoed.
_CODEX_REVIEW_STATUS_ENUM = frozenset({"invoked", "passed", "failed", "deferred", "other"})


_CODEX_REVIEW_SOURCE_ENUM = frozenset({"phase_gate", "user_code_auto", "adhoc_mcp", "other"})


_PERSONA_MATCH_MODALITY_ENUM = frozenset({"native_spawn", "codex_review"})
