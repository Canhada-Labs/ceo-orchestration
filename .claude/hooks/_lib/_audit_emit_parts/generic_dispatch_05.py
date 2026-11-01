"""One bounded segment of audit_emit generic action normalization."""

from __future__ import annotations

__all__ = ("_apply_generic_group_05", "_dispatch_generic")


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _apply_generic_group_05(action, state):
    event = state["event"]
    kwargs = state["kwargs"]
    if action == "lesson_approved":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_APPROVED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["trigger"] = _learning_token_field(event.get("trigger"))
        event["content_sha256"] = _learning_sha256_field(event.get("content_sha256"))
        event["scope_tags"] = _learning_scope_tags_field(event.get("scope_tags"))
        if dropped:
            _breadcrumb(
                "emit_generic lesson_approved dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_quarantined":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_QUARANTINED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if event.get("reason") not in _LESSON_QUARANTINE_REASON_ENUM:
            event["reason"] = "injection_pattern"
        if event.get("prior_status") != "PENDING":
            event["prior_status"] = "PENDING"
        if dropped:
            _breadcrumb(
                "emit_generic lesson_quarantined dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_expired":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_EXPIRED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["age_days"] = _learning_int_field(event.get("age_days"), 100000)
        if event.get("created_at_source") not in _LESSON_CREATED_AT_SOURCE_ENUM:
            event["created_at_source"] = "file"
        if dropped:
            _breadcrumb(
                "emit_generic lesson_expired dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_integrity_flag":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_INTEGRITY_FLAG_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if event.get("check") not in _LESSON_INTEGRITY_CHECK_ENUM:
            event["check"] = "hash_unverifiable"
        if event.get("consumer") not in _LESSON_INTEGRITY_CONSUMER_ENUM:
            event["consumer"] = "boot"
        if dropped:
            _breadcrumb(
                "emit_generic lesson_integrity_flag dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_boot_render_dropped":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_BOOT_RENDER_DROPPED_ALLOWLIST
        )
        if event.get("reason") not in _LESSON_BOOT_DROP_REASON_ENUM:
            event["reason"] = "other"
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if dropped:
            _breadcrumb(
                "emit_generic lesson_boot_render_dropped dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "learning_rail_disabled":
        event, dropped = _scrub_ceo_boot_event(event, _LEARNING_RAIL_DISABLED_ALLOWLIST)
        if event.get("rail") not in _LEARNING_RAIL_ENUM:
            event["rail"] = "observe"
        if event.get("switch") not in _LEARNING_SWITCH_ENUM:
            event["switch"] = "other"
        if "hook" in event:
            event["hook"] = _learning_token_field(event.get("hook"))
        if dropped:
            _breadcrumb(
                "emit_generic learning_rail_disabled dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "fact_gate_activation_changed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FACT_GATE_ACTIVATION_CHANGED_ALLOWLIST
        )
        event["enabled"] = bool(event.get("enabled"))
        if event.get("source") not in _FACT_GATE_SOURCE_ENUM:
            event["source"] = "default_advisory"
        if "hook" in event:
            event["hook"] = _learning_token_field(event.get("hook"))
        if dropped:
            _breadcrumb(
                "emit_generic fact_gate_activation_changed dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "advisory_dampened":
        event, dropped = _scrub_ceo_boot_event(event, _ADVISORY_DAMPENED_ALLOWLIST)
        event["advisory_id"] = _learning_token_field(event.get("advisory_id"))
        event["ordinal"] = _learning_int_field(event.get("ordinal"), 1000000)
        if event.get("channel") not in _ADVISORY_DAMPEN_CHANNEL_ENUM:
            event["channel"] = "stderr_prose"
        if dropped:
            _breadcrumb(
                "emit_generic advisory_dampened dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "distiller_run_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _DISTILLER_RUN_COMPLETED_ALLOWLIST
        )
        if event.get("outcome") not in _DISTILLER_OUTCOME_ENUM:
            event["outcome"] = "model_error"
        event["model_id"] = _learning_token_field(event.get("model_id"))
        event["fixture_mode"] = bool(event.get("fixture_mode"))
        event["cursor_advanced"] = bool(event.get("cursor_advanced"))
        for _cnt in (
            "events_consumed",
            "observations_rejected",
            "candidates_proposed",
            "candidates_written",
            "candidates_quarantined",
            "rejected_pre_candidate",
            "tokens_in",
            "tokens_out",
        ):
            event[_cnt] = _learning_int_field(event.get(_cnt))
        if dropped:
            _breadcrumb(
                "emit_generic distiller_run_completed dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_evolve_run":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_EVOLVE_RUN_ALLOWLIST)
        event["dry_run"] = bool(event.get("dry_run"))
        for _cnt in (
            "lessons_scanned",
            "clusters_found",
            "clusters_resolved",
            "proposals_written",
            "proposals_failed",
        ):
            event[_cnt] = _learning_int_field(event.get(_cnt))
        if dropped:
            _breadcrumb(
                "emit_generic lesson_evolve_run dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "codex_tool_recorded":
        if event.get("harness") not in _CODEX_HARNESS_ENUM:
            event["harness"] = "codex"
        if event.get("tool_name_enum") not in _CODEX_TOOL_RECORDED_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("hook_event_name") not in _CODEX_TOOL_RECORDED_EVENT_ENUM:
            event["hook_event_name"] = "PostToolUse"
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_TOOL_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic codex_tool_recorded dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "codex_turn_ended":
        if event.get("harness") not in _CODEX_HARNESS_ENUM:
            event["harness"] = "codex"
        if event.get("source") not in _CODEX_TURN_ENDED_SOURCE_ENUM:
            event["source"] = "other"
        event["stop_hook_active"] = bool(event.get("stop_hook_active"))
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_TURN_ENDED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic codex_turn_ended dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "grok_tool_recorded":
        if event.get("harness") not in _GROK_HARNESS_ENUM:
            event["harness"] = "grok"
        if event.get("tool_name_enum") not in _GROK_TOOL_RECORDED_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("hook_event_name") not in _GROK_TOOL_RECORDED_EVENT_ENUM:
            event["hook_event_name"] = "PostToolUse"
        event, dropped = _scrub_ceo_boot_event(event, _GROK_TOOL_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic grok_tool_recorded dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "grok_turn_ended":
        if event.get("harness") not in _GROK_HARNESS_ENUM:
            event["harness"] = "grok"
        if event.get("source") not in _GROK_TURN_ENDED_SOURCE_ENUM:
            event["source"] = "other"
        event, dropped = _scrub_ceo_boot_event(event, _GROK_TURN_ENDED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic grok_turn_ended dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "council_lane_invoked":
        if event.get("vendor") not in _COUNCIL_VENDOR_ENUM:
            event["vendor"] = "other"
        if event.get("lane_status") not in _COUNCIL_LANE_STATUS_ENUM:
            event["lane_status"] = "other"
        event, dropped = _scrub_ceo_boot_event(event, _COUNCIL_LANE_INVOKED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic council_lane_invoked dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "codex_review_verdict":
        if event.get("outcome") not in _CODEX_REVIEW_VERDICT_OUTCOME_ENUM:
            event["outcome"] = "skipped_failopen"
        _crv_sha = event.get("diff_sha256")
        if not (
            isinstance(_crv_sha, str)
            and _CODEX_REVIEW_DIFF_SHA256_RE.fullmatch(_crv_sha)
        ):
            event["diff_sha256"] = ""
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_REVIEW_VERDICT_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic codex_review_verdict dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "pair_rail_review_expected":
        if event.get("tool_name") not in _PAIR_RAIL_REVIEW_EXPECTED_TOOL_ENUM:
            event["tool_name"] = "unknown"
        _pre_prefix = event.get("file_path_hash_prefix")
        if not (
            isinstance(_pre_prefix, str)
            and _PAIR_RAIL_FILE_HASH_PREFIX_RE.fullmatch(_pre_prefix)
        ):
            event["file_path_hash_prefix"] = ""
        _pre_rid = event.get("review_id")
        if not (
            isinstance(_pre_rid, str) and _PAIR_RAIL_REVIEW_ID_RE.fullmatch(_pre_rid)
        ):
            event["review_id"] = ""
        if "timeout_ms" in event:
            event["timeout_ms"] = _coerce_pair_rail_timeout_ms(event["timeout_ms"])
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic pair_rail_review_expected dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "directory_added_recorded":
        _dar_src = event.get("source")
        if (
            not isinstance(_dar_src, str)
            or _dar_src not in _DIRECTORY_ADDED_SOURCE_ENUM
        ):
            event["source"] = "other"
        _dar_prefix = event.get("directory_hash_prefix")
        if not (
            isinstance(_dar_prefix, str)
            and _DIRECTORY_ADDED_HASH_PREFIX_RE.fullmatch(_dar_prefix)
        ):
            event["directory_hash_prefix"] = ""
        event, dropped = _scrub_ceo_boot_event(
            event, _DIRECTORY_ADDED_RECORDED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic directory_added_recorded dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "notification_lifecycle":
        _nl_type = event.get("notification_type")
        if not isinstance(_nl_type, str) or _nl_type not in _NOTIFICATION_TYPE_ENUM:
            event["notification_type"] = "other"
        event["has_title"] = bool(event.get("has_title"))
        _nl_prefix = event.get("message_sha256_prefix")
        if not (
            isinstance(_nl_prefix, str)
            and _NOTIFICATION_MSG_SHA256_PREFIX_RE.fullmatch(_nl_prefix)
        ):
            event["message_sha256_prefix"] = ""
        event, dropped = _scrub_ceo_boot_event(event, _NOTIFICATION_LIFECYCLE_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic notification_lifecycle dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "night_mode_toggled":
        _nm_mode = event.get("mode")
        if not isinstance(_nm_mode, str) or _nm_mode not in _NIGHT_MODE_MODE_ENUM:
            event["mode"] = "other"
        _nm_prev = event.get("previous_mode")
        if not isinstance(_nm_prev, str) or _nm_prev not in _NIGHT_MODE_MODE_ENUM:
            event["previous_mode"] = "other"
        _nm_result = event.get("result")
        if not isinstance(_nm_result, str) or _nm_result not in _NIGHT_MODE_RESULT_ENUM:
            event["result"] = "other"
        _nm_hh = event.get("hostname_hash")
        if not (
            isinstance(_nm_hh, str) and _NIGHT_MODE_HOSTNAME_HASH_RE.fullmatch(_nm_hh)
        ):
            event["hostname_hash"] = ""
        event, dropped = _scrub_ceo_boot_event(event, _NIGHT_MODE_TOGGLED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic night_mode_toggled dropped: %s" % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action in _EMIT_GENERIC_PASSTHROUGH:
        pass
        state["event"] = event
        return True
    return False


# QDSAA-FUNCAO-LONGA: centraliza a ordem original de scrub/default-deny e mantém
# todos os handlers ligados ao namespace da fachada para monkeypatch em tempo real.
def _dispatch_generic(action, kwargs):
    if action not in _KNOWN_ACTIONS:
        _breadcrumb("unknown audit action dropped: %s" % action)
        return
    event = {"action": action}
    event.update(kwargs)
    state = {"event": event, "kwargs": kwargs}
    for handler in _GENERIC_DISPATCH_HANDLERS:
        outcome = handler(action, state)
        if outcome is None:
            return
        if outcome:
            _write_event(state["event"])
            return
    event = {"action": action}
    _breadcrumb("emit_generic %s: default-deny dropped caller kwargs" % action)
    _write_event(event)
