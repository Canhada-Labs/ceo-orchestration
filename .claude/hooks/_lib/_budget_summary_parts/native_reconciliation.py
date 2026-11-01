from __future__ import annotations

MEMORY_CLAIM_LOW_USD = 1003.0
MEMORY_CLAIM_HIGH_USD = 1543.0
MEMORY_CLAIM_PASS_RATIO_LOW = 0.5
MEMORY_CLAIM_PASS_RATIO_HIGH = 1.5

def _read_native_spawn(
    transcript: Path,
    rail: str,
    session_id: str,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    counters: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    """Read ONE native spawn (transcript + tolerant meta pairing).

    Tolerant by doctrine (probe §handoff item 3): a missing meta, a
    malformed/truncated line (live session appending), or a missing
    field degrades the record — it never raises. Model precedence:
    ``meta.model`` first, else the first ``message.model`` seen in the
    transcript (the workflow-path metas carry NO model at all). A
    ``meta.model`` that resolves to NOTHING (a bare family alias such as
    ``fable`` once the registry holds two Fable ids — ADR-149 Amendment
    2) falls back to the transcript's exact ``message.model``: exact
    evidence beats an ambiguous alias, and neither is ever guessed.
    """
    stem = transcript.name[: -len(".jsonl")]
    meta_path = transcript.with_name(stem + ".meta.json")
    agent_type = "(unknown)"
    meta_model: Optional[str] = None
    meta_description: Optional[str] = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = None
        if isinstance(meta, dict):
            # Hard fingerprint invariants (substrate-watch cc_native_usage,
            # 416/416 measured; codex S306 r3 P2 cure — same sonda as the
            # standalone puller): a meta that parses but lost either field
            # is schema drift, counted so native_cross_check can degrade.
            if "agentType" not in meta or "spawnDepth" not in meta:
                if counters is not None:
                    counters["meta_invariant_missing"] = (
                        counters.get("meta_invariant_missing", 0) + 1
                    )
            at = meta.get("agentType")
            if isinstance(at, str) and at.strip():
                agent_type = at.strip()
            mm = meta.get("model")
            if isinstance(mm, str) and mm.strip():
                meta_model = mm.strip()
            md = meta.get("description")
            if isinstance(md, str) and md:
                meta_description = md

    start_ts: Optional[str] = None
    transcript_model: Optional[str] = None
    sums = {k: 0 for k in _NATIVE_USAGE_KEYS}
    cache_5m = 0                      # nested usage.cache_creation split
    cache_1h = 0                      # (codex S306 r3 P2 cure — 1h TTL @2.0x)
    usage_events = 0
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(rec, dict):
                    continue
                ts = rec.get("timestamp")
                if start_ts is None and isinstance(ts, str) and ts:
                    start_ts = ts
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                if transcript_model is None:
                    m = msg.get("model")
                    if isinstance(m, str) and m.strip():
                        transcript_model = m.strip()
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                # Fingerprint drift sonda (codex S306 r2 P2 cure): a usage
                # dict with NEITHER core key is schema drift — counted so
                # native_cross_check can degrade to audit-only, never summed
                # as a zero-token event.
                if ("input_tokens" not in usage) and ("output_tokens" not in usage):
                    if counters is not None:
                        counters["usage_missing_core_keys"] = (
                            counters.get("usage_missing_core_keys", 0) + 1
                        )
                    continue
                bearing = False
                for key in _NATIVE_USAGE_KEYS:
                    v = usage.get(key)
                    if isinstance(v, (int, float)):
                        sums[key] += int(v)
                        if key in ("input_tokens", "output_tokens"):
                            bearing = True
                cc = usage.get("cache_creation")
                if isinstance(cc, dict):
                    v5 = cc.get("ephemeral_5m_input_tokens")
                    v1 = cc.get("ephemeral_1h_input_tokens")
                    if isinstance(v5, (int, float)):
                        cache_5m += int(v5)
                    if isinstance(v1, (int, float)):
                        cache_1h += int(v1)
                if bearing:
                    usage_events += 1
    except OSError:
        # codex S306 P2 cure: an unreadable transcript must NOT degrade to a
        # zero-token record with a "known" $0.00 cost — it corrupts totals
        # AND the ordinal join. Skip the spawn, count it observably.
        if counters is not None:
            counters["transcripts_unreadable"] = (
                counters.get("transcripts_unreadable", 0) + 1
            )
        sys.stderr.write(
            "budget-summary: unreadable native transcript — spawn skipped: "
            "%s\n" % transcript
        )
        return None

    model_raw = meta_model or transcript_model
    model_id = _normalize_model_id(model_raw, pricing=pricing)
    if (
        model_id is None
        and meta_model
        and transcript_model
        and transcript_model.strip().lower() != meta_model.strip().lower()
    ):
        # ADR-149 Amendment 2 (S338, codex rail r2 P2): a bare family
        # alias in the meta ("fable") turned AMBIGUOUS once the registry
        # held two Fable ids, and the doctrine never guesses a version.
        # The transcript's own message.model is exact evidence, not a
        # guess — fall back to it. Still unresolved => TBD, as before.
        model_raw = transcript_model
        model_id = _normalize_model_id(model_raw, pricing=pricing)
    t_in = sums["input_tokens"]
    t_out = sums["output_tokens"]
    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x
    # input — per-model exceptions in _CACHE_READ_MULTIPLIER_OVERRIDES —,
    # write @1.25x on the 5m TTL and @2.00x on the 1h TTL). When the
    # transcript carries the nested ``usage.cache_creation`` split, each
    # tier gets its own multiplier (codex S306 r3 P2 cure); writes NOT
    # attributed by the split assume 5m, the API default. Priced as
    # input-token EQUIVALENTS so compute_cost_usd's full row/dated-row
    # resolution is reused instead of a second rate table (codex S306 r1 P1
    # cure: pricing only fresh in/out understated the native total ~10x).
    c_total = sums["cache_creation_input_tokens"]
    c_1h = min(cache_1h, c_total)
    c_5m = min(cache_5m, c_total - c_1h)
    c_rest = c_total - c_1h - c_5m    # unattributed -> 5m assumption
    cache_equiv_in = int(
        _cache_read_multiplier(model_id) * sums["cache_read_input_tokens"]
        + 1.25 * (c_5m + c_rest)
        + 2.00 * c_1h
    )
    cost = compute_cost_usd(
        model_id, t_in + cache_equiv_in, t_out, pricing=pricing, ts=start_ts
    )
    return {
        "session_id": session_id,
        "rail": rail,
        "agent_type": agent_type,
        "description": meta_description,
        "transcript": transcript.name,
        "start_ts": start_ts,
        "usage_events": usage_events,
        "tokens_in": t_in,
        "tokens_out": t_out,
        "cache_creation_tokens": sums["cache_creation_input_tokens"],
        "cache_read_tokens": sums["cache_read_input_tokens"],
        "model_raw": model_raw,
        "model_id": model_id,
        "cost_usd": cost,
        "cost_tbd": cost is None,
    }


def collect_native_spawns(
    native_root: Optional[Path] = None,
    *,
    cutoff: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    counters: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Collect all native spawn records under ``native_root``.

    ``cutoff`` mirrors the rollup's ``--since`` semantics: a spawn whose
    start timestamp parses AND precedes the cutoff is excluded; a spawn
    with no parseable timestamp is kept (visibility over silence).
    """
    spawns: List[Dict[str, Any]] = []
    for path, rail, session_id in _native_transcript_paths(native_root):
        rec = _read_native_spawn(
            path, rail, session_id, pricing=pricing, counters=counters
        )
        if rec is None:               # unreadable transcript — counted, skipped
            continue
        if cutoff is not None:
            parsed = _parse_ts_any(rec.get("start_ts"))
            if parsed is not None and parsed < cutoff:
                continue
        spawns.append(rec)
    return spawns


def _collect_audit_spawn_rows(
    log_paths: Iterable[Path],
    cutoff: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Audit-log side of the join: one row per ``agent_spawn`` event.

    Token fields are None-PRESERVING (not coerced to 0): a null stays
    null so the report can say "no number on the audit side" instead of
    fabricating a 0 that would fake a divergence.
    """

    def _opt_int(v: Any) -> Optional[int]:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return int(v)
        return None

    rows: List[Dict[str, Any]] = []
    for ev in iter_unique_events(log_paths):
        if (ev.get("action") or "") != "agent_spawn":
            continue
        ts_parsed = _parse_ts(ev.get("ts"))
        if cutoff is not None and ts_parsed is not None and ts_parsed < cutoff:
            continue
        subagent_type = ev.get("subagent_type")
        desc_hash = ev.get("desc_hash")
        rows.append({
            "session_id": ev.get("session_id") or "(unknown)",
            "agent_type": (
                subagent_type.strip()
                if isinstance(subagent_type, str) and subagent_type.strip()
                else "(unknown)"
            ),
            "desc_hash": (
                desc_hash if isinstance(desc_hash, str) and desc_hash else None
            ),
            "ts": ev.get("ts"),
            "model": ev.get("model"),
            "tokens_in": _opt_int(ev.get("tokens_in")),
            "tokens_out": _opt_int(ev.get("tokens_out")),
            "tokens_total": _opt_int(ev.get("tokens_total")),
        })
    return rows


def _audit_total_tokens(row: Dict[str, Any]) -> Optional[int]:
    """Comparable audit-side token total, or None when the ledger has no
    number for this spawn (the current-rotation reality: all null)."""
    total = row.get("tokens_total")
    if isinstance(total, int):
        return total
    t_in = row.get("tokens_in")
    t_out = row.get("tokens_out")
    if isinstance(t_in, int) and isinstance(t_out, int):
        return t_in + t_out
    return None


def native_cross_check(
    *,
    audit_dir: Optional[Path] = None,
    native_root: Optional[Path] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Join the audit-log spawn ledger against the native corpus (W1.2-2).

    Join key: ``(session_id, agent_type)`` with agent_type =
    audit ``subagent_type`` ≈ native meta ``agentType`` (case-folded);
    within each group both sides sort by timestamp and zip by ordinal.
    Matched pairs, plus UNMATCHED residue from BOTH sides, are all
    returned — nothing is silenced. Read-only; fail-open on infra
    (a broken corpus degrades to a dormant block with a note, never a
    crash — the audit-log rollup is unaffected either way).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None
    root = native_root if native_root is not None else default_native_root()

    doctrine = (
        "cross-check, not authority-swap: the native source NEVER "
        "silently replaces the audit-log rollup"
    )

    infra_note: Optional[str] = None
    read_counters: Dict[str, int] = {}
    try:
        transcript_count = len(_native_transcript_paths(root))
        native = collect_native_spawns(
            root, cutoff=cutoff, pricing=pricing, counters=read_counters
        )
    except Exception as exc:  # fail-open on infra (CLAUDE.md §4)
        transcript_count = 0
        native = []
        infra_note = (
            f"native collection failed ({type(exc).__name__}) — degraded to "
            f"audit-log only"
        )

    # Audit side is read BEFORE any early return (codex S306 r5 P2 cure): a
    # dormant/drifted native source must still report ACCURATE audit counts —
    # hard-coded zeros would tell JSON consumers the audit ledger is empty
    # when only the native side is missing.
    audit_rows = _collect_audit_spawn_rows(discover_logs(audit_dir), cutoff)

    # Path-shape sonda (codex S306 r3 P2 cure — parity with the puller): a
    # walk sweep seeing MORE agent transcripts than the two known globs
    # matched means the harness moved the layout. Report DRIFT, never
    # ordinary dormancy or a zero total.
    try:
        walk_seen = sum(
            1 for p in root.rglob("agent-a*.jsonl") if "subagents" in p.parts
        )
    except OSError:
        walk_seen = transcript_count
    if walk_seen > transcript_count:
        return {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "degraded": "schema-drift",
            "drift": {"path_shape_unmatched": walk_seen - transcript_count},
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "unmatched_audit_count": len(audit_rows),
            "note": (
                "native path shape drifted (%d transcript(s) outside the "
                "known globs) — cross-check degraded to audit-log only"
                % (walk_seen - transcript_count)
            ),
        }

    if transcript_count == 0:
        result: Dict[str, Any] = {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "matched_count": 0,
            "comparable_pair_count": 0,
            "unmatched_native_count": 0,
            "unmatched_audit_count": len(audit_rows),
            "note": (
                infra_note
                or "no native transcripts found — audit-log rollup is the "
                   "sole source (dormant, by design)"
            ),
        }
        return result

    # Drift gate on the integrated reader (codex S306 r2 P2 cure — same
    # fingerprint sonda as the puller): usage dicts whose core token keys
    # vanished mean the harness schema moved; publishing zero/partial totals
    # would present drift as genuine zero usage. Degrade to audit-only.
    drift_hits = {
        k: read_counters.get(k, 0)
        for k in ("usage_missing_core_keys", "meta_invariant_missing")
        if read_counters.get(k, 0) > 0
    }
    if drift_hits:
        return {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "degraded": "schema-drift",
            "drift": dict(read_counters),
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "unmatched_audit_count": len(audit_rows),
            "note": (
                "native schema drifted (%s) — cross-check degraded to "
                "audit-log only"
                % ", ".join(f"{k}={v}" for k, v in sorted(drift_hits.items()))
            ),
        }

    def _key(session_id: Any, agent_type: Any) -> Tuple[str, str]:
        return (
            str(session_id or ""),
            str(agent_type or "").strip().lower(),
        )

    # Pass 0 — EXACT join (codex S306 r2 P1 cure): native ``meta.description``
    # hashes (sha256, same function as audit_log's hash_description) to the
    # audit row's ``desc_hash``. This survives the shape where a teammate's
    # native agentType is its NAME while the audit row says
    # ``general-purpose`` — the (session, type) grouping alone under-matches.
    audit_by_hash: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in audit_rows:
        h = row.get("desc_hash")
        if isinstance(h, str) and h:
            audit_by_hash.setdefault(
                (str(row["session_id"] or ""), h), []
            ).append(row)
    for group in audit_by_hash.values():
        group.sort(key=lambda r: r.get("ts") or "")
    exact_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    consumed_audit: Set[int] = set()
    remaining_native: List[Dict[str, Any]] = []
    # Duplicate-description groups pair oldest-to-oldest on BOTH sides
    # (codex S306 r4 P2 cure): the audit hash groups are ts-sorted above, so
    # native candidates must be consumed in start_ts order too — glob order
    # would associate the wrong token totals within the duplicate group.
    for rec in sorted(native, key=lambda r: r.get("start_ts") or ""):
        desc = rec.get("description")
        if isinstance(desc, str) and desc:
            hkey = (
                str(rec["session_id"] or ""),
                hashlib.sha256(
                    desc.encode("utf-8", errors="replace")
                ).hexdigest(),
            )
            group = audit_by_hash.get(hkey)
            if group:
                aud = group.pop(0)
                consumed_audit.add(id(aud))
                exact_pairs.append((rec, aud))
                continue
        remaining_native.append(rec)
    remaining_audit = [r for r in audit_rows if id(r) not in consumed_audit]

    native_by: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for rec in remaining_native:
        native_by.setdefault(_key(rec["session_id"], rec["agent_type"]), []).append(rec)
    audit_by: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in remaining_audit:
        audit_by.setdefault(_key(row["session_id"], row["agent_type"]), []).append(row)

    for group in native_by.values():
        group.sort(key=lambda r: r.get("start_ts") or "")
    for group in audit_by.values():
        group.sort(key=lambda r: r.get("ts") or "")

    matched: List[Dict[str, Any]] = []
    unmatched_native: List[Dict[str, Any]] = []
    unmatched_audit: List[Dict[str, Any]] = []
    divergences_by_rail: Dict[str, List[float]] = {"task": [], "workflow": []}

    def _emit_pair(nat: Dict[str, Any], aud: Dict[str, Any],
                   ordinal: Optional[int], join: str) -> None:
        nat_total = int(nat["tokens_in"]) + int(nat["tokens_out"])
        aud_total = _audit_total_tokens(aud)
        comparable = aud_total is not None
        divergence_pct: Optional[float] = None
        if comparable:
            base = aud_total if aud_total else 1
            divergence_pct = round(
                abs(nat_total - aud_total) * 100.0 / base, 2
            )
            divergences_by_rail.setdefault(nat["rail"], []).append(
                divergence_pct
            )
        matched.append({
            "session_id": str(nat["session_id"] or ""),
            "agent_type": str(nat["agent_type"] or "").strip().lower(),
            "ordinal": ordinal,
            "join": join,
            "native_rail": nat["rail"],
            "native_start_ts": nat["start_ts"],
            "native_tokens_in": nat["tokens_in"],
            "native_tokens_out": nat["tokens_out"],
            "native_cache_creation_tokens": nat["cache_creation_tokens"],
            "native_cache_read_tokens": nat["cache_read_tokens"],
            "native_model_raw": nat["model_raw"],
            "native_model_id": nat["model_id"],
            "native_cost_usd": nat["cost_usd"],
            "native_cost_tbd": nat["cost_tbd"],
            "audit_ts": aud["ts"],
            "audit_model": aud["model"],
            "audit_tokens_in": aud["tokens_in"],
            "audit_tokens_out": aud["tokens_out"],
            "audit_tokens_total": aud["tokens_total"],
            "comparable": comparable,
            "divergence_pct": divergence_pct,
        })

    for nat, aud in exact_pairs:
        _emit_pair(nat, aud, None, "desc_hash")

    for key in sorted(set(native_by) | set(audit_by)):
        n_group = native_by.get(key, [])
        a_group = audit_by.get(key, [])
        pair_n = min(len(n_group), len(a_group))
        for i in range(pair_n):
            _emit_pair(n_group[i], a_group[i], i, "ordinal")
        for i in range(pair_n, len(n_group)):
            rec = dict(n_group[i])
            rec["ordinal"] = i
            unmatched_native.append(rec)
        for i in range(pair_n, len(a_group)):
            row = dict(a_group[i])
            row["ordinal"] = i
            unmatched_audit.append(row)

    tok = {
        "in": sum(int(r["tokens_in"]) for r in native),
        "out": sum(int(r["tokens_out"]) for r in native),
        "cache_creation": sum(int(r["cache_creation_tokens"]) for r in native),
        "cache_read": sum(int(r["cache_read_tokens"]) for r in native),
    }
    priced = [r for r in native if r["cost_usd"] is not None]
    tbd_spawns = len(native) - len(priced)
    native_cost = round(sum(float(r["cost_usd"]) for r in priced), 6) if priced else None

    max_div: Dict[str, Optional[float]] = {}
    for rail in ("task", "workflow"):
        vals = divergences_by_rail.get(rail) or []
        max_div[rail] = max(vals) if vals else None

    comparable_pairs = sum(1 for m in matched if m["comparable"])

    result = {
        "doctrine": doctrine,
        "native_root": str(root),
        "dormant": False,
        "native_spawn_count": len(native),
        "native_task_spawns": sum(1 for r in native if r["rail"] == "task"),
        "native_workflow_spawns": sum(
            1 for r in native if r["rail"] == "workflow"
        ),
        "native_usage_event_count": sum(int(r["usage_events"]) for r in native),
        "native_transcripts_unreadable": read_counters.get(
            "transcripts_unreadable", 0
        ),
        "audit_spawn_count": len(audit_rows),
        "matched_count": len(matched),
        "comparable_pair_count": comparable_pairs,
        "unmatched_native_count": len(unmatched_native),
        "unmatched_audit_count": len(unmatched_audit),
        "native_tokens": tok,
        "native_cost_usd": native_cost,
        "native_cost_tbd_spawns": tbd_spawns,
        "native_cost_note": (
            "spawns without a resolvable/priced model are cost TBD — they "
            "are NEVER priced as $0 and are excluded from native_cost_usd"
        ),
        "max_divergence_pct_by_rail": max_div,
        "matched": matched,
        "unmatched_native": unmatched_native,
        "unmatched_audit": unmatched_audit,
    }
    if infra_note:
        result["note"] = infra_note
    return result


def validate_memory_claim(
    total_cost_usd: Optional[float],
    low: float = MEMORY_CLAIM_LOW_USD,
    high: float = MEMORY_CLAIM_HIGH_USD,
    ratio_low: float = MEMORY_CLAIM_PASS_RATIO_LOW,
    ratio_high: float = MEMORY_CLAIM_PASS_RATIO_HIGH,
) -> Dict[str, Any]:
    """Check the rollup against the CLAUDE.md S82-S99 memory claim band.

    Returns a structured verdict:
      - ``status``: ``"pass"`` (within band), ``"warn"`` (outside
        [ratio_low, ratio_high] multiplied band) or ``"unknown"``
        (no cost computed).
      - ``band_low_usd`` / ``band_high_usd`` / ``observed_usd`` /
        ``ratio_to_band_low`` / ``ratio_to_band_high``.

    Methodology: the memory claim is itself a *range* ($1003-1543); we
    pass when the observed cost is anywhere inside, warn when outside
    the [0.5*low, 1.5*high] enclosing band. This wide gate accepts
    pricing-table drift while still flagging obvious bugs.
    """
    if total_cost_usd is None:
        return {
            "status": "unknown",
            "band_low_usd": low,
            "band_high_usd": high,
            "observed_usd": None,
            "ratio_to_band_low": None,
            "ratio_to_band_high": None,
            "message": "No cost computed; pricing table likely missed all models.",
        }
    enclosing_low = low * ratio_low
    enclosing_high = high * ratio_high
    if low <= total_cost_usd <= high:
        status = "pass"
        message = (
            f"Observed ${total_cost_usd:.2f} within memory-claim "
            f"band [${low:.2f}, ${high:.2f}]."
        )
    elif enclosing_low <= total_cost_usd <= enclosing_high:
        status = "pass"
        message = (
            f"Observed ${total_cost_usd:.2f} within widened band "
            f"[${enclosing_low:.2f}, ${enclosing_high:.2f}] "
            f"(memory claim ${low:.2f}-${high:.2f})."
        )
    else:
        status = "warn"
        message = (
            f"Observed ${total_cost_usd:.2f} OUTSIDE widened band "
            f"[${enclosing_low:.2f}, ${enclosing_high:.2f}] "
            f"(memory claim ${low:.2f}-${high:.2f}). "
            f"Likely token-tracking gap OR pricing drift."
        )
    return {
        "status": status,
        "band_low_usd": low,
        "band_high_usd": high,
        "observed_usd": total_cost_usd,
        "ratio_to_band_low": round(total_cost_usd / low, 4) if low else None,
        "ratio_to_band_high": round(total_cost_usd / high, 4) if high else None,
        "message": message,
    }


def _fmt_tokens(n: int) -> str:
    return f"{n:>14,}"





