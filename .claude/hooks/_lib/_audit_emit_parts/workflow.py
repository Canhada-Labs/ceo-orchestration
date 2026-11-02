"""Workflow.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_debate_event', 'emit_plan_transition', 'emit_veto_triggered', 'emit_benchmark_run', '_EVAL_TASK_COMPLETED_ALLOWLIST', 'emit_eval_task_completed', 'emit_injection_flag', 'emit_lesson_write', 'emit_confidence_gate', 'emit_lesson_read', 'emit_lesson_archived', 'emit_lesson_restored', 'emit_lesson_outcome', 'emit_state_store_write', 'emit_state_store_read', 'emit_budget_exceeded', 'emit_budget_bypass_used', 'emit_otel_export_dropped', 'emit_output_safety_flag')

# -----------------------------------------------------------------------------
# Public emitters
# -----------------------------------------------------------------------------


def emit_debate_event(
    plan_id: str,
    round_num: int,
    phase: str,
    agent: str,
    artifact_path: Optional[str] = None,
    consensus_adjustments_count: Optional[int] = None,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a debate round event.

    Args:
        plan_id: e.g. "PLAN-004"
        round_num: 1–3
        phase: "start" | "agent-done" | "consensus"
        agent: archetype slug (vp-engineering, security-engineer, etc.) or "consensus"
        artifact_path: path to the critique/consensus file
        consensus_adjustments_count: set only on phase="consensus"
    """
    event: Dict[str, Any] = {
        "action": "debate_event",
        "plan_id": plan_id,
        "round": round_num,
        "phase": phase,
        "agent": agent,
        "session_id": session_id,
        "project": project,
    }
    if artifact_path is not None:
        event["artifact_path"] = artifact_path
    if consensus_adjustments_count is not None:
        event["consensus_adjustments_count"] = consensus_adjustments_count
    _write_event(event)


def emit_plan_transition(
    plan_id: str,
    from_status: str,
    to_status: str,
    file_path: str,
    editor_tool: str = "Edit",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a legal plan status transition event.

    Illegal transitions are blocked by check_plan_edit.py and emit a
    veto_triggered event instead.
    """
    event: Dict[str, Any] = {
        "action": "plan_transition",
        "plan_id": plan_id,
        "from_status": from_status,
        "to_status": to_status,
        "editor_tool": editor_tool,
        "file_path": file_path,
        "transition_legal": True,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_veto_triggered(
    hook: str,
    reason_code: str,
    reason_preview: str,
    blocked_tool: str = "",
    strike_count: Optional[int] = None,
    session_id: str = "",
    project: str = "",
    caller: str = "",
) -> None:
    """Emit a veto / block event from any governance hook.

    Args:
        hook: "check_agent_spawn" | "check_plan_edit" | "check_bash_safety"
        reason_code: machine-readable rule identifier (e.g. "missing_skill_content")
        reason_preview: human-readable summary (redacted + truncated)
        blocked_tool: tool call that was blocked
        strike_count: session-scoped count (if tracked)
        caller: identity of the spawning agent or "ceo" (kernel events
            require this for forensic traceability — schema v2.14)
    """
    event: Dict[str, Any] = {
        "action": "veto_triggered",
        "hook": hook,
        "reason_code": reason_code,
        "reason_preview": _preview(reason_preview),
        "blocked_tool": blocked_tool,
        "session_id": session_id,
        "project": project,
    }
    if strike_count is not None:
        event["strike_count"] = strike_count
    if caller:
        event["caller"] = caller
    _write_event(event)


def emit_benchmark_run(
    benchmark_id: str,
    skill: str,
    pass_count: int,
    fail_count: int,
    pass_rate: float,
    median_score: float,
    floor: float,
    cost_usd: float = 0.0,
    duration_s: float = 0.0,
    lessons_written: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a benchmark run completion event.

    Float fields are encoded as integers to satisfy the canonical_json
    no-float invariant on HMAC-covered audit events:

    - ``pass_rate``    → ``pass_rate_bps``    (rate × 1000, 0..1000)
    - ``median_score`` → ``median_score_bps`` (score × 1000, 0..1000)
    - ``floor``        → ``floor_bps``        (rate × 1000, 0..1000)
    - ``cost_usd``     → ``cost_usd_cents``   (USD × 100, ≥0)
    - ``duration_s``   → ``duration_ms``      (seconds × 1000, ≥0)

    Readers must divide by the respective denominator to recover the
    original scale.
    """
    event: Dict[str, Any] = {
        "action": "benchmark_run",
        "benchmark_id": benchmark_id,
        "skill": skill,
        "pass_count": int(pass_count),
        "fail_count": int(fail_count),
        "pass_rate_bps": max(0, min(1000, int(round(float(pass_rate) * 1000)))),
        "median_score_bps": max(0, min(1000, int(round(float(median_score) * 1000)))),
        "floor_bps": max(0, min(1000, int(round(float(floor) * 1000)))),
        "cost_usd_cents": max(0, int(round(float(cost_usd) * 100))),
        "duration_ms": max(0, int(round(float(duration_s) * 1000))),
        "lessons_written": int(lessons_written),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# PLAN-133 C3 — Sec MF-3 field allowlist for eval_task_completed. Closed set;
# anything outside it is dropped by _scrub (see emit_generic dispatch below).
_EVAL_TASK_COMPLETED_ALLOWLIST = frozenset({
    "action", "task_id", "reward_bps", "status", "attempts",
    "flaky", "tokens", "turns", "event_schema", "ts",
})


def emit_eval_task_completed(
    task_id: str,
    reward: float,
    status: str = "",
    attempts: int = 0,
    flaky: bool = False,
    tokens: int = 0,
    turns: int = 0,
) -> None:
    """Emit one real-task reward-benchmark result (PLAN-133 C3).

    NO-VALUE-ECHO contract: the only free-text inputs are ``task_id`` (a stable
    task slug from .claude/eval/tasks/, NOT user/model content) and ``status``
    (coerced to the closed trial-status enum). No rejected env value, egress
    destination, retry_delay, or model output is ever carried. ``reward`` is
    encoded as basis-points (``reward_bps`` 0..1000) to satisfy the canonical_json
    no-float invariant; ``flaky`` is encoded as 0/1.
    """
    status_norm = status if status in ("pass", "partial", "fail") else "other"
    event: Dict[str, Any] = {
        "action": "eval_task_completed",
        "task_id": str(task_id)[:64],
        "reward_bps": max(0, min(1000, int(round(float(reward) * 1000)))),
        "status": status_norm,
        "attempts": max(0, int(attempts)),
        "flaky": 1 if flaky else 0,
        "tokens": max(0, int(tokens)),
        "turns": max(0, int(turns)),
    }
    _write_event(event)


def emit_injection_flag(
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    triggered_by_tool: str = "",
    snippet_preview: str = "",
    truncated: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a prompt-injection flag event (v2.1, ADR-011).

    Always advisory: this event records observation, never enforces a
    block. The PreToolUse hook `check_read_injection.py` calls this
    after running scan_text on a Read result; the audit-query.py
    `vetoes` and `metrics` sub-commands surface aggregated counts.

    Args:
        source: file path / "<stdin>" / tool input identifier
        family_counts: per-family hit counts (e.g. {"direct_override": 2})
        match_count: total matches across families
        bytes_scanned: bytes the scanner inspected (bounded at 1 MiB)
        triggered_by_tool: e.g. "Read", "Bash"
        snippet_preview: redacted snippet of the highest-confidence hit
        truncated: True if input exceeded scanner cap
    """
    event: Dict[str, Any] = {
        "action": "injection_flag",
        "source": source,
        "family_counts": dict(family_counts),
        "match_count": int(match_count),
        "bytes_scanned": int(bytes_scanned),
        "truncated": bool(truncated),
        "triggered_by_tool": triggered_by_tool,
        "snippet_preview": _preview(snippet_preview, max_len=200),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_write(
    lesson_id: str,
    archetype: str,
    scope_tags: List[str],
    trigger: str,
    source_event_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson-write event (Reflexion corpus growth).

    Args:
        lesson_id: stable identifier (e.g. hash or ULID)
        archetype: owning archetype slug
        scope_tags: scope tag list (subset of skill scope_tags)
        trigger: "benchmark_fail" | "debate_adjustment" | "manual"
        source_event_id: correlation to the originating event (desc_hash or artifact_path)
    """
    event: Dict[str, Any] = {
        "action": "lesson_write",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "scope_tags": list(scope_tags),
        "trigger": trigger,
        "source_event_id": source_event_id,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate(
    claim_count: int,
    pass_count: int,
    fail_count: int,
    verifier_kind_counts: Dict[str, int],
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
    raw_claim_count: Optional[int] = None,
    truncated: bool = False,
) -> None:
    """Emit a confidence_gate event (Sprint 8 Phase 2, ADR-018).

    Advisory-only in Sprint 8: collects FPR baseline for Sprint 9 enforcement
    decision. Reserved fields set from day 1 (debate consensus C4).

    Sprint 9 (PLAN-009 A12) adds ``raw_claim_count`` + ``truncated`` for
    ``CEO_CONFIDENCE_MAX_CLAIMS`` cap reporting. When the input produced
    more CLAIM tokens than the cap, ``claim_count`` is the post-cap value,
    ``raw_claim_count`` is the pre-cap count, and ``truncated=True``.

    Args:
        claim_count: verified CLAIM tokens (post code-block exemption + cap)
        pass_count: claims that verified
        fail_count: claims that failed to verify
        verifier_kind_counts: dict of claim kind -> count (all kinds seen)
        agent_name: name of the agent whose output was scanned (optional)
        source: "stdin" | "<file path>" | "<spawn-ref>"
        raw_claim_count: pre-cap CLAIM token count; defaults to claim_count
            when the caller did not surface a cap
        truncated: True when raw_claim_count > claim_count
    """
    if raw_claim_count is None:
        raw_claim_count = int(claim_count)
    event: Dict[str, Any] = {
        "action": "confidence_gate",
        "claim_count": int(claim_count),
        "raw_claim_count": int(raw_claim_count),
        "truncated": bool(truncated),
        "pass_count": int(pass_count),
        "fail_count": int(fail_count),
        "verifier_kind_counts": dict(verifier_kind_counts),
        "agent_name": agent_name,
        "source": source,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_read(
    lesson_ids: List[str],
    archetype: str,
    keywords: List[str],
    k: int,
    consumer: str = "architect",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_read event (Sprint 8 Phase 3).

    Logged when `lessons.get_top_k()` is invoked to inject top-K lessons
    into a spawn prompt. Enables Sprint 9 outcome-tracking integration
    (correlating which injected lessons correlated with benchmark hits).

    Args:
        lesson_ids: list of lesson IDs that were read (length <= k)
        archetype: archetype that the lessons were queried for
        keywords: keywords used for ranking
        k: requested top-K count
        consumer: "architect" | "spawn" | "cli"
    """
    event: Dict[str, Any] = {
        "action": "lesson_read",
        "lesson_ids": list(lesson_ids),
        "lesson_count": len(lesson_ids),
        "archetype": archetype,
        "keywords": list(keywords),
        "k": int(k),
        "consumer": consumer,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_archived(
    lesson_id: str,
    archetype: str,
    hit_count: int,
    miss_count: int,
    hit_rate: float,
    archive_path: str,
    reason: str = "low_hit_rate",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_archived event (Sprint 8 Phase 4).

    Logged by `prune-lessons.py --execute` when a lesson meets prune
    criteria (ADR-017, amended Sprint 8) and is moved to archive.
    Archive is reversible via `lesson-restore.py`.

    ``hit_rate_bps`` is integer basis-points (hit_rate × 1000, clamped
    0..1000). canonical_json forbids floats in HMAC-covered fields; the
    old ``hit_rate`` float caused CanonicalJsonError + dropped events.
    Caller passes the raw 0..1 float; we convert here.
    """
    bps = max(0, min(1000, int(round(hit_rate * 1000))))
    event: Dict[str, Any] = {
        "action": "lesson_archived",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "hit_rate_bps": bps,
        "archive_path": archive_path,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_restored(
    lesson_id: str,
    archetype: str,
    restored_from: str,
    restored_to: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_restored event (Sprint 8 Phase 4b).

    Logged by `lesson-restore.py` when a previously archived lesson is
    moved back to the active lessons directory.
    """
    event: Dict[str, Any] = {
        "action": "lesson_restored",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "restored_from": restored_from,
        "restored_to": restored_to,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_outcome(
    lesson_id: str,
    archetype: str,
    hit: bool,
    hit_count: int = 0,
    miss_count: int = 0,
    session_id: str = "",
    project: str = "",
    consumer: str = "benchmark",
    inference_mode: str = "",
    window_duration_seconds: int = 0,
    session_end_reason: str = "",
) -> None:
    """Emit a lesson_outcome event (Reflexion v2 / ADR-015).

    Logged when a consumer (benchmark or architect) applies a lesson and
    the outcome is classified as hit / miss.

    PLAN-009 P3.2/P3.5 (ADR-015 amendment) adds:

    - ``consumer`` — closed enum {"benchmark", "architect"}. Back-compat:
      pre-Sprint-9 events missing this field are parsed as "benchmark"
      (single-consumer era default). SPEC/v1/audit-log.schema.md v2.2.2.
    - ``inference_mode`` — "window-only" | "session-correlated" |
      "" (legacy). Architect paths use "session-correlated"; older
      benchmarks retain "window-only" retroactively.
    - ``window_duration_seconds`` — how wide a window the outcome was
      attributed across (0 = not-applicable / benchmark).
    - ``session_end_reason`` — "timeout" | "explicit" | "unknown" | "".

    `event_schema` stays "v2" — additive per ADR-011 pattern.
    """
    event: Dict[str, Any] = {
        "action": "lesson_outcome",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "hit": bool(hit),
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "session_id": session_id,
        "project": project,
        "consumer": consumer,
        "inference_mode": inference_mode,
        "window_duration_seconds": int(window_duration_seconds),
        "session_end_reason": session_end_reason,
    }
    _write_event(event)


def emit_state_store_write(
    store_name: str,
    plan_id_hash: str,
    key_hash: str,
    value_bytes: int,
    ttl_seconds: Optional[int] = None,
    redaction_applied: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store write event (Sprint 11 Phase 0, ADR-027).

    ``plan_id_hash`` and ``key_hash`` are SHA-256 prefixes (16 chars) —
    plaintext plan_id/key is never audited. ``redaction_applied`` is True
    if ``redact_secrets`` mutated the original string value.

    Args:
        store_name: short store slug (e.g. "scratchpad").
        plan_id_hash: 16-char SHA-256 prefix of PLAN-NNN string.
        key_hash: 16-char SHA-256 prefix of the key.
        value_bytes: size of the stored value (post-redaction) in bytes.
        ttl_seconds: None if no TTL; int seconds-from-now otherwise.
        redaction_applied: True if ``redact_secrets`` changed the value.
    """
    event: Dict[str, Any] = {
        "action": "state_store_write",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "key_hash": key_hash,
        "value_bytes": int(value_bytes),
        "ttl_seconds": int(ttl_seconds) if ttl_seconds is not None else None,
        "redaction_applied": bool(redaction_applied),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_state_store_read(
    store_name: str,
    plan_id_hash: str,
    key_hash: str,
    found: bool,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store read event (Sprint 11 Phase 0, ADR-027).

    ``found=False`` covers both missing-key and expired-TTL — the
    consumer can correlate with subsequent prune events to tell them
    apart if needed.
    """
    event: Dict[str, Any] = {
        "action": "state_store_read",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "key_hash": key_hash,
        "found": bool(found),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_budget_exceeded(
    plan_id: str,
    spawn_id: str,
    tokens_used: int,
    cap: int,
    scope: str = "spawn",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a budget_exceeded event (Sprint 11 Phase 6, ADR-033).

    Fired by ``check_budget.py`` when a spawn or plan rollup exceeds the
    configured cap. Advisory in Sprint 11 (enforcing Sprint 12 IFF FPR
    data supports it per H16).

    Args:
        plan_id: PLAN-NNN string (unhashed; plan-level budgets are
            Owner-visible).
        spawn_id: session-local spawn identifier or ``""`` for plan-scope.
        tokens_used: post-spawn running total.
        cap: configured cap (e.g. CEO_MAX_SPAWN_TOKENS).
        scope: ``"spawn"`` | ``"plan"``.
    """
    event: Dict[str, Any] = {
        "action": "budget_exceeded",
        "plan_id": plan_id,
        "spawn_id": spawn_id,
        "tokens_used": int(tokens_used),
        "cap": int(cap),
        "scope": scope,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_budget_bypass_used(
    plan_id: str,
    caller_pid: int,
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a budget_bypass_used event (Sprint 11 Phase 6, H13).

    Fired when ``CEO_BUDGET_BYPASS=1`` is honored on a blocked spawn.
    Owner-only scope (H13 mirrors ADR-019 C6/A8). Rate-limited to N
    bypasses / 24h — caller enforces the counter; this emitter just
    records the event. ``reason`` is a short free-text preview (e.g.
    ``"emergency: prod down"``).
    """
    event: Dict[str, Any] = {
        "action": "budget_bypass_used",
        "plan_id": plan_id,
        "caller_pid": int(caller_pid),
        "reason_preview": _preview(reason, max_len=120),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_otel_export_dropped(
    fields_dropped_count: int,
    endpoint_host: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit an otel_export_dropped event (Sprint 11 Phase 8, CR3).

    Fired by ``otel-export.py`` when ``redact_secrets`` removes a field
    from a span attribute OR when host allowlist rejects a target. The
    endpoint is recorded as host-only (no URL path, no query). Full
    endpoint URL is NEVER audited (defense-in-depth).
    """
    event: Dict[str, Any] = {
        "action": "otel_export_dropped",
        "fields_dropped_count": int(fields_dropped_count),
        "endpoint_host": endpoint_host,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_output_safety_flag(
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    redaction_applied: bool = False,
    triggered_by_tool: str = "",
    snippet_preview: str = "",
    truncated: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit an output_safety_flag event (Sprint 11 Phase 9, ADR-036).

    Shape mirrors ``injection_flag`` (ADR-011) but scans agent outputs
    instead of inputs (PostToolUse Agent). Advisory Sprint 11. See
    consensus H14 for scanner pipeline order.
    """
    event: Dict[str, Any] = {
        "action": "output_safety_flag",
        "source": source,
        "family_counts": dict(family_counts),
        "match_count": int(match_count),
        "bytes_scanned": int(bytes_scanned),
        "redaction_applied": bool(redaction_applied),
        "truncated": bool(truncated),
        "triggered_by_tool": triggered_by_tool,
        "snippet_preview": _preview(snippet_preview, max_len=200),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
