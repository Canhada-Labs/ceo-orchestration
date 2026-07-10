"""PLAN-050 Phase 1c F-02-08 — audit_emit public API contract test.

Pins the public surface of `.claude/hooks/_lib/audit_emit.py` so that
the package-split refactor (F-02-08) cannot silently remove or rename
any emitter. Required to be staged + GREEN in the monolith BEFORE the
kernel-batch-phase-1c.py applies the split (per design doc §Stage 1).

Post-split, the SAME test MUST remain green against the shim facade.
Any change to the pinned list requires:
- ADR entry justifying add/remove
- Updated SHA256 of `_KNOWN_ACTIONS` in this test
- Updated memory + CLAUDE.md CHANGELOG

Captured baseline (Session 54, 2026-04-22):
- 50 public emitter/iterator functions
- 89 `_KNOWN_ACTIONS` entries
- SHA256(sorted(_KNOWN_ACTIONS)) = 4082e9b3377… first-16
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

# Codex iter 2 P1-2 closure. The contract test is **promotion-canonical**:
# the staged copy (under ``.claude/plans/PLAN-081/staging/phase-2/tests/``)
# is forensic only. Ceremony Block 3 ``cp``s it to
# ``.claude/hooks/tests/test_audit_emit_api_contract.py``; Block 4
# runs ``pytest`` against the canonical-position file where the project
# root + ``.claude/hooks/`` is already on ``sys.path``. From staging
# position pre-ceremony, this test imports the *pre-Phase-2* canonical
# audit_emit and asserts the *Phase-2* expected baseline — it fails as
# expected and that failure IS the gate. Pre-ceremony validation of
# the staged audit_emit content is performed by the iter-N harness
# documented in PLAN-081 §14 (manual subprocess copy of staged
# ``audit_emit.py`` into a temp tree).
#
# The conditional path injection below adds ``.claude/hooks/`` to
# ``sys.path`` when running from the staging position, so the test
# can at least *import* the canonical module + report the contract
# drift instead of crashing with ``ModuleNotFoundError``. ADR-010
# forbids a staged ``conftest.py`` (``.claude/**/conftest.py`` is in
# ``_CANONICAL_GUARDS``), so the path setup must live in this file.
_THIS_FILE = Path(__file__).resolve()
_IS_STAGING = "staging" in _THIS_FILE.parts and "phase-2" in _THIS_FILE.parts
if _IS_STAGING:
    # File path:
    #   <repo>/.claude/plans/PLAN-081/staging/phase-2/tests/<this>.py
    # parents[0] = .../tests
    # parents[1] = .../phase-2
    # parents[2] = .../staging
    # parents[3] = .../PLAN-081
    # parents[4] = .../plans
    # parents[5] = .../.claude
    # parents[6] = <repo>            ← repo root (Codex iter 3 P1-1 fix)
    _REPO_ROOT = _THIS_FILE.parents[6]
    _CANONICAL_HOOKS = _REPO_ROOT / ".claude" / "hooks"
    if str(_CANONICAL_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CANONICAL_HOOKS))


from _lib import audit_emit  # noqa: E402


# -- Public API surface (alphabetical) --------------------------------------
# Pinned 2026-04-22. Every emit_* / iter_* function callable via
# `from _lib import audit_emit; audit_emit.<name>`. Matches output of
# `grep -nE '^def (emit_|iter_)' _lib/audit_emit.py | awk '{print $2}'`.
_EXPECTED_PUBLIC_SYMBOLS = frozenset({
    # PLAN-059 SEC-P0-04 / ADR-080 (Session 62 cont, 2026-04-25) — audit-tokens
    # content-ban emitters (counts-only allowlist enforcement).
    "emit_audit_tokens_emitted",
    "emit_audit_tokens_key_dropped",
    "emit_audit_tokens_timeout",
    "emit_benchmark_run",
    "emit_breaker_closed",
    "emit_breaker_opened",
    "emit_budget_bypass_used",
    "emit_budget_exceeded",
    # PLAN-065 Phase 2 / ADR-098 (S82 ceremony lote, 2026-05-04) —
    # /ceo-boot session-boot autopilot emits ceo_boot_emitted (per-boot
    # lifecycle) + ceo_boot_check_skipped (per-check timeout). Sec MF-3
    # field allowlist enforced via _scrub_ceo_boot_event. Closes
    # Reality-Ledger fixture #4 (declared-but-not-wired pattern from
    # PLAN-071 Phase 0 baseline detector D4).
    "emit_ceo_boot_check_skipped",
    "emit_ceo_boot_emitted",
    "emit_ceo_boot_persona_coverage_score",  # PLAN-093 Wave C.5 (S123)
    "emit_confidence_gate",
    "emit_credential_rotation_due",
    "emit_debate_event",
    "emit_generic",
    "emit_injection_flag",
    "emit_lesson_archived",
    "emit_lesson_outcome",
    "emit_lesson_outcome_undone",
    "emit_lesson_read",
    "emit_lesson_restored",
    "emit_lesson_write",
    "emit_live_adapter_call_failed",
    "emit_live_adapter_call_started",
    "emit_live_adapter_call_succeeded",
    "emit_mcp_handler_denied",
    "emit_mcp_handler_invoked",
    "emit_mcp_injection_finding",  # PLAN-044 audit-v2 Wave B (ADR-083)
    "emit_mcp_server_disabled_by_kill_switch",
    "emit_mcp_server_started",
    "emit_otel_export_dropped",
    "emit_output_safety_flag",
    "emit_output_scan_finding",
    "emit_pattern_evicted",
    "emit_pattern_queried",
    "emit_pattern_stored",
    "emit_plan_transition",
    "emit_policy_denied",
    "emit_policy_error",
    "emit_policy_evaluated",
    "emit_prediction_queried",
    "emit_prompt_submitted",
    "emit_replay_capture_completed",
    "emit_replay_capture_started",
    "emit_replay_completed",
    "emit_replay_diff_produced",
    "emit_replay_started",
    "emit_session_end",
    "emit_session_start",
    "emit_session_stop",
    "emit_skill_patch_applied",
    "emit_squad_imported",
    "emit_state_store_pruned",
    "emit_state_store_read",
    "emit_state_store_write",
    "emit_threat_model_freshness_breach",
    "emit_threat_model_promoted",
    # PLAN-125 WS-1 (kooky-harvest) — per-tool-call lifecycle telemetry.
    # Deny-by-default scrub-branch + _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST;
    # closed enums tool_name_enum (MF-SEC-1) + duration_bucket (MF-SEC-3).
    "emit_tool_call_lifecycle_recorded",
    "emit_learning_rail_disabled",  # PLAN-154 A12 typed emitter (ADR-160 D8)
    # PLAN-155 Wave 4 (Codex harness audit chain / SENT-CX-B, ADR-161) — two
    # metadata-only typed emitters. Deny-by-default scrub-branch +
    # _CODEX_TOOL_RECORDED_ALLOWLIST / _CODEX_TURN_ENDED_ALLOWLIST; closed
    # enums (tool_name_enum -> other, source -> other, harness -> codex).
    "emit_codex_tool_recorded",
    "emit_codex_turn_ended",
    # PLAN-124 WS-1 (ECC value-harvest) — git hook-bypass guard breadcrumb.
    # Deny-by-default scrub-branch + _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST;
    # the ONLY caller field is the closed-enum flag_class (MF-G), never the
    # matched command bytes.
    "emit_git_hook_bypass_blocked",
    # PLAN-135 W2 H5 (ADR-154 single-rewriter) — corrective bash-input
    # rewrite breadcrumb. Deny-by-default scrub-branch +
    # _BASH_INPUT_REWRITTEN_ALLOWLIST; the ONLY caller fields are the
    # closed-enum rewrite_class + the before/after sha256 hash pair, never
    # the command bytes (the hash pair proves audited-cmd == executed-cmd).
    "emit_bash_input_rewritten",
    # PLAN-135 W2 H3 (subagent lifecycle bracket) — TYPED wrapper for the
    # SubagentStop per-agent emit. Deny-by-default scrub-branch +
    # _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST; every caller field is a closed
    # enum or coarse bucket (agent_archetype + wall/token/claim brackets),
    # never a raw count, transcript path/body or marker snippet.
    "emit_subagent_lifecycle_observed",
    "emit_veto_triggered",
    # PLAN-078 Wave 1+W2 (S89 Fase 1 commit 2cb1472, registered S92 Wave 1b
    # ceremony, 2026-05-07) — Reality Ledger advisory emitters. Wave 1
    # ships model_routing_advised; Wave 2 ships estimate_drift_detected +
    # estimate_drift_systematic_bias. Sec MF-3 enforced via dedicated
    # `_FORBIDDEN_FIELDS_*` allowlists in audit_emit.py.
    "emit_estimate_drift_detected",
    "emit_estimate_drift_systematic_bias",
    "emit_model_routing_advised",
    # PLAN-078 Wave 5 (S95 ceremony 2026-05-08) — TaskCreate-candidate
    # orchestration. Emitted by ceo-boot.py per `<!-- TASKCREATE-CANDIDATE -->`
    # marker block written when gate_pass=False AND severity≥medium. Sec MF-3
    # 4-field allowlist enforced via _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST.
    "emit_ceo_boot_task_candidate_emitted",
    # PLAN-075 v1.13.x patch (S96-cont-2 ceremony 2026-05-09) / ADR-106 + ADR-110 —
    # Pair-Rail Multi-LLM cross-review hook events. Wired by check_pair_rail.py
    # PreToolUse on Edit|Write|MultiEdit against L3+ canonical-guarded paths.
    # Registered with KERNEL_OVERRIDE bypass since audit_emit.py is in _KERNEL_PATHS.
    "emit_pair_rail_codex_unavailable",
    "emit_pair_rail_codex_violation",
    "emit_pair_rail_review_passed",
    "emit_pair_rail_sentinel_bypass",
    # PLAN-081 Phase 1-full / R1 S-Sec-5 (S99 ceremony 2026-05-09) —
    # ingress sanitization PostToolUse emitter (mcp__codex__codex /
    # mcp__codex__codex-reply matchers; emits forensic event when
    # Codex stdout contains harness-mimicry / xml-system-tag /
    # tool-use-forgery patterns). ADVISORY only per ADR-106.
    "emit_pair_rail_codex_injection_detected",
    # PLAN-081 Phase 2 (S100 ceremony 2026-05-10) — dispatcher
    # routing-matrix decision audit emitter (called by
    # inject-agent-context.sh --pair-mode dispatch path). Carries
    # archetype + rail + reason_code + matrix SHA prefix +
    # wall_clock_ms (int per Codex iter 1 P0-1 canonical_json no-float
    # invariant). Sec MF-3 enforced via _DISPATCHER_ROUTE_EMIT_ALLOWLIST
    # + dispatch-gate scrub.
    "emit_dispatcher_route",
    # PLAN-081 Phase 3 (S100 ceremony 2026-05-10) — Asymmetric VETO
    # matrix Cases A-F decision audit emitter (called by
    # check_pair_rail.py:_decide_with_matrix() once per Pair-Rail
    # PreToolUse evaluation that reaches the matrix arm). Carries
    # case + claude_verdict + codex_verdict + precondition_met +
    # rubric_violation_id + severity + jaccard_bucket + grace_h.
    # Sec MF-3 enforced via _PAIR_RAIL_CASE_EMIT_ALLOWLIST + dispatch-gate
    # scrub. Source action for fp_rate_30d + disagreement_rate_30d
    # predicate aggregators. ADR-107 + ADR-108 ACCEPTED gate.
    "emit_pair_rail_case",
    # PLAN-081 Phase 4 (S100 ceremony 2026-05-10) — promotion gate
    # verdict audit emitter (called by .claude/scripts/run-promotion-gate.py
    # at end of each locked-corpus run). Carries run_id + verdict +
    # corpus_n + manifest_sha + catch_rate + bucketed metrics + tool
    # versions. Sec MF-3 enforced via _PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST
    # + dispatch-gate scrub. ADR-111 ACCEPTED gate.
    "emit_pair_rail_promotion",
    "iter_events",
    "emit_token_budget_guard_paused",  # PLAN-083 Wave 0a/0b (S106 2026-05-11)
    "emit_anti_ceo_overhead_block",  # PLAN-083 Wave 0a/0b (S106 2026-05-11)
    "emit_anti_ceo_overhead_override_used",  # PLAN-083 Wave 0a/0b (S106 2026-05-11)
    "emit_smart_loading_resolved",  # PLAN-083 Wave 0a/0b (S106 2026-05-11)
    # PLAN-085 v1.19.0 (S111 2026-05-12) — Wave C identity/credentials (5).
    "emit_live_adapter_blocked",
    "emit_credential_blocked_due_to_age",
    "emit_credential_emergency_override_used",
    # PLAN-117 WS-A (S176) — ADR-040-AMEND-2 §Layer-1 late-set forensic.
    "emit_credential_override_late_set_ignored",
    "emit_mcp_bearer_replay_rejected",
    "emit_mcp_non_loopback_rejected",
    # PLAN-085 v1.19.0 (S111 2026-05-12) — Wave G.1b ATLAS schema (4).
    "emit_prompt_injection_detected",
    "emit_secret_leak_detected",
    "emit_pii_redacted_outgoing",
    "emit_codex_egress_redacted",
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (S161 / ADR-114 F-7.9) —
    # wires the registered-but-un-wired pair_rail_outgoing_redaction_applied
    # action (allowlist + dispatch-gate + typed helper). No new _KNOWN_ACTIONS
    # entry (the name was already counted), so the SHA256/count(258) are
    # unchanged; only this public-emitter set gains the typed wrapper.
    "emit_pair_rail_outgoing_redaction_applied",
    # PLAN-088 canonical-13 god-mode auto-activation (S114 Wave 1) — 12
    # new typed emit_* wrappers (11 net-new + 1 ATLAS-binding wire on
    # pre-existing mcp_route_advised stub from PLAN-086 Wave D).
    # ADR-118 PROPOSED W4.3; capability_surface_delta=0 per §3 SHA-pin
    # table; ATLAS bindings per W0 canonical-13 table.
    "emit_anthropic_429_observed",
    "emit_batch_dispatched",
    "emit_cache_discipline_alerted",
    "emit_codex_invoke_dispatched",
    "emit_cookbook_pattern_advised",
    "emit_estimate_calibrator_pipeline_run",
    "emit_first_run_wizard_dispatched",
    "emit_git_index_lock_retry",
    "emit_mcp_route_advised",
    "emit_pair_rail_phase_advanced",
    "emit_subagent_findings_partial_drop",
    "emit_tier_policy_misrouting_advised",
    # PLAN-116 (S172 2026-05-27) — dedicated tier-policy loader advisory-fallback
    # action (replaces the tier_policy_misrouting_advised piggyback that dropped
    # a free-text `reason` field on every emit). No new ADR (mechanical
    # registration; precedented by swarm_layer_3_4_blocked / persona_coverage).
    "emit_tier_policy_loader_fallback_observed",
    # PLAN-118 AC-B5 (S179 2026-05-28) — producer-side fail-CLOSED forensic
    # breadcrumb for canonical-resolution mismatch (chokepoint=
    # chain_reset_marker | spool_drain). Closed-enum payload (chokepoint +
    # reason_code + 2×8-hex-prefix). No new ADR (precedented by PLAN-116
    # pattern; AC-B5 closes ADR-055-AMEND-2 evidence-red defer via the
    # PLAN-118 plan). Registered via kernel-override
    # PLAN-118-WS-B-CHOKEPOINTS.
    "emit_audit_producer_path_pollution_detected",
    # PLAN-089 v1.23.0 (S117 2026-05-13) — kernel + auth hardening (12 emits).
    # PLAN-090 v1.24.0 (S118 2026-05-13) — capability rollout (4 emits).
    # Rebaselined S122 PLAN-092 closeout hotfix (2026-05-14) — these were
    # shipped without contract-test bump in their respective plans; this
    # rebaseline closes the audit-registry-drift debt.
    "emit_bash_canonical_bypass_invoked",
    "emit_capability_rollout_complete",
    "emit_confidence_gate_baseline_emitted",
    "emit_kernel_extension_landed",
    "emit_kill_switch_invoked",
    "emit_mcp_bearer_friction_observed",
    "emit_persona_auto_decision_emitted",
    "emit_persona_auto_rate_capped",
    "emit_phase_c_enforcing_flipped",
    "emit_sentinel_signer_expiry_warned",
    "emit_sentinel_signer_quorum_attempted",
    "emit_sentinel_signer_quorum_failed",
    "emit_sentinel_signer_revoked",
    "emit_sentinel_signer_rotated",
    "emit_streaming_rate_capped",
    "emit_streaming_token_yielded",
    # PLAN-096 (ADR-042-AMEND-1, S130 2026-05-17) — Wave D cross-tenant denial
    # + Wave E soak FPR breach (read-only MCP expansion governance surface).
    "emit_mcp_cross_tenant_denied",
    "emit_mcp_soak_fpr_breach",
    # PLAN-097 (ADR-062-AMEND-1 / ADR-128 §6, S131 2026-05-17) — RAG routing
    # audit surface (5 emits; Wave C decision layer).
    "emit_rag_profile_recommended",
    "emit_rag_auto_wire_skipped_sidecar_down",
    "emit_rag_query_routed",
    "emit_rag_false_large_demoted",
    "emit_rag_hit_rate_degraded",
    # PLAN-098 (ADR-132, S132 2026-05-17) — GOAP A* advisory-only planner
    # audit surface (9 emits; Wave A per-edge sampled + terminus aggregates).
    "emit_goap_edge_explored",
    "emit_goap_search_aborted",
    "emit_goap_search_summary",
    "emit_goap_cycle_detected",
    "emit_goap_depth_exceeded",
    "emit_goap_replan_triggered",
    "emit_goap_replan_exhausted",
    "emit_goap_disabled_by_env",
    "emit_goap_recommendation_accepted",
    # PLAN-099 (ADR-129 / ADR-135, S134 2026-05-17) — federation cross-machine
    # MVP audit surface (10 emits; Wave D kernel-override extension).
    "emit_federation_connection_accepted",
    "emit_federation_connection_rejected",
    "emit_federation_connection_replay_suspected",
    "emit_federation_cert_expiry_warned",
    "emit_federation_cert_rotated",
    "emit_federation_cert_revoked",
    "emit_federation_write_attempt_blocked",
    "emit_federation_lan_bind_denied",
    "emit_federation_autonomous_call_blocked",
    "emit_federation_enable_sentinel_invalid",
    # PLAN-105 Wave A.1 + A.2 (S134-cont 2026-05-17) — GOAP recommendation
    # outcome telemetry (rendered = denominator; overridden = enum mismatches).
    "emit_goap_recommendation_rendered",
    "emit_goap_recommendation_overridden",
    # PLAN-104 Wave A (S136 2026-05-18) — persona-demand ledger (4 emits).
    # Pre-existing drift absorbed by PLAN-090-FOLLOWUP S138 ceremony per
    # ADR-115 §3 (instrumentation drift cleanup).
    "emit_persona_demand_opened",
    "emit_persona_demand_matched",
    "emit_persona_demand_unmet",
    "emit_persona_demand_waived",
    # PLAN-090-FOLLOWUP Wave A (S138 2026-05-18) — claim producer pair.
    "emit_claim_emitted",
    "emit_confidence_gate_verdict",
    # PLAN-100 Wave B (S139 2026-05-18) — per-class block-mode + drift detector.
    "emit_confidence_gate_blocked",
    "emit_confidence_gate_fp_drift_detected",
    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 (S152, v1.39.4) — public
    # emitter for the chain_reset_marker rotation re-anchor sentinel.
    # ADR-055-AMEND-2 ACCEPTED. Wraps _emit_chain_reset_marker_under_lock.
    "emit_chain_reset_marker",
    # PLAN-113 Phase B WIRE-AUDIT (S163, v1.45.x) — typed wrappers for
    # previously-orphan emit actions wired to their production call-sites.
    # Escalation cluster (4): wired in ceo-escalation-detector.py main().
    "emit_escalation_detected",
    "emit_escalation_dispatched",
    "emit_escalation_suppressed",
    "emit_escalation_baseline_recorded",
    # Swarm finalize cluster (2): wired via coordinator.finalize_swarm().
    "emit_swarm_finalize_grouped",
    "emit_swarm_finalize_committed",
    # Skill / ledger typed wrappers (3): wired to their owning modules.
    "emit_skill_reference_never_read",
    "emit_task_route_key_dropped",
    "emit_reality_ledger_key_dropped",
    # Tournament cluster (8): wired in swarm/tournament.py Tournament.run().
    "emit_tournament_run_started",
    "emit_tournament_task_scored",
    "emit_tournament_run_completed",
    "emit_tournament_budget_projected",
    "emit_tournament_budget_exceeded",
    "emit_tournament_aborted",
    "emit_tournament_fixture_rejected",
    "emit_tournament_judge_hijack_suspected",
    # PLAN-133 (Goose-harvest SOTA evolution) — net-new typed emit_* wrappers
    # introduced by the harvested waves. Each carries a deny-by-default scrub
    # allowlist in audit_emit.py; the closed-enum action it wraps is added to
    # _KNOWN_ACTIONS (count 273 -> 292; SHA rebaselined below). Attribution:
    #   A1 (hardening)           — emit_env_var_hijack_blocked,
    #                              emit_persistent_instructions_blocked
    #   A3 (egress taxonomy)     — emit_egress_destination_detected
    #   C3 (eval harness)        — emit_eval_task_completed
    #   E1 (adversary review)    — emit_adversary_review_flagged
    #   G3 (hint provenance)     — emit_hint_provenance_recorded
    # (Actions emitted purely via emit_generic add NO public symbol and are
    #  reflected only in the _KNOWN_ACTIONS count + SHA.)
    "emit_adversary_review_flagged",
    "emit_egress_destination_detected",
    "emit_env_var_hijack_blocked",
    "emit_eval_task_completed",
    "emit_hint_provenance_recorded",
    "emit_persistent_instructions_blocked",
})


# Bumped 2026-04-25 (Session 62 cont) — PLAN-059 SEC-P0-04 / ADR-080 added
# 3 audit-tokens content-ban actions (audit_tokens_emitted, _timeout,
# _key_dropped). Count: 89 → 92.
# Bumped 2026-04-27 (Wave B) — PLAN-052 / ADR-083 mcp_injection_finding
# wired up via PLAN-044 audit-v2 C1-P0-03 fix. Count: 92 → 93.
# Bumped 2026-04-29 (Session 76 audit-v3 / DIM-04 #1) — registered the 2
# skill-bootstrap actions (skill_bootstrap_used, skill_bootstrap_post_hash)
# that were emitted by hooks but dropped silently by `_write_event`
# pre-Session-76. Count: 93 → 95.
# Bumped 2026-05-03 (Session 81 / PLAN-069 Phase 1 Wave D / ADR-101) —
# replay_capture_started + replay_capture_completed actions added so capture
# mode emits its own lifecycle events (was reusing replay_started/_completed).
# Count: 95 → 97.
# Bumped 2026-05-04 (Session 82 / PLAN-065 Phase 2 / ADR-098) — ceo_boot_emitted
# + ceo_boot_check_skipped actions added (S82 ceremony lote bundle). /ceo-boot
# session-boot autopilot lifecycle telemetry; Sec MF-3 enforced via
# _scrub_ceo_boot_event; closes Reality-Ledger fixture #4 (declared-but-not-wired).
# Count: 97 → 99.
# Bumped 2026-05-05 (Session 85 / PLAN-070 / ADR-102) — mcp_canonical_guard_blocked
# + mcp_canonical_guard_allowed actions added (Layer B server-side MCP middleware
# closes ADR-095 §gate-#6 NG-06). Sec MF-3 enforced via dedicated allowlists
# (_MCP_CANONICAL_GUARD_{ALLOWED,BLOCKED}_ALLOWLIST). Count: 99 → 101.
# Bumped 2026-05-05 (Session 87 / PLAN-071 / ADR-104) — task_route_advised +
# task_route_key_dropped + reality_ledger_finding + reality_ledger_key_dropped
# actions added (Adaptive Execution Kernel + Reality Ledger advisory). Sec MF-3
# enforced via dedicated allowlists (_TASK_ROUTE_ADVISED_ALLOWLIST +
# _REALITY_LEDGER_FINDING_ALLOWLIST). Count: 101 → 105.
#
# Wave 1b S92 ceremony (2026-05-07) — added 3 PLAN-078 actions
# (model_routing_advised + estimate_drift_detected +
# estimate_drift_systematic_bias) shipped in S89 Fase 1 commit 2cb1472 but
# never registered in this test contract. Closing the audit-registry-drift
# debt MEMORY tracked since S89. Sec MF-3 enforced via dedicated allowlists
# in audit_emit.py (`_FORBIDDEN_FIELDS_MODEL_ROUTING_ADVISED` etc.).
# Count: 105 → 108.
#
# Wave 5 S95 ceremony (2026-05-08) — added 1 PLAN-078 Wave 5 action
# (ceo_boot_task_candidate_emitted) — TaskCreate-candidate orchestration.
# Emitted by ceo-boot.py per stdout marker block when gate_pass=False AND
# severity≥medium. Sec MF-3 enforced via _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST.
# Count: 108 → 109.
#
# PLAN-075 v1.13.x patch S96-cont-2 ceremony (2026-05-09) — added 4 PLAN-075
# Pair-Rail Multi-LLM actions (pair_rail_review_passed, pair_rail_codex_unavailable,
# pair_rail_codex_violation, pair_rail_sentinel_bypass). Wired by
# check_pair_rail.py PreToolUse on Edit|Write|MultiEdit against L3+ canonical-
# guarded paths. ADR-106 + ADR-110 ACCEPTED. Registered with KERNEL_OVERRIDE
# since audit_emit.py is in _KERNEL_PATHS. Count: 109 → 113.
#
# PLAN-081 Phase 1-full S99 ceremony (2026-05-09) — added 1 R1 S-Sec-5 action
# (pair_rail_codex_injection_detected). Wired by check_codex_response.py
# PostToolUse on mcp__codex__codex|mcp__codex__codex-reply matchers. ADR-106
# + ADR-107 + ADR-108 lineage. Registered with KERNEL_OVERRIDE since
# audit_emit.py is in _KERNEL_PATHS. Count: 113 → 114.
#
# PLAN-081 Phase 2 S100 ceremony (2026-05-10) — added 1 dispatcher action
# (dispatcher_route_emit). Wired by .claude/scripts/inject-agent-context.sh
# `--pair-mode` Pair-Rail dispatch resolution path. ADR-106 + ADR-107 +
# ADR-108 lineage. Sec MF-3 allowlist via _DISPATCHER_ROUTE_EMIT_ALLOWLIST.
# Codex iter 1 closure: wall_clock_ms (int) + retry_at_timeout_ms (int) per
# canonical_json.py:85 no-float invariant. Count: 114 → 115.
_EXPECTED_KNOWN_ACTIONS_SHA256 = (
    # Updated PLAN-105 Wave A (S134-cont) — rebaselined to absorb 28
    # actions from S128..S134 that were never folded into this contract:
    #   PLAN-096 (S130): mcp_cross_tenant_denied + mcp_soak_fpr_breach
    #   PLAN-097 (S131): rag_profile_recommended + rag_auto_wire_skipped_sidecar_down
    #                    + rag_query_routed + rag_false_large_demoted
    #                    + rag_hit_rate_degraded
    #   PLAN-098 (S132): goap_edge_explored + goap_search_aborted + goap_search_summary
    #                    + goap_cycle_detected + goap_depth_exceeded
    #                    + goap_replan_triggered + goap_replan_exhausted
    #                    + goap_disabled_by_env + goap_recommendation_accepted
    #   PLAN-099 (S134): federation_connection_accepted + _rejected + _replay_suspected
    #                    + federation_cert_expiry_warned + _rotated + _revoked
    #                    + federation_write_attempt_blocked + _lan_bind_denied
    #                    + federation_autonomous_call_blocked + _enable_sentinel_invalid
    #   PLAN-105 (this plan): goap_recommendation_rendered + goap_recommendation_overridden
    # Count: 188 -> 216.
    # Updated PLAN-090-FOLLOWUP Wave D (S138 2026-05-18) — absorbs:
    #   PLAN-104 (S136): persona_demand_opened + _matched + _unmet + _waived (+4)
    #   PLAN-090-FOLLOWUP (this plan): claim_emitted + confidence_gate_verdict (+2)
    # Count: 216 -> 222.
    # Updated PLAN-100 Wave B (S139 2026-05-18) — PLAN-100 +2 actions
    # (confidence_gate_blocked + confidence_gate_fp_drift_detected).
    # Count: 222 -> 224.
    # Updated PLAN-101 Wave B (S141 2026-05-18) — PLAN-101 +1 action
    # (task_route_ground_truth_label).
    # Count: 224 -> 225.
    # Updated PLAN-102 Wave A+B (S142 2026-05-18) — PLAN-102 +5 actions:
    #   Wave A: cost_envelope_capped + swarm_paused_owner_absent
    #           + swarm_runaway_suspected (+3)
    #   Wave B: execution_context_signed +
    #           execution_context_validation_failed (+2)
    # Count: 225 -> 230.
    # Updated PLAN-110 Wave D (S147 2026-05-20) — +1 action
    # (protocol_edit_missing_amend_paired) via kernel-override
    # PLAN-110-WAVE-D-AUDIT-EMIT-EXTENSION. Count: 234 -> 235.
    # Updated PLAN-099-FOLLOWUP Wave F (S148 2026-05-20) — 20 actions
    # touched; +19 net-new via kernel-override
    # PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION. The 20 actions:
    #   "federation_audit_event_pushed"
    #   "federation_audit_event_pushed_batch"
    #   "federation_audit_log_backpressure"
    #   "federation_cert_rotated" (already in _KNOWN_ACTIONS from PLAN-099 MVP S134;
    #     field-shape-superseded in-place at Wave F.2 — NOT a new set entry)
    #   "federation_cert_validity_window_too_large"
    #   "federation_event_action_blocked"
    #   "federation_hmac_secret_rotated"
    #   "federation_key_floor_rejected"
    #   "federation_key_floor_stale"
    #   "federation_message_storm_detected"
    #   "federation_peer_invalid_no_fingerprint"
    #   "federation_peer_registered"
    #   "federation_peer_registered_collision"
    #   "federation_peer_revoked_remote"
    #   "federation_pin_legacy_used"
    #   "federation_scope_denied"
    #   "federation_spki_fingerprint_mismatch"
    #   "federation_tamper_detected"
    #   "federation_write_disabled_sentinel_invalid"
    #   "federation_write_endpoint_denied"
    # Count: 235 -> 254.
    # Updated PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 (S152, v1.39.4) — +1
    # action chain_reset_marker (rotation re-anchor sentinel; ADR-055-AMEND-2
    # ACCEPTED). The action shipped at v1.39.4 without a contract bump, leaving
    # CI red; this rebaseline (S155) aligns the contract to the already-approved
    # action. Count: 254 -> 255.
    # Updated PLAN-112-FOLLOWUP-persona-routing-wire (S158, v1.42.0) — +2
    # actions model_routing_enforced + model_routing_eval_error (god-mode
    # routing-matrix consult in check_agent_spawn; CONSULT+AUDIT, block
    # deferred). Registered via kernel-override
    # PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION. Count: 255 -> 257.
    # NOTE: federation-wire-or-delete's +1 (federation_peer_list_reloaded)
    # was NOT applied in S158 (its federation/* producer code is canonical-
    # guarded and was BLOCKED at apply — no discoverable sentinel scoped it),
    # PLAN-112-FOLLOWUP-federation-wire PHASE2 (S159, v1.43.0) — +1 action
    # federation_peer_list_reloaded. Count: 257 -> 258.
    # Updated PLAN-113 Phase B WIRE-DEADMOD (S163, v1.45.x) — +2 actions
    # spec_context_sanitized + spawn_confidence_advisory (spawn-prompt advisory
    # telemetry emitted via emit_generic from check_agent_spawn.py). Count: 258 -> 260.
    # Updated PLAN-116 (S172, 2026-05-27) — +1 action
    # tier_policy_loader_fallback_observed (dedicated tier-policy loader
    # advisory-fallback telemetry; replaces the tier_policy_misrouting_advised
    # piggyback). Count: 260 -> 261.
    # Updated PLAN-117 WS-A (S176, 2026-05-27) — +1 action
    # credential_override_late_set_ignored (ADR-040-AMEND-2 §Layer-1 forensic;
    # live Claude adapter sources the credential emergency-override from the
    # trust-root snapshot, emits this on an ignored late-set). Count: 261 -> 262.
    # Updated PLAN-118 AC-B5 (S179 2026-05-28) — +1 closed-enum action
    # `audit_producer_path_pollution_detected` for producer-side fail-CLOSED
    # canonical-resolution breadcrumb (chokepoint=chain_reset_marker |
    # spool_drain). Registered via kernel-override
    # PLAN-118-WS-B-CHOKEPOINTS. Count: 262 -> 263.
    # Updated PLAN-125 WS-1 (kooky-harvest) — +1 action
    # tool_call_lifecycle_recorded (per-tool-call lifecycle telemetry; deny-by-
    # default scrub-branch + _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST, NEVER
    # _EMIT_GENERIC_PASSTHROUGH). Closed enums tool_name_enum (mcp__* →
    # mcp_other, MF-SEC-1) + duration_bucket (no raw ms, MF-SEC-3). Net-new
    # public emitter emit_tool_call_lifecycle_recorded added to
    # _EXPECTED_PUBLIC_SYMBOLS. Count: 269 -> 270.
    # Updated PLAN-124 WS-1 (ECC value-harvest) — +1 action
    # git_hook_bypass_blocked (git hook-bypass guard breadcrumb; deny-by-default
    # scrub-branch + _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST, NEVER
    # _EMIT_GENERIC_PASSTHROUGH). Closed enum flag_class (MF-G; matched command
    # bytes never persisted). Net-new public emitter emit_git_hook_bypass_blocked
    # added to _EXPECTED_PUBLIC_SYMBOLS. Count: 270 -> 271.
    # Updated PLAN-128 §7 (S217) — +2 actions verify_after_edit_finding +
    # adequacy_gate_flag (accelerator catch telemetry; deny-by-default dispatch-gate +
    # _VERIFY_AFTER_EDIT_FINDING_ALLOWLIST / _ADEQUACY_GATE_FLAG_ALLOWLIST with enum
    # coercion to "other" + 0..99 clamp). NO new public emitter — both via emit_generic.
    # Count: 271 -> 273.
    # Updated PLAN-133 (Goose-harvest SOTA evolution) — net-new closed-enum
    # actions across the harvested waves (typed wrappers: env_var_hijack_blocked,
    # persistent_instructions_blocked [A1]; egress_destination_detected [A3];
    # eval_task_completed [C3]; adversary_review_flagged [E1];
    # hint_provenance_recorded [G3]) plus the emit_generic-only actions added by
    # the remaining items. SHA re-derived from the MATERIALIZED audit_emit.py
    # under canonical-ready/. Count: 273 -> 292.
    # Updated PLAN-135 W1 S3 (anthropic-surface-harvest, S231) — +1 action
    # settings_tamper_detected (/ceo-boot Tier-S tamper-tripwire breadcrumb;
    # deny-by-default scrub branch + _SETTINGS_TAMPER_DETECTED_ALLOWLIST with
    # closed-enum coercion to "other" + 0..99 clamp). NO new public emitter —
    # emit_generic only (persona_coverage_synthesized precedent). SHA
    # re-derived from the STAGED audit_emit.py under
    # .claude/plans/PLAN-135/staged/w1/files/. Count: 292 -> 293.
    # Updated PLAN-135 W2 (anthropic-surface-harvest hook wave) — net-new
    # closed-enum actions for the W2 new-event hooks, materialized into the
    # SHARED staged W2 audit_emit.py under
    # .claude/plans/PLAN-135/staged/w2/files/:
    #   H2 ConfigChange guard (emit_generic only): config_change_observed +
    #      config_change_forbidden_key (+2)
    #   H1 PreCompact/PostCompact pair (emit_generic only):
    #      compaction_continuity_snapshot + compaction_context_reinjected (+2)
    #   H5 corrective bash-input rewrite (ADR-154; TYPED wrapper
    #      emit_bash_input_rewritten added to _EXPECTED_PUBLIC_SYMBOLS):
    #      bash_input_rewritten (+1)
    #   H3 SubagentStart/SubagentStop bracket (emit_generic only):
    #      subagent_lifecycle_observed (+1)
    # SHA re-derived from the consolidated STAGED W2 audit_emit.py.
    # Count: 293 -> 299. CONSOLIDATION NOTE: this count + SHA cover ALL W2
    # actions assembled at H5-unit reconciliation time (W1 settings_tamper_detected
    # + H2 config_change ×2 + H1 compaction ×2 + H5 bash_input_rewritten + H3
    # subagent_lifecycle_observed = 7 over the live 292). The W2 audit_emit is a
    # SHARED file; if a later W2 unit registers an additional action, arc-verify
    # MUST re-derive both this SHA and the count pins (this file line ~606 +
    # test_git_bypass_guard.py + test_codex_egress_proof_telemetry.py) against the
    # FINAL staged W2 audit_emit.py. See staged/w2/actions-added.md.
    #
    # ARC CONSOLIDATION (PLAN-135 arc layer): the W5 ops actions fold in here in
    # ONE place — admin_key_lifecycle_event (o9) + statusline_sidecar_write (o4)
    # + model_refusal_observed (o7) = +3 over the W2 count 299 -> 302. As of
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) all three route through dedicated
    # per-action `_scrub_*` allowlist branches (NOT `_EMIT_GENERIC_PASSTHROUGH`);
    # the _KNOWN_ACTIONS SET is unchanged by that move, so this SHA + the 302
    # count pin still hold. SHA re-derived from the FINAL arc audit_emit.py via
    # sha256(json.dumps(sorted(_KNOWN_ACTIONS))). See staged/w5/actions-added.md.
    # Updated PLAN-153 Wave E item 7 / NEW-4 (ADR-159, 2026-07-07) — +1 action
    # spawn_prompt_defense_gate (Prompt Defense Baseline gate telemetry emitted
    # via emit_generic from check_agent_spawn._emit_prompt_defense_event; closed-
    # enum fields keyword/present/enforced, Sec MF-3 dedicated dispatch branch +
    # _SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST, NEVER _EMIT_GENERIC_PASSTHROUGH). NO
    # new public emitter — emit_generic only (spawn_confidence_advisory precedent).
    # SHA re-derived from the STAGED audit_emit.py under
    # .claude/plans/PLAN-153/staged/wave-E/ via
    # sha256(json.dumps(sorted(_KNOWN_ACTIONS))). Count: 302 -> 303.
    # Updated PLAN-154 (Gated Learning Loop / ADR-160, SENT-F ceremony) —
    # +11 metadata-only actions: lesson_candidate_written + lesson_approved
    # + lesson_quarantined + lesson_expired + lesson_integrity_flag
    # + lesson_boot_render_dropped + learning_rail_disabled
    # + fact_gate_activation_changed + advisory_dampened
    # + distiller_run_completed + lesson_evolve_run. All route through
    # dedicated Sec MF-3 dispatch branches + per-action allowlists
    # (_LEARNING_ENVELOPE family), NEVER _EMIT_GENERIC_PASSTHROUGH. ONE new
    # public typed emitter: emit_learning_rail_disabled (added to
    # _EXPECTED_PUBLIC_SYMBOLS). SPEC amend v2.48. SHA re-derived from the
    # STAGED audit_emit.py under .claude/plans/PLAN-154/staged/sent-f/ via
    # sha256(json.dumps(sorted(_KNOWN_ACTIONS))). Count: 303 -> 314.
    # Updated PLAN-155 Wave 4 (Codex harness audit chain / ADR-161, SENT-CX-B
    # ceremony) — +2 metadata-only actions: codex_tool_recorded (per-tool
    # PostToolUse append, A) + codex_turn_ended (turn-level backstop, B). Both
    # route through dedicated Sec MF-3 dispatch branches + per-action
    # allowlists (_CODEX_TOOL_RECORDED_ALLOWLIST / _CODEX_TURN_ENDED_ALLOWLIST),
    # NEVER _EMIT_GENERIC_PASSTHROUGH. TWO new public typed emitters:
    # emit_codex_tool_recorded + emit_codex_turn_ended (added to
    # _EXPECTED_PUBLIC_SYMBOLS). SPEC amend v2.49. SHA re-derived from the
    # STAGED audit_emit.py under .claude/plans/PLAN-155/staged/wave-4/ via
    # sha256(json.dumps(sorted(_KNOWN_ACTIONS))). Count: 314 -> 316.
    "bcb1afc7f79d473b7febc3b8b6662f722b404300f91fa922cdd2e416113b49ee"
)


class AuditEmitPublicSurfaceTests(unittest.TestCase):
    """Pinned public API contract — survives Phase 1c package split."""

    def test_every_pinned_symbol_is_callable(self) -> None:
        missing = []
        for name in sorted(_EXPECTED_PUBLIC_SYMBOLS):
            fn = getattr(audit_emit, name, None)
            if fn is None or not callable(fn):
                missing.append(name)
        self.assertEqual(
            missing, [],
            f"Pinned emitters missing or not callable: {missing}. "
            f"Phase 1c split must preserve the full public surface.",
        )

    def test_no_unexpected_public_emitters_without_adr(self) -> None:
        """Catch silent additions; every new emitter needs an ADR bump."""
        actual = {
            n for n in dir(audit_emit)
            if (n.startswith("emit_") or n.startswith("iter_"))
            and not n.startswith("_")
            and callable(getattr(audit_emit, n, None))
        }
        unexpected = actual - _EXPECTED_PUBLIC_SYMBOLS
        self.assertFalse(
            unexpected,
            f"New public emitter(s) added without contract update: {sorted(unexpected)}. "
            f"Add to _EXPECTED_PUBLIC_SYMBOLS + write ADR + bump SHA256 if needed.",
        )

    def test_known_actions_set_byte_identity(self) -> None:
        """SHA256(sorted(_KNOWN_ACTIONS)) pinned — prevents silent action drift."""
        actions = sorted(audit_emit._KNOWN_ACTIONS)
        canon = json.dumps(actions)
        actual = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        self.assertEqual(
            actual, _EXPECTED_KNOWN_ACTIONS_SHA256,
            f"_KNOWN_ACTIONS drift detected. "
            f"Count={len(actions)} (expected 316). "
            f"Rebaseline this test + add audit-registry entry if the change is intentional.",
        )

    def test_known_actions_count_fixed(self) -> None:
        self.assertEqual(
            len(audit_emit._KNOWN_ACTIONS), 316,
            "_KNOWN_ACTIONS count drifted from 163 baseline (PLAN-088 S114 Wave 1 +11 actions: "
            "cache_discipline_alerted + first_run_wizard_dispatched + "
            "estimate_calibrator_pipeline_run + subagent_findings_partial_drop + "
            "anthropic_429_observed + git_index_lock_retry + codex_invoke_dispatched + "
            "tier_policy_misrouting_advised + cookbook_pattern_advised + "
            "pair_rail_phase_advanced + batch_dispatched; canonical-13 set complete "
            "with model_routing_advised PLAN-078 + mcp_route_advised PLAN-086 Wave D "
            "pre-existing. Plus PLAN-086 v1.20.x drift +5 actions already absorbed: "
            "mcp_route_advised + mcp_canonical_guard_internal_error + thinking_budget_set + "
            "codex-reply + repo_profile_confirmed. Was 147 PLAN-085 v1.19.0 S111 +10 actions: "
            "Wave C 5 [live_adapter_blocked, credential_blocked_due_to_age, "
            "credential_emergency_override_used, mcp_bearer_replay_rejected, "
            "mcp_non_loopback_rejected] + Wave G.1b 5 [prompt_injection_detected, "
            "secret_leak_detected, pii_redacted_outgoing, codex_egress_redacted, "
            "canonical_edit_completed]) (was 127 baseline at PLAN-083 Wave 0a/0b/1+2 "
            "(89 + 3 audit-tokens per ADR-080 SEC-P0-04 + 1 mcp_injection_finding "
            "per ADR-083 / PLAN-044 audit-v2 Wave B + 2 skill-bootstrap "
            "per Session 76 audit-v3 DIM-04 #1 + 2 replay-capture actions "
            "per Session 81 / PLAN-069 Phase 1 / ADR-101 + 2 ceo-boot actions "
            "per Session 82 / PLAN-065 Phase 2 / ADR-098 + 2 mcp-canonical-guard "
            "actions per Session 85 / PLAN-070 / ADR-102 + 4 task-route + "
            "reality-ledger actions per Session 87 / PLAN-071 / ADR-104 + "
            "3 PLAN-078 actions per S92 Wave 1b drift fix + "
            "1 PLAN-078 Wave 5 action per S95 ceremony "
            "(ceo_boot_task_candidate_emitted) + "
            "4 PLAN-075 v1.13.x patch actions per S96-cont-2 ceremony "
            "(pair_rail_review_passed + pair_rail_codex_unavailable + "
            "pair_rail_codex_violation + pair_rail_sentinel_bypass) + "
            "1 PLAN-081 Phase 1-full action per S99 ceremony "
            "(pair_rail_codex_injection_detected per R1 S-Sec-5) + "
            "1 PLAN-081 Phase 2 action per S100 ceremony "
            "(dispatcher_route_emit per Codex iter 1) + "
            "1 PLAN-081 Phase 3 action per S100 ceremony "
            "(pair_rail_case_emit per ADR-107/108 ACCEPTED)",
        )

    def test_write_event_helper_still_private(self) -> None:
        """`_write_event` stays an internal contract — emitters depend on it."""
        self.assertTrue(hasattr(audit_emit, "_write_event"))
        self.assertTrue(callable(audit_emit._write_event))


if __name__ == "__main__":
    unittest.main()
