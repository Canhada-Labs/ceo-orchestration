"""Lifecycle schemas.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
import re

__all__ = ('emit_session_start', 'emit_session_end', 'emit_prompt_submitted', 'emit_session_stop', 'emit_output_scan_finding', '_AUDIT_TOKENS_ALLOWLIST', '_TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST', '_CODEX_AUDIT_ENVELOPE', '_CODEX_HARNESS_ENUM', '_CODEX_TOOL_RECORDED_TOOL_NAME_ENUM', '_CODEX_TOOL_RECORDED_EVENT_ENUM', '_CODEX_TOOL_RECORDED_ALLOWLIST', '_CODEX_TURN_ENDED_SOURCE_ENUM', '_CODEX_TURN_ENDED_ALLOWLIST', '_GROK_HARNESS_ENUM', '_GROK_TOOL_RECORDED_TOOL_NAME_ENUM', '_GROK_TOOL_RECORDED_EVENT_ENUM', '_GROK_TOOL_RECORDED_ALLOWLIST', '_GROK_TURN_ENDED_SOURCE_ENUM', '_GROK_TURN_ENDED_ALLOWLIST', '_COUNCIL_VENDOR_ENUM', '_COUNCIL_LANE_STATUS_ENUM', '_COUNCIL_LANE_INVOKED_ALLOWLIST', '_CODEX_REVIEW_VERDICT_OUTCOME_ENUM', '_CODEX_REVIEW_DIFF_SHA256_RE', '_CODEX_REVIEW_VERDICT_ALLOWLIST', '_PAIR_RAIL_REVIEW_EXPECTED_TOOL_ENUM', '_PAIR_RAIL_FILE_HASH_PREFIX_RE', '_PAIR_RAIL_REVIEW_ID_RE', '_PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST', '_PAIR_RAIL_TIMEOUT_MS_MAX', '_coerce_pair_rail_timeout_ms', '_DIRECTORY_ADDED_SOURCE_ENUM', '_DIRECTORY_ADDED_HASH_PREFIX_RE', '_DIRECTORY_ADDED_RECORDED_ALLOWLIST', '_NOTIFICATION_TYPE_ENUM', '_NOTIFICATION_MSG_SHA256_PREFIX_RE', '_NOTIFICATION_LIFECYCLE_ALLOWLIST', '_NIGHT_MODE_MODE_ENUM', '_NIGHT_MODE_RESULT_ENUM', '_NIGHT_MODE_HOSTNAME_HASH_RE', '_NIGHT_MODE_TOGGLED_ALLOWLIST', '_LEARNING_ENVELOPE', '_LEARNING_RAIL_ENUM', '_LEARNING_SWITCH_ENUM', '_LESSON_CANDIDATE_STATUS_ENUM', '_LESSON_SCAN_OUTCOME_ENUM', '_LESSON_QUARANTINE_REASON_ENUM', '_LESSON_CREATED_AT_SOURCE_ENUM', '_LESSON_INTEGRITY_CHECK_ENUM', '_LESSON_INTEGRITY_CONSUMER_ENUM', '_LESSON_BOOT_DROP_REASON_ENUM', '_FACT_GATE_SOURCE_ENUM', '_ADVISORY_DAMPEN_CHANNEL_ENUM', '_DISTILLER_OUTCOME_ENUM', '_LEARNING_ID_RE', '_LESSON_SHA256_RE')

def emit_session_start(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    governance_state: str = "unknown",
    gate_1_hashes: Optional[Dict[str, Optional[str]]] = None,
    warmup_bytes: int = 0,
    project: str = "",
) -> None:
    """Emit session_start event (SessionStart.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_start",
        session_id=session_id,
        hook_version=hook_version,
        governance_state=governance_state,
        gate_1_hashes=gate_1_hashes or {},
        warmup_bytes=warmup_bytes,
        project=project,
    )


def emit_session_end(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    reason: str = "normal",
    memory_writable: bool = False,
    memory_index_present: bool = False,
    project: str = "",
) -> None:
    """Emit session_end event (SessionEnd.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_end",
        session_id=session_id,
        hook_version=hook_version,
        reason=reason,
        memory_writable=memory_writable,
        memory_index_present=memory_index_present,
        project=project,
    )


def emit_prompt_submitted(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    prompt_len_bucket: str = "",
    prompt_sha256: str = "",
    redact_hits_count: int = 0,
    injection_family_counts: Optional[Dict[str, int]] = None,
    project: str = "",
) -> None:
    """Emit prompt_submitted event (UserPromptSubmit.py). ADR-056 §Per-hook matrix.

    Privacy: prompt content is NEVER persisted raw — only bucket, hash
    prefix, and family counters.
    """
    emit_generic(
        "prompt_submitted",
        session_id=session_id,
        hook_version=hook_version,
        prompt_len_bucket=prompt_len_bucket,
        prompt_sha256=prompt_sha256,
        redact_hits_count=redact_hits_count,
        injection_family_counts=injection_family_counts or {},
        project=project,
    )


def emit_session_stop(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    reason: str = "user_stop",
    partial_state_saved: bool = False,
    project: str = "",
) -> None:
    """Emit session_stop event (Stop.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_stop",
        session_id=session_id,
        hook_version=hook_version,
        reason=reason,
        partial_state_saved=partial_state_saved,
        project=project,
    )


def emit_output_scan_finding(
    *,
    session_id: str,
    tool_name: str,
    hook_version: str = "1.0.0",
    total_findings: int = 0,
    family_counts: Optional[Dict[str, int]] = None,
    kill_switched: Optional[Dict[str, bool]] = None,
    project: str = "",
) -> None:
    """Emit output_scan_finding event (check_output_secrets.py). ADR-057 §Audit event.

    Only called when total_findings > 0 (hook short-circuits on clean).
    """
    emit_generic(
        "output_scan_finding",
        session_id=session_id,
        tool_name=tool_name,
        hook_version=hook_version,
        total_findings=total_findings,
        family_counts=family_counts or {},
        kill_switched=kill_switched or {},
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-059 SEC-P0-04 / ADR-080 — audit-tokens content-ban
# (Session 62 cont, 2026-04-25)
# ---------------------------------------------------------------------

# Counts-only allowlist for audit_tokens_emitted events.
# Per SEC-P0-04 spec §Emission contract (ALLOWED), the audit-tokens
# stub format MUST emit ONLY these keys. Any forbidden key (raw prompt
# text, tool input/output bodies, sub-agent persona/skill/task content,
# error messages with payload context, stack traces with locals) is
# stripped by scrub_audit_tokens_event() and a key-dropped breadcrumb
# is emitted. Defense-in-depth on top of audit-tokens.py CLI flag.
_AUDIT_TOKENS_ALLOWLIST = frozenset({
    # Required by emit_audit_tokens_emitted (always present)
    "action",
    "session_id",
    "timestamp",
    "window_seconds",
    "events_scanned",
    "tokens_in_total",
    "tokens_out_total",
    "cost_cents",
    "tier_id_distribution",
    "detector_findings_count",
    "hook_duration_ms",
    # _write_event metadata (added by base emitter; pre-allowed so
    # scrub doesn't strip them on round-trip)
    "ts",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "project",
})


# PLAN-125 WS-1 — Sec MF-3 field allowlist for tool_call_lifecycle_recorded.
# Deny-by-default. The 4 payload fields + the base-envelope keys that
# _write_event adds back (pre-allowed so the scrub does not strip them on a
# round-trip). Anything else (a raw mcp__* tool name, a raw duration_ms, a
# prompt/command/path body) is DROPPED before the wire (MF-SEC-1/3).
_TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tool_name_enum", "duration_bucket", "success", "orphan",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# ---------------------------------------------------------------------------
# PLAN-155 Wave 4 (Codex harness audit chain / SENT-CX-B, ADR-161) — Sec MF-3
# closed enums + field allowlists for the two codex audit-chain actions.
# Deny-by-default; every emit_generic branch ALSO re-coerces the enum VALUES
# by closed-set membership so a direct emit_generic caller can never sign a
# raw tool name / patch body / command string into the HMAC chain. NEVER
# _EMIT_GENERIC_PASSTHROUGH.
# ---------------------------------------------------------------------------

# Base signed envelope both codex actions pre-allow so the scrub does not strip
# _write_event's own keys on a round-trip. Mirrors _LEARNING_ENVELOPE /
# _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST shape.
_CODEX_AUDIT_ENVELOPE = frozenset({
    "action", "session_id", "project",
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# Harness discriminator — always "codex" for these two actions (they exist
# ONLY on the codex host wire), but kept as a closed field so completeness
# analysis can pivot codex_tool_recorded vs the claude-only agent_spawn rail
# without inferring from the action name. A miss coerces to "codex".
_CODEX_HARNESS_ENUM = frozenset({"codex"})


# codex_tool_recorded — the per-tool-call closed tool-name enum. The codex host
# adapter has ALREADY normalized apply_patch -> Write/Edit and spawn_agent ->
# Task before this point; a raw mcp__<server>__<tool> string coerces to
# "mcp_other" and anything unrecognized to "other" so NO raw tool name reaches
# the wire even on a direct caller path (MF-SEC-1). Deliberately a SEPARATE
# constant from _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM (no cross-plan pin-sync
# coupling to _lib/tool_lifecycle.py).
_CODEX_TOOL_RECORDED_TOOL_NAME_ENUM = frozenset({
    "Bash", "Edit", "Write", "Task", "Read",
    "MultiEdit", "NotebookEdit", "Glob", "Grep", "WebFetch", "WebSearch",
    "mcp_other", "other",
})


# codex_tool_recorded — the codex host event that produced this per-tool
# append. Only PostToolUse produces action (A); a miss coerces to "PostToolUse".
_CODEX_TOOL_RECORDED_EVENT_ENUM = frozenset({"PostToolUse"})


_CODEX_TOOL_RECORDED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "harness", "hook_event_name", "tool_name_enum",
})


# codex_turn_ended — how the turn-end was signaled. "stop"/"subagent_stop" are
# the codex Stop-family hook events; "notify" is the codex notify program
# surface; "wrapper" is the headless codex-exec-wrapper.sh bracket (its
# synthetic Stop envelope). A miss coerces to "other".
_CODEX_TURN_ENDED_SOURCE_ENUM = frozenset({
    "stop", "subagent_stop", "notify", "wrapper", "other",
})


_CODEX_TURN_ENDED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "harness", "source", "stop_hook_active",
})


# ---------------------------------------------------------------------------
# PLAN-156 Wave 4 (SENT-GK-B) — grok host audit actions. Mirror of the codex
# pair above; SEPARATE constants (no cross-plan pin-sync coupling). Grok's
# turn-end surface is narrower than codex's: only the `stop` hook is a
# reliable turn-boundary (SessionEnd does not fire in headless runs — S269),
# so the source enum omits the codex-specific `notify`/`wrapper` and keeps
# `stop`/`subagent_stop`/`other`. `stop_hook_active` has no grok analogue and
# is NOT allowlisted (a direct caller cannot smuggle it onto the wire).
# ---------------------------------------------------------------------------
_GROK_HARNESS_ENUM = frozenset({"grok"})


_GROK_TOOL_RECORDED_TOOL_NAME_ENUM = frozenset({
    "Bash", "Edit", "Write", "Task", "Read",
    "MultiEdit", "NotebookEdit", "Glob", "Grep", "WebFetch", "WebSearch",
    "mcp_other", "other",
})


_GROK_TOOL_RECORDED_EVENT_ENUM = frozenset({"PostToolUse"})


_GROK_TOOL_RECORDED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "harness", "hook_event_name", "tool_name_enum",
})


_GROK_TURN_ENDED_SOURCE_ENUM = frozenset({
    "stop", "subagent_stop", "other",
})


_GROK_TURN_ENDED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "harness", "source",
})


# ---------------------------------------------------------------------------
# PLAN-156 Wave 6 (SENT-GK-F) — cross-vendor council lane invocation. A LIVE
# external-egress action: repo scope leaves the process to xAI/OpenAI, so the
# allowlist is deny-by-default and carries NO scope text, NO findings, NO
# prompt bytes — only WHICH vendor lane ran and its terminal status. The
# scope is NEVER persisted (an operator ratifies the egress at OQ5; the audit
# row records the fact of egress, not its content).
# ---------------------------------------------------------------------------
_COUNCIL_VENDOR_ENUM = frozenset({"claude", "codex", "grok", "other"})


_COUNCIL_LANE_STATUS_ENUM = frozenset({"ok", "unavailable", "other"})


_COUNCIL_LANE_INVOKED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "vendor", "lane_status",
})


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — pair-rail liveness telemetry pair (CF-9). Sec MF-3
# deny-by-default; every branch also re-coerces VALUES by closed-set
# membership / bounded shape so a direct emit_generic caller can never sign
# free text into the HMAC chain. NEVER _EMIT_GENERIC_PASSTHROUGH.
# ---------------------------------------------------------------------------

# Closed outcome enum for the Stop-hook cross-review. The COERCION TARGET for
# an unrecognized value is "skipped_failopen" (never a healthy-class value):
# unparseable telemetry input must not be able to claim rail health.
_CODEX_REVIEW_VERDICT_OUTCOME_ENUM = frozenset({
    "clean", "findings", "skipped_failopen", "detected_only",
})


# 64-lowercase-hex sha256 shape gate for diff_sha256; off-shape -> "".
_CODEX_REVIEW_DIFF_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


_CODEX_REVIEW_VERDICT_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "outcome", "diff_sha256",
})


# Mirrors emit_pair_rail_case's write-tool coercion set (+ the "unknown"
# coercion target itself).
_PAIR_RAIL_REVIEW_EXPECTED_TOOL_ENUM = frozenset({
    "Edit", "Write", "MultiEdit", "NotebookEdit", "unknown",
})


# r4 F2 — bounded shape gate for `file_path_hash_prefix` (same 16-hex
# SHA-256-prefix token `pair_rail_case` carries; raw path forbidden per
# LLM06). 0..16 lowercase hex; off-shape -> "". Kept as the legacy
# fallback bucket key (+ harmless secondary key) for id-less events.
_PAIR_RAIL_FILE_HASH_PREFIX_RE = re.compile(r"^[0-9a-f]{0,16}$")


# r5 F2 — bounded shape gate for `review_id`, the PER-INVOCATION
# correlation id (os.urandom(8).hex() minted by check_pair_rail.py
# `_decide()` at review entry; identical on a review's
# `pair_rail_review_expected` AND its own `pair_rail_case`).
# r6 F2 tightening: EXACTLY 16 lowercase hex, or exactly "" (legacy
# id-less emit — falls back to the r4 (session, file-hash) bucket-count
# heuristic in /ceo-boot). Any other value (short/partial, oversize,
# uppercase, non-hex) is DROPPED to "" — never truncated: the r5
# `{0,16}` + truncate-before-validate let two distinct off-shape ids
# sharing their first 16 chars ALIAS to one pairing key, so an older
# terminal could offset a later dead review again (the exact F2
# false-green this id exists to prevent). The exact-id pairing is what
# counting could not do: pair a specific expected with its OWN case, so
# an old completed case for the SAME (session, file) can never offset a
# later dead expected.
_PAIR_RAIL_REVIEW_ID_RE = re.compile(r"^([0-9a-f]{16})?$")


_PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    # ADR-110-AMEND-2 §1.6 — `timeout_ms`: the EFFECTIVE post-clamp codex
    # budget in INTEGER MILLISECONDS (canonical_json forbids floats in
    # HMAC-covered fields; a float here is not merely rejected — the spool
    # writer DROPS the whole event). Carried on BOTH pair-rail liveness
    # actions so the expected/case pair records the budget it ran under.
    "tool_name", "file_path_hash_prefix", "review_id", "timeout_ms",
})


# ADR-110-AMEND-2 §1.6 — shared bound for the pair-rail effective-budget
# field. 6_000_000 ms = 6000 s = 10x the hook's own 600 s clamp ceiling:
# wide enough that a legitimate value is never distorted, tight enough
# that a direct emit_generic caller cannot sign an unbounded number.
_PAIR_RAIL_TIMEOUT_MS_MAX = 6_000_000


def _coerce_pair_rail_timeout_ms(value: Any) -> int:
    """Bound an effective-budget value to `[0, 6_000_000]` integer ms.

    Deny-by-default VALUE coercion (Sec MF-3): a non-numeric, boolean,
    NaN or infinite input becomes `0` (the "unknown budget" sentinel)
    rather than reaching the signed chain. `bool` is rejected explicitly
    because `isinstance(True, int)` would otherwise sign `1` as a budget.
    """
    if isinstance(value, bool):
        return 0
    try:
        ms = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(_PAIR_RAIL_TIMEOUT_MS_MAX, ms))


# ---------------------------------------------------------------------------
# PLAN-163 T3.1/T3.2 (CC 2.1.220 substrate uplift / ADR-183) — the two new
# harness lifecycle actions. Sec MF-3 deny-by-default; every branch also
# re-coerces VALUES by closed-set membership / bounded shape so a direct
# emit_generic caller can never sign free text into the HMAC chain.
# NEVER _EMIT_GENERIC_PASSTHROUGH.
# ---------------------------------------------------------------------------

# directory_added_recorded — how the workspace root was added. The CC 2.1.220
# wire carries `slash_command` (/add-dir) and `register_repo_root` (the SDK
# control_request); `session_start_snapshot` is RESERVED for the documented
# --add-dir-at-LAUNCH blind spot (the launch flag never fires DirectoryAdded,
# so a SessionStart roots snapshot is the only producer that can record those
# roots — keeping the discriminator here means that mitigation never needs a
# second kernel-file ceremony). Off-enum COERCES to "other" (never echoed).
_DIRECTORY_ADDED_SOURCE_ENUM = frozenset({
    "slash_command", "register_repo_root", "session_start_snapshot", "other",
})


# Exact 12-lowercase-hex sha256 prefix of the ABSOLUTE directory path, or
# exactly "" — the raw path is forbidden on the wire (LLM06 side-channel
# guard; same 12-hex token class as `message_sha256_prefix` below and the
# federation path re-hash, and the EXACT length the producer
# check_directory_added.py `_hash_prefix()` computes). The RAW value is
# validated (r6 F2 precedent: off-shape incl. oversize is DROPPED to "",
# never truncated — truncate-before-validate lets two distinct oversize
# values alias to one 12-hex key).
_DIRECTORY_ADDED_HASH_PREFIX_RE = re.compile(r"^([0-9a-f]{12})?$")


_DIRECTORY_ADDED_RECORDED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "source", "directory_hash_prefix",
})


# notification_lifecycle — the harness `notification_type` enum is OPEN
# (matcher-visible string), so the wire vocabulary here is CLOSED and any
# unrecognized value COERCES to "other" — the raw type string is NEVER
# echoed into the signed chain (no-value-echo).
_NOTIFICATION_TYPE_ENUM = frozenset({
    "agent_needs_input", "agent_completed", "permission_request", "other",
})


# Exact 12-lowercase-hex sha256 prefix of the notification message body, or
# exactly "" (empty/absent message). Hash, never content: a notification
# message can quote tool output, file paths, or secrets. RAW value
# validated; off-shape incl. oversize DROPPED to "", never truncated.
_NOTIFICATION_MSG_SHA256_PREFIX_RE = re.compile(r"^([0-9a-f]{12})?$")


_NOTIFICATION_LIFECYCLE_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "notification_type", "has_title", "message_sha256_prefix",
})


# ---------------------------------------------------------------------------
# PLAN-165 P2 (night-mode) — Owner-invoked autonomy posture toggle. Sec MF-3
# deny-by-default; the branch also re-coerces VALUES by closed-set membership
# / bounded shape so a direct emit_generic caller can never sign free text
# into the HMAC chain. NEVER _EMIT_GENERIC_PASSTHROUGH.
# ---------------------------------------------------------------------------

# night_mode_toggled — the posture the invocation wrote / restored. CLOSED
# vocabulary: the harness accepts a wider defaultMode enum, but night-mode
# only ever writes "acceptEdits" (on) or restores "manual" / removes the key
# ("absent" — the overlay had no defaultMode). Off-enum COERCES to "other"
# and is NEVER echoed — a free-text mode string could smuggle content into
# the signed chain.
_NIGHT_MODE_MODE_ENUM = frozenset({
    "acceptEdits", "manual", "absent", "other",
})


# night_mode_toggled — invocation outcome. Off-enum COERCES to "other".
#   applied — settings write + marker landed (on/off took effect)
#   noop    — idempotent second on / second off (exit 0, nothing written)
#   refused — a guard refused (CI env set; malformed settings.local.json
#             fail-closed exit; lock contention)
#   failed  — write attempted but read-back diverged / replace failed
_NIGHT_MODE_RESULT_ENUM = frozenset({
    "applied", "noop", "refused", "failed", "other",
})


# Exact 12-lowercase-hex sha256 prefix of the machine hostname, or exactly
# "" — the toggle is per-machine state, so recurrence analysis needs a
# machine discriminator, but the RAW hostname can carry usernames or org
# identity (LLM06 side-channel guard; same 12-hex token class as
# directory_hash_prefix above). RAW value validated; off-shape incl.
# oversize is DROPPED to "", never truncated (truncate-before-validate
# lets two distinct oversize values alias to one 12-hex key).
_NIGHT_MODE_HOSTNAME_HASH_RE = re.compile(r"^([0-9a-f]{12})?$")


_NIGHT_MODE_TOGGLED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE | frozenset({
    "mode", "previous_mode", "result", "hostname_hash",
})


# ---------------------------------------------------------------------------
# PLAN-154 (Gated Learning Loop / ADR-160) — Sec MF-3 closed enums + field
# allowlists for the 11 learning-loop actions. All deny-by-default; every
# branch also re-coerces VALUES by closed-set membership / bounded charset so
# a direct emit_generic caller can never sign free text into the HMAC chain
# (A2 metadata-only). NEVER _EMIT_GENERIC_PASSTHROUGH.
# ---------------------------------------------------------------------------

# Base signed envelope every PLAN-154 allowlist pre-allows so the scrub does
# not strip _write_event's own keys on a round-trip.
_LEARNING_ENVELOPE = frozenset({
    "action", "session_id", "project",
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


_LEARNING_RAIL_ENUM = frozenset({"observe", "distill", "boot_render", "fact_gate", "bash_indirect"})


_LEARNING_SWITCH_ENUM = frozenset({
    "CEO_LEARNING_OBSERVE", "CEO_LEARNING_BOOT_LESSONS",
    "CEO_LEARNING_DISTILL_MODEL", "CEO_FACT_GATE_ENFORCE",
    "CEO_FACT_GATE_SHADOW", "CEO_ADVISORY_DAMPEN",
    "CEO_SOTA_DISABLE", "other",
    "CEO_BASH_INDIRECT_GUARD", "CEO_BASH_INDIRECT_HEURISTICS",
})


_LESSON_CANDIDATE_STATUS_ENUM = frozenset({"PENDING", "QUARANTINED"})


_LESSON_SCAN_OUTCOME_ENUM = frozenset({
    "clean", "scanner_unavailable", "injection_pattern",
})


_LESSON_QUARANTINE_REASON_ENUM = frozenset({
    "injection_pattern", "content_hash_mismatch", "vocab_violation",
})


_LESSON_CREATED_AT_SOURCE_ENUM = frozenset({"chain", "file"})


_LESSON_INTEGRITY_CHECK_ENUM = frozenset({
    "hash_mismatch", "missing_approval_event", "vocab_violation",
    "hash_unverifiable",
})


_LESSON_INTEGRITY_CONSUMER_ENUM = frozenset({"boot", "spawn"})


_LESSON_BOOT_DROP_REASON_ENUM = frozenset({
    "bad_shape", "hash_malformed", "vocab", "oversize",
    "validator_unavailable", "validator_block", "scan_redacted",
    "excess", "other",
})


_FACT_GATE_SOURCE_ENUM = frozenset({
    "settings", "env_emergency_off", "sota_master_off", "default_advisory",
})


_ADVISORY_DAMPEN_CHANNEL_ENUM = frozenset({"stderr_prose"})


_DISTILLER_OUTCOME_ENUM = frozenset({
    "ok", "no_new_events", "schema_reject", "scan_unavailable",
    "token_ceiling", "model_error", "store_unavailable",
    "input_surface_unavailable",
})


# Bounded-token shapes (mirror lessons.py `_CANDIDATE_TOKEN_RE` and the
# ceo-boot `_LESSON_ID_RE`): identifier-charset only, hard length cap. A
# value that fails the shape is coerced to "" — never echoed.
_LEARNING_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")


_LESSON_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
