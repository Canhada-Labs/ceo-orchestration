"""Operations.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_cache_discipline_alerted', '_FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST', 'emit_first_run_wizard_dispatched', '_ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST', 'emit_estimate_calibrator_pipeline_run', '_STDLIB_VIOLATION_ALLOWLIST', '_SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST', 'emit_subagent_findings_partial_drop', '_ANTHROPIC_429_OBSERVED_ALLOWLIST', 'emit_anthropic_429_observed', '_OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST', '_GIT_INDEX_LOCK_RETRY_ALLOWLIST', 'emit_git_index_lock_retry', '_CODEX_INVOKE_DISPATCHED_ALLOWLIST', 'emit_codex_invoke_dispatched', '_TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST', 'emit_tier_policy_misrouting_advised', '_TIER_POLICY_LOADER_FALLBACK_REASON_CODES', '_TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST', 'emit_tier_policy_loader_fallback_observed', '_AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS', '_AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES', '_AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST')

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
