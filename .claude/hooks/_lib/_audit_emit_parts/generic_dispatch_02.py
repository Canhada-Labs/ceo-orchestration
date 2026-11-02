"""One bounded segment of audit_emit generic action normalization."""

from __future__ import annotations

__all__ = ("_apply_generic_group_02",)


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _apply_generic_group_02(action, state):
    event = state["event"]
    kwargs = state["kwargs"]
    if action == "mcp_canonical_guard_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "task_route_advised":
        event, dropped = _scrub_ceo_boot_event(event, _TASK_ROUTE_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_advised dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
            try:
                emit_task_route_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    reason_code="allowlist_strip",
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:
                pass
        state["event"] = event
        return True

    if action == "task_route_ground_truth_label":
        event, dropped = _scrub_ceo_boot_event(
            event, _TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_ground_truth_label dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "cost_envelope_capped":
        event, dropped = _scrub_ceo_boot_event(event, _COST_ENVELOPE_CAPPED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic cost_envelope_capped dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "swarm_runaway_suspected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_RUNAWAY_SUSPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_runaway_suspected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "swarm_paused_owner_absent":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST
        )
        if (
            "loop_duration_hours" in event
            and event.get("loop_duration_hours") is not None
        ):
            try:
                event["loop_duration_hours"] = max(
                    1, min(int(round(float(event.get("loop_duration_hours")))), 100000)
                )
            except (TypeError, ValueError, OverflowError):
                event["loop_duration_hours"] = 1
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_paused_owner_absent dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "swarm_layer_3_4_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_LAYER_3_4_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_layer_3_4_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "execution_context_signed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_SIGNED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_signed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "execution_context_validation_failed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_validation_failed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "reality_ledger_finding":
        event, dropped = _scrub_ceo_boot_event(event, _REALITY_LEDGER_FINDING_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic reality_ledger_finding dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
            try:
                emit_reality_ledger_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    detector=str(event.get("detector", "")),
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:
                pass
        state["event"] = event
        return True

    if action == "model_routing_advised":
        event, dropped = _scrub_ceo_boot_event(event, _MODEL_ROUTING_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_advised dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "model_routing_enforced":
        event, dropped = _scrub_ceo_boot_event(event, _MODEL_ROUTING_ENFORCED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_enforced dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "model_routing_eval_error":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_EVAL_ERROR_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_eval_error dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "estimate_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "estimate_drift_systematic_bias":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_systematic_bias dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ceo_boot_task_candidate_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_task_candidate_emitted dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "pair_rail_codex_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_codex_injection_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "dispatcher_route":
        event, dropped = _scrub_ceo_boot_event(event, _DISPATCHER_ROUTE_EMIT_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic dispatcher_route dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "pair_rail_case":
        _prc_rid = event.get("review_id")
        if not (
            isinstance(_prc_rid, str) and _PAIR_RAIL_REVIEW_ID_RE.fullmatch(_prc_rid)
        ):
            event["review_id"] = ""
        if "timeout_ms" in event:
            event["timeout_ms"] = _coerce_pair_rail_timeout_ms(event["timeout_ms"])
        event, dropped = _scrub_ceo_boot_event(event, _PAIR_RAIL_CASE_EMIT_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_case dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "pair_rail_promotion":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_promotion dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "token_budget_guard_paused":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic token_budget_guard_paused dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "anti_ceo_overhead_block":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_block dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "anti_ceo_overhead_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_override_used dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "smart_loading_resolved":
        event, dropped = _scrub_ceo_boot_event(event, _SMART_LOADING_RESOLVED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic smart_loading_resolved dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "first_run_wizard_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_completed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "contextual_recommendation_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic contextual_recommendation_emitted dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "value_dashboard_summarized":
        event, dropped = _scrub_ceo_boot_event(
            event, _VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic value_dashboard_summarized dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "live_adapter_blocked":
        event, dropped = _scrub_ceo_boot_event(event, _LIVE_ADAPTER_BLOCKED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic live_adapter_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "prompt_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PROMPT_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic prompt_injection_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "mcp_injection_finding":
        if "snippet_preview" in event:
            event["snippet_preview"] = _preview(
                str(event.get("snippet_preview", "")), max_len=120
            )
        event, dropped = _scrub_ceo_boot_event(event, _MCP_INJECTION_FINDING_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_injection_finding dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "secret_leak_detected":
        event, dropped = _scrub_ceo_boot_event(event, _SECRET_LEAK_DETECTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic secret_leak_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "pii_redacted_outgoing":
        event, dropped = _scrub_ceo_boot_event(event, _PII_REDACTED_OUTGOING_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic pii_redacted_outgoing dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "codex_egress_redacted":
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_EGRESS_REDACTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic codex_egress_redacted dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "pair_rail_outgoing_redaction_applied":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_outgoing_redaction_applied dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "canonical_edit_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CANONICAL_EDIT_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic canonical_edit_completed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "credential_blocked_due_to_age":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic credential_blocked_due_to_age dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "credential_emergency_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic credential_emergency_override_used dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "credential_override_late_set_ignored":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST
        )
        event["attempted_var_name"] = _CREDENTIAL_OVERRIDE_VAR_NAME
        if event.get("provenance_hint") not in _CREDENTIAL_OVERRIDE_PROVENANCE_HINTS:
            event["provenance_hint"] = "unspecified"
        if dropped:
            _breadcrumb(
                f"emit_generic credential_override_late_set_ignored dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "mcp_bearer_replay_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_BEARER_REPLAY_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_bearer_replay_rejected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "mcp_non_loopback_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_NON_LOOPBACK_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_non_loopback_rejected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "trading_write_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_WRITE_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_write_override_used dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "trading_kill_switch_invoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_INVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_invoked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "trading_kill_switch_disabled":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_DISABLED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_disabled dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "cache_discipline_alerted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CACHE_DISCIPLINE_ALERTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic cache_discipline_alerted dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "first_run_wizard_dispatched":
        event, dropped = _scrub_ceo_boot_event(
            event, _FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_dispatched dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True
    return False
