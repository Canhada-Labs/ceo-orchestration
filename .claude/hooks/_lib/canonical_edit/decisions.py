"""Mechanically extracted canonical-edit declarations."""
from __future__ import annotations

def _emit_unlock_audit(target_rel: str, unlock_reason: str) -> None:
    """Best-effort audit emission for sentinel env-override grants.

    Session 75 Codex Finding 8 closure (extracted helper for PLAN-064
    Option D Tier-1/Tier-2 DRY): docstring promised
    `veto_triggered(reason_code=sentinel_unlock_used)` event when the
    env-var override path grants a canonical edit. Emission failures
    never block (advisory).
    """
    try:
        from _lib import audit_emit as _audit_emit_unlock
        _audit_emit_unlock.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="sentinel_unlock_used",
            reason_preview=(
                f"sentinel env-override granted edit to {target_rel}; "
                f"reason={unlock_reason!r}"
            ),
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            caller=os.environ.get("CLAUDE_AGENT_NAME", "ceo"),
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass  # advisory; emission failure never blocks


def decide(
    *,
    file_path: str,
    repo_root: Path,
) -> str:
    """Pure decision function.

    Returns the JSON payload to write to stdout.
    """
    # PLAN162_FIX_S2R2 — per-decision state, so an in-process caller
    # (``check_pair_rail``, the tests) never inherits a previous event's
    # unlock diagnosis.
    _reset_unlock_trust_diag()

    if not file_path:
        return _emit_allow()

    if not _is_canonical(file_path, repo_root):
        return _emit_allow()

    # Confirmed canonical. Re-derive the repo-relative form for sentinel
    # matching via the SAME dual-anchor resolution as _is_canonical
    # (PLAN160_FIX_D), so the path is paired with the rel that classified
    # it (a repo_root-anchored canonical path would otherwise fault the
    # historical CWD-anchored resolve and route a clean sentinel-block
    # through the finding-C fault branch).
    rel = _canonical_rel(file_path, repo_root)
    if rel is None:
        # PLAN160_FIX_C (finding C): fail-CLOSED. ``_is_canonical`` (guard
        # above) returned True, yet no anchoring yields a canonical rel
        # HERE — only a same-process TOCTOU between those two resolves can
        # reach this. The historical code fail-OPENED via
        # ``return _emit_allow()`` on the resolve fault; a confirmed-canonical
        # path MUST block (PLAN-045 F-01-07). Dead in same-process terms;
        # defense-in-depth.
        return _emit_block(
            reason=(
                "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — a "
                "confirmed-canonical path could not be resolved repo-relative "
                "for sentinel matching (same-process TOCTOU). PLAN-045 "
                "F-01-07 / PLAN-160 finding C fail-closed."
            )
        )

    sentinels = _find_sentinels(repo_root)
    for sentinel in sentinels:
        # PLAN162_FIX_1 (C2) — wall-clock deadline, checked at the TOP of
        # the sentinel loop and fail-CLOSED. Never "allow because we ran
        # out of time", and never "stop checking sentinels" (a cap would
        # drop the highest-numbered pack, i.e. the ceremony the Owner just
        # signed — self-DoS with the signature in hand).
        if _wall_budget_expired():
            return _emit_block(reason=_WALL_DEADLINE_BLOCK_REASON)
        if _sentinel_grants_path(sentinel, rel):
            # PLAN-106 Wave C — persona coverage emit at canonical-edit
            # sentinel-approved allow path.
            _emit_persona_coverage_synthesized(rel_path=rel)
            return _emit_allow(
                system_message=(
                    f"CANONICAL-EDIT: allowed via sentinel "
                    f"{sentinel.relative_to(repo_root)}"
                )
            )

    # PLAN162_FIX_1 (Codex P1 fold) — the budget can run out DURING the
    # last sentinel's verification, after the final top-of-loop poll. Both
    # outcomes block, but only this one names the cause and carries the
    # recovery route; the generic block below would tell the Owner to
    # declare a path that IS already declared.
    if _wall_budget_expired():
        return _emit_block(reason=_WALL_DEADLINE_BLOCK_REASON)

    return _emit_block(
        reason=(
            f"CANONICAL-EDIT-BLOCKED: '{rel}' is a canonical governance "
            "path. Edits require an Owner-signed sentinel at "
            ".claude/plans/PLAN-NNN/architect/round-N/approved.md with "
            f"this path declared in the Scope: block. See ADR-010."
            # PLAN162_FIX_S2R2 (P1-3): when an unlock window IS armed and
            # the trust rail is what refused, say so and name the value.
            + _unlock_trust_hint()
        )
    )


def _candidate_is_granted(path_str: str, repo_root: Path, sentinels) -> bool:
    """PLAN160_FIX_A helper — pure grant predicate for one candidate.

    True iff the (assumed-canonical) ``path_str`` resolves repo-relative
    AND some sentinel in ``sentinels`` grants that repo-relative path. A
    resolve fault on a canonical path is NOT a grant → returns False, so
    the caller treats the candidate as the offender and blocks
    (fail-CLOSED, mirroring finding C's decide() contract).

    Pure: NO side effects (does not emit persona coverage or audit) — those
    stay once-per-event concerns owned by ``decide()``. Uses the SAME
    ``_canonical_rel`` anchoring as ``_is_canonical`` and ``decide()``
    (PLAN160_FIX_D), so grant is checked against the exact rel that
    classified the candidate canonical; a candidate with no canonical rel
    is conservatively treated as ungranted (→ offender → block).
    """
    rel = _canonical_rel(path_str, repo_root)
    if rel is None:
        return False
    for sentinel in sentinels:
        if _sentinel_grants_path(sentinel, rel):
            return True
    return False


def _safe_sentinel_count(repo_root: Path) -> int:
    """Best-effort sentinel count for the veto-audit breadcrumb.

    PLAN160_FIX_A (codex pair-rail HIGH#2): the audit breadcrumb must never
    let a ``_find_sentinels`` fault (a malformed sentinel dir, an OSError
    walking the tree) propagate out of ``main()`` and produce a ZERO-emit
    hook on a governance event. Returns 0 on any fault — the count is
    forensic only; the block/allow decision is already made.
    """
    try:
        return len(_find_sentinels(repo_root))
    except Exception:
        return 0


def _block_reason_code(reason: str) -> str:
    """Which ``reason_code`` the CHAIN gets for a block decision.

    PLAN162_FIX_1B (r8 P2). ``_emit_block`` already names the class in the
    DECISION text, but the audit breadcrumb hard-coded
    ``canonical_edit_unsigned`` for every block — so the wall-deadline
    fail-CLOSED (and the pre-existing over-cap / scan-fault blocks) landed
    in the HMAC chain labelled as an unsigned edit: indistinguishable from
    a legitimate missing-sentinel block, and therefore UNCOUNTABLE for the
    ADR-110-AMEND-2 §3 censorship RATE. ``wave-readonly-monitor.py``
    already lists ``canonical_edit_hook_fault`` in
    ``_LAYER_3A_REASON_CODES``: a consumer with zero producers.

    Closed 2-value derivation, read off the decision this hook itself
    built — never off attacker-shaped input.
    """
    return (
        "canonical_edit_hook_fault"
        if "canonical_edit_hook_fault" in (reason or "")
        else "canonical_edit_unsigned"
    )


def _audit_block(
    rel: str,
    sentinels_count: int,
    reason_code: str = "canonical_edit_unsigned",
) -> None:
    """Best-effort emit of veto_triggered event. Never raises.

    ``reason_code`` defaults to the historical value, so every existing
    caller is byte-identical. NO new ACTION is invented — ``veto_triggered``
    stays the registered action, same precedent as
    ``_audit_registry_unreadable``'s ``session_roots_registry_unreadable``.
    """
    try:
        from _lib import audit_emit
        if reason_code == "canonical_edit_unsigned":
            _preview = (
                f"blocked edit to {rel}; {sentinels_count} sentinel(s) checked, "
                "none grant this path"
            )
        else:
            _preview = (
                f"blocked edit to {rel}; fail-CLOSED before the sentinel sweep "
                f"could complete ({sentinels_count} sentinel(s) on disk)"
            )
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code=reason_code,
            reason_preview=_preview,
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return

__all__ = ['_emit_unlock_audit', 'decide', '_candidate_is_granted', '_safe_sentinel_count', '_block_reason_code', '_audit_block']
