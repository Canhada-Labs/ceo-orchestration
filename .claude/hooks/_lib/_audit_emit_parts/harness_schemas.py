"""Harness schemas.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
import re
from .lifecycle_schemas import _LEARNING_ENVELOPE

__all__ = ('_learning_token_field', '_learning_sha256_field', '_learning_scope_tags_field', '_learning_int_field', '_LESSON_CANDIDATE_WRITTEN_ALLOWLIST', '_LESSON_APPROVED_ALLOWLIST', '_LESSON_QUARANTINED_ALLOWLIST', '_LESSON_EXPIRED_ALLOWLIST', '_LESSON_INTEGRITY_FLAG_ALLOWLIST', '_LESSON_BOOT_RENDER_DROPPED_ALLOWLIST', '_LEARNING_RAIL_DISABLED_ALLOWLIST', '_FACT_GATE_ACTIVATION_CHANGED_ALLOWLIST', '_ADVISORY_DAMPENED_ALLOWLIST', '_DISTILLER_RUN_COMPLETED_ALLOWLIST', '_LESSON_EVOLVE_RUN_ALLOWLIST', '_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST', '_GIT_HOOK_BYPASS_FLAG_CLASSES', '_ENV_VAR_HIJACK_BLOCKED_ALLOWLIST', '_ENV_VAR_HIJACK_CLASSES', '_EGRESS_DESTINATION_DETECTED_ALLOWLIST', '_EGRESS_CLASSES', '_EGRESS_DEST_MAX_LEN', '_coerce_egress_destination', '_ADVERSARY_REVIEW_FLAGGED_ALLOWLIST', '_ADVERSARY_DECISIONS', '_ADVERSARY_RULE_CLASSES', '_PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST', '_PERSISTENT_INSTRUCTIONS_REASONS', '_HINT_PROVENANCE_RECORDED_ALLOWLIST', '_HINT_PROVENANCE_REASONS', '_SETTINGS_TAMPER_DETECTED_ALLOWLIST', '_CEREMONY_LINT_UNLOCK_USED_ALLOWLIST', '_SALT_ROTATION_REGISTERED_ALLOWLIST', '_SALT_ROTATION_REASONS', '_LEDGER_CHECKPOINT_RECORDED_ALLOWLIST', '_LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST', '_LEDGER_ENTRY_REJECTED_ALLOWLIST', '_SESSION_MEMORY_DELTA_OBSERVED_ALLOWLIST', '_SESSION_MEMORY_DELTA_OUTCOMES', '_SESSION_MEMORY_DELTA_ANCHOR_SOURCES', '_LEDGER_CHECKPOINT_OUTCOMES', '_LEDGER_CHECKPOINT_SKIP_REASONS', '_LEDGER_CHECKPOINT_SCOPE_SOURCES', '_LEDGER_CHECKPOINT_STATE_KINDS', '_LEDGER_GATE_SIGNAL', '_LEDGER_GATE_DECISIONS', '_LEDGER_ID_RE', '_LEDGER_GATE_REASONS', '_LEDGER_GATE_FAMILIES')

def _learning_token_field(value: Any) -> str:
    """Coerce a bounded-identifier field: shape-pass verbatim, else ''."""
    if isinstance(value, str) and _LEARNING_ID_RE.match(value):
        return value
    return ""


def _learning_sha256_field(value: Any) -> str:
    """Coerce a content_sha256 field: 64 lowercase hex or ''."""
    if isinstance(value, str) and _LESSON_SHA256_RE.match(value):
        return value
    return ""


def _learning_scope_tags_field(value: Any) -> List[str]:
    """Coerce scope_tags: <=16 bounded identifier tokens, rest dropped."""
    out: List[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str) and _LEARNING_ID_RE.match(item):
                out.append(item)
            if len(out) >= 16:
                break
    return out


def _learning_int_field(value: Any, ceiling: int = 1_000_000_000) -> int:
    """Coerce a counter field: non-negative bounded int, else 0."""
    try:
        if isinstance(value, bool):
            return int(value)
        iv = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(iv, ceiling))


_LESSON_CANDIDATE_WRITTEN_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lesson_id", "trigger", "status", "scan_outcome", "content_sha256",
    "scope_tags",
})


_LESSON_APPROVED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lesson_id", "trigger", "content_sha256", "scope_tags",
})


_LESSON_QUARANTINED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lesson_id", "reason", "prior_status",
})


_LESSON_EXPIRED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lesson_id", "age_days", "created_at_source",
})


_LESSON_INTEGRITY_FLAG_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lesson_id", "check", "consumer",
})


_LESSON_BOOT_RENDER_DROPPED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "reason", "lesson_id",
})


_LEARNING_RAIL_DISABLED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "hook", "rail", "switch",
})


_FACT_GATE_ACTIVATION_CHANGED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "hook", "enabled", "source",
})


_ADVISORY_DAMPENED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "advisory_id", "ordinal", "channel",
})


_DISTILLER_RUN_COMPLETED_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "outcome", "model_id", "fixture_mode", "events_consumed",
    "observations_rejected", "candidates_proposed", "candidates_written",
    "candidates_quarantined", "rejected_pre_candidate", "cursor_advanced",
})


_LESSON_EVOLVE_RUN_ALLOWLIST = _LEARNING_ENVELOPE | frozenset({
    "lessons_scanned", "clusters_found", "clusters_resolved",
    "proposals_written", "proposals_failed", "dry_run",
})


# PLAN-124 WS-1 — Sec MF-3 field allowlist for git_hook_bypass_blocked.
# Deny-by-default. The ONLY caller-supplied payload field is `flag_class`
# (a closed enum token, MF-G); everything else is the standard signed
# envelope that _write_event adds back (pre-allowed so the scrub does not
# strip them on a round-trip). The matched command bytes are NEVER an
# allowed field, so a malicious flag value (e.g. a smuggled Bearer token)
# can never reach the wire.
_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "flag_class",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-124 WS-1 — closed flag_class enum (MF-G). MUST mirror
# _lib/git_bypass.py GIT_BYPASS_FLAG_CLASSES. Kept as a literal frozenset here
# (NOT imported from git_bypass) so audit_emit has zero import-time dependency
# on the hook-side tokenizer; a drift between the two sets is caught by a
# dedicated test (the two frozensets MUST be equal). A value outside this set
# is COERCED to "parse_failure" before emit (defense-in-depth) so a smuggled
# raw token can never reach the signed chain.
_GIT_HOOK_BYPASS_FLAG_CLASSES = frozenset({
    "no_verify_commit", "no_verify_other_subcmd", "hookspath_inline",
    "hookspath_config_write", "git_config_env_channel", "git_dir_redirect",
    "alias_abuse", "parse_failure", "escape_hatch_used",
})


# PLAN-133 A1 — Sec field allowlist for env_var_hijack_blocked. Deny-by-default.
# The ONLY caller-supplied payload field is `hijack_class` (closed enum); the var
# NAME and the assigned VALUE are NEVER allowed fields, so a smuggled path/secret
# can never reach the wire.
_ENV_VAR_HIJACK_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "hijack_class",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-133 A1 — closed hijack_class enum. MUST mirror
# _lib/env_guard.ENV_VAR_HIJACK_CLASSES. Kept as a literal frozenset here (NOT
# imported from env_guard) so audit_emit has zero import-time dependency on the
# hook-side scanner; a drift between the two is caught by a dedicated test (the
# two frozensets MUST be equal). A value outside this set is COERCED to
# "parse_failure" before emit (defense-in-depth).
_ENV_VAR_HIJACK_CLASSES = frozenset({
    "linker_preload", "linker_path", "runtime_hook",
    "linker_other", "parse_failure",
})


# PLAN-133 A3 — Sec field allowlist for egress_destination_detected. Deny-by-
# default. The ONLY caller-supplied payload fields are `egress_class` (closed
# enum) + `destination` (BARE HOST). The full URL, path, query, and any inline
# credential are NEVER allowed fields — a smuggled `command`/`url`/`full_url`
# body is dropped before the wire.
_EGRESS_DESTINATION_DETECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "egress_class", "destination",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-133 A3 — closed egress_class enum. MUST mirror
# _lib/egress_taxonomy.EGRESS_CLASSES. Kept as a literal frozenset here (NOT
# imported from egress_taxonomy) so audit_emit has zero import-time dependency on
# the hook-side classifier; a drift between the two is caught by a dedicated test
# (the two frozensets MUST be equal). A value outside this set is COERCED to
# "unknown" before emit (defense-in-depth).
_EGRESS_CLASSES = frozenset({
    "network_http", "ssh_remote", "cloud_store", "container_push",
    "package_publish", "raw_socket", "pair_rail", "unknown",
})


# PLAN-133 A3 — defensive host-only re-truncation of a persisted destination.
# Drops scheme/userinfo/port/path/query so even a direct emit_generic caller that
# passes a full URL in `destination` cannot leak a path/query/credential.
_EGRESS_DEST_MAX_LEN = 253


def _coerce_egress_destination(dest: Any) -> str:
    """Reduce a destination to a bare host string (no scheme/path/query/cred).

    Mirrors egress_taxonomy._host_only's contract but is self-contained (no import
    dependency). Non-str -> "". Pure; never raises.
    """
    if not isinstance(dest, str) or not dest:
        return ""
    s = dest.strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    for sep in ("/", "?", "#"):
        idx = s.find(sep)
        if idx != -1:
            s = s[:idx]
    if "@" in s:
        s = s.rsplit("@", 1)[1]
    if s.startswith("["):
        end = s.find("]")
        if end != -1:
            s = s[: end + 1]
    elif ":" in s:
        s = s.split(":", 1)[0]
    return s[:_EGRESS_DEST_MAX_LEN]


# PLAN-133 E1 — Sec field allowlist for adversary_review_flagged. Deny-by-default.
# Caller-supplied: `decision` (closed enum), `rule_class` (closed enum), `rule_id`
# (author-controlled config token — carries no command bytes). The matched command
# text / matched substring / rule `match`|`regex` source are NEVER allowed fields.
_ADVERSARY_REVIEW_FLAGGED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "decision", "rule_class", "rule_id",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-133 E1 — closed enums. MUST mirror _lib/adversary_rules.ADVERSARY_DECISIONS
# and .RULE_CLASSES. Kept literal here (NOT imported from adversary_rules) so
# audit_emit has zero import-time dependency on the hook-side engine; a drift
# between the two is caught by a dedicated test (the frozensets MUST be equal).
# A value outside the set is COERCED to "advisory"/"other" before emit.
_ADVERSARY_DECISIONS = frozenset({"deny", "ask", "advisory", "allow"})


_ADVERSARY_RULE_CLASSES = frozenset(
    {"destructive", "exfiltration", "privilege", "tampering", "other"}
)


# PLAN-133 G1 — Sec field allowlist for persistent_instructions_blocked.
# Deny-by-default. Caller-supplied: `reason` (closed enum) + `family_hits` /
# `bytes_scanned` (integers). The instruction-file body / matched line / resolved
# path / any env value are NEVER allowed fields (no-value-echo).
_PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "family_hits", "bytes_scanned",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-133 G1 — closed enum. MUST mirror
# _lib/guardrail_validator.VERDICT_REASONS. Kept literal here (NOT imported) so
# audit_emit has zero import-time dependency on the hook-side engine; a drift is
# caught by the parity test (§9). A value outside the set is COERCED to "other".
_PERSISTENT_INSTRUCTIONS_REASONS = frozenset(
    {"ok", "injection_pattern", "oversize", "outside_project_dir", "other"}
)


# PLAN-133 G3 — Sec field allowlist for hint_provenance_recorded.
# Deny-by-default. Caller-supplied: `reason` (closed enum) + `rel_dir_depth` /
# `family_hits` / `bytes_scanned` (integers). The hint-file body / matched line /
# the path text (absolute OR relative) are NEVER allowed fields (no-value-echo;
# only the integer DEPTH below the repo root is persisted).
_HINT_PROVENANCE_RECORDED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "rel_dir_depth", "family_hits", "bytes_scanned",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-133 G3 — closed enum. MUST mirror
# _lib/guardrail_validator.HINT_PROVENANCE_REASONS. Kept literal here (NOT
# imported) so audit_emit has zero import-time dependency on the hook-side
# engine; a drift is caught by the parity test (§9). A value outside the set is
# COERCED to "other".
_HINT_PROVENANCE_REASONS = frozenset(
    {"loaded", "blocked_injection", "blocked_oversize", "read_error", "other"}
)


# PLAN-135 W1 S3 — Sec field allowlist for settings_tamper_detected.
# Deny-by-default. Caller-supplied: `tamper_class` (closed enum), `layer`
# (closed enum) + `finding_count` (int, clamped 0..99 caller-side and
# re-clamped here). The tamper finding DETAIL string is NEVER an allowed
# field — it can carry an attacker endpoint URL, an off-allowlist model id,
# an apiKeyHelper path or a dangerously-flag value
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
# ANTHROPIC_AUTH_TOKEN values never reach even the producer (redacted at
# the effective_config classification layer); this allowlist is the second
# fence.
_SETTINGS_TAMPER_DETECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tamper_class", "layer", "finding_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-174 W1 (SENT-S318 pack) — ceremony-lint ADR-186 unlock breadcrumb.
# Metadata-only: `file_sha256` is a 16-hex sha256 PREFIX of the unlocked
# ceremony script, `reason_len` the LENGTH of the operator's mandatory
# CEO_CEREMONY_LINT_UNLOCK_REASON. DENIED on the wire by construction:
# the reason TEXT, the script path, the script body.
_CEREMONY_LINT_UNLOCK_USED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "file_sha256", "reason_len",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-182 W1 (ADR-079 S318 amendment §2) — Sec MF-3 field allowlist for
# salt_rotation_registered. Deny-by-default; raw slug and salt-file path
# are excluded (16-hex sha256 prefix only, mirroring file_sha256). The base
# `project` field is allowed and carries the absolute repository path.
_SALT_ROTATION_REGISTERED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "salt_scope", "slug_sha256",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# Closed enum for salt_rotation_registered.reason (S172 doctrine: values
# outside the set are COERCED to "other", never echoed).
_SALT_ROTATION_REASONS = frozenset({"first_mint", "migration_mint", "other"})


# PLAN-179 W2 (ADR-195) — Sec MF-3 field allowlists for the work-boundary
# ledger rail. Deny-by-default, same no-value-echo contract as the compaction
# pair: the commit MESSAGE, the committed PATHS, the ledger BODY and the repo
# ROOT are never allowed field NAMES, so a smuggled value cannot reach the
# wire even from a direct emit_generic caller.
_LEDGER_CHECKPOINT_RECORDED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "outcome", "plan_id", "scope_source",
    "in_scope_path_count", "ledger_size_bucket_kib", "over_ceiling",
    "unverified_ac_claim_count", "commits_since_last_observation",
    "state_kind", "would_block",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


_LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "plan_id", "commits_since_last_observation",
    "state_kind", "would_block",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


_LEDGER_ENTRY_REJECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "signal", "decision", "reason", "family",
    "hits_count", "bytes_scanned", "scanned", "enforced",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-179 W2 US8 (wave-179-close) — SessionEnd memory-delta observation.
# Field allowlist (deny-by-default) + closed value sets. The sets MUST
# mirror the producer's own literals in `.claude/hooks/SessionEnd.py`
# (`_MEMORY_DELTA_OUTCOMES`); kept LITERAL here (never imported) for the
# same zero-import-time-dependency posture as `_LEDGER_CHECKPOINT_OUTCOMES`
# below; drift is caught by the enum-parity test in
# `.claude/hooks/tests/test_session_end_memory_delta.py`.
_SESSION_MEMORY_DELTA_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "outcome", "files_count", "modified_count", "index_modified",
    "anchor_source",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


#: Closed outcome enum for `session_memory_delta_observed`. Off-enum values
#: are COERCED to "other" — NEVER to "written": an unparseable observation
#: must never be laundered into a healthy-class value (SESSIONEND-NOTE.md
#: §4, the same S172 never-echo doctrine as every sibling).
_SESSION_MEMORY_DELTA_OUTCOMES = frozenset({
    "written", "absent", "index_only", "start_unknown",
    "dir_missing", "not_writable", "error", "other",
})


#: Which resolution step of the session-start anchor answered
#: (SESSIONEND-NOTE.md §2): the HMAC chain, the tool-lifecycle per-session
#: state file, or none (terminal "I do not know" — never a guess).
_SESSION_MEMORY_DELTA_ANCHOR_SOURCES = frozenset({
    "chain", "state_file", "none",
})


# PLAN-179 W2 (ADR-195) — closed enums for the two checkpoint actions. These
# MUST mirror the producer's own tuples in
# `.claude/hooks/check_ledger_checkpoint.py` (`_OUTCOMES`, `_SKIP_REASONS`,
# `_SCOPE_SOURCES`, `_STATE_KINDS`). Kept LITERAL here (never imported) so
# audit_emit keeps its zero-import-time-dependency posture — the same
# treatment `_SETTINGS_TAMPER_CLASSES` gets; the drift is caught by the
# staged parity test in `.claude/hooks/tests/test_check_ledger_checkpoint.py`
# (§enum-parity), which is what that test is for. Values outside a set are
# COERCED to the safe sentinel (S172 doctrine — never echoed).
_LEDGER_CHECKPOINT_OUTCOMES = frozenset({
    "ledger_updated", "ledger_missing", "ledger_absent_from_plan",
    "error", "other",
})


_LEDGER_CHECKPOINT_SKIP_REASONS = frozenset({
    "out_of_scope_paths", "kill_switch", "hotfix", "exploratory",
    "operator_opt_out", "unparseable", "budget_exhausted", "no_repo",
    "other",
})


_LEDGER_CHECKPOINT_SCOPE_SOURCES = frozenset({
    "plan_dir", "plan_ac", "both", "other",
})


_LEDGER_CHECKPOINT_STATE_KINDS = frozenset({"fresh", "resumed", "unavailable"})


# PLAN-179 W4 (ADR-195) — closed enums for the ledger write-gate discard.
# `_LEDGER_GATE_SIGNAL` is a fixed vocabulary of ONE: this action has exactly
# one producer, so a different signal names a caller that is not the gate and
# is coerced rather than echoed.
_LEDGER_GATE_SIGNAL = "ledger_write_gate"


_LEDGER_GATE_DECISIONS = frozenset({"accept", "reject"})


#: Forma admissivel para os campos de IDENTIDADE das acoes de ledger. Sem
#: barra, sem espaco, limitado: um path NUNCA casa, que e o ponto.
_LEDGER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{0,64}$")


_LEDGER_GATE_REASONS = frozenset({
    "ok", "not_scanned_trusted_provenance", "scanner_hit",
    "scanner_unavailable", "oversize", "malformed_input",
})


# The family vocabulary is the UNION of two authorities, mirrored LITERALLY
# for the same zero-import reason as the enums above:
#   * `_lib/ledger_provenance._LOCAL_FAMILIES` — the families the gate names
#     itself, without consulting a scanner;
#   * `_lib/injection_patterns.family_names()` — the pattern CATALOGUE.
# A catalogue that GROWS without this mirror growing would silently narrow a
# legitimate family to `unknown_family`; the parity test in
# `.claude/hooks/tests/test_ledger_provenance.py` (§family-enum-parity) is
# the guard that turns that drift RED instead of silent.
_LEDGER_GATE_FAMILIES = frozenset({
    # local (ledger_provenance._LOCAL_FAMILIES)
    "none", "scanner_unavailable", "oversize", "malformed_input",
    "unknown_family",
    # catalogue (injection_patterns.family_names())
    "directive_prose", "harness_mimicry", "provider_tokens", "role_preamble",
})
