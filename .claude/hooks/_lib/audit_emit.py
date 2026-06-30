"""Typed event emitters for audit-log.jsonl event stream v2.

Promotes audit-log.jsonl from single-event-type (`agent_spawn`) to a
typed event stream with discriminator field `action` covering spawns,
debate rounds, plan transitions, veto triggers, benchmark runs, and
lesson writes. See PLAN-004 Phase 1 + ADR-005.

## Design contract

- **Additive only.** v1 `agent_spawn` entries remain valid; no fields
  removed. `event_schema: "v2"` field marks new entries. Consumers
  tolerate unknown fields per AUDIT-LOG-SCHEMA.md §2 forward-compat.
- **Fail-open.** Any emission error writes breadcrumb to `audit-log.errors`
  and returns silently. Framework MUST NOT block on observability.
- **Concurrent-write safe.** Uses `_lib.filelock.FileLock` (same lock
  file as `audit_log.py`).
- **Redaction.** Free-text fields (`desc_preview`, `reason_preview`)
  pass through `_lib.redact.redact_secrets` before write.
- **Stdlib-only.** No new dependencies.

## Public API (pure functions)

    emit_debate_event(plan_id, round, phase, agent, artifact_path, ...)
    emit_plan_transition(plan_id, from_status, to_status, file_path, ...)
    emit_veto_triggered(hook, reason_code, reason_preview, blocked_tool, ...)
    emit_benchmark_run(benchmark_id, skill, pass_rate, median_score, ...)
    emit_lesson_write(lesson_id, archetype, scope_tags, trigger, ...)

All emitters are side-effect-only (return None). Unit tests use
`TestEnvContext` from `_lib.testing` for isolation.

## Reserved fields (writer-deferred)

Every v2 event reserves nullable `tokens_in`, `tokens_out`, `tokens_total`
fields for future per-event cost accounting (AI specialist proposal P5,
deferred to Sprint 6). Schema reservation is free today; back-filling
schema later would force consumer breakage.
"""

from __future__ import annotations

import json
import os
import sys
import threading  # PLAN-088 W1.4 / M-12 rate-cap state lock
import time  # PLAN-088 W1.4 / M-12 rate-cap sliding window
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import redact as _redact  # noqa: E402
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402

import getpass  # noqa: E402

# PLAN-023 Phase B (ADR-055) — HMAC chain integration. Import guarded
# so the module loads even if audit_hmac is unavailable during partial
# rollout; fail-open invariant covers the runtime path.
try:
    from _lib import audit_hmac as _audit_hmac  # noqa: E402
    _HMAC_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_hmac = None  # type: ignore[assignment]
    _HMAC_AVAILABLE = False

# PLAN-094 Wave A.3 — spool-writer hot-path wire-in (ADR-055-AMEND-1).
# Kill-switch: CEO_AUDIT_SYNC_MODE=1 reverts to pre-Wave-A sync-fsync-per-call.
try:
    from _lib import spool_writer as _spool_writer  # noqa: E402
    _SPOOL_WRITER_AVAILABLE = True
except Exception:  # pragma: no cover
    _spool_writer = None  # type: ignore[assignment]
    _SPOOL_WRITER_AVAILABLE = False

# F-CHAOS-1 (PLAN-019) — session-scoped one-shot banner guard. Prevents
# per-write banner spam when the primary audit dir stays unwritable.
_FALLBACK_NOTIFIED = False


def _fallback_log_path() -> Path:
    """Return the /tmp fallback audit path, user-scoped.

    Env override: ``CEO_AUDIT_LOG_FALLBACK_PATH`` for tests.
    """
    override = os.environ.get("CEO_AUDIT_LOG_FALLBACK_PATH")
    if override:
        return Path(override)
    try:
        user = getpass.getuser() or "unknown"
    except Exception:  # pragma: no cover
        user = os.environ.get("USER") or "unknown"
    user = "".join(c for c in user if c.isalnum() or c in ("-", "_", "."))
    return Path("/tmp") / f"ceo-audit-fallback-{user}.log"


def _emit_fallback_banner_once(primary: Path, fallback: Path, err: str) -> None:
    """Emit `::warning::` stderr banner once per session (F-CHAOS-1)."""
    global _FALLBACK_NOTIFIED
    if _FALLBACK_NOTIFIED:
        return
    _FALLBACK_NOTIFIED = True
    try:
        sys.stderr.write(
            f"::warning::audit-log write failed ({err}); "
            f"falling back to {fallback}. "
            f"Investigate writability of {primary.parent}.\n"
        )
        sys.stderr.flush()
    except Exception:  # pragma: no cover
        pass


def _write_fallback(event_line: str) -> bool:
    """Append ``event_line`` to fallback path with 0o600. Never raises."""
    try:
        fallback = _fallback_log_path()
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with fallback.open("a", encoding="utf-8") as f:
            f.write(event_line)
            # PLAN-025 F-obs-002 — durability on fallback path too; if the
            # primary failed and we're writing fallback, crash-safety matters
            # MORE than on the happy path.
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass
        try:
            os.chmod(fallback, 0o600)
        except OSError:
            pass
        return True
    except Exception as e:
        try:
            sys.stderr.write(
                f"[audit_emit] fallback write ALSO failed: "
                f"{type(e).__name__}: {e}\n"
            )
            sys.stderr.flush()
        except Exception:  # pragma: no cover
            pass
        return False


# Event schema version marker — bump only on breaking change
EVENT_SCHEMA_V2 = "v2"

# Known action literals (v2). v1 used `agent_spawn` only.
_KNOWN_ACTIONS = {
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
    "goap_search_aborted",
    "goap_search_summary",
    "goap_cycle_detected",
    "goap_depth_exceeded",
    "goap_replan_triggered",
    "goap_replan_exhausted",
    "goap_disabled_by_env",
    "goap_recommendation_accepted",
    # PLAN-105 Wave A.1 + A.2 — GOAP recommendation outcome telemetry.
    "goap_recommendation_rendered",
    "goap_recommendation_overridden",
    # PLAN-099 (ADR-129 / ADR-135) — federation cross-machine MVP audit surface.
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
    # PLAN-099-FOLLOWUP Wave F — federation write-mode audit surface
    # (ADR-129-AMEND-1 / ADR-135-AMEND-1 / attack-rebinding.md §2).
    # 20 actions touched; +19 net-new (federation_cert_rotated already
    # in set from PLAN-099 MVP S134, field-shape-superseded in-place).
    # Registered via kernel-override
    # PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION at v1.39.1.
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
    "federation_peer_registered",
    "federation_peer_registered_collision",
    "federation_peer_revoked_remote",
    "federation_pin_legacy_used",
    "federation_scope_denied",
    "federation_spki_fingerprint_mismatch",
    "federation_tamper_detected",
    "federation_write_disabled_sentinel_invalid",
    "federation_write_endpoint_denied",
    "federation_peer_list_reloaded",
    # PLAN-104 Wave A — persona-demand ledger audit surface (S134 R2 ACCEPT).
    "persona_demand_opened",
    "persona_demand_matched",
    "persona_demand_unmet",
    "persona_demand_waived",
    # PLAN-090-FOLLOWUP Wave A — claim producer pair (S138 R2 ACCEPT).
    "claim_emitted",
    "confidence_gate_verdict",
    # PLAN-100 Wave B — per-class block-mode (S139 R2 ACCEPT;
    # ADR-019-AMEND-1 PROPOSED). confidence_gate_blocked emitted when
    # decision.action == "block"; confidence_gate_fp_drift_detected
    # emitted by check-confidence-gate-drift.py on 7d rolling FPR > 2%.
    "confidence_gate_blocked",
    "confidence_gate_fp_drift_detected",
    # PLAN-106 Wave C — persona-coverage 4×4 cell emit from production
    # hooks (check_agent_spawn allow path + check_canonical_edit allow
    # path). Source field carries `dispatch` | `canonical_edit` for
    # downstream attribution. NO public typed wrapper — emit_generic +
    # Sec MF-3 scrub keeps `_EXPECTED_PUBLIC_SYMBOLS` stable per
    # PLAN-102 Wave A precedent (S142 R2 iter-1 P1 #3 fold).
    "persona_coverage_synthesized",
    # PLAN-110 Wave D — protocol_semver_cascade advisory hook
    "protocol_edit_missing_amend_paired",
    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — chain_reset_marker is
    # the synthetic genesis entry written as line 1 of every rotation-
    # created fresh audit-log.jsonl. Per ADR-055-AMEND-2 (drafted in
    # this plan): verifier reads `audit-log.rotation-manifest.json`
    # sidecar; if present, line 1 of fresh log MUST be a
    # chain_reset_marker entry — non-marker line 1 = STATUS_TAMPER.
    # Registered via kernel-override
    # PLAN-112-FOLLOWUP-WAVE-B3-AUDIT-EMIT-EXTENSION at v1.39.4.
    "chain_reset_marker",
    # PLAN-118 AC-B5 — closed-enum producer-pollution forensic breadcrumb.
    # Emitted by chokepoint 1 (audit_emit._emit_chain_reset_marker_under_lock)
    # + chokepoint 4 (spool_writer._phase4_build_batch) when the canonical-
    # resolution check (audit_hmac._ensure_canonical_lib_modules) detects
    # a stale `_lib` copy on sys.path. Allowlist payload: chokepoint
    # (enum: chain_reset_marker | spool_drain) + reason_code (enum:
    # audit_emit_path_pollution | canonical_json_path_pollution |
    # audit_hmac_path_pollution) + path_sha256_prefix (8 hex chars) +
    # expected_canonical_prefix (8 hex chars). NO `__file__` raw echo
    # per [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]].
    "audit_producer_path_pollution_detected",
    # PLAN-125 WS-1 (kooky-harvest) — per-tool-call lifecycle telemetry.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH (Sec MF-SEC-2). Carries ONLY 4 closed fields:
    # tool_name_enum (mcp__* → mcp_other, Sec MF-SEC-1), duration_bucket
    # (coarse enum, never raw duration_ms, Sec MF-SEC-3), success, orphan.
    "tool_call_lifecycle_recorded",
    # PLAN-124 WS-1 (ECC value-harvest) — git hook-bypass guard breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `flag_class` (closed enum, MF-G); the
    # matched command bytes are NEVER persisted (a malicious flag value such as
    # `-c http.extraHeader="Bearer <secret>"` could otherwise leak).
    "git_hook_bypass_blocked",
    # PLAN-133 A1 — linker/loader/runtime env-hijack denylist breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `hijack_class` (closed enum); the matched
    # variable NAME and the assigned VALUE are NEVER persisted (the value can be
    # a path/preload payload or a smuggled secret).
    "env_var_hijack_blocked",
    # PLAN-133 A3 — egress-destination taxonomy breadcrumb (advisory). Routes
    # through the dedicated _scrub_ branch + _EGRESS_DESTINATION_DETECTED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The ONLY
    # caller-supplied fields are `egress_class` (closed enum) + `destination`
    # (BARE HOST only — never the full URL/path/query/credential).
    "egress_destination_detected",
    # PLAN-133 E1 — adversary local-rules deny/ask gate breadcrumb. Deny-by-default:
    # routes through the dedicated _scrub_ branch + _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The ONLY
    # caller-supplied fields are `decision` + `rule_class` (both closed enums) and
    # `rule_id` (author-controlled config token). The matched COMMAND bytes and any
    # env value are NEVER persisted.
    "adversary_review_flagged",
    # PLAN-133 G1 — MOIM persistent-instructions BLOCKING validator breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `reason` (closed enum) + integer counts
    # `family_hits`/`bytes_scanned`. The instruction-file body, the matched
    # line, and any path/env value are NEVER persisted.
    "persistent_instructions_blocked",
    # PLAN-133 G3 — hierarchical nested .claude/hints.md provenance breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _HINT_PROVENANCE_RECORDED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `reason` (closed enum) + integer
    # `rel_dir_depth` / `family_hits` / `bytes_scanned`. The hint-file body, the
    # matched line, and the absolute/relative PATH text are NEVER persisted —
    # only the integer directory DEPTH below the repo root.
    "hint_provenance_recorded",
    # PLAN-135 W1 S3 — /ceo-boot Tier-S settings/env tamper tripwire
    # breadcrumb (one emit per detected tamper class). Deny-by-default:
    # routes through the dedicated _scrub_ branch +
    # _SETTINGS_TAMPER_DETECTED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied fields are `tamper_class` + `layer` (both
    # closed enums mirroring _lib/effective_config; coerced to "other" on
    # a miss) and integer `finding_count` (clamped 0..99). The tamper
    # finding DETAIL (endpoint URL / model id / helper path / flag value)
    # and any env VALUE are NEVER persisted.
    "settings_tamper_detected",
    # PLAN-135 W2 H2 — ConfigChange guard: a settings-surface config change
    # was observed and NO forbidden-key finding was scoped to it (allow +
    # audit path of check_config_change.py). Deny-by-default: routes through
    # the dedicated _scrub_ branch + _CONFIG_CHANGE_OBSERVED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `layer` (closed enum
    # user/project/local/managed/other; coerced to "other" on a miss). The
    # changed file's CONTENT, its path text and any key/value are NEVER
    # persisted.
    "config_change_observed",
    # PLAN-135 W2 H2 — ConfigChange guard: a forbidden-key finding
    # (_lib/effective_config.FORBIDDEN_KEYS, the S3/H2 single source) was
    # scoped to a settings-surface config change → advisory-block (one emit
    # per tamper class, settings_tamper_detected producer precedent).
    # Deny-by-default: dedicated _scrub_ branch +
    # _CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH. The ONLY caller-supplied fields are
    # `tamper_class` (closed enum mirroring _lib/effective_config
    # TAMPER_CLASSES; coerced to "other") + `layer` (closed enum
    # user/project/local/managed/other; coerced to "other") and integer
    # `finding_count` (clamped 0..99). The forbidden key's VALUE (endpoint
    # URL / model id / helper path / flag value) and the finding DETAIL are
    # NEVER persisted.
    "config_change_forbidden_key",
    # PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PreCompact governance
    # snapshot breadcrumb (one emit per compaction event,
    # check_precompact_continuity.py). Deny-by-default: routes through the
    # dedicated _scrub_ branch + _COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied fields are `trigger` + `snapshot_outcome`
    # (closed enums, coerced to "other"), `plan_id` (strict PLAN-NNN shape
    # check, coerced to "unknown") and integer `chain_length` (clamped
    # 0..99999999). The snapshot BODY (plan path, checkbox position,
    # ceremony flags, last-hmac prefix) lives in the plan-scoped scratchpad
    # ONLY and is NEVER persisted on the audit wire.
    "compaction_continuity_snapshot",
    # PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PostCompact
    # governance-pointer reinjection breadcrumb
    # (check_postcompact_reinject.py). Deny-by-default: dedicated _scrub_
    # branch + _COMPACTION_CONTEXT_REINJECTED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH. The ONLY caller-supplied fields are
    # `plan_id` (strict PLAN-NNN shape check, coerced to "unknown"),
    # boolean `snapshot_found` (any non-bool coerced to False) and integers
    # `snapshot_age_s` (clamped 0..9999999) + `pointer_count` (clamped
    # 0..9). The reinjected additionalContext TEXT is NEVER persisted
    # (pointers-only by design; the audit wire carries counters, not
    # context).
    "compaction_context_reinjected",
    # PLAN-135 W2 H5 (ADR-154 single-rewriter) — check_bash_safety rewrote a
    # `git push --force`/`-f` Bash input to `--force-with-lease` via the
    # PreToolUse `updatedInput` channel (surfaced as an `ask`, never a silent
    # allow). Deny-by-default: dedicated _scrub_ branch +
    # _BASH_INPUT_REWRITTEN_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `rewrite_class` (closed enum, coerced to
    # "other") + the before/after sha256 hash PAIR (`before_sha256` /
    # `after_sha256`, each validated to 64-hex else coerced to ""). The
    # command BYTES (before OR after) are NEVER persisted — a force-push line
    # can carry a remote URL with an inline token; the hash pair lets an
    # auditor prove audited-cmd == executed-cmd without seeing either command
    # (ADR-154 §2 before/after hash invariant).
    "bash_input_rewritten",
    # PLAN-135 W2 H3 — per-agent lifecycle bracket emitted ONCE at SubagentStop
    # (.claude/hooks/check_fluency_nudge.py H3 extension) after consuming the
    # SubagentStart sidecar (check_subagent_start.py) + the harness-supplied
    # `agent_transcript_path`: the S227 `modelUsage` forensic reconstruction
    # becomes a live hook emit, feeding the persona-ledger (PLAN-104) + quota
    # economics. Deny-by-default: dedicated _scrub_ branch +
    # _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). EVERY
    # caller-supplied field is a CLOSED enum or a coarse BUCKET — `agent_archetype`
    # (persona-ledger archetype enum, coerced to "other"/"unknown"), `wall_bucket`
    # + `wall_source` + `token_bucket` + `claim_bucket` (closed enums). RAW
    # wall-time seconds, RAW token counts, the transcript path/body, the
    # confidence-marker snippets and the raw agent_id are NEVER persisted —
    # only the closed-enum brackets travel (the bracket is the audit signal; the
    # raw counts stay forensic-private, mirroring the S227 reconstruction).
    "subagent_lifecycle_observed",
    # ---- PLAN-135 ARC CONSOLIDATION — W5 ops actions folded in one place ----
    # The three W5 actions are TRUSTED-producer emit_generic actions (the
    # emitter is a standalone Owner-run / Owner-configured script OR the
    # adapter library itself, not a deny-by-default hook). The producers
    # pre-redact at the emit site (key-hygiene.py `_redact()`; statusline-ceo.py
    # passes only numbers/enum-ids; claude.py drops `stop_details.explanation`
    # and forwards ONLY the closed `stop_details.category` vocabulary) — BUT per
    # Codex R5 P1-2 (PLAN-135-FOLLOWUP) producer-side pre-redaction is NOT the
    # only line: each action is ALSO given a dedicated deny-by-default scrub
    # branch in emit_generic (NEVER _EMIT_GENERIC_PASSTHROUGH) so the Sec MF-3
    # field-allowlist + enum-value-coercion boundary holds against a direct /
    # future mis-caller that bypasses the trusted producer — the established
    # invisible_unicode_blocked / tool_call_lifecycle_recorded precedent. They
    # are "branched" members of the ghost-action-guard tri-state invariant.
    # PLAN-135 W5 o9 — Anthropic Admin API key-lifecycle breadcrumb
    # (.claude/scripts/key-hygiene.py `_audit_emit` -> emit_generic). Closed-enum
    # `operation`/`reason` + IDs/counts only; key material never reaches the emit
    # (producer `_redact()` on free text). Secondary tamper-evident breadcrumb;
    # the load-bearing artifact is the append-only docs/rotation-log.md row.
    "admin_key_lifecycle_event",
    # PLAN-135 W5 o4 — statusLine sidecar-write breadcrumb
    # (.claude/scripts/statusline-ceo.py `maybe_emit` -> emit_generic). Debounced
    # (material-digest + CEO_STATUSLINE_EMIT_INTERVAL_S); carries only the sidecar
    # abs path, plan-id, percentages, bucket count, session_id + a 12-char digest
    # prefix — never the raw statusLine stdin free text. The load-bearing artifact
    # is the atomic sidecar JSON (always written); this event arms post-ceremony.
    "statusline_sidecar_write",
    # PLAN-135 W5 o7 — model-refusal observability breadcrumb
    # (.claude/hooks/_lib/adapters/live/claude.py `_on_response` -> emit_generic on
    # stop_reason == "refusal"). Forwards ONLY the closed provider
    # `stop_details.category` vocabulary (<=64 chars) + provider/model slugs +
    # status/duration ints; `stop_details.explanation` (model free text) is dropped
    # at the emit site and can NEVER reach the audit log.
    "model_refusal_observed",
}


# PLAN-065 Phase 2 / ADR-098 — Sec MF-3 field allowlist for /ceo-boot events.
# Whitelist (deny-by-default). Forbidden fields stripped + breadcrumbed before
# emit. Caller passes ceo_boot_emitted/_check_skipped via the typed wrappers
# below; emit_generic dispatch is also gated by the allowlist (defense-in-
# depth on adopter or future-CEO drift). See PLAN-065 §4.3.4.
_CEO_BOOT_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",  # reserved nullable per v2 contract
    "hmac", "hmac_error",  # ADR-055 chain fields
    "gate_pass", "duration_ms", "checks_total", "checks_failed", "cache_hit",
})
_CEO_BOOT_CHECK_SKIPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "check_name", "timeout_ms",
})
_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST = frozenset({  # PLAN-093 Wave C.5 + PLAN-104 carry-over
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "score_x100", "cells_covered", "total_cells",
    # PLAN-104 Wave A.2 — S127 scope-(b) carry-over (3 fields).
    "window_hours", "events_with_target_archetype", "eligible_demand_events",
})

# PLAN-070 Round 6 / Codex R6-01 closure — Sec MF-3 field allowlist for
# Layer B MCP middleware events. Tightened to the agreed 6-field contract
# (Sec ACCEPT-CONDITIONAL R4 + Codex R6-01 P2 ratification, 2026-05-05):
#
#   caller-supplied: tool_name, target_path, reason
#   auto-baseline:   action, ts (==timestamp), session_id, project,
#                    event_schema, tokens_*, hmac, hmac_error
#
# Deny-by-default. NO raw params, NO content/patch body, NO sentinel
# body, NO error class names, NO reason_code (renamed -> reason), NO
# file_path (renamed -> target_path). Pre-R6-01 the allowlist included
# `reason_code`/`file_path`/`sentinel`/`error` as caller fields — Codex
# R6-01 flagged this as schema drift from the agreed Sec MF-3 contract;
# the canonical_guard.py emit call sites are simultaneously renamed.
_MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tool_name", "target_path", "reason",
})
_MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST = _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST


# PLAN-071 / ADR-104 — task-route + reality-ledger field allowlists
# (Sec MF-3 enforcement, deny-by-default). Forbidden fields stripped +
# breadcrumb action emitted. Token counts, cost, prompt content,
# SKILL.md content, file paths, recommendation text body, environment
# values are NEVER persisted to audit-log.
#
# S87 ceremony hot-fix (post Codex audit #15): the ceremony script's
# first injection pass skip-check matched on the dispatch-gate
# REFERENCE (audit_emit.py:2037+2046) instead of the definition,
# leaving these frozensets undefined. Codex MCP audit caught the
# runtime NameError pre-tag; injected directly via Bash python3
# inline (matches S80 ceremony pattern; arbitration-kernel hook
# matcher is Edit|Write|MultiEdit only).
_TASK_ROUTE_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "contract_id", "classification", "task_description_hmac",
    "duration_ms",
})

_REALITY_LEDGER_FINDING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "detector", "severity",
    # confidence_bps: integer basis-points (confidence × 1000, 0..1000).
    # canonical_json forbids floats; the old "confidence" float (0.0-1.0)
    # caused CanonicalJsonError on every reality_ledger_finding emit.
    "confidence_bps",
    "claim_source_sha256", "finding_count_in_run",
})

# PLAN-101 Wave B / ADR-104-AMEND-1 §E — task_route_ground_truth_label.
# Append-only ground-truth join-key for AEK calibration C3 FPR matrix.
# Sec MF-3 deny-by-default: only the 8 fields below persist; LLM06
# hold preserved (raw task descriptions never persisted via this row).
_TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "contract_id", "ground_truth_class", "ground_truth_source",
    "annotation_confidence_bps",
})

# PLAN-102 Wave A / ADR-133 §A — cost_envelope_capped.
# Emitted by check_cost_envelope.py on HARD CAP breach.
# Sec MF-3 deny-by-default: project_path raw, user_id raw, plan body,
# command text are NEVER persisted via this row.
_COST_ENVELOPE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "class_tier", "window_breached", "cap_cents", "current_cents",
})

# PLAN-102 Wave A / ADR-133 §B — swarm_runaway_suspected.
# Reverse-tripwire over 24h rolling iteration counter; advisory only.
_SWARM_RUNAWAY_SUSPECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "iteration_count_24h", "threshold", "triggering_class",
})

# PLAN-102 Wave A / ADR-133 §C — swarm_paused_owner_absent.
# Weekend-burn detector. loop_duration_hours bucketed (>=1h) to avoid
# wallclock side-channel leakage.
_SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "loop_duration_hours", "last_owner_read_iso", "swarm_pid",
})

# PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — swarm_layer_3_4_blocked.
# Per-iteration runtime gate event (distinct from swarm_paused_owner_absent
# which is the weekend-burn detector). LLM06 hold: NO command text, NO
# sentinel body, NO env values, NO file paths, NO error stack traces.
_SWARM_LAYER_3_4_BLOCKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "class_tier", "reason_code", "loop_id",
})

# PLAN-102 Wave B / ADR-133 §D — execution_context_signed.
# Emitted whenever an execution_context HMAC is recorded against an
# autonomous-loop iteration. NO command text, NO plan body.
_EXECUTION_CONTEXT_SIGNED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "context_hash", "key_id", "iteration",
})

# PLAN-102 Wave B / ADR-133 §D — execution_context_validation_failed.
# Emitted when execution_context HMAC verification fails (tamper signal).
# Sec MF-3 deny-by-default: forbid raw context body.
_EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "context_hash", "key_id", "iteration", "failure_reason",
})


# PLAN-078 Wave 1 — `model_routing_advised` field allowlist (deny-by-default).
# 6 caller fields per plan §4 Wave 1 + the auto-baseline (action, ts,
# session_id, project, event_schema, tokens_*, hmac, hmac_error) added by
# `_write_event`. NO prompt content, NO description, NO path of agent
# frontmatter file, NO classify rationale, NO env-var values.
#
# Codex W1+W2 fix-pack #2: confidence is integer basis-points (0..1000)
# instead of float — canonical_json forbids floats, otherwise HMAC chain
# breaks with `hmac=null` + `hmac_error=CanonicalJsonError` breadcrumb.
# 0.875 caller → 875 emitted; consumer divides by 1000 to recover ratio.
_MODEL_ROUTING_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "task_type", "model_recommended",
    "confidence_basis_points", "applied_or_skipped", "override_reason",
})


# PLAN-122 WS12 — Sec MF-3 deny-by-default field allowlists for the optimizer
# recommender actions. The allowlist gates only CALLER-supplied fields (the
# scrub runs in emit_generic BEFORE _write_event); _write_event adds the
# ts/event_schema/tokens_*/hmac/hmac_error envelope by setdefault AFTER the
# scrub, so those reserved fields are NOT (and must NOT be) allowlisted here —
# allowlisting tokens_* would let a caller inject a token-count side channel
# (Codex 019e7ebc P1). The optimizer caller passes only `action` + `session_id`
# + the per-action fields below. NO prompt body, NO file paths, NO label free
# text, NO secret/token side-channel.
_OPTIMIZER_ENVELOPE = ("action", "session_id")
_OPTIMIZER_ALLOWLISTS = {
    "optimizer_route_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "route", "complexity_bucket", "parallelizable", "suggested_width",
        "prompt_len_bucket", "kill_switch_state",
    )),
    "fanout_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "subtask_count", "suggested_width", "width_capped", "budget_governed",
        "rate_backoff_applied", "models_basis",
    )),
    "model_choice_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "subtask_index", "model_recommended", "confidence_basis_points",
        "cost_governed", "fell_back_to_static",
    )),
    "rag_context_recommended": frozenset(_OPTIMIZER_ENVELOPE + (
        "router_decision", "chunks_returned", "kill_switch_state",
    )),
    "codex_review_disabled": frozenset(_OPTIMIZER_ENVELOPE + (
        "reason",
    )),
    # PLAN-122 WS3 — per-phase Codex review event. Caller-supplied fields ONLY
    # (PhaseReview-shaped, redacted). NO raw Codex text, NO tokens_* side channel,
    # NO review_disabled_signal bool.
    "codex_review_invoked": frozenset(_OPTIMIZER_ENVELOPE + (
        "phase_number", "review_status", "summary_hash", "thread_id_redacted",
        "codex_model", "duration_ms", "violations_found_count",
        "review_source", "target_ref_hash",  # PLAN-132 / ADR-145 (branch-binding)
    )),
}


# PLAN-128 §7 (S217) — accelerator catch-emit closed enums + allowlists (Sec MF-3).
# Invalid enum value is coerced to "other" in the dispatch-gate (S172: never echo the
# rejected value); the breadcrumb lists dropped KEY NAMES only. Counts clamped 0..99.
_ACCEL_LANG_ENUM = frozenset({"python", "js_ts", "go", "other"})
_VERIFY_CHECKER_ENUM = frozenset({"py_compile", "ruff", "eslint", "node_check", "go_build", "other"})
_ADEQUACY_REASON_ENUM = frozenset({"no_test_delta", "weak_assertion", "uncovered_change", "other"})

# PLAN-132 / ADR-145 — closed enums for cross-model review provenance + match
# modality. S172 doctrine: an invalid value coerces to a safe sentinel, never echoed.
_CODEX_REVIEW_STATUS_ENUM = frozenset({"invoked", "passed", "failed", "deferred", "other"})
_CODEX_REVIEW_SOURCE_ENUM = frozenset({"phase_gate", "user_code_auto", "adhoc_mcp", "other"})
_PERSONA_MATCH_MODALITY_ENUM = frozenset({"native_spawn", "codex_review"})


def _safe_target_ref_hash_field(v):
    """Return a non-empty 12-hex (or shorter) lowercase hash, else '' (fail-closed;
    never echoes a rejected value such as a raw branch name a caller tried to stuff)."""
    s = str(v or "")
    if s and len(s) <= 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return ""


def _accel_clamp_count(v):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return 0 if n < 0 else (99 if n > 99 else n)


_VERIFY_AFTER_EDIT_FINDING_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "checker", "lang", "finding_count",
))
_ADEQUACY_GATE_FLAG_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "flag_reason", "lang", "flag_count",
))


# PLAN-133 B5 — provider/cost error taxonomy mirror closed enums + allowlist (Sec MF-3).
# error_class is coerced to a closed-enum member in the dispatch-gate (S172: an
# invalid value is replaced by "unknown", NEVER echoed). source is a closed enum
# distinguishing the metered-API path from the subscription main loop. NO
# retry_delay / Retry-After / body / header value is ever allowlisted — the
# backoff seconds are a caller-side float that must never reach the payload.
_QUOTA_ERROR_CLASS_ENUM = frozenset({
    "quota_exhausted", "credits_exhausted", "auth", "rate_limited", "overloaded",
    "server_error", "bad_request", "timeout", "network", "unknown",
})
_QUOTA_ERROR_SOURCE_ENUM = frozenset({"subscription_main_loop", "metered_api", "subprocess", "unknown"})

_QUOTA_EXHAUSTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    # closed-enum scalars + bounded ints ONLY
    "error_class",        # closed enum (coerced)
    "source",             # closed enum (coerced)
    "http_status",        # int (the bare status code; no body)
    "retryable",          # bool
    "metered_api_only",   # bool
    "attempt",            # int 0..99 (clamped) — which retry attempt
    "project",
))


# PLAN-133 D1 — proactive auto-compaction telemetry. Closed enums so a malformed
# value coerces to a safe sentinel (S172 doctrine: never echo a rejected value).
# `reason` mirrors REASON_* in scripts/context-budget.py. `trigger` distinguishes
# the high/low-water hysteresis edge. NO bytes/tokens raw text — only bucketed
# percentages (0..100 clamp) so a transcript size can never be reconstructed
# field-by-field into a side channel.
_AUTO_COMPACT_REASON_ENUM = frozenset({
    "compact", "cooldown", "reclaim_floor", "not_rearmed",
    "below_high_water", "disabled", "other",
})
_AUTO_COMPACT_SUPPRESS_REASON_ENUM = frozenset({
    "cooldown", "reclaim_floor", "other",
})


def _auto_compact_clamp_pct(v):
    """Coerce to an int percent in [0, 100]; 0 on malformed (never echoes)."""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return 0 if n < 0 else (100 if n > 100 else n)


# context_auto_compacted — a compaction WAS performed. Carries only the closed
# reason enum + the hysteresis percentages + the reclaimed-percent bucket + a
# turn counter. `reason` IS in the allowlist (the dispatch gate coerces it).
_CONTEXT_AUTO_COMPACTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "usage_pct", "reclaim_pct", "turns_since_last",
))
# context_auto_compact_suppressed — a would-be compaction was SKIPPED by a gate
# (cooldown or reclaim-floor). Carries the closed suppression reason + the same
# bucketed percentages.
_CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "suppress_reason", "usage_pct", "reclaim_pct", "turns_since_last",
))


# PLAN-133 D5 — middle-out degradation telemetry for the context-overflow path.
# Closed enums so a malformed value coerces to a safe sentinel (S172 doctrine:
# never echo a rejected value). `reason` mirrors MO_REASON_* in
# scripts/context-budget.py. Only bucketed COUNTS + a small ladder-rung int are
# carried (0..99 clamp) — NOT the message text, tool/agent identity, file paths,
# or raw token totals — so a transcript can never be reconstructed field-by-
# field into a side channel.
_MIDDLE_OUT_REASON_ENUM = frozenset({
    "degraded", "failed", "no_overflow", "disabled", "other",
})


# context_middle_out_degraded — a degradation pass DID elide >=1 message's
# middle to fit the budget. Carries only the closed reason enum + bucketed
# counts (degraded / total messages + protect_last) + the ladder `rung` int
# (0..99 clamp) + a coarse reclaim-tokens BUCKET + the `fits_after` bool.
# `reason` IS in the allowlist (the dispatch gate coerces it).
_CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "rung", "degraded_count", "total_count", "protect_last",
    "reclaim_bucket", "fits_after",
))
# context_middle_out_degrade_failed — the ladder was exhausted (or no message
# was eligible) and the context STILL overflows; the caller must summarize /
# compact / fail upstream. Carries the closed reason + bucketed counts + rung.
_CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "reason", "rung", "degraded_count", "total_count", "protect_last",
    "reclaim_bucket",
))


# PLAN-133 E2 — supply-chain advisory closed enums + field allowlist.
# verdict/reason are closed enums (coerce-to-"other" on a miss); ecosystem
# coerces to "other"; advisory_count is an int clamped 0..99. The package
# name + advisory ids are caller-supplied but are PUBLIC identifiers (a pkg
# name + a published OSV id) — never a path, command, env, or error body.
_SUPPLY_CHAIN_VERDICT_ENUM = frozenset({"BLOCK", "ALLOW", "SKIP"})
_SUPPLY_CHAIN_REASON_ENUM = frozenset({
    "mal_advisory_present", "clean", "unknown", "malformed_response",
    "network_timeout", "network_error", "offline", "disabled", "no_package",
})
_SUPPLY_CHAIN_ECOSYSTEM_ENUM = frozenset({"npm", "PyPI", "other"})
_SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "verdict", "reason", "ecosystem", "package", "advisory_count",
))


# PLAN-133 E3 — closed enums + deny-by-default field allowlists. Mirror the
# §7 (verify_after_edit_finding) pattern exactly. NO raw path / prompt / tool
# arg ever appears — `detail` is tool-NAMES + counts only; paths are 12-hex
# sha256 prefixes.
_SPAWN_RAIL_ENUM = frozenset({"tool_scope", "depth", "overlap", "other"})

_SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "rail", "enforced", "detail",
))
_SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "rail", "enforced", "count",
))
_SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "path_hashes", "path_count",
))


def _e3_clamp01(v):
    """Coerce to 0/1 (enforced flag). Anything truthy-but-weird -> 0 (safe)."""
    try:
        return 1 if int(v) == 1 else 0
    except (TypeError, ValueError):
        return 0


def _e3_safe_path_hashes(v):
    """Keep only comma-joined 12-hex tokens; drop anything else (a caller
    that tries to stuff a raw path gets it silently dropped, never echoed)."""
    s = str(v or "")
    toks = []
    for t in s.split(","):
        t = t.strip()
        if t and len(t) <= 12 and all(c in "0123456789abcdef" for c in t):
            toks.append(t)
    return ",".join(toks)[:512]


# PLAN-133 E6 — HITL confirmation-rail closed enums + field allowlists.
# S172 doctrine: an invalid value coerces to a safe sentinel, never echoed.
_ACTION_REQUIRED_KIND_ENUM = frozenset({
    "bash_command", "file_write", "file_delete", "spend_over_cap",
    "spawn", "network_egress", "other",
})
_ACTION_REQUIRED_REJECT_ENUM = frozenset({
    "unknown_token", "replayed", "expired", "session_mismatch",
    "action_id_mismatch", "malformed_request", "infra_error", "other",
})


def _safe_token_sha_field(v):
    """Return a 64-hex lowercase token hash, else '' (fail-closed; never
    echoes a rejected value such as a raw token a caller tried to stuff)."""
    s = str(v or "")
    if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
        return s
    return ""


_ACTION_REQUIRED_HELD_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "kind", "token_sha256", "expires_at",
))
_ACTION_REQUIRED_RESUMED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "token_sha256",
))
_ACTION_REQUIRED_REJECTED_ALLOWLIST = frozenset(_OPTIMIZER_ENVELOPE + (
    "action_id", "token_sha256", "reject_reason",
))


# PLAN-112-FOLLOWUP-persona-routing-wire W2 — `model_routing_enforced`
# field allowlist (deny-by-default). Forensic telemetry of the god-mode
# matrix consult. `killswitch_armed` is a bool (canonical_json-safe).
# `decision` enum: enforce_telemetry | advisory | eval_error — NO `block`
# value (block deferred). NO prompt/description/frontmatter-path content.
_MODEL_ROUTING_ENFORCED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "mode", "recommended_model",
    "killswitch_armed", "decision",
})

# PLAN-112-FOLLOWUP-persona-routing-wire W2 — `model_routing_eval_error`
# fail-open infra branch allowlist. Carries archetype + reason_code +
# `decision` (always the constant "eval_error" — keeps the `decision`
# enum {enforce_telemetry, advisory, eval_error} consistent across BOTH
# new actions per AC5).
_MODEL_ROUTING_EVAL_ERROR_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "reason_code", "decision",
})


# PLAN-113 Phase B B-STRUCTURAL — federation emit_generic Sec MF-3 field
# allowlists (deny-by-default). Closes the "ghost-action leak" finding: the
# ~25 `federation_*` actions reach `emit_generic` via
# `_lib.federation.*._safe_emit(action, **fields)` but had NO dispatch-gate
# branch — so before this plan their caller kwargs were written VERBATIM into
# the HMAC audit log (no allowlist scrub). Each allowlist below is the union
# of the framework envelope (`_FEDERATION_ENVELOPE`) + the per-action SAFE
# fields taken BYTE-FOR-BYTE from SPEC/v1/audit-log.schema.md v2.29/v2.33.
#
# LLM06 / GDPR hold preserved per the SPEC rows: full SPKI/DER fingerprints
# are never logged (only `*_prefix` 16-hex), full IPs are /24-truncated
# (`ip_prefix`) where the producer truncates, and the two filesystem-path
# fields (`source_path`, `sentinel_path`) are NEVER persisted raw — the
# dispatch-gate re-hashes them via `_federation_safe_path_hash` (12-hex)
# BEFORE write, so an accidental caller cannot leak a host path into the
# chained log.
_FEDERATION_ENVELOPE = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# Read-path connection lifecycle (PLAN-099 MVP / ADR-129 / ADR-135). `client_ip`
# is persisted per the SPEC v2.27 rows (read-path connection forensics; the
# LLM06 drop applies to the WRITE-handler emits, not these).
_FEDERATION_CONNECTION_ACCEPTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "client_ip", "fed_correlation_id",
}
_FEDERATION_CONNECTION_REJECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id_cert_fingerprint", "client_ip", "reason",
}
_FEDERATION_CONNECTION_REPLAY_SUSPECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "client_ip", "reason",
}
_FEDERATION_CERT_EXPIRY_WARNED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "days_remaining",
}
_FEDERATION_CERT_REVOKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "reason",
}
_FEDERATION_CERT_VALIDITY_WINDOW_TOO_LARGE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "window_days", "max_days",
    # SPEC v2.29 also carries the ISO bounds + duration_days for the
    # advisory; allow them (no PII — cert validity window is public).
    "not_before_iso", "not_after_iso", "duration_days",
}
_FEDERATION_ENABLE_SENTINEL_INVALID_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "sentinel_kind", "reason",
}
_FEDERATION_LAN_BIND_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "bind_host", "resolved_ip", "reason",
}
# Write-mode surface (PLAN-099-FOLLOWUP Wave E/F.2 / ADR-135-AMEND-1).
_FEDERATION_WRITE_ATTEMPT_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id_cert_fingerprint", "client_ip", "fed_correlation_id",
    "method", "path",
}
_FEDERATION_WRITE_ENDPOINT_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "gate_failed", "reason_code",
}
_FEDERATION_WRITE_DISABLED_SENTINEL_INVALID_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "reason_code", "sentinel_path",  # sentinel_path re-hashed in dispatch-gate
}
_FEDERATION_SCOPE_DENIED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "required_scope", "peer_scopes_count",
}
_FEDERATION_EVENT_ACTION_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "event_action", "reason_code",
}
_FEDERATION_AUDIT_EVENT_PUSHED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "event_action", "hmac_ok", "origin_overwritten",
}
_FEDERATION_AUDIT_EVENT_PUSHED_BATCH_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "batch_size", "accepted_count", "rejected_count",
}
_FEDERATION_PEER_REGISTERED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "scopes_count", "spki_fingerprint_prefix",
}
_FEDERATION_PEER_REGISTERED_COLLISION_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "attempted_by_origin_peer_id",
}
_FEDERATION_PEER_REVOKED_REMOTE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "revoked_by_origin_peer_id", "reason_code",
}
_FEDERATION_PEER_INVALID_NO_FINGERPRINT_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "source_path",  # source_path re-hashed in dispatch-gate
}
_FEDERATION_PEER_LIST_RELOADED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "peer_count", "reload_reason",
    "source_path",  # source_path re-hashed in dispatch-gate
}
_FEDERATION_PIN_LEGACY_USED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "der_fingerprint_prefix",
}
_FEDERATION_SPKI_FINGERPRINT_MISMATCH_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "expected_prefix", "presented_prefix", "route",
}
# T1499 DoS surface (PLAN-099-FOLLOWUP Wave E.1 / ADR-135-AMEND-1 §2.4).
_FEDERATION_MESSAGE_STORM_DETECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "ip_prefix", "hits_in_window", "window_seconds",
}
_FEDERATION_AUDIT_LOG_BACKPRESSURE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "p99_latency_ms", "window_seconds", "action_taken",
}
# T1565 tamper surface (PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6).
_FEDERATION_TAMPER_DETECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "route", "tamper_type", "prev_hash_prefix",
}

# PLAN-113 Phase B B5 — RESERVED-no-producer registry. Each maps a registered
# `_KNOWN_ACTIONS` member that has ZERO production caller today to its gating
# ADR. The CI-guard test (test_audit_emit_ghost_action_guard.py) asserts (a)
# every member here is truly producer-less and (b) if a member ever GROWS a
# production caller, its gating ADR MUST be in ACCEPTED state — else fail.
# Verified against SPEC/v1/audit-log.schema.md governing-ADR columns:
#   - execution_context_* : ADR-133 §D (cross-process wiring DEFERRED, F-1.2)
#   - federation_autonomous_call_blocked : ADR-135 (PLAN-099 import-graph
#     denylist surface; AC18 helper exists but is never invoked)
#   - federation_hmac_secret_rotated : ADR-135-AMEND-1 §6 (Owner co-sign
#     rotate path not wired to a producer)
#   - federation_key_floor_rejected / _stale : ADR-129-AMEND-1 §3/§4
#     (key-floor enforcement is advisory-staged; no emit producer yet)
# NOTE: federation_tamper_detected / federation_message_storm_detected /
# federation_audit_log_backpressure are NOT reserved — they have live
# `_safe_emit` producers (audit_chain_ext.py / rate_limit.py) and get explicit
# dispatch-gate branches above.
_RESERVED_ACTIONS = {
    "execution_context_signed": "ADR-133",
    "execution_context_validation_failed": "ADR-133",
    "federation_autonomous_call_blocked": "ADR-135",
    "federation_hmac_secret_rotated": "ADR-135-AMEND-1",
    "federation_key_floor_rejected": "ADR-129-AMEND-1",
    "federation_key_floor_stale": "ADR-129-AMEND-1",
}

# PLAN-113 Phase B B-STRUCTURAL — emit_generic verbatim-passthrough registry.
# These `_KNOWN_ACTIONS` members are emitted via emit_generic by TRUSTED
# in-repo producers (their own typed wrappers in this module, or first-party
# hook/script producers) with controlled, pre-scrubbed field sets. They have
# no dedicated dispatch-gate scrub branch and their verbatim pass-through is
# the ACCEPTED pre-existing contract (each has direct field-presence coverage
# in test_audit_emit_coverage.py). They are explicitly enumerated here so the
# default-deny `else` in emit_generic can distinguish them from a genuinely
# unhandled / future / unexpected producer.
#
# INVARIANT (enforced by test_audit_emit_ghost_action_guard.py): every
# `_KNOWN_ACTIONS` member is EXACTLY ONE of: (a) has an explicit `action ==`
# dispatch-gate branch, (b) is in `_RESERVED_ACTIONS`, or (c) is in this
# passthrough set. Any member matching NONE of the three reaches the
# default-deny `else` (all caller kwargs dropped). A NEW action added to
# `_KNOWN_ACTIONS` therefore defaults to fail-closed (default-deny) until the
# author either gives it a scrub branch or consciously lists it here — the
# leak class cannot silently reopen.
_EMIT_GENERIC_PASSTHROUGH = frozenset({
    # admin_key_lifecycle_event MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST scrub
    # branch in emit_generic: Sec MF-3 deny-by-default + operation/reason
    # enum-value coercion enforced even against a direct emit_generic caller.
    "agent_spawn",
    "audit_flush_dropped_count",
    "audit_spool_duplicate_tuple_rejected",
    "audit_spool_intentionally_deleted",
    "audit_spool_partial_line_discarded",
    "audit_spool_stale_recovered",
    "audit_spool_tamper_detected",
    "audit_spool_unexpected_skip",
    "audit_tokens_emitted",
    "audit_tokens_key_dropped",
    "audit_tokens_timeout",
    # bash_canonical_bypass_invoked REMOVED from passthrough (PLAN-113 Codex P1):
    # routed through explicit _BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST scrub branch
    # so target_path_hash (12-hex sha256) is the ONLY path representation in the log
    # (replaces the old target_path_preview raw-path field; Sec MF-3 P1 fix).
    "benchmark_run",
    "breaker_closed",
    "breaker_opened",
    "budget_bypass_used",
    "budget_exceeded",
    "canonical_edit_attempted",
    "canonical_edit_blocked",
    "capability_rollout_complete",
    "chain_reset_marker",
    "codex-reply",
    "confidence_gate",
    "confidence_gate_baseline_emitted",
    "credential_rotation_due",
    "debate_event",
    "escalation_baseline_recorded",
    "escalation_detected",
    "escalation_dispatched",
    "escalation_suppressed",
    "estimate_refined",
    "federation_cert_rotated",
    "fluency_nudge",
    "goap_cycle_detected",
    "goap_depth_exceeded",
    "goap_disabled_by_env",
    "goap_edge_explored",
    "goap_recommendation_accepted",
    "goap_recommendation_overridden",
    "goap_recommendation_rendered",
    "goap_replan_exhausted",
    "goap_replan_triggered",
    "goap_search_aborted",
    "goap_search_summary",
    "gpg_signed",
    "gpg_verified",
    "injection_flag",
    "kernel_extension_landed",
    "kill_switch_invoked",
    "lesson_archived",
    "lesson_outcome",
    "lesson_outcome_undone",
    "lesson_read",
    "lesson_restored",
    "lesson_write",
    "live_adapter_call_failed",
    "live_adapter_call_started",
    "live_adapter_call_succeeded",
    "mcp_bearer_friction_observed",
    "mcp_canonical_guard_internal_error",
    "mcp_cross_tenant_denied",
    "mcp_handler_denied",
    "mcp_handler_invoked",
    # mcp_injection_finding REMOVED from passthrough (PLAN-113 Codex B3 P1):
    # it carries MCP-controlled snippet_preview → routed through an explicit
    # scrub branch with allowlist + _preview() re-truncation instead.
    "mcp_server_disabled_by_kill_switch",
    "mcp_server_started",
    "mcp_soak_fpr_breach",
    # model_refusal_observed MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _MODEL_REFUSAL_OBSERVED_ALLOWLIST scrub
    # branch in emit_generic (stop_reason/stop_category/http_status/duration_ms
    # value-bounded against a direct caller).
    "otel_export_dropped",
    "output_safety_flag",
    "output_scan_finding",
    "pair_rail_codex_unavailable",
    "pair_rail_codex_violation",
    "pair_rail_review_passed",
    "pair_rail_sentinel_bypass",
    "pattern_evicted",
    "pattern_queried",
    "pattern_stored",
    "persona_auto_decision_emitted",
    "persona_auto_rate_capped",
    "phase_c_enforcing_flipped",
    "plan_transition",
    "policy_denied",
    "policy_error",
    "policy_evaluated",
    "prediction_queried",
    "prompt_submitted",
    "protocol_edit_missing_amend_paired",
    "rag_auto_wire_skipped_sidecar_down",
    "rag_false_large_demoted",
    "rag_hit_rate_degraded",
    "rag_index_redacted",
    "rag_profile_recommended",
    "rag_query_fallback",
    "rag_query_issued",
    "rag_query_redacted",
    "rag_query_returned",
    "rag_query_routed",
    "reality_ledger_key_dropped",
    "replay_capture_completed",
    "replay_capture_started",
    "replay_completed",
    "replay_diff_produced",
    "replay_started",
    "repo_profile_confirmed",
    "sentinel_created",
    "sentinel_signer_expiry_warned",
    "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed",
    "sentinel_signer_revoked",
    "sentinel_signer_rotated",
    "sentinel_verified",
    "session_end",
    "session_start",
    "session_stop",
    "skill_bootstrap_post_hash",
    "skill_bootstrap_used",
    "skill_cache_stats",
    "skill_patch_applied",
    "skill_reference_never_read",
    "skill_reference_read_mismatch",
    "skill_reference_read_stale",
    # spawn_confidence_advisory + spec_context_sanitized REMOVED from passthrough
    # (PLAN-113 Codex P2): moved to explicit per-action allowlist branches so
    # Sec MF-3 deny-by-default is structurally enforced even if a future
    # callsite adds unexpected fields. See _SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST
    # and _SPEC_CONTEXT_SANITIZED_ALLOWLIST below + dispatch branches in
    # emit_generic.
    "squad_imported",
    "state_store_pruned",
    "state_store_read",
    "state_store_write",
    # statusline_sidecar_write MOVED out of passthrough (Codex R5 P1-2,
    # PLAN-135-FOLLOWUP) → dedicated _STATUSLINE_SIDECAR_WRITE_ALLOWLIST scrub
    # branch in emit_generic (numeric/id/digest fields type-bounded; sidecar_path
    # length-capped against a direct caller).
    "streaming_rate_capped",
    "streaming_token_yielded",
    "swarm_aborted_error",
    "swarm_finalize_committed",
    "swarm_finalize_grouped",
    "swarm_halted_budget",
    "swarm_halted_convergence",
    "swarm_halted_kill",
    "swarm_iteration",
    "swarm_killed",
    "swarm_started",
    "swarm_tournament_selected",
    "task_route_key_dropped",
    "thinking_budget_set",
    "threat_model_freshness_breach",
    "threat_model_promoted",
    "tier_policy_adopter_override_respected",
    "tier_policy_demote_requested",
    "tier_policy_derived",
    "tier_policy_dry_run_complete",
    "tier_policy_hmac_verify_failed",
    "tier_policy_killswitch_triggered",
    "tier_policy_promote_applied",
    "tier_policy_promote_cost_gated",
    "tier_policy_rejected",
    "tournament_aborted",
    "tournament_budget_exceeded",
    "tournament_budget_projected",
    "tournament_fixture_rejected",
    "tournament_judge_hijack_suspected",
    "tournament_run_completed",
    "tournament_run_started",
    "tournament_task_scored",
    "veto_triggered",
    "wave_artifact_written",
    "wave_readonly_violation",
})

# Defense-in-depth allowlists for the 3 destructive RESERVED federation
# actions (no producer today; if an accidental caller appears, fields are
# allowlist-bounded not raw). Fields per SPEC v2.29 rows.
_FEDERATION_AUTONOMOUS_CALL_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "call_site",
}
_FEDERATION_HMAC_SECRET_ROTATED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "rotation_reason_code",
}
_FEDERATION_KEY_FLOOR_REJECTED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "key_type", "key_bits", "curve_name", "reason_code",
}
_FEDERATION_KEY_FLOOR_STALE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "peer_id", "key_floor_verified_at_iso", "advisory_only",
}


# PLAN-113 Codex P1 — bash_canonical_bypass_invoked field allowlist.
# target_path_preview REMOVED (raw filesystem path → Sec MF-3 violation).
# Replaced by target_path_hash (12-hex sha256 prefix; no path body leaks).
_BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "token_hash_prefix",
    "target_path_hash",
    "ticket_expires_in_s",
    "atlas_technique",
}

# PLAN-113 Codex P2 — spawn_confidence_advisory explicit allowlist.
# Moved from _EMIT_GENERIC_PASSTHROUGH so Sec MF-3 deny-by-default is
# structurally enforced. Fields: bounded enums/labels from
# check_agent_spawn._emit_spawn_confidence_advisory() per SPEC v2.34.
_SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "action_type",
    "confidence_level",
    "confidence_marker",
    "reason_code",
    "is_named_spawn",
}

# PLAN-113 Codex P2 — spec_context_sanitized explicit allowlist.
# Moved from _EMIT_GENERIC_PASSTHROUGH so Sec MF-3 deny-by-default is
# structurally enforced. Fields: bounded counters/flags from
# check_agent_spawn._maybe_sanitize_spec_context() per SPEC v2.34.
# No prompt content is persisted — all fields are derived byte/count metrics.
_SPEC_CONTEXT_SANITIZED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "original_bytes",
    "cleaned_bytes",
    "truncated",
    "sentinel_violations",
    "control_chars_stripped",
    "bidi_zw_chars_stripped",
    "tag_chars_stripped",
    "header_escape_count",
}

# PLAN-135-FOLLOWUP (Codex R5 P1-2) — the 3 W5 ops actions move OFF
# _EMIT_GENERIC_PASSTHROUGH into dedicated deny-by-default scrub branches so the
# Sec MF-3 field-allowlist + enum-value-coercion boundary holds against a direct /
# future emit_generic caller that bypasses the trusted producer. Field sets are
# byte-accurate to the live producers AND to SPEC/v1/audit-log.schema.md L480-482.
#
# o9 — Anthropic Admin API key-lifecycle (.claude/scripts/key-hygiene.py
# `_audit_emit`). Producer passes operation + a per-call-site subset of
# {key_count | key_id | reason | rotation_log_appended}; rotated_by/notes go to
# docs/rotation-log.md, NEVER the emit. `reason` is a REQUIRED credential-forensic
# field (the WHY of a key deactivation) — kept + enum-coerced, never dropped.
_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "operation",
    "key_id",
    "key_count",
    "reason",
    "rotation_log_appended",
}
# Closed enums for VALUE re-coercion (mirror key-hygiene.py: the operation
# discriminator + VALID_REASONS). Out-of-set → "other" (S172 coerce-to-safe-
# sentinel) so a direct caller cannot smuggle free text through an allowed key.
_ADMIN_KEY_OPERATIONS = frozenset({"list", "deactivate", "incident"})
_ADMIN_KEY_REASONS = frozenset({"compromise", "suspicion", "scheduled"})

# o4 — statusLine sidecar-write (.claude/scripts/statusline-ceo.py `maybe_emit`).
# session_id is already in _FEDERATION_ENVELOPE; sidecar_path is an abs path SPEC
# L481 explicitly permits — length-capped to bound log-line bloat / oversized-field
# log-injection (Codex R5 P1-2 sec must-fix).
_STATUSLINE_SIDECAR_WRITE_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "sidecar_path",
    "plan_id",
    # PLAN-135-FOLLOWUP-2 (S234): percentage fields are HMAC-covered ->
    # integer basis-points (pct * 100), NEVER float. The canonical encoder
    # forbids float (S181 / ADR-055-AMEND-2); the float form was written
    # with hmac=null on every emit since v2.44. Producer converts pct->bps;
    # the scrub branch below clamps to int authoritatively.
    "context_pct_bps",
    "bucket_count",
    "buckets_used_pct_max_bps",
    "digest",
}
_STATUSLINE_SIDECAR_PATH_CAP = 512
_STATUSLINE_STR_CAP = 256

# o7 — model-refusal observability (.claude/hooks/_lib/adapters/live/claude.py
# `_on_response`). stop_reason is the const "refusal"; stop_category is the closed
# provider vocabulary (<=64); http_status/duration_ms are bounded non-negative ints
# (no float in the HMAC-covered chain — S181 doctrine).
_MODEL_REFUSAL_OBSERVED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "provider",
    "model",
    "stop_reason",
    "stop_category",
    "http_status",
    "duration_ms",
}

# PLAN-133 A2 — Sec field allowlist for invisible_unicode_blocked. Deny-by-default.
# The ONLY caller-supplied payload fields are the closed-enum `surface` +
# `unicode_class`, the bounded int `char_count`, and the flag `enforced`. The
# prompt / skill text, the matched characters, and any var/value are NEVER allowed
# fields, so smuggled content can never reach the signed chain.
_INVISIBLE_UNICODE_BLOCKED_ALLOWLIST = _FEDERATION_ENVELOPE | {
    "surface",
    "unicode_class",
    "char_count",
    "enforced",
}

# PLAN-133 A2 — closed unicode_class enum. MUST mirror
# _lib/spec_context_sanitizer.INVISIBLE_UNICODE_CLASSES. Kept as a literal frozenset
# here (NOT imported) so audit_emit has zero import-time dependency on the sanitizer;
# a drift is caught by a dedicated test (the two frozensets MUST be equal). A value
# outside this set is COERCED to "control" before emit (defense-in-depth).
_INVISIBLE_UNICODE_CLASSES = frozenset({
    "tag_block", "bidi_zw", "control", "none",
})

# PLAN-133 A2 — closed surface enum (origin of the detection). Out-of-set → "spawn".
_INVISIBLE_UNICODE_SURFACES = frozenset({
    "spawn", "skill_write", "skill_read",
})


def _federation_safe_path_hash(raw: str) -> str:
    """Return a 12-hex hash of a filesystem-path field (Sec MF-3 / LLM06).

    Mirrors :func:`_persona_demand_safe_hash` strictness: an already-12-hex
    value passes through (idempotent re-hash safe); anything else (a raw
    host path) is SHA-256'd and truncated to 12 hex chars so no path body
    can leak into the HMAC-chained audit log.
    """
    import hashlib
    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:12]


# PLAN-078 Wave 2 — `estimate_drift_detected` field allowlist (deny-by-default).
# 6 caller fields per plan §4 Wave 2 + auto-baseline. NO commit SHAs (raw),
# NO file paths, NO plan body text, NO CSV row body. plan_id is Owner-
# visible per ADR-033 §plan-budget precedent.
#
# Codex W1+W2 fix-pack #2: drift_factor_*_basis_points are int (multiplier
# × 1000). 1.234× → 1234; 0.500× → 500. Float forbidden by canonical_json
# (HMAC-covered field constraint). Severity classification + reality-ledger
# in-memory math still uses float for precision; only emission converts
# to int basis-points. systematic_bias_direction enum is
# "" | "underestimate" | "overestimate" (we under-estimated when actual
# span > estimated upper bound, factor > 1.2 = "overrun" semantically;
# we over-estimated when actual span < estimated lower bound,
# factor < 0.83 = "underrun" semantically). Codex S89 call #4 alignment.
_ESTIMATE_DRIFT_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "plan_id", "drift_factor_compute_basis_points",
    "drift_factor_owner_basis_points",
    "severity", "plan_count_in_run", "systematic_bias_direction",
})

# PLAN-078 Wave 2 — `estimate_drift_systematic_bias` recommendation event.
# Strict 4-caller-field contract: bias_direction, plans_affected_count,
# avg_drift_factor_compute_basis_points, avg_drift_factor_owner_basis_points.
# Codex W1+W2 fix-pack #2: avg factors emitted as int basis-points to
# preserve HMAC chain (canonical_json no-floats invariant).
_ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "bias_direction", "plans_affected_count",
    "avg_drift_factor_compute_basis_points",
    "avg_drift_factor_owner_basis_points",
})


# PLAN-078 Wave 5 — `ceo_boot_task_candidate_emitted` field allowlist
# (deny-by-default). 4 caller fields per plan §4 Wave 5 Layer A + auto-baseline.
# Sec MF-3 enforcement: NO subject text body, NO recommendation text body,
# NO check name, NO check stderr/detail, NO env values, NO file paths.
# `subject_hash` is a 12-hex-char prefix of sha256(canonicalized subject) for
# dedup state-file bookkeeping; `rank` is 1..3 (top-3 cap); `severity` is the
# recommendation engine bucket {low, medium, high} bound to ASCII a-z; and
# `awaiting_confirm` is a bool reserved for a future "Owner-must-confirm"
# escape (default False — Claude orchestrator auto-creates the task in
# the v1.15.0 baseline without confirmation). Dispatch-gate in emit_generic
# re-enforces the allowlist defensively for any direct caller drift.
_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "rank", "severity", "subject_hash", "awaiting_confirm",
})


# PLAN-081 Phase 1-full / R1 S-Sec-5 / Sec MF-3 — pair_rail_codex_injection_detected
# allowlist. Codex stdout pattern matches MUST emit ONLY the pattern family +
# match count + length-bucketed first offset; NEVER raw matched content nor raw
# offset values (LLM06 side-channel guard — raw offset leaks prompt prefix length).
# Dispatch-gate in emit_generic re-enforces this allowlist defensively for any
# direct caller drift.
_PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tool_name", "family_ids", "match_count", "first_offset_bucket",
})


# PLAN-081 Phase 2 / Sec MF-3 — dispatcher_route allowlist.
# Carries dispatcher decision metadata for audit forensics + perf metric
# extraction (`codex_latency_p95_s` predicate aggregator reads
# wall_clock_s from this action). NEVER persists raw archetype profile,
# task description, skill content, or matrix YAML body — those would
# duplicate canonical-guarded sources or leak prompt content (LLM06
# side-channel). Only:
#   - archetype: which archetype was dispatched
#   - rail: "pair_rail" | "fallback_claude_only" | "fallback_codex_only"
#   - reason_code: "ok" | "predicate_<id>_fired" | "matrix_sha_mismatch" |
#       "health_prereq_unmet_<u-id>"
#   - matrix_sha256_prefix: 16-hex prefix of loaded matrix sha (never raw)
#   - matrix_sha256_match: bool (vs CEO_PAIR_RAIL_MATRIX_SHA256 env)
#   - coder / reviewer: provider names from routing-matrix.yaml
#   - coder_model: model floor (sonnet/opus/haiku)
#   - reviewer_sandbox: sandbox mode for the reviewer
#   - wall_clock_s: dispatcher-side resolution wall-clock (perf metric
#       source; bounded float ≥0)
#   - retry_at_timeout_s: present when the dispatcher hit a fallback
#       retry path (R1 C7 codex.py timeout classifier)
# Dispatch-gate in emit_generic re-enforces this allowlist defensively
# for any direct caller drift.
_DISPATCHER_ROUTE_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "rail", "reason_code",
    "matrix_sha256_prefix", "matrix_sha256_match",
    "coder", "reviewer", "coder_model", "reviewer_sandbox",
    "fallback_provider",
    # Codex iter 1 P0-1: wall-clock + retry timing carried as **integer
    # milliseconds**, NOT float seconds, because canonical_json forbids
    # floats in HMAC-covered fields per `_lib/canonical_json.py:85`.
    # Float emit would fail HMAC chain with `hmac_error=CanonicalJsonError`,
    # silently dropping the audit-trail signal needed by the
    # `codex_latency_p95_s` predicate aggregator. Aggregator divides by
    # 1000 to recover seconds for p95 percentile comparison.
    "wall_clock_ms", "retry_at_timeout_ms",
})


# PLAN-081 Phase 3 / Sec MF-3 — pair_rail_case allowlist.
# Carries asymmetric VETO matrix Cases A-F decision metadata. NEVER
# persists raw Codex review body / proposed-content / raw file path.
_PAIR_RAIL_CASE_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "case", "claude_verdict", "codex_verdict",
    "precondition_met", "rubric_violation_id", "severity",
    "jaccard_similarity_bucket", "file_path_hash_prefix",
    "tool_name", "human_triage_grace_h",
})


# PLAN-081 Phase 4 / Sec MF-3 — pair_rail_promotion allowlist.
_PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "run_id", "verdict", "corpus_n", "corpus_manifest_sha",
    "catch_rate_num", "catch_rate_den",
    "fp_rate_bucket", "schema_adherence_pct_bucket", "rubric_gap_pp_bucket",
    "codex_cli_version", "python_version", "git_head_sha_prefix",
    "pass_2_retry_used", "manual_triage",
})

# PLAN-083 Wave 0b sub-agent 0.4 (S106 ceremony) — Sec MF-3
# field allowlist for token_budget_guard_paused.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by token-budget-guard.py when cumulative plan tokens cross threshold × estimate. Volume cap ≤10/hr.
_TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "plan_id", "estimate_tokens", "actual_tokens", "ratio_basis_points", "threshold_basis_points",
})

# PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony) — Sec MF-3
# field allowlist for anti_ceo_overhead_block.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by check_anti_ceo_overhead.py PreToolUse hook when CEO-overhead anti-pattern detected. Emit budget ≤20/day sliding window.
_ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "anti_pattern_id", "count_in_window", "override_recommended_subagent_type",
})

# PLAN-083 Wave 0b sub-agent 0.5 (S106 ceremony) — Sec MF-3
# field allowlist for anti_ceo_overhead_override_used.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by check_anti_ceo_overhead.py when CEO_OVERHEAD_ACK=1 env override bypasses a block.
_ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "anti_pattern_id", "override_justification_sha",
})

# PLAN-083 Wave 0b sub-agent 0.7d (S106 ceremony) — Sec MF-3
# field allowlist for smart_loading_resolved.
# Deny-by-default. NEVER persists raw content / paths / token text.
# Fired by smart-loading-resolver.py per resolution. Carries profile + active/suppressed counts + context budget total + arbitration dropped count.
_SMART_LOADING_RESOLVED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "profile", "active_count", "suppressed_count", "context_total_tokens", "arbitration_dropped_count",
})


def _audit_dir() -> Path:
    """Return the audit log directory (env-overridable; matches audit_log.py)."""
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _log_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    return _audit_dir() / "audit-log.jsonl"


def _lock_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_LOCK")
    if env:
        return Path(env)
    return _audit_dir() / "audit-log.lock"


def _errors_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_ERR")
    if env:
        return Path(env)
    return _audit_dir() / "audit-log.errors"


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 second-precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _breadcrumb(message: str) -> None:
    """Append a failure breadcrumb. Fail-open: never raise."""
    try:
        err = _errors_path()
        err.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with err.open("a", encoding="utf-8") as f:
            f.write(f"{_utc_now_iso()} audit_emit: {message}\n")
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# PLAN-045 Wave 2 P0-07/08 rotation wire — shared with audit_log.py
# ---------------------------------------------------------------------------

# 10 MiB default rotation threshold (matches audit_log.DEFAULT_ROTATE_AT_BYTES).
# Overridable via CEO_AUDIT_LOG_ROTATE_BYTES for tests.
_DEFAULT_ROTATE_AT_BYTES = 10 * 1024 * 1024


def _rotate_threshold() -> int:
    """Return the active rotation threshold (bytes).

    Mirrors `audit_log.rotate_threshold()` so both write paths use
    identical semantics. Env override: ``CEO_AUDIT_LOG_ROTATE_BYTES``.
    """
    env = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
    if env:
        try:
            val = int(env)
            if val > 0:
                return val
        except ValueError:
            pass
    return _DEFAULT_ROTATE_AT_BYTES


def _now_month_slug() -> str:
    """Return the current UTC year-month slug (YYYY-MM) for rotated files.

    Mirrors `audit_log.now_month_slug()`; kept local to avoid a runtime
    coupling on that module (audit_emit.py is a leaf `_lib/` primitive
    per ADR-002, audit_log.py is a hook entrypoint).
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


# Import guard for the shared rotation primitive. Fail-open: if the
# module is missing during partial rollout, `_rotate_if_needed_safe`
# becomes a no-op and the existing write path continues unchanged.
try:
    from _lib.audit_rotation import rotate_if_needed as _shared_rotate_if_needed  # noqa: E402
    _ROTATION_AVAILABLE = True
except Exception:  # pragma: no cover
    _shared_rotate_if_needed = None  # type: ignore[assignment]
    _ROTATION_AVAILABLE = False


def _rotate_if_needed_safe(log_path: Path) -> Optional[Path]:
    """Invoke the shared rotation primitive; fail-open on any error.

    MUST be called UNDER the audit-log FileLock. Returns the rotated-to
    path on success or None if no rotation was performed.
    """
    if not _ROTATION_AVAILABLE or _shared_rotate_if_needed is None:
        return None
    try:
        return _shared_rotate_if_needed(
            log_path, _rotate_threshold(), _now_month_slug()
        )
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"rotate_if_needed exception: {type(e).__name__}: {e}")
        return None


# PLAN-120-FOLLOWUP WS-D (E4-F4) — single source of truth for the
# rotation_trigger closed enum. Previously the public helper
# emit_chain_reset_marker validated membership but the internal
# _emit_chain_reset_marker_under_lock (the path actually exercised on
# automatic rotation) did not, so a future/buggy internal caller could land
# an off-enum free-text trigger in the on-disk chain_reset_marker. Both
# helpers now route through _normalize_rotation_trigger().
_VALID_ROTATION_TRIGGERS = frozenset((
    "size_threshold", "manual", "owner_rotation", "quarantine_pre_fix",
))


def _normalize_rotation_trigger(value: object) -> str:
    """Coerce + validate a rotation_trigger against the closed enum.

    Truncates to 32 chars then fails OPEN to the common-case
    ``size_threshold`` for any value outside ``_VALID_ROTATION_TRIGGERS``.
    Fail-open (never raises) matches the audit-emit contract — the marker
    must still be written on rotation.
    """
    s = str(value)[:32]
    if s not in _VALID_ROTATION_TRIGGERS:
        return "size_threshold"
    return s


# PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — helper to emit
# chain_reset_marker as line 1 of new (post-rotation) audit-log + write
# rotation manifest. MUST be called UNDER the audit-log FileLock by the
# caller. Per ADR-055-AMEND-2.
def _emit_chain_reset_marker_under_lock(
    log: Path,
    previous_archive_path: str,
    rotation_trigger: str = "size_threshold",
) -> Optional[bytes]:
    """Emit chain_reset_marker as line 1 + write rotation manifest.

    Caller MUST hold the canonical FileLock + the canonical log file
    MUST be empty (just rotated). Returns the marker HMAC bytes on
    success or None on failure (caller breadcrumbs + falls back to
    legacy-mode rotation without marker).

    Side effects under the lock (sidecars-before-marker order per
    Codex R3 P1 fold — partial-failure recoverable):
    1. Read rotated archive's last hmac (best-effort; "" if not found)
    2. Compute marker HMAC at GENESIS_PREV (marker is genesis-anchored)
    3. **Write rotation manifest sidecar FIRST** (fail-closed: return None
       if fails — marker not on disk, next emit uses legacy mode)
    4. **Write audit-log.last-hmac with marker HMAC** (fail-closed: revert
       manifest, return None — both sidecars in pre-marker state)
    5. Write audit-log.chain-length to 1 (non-critical canary; fail-open
       with breadcrumb)
    6. **Append marker line LAST to new audit-log.jsonl** (line 1; if this
       fails, sidecars + manifest already consistent → verifier in
       manifest-required mode tamper-flags the missing line 1 marker,
       which is correct fail-LOUD detection)

    Pre-R3 order was: append-then-sidecars (marker on disk before manifest
    write); a sidecar failure could leave marker on disk + stale sidecars,
    causing the NEXT emit to chain from genesis and produce a broken
    line 2. The sidecars-first ordering eliminates this failure mode.
    """
    from datetime import datetime, timezone
    try:
        # Step 1: read rotated archive's last hmac.
        previous_archive_last_hmac = ""
        try:
            archive_path = Path(previous_archive_path)
            if archive_path.exists() and archive_path.stat().st_size > 0:
                # Read last non-empty line from archive
                with open(archive_path, "rb") as f:
                    f.seek(0, 2)  # seek to end
                    file_size = f.tell()
                    # Read last 4KB (sufficient for one JSONL line)
                    seek_to = max(0, file_size - 4096)
                    f.seek(seek_to)
                    tail = f.read().decode("utf-8", errors="replace")
                    last_line = ""
                    for line in tail.splitlines():
                        line = line.strip()
                        if line:
                            last_line = line
                    if last_line:
                        try:
                            last_entry = json.loads(last_line)
                            if isinstance(last_entry, dict):
                                hmac_val = last_entry.get("hmac")
                                if isinstance(hmac_val, str) and len(hmac_val) == 64:
                                    previous_archive_last_hmac = hmac_val
                        except json.JSONDecodeError:
                            pass
        except (OSError, AttributeError):
            pass

        # Step 2: compute marker HMAC at GENESIS_PREV (genesis-anchored).
        rotated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        marker_event = {
            "action": "chain_reset_marker",
            "previous_archive_path": str(previous_archive_path)[:256],
            "previous_archive_last_hmac": previous_archive_last_hmac[:64],
            "rotation_ts": rotated_at,
            "rotation_trigger": _normalize_rotation_trigger(rotation_trigger),
            "session_id": "",
            "project": "",
            "event_schema": "v2",
            "ts": rotated_at,
            "tokens_in": None,
            "tokens_out": None,
            "tokens_total": None,
        }
        key = _audit_hmac.get_or_create_key()
        marker_sans_hmac = {k: v for k, v in marker_event.items()
                            if k != "hmac" and k != "hmac_error"}
        try:
            marker_digest = _audit_hmac.compute_entry_hmac(
                key, _audit_hmac.GENESIS_PREV, marker_sans_hmac
            )
        except _audit_hmac.AuditProducerPathPollutionError as ppe:
            # PLAN-118 AC-B4 chokepoint 1 + recursion-safety case 3 —
            # detected at the marker chokepoint itself. SKIP the marker
            # emission entirely (the marker would otherwise be signed
            # under the polluted producer's canonicalization, perpetuating
            # the exact bug we're closing). Write ONE bounded breadcrumb
            # line directly to the host's audit-log via the pre-canonical
            # fast-path (stdlib `open(path, 'a')` JSON write — NO
            # _write_event, NO compute_entry_hmac re-entry, NO chain
            # anchoring). The breadcrumb is non-chain-anchored advisory;
            # the chain head is what we're protecting.
            _breadcrumb(
                f"chain_reset_marker SKIPPED (producer path pollution): {ppe}"
            )
            # Parse the exception message to extract closed-enum fields.
            # The exception message format is:
            #   "non_canonical_lib_resolution: reason_code=<rc> "
            #   "path_sha256_prefix=<8hex> "
            #   "expected_canonical_prefix=<8hex>"
            try:
                _msg = str(ppe)
                _rc = "audit_emit_path_pollution"  # safe default
                _psp = "00000000"
                _ecp = "00000000"
                for _tok in _msg.split():
                    if _tok.startswith("reason_code="):
                        _rc_candidate = _tok.split("=", 1)[1]
                        if _rc_candidate in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
                            _rc = _rc_candidate
                    elif _tok.startswith("path_sha256_prefix="):
                        _psp_candidate = _tok.split("=", 1)[1]
                        if len(_psp_candidate) == 8 and all(c in "0123456789abcdef" for c in _psp_candidate):
                            _psp = _psp_candidate
                    elif _tok.startswith("expected_canonical_prefix="):
                        _ecp_candidate = _tok.split("=", 1)[1]
                        if len(_ecp_candidate) == 8 and all(c in "0123456789abcdef" for c in _ecp_candidate):
                            _ecp = _ecp_candidate
                _breadcrumb_event = {
                    "action": "audit_producer_path_pollution_detected",
                    "ts": rotated_at,
                    "session_id": "",
                    "project": "",
                    "event_schema": "v2",
                    "tokens_in": None,
                    "tokens_out": None,
                    "tokens_total": None,
                    "hmac": None,
                    "hmac_error": "producer_path_pollution_detected",
                    "chokepoint": "chain_reset_marker",
                    "reason_code": _rc,
                    "path_sha256_prefix": _psp,
                    "expected_canonical_prefix": _ecp,
                }
                _line = json.dumps(_breadcrumb_event, ensure_ascii=False) + "\n"
                with log.open("a", encoding="utf-8") as _f:
                    _f.write(_line)
                    _f.flush()
            except Exception as _be:  # pragma: no cover
                _breadcrumb(
                    f"chain_reset_marker breadcrumb fast-path write failed: "
                    f"{type(_be).__name__}: {_be}"
                )
            return None
        marker_event["hmac"] = _audit_hmac.hex_digest(marker_digest)

        # PLAN-112-FOLLOWUP-hmac-tamper-fix Codex R3 P1 fold —
        # Sidecars-before-marker ordering: write all 3 sidecars FIRST,
        # then marker line LAST. If sidecar writes fail, marker is NOT
        # on disk yet → next emit handles via legacy chain-from-genesis
        # (recoverable). If sidecar succeeds + marker fails: revert
        # sidecars to pre-marker state (delete manifest + reset chain).
        # This makes partial-failure states recoverable + fail-closed
        # rather than silently mischaining line 2.

        # Step 3 (was 4): write rotation manifest sidecar FIRST
        try:
            _audit_hmac.write_rotation_manifest(
                previous_archive_filename=str(Path(previous_archive_path).name),
                rotated_at=rotated_at,
            )
        except _audit_hmac.AuditHmacError as me:
            _breadcrumb(
                "chain_reset_marker manifest write FAIL-CLOSED: {e}".format(e=me)
            )
            return None  # marker not on disk; next emit uses legacy mode

        # Step 4 (was 5): update last-hmac sidecar with marker's HMAC.
        try:
            _audit_hmac.write_last_hmac(marker_digest)
        except _audit_hmac.AuditHmacError as me:
            # Sidecar update failed; revert manifest write
            try:
                _audit_hmac.delete_rotation_manifest()
            except Exception:
                pass
            _breadcrumb(
                "chain_reset_marker last_hmac write FAIL-CLOSED: {e}".format(e=me)
            )
            return None

        # Step 5 (was 6): update chain-length to 1 (marker is HMAC-bearing).
        try:
            _audit_hmac.write_chain_length(1)
        except _audit_hmac.AuditHmacError as ce:
            # Chain-length is detection-canary; non-critical
            _breadcrumb(
                "chain_reset_marker chain_length write failed (non-blocking): "
                "{e}".format(e=ce)
            )

        # Step 6 (was 3): NOW append marker as line 1 of (current) new log.
        # If this fails, sidecars are already in marker-consistent state
        # but no line on disk — this is also recoverable: next sync emit
        # will see last-hmac=marker_digest and chain from it; the missing
        # marker line means verifier (manifest-mode) will tamper-flag
        # line 1, which is correct: marker IS required if manifest exists.
        line = json.dumps(marker_event, ensure_ascii=False) + "\n"
        try:
            with log.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError):
                    pass
        except OSError as we:
            # Marker line write failed. Sidecars already point at marker
            # HMAC + manifest exists → verifier will tamper-flag the
            # marker-missing state on next verify (correct fail-loud
            # behavior). Caller breadcrumbs.
            _breadcrumb(
                "chain_reset_marker line write FAIL-LOUD: {e}".format(e=we)
            )
            return None

        return marker_digest
    except Exception as e:  # pragma: no cover
        _breadcrumb(
            f"_emit_chain_reset_marker_under_lock failed: "
            f"{type(e).__name__}: {e}"
        )
        return None


def _write_event(event: Dict[str, Any]) -> None:
    """Write a single JSONL event under the shared lock.

    Fail-open: any exception writes a breadcrumb and returns silently.
    F-CHAOS-1 (PLAN-019): when the primary audit dir is unwritable, fall
    back to /tmp/ceo-audit-fallback-<user>.log with once-per-session banner.
    """
    try:
        log = _log_path()

        # Enforce mandatory fields
        if "action" not in event or event["action"] not in _KNOWN_ACTIONS:
            _breadcrumb(f"unknown action: {event.get('action')!r}")
            return

        # Always set event_schema + ts
        event.setdefault("event_schema", EVENT_SCHEMA_V2)
        event.setdefault("ts", _utc_now_iso())

        # Reserve nullable cost fields (AI specialist P5)
        event.setdefault("tokens_in", None)
        event.setdefault("tokens_out", None)
        event.setdefault("tokens_total", None)

        # PLAN-023 Phase B (ADR-055) — HMAC chain fields.
        # Additive; null when chain is disabled or key-read fails.
        event.setdefault("hmac", None)
        event.setdefault("hmac_error", None)

        # PLAN-094 Wave A.3 — spool-writer hot path (ADR-055-AMEND-1).
        # Default path: append to per-PID spool + occasional amortized drain.
        # Falls back to sync canonical write on kill-switch or any spool error.
        if (
            _SPOOL_WRITER_AVAILABLE
            and _spool_writer is not None
            and not _spool_writer.is_sync_mode()
        ):
            try:
                _spool_writer.spool_append(event)
                # PLAN-094-FOLLOWUP Wave A.3-fail-open (option B) — check
                # durability indicator; fall through to sync canonical
                # write if spool path silently swallowed an OSError.
                if _spool_writer.last_append_succeeded():
                    if _spool_writer.should_drain():
                        _spool_writer.drain_now()
                    return  # spool path succeeded
                _breadcrumb(
                    "spool_append silent drop; falling back to sync canonical write"
                )
                # fall through to sync canonical write below
            except Exception as se:  # pragma: no cover
                _breadcrumb(
                    f"spool path fallback to sync: {type(se).__name__}: {se}"
                )
                # fall through to sync canonical write below

        # Phase 1: attempt primary write under lock.
        try:
            log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with FileLock(str(_lock_path()), timeout=2.5):
                # PLAN-045 Wave 2 P0-07/08 rotation wire — invoke the
                # shared rotation primitive BEFORE computing the HMAC.
                # If rotation happens, reset the chain sidecar so the next
                # write re-anchors at genesis in the new (empty) file.
                # Fail-open: any rotation exception is breadcrumbed and
                # the write proceeds against the over-threshold log.
                rotated_to = _rotate_if_needed_safe(log)
                if rotated_to is not None and _HMAC_AVAILABLE:
                    try:
                        _audit_hmac.reset_chain_on_rotation()
                    except Exception as re:  # pragma: no cover
                        _breadcrumb(
                            f"reset_chain_on_rotation failed: "
                            f"{type(re).__name__}: {re}"
                        )
                    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — write
                    # chain_reset_marker as line 1 of new file + rotation
                    # manifest sidecar, per ADR-055-AMEND-2. Fail-open:
                    # if marker emit fails, manifest is NOT written, so
                    # verifier falls back to legacy mode (no marker
                    # enforcement on this rotation event).
                    if not _audit_hmac.is_disabled():
                        try:
                            _emit_chain_reset_marker_under_lock(
                                log=log,
                                previous_archive_path=str(rotated_to),
                                rotation_trigger="size_threshold",
                            )
                        except Exception as me:  # pragma: no cover
                            _breadcrumb(
                                f"chain_reset_marker emit failed (rotation "
                                f"proceeds without marker): "
                                f"{type(me).__name__}: {me}"
                            )

                # PLAN-023 Phase B — compute HMAC INSIDE the lock so the
                # read-modify-write sequence is atomic against concurrent
                # subprocess writes. Chain-fork defect (security review
                # §3b) avoided because prev_hmac read + compute + write +
                # sidecar update all happen under the same FileLock.
                if _HMAC_AVAILABLE and not _audit_hmac.is_disabled():
                    try:
                        key = _audit_hmac.get_or_create_key()
                        prev = _audit_hmac.read_prev_hmac()
                        entry_sans = {k: v for k, v in event.items()
                                      if k != "hmac" and k != "hmac_error"}
                        digest = _audit_hmac.compute_entry_hmac(
                            key, prev, entry_sans
                        )
                        event["hmac"] = _audit_hmac.hex_digest(digest)
                    except _audit_hmac.AuditProducerPathPollutionError as ppe:
                        # PLAN-118 AC-B4 chokepoint 2 — _write_event HMAC
                        # path. Stale `_lib` on sys.path was detected by
                        # audit_hmac._ensure_canonical_lib_modules at
                        # compute_entry_hmac entry. Fail-OPEN at host
                        # hook (line written with hmac=null + closed-enum
                        # hmac_error); fail-CLOSED for the chain (no
                        # signed bytes leak under stale canonicalization).
                        # User session NEVER blocked.
                        event["hmac"] = None
                        event["hmac_error"] = "producer_path_pollution_detected"
                        _breadcrumb(
                            f"hmac_error: producer_path_pollution_detected: {ppe}"
                        )
                    except _audit_hmac.AuditHmacError as he:
                        # Fail-open: record the error kind + proceed
                        # with hmac=null. Operator finds breadcrumbs in
                        # audit-log.errors.
                        event["hmac"] = None
                        event["hmac_error"] = type(he).__name__
                        _breadcrumb(
                            f"hmac_error: {he}"
                        )
                    except Exception as he:  # pragma: no cover
                        event["hmac"] = None
                        event["hmac_error"] = type(he).__name__
                        _breadcrumb(
                            f"hmac_unexpected: {type(he).__name__}: {he}"
                        )

                # Serialize AFTER the hmac field was populated so the
                # on-disk line matches the canonical form used to compute
                # the HMAC. ensure_ascii=False keeps Unicode; the HMAC
                # was computed on the NFC-normalized canonical form so
                # a verifier re-computing from the line gets the same
                # digest (json.loads → canonical_json.encode is lossless).
                line = json.dumps(event, ensure_ascii=False) + "\n"

                with log.open("a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
                try:
                    os.chmod(log, 0o600)
                except OSError:
                    pass

                # Update the last-hmac sidecar under the same lock so
                # the next writer sees the correct prev_hmac. Best-effort
                # (no fsync on sidecar per perf-engineer §10).
                if (
                    _HMAC_AVAILABLE
                    and event.get("hmac")
                    and not _audit_hmac.is_disabled()
                ):
                    try:
                        _audit_hmac.write_last_hmac(
                            _audit_hmac.from_hex(event["hmac"])
                        )
                    except _audit_hmac.AuditHmacError:
                        pass  # next read falls back to genesis

                # PLAN-044 audit-v2 C6-P0-03 fix: wire chain-length canary
                # increment under same FileLock, after the JSON line is
                # already on disk + last_hmac persisted. Detection aid for
                # tail-truncation; gate-on-event["hmac"] keeps counter
                # semantically aligned with verify_chain.verified_count.
                # Fail-open with breadcrumb (canary is detection-aid, not
                # correctness-critical). Ordering invariant: rotation ->
                # hmac compute -> JSON write+fsync -> write_last_hmac ->
                # canary increment. Future refactors must preserve order.
                if (
                    _HMAC_AVAILABLE
                    and event.get("hmac")
                    and not _audit_hmac.is_disabled()
                ):
                    try:
                        n = _audit_hmac.read_chain_length()
                        _audit_hmac.write_chain_length(n + 1)
                    except _audit_hmac.AuditHmacError as ce:
                        _breadcrumb(
                            "chain_length_canary_io_error: "
                            "{cls}: {err}".format(
                                cls=type(ce).__name__, err=ce
                            )
                        )  # fail-open: counter may stay stale; verifier-side re-walk catches drift
            return  # primary write succeeded
        except FileLockTimeout:
            # M9 — previously the entry was DROPPED on lock-timeout
            # (only a breadcrumb), so a contended log silently lost audit
            # events — the opposite of the tamper-evidence contract. Route the
            # event to the /tmp fallback log instead of dropping it. `line` is
            # NOT in scope here (it is built INSIDE the lock body, which never
            # ran because FileLock.__enter__ timed out), so serialize a
            # best-effort fallback line from `event` directly. It carries
            # hmac=null — acceptable: the fallback log is an explicitly
            # degraded, un-chained durability path (see banner), and a
            # null-hmac line in fallback is strictly better than a lost event.
            _breadcrumb(f"lock timeout for action={event.get('action')!r}")
            try:
                _fallback_line = json.dumps(event, ensure_ascii=False) + "\n"
            except Exception:  # pragma: no cover — event unserializable
                _fallback_line = None
            if _fallback_line is not None:
                _emit_fallback_banner_once(
                    log, _fallback_log_path(), "lock timeout"
                )
                _write_fallback(_fallback_line)
            return
        except (OSError, PermissionError) as primary_err:
            # F-CHAOS-1: primary path unwritable → fallback + banner.
            _emit_fallback_banner_once(log, _fallback_log_path(), str(primary_err))
            _write_fallback(line)
            return
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"write_event exception: {type(e).__name__}: {e}")


def _preview(text: Optional[str], max_len: int = 120) -> str:
    """Redact + collapse whitespace + truncate to max_len.

    PLAN-087 Wave C.8: outer whitespace collapse removed. The
    redact_secrets call internally collapses whitespace already
    (see _lib/redact.py); the outer collapse was an O(N) no-op on
    the hot path that doubled the string scan cost for long inputs.
    str() coercion kept for defense-in-depth on Optional callers.
    KERNEL FILE - landed under CEO_KERNEL_OVERRIDE per ADR-116.
    """
    if not text:
        return ""
    redacted = _redact.redact_secrets(str(text))
    if len(redacted) > max_len:
        return redacted[: max_len - 1] + "…"
    return redacted


# -----------------------------------------------------------------------------
# Public emitters
# -----------------------------------------------------------------------------


def emit_debate_event(
    plan_id: str,
    round_num: int,
    phase: str,
    agent: str,
    artifact_path: Optional[str] = None,
    consensus_adjustments_count: Optional[int] = None,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a debate round event.

    Args:
        plan_id: e.g. "PLAN-004"
        round_num: 1–3
        phase: "start" | "agent-done" | "consensus"
        agent: archetype slug (vp-engineering, security-engineer, etc.) or "consensus"
        artifact_path: path to the critique/consensus file
        consensus_adjustments_count: set only on phase="consensus"
    """
    event: Dict[str, Any] = {
        "action": "debate_event",
        "plan_id": plan_id,
        "round": round_num,
        "phase": phase,
        "agent": agent,
        "session_id": session_id,
        "project": project,
    }
    if artifact_path is not None:
        event["artifact_path"] = artifact_path
    if consensus_adjustments_count is not None:
        event["consensus_adjustments_count"] = consensus_adjustments_count
    _write_event(event)


def emit_plan_transition(
    plan_id: str,
    from_status: str,
    to_status: str,
    file_path: str,
    editor_tool: str = "Edit",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a legal plan status transition event.

    Illegal transitions are blocked by check_plan_edit.py and emit a
    veto_triggered event instead.
    """
    event: Dict[str, Any] = {
        "action": "plan_transition",
        "plan_id": plan_id,
        "from_status": from_status,
        "to_status": to_status,
        "editor_tool": editor_tool,
        "file_path": file_path,
        "transition_legal": True,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_veto_triggered(
    hook: str,
    reason_code: str,
    reason_preview: str,
    blocked_tool: str = "",
    strike_count: Optional[int] = None,
    session_id: str = "",
    project: str = "",
    caller: str = "",
) -> None:
    """Emit a veto / block event from any governance hook.

    Args:
        hook: "check_agent_spawn" | "check_plan_edit" | "check_bash_safety"
        reason_code: machine-readable rule identifier (e.g. "missing_skill_content")
        reason_preview: human-readable summary (redacted + truncated)
        blocked_tool: tool call that was blocked
        strike_count: session-scoped count (if tracked)
        caller: identity of the spawning agent or "ceo" (kernel events
            require this for forensic traceability — schema v2.14)
    """
    event: Dict[str, Any] = {
        "action": "veto_triggered",
        "hook": hook,
        "reason_code": reason_code,
        "reason_preview": _preview(reason_preview),
        "blocked_tool": blocked_tool,
        "session_id": session_id,
        "project": project,
    }
    if strike_count is not None:
        event["strike_count"] = strike_count
    if caller:
        event["caller"] = caller
    _write_event(event)


def emit_benchmark_run(
    benchmark_id: str,
    skill: str,
    pass_count: int,
    fail_count: int,
    pass_rate: float,
    median_score: float,
    floor: float,
    cost_usd: float = 0.0,
    duration_s: float = 0.0,
    lessons_written: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a benchmark run completion event.

    Float fields are encoded as integers to satisfy the canonical_json
    no-float invariant on HMAC-covered audit events:

    - ``pass_rate``    → ``pass_rate_bps``    (rate × 1000, 0..1000)
    - ``median_score`` → ``median_score_bps`` (score × 1000, 0..1000)
    - ``floor``        → ``floor_bps``        (rate × 1000, 0..1000)
    - ``cost_usd``     → ``cost_usd_cents``   (USD × 100, ≥0)
    - ``duration_s``   → ``duration_ms``      (seconds × 1000, ≥0)

    Readers must divide by the respective denominator to recover the
    original scale.
    """
    event: Dict[str, Any] = {
        "action": "benchmark_run",
        "benchmark_id": benchmark_id,
        "skill": skill,
        "pass_count": int(pass_count),
        "fail_count": int(fail_count),
        "pass_rate_bps": max(0, min(1000, int(round(float(pass_rate) * 1000)))),
        "median_score_bps": max(0, min(1000, int(round(float(median_score) * 1000)))),
        "floor_bps": max(0, min(1000, int(round(float(floor) * 1000)))),
        "cost_usd_cents": max(0, int(round(float(cost_usd) * 100))),
        "duration_ms": max(0, int(round(float(duration_s) * 1000))),
        "lessons_written": int(lessons_written),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# PLAN-133 C3 — Sec MF-3 field allowlist for eval_task_completed. Closed set;
# anything outside it is dropped by _scrub (see emit_generic dispatch below).
_EVAL_TASK_COMPLETED_ALLOWLIST = frozenset({
    "action", "task_id", "reward_bps", "status", "attempts",
    "flaky", "tokens", "turns", "event_schema", "ts",
})


def emit_eval_task_completed(
    task_id: str,
    reward: float,
    status: str = "",
    attempts: int = 0,
    flaky: bool = False,
    tokens: int = 0,
    turns: int = 0,
) -> None:
    """Emit one real-task reward-benchmark result (PLAN-133 C3).

    NO-VALUE-ECHO contract: the only free-text inputs are ``task_id`` (a stable
    task slug from .claude/eval/tasks/, NOT user/model content) and ``status``
    (coerced to the closed trial-status enum). No rejected env value, egress
    destination, retry_delay, or model output is ever carried. ``reward`` is
    encoded as basis-points (``reward_bps`` 0..1000) to satisfy the canonical_json
    no-float invariant; ``flaky`` is encoded as 0/1.
    """
    status_norm = status if status in ("pass", "partial", "fail") else "other"
    event: Dict[str, Any] = {
        "action": "eval_task_completed",
        "task_id": str(task_id)[:64],
        "reward_bps": max(0, min(1000, int(round(float(reward) * 1000)))),
        "status": status_norm,
        "attempts": max(0, int(attempts)),
        "flaky": 1 if flaky else 0,
        "tokens": max(0, int(tokens)),
        "turns": max(0, int(turns)),
    }
    _write_event(event)


def emit_injection_flag(
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    triggered_by_tool: str = "",
    snippet_preview: str = "",
    truncated: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a prompt-injection flag event (v2.1, ADR-011).

    Always advisory: this event records observation, never enforces a
    block. The PreToolUse hook `check_read_injection.py` calls this
    after running scan_text on a Read result; the audit-query.py
    `vetoes` and `metrics` sub-commands surface aggregated counts.

    Args:
        source: file path / "<stdin>" / tool input identifier
        family_counts: per-family hit counts (e.g. {"direct_override": 2})
        match_count: total matches across families
        bytes_scanned: bytes the scanner inspected (bounded at 1 MiB)
        triggered_by_tool: e.g. "Read", "Bash"
        snippet_preview: redacted snippet of the highest-confidence hit
        truncated: True if input exceeded scanner cap
    """
    event: Dict[str, Any] = {
        "action": "injection_flag",
        "source": source,
        "family_counts": dict(family_counts),
        "match_count": int(match_count),
        "bytes_scanned": int(bytes_scanned),
        "truncated": bool(truncated),
        "triggered_by_tool": triggered_by_tool,
        "snippet_preview": _preview(snippet_preview, max_len=200),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_write(
    lesson_id: str,
    archetype: str,
    scope_tags: List[str],
    trigger: str,
    source_event_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson-write event (Reflexion corpus growth).

    Args:
        lesson_id: stable identifier (e.g. hash or ULID)
        archetype: owning archetype slug
        scope_tags: scope tag list (subset of skill scope_tags)
        trigger: "benchmark_fail" | "debate_adjustment" | "manual"
        source_event_id: correlation to the originating event (desc_hash or artifact_path)
    """
    event: Dict[str, Any] = {
        "action": "lesson_write",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "scope_tags": list(scope_tags),
        "trigger": trigger,
        "source_event_id": source_event_id,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate(
    claim_count: int,
    pass_count: int,
    fail_count: int,
    verifier_kind_counts: Dict[str, int],
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
    raw_claim_count: Optional[int] = None,
    truncated: bool = False,
) -> None:
    """Emit a confidence_gate event (Sprint 8 Phase 2, ADR-018).

    Advisory-only in Sprint 8: collects FPR baseline for Sprint 9 enforcement
    decision. Reserved fields set from day 1 (debate consensus C4).

    Sprint 9 (PLAN-009 A12) adds ``raw_claim_count`` + ``truncated`` for
    ``CEO_CONFIDENCE_MAX_CLAIMS`` cap reporting. When the input produced
    more CLAIM tokens than the cap, ``claim_count`` is the post-cap value,
    ``raw_claim_count`` is the pre-cap count, and ``truncated=True``.

    Args:
        claim_count: verified CLAIM tokens (post code-block exemption + cap)
        pass_count: claims that verified
        fail_count: claims that failed to verify
        verifier_kind_counts: dict of claim kind -> count (all kinds seen)
        agent_name: name of the agent whose output was scanned (optional)
        source: "stdin" | "<file path>" | "<spawn-ref>"
        raw_claim_count: pre-cap CLAIM token count; defaults to claim_count
            when the caller did not surface a cap
        truncated: True when raw_claim_count > claim_count
    """
    if raw_claim_count is None:
        raw_claim_count = int(claim_count)
    event: Dict[str, Any] = {
        "action": "confidence_gate",
        "claim_count": int(claim_count),
        "raw_claim_count": int(raw_claim_count),
        "truncated": bool(truncated),
        "pass_count": int(pass_count),
        "fail_count": int(fail_count),
        "verifier_kind_counts": dict(verifier_kind_counts),
        "agent_name": agent_name,
        "source": source,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_read(
    lesson_ids: List[str],
    archetype: str,
    keywords: List[str],
    k: int,
    consumer: str = "architect",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_read event (Sprint 8 Phase 3).

    Logged when `lessons.get_top_k()` is invoked to inject top-K lessons
    into a spawn prompt. Enables Sprint 9 outcome-tracking integration
    (correlating which injected lessons correlated with benchmark hits).

    Args:
        lesson_ids: list of lesson IDs that were read (length <= k)
        archetype: archetype that the lessons were queried for
        keywords: keywords used for ranking
        k: requested top-K count
        consumer: "architect" | "spawn" | "cli"
    """
    event: Dict[str, Any] = {
        "action": "lesson_read",
        "lesson_ids": list(lesson_ids),
        "lesson_count": len(lesson_ids),
        "archetype": archetype,
        "keywords": list(keywords),
        "k": int(k),
        "consumer": consumer,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_archived(
    lesson_id: str,
    archetype: str,
    hit_count: int,
    miss_count: int,
    hit_rate: float,
    archive_path: str,
    reason: str = "low_hit_rate",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_archived event (Sprint 8 Phase 4).

    Logged by `prune-lessons.py --execute` when a lesson meets prune
    criteria (ADR-017, amended Sprint 8) and is moved to archive.
    Archive is reversible via `lesson-restore.py`.

    ``hit_rate_bps`` is integer basis-points (hit_rate × 1000, clamped
    0..1000). canonical_json forbids floats in HMAC-covered fields; the
    old ``hit_rate`` float caused CanonicalJsonError + dropped events.
    Caller passes the raw 0..1 float; we convert here.
    """
    bps = max(0, min(1000, int(round(hit_rate * 1000))))
    event: Dict[str, Any] = {
        "action": "lesson_archived",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "hit_rate_bps": bps,
        "archive_path": archive_path,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_restored(
    lesson_id: str,
    archetype: str,
    restored_from: str,
    restored_to: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_restored event (Sprint 8 Phase 4b).

    Logged by `lesson-restore.py` when a previously archived lesson is
    moved back to the active lessons directory.
    """
    event: Dict[str, Any] = {
        "action": "lesson_restored",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "restored_from": restored_from,
        "restored_to": restored_to,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_outcome(
    lesson_id: str,
    archetype: str,
    hit: bool,
    hit_count: int = 0,
    miss_count: int = 0,
    session_id: str = "",
    project: str = "",
    consumer: str = "benchmark",
    inference_mode: str = "",
    window_duration_seconds: int = 0,
    session_end_reason: str = "",
) -> None:
    """Emit a lesson_outcome event (Reflexion v2 / ADR-015).

    Logged when a consumer (benchmark or architect) applies a lesson and
    the outcome is classified as hit / miss.

    PLAN-009 P3.2/P3.5 (ADR-015 amendment) adds:

    - ``consumer`` — closed enum {"benchmark", "architect"}. Back-compat:
      pre-Sprint-9 events missing this field are parsed as "benchmark"
      (single-consumer era default). SPEC/v1/audit-log.schema.md v2.2.2.
    - ``inference_mode`` — "window-only" | "session-correlated" |
      "" (legacy). Architect paths use "session-correlated"; older
      benchmarks retain "window-only" retroactively.
    - ``window_duration_seconds`` — how wide a window the outcome was
      attributed across (0 = not-applicable / benchmark).
    - ``session_end_reason`` — "timeout" | "explicit" | "unknown" | "".

    `event_schema` stays "v2" — additive per ADR-011 pattern.
    """
    event: Dict[str, Any] = {
        "action": "lesson_outcome",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "hit": bool(hit),
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "session_id": session_id,
        "project": project,
        "consumer": consumer,
        "inference_mode": inference_mode,
        "window_duration_seconds": int(window_duration_seconds),
        "session_end_reason": session_end_reason,
    }
    _write_event(event)


def emit_state_store_write(
    store_name: str,
    plan_id_hash: str,
    key_hash: str,
    value_bytes: int,
    ttl_seconds: Optional[int] = None,
    redaction_applied: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store write event (Sprint 11 Phase 0, ADR-027).

    ``plan_id_hash`` and ``key_hash`` are SHA-256 prefixes (16 chars) —
    plaintext plan_id/key is never audited. ``redaction_applied`` is True
    if ``redact_secrets`` mutated the original string value.

    Args:
        store_name: short store slug (e.g. "scratchpad").
        plan_id_hash: 16-char SHA-256 prefix of PLAN-NNN string.
        key_hash: 16-char SHA-256 prefix of the key.
        value_bytes: size of the stored value (post-redaction) in bytes.
        ttl_seconds: None if no TTL; int seconds-from-now otherwise.
        redaction_applied: True if ``redact_secrets`` changed the value.
    """
    event: Dict[str, Any] = {
        "action": "state_store_write",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "key_hash": key_hash,
        "value_bytes": int(value_bytes),
        "ttl_seconds": int(ttl_seconds) if ttl_seconds is not None else None,
        "redaction_applied": bool(redaction_applied),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_state_store_read(
    store_name: str,
    plan_id_hash: str,
    key_hash: str,
    found: bool,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store read event (Sprint 11 Phase 0, ADR-027).

    ``found=False`` covers both missing-key and expired-TTL — the
    consumer can correlate with subsequent prune events to tell them
    apart if needed.
    """
    event: Dict[str, Any] = {
        "action": "state_store_read",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "key_hash": key_hash,
        "found": bool(found),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_budget_exceeded(
    plan_id: str,
    spawn_id: str,
    tokens_used: int,
    cap: int,
    scope: str = "spawn",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a budget_exceeded event (Sprint 11 Phase 6, ADR-033).

    Fired by ``check_budget.py`` when a spawn or plan rollup exceeds the
    configured cap. Advisory in Sprint 11 (enforcing Sprint 12 IFF FPR
    data supports it per H16).

    Args:
        plan_id: PLAN-NNN string (unhashed; plan-level budgets are
            Owner-visible).
        spawn_id: session-local spawn identifier or ``""`` for plan-scope.
        tokens_used: post-spawn running total.
        cap: configured cap (e.g. CEO_MAX_SPAWN_TOKENS).
        scope: ``"spawn"`` | ``"plan"``.
    """
    event: Dict[str, Any] = {
        "action": "budget_exceeded",
        "plan_id": plan_id,
        "spawn_id": spawn_id,
        "tokens_used": int(tokens_used),
        "cap": int(cap),
        "scope": scope,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_budget_bypass_used(
    plan_id: str,
    caller_pid: int,
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a budget_bypass_used event (Sprint 11 Phase 6, H13).

    Fired when ``CEO_BUDGET_BYPASS=1`` is honored on a blocked spawn.
    Owner-only scope (H13 mirrors ADR-019 C6/A8). Rate-limited to N
    bypasses / 24h — caller enforces the counter; this emitter just
    records the event. ``reason`` is a short free-text preview (e.g.
    ``"emergency: prod down"``).
    """
    event: Dict[str, Any] = {
        "action": "budget_bypass_used",
        "plan_id": plan_id,
        "caller_pid": int(caller_pid),
        "reason_preview": _preview(reason, max_len=120),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_otel_export_dropped(
    fields_dropped_count: int,
    endpoint_host: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit an otel_export_dropped event (Sprint 11 Phase 8, CR3).

    Fired by ``otel-export.py`` when ``redact_secrets`` removes a field
    from a span attribute OR when host allowlist rejects a target. The
    endpoint is recorded as host-only (no URL path, no query). Full
    endpoint URL is NEVER audited (defense-in-depth).
    """
    event: Dict[str, Any] = {
        "action": "otel_export_dropped",
        "fields_dropped_count": int(fields_dropped_count),
        "endpoint_host": endpoint_host,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_output_safety_flag(
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    redaction_applied: bool = False,
    triggered_by_tool: str = "",
    snippet_preview: str = "",
    truncated: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit an output_safety_flag event (Sprint 11 Phase 9, ADR-036).

    Shape mirrors ``injection_flag`` (ADR-011) but scans agent outputs
    instead of inputs (PostToolUse Agent). Advisory Sprint 11. See
    consensus H14 for scanner pipeline order.
    """
    event: Dict[str, Any] = {
        "action": "output_safety_flag",
        "source": source,
        "family_counts": dict(family_counts),
        "match_count": int(match_count),
        "bytes_scanned": int(bytes_scanned),
        "redaction_applied": bool(redaction_applied),
        "truncated": bool(truncated),
        "triggered_by_tool": triggered_by_tool,
        "snippet_preview": _preview(snippet_preview, max_len=200),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_skill_patch_applied(
    proposal_id: str,
    skill_slug: str,
    commit_sha: str,
    signer_fingerprint: str = "",
    shadow_mode: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a skill_patch_applied event (Sprint 11 Phase 4, ADR-031).

    Fired by ``skill-patch-apply.py`` when a proposal is merged via
    signed Owner approval. ``shadow_mode=True`` during the 7-day shadow
    period per CR1; ``False`` after promotion to real SKILL.md.
    """
    event: Dict[str, Any] = {
        "action": "skill_patch_applied",
        "proposal_id": proposal_id,
        "skill_slug": skill_slug,
        "commit_sha": commit_sha,
        "signer_fingerprint": signer_fingerprint,
        "shadow_mode": bool(shadow_mode),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_squad_imported(
    squad_name: str,
    manifest_sha256: str,
    signer_fingerprint: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a squad_imported event (Sprint 11 Phase 12, CR2).

    Fired by ``squad-import.py`` after signature verification passes.
    ``source`` is the pin-allowlist entry (e.g.
    ``"github.com/acme/squad-edtech@v1"``).
    """
    event: Dict[str, Any] = {
        "action": "squad_imported",
        "squad_name": squad_name,
        "manifest_sha256": manifest_sha256,
        "signer_fingerprint": signer_fingerprint,
        "source": source,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_state_store_pruned(
    store_name: str,
    plan_id_hash: str,
    keys_pruned_count: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store prune event (Sprint 11 Phase 0, ADR-027).

    Emitted by ``SqliteStateStore.prune_expired()`` (TTL sweep) and
    ``clear_plan()`` (plan rollback). A single event covers a batch.
    """
    event: Dict[str, Any] = {
        "action": "state_store_pruned",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "keys_pruned_count": int(keys_pruned_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_outcome_undone(
    lesson_id: str,
    archetype: str,
    consumer: str,
    undone_kind: str,
    hit_count: int = 0,
    miss_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_outcome_undone event (PLAN-009 P3.3, schema v2.3).

    Admin-facing escape hatch for reversing a bad attribution. Emitted
    by `lessons.undo_outcome()` after the decrement is persisted.

    ``undone_kind`` is "hit" or "miss" — which counter was decremented.
    """
    event: Dict[str, Any] = {
        "action": "lesson_outcome_undone",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "consumer": consumer,
        "undone_kind": undone_kind,
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# Sprint 13 Phase A.0 (PLAN-013 Gap #3) — Live adapter / breaker / credential
# -----------------------------------------------------------------------------


def emit_live_adapter_call_started(
    provider: str,
    url: str,
    attempt: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_started event (ADR-040 §7).

    Fired by ``_lib/adapters/live/_transport.py::post_json`` on every
    attempt (initial + retries). ``url`` MUST be query-scrubbed by
    the caller (_scrub_url_query). Credential values never appear.
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_started",
        "provider": provider,
        "url": url,
        "attempt": int(attempt),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_live_adapter_call_succeeded(
    provider: str,
    url: str,
    status: int,
    duration_ms: int,
    retried: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_succeeded event (ADR-040 §7).

    Fired on any 2xx response. ``duration_ms`` is wall-clock including
    retry backoff. ``retried=True`` if this response came after at least
    one earlier attempt failed transiently.
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_succeeded",
        "provider": provider,
        "url": url,
        "status": int(status),
        "duration_ms": int(duration_ms),
        "retried": bool(retried),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_live_adapter_call_failed(
    provider: str,
    failure_mode: str,
    http_status: Optional[int] = None,
    duration_ms: int = 0,
    retry_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a live_adapter_call_failed event (ADR-040 §7).

    ``failure_mode`` is the closed enum from SPEC/v1/live-adapters-policy
    §3 (auth_permanent, rate_limit, server_error, connect_timeout,
    read_timeout, connection_refused, parse_error, breaker_open,
    budget_hard_stop, scope_misconfigured).
    """
    event: Dict[str, Any] = {
        "action": "live_adapter_call_failed",
        "provider": provider,
        "failure_mode": failure_mode,
        "http_status": int(http_status) if http_status is not None else None,
        "duration_ms": int(duration_ms),
        "retry_count": int(retry_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_breaker_opened(
    provider: str,
    failures_in_window: int,
    threshold: int,
    reason: str = "server_error",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a breaker_opened event (ADR-040 §2).

    Fired when :class:`_lib.adapters.live._breaker.CircuitBreaker`
    transitions CLOSED → OPEN (threshold crossed) or HALF_OPEN → OPEN
    (probe failed). ``reason`` is the failure classification that
    triggered the transition.
    """
    event: Dict[str, Any] = {
        "action": "breaker_opened",
        "provider": provider,
        "failures_in_window": int(failures_in_window),
        "threshold": int(threshold),
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_breaker_closed(
    provider: str,
    from_state: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a breaker_closed event (ADR-040 §2).

    Fired when :class:`_lib.adapters.live._breaker.CircuitBreaker`
    transitions back to CLOSED (from HALF_OPEN after successful probe,
    or explicit reset). ``from_state`` ∈ {"open", "half_open", "reset"}.
    """
    event: Dict[str, Any] = {
        "action": "breaker_closed",
        "provider": provider,
        "from_state": from_state,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_credential_rotation_due(
    provider: str,
    age_days: int,
    warn_threshold_days: int = 75,
    max_threshold_days: int = 90,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a credential_rotation_due event (ADR-040 §4).

    Fired on every live call once the active API key is older than
    ``warn_threshold_days`` (default 75). The event does not block the
    call — it surfaces in the dashboard so the operator rotates before
    the 90-day hard cap. Credential value is NEVER in any field.
    """
    event: Dict[str, Any] = {
        "action": "credential_rotation_due",
        "provider": provider,
        "age_days": int(age_days),
        "warn_threshold_days": int(warn_threshold_days),
        "max_threshold_days": int(max_threshold_days),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# Sprint 13 Phase A (PLAN-013) — MCP server events (ADR-042)
# -----------------------------------------------------------------------------


# ---------------------------------------------------------------------
# PLAN-085 Wave C.1 — live_adapter_blocked
# ---------------------------------------------------------------------


def emit_live_adapter_blocked(
    provider: str,
    reason: str,
    session_id: str = "",
    project: str = "",
    *,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit a live_adapter_blocked event (PLAN-085 C.1 / ADR-040 §6.3).

    PLAN-085 Wave G.1b — extended with optional ``atlas_technique``
    parameter. Defaults to AML.T0049 (Exploit Public-Facing
    Application) from the immutable registry.
    """
    emit_generic(
        "live_adapter_blocked",
        provider=provider,
        reason=reason,
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["live_adapter_blocked"],
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave C.2 — credential lifecycle blocking + override
# ---------------------------------------------------------------------


def emit_credential_blocked_due_to_age(
    provider: str,
    age_days: int,
    max_age_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_blocked_due_to_age (ADR-040 §4 + ADR-040-AMEND-2)."""
    emit_generic(
        "credential_blocked_due_to_age",
        provider=provider,
        age_days=int(age_days),
        max_age_days=int(max_age_days),
        session_id=session_id,
        project=project,
    )


def emit_credential_emergency_override_used(
    provider: str,
    ticket_id: str,
    age_days: int,
    max_age_days: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_emergency_override_used (ADR-040-AMEND-2)."""
    emit_generic(
        "credential_emergency_override_used",
        provider=provider,
        ticket_id=ticket_id,
        age_days=int(age_days),
        max_age_days=int(max_age_days),
        session_id=session_id,
        project=project,
    )


# PLAN-117 WS-A — closed-enum + constant for the late-set forensic emit. The
# rejected override VALUE must NEVER reach the payload, so the dispatch gate
# (below) forces the var name to this constant and coerces an out-of-enum
# provenance hint to "unspecified" — the no-value-echo invariant is enforced at
# the chokepoint, independent of the caller (defense-in-depth, mirrors the
# closed-enum reason_code precedent in tier_policy_loader_fallback_observed).
_CREDENTIAL_OVERRIDE_VAR_NAME = "CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE"
_CREDENTIAL_OVERRIDE_PROVENANCE_HINTS = frozenset({
    "late_os_environ_set", "spawn_payload_env", "subprocess_inherited",
})


def emit_credential_override_late_set_ignored(
    provider: str,
    provenance_hint: str = "late_os_environ_set",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit credential_override_late_set_ignored (ADR-040-AMEND-2 §Layer-1).

    Forensic trace for an emergency-override value that was present in the
    LIVE environment but ABSENT from the import-time trust-root snapshot
    (set post-anchor) and therefore IGNORED — never honored. The rejected
    VALUE is never persisted: the emit_generic dispatch gate FORCES
    ``attempted_var_name`` to the constant variable name and COERCES an
    out-of-enum ``provenance_hint`` — so the no-value-echo invariant does not
    depend on the caller (closed-enum-breadcrumb-must-not-echo-rejected-value).
    There is intentionally no ``attempted_var_name`` parameter: a caller cannot
    inject it.
    """
    emit_generic(
        "credential_override_late_set_ignored",
        provider=provider,
        provenance_hint=provenance_hint,
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave C.3 — MCP bearer-token replay defense (loopback-only)
# ---------------------------------------------------------------------


def emit_mcp_bearer_replay_rejected(
    reason: str,
    nonce_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_bearer_replay_rejected (PLAN-085 C.3 / IDA-P0-03)."""
    emit_generic(
        "mcp_bearer_replay_rejected",
        reason=reason,
        nonce_prefix=nonce_prefix[:8] if nonce_prefix else "",
        session_id=session_id,
        project=project,
    )


def emit_mcp_non_loopback_rejected(
    remote_addr_family: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_non_loopback_rejected (PLAN-085 C.3 / ADR-040-MCP-Auth)."""
    emit_generic(
        "mcp_non_loopback_rejected",
        remote_addr_family=remote_addr_family,
        session_id=session_id,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-085 Wave G.1b — ATLAS technique-ID schema (5 mappings).
# Immutable v1.19.0 registry; G.1a authored docs + fixtures + test
# infrastructure; G.1b lands the production audit_emit wiring.
# Source of truth: docs/EXT-011-mitre-atlas.md §2 SHIPPED table.
#
# PLAN-095 Wave A (S128) — registry expanded to 19 entries / 11 unique
# technique IDs by PLAN-088/089/090 across multiple plan ships. PLAN-095
# Wave B ships OWASP LLM03:2025 Supply Chain detection in
# `_lib/output_scan.py::_LLM_PATTERN_GROUPS` (family LLM03_2025_supply_chain).
# That detection family is NOT bound to a row in this registry because
# supply-chain is a family-level concern over output payloads, not a
# single technique-ID bound to a single audit-action. Cross-reference
# only; see `.claude/plans/PLAN-095/honest-scope-correction.md` §A.2.
# ---------------------------------------------------------------------

_ATLAS_REGISTRY = {
    "prompt_injection_detected": "AML.T0051",
    # PLAN-095 Wave A LLM02:2025 retag — AML.T0024.001 (ATLAS Infer
    # Training Data Membership) maps to OWASP 2024 LLM06 Sensitive
    # Information Disclosure AND OWASP 2025 LLM02 Sensitive Information
    # Disclosure (renumbering only; semantic preserved across both).
    "secret_leak_detected": "AML.T0024.001",
    "pii_redacted_outgoing": "AML.T0048.004",
    "live_adapter_blocked": "AML.T0049",
    "codex_egress_redacted": "AML.T0054",
    # PLAN-088 canonical-13 ATLAS bindings (S114) — 6 actions with non-null
    # technique-IDs per W0 ATLAS-binding table. Remaining 7 canonical-13
    # actions have atlas_technique=null + atlas_rationale per PLAN-088 §1.5
    # (telemetry-only / UX-trigger / infra-error / cost-optimization).
    "subagent_findings_partial_drop": "AML.T0048",   # W1.4 SEMI-13 — Governance bypass observation
    "anthropic_429_observed":         "AML.T0029",   # W1.4 SEMI-13 — Denial of ML Service signal
    "codex_invoke_dispatched":        "AML.T0050",   # W1.4 SEMI-13 — LLM Plugin Compromise dual-rail
    "tier_policy_misrouting_advised": "AML.T0048",   # W2.1 AUTO-04 — Governance bypass
    "mcp_route_advised":              "AML.T0050",   # W3.1 AUTO-06 — LLM Plugin / supply-chain signal
    "pair_rail_phase_advanced":       "AML.T0050",   # W4.1 AUTO-07 — LLM Plugin Compromise dual-rail check
    # PLAN-089 Wave C.5 — ATT&CK Enterprise bindings (R1 TDE P0 fold +
    # R2 Codex iter-1 P1 taxonomy correction). T1556/T1565.001 are
    # ATT&CK Enterprise (not ATLAS); registry name is generic for
    # technique-ID storage despite historic ATLAS-only origin.
    "kernel_extension_landed":            "T1565.001",  # Stored Data Manipulation — canonical kernel surface
    "bash_canonical_bypass_invoked":      "T1565.001",  # Stored Data Manipulation — same surface, kill-switch path
    "sentinel_signer_rotated":            "T1556",      # Modify Authentication Process
    "sentinel_signer_expiry_warned":      "T1556",      # Modify Authentication Process (forward signal)
    "sentinel_signer_revoked":            "T1556",      # Modify Authentication Process
    "sentinel_signer_quorum_failed":      "T1556",      # Modify Authentication Process (negative path canary)
    "sentinel_signer_quorum_attempted":   "T1556",      # Modify Authentication Process (forensic completeness)
    # PLAN-090 Wave B.5 — streaming side-channel monitoring.
    "streaming_token_yielded":            "T1071",
    # Note: T1584 (Compromise Infrastructure) applies to cold-key
    # compromise SCENARIOS — captured at IR investigation time, not at
    # any single audit-event level. See ADR-121 §7.
}


# PLAN-095 Wave A.8 (S128) — explicit namespace metadata per unique
# technique-ID for `verify-atlas-binding.py --strict-namespace` gate.
# Maps each of the 11 unique technique IDs in `_ATLAS_REGISTRY` to its
# source namespace: `atlas` (MITRE ATLAS LLM-system surface) or
# `attack-enterprise` (MITRE ATT&CK Enterprise OS-level surface).
# Registry intentionally carries the namespace mix per ADR-049
# detection-as-code corpus expansion; strict-namespace gate makes the
# mix EXPLICIT rather than implicit.
_ATLAS_NAMESPACE_REGISTRY: Dict[str, str] = {
    "AML.T0024.001": "atlas",
    "AML.T0029":     "atlas",
    "AML.T0048":     "atlas",
    "AML.T0048.004": "atlas",
    "AML.T0049":     "atlas",
    "AML.T0050":     "atlas",
    "AML.T0051":     "atlas",
    "AML.T0054":     "atlas",
    "T1071":         "attack-enterprise",
    "T1556":         "attack-enterprise",
    "T1565.001":     "attack-enterprise",
}


def emit_prompt_injection_detected(
    *,
    signal: str = "",
    family: str = "",
    snippet_preview: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    triggered_by_tool: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit prompt_injection_detected event (PLAN-085 G.1b / AML.T0051).

    Detection of LLM prompt-injection patterns at hook/scanner layer.
    ``atlas_technique`` defaults to the immutable registry value;
    callers may override for sub-technique disambiguation.
    """
    emit_generic(
        "prompt_injection_detected",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["prompt_injection_detected"],
        signal=signal,
        family=family,
        snippet_preview=snippet_preview[:200],
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        triggered_by_tool=triggered_by_tool,
        session_id=session_id,
        project=project,
    )


def emit_secret_leak_detected(
    *,
    signal: str = "",
    family: str = "",
    snippet_preview: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    triggered_by_tool: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit secret_leak_detected event (PLAN-085 G.1b / AML.T0024.001).

    Detection of credential/secret patterns in payloads or egress.
    """
    emit_generic(
        "secret_leak_detected",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["secret_leak_detected"],
        signal=signal,
        family=family,
        snippet_preview=snippet_preview[:200],
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        triggered_by_tool=triggered_by_tool,
        session_id=session_id,
        project=project,
    )


def emit_pii_redacted_outgoing(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit pii_redacted_outgoing event (PLAN-085 G.1b / AML.T0048.004).

    PII categories detected + scrubbed in outgoing payload (egress
    redaction success). Audit forensic trail.
    """
    emit_generic(
        "pii_redacted_outgoing",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["pii_redacted_outgoing"],
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        session_id=session_id,
        project=project,
    )


def emit_codex_egress_redacted(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    callsite: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit codex_egress_redacted event (PLAN-085 G.1b / AML.T0054).

    Codex MCP egress redactor scrubbed canonical jailbreak/injection
    patterns from outgoing prompt. Composition with Wave B.4 fail-CLOSED
    inversion (RedactorImportFailed surfaces on import failure).
    """
    emit_generic(
        "codex_egress_redacted",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY["codex_egress_redacted"],
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        callsite=callsite,
        session_id=session_id,
        project=project,
    )


def emit_pair_rail_outgoing_redaction_applied(
    *,
    signal: str = "",
    family: str = "",
    match_count: int = 0,
    bytes_scanned: int = 0,
    callsite: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit pair_rail_outgoing_redaction_applied (ADR-114; F-7.9 positive proof).

    The OUTBOUND pair-rail egress redactor (framework → Codex/external LLM)
    scrubbed the outgoing prompt. Emitted on EVERY redaction call, INCLUDING
    when the findings list is empty (``match_count=0`` is positive proof the
    redaction path was exercised). Content-field-free per Sec MF-3 — the
    dispatch gate routes through _PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
    which excludes ``text``/``prompt``/``match_value``. Mirrors
    ``emit_codex_egress_redacted``'s signature.
    """
    emit_generic(
        "pair_rail_outgoing_redaction_applied",
        atlas_technique=atlas_technique or "AML.T0054",
        signal=signal,
        family=family,
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        callsite=callsite,
        session_id=session_id,
        project=project,
    )


def emit_mcp_handler_invoked(
    handler: str,
    client_id: str,
    transport: str,
    duration_ms: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_handler_invoked event (ADR-042 §Auth).

    Fired on every successful handler entry AFTER auth + ACL + rate-limit
    pass. ``client_id`` is the 16-hex opaque identifier (never the token
    itself). ``transport`` ∈ {"http", "stdio"}. ``handler`` ∈ the 7 handler
    names registered in ADR-042 §Auth.2 ACL.
    """
    event: Dict[str, Any] = {
        "action": "mcp_handler_invoked",
        "handler": handler,
        "client_id": client_id,
        "transport": transport,
        "duration_ms": int(duration_ms),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_handler_denied(
    handler: str,
    client_id: str,
    transport: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_handler_denied event (ADR-042 §Auth.5).

    ``reason`` is the closed enum: acl_missing_handler | rate_limit |
    timestamp_skew | cors_default_deny | auth_hmac_invalid |
    auth_token_malformed | budget_hard_stop_per_spawn |
    budget_hard_stop_per_plan_5min | debate_max_rounds | breaker_open |
    plan_id_unknown. Token value MUST NOT appear anywhere (ADR-042
    §Auth.6 hygiene).
    """
    event: Dict[str, Any] = {
        "action": "mcp_handler_denied",
        "handler": handler,
        "client_id": client_id,
        "transport": transport,
        "reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_cross_tenant_denied(
    handler: str,
    caller_client_id_hash: str,
    target_client_id_hash: str,
    transport: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_cross_tenant_denied event (ADR-042-AMEND-1 §6.2).

    Fires when a get_cost_budget call with scope=caller attempts to
    read a target_client_id different from the caller's own. The
    caller/target identifiers are HASHED via auth.hash_client_id
    before serialization (Sec MF-3 hygiene).
    """
    event: Dict[str, Any] = {
        "action": "mcp_cross_tenant_denied",
        "handler": handler,
        "caller_client_id_hash": caller_client_id_hash,
        "target_client_id_hash": target_client_id_hash,
        "transport": transport,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_mcp_soak_fpr_breach(
    window_days: int,
    fpr_observed: float,
    threshold: float,
    top_deny_reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a mcp_soak_fpr_breach event (ADR-042-AMEND-1 §6.2 / AC-F-4).

    Fires when 7-day rolling FPR > threshold (default 0.01 = 1%).
    Fires AT MOST once per breach day; the soak monitor enforces
    dedup against the most recent emit.

    Float fields are encoded as integers to satisfy the canonical_json
    no-float invariant on HMAC-covered audit events:

    - ``fpr_observed``  → ``fpr_observed_bps``  (rate × 10000, 0..10000+)
    - ``threshold``     → ``threshold_bps``     (rate × 10000, 0..10000+)

    Example: FPR 0.01 (1%) → 100 bps; threshold 0.01 → 100 bps.
    Readers must divide by 10000 to recover the original rate.
    """
    event: Dict[str, Any] = {
        "action": "mcp_soak_fpr_breach",
        "window_days": int(window_days),
        "fpr_observed_bps": max(0, int(round(float(fpr_observed) * 10000))),
        "threshold_bps": max(0, int(round(float(threshold) * 10000))),
        "top_deny_reason": str(top_deny_reason),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


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


# ---------------------------------------------------------------------
# PLAN-028 + PLAN-029 Wave A — lifecycle + output-scan emit helpers
# (kernel-apply closeout 2026-04-19, ADR-056 + ADR-057)
# ---------------------------------------------------------------------


def emit_generic(action: str, **kwargs: Any) -> None:
    """Generic event dispatcher for Wave A lifecycle + output-scan hooks.

    Validates ``action`` against _KNOWN_ACTIONS and writes the event
    via _write_event (same filelock + HMAC chain as named emitters).
    Caller provides arbitrary keyword arguments which become event
    fields. No redaction applied by this entry point — callers must
    pre-redact any free-text fields before passing.

    Never raises. Unknown action → breadcrumb + silent return.

    Added via kernel-apply batch for PLAN-027 Wave A exhaustive
    closeout (session 35 post-ship). See ADR-056 §Implementation +
    ADR-057 §Audit event registration.

    PLAN-065 Phase 2 / ADR-098 — Sec MF-3 enforcement defense-in-depth.
    The typed wrappers `emit_ceo_boot_emitted` / `emit_ceo_boot_check_skipped`
    are the canonical entrypoints with field allowlist scrubbing. If a
    future caller invokes `emit_generic("ceo_boot_emitted", prompt=...)`
    directly, route through the same scrub so the field allowlist
    boundary cannot be bypassed (Codex S82 P1 #1 closure).
    """
    if action not in _KNOWN_ACTIONS:
        _breadcrumb(f"emit_generic: unknown action {action!r}")
        return
    event: Dict[str, Any] = {"action": action}
    event.update(kwargs)
    # PLAN-065 Phase 2 / ADR-098 — Sec MF-3 boundary enforcement.
    # Route ceo_boot_* through the scrub even on emit_generic path so
    # the allowlist cannot be bypassed by future direct callers.
    if action == "ceo_boot_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "ceo_boot_check_skipped":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_CHECK_SKIPPED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_check_skipped dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "optimizer_route_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["optimizer_route_recommended"])
        if dropped:
            _breadcrumb("emit_generic optimizer_route_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "fanout_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["fanout_recommended"])
        if dropped:
            _breadcrumb("emit_generic fanout_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "model_choice_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["model_choice_recommended"])
        if dropped:
            _breadcrumb("emit_generic model_choice_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "eval_task_completed":  # PLAN-133 C3 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _EVAL_TASK_COMPLETED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic eval_task_completed dropped: %s" % sorted(dropped)[:10])
    elif action == "rag_context_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["rag_context_recommended"])
        if dropped:
            _breadcrumb("emit_generic rag_context_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "codex_review_disabled":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["codex_review_disabled"])
        if dropped:
            _breadcrumb("emit_generic codex_review_disabled dropped: %s" % sorted(dropped)[:10])
    elif action == "codex_review_invoked":  # PLAN-122 WS3 + PLAN-132 — Sec MF-3 + S172 coercion
        if "review_status" in event and event.get("review_status") not in _CODEX_REVIEW_STATUS_ENUM:
            event["review_status"] = "other"
        if "review_source" in event and event.get("review_source") not in _CODEX_REVIEW_SOURCE_ENUM:
            event["review_source"] = "other"
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _safe_target_ref_hash_field(event.get("target_ref_hash"))
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["codex_review_invoked"])
        if dropped:
            _breadcrumb("emit_generic codex_review_invoked dropped: %s" % sorted(dropped)[:10])
    elif action == "verify_after_edit_finding":  # PLAN-128 §7 — Sec MF-3 + S172 coercion
        if event.get("checker") not in _VERIFY_CHECKER_ENUM:
            event["checker"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["finding_count"] = _accel_clamp_count(event.get("finding_count"))
        event, dropped = _scrub_ceo_boot_event(event, _VERIFY_AFTER_EDIT_FINDING_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic verify_after_edit_finding dropped: %s" % sorted(dropped)[:10])
    elif action == "adequacy_gate_flag":  # PLAN-128 §7 — Sec MF-3 + S172 coercion
        if event.get("flag_reason") not in _ADEQUACY_REASON_ENUM:
            event["flag_reason"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["flag_count"] = _accel_clamp_count(event.get("flag_count"))
        event, dropped = _scrub_ceo_boot_event(event, _ADEQUACY_GATE_FLAG_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic adequacy_gate_flag dropped: %s" % sorted(dropped)[:10])
    elif action == "quota_exhausted":  # PLAN-133 B5 — Sec MF-3 + S172 coercion
        if event.get("error_class") not in _QUOTA_ERROR_CLASS_ENUM:
            event["error_class"] = "unknown"
        if event.get("source") not in _QUOTA_ERROR_SOURCE_ENUM:
            event["source"] = "unknown"
        # http_status: keep only a small non-negative int, else drop the key.
        _hs = event.get("http_status")
        if not isinstance(_hs, int) or isinstance(_hs, bool) or _hs < 0 or _hs > 599:
            event.pop("http_status", None)
        event["attempt"] = _accel_clamp_count(event.get("attempt"))  # reuse 0..99 clamp
        event, dropped = _scrub_ceo_boot_event(event, _QUOTA_EXHAUSTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic quota_exhausted dropped: %s" % sorted(dropped)[:10])
    elif action == "context_auto_compacted":  # PLAN-133 D1 — Sec MF-3 + S172 coercion
        if event.get("reason") not in _AUTO_COMPACT_REASON_ENUM:
            event["reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(event.get("turns_since_last"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_AUTO_COMPACTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_auto_compacted dropped: %s" % sorted(dropped)[:10])
    elif action == "context_auto_compact_suppressed":  # PLAN-133 D1 — Sec MF-3 + S172 coercion
        if event.get("suppress_reason") not in _AUTO_COMPACT_SUPPRESS_REASON_ENUM:
            event["suppress_reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(event.get("turns_since_last"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_auto_compact_suppressed dropped: %s" % sorted(dropped)[:10])
    elif action == "context_middle_out_degraded":  # PLAN-133 D5 — Sec MF-3 + S172 coercion
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
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_middle_out_degraded dropped: %s" % sorted(dropped)[:10])
    elif action == "context_middle_out_degrade_failed":  # PLAN-133 D5 — Sec MF-3 + S172 coercion
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
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_middle_out_degrade_failed dropped: %s" % sorted(dropped)[:10])
    elif action == "supply_chain_advisory_emitted":  # PLAN-133 E2 — Sec MF-3 coercion
        if event.get("verdict") not in _SUPPLY_CHAIN_VERDICT_ENUM:
            event["verdict"] = "ALLOW"          # safe default; never invents a BLOCK
        if event.get("reason") not in _SUPPLY_CHAIN_REASON_ENUM:
            event["reason"] = "unknown"
        if event.get("ecosystem") not in _SUPPLY_CHAIN_ECOSYSTEM_ENUM:
            event["ecosystem"] = "other"
        # package: bound length + strip control chars (public identifier, but bound it).
        pkg = str(event.get("package", ""))
        event["package"] = "".join(c for c in pkg if c.isprintable())[:128]
        event["advisory_count"] = _accel_clamp_count(event.get("advisory_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic supply_chain_advisory_emitted dropped: %s"
                % sorted(dropped)[:10])
    elif action == "spawn_tool_scope_violation":  # PLAN-133 E3 — Sec MF-3 + coercion
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        # `detail` is tool-NAMES + counts; bound length, drop any path-shaped
        # token defensively (a "/" or "\" in detail is dropped to "" — no echo).
        _d = str(event.get("detail") or "")[:96]
        if "/" in _d or "\\" in _d:
            _d = ""
        event["detail"] = _d
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_tool_scope_violation dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "spawn_depth_or_overlap_blocked":  # PLAN-133 E3 — Sec MF-3 + coercion
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        event["count"] = _accel_clamp_count(event.get("count"))  # reuse §7 0..99 clamp
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_depth_or_overlap_blocked dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "spawn_file_assignment_recorded":  # PLAN-133 E3 — Sec MF-3 + coercion
        event["path_hashes"] = _e3_safe_path_hashes(event.get("path_hashes"))
        event["path_count"] = _accel_clamp_count(event.get("path_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_file_assignment_recorded dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "action_required_held":  # PLAN-133 E6 — Sec MF-3 + coercion
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
            _breadcrumb("emit_generic action_required_held dropped: %s" % sorted(dropped)[:10])
    elif action == "action_required_resumed":  # PLAN-133 E6 — Sec MF-3
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_RESUMED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic action_required_resumed dropped: %s" % sorted(dropped)[:10])
    elif action == "action_required_rejected":  # PLAN-133 E6 — Sec MF-3 + coercion
        if event.get("reject_reason") not in _ACTION_REQUIRED_REJECT_ENUM:
            event["reject_reason"] = "other"
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_REJECTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic action_required_rejected dropped: %s" % sorted(dropped)[:10])
    elif action == "ceo_boot_persona_coverage_score":  # PLAN-093 Wave C.5
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_persona_coverage_score dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-104 Wave A.4b — persona_demand_* Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("persona_demand_*",
    # raw_target_path=...)` would persist the forbidden field verbatim.
    # Codex iter-1 P0 #4 + iter-4 P0 fold (re-hash target_ref_hash
    # in opened/unmet branches so a caller can't stuff a raw path
    # into the allowed target_ref_hash field).
    elif action == "persona_demand_opened":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_OPENED_ALLOWLIST
        )
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_opened dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_matched":
        if "match_modality" in event and event.get("match_modality") not in _PERSONA_MATCH_MODALITY_ENUM:
            event["match_modality"] = "native_spawn"  # PLAN-132 — S172 safe default
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_MATCHED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_matched dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_unmet":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_UNMET_ALLOWLIST
        )
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_unmet dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_waived":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_WAIVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_waived dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_coverage_synthesized":  # PLAN-106 Wave C
        # Closed-enum validation BEFORE scrub. Invalid enum → drop the
        # whole event with breadcrumb (deny-by-default; prevents a
        # buggy caller from polluting the 4×4 matrix with free text).
        archetype = str(event.get("archetype", ""))
        task_type = str(event.get("task_type", ""))
        source = str(event.get("source", ""))
        if archetype not in _PERSONA_COVERAGE_ARCHETYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"archetype {archetype!r} not in closed enum"
            )
            return
        if task_type not in _PERSONA_COVERAGE_TASK_TYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"task_type {task_type!r} not in closed enum"
            )
            return
        if source not in _PERSONA_COVERAGE_SOURCES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"source {source!r} not in closed enum"
            )
            return
        # cell_id MUST be sha256[:8] (8 lowercase hex chars). Defensive
        # rebuild if caller passed a longer/non-hex value — always update
        # the event field so non-hex stripped values do not leak through.
        cell_id = str(event.get("cell_id", ""))[:8]
        if cell_id and not all(c in "0123456789abcdef" for c in cell_id):
            cell_id = ""
        event["cell_id"] = cell_id
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-090-FOLLOWUP Wave A.6 — claim producer pair Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("claim_emitted",
    # claim_id="/raw/path")` would persist forbidden raw text.
    # Codex iter-1 P0-3 + P0-4 + P1-1 folds (defensive rehash +
    # enum re-validation at emit_generic dispatch).
    elif action == "claim_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CLAIM_EMITTED_ALLOWLIST
        )
        if "claim_id" in event:
            event["claim_id"] = _safe_claim_id_hash(event.get("claim_id", ""))
        if "payload_hash" in event:
            event["payload_hash"] = _safe_payload_hash(event.get("payload_hash", ""))
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic claim_emitted dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "confidence_gate_verdict":
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
                f"emit_generic confidence_gate_verdict dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-100 Wave B — per-class block-mode Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("confidence_gate_blocked",
    # blocking_classes="unsanitized")` would persist non-list types.
    elif action == "confidence_gate_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_BLOCKED_ALLOWLIST
        )
        # Defensive — re-validate blocking_classes shape (list of short strings)
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
                f"emit_generic confidence_gate_blocked dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "confidence_gate_fp_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST
        )
        # Defensive — re-validate numeric fields
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
                f"emit_generic confidence_gate_fp_drift_detected dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-070 Round 5 / Layer B (Codex R5-02 closure, 2026-05-05+) —
    # wire `mcp_canonical_guard_{allowed,blocked}` through the same
    # field-allowlist scrub used by `ceo_boot_*`. The `_scrub_ceo_boot_
    # event` helper is allowlist-agnostic (pure dict-filter), so we
    # reuse it here. Without this wire-up, a future caller invoking
    # `emit_generic("mcp_canonical_guard_blocked", raw_secret=...)`
    # would persist forbidden fields verbatim — Codex R5-02 PoC.
    elif action == "mcp_canonical_guard_allowed":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_allowed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "mcp_canonical_guard_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_blocked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-071 / ADR-104 — task-route + reality-ledger advisory events.
    # Reuse allowlist-agnostic _scrub_ceo_boot_event helper.
    elif action == "task_route_advised":
        event, dropped = _scrub_ceo_boot_event(
            event, _TASK_ROUTE_ADVISED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
            # PLAN-114 F-1-1.8-47dba028 — wire the typed defense-in-depth
            # action so the strip is in the HMAC-covered audit trail (not
            # only the errors-sidecar breadcrumb). Fail-open: a wire error
            # must never block the parent task_route_advised emit.
            try:
                emit_task_route_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    reason_code="allowlist_strip",
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass
    # PLAN-101 Wave B / ADR-104-AMEND-1 §E — task_route_ground_truth_label.
    elif action == "task_route_ground_truth_label":
        event, dropped = _scrub_ceo_boot_event(
            event, _TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_ground_truth_label dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §A — cost_envelope_capped.
    elif action == "cost_envelope_capped":
        event, dropped = _scrub_ceo_boot_event(
            event, _COST_ENVELOPE_CAPPED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic cost_envelope_capped dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §B — swarm_runaway_suspected.
    elif action == "swarm_runaway_suspected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_RUNAWAY_SUSPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_runaway_suspected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §C — swarm_paused_owner_absent.
    elif action == "swarm_paused_owner_absent":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST
        )
        # PLAN-136 W3 (S3) — defense-in-depth int coercion of the bucketed
        # loop_duration_hours field (same class as PLAN-135-FOLLOWUP-2 / S234:
        # the HMAC canonical encoder rejects float — S181). The live producer is
        # already int (>=1h bucket), so this path is safe today; this is the
        # authoritative int-coercion boundary so a DIRECT emit_generic caller
        # cannot smuggle a float / string / non-finite into the signed chain.
        # Floor is max(1, ...) — the producer's >=1h bucket floor IS the sentinel
        # (a coerce-failure or sub-1h value collapses to the smallest legit
        # bucket, never 0). OverflowError (int(round(float('inf')))) is caught
        # alongside Type/ValueError so the boundary never raises.
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
                f"emit_generic swarm_paused_owner_absent dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — swarm_layer_3_4_blocked.
    elif action == "swarm_layer_3_4_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_LAYER_3_4_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_layer_3_4_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave B / ADR-133 §D — execution_context_signed.
    elif action == "execution_context_signed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_SIGNED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_signed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave B / ADR-133 §D — execution_context_validation_failed.
    elif action == "execution_context_validation_failed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_validation_failed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "reality_ledger_finding":
        event, dropped = _scrub_ceo_boot_event(
            event, _REALITY_LEDGER_FINDING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic reality_ledger_finding dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
            # PLAN-114 F-1-1.8-8d4e2519 — wire the typed defense-in-depth
            # action into the HMAC-covered audit trail. Fail-open.
            try:
                emit_reality_ledger_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    detector=str(event.get("detector", "")),
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass
    # PLAN-078 Wave 1 — model_routing_advised dispatch gate.
    elif action == "model_routing_advised":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_ADVISED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-persona-routing-wire W2 — model_routing_enforced gate.
    elif action == "model_routing_enforced":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_ENFORCED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_enforced dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-persona-routing-wire W2 — model_routing_eval_error gate.
    elif action == "model_routing_eval_error":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_EVAL_ERROR_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_eval_error dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-078 Wave 2 — estimate_drift dispatch gates.
    elif action == "estimate_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "estimate_drift_systematic_bias":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_systematic_bias dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-078 Wave 5 — ceo_boot_task_candidate_emitted dispatch gate.
    # Defense-in-depth: blocks future direct callers (e.g.
    # `emit_generic("ceo_boot_task_candidate_emitted", subject="...")`)
    # from leaking subject text or other forbidden fields.
    elif action == "ceo_boot_task_candidate_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_task_candidate_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 1-full — pair_rail_codex_injection_detected dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through the
    # Sec MF-3 allowlist scrub. Raw matched-content / raw-offset must NEVER
    # persist (LLM06 side-channel guard).
    elif action == "pair_rail_codex_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_codex_injection_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 2 — dispatcher_route dispatch gate.
    # Defense-in-depth: archetype profile / task description / skill body
    # MUST never persist via this action — the canonical sources are
    # _CANONICAL_GUARDS-protected. Only routing-decision metadata + perf
    # field (wall_clock_s) per allowlist.
    elif action == "dispatcher_route":
        event, dropped = _scrub_ceo_boot_event(
            event, _DISPATCHER_ROUTE_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic dispatcher_route dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 3 — pair_rail_case dispatch gate.
    elif action == "pair_rail_case":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_CASE_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_case dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 4 — pair_rail_promotion dispatch gate.
    elif action == "pair_rail_promotion":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_promotion dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.4 (S106) — token_budget_guard_paused dispatch gate.
    elif action == "token_budget_guard_paused":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic token_budget_guard_paused dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_block dispatch gate.
    elif action == "anti_ceo_overhead_block":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_block dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_override_used dispatch gate.
    elif action == "anti_ceo_overhead_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.7d (S106) — smart_loading_resolved dispatch gate.
    elif action == "smart_loading_resolved":
        event, dropped = _scrub_ceo_boot_event(
            event, _SMART_LOADING_RESOLVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic smart_loading_resolved dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.1 — first_run_wizard_completed dispatch gate.
    elif action == "first_run_wizard_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_completed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.2 — contextual_recommendation_emitted dispatch gate.
    elif action == "contextual_recommendation_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic contextual_recommendation_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.4 — value_dashboard_summarized dispatch gate.
    elif action == "value_dashboard_summarized":
        event, dropped = _scrub_ceo_boot_event(
            event, _VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic value_dashboard_summarized dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_write_override_used dispatch gate.
    # PLAN-085 Wave C.1 — live_adapter_blocked dispatch gate.
    elif action == "live_adapter_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _LIVE_ADAPTER_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic live_adapter_blocked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — prompt_injection_detected dispatch gate.
    elif action == "prompt_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PROMPT_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic prompt_injection_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex B3 P1 — mcp_injection_finding scrub gate (was passthrough).
    # MCP-controlled snippet_preview is re-truncated via _preview() so a direct
    # emit_generic caller cannot bypass the named-emitter [:120] cap.
    elif action == "mcp_injection_finding":
        if "snippet_preview" in event:
            event["snippet_preview"] = _preview(
                str(event.get("snippet_preview", "")), max_len=120
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_INJECTION_FINDING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_injection_finding dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — secret_leak_detected dispatch gate.
    elif action == "secret_leak_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SECRET_LEAK_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic secret_leak_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — pii_redacted_outgoing dispatch gate.
    elif action == "pii_redacted_outgoing":
        event, dropped = _scrub_ceo_boot_event(
            event, _PII_REDACTED_OUTGOING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic pii_redacted_outgoing dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — codex_egress_redacted dispatch gate.
    elif action == "codex_egress_redacted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CODEX_EGRESS_REDACTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic codex_egress_redacted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry — pair_rail_outgoing_redaction_applied gate.
    elif action == "pair_rail_outgoing_redaction_applied":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic pair_rail_outgoing_redaction_applied dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave E.4 piggyback — canonical_edit_completed dispatch gate.
    elif action == "canonical_edit_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CANONICAL_EDIT_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic canonical_edit_completed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.2 — credential_blocked_due_to_age dispatch gate.
    elif action == "credential_blocked_due_to_age":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic credential_blocked_due_to_age dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.2 — credential_emergency_override_used dispatch gate.
    elif action == "credential_emergency_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic credential_emergency_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-117 WS-A — credential_override_late_set_ignored dispatch gate.
    elif action == "credential_override_late_set_ignored":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST
        )
        # Self-enforce the closed-enum / no-value-echo contract at the chokepoint,
        # independent of the caller: FORCE the var name to the constant and COERCE
        # an out-of-enum provenance hint. The rejected override VALUE can never
        # reach the payload via either field (even on a direct emit_generic call).
        event["attempted_var_name"] = _CREDENTIAL_OVERRIDE_VAR_NAME
        if event.get("provenance_hint") not in _CREDENTIAL_OVERRIDE_PROVENANCE_HINTS:
            event["provenance_hint"] = "unspecified"
        if dropped:
            _breadcrumb(
                "emit_generic credential_override_late_set_ignored dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.3 — mcp_bearer_replay_rejected dispatch gate.
    elif action == "mcp_bearer_replay_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_BEARER_REPLAY_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_bearer_replay_rejected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.3 — mcp_non_loopback_rejected dispatch gate.
    elif action == "mcp_non_loopback_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_NON_LOOPBACK_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_non_loopback_rejected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "trading_write_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_WRITE_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_write_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_invoked dispatch gate.
    elif action == "trading_kill_switch_invoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_INVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_invoked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_disabled dispatch gate.
    elif action == "trading_kill_switch_disabled":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_DISABLED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_disabled dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-088 canonical-13 god-mode auto-activation (S114) — 12 dispatch
    # gates for the 11 net-new + 1 wire (mcp_route_advised). Sec MF-3
    # defense-in-depth per qa-architect P0-3: prevent emit_generic callers
    # from bypassing the typed-wrapper allowlist enforcement.
    elif action == "cache_discipline_alerted":
        event, dropped = _scrub_ceo_boot_event(event, _CACHE_DISCIPLINE_ALERTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic cache_discipline_alerted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "first_run_wizard_dispatched":
        event, dropped = _scrub_ceo_boot_event(event, _FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "estimate_calibrator_pipeline_run":
        event, dropped = _scrub_ceo_boot_event(event, _ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_calibrator_pipeline_run dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "subagent_findings_partial_drop":
        event, dropped = _scrub_ceo_boot_event(event, _SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic subagent_findings_partial_drop dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-106 Wave H.1 — output_scan_finding_suppressed dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through
    # the Sec MF-3 allowlist scrub. NO raw secret / matched_content /
    # command body must persist — closed-enum `pattern_id` + `family`
    # enforced at producer site (`_lib/output_scan._PATTERN_IDS`).
    elif action == "output_scan_finding_suppressed":
        event, dropped = _scrub_ceo_boot_event(
            event, _OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic output_scan_finding_suppressed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "anthropic_429_observed":
        event, dropped = _scrub_ceo_boot_event(event, _ANTHROPIC_429_OBSERVED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic anthropic_429_observed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "git_index_lock_retry":
        event, dropped = _scrub_ceo_boot_event(event, _GIT_INDEX_LOCK_RETRY_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic git_index_lock_retry dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "codex_invoke_dispatched":
        # PLAN-143 item-3 (audit-errors-04): clamp the dual-rail exit_code
        # to the POSIX exit-status range (0..255) BEFORE the allowlist
        # scrub so the now-retained field can never carry an unbounded /
        # non-int value. Mirrors the bps/count clamps used elsewhere in
        # emit_generic. Absent/garbage -> 0 (fail-open, advisory telemetry).
        if "exit_code" in event:
            try:
                event["exit_code"] = max(0, min(255, int(event["exit_code"])))
            except (TypeError, ValueError):
                event["exit_code"] = 0
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_INVOKE_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic codex_invoke_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "tier_policy_misrouting_advised":
        event, dropped = _scrub_ceo_boot_event(event, _TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic tier_policy_misrouting_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "tier_policy_loader_fallback_observed":  # PLAN-116 (S172)
        # Closed-enum validation BEFORE scrub (deny-by-default; mirrors
        # persona_coverage_synthesized). An out-of-enum reason_code drops the
        # whole event with a breadcrumb so a buggy/future caller cannot
        # pollute the action with free text.
        _rc = str(event.get("reason_code", ""))
        if _rc not in _TIER_POLICY_LOADER_FALLBACK_REASON_CODES:
            # Do NOT echo the rejected value: free-text into the errors
            # sidecar is exactly the noise class PLAN-116 closes. Length only.
            _breadcrumb(
                "emit_generic tier_policy_loader_fallback_observed dropped: "
                f"reason_code not in closed enum (len={len(_rc)})"
            )
            return
        event, dropped = _scrub_ceo_boot_event(
            event, _TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic tier_policy_loader_fallback_observed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "audit_producer_path_pollution_detected":  # PLAN-118 AC-B5
        # Closed-enum validation BEFORE scrub. Two enums: `chokepoint`
        # (origin of the breadcrumb) + `reason_code` (which canonical
        # module mismatched). NO `__file__` echo — only sha256[:8]
        # prefixes per [[feedback-closed-enum-breadcrumb-must-not-echo-
        # rejected-value]]. Out-of-enum values DROP the event with a
        # length-only breadcrumb (defense against a buggy/future caller
        # smuggling free text). Sec MF-3 defense-in-depth: a direct
        # emit_generic caller cannot bypass the typed wrapper's
        # validation.
        _cp = str(event.get("chokepoint", ""))
        if _cp not in _AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS:
            _breadcrumb(
                "emit_generic audit_producer_path_pollution_detected dropped: "
                f"chokepoint not in closed enum (len={len(_cp)})"
            )
            return
        _rc = str(event.get("reason_code", ""))
        if _rc not in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
            _breadcrumb(
                "emit_generic audit_producer_path_pollution_detected dropped: "
                f"reason_code not in closed enum (len={len(_rc)})"
            )
            return
        # Validate the two 8-hex-prefix fields exist and are well-formed.
        for _hex_field in ("path_sha256_prefix", "expected_canonical_prefix"):
            _val = str(event.get(_hex_field, ""))
            if len(_val) != 8 or not all(c in "0123456789abcdef" for c in _val):
                _breadcrumb(
                    "emit_generic audit_producer_path_pollution_detected dropped: "
                    f"{_hex_field} not 8 hex chars (len={len(_val)})"
                )
                return
        event, dropped = _scrub_ceo_boot_event(
            event, _AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic audit_producer_path_pollution_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "mcp_route_advised":
        event, dropped = _scrub_ceo_boot_event(event, _MCP_ROUTE_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_route_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "cookbook_pattern_advised":
        event, dropped = _scrub_ceo_boot_event(event, _COOKBOOK_PATTERN_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic cookbook_pattern_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "pair_rail_phase_advanced":
        event, dropped = _scrub_ceo_boot_event(event, _PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_phase_advanced dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "batch_dispatched":
        event, dropped = _scrub_ceo_boot_event(event, _BATCH_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic batch_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-107 Wave B.4.2 (S145 2026-05-19) — stdlib_violation dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through
    # the Sec MF-3 allowlist scrub. Without this branch the orphan event
    # would be silently scrubbed by the default fall-through path.
    elif action == "stdlib_violation":
        event, dropped = _scrub_ceo_boot_event(event, _STDLIB_VIOLATION_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic stdlib_violation dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-113 Phase B B-STRUCTURAL — federation_* dispatch gates. Each LIVE
    # federation action (emitted via _lib.federation.*._safe_emit ->
    # emit_generic) is routed through the Sec MF-3 allowlist scrub. Without
    # these branches the caller kwargs were written VERBATIM into the HMAC
    # audit log (the ghost-action leak). The two path fields (source_path /
    # sentinel_path) are re-hashed to 12-hex AFTER the scrub so no host path
    # can leak even from an in-allowlist field.
    elif action == "federation_connection_accepted":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_ACCEPTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_accepted dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_connection_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_rejected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_connection_replay_suspected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_REPLAY_SUSPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_replay_suspected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_expiry_warned":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_EXPIRY_WARNED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_expiry_warned dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_revoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_REVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_revoked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_validity_window_too_large":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_VALIDITY_WINDOW_TOO_LARGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_validity_window_too_large "
                f"dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_enable_sentinel_invalid":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_ENABLE_SENTINEL_INVALID_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_enable_sentinel_invalid dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_lan_bind_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_LAN_BIND_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_lan_bind_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_attempt_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_ATTEMPT_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_attempt_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_endpoint_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_ENDPOINT_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_endpoint_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_disabled_sentinel_invalid":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_DISABLED_SENTINEL_INVALID_ALLOWLIST
        )
        if "sentinel_path" in event:
            event["sentinel_path"] = _federation_safe_path_hash(
                event.get("sentinel_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_disabled_sentinel_invalid "
                f"dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_scope_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_SCOPE_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_scope_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_event_action_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_EVENT_ACTION_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_event_action_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_event_pushed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_EVENT_PUSHED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_event_pushed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_event_pushed_batch":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_EVENT_PUSHED_BATCH_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_event_pushed_batch dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_registered":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REGISTERED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_registered dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_registered_collision":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REGISTERED_COLLISION_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_registered_collision dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_revoked_remote":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REVOKED_REMOTE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_revoked_remote dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_invalid_no_fingerprint":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_INVALID_NO_FINGERPRINT_ALLOWLIST
        )
        if "source_path" in event:
            event["source_path"] = _federation_safe_path_hash(
                event.get("source_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_invalid_no_fingerprint dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_list_reloaded":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_LIST_RELOADED_ALLOWLIST
        )
        if "source_path" in event:
            event["source_path"] = _federation_safe_path_hash(
                event.get("source_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_list_reloaded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_pin_legacy_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PIN_LEGACY_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_pin_legacy_used dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_spki_fingerprint_mismatch":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_SPKI_FINGERPRINT_MISMATCH_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_spki_fingerprint_mismatch dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_message_storm_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_MESSAGE_STORM_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_message_storm_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_log_backpressure":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_LOG_BACKPRESSURE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_log_backpressure dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_tamper_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_TAMPER_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_tamper_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Phase B B5 — defense-in-depth scrub branches for the
    # RESERVED-no-producer destructive federation actions. No producer
    # invokes these today (see _RESERVED_ACTIONS), but if an accidental
    # caller ever appears the fields are allowlist-bounded, not raw.
    elif action == "federation_autonomous_call_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUTONOMOUS_CALL_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_autonomous_call_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_hmac_secret_rotated":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_HMAC_SECRET_ROTATED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_hmac_secret_rotated dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_key_floor_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_KEY_FLOOR_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_key_floor_rejected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_key_floor_stale":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_KEY_FLOOR_STALE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_key_floor_stale dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P1 — bash_canonical_bypass_invoked Sec MF-3 scrub.
    # target_path_preview (raw filesystem path) replaced by target_path_hash
    # (12-hex sha256 prefix). The allowlist enforces the deny-by-default
    # boundary so no future caller can reintroduce a raw path field.
    elif action == "bash_canonical_bypass_invoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic bash_canonical_bypass_invoked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P2 — spawn_confidence_advisory explicit allowlist branch.
    # Moved from _EMIT_GENERIC_PASSTHROUGH; Sec MF-3 deny-by-default enforced.
    elif action == "spawn_confidence_advisory":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic spawn_confidence_advisory dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P2 — spec_context_sanitized explicit allowlist branch.
    # Moved from _EMIT_GENERIC_PASSTHROUGH; Sec MF-3 deny-by-default enforced.
    elif action == "spec_context_sanitized":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPEC_CONTEXT_SANITIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic spec_context_sanitized dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A2 — invisible-unicode hard-block breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted
    # keys (so a smuggled prompt/content/char body can never reach the wire) and the
    # VALUE re-coercion below closes the direct-emit_generic-caller path: a raw value
    # placed in unicode_class/surface is reset to a safe default, and char_count is
    # clamped to a bounded non-negative int.
    elif action == "invisible_unicode_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _INVISIBLE_UNICODE_BLOCKED_ALLOWLIST
        )
        if event.get("unicode_class") not in _INVISIBLE_UNICODE_CLASSES:
            event["unicode_class"] = "control"
        if event.get("surface") not in _INVISIBLE_UNICODE_SURFACES:
            event["surface"] = "spawn"
        # Bounded non-negative int (no float in HMAC-covered fields; clamp 0..1e6).
        try:
            cc = int(event.get("char_count", 0))
        except (TypeError, ValueError):
            cc = 0
        event["char_count"] = max(0, min(cc, 1_000_000))
        # enforced is a 0/1 flag.
        event["enforced"] = 1 if str(event.get("enforced")) in ("1", "True", "true") else 0
        if dropped:
            _breadcrumb(
                f"emit_generic invisible_unicode_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-125 WS-1 — per-tool-call lifecycle telemetry. Dedicated scrub
    # branch (Sec MF-SEC-2: NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name
    # scrub below only DROPS non-allowlisted keys — it does NOT re-validate the
    # VALUES of the allowlisted enum fields. So a direct emit_generic caller
    # (bypassing the typed emitter) could otherwise smuggle a raw mcp__* tool
    # name or a raw duration token into the signed chain via the allowed
    # tool_name_enum / duration_bucket fields. Re-coerce both VALUES here by
    # closed-set membership — mirroring emit_tool_call_lifecycle_recorded — so
    # the emit_generic path is a true second line of defense (MF-SEC-1/3).
    elif action == "tool_call_lifecycle_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST
        )
        if event.get("tool_name_enum") not in _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("duration_bucket") not in _TOOL_CALL_LIFECYCLE_DURATION_BUCKETS:
            event["duration_bucket"] = "lt_100ms"
        # The allowlist also permits success / orphan — coerce their VALUES to
        # bool too (Codex pair-rail P0): a direct emit_generic caller could
        # otherwise put a free-form string/dict (signed verbatim into the HMAC
        # chain) or a float (breaks canonical-JSON → unsigned hmac_error row)
        # into either field. The typed emitter already does bool(...); mirror it.
        event["success"] = bool(event.get("success"))
        event["orphan"] = bool(event.get("orphan"))
        if dropped:
            _breadcrumb(
                f"emit_generic tool_call_lifecycle_recorded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-124 WS-1 — git hook-bypass guard breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH;
    # [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # field-name scrub below only DROPS non-allowlisted keys (so a smuggled
    # `command`/`raw`/`token` body never reaches the wire) — it does NOT
    # re-validate the VALUE of the allowed `flag_class` field. So a direct
    # emit_generic caller (bypassing the typed emitter) could otherwise put a
    # raw command substring into `flag_class` and have it signed verbatim into
    # the HMAC chain. Re-coerce the VALUE here by closed-set membership —
    # mirroring emit_git_hook_bypass_blocked — so the emit_generic path is a
    # true second line of defense (MF-G).
    elif action == "git_hook_bypass_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST
        )
        if event.get("flag_class") not in _GIT_HOOK_BYPASS_FLAG_CLASSES:
            event["flag_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic git_hook_bypass_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A1 — env-hijack denylist breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`key`/`value` body never reaches the wire) and the
    # VALUE re-coercion below closes the direct-emit_generic-caller path: a raw
    # var name/value placed in `hijack_class` is reset to "parse_failure".
    elif action == "env_var_hijack_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST
        )
        if event.get("hijack_class") not in _ENV_VAR_HIJACK_CLASSES:
            event["hijack_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic env_var_hijack_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A3 — egress-destination breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`url`/`full_url` body never reaches the wire); the
    # egress_class re-coercion resets an out-of-set value; the destination is
    # re-reduced to a bare host (defense-in-depth on a direct emit_generic caller).
    elif action == "egress_destination_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _EGRESS_DESTINATION_DETECTED_ALLOWLIST
        )
        if event.get("egress_class") not in _EGRESS_CLASSES:
            event["egress_class"] = "unknown"
        if "destination" in event:
            event["destination"] = _coerce_egress_destination(event["destination"])
        if dropped:
            _breadcrumb(
                f"emit_generic egress_destination_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 E1 — adversary local-rules breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`match`/`regex` body never reaches the wire); the
    # closed-enum re-coercions below close the direct-emit_generic-caller path.
    elif action == "adversary_review_flagged":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
        )
        if event.get("decision") not in _ADVERSARY_DECISIONS:
            event["decision"] = "advisory"
        if event.get("rule_class") not in _ADVERSARY_RULE_CLASSES:
            event["rule_class"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic adversary_review_flagged dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 G1 — persistent-instructions breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS
    # non-allowlisted keys (so a smuggled instruction body / matched line / path
    # never reaches the wire); the closed-enum re-coercion closes the direct
    # emit_generic-caller path.
    elif action == "persistent_instructions_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST
        )
        if event.get("reason") not in _PERSISTENT_INSTRUCTIONS_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic persistent_instructions_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 G3 — hint provenance breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted
    # keys (so a smuggled hint body / matched line / path text never reaches the
    # wire); the closed-enum re-coercion closes the direct emit_generic-caller
    # path.
    elif action == "hint_provenance_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _HINT_PROVENANCE_RECORDED_ALLOWLIST
        )
        if event.get("reason") not in _HINT_PROVENANCE_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic hint_provenance_recorded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W1 S3 — /ceo-boot settings/env tamper tripwire breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys (so a smuggled finding
    # `detail` / env value / endpoint URL never reaches the wire); the
    # closed-enum re-coercions + int clamp close the direct
    # emit_generic-caller path (S172 doctrine — rejected values are
    # replaced with the safe sentinel, never echoed).
    elif action == "settings_tamper_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SETTINGS_TAMPER_DETECTED_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _SETTINGS_TAMPER_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(
                0, min(99, int(event.get("finding_count", 0)))
            )
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic settings_tamper_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H2 — ConfigChange-guard observed breadcrumb. Dedicated
    # scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub
    # DROPS non-allowlisted keys (so a smuggled file path / settings body /
    # key value never reaches the wire); the closed-enum re-coercion closes
    # the direct emit_generic-caller path (S172 doctrine — rejected values
    # are replaced with the safe sentinel, never echoed).
    elif action == "config_change_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIG_CHANGE_OBSERVED_ALLOWLIST
        )
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H2 — ConfigChange-guard forbidden-key breadcrumb (the
    # advisory-block path). Same contract as settings_tamper_detected: the
    # field-name scrub DROPS non-allowlisted keys, closed-enum re-coercions
    # + int clamp close the direct emit_generic-caller path. The forbidden
    # key's VALUE and the finding DETAIL never reach the wire.
    elif action == "config_change_forbidden_key":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(
                0, min(99, int(event.get("finding_count", 0)))
            )
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_forbidden_key dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H1 (ADR-153) — PreCompact compaction-continuity snapshot
    # breadcrumb. Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH).
    # The field-name scrub DROPS non-allowlisted keys (so a smuggled
    # snapshot body / plan text / hmac hex never reaches the wire); the
    # closed-enum re-coercions + strict plan-id shape check + int clamp
    # close the direct emit_generic-caller path (S172 doctrine — rejected
    # values are replaced with the safe sentinel, never echoed).
    elif action == "compaction_continuity_snapshot":
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
                f"emit_generic compaction_continuity_snapshot dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H1 (ADR-153) — PostCompact governance-pointer reinjection
    # breadcrumb. Same contract: deny-by-default scrub, strict plan-id shape
    # check, bool/int coercions. The reinjected additionalContext TEXT is
    # never an allowed field (pointers-only doctrine — the wire carries
    # counters, not context).
    elif action == "compaction_context_reinjected":
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
            event["pointer_count"] = max(
                0, min(9, int(event.get("pointer_count", 0)))
            )
        except (TypeError, ValueError):
            event["pointer_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic compaction_context_reinjected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H5 (ADR-154) — corrective bash-input rewrite breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys (so a smuggled command
    # string / remote URL / inline token never reaches the wire); the
    # closed-enum re-coercion + 64-hex hash validation close the direct
    # emit_generic-caller path (S172 doctrine — rejected values are replaced
    # with the safe sentinel, never echoed).
    elif action == "bash_input_rewritten":
        event, dropped = _scrub_ceo_boot_event(
            event, _BASH_INPUT_REWRITTEN_ALLOWLIST
        )
        if event.get("rewrite_class") not in _BASH_REWRITE_CLASSES:
            event["rewrite_class"] = "other"
        if not _is_sha256_hex(event.get("before_sha256")):
            event["before_sha256"] = ""
        if not _is_sha256_hex(event.get("after_sha256")):
            event["after_sha256"] = ""
        if dropped:
            _breadcrumb(
                f"emit_generic bash_input_rewritten dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H3 — per-agent SubagentStop lifecycle bracket breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name
    # scrub DROPS non-allowlisted keys (so a smuggled transcript path/body, raw
    # token count, raw wall-time, raw agent_id or marker snippet never reaches
    # the wire); the closed-enum re-coercions close the direct emit_generic-caller
    # path (S172 doctrine — rejected values are replaced with the safe sentinel,
    # never echoed). Every wire field is a closed enum or coarse bucket.
    elif action == "subagent_lifecycle_observed":
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
                f"emit_generic subagent_lifecycle_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — admin_key_lifecycle_event dedicated
    # deny-by-default scrub branch. Field-name scrub DROPS any non-allowlisted key
    # (a smuggled secret=... can never reach the HMAC-signed wire) AND the VALUE
    # re-coercion closes the direct-emit_generic-caller path: operation + reason
    # reset to their closed enums (else "other"), key_id str-bounded, key_count
    # int-clamped (no float in HMAC-covered fields — S181), rotation_log_appended
    # coerced to a real bool (the SPEC-declared type). NEVER
    # _EMIT_GENERIC_PASSTHROUGH (Sec MF-SEC-2).
    elif action == "admin_key_lifecycle_event":
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
                event["key_count"] = max(0, min(int(event.get("key_count", 0)), 1_000_000))
            except (TypeError, ValueError, OverflowError):
                event["key_count"] = 0
        if "rotation_log_appended" in event:
            # SPEC declares this a BOOL (not 0/1) — coerce to a real bool so a
            # direct caller cannot smuggle a string/int through (Codex R5-R1 P1).
            event["rotation_log_appended"] = str(
                event.get("rotation_log_appended")
            ).strip().lower() in ("1", "true", "yes")
        if dropped:
            _breadcrumb(
                "emit_generic admin_key_lifecycle_event dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — statusline_sidecar_write scrub branch.
    # All fields are numeric / id / digest; sidecar_path length-capped to bound
    # log-line bloat; pct fields are integer BASIS-POINTS clamped to int
    # (PLAN-135-FOLLOWUP-2, S234 — never float; a direct caller cannot smuggle a
    # string OR a float into the signed chain). NEVER _EMIT_GENERIC_PASSTHROUGH.
    elif action == "statusline_sidecar_write":
        event, dropped = _scrub_ceo_boot_event(
            event, _STATUSLINE_SIDECAR_WRITE_ALLOWLIST
        )
        if "sidecar_path" in event:
            event["sidecar_path"] = str(event.get("sidecar_path", ""))[:_STATUSLINE_SIDECAR_PATH_CAP]
        if "plan_id" in event and event.get("plan_id") is not None:
            event["plan_id"] = str(event.get("plan_id"))[:_STATUSLINE_STR_CAP]
        if "digest" in event:
            event["digest"] = str(event.get("digest", ""))[:_STATUSLINE_STR_CAP]
        if "bucket_count" in event:
            try:
                event["bucket_count"] = max(0, min(int(event.get("bucket_count", 0)), 1_000_000))
            except (TypeError, ValueError, OverflowError):
                event["bucket_count"] = 0
        # PLAN-135-FOLLOWUP-2 (S234): integer basis-points, NEVER float — the
        # HMAC canonical encoder rejects float (S181). The producer
        # (.claude/scripts/statusline-ceo.py) owns the pct*100 scaling and emits
        # a finished *_bps int; this scrub is the authoritative Sec MF-3 int
        # coercion boundary — it int-coerces + clamps but NEVER re-scales (a
        # direct caller is contracted to pass basis-points; SPEC v2.46). Ranges
        # DIFFER: context_pct is 0..100% -> 0..10000 bps; buckets_used_pct_max
        # derives from rate-limit used_pct capped at 999% -> 0..99900 bps (NO
        # 100% ceiling, so an over-quota burst is not silently floored).
        # OverflowError (float("inf")) is caught alongside Type/ValueError.
        if (
            "context_pct_bps" in event
            and event.get("context_pct_bps") is not None
        ):
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
                    min(99900, int(round(float(event.get("buckets_used_pct_max_bps"))))),
                )
            except (TypeError, ValueError, OverflowError):
                event["buckets_used_pct_max_bps"] = None
        if dropped:
            _breadcrumb(
                "emit_generic statusline_sidecar_write dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — model_refusal_observed scrub branch.
    # stop_reason coerced to the const "refusal"; stop_category bounded to the
    # closed provider vocabulary (<=64, non-str → ""); http_status/duration_ms
    # bounded non-negative ints (no float in HMAC-covered fields — S181).
    # NEVER _EMIT_GENERIC_PASSTHROUGH.
    elif action == "model_refusal_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_REFUSAL_OBSERVED_ALLOWLIST
        )
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
                    event[_intf] = max(0, min(int(event.get(_intf, 0)), 1_000_000_000))
                except (TypeError, ValueError, OverflowError):
                    event[_intf] = 0
        if dropped:
            _breadcrumb(
                "emit_generic model_refusal_observed dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # PLAN-113 Phase B B-STRUCTURAL — verbatim passthrough for the documented
    # set of TRUSTED first-party producers (see _EMIT_GENERIC_PASSTHROUGH).
    # Their field sets are controlled at the producer site; pass through as-is
    # to preserve the pre-existing accepted contract (no regression).
    elif action in _EMIT_GENERIC_PASSTHROUGH:
        pass
    # PLAN-113 Phase B B-STRUCTURAL — DEFAULT-DENY safety net. Any
    # _KNOWN_ACTIONS member that reached emit_generic WITHOUT an explicit
    # scrub branch, that is NOT a RESERVED action, and that is NOT in the
    # documented verbatim-passthrough set, has ALL caller kwargs dropped: we
    # rebuild the event as just {"action": action} and let _write_event add
    # the framework envelope. This is the safety net for future / unregistered
    # / unexpected producers — closing the ghost-action leak class: a freshly
    # registered action defaults to fail-closed until its author gives it a
    # scrub branch or consciously lists it as a passthrough.
    else:
        event = {"action": action}
        _breadcrumb(
            f"emit_generic {action}: default-deny dropped caller kwargs"
        )
    _write_event(event)


def emit_session_start(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    governance_state: str = "unknown",
    gate_1_hashes: Optional[Dict[str, Optional[str]]] = None,
    warmup_bytes: int = 0,
    project: str = "",
) -> None:
    """Emit session_start event (SessionStart.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_start",
        session_id=session_id,
        hook_version=hook_version,
        governance_state=governance_state,
        gate_1_hashes=gate_1_hashes or {},
        warmup_bytes=warmup_bytes,
        project=project,
    )


def emit_session_end(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    reason: str = "normal",
    memory_writable: bool = False,
    memory_index_present: bool = False,
    project: str = "",
) -> None:
    """Emit session_end event (SessionEnd.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_end",
        session_id=session_id,
        hook_version=hook_version,
        reason=reason,
        memory_writable=memory_writable,
        memory_index_present=memory_index_present,
        project=project,
    )


def emit_prompt_submitted(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    prompt_len_bucket: str = "",
    prompt_sha256: str = "",
    redact_hits_count: int = 0,
    injection_family_counts: Optional[Dict[str, int]] = None,
    project: str = "",
) -> None:
    """Emit prompt_submitted event (UserPromptSubmit.py). ADR-056 §Per-hook matrix.

    Privacy: prompt content is NEVER persisted raw — only bucket, hash
    prefix, and family counters.
    """
    emit_generic(
        "prompt_submitted",
        session_id=session_id,
        hook_version=hook_version,
        prompt_len_bucket=prompt_len_bucket,
        prompt_sha256=prompt_sha256,
        redact_hits_count=redact_hits_count,
        injection_family_counts=injection_family_counts or {},
        project=project,
    )


def emit_session_stop(
    *,
    session_id: str,
    hook_version: str = "1.0.0",
    reason: str = "user_stop",
    partial_state_saved: bool = False,
    project: str = "",
) -> None:
    """Emit session_stop event (Stop.py). ADR-056 §Per-hook matrix."""
    emit_generic(
        "session_stop",
        session_id=session_id,
        hook_version=hook_version,
        reason=reason,
        partial_state_saved=partial_state_saved,
        project=project,
    )


def emit_output_scan_finding(
    *,
    session_id: str,
    tool_name: str,
    hook_version: str = "1.0.0",
    total_findings: int = 0,
    family_counts: Optional[Dict[str, int]] = None,
    kill_switched: Optional[Dict[str, bool]] = None,
    project: str = "",
) -> None:
    """Emit output_scan_finding event (check_output_secrets.py). ADR-057 §Audit event.

    Only called when total_findings > 0 (hook short-circuits on clean).
    """
    emit_generic(
        "output_scan_finding",
        session_id=session_id,
        tool_name=tool_name,
        hook_version=hook_version,
        total_findings=total_findings,
        family_counts=family_counts or {},
        kill_switched=kill_switched or {},
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-059 SEC-P0-04 / ADR-080 — audit-tokens content-ban
# (Session 62 cont, 2026-04-25)
# ---------------------------------------------------------------------

# Counts-only allowlist for audit_tokens_emitted events.
# Per SEC-P0-04 spec §Emission contract (ALLOWED), the audit-tokens
# stub format MUST emit ONLY these keys. Any forbidden key (raw prompt
# text, tool input/output bodies, sub-agent persona/skill/task content,
# error messages with payload context, stack traces with locals) is
# stripped by scrub_audit_tokens_event() and a key-dropped breadcrumb
# is emitted. Defense-in-depth on top of audit-tokens.py CLI flag.
_AUDIT_TOKENS_ALLOWLIST = frozenset({
    # Required by emit_audit_tokens_emitted (always present)
    "action",
    "session_id",
    "timestamp",
    "window_seconds",
    "events_scanned",
    "tokens_in_total",
    "tokens_out_total",
    "cost_cents",
    "tier_id_distribution",
    "detector_findings_count",
    "hook_duration_ms",
    # _write_event metadata (added by base emitter; pre-allowed so
    # scrub doesn't strip them on round-trip)
    "ts",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "project",
})


# PLAN-125 WS-1 — Sec MF-3 field allowlist for tool_call_lifecycle_recorded.
# Deny-by-default. The 4 payload fields + the base-envelope keys that
# _write_event adds back (pre-allowed so the scrub does not strip them on a
# round-trip). Anything else (a raw mcp__* tool name, a raw duration_ms, a
# prompt/command/path body) is DROPPED before the wire (MF-SEC-1/3).
_TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tool_name_enum", "duration_bucket", "success", "orphan",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-124 WS-1 — Sec MF-3 field allowlist for git_hook_bypass_blocked.
# Deny-by-default. The ONLY caller-supplied payload field is `flag_class`
# (a closed enum token, MF-G); everything else is the standard signed
# envelope that _write_event adds back (pre-allowed so the scrub does not
# strip them on a round-trip). The matched command bytes are NEVER an
# allowed field, so a malicious flag value (e.g. a smuggled Bearer token)
# can never reach the wire.
_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "flag_class",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-124 WS-1 — closed flag_class enum (MF-G). MUST mirror
# _lib/git_bypass.py GIT_BYPASS_FLAG_CLASSES. Kept as a literal frozenset here
# (NOT imported from git_bypass) so audit_emit has zero import-time dependency
# on the hook-side tokenizer; a drift between the two sets is caught by a
# dedicated test (the two frozensets MUST be equal). A value outside this set
# is COERCED to "parse_failure" before emit (defense-in-depth) so a smuggled
# raw token can never reach the signed chain.
_GIT_HOOK_BYPASS_FLAG_CLASSES = frozenset({
    "no_verify_commit", "no_verify_other_subcmd", "hookspath_inline",
    "hookspath_config_write", "git_config_env_channel", "git_dir_redirect",
    "alias_abuse", "parse_failure", "escape_hatch_used",
})


# PLAN-133 A1 — Sec field allowlist for env_var_hijack_blocked. Deny-by-default.
# The ONLY caller-supplied payload field is `hijack_class` (closed enum); the var
# NAME and the assigned VALUE are NEVER allowed fields, so a smuggled path/secret
# can never reach the wire.
_ENV_VAR_HIJACK_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "hijack_class",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-133 A1 — closed hijack_class enum. MUST mirror
# _lib/env_guard.ENV_VAR_HIJACK_CLASSES. Kept as a literal frozenset here (NOT
# imported from env_guard) so audit_emit has zero import-time dependency on the
# hook-side scanner; a drift between the two is caught by a dedicated test (the
# two frozensets MUST be equal). A value outside this set is COERCED to
# "parse_failure" before emit (defense-in-depth).
_ENV_VAR_HIJACK_CLASSES = frozenset({
    "linker_preload", "linker_path", "runtime_hook",
    "linker_other", "parse_failure",
})


# PLAN-133 A3 — Sec field allowlist for egress_destination_detected. Deny-by-
# default. The ONLY caller-supplied payload fields are `egress_class` (closed
# enum) + `destination` (BARE HOST). The full URL, path, query, and any inline
# credential are NEVER allowed fields — a smuggled `command`/`url`/`full_url`
# body is dropped before the wire.
_EGRESS_DESTINATION_DETECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "egress_class", "destination",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-133 A3 — closed egress_class enum. MUST mirror
# _lib/egress_taxonomy.EGRESS_CLASSES. Kept as a literal frozenset here (NOT
# imported from egress_taxonomy) so audit_emit has zero import-time dependency on
# the hook-side classifier; a drift between the two is caught by a dedicated test
# (the two frozensets MUST be equal). A value outside this set is COERCED to
# "unknown" before emit (defense-in-depth).
_EGRESS_CLASSES = frozenset({
    "network_http", "ssh_remote", "cloud_store", "container_push",
    "package_publish", "raw_socket", "pair_rail", "unknown",
})

# PLAN-133 A3 — defensive host-only re-truncation of a persisted destination.
# Drops scheme/userinfo/port/path/query so even a direct emit_generic caller that
# passes a full URL in `destination` cannot leak a path/query/credential.
_EGRESS_DEST_MAX_LEN = 253


def _coerce_egress_destination(dest: Any) -> str:
    """Reduce a destination to a bare host string (no scheme/path/query/cred).

    Mirrors egress_taxonomy._host_only's contract but is self-contained (no import
    dependency). Non-str -> "". Pure; never raises.
    """
    if not isinstance(dest, str) or not dest:
        return ""
    s = dest.strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    for sep in ("/", "?", "#"):
        idx = s.find(sep)
        if idx != -1:
            s = s[:idx]
    if "@" in s:
        s = s.rsplit("@", 1)[1]
    if s.startswith("["):
        end = s.find("]")
        if end != -1:
            s = s[: end + 1]
    elif ":" in s:
        s = s.split(":", 1)[0]
    return s[:_EGRESS_DEST_MAX_LEN]


# PLAN-133 E1 — Sec field allowlist for adversary_review_flagged. Deny-by-default.
# Caller-supplied: `decision` (closed enum), `rule_class` (closed enum), `rule_id`
# (author-controlled config token — carries no command bytes). The matched command
# text / matched substring / rule `match`|`regex` source are NEVER allowed fields.
_ADVERSARY_REVIEW_FLAGGED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "decision", "rule_class", "rule_id",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-133 E1 — closed enums. MUST mirror _lib/adversary_rules.ADVERSARY_DECISIONS
# and .RULE_CLASSES. Kept literal here (NOT imported from adversary_rules) so
# audit_emit has zero import-time dependency on the hook-side engine; a drift
# between the two is caught by a dedicated test (the frozensets MUST be equal).
# A value outside the set is COERCED to "advisory"/"other" before emit.
_ADVERSARY_DECISIONS = frozenset({"deny", "ask", "advisory", "allow"})
_ADVERSARY_RULE_CLASSES = frozenset(
    {"destructive", "exfiltration", "privilege", "tampering", "other"}
)


# PLAN-133 G1 — Sec field allowlist for persistent_instructions_blocked.
# Deny-by-default. Caller-supplied: `reason` (closed enum) + `family_hits` /
# `bytes_scanned` (integers). The instruction-file body / matched line / resolved
# path / any env value are NEVER allowed fields (no-value-echo).
_PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "family_hits", "bytes_scanned",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-133 G1 — closed enum. MUST mirror
# _lib/guardrail_validator.VERDICT_REASONS. Kept literal here (NOT imported) so
# audit_emit has zero import-time dependency on the hook-side engine; a drift is
# caught by the parity test (§9). A value outside the set is COERCED to "other".
_PERSISTENT_INSTRUCTIONS_REASONS = frozenset(
    {"ok", "injection_pattern", "oversize", "outside_project_dir", "other"}
)


# PLAN-133 G3 — Sec field allowlist for hint_provenance_recorded.
# Deny-by-default. Caller-supplied: `reason` (closed enum) + `rel_dir_depth` /
# `family_hits` / `bytes_scanned` (integers). The hint-file body / matched line /
# the path text (absolute OR relative) are NEVER allowed fields (no-value-echo;
# only the integer DEPTH below the repo root is persisted).
_HINT_PROVENANCE_RECORDED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "reason", "rel_dir_depth", "family_hits", "bytes_scanned",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-133 G3 — closed enum. MUST mirror
# _lib/guardrail_validator.HINT_PROVENANCE_REASONS. Kept literal here (NOT
# imported) so audit_emit has zero import-time dependency on the hook-side
# engine; a drift is caught by the parity test (§9). A value outside the set is
# COERCED to "other".
_HINT_PROVENANCE_REASONS = frozenset(
    {"loaded", "blocked_injection", "blocked_oversize", "read_error", "other"}
)


# PLAN-135 W1 S3 — Sec field allowlist for settings_tamper_detected.
# Deny-by-default. Caller-supplied: `tamper_class` (closed enum), `layer`
# (closed enum) + `finding_count` (int, clamped 0..99 caller-side and
# re-clamped here). The tamper finding DETAIL string is NEVER an allowed
# field — it can carry an attacker endpoint URL, an off-allowlist model id,
# an apiKeyHelper path or a dangerously-flag value
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
# ANTHROPIC_AUTH_TOKEN values never reach even the producer (redacted at
# the effective_config classification layer); this allowlist is the second
# fence.
_SETTINGS_TAMPER_DETECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tamper_class", "layer", "finding_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-135 W1 S3 — closed enums. MUST mirror
# _lib/effective_config.TAMPER_CLASSES and the layer names
# (LAYER_MERGE_ORDER + LAYER_ENV + LAYER_DISK). Kept literal here (NOT
# imported) so audit_emit has zero import-time dependency on the resolver;
# a drift is caught by the staged parity test
# (test_ceo_boot_tamper_tripwires.py §enum-parity). Values outside the
# sets are COERCED to the safe sentinel "other" (S172 doctrine — the
# rejected value is never echoed).
_SETTINGS_TAMPER_CLASSES = frozenset({
    "settings_tamper_disable_all_hooks",
    "settings_tamper_model_remap",
    "settings_tamper_endpoint_remap",
    "settings_tamper_permission_bypass",
    "settings_tamper_hook_count_mismatch",
    # PLAN-135-FOLLOWUP (Codex R5 P1-3) — settings-layer CEO_STATUSLINE_SIDECAR
    # write-path steer (output/exfil-path class, NOT endpoint_remap). MUST mirror
    # _lib/effective_config.TAMPER_CLASSES (enum-parity test). A settings.json env
    # block steering the always-on statusline sidecar writer out of the state dir.
    "settings_tamper_sidecar_redirect",
    "other",
})
_SETTINGS_TAMPER_LAYERS = frozenset({
    "user", "project", "local", "managed", "env", "disk", "other",
})


# PLAN-135 W2 H2 — Sec field allowlists for the ConfigChange-guard pair
# (config_change_observed / config_change_forbidden_key, producer
# .claude/hooks/check_config_change.py). Deny-by-default. Same no-value-echo
# contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# changed file's path text and body, the forbidden key's VALUE (endpoint
# URL / model id / apiKeyHelper path / dangerously-flag value) and the
# effective_config finding DETAIL string are NEVER allowed fields.
_CONFIG_CHANGE_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "layer",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})
_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "tamper_class", "layer", "finding_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-135 W2 H2 — closed layer enum for the ConfigChange pair. SUBSET of
# _SETTINGS_TAMPER_LAYERS minus {env, disk}: H2 polices the SETTINGS file
# surfaces only (a ConfigChange event is a file change); process-env tamper
# is S3's surface and the disk hook-census is state, not a key change —
# census findings are deliberately observe-only in check_config_change.py
# (never blocked on). `tamper_class` reuses _SETTINGS_TAMPER_CLASSES (same
# effective_config closed enum, same coercion sentinel).
_CONFIG_CHANGE_LAYERS = frozenset({
    "user", "project", "local", "managed", "other",
})


# PLAN-135 W2 H1 (ADR-153) — Sec field allowlists for the
# compaction-continuity pair (compaction_continuity_snapshot /
# compaction_context_reinjected, producers
# .claude/hooks/check_precompact_continuity.py /
# check_postcompact_reinject.py). Deny-by-default. Same no-value-echo
# contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# snapshot BODY (plan path text, checkbox position, ceremony flags,
# last-hmac hex prefix) and the reinjected additionalContext TEXT are
# NEVER allowed fields — the snapshot lives in the plan-scoped scratchpad,
# the audit wire carries closed enums + counters only.
_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "trigger", "plan_id", "chain_length", "snapshot_outcome",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})
_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "plan_id", "snapshot_found", "snapshot_age_s", "pointer_count",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-135 W2 H1 — closed enums for the compaction pair. `trigger` mirrors
# the documented PreCompact hook-input values (manual = /compact, auto =
# context-window threshold); anything else (incl. a missing field on a
# future harness change) is COERCED to "other" (S172 doctrine — the
# rejected value is never echoed). `snapshot_outcome` is the producer's
# own closed result enum.
_COMPACTION_TRIGGERS = frozenset({"manual", "auto", "other"})
_COMPACTION_SNAPSHOT_OUTCOMES = frozenset({
    "written", "scratchpad_unavailable", "error", "other",
})


def _compaction_plan_id_ok(value: Any) -> bool:
    """Strict PLAN-NNN shape check for compaction-pair plan_id fields.

    PLAN-SCHEMA §1 naming: exactly ``PLAN-`` + 3 digits (zero-padded,
    8 chars total). Anything else — including path-traversal attempts
    smuggled through a spoofed plan_transition audit event — is rejected
    and the caller coerces to the safe sentinel ``"unknown"``. Kept as a
    plain string check (no regex) to preserve audit_emit's import
    surface.
    """
    if not isinstance(value, str) or len(value) != 8:
        return False
    return value.startswith("PLAN-") and value[5:].isdigit()


# PLAN-135 W2 H5 (ADR-154) — Sec field allowlist for the bash-input-rewrite
# breadcrumb (bash_input_rewritten, producer .claude/hooks/check_bash_safety.py).
# Deny-by-default. Same no-value-echo contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# command STRING (before OR after the rewrite), the remote URL / refspec and
# any inline credential are NEVER allowed fields — only the closed-enum
# rewrite_class + the two 64-hex sha256 hashes travel on the wire. The hash
# pair lets an auditor prove audited-cmd == executed-cmd without seeing either.
_BASH_INPUT_REWRITTEN_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "rewrite_class", "before_sha256", "after_sha256",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-135 W2 H5 — closed enum for the rewrite class. The pilot ships EXACTLY
# one rewrite pattern; widening requires a new ADR + Codex (Doctrine 1
# corollary + ADR-154 §1 single-rewriter invariant). Anything outside the set
# (incl. a missing field) is COERCED to "other" (S172 doctrine — the rejected
# value is never echoed).
_BASH_REWRITE_CLASSES = frozenset({
    "git_push_force_to_lease",
    "other",
})


def _is_sha256_hex(value: Any) -> bool:
    """True iff ``value`` is a 64-char lowercase-hex sha256 digest.

    Defensive validator for the before/after hash pair (ADR-154 §2): a
    non-string, wrong-length, or non-hex value is rejected and the caller
    coerces it to "" (never echoed). Kept as a plain check (no regex) to
    preserve audit_emit's import surface.
    """
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


# PLAN-135 W2 H3 — Sec field allowlist for the per-agent SubagentStop lifecycle
# bracket (subagent_lifecycle_observed, producer
# .claude/hooks/check_fluency_nudge.py H3 extension). Deny-by-default. Same
# no-value-echo contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# transcript path/body, the RAW token counts, the RAW wall-time seconds, the
# raw agent_id and the confidence-marker snippets are NEVER allowed fields —
# only the closed-enum archetype + the four coarse brackets travel on the wire.
# The bracket IS the audit signal; the raw counts stay forensic-private (the
# S227 modelUsage reconstruction lives at bucket granularity here).
_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "agent_archetype", "wall_bucket", "wall_source",
    "token_bucket", "claim_bucket",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})

# PLAN-135 W2 H3 — closed enum for the persona archetype that feeds the
# persona-ledger. Mirrors _PERSONA_COVERAGE_ARCHETYPES (the 4 VETO-floor
# personas, PLAN-093 Wave C.5) + "other" for any non-matching spawn type +
# "unknown" when the SubagentStart sidecar never recorded an agent_type.
# Anything outside the set (incl. a free-text spawn label or a missing field)
# is COERCED to "other" (S172 doctrine — the rejected value is never echoed,
# so a spawn description smuggled into agent_type cannot reach the wire).
_SUBAGENT_LIFECYCLE_ARCHETYPES = frozenset({
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer", "other", "unknown",
})

# PLAN-135 W2 H3 — closed enum for wall_source: was the SubagentStart instant
# recorded (so wall-time is a true bracket) or did the start go unobserved
# (orphaned start / kill-switch / crashed agent → bracket is "unknown")?
_SUBAGENT_LIFECYCLE_WALL_SOURCES = frozenset({
    "bracketed", "unknown",
})

# PLAN-135 W2 H3 — shared closed-enum bucket vocabulary for wall_bucket,
# token_bucket and claim_bucket. Coarse, monotonic, never a raw count. The
# bucketing function lives producer-side (check_fluency_nudge.py); audit_emit
# only validates the resulting token against this closed set (defense-in-depth
# on the direct emit_generic-caller path). "unknown" is the fail-closed
# sentinel for an unmeasured / unparseable dimension.
_SUBAGENT_LIFECYCLE_BUCKETS = frozenset({
    "none", "low", "medium", "high", "very_high", "unknown",
})


def scrub_audit_tokens_event(
    event: Dict[str, Any],
    *,
    allowlist: Optional[frozenset] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Filter an audit-tokens event dict to allowlisted keys only.

    Returns ``(cleaned_event, dropped_keys)``. Dropped keys are
    typically forbidden (raw text, payload bodies). Caller should
    emit ``audit_tokens_key_dropped`` breadcrumb if dropped is
    non-empty (defense-in-depth on allowlist drift).

    Pure function — no side effects. Never raises.

    Per SEC-P0-04 spec §Hook integration, this is called by
    emit_audit_tokens_emitted before _write_event. Belt-and-braces
    on top of audit-tokens.py CLI flag (--content-ban=strict).
    """
    if allowlist is None:
        allowlist = _AUDIT_TOKENS_ALLOWLIST
    if not isinstance(event, dict):
        return ({}, [])
    cleaned: Dict[str, Any] = {}
    dropped: List[str] = []
    for key, value in event.items():
        if key in allowlist:
            cleaned[key] = value
        else:
            dropped.append(key)
    return (cleaned, dropped)


def emit_audit_tokens_emitted(
    *,
    session_id: str,
    window_seconds: int,
    events_scanned: int,
    tokens_in_total: int,
    tokens_out_total: int,
    cost_cents: int,
    tier_id_distribution: Optional[Dict[str, int]] = None,
    detector_findings_count: Optional[Dict[str, int]] = None,
    hook_duration_ms: int = 0,
    timestamp: str = "",
    project: str = "",
) -> None:
    """Emit audit_tokens_emitted (SEC-P0-04 / ADR-080).

    Builds a counts-only event from audit-tokens.py stub output.
    Applies scrub_audit_tokens_event() defense-in-depth before write.
    If forbidden keys are stripped, also emits
    audit_tokens_key_dropped breadcrumb.

    Total event payload is bounded: per SEC-P0-04 spec §Acceptance
    test 8, serialized JSON < 2 KiB. The 12-key allowlist + integer/
    short-string values keep this well under cap.
    """
    raw_event: Dict[str, Any] = {
        "action": "audit_tokens_emitted",
        "session_id": session_id,
        "timestamp": timestamp or _utc_now_iso(),
        "window_seconds": int(window_seconds),
        "events_scanned": int(events_scanned),
        "tokens_in_total": int(tokens_in_total),
        "tokens_out_total": int(tokens_out_total),
        "cost_cents": int(cost_cents),
        "tier_id_distribution": dict(tier_id_distribution or {}),
        "detector_findings_count": dict(detector_findings_count or {}),
        "hook_duration_ms": int(hook_duration_ms),
        "project": project,
    }
    cleaned, dropped = scrub_audit_tokens_event(raw_event)
    _write_event(cleaned)
    # Defense-in-depth: if any keys were stripped, breadcrumb so a
    # post-flight scan or CI gate can detect allowlist drift.
    if dropped:
        emit_audit_tokens_key_dropped(
            session_id=session_id,
            dropped_keys=dropped,
            project=project,
        )


def emit_audit_tokens_timeout(
    *,
    session_id: str,
    timeout_seconds: float,
    project: str = "",
) -> None:
    """Emit audit_tokens_timeout (SEC-P0-04 §Performance budget).

    Fired when audit-tokens.py subprocess invocation exceeds
    ``timeout_seconds`` (default per SEC-P0-04: 0.05 = 50ms wall).
    Replaces the audit_tokens_emitted that would have been emitted
    on success — SessionEnd hook should not block on slow detectors.

    ``timeout_ms`` is integer milliseconds. canonical_json forbids floats
    in HMAC-covered fields; the old ``timeout_seconds`` float caused
    CanonicalJsonError + dropped events. Caller passes a float seconds
    value (backward-compatible); we convert to int ms here.
    """
    event: Dict[str, Any] = {
        "action": "audit_tokens_timeout",
        "session_id": session_id,
        "timeout_ms": max(0, int(round(timeout_seconds * 1000))),
        "project": project,
    }
    _write_event(event)


def emit_audit_tokens_key_dropped(
    *,
    session_id: str,
    dropped_keys: List[str],
    project: str = "",
) -> None:
    """Emit audit_tokens_key_dropped breadcrumb (SEC-P0-04 defense-in-depth).

    Fired by scrub_audit_tokens_event() when forbidden keys are
    stripped from an audit-tokens event. Indicates either:

    1. A code change introduced a new key without updating
       _AUDIT_TOKENS_ALLOWLIST (likely benign — drift signal).
    2. An attacker / misconfigured code injected forbidden content
       into audit-tokens output (real signal — investigate).

    Either way, post-flight scan can grep for these breadcrumbs to
    catch drift OR alert on attack. Event itself does NOT include
    the dropped values, only the keys (so even hostile keys with
    payload-like names don't leak content).
    """
    # Bound dropped_keys list size to prevent pathological emit cost
    # if every key in a misconfigured event was forbidden.
    keys_preview = list(dropped_keys)[:50]
    event: Dict[str, Any] = {
        "action": "audit_tokens_key_dropped",
        "session_id": session_id,
        "dropped_keys": keys_preview,
        "dropped_count": len(dropped_keys),
        "project": project,
    }






    _write_event(event)


# ---------------------------------------------------------------------
# PLAN-052 Phase 1 / ADR-083 — MCP injection scanner advisory finding
# Wired by PLAN-044 audit-v2 Wave B (C1-P0-03).
# ---------------------------------------------------------------------


def emit_mcp_injection_finding(
    *,
    server_id: str,
    mcp_tool_name: str,
    source_kind: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    severity: str,
    snippet_preview: str,
    scanner_action: str = "advisory",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `mcp_injection_finding` event from check_mcp_response.py.

    Schema mirrors `output_scan_finding` (ADR-057) with MCP-specific
    fields. Per SPEC/v1/audit-log.schema.md v2.13, fields are:

      - server_id: MCP server identifier (parsed from `mcp__<server>__<tool>`)
      - mcp_tool_name: tool name within the server
      - source_kind: which MCP surface triggered the scan
        (`tool_result` | `instructions` | `resource_fetch`)
      - family_counts: per-injection-family hit counts
        (harness_mimicry, role_preamble, directive_prose, synthetic_tool_call)
      - match_count: total individual pattern matches across families
      - bytes_scanned: total bytes the scanner inspected (for budget tracking)
      - severity: `low` | `medium` | `high` (per `_lib/mcp_injection_scan.py`
        `_SEVERITY_BY_FAMILY`; SPEC v1 audit-log.schema.md aligned). Session 75
        Codex Finding 6 closure: prior docstring `info|warn|block` was schema
        drift — never matched `classify()` returns.
      - snippet_preview: redacted ≤120-char preview of the offending text
      - scanner_action: `advisory` | `stripped` | `blocked` (per SPEC v1
        audit-log.schema.md). Session 75 Codex Finding 6 closure: prior
        docstring `block` was verb-form drift; SPEC declares state-form
        `blocked`. `stripped` is reserved for Phase 2 sanitization.

    Called from check_mcp_response.py:148 only when
    finding.matched. The hook is fail-open by contract — emission failures
    are swallowed by the caller's try/except.

    PLAN-044 audit-v2 C1-P0-03 closes 5 cross-validating findings
    (dim 04, 06, 07, 16, 18) by removing the `hasattr` guard in the
    hook AND registering the action here so emit_generic doesn't
    short-circuit.
    """
    emit_generic(
        "mcp_injection_finding",
        session_id=session_id,
        server_id=server_id,
        mcp_tool_name=mcp_tool_name,
        source_kind=source_kind,
        family_counts=dict(family_counts or {}),
        match_count=int(match_count),
        bytes_scanned=int(bytes_scanned),
        severity=severity,
        snippet_preview=snippet_preview[:120] if snippet_preview else "",
        scanner_action=scanner_action,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-065 Phase 2 / ADR-098 — /ceo-boot lifecycle emitters.
# Sec MF-3 field allowlist enforced (deny-by-default). Forbidden fields
# (tokens / cost / paths / prompt / SKILL / env) are stripped before emit
# and a breadcrumb is written to audit-log.errors (NOT a typed audit
# event — drift signal only, mirrors the audit-tokens `_key_dropped`
# defense-in-depth pattern but kept off the typed stream until v1.13.0
# PLAN-067 if needed).
# ---------------------------------------------------------------------


def _scrub_ceo_boot_event(
    event: Dict[str, Any],
    allowlist: frozenset,
) -> Tuple[Dict[str, Any], List[str]]:
    """Strip any field outside ``allowlist``. Returns (cleaned, dropped_keys).

    Pure function. No I/O. Caller decides whether to breadcrumb the drop.
    Forbidden fields are NEVER returned in cleaned dict — this is the
    Sec MF-3 enforcement boundary. Drift = drop = visible.
    """
    cleaned: Dict[str, Any] = {}
    dropped: List[str] = []
    for k, v in event.items():
        if k in allowlist:
            cleaned[k] = v
        else:
            dropped.append(k)
    return cleaned, dropped


def emit_ceo_boot_emitted(
    *,
    session_id: str,
    gate_pass: bool,
    duration_ms: int,
    checks_total: int,
    checks_failed: int,
    cache_hit: bool = False,
    project: str = "",
) -> None:
    """Emit ceo_boot_emitted (PLAN-065 Phase 2 / ADR-098).

    Fired once per /ceo-boot invocation at end-of-run (cached + uncached).
    Field allowlist enforced (Sec MF-3): no token counts, no cost, no
    paths, no prompt content, no SKILL.md content, no environment values.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. Caller (ceo-boot.py) MUST also wrap in a broad except
    so that a slow audit-log filelock NEVER blocks the user session.
    """
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_emitted",
        "session_id": session_id,
        "project": project,
        "gate_pass": bool(gate_pass),
        "duration_ms": int(duration_ms),
        "checks_total": int(checks_total),
        "checks_failed": int(checks_failed),
        "cache_hit": bool(cache_hit),
    }
    cleaned, dropped = _scrub_ceo_boot_event(raw_event, _CEO_BOOT_EMITTED_ALLOWLIST)
    _write_event(cleaned)
    if dropped:  # pragma: no cover — should be impossible from the typed wrapper
        _breadcrumb(
            f"ceo_boot_emitted dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


# PLAN-125 WS-1 (kooky-harvest) — closed-enum validation sets for the
# tool_call_lifecycle_recorded typed emitter. Kept local to the emitter so the
# enum domain is enforced at the typed entrypoint AND re-checked here even if a
# caller hand-builds the field values (defense-in-depth; the mapper in
# _lib/tool_lifecycle.py is the canonical producer).
_TOOL_CALL_LIFECYCLE_DURATION_BUCKETS = frozenset({
    "lt_100ms", "b_100ms_1s", "b_1_10s", "b_10_60s", "gt_60s",
})
# Recognized standard tool names + the two synthetic buckets the mapper
# produces. A value outside this set is coerced to "other" before emit so a
# raw mcp__<server>__<tool> string can NEVER reach the wire (MF-SEC-1), even on
# a direct typed-emitter call that bypassed the mapper.
_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM = frozenset({
    "Agent", "Task", "Bash", "Edit", "MultiEdit", "Write", "Read",
    "Glob", "Grep", "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite",
    "mcp_other", "other",
})


def emit_tool_call_lifecycle_recorded(
    *,
    session_id: str,
    tool_name_enum: str,
    duration_bucket: str,
    success: bool,
    orphan: bool,
    project: str = "",
) -> None:
    """Emit tool_call_lifecycle_recorded (PLAN-125 WS-1 / kooky-harvest).

    Fired once per paired PostToolUse / PostToolUseFailure completion (and by
    the bounded orphan sweeper). Deny-by-default field allowlist enforced
    (Sec MF-SEC-1/2/3): NO raw tool name, NO raw duration_ms, NO body fields.

    The two closed enums are re-validated here (defense-in-depth): an
    unrecognized ``tool_name_enum`` is coerced to ``"other"`` and an
    unrecognized ``duration_bucket`` to ``"lt_100ms"`` so a smuggled raw value
    can never reach the wire even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. The lifecycle producer (`_lib/tool_lifecycle.py`) also wraps
    this in a broad except so a slow filelock NEVER blocks the tool (MF-SEC-5).
    """
    safe_tool_name = (
        tool_name_enum
        if tool_name_enum in _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM
        else "other"
    )
    safe_bucket = (
        duration_bucket
        if duration_bucket in _TOOL_CALL_LIFECYCLE_DURATION_BUCKETS
        else "lt_100ms"
    )
    raw_event: Dict[str, Any] = {
        "action": "tool_call_lifecycle_recorded",
        "session_id": session_id,
        "project": project,
        "tool_name_enum": safe_tool_name,
        "duration_bucket": safe_bucket,
        "success": bool(success),
        "orphan": bool(orphan),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"tool_call_lifecycle_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_git_hook_bypass_blocked(
    *,
    flag_class: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit git_hook_bypass_blocked (PLAN-124 WS-1 / ECC value-harvest).

    Fired by `check_bash_safety.py` when the git hook-bypass tokenizer
    (`_lib/git_bypass.py`) blocks a `--no-verify` / `core.hooksPath` /
    env-channel / alias / redirect bypass, AND when the audited dual-auth
    escape hatch (CEO_GIT_BYPASS_ALLOW) is used to ALLOW one
    (flag_class=`escape_hatch_used`).

    Deny-by-default field allowlist enforced (MF-G): the ONLY caller-supplied
    field is `flag_class`, a CLOSED enum token. The matched command bytes are
    NEVER persisted (a flag value like `-c http.extraHeader="Bearer <secret>"`
    is a secret). An unrecognized `flag_class` is COERCED to `"parse_failure"`
    here (defense-in-depth) so a smuggled raw value can never reach the wire,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event. NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_flag_class = (
        flag_class
        if flag_class in _GIT_HOOK_BYPASS_FLAG_CLASSES
        else "parse_failure"
    )
    raw_event: Dict[str, Any] = {
        "action": "git_hook_bypass_blocked",
        "session_id": session_id,
        "project": project,
        "flag_class": safe_flag_class,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"git_hook_bypass_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_bash_input_rewritten(
    *,
    rewrite_class: str,
    before_sha256: str,
    after_sha256: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit bash_input_rewritten (PLAN-135 W2 H5 / ADR-154 single-rewriter).

    Fired by `check_bash_safety.py` when the PreToolUse Bash rail REWRITES a
    `git push --force`/`-f` command to `--force-with-lease` via the
    `updatedInput` channel (surfaced to the user as an `ask`, never a silent
    allow). Records the before/after sha256 hash PAIR so an auditor can prove
    the audited command equals the executed command (ADR-154 §2).

    Deny-by-default field allowlist enforced: the ONLY caller-supplied fields
    are `rewrite_class` (a CLOSED enum token, coerced to "other" here as
    defense-in-depth) + the two 64-hex sha256 hashes (validated, else "").
    The command BYTES (before OR after) are NEVER persisted — a force-push
    line can carry a remote URL with an inline token. NEVER routes through
    _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event.
    """
    safe_class = (
        rewrite_class if rewrite_class in _BASH_REWRITE_CLASSES else "other"
    )
    safe_before = before_sha256 if _is_sha256_hex(before_sha256) else ""
    safe_after = after_sha256 if _is_sha256_hex(after_sha256) else ""
    raw_event: Dict[str, Any] = {
        "action": "bash_input_rewritten",
        "session_id": session_id,
        "project": project,
        "rewrite_class": safe_class,
        "before_sha256": safe_before,
        "after_sha256": safe_after,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _BASH_INPUT_REWRITTEN_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"bash_input_rewritten dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_subagent_lifecycle_observed(
    *,
    agent_archetype: str,
    wall_bucket: str,
    wall_source: str,
    token_bucket: str,
    claim_bucket: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit subagent_lifecycle_observed (PLAN-135 W2 H3 / per-agent bracket).

    Fired ONCE per returning sub-agent by `check_fluency_nudge.py` (the
    SubagentStop H3 extension) after it consumes the SubagentStart sidecar
    written by `check_subagent_start.py` + the harness-supplied
    `agent_transcript_path`. Turns the S227 `modelUsage` forensic
    reconstruction into a live hook emit and feeds the persona-ledger
    (PLAN-104) via `agent_archetype`, alongside `agent_spawn`.

    Deny-by-default field allowlist enforced (Sec MF-3): EVERY caller-supplied
    field is a CLOSED enum or coarse BUCKET, each coerced here as
    defense-in-depth. The RAW wall-time seconds, the RAW token counts, the
    transcript path/body, the raw agent_id and the confidence-marker snippets
    are NEVER persisted — only the closed-enum archetype + the four brackets
    travel (the bracket is the audit signal; the raw counts stay forensic-
    private). NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open per audit_emit contract — exceptions are swallowed by
    _write_event.
    """
    safe_archetype = (
        agent_archetype
        if agent_archetype in _SUBAGENT_LIFECYCLE_ARCHETYPES
        else "other"
    )
    safe_wall_source = (
        wall_source
        if wall_source in _SUBAGENT_LIFECYCLE_WALL_SOURCES
        else "unknown"
    )
    safe_wall_bucket = (
        wall_bucket if wall_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    safe_token_bucket = (
        token_bucket if token_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    safe_claim_bucket = (
        claim_bucket if claim_bucket in _SUBAGENT_LIFECYCLE_BUCKETS else "unknown"
    )
    raw_event: Dict[str, Any] = {
        "action": "subagent_lifecycle_observed",
        "session_id": session_id,
        "project": project,
        "agent_archetype": safe_archetype,
        "wall_bucket": safe_wall_bucket,
        "wall_source": safe_wall_source,
        "token_bucket": safe_token_bucket,
        "claim_bucket": safe_claim_bucket,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"subagent_lifecycle_observed dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_env_var_hijack_blocked(
    *,
    hijack_class: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit env_var_hijack_blocked (PLAN-133 A1 / Goose-harvest).

    Fired by `check_bash_safety.py` when `_lib/env_guard.scan_command` detects a
    Bash command that SETS a denylisted linker/loader/runtime-hijack environment
    variable (LD_PRELOAD / DYLD_INSERT_LIBRARIES / PYTHONSTARTUP / NODE_OPTIONS /
    BASH_ENV / …). Emitted on BOTH an enforced block (CEO_ENV_GUARD_ENFORCE=1) AND
    an advisory default-OFF detection.

    Deny-by-default field allowlist enforced: the ONLY caller-supplied field is
    `hijack_class`, a CLOSED enum token. The variable NAME and the assigned VALUE
    are NEVER persisted (the value is a preload-payload path or a smuggled secret).
    An unrecognized `hijack_class` is COERCED to `"parse_failure"` here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_class = (
        hijack_class
        if hijack_class in _ENV_VAR_HIJACK_CLASSES
        else "parse_failure"
    )
    raw_event: Dict[str, Any] = {
        "action": "env_var_hijack_blocked",
        "session_id": session_id,
        "project": project,
        "hijack_class": safe_class,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"env_var_hijack_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_egress_destination_detected(
    *,
    egress_class: str,
    destination: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit egress_destination_detected (PLAN-133 A3 / Goose-harvest).

    Fired by `check_bash_safety.py` when `_lib/egress_taxonomy.classify_command`
    detects an outbound channel in a Bash command (curl/wget/scp/rsync/ssh/aws-s3/
    gsutil/docker-push/npm-publish/nc/socat/codex). ADVISORY — emitted (default-OFF
    behind CEO_EGRESS_TAXONOMY_EMIT) regardless of whether the command is also
    blocked by a higher-severity rule, so a destructive+egress compound still
    records the egress.

    Deny-by-default field allowlist enforced: the ONLY caller-supplied fields are
    `egress_class` (a CLOSED enum) + `destination` (a BARE HOST). The full URL,
    path, query, and any inline credential are NEVER persisted. An unrecognized
    `egress_class` is COERCED to "unknown" and `destination` is re-reduced to a
    bare host here (defense-in-depth) so even a direct caller cannot leak.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_class = (
        egress_class if egress_class in _EGRESS_CLASSES else "unknown"
    )
    raw_event: Dict[str, Any] = {
        "action": "egress_destination_detected",
        "session_id": session_id,
        "project": project,
        "egress_class": safe_class,
        "destination": _coerce_egress_destination(destination),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _EGRESS_DESTINATION_DETECTED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"egress_destination_detected dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_adversary_review_flagged(
    *,
    decision: str,
    rule_class: str,
    rule_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit adversary_review_flagged (PLAN-133 E1 / Goose-harvest).

    Fired by `check_adversary.py` when the local-rules engine
    (`_lib/adversary_rules.py`) flags a Bash command — on BOTH an enforced
    deny/ask (CEO_ADVERSARY=1) AND an advisory default-OFF detection — and on the
    secret-in-command fail-CLOSED path (E1 §4).

    Deny-by-default field allowlist enforced: caller-supplied fields are `decision`
    + `rule_class` (CLOSED enums) and `rule_id` (author-controlled config token).
    The matched COMMAND bytes, the matched substring, and the rule `match`/`regex`
    source are NEVER persisted (a command can carry a smuggled credential). An
    unrecognized `decision`/`rule_class` is COERCED to "advisory"/"other" here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_decision = decision if decision in _ADVERSARY_DECISIONS else "advisory"
    safe_class = rule_class if rule_class in _ADVERSARY_RULE_CLASSES else "other"
    raw_event: Dict[str, Any] = {
        "action": "adversary_review_flagged",
        "session_id": session_id,
        "project": project,
        "decision": safe_decision,
        "rule_class": safe_class,
        "rule_id": rule_id,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"adversary_review_flagged dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_persistent_instructions_blocked(
    *,
    reason: str,
    family_hits: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persistent_instructions_blocked (PLAN-133 G1 / Goose-harvest MOIM).

    Fired by `SessionStart.py` when the BLOCKING MOIM validator
    (`_lib/guardrail_validator.py`) returns ``decision="block"`` for the
    trusted-instructions file (injection pattern or oversize) and the session
    boot is refused.

    Deny-by-default field allowlist enforced: caller-supplied fields are
    `reason` (CLOSED enum) + `family_hits` / `bytes_scanned` (integers). The
    instruction-file BODY, the matched line, the matched substring, the resolved
    path, and any env value are NEVER persisted (the file is the exact injection
    vector PLAN-133 §2 flags). An unrecognized `reason` is COERCED to "other"
    here (defense-in-depth) so a smuggled raw value can never reach the signed
    chain, even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_reason = reason if reason in _PERSISTENT_INSTRUCTIONS_REASONS else "other"
    raw_event: Dict[str, Any] = {
        "action": "persistent_instructions_blocked",
        "session_id": session_id,
        "project": project,
        "reason": safe_reason,
        "family_hits": int(family_hits) if isinstance(family_hits, int) else 0,
        "bytes_scanned": int(bytes_scanned) if isinstance(bytes_scanned, int) else 0,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"persistent_instructions_blocked dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_hint_provenance_recorded(
    *,
    reason: str,
    rel_dir_depth: int = 0,
    family_hits: int = 0,
    bytes_scanned: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit hint_provenance_recorded (PLAN-133 G3 / Goose-harvest nested hints).

    Fired by `SessionStart.py` for each nested `.claude/hints.md` the BLOCKING
    validator (`_lib/guardrail_validator.py`) rejected (injection pattern or
    oversize) during the hierarchical discovery walk.

    Deny-by-default field allowlist enforced: caller-supplied fields are
    `reason` (CLOSED enum) + `rel_dir_depth` / `family_hits` / `bytes_scanned`
    (integers). The hint-file BODY, the matched line, the matched substring, and
    the PATH text (absolute OR relative dir name) are NEVER persisted — only the
    integer DEPTH below the repo root (so a poisoned dir NAME cannot itself be an
    exfil channel). An unrecognized `reason` is COERCED to "other" here
    (defense-in-depth) so a smuggled raw value can never reach the signed chain,
    even on a direct caller path.

    Fail-open per audit_emit contract — exceptions are swallowed by _write_event.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH
    ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    safe_reason = reason if reason in _HINT_PROVENANCE_REASONS else "other"
    raw_event: Dict[str, Any] = {
        "action": "hint_provenance_recorded",
        "session_id": session_id,
        "project": project,
        "reason": safe_reason,
        "rel_dir_depth": int(rel_dir_depth) if isinstance(rel_dir_depth, int) else 0,
        "family_hits": int(family_hits) if isinstance(family_hits, int) else 0,
        "bytes_scanned": int(bytes_scanned) if isinstance(bytes_scanned, int) else 0,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _HINT_PROVENANCE_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"hint_provenance_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_ceo_boot_persona_coverage_score(
    *,
    score_x100: int = 0,
    cells_covered: int = 0,
    total_cells: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """PLAN-093 Wave C.5 — emit 4×4 persona × task coverage score from /ceo-boot.

    Field allowlist (Sec MF-3): score_x100, cells_covered, total_cells,
    session_id, project. Scrub enforced both here AND in emit_generic
    dispatch branch (Codex S123 P1-2 closure).

    score_x100 is integer basis-points (7234 = 72.34%; 0-10000 range) —
    floats break canonical JSON HMAC chain (Codex S123 iter-2 P1).
    Fail-open per audit_emit contract — exceptions swallowed by _write_event.
    """
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_persona_coverage_score",
        "session_id": session_id,
        "project": project,
        "score_x100": int(score_x100),
        "cells_covered": int(cells_covered),
        "total_cells": int(total_cells),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover
        _breadcrumb(
            f"ceo_boot_persona_coverage_score dropped: {sorted(dropped)[:10]}"
        )


def emit_ceo_boot_check_skipped(
    *,
    session_id: str,
    check_name: str,
    timeout_ms: int,
    project: str = "",
) -> None:
    """Emit ceo_boot_check_skipped (PLAN-065 Phase 2 / ADR-098 / CR-MF6).

    Fired per timed-out Tier-S check inside the dispatcher. Required by
    Codex audit-v3 finding A precedent (silently dropped events block
    forensic reconstruction).

    Field allowlist enforced (Sec MF-3): no detail / no error message /
    no stack trace — only the check name + the timeout budget that was
    breached. Operator queries audit-log + correlates with ceo_boot_emitted
    `checks_failed` count for forensic reconstruction.

    `check_name` is length-bounded to 64 chars (defense-in-depth on caller
    drift; PLAN-065 registry pins 15 Tier-S + 10 Tier-A all <32 chars).
    """
    safe_name = (check_name or "")[:64]
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_check_skipped",
        "session_id": session_id,
        "project": project,
        "check_name": safe_name,
        "timeout_ms": int(timeout_ms),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CEO_BOOT_CHECK_SKIPPED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"ceo_boot_check_skipped dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


# ---------------------------------------------------------------------
# PLAN-078 Wave 1+2 — typed advisory emitters.
# Both share the `_scrub_ceo_boot_event` allowlist-agnostic helper.
# Caller-side fail-open is the responsibility of the call site (hook /
# detector); these wrappers themselves never raise, but if `_write_event`
# under their hood encounters an exception it breadcrumbs + returns.
# ---------------------------------------------------------------------


def _to_basis_points(value: Any, *, lo: int = 0, hi: int = 1_000_000) -> int:
    """Convert a float multiplier to integer basis-points (×1000), clamped.

    Codex W1+W2 fix-pack #2: HMAC chain requires int (canonical_json forbids
    floats). Multiplier 1.234 → 1234 bp. NaN/inf → 0. Negatives → 0.
    Clamped to [lo, hi] to bound on-disk size + downstream consumers.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return lo
    # Reject NaN / inf (canonical_json bans these too).
    if f != f or f in (float("inf"), float("-inf")):
        return lo
    bp = int(round(f * 1000.0))
    if bp < lo:
        return lo
    if bp > hi:
        return hi
    return bp


def emit_model_routing_advised(
    *,
    session_id: str = "",
    archetype: str = "",
    task_type: str = "",
    model_recommended: str = "",
    confidence_basis_points: int = 0,
    applied_or_skipped: str = "",
    override_reason: str = "",
    project: str = "",
) -> None:
    """Emit model_routing_advised (PLAN-078 Wave 1).

    Advisory-only telemetry from check_agent_spawn._emit_model_routing_advisory().
    Sec MF-3 field allowlist enforced — only the 6 caller fields + auto-baseline
    are persisted. Caller is responsible for length-bounding strings.

    Codex W1+W2 fix-pack #2: ``confidence_basis_points`` int 0..1000
    (was float ``confidence`` 0..1). canonical_json forbids floats in
    HMAC-covered fields; with float, _write_event would catch
    CanonicalJsonError and persist hmac=null, breaking the chain.
    Caller converts: ``bp = int(round(ratio * 1000))``.
    """
    sev_int_bp = int(confidence_basis_points)
    if sev_int_bp < 0:
        sev_int_bp = 0
    if sev_int_bp > 1000:
        sev_int_bp = 1000
    raw_event: Dict[str, Any] = {
        "action": "model_routing_advised",
        "session_id": session_id,
        "project": project,
        "archetype": (archetype or "")[:64],
        "task_type": (task_type or "")[:32],
        "model_recommended": (model_recommended or "")[:64],
        "confidence_basis_points": sev_int_bp,
        "applied_or_skipped": (applied_or_skipped or "")[:64],
        "override_reason": (override_reason or "")[:128],
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _MODEL_ROUTING_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"model_routing_advised dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_estimate_drift_detected(
    *,
    session_id: str = "",
    plan_id: str = "",
    drift_factor_compute_basis_points: int = 0,
    drift_factor_owner_basis_points: int = 0,
    severity: str = "low",
    plan_count_in_run: int = 0,
    systematic_bias_direction: str = "",
    project: str = "",
) -> None:
    """Emit estimate_drift_detected (PLAN-078 Wave 2 / Reality Ledger detector #7).

    Advisory event fired on plan close-out (`status:done` transition).
    Sec MF-3 field allowlist enforced. drift_factor values are integer
    basis-points (×1000) per Codex W1+W2 fix-pack #2 to preserve HMAC chain.
    severity is closed enum {low, medium, high}.

    Codex W1+W2 fix-pack #3: ``systematic_bias_direction`` enum extended
    with ``underestimate`` (overrun, factor>1.2) and ``overestimate``
    (underrun, factor<0.83) — bidirectional detection.
    """
    sev = severity if severity in ("low", "medium", "high") else "low"
    bias = systematic_bias_direction if systematic_bias_direction in (
        "", "underestimate", "overestimate"
    ) else ""
    bp_compute = int(drift_factor_compute_basis_points)
    if bp_compute < 0:
        bp_compute = 0
    bp_owner = int(drift_factor_owner_basis_points)
    if bp_owner < 0:
        bp_owner = 0
    raw_event: Dict[str, Any] = {
        "action": "estimate_drift_detected",
        "session_id": session_id,
        "project": project,
        "plan_id": (plan_id or "")[:32],
        "drift_factor_compute_basis_points": bp_compute,
        "drift_factor_owner_basis_points": bp_owner,
        "severity": sev,
        "plan_count_in_run": int(plan_count_in_run),
        "systematic_bias_direction": bias,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ESTIMATE_DRIFT_DETECTED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"estimate_drift_detected dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_estimate_drift_systematic_bias(
    *,
    session_id: str = "",
    bias_direction: str = "",
    plans_affected_count: int = 0,
    avg_drift_factor_compute_basis_points: int = 0,
    avg_drift_factor_owner_basis_points: int = 0,
    project: str = "",
) -> None:
    """Emit estimate_drift_systematic_bias (PLAN-078 Wave 2 follow-on).

    Fired when N>=5 drifts in same direction observed in a single
    detector run. bias_direction in {underestimate, overestimate}.

    Codex W1+W2 fix-pack #2: avg drift factors are int basis-points
    (×1000) to preserve HMAC chain (canonical_json no-floats invariant).
    """
    bias = bias_direction if bias_direction in (
        "underestimate", "overestimate"
    ) else "underestimate"
    bp_compute = int(avg_drift_factor_compute_basis_points)
    if bp_compute < 0:
        bp_compute = 0
    bp_owner = int(avg_drift_factor_owner_basis_points)
    if bp_owner < 0:
        bp_owner = 0
    raw_event: Dict[str, Any] = {
        "action": "estimate_drift_systematic_bias",
        "session_id": session_id,
        "project": project,
        "bias_direction": bias,
        "plans_affected_count": int(plans_affected_count),
        "avg_drift_factor_compute_basis_points": bp_compute,
        "avg_drift_factor_owner_basis_points": bp_owner,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"estimate_drift_systematic_bias dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_ceo_boot_task_candidate_emitted(
    *,
    session_id: str = "",
    rank: int = 0,
    severity: str = "",
    subject_hash: str = "",
    awaiting_confirm: bool = False,
    project: str = "",
) -> None:
    """Emit ceo_boot_task_candidate_emitted (PLAN-078 Wave 5).

    Fired by .claude/scripts/ceo-boot.py:_emit_task_candidate_safe per
    `<!-- TASKCREATE-CANDIDATE -->` marker block written to stdout when the
    boot run has gate_pass=False AND the recommendation severity is medium
    or higher. Top-3 candidates per invocation; dedup by `subject_hash` is
    enforced caller-side via a 24h TTL state file under `_lib/filelock`.

    Sec MF-3 field allowlist enforced (deny-by-default): NO subject text,
    NO recommendation body, NO check name/detail, NO env values, NO file
    paths. Only the 4 caller fields + the auto-baseline (action, ts,
    session_id, project, event_schema, tokens_*, hmac, hmac_error) added
    by `_write_event`.

    Args:
        session_id: forensic correlator (matches sibling `ceo_boot_emitted`).
        rank: 1-based ordinal of the candidate in the boot run (1..3).
            Clamped to [1, 3]; values outside the range fall back to 0
            (sentinel for "drift" — caller invariants are bound to top-3).
        severity: recommendation engine bucket ∈ {low, medium, high}.
            Unknown values become "" (defense-in-depth).
        subject_hash: 12-hex-char prefix of sha256(canonical subject text).
            The full subject is NEVER persisted (Sec MF-3); the hash is
            the only stable identifier shared between this event and the
            dedup state file. Length-bounded to 12 chars; non-hex chars
            stripped to keep the on-disk shape predictable.
        awaiting_confirm: bool reserved for a future "Owner-must-confirm"
            escape (default False — Claude orchestrator auto-creates the
            task in the v1.15.0 baseline). Persisted as a bool literal.
        project: optional ``$CLAUDE_PROJECT_DIR`` correlator for adopters.

    Fail-open per audit_emit contract — exceptions inside `_write_event`
    are swallowed; this wrapper itself never raises.
    """
    safe_rank = int(rank) if isinstance(rank, (int, bool)) else 0
    if safe_rank < 1 or safe_rank > 3:
        safe_rank = 0
    safe_severity = severity if severity in ("low", "medium", "high") else ""
    raw_hash = (subject_hash or "").lower()
    safe_hash = "".join(ch for ch in raw_hash if ch in "0123456789abcdef")[:12]
    raw_event: Dict[str, Any] = {
        "action": "ceo_boot_task_candidate_emitted",
        "session_id": session_id,
        "project": project,
        "rank": safe_rank,
        "severity": safe_severity,
        "subject_hash": safe_hash,
        "awaiting_confirm": bool(awaiting_confirm),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — typed wrapper guarantees clean
        _breadcrumb(
            f"ceo_boot_task_candidate_emitted dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


# ---------------------------------------------------------------------
# PLAN-075 Phase 1 narrow-promotion (v1.13.x patch) / ADR-106 + ADR-110
# Pair-Rail Multi-LLM (Claude + Codex Cross-Review) PreToolUse hook
# `check_pair_rail.py` audit emitters. Registered with KERNEL_OVERRIDE
# at ceremony commit __FILLED_AT_COMMIT__. SPEC/v1/audit-log.schema.md
# documents per-event schema.
# ---------------------------------------------------------------------


def emit_pair_rail_review_passed(
    *,
    target_path: str,
    tool_name: str,
    codex_duration_ms: int,
    codex_response_sha256: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `pair_rail_review_passed` event from check_pair_rail.py.

    Fired when Codex MCP is invoked in read-only review mode against
    an L3+ canonical-guarded path AND returns a clean review (no
    write-shaped patches, no `*** Update File:`, no unified diff,
    no JSON Patch RFC 6902 envelope). Allow decision granted.
    """
    emit_generic(
        "pair_rail_review_passed",
        session_id=session_id,
        target_path=str(target_path)[:300],
        tool_name=str(tool_name)[:50],
        codex_duration_ms=int(codex_duration_ms),
        codex_response_sha256=str(codex_response_sha256)[:64],
        project=project,
    )


def emit_pair_rail_codex_unavailable(
    *,
    target_path: str,
    tool_name: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `pair_rail_codex_unavailable` event from check_pair_rail.py.

    Fired when Codex MCP is unavailable (binary missing, connect
    timeout, spawn error). Hook fail-OPENs (allow decision) — this
    breadcrumb provides forensic trace for fail-open paths. Reason
    is one of: `binary_missing`, `connect_timeout`, `spawn_error`,
    `disabled_via_killswitch`.
    """
    emit_generic(
        "pair_rail_codex_unavailable",
        session_id=session_id,
        target_path=str(target_path)[:300],
        tool_name=str(tool_name)[:50],
        reason=str(reason)[:64],
        project=project,
    )


def emit_pair_rail_codex_violation(
    *,
    target_path: str,
    tool_name: str,
    violation_type: str,
    codex_response_sha256: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `pair_rail_codex_violation` event from check_pair_rail.py.

    Fired when Codex MCP review returned a write-shaped patch (any of:
    `*** Update File:`, unified diff `--- a/`, JSON Patch RFC 6902
    `[{"op":"replace",...}]`). Codex is read-only by contract here;
    a write-shaped response is a contract violation. Hook BLOCKs the
    tool call. violation_type is one of: `unified_diff_detected`,
    `apply_patch_envelope`, `json_patch_rfc6902`, `mcp_write_tool_call`.
    """
    emit_generic(
        "pair_rail_codex_violation",
        session_id=session_id,
        target_path=str(target_path)[:300],
        tool_name=str(tool_name)[:50],
        violation_type=str(violation_type)[:64],
        codex_response_sha256=str(codex_response_sha256)[:64],
        project=project,
    )


def emit_pair_rail_sentinel_bypass(
    *,
    target_path: str,
    tool_name: str,
    sentinel_path: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `pair_rail_sentinel_bypass` event from check_pair_rail.py.

    Fired when an Owner-signed sentinel grants the L3+ canonical path
    AND the pair-rail review is short-circuited via sentinel_bypass.
    Allow decision granted without invoking Codex. Sentinel must
    already have been verified by check_canonical_edit.py upstream.
    """
    emit_generic(
        "pair_rail_sentinel_bypass",
        session_id=session_id,
        target_path=str(target_path)[:300],
        tool_name=str(tool_name)[:50],
        sentinel_path=str(sentinel_path)[:300],
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-081 Phase 1-full / R1 S-Sec-5 — Codex ingress sanitization audit
# emitter. Wired via check_codex_response.py PostToolUse hook on
# mcp__codex__codex|mcp__codex__codex-reply matchers. Per ADR-106 the
# hook is advisory-only (cannot block); this audit event is the
# forensic-trail surface for downstream `audit-query.py
# codex-injection-summary`.
# ---------------------------------------------------------------------


def emit_pair_rail_codex_injection_detected(
    *,
    tool_name: str,
    family_ids: List[str],
    match_count: int,
    first_offset_bucket: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `pair_rail_codex_injection_detected` event.

    Fired by check_codex_response.py when Codex MCP stdout contains
    one of the harness-mimicry / xml-system-tag / tool-use-forgery
    injection patterns scanned by `_scan_injection`. Sec MF-3
    whitelisted fields ONLY:

    - tool_name: which Codex MCP tool (mcp__codex__codex /
      mcp__codex__codex-reply).
    - family_ids: sorted unique pattern family identifiers that
      matched (subset of {"harness_mimicry", "xml_system_tag",
      "tool_use_forgery"}).
    - match_count: total match count across all families.
    - first_offset_bucket: coarse-bucketed first match offset
      ("0-100" / "100-1k" / "1k-10k" / "10k-100k" / "100k+") — raw
      offset is FORBIDDEN per LLM06 side-channel guard.

    Raw matched content is NEVER persisted. The forensic surface is
    "patterns matched + how many + roughly where" — sufficient for
    SOC alerting without leaking the prompt prefix length or the
    matched-token bytes themselves.

    R1 S-Sec-9 atomicity: this typed wrapper + the dispatch-gate
    elif branch + the _PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST
    frozenset MUST all land in the same ceremony script (per S87
    hot-fix history at audit_emit.py:386-396). The ceremony scripts
    enforces this via Block 3 verification.
    """
    # Defensive: coerce family_ids to sorted unique list[str] of
    # known families. Anything else is dropped to satisfy MF-3.
    _KNOWN_FAMILIES = ("harness_mimicry", "xml_system_tag", "tool_use_forgery")
    safe_families = sorted({
        str(f) for f in family_ids if str(f) in _KNOWN_FAMILIES
    })
    safe_count = max(0, int(match_count))
    safe_bucket = (
        first_offset_bucket
        if first_offset_bucket in ("0-100", "100-1k", "1k-10k", "10k-100k", "100k+")
        else "0-100"
    )
    emit_generic(
        "pair_rail_codex_injection_detected",
        session_id=session_id,
        tool_name=str(tool_name)[:50],
        family_ids=safe_families,
        match_count=safe_count,
        first_offset_bucket=safe_bucket,
        project=project,
    )




# ---------------------------------------------------------------------
# PLAN-081 Phase 2 — dispatcher_route typed wrapper.
# Wired via inject-agent-context.sh --pair-mode dispatch path. Carries
# routing-decision metadata for audit forensics (which archetype, which
# rail, why fallback if any) plus the perf metric source field
# (wall_clock_s) consumed by disable_predicate_eval._latency_p95.
#
# Sec MF-3: ONLY whitelisted fields persisted. NO archetype profile
# body, NO task description, NO skill content. The dispatch-gate in
# emit_generic re-enforces _DISPATCHER_ROUTE_EMIT_ALLOWLIST defensively.
# ---------------------------------------------------------------------


def emit_dispatcher_route(
    *,
    archetype: str,
    rail: str,
    reason_code: str,
    matrix_sha256_prefix: str,
    matrix_sha256_match: bool,
    coder: str,
    reviewer: str,
    coder_model: Optional[str] = None,
    reviewer_sandbox: str = "read-only",
    fallback_provider: str = "claude",
    wall_clock_ms: int = 0,
    retry_at_timeout_ms: Optional[int] = None,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit ``dispatcher_route`` event from inject-agent-context.sh.

    Fired once per ``--pair-mode`` dispatch (one event per spawned
    Agent). Records the routing decision so post-hoc audit-query.py can
    reconstruct which rail was chosen + why fallback occurred (if any).

    Args (all keyword-only):
        archetype: archetype name (e.g. ``"code-reviewer"``).
        rail: ``"pair_rail"`` | ``"fallback_claude_only"`` |
            ``"fallback_codex_only"``.
        reason_code: ``"ok"`` (pair-rail engaged) |
            ``"predicate_<id>_fired"`` (disable predicate triggered) |
            ``"matrix_sha_mismatch"`` | ``"health_prereq_unmet_<u-id>"``.
        matrix_sha256_prefix: 16-hex prefix of loaded matrix SHA-256
            (raw full hex digest is forbidden — bucket prefix only).
        matrix_sha256_match: True iff ``CEO_PAIR_RAIL_MATRIX_SHA256``
            env var was set AND matched the loaded matrix digest.
        coder: provider name from routing-matrix.yaml ``coder`` field.
        reviewer: provider name from routing-matrix.yaml ``reviewer``
            field.
        coder_model: optional model floor (sonnet/opus/haiku).
        reviewer_sandbox: sandbox mode for reviewer (read-only /
            workspace-write / danger-full-access).
        fallback_provider: provider used when pair-rail disabled.
        wall_clock_ms: dispatcher-side resolution wall-clock as an
            integer in milliseconds (≥0). Source field for the
            ``codex_latency_p95_s`` perf predicate aggregator (which
            divides by 1000 to recover seconds for percentile compare).
            Codex iter 1 P0-1: integer-only, NOT float — canonical_json
            forbids floats in HMAC-covered fields per
            ``_lib/canonical_json.py:85``.
        retry_at_timeout_ms: optional retry timeout (integer ms) when
            codex.py classifier escalated simple → audit class.
        session_id: optional session identifier.
        project: optional project tag.

    Sec MF-3 enforcement: ALL fields whitelisted by
    ``_DISPATCHER_ROUTE_EMIT_ALLOWLIST``. Any caller drift carrying
    archetype profile body / task description / skill content is dropped
    by the dispatch-gate scrub in ``emit_generic``.

    R1 S-Sec-9 atomicity: this typed wrapper + the dispatch-gate elif
    branch + the ``_DISPATCHER_ROUTE_EMIT_ALLOWLIST`` frozenset MUST all
    land in the same ceremony script per S87 hot-fix history at
    ``audit_emit.py:386-396``. Phase 2 ceremony Block 3 verification
    enforces this via grep -F assertions on all three.
    """
    # Defensive coercion to satisfy MF-3 + canonical_json no-float
    # invariant. Codex iter 1 P0-1: wall_clock_ms / retry_at_timeout_ms
    # are stored as integers (NOT floats) so the HMAC chain over the
    # event JSON does not reject the record at canonical_json validation.
    safe_rail = rail if rail in (
        "pair_rail", "fallback_claude_only", "fallback_codex_only"
    ) else "fallback_claude_only"
    safe_prefix = (matrix_sha256_prefix or "")[:16]
    try:
        safe_wall_ms = max(0, int(wall_clock_ms))
    except (TypeError, ValueError):
        safe_wall_ms = 0
    kwargs = dict(
        session_id=session_id,
        archetype=str(archetype)[:64],
        rail=safe_rail,
        reason_code=str(reason_code)[:80],
        matrix_sha256_prefix=safe_prefix,
        matrix_sha256_match=bool(matrix_sha256_match),
        coder=str(coder)[:32],
        reviewer=str(reviewer)[:32],
        coder_model=str(coder_model)[:32] if coder_model is not None else None,
        reviewer_sandbox=str(reviewer_sandbox)[:32],
        fallback_provider=str(fallback_provider)[:32],
        wall_clock_ms=safe_wall_ms,
        project=project,
    )
    if retry_at_timeout_ms is not None:
        try:
            kwargs["retry_at_timeout_ms"] = max(0, int(retry_at_timeout_ms))
        except (TypeError, ValueError):
            kwargs["retry_at_timeout_ms"] = 0
    emit_generic("dispatcher_route", **kwargs)


# ---------------------------------------------------------------------
# PLAN-081 Phase 3 — pair_rail_case typed wrapper.
# ---------------------------------------------------------------------


def emit_pair_rail_case(
    *,
    case: str,
    claude_verdict: str,
    codex_verdict: str,
    tool_name: str,
    file_path_hash_prefix: str,
    precondition_met: bool = False,
    rubric_violation_id: str = "",
    severity: str = "",
    jaccard_similarity_bucket: str = "",
    human_triage_grace_h: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit ``pair_rail_case`` event from check_pair_rail.py:_decide_with_matrix."""
    import re as _re
    safe_case = case if case in ("A", "B", "C", "D", "E", "F") else "F"
    safe_claude = claude_verdict if claude_verdict in ("PASS", "BLOCK") else "PASS"
    safe_codex = codex_verdict if codex_verdict in (
        "PASS", "BLOCK", "ADVISORY", "TIMEOUT", "MALFORMED"
    ) else "MALFORMED"
    safe_tool = str(tool_name)[:32] if tool_name in (
        "Edit", "Write", "MultiEdit", "NotebookEdit"
    ) else "unknown"
    raw_prefix = (file_path_hash_prefix or "")[:16]
    safe_prefix = raw_prefix if _re.fullmatch(r"[0-9a-f]{0,16}", raw_prefix) else ""
    raw_rubric = (rubric_violation_id or "")[:64]
    if raw_rubric and not _re.fullmatch(r"[a-z][a-z0-9-]{0,63}", raw_rubric):
        safe_rubric = "unknown_rubric_id"
    else:
        safe_rubric = raw_rubric
    safe_severity = severity if severity in ("P0", "P1", "") else ""
    safe_jaccard = jaccard_similarity_bucket if jaccard_similarity_bucket in (
        "<=0.3", "0.3-0.5", "0.5-0.8", ">0.8", ""
    ) else ""
    try:
        safe_grace_h = max(0, min(24, int(human_triage_grace_h)))
    except (TypeError, ValueError):
        safe_grace_h = 0
    emit_generic(
        "pair_rail_case",
        session_id=session_id,
        case=safe_case,
        claude_verdict=safe_claude,
        codex_verdict=safe_codex,
        tool_name=safe_tool,
        file_path_hash_prefix=safe_prefix,
        precondition_met=bool(precondition_met),
        rubric_violation_id=safe_rubric,
        severity=safe_severity,
        jaccard_similarity_bucket=safe_jaccard,
        human_triage_grace_h=safe_grace_h,
        project=project,
    )


# ---------------------------------------------------------------------
# PLAN-081 Phase 4 — pair_rail_promotion typed wrapper.
# ---------------------------------------------------------------------


def emit_pair_rail_promotion(
    *,
    run_id: str,
    verdict: str,
    corpus_n: int,
    corpus_manifest_sha: str,
    catch_rate_num: int,
    catch_rate_den: int,
    fp_rate_bucket: str = "",
    schema_adherence_pct_bucket: str = "",
    rubric_gap_pp_bucket: str = "",
    codex_cli_version: str = "",
    python_version: str = "",
    git_head_sha_prefix: str = "",
    pass_2_retry_used: bool = False,
    manual_triage: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit ``pair_rail_promotion`` event from run-promotion-gate.py."""
    safe_verdict = verdict if verdict in (
        "PASS", "PASS_AFTER_RETRY", "TRIAGE", "FAIL"
    ) else "FAIL"
    safe_corpus_n = max(0, int(corpus_n))
    safe_manifest = (corpus_manifest_sha or "")[:16]
    safe_num = max(0, int(catch_rate_num))
    safe_den = max(1, int(catch_rate_den))
    safe_fp = fp_rate_bucket if fp_rate_bucket in (
        "<=15%", "15-30%", ">30%", ""
    ) else ""
    safe_schema = schema_adherence_pct_bucket if schema_adherence_pct_bucket in (
        "100%", "95-99%", "<95%", ""
    ) else ""
    safe_rubric = rubric_gap_pp_bucket if rubric_gap_pp_bucket in (
        "<=0pp", "0-5pp", "5-10pp", ">10pp", ""
    ) else ""
    safe_codex_v = (codex_cli_version or "")[:32]
    safe_py_v = (python_version or "")[:16]
    safe_git = (git_head_sha_prefix or "")[:12]
    emit_generic(
        "pair_rail_promotion",
        session_id=session_id,
        run_id=str(run_id)[:36],
        verdict=safe_verdict,
        corpus_n=safe_corpus_n,
        corpus_manifest_sha=safe_manifest,
        catch_rate_num=safe_num,
        catch_rate_den=safe_den,
        fp_rate_bucket=safe_fp,
        schema_adherence_pct_bucket=safe_schema,
        rubric_gap_pp_bucket=safe_rubric,
        codex_cli_version=safe_codex_v,
        python_version=safe_py_v,
        git_head_sha_prefix=safe_git,
        pass_2_retry_used=bool(pass_2_retry_used),
        manual_triage=bool(manual_triage),
        project=project,
    )


# PLAN-083 Wave 0b sub-agent 0.4 (S106) — typed wrapper.
def emit_token_budget_guard_paused(
    *,
    plan_id: str,
    estimate_tokens: int,
    actual_tokens: int,
    ratio_basis_points: int,
    threshold_basis_points: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit token_budget_guard_paused event (PLAN-083 Wave 0b sub-agent 0.4).

    Fired by token-budget-guard.py when cumulative plan tokens cross threshold × estimate. Volume cap ≤10/hr.
    Sec MF-3 field allowlist enforced via TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST
    + dispatch-gate scrub in emit_generic. Caller drift defense.
    """
    emit_generic(
        "token_budget_guard_paused",
        plan_id=plan_id,
        estimate_tokens=int(estimate_tokens),
        actual_tokens=int(actual_tokens),
        ratio_basis_points=int(ratio_basis_points),
        threshold_basis_points=int(threshold_basis_points),
        session_id=session_id,
        project=project,
    )

# PLAN-083 Wave 0b sub-agent 0.5 (S106) — typed wrapper.
def emit_anti_ceo_overhead_block(
    *,
    anti_pattern_id: str,
    count_in_window: int,
    override_recommended_subagent_type: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit anti_ceo_overhead_block event (PLAN-083 Wave 0b sub-agent 0.5).

    Fired by check_anti_ceo_overhead.py PreToolUse hook when CEO-overhead anti-pattern detected. Emit budget ≤20/day sliding window.
    Sec MF-3 field allowlist enforced via ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST
    + dispatch-gate scrub in emit_generic. Caller drift defense.
    """
    emit_generic(
        "anti_ceo_overhead_block",
        anti_pattern_id=anti_pattern_id,
        count_in_window=int(count_in_window),
        override_recommended_subagent_type=override_recommended_subagent_type,
        session_id=session_id,
        project=project,
    )

# PLAN-083 Wave 0b sub-agent 0.5 (S106) — typed wrapper.
def emit_anti_ceo_overhead_override_used(
    *,
    anti_pattern_id: str,
    override_justification_sha: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit anti_ceo_overhead_override_used event (PLAN-083 Wave 0b sub-agent 0.5).

    Fired by check_anti_ceo_overhead.py when CEO_OVERHEAD_ACK=1 env override bypasses a block.
    Sec MF-3 field allowlist enforced via ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST
    + dispatch-gate scrub in emit_generic. Caller drift defense.
    """
    emit_generic(
        "anti_ceo_overhead_override_used",
        anti_pattern_id=anti_pattern_id,
        override_justification_sha=override_justification_sha,
        session_id=session_id,
        project=project,
    )

# PLAN-083 Wave 0b sub-agent 0.7d (S106) — typed wrapper.
def emit_smart_loading_resolved(
    *,
    profile: str,
    active_count: int,
    suppressed_count: int,
    context_total_tokens: int,
    arbitration_dropped_count: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit smart_loading_resolved event (PLAN-083 Wave 0b sub-agent 0.7d).

    Fired by smart-loading-resolver.py per resolution. Carries profile + active/suppressed counts + context budget total + arbitration dropped count.
    Sec MF-3 field allowlist enforced via SMART_LOADING_RESOLVED_ALLOWLIST
    + dispatch-gate scrub in emit_generic. Caller drift defense.
    """
    emit_generic(
        "smart_loading_resolved",
        profile=profile,
        active_count=int(active_count),
        suppressed_count=int(suppressed_count),
        context_total_tokens=int(context_total_tokens),
        arbitration_dropped_count=int(arbitration_dropped_count),
        session_id=session_id,
        project=project,
    )


# PLAN-083 Wave 2 sub-agent 2.1 — Sec MF-3 allowlist for first_run_wizard_completed.
_FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "profile", "recommendation_count", "user_action",
})

# PLAN-083 Wave 2 sub-agent 2.2 — Sec MF-3 allowlist for contextual_recommendation_emitted.
_CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "profile", "recommendation_count", "top_score", "suppressed_count",
})

# PLAN-083 Wave 2 sub-agent 2.4 — Sec MF-3 allowlist for value_dashboard_summarized.
# PLAN-085 Wave C.1 — Sec MF-3 allowlist for live_adapter_blocked.
_LIVE_ADAPTER_BLOCKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "reason",
    "atlas_technique",  # PLAN-085 Wave G.1b
})

# PLAN-085 Wave G.1b — ATLAS technique-ID allowlists (4 NEW actions).
# Each carries `atlas_technique` (AML.T<NNNN>) + detector context fields.

_PROMPT_INJECTION_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "snippet_preview", "match_count", "bytes_scanned",
    "triggered_by_tool",
})
# PLAN-113 Codex B3 P1 — mcp_injection_finding carries MCP-controlled
# snippet_preview; route through an explicit scrub branch (was passthrough)
# + re-truncate snippet_preview via _preview() so a DIRECT emit_generic
# caller cannot bypass the named-emitter's [:120] cap and leak secrets.
_MCP_INJECTION_FINDING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "server_id", "mcp_tool_name", "source_kind", "family_counts",
    "match_count", "bytes_scanned", "severity",
    "snippet_preview", "scanner_action",
})

_SECRET_LEAK_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "snippet_preview", "match_count", "bytes_scanned",
    "triggered_by_tool",
})

_PII_REDACTED_OUTGOING_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned",
})

_CODEX_EGRESS_REDACTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned", "callsite",
})

# PLAN-112-FOLLOWUP-codex-egress-proof-telemetry — Sec MF-3 allowlist for
# pair_rail_outgoing_redaction_applied (ADR-114 outbound pair-rail vector).
# Content-field-free BY CONSTRUCTION: deliberately NO text / prompt /
# match_value — wiring an emit without this gate would write caller fields
# verbatim into the HMAC-chained log (the F-7.9 W1 hard-prerequisite).
_PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique", "signal", "family",
    "match_count", "bytes_scanned", "callsite",
})

# PLAN-085 Wave E.4 piggyback — canonical_edit_completed allowlist.
# Emitted by check_bash_canonical_forensic.py PostToolUse hook.
_CANONICAL_EDIT_COMPLETED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "path", "sentinel_hint",
})

# PLAN-085 Wave C.2 — Sec MF-3 allowlist for credential_blocked_due_to_age.
_CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "age_days", "max_age_days",
})

# PLAN-085 Wave C.2 — Sec MF-3 allowlist for credential_emergency_override_used.
_CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "ticket_id", "age_days", "max_age_days",
})

# PLAN-117 WS-A — Sec MF-3 allowlist for credential_override_late_set_ignored.
# Forensic-only fields; the rejected override VALUE is intentionally absent
# (closed-enum-breadcrumb-must-not-echo-rejected-value).
_CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "provider", "attempted_var_name", "provenance_hint",
})

# PLAN-085 Wave C.3 — Sec MF-3 allowlist for mcp_bearer_replay_rejected.
_MCP_BEARER_REPLAY_REJECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "reason", "nonce_prefix",
})

# PLAN-085 Wave C.3 — Sec MF-3 allowlist for mcp_non_loopback_rejected.
_MCP_NON_LOOPBACK_REJECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "remote_addr_family",
})


_VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "period_days", "cost_usd_int_cents", "bugs_count", "dispatches_count", "plans_count",
})

# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_write_override_used.
_TRADING_WRITE_OVERRIDE_USED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    # PLAN-083 Wave 3 P0 fix (2026-05-11): align with caller fields in
    # .claude/scripts/trading-readonly-guardrails.py:_check_write_override.
    # Sec MF-3 deny-by-default — these are hashed prefixes + length only;
    # raw target_path / justification text NEVER persisted.
    "allowed", "reason",
    "target_path_sha256_prefix",  # 16-hex sha256 prefix
    "justification_sha256_prefix",  # 16-hex sha256 prefix
    "justification_length",  # int — bounded length only, no content
    "err_preview",  # str ≤80 — exception preview from path resolution failure (NO raw paths)
})

# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_kill_switch_invoked.
_TRADING_KILL_SWITCH_INVOKED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "event_schema",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "hmac",
    "hmac_error",
    "reason",
})

# PLAN-083 Wave 2 sub-agent 2.7 — Sec MF-3 allowlist for trading_kill_switch_disabled.
_TRADING_KILL_SWITCH_DISABLED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    # PLAN-083 Wave 3 P0 fix (2026-05-11): align with caller fields in
    # scripts/local/trading-readonly-escape-hatch.sh emit_generic call.
    # All hashed prefixes — raw justification body NEVER persisted.
    "justification_sha256_prefix",  # 16-hex sha256 prefix
    "signer_fingerprint_prefix",  # 16-hex GPG fingerprint prefix
    "signed_new",  # bool — true if .asc freshly created vs reused
    "justification_length",  # int — bounded length
})


# =============================================================================
# PLAN-088 canonical-13 god-mode auto-activation (S114 / qa-architect-reviewed).
# Per W0 ATLAS-binding table + M-12/Sec-3 (rate-cap 100/min/action +
# payload_max_bytes=4096) + Sec MF-3 (deny-by-default allowlists).
#
# 11 net-new typed emitters + 11 allowlists + 11 emit_generic dispatch gates.
# The 2 remaining canonical-13 (`model_routing_advised` + `mcp_route_advised`)
# are pre-existing stubs registered by PLAN-078 / PLAN-086.
#
# QA fixes from S114 dispatch verdict ACCEPT-WITH-FIXES (4 P0):
#   1. `time` + `threading` moved to top-of-file imports (unaliased)
#   2. `_PLAN088_RATE_STATE` cleared via _plan088_rate_state_clear() in tests;
#      injectable clock via `_clock` parameter for test-time advance
#   3. `emit_generic` dispatch gates added for all 11 new actions (Sec MF-3
#      defense-in-depth — see emit_generic body for the 11 elif branches)
#   4. `_plan088_payload_cap` uses errors='ignore' + strip-continuation-byte
#      loop (utf-8 mid-codepoint boundary safe; no � overflow)
# =============================================================================

_PLAN088_RATE_CAP_PER_MIN = 100
_PLAN088_PAYLOAD_MAX_BYTES = 4096
_PLAN088_RATE_STATE: Dict[str, Tuple[float, int, int]] = {}  # action -> (window_start_ts, count, dropped)
_PLAN088_RATE_LOCK = threading.Lock()


def _plan088_rate_state_clear() -> None:
    """Reset PLAN-088 rate-cap state. Test helper for cross-test isolation
    (qa-architect P0-2 fix: module-level mutable singleton needs explicit
    reset to avoid test order dependence)."""
    with _PLAN088_RATE_LOCK:
        _PLAN088_RATE_STATE.clear()


def _plan088_rate_admit(action: str, _clock: Callable[[], float] = time.time) -> bool:
    """Return True if action emit is within the 100/min/action cap.

    Sliding 60s window; on rollover, resets count. Increments `dropped`
    counter when over-budget WITHOUT re-emitting (M-12 anti-recursive-flood
    invariant — never call `_write_event` or `_breadcrumb` from this path).

    `_clock` is injectable for tests (advance simulated time without
    `time.sleep`).
    """
    now = _clock()
    with _PLAN088_RATE_LOCK:
        window_start, count, dropped = _PLAN088_RATE_STATE.get(action, (now, 0, 0))
        if now - window_start >= 60.0:
            window_start, count, dropped = now, 0, 0
        if count >= _PLAN088_RATE_CAP_PER_MIN:
            _PLAN088_RATE_STATE[action] = (window_start, count, dropped + 1)
            return False
        _PLAN088_RATE_STATE[action] = (window_start, count + 1, dropped)
        return True


def _plan088_payload_cap(value: str, max_bytes: int = _PLAN088_PAYLOAD_MAX_BYTES) -> str:
    """Truncate a utf-8 string to ``max_bytes`` without breaking codepoint.

    M-12 anti-traceback-leak guard. qa-architect P0-4 fix: use ``errors='ignore'``
    + strip-continuation-byte loop so the cut point lands on a valid utf-8
    boundary (no \\ufffd replacement-char overflow that would push past
    max_bytes by 1-2 bytes).

    Only accepts str input (P1 fix: do not coerce None / non-str types
    silently — let caller's typed default handle missing values).
    """
    if not isinstance(value, str):
        return ""
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return value
    # Strip trailing continuation bytes (0b10xxxxxx) to land on a valid
    # codepoint boundary, then decode with errors='ignore' as belt+suspenders.
    cut = encoded[:max_bytes]
    while cut and (cut[-1] & 0xC0) == 0x80:
        cut = cut[:-1]
    return cut.decode("utf-8", errors="ignore")


# --- W1.1 AUTO-01: cache_discipline_alerted (telemetry-only) -----------

_CACHE_DISCIPLINE_ALERTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "hit_rate_basis_points", "floor_basis_points", "session_count_24h",
    "below_floor", "opted_out",
})


def emit_cache_discipline_alerted(
    *,
    session_id: str = "",
    hit_rate_basis_points: int = 0,
    floor_basis_points: int = 700,
    session_count_24h: int = 0,
    below_floor: bool = False,
    opted_out: bool = False,
    project: str = "",
) -> None:
    """Emit cache_discipline_alerted (PLAN-088 W1.1 AUTO-01).

    Tier-S /ceo-boot check telemetry. Fires when SessionStart cache-discipline
    check observes hit-rate below floor (default 700 basis-points = 0.70).
    Sec MF-3 field allowlist enforced. Cap: 100/min/action.
    """
    if not _plan088_rate_admit("cache_discipline_alerted"):
        return
    hrbp = max(0, min(1000, int(hit_rate_basis_points)))
    fbp = max(0, min(1000, int(floor_basis_points)))
    raw_event: Dict[str, Any] = {
        "action": "cache_discipline_alerted",
        "session_id": session_id,
        "project": project,
        "hit_rate_basis_points": hrbp,
        "floor_basis_points": fbp,
        "session_count_24h": int(session_count_24h),
        "below_floor": bool(below_floor),
        "opted_out": bool(opted_out),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _CACHE_DISCIPLINE_ALERTED_ALLOWLIST)
    _write_event(cleaned)


# --- W1.2 AUTO-02: first_run_wizard_dispatched (UX trigger) ------------

_FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "trigger_source", "wizard_phase", "skipped_reason",
})


def emit_first_run_wizard_dispatched(
    *,
    session_id: str = "",
    trigger_source: str = "session_start",
    wizard_phase: str = "dispatched",
    skipped_reason: str = "",
    project: str = "",
) -> None:
    """Emit first_run_wizard_dispatched (PLAN-088 W1.2 AUTO-02)."""
    if not _plan088_rate_admit("first_run_wizard_dispatched"):
        return
    raw_event: Dict[str, Any] = {
        "action": "first_run_wizard_dispatched",
        "session_id": session_id,
        "project": project,
        "trigger_source": _plan088_payload_cap((trigger_source or "")[:64]),
        "wizard_phase": _plan088_payload_cap((wizard_phase or "")[:32]),
        "skipped_reason": _plan088_payload_cap((skipped_reason or "")[:128]),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST)
    _write_event(cleaned)


# --- W1.3 AUTO-03 / W6.1: estimate_calibrator_pipeline_run (telemetry) -

_ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "pipeline_phase", "plans_consumed", "posterior_alpha_basis_points",
    "posterior_beta_basis_points", "trigger_source",
})


def emit_estimate_calibrator_pipeline_run(
    *,
    session_id: str = "",
    pipeline_phase: str = "completed",
    plans_consumed: int = 0,
    posterior_alpha_basis_points: int = 0,
    posterior_beta_basis_points: int = 0,
    trigger_source: str = "nightly_cron",
    project: str = "",
) -> None:
    """Emit estimate_calibrator_pipeline_run (PLAN-088 W1.3 / W6.1 AUTO-03).

    Bayesian posterior refresh telemetry. trigger_source ∈ {nightly_cron,
    plan_close_hook}. Posteriors as integer basis-points (×1000) per
    canonical_json no-float invariant.
    """
    if not _plan088_rate_admit("estimate_calibrator_pipeline_run"):
        return
    raw_event: Dict[str, Any] = {
        "action": "estimate_calibrator_pipeline_run",
        "session_id": session_id,
        "project": project,
        "pipeline_phase": (pipeline_phase or "")[:32],
        "plans_consumed": int(plans_consumed),
        "posterior_alpha_basis_points": max(0, int(posterior_alpha_basis_points)),
        "posterior_beta_basis_points": max(0, int(posterior_beta_basis_points)),
        "trigger_source": (trigger_source or "")[:32],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST
    )
    _write_event(cleaned)


# --- W1.4 SEMI-13: 4 graceful-degradation emits ------------------------

# PLAN-107 Wave B.4.1 (S145 2026-05-19) — Sec MF-3 deny-by-default
# allowlist for `stdlib_violation` orphan register. Without this
# entry, _scrub_ceo_boot_event silently strips `violation_count`
# (and any future field) from the event. Single-field contract per
# AC12 — `violation_count` is an int; NO file paths / module names /
# import strings / source body persist.
_STDLIB_VIOLATION_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "violation_count",
})

_SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "findings_total", "findings_dropped", "drop_reason", "archetype",
})


def emit_subagent_findings_partial_drop(
    *,
    session_id: str = "",
    findings_total: int = 0,
    findings_dropped: int = 0,
    drop_reason: str = "",
    archetype: str = "",
    project: str = "",
) -> None:
    """Emit subagent_findings_partial_drop (PLAN-088 W1.4 SEMI-13).

    ATLAS: AML.T0048 (Governance bypass observation). Fires when sub-agent
    spawn returns fewer findings than expected (e.g. context-window cut).
    """
    if not _plan088_rate_admit("subagent_findings_partial_drop"):
        return
    raw_event: Dict[str, Any] = {
        "action": "subagent_findings_partial_drop",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("subagent_findings_partial_drop", "AML.T0048"),
        "findings_total": int(findings_total),
        "findings_dropped": int(findings_dropped),
        "drop_reason": _plan088_payload_cap((drop_reason or "")[:256]),
        "archetype": (archetype or "")[:64],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST
    )
    _write_event(cleaned)


_ANTHROPIC_429_OBSERVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "retry_after_ms", "endpoint_class", "consecutive_count",
})


def emit_anthropic_429_observed(
    *,
    session_id: str = "",
    retry_after_ms: int = 0,
    endpoint_class: str = "",
    consecutive_count: int = 1,
    project: str = "",
) -> None:
    """Emit anthropic_429_observed (PLAN-088 W1.4 SEMI-13).

    ATLAS: AML.T0029 (Denial of ML Service signal). Fires on HTTP 429
    from Anthropic API. Telemetry only; back-off handled by transport
    layer breaker (ADR-072).
    """
    if not _plan088_rate_admit("anthropic_429_observed"):
        return
    raw_event: Dict[str, Any] = {
        "action": "anthropic_429_observed",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("anthropic_429_observed", "AML.T0029"),
        "retry_after_ms": max(0, int(retry_after_ms)),
        "endpoint_class": (endpoint_class or "")[:32],
        "consecutive_count": max(0, int(consecutive_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _ANTHROPIC_429_OBSERVED_ALLOWLIST
    )
    _write_event(cleaned)


# PLAN-106 Wave G.2 — extend with upgrade.sh-style triple
# (attempt + backoff_seconds + repo_path_hash) per plan §3 G.2.b.
# Legacy fields (retry_count, elapsed_ms, operation) preserved for
# PLAN-088 SEMI-13 callers — additive only, no breaking change.
# PLAN-106 Wave H.1 (absorbing PLAN-095-FOLLOWUP §B.5) — output_scan
# dedup suppression event allowlist. Closed-enum on `pattern_id` is
# enforced at the producer (`_lib/output_scan._PATTERN_IDS`) per
# PLAN-106 §3 Wave H.1.b security R1 P1 fold. `family` is closed-enum
# `LLM01`..`LLM10` validated at the same producer site.
_OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "repo_path_hash", "command_sha", "pattern_id", "family",
    "ttl_hours_remaining",
})


_GIT_INDEX_LOCK_RETRY_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "retry_count", "elapsed_ms", "operation",
    "attempt", "backoff_seconds", "repo_path_hash",
})


def emit_git_index_lock_retry(
    *,
    session_id: str = "",
    retry_count: int = 0,
    elapsed_ms: int = 0,
    operation: str = "",
    project: str = "",
    # PLAN-106 Wave G.2 — upgrade.sh-style triple per plan §3 G.2.b
    attempt: int = 0,
    backoff_seconds: int = 0,
    repo_path_hash: str = "",
) -> None:
    """Emit git_index_lock_retry (PLAN-088 W1.4 SEMI-13 + PLAN-106 G.2).

    Infra-error telemetry. Fires when `git_safe_commit.sh` (legacy)
    OR `scripts/upgrade.sh` (PLAN-106) encounters a stale
    `.git/index.lock` and retries.

    Two field families coexist:
    - PLAN-088 legacy: retry_count + elapsed_ms + operation
    - PLAN-106 G.2: attempt + backoff_seconds + repo_path_hash

    Both families pass through the same allowlist scrub. Callers pass
    whichever family applies; absent fields default to 0/"" and are
    persisted as such (no key omission to keep schema stable).
    """
    if not _plan088_rate_admit("git_index_lock_retry"):
        return
    raw_event: Dict[str, Any] = {
        "action": "git_index_lock_retry",
        "session_id": session_id,
        "project": project,
        # Legacy PLAN-088 fields
        "retry_count": max(0, int(retry_count)),
        "elapsed_ms": max(0, int(elapsed_ms)),
        "operation": (operation or "")[:32],
        # PLAN-106 G.2 fields
        "attempt": max(0, int(attempt)),
        "backoff_seconds": max(0, int(backoff_seconds)),
        "repo_path_hash": (repo_path_hash or "")[:64],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _GIT_INDEX_LOCK_RETRY_ALLOWLIST
    )
    _write_event(cleaned)


_CODEX_INVOKE_DISPATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "invocation_class", "thread_id_prefix", "redacted_outgoing",
    # PLAN-143 item-3 (audit-errors-04): retain the dual-rail process
    # exit code that check_pair_rail.py emits via emit_generic. Bounded
    # int 0..255 (POSIX exit-status range), clamped in the emit_generic
    # dispatch branch before scrub. Same forbidden-field-drop class as
    # PLAN-140's hook_origin (ADR-153). Advisory telemetry; no PII.
    "exit_code",
})


def emit_codex_invoke_dispatched(
    *,
    session_id: str = "",
    invocation_class: str = "",
    thread_id_prefix: str = "",
    redacted_outgoing: bool = True,
    project: str = "",
) -> None:
    """Emit codex_invoke_dispatched (PLAN-088 W1.4 SEMI-13).

    ATLAS: AML.T0050 (LLM Plugin Compromise dual-rail). Fires per Codex
    dispatch through the egress envelope. ADR-114 callsite — payload
    redact_outgoing()'d at adapter; this emit captures the dispatch
    decision. thread_id_prefix is 8-16-hex prefix only (no PII).
    """
    if not _plan088_rate_admit("codex_invoke_dispatched"):
        return
    raw_event: Dict[str, Any] = {
        "action": "codex_invoke_dispatched",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("codex_invoke_dispatched", "AML.T0050"),
        "invocation_class": (invocation_class or "")[:32],
        "thread_id_prefix": (thread_id_prefix or "")[:16],
        "redacted_outgoing": bool(redacted_outgoing),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _CODEX_INVOKE_DISPATCHED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W2.1 AUTO-04: tier_policy_misrouting_advised (Governance bypass) --

_TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "empty_model_rate_basis_points", "window_hours", "top_gap_archetype",
    "above_threshold",
})


def emit_tier_policy_misrouting_advised(
    *,
    session_id: str = "",
    empty_model_rate_basis_points: int = 0,
    window_hours: int = 24,
    top_gap_archetype: str = "",
    above_threshold: bool = False,
    project: str = "",
) -> None:
    """Emit tier_policy_misrouting_advised (PLAN-088 W2.1 AUTO-04).

    ATLAS: AML.T0048 (Governance bypass). Fires on /ceo-boot Tier-S check
    when empty model_recommended rate > 10% threshold.
    """
    if not _plan088_rate_admit("tier_policy_misrouting_advised"):
        return
    rate_bp = max(0, min(1000, int(empty_model_rate_basis_points)))
    raw_event: Dict[str, Any] = {
        "action": "tier_policy_misrouting_advised",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("tier_policy_misrouting_advised", "AML.T0048"),
        "empty_model_rate_basis_points": rate_bp,
        "window_hours": max(1, int(window_hours)),
        "top_gap_archetype": (top_gap_archetype or "")[:64],
        "above_threshold": bool(above_threshold),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)


# --- PLAN-116 (S172): tier_policy_loader_fallback_observed -------------
# Dedicated loader advisory-fallback telemetry. Replaces the PLAN-093 Wave C.3
# piggyback of tier_policy_misrouting_advised (which dropped a free-text
# `reason` field on every emit → audit-log.errors noise). `reason_code` is a
# closed enum (deny-by-default). NO ATLAS technique — loader telemetry, not a
# detection signal (distinct from misrouting's AML.T0048).
_TIER_POLICY_LOADER_FALLBACK_REASON_CODES = frozenset({
    "advisory_safety_net", "bad_mode", "depth_limit", "key_count", "missing",
    "not_object", "open_failed", "oversize", "parse_error", "read_failed",
    "schema_mismatch", "stat_error", "type_mismatch", "unknown_model",
})

_TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "reason_code",
})


def emit_tier_policy_loader_fallback_observed(
    *,
    reason_code: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit tier_policy_loader_fallback_observed (PLAN-116).

    Operational telemetry: the tier-policy loader took its advisory-only
    fallback path. ``reason_code`` is a closed enum (deny-by-default; an
    out-of-enum value drops the whole event with a breadcrumb). The
    ``emit_generic`` dispatch branch enforces the same boundary so a direct
    ``emit_generic`` caller cannot bypass it (Sec MF-3 defense-in-depth).
    """
    rc = str(reason_code)
    if rc not in _TIER_POLICY_LOADER_FALLBACK_REASON_CODES:
        # Do NOT echo the rejected value (no free-text into the errors
        # sidecar — the noise class PLAN-116 closes). Length only.
        _breadcrumb(
            "emit_tier_policy_loader_fallback_observed dropped: "
            f"reason_code not in closed enum (len={len(rc)})"
        )
        return
    raw_event: Dict[str, Any] = {
        "action": "tier_policy_loader_fallback_observed",
        "session_id": session_id,
        "project": project,
        "reason_code": rc,
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST
    )
    _write_event(cleaned)


# --- PLAN-118 AC-B5: audit_producer_path_pollution_detected -----------
# Closed-enum forensic breadcrumb for the producer-side fail-CLOSED
# canonical-resolution check (PLAN-118 AC-B4). Emitted from:
#   chokepoint=chain_reset_marker — audit_emit._emit_chain_reset_marker_
#                                   under_lock fast-path on AC-B4 mismatch
#                                   (recursion-safety case 3 — fast-path
#                                   stdlib open(path,'a') to avoid
#                                   re-entering the polluted producer).
#   chokepoint=spool_drain        — spool_writer._phase4_build_batch on
#                                   AC-B4 mismatch at drain time
#                                   (case 5 — polluted HMACs never enter
#                                   the chain at all).
# Cases 1/2/4 (audit_hmac.compute_entry_hmac + audit_emit._write_event +
# emit_generic HMAC-bearing path) flow through the existing
# `hmac:null` + `hmac_error=producer_path_pollution_detected` channel
# at the regular emit path; they do NOT emit this action.
_AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS = frozenset({
    "chain_reset_marker",
    "spool_drain",
})

_AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES = frozenset({
    "audit_emit_path_pollution",
    "canonical_json_path_pollution",
    "audit_hmac_path_pollution",
})

_AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "chokepoint",                 # closed enum (CHOKEPOINTS)
    "reason_code",                # closed enum (REASON_CODES)
    "path_sha256_prefix",         # 8 hex chars
    "expected_canonical_prefix",  # 8 hex chars
})


def emit_audit_producer_path_pollution_detected(
    *,
    chokepoint: str,
    reason_code: str,
    path_sha256_prefix: str,
    expected_canonical_prefix: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """PLAN-118 AC-B5 — emit ``audit_producer_path_pollution_detected``.

    Closed-enum forensic breadcrumb invoked from the marker chokepoint
    (3) AND the spool-drain chokepoint (5) when the canonical-resolution
    check (audit_hmac._ensure_canonical_lib_modules) detects a stale
    `_lib` copy on sys.path. Both enums are deny-by-default; out-of-enum
    values DROP the event with a length-only breadcrumb (NO free-text
    into errors sidecar per
    [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    The two 8-hex-prefix fields are validated for shape too.

    Safe from recursion: this typed wrapper writes via ``_write_event``
    which itself goes through HMAC computation — and the producer is
    polluted. The recursion-safety pattern (per PLAN-118 §Producer
    runtime fail-CLOSED layer) is that the marker chokepoint (case 3)
    writes the breadcrumb via the fast-path ``open(path, 'a')`` directly
    (NOT this wrapper); spool_drain (case 5) uses this wrapper, accepting
    that its OWN HMAC will land as ``hmac:null`` + the same
    ``hmac_error`` channel — which is exactly the breadcrumb's purpose.
    """
    cp = str(chokepoint)
    if cp not in _AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS:
        _breadcrumb(
            "emit_audit_producer_path_pollution_detected dropped: "
            f"chokepoint not in closed enum (len={len(cp)})"
        )
        return
    rc = str(reason_code)
    if rc not in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
        _breadcrumb(
            "emit_audit_producer_path_pollution_detected dropped: "
            f"reason_code not in closed enum (len={len(rc)})"
        )
        return
    psp = str(path_sha256_prefix)
    ecp = str(expected_canonical_prefix)
    for name, val in (("path_sha256_prefix", psp), ("expected_canonical_prefix", ecp)):
        if len(val) != 8 or not all(c in "0123456789abcdef" for c in val):
            _breadcrumb(
                "emit_audit_producer_path_pollution_detected dropped: "
                f"{name} not 8 hex chars (len={len(val)})"
            )
            return
    raw_event: Dict[str, Any] = {
        "action": "audit_producer_path_pollution_detected",
        "session_id": session_id,
        "project": project,
        "chokepoint": cp,
        "reason_code": rc,
        "path_sha256_prefix": psp,
        "expected_canonical_prefix": ecp,
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W3.2 SEMI-11: cookbook_pattern_advised (UX hint) ------------------

_COOKBOOK_PATTERN_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "task_signature", "top_pattern_keys", "pattern_count",
})


def emit_cookbook_pattern_advised(
    *,
    session_id: str = "",
    task_signature: str = "",
    top_pattern_keys: str = "",
    pattern_count: int = 0,
    project: str = "",
) -> None:
    """Emit cookbook_pattern_advised (PLAN-088 W3.2 SEMI-11).

    UX hint telemetry. task_signature ∈ {skill-author, plan-draft, other}.
    top_pattern_keys is a comma-joined list bounded to 128 chars.
    """
    if not _plan088_rate_admit("cookbook_pattern_advised"):
        return
    raw_event: Dict[str, Any] = {
        "action": "cookbook_pattern_advised",
        "session_id": session_id,
        "project": project,
        "task_signature": (task_signature or "")[:32],
        "top_pattern_keys": _plan088_payload_cap((top_pattern_keys or "")[:128]),
        "pattern_count": max(0, int(pattern_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _COOKBOOK_PATTERN_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W4.1 AUTO-07: pair_rail_phase_advanced (dual-rail check) ----------

_PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "from_phase", "to_phase", "samples_observed", "signal_source",
    "time_elapsed_seconds",
})


def emit_pair_rail_phase_advanced(
    *,
    session_id: str = "",
    from_phase: str = "",
    to_phase: str = "",
    samples_observed: int = 0,
    signal_source: str = "",
    time_elapsed_seconds: int = 0,
    project: str = "",
) -> None:
    """Emit pair_rail_phase_advanced (PLAN-088 W4.1 AUTO-07).

    ATLAS: AML.T0050 (LLM Plugin Compromise dual-rail check). Fires on
    Pair-Rail phase transition SHADOW → DRY_RUN (Phase C is
    [DEFERRED-TO-PLAN-090] per M-6 scope amendment).

    signal_source carries persona-detection telemetry per M-10
    (env-var / cli-flag / heuristic). The dedicated `persona_detected`
    action was STRICKEN per R2 iter-1 C2 strict-13 cardinality fold;
    persona is now implicit in this payload field.
    """
    if not _plan088_rate_admit("pair_rail_phase_advanced"):
        return
    raw_event: Dict[str, Any] = {
        "action": "pair_rail_phase_advanced",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("pair_rail_phase_advanced", "AML.T0050"),
        "from_phase": (from_phase or "")[:32],
        "to_phase": (to_phase or "")[:32],
        "samples_observed": max(0, int(samples_observed)),
        "signal_source": (signal_source or "")[:32],
        "time_elapsed_seconds": max(0, int(time_elapsed_seconds)),
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST
    )
    _write_event(cleaned)


# --- W4.2 AUTO-08: batch_dispatched (cost-optimization telemetry) ------

_BATCH_DISPATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "phase", "request_count", "estimated_savings_basis_points",
    "trigger_source",
})


def emit_batch_dispatched(
    *,
    session_id: str = "",
    phase: str = "dispatched",
    request_count: int = 0,
    estimated_savings_basis_points: int = 0,
    trigger_source: str = "",
    project: str = "",
) -> None:
    """Emit batch_dispatched (PLAN-088 W4.2 AUTO-08).

    Single canonical-13 action covers BOTH endpoint phases via the
    `phase` field: `dispatched` (request submitted) / `completed`
    (response received). The earlier `batch_completed` separate-action
    framing was STRICKEN per R2 iter-1 C2 strict-13 cardinality fold.
    """
    if not _plan088_rate_admit("batch_dispatched"):
        return
    sav_bp = max(0, min(1000, int(estimated_savings_basis_points)))
    raw_event: Dict[str, Any] = {
        "action": "batch_dispatched",
        "session_id": session_id,
        "project": project,
        "phase": (phase or "")[:32],
        "request_count": max(0, int(request_count)),
        "estimated_savings_basis_points": sav_bp,
        "trigger_source": (trigger_source or "")[:32],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _BATCH_DISPATCHED_ALLOWLIST
    )
    _write_event(cleaned)


# Wave 2.2 + Wave 3.1 — production callsite wires for pre-existing stubs.
# `model_routing_advised` (PLAN-078) + `mcp_route_advised` (PLAN-086 Wave D)
# are already registered; PLAN-088 attaches ATLAS-bound telemetry by
# extending allowlists in-place. The wrappers `emit_model_routing_advised`
# (line ~3484) + future `emit_mcp_route_advised` retain existing semantics.
# The W3.1 wrapper is added next to keep ADR-114 egress symmetry intact.

_MCP_ROUTE_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "task_class", "suggested_servers", "kill_switch_overrides",
    "signal_source",
})


def emit_mcp_route_advised(
    *,
    session_id: str = "",
    task_class: str = "",
    suggested_servers: str = "",
    kill_switch_overrides: str = "",
    signal_source: str = "",
    project: str = "",
) -> None:
    """Emit mcp_route_advised (PLAN-088 W3.1 / W3.3 AUTO-06 / AUTO-10).

    ATLAS: AML.T0050 (LLM Plugin / supply-chain signal). Single canonical-13
    action covers both AUTO-06 MCP routing AND AUTO-10 general→specialized
    promotion via `signal_source` payload discriminator (per R2 iter-2
    strict-13 cardinality — `specialization_promoted` separate action was
    STRICKEN).

    `signal_source` ∈ {mcp_task_class, specialization_promoted}.
    `suggested_servers` is a comma-joined list of MCP server names (bounded
    to 128 chars); `kill_switch_overrides` enumerates env-vars currently
    overriding routing decisions (bounded to 128 chars).
    """
    if not _plan088_rate_admit("mcp_route_advised"):
        return
    raw_event: Dict[str, Any] = {
        "action": "mcp_route_advised",
        "session_id": session_id,
        "project": project,
        "atlas_technique": _ATLAS_REGISTRY.get("mcp_route_advised", "AML.T0050"),
        "task_class": (task_class or "")[:32],
        "suggested_servers": _plan088_payload_cap((suggested_servers or "")[:128]),
        "kill_switch_overrides": _plan088_payload_cap((kill_switch_overrides or "")[:128]),
        "signal_source": (signal_source or "")[:32],
    }
    cleaned, _ = _scrub_ceo_boot_event(
        raw_event, _MCP_ROUTE_ADVISED_ALLOWLIST
    )
    _write_event(cleaned)


# === End PLAN-088 canonical-13 god-mode auto-activation block =================



# ---------------------------------------------------------------------
# PLAN-089 Wave C.5 — kernel + auth hardening emit helpers
# ---------------------------------------------------------------------
#
# ATT&CK bindings (Enterprise, not ATLAS) per ADR-121 §7:
#   T1556       — Modify Authentication Process (signer lifecycle)
#   T1565.001   — Stored Data Manipulation (canonical kernel surface)
#   T1584       — Compromise Infrastructure (IR scenario; not single-event)
#
# Rate-cap: `sentinel_signer_expiry_warned` 1×/hour throttled at the
# caller via the standard `_plan088_rate_admit` helper (best-effort —
# falls open if missing).


def _try_rate_admit(action: str) -> bool:
    """Best-effort rate gate. Returns True (admit) if no gate available."""
    try:
        gate = globals().get("_plan088_rate_admit")
        if callable(gate):
            return bool(gate(action))
    except Exception:  # pragma: no cover
        pass
    return True


def emit_kernel_extension_landed(
    *,
    plan_id: str = "",
    wave: str = "",
    entries_added: int = 0,
    cardinality_after: int = 0,
    ceremony_sha: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit kernel_extension_landed (PLAN-089 Wave A.4 / T1565.001)."""
    emit_generic(
        "kernel_extension_landed",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "kernel_extension_landed", "T1565.001"
        ),
        plan_id=plan_id,
        wave=wave,
        entries_added=int(entries_added),
        cardinality_after=int(cardinality_after),
        ceremony_sha=ceremony_sha[:64],
    )


def emit_bash_canonical_bypass_invoked(
    *,
    token_hash_prefix: str = "",
    target_path_hash: str = "",
    ticket_expires_in_s: int = 0,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit bash_canonical_bypass_invoked (PLAN-089 Wave B.4 / T1565.001).

    NEVER persist raw token. ``token_hash_prefix`` is the first 8 hex
    chars of sha256(token). FPR budget ≤3/week per ADR-121 §4.
    Sec MF-3: ``target_path_hash`` is the first 12 hex chars of
    sha256(normalized_target) — no raw filesystem path is persisted.
    """
    emit_generic(
        "bash_canonical_bypass_invoked",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "bash_canonical_bypass_invoked", "T1565.001"
        ),
        token_hash_prefix=token_hash_prefix[:16],
        target_path_hash=target_path_hash[:12],
        ticket_expires_in_s=int(ticket_expires_in_s),
    )


def emit_sentinel_signer_rotated(
    *,
    key_id: str = "",
    key_type: str = "",
    rotated_from_key_id: str = "",
    rotated_by: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_rotated (PLAN-089 Wave C.5 / T1556)."""
    emit_generic(
        "sentinel_signer_rotated",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_rotated", "T1556"
        ),
        key_id=key_id[:80],
        key_type=key_type[:16],
        rotated_from_key_id=rotated_from_key_id[:80],
        rotated_by=rotated_by[:80],
    )


def emit_sentinel_signer_expiry_warned(
    *,
    key_id: str = "",
    days_remaining: int = 0,
    expires_at_iso: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_expiry_warned (PLAN-089 Wave C.5 / T1556).

    Rate-capped 1×/hour via best-effort `_plan088_rate_admit` helper.
    """
    if not _try_rate_admit("sentinel_signer_expiry_warned"):
        return
    emit_generic(
        "sentinel_signer_expiry_warned",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_expiry_warned", "T1556"
        ),
        key_id=key_id[:80],
        days_remaining=int(days_remaining),
        expires_at_iso=expires_at_iso[:40],
    )


def emit_sentinel_signer_revoked(
    *,
    key_id: str = "",
    key_type: str = "",
    revoked_by: str = "",
    reason: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_revoked (PLAN-089 Wave C.5 / T1556).

    Separate from _rotated per R1 IDA P0 — explicit revocation channel
    for compromised-but-not-expired keys.
    """
    emit_generic(
        "sentinel_signer_revoked",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_revoked", "T1556"
        ),
        key_id=key_id[:80],
        key_type=key_type[:16],
        revoked_by=revoked_by[:80],
        reason=reason[:200],
    )


def emit_sentinel_signer_quorum_failed(
    *,
    key_id: str = "",
    reason: str = "",
    source: str = "",
    distinct_signers: int = 0,
    threshold_required: int = 0,
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_quorum_failed (PLAN-089 Wave C.5 / T1556).

    R1 TDE P0 fold — SOC consumption canary. Without this, cold-key
    compromise scenarios are undetectable until a successful rotation
    completes.
    """
    emit_generic(
        "sentinel_signer_quorum_failed",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_quorum_failed", "T1556"
        ),
        key_id=key_id[:80],
        reason=reason[:200],
        source=source[:80],
        distinct_signers=int(distinct_signers),
        threshold_required=int(threshold_required),
    )


def emit_sentinel_signer_quorum_attempted(
    *,
    distinct_signers: int = 0,
    threshold_required: int = 0,
    outcome: str = "",
    source: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit sentinel_signer_quorum_attempted (PLAN-089 Wave C.5 / T1556).

    R1 IDA P2 fold — forensic completeness regardless of outcome.
    Fires for ALL quorum invocations (success + failure), enabling
    detection of brute-force quorum probing.
    """
    emit_generic(
        "sentinel_signer_quorum_attempted",
        atlas_technique=atlas_technique or _ATLAS_REGISTRY.get(
            "sentinel_signer_quorum_attempted", "T1556"
        ),
        distinct_signers=int(distinct_signers),
        threshold_required=int(threshold_required),
        outcome=outcome[:32],
        source=source[:80],
    )

# =============================================================================
# PLAN-090 Wave A.4 + B.5 + C.2 §B + A.10 — typed emit wrappers + helpers.
# =============================================================================

_PLAN090_STREAM_BUCKETS: Dict[str, Tuple[float, int]] = {}
_PLAN090_STREAM_BURST = 10
_PLAN090_STREAM_REFILL_PER_MIN = 5
_PLAN090_PERSONA_BUCKETS: Dict[str, Tuple[float, int]] = {}
_PLAN090_PERSONA_BURST = 10
_PLAN090_PERSONA_REFILL_PER_MIN = 5
_PLAN090_BUCKET_LOCK = threading.Lock()
_VERBOSE_STREAM_ENV = "CEO_AUDIT_STREAM_VERBOSE"
_VERBOSE_STREAM_ARMED_VALUE = "1"


def is_audit_stream_verbose() -> bool:
    """ADR-123 §4 — EXACT MATCH ``CEO_AUDIT_STREAM_VERBOSE=1`` only."""
    return os.environ.get(_VERBOSE_STREAM_ENV) == _VERBOSE_STREAM_ARMED_VALUE


def streaming_rate_admit(persona: str, _now: Callable[[], float] = time.monotonic) -> bool:
    """Per-persona token bucket for streaming_token_yielded."""
    now = _now()
    with _PLAN090_BUCKET_LOCK:
        last_ts, tokens = _PLAN090_STREAM_BUCKETS.get(persona, (now, _PLAN090_STREAM_BURST))
        elapsed_min = (now - last_ts) / 60.0
        refill = int(elapsed_min * _PLAN090_STREAM_REFILL_PER_MIN)
        if refill > 0:
            tokens = min(_PLAN090_STREAM_BURST, tokens + refill)
            last_ts = now
        if tokens <= 0:
            _PLAN090_STREAM_BUCKETS[persona] = (last_ts, tokens)
            return False
        _PLAN090_STREAM_BUCKETS[persona] = (last_ts, tokens - 1)
        return True


def persona_auto_decision_rate_admit(
    persona: str, _now: Callable[[], float] = time.monotonic
) -> bool:
    """Per-persona token bucket for persona_auto_decision_emitted."""
    now = _now()
    with _PLAN090_BUCKET_LOCK:
        last_ts, tokens = _PLAN090_PERSONA_BUCKETS.get(persona, (now, _PLAN090_PERSONA_BURST))
        elapsed_min = (now - last_ts) / 60.0
        refill = int(elapsed_min * _PLAN090_PERSONA_REFILL_PER_MIN)
        if refill > 0:
            tokens = min(_PLAN090_PERSONA_BURST, tokens + refill)
            last_ts = now
        if tokens <= 0:
            _PLAN090_PERSONA_BUCKETS[persona] = (last_ts, tokens)
            return False
        _PLAN090_PERSONA_BUCKETS[persona] = (last_ts, tokens - 1)
        return True


_PHASE_C_ENFORCING_FLIPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "migration_phase", "ts_unix",
})


def emit_phase_c_enforcing_flipped(
    *,
    migration_phase: str = "first_session",
    ts_unix: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit phase_c_enforcing_flipped (PLAN-090 Wave A.4 / ADR-118-AMEND-1 §4)."""
    raw_event: Dict[str, Any] = {
        "action": "phase_c_enforcing_flipped",
        "session_id": session_id,
        "project": project,
        "migration_phase": (migration_phase or "")[:32],
        "ts_unix": int(ts_unix),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PHASE_C_ENFORCING_FLIPPED_ALLOWLIST)
    _write_event(cleaned)


_KILL_SWITCH_INVOKED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "env_value",
})


def emit_kill_switch_invoked(
    *,
    env_value: str = "0",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit kill_switch_invoked (PLAN-090 Wave A.4 / ADR-118-AMEND-1 §3)."""
    raw_event: Dict[str, Any] = {
        "action": "kill_switch_invoked",
        "session_id": session_id,
        "project": project,
        "env_value": (env_value or "")[:8],
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _KILL_SWITCH_INVOKED_ALLOWLIST)
    _write_event(cleaned)


_PERSONA_AUTO_DECISION_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "persona", "primitive", "decision", "decision_rationale",
})


def emit_persona_auto_decision_emitted(
    *,
    persona: str = "",
    primitive: str = "",
    decision: str = "",
    decision_rationale: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit persona_auto_decision_emitted (PLAN-090 Wave A.4)."""
    if not persona_auto_decision_rate_admit(persona):
        return
    raw_event: Dict[str, Any] = {
        "action": "persona_auto_decision_emitted",
        "session_id": session_id,
        "project": project,
        "atlas_technique": atlas_technique or "T1059",
        "persona": (persona or "")[:64],
        "primitive": (primitive or "")[:32],
        "decision": (decision or "")[:32],
        "decision_rationale": _plan088_payload_cap((decision_rationale or "")[:256]),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PERSONA_AUTO_DECISION_EMITTED_ALLOWLIST)
    _write_event(cleaned)


_PERSONA_AUTO_RATE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "persona", "dropped_count",
})


def emit_persona_auto_rate_capped(
    *,
    persona: str = "",
    dropped_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_auto_rate_capped (PLAN-090 Wave A.4)."""
    raw_event: Dict[str, Any] = {
        "action": "persona_auto_rate_capped",
        "session_id": session_id,
        "project": project,
        "persona": (persona or "")[:64],
        "dropped_count": max(0, int(dropped_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _PERSONA_AUTO_RATE_CAPPED_ALLOWLIST)
    _write_event(cleaned)


_STREAMING_TOKEN_YIELDED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "atlas_technique",
    "persona", "token_preview", "token_length",
})


def emit_streaming_token_yielded(
    *,
    persona: str = "",
    token: str = "",
    session_id: str = "",
    project: str = "",
    atlas_technique: Optional[str] = None,
) -> None:
    """Emit streaming_token_yielded (PLAN-090 Wave B.5 / ADR-123 §4)."""
    if not is_audit_stream_verbose():
        return
    if not streaming_rate_admit(persona):
        return
    preview = (token or "")[:16]
    raw_event: Dict[str, Any] = {
        "action": "streaming_token_yielded",
        "session_id": session_id,
        "project": project,
        "atlas_technique": atlas_technique or _ATLAS_REGISTRY.get(
            "streaming_token_yielded", "T1071"
        ),
        "persona": (persona or "")[:64],
        "token_preview": preview,
        "token_length": len(token or ""),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _STREAMING_TOKEN_YIELDED_ALLOWLIST)
    _write_event(cleaned)


_STREAMING_RATE_CAPPED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "persona", "dropped_count",
})


def emit_streaming_rate_capped(
    *,
    persona: str = "",
    dropped_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit streaming_rate_capped (PLAN-090 Wave B.5)."""
    raw_event: Dict[str, Any] = {
        "action": "streaming_rate_capped",
        "session_id": session_id,
        "project": project,
        "persona": (persona or "")[:64],
        "dropped_count": max(0, int(dropped_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _STREAMING_RATE_CAPPED_ALLOWLIST)
    _write_event(cleaned)


_MCP_BEARER_FRICTION_OBSERVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "mcp_server", "failure_reason", "replay_suspected",
})


def emit_mcp_bearer_friction_observed(
    *,
    mcp_server: str = "",
    failure_reason: str = "",
    replay_suspected: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit mcp_bearer_friction_observed (PLAN-090 Wave C.2 §B / ADR-122 §B.3)."""
    raw_event: Dict[str, Any] = {
        "action": "mcp_bearer_friction_observed",
        "session_id": session_id,
        "project": project,
        "mcp_server": (mcp_server or "")[:64],
        "failure_reason": (failure_reason or "")[:128],
        "replay_suspected": bool(replay_suspected),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _MCP_BEARER_FRICTION_OBSERVED_ALLOWLIST)
    _write_event(cleaned)


_CONFIDENCE_GATE_BASELINE_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "distinct_classes", "insufficient_data_classes", "rows_total",
})


def emit_confidence_gate_baseline_emitted(
    *,
    distinct_classes: int = 0,
    insufficient_data_classes: int = 0,
    rows_total: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit confidence_gate_baseline_emitted (PLAN-090 AMENDMENT-1 / Wave A.10)."""
    raw_event: Dict[str, Any] = {
        "action": "confidence_gate_baseline_emitted",
        "session_id": session_id,
        "project": project,
        "distinct_classes": max(0, int(distinct_classes)),
        "insufficient_data_classes": max(0, int(insufficient_data_classes)),
        "rows_total": max(0, int(rows_total)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _CONFIDENCE_GATE_BASELINE_EMITTED_ALLOWLIST)
    _write_event(cleaned)


_CAPABILITY_ROLLOUT_COMPLETE_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "tag", "auto_primitives_enforcing", "semi_primitives_advisory",
    "ac_pass_count",
})


def emit_capability_rollout_complete(
    *,
    tag: str = "",
    auto_primitives_enforcing: int = 10,
    semi_primitives_advisory: int = 3,
    ac_pass_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit capability_rollout_complete (PLAN-090 Wave D closeout)."""
    raw_event: Dict[str, Any] = {
        "action": "capability_rollout_complete",
        "session_id": session_id,
        "project": project,
        "tag": (tag or "")[:32],
        "auto_primitives_enforcing": max(0, int(auto_primitives_enforcing)),
        "semi_primitives_advisory": max(0, int(semi_primitives_advisory)),
        "ac_pass_count": max(0, int(ac_pass_count)),
    }
    cleaned, _ = _scrub_ceo_boot_event(raw_event, _CAPABILITY_ROLLOUT_COMPLETE_ALLOWLIST)
    _write_event(cleaned)

# PLAN-094 Wave A.3 — module-load wire-up for spool-writer integration.
# Executes at first import of audit_emit. Idempotent (set_forensic_emitter
# overwrites callback safely; install_exit_handlers is guarded internally).
# Codex iter-1 P1 fix: spool_writer._forensic calls cb(action, fields)
# (positional dict), but emit_generic signature is (action, **kwargs).
# Adapt via lambda so forensic events don't TypeError.
if _SPOOL_WRITER_AVAILABLE and _spool_writer is not None:
    try:
        _spool_writer.set_forensic_emitter(
            lambda _action, _fields: emit_generic(_action, **_fields)
        )
    except Exception:  # pragma: no cover
        pass
    try:
        _spool_writer.install_exit_handlers()
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# PLAN-099 (ADR-129 / ADR-135) — federation cross-machine MVP emit functions.
# Sec MF-3 caller-field whitelist (deny-by-default). 10 actions total.
# ATT&CK technique bindings: T1071.001 / T1573 / T1556.
# ---------------------------------------------------------------------------


def emit_federation_connection_accepted(
    peer_id: str,
    client_ip: str = "",
    fed_correlation_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_accepted (PLAN-099 AC2)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_accepted",
        "peer_id": str(peer_id)[:64],
        "client_ip": str(client_ip)[:64],
        "fed_correlation_id": str(fed_correlation_id)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_connection_rejected(
    reason: str,
    peer_id_cert_fingerprint: str = "",
    client_ip: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_rejected (PLAN-099 AC2)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_rejected",
        "reason": str(reason)[:64],
        "peer_id_cert_fingerprint": str(peer_id_cert_fingerprint)[:64],
        "client_ip": str(client_ip)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_connection_replay_suspected(
    peer_id: str,
    reason: str,
    client_ip: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_connection_replay_suspected (PLAN-099 AC13)."""
    event: Dict[str, Any] = {
        "action": "federation_connection_replay_suspected",
        "peer_id": str(peer_id)[:64],
        "reason": str(reason)[:64],
        "client_ip": str(client_ip)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_expiry_warned(
    peer_id: str,
    days_remaining: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_expiry_warned (PLAN-099 AC11 — 14d before expiry)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_expiry_warned",
        "peer_id": str(peer_id)[:64],
        "days_remaining": int(days_remaining),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_rotated(
    peer_id: str,
    old_fingerprint_prefix: str = "",
    new_fingerprint_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_rotated (PLAN-099 AC11)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_rotated",
        "peer_id": str(peer_id)[:64],
        "old_fingerprint_prefix": str(old_fingerprint_prefix)[:16],
        "new_fingerprint_prefix": str(new_fingerprint_prefix)[:16],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_cert_revoked(
    peer_id: str,
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_cert_revoked (PLAN-099 AC11)."""
    event: Dict[str, Any] = {
        "action": "federation_cert_revoked",
        "peer_id": str(peer_id)[:64],
        "reason": str(reason)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_write_attempt_blocked(
    method: str,
    path: str,
    peer_id_cert_fingerprint: str = "",
    client_ip: str = "",
    fed_correlation_id: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_write_attempt_blocked (PLAN-099 AC15 — method allowlist)."""
    event: Dict[str, Any] = {
        "action": "federation_write_attempt_blocked",
        "method": str(method)[:16],
        "path": str(path)[:128],
        "peer_id_cert_fingerprint": str(peer_id_cert_fingerprint)[:64],
        "client_ip": str(client_ip)[:64],
        "fed_correlation_id": str(fed_correlation_id)[:64],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_lan_bind_denied(
    bind_host: str,
    resolved_ip: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_lan_bind_denied (PLAN-099 AC3 — non-loopback bind gate)."""
    event: Dict[str, Any] = {
        "action": "federation_lan_bind_denied",
        "bind_host": str(bind_host)[:64],
        "resolved_ip": str(resolved_ip)[:64],
        "reason": str(reason)[:96],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_autonomous_call_blocked(
    call_site: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_autonomous_call_blocked (PLAN-099 AC18 — import-graph denylist)."""
    event: Dict[str, Any] = {
        "action": "federation_autonomous_call_blocked",
        "call_site": str(call_site)[:128],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_federation_enable_sentinel_invalid(
    sentinel_kind: str,
    reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit federation_enable_sentinel_invalid (PLAN-099 AC22 — 2-stage failure modes)."""
    event: Dict[str, Any] = {
        "action": "federation_enable_sentinel_invalid",
        "sentinel_kind": str(sentinel_kind)[:32],
        "reason": str(reason)[:96],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# PLAN-104 Wave A.3 + A.4 — persona-demand ledger emit functions + allowlists.
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-104-WAVE-A-
# AUDIT-EMIT-EXTENSION + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT (S123 pattern).
# Sec MF-3 caller-field deny-by-default per action.
# Field bodies NEVER persist raw target paths or branch refs.
# Codex iter-1 P0 #4 fold: target_ref_hash is re-derived defensively
# from a 12-hex check (strip + ascii-only); caller-supplied non-hex
# values fall back to sha256[:12] of the input. This blocks an LLM06
# side-channel where a hostile caller passes raw text as
# `target_ref_hash`.
# -----------------------------------------------------------------------------

def _persona_demand_safe_hash(raw: str) -> str:
    """Return 12-hex target_ref_hash. Re-hashes if caller value not valid hex."""
    import hashlib
    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:12]


_PERSONA_DEMAND_OPENED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "target_ref_hash", "match_window_hours",
})
_PERSONA_DEMAND_MATCHED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "actual_persona", "latency_ms",
    "match_modality",  # PLAN-132 / ADR-145 — {native_spawn, codex_review}
})
_PERSONA_DEMAND_UNMET_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "target_ref_hash", "window_expired_at",
})
_PERSONA_DEMAND_WAIVED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "demand_id", "demand_event_type", "expected_persona",
    "waive_reason",
})

# PLAN-106 Wave C — Sec MF-3 deny-by-default allowlist for
# persona_coverage_synthesized. Caller-supplied: archetype, task_type,
# cell_id (≤32 byte sha256[:8] hash for stable 4×4 cell index),
# source ("dispatch" | "canonical_edit"). NO raw prompt body, NO file
# path, NO description preview — LLM06 side-channel hold.
_PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "archetype", "task_type", "cell_id", "source",
})

# Closed enums for archetype + task_type (deny free-text per PLAN-093
# Wave C.5 4-persona × 4-task matrix). Mirrors ceo-boot.py:
# _VETO_FLOOR_PERSONAS + _PERSONA_TASK_TYPES at module-level so the
# allowlist scrub stays self-contained.
_PERSONA_COVERAGE_ARCHETYPES = frozenset({
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer",
})
_PERSONA_COVERAGE_TASK_TYPES = frozenset({
    "review", "vet", "test", "detect",
})
_PERSONA_COVERAGE_SOURCES = frozenset({
    "dispatch", "canonical_edit",
})

# Closed enum for waive_reason. Free-text values rejected pre-emit.
_PERSONA_WAIVE_REASONS = frozenset({
    "docs-only",
    "generated-or-vendored",
    "emergency-hotfix",
    "explicit-skip",
})


def emit_persona_demand_opened(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    target_ref_hash: str,
    match_window_hours: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_opened (PLAN-104 Wave A; S134 R2 ACCEPT).

    Fired by persona_demand_scan.py when a new demand_id is detected
    within the bounded scan horizon. target_ref_hash is pre-computed
    sha256[:12] of the NFKC-normalized target_ref (path OR branch_ref);
    raw value NEVER persisted (LLM06 hold).
    """
    event: Dict[str, Any] = {
        "action": "persona_demand_opened",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "target_ref_hash": _persona_demand_safe_hash(target_ref_hash),
        "match_window_hours": int(match_window_hours),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_matched(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    actual_persona: str,
    latency_ms: int,
    session_id: str = "",
    project: str = "",
    match_modality: str = "native_spawn",
) -> None:
    """Emit persona_demand_matched (PLAN-104 Wave A; S134 R2 P1 #3 fold).

    Native strict-match: actual_persona == expected_persona (S134 R2 Q4 — no peer
    substitution). PLAN-132 / ADR-145 adds ONE recognized exception: a cross-model
    Codex review may satisfy a `code-reviewer` demand, emitted with
    match_modality="codex_review" and actual_persona="code-reviewer" (so the
    published SPEC invariant actual_persona == expected_persona still HOLDS). The
    relaxation is code-reviewer-ONLY and is enforced by the resolver's literal
    guard; this emitter only records the modality. An invalid modality coerces to
    the safe default "native_spawn" (S172: never echo a rejected value).
    """
    mm = match_modality if match_modality in _PERSONA_MATCH_MODALITY_ENUM else "native_spawn"
    event: Dict[str, Any] = {
        "action": "persona_demand_matched",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "actual_persona": str(actual_persona)[:64],
        "latency_ms": int(latency_ms),
        "match_modality": mm,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_unmet(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    target_ref_hash: str,
    window_expired_at: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_unmet (PLAN-104 Wave A).

    Idempotency contract: at most ONE per demand_id (dedup at
    persona_demand_resolver scan time via terminal-event index).
    """
    event: Dict[str, Any] = {
        "action": "persona_demand_unmet",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "target_ref_hash": _persona_demand_safe_hash(target_ref_hash),
        "window_expired_at": str(window_expired_at)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_persona_demand_waived(
    demand_id: str,
    demand_event_type: str,
    expected_persona: str,
    waive_reason: str,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit persona_demand_waived (PLAN-104 Wave A; S134 R2 P1 #2 fold).

    waive_reason MUST be one of the closed enum
    `_PERSONA_WAIVE_REASONS` (free-text rejected pre-emit; invalid
    values dropped to a known-bad sentinel for forensic trace
    without polluting the enum surface).
    """
    reason = str(waive_reason)[:32]
    if reason not in _PERSONA_WAIVE_REASONS:
        reason = "invalid-enum"
    event: Dict[str, Any] = {
        "action": "persona_demand_waived",
        "demand_id": str(demand_id)[:16],
        "demand_event_type": str(demand_event_type)[:32],
        "expected_persona": str(expected_persona)[:64],
        "waive_reason": reason,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# PLAN-090-FOLLOWUP Wave A — claim producer pair (S138 R2 ACCEPT).
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-090-FOLLOWUP-
# PRODUCER-PAIR + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
# Sec MF-3 caller-field deny-by-default per action.
# Raw claim bodies + verifier free-text NEVER persisted (LLM06 hold).
# -----------------------------------------------------------------------------

def _safe_claim_id_hash(raw: str) -> str:
    """Return collision-safe claim_id of form '<claim_type>:<12-hex>'.

    Accepts pre-formatted claim_id ('<type>:<12-hex>') ONLY if the
    prefix matches the KNOWN_KINDS grammar `^[a-z_]{1,32}$`; else
    rehashes raw via NFKC + sha256[:12] (Codex iter-1 P0-3 fold —
    prior version accepted ARBITRARY prefix, allowing a direct
    `emit_generic(claim_id="password=hunter2:deadbeefdead")` to
    persist the secret unchanged through the "defensive" path).

    Force `unknown:` prefix on rehash (no inheritance of caller
    prefix; mirrors `_persona_demand_safe_hash` strictness).
    """
    import hashlib
    import re
    import unicodedata
    s = str(raw or "").strip()
    _PREFIX_RE = re.compile(r"^[a-z_]{1,32}$")
    if ":" in s:
        prefix, _, suffix = s.partition(":")
        if (
            _PREFIX_RE.match(prefix)
            and len(suffix) == 12
            and all(c in "0123456789abcdef" for c in suffix.lower())
        ):
            return f"{prefix}:{suffix.lower()}"
    norm = unicodedata.normalize("NFKC", s)
    digest = hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"unknown:{digest}"


def _safe_payload_hash(raw: str) -> str:
    """Return bare 12-hex payload_hash.

    Distinct from `_safe_claim_id_hash` (P0-4 fold): the `payload_hash`
    audit field is the bare digest with NO `<type>:` prefix, so a
    pre-hashed caller value of exactly 12-hex MUST round-trip unchanged
    (otherwise determinism breaks between call sites — producer in
    `confidence_gate.py:_format_json` and re-hash defense at
    `emit_generic`).
    """
    import hashlib
    import unicodedata
    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    norm = unicodedata.normalize("NFKC", s)
    return hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()[:12]


def _safe_verifier_outcome(raw: str, claim_args: str = "") -> str:
    """Return redacted + truncated verifier_outcome (security iter-1 P1-B fold).

    `r.detail` is verifier free-text output (e.g. `f"path {path} does
    not exist"` for path_exists verifier). It echoes `r.claim.args`
    fragments and can leak absolute paths, username, or claim payload
    via the free-text channel.

    Pipeline (defense-in-depth):
      1. PII redact via shipped `_lib.redact.redact_secrets` — fail-
         CLOSED to empty string if redactor not importable.
      2. Overlap scrub: any contiguous substring of length >=8 chars
         that also appears in `claim_args` is replaced with
         `<redacted>` (catches r.detail echoing r.claim.args).
      3. NFKC normalize + clip to 64 chars.
    """
    try:
        from _lib.redact import redact_secrets as _redact
        s = _redact(str(raw or ""))
    except Exception:
        # Fail-CLOSED on missing redactor.
        return ""
    ca = str(claim_args or "")
    if ca:
        for i in range(0, max(0, len(ca) - 8 + 1)):
            window = ca[i:i + 8]
            if window in s:
                s = s.replace(window, "<redacted>")
    import unicodedata
    return unicodedata.normalize("NFKC", s)[:64]


_CLAIM_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "claim_id", "claim_type", "severity",
    "verifier_kind", "agent_name", "source",
    "line_num", "payload_hash",
    "kind_supported",
})

_CONFIDENCE_GATE_VERDICT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "claim_id", "verdict", "was_false_positive",
    "verifier_kind", "verifier_outcome",
    "agent_name", "source",
    "kind_supported",
})

# Closed enum for verdict. Per P1-1 fold: invalid values fall back to
# "fail" (non-inflammatory) NOT "refuted" — "refuted" is the FP signal
# in backfill line 134 and a parser sentinel must NOT pollute the FPR
# numerator.
_CONFIDENCE_GATE_VERDICTS = frozenset({"pass", "fail", "refuted"})

# Closed enum for severity (anchored to ADR-018 claim taxonomy).
_CLAIM_SEVERITIES = frozenset({"info", "warn", "critical"})


def emit_claim_emitted(
    claim_id: str,
    claim_type: str,
    severity: str,
    verifier_kind: str,
    payload_hash: str,
    kind_supported: bool,
    line_num: int = 0,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit claim_emitted (PLAN-090-FOLLOWUP Wave A; S138 R2).

    Fired by check_confidence_gate.py once per CLAIM token the gate
    evaluates. payload_hash is sha256[:12] of NFKC-normalized claim
    body; raw claim text NEVER persisted (LLM06 hold).

    kind_supported is the boolean shipped as the extraction-FP signal
    (P0-1 fold). False means the CLAIM:<kind>:... token used a kind
    NOT in `confidence_gate.KNOWN_KINDS`; the gate cannot verify it
    and treats it as an extraction-level false-positive.

    Severity is the ADR-018 closed enum {info, warn, critical};
    invalid values dropped to 'info' (forensic-safe sentinel).
    """
    sev = str(severity)[:16]
    if sev not in _CLAIM_SEVERITIES:
        sev = "info"
    event: Dict[str, Any] = {
        "action": "claim_emitted",
        "claim_id": _safe_claim_id_hash(claim_id),
        "claim_type": str(claim_type)[:32],
        "severity": sev,
        "verifier_kind": str(verifier_kind)[:32],
        "payload_hash": _safe_payload_hash(payload_hash),
        "kind_supported": bool(kind_supported),
        "line_num": int(line_num),
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate_verdict(
    claim_id: str,
    verdict: str,
    was_false_positive: bool,
    kind_supported: bool,
    verifier_kind: str = "",
    verifier_outcome: str = "",
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit confidence_gate_verdict (PLAN-090-FOLLOWUP Wave A).

    Fired by check_confidence_gate.py AFTER claim_emitted, paired via
    claim_id.

    verdict is the closed enum {pass, fail, refuted}; invalid values
    dropped to 'fail' (P1-1 fold — NOT 'refuted', because backfill
    treats 'refuted' as an FP signal and a parser-sentinel must NOT
    pollute the FPR numerator).

    was_false_positive is the boolean PLAN-100 baseline analysis
    consumes (paired with claim_id to compute FPR per class). PLAN-090-
    FOLLOWUP shipping rule (P0-1 fold — no chicken-and-egg with PLAN-
    100 drift detector):

      was_false_positive = (NOT kind_supported)

    Caller is expected to derive this at the producer site
    (`confidence_gate._format_json`); the emit fn does not enforce
    the rule itself — only the emit signature carries both fields
    independently to allow future expansion when PLAN-100 Wave B.3
    drift detector emits additional verdicts with was_false_positive=True
    from cross-verifier disagreement.
    """
    v = str(verdict)[:16].lower()
    if v not in _CONFIDENCE_GATE_VERDICTS:
        v = "fail"
    event: Dict[str, Any] = {
        "action": "confidence_gate_verdict",
        "claim_id": _safe_claim_id_hash(claim_id),
        "verdict": v,
        "was_false_positive": bool(was_false_positive),
        "kind_supported": bool(kind_supported),
        "verifier_kind": str(verifier_kind)[:32],
        "verifier_outcome": _safe_verifier_outcome(verifier_outcome, ""),
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# PLAN-100 Wave B — per-class block-mode (S139 R2 ACCEPT; ADR-019-AMEND-1).
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-100-WAVE-B-
# AUDIT-EMIT-EXTENSION + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
# Sec MF-3 caller-field deny-by-default per action.
# -----------------------------------------------------------------------------

_CONFIDENCE_GATE_BLOCKED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "agent_name",
    "source",
    "blocking_classes",   # list[str] of HIGH_CONFIDENCE_BLOCK kinds that fired
    "fail_count",         # int — total fail_count from gate payload
    "hmac",
    "hmac_error",
    "record_id",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "wall_ns",
    "pid",
    "spool_uuid",
    "ordinal_within_file",
    "_drain_sha256",
    "_drain_epoch",
    "event_schema",
})

_CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "agent_name",
    "source",
    "drift_class",        # str — class with drift detected
    "window_days",        # int — rolling window (7 in v1.34.0)
    "fpr_bps",            # int — observed FPR in basis points
    "threshold_bps",      # int — drift threshold (200 = 2.0%)
    "sample_n",           # int — events in window
    "auto_demote_at",     # str ISO8601 — wall-clock when auto-demotion fires
    "hmac",
    "hmac_error",
    "record_id",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "wall_ns",
    "pid",
    "spool_uuid",
    "ordinal_within_file",
    "_drain_sha256",
    "_drain_epoch",
    "event_schema",
})


def emit_confidence_gate_blocked(
    blocking_classes,
    fail_count,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `confidence_gate_blocked` when ADR-019-AMEND-1 per-class
    block-mode fires. Caller fields scrubbed via
    `_CONFIDENCE_GATE_BLOCKED_ALLOWLIST`.

    `blocking_classes` is a list[str] of HIGH_CONFIDENCE_BLOCK kinds
    that fired (sorted/deduped by caller; defense-in-depth re-validation
    at emit_generic dispatch).
    """
    classes = []
    if isinstance(blocking_classes, (list, tuple)):
        for c in blocking_classes:
            if isinstance(c, str) and 0 < len(c) <= 64:
                classes.append(c)
    try:
        n_fail = int(fail_count)
    except (TypeError, ValueError):
        n_fail = 0
    event: Dict[str, Any] = {
        "action": "confidence_gate_blocked",
        "blocking_classes": classes,
        "fail_count": n_fail,
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate_fp_drift_detected(
    drift_class: str,
    window_days,
    fpr_bps,
    threshold_bps,
    sample_n,
    auto_demote_at: str,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `confidence_gate_fp_drift_detected` when drift detector
    observes 7d rolling FPR exceeding threshold for a
    HIGH_CONFIDENCE_BLOCK class. Per ADR-019-AMEND-1 §6.

    Fail-CLOSED on malformed numeric fields (no emit) to avoid
    polluting drift signal with garbage.
    """
    try:
        n_w = int(window_days)
        n_fpr = int(fpr_bps)
        n_thr = int(threshold_bps)
        n_s = int(sample_n)
    except (TypeError, ValueError):
        return
    event: Dict[str, Any] = {
        "action": "confidence_gate_fp_drift_detected",
        "drift_class": str(drift_class)[:64],
        "window_days": n_w,
        "fpr_bps": n_fpr,
        "threshold_bps": n_thr,
        "sample_n": n_s,
        "auto_demote_at": str(auto_demote_at)[:32],
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


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
