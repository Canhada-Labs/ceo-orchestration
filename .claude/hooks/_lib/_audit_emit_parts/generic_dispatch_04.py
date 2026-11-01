"""One bounded segment of audit_emit generic action normalization."""

from __future__ import annotations

__all__ = ("_apply_generic_group_04",)


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _apply_generic_group_04(action, state):
    event = state["event"]
    kwargs = state["kwargs"]
    if action == "spawn_prompt_defense_gate":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST
        )
        event["keyword"] = str(event.get("keyword", ""))[:32]
        event["present"] = (
            1 if str(event.get("present")) in ("1", "True", "true") else 0
        )
        event["enforced"] = (
            1 if str(event.get("enforced")) in ("1", "True", "true") else 0
        )
        if dropped:
            _breadcrumb(
                f"emit_generic spawn_prompt_defense_gate dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "spec_context_sanitized":
        event, dropped = _scrub_ceo_boot_event(event, _SPEC_CONTEXT_SANITIZED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic spec_context_sanitized dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "invisible_unicode_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _INVISIBLE_UNICODE_BLOCKED_ALLOWLIST
        )
        if event.get("unicode_class") not in _INVISIBLE_UNICODE_CLASSES:
            event["unicode_class"] = "control"
        if event.get("surface") not in _INVISIBLE_UNICODE_SURFACES:
            event["surface"] = "spawn"
        try:
            cc = int(event.get("char_count", 0))
        except (TypeError, ValueError):
            cc = 0
        event["char_count"] = max(0, min(cc, 1000000))
        event["enforced"] = (
            1 if str(event.get("enforced")) in ("1", "True", "true") else 0
        )
        if dropped:
            _breadcrumb(
                f"emit_generic invisible_unicode_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "tool_call_lifecycle_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST
        )
        if event.get("tool_name_enum") not in _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("duration_bucket") not in _TOOL_CALL_LIFECYCLE_DURATION_BUCKETS:
            event["duration_bucket"] = "lt_100ms"
        event["success"] = bool(event.get("success"))
        event["orphan"] = bool(event.get("orphan"))
        if dropped:
            _breadcrumb(
                f"emit_generic tool_call_lifecycle_recorded dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "git_hook_bypass_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST
        )
        if event.get("flag_class") not in _GIT_HOOK_BYPASS_FLAG_CLASSES:
            event["flag_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic git_hook_bypass_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "env_var_hijack_blocked":
        event, dropped = _scrub_ceo_boot_event(event, _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST)
        if event.get("hijack_class") not in _ENV_VAR_HIJACK_CLASSES:
            event["hijack_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic env_var_hijack_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "egress_destination_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _EGRESS_DESTINATION_DETECTED_ALLOWLIST
        )
        if event.get("egress_class") not in _EGRESS_CLASSES:
            event["egress_class"] = "unknown"
        if "destination" in event:
            event["destination"] = _coerce_egress_destination(event["destination"])
        if dropped:
            _breadcrumb(
                f"emit_generic egress_destination_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "adversary_review_flagged":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
        )
        if event.get("decision") not in _ADVERSARY_DECISIONS:
            event["decision"] = "advisory"
        if event.get("rule_class") not in _ADVERSARY_RULE_CLASSES:
            event["rule_class"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic adversary_review_flagged dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "persistent_instructions_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST
        )
        if event.get("reason") not in _PERSISTENT_INSTRUCTIONS_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic persistent_instructions_blocked dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "hint_provenance_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _HINT_PROVENANCE_RECORDED_ALLOWLIST
        )
        if event.get("reason") not in _HINT_PROVENANCE_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic hint_provenance_recorded dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "settings_tamper_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SETTINGS_TAMPER_DETECTED_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _SETTINGS_TAMPER_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(0, min(99, int(event.get("finding_count", 0))))
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic settings_tamper_detected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ceremony_lint_unlock_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEREMONY_LINT_UNLOCK_USED_ALLOWLIST
        )
        fs = event.get("file_sha256")
        if not (
            isinstance(fs, str)
            and len(fs) == 16
            and all((c in "0123456789abcdef" for c in fs))
        ):
            event["file_sha256"] = "invalid"
        rl = event.get("reason_len", 0)
        if isinstance(rl, bool) or not isinstance(rl, int):
            event["reason_len"] = 0
        else:
            event["reason_len"] = max(0, min(9999, rl))
        if dropped:
            _breadcrumb(
                f"emit_generic ceremony_lint_unlock_used dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "salt_rotation_registered":
        event, dropped = _scrub_ceo_boot_event(
            event, _SALT_ROTATION_REGISTERED_ALLOWLIST
        )
        _reason = event.get("reason")
        if not isinstance(_reason, str) or _reason not in _SALT_ROTATION_REASONS:
            event["reason"] = "other"
        if event.get("salt_scope") != "project":
            event["salt_scope"] = "project"
        ss = event.get("slug_sha256")
        if not (
            isinstance(ss, str)
            and len(ss) == 16
            and all((c in "0123456789abcdef" for c in ss))
        ):
            event["slug_sha256"] = "invalid"
        if dropped:
            _breadcrumb(
                f"emit_generic salt_rotation_registered dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "config_change_observed":
        event, dropped = _scrub_ceo_boot_event(event, _CONFIG_CHANGE_OBSERVED_ALLOWLIST)
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_observed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "config_change_forbidden_key":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(0, min(99, int(event.get("finding_count", 0))))
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_forbidden_key dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "compaction_continuity_snapshot":
        event, dropped = _scrub_ceo_boot_event(
            event, _COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST
        )
        if event.get("trigger") not in _COMPACTION_TRIGGERS:
            event["trigger"] = "other"
        if event.get("snapshot_outcome") not in _COMPACTION_SNAPSHOT_OUTCOMES:
            event["snapshot_outcome"] = "other"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        try:
            event["chain_length"] = max(
                0, min(99999999, int(event.get("chain_length", 0)))
            )
        except (TypeError, ValueError):
            event["chain_length"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic compaction_continuity_snapshot dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "compaction_context_reinjected":
        event, dropped = _scrub_ceo_boot_event(
            event, _COMPACTION_CONTEXT_REINJECTED_ALLOWLIST
        )
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        if not isinstance(event.get("snapshot_found"), bool):
            event["snapshot_found"] = False
        try:
            event["snapshot_age_s"] = max(
                0, min(9999999, int(event.get("snapshot_age_s", 0)))
            )
        except (TypeError, ValueError):
            event["snapshot_age_s"] = 0
        try:
            event["pointer_count"] = max(0, min(9, int(event.get("pointer_count", 0))))
        except (TypeError, ValueError):
            event["pointer_count"] = 0
        try:
            event["constraint_count"] = max(
                0, min(99, int(event.get("constraint_count", 0)))
            )
        except (TypeError, ValueError):
            event["constraint_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic compaction_context_reinjected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "context_pressure_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXT_PRESSURE_OBSERVED_ALLOWLIST
        )
        if not _context_pressure_bucket_ok(event.get("used_bucket")):
            event["used_bucket"] = 0
        _cp_src = event.get("event_source")
        if (
            not isinstance(_cp_src, str)
            or _cp_src not in _CONTEXT_PRESSURE_EVENT_SOURCES
        ):
            event["event_source"] = "other"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        if dropped:
            _breadcrumb(
                f"emit_generic context_pressure_observed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ledger_checkpoint_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEDGER_CHECKPOINT_RECORDED_ALLOWLIST
        )
        _lc_outcome = event.get("outcome")
        if (
            not isinstance(_lc_outcome, str)
            or _lc_outcome not in _LEDGER_CHECKPOINT_OUTCOMES
        ):
            event["outcome"] = "other"
        _lc_scope = event.get("scope_source")
        if (
            not isinstance(_lc_scope, str)
            or _lc_scope not in _LEDGER_CHECKPOINT_SCOPE_SOURCES
        ):
            event["scope_source"] = "other"
        _lc_state = event.get("state_kind")
        if (
            not isinstance(_lc_state, str)
            or _lc_state not in _LEDGER_CHECKPOINT_STATE_KINDS
        ):
            event["state_kind"] = "unavailable"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        for _lc_key, _lc_hi in (
            ("in_scope_path_count", 99),
            ("ledger_size_bucket_kib", 99),
            ("unverified_ac_claim_count", 99),
            ("commits_since_last_observation", 99),
            ("over_ceiling", 1),
            ("would_block", 1),
        ):
            event[_lc_key] = _ledger_int_field(event.get(_lc_key), _lc_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_checkpoint_recorded dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ledger_checkpoint_skipped":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST
        )
        _ls_reason = event.get("reason")
        if (
            not isinstance(_ls_reason, str)
            or _ls_reason not in _LEDGER_CHECKPOINT_SKIP_REASONS
        ):
            event["reason"] = "other"
        _ls_state = event.get("state_kind")
        if (
            not isinstance(_ls_state, str)
            or _ls_state not in _LEDGER_CHECKPOINT_STATE_KINDS
        ):
            event["state_kind"] = "unavailable"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        for _ls_key, _ls_hi in (
            ("commits_since_last_observation", 99),
            ("would_block", 1),
        ):
            event[_ls_key] = _ledger_int_field(event.get(_ls_key), _ls_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_checkpoint_skipped dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "ledger_entry_rejected":
        event, dropped = _scrub_ceo_boot_event(event, _LEDGER_ENTRY_REJECTED_ALLOWLIST)
        if event.get("signal") != _LEDGER_GATE_SIGNAL:
            event["signal"] = _LEDGER_GATE_SIGNAL
        _lg_sid = event.get("session_id")
        if not isinstance(_lg_sid, str) or not _LEDGER_ID_RE.match(_lg_sid):
            event["session_id"] = ""
        _lg_proj = event.get("project")
        if not isinstance(_lg_proj, str) or not _LEDGER_ID_RE.match(_lg_proj):
            event["project"] = ""
        if event.get("decision") != "reject":
            event["decision"] = "reject"
        _lg_reason = event.get("reason")
        if (
            not isinstance(_lg_reason, str)
            or _lg_reason not in _LEDGER_GATE_REASONS
            or _lg_reason == "ok"
        ):
            event["reason"] = "malformed_input"
        _lg_family = event.get("family")
        if not isinstance(_lg_family, str) or _lg_family not in _LEDGER_GATE_FAMILIES:
            event["family"] = "unknown_family"
        for _lg_key, _lg_hi in (
            ("hits_count", 9999),
            ("bytes_scanned", 8192),
            ("scanned", 1),
            ("enforced", 1),
        ):
            event[_lg_key] = _ledger_int_field(event.get(_lg_key), _lg_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_entry_rejected dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "session_memory_delta_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _SESSION_MEMORY_DELTA_OBSERVED_ALLOWLIST
        )
        _smd_outcome = event.get("outcome")
        if (
            not isinstance(_smd_outcome, str)
            or _smd_outcome not in _SESSION_MEMORY_DELTA_OUTCOMES
        ):
            event["outcome"] = "other"
        _smd_anchor = event.get("anchor_source")
        if (
            not isinstance(_smd_anchor, str)
            or _smd_anchor not in _SESSION_MEMORY_DELTA_ANCHOR_SOURCES
        ):
            event["anchor_source"] = "none"
        for _smd_key in ("files_count", "modified_count"):
            _smd_val = event.get(_smd_key)
            if isinstance(_smd_val, bool) or not isinstance(_smd_val, int):
                event[_smd_key] = 0
            else:
                event[_smd_key] = max(0, min(99999, _smd_val))
        if not isinstance(event.get("index_modified"), bool):
            event["index_modified"] = False
        _smd_sid = event.get("session_id")
        if not isinstance(_smd_sid, str):
            event["session_id"] = ""
        else:
            event["session_id"] = _smd_sid[:128]
        _smd_proj = event.get("project")
        if not isinstance(_smd_proj, str):
            event["project"] = ""
        else:
            event["project"] = _smd_proj[:256]
        if dropped:
            _breadcrumb(
                f"emit_generic session_memory_delta_observed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "bash_input_rewritten":
        event, dropped = _scrub_ceo_boot_event(event, _BASH_INPUT_REWRITTEN_ALLOWLIST)
        if event.get("rewrite_class") not in _BASH_REWRITE_CLASSES:
            event["rewrite_class"] = "other"
        if not _is_sha256_hex(event.get("before_sha256")):
            event["before_sha256"] = ""
        if not _is_sha256_hex(event.get("after_sha256")):
            event["after_sha256"] = ""
        if dropped:
            _breadcrumb(
                f"emit_generic bash_input_rewritten dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "subagent_lifecycle_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST
        )
        if event.get("agent_archetype") not in _SUBAGENT_LIFECYCLE_ARCHETYPES:
            event["agent_archetype"] = "other"
        if event.get("wall_source") not in _SUBAGENT_LIFECYCLE_WALL_SOURCES:
            event["wall_source"] = "unknown"
        if event.get("wall_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["wall_bucket"] = "unknown"
        if event.get("token_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["token_bucket"] = "unknown"
        if event.get("claim_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["claim_bucket"] = "unknown"
        if dropped:
            _breadcrumb(
                f"emit_generic subagent_lifecycle_observed dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
        state["event"] = event
        return True

    if action == "admin_key_lifecycle_event":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST
        )
        if "operation" in event and event.get("operation") not in _ADMIN_KEY_OPERATIONS:
            event["operation"] = "other"
        if "reason" in event and event.get("reason") not in _ADMIN_KEY_REASONS:
            event["reason"] = "other"
        if "key_id" in event:
            event["key_id"] = str(event.get("key_id", ""))[:128]
        if "key_count" in event:
            try:
                event["key_count"] = max(
                    0, min(int(event.get("key_count", 0)), 1000000)
                )
            except (TypeError, ValueError, OverflowError):
                event["key_count"] = 0
        if "rotation_log_appended" in event:
            event["rotation_log_appended"] = str(
                event.get("rotation_log_appended")
            ).strip().lower() in ("1", "true", "yes")
        if dropped:
            _breadcrumb(
                "emit_generic admin_key_lifecycle_event dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "statusline_sidecar_write":
        event, dropped = _scrub_ceo_boot_event(
            event, _STATUSLINE_SIDECAR_WRITE_ALLOWLIST
        )
        if "sidecar_path" in event:
            event["sidecar_path"] = str(event.get("sidecar_path", ""))[
                :_STATUSLINE_SIDECAR_PATH_CAP
            ]
        if "plan_id" in event and event.get("plan_id") is not None:
            event["plan_id"] = str(event.get("plan_id"))[:_STATUSLINE_STR_CAP]
        if "digest" in event:
            event["digest"] = str(event.get("digest", ""))[:_STATUSLINE_STR_CAP]
        if "bucket_count" in event:
            try:
                event["bucket_count"] = max(
                    0, min(int(event.get("bucket_count", 0)), 1000000)
                )
            except (TypeError, ValueError, OverflowError):
                event["bucket_count"] = 0
        if "context_pct_bps" in event and event.get("context_pct_bps") is not None:
            try:
                event["context_pct_bps"] = max(
                    0, min(10000, int(round(float(event.get("context_pct_bps")))))
                )
            except (TypeError, ValueError, OverflowError):
                event["context_pct_bps"] = None
        if (
            "buckets_used_pct_max_bps" in event
            and event.get("buckets_used_pct_max_bps") is not None
        ):
            try:
                event["buckets_used_pct_max_bps"] = max(
                    0,
                    min(
                        99900, int(round(float(event.get("buckets_used_pct_max_bps"))))
                    ),
                )
            except (TypeError, ValueError, OverflowError):
                event["buckets_used_pct_max_bps"] = None
        if dropped:
            _breadcrumb(
                "emit_generic statusline_sidecar_write dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "model_refusal_observed":
        event, dropped = _scrub_ceo_boot_event(event, _MODEL_REFUSAL_OBSERVED_ALLOWLIST)
        if "stop_reason" in event:
            event["stop_reason"] = "refusal"
        if "stop_category" in event:
            _cat = event.get("stop_category")
            event["stop_category"] = _cat[:64] if isinstance(_cat, str) else ""
        if "provider" in event:
            event["provider"] = str(event.get("provider", ""))[:64]
        if "model" in event:
            event["model"] = str(event.get("model", ""))[:128]
        for _intf in ("http_status", "duration_ms"):
            if _intf in event:
                try:
                    event[_intf] = max(0, min(int(event.get(_intf, 0)), 1000000000))
                except (TypeError, ValueError, OverflowError):
                    event[_intf] = 0
        if dropped:
            _breadcrumb(
                "emit_generic model_refusal_observed dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True

    if action == "lesson_candidate_written":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_CANDIDATE_WRITTEN_ALLOWLIST
        )
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["trigger"] = _learning_token_field(event.get("trigger"))
        if event.get("status") not in _LESSON_CANDIDATE_STATUS_ENUM:
            event["status"] = "QUARANTINED"
        if event.get("scan_outcome") not in _LESSON_SCAN_OUTCOME_ENUM:
            event["scan_outcome"] = "scanner_unavailable"
        event["content_sha256"] = _learning_sha256_field(event.get("content_sha256"))
        event["scope_tags"] = _learning_scope_tags_field(event.get("scope_tags"))
        if dropped:
            _breadcrumb(
                "emit_generic lesson_candidate_written dropped: %s"
                % sorted(dropped)[:10]
            )
        state["event"] = event
        return True
    return False
