"""Tokens boot.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_is_sha256_hex', '_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST', '_SUBAGENT_LIFECYCLE_ARCHETYPES', '_SUBAGENT_LIFECYCLE_WALL_SOURCES', '_SUBAGENT_LIFECYCLE_BUCKETS', 'scrub_audit_tokens_event', 'emit_audit_tokens_emitted', 'emit_audit_tokens_timeout', 'emit_audit_tokens_key_dropped', 'emit_mcp_injection_finding', '_scrub_ceo_boot_event', 'emit_ceo_boot_emitted', '_TOOL_CALL_LIFECYCLE_DURATION_BUCKETS', '_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM')

def _is_sha256_hex(value: Any) -> bool:
    """True iff ``value`` is a 64-char lowercase-hex sha256 digest.

    Defensive validator for the before/after hash pair (ADR-154 §2): a
    non-string, wrong-length, or non-hex value is rejected and the caller
    coerces it to "" (never echoed). Kept as a plain check (no regex) to
    preserve audit_emit's import surface.
    """
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


# PLAN-135 W2 H3 — Sec field allowlist for the per-agent SubagentStop lifecycle
# bracket (subagent_lifecycle_observed, producer
# .claude/hooks/check_fluency_nudge.py H3 extension). Deny-by-default. Same
# no-value-echo contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# transcript path/body, the RAW token counts, the RAW wall-time seconds, the
# raw agent_id and the confidence-marker snippets are NEVER allowed fields —
# only the closed-enum archetype + the four coarse brackets travel on the wire.
# The bracket IS the audit signal; the raw counts stay forensic-private (the
# S227 modelUsage reconstruction lives at bucket granularity here).
_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "agent_archetype", "wall_bucket", "wall_source",
    "token_bucket", "claim_bucket",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-135 W2 H3 — closed enum for the persona archetype that feeds the
# persona-ledger. Mirrors _PERSONA_COVERAGE_ARCHETYPES (the 4 VETO-floor
# personas, PLAN-093 Wave C.5) + "other" for any non-matching spawn type +
# "unknown" when the SubagentStart sidecar never recorded an agent_type.
# Anything outside the set (incl. a free-text spawn label or a missing field)
# is COERCED to "other" (S172 doctrine — the rejected value is never echoed,
# so a spawn description smuggled into agent_type cannot reach the wire).
_SUBAGENT_LIFECYCLE_ARCHETYPES = frozenset({
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer", "other", "unknown",
})


# PLAN-135 W2 H3 — closed enum for wall_source: was the SubagentStart instant
# recorded (so wall-time is a true bracket) or did the start go unobserved
# (orphaned start / kill-switch / crashed agent → bracket is "unknown")?
_SUBAGENT_LIFECYCLE_WALL_SOURCES = frozenset({
    "bracketed", "unknown",
})


# PLAN-135 W2 H3 — shared closed-enum bucket vocabulary for wall_bucket,
# token_bucket and claim_bucket. Coarse, monotonic, never a raw count. The
# bucketing function lives producer-side (check_fluency_nudge.py); audit_emit
# only validates the resulting token against this closed set (defense-in-depth
# on the direct emit_generic-caller path). "unknown" is the fail-closed
# sentinel for an unmeasured / unparseable dimension.
_SUBAGENT_LIFECYCLE_BUCKETS = frozenset({
    "none", "low", "medium", "high", "very_high", "unknown",
})


def scrub_audit_tokens_event(
    event: Dict[str, Any],
    *,
    allowlist: Optional[frozenset] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Filter an audit-tokens event dict to allowlisted keys only.

    Returns ``(cleaned_event, dropped_keys)``. Dropped keys are
    typically forbidden (raw text, payload bodies). Caller should
    emit ``audit_tokens_key_dropped`` breadcrumb if dropped is
    non-empty (defense-in-depth on allowlist drift).

    Pure function — no side effects. Never raises.

    Per SEC-P0-04 spec §Hook integration, this is called by
    emit_audit_tokens_emitted before _write_event. Belt-and-braces
    on top of audit-tokens.py CLI flag (--content-ban=strict).
    """
    if allowlist is None:
        allowlist = _AUDIT_TOKENS_ALLOWLIST
    if not isinstance(event, dict):
        return ({}, [])
    cleaned: Dict[str, Any] = {}
    dropped: List[str] = []
    for key, value in event.items():
        if key in allowlist:
            cleaned[key] = value
        else:
            dropped.append(key)
    return (cleaned, dropped)


def emit_audit_tokens_emitted(
    *,
    session_id: str,
    window_seconds: int,
    events_scanned: int,
    tokens_in_total: int,
    tokens_out_total: int,
    cost_cents: int,
    tier_id_distribution: Optional[Dict[str, int]] = None,
    detector_findings_count: Optional[Dict[str, int]] = None,
    hook_duration_ms: int = 0,
    timestamp: str = "",
    project: str = "",
) -> None:
    """Emit audit_tokens_emitted (SEC-P0-04 / ADR-080).

    Builds a counts-only event from audit-tokens.py stub output.
    Applies scrub_audit_tokens_event() defense-in-depth before write.
    If forbidden keys are stripped, also emits
    audit_tokens_key_dropped breadcrumb.

    Total event payload is bounded: per SEC-P0-04 spec §Acceptance
    test 8, serialized JSON < 2 KiB. The 12-key allowlist + integer/
    short-string values keep this well under cap.
    """
    raw_event: Dict[str, Any] = {
        "action": "audit_tokens_emitted",
        "session_id": session_id,
        "timestamp": timestamp or _utc_now_iso(),
        "window_seconds": int(window_seconds),
        "events_scanned": int(events_scanned),
        "tokens_in_total": int(tokens_in_total),
        "tokens_out_total": int(tokens_out_total),
        "cost_cents": int(cost_cents),
        "tier_id_distribution": dict(tier_id_distribution or {}),
        "detector_findings_count": dict(detector_findings_count or {}),
        "hook_duration_ms": int(hook_duration_ms),
        "project": project,
    }
    cleaned, dropped = scrub_audit_tokens_event(raw_event)
    _write_event(cleaned)
    # Defense-in-depth: if any keys were stripped, breadcrumb so a
    # post-flight scan or CI gate can detect allowlist drift.
    if dropped:
        emit_audit_tokens_key_dropped(
            session_id=session_id,
            dropped_keys=dropped,
            project=project,
        )


def emit_audit_tokens_timeout(
    *,
    session_id: str,
    timeout_seconds: float,
    project: str = "",
) -> None:
    """Emit audit_tokens_timeout (SEC-P0-04 §Performance budget).

    Fired when audit-tokens.py subprocess invocation exceeds
    ``timeout_seconds`` (default per SEC-P0-04: 0.05 = 50ms wall).
    Replaces the audit_tokens_emitted that would have been emitted
    on success — SessionEnd hook should not block on slow detectors.

    ``timeout_ms`` is integer milliseconds. canonical_json forbids floats
    in HMAC-covered fields; the old ``timeout_seconds`` float caused
    CanonicalJsonError + dropped events. Caller passes a float seconds
    value (backward-compatible); we convert to int ms here.
    """
    event: Dict[str, Any] = {
        "action": "audit_tokens_timeout",
        "session_id": session_id,
        "timeout_ms": max(0, int(round(timeout_seconds * 1000))),
        "project": project,
    }
    _write_event(event)


def emit_audit_tokens_key_dropped(
    *,
    session_id: str,
    dropped_keys: List[str],
    project: str = "",
) -> None:
    """Emit audit_tokens_key_dropped breadcrumb (SEC-P0-04 defense-in-depth).

    Fired by scrub_audit_tokens_event() when forbidden keys are
    stripped from an audit-tokens event. Indicates either:

    1. A code change introduced a new key without updating
       _AUDIT_TOKENS_ALLOWLIST (likely benign — drift signal).
    2. An attacker / misconfigured code injected forbidden content
       into audit-tokens output (real signal — investigate).

    Either way, post-flight scan can grep for these breadcrumbs to
    catch drift OR alert on attack. Event itself does NOT include
    the dropped values, only the keys (so even hostile keys with
    payload-like names don't leak content).
    """
    # Bound dropped_keys list size to prevent pathological emit cost
    # if every key in a misconfigured event was forbidden.
    keys_preview = list(dropped_keys)[:50]
    event: Dict[str, Any] = {
        "action": "audit_tokens_key_dropped",
        "session_id": session_id,
        "dropped_keys": keys_preview,
        "dropped_count": len(dropped_keys),
        "project": project,
    }






    _write_event(event)


# ---------------------------------------------------------------------
# PLAN-052 Phase 1 / ADR-083 — MCP injection scanner advisory finding
# Wired by PLAN-044 audit-v2 Wave B (C1-P0-03).
# ---------------------------------------------------------------------


def emit_mcp_injection_finding(
    *,
    server_id: str,
    mcp_tool_name: str,
    source_kind: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    severity: str,
    snippet_preview: str,
    scanner_action: str = "advisory",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `mcp_injection_finding` event from check_mcp_response.py.

    Schema mirrors `output_scan_finding` (ADR-057) with MCP-specific
    fields. Per SPEC/v1/audit-log.schema.md v2.13, fields are:

      - server_id: MCP server identifier (parsed from `mcp__<server>__<tool>`)
      - mcp_tool_name: tool name within the server
      - source_kind: which MCP surface triggered the scan
        (`tool_result` | `instructions` | `resource_fetch`)
      - family_counts: per-injection-family hit counts
        (harness_mimicry, role_preamble, directive_prose, synthetic_tool_call)
      - match_count: total individual pattern matches across families
      - bytes_scanned: total bytes the scanner inspected (for budget tracking)
      - severity: `low` | `medium` | `high` (per `_lib/mcp_injection_scan.py`
        `_SEVERITY_BY_FAMILY`; SPEC v1 audit-log.schema.md aligned). Session 75
        Codex Finding 6 closure: prior docstring `info|warn|block` was schema
        drift — never matched `classify()` returns.
      - snippet_preview: redacted ≤120-char preview of the offending text
      - scanner_action: `advisory` | `stripped` | `blocked` (per SPEC v1
        audit-log.schema.md). Session 75 Codex Finding 6 closure: prior
        docstring `block` was verb-form drift; SPEC declares state-form
        `blocked`. `stripped` is reserved for Phase 2 sanitization.

    Called from check_mcp_response.py:148 only when
    finding.matched. The hook is fail-open by contract — emission failures
    are swallowed by the caller's try/except.

    PLAN-044 audit-v2 C1-P0-03 closes 5 cross-validating findings
    (dim 04, 06, 07, 16, 18) by removing the `hasattr` guard in the
    hook AND registering the action here so emit_generic doesn't
    short-circuit.
    """
    emit_generic(
        "mcp_injection_finding",
        session_id=session_id,
        server_id=server_id,
        mcp_tool_name=mcp_tool_name,
        source_kind=source_kind,
        family_counts=dict(family_counts or {}),
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        severity=severity,
        snippet_preview=snippet_preview[:120] if snippet_preview else "",
        scanner_action=scanner_action,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-065 Phase 2 / ADR-098 — /ceo-boot lifecycle emitters.
# Sec MF-3 field allowlist enforced (deny-by-default). Forbidden fields
# (tokens / cost / paths / prompt / SKILL / env) are stripped before emit
# and a breadcrumb is written to audit-log.errors (NOT a typed audit
# event — drift signal only, mirrors the audit-tokens `_key_dropped`
# defense-in-depth pattern but kept off the typed stream until v1.13.0
# PLAN-067 if needed).
# ---------------------------------------------------------------------


def _scrub_ceo_boot_event(
    event: Dict[str, Any],
    allowlist: frozenset,
) -> Tuple[Dict[str, Any], List[str]]:
    """Strip any field outside ``allowlist``. Returns (cleaned, dropped_keys).

    Pure function. No I/O. Caller decides whether to breadcrumb the drop.
    Forbidden fields are NEVER returned in cleaned dict — this is the
    Sec MF-3 enforcement boundary. Drift = drop = visible.
    """
    cleaned: Dict[str, Any] = {}
    dropped: List[str] = []
    for k, v in event.items():
        if k in allowlist:
            cleaned[k] = v
        else:
            dropped.append(k)
    return cleaned, dropped


def emit_ceo_boot_emitted(
    *,
    session_id: str,
    gate_pass: bool,
    duration_ms: int,
    checks_total: int,
    checks_failed: int,
    cache_hit: bool = False,
    project: str = "",
) -> None:
    """Emit ceo_boot_emitted (PLAN-065 Phase 2 / ADR-098).

    Fired once per /ceo-boot invocation at end-of-run (cached + uncached).
    Field allowlist enforced (Sec MF-3): no token counts, no cost, no
    paths, no prompt content, no SKILL.md content, no environment values.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. Caller (ceo-boot.py) MUST also wrap in a broad except
    so that a slow audit-log filelock NEVER blocks the user session.
    """
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_emitted",
        "session_id": session_id,
        "project": project,
        "gate_pass": bool(gate_pass),
        "duration_ms": int(duration_ms),
        "checks_total": int(checks_total),
        "checks_failed": int(checks_failed),
        "cache_hit": bool(cache_hit),
    }
    cleaned, dropped = _scrub_ceo_boot_event(raw_event, _CEO_BOOT_EMITTED_ALLOWLIST)
    _write_event(cleaned)
    if dropped:  # pragma: no cover — should be impossible from the typed wrapper
        _breadcrumb(
            f"ceo_boot_emitted dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


# PLAN-125 WS-1 (kooky-harvest) — closed-enum validation sets for the
# tool_call_lifecycle_recorded typed emitter. Kept local to the emitter so the
# enum domain is enforced at the typed entrypoint AND re-checked here even if a
# caller hand-builds the field values (defense-in-depth; the mapper in
# _lib/tool_lifecycle.py is the canonical producer).
_TOOL_CALL_LIFECYCLE_DURATION_BUCKETS = frozenset({
    "lt_100ms", "b_100ms_1s", "b_1_10s", "b_10_60s", "gt_60s",
})


# Recognized standard tool names + the two synthetic buckets the mapper
# produces. A value outside this set is coerced to "other" before emit so a
# raw mcp__<server>__<tool> string can NEVER reach the wire (MF-SEC-1), even on
# a direct typed-emitter call that bypassed the mapper.
# PLAN-153 wave-backlog (v2.48 additive enum extension): + TaskCreate /
# TaskUpdate / TaskGet / TaskList — the Claude Code 2.1.x Task tools that
# deprecate TodoWrite (which stays for back-compat). COUPLING (3-way pin):
# must stay in sync with `_RECOGNIZED_TOOL_NAMES` in _lib/tool_lifecycle.py
# and the closed enum on the `tool_call_lifecycle_recorded` row of
# SPEC/v1/audit-log.schema.md; pin-sync regression-guarded by
# hooks/tests/test_tool_lifecycle_enum_pin_sync.py.
_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM = frozenset({
    "Agent", "Task", "TaskCreate", "TaskUpdate", "TaskGet", "TaskList",
    "Bash", "Edit", "MultiEdit", "Write", "Read",
    "Glob", "Grep", "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite",
    "mcp_other", "other",
})
