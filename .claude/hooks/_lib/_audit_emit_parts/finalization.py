"""Finalization.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_chain_reset_marker', 'emit_task_route_key_dropped', 'emit_reality_ledger_key_dropped', 'emit_swarm_finalize_grouped', 'emit_swarm_finalize_committed', 'emit_skill_reference_never_read', 'emit_escalation_detected', 'emit_escalation_dispatched', 'emit_escalation_suppressed', 'emit_escalation_baseline_recorded', 'emit_tournament_run_started', 'emit_tournament_task_scored', 'emit_tournament_run_completed', 'emit_tournament_budget_projected', 'emit_tournament_budget_exceeded', 'emit_tournament_aborted', 'emit_tournament_fixture_rejected', 'emit_tournament_judge_hijack_suspected')

# PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — chain_reset_marker
# Registered via kernel-override PLAN-112-FOLLOWUP-WAVE-B3-AUDIT-EMIT-EXTENSION
# at v1.39.4. Per ADR-055-AMEND-2: this is the synthetic genesis entry
# written as line 1 of every rotation-created fresh audit-log.jsonl.
# Verifier marker-enforcement is scoped via audit-log.rotation-manifest.json
# sidecar (NO archive walking — preserves rejected-Path-A boundary).
def emit_chain_reset_marker(
    previous_archive_path: str,
    previous_archive_last_hmac: str,
    rotation_ts: str,
    rotation_trigger: str = "size_threshold",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit chain_reset_marker as the genesis-anchored line 1 of a
    rotation-created fresh audit-log.jsonl.

    Per ADR-055-AMEND-2 (drafted by PLAN-112-FOLLOWUP-hmac-tamper-fix
    at v1.39.4): rotation MUST emit this marker as the first entry of
    the new file, HMAC-anchored at GENESIS_PREV. The marker carries the
    rotated archive's last_hmac as a DATA field (not a chain link), so
    forensic continuity is preserved across rotation without inverting
    the verifier's "log = source of truth" doctrine.

    Caller (`audit_emit._rotate_if_needed_safe` site OR Wave B.2
    quarantine ceremony script) must hold the canonical FileLock and
    write the marker BEFORE releasing the lock, so a concurrent emit
    cannot land a non-marker line 1.

    Args:
      previous_archive_path: relative path of the rotated archive,
        e.g., `audit-log-2026-05-21-pre-fix-tampered.jsonl`
      previous_archive_last_hmac: hex digest of the last HMAC-bearing
        entry of the rotated archive (32-byte HMAC SHA-256 hex-encoded;
        empty string allowed for first-install/no-prior-chain case)
      rotation_ts: ISO-8601 UTC timestamp of the rotation event
      rotation_trigger: one of `size_threshold` | `manual` | `owner_rotation`
        | `quarantine_pre_fix` (the last applies to Wave B.2 ceremony)
    """
    rotation_trigger = _normalize_rotation_trigger(rotation_trigger)
    event: Dict[str, Any] = {
        "action": "chain_reset_marker",
        "previous_archive_path": str(previous_archive_path)[:256],
        "previous_archive_last_hmac": str(previous_archive_last_hmac)[:64],
        "rotation_ts": str(rotation_ts)[:32],
        "rotation_trigger": rotation_trigger,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# =============================================================================
# PLAN-113 Phase B WIRE-AUDIT — typed wrappers for previously-orphan actions.
# Each wrapper follows the Sec MF-3 pattern: explicit field allowlist,
# fail-open (never raises), stdlib-only.
# =============================================================================


def emit_task_route_key_dropped(
    *,
    key: str = "",
    reason_code: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit task_route_key_dropped when AEK drops an unexpected field.

    Emitted by the reality-ledger / task-router when an unknown key
    arrives in a contract payload.  Sec MF-3: only safe, non-content
    fields persist.
    """
    emit_generic(
        "task_route_key_dropped",
        key=str(key)[:64],
        reason_code=str(reason_code)[:32],
        session_id=session_id,
        project=project,
    )


def emit_reality_ledger_key_dropped(
    *,
    key: str = "",
    detector: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit reality_ledger_key_dropped when the reality-ledger strips a field.

    Fired by reality-ledger.py on allowlist-mismatch before persisting
    a finding. Sec MF-3: no raw field value; only key name + detector.
    """
    emit_generic(
        "reality_ledger_key_dropped",
        key=str(key)[:64],
        detector=str(detector)[:64],
        session_id=session_id,
        project=project,
    )


def emit_swarm_finalize_grouped(
    *,
    swarm_id: str = "",
    groups: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit swarm_finalize_grouped when the coordinator groups winner outputs.

    Fired by the swarm coordinator after tournament selection, before
    commit.  Sec MF-3: no raw patch content or file paths.
    """
    emit_generic(
        "swarm_finalize_grouped",
        swarm_id=str(swarm_id)[:64],
        groups=int(groups),
        session_id=session_id,
        project=project,
    )


def emit_swarm_finalize_committed(
    *,
    swarm_id: str = "",
    commit: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit swarm_finalize_committed when the coordinator commits the winner.

    Fired after the winning patch is applied and committed to the branch.
    ``commit`` is a 7-char git SHA-prefix (or empty if pre-commit).
    Sec MF-3: no raw patch content or file paths.
    """
    emit_generic(
        "swarm_finalize_committed",
        swarm_id=str(swarm_id)[:64],
        commit=str(commit)[:16],
        session_id=session_id,
        project=project,
    )


def emit_skill_reference_never_read(
    *,
    skill_path: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit skill_reference_never_read when a pinned SKILL.md is never Read.

    Fired by check_skill_reference_read.py on SubagentStop when a
    skill-reference claim was made at spawn time but the SKILL.md was
    never Read during the sub-agent session.  Sec MF-3: no raw SKILL
    content; only a 12-hex path hash.
    """
    import hashlib as _hashlib
    path_hash = _hashlib.sha256(
        str(skill_path).encode("utf-8", errors="replace")
    ).hexdigest()[:12]
    emit_generic(
        "skill_reference_never_read",
        skill_path_hash=path_hash,
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------------
# Escalation cluster typed wrappers (PLAN-048 Phase 2 / ceo-escalation-
# detector.py). Sec MF-3 enforced: no raw prompt content, no session
# detail text — only signal metadata.
# ---------------------------------------------------------------------------


def emit_escalation_detected(
    *,
    signal: str = "",
    severity: str = "",
    plan_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit escalation_detected when a PLAN-048 escalation signal fires."""
    emit_generic(
        "escalation_detected",
        signal=str(signal)[:64],
        severity=str(severity)[:16],
        plan_id=str(plan_id)[:32],
        session_id=session_id,
        project=project,
    )


def emit_escalation_dispatched(
    *,
    signal: str = "",
    target_model: str = "",
    plan_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit escalation_dispatched when Opus re-dispatch is triggered."""
    emit_generic(
        "escalation_dispatched",
        signal=str(signal)[:64],
        target_model=str(target_model)[:64],
        plan_id=str(plan_id)[:32],
        session_id=session_id,
        project=project,
    )


def emit_escalation_suppressed(
    *,
    signal: str = "",
    reason_code: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit escalation_suppressed when escalation is rate-limited or suppressed."""
    emit_generic(
        "escalation_suppressed",
        signal=str(signal)[:64],
        reason_code=str(reason_code)[:32],
        session_id=session_id,
        project=project,
    )


def emit_escalation_baseline_recorded(
    *,
    signals_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit escalation_baseline_recorded at baseline-observation session end."""
    emit_generic(
        "escalation_baseline_recorded",
        signals_count=int(signals_count),
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------------
# Tournament cluster typed wrappers (PLAN-032 / ADR-063).
# The tournament module (scripts/swarm/tournament.py) calls these after
# scoring + selection. Sec MF-3: no raw patch content.
# ---------------------------------------------------------------------------


def emit_tournament_run_started(
    *,
    swarm_id: str = "",
    candidate_count: int = 0,
    direction: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_run_started at the beginning of a best-of-N run."""
    emit_generic(
        "tournament_run_started",
        swarm_id=str(swarm_id)[:64],
        candidate_count=int(candidate_count),
        direction=str(direction)[:16],
        session_id=session_id,
        project=project,
    )


def emit_tournament_task_scored(
    *,
    swarm_id: str = "",
    loop_id: str = "",
    score_bps: int = 0,
    tests_passed: int = 0,
    tests_failed: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_task_scored when a candidate receives its score.

    ``score_bps`` is integer basis-points (score × 1000) to satisfy
    canonical_json no-floats invariant on HMAC-chained fields.
    """
    emit_generic(
        "tournament_task_scored",
        swarm_id=str(swarm_id)[:64],
        loop_id=str(loop_id)[:64],
        score_bps=int(score_bps),
        tests_passed=int(tests_passed),
        tests_failed=int(tests_failed),
        session_id=session_id,
        project=project,
    )


def emit_tournament_run_completed(
    *,
    swarm_id: str = "",
    winner_loop_id: str = "",
    rejected_count: int = 0,
    decisive: bool = True,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_run_completed after the winner is determined."""
    emit_generic(
        "tournament_run_completed",
        swarm_id=str(swarm_id)[:64],
        winner_loop_id=str(winner_loop_id)[:64],
        rejected_count=int(rejected_count),
        decisive=bool(decisive),
        session_id=session_id,
        project=project,
    )


def emit_tournament_budget_projected(
    *,
    swarm_id: str = "",
    projected_cost_cents: int = 0,
    candidate_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_budget_projected with cost estimate before run."""
    emit_generic(
        "tournament_budget_projected",
        swarm_id=str(swarm_id)[:64],
        projected_cost_cents=int(projected_cost_cents),
        candidate_count=int(candidate_count),
        session_id=session_id,
        project=project,
    )


def emit_tournament_budget_exceeded(
    *,
    swarm_id: str = "",
    actual_cost_cents: int = 0,
    cap_cents: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_budget_exceeded when cost cap is breached."""
    emit_generic(
        "tournament_budget_exceeded",
        swarm_id=str(swarm_id)[:64],
        actual_cost_cents=int(actual_cost_cents),
        cap_cents=int(cap_cents),
        session_id=session_id,
        project=project,
    )


def emit_tournament_aborted(
    *,
    swarm_id: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_aborted when the tournament cannot complete."""
    emit_generic(
        "tournament_aborted",
        swarm_id=str(swarm_id)[:64],
        reason=str(reason)[:64],
        session_id=session_id,
        project=project,
    )


def emit_tournament_fixture_rejected(
    *,
    swarm_id: str = "",
    loop_id: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_fixture_rejected when a candidate fixture is invalid."""
    emit_generic(
        "tournament_fixture_rejected",
        swarm_id=str(swarm_id)[:64],
        loop_id=str(loop_id)[:64],
        reason=str(reason)[:64],
        session_id=session_id,
        project=project,
    )


def emit_tournament_judge_hijack_suspected(
    *,
    swarm_id: str = "",
    loop_id: str = "",
    indicator: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tournament_judge_hijack_suspected on adversarial judge indicators."""
    emit_generic(
        "tournament_judge_hijack_suspected",
        swarm_id=str(swarm_id)[:64],
        loop_id=str(loop_id)[:64],
        indicator=str(indicator)[:64],
        session_id=session_id,
        project=project,
    )
