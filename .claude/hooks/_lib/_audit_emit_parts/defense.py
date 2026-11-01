"""Defense.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_learning_rail_disabled', 'emit_git_hook_bypass_blocked', 'emit_bash_input_rewritten', 'emit_subagent_lifecycle_observed', 'emit_env_var_hijack_blocked', 'emit_egress_destination_detected', 'emit_adversary_review_flagged', 'emit_persistent_instructions_blocked', 'emit_hint_provenance_recorded', 'emit_ceo_boot_persona_coverage_score', 'emit_ceo_boot_check_skipped')

def emit_learning_rail_disabled(
    *,
    rail: str,
    switch: str,
    hook: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit learning_rail_disabled (PLAN-154 A12 / ADR-160 Decision 8).

    Once-per-session "disabled-this-session" breadcrumb shared by the four
    learning-loop rails (observe / distill / boot_render / fact_gate) —
    emitted ONLY on an EXPLICIT operator disable (switch set to a non-enable
    value, or CEO_SOTA_DISABLE master kill over an opted-in rail), NEVER on
    merely-unset (which is structurally off with zero delta). Wired to the
    ADR-158 fail-open-rail liveness surface so "off by recorded operator
    choice" is distinguishable from a dead rail.

    Both closed enums are re-validated here (defense-in-depth): an
    unrecognized ``rail`` is coerced to ``"observe"`` and an unrecognized
    ``switch`` to ``"other"``. ``hook`` (optional producer tag) is bounded
    to the identifier charset. Fail-open per audit_emit contract.
    """
    safe_rail = rail if rail in _LEARNING_RAIL_ENUM else "observe"
    safe_switch = switch if switch in _LEARNING_SWITCH_ENUM else "other"
    raw_event: Dict[str, Any] = {
        "action": "learning_rail_disabled",
        "session_id": session_id,
        "project": project,
        "rail": safe_rail,
        "switch": safe_switch,
    }
    if hook:
        raw_event["hook"] = _learning_token_field(hook)
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _LEARNING_RAIL_DISABLED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"learning_rail_disabled dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_git_hook_bypass_blocked(
    *,
    flag_class: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit git_hook_bypass_blocked (PLAN-124 WS-1 / ECC value-harvest).

    Fired by `check_bash_safety.py` when the git hook-bypass tokenizer
    (`_lib/git_bypass.py`) blocks a `--no-verify` / `core.hooksPath` /
    env-channel / alias / redirect bypass, AND when the audited dual-auth
    escape hatch (CEO_GIT_BYPASS_ALLOW) is used to ALLOW one
    (flag_class=`escape_hatch_used`).

    Deny-by-default field allowlist enforced (MF-G): the ONLY caller-supplied
    field is `flag_class`, a CLOSED enum token. The matched command bytes are
    NEVER persisted (a flag value like `-c http.extraHeader="Bearer <secret>"`
    is a secret). An unrecognized `flag_class` is COERCED to `"parse_failure"`
    here (defense-in-depth) so a smuggled raw value can never reach the wire,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_flag_class = (
        flag_class
        if flag_class in _GIT_HOOK_BYPASS_FLAG_CLASSES
        else "parse_failure"
    )
    raw_event: Dict[str, Any] = {
        "action": "git_hook_bypass_blocked",
        "session_id": session_id,
        "project": project,
        "flag_class": safe_flag_class,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"git_hook_bypass_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_bash_input_rewritten(
    *,
    rewrite_class: str,
    before_sha256: str,
    after_sha256: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit bash_input_rewritten (PLAN-135 W2 H5 / ADR-154 single-rewriter).

    Fired by `check_bash_safety.py` when the PreToolUse Bash rail REWRITES a
    `git push --force`/`-f` command to `--force-with-lease` via the
    `updatedInput` channel (surfaced to the user as an `ask`, never a silent
    allow). Records the before/after sha256 hash PAIR so an auditor can prove
    the audited command equals the executed command (ADR-154 §2).

    Deny-by-default field allowlist enforced: the ONLY caller-supplied fields
    are `rewrite_class` (a CLOSED enum token, coerced to "other" here as
    defense-in-depth) + the two 64-hex sha256 hashes (validated, else "").
    The command BYTES (before OR after) are NEVER persisted — a force-push
    line can carry a remote URL with an inline token. NEVER routes through
    _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event.
    """
    safe_class = (
        rewrite_class if rewrite_class in _BASH_REWRITE_CLASSES else "other"
    )
    safe_before = before_sha256 if _is_sha256_hex(before_sha256) else ""
    safe_after = after_sha256 if _is_sha256_hex(after_sha256) else ""
    raw_event: Dict[str, Any] = {
        "action": "bash_input_rewritten",
        "session_id": session_id,
        "project": project,
        "rewrite_class": safe_class,
        "before_sha256": safe_before,
        "after_sha256": safe_after,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _BASH_INPUT_REWRITTEN_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"bash_input_rewritten dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_subagent_lifecycle_observed(
    *,
    agent_archetype: str,
    wall_bucket: str,
    wall_source: str,
    token_bucket: str,
    claim_bucket: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit subagent_lifecycle_observed (PLAN-135 W2 H3 / per-agent bracket).

    Fired ONCE per returning sub-agent by `check_fluency_nudge.py` (the
    SubagentStop H3 extension) after it consumes the SubagentStart sidecar
    written by `check_subagent_start.py` + the harness-supplied
    `agent_transcript_path`. Turns the S227 `modelUsage` forensic
    reconstruction into a live hook emit and feeds the persona-ledger
    (PLAN-104) via `agent_archetype`, alongside `agent_spawn`.

    Deny-by-default field allowlist enforced (Sec MF-3): EVERY caller-supplied
    field is a CLOSED enum or coarse BUCKET, each coerced here as
    defense-in-depth. The RAW wall-time seconds, the RAW token counts, the
    transcript path/body, the raw agent_id and the confidence-marker snippets
    are NEVER persisted — only the closed-enum archetype + the four brackets
    travel (the bracket is the audit signal; the raw counts stay forensic-
    private). NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event.
    """
    safe_archetype = (
        agent_archetype
        if agent_archetype in _SUBAGENT_LIFECYCLE_ARCHETYPES
        else "other"
    )
    safe_wall_source = (
        wall_source
        if wall_source in _SUBAGENT_LIFECYCLE_WALL_SOURCES
        else "unknown"
    )
    safe_wall_bucket = (
        wall_bucket if wall_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    safe_token_bucket = (
        token_bucket if token_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    safe_claim_bucket = (
        claim_bucket if claim_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    raw_event: Dict[str, Any] = {
        "action": "subagent_lifecycle_observed",
        "session_id": session_id,
        "project": project,
        "agent_archetype": safe_archetype,
        "wall_bucket": safe_wall_bucket,
        "wall_source": safe_wall_source,
        "token_bucket": safe_token_bucket,
        "claim_bucket": safe_claim_bucket,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"subagent_lifecycle_observed dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_env_var_hijack_blocked(
    *,
    hijack_class: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit env_var_hijack_blocked (PLAN-133 A1 / Goose-harvest).

    Fired by `check_bash_safety.py` when `_lib/env_guard.scan_command` detects a
    Bash command that SETS a denylisted linker/loader/runtime-hijack environment
    variable (LD_PRELOAD / DYLD_INSERT_LIBRARIES / PYTHONSTARTUP / NODE_OPTIONS /
    BASH_ENV / …). Emitted on BOTH an enforced block (CEO_ENV_GUARD_ENFORCE=1) AND
    an advisory default-OFF detection.

    Deny-by-default field allowlist enforced: the ONLY caller-supplied field is
    `hijack_class`, a CLOSED enum token. The variable NAME and the assigned VALUE
    are NEVER persisted (the value is a preload-payload path or a smuggled secret).
    An unrecognized `hijack_class` is COERCED to `"parse_failure"` here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_class = (
        hijack_class
        if hijack_class in _ENV_VAR_HIJACK_CLASSES
        else "parse_failure"
    )
    raw_event: Dict[str, Any] = {
        "action": "env_var_hijack_blocked",
        "session_id": session_id,
        "project": project,
        "hijack_class": safe_class,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"env_var_hijack_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_egress_destination_detected(
    *,
    egress_class: str,
    destination: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit egress_destination_detected (PLAN-133 A3 / Goose-harvest).

    Fired by `check_bash_safety.py` when `_lib/egress_taxonomy.classify_command`
    detects an outbound channel in a Bash command (curl/wget/scp/rsync/ssh/aws-s3/
    gsutil/docker-push/npm-publish/nc/socat/codex). ADVISORY — emitted (default-OFF
    behind CEO_EGRESS_TAXONOMY_EMIT) regardless of whether the command is also
    blocked by a higher-severity rule, so a destructive+egress compound still
    records the egress.

    Deny-by-default field allowlist enforced: the ONLY caller-supplied fields are
    `egress_class` (a CLOSED enum) + `destination` (a BARE HOST). The full URL,
    path, query, and any inline credential are NEVER persisted. An unrecognized
    `egress_class` is COERCED to "unknown" and `destination` is re-reduced to a
    bare host here (defense-in-depth) so even a direct caller cannot leak.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_class = (
        egress_class if egress_class in _EGRESS_CLASSES else "unknown"
    )
    raw_event: Dict[str, Any] = {
        "action": "egress_destination_detected",
        "session_id": session_id,
        "project": project,
        "egress_class": safe_class,
        "destination": _coerce_egress_destination(destination),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _EGRESS_DESTINATION_DETECTED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"egress_destination_detected dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_adversary_review_flagged(
    *,
    decision: str,
    rule_class: str,
    rule_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit adversary_review_flagged (PLAN-133 E1 / Goose-harvest).

    Fired by `check_adversary.py` when the local-rules engine
    (`_lib/adversary_rules.py`) flags a Bash command — on BOTH an enforced
    deny/ask (CEO_ADVERSARY=1) AND an advisory default-OFF detection — and on the
    secret-in-command fail-CLOSED path (E1 §4).

    Deny-by-default field allowlist enforced: caller-supplied fields are `decision`
    + `rule_class` (CLOSED enums) and `rule_id` (author-controlled config token).
    The matched COMMAND bytes, the matched substring, and the rule `match`/`regex`
    source are NEVER persisted (a command can carry a smuggled credential). An
    unrecognized `decision`/`rule_class` is COERCED to "advisory"/"other" here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_decision = decision if decision in _ADVERSARY_DECISIONS else "advisory"
    safe_class = rule_class if rule_class in _ADVERSARY_RULE_CLASSES else "other"
    raw_event: Dict[str, Any] = {
        "action": "adversary_review_flagged",
        "session_id": session_id,
        "project": project,
        "decision": safe_decision,
        "rule_class": safe_class,
        "rule_id": rule_id,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"adversary_review_flagged dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_persistent_instructions_blocked(
    *,
    reason: str,
    family_hits: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persistent_instructions_blocked (PLAN-133 G1 / Goose-harvest MOIM).

    Fired by `SessionStart.py` when the BLOCKING MOIM validator
    (`_lib/guardrail_validator.py`) returns ``decision="block"`` for the
    trusted-instructions file (injection pattern or oversize) and the session
    boot is refused.

    Deny-by-default field allowlist enforced: caller-supplied fields are
    `reason` (CLOSED enum) + `family_hits` / `bytes_scanned` (integers). The
    instruction-file BODY, the matched line, the matched substring, the resolved
    path, and any env value are NEVER persisted (the file is the exact injection
    vector PLAN-133 §2 flags). An unrecognized `reason` is COERCED to "other"
    here (defense-in-depth) so a smuggled raw value can never reach the signed
    chain, even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_reason = reason if reason in _PERSISTENT_INSTRUCTIONS_REASONS else "other"
    raw_event: Dict[str, Any] = {
        "action": "persistent_instructions_blocked",
        "session_id": session_id,
        "project": project,
        "reason": safe_reason,
        "family_hits": int(family_hits) if isinstance(family_hits, int) else 0,
        "bytes_scanned": int(bytes_scanned) if isinstance(bytes_scanned, int) else 0,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"persistent_instructions_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_hint_provenance_recorded(
    *,
    reason: str,
    rel_dir_depth: int = 0,
    family_hits: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit hint_provenance_recorded (PLAN-133 G3 / Goose-harvest nested hints).

    Fired by `SessionStart.py` for each nested `.claude/hints.md` the BLOCKING
    validator (`_lib/guardrail_validator.py`) rejected (injection pattern or
    oversize) during the hierarchical discovery walk.

    Deny-by-default field allowlist enforced: caller-supplied fields are
    `reason` (CLOSED enum) + `rel_dir_depth` / `family_hits` / `bytes_scanned`
    (integers). The hint-file BODY, the matched line, the matched substring, and
    the PATH text (absolute OR relative dir name) are NEVER persisted — only the
    integer DEPTH below the repo root (so a poisoned dir NAME cannot itself be an
    exfil channel). An unrecognized `reason` is COERCED to "other" here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_reason = reason if reason in _HINT_PROVENANCE_REASONS else "other"
    raw_event: Dict[str, Any] = {
        "action": "hint_provenance_recorded",
        "session_id": session_id,
        "project": project,
        "reason": safe_reason,
        "rel_dir_depth": int(rel_dir_depth) if isinstance(rel_dir_depth, int) else 0,
        "family_hits": int(family_hits) if isinstance(family_hits, int) else 0,
        "bytes_scanned": int(bytes_scanned) if isinstance(bytes_scanned, int) else 0,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _HINT_PROVENANCE_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"hint_provenance_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_ceo_boot_persona_coverage_score(
    *,
    score_x100: int = 0,
    cells_covered: int = 0,
    total_cells: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """PLAN-093 Wave C.5 — emit 4×4 persona × task coverage score from /ceo-boot.

    Field allowlist (Sec MF-3): score_x100, cells_covered, total_cells,
    session_id, project. Scrub enforced both here AND in emit_generic
    dispatch branch (Codex S123 P1-2 closure).

    score_x100 is integer basis-points (7234 = 72.34%; 0-10000 range) —
    floats break canonical JSON HMAC chain (Codex S123 iter-2 P1).
    Fail-open per audit_emit contract — exceptions swallowed by _write_event.
    """
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_persona_coverage_score",
        "session_id": session_id,
        "project": project,
        "score_x100": int(score_x100),
        "cells_covered": int(cells_covered),
        "total_cells": int(total_cells),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover
        _breadcrumb(
            f"ceo_boot_persona_coverage_score dropped: {sorted(dropped)[:10]}"
        )


def emit_ceo_boot_check_skipped(
    *,
    session_id: str,
    check_name: str,
    timeout_ms: int,
    project: str = "",
) -> None:
    """Emit ceo_boot_check_skipped (PLAN-065 Phase 2 / ADR-098 / CR-MF6).

    Fired per timed-out Tier-S check inside the dispatcher. Required by
    Codex audit-v3 finding A precedent (silently dropped events block
    forensic reconstruction).

    Field allowlist enforced (Sec MF-3): no detail / no error message /
    no stack trace — only the check name + the timeout budget that was
    breached. Operator queries audit-log + correlates with ceo_boot_emitted
    `checks_failed` count for forensic reconstruction.

    `check_name` is length-bounded to 64 chars (defense-in-depth on caller
    drift; PLAN-065 registry pins 15 Tier-S + 10 Tier-A all <32 chars).
    """
    safe_name = (check_name or "")[:64]
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_check_skipped",
        "session_id": session_id,
        "project": project,
        "check_name": safe_name,
        "timeout_ms": int(timeout_ms),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CEO_BOOT_CHECK_SKIPPED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"ceo_boot_check_skipped dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )
