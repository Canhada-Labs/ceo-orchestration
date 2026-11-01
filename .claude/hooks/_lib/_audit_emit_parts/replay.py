"""Replay.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_policy_evaluated', 'emit_policy_denied', 'emit_policy_error', 'emit_replay_started', 'emit_replay_completed', 'emit_replay_diff_produced', 'emit_replay_capture_started', 'emit_replay_capture_completed', 'emit_prediction_queried', 'emit_pattern_stored', 'emit_pattern_queried', 'emit_pattern_evicted', 'emit_threat_model_promoted', 'emit_threat_model_freshness_breach', 'iter_events')

# -----------------------------------------------------------------------------
# Sprint 14 Phase 0.6 (PLAN-014) — audit registry v2.6 emitters
# -----------------------------------------------------------------------------


def emit_policy_evaluated(
    policy_id: str,
    rule_id: str,
    decision: str,
    duration_ms: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit policy_evaluated (ADR-045 + SPEC/v1/policy-dsl.schema.md).

    Fired on every rule evaluation. ``decision`` ∈ {allow, deny, block}.
    ``policy_id`` matches ``.claude/policies/<name>.yaml`` filename.
    """
    _write_event({
        "action": "policy_evaluated",
        "policy_id": policy_id,
        "rule_id": rule_id,
        "decision": decision,
        "duration_ms": int(duration_ms),
        "session_id": session_id,
        "project": project,
    })


def emit_policy_denied(
    policy_id: str,
    rule_id: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit policy_denied (ADR-045 §Decision — final deny after rule evaluation).

    ``reason`` is a closed-enum error-model string per SPEC §Error-model.
    """
    _write_event({
        "action": "policy_denied",
        "policy_id": policy_id,
        "rule_id": rule_id,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    })


def emit_policy_error(
    policy_id: str,
    error_kind: str,
    detail: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit policy_error (ADR-045 §Fail-mode matrix — A.3.1).

    ``error_kind`` ∈ {parse_error, predicate_missing, import_failure,
    depth_limit, size_limit, alias_rejected, tag_rejected}. Security
    surfaces fail-CLOSED after this event; advisory surfaces fail-open.
    ``detail`` is free-text redacted via _redact.redact_secrets in write path.
    """
    _write_event({
        "action": "policy_error",
        "policy_id": policy_id,
        "error_kind": error_kind,
        "detail": _redact.redact_secrets(detail or ""),
        "session_id": session_id,
        "project": project,
    })


def emit_replay_started(
    original_session_id: str,
    mode: str,
    redacted_fragments_count: int = 0,
    as_user: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit replay_started (ADR-046 + SPEC/v1/replay.schema.md).

    ``mode`` ∈ {dry_run, execute}. ``--execute`` default: stub adapters +
    OTEL disabled per ADR-046 invariant "replays never reach real
    providers by default". ``as_user`` preserves original-session-owner
    distinction (Security unseen #3).
    """
    _write_event({
        "action": "replay_started",
        "original_session_id": original_session_id,
        "mode": mode,
        "redacted_fragments_count": int(redacted_fragments_count),
        "as_user": as_user,
        "session_id": session_id,
        "project": project,
    })


def emit_replay_completed(
    original_session_id: str,
    mode: str,
    duration_ms: int,
    spawn_count: int,
    diff_summary: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit replay_completed (ADR-046)."""
    _write_event({
        "action": "replay_completed",
        "original_session_id": original_session_id,
        "mode": mode,
        "duration_ms": int(duration_ms),
        "spawn_count": int(spawn_count),
        "diff_summary": diff_summary,
        "session_id": session_id,
        "project": project,
    })


def emit_replay_diff_produced(
    original_session_id: str,
    spawn_ordinal: int,
    divergence_kind: str,
    artifact_path: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit replay_diff_produced (ADR-046 — per-spawn divergence artifact).

    ``divergence_kind`` ∈ {output_mismatch, spawn_missing, extra_spawn,
    env_mismatch, audit_payload_mismatch}.
    """
    _write_event({
        "action": "replay_diff_produced",
        "original_session_id": original_session_id,
        "spawn_ordinal": int(spawn_ordinal),
        "divergence_kind": divergence_kind,
        "artifact_path": artifact_path,
        "session_id": session_id,
        "project": project,
    })


def emit_replay_capture_started(
    original_session_id: str,
    redacted_fragments_count: int = 0,
    as_user: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit replay_capture_started (PLAN-069 Phase 1 / ADR-101 / SPEC v2.16).

    Capture mode produces a redacted JSONL fixture under $CLAUDE_PROJECT_DIR.
    Distinct from replay_started which describes dry_run/execute paths.
    ``redacted_fragments_count`` mirrors the existing replay_started semantic
    (advisory count of redactable audit-log payloads in scope).
    """
    _write_event({
        "action": "replay_capture_started",
        "original_session_id": original_session_id,
        "redacted_fragments_count": int(redacted_fragments_count),
        "as_user": as_user,
        "session_id": session_id,
        "project": project,
    })


def emit_replay_capture_completed(
    original_session_id: str,
    duration_ms: int,
    event_count: int,
    fixture_path: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit replay_capture_completed (PLAN-069 Phase 1 / ADR-101 / SPEC v2.16).

    ``event_count`` is the total redacted events written to the fixture.
    ``fixture_path`` is the resolved $CLAUDE_PROJECT_DIR-relative path.
    """
    _write_event({
        "action": "replay_capture_completed",
        "original_session_id": original_session_id,
        "duration_ms": int(duration_ms),
        "event_count": int(event_count),
        "fixture_path": fixture_path,
        "session_id": session_id,
        "project": project,
    })


def emit_prediction_queried(
    plan_id: str,
    bucket_range: str,
    confidence: str,
    training_window_plans: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit prediction_queried (ADR-047 + SPEC/v1/predict-budget.schema.md).

    ``bucket_range`` is bucketed string (e.g. "100k-130k") per ADJ-038
    (NO raw dollar figures — Tier 2 sensitive). ``confidence`` ∈
    {high, medium, low, cold_start}. ``cold_start`` for zero-history
    adopter (Staff Backend unseen #5) — advisory only.
    """
    _write_event({
        "action": "prediction_queried",
        "plan_id": plan_id,
        "bucket_range": bucket_range,
        "confidence": confidence,
        "training_window_plans": int(training_window_plans),
        "session_id": session_id,
        "project": project,
    })


def emit_pattern_stored(
    topic: str,
    content_hash: str,
    size_bytes: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit pattern_stored (ADR-048 + SPEC/v1/memory-shared.schema.md).

    ``content_hash`` is sha256 of post-redact content (one-file-per-pattern
    naming per ADJ-035). ``topic`` is Unicode NFC + lowercase + dash-separated.
    Caller MUST redact-on-ingest via _redact.redact_secrets before write.
    """
    _write_event({
        "action": "pattern_stored",
        "topic": topic,
        "content_hash": content_hash,
        "size_bytes": int(size_bytes),
        "session_id": session_id,
        "project": project,
    })


def emit_pattern_queried(
    topic: str,
    k: int,
    match_count: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit pattern_queried (ADR-048). ``k`` clamped 1..10 per SPEC."""
    _write_event({
        "action": "pattern_queried",
        "topic": topic,
        "k": int(k),
        "match_count": int(match_count),
        "session_id": session_id,
        "project": project,
    })


def emit_pattern_evicted(
    topic: str,
    content_hash: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit pattern_evicted (ADR-048 — manual eviction path).

    ``reason`` ∈ {admin_request, size_cap_breach, redact_violation}.
    Retention unbounded per SPEC — eviction only via this event path.
    """
    _write_event({
        "action": "pattern_evicted",
        "topic": topic,
        "content_hash": content_hash,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    })


def emit_threat_model_promoted(
    from_status: str,
    to_status: str,
    accepted_by: str,
    commit_sha: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit threat_model_promoted (Phase C.1 — docs/threat-model.md status flip).

    ``from_status`` → ``to_status`` ∈ {draft, accepted, stale}.
    ``accepted_by`` matches the signed ``Accepted-By:`` line + commit trailer.
    """
    _write_event({
        "action": "threat_model_promoted",
        "from_status": from_status,
        "to_status": to_status,
        "accepted_by": accepted_by,
        "commit_sha": commit_sha,
        "session_id": session_id,
        "project": project,
    })


def emit_threat_model_freshness_breach(
    new_adr_count_since_review: int,
    threshold: int = 2,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit threat_model_freshness_breach (Phase C.4 — status-flip accepted→stale).

    Per ADJ-021: freshness script flips status (not just warn) after
    ``threshold`` new in-scope ADRs merge without review.
    """
    _write_event({
        "action": "threat_model_freshness_breach",
        "new_adr_count_since_review": int(new_adr_count_since_review),
        "threshold": int(threshold),
        "session_id": session_id,
        "project": project,
    })


# -----------------------------------------------------------------------------
# Public: iterate events (derived views — used by audit-query.py sub-commands)
# -----------------------------------------------------------------------------


def iter_events(
    path: Optional[Path] = None,
    action_filter: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield events from the audit log, optionally filtering by action.

    Tolerates malformed lines (logs breadcrumb, skips).
    """
    log = path or _log_path()
    if not log.exists():
        return
    try:
        with log.open("r", encoding="utf-8") as f:
            for line_num, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    _breadcrumb(f"iter_events: malformed line {line_num}")
                    continue
                if action_filter and event.get("action") != action_filter:
                    continue
                yield event
    except OSError as e:  # pragma: no cover
        _breadcrumb(f"iter_events open error: {e}")
