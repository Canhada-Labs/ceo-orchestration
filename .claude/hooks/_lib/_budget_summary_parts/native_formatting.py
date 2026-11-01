from __future__ import annotations

def _format_native_block(native: Dict[str, Any]) -> List[str]:
    """Human rendering of the W1.2 native cross-check block.

    UNMATCHED residue from BOTH sides always appears — aggregated by
    (session, rail, agent_type) so every unmatched spawn is represented
    — each section headed by its COUNT. Full per-spawn detail lives in
    the ``--json`` output.
    """
    lines: List[str] = []
    lines.append("")
    lines.append(
        "Native cross-check (PLAN-178 W1.2 — cross-check, not authority-swap):"
    )
    lines.append(f"  Native root     : {native.get('native_root')}")
    if native.get("dormant"):
        lines.append(f"  Status          : DORMANT — {native.get('note')}")
        return lines
    lines.append(
        f"  Native spawns   : {native['native_spawn_count']:,} "
        f"(task={native['native_task_spawns']:,}, "
        f"workflow={native['native_workflow_spawns']:,})"
    )
    lines.append(
        f"  Audit spawns    : {native['audit_spawn_count']:,} "
        f"(agent_spawn events in scope)"
    )
    lines.append(
        f"  Matched pairs   : {native['matched_count']:,} "
        f"(token-comparable: {native['comparable_pair_count']:,})"
    )
    tok = native.get("native_tokens") or {}
    lines.append(
        f"  Native tokens   : in={tok.get('in', 0):,} out={tok.get('out', 0):,} "
        f"cache_creation={tok.get('cache_creation', 0):,} "
        f"cache_read={tok.get('cache_read', 0):,}"
    )
    cost = native.get("native_cost_usd")
    tbd = int(native.get("native_cost_tbd_spawns") or 0)
    if cost is None and tbd:
        cost_col = f"TBD ({tbd:,} spawns without resolvable model/price)"
    elif tbd:
        cost_col = (
            f"${cost:,.4f} + TBD ({tbd:,} spawns without resolvable "
            f"model/price)"
        )
    elif cost is None:
        cost_col = "-"
    else:
        cost_col = f"${cost:,.4f}"
    lines.append(f"  Native cost     : {cost_col}")
    lines.append(
        "                    (cache priced as input-equivalents: read @0.10x"
        " — " + _cache_read_exceptions_text() + " —,"
        " write @1.25x — 5m-TTL assumption, docs/provider-pricing.md)"
    )
    unreadable = int(native.get("native_transcripts_unreadable", 0) or 0)
    if unreadable:
        lines.append(
            f"  Skipped         : {unreadable} unreadable native transcript(s)"
            " excluded from totals and matching"
        )
    max_div = native.get("max_divergence_pct_by_rail") or {}
    div_cols = []
    for rail in ("task", "workflow"):
        v = max_div.get(rail)
        div_cols.append(f"{rail}={v:.2f}%" if v is not None else f"{rail}=-")
    div_note = ""
    if native["comparable_pair_count"] == 0:
        div_note = (
            " (no comparable pairs: audit-log spawn tokens are null in scope)"
        )
    lines.append(f"  Max divergence  : {' '.join(div_cols)}{div_note}")

    def _grouped(rows: List[Dict[str, Any]], with_rail: bool) -> List[str]:
        counts: Dict[Tuple[str, ...], int] = {}
        for r in rows:
            sess = str(r.get("session_id") or "(unknown)")[:8]
            if with_rail:
                gkey = (sess, str(r.get("rail") or "?"), str(r.get("agent_type") or "?"))
            else:
                gkey = (sess, str(r.get("agent_type") or "?"))
            counts[gkey] = counts.get(gkey, 0) + 1
        out = []
        for gkey in sorted(counts):
            if with_rail:
                out.append(
                    f"    {gkey[0]:<8}  {gkey[1]:<8}  {gkey[2]:<28}  "
                    f"x{counts[gkey]}"
                )
            else:
                out.append(f"    {gkey[0]:<8}  {gkey[1]:<38}  x{counts[gkey]}")
        return out

    un_nat = native.get("unmatched_native") or []
    lines.append(
        f"  UNMATCHED — native side (no audit-log counterpart): "
        f"{native['unmatched_native_count']:,}"
    )
    if un_nat:
        lines.extend(_grouped(un_nat, with_rail=True))
    else:
        lines.append("    (none)")
    un_aud = native.get("unmatched_audit") or []
    lines.append(
        f"  UNMATCHED — audit-log side (no native counterpart): "
        f"{native['unmatched_audit_count']:,}"
    )
    if un_aud:
        lines.extend(_grouped(un_aud, with_rail=False))
    else:
        lines.append("    (none)")
    lines.append(
        "  NOTE: the native source never replaces the audit-log totals "
        "above; the residue is shown in full because silencing it would "
        "fake a low divergence."
    )
    return lines
