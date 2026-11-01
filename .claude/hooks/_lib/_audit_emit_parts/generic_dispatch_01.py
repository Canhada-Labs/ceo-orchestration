"""One bounded segment of audit_emit generic action normalization."""

from __future__ import annotations

__all__ = ("_apply_generic_group_01",)


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _apply_generic_group_01(action, state):
    event = state["event"]
    kwargs = state["kwargs"]
    if action == "ceo_boot_emitted":
        event, dropped = _scrub_ceo_boot_event(event, _CEO_BOOT_EMITTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_emitted dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ceo_boot_check_skipped":
        event, dropped = _scrub_ceo_boot_event(event, _CEO_BOOT_CHECK_SKIPPED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_check_skipped dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "optimizer_route_recommended":
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["optimizer_route_recommended"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic optimizer_route_recommended dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "fanout_recommended":
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["fanout_recommended"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic fanout_recommended dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "model_choice_recommended":
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["model_choice_recommended"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic model_choice_recommended dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "eval_task_completed":
        event, dropped = _scrub_ceo_boot_event(event, _EVAL_TASK_COMPLETED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic eval_task_completed dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "rag_context_recommended":
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["rag_context_recommended"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic rag_context_recommended dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "codex_review_disabled":
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["codex_review_disabled"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic codex_review_disabled dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "codex_review_invoked":
        if (
            "review_status" in event
            and event.get("review_status") not in _CODEX_REVIEW_STATUS_ENUM
        ):
            event["review_status"] = "other"
        if (
            "review_source" in event
            and event.get("review_source") not in _CODEX_REVIEW_SOURCE_ENUM
        ):
            event["review_source"] = "other"
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _safe_target_ref_hash_field(
                event.get("target_ref_hash")
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _OPTIMIZER_ALLOWLISTS["codex_review_invoked"]
        )
        if dropped:
            _breadcrumb(
                "emit_generic codex_review_invoked dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "verify_after_edit_finding":
        if event.get("checker") not in _VERIFY_CHECKER_ENUM:
            event["checker"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["finding_count"] = _accel_clamp_count(event.get("finding_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _VERIFY_AFTER_EDIT_FINDING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic verify_after_edit_finding dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "adequacy_gate_flag":
        if event.get("flag_reason") not in _ADEQUACY_REASON_ENUM:
            event["flag_reason"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["flag_count"] = _accel_clamp_count(event.get("flag_count"))
        event, dropped = _scrub_ceo_boot_event(event, _ADEQUACY_GATE_FLAG_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic adequacy_gate_flag dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "quota_exhausted":
        if event.get("error_class") not in _QUOTA_ERROR_CLASS_ENUM:
            event["error_class"] = "unknown"
        if event.get("source") not in _QUOTA_ERROR_SOURCE_ENUM:
            event["source"] = "unknown"
        _hs = event.get("http_status")
        if not isinstance(_hs, int) or isinstance(_hs, bool) or _hs < 0 or (_hs > 599):
            event.pop("http_status", None)
        event["attempt"] = _accel_clamp_count(event.get("attempt"))
        event, dropped = _scrub_ceo_boot_event(event, _QUOTA_EXHAUSTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic quota_exhausted dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "context_auto_compacted":
        if event.get("reason") not in _AUTO_COMPACT_REASON_ENUM:
            event["reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(
                event.get("turns_since_last")
            )
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_AUTO_COMPACTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic context_auto_compacted dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "context_auto_compact_suppressed":
        if event.get("suppress_reason") not in _AUTO_COMPACT_SUPPRESS_REASON_ENUM:
            event["suppress_reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(
                event.get("turns_since_last")
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic context_auto_compact_suppressed dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "context_middle_out_degraded":
        if event.get("reason") not in _MIDDLE_OUT_REASON_ENUM:
            event["reason"] = "other"
        event["rung"] = _accel_clamp_count(event.get("rung"))
        event["degraded_count"] = _accel_clamp_count(event.get("degraded_count"))
        if "total_count" in event:
            event["total_count"] = _accel_clamp_count(event.get("total_count"))
        if "protect_last" in event:
            event["protect_last"] = _accel_clamp_count(event.get("protect_last"))
        if "reclaim_bucket" in event:
            event["reclaim_bucket"] = _accel_clamp_count(event.get("reclaim_bucket"))
        if "fits_after" in event:
            event["fits_after"] = bool(event.get("fits_after"))
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic context_middle_out_degraded dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "context_middle_out_degrade_failed":
        if event.get("reason") not in _MIDDLE_OUT_REASON_ENUM:
            event["reason"] = "other"
        event["rung"] = _accel_clamp_count(event.get("rung"))
        if "degraded_count" in event:
            event["degraded_count"] = _accel_clamp_count(event.get("degraded_count"))
        if "total_count" in event:
            event["total_count"] = _accel_clamp_count(event.get("total_count"))
        if "protect_last" in event:
            event["protect_last"] = _accel_clamp_count(event.get("protect_last"))
        if "reclaim_bucket" in event:
            event["reclaim_bucket"] = _accel_clamp_count(event.get("reclaim_bucket"))
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic context_middle_out_degrade_failed dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "supply_chain_advisory_emitted":
        if event.get("verdict") not in _SUPPLY_CHAIN_VERDICT_ENUM:
            event["verdict"] = "ALLOW"
        if event.get("reason") not in _SUPPLY_CHAIN_REASON_ENUM:
            event["reason"] = "unknown"
        if event.get("ecosystem") not in _SUPPLY_CHAIN_ECOSYSTEM_ENUM:
            event["ecosystem"] = "other"
        pkg = str(event.get("package", ""))
        event["package"] = "".join((c for c in pkg if c.isprintable()))[:128]
        event["advisory_count"] = _accel_clamp_count(event.get("advisory_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic supply_chain_advisory_emitted dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "spawn_tool_scope_violation":
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        _d = str(event.get("detail") or "")[:96]
        if "/" in _d or "\\" in _d:
            _d = ""
        event["detail"] = _d
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic spawn_tool_scope_violation dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "spawn_depth_or_overlap_blocked":
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        event["count"] = _accel_clamp_count(event.get("count"))
        event, dropped = _scrub_ceo_boot_event(event, _SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic spawn_depth_or_overlap_blocked dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "spawn_file_assignment_recorded":
        event["path_hashes"] = _e3_safe_path_hashes(event.get("path_hashes"))
        event["path_count"] = _accel_clamp_count(event.get("path_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic spawn_file_assignment_recorded dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "action_required_held":
        if event.get("kind") not in _ACTION_REQUIRED_KIND_ENUM:
            event["kind"] = "other"
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        if "expires_at" in event:
            try:
                event["expires_at"] = int(event.get("expires_at"))
            except (TypeError, ValueError):
                event["expires_at"] = 0
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_HELD_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic action_required_held dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "action_required_resumed":
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(
            event, _ACTION_REQUIRED_RESUMED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic action_required_resumed dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "action_required_rejected":
        if event.get("reject_reason") not in _ACTION_REQUIRED_REJECT_ENUM:
            event["reject_reason"] = "other"
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(
            event, _ACTION_REQUIRED_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic action_required_rejected dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "ceo_boot_persona_coverage_score":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_persona_coverage_score dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persona_demand_opened":
        event, dropped = _scrub_ceo_boot_event(event, _PERSONA_DEMAND_OPENED_ALLOWLIST)
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_opened dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persona_demand_matched":
        if (
            "match_modality" in event
            and event.get("match_modality") not in _PERSONA_MATCH_MODALITY_ENUM
        ):
            event["match_modality"] = "native_spawn"
        event, dropped = _scrub_ceo_boot_event(event, _PERSONA_DEMAND_MATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_matched dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persona_demand_unmet":
        event, dropped = _scrub_ceo_boot_event(event, _PERSONA_DEMAND_UNMET_ALLOWLIST)
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_unmet dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persona_demand_waived":
        event, dropped = _scrub_ceo_boot_event(event, _PERSONA_DEMAND_WAIVED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_waived dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persona_coverage_synthesized":
        archetype = str(event.get("archetype", ""))
        task_type = str(event.get("task_type", ""))
        source = str(event.get("source", ""))
        if archetype not in _PERSONA_COVERAGE_ARCHETYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: archetype {archetype!r} not in closed enum"
            )
            return
        if task_type not in _PERSONA_COVERAGE_TASK_TYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: task_type {task_type!r} not in closed enum"
            )
            return
        if source not in _PERSONA_COVERAGE_SOURCES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: source {source!r} not in closed enum"
            )
            return
        cell_id = str(event.get("cell_id", ""))[:8]
        if cell_id and (not all((c in "0123456789abcdef" for c in cell_id))):
            cell_id = ""
        event["cell_id"] = cell_id
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "claim_emitted":
        event, dropped = _scrub_ceo_boot_event(event, _CLAIM_EMITTED_ALLOWLIST)
        if "claim_id" in event:
            event["claim_id"] = _safe_claim_id_hash(event.get("claim_id", ""))
        if "payload_hash" in event:
            event["payload_hash"] = _safe_payload_hash(event.get("payload_hash", ""))
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(f"emit_generic claim_emitted dropped: {sorted(dropped)[:10]}")
        state["event"] = event
        return True

    if action == "confidence_gate_verdict":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_VERDICT_ALLOWLIST
        )
        if "claim_id" in event:
            event["claim_id"] = _safe_claim_id_hash(event.get("claim_id", ""))
        if "verdict" in event:
            v = str(event["verdict"])[:16].lower()
            event["verdict"] = v if v in _CONFIDENCE_GATE_VERDICTS else "fail"
        if "verifier_outcome" in event:
            event["verifier_outcome"] = _safe_verifier_outcome(
                event["verifier_outcome"], ""
            )
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_verdict dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "confidence_gate_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_BLOCKED_ALLOWLIST
        )
        raw_blocking = event.get("blocking_classes")
        if isinstance(raw_blocking, (list, tuple)):
            event["blocking_classes"] = [
                str(c)[:64] for c in raw_blocking if isinstance(c, str)
            ]
        else:
            event["blocking_classes"] = []
        if "fail_count" in event:
            try:
                event["fail_count"] = int(event["fail_count"])
            except (TypeError, ValueError):
                event["fail_count"] = 0
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_blocked dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "confidence_gate_fp_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST
        )
        for f in ("window_days", "fpr_bps", "threshold_bps", "sample_n"):
            if f in event:
                try:
                    event[f] = int(event[f])
                except (TypeError, ValueError):
                    event[f] = 0
        if "drift_class" in event:
            event["drift_class"] = str(event["drift_class"])[:64]
        if "auto_demote_at" in event:
            event["auto_demote_at"] = str(event["auto_demote_at"])[:32]
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_fp_drift_detected dropped: {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "mcp_canonical_guard_allowed":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_allowed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True
    return False
