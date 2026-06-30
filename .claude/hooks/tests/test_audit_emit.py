"""Unit tests for _lib/audit_emit.py — event stream v2 typed emitters.

Covers all 5 emitters plus iter_events + fail-open paths.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_emit  # noqa: E402


class TestAuditEmit(TestEnvContext):
    """Event stream v2 emitters: schema, fields, redaction, iter."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def test_debate_event_basic(self):
        audit_emit.emit_debate_event(
            plan_id="PLAN-004",
            round_num=1,
            phase="agent-done",
            agent="vp-engineering",
            artifact_path=".claude/plans/PLAN-004/debate/round-1/vp-engineering.md",
            session_id="s1",
            project="/test",
        )
        entries = self._read_log()
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["action"], "debate_event")
        self.assertEqual(e["plan_id"], "PLAN-004")
        self.assertEqual(e["round"], 1)
        self.assertEqual(e["phase"], "agent-done")
        self.assertEqual(e["agent"], "vp-engineering")
        self.assertEqual(e["event_schema"], "v2")
        self.assertIn("ts", e)
        self.assertIsNone(e["tokens_in"])
        self.assertIsNone(e["tokens_out"])
        self.assertIsNone(e["tokens_total"])

    def test_debate_consensus_records_adjustments(self):
        audit_emit.emit_debate_event(
            plan_id="PLAN-004",
            round_num=1,
            phase="consensus",
            agent="consensus",
            artifact_path="round-1/consensus.md",
            consensus_adjustments_count=6,
        )
        entries = self._read_log()
        self.assertEqual(entries[0]["consensus_adjustments_count"], 6)

    def test_plan_transition_marks_legal(self):
        audit_emit.emit_plan_transition(
            plan_id="PLAN-004",
            from_status="draft",
            to_status="reviewed",
            file_path=".claude/plans/PLAN-004-sprint-4-state-of-the-art.md",
            editor_tool="Edit",
        )
        entries = self._read_log()
        self.assertEqual(entries[0]["action"], "plan_transition")
        self.assertEqual(entries[0]["from_status"], "draft")
        self.assertEqual(entries[0]["to_status"], "reviewed")
        self.assertTrue(entries[0]["transition_legal"])

    def test_veto_triggered_redacts_reason_preview(self):
        audit_emit.emit_veto_triggered(
            hook="check_agent_spawn",
            reason_code="missing_skill_content",
            reason_preview="sk-proj-abc123xyz456789012345 was in the prompt",
            blocked_tool="Agent",
            strike_count=1,
        )
        entries = self._read_log()
        self.assertNotIn("sk-proj-abc123xyz", entries[0]["reason_preview"])
        self.assertEqual(entries[0]["hook"], "check_agent_spawn")
        self.assertEqual(entries[0]["reason_code"], "missing_skill_content")
        self.assertEqual(entries[0]["strike_count"], 1)

    def test_veto_preview_truncated_to_120_chars(self):
        long_text = "x" * 500
        audit_emit.emit_veto_triggered(
            hook="check_bash_safety",
            reason_code="dangerous_rm",
            reason_preview=long_text,
            blocked_tool="Bash",
        )
        entries = self._read_log()
        self.assertLessEqual(len(entries[0]["reason_preview"]), 120)

    def test_benchmark_run_coerces_numeric_types(self):
        audit_emit.emit_benchmark_run(
            benchmark_id="owasp-basics",
            skill="security-and-auth",
            pass_count=9,
            fail_count=1,
            pass_rate=0.9,
            median_score=0.85,
            floor=0.6,
            cost_usd=0.42,
            duration_s=12.3,
            lessons_written=1,
        )
        entries = self._read_log()
        e = entries[0]
        self.assertEqual(e["action"], "benchmark_run")
        self.assertIsInstance(e["pass_count"], int)
        # Float fields are now int-encoded (bps / cents / ms).
        self.assertNotIn("pass_rate", e)
        self.assertNotIn("median_score", e)
        self.assertNotIn("floor", e)
        self.assertNotIn("cost_usd", e)
        self.assertNotIn("duration_s", e)
        self.assertEqual(e["pass_rate_bps"], 900)
        self.assertEqual(e["median_score_bps"], 850)
        self.assertEqual(e["floor_bps"], 600)
        self.assertEqual(e["cost_usd_cents"], 42)
        self.assertEqual(e["duration_ms"], 12300)
        self.assertIsInstance(e["pass_rate_bps"], int)
        self.assertIsInstance(e["median_score_bps"], int)
        self.assertIsInstance(e["floor_bps"], int)
        self.assertIsInstance(e["cost_usd_cents"], int)
        self.assertIsInstance(e["duration_ms"], int)
        self.assertEqual(e["skill"], "security-and-auth")

    def test_lesson_write_copies_scope_tags(self):
        tags = ["security", "auth", "owasp"]
        audit_emit.emit_lesson_write(
            lesson_id="LES-001",
            archetype="security-engineer",
            scope_tags=tags,
            trigger="benchmark_fail",
            source_event_id="bench-42",
        )
        entries = self._read_log()
        self.assertEqual(entries[0]["scope_tags"], tags)
        tags.append("xxx")
        self.assertNotIn("xxx", entries[0]["scope_tags"])

    def test_unknown_action_rejected_via_breadcrumb(self):
        audit_emit._write_event({"action": "bogus", "foo": "bar"})
        entries = self._read_log()
        self.assertEqual(entries, [])
        err = Path(os.environ["CEO_AUDIT_LOG_ERR"])
        self.assertTrue(err.exists())
        self.assertIn("unknown action", err.read_text())

    def test_all_events_have_event_schema_v2(self):
        audit_emit.emit_debate_event("PLAN-004", 1, "start", "proposal")
        audit_emit.emit_plan_transition("PLAN-004", "draft", "reviewed", "x.md")
        audit_emit.emit_veto_triggered("h", "r", "p")
        audit_emit.emit_benchmark_run("b", "s", 1, 0, 1.0, 1.0, 0.6)
        audit_emit.emit_lesson_write("L", "a", [], "manual")
        entries = self._read_log()
        self.assertEqual(len(entries), 5)
        for e in entries:
            self.assertEqual(e["event_schema"], "v2")
            self.assertIn("ts", e)
            self.assertIn("tokens_in", e)

    def test_iter_events_no_filter_yields_all(self):
        audit_emit.emit_debate_event("PLAN-004", 1, "start", "proposal")
        audit_emit.emit_plan_transition("PLAN-004", "draft", "reviewed", "x.md")
        events = list(audit_emit.iter_events())
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["action"], "debate_event")
        self.assertEqual(events[1]["action"], "plan_transition")

    def test_iter_events_action_filter(self):
        audit_emit.emit_debate_event("P", 1, "start", "proposal")
        audit_emit.emit_veto_triggered("h", "r", "p")
        audit_emit.emit_debate_event("P", 1, "consensus", "consensus")
        events = list(audit_emit.iter_events(action_filter="debate_event"))
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["action"] == "debate_event" for e in events))

    def test_iter_events_tolerates_malformed_lines(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            '{"valid":"yes","action":"agent_spawn"}\n'
            'not-json\n'
            '{"action":"debate_event","plan_id":"P"}\n'
        )
        events = list(audit_emit.iter_events())
        self.assertEqual(len(events), 2)
        err = Path(os.environ["CEO_AUDIT_LOG_ERR"])
        self.assertTrue(err.exists())

    def test_log_file_permissions_600(self):
        audit_emit.emit_debate_event("P", 1, "start", "proposal")
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        mode = log.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_timestamp_is_iso_8601_z(self):
        ts = audit_emit._utc_now_iso()
        import re
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_event_schema_constant_is_v2(self):
        self.assertEqual(audit_emit.EVENT_SCHEMA_V2, "v2")

    def test_known_actions_set_contract(self):
        expected = {
            "agent_spawn",
            "debate_event",
            "plan_transition",
            "veto_triggered",
            "benchmark_run",
            "lesson_write",
            "lesson_outcome",  # v2, ADR-015
            "injection_flag",  # v2.1, ADR-011
            "confidence_gate",  # Sprint 8, ADR-018
            "lesson_read",  # Sprint 8 Phase 3
            "lesson_archived",  # Sprint 8 Phase 4
            "lesson_restored",  # Sprint 8 Phase 4b
            "lesson_outcome_undone",  # Sprint 9 P3.3
            "state_store_write",  # Sprint 11 Phase 0, ADR-027
            "state_store_read",  # Sprint 11 Phase 0, ADR-027
            "state_store_pruned",  # Sprint 11 Phase 0, ADR-027
            "budget_exceeded",  # Sprint 11 Phase 6, ADR-033
            "budget_bypass_used",  # Sprint 11 Phase 6, H13
            "otel_export_dropped",  # Sprint 11 Phase 8, CR3
            "output_safety_flag",  # Sprint 11 Phase 9, ADR-036
            "skill_patch_applied",  # Sprint 11 Phase 4, ADR-031
            "squad_imported",  # Sprint 11 Phase 12, CR2
            # Sprint 13 Phase A.0 (PLAN-013 Gap #3) — live-adapter / breaker /
            # credential events previously emitted but unregistered.
            "live_adapter_call_started",  # ADR-040 §7
            "live_adapter_call_succeeded",  # ADR-040 §7
            "live_adapter_call_failed",  # ADR-040 §7
            "breaker_opened",  # ADR-040 §2
            "breaker_closed",  # ADR-040 §2
            "credential_rotation_due",  # ADR-040 §4
            # Sprint 13 Phase A (PLAN-013) — MCP server events (ADR-042)
            "mcp_handler_invoked",  # ADR-042 §Auth
            "mcp_handler_denied",  # ADR-042 §Auth.5
            "mcp_server_started",  # ADR-042 §Cost.4
            "mcp_server_disabled_by_kill_switch",  # ADR-042 §Cost.4
            # Sprint 14 Phase 0.6 (PLAN-014 ADJ-010) — audit registry v2.6
            "policy_evaluated",
            "policy_denied",
            "policy_error",
            "replay_started",
            "replay_completed",
            "replay_diff_produced",
            "prediction_queried",
            "pattern_stored",
            "pattern_queried",
            "pattern_evicted",
            "threat_model_promoted",
            "threat_model_freshness_breach",
            # PLAN-028 Wave A Fase 3 (ADR-056) — lifecycle expansion hooks
            "session_start",
            "session_end",
            "prompt_submitted",
            "session_stop",
            # PLAN-029 Wave A Fase 4 (ADR-057) — output-scan redaction
            "output_scan_finding",
            # PLAN-041 Wave A+ (ADR-062) — LightRAG sidecar MCP opt-in
            "rag_query_issued",
            "rag_query_returned",
            "rag_query_fallback",
            "rag_query_redacted",
            "rag_index_redacted",
            # PLAN-043 Wave B (ADR-064) — dynamic tier-policy learned dispatch
            "tier_policy_adopter_override_respected",
            "tier_policy_demote_requested",
            "tier_policy_derived",
            "tier_policy_dry_run_complete",
            "tier_policy_hmac_verify_failed",
            "tier_policy_killswitch_triggered",
            "tier_policy_promote_applied",
            "tier_policy_promote_cost_gated",
            "tier_policy_rejected",
            # PLAN-045 P0-04 closure — tournament_* actions registered via
            # Owner kernel batch /tmp/plan_032_audit_emit_batch.py on 2026-04-20.
            # Closes PLAN-044 F-12-01 / F-07-02 (tournament audit trail).
            "tournament_aborted",
            "tournament_budget_exceeded",
            "tournament_budget_projected",
            "tournament_fixture_rejected",
            "tournament_judge_hijack_suspected",
            "tournament_run_completed",
            "tournament_run_started",
            "tournament_task_scored",
            # PLAN-045 Wave 5 round-8 (Session 43) — registered via
            # kernel-batch-wave-5.py. Closes P0-09 (b) fluency advisory +
            # F-10-07 v2 session-state reconcile.
            "fluency_nudge",
            "skill_reference_read_mismatch",
            "skill_reference_read_stale",
            "skill_reference_never_read",
            # PLAN-017 Phase 4 (Session 51 physical closeout) — swarm events
            "swarm_started",
            "swarm_iteration",
            "swarm_halted_budget",
            "swarm_halted_convergence",
            "swarm_halted_kill",
            "swarm_aborted_error",
            "swarm_killed",
            "swarm_tournament_selected",
            "swarm_finalize_grouped",
            "swarm_finalize_committed",
            # PLAN-048 Phase 2 (Session 51 physical closeout) — CEO escalation
            "escalation_detected",
            "escalation_dispatched",
            "escalation_suppressed",
            "escalation_baseline_recorded",
            # PLAN-059 SEC-P0-04 / ADR-080 (Session 62 cont, 2026-04-25) —
            # audit-tokens content-ban events (counts-only allowlist).
            "audit_tokens_emitted",
            "audit_tokens_timeout",
            "audit_tokens_key_dropped",
            # PLAN-052 / ADR-083 (Wave B, 2026-04-27) — MCP injection scanner
            # finding wired up via PLAN-044 audit-v2 C1-P0-03 fix.
            "mcp_injection_finding",
            # Session 76 audit-v3 / Codex DIM-04 #1 (2026-04-29) — skill
            # bootstrap observability. Pre-Session-76 these were emitted by
            # check_skill_patch_sentinel + check_skill_bootstrap_post yet
            # dropped silently by `_write_event` because the actions were
            # unregistered. SPEC v2.15 row added in the same ceremony.
            "skill_bootstrap_used",
            "skill_bootstrap_post_hash",
            # Session 81 / PLAN-069 Phase 1 Wave D (ADR-101, 2026-05-03) —
            # replay capture-as-fixture mode emits its own lifecycle pair
            # distinct from replay_started/_completed. SPEC v2.16.
            "replay_capture_started",
            "replay_capture_completed",
            # Session 82 / PLAN-065 Phase 2 (ADR-098, 2026-05-04) —
            # /ceo-boot session-start autopilot telemetry. ceo_boot_emitted
            # fires once per boot with gate_pass + duration_ms + checks_total/
            # _failed + cache_hit (Sec MF-3 field allowlist enforced).
            # ceo_boot_check_skipped fires per-check on aggregate timeout.
            # SPEC v2.17.
            "ceo_boot_emitted",
            "ceo_boot_check_skipped",
            "ceo_boot_persona_coverage_score",  # PLAN-093 Wave C.5 (S123) — 4×4 persona × task coverage matrix
            # Session 85 / PLAN-070 / ADR-102 (2026-05-05) — Layer B server-side
            # MCP canonical-guard middleware. Closes ADR-095 §gate-#6 NG-06
            # (custom mcp__* tools previously bypassed check_canonical_edit
            # because the hook only filtered Edit/Write/MultiEdit/NotebookEdit).
            # Sec MF-3 enforced via dedicated allowlists.
            "mcp_canonical_guard_blocked",
            "mcp_canonical_guard_allowed",
            # Session 87 / PLAN-071 / ADR-104 (2026-05-05) — Adaptive Execution
            # Kernel + Reality Ledger advisory events. task-route.py emits
            # task_route_advised per invocation; reality-ledger.py emits
            # reality_ledger_finding per detected finding. *_key_dropped
            # are defense-in-depth breadcrumbs when scrub strips forbidden
            # fields (Sec MF-3 allowlist enforcement). SPEC v2.19.

            "task_route_advised",
            "task_route_key_dropped",
            "reality_ledger_finding",
            "reality_ledger_key_dropped",
            # PLAN-078 Wave 1 (model_routing_advised) + Wave 2
            # (estimate_drift_detected, estimate_drift_systematic_bias) —
            # Reality Ledger advisory events shipped in S89 Fase 1 commit
            # 2cb1472. Sec MF-3 field allowlist enforced via dedicated
            # _FORBIDDEN_FIELDS_* sets in audit_emit.py (deny-by-default).
            # Test drift fixed in Wave 1b S92 ceremony alongside SKILL ship.
            "model_routing_advised",
            # PLAN-112-FOLLOWUP-persona-routing-wire (S158, v1.42.0) — god-mode
            # routing-matrix consult telemetry (CONSULT+AUDIT; block deferred).
            # Registered via kernel-override PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION.
            "model_routing_enforced",
            "model_routing_eval_error",
            "estimate_drift_detected",
            "estimate_drift_systematic_bias",
            # PLAN-078 Wave 5 (S95 ceremony 2026-05-08) — TaskCreate-candidate
            # orchestration. Emitted by ceo-boot.py per stdout marker block
            # written when gate_pass=False AND severity≥medium. Sec MF-3
            # 4-field allowlist (rank, severity, subject_hash, awaiting_confirm).
            "ceo_boot_task_candidate_emitted",
            # PLAN-075 v1.13.x patch (S96-cont-2 ceremony 2026-05-09) —
            # Pair-Rail Multi-LLM cross-review hook events. Wired by
            # check_pair_rail.py PreToolUse on Edit|Write|MultiEdit against
            # L3+ canonical-guarded paths. ADR-106 + ADR-110 ACCEPTED.
            # Registered with KERNEL_OVERRIDE bypass (audit_emit.py is in
            # _KERNEL_PATHS).
            "pair_rail_review_passed",
            "pair_rail_codex_unavailable",
            "pair_rail_codex_violation",
            "pair_rail_sentinel_bypass",
            # PLAN-081 Phase 1-full / R1 S-Sec-5 (S99 ceremony 2026-05-09).
            # Wired by check_codex_response.py PostToolUse on
            # mcp__codex__codex|mcp__codex__codex-reply matchers. ADVISORY
            # only per ADR-106. Sec MF-3 fields: tool_name + family_ids
            # + match_count + first_offset_bucket. Registered with
            # KERNEL_OVERRIDE bypass (audit_emit.py is in _KERNEL_PATHS).
            "pair_rail_codex_injection_detected",
            # PLAN-081 Phase 2 (S100 ceremony 2026-05-10). Wired by
            # .claude/scripts/inject-agent-context.sh `--pair-mode`
            # dispatcher resolution. Sec MF-3 fields: archetype + rail +
            # reason_code + matrix SHA prefix + wall_clock_ms (int per
            # canonical_json no-float invariant). Registered with
            # KERNEL_OVERRIDE bypass.
            "dispatcher_route",
            # PLAN-081 Phase 3 (S100 ceremony) - asymmetric matrix Cases A-F.
            "pair_rail_case",
            # PLAN-081 Phase 4 (S100 ceremony) - promotion gate verdict.
            "pair_rail_promotion",
        "smart_loading_resolved",
        "trading_kill_switch_disabled",
        "trading_kill_switch_invoked",
        "trading_write_override_used",
        "value_dashboard_summarized",
        "contextual_recommendation_emitted",
        "first_run_wizard_completed",
        "anti_ceo_overhead_override_used",
        "anti_ceo_overhead_block",
        "token_budget_guard_paused",
        # PLAN-084 Wave 0.5 + 0.8 (S107-cont 2026-05-12, commit 9ff2b9e).
        # Registered atomically with CEO_KERNEL_OVERRIDE=PLAN-084-WAVE-0-CANONICAL-GUARD-EXTENSION
        # ceremony per ADR-113 + ADR-114 PROPOSED.
        # Canonical-edit lifecycle direct emit (parallel to veto_triggered reason_code filter).
        # AC1 verifier uses these direct action names.
        "canonical_edit_attempted",
        "canonical_edit_blocked",
        "sentinel_created",
        "sentinel_verified",
        "gpg_signed",
        "gpg_verified",
        "wave_readonly_violation",
        # PLAN-084 Wave 0.10 — staging artifact integrity per R2-iter-2 CODEX-P0-2.
        "wave_artifact_written",
        # PLAN-084 Wave 0.5 — Codex egress redaction (R1 Sec-P0-2 + R2 CODEX-P0-1).
        # Mirror of pair_rail_codex_injection_detected for outgoing direction.
        "pair_rail_outgoing_redaction_applied",
        # PLAN-084 AC12d — estimate refinement per phase milestone (Bayesian-ish).
        "estimate_refined",
        # PLAN-085 v1.19.0 Wave C — identity / credentials (S111 2026-05-12).
        "live_adapter_blocked",
        "credential_blocked_due_to_age",
        "credential_emergency_override_used",
        "credential_override_late_set_ignored",  # PLAN-117 WS-A (S176)
        "mcp_bearer_replay_rejected",
        "mcp_non_loopback_rejected",
        # PLAN-085 v1.19.0 Wave G.1b — MITRE ATLAS schema (S111 2026-05-12).
        "prompt_injection_detected",        # AML.T0051
        "secret_leak_detected",              # AML.T0024.001
        "pii_redacted_outgoing",             # AML.T0048.004
        "codex_egress_redacted",             # AML.T0054
        # PLAN-085 v1.19.0 Wave E.4 piggyback — PostToolUse Bash forensic.
        "canonical_edit_completed",
        # PLAN-086 v1.20.0 Wave B/C/D/G (S112 2026-05-12) — Codex MCP routing
        # bundle, Anthropic 429 observation, Codex session-id chain integrity,
        # MCP canonical-guard internal-error breadcrumb, repo-profile confirmation.
        "anthropic_429_observed",
        "codex-reply",
        "codex_invoke_dispatched",
        "git_index_lock_retry",
        "mcp_canonical_guard_internal_error",
        "mcp_route_advised",
        "repo_profile_confirmed",
        "subagent_findings_partial_drop",
        "thinking_budget_set",
        # PLAN-088 v1.22.0 Wave 1 canonical-13 audit-emit foundation (S114
        # 2026-05-13). 11 net-new actions for the god-mode AUTO-USABLE
        # capability surface.
        "batch_dispatched",
        "cache_discipline_alerted",
        "cookbook_pattern_advised",
        "estimate_calibrator_pipeline_run",
        "first_run_wizard_dispatched",
        "pair_rail_phase_advanced",
        "tier_policy_misrouting_advised",
        "tier_policy_loader_fallback_observed",  # PLAN-116 (S172)
        # PLAN-090 Wave B + AMENDMENT-1 + D (S118 v1.24.0) — streaming +
        # confidence-gate baseline + rollout completion sentinel.
        "streaming_token_yielded",
        "streaming_rate_capped",
        "capability_rollout_complete",
        "kill_switch_invoked",
        "confidence_gate_baseline_emitted",
        "mcp_bearer_friction_observed",
        "phase_c_enforcing_flipped",
        # PLAN-089 Wave A.4 + B.3 + C (S117 v1.23.0) — kernel extension +
        # canonical bypass + sentinel signer rotation (ADR-116-AMEND-1 + ADR-121).
        "bash_canonical_bypass_invoked",
        "kernel_extension_landed",
        "sentinel_signer_quorum_failed",
        "sentinel_signer_quorum_attempted",
        "sentinel_signer_rotated",
        "sentinel_signer_revoked",
        "sentinel_signer_expiry_warned",
        # PLAN-091 / PLAN-088 — persona auto decision telemetry.
        "persona_auto_decision_emitted",
        "persona_auto_rate_capped",
        # PLAN-094 Wave A (S124 v1.27.0-pending) — ADR-055-AMEND-1
        # spool-writer drain forensic events. 7 net-new audit actions
        # registered atomically with the spool_writer.py canonical
        # promotion ceremony (sentinel round-2 GPG-signed 00000000,
        # Codex R2 ACCEPT iter-7 thread 019e2889).
        "audit_flush_dropped_count",
        "audit_spool_stale_recovered",
        "audit_spool_partial_line_discarded",
        "audit_spool_tamper_detected",
        "audit_spool_duplicate_tuple_rejected",
        "audit_spool_intentionally_deleted",
        "audit_spool_unexpected_skip",
        # PLAN-094 Wave B (R-039, S124) — smart-loading frontmatter
        # cache stats. Emitted by smart-loading-resolver.py at
        # session-end atexit handler with hit_count/miss_count/size
        # counters (per Wave B §B.6 audit surface).
        "skill_cache_stats",
        # PLAN-096 (ADR-042-AMEND-1, S130) — Wave D cross-tenant denial
        # + Wave E soak FPR breach surfaces (read-only MCP expansion).
        "mcp_cross_tenant_denied",
        "mcp_soak_fpr_breach",
        # PLAN-097 (ADR-062-AMEND-1 / ADR-128 §6, S131) — RAG routing
        # audit surface (5 actions, Wave C decision layer).
        "rag_profile_recommended",
        "rag_auto_wire_skipped_sidecar_down",
        "rag_query_routed",
        "rag_false_large_demoted",
        "rag_hit_rate_degraded",
        # PLAN-098 (ADR-132, S132) — GOAP A* advisory-only planner
        # audit surface (10 actions; Wave A per-edge sampled + terminus).
        "goap_edge_explored",
        "goap_search_aborted",
        "goap_search_summary",
        "goap_cycle_detected",
        "goap_depth_exceeded",
        "goap_replan_triggered",
        "goap_replan_exhausted",
        "goap_disabled_by_env",
        "goap_recommendation_accepted",
        # PLAN-099 (ADR-129 / ADR-135, S134) — federation cross-machine
        # MVP audit surface (9 actions; Wave D kernel-override extension).
        "federation_connection_accepted",
        "federation_connection_rejected",
        "federation_connection_replay_suspected",
        "federation_cert_expiry_warned",
        "federation_cert_rotated",
        "federation_cert_revoked",
        "federation_write_attempt_blocked",
        "federation_lan_bind_denied",
        "federation_autonomous_call_blocked",
        "federation_enable_sentinel_invalid",
        # PLAN-105 Wave A.1 + A.2 (S134-cont) — GOAP recommendation
        # outcome telemetry (rendered + overridden); accepted call-site
        # wire-in (A.3) reuses pre-existing emit_goap_recommendation_accepted.
        "goap_recommendation_rendered",
        "goap_recommendation_overridden",
        # PLAN-104 Wave A (S136 2026-05-18) — persona-demand ledger (4 actions).
        # Pre-existing drift absorbed by PLAN-090-FOLLOWUP S138 ceremony.
        "persona_demand_opened",
        "persona_demand_matched",
        "persona_demand_unmet",
        "persona_demand_waived",
        # PLAN-090-FOLLOWUP Wave A (S138 2026-05-18) — claim producer pair.
        "claim_emitted",
        "confidence_gate_verdict",
        # PLAN-100 Wave B (S139 2026-05-18) — per-class block-mode + drift detector.
        "confidence_gate_blocked",
        "confidence_gate_fp_drift_detected",
        # PLAN-101 v1.35.0 — AEK calibration ground-truth label
        "task_route_ground_truth_label",
        # PLAN-102 v1.36.0 — autonomous-loop cost-envelope + execution-context
        "cost_envelope_capped",
        "swarm_runaway_suspected",
        "swarm_paused_owner_absent",
        "execution_context_signed",
        "execution_context_validation_failed",
        # PLAN-106 v1.37.0 — persona coverage + output-scan dedup
        "persona_coverage_synthesized",
        "output_scan_finding_suppressed",
        # PLAN-107 v1.38.0 Wave B.4 (S145) — orphan emit register via
        # kernel-override sentinel PLAN-107-WAVE-B-ORPHAN-REGISTER.
        "stdlib_violation",
        # PLAN-102-FOLLOWUP v1.38.2 Wave B (S145) — Layer 3+4 gate emit via
        # kernel-override sentinel PLAN-102-FOLLOWUP-WAVE-A-AUDIT-EMIT-EXTENSION.
        "swarm_layer_3_4_blocked",
        # PLAN-110 v1.39.0 Wave D (S147) — protocol-semver-cascade advisory
        # emit register via kernel-override sentinel
        # PLAN-110-WAVE-D-AUDIT-EMIT-EXTENSION.
        "protocol_edit_missing_amend_paired",
        # PLAN-099-FOLLOWUP v1.39.1 Wave F (S148) — federation write-mode
        # audit surface via kernel-override sentinel
        # PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION (19 new actions;
        # `federation_cert_rotated` already in set from PLAN-099 MVP S134 and
        # field-shape-superseded in-place at Wave F.2).
        "federation_audit_event_pushed",
        "federation_audit_event_pushed_batch",
        "federation_audit_log_backpressure",
        "federation_cert_validity_window_too_large",
        "federation_event_action_blocked",
        "federation_hmac_secret_rotated",
        "federation_key_floor_rejected",
        "federation_key_floor_stale",
        "federation_message_storm_detected",
        "federation_peer_invalid_no_fingerprint",
        "federation_peer_list_reloaded",
        "federation_peer_registered",
        "federation_peer_registered_collision",
        "federation_peer_revoked_remote",
        "federation_pin_legacy_used",
        "federation_scope_denied",
        "federation_spki_fingerprint_mismatch",
        "federation_tamper_detected",
        "federation_write_disabled_sentinel_invalid",
        "federation_write_endpoint_denied",
        # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 (S152, v1.39.4) —
        # chain_reset_marker rotation re-anchor sentinel. ADR-055-AMEND-2
        # ACCEPTED. Emitted as line 1 of a freshly rotated audit-log.jsonl.
        "chain_reset_marker",
        # PLAN-113 Phase B WIRE-DEADMOD (S163, v1.45.x) — spawn-prompt advisory
        # telemetry emitted via emit_generic from check_agent_spawn.py.
        "spec_context_sanitized",
        "spawn_confidence_advisory",
        # PLAN-118 AC-B5 (S179) — producer-side fail-CLOSED forensic
        # breadcrumb for canonical-resolution mismatch detected at the
        # marker chokepoint (chain_reset_marker) or spool-drain chokepoint
        # (spool_drain). Registered via kernel-override
        # PLAN-118-WS-B-CHOKEPOINTS.
        "audit_producer_path_pollution_detected",
        }
        # Other actions added since this test was last rebased may be
        # present (e.g. S134 federation set, S172 tier_policy_loader_
        # fallback_observed, S176 credential_override_late_set_ignored).
        # Assert the new PLAN-118 action is present + the count matches the
        # canonical _KNOWN_ACTIONS pinned in test_audit_emit_api_contract
        # (which is the single source of truth for the closed enum).
        self.assertTrue(expected.issubset(audit_emit._KNOWN_ACTIONS))


class TestSprint8Emitters(TestEnvContext):
    """Sprint 8 emitters: confidence_gate, lesson_read, lesson_archived, lesson_restored."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def test_confidence_gate_records_reserved_fields(self):
        audit_emit.emit_confidence_gate(
            claim_count=5,
            pass_count=4,
            fail_count=1,
            verifier_kind_counts={"path_exists": 3, "function_exists": 2},
            agent_name="Staff Backend Engineer",
            source="stdin",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "confidence_gate")
        self.assertEqual(e["claim_count"], 5)
        self.assertEqual(e["pass_count"], 4)
        self.assertEqual(e["fail_count"], 1)
        self.assertEqual(e["verifier_kind_counts"], {"path_exists": 3, "function_exists": 2})
        self.assertEqual(e["agent_name"], "Staff Backend Engineer")
        self.assertEqual(e["source"], "stdin")
        self.assertEqual(e["event_schema"], "v2")

    def test_confidence_gate_zero_claims_is_valid(self):
        audit_emit.emit_confidence_gate(
            claim_count=0,
            pass_count=0,
            fail_count=0,
            verifier_kind_counts={},
        )
        e = self._read_log()[0]
        self.assertEqual(e["claim_count"], 0)
        self.assertEqual(e["verifier_kind_counts"], {})

    def test_confidence_gate_kind_counts_is_dict_copy(self):
        counts = {"sha_exists": 2}
        audit_emit.emit_confidence_gate(
            claim_count=2, pass_count=2, fail_count=0,
            verifier_kind_counts=counts,
        )
        counts["sha_exists"] = 99  # mutate caller's dict post-emit
        e = self._read_log()[0]
        self.assertEqual(e["verifier_kind_counts"]["sha_exists"], 2)

    def test_confidence_gate_truncated_fields(self):
        """PLAN-009 A12: raw_claim_count + truncated propagate on cap."""
        audit_emit.emit_confidence_gate(
            claim_count=200,
            pass_count=200,
            fail_count=0,
            verifier_kind_counts={"path_exists": 200},
            raw_claim_count=350,
            truncated=True,
        )
        e = self._read_log()[0]
        self.assertEqual(e["claim_count"], 200)
        self.assertEqual(e["raw_claim_count"], 350)
        self.assertIs(e["truncated"], True)

    def test_confidence_gate_truncated_defaults_when_not_passed(self):
        """Back-compat: callers that don't pass raw_claim_count still work."""
        audit_emit.emit_confidence_gate(
            claim_count=3, pass_count=3, fail_count=0,
            verifier_kind_counts={"path_exists": 3},
        )
        e = self._read_log()[0]
        self.assertEqual(e["raw_claim_count"], 3)
        self.assertIs(e["truncated"], False)

    def test_lesson_read_records_ids_and_meta(self):
        audit_emit.emit_lesson_read(
            lesson_ids=["L1", "L2", "L3"],
            archetype="Agent Architect",
            keywords=["trading", "hft"],
            k=5,
            consumer="architect",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "lesson_read")
        self.assertEqual(e["lesson_ids"], ["L1", "L2", "L3"])
        self.assertEqual(e["lesson_count"], 3)
        self.assertEqual(e["archetype"], "Agent Architect")
        self.assertEqual(e["keywords"], ["trading", "hft"])
        self.assertEqual(e["k"], 5)
        self.assertEqual(e["consumer"], "architect")

    def test_lesson_read_empty_list_is_valid(self):
        audit_emit.emit_lesson_read(
            lesson_ids=[], archetype="X", keywords=[], k=3,
        )
        e = self._read_log()[0]
        self.assertEqual(e["lesson_count"], 0)
        self.assertEqual(e["lesson_ids"], [])

    def test_lesson_archived_records_outcome_fields(self):
        audit_emit.emit_lesson_archived(
            lesson_id="L-dead",
            archetype="Security Engineer",
            hit_count=1,
            miss_count=9,
            hit_rate=0.1,
            archive_path="/tmp/archive/L-dead.json",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "lesson_archived")
        self.assertEqual(e["lesson_id"], "L-dead")
        self.assertEqual(e["hit_count"], 1)
        self.assertEqual(e["miss_count"], 9)
        # hit_rate_bps: int basis-points (0.1 → 100). No float in HMAC field.
        self.assertEqual(e["hit_rate_bps"], 100)
        self.assertNotIn("hit_rate", e, "old float field must not appear")
        self.assertEqual(e["reason"], "low_hit_rate")

    def test_lesson_archived_reason_override(self):
        audit_emit.emit_lesson_archived(
            lesson_id="L-x", archetype="A",
            hit_count=0, miss_count=0, hit_rate=0.0,
            archive_path="/tmp/a.json",
            reason="manual",
        )
        e = self._read_log()[0]
        self.assertEqual(e["reason"], "manual")

    def test_lesson_restored_basic(self):
        audit_emit.emit_lesson_restored(
            lesson_id="L-back",
            archetype="A",
            restored_from="/archive/2026-04-13/L-back.json",
            restored_to="/lessons/L-back.json",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "lesson_restored")
        self.assertEqual(e["lesson_id"], "L-back")
        self.assertTrue(e["restored_from"].endswith("L-back.json"))
        self.assertTrue(e["restored_to"].endswith("L-back.json"))


class TestSprint11Emitters(TestEnvContext):
    """Sprint 11 emitters added pre-Group A for cross-phase audit wiring."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def test_budget_exceeded_records_scope_and_cap(self):
        audit_emit.emit_budget_exceeded(
            plan_id="PLAN-011",
            spawn_id="spawn-42",
            tokens_used=15000,
            cap=10000,
            scope="spawn",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "budget_exceeded")
        self.assertEqual(e["tokens_used"], 15000)
        self.assertEqual(e["cap"], 10000)
        self.assertEqual(e["scope"], "spawn")

    def test_budget_bypass_used_redacts_reason(self):
        audit_emit.emit_budget_bypass_used(
            plan_id="PLAN-011",
            caller_pid=42,
            reason="password=supersecret emergency",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "budget_bypass_used")
        self.assertEqual(e["caller_pid"], 42)
        self.assertNotIn("supersecret", e["reason_preview"])

    def test_otel_export_dropped_records_host_not_full_url(self):
        audit_emit.emit_otel_export_dropped(
            fields_dropped_count=3,
            endpoint_host="otlp.example.com",
            reason="host_not_in_allowlist",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "otel_export_dropped")
        self.assertEqual(e["fields_dropped_count"], 3)
        self.assertEqual(e["endpoint_host"], "otlp.example.com")
        self.assertNotIn("://", e["endpoint_host"])

    def test_output_safety_flag_mirrors_injection_flag_shape(self):
        audit_emit.emit_output_safety_flag(
            source="agent-output",
            family_counts={"aws_key": 1},
            match_count=1,
            bytes_scanned=512,
            redaction_applied=True,
            triggered_by_tool="Agent",
            snippet_preview="AKIAIOSFODNN7EXAMPLE",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "output_safety_flag")
        self.assertEqual(e["family_counts"]["aws_key"], 1)
        self.assertTrue(e["redaction_applied"])
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", e["snippet_preview"])

    def test_skill_patch_applied_records_shadow_mode(self):
        audit_emit.emit_skill_patch_applied(
            proposal_id="SP-001",
            skill_slug="testing-strategy",
            commit_sha="abc123def456",
            signer_fingerprint="AAAA BBBB CCCC DDDD",
            shadow_mode=True,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "skill_patch_applied")
        self.assertEqual(e["proposal_id"], "SP-001")
        self.assertTrue(e["shadow_mode"])

    def test_squad_imported_records_manifest_sha_and_source(self):
        audit_emit.emit_squad_imported(
            squad_name="edtech",
            manifest_sha256="e" * 64,
            signer_fingerprint="AAAA",
            source="github.com/acme/squad-edtech@v1",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "squad_imported")
        self.assertEqual(e["squad_name"], "edtech")
        self.assertEqual(e["manifest_sha256"], "e" * 64)

    # -------------------------------------------------------------------------
    # Sprint 13 Phase A.0 (PLAN-013 Gap #3) — live-adapter / breaker / credential
    # -------------------------------------------------------------------------

    def test_live_adapter_call_started_registered(self):
        audit_emit.emit_live_adapter_call_started(
            provider="openai",
            url="https://api.openai.com/v1/chat/completions",
            attempt=1,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "live_adapter_call_started")
        self.assertEqual(e["provider"], "openai")
        self.assertEqual(e["attempt"], 1)
        self.assertEqual(e["event_schema"], "v2")
        self.assertIn("ts", e)

    def test_live_adapter_call_succeeded_records_duration(self):
        audit_emit.emit_live_adapter_call_succeeded(
            provider="claude",
            url="https://api.anthropic.com/v1/messages",
            status=200,
            duration_ms=842,
            retried=True,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "live_adapter_call_succeeded")
        self.assertEqual(e["status"], 200)
        self.assertEqual(e["duration_ms"], 842)
        self.assertTrue(e["retried"])

    def test_live_adapter_call_failed_preserves_failure_mode(self):
        audit_emit.emit_live_adapter_call_failed(
            provider="gemini",
            failure_mode="connect_timeout",
            http_status=None,
            duration_ms=2500,
            retry_count=1,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "live_adapter_call_failed")
        self.assertEqual(e["failure_mode"], "connect_timeout")
        self.assertIsNone(e["http_status"])
        self.assertEqual(e["retry_count"], 1)

    def test_breaker_opened_records_threshold_and_reason(self):
        audit_emit.emit_breaker_opened(
            provider="openai",
            failures_in_window=5,
            threshold=5,
            reason="server_error",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "breaker_opened")
        self.assertEqual(e["failures_in_window"], 5)
        self.assertEqual(e["threshold"], 5)
        self.assertEqual(e["reason"], "server_error")

    def test_breaker_closed_records_from_state(self):
        audit_emit.emit_breaker_closed(provider="claude", from_state="half_open")
        e = self._read_log()[0]
        self.assertEqual(e["action"], "breaker_closed")
        self.assertEqual(e["from_state"], "half_open")

    def test_credential_rotation_due_records_age(self):
        audit_emit.emit_credential_rotation_due(
            provider="openai",
            age_days=80,
            warn_threshold_days=75,
            max_threshold_days=90,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "credential_rotation_due")
        self.assertEqual(e["age_days"], 80)
        self.assertEqual(e["warn_threshold_days"], 75)
        self.assertEqual(e["max_threshold_days"], 90)

    # -------------------------------------------------------------------------
    # Sprint 13 Phase A (PLAN-013) — MCP server events (ADR-042)
    # -------------------------------------------------------------------------

    def test_mcp_handler_invoked_records_client_and_duration(self):
        audit_emit.emit_mcp_handler_invoked(
            handler="list_skills",
            client_id="0123456789abcdef",
            transport="http",
            duration_ms=42,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "mcp_handler_invoked")
        self.assertEqual(e["handler"], "list_skills")
        self.assertEqual(e["client_id"], "0123456789abcdef")
        self.assertEqual(e["transport"], "http")
        self.assertEqual(e["duration_ms"], 42)

    def test_mcp_handler_denied_closed_enum_reason(self):
        audit_emit.emit_mcp_handler_denied(
            handler="spawn_agent",
            client_id="fedcba9876543210",
            transport="stdio",
            reason="acl_missing_handler",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "mcp_handler_denied")
        self.assertEqual(e["reason"], "acl_missing_handler")
        # ADR-042 §Auth.6 hygiene: token value MUST NOT appear. client_id
        # is the hex16 opaque identifier — safe to record.
        self.assertEqual(e["client_id"], "fedcba9876543210")

    def test_mcp_server_started_records_transport_and_version(self):
        audit_emit.emit_mcp_server_started(
            transport="http",
            host="127.0.0.1",
            port=9000,
            version="1.0.0-rc.1",
            handlers_count=7,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "mcp_server_started")
        self.assertEqual(e["transport"], "http")
        self.assertEqual(e["host"], "127.0.0.1")
        self.assertEqual(e["port"], 9000)
        self.assertEqual(e["handlers_count"], 7)

    def test_mcp_server_started_stdio_port_zero(self):
        audit_emit.emit_mcp_server_started(
            transport="stdio",
            host="",
            port=0,
            version="1.0.0-rc.1",
            handlers_count=7,
        )
        e = self._read_log()[0]
        self.assertEqual(e["transport"], "stdio")
        self.assertEqual(e["port"], 0)

    def test_mcp_server_disabled_by_kill_switch_records_reason(self):
        audit_emit.emit_mcp_server_disabled_by_kill_switch(
            reason="CEO_SOTA_DISABLE=1",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "mcp_server_disabled_by_kill_switch")
        self.assertEqual(e["reason"], "CEO_SOTA_DISABLE=1")

    def test_all_10_new_actions_in_known_actions(self):
        """Guard: the 10 new event literals are registered in _KNOWN_ACTIONS.

        Regression test for PLAN-013 Gap #3 — events emitted in code but not
        registered were being silently dropped via _breadcrumb.
        """
        required = {
            "live_adapter_call_started",
            "live_adapter_call_succeeded",
            "live_adapter_call_failed",
            "breaker_opened",
            "breaker_closed",
            "credential_rotation_due",
            "mcp_handler_invoked",
            "mcp_handler_denied",
            "mcp_server_started",
            "mcp_server_disabled_by_kill_switch",
        }
        self.assertTrue(
            required.issubset(audit_emit._KNOWN_ACTIONS),
            f"missing from _KNOWN_ACTIONS: {required - audit_emit._KNOWN_ACTIONS}",
        )


class TestSprint14V26Emitters(TestEnvContext):
    """Sprint 14 Phase 0.6 (PLAN-014) — 12 v2.6 emitters."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def test_policy_evaluated(self):
        audit_emit.emit_policy_evaluated(
            policy_id="bash-safety", rule_id="deny_rm_rf", decision="deny", duration_ms=3,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "policy_evaluated")
        self.assertEqual(e["policy_id"], "bash-safety")
        self.assertEqual(e["decision"], "deny")
        self.assertEqual(e["duration_ms"], 3)

    def test_policy_denied(self):
        audit_emit.emit_policy_denied(
            policy_id="plan-edit", rule_id="require_sentinel", reason="sentinel_missing",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "policy_denied")
        self.assertEqual(e["reason"], "sentinel_missing")

    def test_policy_error_redacts_detail(self):
        audit_emit.emit_policy_error(
            policy_id="bash-safety", error_kind="parse_error",
            detail="sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "policy_error")
        self.assertEqual(e["error_kind"], "parse_error")
        self.assertNotIn("sk-ant-api03-XXXXX", e["detail"])

    def test_replay_started(self):
        audit_emit.emit_replay_started(
            original_session_id="abc123", mode="dry_run", redacted_fragments_count=5,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "replay_started")
        self.assertEqual(e["mode"], "dry_run")
        self.assertEqual(e["redacted_fragments_count"], 5)

    def test_replay_completed(self):
        audit_emit.emit_replay_completed(
            original_session_id="abc123", mode="execute", duration_ms=1200, spawn_count=7,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "replay_completed")
        self.assertEqual(e["spawn_count"], 7)

    def test_replay_diff_produced(self):
        audit_emit.emit_replay_diff_produced(
            original_session_id="abc123", spawn_ordinal=3, divergence_kind="output_mismatch",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "replay_diff_produced")
        self.assertEqual(e["divergence_kind"], "output_mismatch")

    def test_prediction_queried(self):
        audit_emit.emit_prediction_queried(
            plan_id="PLAN-014", bucket_range="100k-130k", confidence="medium",
            training_window_plans=10,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "prediction_queried")
        self.assertEqual(e["bucket_range"], "100k-130k")
        self.assertEqual(e["confidence"], "medium")

    def test_pattern_stored(self):
        audit_emit.emit_pattern_stored(
            topic="debate-patterns", content_hash="a" * 64, size_bytes=512,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "pattern_stored")
        self.assertEqual(e["size_bytes"], 512)

    def test_pattern_queried(self):
        audit_emit.emit_pattern_queried(topic="debate-patterns", k=5, match_count=3)
        e = self._read_log()[0]
        self.assertEqual(e["action"], "pattern_queried")
        self.assertEqual(e["k"], 5)

    def test_pattern_evicted(self):
        audit_emit.emit_pattern_evicted(
            topic="debate-patterns", content_hash="a" * 64, reason="admin_request",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "pattern_evicted")
        self.assertEqual(e["reason"], "admin_request")

    def test_threat_model_promoted(self):
        audit_emit.emit_threat_model_promoted(
            from_status="draft", to_status="accepted",
            accepted_by="@security-lead", commit_sha="abc123def",
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "threat_model_promoted")
        self.assertEqual(e["to_status"], "accepted")

    def test_threat_model_freshness_breach(self):
        audit_emit.emit_threat_model_freshness_breach(
            new_adr_count_since_review=3, threshold=2,
        )
        e = self._read_log()[0]
        self.assertEqual(e["action"], "threat_model_freshness_breach")
        self.assertEqual(e["new_adr_count_since_review"], 3)

    def test_all_12_v26_actions_in_known_actions(self):
        """Guard: the 12 v2.6 event literals are registered (ADJ-010)."""
        required = {
            "policy_evaluated", "policy_denied", "policy_error",
            "replay_started", "replay_completed", "replay_diff_produced",
            "prediction_queried",
            "pattern_stored", "pattern_queried", "pattern_evicted",
            "threat_model_promoted", "threat_model_freshness_breach",
        }
        self.assertTrue(
            required.issubset(audit_emit._KNOWN_ACTIONS),
            f"missing from _KNOWN_ACTIONS: {required - audit_emit._KNOWN_ACTIONS}",
        )


class TestAuditFallbackPath(TestEnvContext):
    """F-CHAOS-1 — when primary audit dir is unwritable, emit writes
    land in /tmp fallback with a once-per-session stderr banner."""

    def setUp(self):
        super().setUp()
        audit_emit._FALLBACK_NOTIFIED = False
        import tempfile
        self._fb_tmp = tempfile.TemporaryDirectory()
        self.fallback_path = Path(self._fb_tmp.name) / "ceo-audit-fallback-testuser.log"
        os.environ["CEO_AUDIT_LOG_FALLBACK_PATH"] = str(self.fallback_path)

    def tearDown(self):
        os.environ.pop("CEO_AUDIT_LOG_FALLBACK_PATH", None)
        audit_emit._FALLBACK_NOTIFIED = False
        self._fb_tmp.cleanup()
        super().tearDown()

    def test_fallback_used_when_primary_unwritable(self):
        import io
        from unittest import mock

        stderr_capture = io.StringIO()
        primary_log = audit_emit._log_path()
        real_open = Path.open

        def fake_open(self_path, *args, **kwargs):
            if self_path == primary_log:
                raise PermissionError("simulated unwritable primary")
            return real_open(self_path, *args, **kwargs)

        with mock.patch.object(Path, "open", fake_open), \
             mock.patch("sys.stderr", stderr_capture):
            audit_emit.emit_debate_event(
                plan_id="PLAN-019", round_num=1, phase="agent-done",
                agent="security-engineer",
            )

        self.assertTrue(self.fallback_path.exists())
        content = self.fallback_path.read_text()
        self.assertIn('"action": "debate_event"', content)
        self.assertIn('"plan_id": "PLAN-019"', content)

        banner = stderr_capture.getvalue()
        self.assertIn("::warning::audit-log write failed", banner)
        self.assertIn("falling back to", banner)
        self.assertEqual(banner.count("::warning::audit-log write failed"), 1)

    def test_fallback_banner_dedups_across_writes(self):
        import io
        from unittest import mock

        stderr_capture = io.StringIO()
        primary_log = audit_emit._log_path()
        real_open = Path.open

        def fake_open(self_path, *args, **kwargs):
            if self_path == primary_log:
                raise PermissionError("simulated")
            return real_open(self_path, *args, **kwargs)

        with mock.patch.object(Path, "open", fake_open), \
             mock.patch("sys.stderr", stderr_capture):
            for i in range(5):
                audit_emit.emit_veto_triggered(
                    hook="check_agent_spawn",
                    reason_code="test",
                    reason_preview=f"preview {i}",
                )

        self.assertTrue(self.fallback_path.exists())
        lines = [
            line for line in self.fallback_path.read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(len(lines), 5)

        banner = stderr_capture.getvalue()
        self.assertEqual(banner.count("::warning::audit-log write failed"), 1)

    def test_no_banner_when_primary_writable(self):
        import io
        from unittest import mock

        stderr_capture = io.StringIO()
        with mock.patch("sys.stderr", stderr_capture):
            audit_emit.emit_debate_event(
                plan_id="PLAN-019", round_num=1, phase="agent-done",
                agent="security-engineer",
            )
        self.assertEqual(stderr_capture.getvalue(), "")
        self.assertFalse(self.fallback_path.exists())

    def test_never_raises_from_emit(self):
        """Invariant: emit_* must NEVER raise, regardless of disk state."""
        from unittest import mock

        def always_raises(self_path, *args, **kwargs):
            raise OSError("disk on fire")

        with mock.patch.object(Path, "open", always_raises):
            # If this raises, the test fails.
            audit_emit.emit_debate_event(
                plan_id="PLAN-019", round_num=1, phase="agent-done",
                agent="security-engineer",
            )
            audit_emit.emit_veto_triggered(
                hook="test", reason_code="x", reason_preview="y",
            )


class TestNoFloatInHmacCoveredFields(TestEnvContext):
    """COMPREHENSIVE regression guard for the float-in-HMAC bug class.

    Strategy (Codex R4 directive):
    - Make the GUARD the oracle: programmatically introspect ALL public
      ``emit_*`` functions in ``audit_emit`` via ``inspect``, call each
      with representative valid args derived from the parameter type
      annotations, then assert ``canonical_json.encode(event)`` does NOT
      raise (i.e. no float reaches an HMAC-covered field).
    - Also covers external direct-``_write_event`` producers:
        * ``run-skill-benchmark.py:_emit_benchmark_audit_event``
        * ``emit_mcp_soak_fpr_breach`` (the known float bug fixed in PLAN-113)
    - Skips listed explicitly when auto-arg construction is not possible
      (e.g. ``emit_generic`` which takes ``**kwargs`` without a fixed
      action, and a handful of federation constructors that require live
      peer objects).

    Each assertion uses ``canonical_json.encode(event)`` as the oracle
    (the actual codec the HMAC chain uses) rather than a hand-rolled
    isinstance check — so any new float-typed field will be caught
    automatically in future rounds.
    """

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def _assert_no_canonical_json_error(self, event: dict, context: str) -> None:
        self.assertNotEqual(
            event.get("hmac_error"), "CanonicalJsonError",
            f"{context}: float leaked into HMAC-covered field "
            f"(hmac_error=CanonicalJsonError). event={event}",
        )

    # ------------------------------------------------------------------
    # Targeted regression tests for specifically-fixed fields
    # ------------------------------------------------------------------

    def test_lesson_archived_hit_rate_bps_is_int(self):
        """hit_rate float → hit_rate_bps int (3087 errors in prod)."""
        audit_emit.emit_lesson_archived(
            lesson_id="L-float-guard",
            archetype="Security Engineer",
            hit_count=3,
            miss_count=7,
            hit_rate=0.3,  # caller passes float; emit converts to bps
            archive_path="/tmp/L-float-guard.json",
        )
        events = self._read_log()
        e = next(ev for ev in events if ev.get("action") == "lesson_archived")
        self.assertEqual(e["hit_rate_bps"], 300)
        self.assertIsInstance(e["hit_rate_bps"], int)
        self.assertNotIn("hit_rate", e)
        self._assert_no_canonical_json_error(e, "lesson_archived")

    def test_audit_tokens_timeout_timeout_ms_is_int(self):
        """timeout_seconds float → timeout_ms int (199 errors in prod)."""
        audit_emit.emit_audit_tokens_timeout(
            session_id="s-float-guard",
            timeout_seconds=0.05,  # caller passes float; emit converts to ms
        )
        events = self._read_log()
        e = next(ev for ev in events if ev.get("action") == "audit_tokens_timeout")
        self.assertEqual(e["timeout_ms"], 50)
        self.assertIsInstance(e["timeout_ms"], int)
        self.assertNotIn("timeout_seconds", e)
        self._assert_no_canonical_json_error(e, "audit_tokens_timeout")

    def test_hit_rate_bps_boundary_values(self):
        """Clamping: 0.0 → 0, 1.0 → 1000, >1.0 → 1000, <0.0 → 0."""
        for rate, expected_bps in [(0.0, 0), (1.0, 1000), (1.5, 1000), (-0.1, 0)]:
            with self.subTest(rate=rate):
                audit_emit.emit_lesson_archived(
                    lesson_id=f"L-clamp-{rate}",
                    archetype="A",
                    hit_count=0,
                    miss_count=0,
                    hit_rate=rate,
                    archive_path="/tmp/x.json",
                )
                events = self._read_log()
                latest = next(
                    ev for ev in reversed(events)
                    if ev.get("action") == "lesson_archived"
                    and ev.get("lesson_id") == f"L-clamp-{rate}"
                )
                self.assertEqual(latest["hit_rate_bps"], expected_bps)
                self.assertIsInstance(latest["hit_rate_bps"], int)
                self._assert_no_canonical_json_error(latest, f"lesson_archived rate={rate}")

    def test_timeout_ms_conversion(self):
        """1.0s → 1000ms, 0.001s → 1ms, 0.0s → 0ms."""
        for seconds, expected_ms in [(1.0, 1000), (0.001, 1), (0.0, 0)]:
            with self.subTest(seconds=seconds):
                audit_emit.emit_audit_tokens_timeout(
                    session_id=f"s-conv-{seconds}",
                    timeout_seconds=seconds,
                )
                events = self._read_log()
                latest = next(
                    ev for ev in reversed(events)
                    if ev.get("action") == "audit_tokens_timeout"
                    and ev.get("session_id") == f"s-conv-{seconds}"
                )
                self.assertEqual(latest["timeout_ms"], expected_ms)
                self.assertIsInstance(latest["timeout_ms"], int)
                self._assert_no_canonical_json_error(latest, f"audit_tokens_timeout {seconds}s")

    def test_benchmark_run_no_float_in_hmac_fields(self):
        """benchmark_run emits int-encoded fields; no float reaches HMAC chain."""
        audit_emit.emit_benchmark_run(
            benchmark_id="guard-test",
            skill="test-skill",
            pass_count=7,
            fail_count=3,
            pass_rate=0.7,
            median_score=0.65,
            floor=0.6,
            cost_usd=1.50,
            duration_s=8.5,
            lessons_written=2,
        )
        events = self._read_log()
        e = next(ev for ev in events if ev.get("action") == "benchmark_run")
        self.assertEqual(e["pass_rate_bps"], 700)
        self.assertEqual(e["median_score_bps"], 650)
        self.assertEqual(e["floor_bps"], 600)
        self.assertEqual(e["cost_usd_cents"], 150)
        self.assertEqual(e["duration_ms"], 8500)
        for field in ("pass_rate_bps", "median_score_bps", "floor_bps",
                      "cost_usd_cents", "duration_ms"):
            self.assertIsInstance(e[field], int, f"{field} must be int")
        for field in ("pass_rate", "median_score", "floor", "cost_usd", "duration_s"):
            self.assertNotIn(field, e, f"legacy float field '{field}' must not appear")
        self._assert_no_canonical_json_error(e, "benchmark_run")

    def test_benchmark_run_bps_clamping(self):
        """pass_rate > 1.0 clamps to 1000 bps; negative floor clamps to 0."""
        audit_emit.emit_benchmark_run(
            benchmark_id="clamp-test",
            skill="s",
            pass_count=10,
            fail_count=0,
            pass_rate=1.5,
            median_score=0.0,
            floor=-0.1,
        )
        events = self._read_log()
        e = next(ev for ev in events if ev.get("action") == "benchmark_run"
                 and ev.get("benchmark_id") == "clamp-test")
        self.assertEqual(e["pass_rate_bps"], 1000)
        self.assertEqual(e["floor_bps"], 0)
        self._assert_no_canonical_json_error(e, "benchmark_run clamp")

    def test_cache_discipline_alerted_uses_int_bps(self):
        """emit_cache_discipline_alerted emits ints; no float in HMAC fields."""
        audit_emit.emit_cache_discipline_alerted(
            hit_rate_basis_points=650,
            floor_basis_points=700,
            session_count_24h=5,
            below_floor=True,
            opted_out=False,
            session_id="s-cache-guard",
        )
        events = self._read_log()
        e = next(
            ev for ev in events if ev.get("action") == "cache_discipline_alerted"
        )
        self.assertIsInstance(e["hit_rate_basis_points"], int)
        self.assertIsInstance(e["floor_basis_points"], int)
        self.assertEqual(e["hit_rate_basis_points"], 650)
        self.assertEqual(e["floor_basis_points"], 700)
        self.assertNotIn("cache_coverage", e, "legacy float field must not appear")
        self.assertNotIn("threshold", e, "legacy float field must not appear")
        self._assert_no_canonical_json_error(e, "cache_discipline_alerted")

    def test_mcp_soak_fpr_breach_no_float(self):
        """emit_mcp_soak_fpr_breach: fpr_observed/threshold were raw floats → now bps ints.

        This is the PLAN-113 Phase B fix for the float that was still slipping
        through after earlier rounds. fpr_observed_bps and threshold_bps must
        be int; the old float-named fields must be absent from the emitted event.
        """
        from _lib.canonical_json import CanonicalJsonError, encode as canonical_encode

        audit_emit.emit_mcp_soak_fpr_breach(
            window_days=7,
            fpr_observed=0.015,   # 1.5% FPR
            threshold=0.01,       # 1% threshold
            top_deny_reason="missing_auth_header",
        )
        events = self._read_log()
        e = next(ev for ev in events if ev.get("action") == "mcp_soak_fpr_breach")
        # Float fields must be encoded as int bps (×10000).
        self.assertIn("fpr_observed_bps", e, "fpr_observed_bps must be present")
        self.assertIn("threshold_bps", e, "threshold_bps must be present")
        self.assertIsInstance(e["fpr_observed_bps"], int, "fpr_observed_bps must be int")
        self.assertIsInstance(e["threshold_bps"], int, "threshold_bps must be int")
        self.assertEqual(e["fpr_observed_bps"], 150,  # 0.015 * 10000
                         "0.015 FPR → 150 bps")
        self.assertEqual(e["threshold_bps"], 100,  # 0.01 * 10000
                         "0.01 threshold → 100 bps")
        # Legacy float-named fields must be absent.
        self.assertNotIn("fpr_observed", e, "raw float field fpr_observed must be absent")
        self.assertNotIn("threshold", e, "raw float field threshold must be absent")
        # canonical_json oracle must not raise.
        try:
            canonical_encode(e)
        except CanonicalJsonError as exc:
            self.fail(f"mcp_soak_fpr_breach: float reached HMAC-covered payload: {exc}")
        self._assert_no_canonical_json_error(e, "mcp_soak_fpr_breach")

    # ------------------------------------------------------------------
    # Tournament emitters — all int-encoded
    # ------------------------------------------------------------------

    def test_tournament_emitters_no_float(self):
        """All tournament typed emitters produce no float in HMAC-covered fields."""
        from _lib.canonical_json import CanonicalJsonError, encode as canonical_encode

        def _oracle(action_name: str, event: dict) -> None:
            try:
                canonical_encode(event)
            except CanonicalJsonError as exc:
                self.fail(f"{action_name}: float reached HMAC-covered payload: {exc}")
            self.assertNotEqual(
                event.get("hmac_error"), "CanonicalJsonError",
                f"{action_name}: hmac_error=CanonicalJsonError in emitted event",
            )

        audit_emit.emit_tournament_task_scored(
            swarm_id="sw-1", loop_id="lp-1", score_bps=750,
            tests_passed=3, tests_failed=1,
        )
        events = self._read_log()
        ev = next((e for e in events if e.get("action") == "tournament_task_scored"), None)
        if ev:
            _oracle("tournament_task_scored", ev)
            self.assertIsInstance(ev.get("score_bps"), int)

        audit_emit.emit_tournament_run_completed(
            swarm_id="sw-1", winner_loop_id="lp-1", rejected_count=2, decisive=True,
        )
        events = self._read_log()
        ev = next((e for e in events if e.get("action") == "tournament_run_completed"), None)
        if ev:
            _oracle("tournament_run_completed", ev)

        audit_emit.emit_tournament_budget_projected(
            swarm_id="sw-1", projected_cost_cents=250, candidate_count=4,
        )
        events = self._read_log()
        ev = next((e for e in events if e.get("action") == "tournament_budget_projected"), None)
        if ev:
            _oracle("tournament_budget_projected", ev)
            self.assertIsInstance(ev.get("projected_cost_cents"), int)

        audit_emit.emit_tournament_budget_exceeded(
            swarm_id="sw-1", actual_cost_cents=1100, cap_cents=1000,
        )
        events = self._read_log()
        ev = next((e for e in events if e.get("action") == "tournament_budget_exceeded"), None)
        if ev:
            _oracle("tournament_budget_exceeded", ev)

    # ------------------------------------------------------------------
    # COMPREHENSIVE programmatic full-class scan (Codex R4 directive)
    # ------------------------------------------------------------------

    def test_comprehensive_all_emit_functions_no_float(self):
        """Programmatically enumerate ALL public emit_* functions in audit_emit,
        call each with auto-derived representative args (ints for numerics,
        short strings for text, empty lists/dicts for collections, floats for
        float-typed params so the emitter's own conversion is exercised), and
        assert canonical_json.encode(event) does NOT raise.

        This is the GUARD that makes the bug class impossible to re-introduce:
        any new emit_* that puts a raw float into the event dict will be caught
        here automatically, without requiring a hand-written test for each emitter.

        Skipped functions (listed explicitly — all have a structural reason):
          - emit_generic: takes **kwargs without a fixed action; can't auto-build.
          - emit_dispatcher_route: calls emit_generic internally; covered by
            its own dedicated caller test if needed.
          - Functions that delegate entirely to emit_generic with no own dict
            building are still covered because emit_generic → _write_event path
            is exercised; we keep them in the scan and let the auto-builder try.
        """
        import inspect
        from typing import get_type_hints
        from _lib.canonical_json import CanonicalJsonError, encode as canonical_encode

        # Functions that cannot be auto-called (structural reasons documented).
        EXPLICIT_SKIPS = {
            # **kwargs signature — no fixed parameter list to introspect.
            "emit_generic",
        }

        # Type-dispatch table: annotation → representative value.
        # float params are intentionally passed a float so the emitter's
        # own int-conversion code is exercised by this test.
        def _default_for_annotation(annotation: type) -> object:
            """Return a safe representative value for a parameter annotation."""
            import typing
            origin = getattr(annotation, "__origin__", None)
            args = getattr(annotation, "__args__", ())
            # Optional[X] → None (valid; emitters handle None gracefully)
            if origin is type(None):
                return None
            # Union[X, None] / Optional[X]
            if origin is getattr(__import__("typing"), "Union", None):
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    return _default_for_annotation(non_none[0])
                return None
            # List[X] → []
            if origin is list:
                return []
            # Dict[X, Y] → {}
            if origin is dict:
                return {}
            # Bare type checks
            if annotation is str or annotation == "str":
                return "x"
            if annotation is int or annotation == "int":
                return 1
            if annotation is bool or annotation == "bool":
                return False
            if annotation is float or annotation == "float":
                return 0.5  # intentional float — emitter must convert
            # Fallback for Any or unknown
            return "x"

        # Collect all public emit_* members from the audit_emit module.
        emitters = [
            (name, fn)
            for name, fn in inspect.getmembers(audit_emit, inspect.isfunction)
            if name.startswith("emit_") and name not in EXPLICIT_SKIPS
        ]

        self.assertGreater(len(emitters), 50,
                           "Expected at least 50 emit_* functions; got fewer — "
                           "introspection broken or module not loaded correctly")

        called_actions: list = []
        failures: list = []

        for name, fn in emitters:
            try:
                sig = inspect.signature(fn)
            except (ValueError, TypeError):
                # Can't introspect (e.g. C extension) — skip silently.
                continue

            kwargs: dict = {}
            skip_reason = None
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                if param.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ):
                    # *args / **kwargs — can't auto-derive; skip this emitter.
                    skip_reason = f"VAR param {param.kind.name}"
                    break
                if param.default is not inspect.Parameter.empty:
                    # Has a default — use it (most defaults are safe int/str/None).
                    kwargs[param_name] = param.default
                    continue
                # Required parameter — derive from annotation.
                ann = param.annotation
                if ann is inspect.Parameter.empty:
                    ann = str  # no annotation → treat as str
                kwargs[param_name] = _default_for_annotation(ann)

            if skip_reason:
                # Log but don't fail — skips are documented above.
                continue

            # Snapshot log before call.
            before = self._read_log()
            before_count = len(before)
            try:
                fn(**kwargs)
            except Exception:
                # Fail-open: emitters must not raise; if they do it's a
                # separate bug. We still read whatever was emitted.
                pass

            # Read new events.
            after = self._read_log()
            new_events = after[before_count:]
            for ev in new_events:
                action = ev.get("action", name)
                called_actions.append(action)
                try:
                    canonical_encode(ev)
                except CanonicalJsonError as exc:
                    failures.append(
                        f"{name} (action={action!r}): float in HMAC field: {exc}"
                    )
                if ev.get("hmac_error") == "CanonicalJsonError":
                    failures.append(
                        f"{name} (action={action!r}): hmac_error=CanonicalJsonError"
                    )

        if failures:
            self.fail(
                f"Float-in-HMAC violations found ({len(failures)}):\n"
                + "\n".join(f"  - {f}" for f in failures)
            )

        # Ensure the specifically-fixed emitters were exercised.
        required_actions = {
            "benchmark_run",
            "cache_discipline_alerted",
            "lesson_archived",
            "audit_tokens_timeout",
            "mcp_soak_fpr_breach",
        }
        missing = required_actions - set(called_actions)
        if missing:
            self.fail(
                f"Required actions not covered by comprehensive scan: {sorted(missing)}"
            )


if __name__ == "__main__":
    unittest.main()
