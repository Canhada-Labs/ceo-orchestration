"""Compaction.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_ledger_int_field', '_SETTINGS_TAMPER_CLASSES', '_SETTINGS_TAMPER_LAYERS', '_CONFIG_CHANGE_OBSERVED_ALLOWLIST', '_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST', '_CONFIG_CHANGE_LAYERS', '_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST', '_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST', '_CONTEXT_PRESSURE_OBSERVED_ALLOWLIST', '_COMPACTION_TRIGGERS', '_COMPACTION_SNAPSHOT_OUTCOMES', '_compaction_plan_id_ok', '_CONTEXT_PRESSURE_USED_BUCKETS_PCT', '_CONTEXT_PRESSURE_EVENT_SOURCES', '_CONTEXT_PRESSURE_STATE_BASENAME', '_GC_MARKER_WALL_BUDGET_S', '_CONTEXT_PRESSURE_SID_SAFE_CHARS', '_CONTEXT_PRESSURE_SID_MAX_LEN', '_CONTEXT_PRESSURE_MARKER_TTL_S', '_CONTEXT_PRESSURE_MARKER_GC_MAX')

def _ledger_int_field(value: Any, hi: int) -> int:
    """TYPE-strict clamp for the ledger rail's integer wire fields.

    Deliberately NOT ``int(value)``: ``bool`` is an ``int`` subclass (so
    ``True`` would sail through any numeric test) and ``canonical_json``
    REFUSES floats in HMAC-covered fields — a float here would drop the
    WHOLE event to an ``audit-log.errors`` breadcrumb rather than the one
    field (S181 / ADR-055-AMEND-2). Anything that is not a plain
    non-negative ``int`` therefore becomes ``0``, and values above ``hi``
    are clamped. Never echoes the rejected value.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    if value < 0:
        return 0
    return value if value <= hi else hi


# PLAN-135 W1 S3 — closed enums. MUST mirror
# _lib/effective_config.TAMPER_CLASSES and the layer names
# (LAYER_MERGE_ORDER + LAYER_ENV + LAYER_DISK). Kept literal here (NOT
# imported) so audit_emit has zero import-time dependency on the resolver;
# a drift is caught by the staged parity test
# (test_ceo_boot_tamper_tripwires.py §enum-parity). Values outside the
# sets are COERCED to the safe sentinel "other" (S172 doctrine — the
# rejected value is never echoed).
_SETTINGS_TAMPER_CLASSES = frozenset({
    "settings_tamper_disable_all_hooks",
    "settings_tamper_model_remap",
    "settings_tamper_endpoint_remap",
    "settings_tamper_permission_bypass",
    "settings_tamper_hook_count_mismatch",
    # PLAN-135-FOLLOWUP (Codex R5 P1-3) — settings-layer CEO_STATUSLINE_SIDECAR
    # write-path steer (output/exfil-path class, NOT endpoint_remap). MUST mirror
    # _lib/effective_config.TAMPER_CLASSES (enum-parity test). A settings.json env
    # block steering the always-on statusline sidecar writer out of the state dir.
    "settings_tamper_sidecar_redirect",
    # PLAN-155 Wave 3b (SENT-CX-E) — Codex kill-switch surface census tamper:
    # a deregistered `.codex` registration (only ceo.rules left) or a referenced
    # codex hook missing on disk. Added to _lib/effective_config.TAMPER_CLASSES
    # in the same wave; MUST mirror here (enum-parity test).
    "settings_tamper_codex_killswitch_missing",
    "other",
})


_SETTINGS_TAMPER_LAYERS = frozenset({
    "user", "project", "local", "managed", "env", "disk", "other",
})


# PLAN-135 W2 H2 — Sec field allowlists for the ConfigChange-guard pair
# (config_change_observed / config_change_forbidden_key, producer
# .claude/hooks/check_config_change.py). Deny-by-default. Same no-value-echo
# contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# changed file's path text and body, the forbidden key's VALUE (endpoint
# URL / model id / apiKeyHelper path / dangerously-flag value) and the
# effective_config finding DETAIL string are NEVER allowed fields.
_CONFIG_CHANGE_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "layer",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tamper_class", "layer", "finding_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-135 W2 H2 — closed layer enum for the ConfigChange pair. SUBSET of
# _SETTINGS_TAMPER_LAYERS minus {env, disk}: H2 polices the SETTINGS file
# surfaces only (a ConfigChange event is a file change); process-env tamper
# is S3's surface and the disk hook-census is state, not a key change —
# census findings are deliberately observe-only in check_config_change.py
# (never blocked on). `tamper_class` reuses _SETTINGS_TAMPER_CLASSES (same
# effective_config closed enum, same coercion sentinel).
_CONFIG_CHANGE_LAYERS = frozenset({
    "user", "project", "local", "managed", "other",
})


# PLAN-135 W2 H1 (ADR-153) — Sec field allowlists for the
# compaction-continuity pair (compaction_continuity_snapshot /
# compaction_context_reinjected, producers
# .claude/hooks/check_precompact_continuity.py /
# check_postcompact_reinject.py). Deny-by-default. Same no-value-echo
# contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# snapshot BODY (plan path text, checkbox position, ceremony flags,
# last-hmac hex prefix) and the reinjected additionalContext TEXT are
# NEVER allowed fields — the snapshot lives in the plan-scoped scratchpad,
# the audit wire carries closed enums + counters only.
_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "trigger", "plan_id", "chain_length", "snapshot_outcome",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "plan_id", "snapshot_found", "snapshot_age_s", "pointer_count",
    # PLAN-179 W1-b [amendment r1-C3]: constraints ride a budget SEPARATE from
    # the pointers, so they need a counter of their own. `pointer_count` keeps
    # meaning "pointers only" — re-scoping it would silently redefine a series
    # already on the wire. Without this entry the deny-by-default scrub drops
    # the field and the counter is a dead instrument (caught RED by the W1
    # integration test before signature, which is what that test is for).
    "constraint_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-179 W0 US2 (amendment 8.1) — Sec field allowlist for the
# edge-triggered context-pressure breadcrumb (context_pressure_observed;
# producers = the PreCompact observer, the SessionStart(matcher=compact)
# PRIMARY channel and the UserPromptSubmit sampler). Deny-by-default, same
# no-value-echo contract as the compaction pair above: the transcript TEXT,
# the raw token/byte counts and the plan PATH are NEVER allowed fields —
# the wire carries one closed integer percent bucket, one closed-enum
# source and the strict PLAN-NNN id, nothing else.
_CONTEXT_PRESSURE_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "used_bucket", "event_source", "plan_id",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-135 W2 H1 — closed enums for the compaction pair. `trigger` mirrors
# the documented PreCompact hook-input values (manual = /compact, auto =
# context-window threshold); anything else (incl. a missing field on a
# future harness change) is COERCED to "other" (S172 doctrine — the
# rejected value is never echoed). `snapshot_outcome` is the producer's
# own closed result enum.
_COMPACTION_TRIGGERS = frozenset({"manual", "auto", "other"})


_COMPACTION_SNAPSHOT_OUTCOMES = frozenset({
    "written", "scratchpad_unavailable", "error", "other",
    # PLAN-179 W1 US3 — the snapshot WAS written, but to the SESSION-scoped
    # fallback location because resolve_plan_id() could not name a plan.
    # That is the S309 fires-proof DOMINANT path, not an edge: a
    # `plan_transition` is emitted only on a status CHANGE, so a long
    # session normally carries none of its own. Kept distinct from
    # "written" so a ledger can separate plan-scoped continuity from
    # session-scoped continuity instead of conflating the two. The enum
    # stays CLOSED — anything else still coerces to "other".
    "written_session_scope",
})


def _compaction_plan_id_ok(value: Any) -> bool:
    """Strict PLAN-NNN shape check for compaction-pair plan_id fields.

    PLAN-SCHEMA §1 naming: exactly ``PLAN-`` + 3 digits (zero-padded,
    8 chars total). Anything else — including path-traversal attempts
    smuggled through a spoofed plan_transition audit event — is rejected
    and the caller coerces to the safe sentinel ``"unknown"``. Kept as a
    plain string check (no regex) to preserve audit_emit's import
    surface.
    """
    if not isinstance(value, str) or len(value) != 8:
        return False
    return value.startswith("PLAN-") and value[5:].isdigit()


# PLAN-179 W0 US2 (amendment 8.1) — closed enums for the context-pressure
# breadcrumb. `used_bucket` is an INTEGER PERCENT bucket: the value is the
# share of the context window already consumed, floored onto one of five
# coarse rungs. The unit lives in the field NAME (and in this comment)
# because the field is HMAC-covered and canonical_json REFUSES floats — a
# float here would drop the WHOLE event, not merely the field (S181 /
# ADR-055-AMEND-2). The rungs are deliberately coarse: an exact percentage
# is a side channel on session size, a rung is a governance signal.
_CONTEXT_PRESSURE_USED_BUCKETS_PCT = frozenset({40, 60, 80, 90, 95})


# `event_source` names WHICH observer noticed the pressure. PLAN-179 W0-1
# leaves the PostCompact `additionalContext` channel UNPROVEN, so the
# primary channel is SessionStart(matcher=compact); `userpromptsubmit` is
# the per-turn sampler and `precompact` the pre-compaction observer.
# Anything else (incl. a missing field) is COERCED to "other" (S172
# doctrine — the rejected value is never echoed).
_CONTEXT_PRESSURE_EVENT_SOURCES = frozenset({
    "precompact", "sessionstart_compact", "userpromptsubmit", "other",
})


# PLAN-179 W0 US2 (amendment 8.1) — basename of the edge-trigger marker.
# Lives under `.claude/state/`, which .gitignore declares NON-COMMIT as a
# whole (runtime state, never framework source).
#
# PLAN-179 rail finding A (round-1 REJECT): this basename is now the
# PROJECT-WIDE marker — the honest DEGRADED mode, used only when the caller
# has no trusted session id. A call that carries one keys its own marker
# `<basename>.<session-id>` (see _context_pressure_marker_name), because a
# single project-wide file makes two concurrent sessions in the same repo
# corrupt each other's hysteresis: one session sitting at rung 80 SUPPRESSES
# the other's first 80 event, and sessions at different rungs re-arm each
# other on every call. The resulting wire rows cannot be attributed back to a
# session, so the true transitions are unrecoverable — which would defeat the
# measurement PLAN-179 exists to make.
_CONTEXT_PRESSURE_STATE_BASENAME = "context-pressure-last-bucket"


# PLAN-179 rail round-4 [P2]: sweep bounded by TIME, never by a slice of the
# directory — a slice starves whatever sits behind it. Small fraction of the
# hook timeout; the sweep is fail-open, so overrunning costs only a later reclaim.
_GC_MARKER_WALL_BUDGET_S = 0.25


# PLAN-179 rail finding A — the session id reaches the FILESYSTEM as a name
# component, so it is sanitized here rather than trusted. Only these ASCII
# characters pass through verbatim (str.isalnum() is deliberately NOT used: it
# is True for unicode letters/digits, which have no business in a marker
# name). Anything else — a separator, a dot, a control char, an over-long id
# — falls back to a sha256 prefix of the RAW id: still one distinct marker per
# distinct session (no collisions, so no cross-session suppression), just not
# a human-readable one.
_CONTEXT_PRESSURE_SID_SAFE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)


_CONTEXT_PRESSURE_SID_MAX_LEN = 64


# PLAN-179 rail finding A — reclaim for the per-session markers (see
# _gc_context_pressure_markers). Hygiene values, not decision-bearing: a
# marker untouched for 7 days belongs to a session that is long gone, and the
# sweep unlinks at most 32 files per run so a large backlog drains over
# several runs instead of stalling one hook invocation.
_CONTEXT_PRESSURE_MARKER_TTL_S = 7 * 24 * 3600


_CONTEXT_PRESSURE_MARKER_GC_MAX = 32
