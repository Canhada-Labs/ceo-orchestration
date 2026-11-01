"""Pair rail.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_dispatcher_route', 'emit_pair_rail_case', 'emit_pair_rail_promotion', 'emit_token_budget_guard_paused', 'emit_anti_ceo_overhead_block', 'emit_anti_ceo_overhead_override_used', 'emit_smart_loading_resolved')

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


# QDSAA-FUNCAO-LONGA: Preserve the existing event schema and its field coercion together during relocation.
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


# QDSAA-FUNCAO-LONGA: Preserve the existing event schema and its field coercion together during relocation.
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
    review_id: str = "",
    timeout_ms: int = 0,
    project: str = "",
) -> None:
    """Emit ``pair_rail_case`` event from check_pair_rail.py:_decide_with_matrix.

    ADR-110-AMEND-2 §1.6: ``timeout_ms`` is the EFFECTIVE post-clamp codex
    budget this invocation ran under, as INTEGER MILLISECONDS (bounded
    `[0, 6_000_000]`, off-shape COERCED to 0). NOT float seconds — see
    `emit_pair_rail_review_expected` for why a float would drop the whole
    event. It disambiguates a case F produced by a sub-floor
    `CEO_PAIR_RAIL_TIMEOUT_S` export from a genuine Codex outage (§4(i)).

    PLAN-161 C5 r5 F2 + r6 F2: ``review_id`` (EXACTLY 16 lowercase hex or
    exactly ""; the RAW value is validated before any bounding — off-shape
    incl. oversize is DROPPED to "", never truncated) is the
    per-invocation correlation key minted by ``_decide()`` at review entry
    — identical on this case emit and the same invocation's
    ``pair_rail_review_expected``, so the /ceo-boot liveness deficit pairs
    a specific expected with its OWN case (invocation-exact; bucket
    counting could not). "" = legacy/id-less emit (falls back to the r4
    (session, file-hash) bucket heuristic).
    """
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
    # r5 F2 + r6 F2 — the SAME exact-16-or-empty gate as the module-level
    # _PAIR_RAIL_REVIEW_ID_RE, applied to the RAW value (no truncation:
    # truncate-then-accept collapsed distinct oversize ids to one key).
    raw_rid = review_id if isinstance(review_id, str) else ""
    safe_rid = raw_rid if _PAIR_RAIL_REVIEW_ID_RE.fullmatch(raw_rid) else ""
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
        review_id=safe_rid,
        # ADR-110-AMEND-2 §1.6 — bounded integer ms, never float seconds.
        timeout_ms=_coerce_pair_rail_timeout_ms(timeout_ms),
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
