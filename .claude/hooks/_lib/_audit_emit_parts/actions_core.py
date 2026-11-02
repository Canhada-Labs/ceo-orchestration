"""Audit action registrations; combined by schemas_actions."""
from __future__ import annotations

_ACTIONS = {
    "agent_spawn",  # v1, still emitted by audit_log.py
    "debate_event",
    "plan_transition",
    "veto_triggered",
    "benchmark_run",
    "eval_task_completed",  # PLAN-133 C3 — real-task reward benchmark (.claude/eval/runner.py)
    "lesson_write",
    "lesson_outcome",  # v2 (Sprint 6 Phase 4, ADR-015)
    "injection_flag",  # v2.1 (Sprint 5 Phase 5, ADR-011)
    "confidence_gate",  # Sprint 8 Phase 2, ADR-018
    "lesson_read",  # Sprint 8 Phase 3 (top-K lessons injected into spawn)
    "lesson_archived",  # Sprint 8 Phase 4 (pruning enforcement)
    "lesson_restored",  # Sprint 8 Phase 4b (restore companion)
    "lesson_outcome_undone",  # Sprint 9 P3.3 (escape hatch for Architect)
    "state_store_write",  # Sprint 11 Phase 0, ADR-027
    "state_store_read",  # Sprint 11 Phase 0, ADR-027
    "state_store_pruned",  # Sprint 11 Phase 0, ADR-027
    "budget_exceeded",  # Sprint 11 Phase 6 (ADR-033)
    "budget_bypass_used",  # Sprint 11 Phase 6 (H13)
    "otel_export_dropped",  # Sprint 11 Phase 8 (CR3)
    "output_safety_flag",  # Sprint 11 Phase 9 (ADR-036)
    "skill_patch_applied",  # Sprint 11 Phase 4 (ADR-031)
    "squad_imported",  # Sprint 11 Phase 12 (CR2)
    # Sprint 13 Phase A.0 (PLAN-013 Gap #3 fix) — live adapter / breaker /
    # credential events emitted by _lib/adapters/live/_transport.py via
    # on_audit callback + planned breaker/credential sites per ADR-040 §4/§7.
    # Registration here ensures they land in audit-log instead of breadcrumb.
    "live_adapter_call_started",  # ADR-040 §7 — _transport.py:186
    "live_adapter_call_succeeded",  # ADR-040 §7 — _transport.py:198
    "live_adapter_call_failed",  # ADR-040 §7 — _transport.py:214/245
    "breaker_opened",  # ADR-040 §2 — planned _breaker.py transition hook
    "breaker_closed",  # ADR-040 §2 — planned _breaker.py transition hook
    "credential_rotation_due",  # ADR-040 §4 — >75d age gate
    # PLAN-085 Wave C.1 (R-029, F-A-SEC-0012-253dcfe3).
    "live_adapter_blocked",
    # PLAN-085 Wave C.2 (R-030, ADR-040-AMEND-2 / F-A-SEC-0011-142cbfe2).
    "credential_blocked_due_to_age",
    # PLAN-085 Wave C.2 — emergency override audit trail.
    "credential_emergency_override_used",
    # PLAN-117 WS-A (S176) — ADR-040-AMEND-2 §Layer-1 forensic: a late-set
    # (post-trust-anchor) override attempt that was IGNORED, not honored.
    "credential_override_late_set_ignored",
    # PLAN-085 Wave C.3 (IDA-P0-03 / F-A-IDA-T-0003).
    "mcp_bearer_replay_rejected",
    # PLAN-085 Wave C.3 — handler-entry loopback fail-CLOSED.
    "mcp_non_loopback_rejected",
    # PLAN-085 Wave G.1b — ATLAS technique-ID schema (5 mappings).
    "prompt_injection_detected",       # AML.T0051
    "secret_leak_detected",            # AML.T0024.001
    "pii_redacted_outgoing",           # AML.T0048.004
    "codex_egress_redacted",           # AML.T0054
    # PLAN-085 Wave E.4 piggyback — PostToolUse Bash forensic advisory.
    "canonical_edit_completed",
    # Sprint 13 Phase A (PLAN-013) — MCP server events per ADR-042 §Auth.5 / §Cost.4
    "mcp_handler_invoked",  # ADR-042 §Auth — every handler entry (read + write)
    "mcp_handler_denied",  # ADR-042 §Auth.5 — every deny path
    "mcp_server_started",  # ADR-042 §Cost.4 — startup observability
    "mcp_server_disabled_by_kill_switch",  # ADR-042 §Cost.4 — CEO_SOTA_DISABLE short-circuit
    # Sprint 14 Phase 0.6 (PLAN-014 ADJ-010) — audit registry v2.6
    # Policy engine events (Phase A, ADR-045 + SPEC/v1/policy-dsl.schema.md)
    "policy_evaluated",  # every rule evaluation (allow/deny decision)
    "policy_denied",  # final deny after rule evaluation
    "policy_error",  # parse/predicate/import failure — fail-closed for security surfaces per A.3.1
    # Replay events (Phase F.1, ADR-046 + SPEC/v1/replay.schema.md)
    "replay_started",  # original_session_id + redacted_fragments_count + mode
    "replay_completed",  # duration + spawn_count + diff_summary
    "replay_diff_produced",  # per-spawn divergence artifact
    # Predictive budget events (Phase F.3, ADR-047 + SPEC/v1/predict-budget.schema.md)
    "prediction_queried",  # plan_id + bucket_range + confidence (incl. cold_start)
    # Cross-plan memory events (Phase F.5, ADR-048 + SPEC/v1/memory-shared.schema.md)
    "pattern_stored",  # topic + content_hash + size_bytes (redacted)
    "pattern_queried",  # topic + k + match_count
    "pattern_evicted",  # manual eviction via admin path
    # Threat-model governance (Phase C)
    "threat_model_promoted",  # draft → accepted transition
    "threat_model_freshness_breach",  # check-threat-model-freshness.py CI event
    # PLAN-028 Wave A Fase 3 (ADR-056) — lifecycle expansion hooks
    "session_start",  # SessionStart hook fires at session boot
    "session_end",  # SessionEnd hook fires at session close
    "prompt_submitted",  # UserPromptSubmit advisory scan event
    "session_stop",  # Stop hook fires on interrupt / termination
    # PLAN-029 Wave A Fase 4 (ADR-057) — output-scan redaction
    "output_scan_finding",  # check_output_secrets hook emit on hit
    # PLAN-106 Wave H.1 (absorbing PLAN-095-FOLLOWUP).
    # Emitted by check_output_secrets.py when a finding is suppressed by
    # `_lib/output_scan_dedup.check_and_record` within a 24h rolling
    # window. Composite key = (repo_path_hash, command_sha, pattern_id).
    # NO raw secret / command body / path content persists — Sec MF-3
    # allowlist (_OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST) enforces.
    "output_scan_finding_suppressed",
    # PLAN-041 Wave A+ (ADR-062)
    "rag_query_issued",
    "rag_query_returned",
    "rag_query_fallback",
    "rag_query_redacted",
    "rag_index_redacted",
    # Session 76 audit-v3 (DIM-04 finding 1) — skill bootstrap observability
    # Emitted by check_skill_patch_sentinel.py:251 on bootstrap-env-var
    # detection; correlated post-write by check_skill_bootstrap_post.py via
    # SHA-256 hash. Pre-Session-76 these were dropped silently by
    # _write_event because the actions were unregistered. SPEC v2.15.
    "skill_bootstrap_used",
    "skill_bootstrap_post_hash",
    # PLAN-122 WS12 — optimizer (WS-1/WS-2) recommender telemetry. Emitted via
    # emit_generic through optimizer/_skeleton.safe_emit (HMAC-safe scalars only;
    # NO prompt body / paths / token counts). Sec MF-3 allowlists below.
    "optimizer_route_recommended",
    "fanout_recommended",
    "model_choice_recommended",
    "rag_context_recommended",
    "codex_review_disabled",
    # PLAN-122 WS3 — per-phase Codex review event (the complement of
    # codex_review_disabled). Emitted via emit_generic through
    # optimizer/_skeleton.safe_emit with the redacted PhaseReview fields only
    # (enum / bounded int / stable hash / fixed slug — NO raw Codex text, NO
    # token side-channel). Sec MF-3 allowlist below.
    "codex_review_invoked",
    # PLAN-128 §7 (S217) — accelerator catch-emit telemetry (Sec MF-3; enum coercion +
    # int clamp in the emit_generic dispatch-gate). NO paths / source / error text.
    "verify_after_edit_finding",
    "adequacy_gate_flag",
    # PLAN-133 B5 — closed-enum provider/cost error taxonomy mirror. The
    # subscription-ceiling member (the dominant ADR-144 primary-limit), a PEER
    # of credits_exhausted/auth (those two are the advisor_executor metered-API
    # path ONLY). Advisory/observability today: this is the ONLY trust-eligible
    # (HMAC-chained) representation of a quota ceiling — a trust gate must NEVER
    # read the advisory advisor-calls.jsonl. Emitted via emit_generic; deny-by-
    # default dispatch-gate + _QUOTA_EXHAUSTED_ALLOWLIST below; error_class
    # coerced to a closed enum; NO retry_delay / Retry-After value / body text
    # on the wire (S172 no-value-echo). Sec MF-3.
    "quota_exhausted",
    # PLAN-133 D1 (Wave D) — proactive auto-compaction telemetry. Emitted via
    # emit_generic from the host loop's context-management step. Sec MF-3
    # deny-by-default allowlists + enum coercion + int clamp in the dispatch
    # gate; NO transcript text / file paths / command bytes / env values on the
    # wire (no-value-echo property test below). Default-OFF behavior
    # (CEO_AUTO_COMPACT_THRESHOLD); decision logic lives in
    # .claude/scripts/context-budget.py:decide_compaction (non-canonical).
    "context_auto_compacted",
    "context_auto_compact_suppressed",
    # PLAN-133 D5 (Wave D) — middle-out degradation ladder on the context-
    # overflow path: drop growing fractions of the MIDDLE of the largest tool-
    # response messages (keep head + tail), protecting the last N + pinned, only
    # as far as the overflow requires. Emitted via emit_generic from the host
    # loop's context-overflow step when a degradation pass acts (degraded) or
    # the ladder is exhausted (failed). Sec MF-3 deny-by-default allowlists +
    # enum coercion + 0..99 int clamp in the dispatch gate; NO message text /
    # tool names / agent names / file paths / command bytes / raw token counts
    # on the wire (no-value-echo property test below). Default-OFF behavior
    # (CEO_MIDDLE_OUT_DEGRADE); decision + transform live in
    # .claude/scripts/context-budget.py:decide_middle_out_degradation /
    # apply_middle_out_degradation (non-canonical).
    "context_middle_out_degraded",
    "context_middle_out_degrade_failed",
    # PLAN-133 E2 — OSV.dev / OSSF malicious-packages supply-chain advisory.
    # Emitted via emit_generic from .claude/scripts/osv_check.py (advisory by
    # default; CEO_OSV_GATE=block to fail-CLOSED on a MAL hit). Sec MF-3:
    # deny-by-default _SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST + closed-enum
    # verdict/reason + ecosystem coercion. NO command bytes / env / advisory-body
    # text are ever persisted — only the parsed package name, ecosystem, the
    # closed-enum verdict/reason, and the (already-public) advisory ids.
    "supply_chain_advisory_emitted",
    # PLAN-133 E3 — per-spawn tool scoping + depth/overlap rails (Sec MF-3;
    # enum coercion + int clamp in the emit_generic dispatch-gate). NO paths
    # (only 12-hex path HASHES) / prompt body / tool-arg text.
    "spawn_tool_scope_violation",
    "spawn_depth_or_overlap_blocked",
    "spawn_file_assignment_recorded",
    # PLAN-133 E6 (HITL confirmation rail) — emitted by the consuming hook,
    # NEVER by _lib/action_required.py (a pure helper). Deny-by-default
    # field allowlists + closed-enum coercion below; no-value-echo
    # (raw token / summary / rejected value never persisted).
    "action_required_held",
    "action_required_resumed",
    "action_required_rejected",
    # PLAN-107 Wave B (S145 2026-05-19) — orphan emit register.
    # `.claude/scripts/check-stdlib-only.py:280` has called
    # `emit_generic("stdlib_violation", violation_count=...)` since
    # PLAN-029, but the action was never added to _KNOWN_ACTIONS —
    # every call was silently dropped via fail-open. AC12 of PLAN-107
    # scopes the kernel delta to +1 (this orphan only). Allowlist
    # _STDLIB_VIOLATION_ALLOWLIST defined below; dispatch-gate in
    # emit_generic. SPEC v2.23 row added in same ceremony.
    "stdlib_violation",
    # PLAN-032 Wave B (ADR-063) — agent-eval tournament
    "tournament_run_started",
    "tournament_task_scored",
    "tournament_run_completed",
    "tournament_budget_projected",
    "tournament_budget_exceeded",
    "tournament_aborted",
    "tournament_fixture_rejected",
    "tournament_judge_hijack_suspected",
    # PLAN-043 / ADR-064 — dynamic tier policy dispatch events
    "tier_policy_derived",
    "tier_policy_promote_applied",
    "tier_policy_demote_requested",
    "tier_policy_rejected",
    "tier_policy_hmac_verify_failed",
    "tier_policy_adopter_override_respected",
    "tier_policy_killswitch_triggered",
    "tier_policy_dry_run_complete",
    "tier_policy_promote_cost_gated",
    # PLAN-045 Wave 5 / Round-8 — P0-09 (b) Artifact Paradox advisory hook
    # (SubagentStop) + F-10-07 v2 session-state sentinel.
    "fluency_nudge",  # P0-09 (b) — SubagentStop advisory on confidence markers
    "skill_reference_read_mismatch",  # F-10-07 v2 — SHA pin vs read-time hash diverged
    "skill_reference_read_stale",  # F-10-07 v2 — SKILL.md read older than spawn event
    "skill_reference_never_read",  # F-10-07 v2 — sub-agent never Read the pinned SKILL.md
    # PLAN-113 WIRE-DEADMOD — spawn-prompt advisory telemetry (ADVISORY-only,
    # fail-open, emitted via emit_generic from check_agent_spawn.py).
    "spec_context_sanitized",  # PLAN-113 / ADR-089 — SPEC CONTEXT block sanitizer telemetry
    # PLAN-133 A2 (Goose-harvest) — invisible-unicode hard-block breadcrumb.
    # Deny-by-default: dedicated _scrub_ branch + _INVISIBLE_UNICODE_BLOCKED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The only
    # caller-supplied payload fields are CLOSED enums / bounded ints
    # (surface, unicode_class, char_count, enforced) — the prompt/skill text, the
    # matched chars, and the var/value are NEVER persisted.
    "invisible_unicode_blocked",
    "spawn_confidence_advisory",  # PLAN-113 / PLAN-083 1.10 — spawn action-type confidence label
    # PLAN-153 Wave E item 7 (ADR-175) — Prompt Defense Baseline gate telemetry.
    # Emitted (ADVISORY, fail-open) by check_agent_spawn._emit_prompt_defense_event()
    # after an untrusted-content signal match on a NAMED spawn. Sec MF-3
    # deny-by-default via _SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST + dedicated
    # dispatch-gate branch below: `keyword` is a closed-enum hint
    # (_UNTRUSTED_CONTENT_HINTS, 32-char capped at the producer AND re-capped in
    # the dispatch gate), `present`/`enforced` are 0/1 flags — NO prompt or
    # description body is ever persisted.
    "spawn_prompt_defense_gate",
    # PLAN-017 Phase 4 — Autonomous-loop parallelism swarm events
    # (PLAN-102 Wave A extends with cost_envelope_capped +
    # swarm_runaway_suspected + swarm_paused_owner_absent. See ADR-133.)
    "cost_envelope_capped",  # PLAN-102 Wave A / ADR-133 §A
    "swarm_paused_owner_absent",  # PLAN-102 Wave A / ADR-133 §C
    "swarm_runaway_suspected",  # PLAN-102 Wave A / ADR-133 §B
    "swarm_layer_3_4_blocked",  # PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6
    "swarm_started",
    "swarm_iteration",
    "swarm_halted_budget",
    "swarm_halted_convergence",
    "swarm_halted_kill",
    # PLAN-059 SEC-P0-04 / ADR-080 — audit-tokens content-ban events.
    # Emitted by SessionEnd.py via audit-tokens.py subprocess. Allowlist
    # enforced by scrub_audit_tokens_event() — see _AUDIT_TOKENS_ALLOWLIST
    # below. Forbidden keys are stripped + audit_tokens_key_dropped
    # breadcrumb emitted (defense-in-depth on allowlist drift).
    "audit_tokens_emitted",
    "audit_tokens_timeout",
    "audit_tokens_key_dropped",
    "swarm_aborted_error",
    "swarm_killed",
    "swarm_tournament_selected",
    "swarm_finalize_grouped",
    "swarm_finalize_committed",
    # PLAN-048 Phase 2 — CEO model downshift experiment harness
    "escalation_detected",
    "escalation_dispatched",
    "escalation_suppressed",
    "escalation_baseline_recorded",
    # PLAN-052 Phase 1 / ADR-083 — MCP injection scanner advisory finding.
    # PLAN-044 audit-v2 C1-P0-03 fix (Wave B): wire emit_mcp_injection_finding
    # so check_mcp_response.py records detections in audit-log instead of
    # silently dropping (hasattr guard in check_mcp_response.py:148 was
    # always-False before this registration). See SPEC/v1/audit-log.schema.md
    # v2.13 row for the field schema.
    "mcp_injection_finding",
    # PLAN-069 Phase 1 / ADR-101 — replay capture-as-fixture lifecycle
    # Emitted by replay-session.py:_emit_started/_emit_completed when
    # mode == "capture" (mode-aware dispatch). Distinct action names from
    # replay_started/replay_completed because capture is its own mode
    # (redacted fixture write) not a dry_run/execute path. SPEC v2.16.
    "replay_capture_started",
    "replay_capture_completed",
    # PLAN-065 Phase 2 / ADR-098 (Session 82+, 2026-05-04+) — /ceo-boot
    # session-boot autopilot lifecycle. Emitted by .claude/scripts/ceo-boot.py
    # at end of every invocation (cached + uncached paths) and on per-check
    # timeout (`ceo_boot_check_skipped`). Sec MF-3 enforced field allowlist
    # below in emit_ceo_boot_emitted / emit_ceo_boot_check_skipped — denies
    # token-count + cost + paths + prompt + SKILL + env. SPEC v2.17 row
    # added in same v1.12.0 ceremony. Reality-Ledger fixture #4 closure
    # (declared-but-not-wired): pre-ceremony, ceo-boot.py shipped emit
    # comments only ("# ceo_boot_emitted emit deferred to v1.12.0
    # ceremony.") — Codex audit-v3 DIM-04 finding 2 detection pattern.
    "ceo_boot_emitted",
    "ceo_boot_check_skipped",
    # PLAN-070 Round 4 / Layer B (Codex P1-04 closure, 2026-05-04+) —
    # server-side MCP canonical-guard middleware lifecycle. Emitted by
    # `.claude/hooks/_lib/mcp/canonical_guard.py:check_mcp_call` on every
    # MCP dispatch decision (allow + block branches) for tools matching
    # `mcp__*`. Sec MF-3 field allowlists below enforce deny-by-default.
    "mcp_canonical_guard_allowed",
    "mcp_canonical_guard_blocked",
    # PLAN-071 / ADR-104 — Adaptive Execution Kernel + Reality Ledger
    # advisory events (S87 ceremony 2026-05-05 v1.14.0). Allowlists below
    # enforced via _scrub_ceo_boot_event helper (allowlist-agnostic) +
    # dispatch-gate in emit_generic (Codex R5-02 closure pattern).
    "task_route_advised",
    "task_route_key_dropped",
    "task_route_ground_truth_label",  # PLAN-101 Wave B / ADR-104-AMEND-1 §E
    # PLAN-102 Wave B — execution_context HMAC tamper-evidence.
    # RESERVED (zero producers) — PLAN-112-FOLLOWUP-execution-context-wire
    # (S154, decision RESCOPE-DEFER) closed finding F-1.2-execution_context as
    # DEFERRED: cross-process sign->validate is cryptographically infeasible
    # (per-process in-memory key; hook process => validate() == (False,
    # "no_key")). Kept (NOT deleted) to preserve the SPEC v1 + allowlist
    # contract for a future rebind. Re-wire pre-conditions: coordinator exits
    # scaffold AND a cross-process key design lands via ADR-133-AMEND-1.
    # See _lib/EXECUTION-CONTEXT-DEFERRED.md.
    "execution_context_signed",  # RESERVED — PLAN-102 Wave B / ADR-133 §D; deferred F-1.2
    "execution_context_validation_failed",  # RESERVED — PLAN-102 Wave B / ADR-133 §D; deferred F-1.2
    "reality_ledger_finding",
    "reality_ledger_key_dropped",
    # PLAN-078 Wave 1 — model routing telemetry (advisory-emit-only).
    # Emitted by check_agent_spawn._emit_model_routing_advisory() after
    # VETO-floor enforcement; NEVER affects allow/block decision. Sec MF-3
    # field allowlist enforced via _MODEL_ROUTING_ADVISED_ALLOWLIST below
    # + dispatch-gate in emit_generic. NO prompt/description/path content
    # is persisted; only archetype + classification + recommendation tags.
    "model_routing_advised",
    # PLAN-112-FOLLOWUP-persona-routing-wire W2 — god-mode matrix consult
    # telemetry. Emitted by check_agent_spawn._consult_model_routing_mode()
    # AFTER VETO-floor enforcement. CONSULT+AUDIT only — the matrix is
    # observed/audited; the model-tier BLOCK is DEFERRED (no requested-model
    # signal in the Agent hook payload). `decision` enum has NO `block`
    # value. Sec MF-3 field allowlist enforced via
    # _MODEL_ROUTING_ENFORCED_ALLOWLIST + dispatch-gate below. NO prompt /
    # description / frontmatter-path content persisted.
    "model_routing_enforced",
    # Fail-open infra branch: persona_routing import/get_mode raised. Carries
    # archetype + reason_code only.
    "model_routing_eval_error",
    # PLAN-078 Wave 2 — Reality Ledger detector #7 estimate-drift.
    # Emitted by reality-ledger.detect_estimate_drift() on plan close-outs;
    # carries plan_id (Owner-visible per ADR-033 §plan-budget) + drift
    # factors (numeric only). Allowlist below denies CSV body / plan body /
    # commit shas / file paths.
    "estimate_drift_detected",
    # Recommendation event after N=5 drifts in same direction (low/high).
    "estimate_drift_systematic_bias",
    # PLAN-078 Wave 5 — /ceo-boot recommendations TaskCreate orchestration.
    # Emitted by .claude/scripts/ceo-boot.py:_emit_task_candidate_safe per
    # marker block written to stdout when gate_pass=False AND severity>=medium.
    # Top-3 max per invocation, dedup by subject_hash via 24h TTL state file
    # (~/.claude/projects/.../state/ceo-boot-tasks-emitted.json) under
    # _lib/filelock. Sec MF-3 field allowlist enforced via
    # _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST below + dispatch-gate in
    # emit_generic. NO recommendation body / NO subject text / NO check
    # detail / NO env / NO paths — only rank + severity + 12-hex subject
    # hash + awaiting_confirm flag.
    "ceo_boot_task_candidate_emitted",
    # PLAN-075 Phase 1 narrow-promotion (ADR-106 + ADR-110) —
    # Pair-Rail Multi-LLM cross-review hook events. Wired via
    # check_pair_rail.py PreToolUse on Edit|Write|MultiEdit
    # against L3+ canonical-guarded paths.
    "pair_rail_review_passed",
    "pair_rail_codex_unavailable",
    "pair_rail_codex_violation",
    "pair_rail_sentinel_bypass",
    # PLAN-081 Phase 1-full / R1 S-Sec-5 — Codex MCP ingress
    # sanitization (check_codex_response.py PostToolUse). Fired when
    # Codex stdout contains harness-mimicry / xml-system-tag /
    # tool-use-forgery patterns. Advisory-only per ADR-106 (PostToolUse
    # cannot block; detection emits forensic trace for audit-query.py
    # codex-injection-summary).
    "pair_rail_codex_injection_detected",
    # PLAN-081 Phase 2 — dispatcher routing-matrix decision audit.
    # Fired by inject-agent-context.sh --pair-mode (and any future
    # programmatic caller) per archetype dispatch. Carries the chosen
    # rail (pair-rail vs single-LLM fallback) + matrix SHA-pin status
    # + which disable_predicate (if any) caused fallback. Sec MF-3
    # field allowlist enforced via _DISPATCHER_ROUTE_EMIT_ALLOWLIST
    # below + dispatch-gate in emit_generic. Used by Phase 2 perf
    # predicate `codex_latency_p95_s` aggregator (the wall_clock_s
    # field is sourced from this action's records).
    "dispatcher_route",
    # PLAN-081 Phase 3 — Asymmetric VETO matrix Cases A-F decision.
    # Fired by check_pair_rail.py:_decide_with_matrix() once per Pair-Rail
    # PreToolUse evaluation that reaches the matrix arm. Carries case +
    # claude_verdict + codex_verdict + Case-B preconditions + rubric +
    # severity + jaccard bucket + grace hours. Sec MF-3 enforced via
    # _PAIR_RAIL_CASE_EMIT_ALLOWLIST + dispatch-gate scrub.
    "pair_rail_case",
    # PLAN-081 Phase 4 — Promotion gate verdict.
    # Fired by .claude/scripts/run-promotion-gate.py at end of each run.
    "pair_rail_promotion",
    # PLAN-083 Wave 0b sub-agent 0.4 (S106 ceremony, 2026-05-11).
    # Fired by token-budget-guard.py when cumulative plan tokens cross threshold × estimate. Volume cap ≤10/hr.
    "token_budget_guard_paused",
    # PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony, 2026-05-11).
    # Fired by check_anti_ceo_overhead.py PreToolUse hook when CEO-overhead anti-pattern detected. Emit budget ≤20/day sliding window.
    "anti_ceo_overhead_block",
    # PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony, 2026-05-11).
    # Fired by check_anti_ceo_overhead.py when CEO_OVERHEAD_ACK=1 env override bypasses a block.
    "anti_ceo_overhead_override_used",
    # PLAN-083 Wave 0b sub-agent 0.7d (S106 ceremony, 2026-05-11).
    # Fired by smart-loading-resolver.py per resolution. Carries profile + active/suppressed counts + context budget total + arbitration dropped count.
    "smart_loading_resolved",
    # PLAN-083 Wave 2 sub-agent 2.1 (S106). Wizard completion event.
    "first_run_wizard_completed",
    # PLAN-083 Wave 2 sub-agent 2.2 (S106). Contextual recommender emit.
    "contextual_recommendation_emitted",
    # PLAN-083 Wave 2 sub-agent 2.4 (S106). Weekly value dashboard rollup.
    "value_dashboard_summarized",
    # PLAN-083 Wave 2 sub-agent 2.7 (S106). Trading-readonly write override invoked.
    "trading_write_override_used",
    # PLAN-083 Wave 2 sub-agent 2.7 (S106). Trading kill-switch read (missing repo-profile.yaml).
    "trading_kill_switch_invoked",
    # PLAN-083 Wave 2 sub-agent 2.7 (S106). Trading kill-switch disabled via escape-hatch ceremony.
    "trading_kill_switch_disabled",
    # PLAN-084 Wave 0.5 — canonical-edit lifecycle direct emit
    # (parallel to existing veto_triggered reason_code filter). AC1
    # verifier uses these direct action names.
    "canonical_edit_attempted",
    "canonical_edit_blocked",
    "sentinel_created",
    "sentinel_verified",
    "gpg_signed",
    "gpg_verified",
    "wave_readonly_violation",
    # PLAN-084 Wave 0.10 — staging artifact integrity per R2-iter-2 CODEX-P0-2.
    # Per-archetype ownership tuple; watchdog Layer 3b validation.
    "wave_artifact_written",
    # PLAN-084 Wave 0.5 — Codex egress redaction (R1 Sec-P0-2 + R2 CODEX-P0-1).
    # Mirror of pair_rail_codex_injection_detected for outgoing direction.
    "pair_rail_outgoing_redaction_applied",
    # PLAN-084 AC12d — estimate refinement per phase milestone (Bayesian-ish).
    "estimate_refined",
    # PLAN-086 Wave E — typed-wrapper promotions (S106 carryover #4).
    "mcp_route_advised",            # Wave D (R-015 MCP routing)
    "mcp_canonical_guard_internal_error",  # Wave F.2 catch-all
    "thinking_budget_set",          # Wave A.1 /effort slash command
    "codex-reply",                  # Wave C R-016 codex multi-turn
    "repo_profile_confirmed",       # Wave H.4 confirm-profile emit
    # PLAN-088 canonical-13 god-mode auto-activation (S114) — 11 net-new.
    # mcp_route_advised + model_routing_advised already registered above;
    # PLAN-088 wires production callsites onto those pre-existing stubs.
    # Per W0 ATLAS-binding table in `verify-atlas-binding.py` _CANONICAL_13.
    "cache_discipline_alerted",            # W1.1 AUTO-01 — F1 hook-driven (telemetry-only)
    "ceo_boot_persona_coverage_score",  # PLAN-093 Wave C.5
    "first_run_wizard_dispatched",         # W1.2 AUTO-02 — F1 hook-driven (UX trigger)
    "estimate_calibrator_pipeline_run",    # W1.3 AUTO-03 / W6.1 — F4 telemetry (Bayesian pipeline)
    "subagent_findings_partial_drop",      # W1.4 SEMI-13 — F4 (AML.T0048 Governance bypass)
    "anthropic_429_observed",              # W1.4 SEMI-13 — F4 (AML.T0029 Denial of ML Service)
    "git_index_lock_retry",                # W1.4 SEMI-13 — F4 telemetry (infra-error)
    "codex_invoke_dispatched",             # W1.4 SEMI-13 — F4 (AML.T0050 LLM Plugin Compromise)
    "tier_policy_misrouting_advised",      # W2.1 AUTO-04 — F2 (AML.T0048 Governance bypass)
    "tier_policy_loader_fallback_observed",  # PLAN-116 (S172) — loader advisory-fallback telemetry
    "cookbook_pattern_advised",            # W3.2 SEMI-11 — F3 skill (UX hint)
    "pair_rail_phase_advanced",            # W4.1 AUTO-07 — F4 (AML.T0050 dual-rail check)
    "batch_dispatched",                    # W4.2 AUTO-08 — F4 (cost-optimization telemetry)
    # PLAN-089 Wave C.5 — kernel + auth hardening audit surface.
    # ADR-121 sentinel signers rotation + ADR-116-AMEND-1 kernel extension.
    "kernel_extension_landed",             # Wave A.4 — _KERNEL_PATHS extension ceremony emit
    "bash_canonical_bypass_invoked",       # Wave B.4 — CEO_BASH_CANONICAL_BYPASS HMAC kill-switch use
    "sentinel_signer_rotated",             # Wave C.5 — rotation success
    "sentinel_signer_expiry_warned",       # Wave C.5 — 60d-before-expires_at notice (rate-capped 1/hour)
    "sentinel_signer_revoked",             # Wave C.5 — explicit revocation (R1 IDA P0 fold — separate from _rotated)
    "sentinel_signer_quorum_failed",       # Wave C.5 — R1 TDE P0 fold — SOC consumption canary
    "sentinel_signer_quorum_attempted",    # Wave C.5 — R1 IDA P2 fold — forensic completeness regardless of outcome
    # PLAN-090 Wave A — Phase C enforcing flip + persona-routing audit surface.
    "phase_c_enforcing_flipped",
    "persona_auto_decision_emitted",
    "persona_auto_rate_capped",
    "kill_switch_invoked",
    # PLAN-090 Wave B — BatchClaudeLiveAdapter streaming + verbose audit surface.
    "streaming_token_yielded",
    "streaming_rate_capped",
    # PLAN-090 Wave C — ADR-122 §B firing path.
    "mcp_bearer_friction_observed",
    # PLAN-090 AMENDMENT-1 — confidence-gate empirical baseline.
    "confidence_gate_baseline_emitted",
    # PLAN-090 Wave D — capability rollout completion sentinel.
    "capability_rollout_complete",
    # PLAN-094 Wave 0 (ADR-055-AMEND-1) — spool-writer drain forensic events.
    "audit_flush_dropped_count",
    "audit_spool_stale_recovered",
    "audit_spool_partial_line_discarded",
    "audit_spool_tamper_detected",
    "audit_spool_duplicate_tuple_rejected",
    "audit_spool_intentionally_deleted",
    "audit_spool_unexpected_skip",
    # PLAN-094 Wave B (R-039) — smart-loading frontmatter cache stats.
    "skill_cache_stats",
    # PLAN-096 (ADR-042-AMEND-1) — Wave D cross-tenant + Wave E soak FPR.
    "mcp_cross_tenant_denied",
    "mcp_soak_fpr_breach",
    # PLAN-097 (ADR-062-AMEND-1 / ADR-128 §6) — Wave C RAG routing audit surface.
    "rag_profile_recommended",
    "rag_auto_wire_skipped_sidecar_down",
    "rag_query_routed",
    "rag_false_large_demoted",
    "rag_hit_rate_degraded",
    # PLAN-098 (ADR-132) — GOAP A* advisory-only planner audit surface.
    "goap_edge_explored",
}
