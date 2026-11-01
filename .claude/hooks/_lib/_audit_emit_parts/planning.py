"""Planning.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_rag_profile_recommended', 'emit_rag_auto_wire_skipped_sidecar_down', 'emit_rag_query_routed', 'emit_rag_false_large_demoted', 'emit_rag_hit_rate_degraded', 'emit_goap_edge_explored', 'emit_goap_search_aborted', 'emit_goap_search_summary', 'emit_goap_cycle_detected', 'emit_goap_depth_exceeded', 'emit_goap_replan_triggered', 'emit_goap_replan_exhausted', 'emit_goap_disabled_by_env', 'emit_goap_recommendation_accepted', 'emit_goap_recommendation_rendered', 'emit_goap_recommendation_overridden', 'emit_mcp_server_started', 'emit_mcp_server_disabled_by_kill_switch')

def emit_rag_profile_recommended(
    profile: str,
    decision: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a rag_profile_recommended event (PLAN-097 Wave C.5 / ADR-128 §6).

    Fires once per session at routing-decision time. `profile` is one of
    SMALL/MEDIUM/LARGE; `decision` is one of auto-wire/skip/kill-switched.
    """
    event: Dict[str, Any] = {
        "action": "rag_profile_recommended",
        "profile": str(profile),
        "decision": str(decision),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_rag_auto_wire_skipped_sidecar_down(
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a rag_auto_wire_skipped_sidecar_down event (PLAN-097 Wave C.5).

    Fires when profile=LARGE but the sidecar socket is missing OR the
    health probe fails OR kill-switch flips routing off.
    """
    event: Dict[str, Any] = {
        "action": "rag_auto_wire_skipped_sidecar_down",
        "reason": str(reason),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_rag_query_routed(
    query_class: str,
    result: str,
    latency_ms_p50: Optional[int] = None,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a rag_query_routed event per routed query (ADR-128 §6).

    Sec MF-3 caller-field whitelist: query_class / result / latency_ms_p50.
    """
    event: Dict[str, Any] = {
        "action": "rag_query_routed",
        "query_class": str(query_class),
        "result": str(result),
        "latency_ms_p50": None if latency_ms_p50 is None else int(latency_ms_p50),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_rag_false_large_demoted(
    false_large_rate_x100: int,
    window_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a rag_false_large_demoted event (PLAN-097 AC10).

    Fires when 7-day-sustained false-LARGE classification rate exceeds
    1% (100 basis points).
    """
    event: Dict[str, Any] = {
        "action": "rag_false_large_demoted",
        "false_large_rate_x100": int(false_large_rate_x100),
        "window_days": int(window_days),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_rag_hit_rate_degraded(
    hit_rate_x100: int,
    window_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a rag_hit_rate_degraded event (PLAN-097 AC11).

    Fires when 7-day-sustained hit-rate on golden-query corpus falls
    below 60% (6000 basis points).
    """
    event: Dict[str, Any] = {
        "action": "rag_hit_rate_degraded",
        "hit_rate_x100": int(hit_rate_x100),
        "window_days": int(window_days),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_edge_explored(
    from_state_hash: str,
    action_id: str,
    cost: int,
    frontier_size: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_edge_explored event (PLAN-098 AC2)."""
    event: Dict[str, Any] = {
        "action": "goap_edge_explored",
        "from_state_hash": str(from_state_hash)[:16],
        "action_id": str(action_id)[:64],
        "cost": int(cost),
        "frontier_size": int(frontier_size),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_search_aborted(
    reason: str,
    explored: int,
    elapsed_ms: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_search_aborted event (PLAN-098 §6.R-state-space-explosion)."""
    event: Dict[str, Any] = {
        "action": "goap_search_aborted",
        "reason": str(reason)[:64],
        "explored": int(explored),
        "elapsed_ms": int(elapsed_ms),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_search_summary(
    explored: int,
    cycles_rejected: int,
    terminus: str,
    elapsed_ms: int,
    plan_depth: Optional[int] = None,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_search_summary event (PLAN-098 AC2 terminus aggregate)."""
    event: Dict[str, Any] = {
        "action": "goap_search_summary",
        "explored": int(explored),
        "cycles_rejected": int(cycles_rejected),
        "terminus": str(terminus)[:32],
        "elapsed_ms": int(elapsed_ms),
        "plan_depth": None if plan_depth is None else int(plan_depth),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_cycle_detected(
    state_hash: str,
    explored: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_cycle_detected event (PLAN-098 AC12)."""
    event: Dict[str, Any] = {
        "action": "goap_cycle_detected",
        "state_hash": str(state_hash)[:16],
        "explored": int(explored),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_depth_exceeded(
    state_hash: str,
    depth: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_depth_exceeded event (PLAN-098 §3.A.4)."""
    event: Dict[str, Any] = {
        "action": "goap_depth_exceeded",
        "state_hash": str(state_hash)[:16],
        "depth": int(depth),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_replan_triggered(
    attempt: int,
    state_hash: str,
    session_id: str = "",
    project: str = "",
    plan_id: Optional[str] = None,  # PLAN-105 Wave A.4 — per-plan denominator
) -> None:
    """Emit a goap_replan_triggered event (PLAN-098 AC7; PLAN-105 A.4 plan_id).

    PLAN-105 Wave A.4: optional `plan_id` (Sec MF-3 sanitized, trunc 32).
    When omitted, schema byte-identical to v1.31.0.
    """
    event: Dict[str, Any] = {
        "action": "goap_replan_triggered",
        "attempt": int(attempt),
        "state_hash": str(state_hash)[:16],
        "session_id": session_id,
        "project": project,
    }
    if plan_id is not None:
        event["plan_id"] = str(plan_id)[:32]
    _write_event(event)


def emit_goap_replan_exhausted(
    attempt: int,
    session_id: str = "",
    project: str = "",
    plan_id: Optional[str] = None,  # PLAN-105 Wave A.4 — per-plan denominator
) -> None:
    """Emit a goap_replan_exhausted event (PLAN-098 AC7; PLAN-105 A.4 plan_id).

    PLAN-105 Wave A.4: optional `plan_id` (Sec MF-3 sanitized, trunc 32).
    When omitted, schema byte-identical to v1.31.0.
    """
    event: Dict[str, Any] = {
        "action": "goap_replan_exhausted",
        "attempt": int(attempt),
        "session_id": session_id,
        "project": project,
    }
    if plan_id is not None:
        event["plan_id"] = str(plan_id)[:32]
    _write_event(event)


def emit_goap_disabled_by_env(
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_disabled_by_env event (PLAN-098 AC10 kill-switch)."""
    event: Dict[str, Any] = {
        "action": "goap_disabled_by_env",
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_recommendation_accepted(
    plan_id: str,
    action_id: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_recommendation_accepted event (PLAN-098 AC9 promotion gate)."""
    event: Dict[str, Any] = {
        "action": "goap_recommendation_accepted",
        "plan_id": str(plan_id)[:32],
        "action_id": str(action_id)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_recommendation_rendered(
    plan_id: str,
    action_ids_csv: str,
    actions_rendered_count: int,
    goal_verb: str,
    goal_text_hash: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_recommendation_rendered event (PLAN-105 Wave A.1).

    Fires when /goap renders an action tree successfully. Goal text body
    is NEVER persisted — only the hash. action_ids_csv is the comma-
    separated list of canonical action_ids from the tree (LLM06 holds:
    fixed vocabulary from action-cost-baseline.json, NOT user content).
    """
    event: Dict[str, Any] = {
        "action": "goap_recommendation_rendered",
        "plan_id": str(plan_id)[:32],
        "action_ids_csv": str(action_ids_csv)[:1600],
        "actions_rendered_count": int(actions_rendered_count),
        "goal_verb": str(goal_verb)[:32],
        "goal_text_hash": str(goal_text_hash)[:12],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_goap_recommendation_overridden(
    plan_id: str,
    original_action_id: str,
    dispatched_action_id: str,
    override_type: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a goap_recommendation_overridden event (PLAN-105 Wave A.2).

    Fires when a GOAP-tagged spawn dispatches an action that does not
    match the most-recent rendered action set. override_type enum:
    substituted_action / no_render_prior / marker_absent.
    """
    event: Dict[str, Any] = {
        "action": "goap_recommendation_overridden",
        "plan_id": str(plan_id)[:32],
        "original_action_id": str(original_action_id)[:64],
        "dispatched_action_id": str(dispatched_action_id)[:64],
        "override_type": str(override_type)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_server_started(
    transport: str,
    host: str = "",
    port: int = 0,
    version: str = "",
    handlers_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_server_started event (ADR-042 §Auth + observability).

    Fired once on server entry AFTER CEO_SOTA_DISABLE kill-switch check
    passes. ``host`` is loopback-or-explicit (no wildcard in default
    config). ``port=0`` for stdio transport. ``version`` is the server
    semver (not the framework VERSION).
    """
    event: Dict[str, Any] = {
        "action": "mcp_server_started",
        "transport": transport,
        "host": host,
        "port": int(port),
        "version": version,
        "handlers_count": int(handlers_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_server_disabled_by_kill_switch(
    reason: str = "CEO_SOTA_DISABLE=1",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_server_disabled_by_kill_switch event (ADR-042 §Cost.4).

    Fired before binding port / opening stdio when CEO_SOTA_DISABLE=1
    short-circuits server entry. Mirrors ADR-040 §6 activation gate.
    """
    event: Dict[str, Any] = {
        "action": "mcp_server_disabled_by_kill_switch",
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
