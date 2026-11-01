"""Harness.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_tool_call_lifecycle_recorded', 'emit_codex_tool_recorded', 'emit_codex_turn_ended', 'emit_grok_tool_recorded', 'emit_grok_turn_ended', 'emit_council_lane_invoked', 'emit_codex_review_verdict')

def emit_tool_call_lifecycle_recorded(
    *,
    session_id: str,
    tool_name_enum: str,
    duration_bucket: str,
    success: bool,
    orphan: bool,
    project: str = "",
) -> None:
    """Emit tool_call_lifecycle_recorded (PLAN-125 WS-1 / kooky-harvest).

    Fired once per paired PostToolUse / PostToolUseFailure completion (and by
    the bounded orphan sweeper). Deny-by-default field allowlist enforced
    (Sec MF-SEC-1/2/3): NO raw tool name, NO raw duration_ms, NO body fields.

    The two closed enums are re-validated here (defense-in-depth): an
    unrecognized ``tool_name_enum`` is coerced to ``"other"`` and an
    unrecognized ``duration_bucket`` to ``"lt_100ms"`` so a smuggled raw value
    can never reach the wire even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. The lifecycle producer (`_lib/tool_lifecycle.py`) also wraps
    this in a broad except so a slow filelock NEVER blocks the tool (MF-SEC-5).
    """
    safe_tool_name = (
        tool_name_enum
        if tool_name_enum in _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM
        else "other"
    )
    safe_bucket = (
        duration_bucket
        if duration_bucket in _TOOL_CALL_LIFECYCLE_DURATION_BUCKETS
        else "lt_100ms"
    )
    raw_event: Dict[str, Any] = {
        "action": "tool_call_lifecycle_recorded",
        "session_id": session_id,
        "project": project,
        "tool_name_enum": safe_tool_name,
        "duration_bucket": safe_bucket,
        "success": bool(success),
        "orphan": bool(orphan),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"tool_call_lifecycle_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_codex_tool_recorded(
    *,
    session_id: str,
    tool_name_enum: str,
    hook_event_name: str = "PostToolUse",
    project: str = "",
) -> None:
    """Emit codex_tool_recorded (PLAN-155 Wave 4 / SENT-CX-B / ADR-161).

    Fired once per codex PostToolUse `*` matcher hit by audit_log.py under
    CEO_HOOK_ADAPTER=codex — the completeness-bounded per-tool-call append
    that lands the codex session in the HMAC chain. DISTINCT action from
    agent_spawn (claude-only spawn record) and codex_turn_ended (the
    turn-level backstop) so a completeness query can count them separately.

    Deny-by-default field allowlist enforced (Sec MF-3): NO command bytes,
    NO apply_patch body, NO file paths, NO tool_response text, NO prompt.
    Both closed enums are re-validated here (defense-in-depth): an
    unrecognized ``tool_name_enum`` coerces to ``"other"`` (a raw
    ``mcp__<server>__<tool>`` string that reached here uncoerced would map to
    ``"other"`` — the audit_log codex path pre-maps mcp__* to ``"mcp_other"``)
    and an unrecognized ``hook_event_name`` coerces to ``"PostToolUse"`` so a
    smuggled raw value can never reach the wire on a direct caller path.

    Completeness residual (named, ADR-161 + degradation page): under partial
    shell interception codex may not fire PostToolUse for every tool call, so
    absence of a row is NOT evidence of absence of activity. The chain shape
    and verify_chain() are unchanged; this only appends.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. audit_log.py also wraps this so a slow filelock never blocks
    the codex session (the whole hook exits 0 on every path).
    """
    safe_tool = (
        tool_name_enum
        if tool_name_enum in _CODEX_TOOL_RECORDED_TOOL_NAME_ENUM
        else "other"
    )
    safe_event = (
        hook_event_name
        if hook_event_name in _CODEX_TOOL_RECORDED_EVENT_ENUM
        else "PostToolUse"
    )
    raw_event: Dict[str, Any] = {
        "action": "codex_tool_recorded",
        "session_id": session_id,
        "project": project,
        "harness": "codex",
        "hook_event_name": safe_event,
        "tool_name_enum": safe_tool,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CODEX_TOOL_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"codex_tool_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_codex_turn_ended(
    *,
    session_id: str,
    source: str,
    stop_hook_active: bool = False,
    project: str = "",
) -> None:
    """Emit codex_turn_ended (PLAN-155 Wave 4 / SENT-CX-B / ADR-161).

    The turn-level backstop append. Fired by audit_log.py under
    CEO_HOOK_ADAPTER=codex on a codex Stop / SubagentStop hook event, and by
    the headless ``codex-exec-wrapper.sh`` bracket (source="wrapper"). A
    DISTINCT action from codex_tool_recorded so a partial-interception turn
    (per-tool appends dropped) is still marked in the chain AND is never
    conflated with a per-tool append by the completeness query.

    Deny-by-default field allowlist (Sec MF-3): NO last_assistant_message,
    NO transcript path, NO agent id, NO command/prompt text. ``source`` is a
    closed enum (miss -> "other"); ``stop_hook_active`` is the codex loop
    guard (bool). Fail-open per audit_emit contract.
    """
    safe_source = (
        source if source in _CODEX_TURN_ENDED_SOURCE_ENUM else "other"
    )
    raw_event: Dict[str, Any] = {
        "action": "codex_turn_ended",
        "session_id": session_id,
        "project": project,
        "harness": "codex",
        "source": safe_source,
        "stop_hook_active": bool(stop_hook_active),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CODEX_TURN_ENDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"codex_turn_ended dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_grok_tool_recorded(
    *,
    session_id: str,
    tool_name_enum: str,
    hook_event_name: str = "PostToolUse",
    project: str = "",
) -> None:
    """Emit grok_tool_recorded (PLAN-156 Wave 4 / SENT-GK-B / ADR-162).

    Fired once per grok PostToolUse hit by audit_log.py under
    CEO_HOOK_ADAPTER=grok — the completeness-bounded per-tool-call append
    that lands the grok session in the HMAC chain. DISTINCT action from the
    codex/claude rails so a completeness query can count grok separately.

    Deny-by-default field allowlist (Sec MF-3): NO command bytes, NO edit
    body, NO file paths, NO tool_response text, NO prompt. Both closed enums
    are re-validated here (a smuggled raw value can never reach the wire).

    Completeness residual (named, ADR-162 + degradation page): grok's hook
    coverage is per-event, and PostToolUse is passive there, so absence of a
    row is NOT evidence of absence of activity. Chain shape + verify_chain()
    unchanged; this only appends. Fail-open per audit_emit contract.
    """
    safe_tool = (
        tool_name_enum
        if tool_name_enum in _GROK_TOOL_RECORDED_TOOL_NAME_ENUM
        else "other"
    )
    safe_event = (
        hook_event_name
        if hook_event_name in _GROK_TOOL_RECORDED_EVENT_ENUM
        else "PostToolUse"
    )
    raw_event: Dict[str, Any] = {
        "action": "grok_tool_recorded",
        "session_id": session_id,
        "project": project,
        "harness": "grok",
        "hook_event_name": safe_event,
        "tool_name_enum": safe_tool,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _GROK_TOOL_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"grok_tool_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_grok_turn_ended(
    *,
    session_id: str,
    source: str,
    project: str = "",
) -> None:
    """Emit grok_turn_ended (PLAN-156 Wave 4 / SENT-GK-B / ADR-162).

    The turn-level backstop append. Fired by audit_log.py under
    CEO_HOOK_ADAPTER=grok on a grok Stop / SubagentStop hook event. Grok's
    Stop is PASSIVE (it cannot block), but the audit append still lands — a
    DISTINCT action from grok_tool_recorded so a partial-coverage turn is
    still marked in the chain. Grok has no `stop_hook_active` analogue, so
    (unlike the codex twin) this carries no loop-guard field.

    ``source`` is a closed enum (miss -> "other"). Deny-by-default field
    allowlist (Sec MF-3): NO last_assistant_message, NO transcript path, NO
    command/prompt text. Fail-open per audit_emit contract.
    """
    safe_source = (
        source if source in _GROK_TURN_ENDED_SOURCE_ENUM else "other"
    )
    raw_event: Dict[str, Any] = {
        "action": "grok_turn_ended",
        "session_id": session_id,
        "project": project,
        "harness": "grok",
        "source": safe_source,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _GROK_TURN_ENDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"grok_turn_ended dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_council_lane_invoked(
    *,
    session_id: str,
    vendor: str,
    lane_status: str,
    project: str = "",
) -> None:
    """Emit council_lane_invoked (PLAN-156 Wave 6 / SENT-GK-F / ADR-162).

    One append per AVAILABLE external council lane per run — the auditable
    record that repo scope left the process to an external vendor. Sec MF-3
    deny-by-default: the ONLY caller fields are the closed-enum ``vendor``
    and ``lane_status``. NEVER the audited scope, NEVER findings, NEVER any
    prompt bytes — the egress content is ratified by the operator at OQ5;
    this row records the FACT of egress, not its content.

    Completeness residual (ADR-162): an absent row is not evidence of an
    absent invocation. Fail-open per audit_emit contract.
    """
    safe_vendor = vendor if vendor in _COUNCIL_VENDOR_ENUM else "other"
    safe_status = lane_status if lane_status in _COUNCIL_LANE_STATUS_ENUM else "other"
    raw_event: Dict[str, Any] = {
        "action": "council_lane_invoked",
        "session_id": session_id,
        "project": project,
        "vendor": safe_vendor,
        "lane_status": safe_status,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _COUNCIL_LANE_INVOKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"council_lane_invoked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_codex_review_verdict(
    *,
    outcome: str,
    diff_sha256: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit codex_review_verdict (PLAN-161 W2 C5 / CF-9 liveness telemetry).

    Fired by `codex_review_user_code.py` (the Stop-hook cross-model review of
    the adopter's own risky diff) once per distinct (diff_sha256, outcome)
    pair — the producer dedupes so Stop-retry loops re-review without
    re-emitting. Closed outcome enum:

      clean / findings     — a strictly PARSED verdict on a risky diff
                             (the healthy class for the /ceo-boot
                             `stop_review` liveness sub-rail)
      skipped_failopen     — infra fail-open (codex missing / rc!=0 / empty
                             stdout / timeout) OR a MALFORMED verdict; the
                             coercion target for any unrecognized value
      detected_only        — DETECT-ONLY default mode nudged a review but
                             never ran one (neutral: never healthy, never
                             failopen — r3 F3)

    Deny-by-default field allowlist enforced: the ONLY caller fields are the
    closed-enum `outcome` + shape-validated `diff_sha256` (64-lowercase-hex,
    else COERCED to ""). The verdict TEXT, the diff content, and file paths
    are NEVER persisted (a Codex finding can quote secrets from the diff).

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. NEVER routes through _EMIT_GENERIC_PASSTHROUGH.
    """
    safe_outcome = (
        outcome
        if outcome in _CODEX_REVIEW_VERDICT_OUTCOME_ENUM
        else "skipped_failopen"
    )
    safe_sha = (
        diff_sha256
        if (isinstance(diff_sha256, str)
            and _CODEX_REVIEW_DIFF_SHA256_RE.fullmatch(diff_sha256))
        else ""
    )
    raw_event: Dict[str, Any] = {
        "action": "codex_review_verdict",
        "session_id": session_id,
        "project": project,
        "outcome": safe_outcome,
        "diff_sha256": safe_sha,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CODEX_REVIEW_VERDICT_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"codex_review_verdict dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )
