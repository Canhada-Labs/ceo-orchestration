"""Optimizer.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
from .boot_schemas import _OPTIMIZER_ENVELOPE

__all__ = ('_VERIFY_AFTER_EDIT_FINDING_ALLOWLIST', '_ADEQUACY_GATE_FLAG_ALLOWLIST', '_QUOTA_ERROR_CLASS_ENUM', '_QUOTA_ERROR_SOURCE_ENUM', '_QUOTA_EXHAUSTED_ALLOWLIST', '_AUTO_COMPACT_REASON_ENUM', '_AUTO_COMPACT_SUPPRESS_REASON_ENUM', '_CONTEXT_AUTO_COMPACTED_ALLOWLIST', '_CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST', '_MIDDLE_OUT_REASON_ENUM', '_CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST', '_CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST', '_SUPPLY_CHAIN_VERDICT_ENUM', '_SUPPLY_CHAIN_REASON_ENUM', '_SUPPLY_CHAIN_ECOSYSTEM_ENUM', '_SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST', '_SPAWN_RAIL_ENUM', '_SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST', '_SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST', '_SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST', '_ACTION_REQUIRED_KIND_ENUM', '_ACTION_REQUIRED_REJECT_ENUM', '_ACTION_REQUIRED_HELD_ALLOWLIST', '_ACTION_REQUIRED_RESUMED_ALLOWLIST', '_ACTION_REQUIRED_REJECTED_ALLOWLIST', '_MODEL_ROUTING_ENFORCED_ALLOWLIST', '_MODEL_ROUTING_EVAL_ERROR_ALLOWLIST')

_VERIFY_AFTER_EDIT_FINDING_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "checker", "lang", "finding_count",
))


_ADEQUACY_GATE_FLAG_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "flag_reason", "lang", "flag_count",
))


# PLAN-133 B5 — provider/cost error taxonomy mirror closed enums + allowlist (Sec MF-3).
# error_class is coerced to a closed-enum member in the dispatch-gate (S172: an
# invalid value is replaced by "unknown", NEVER echoed). source is a closed enum
# distinguishing the metered-API path from the subscription main loop. NO
# retry_delay / Retry-After / body / header value is ever allowlisted — the
# backoff seconds are a caller-side float that must never reach the payload.
_QUOTA_ERROR_CLASS_ENUM = frozenset({
    "quota_exhausted", "credits_exhausted", "auth", "rate_limited", "overloaded",
    "server_error", "bad_request", "timeout", "network", "unknown",
})


_QUOTA_ERROR_SOURCE_ENUM = frozenset({"subscription_main_loop", "metered_api", "subprocess", "unknown"})


_QUOTA_EXHAUSTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    # closed-enum scalars + bounded ints ONLY
    "error_class",        # closed enum (coerced)
    "source",             # closed enum (coerced)
    "http_status",        # int (the bare status code; no body)
    "retryable",          # bool
    "metered_api_only",   # bool
    "attempt",            # int 0..99 (clamped) — which retry attempt
    "project",
))


# PLAN-133 D1 — proactive auto-compaction telemetry. Closed enums so a malformed
# value coerces to a safe sentinel (S172 doctrine: never echo a rejected value).
# `reason` mirrors REASON_* in scripts/context-budget.py. `trigger` distinguishes
# the high/low-water hysteresis edge. NO bytes/tokens raw text — only bucketed
# percentages (0..100 clamp) so a transcript size can never be reconstructed
# field-by-field into a side channel.
_AUTO_COMPACT_REASON_ENUM = frozenset({
    "compact", "cooldown", "reclaim_floor", "not_rearmed",
    "below_high_water", "disabled", "other",
})


_AUTO_COMPACT_SUPPRESS_REASON_ENUM = frozenset({
    "cooldown", "reclaim_floor", "other",
})


# context_auto_compacted — a compaction WAS performed. Carries only the closed
# reason enum + the hysteresis percentages + the reclaimed-percent bucket + a
# turn counter. `reason` IS in the allowlist (the dispatch gate coerces it).
_CONTEXT_AUTO_COMPACTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "usage_pct", "reclaim_pct", "turns_since_last",
))


# context_auto_compact_suppressed — a would-be compaction was SKIPPED by a gate
# (cooldown or reclaim-floor). Carries the closed suppression reason + the same
# bucketed percentages.
_CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "suppress_reason", "usage_pct", "reclaim_pct", "turns_since_last",
))


# PLAN-133 D5 — middle-out degradation telemetry for the context-overflow path.
# Closed enums so a malformed value coerces to a safe sentinel (S172 doctrine:
# never echo a rejected value). `reason` mirrors MO_REASON_* in
# scripts/context-budget.py. Only bucketed COUNTS + a small ladder-rung int are
# carried (0..99 clamp) — NOT the message text, tool/agent identity, file paths,
# or raw token totals — so a transcript can never be reconstructed field-by-
# field into a side channel.
_MIDDLE_OUT_REASON_ENUM = frozenset({
    "degraded", "failed", "no_overflow", "disabled", "other",
})


# context_middle_out_degraded — a degradation pass DID elide >=1 message's
# middle to fit the budget. Carries only the closed reason enum + bucketed
# counts (degraded / total messages + protect_last) + the ladder `rung` int
# (0..99 clamp) + a coarse reclaim-tokens BUCKET + the `fits_after` bool.
# `reason` IS in the allowlist (the dispatch gate coerces it).
_CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "rung", "degraded_count", "total_count", "protect_last",
    "reclaim_bucket", "fits_after",
))


# context_middle_out_degrade_failed — the ladder was exhausted (or no message
# was eligible) and the context STILL overflows; the caller must summarize /
# compact / fail upstream. Carries the closed reason + bucketed counts + rung.
_CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "rung", "degraded_count", "total_count", "protect_last",
    "reclaim_bucket",
))


# PLAN-133 E2 — supply-chain advisory closed enums + field allowlist.
# verdict/reason are closed enums (coerce-to-"other" on a miss); ecosystem
# coerces to "other"; advisory_count is an int clamped 0..99. The package
# name + advisory ids are caller-supplied but are PUBLIC identifiers (a pkg
# name + a published OSV id) — never a path, command, env, or error body.
_SUPPLY_CHAIN_VERDICT_ENUM = frozenset({"BLOCK", "ALLOW", "SKIP"})


_SUPPLY_CHAIN_REASON_ENUM = frozenset({
    "mal_advisory_present", "clean", "unknown", "malformed_response",
    "network_timeout", "network_error", "offline", "disabled", "no_package",
})


_SUPPLY_CHAIN_ECOSYSTEM_ENUM = frozenset({"npm", "PyPI", "other"})


_SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "verdict", "reason", "ecosystem", "package", "advisory_count",
))


# PLAN-133 E3 — closed enums + deny-by-default field allowlists. Mirror the
# §7 (verify_after_edit_finding) pattern exactly. NO raw path / prompt / tool
# arg ever appears — `detail` is tool-NAMES + counts only; paths are 12-hex
# sha256 prefixes.
_SPAWN_RAIL_ENUM = frozenset({"tool_scope", "depth", "overlap", "other"})


_SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "rail", "enforced", "detail",
))


_SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "rail", "enforced", "count",
))


_SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "path_hashes", "path_count",
))


# PLAN-133 E6 — HITL confirmation-rail closed enums + field allowlists.
# S172 doctrine: an invalid value coerces to a safe sentinel, never echoed.
_ACTION_REQUIRED_KIND_ENUM = frozenset({
    "bash_command", "file_write", "file_delete", "spend_over_cap",
    "spawn", "network_egress", "other",
})


_ACTION_REQUIRED_REJECT_ENUM = frozenset({
    "unknown_token", "replayed", "expired", "session_mismatch",
    "action_id_mismatch", "malformed_request", "infra_error", "other",
})


_ACTION_REQUIRED_HELD_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "kind", "token_sha256", "expires_at",
))


_ACTION_REQUIRED_RESUMED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "token_sha256",
))


_ACTION_REQUIRED_REJECTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "token_sha256", "reject_reason",
))


# PLAN-112-FOLLOWUP-persona-routing-wire W2 — `model_routing_enforced`
# field allowlist (deny-by-default). Forensic telemetry of the god-mode
# matrix consult. `killswitch_armed` is a bool (canonical_json-safe).
# `decision` enum: enforce_telemetry | advisory | eval_error — NO `block`
# value (block deferred). NO prompt/description/frontmatter-path content.
_MODEL_ROUTING_ENFORCED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "mode", "recommended_model",
    "killswitch_armed", "decision",
})


# PLAN-112-FOLLOWUP-persona-routing-wire W2 — `model_routing_eval_error`
# fail-open infra branch allowlist. Carries archetype + reason_code +
# `decision` (always the constant "eval_error" — keeps the `decision`
# enum {enforce_telemetry, advisory, eval_error} consistent across BOTH
# new actions per AC5).
_MODEL_ROUTING_EVAL_ERROR_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "reason_code", "decision",
})
