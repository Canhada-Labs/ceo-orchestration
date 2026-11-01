"""Routing.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_to_basis_points', 'emit_model_routing_advised', 'emit_estimate_drift_detected', 'emit_estimate_drift_systematic_bias', 'emit_ceo_boot_task_candidate_emitted', 'emit_pair_rail_review_passed', 'emit_pair_rail_codex_unavailable', 'emit_pair_rail_codex_violation', 'emit_pair_rail_sentinel_bypass', 'emit_pair_rail_codex_injection_detected')

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
