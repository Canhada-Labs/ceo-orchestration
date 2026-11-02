from __future__ import annotations

def build_plan_attribution(
    events: List[Dict[str, Any]],
) -> Dict[int, Optional[str]]:
    """Build event-index → plan_id attribution map.

    Algorithm (best-effort, in order):
      1. If event has an explicit ``plan_id`` field matching PLAN-NNN,
         that wins.
      2. Else: find the most recent preceding ``plan_status_transition``
         event in the same ``session_id`` whose ``to_status`` (or
         ``status``) is ``executing``; attribute to that plan.
      3. Else: None (display as ``(unknown)``).

    The events list must be sorted by timestamp ascending. The map is
    keyed by *index in the supplied list* so callers can re-zip without
    holding a second copy.
    """
    attribution: Dict[int, Optional[str]] = {}
    # session_id → currently-executing plan_id
    session_executing: Dict[str, str] = {}

    for idx, ev in enumerate(events):
        action = ev.get("action") or ""
        session_id = ev.get("session_id") or ""

        # Update executing context from plan_status_transition events.
        if action == "plan_status_transition":
            to_status = (
                ev.get("to_status")
                or ev.get("status")
                or ev.get("new_status")
                or ""
            )
            pid = _safe_plan_id(ev.get("plan_id"))
            if pid and to_status == "executing":
                session_executing[session_id] = pid
            elif pid and to_status in ("done", "abandoned", "blocked"):
                # Plan no longer executing — clear if it matches.
                if session_executing.get(session_id) == pid:
                    session_executing.pop(session_id, None)

        # Explicit field wins.
        explicit = _safe_plan_id(ev.get("plan_id"))
        if explicit:
            attribution[idx] = explicit
            continue

        # Inferred from session executing context.
        inferred = session_executing.get(session_id)
        if inferred:
            attribution[idx] = inferred
        else:
            attribution[idx] = None

    return attribution


def compute_cost_usd(
    model: Optional[str],
    tokens_in: int,
    tokens_out: int,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    ts: Optional[str] = None,
) -> Optional[float]:
    """Compute USD cost from model + token counts; None on unknown model.

    P2a: when ``ts`` (the event's own ISO-8601 timestamp) is given and the
    model has a dated row, the rate is resolved against that date
    (``ts[:10]`` lexicographic compare — no parse). A caller-supplied
    custom row for the model always wins over the built-in dated row; a
    missing ``ts`` falls back to the static row (pre-P2a behaviour).
    """
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str) or not model:
        return None
    key = model.lower()
    row = pricing.get(key)
    dated = _DATED_PRICING.get(key)
    if (
        dated is not None
        and isinstance(ts, str)
        and len(ts) >= 10
        and row == _DEFAULT_PRICING.get(key)
    ):
        cutoff, through, after = dated
        row = through if ts[:10] <= cutoff else after
    if not row:
        return None
    cost = (tokens_in / 1000.0) * row.get("in", 0.0)
    cost += (tokens_out / 1000.0) * row.get("out", 0.0)
    return round(cost, 6)


def _load_normalize_model_name():
    """Load ``normalize_model_name`` from the repo's EXISTING registry
    module ``optimizer/model_normalize.py`` (PLAN-133 B2) — REUSE, never
    a second table. Tries the deterministic sibling file first (works
    when this script is loaded by path, as the test suite does), then a
    plain package import. Fail-open on infra: returns None when neither
    route works; ``_normalize_model_id`` then degrades to case/
    whitespace/``[1m]`` handling + registry-derived family folding.
    """
    candidate = Path(__file__).resolve().parent / "optimizer" / "model_normalize.py"
    try:
        if candidate.is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "_budget_summary_model_normalize", str(candidate)
            )
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                fn = getattr(mod, "normalize_model_name", None)
                if callable(fn):
                    return fn
    except Exception:
        pass
    try:
        from optimizer.model_normalize import normalize_model_name as fn2  # type: ignore

        if callable(fn2):
            return fn2
    except Exception:
        pass
    return None


def _family_candidates(
    family: str,
    pricing: Dict[str, Dict[str, float]],
) -> Set[str]:
    """Canonical ids in the EXISTING pricing registry whose family segment
    equals ``family`` (date-stamped variants folded through the reused
    normalizer so ``claude-haiku-4-5-20251001`` and ``claude-haiku-4-5``
    count as ONE candidate, not two)."""
    out: Set[str] = set()
    for key in pricing:
        m = _CLAUDE_FAMILY_RE.match(key)
        if not m or m.group(1) != family:
            continue
        canon = key
        if _NORMALIZE_MODEL_NAME is not None:
            try:
                folded = _NORMALIZE_MODEL_NAME(key)
                if folded:
                    canon = folded
            except Exception:
                pass
        out.add(canon)
    return out


def _normalize_model_id(
    model: Any,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[str]:
    """Resolve a raw model string to a canonical model id (W1.2-3).

    Pipeline (all lookups against EXISTING registry surfaces):
      1. coerce/strip/lower; empty → None.
      2. strip a trailing ``[1m]`` packaging suffix (generic — the
         ``model_normalize`` alias map only carries the 4-8 row).
      3. fold aliases via the reused ``normalize_model_name``
         (``optimizer/model_normalize.py``): date stamps, bare
         family+version (``opus-5`` → ``claude-opus-5``),
         ``anthropic/`` prefix, case/whitespace.
      4. exact hit in the pricing registry → resolved.
      5. bare family alias (``fable``): resolved ONLY when the registry
         holds exactly one canonical id for that family; ambiguous
         families (``opus``/``sonnet``/``haiku``) → None — never guess
         a version.
      6. a specific-but-unpriced id passes through unchanged so reports
         can NAME the model that lacks a pricing row (cost stays TBD).

    Returns the canonical id, or None when the input is empty or an
    ambiguous alias. A None result (or a resolved id with no pricing
    row) MUST surface as ``TBD`` in cost columns — never as $0.
    """
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str):
        return None
    m = model.strip().lower()
    if not m:
        return None
    m = _ONE_M_SUFFIX_RE.sub("", m)
    if not m:
        return None
    if _NORMALIZE_MODEL_NAME is not None:
        try:
            folded = _NORMALIZE_MODEL_NAME(m)
            if folded:
                m = folded
        except Exception:
            pass
    if m in pricing:
        return m
    if _BARE_FAMILY_RE.match(m):
        candidates = _family_candidates(m, pricing)
        if len(candidates) == 1:
            return next(iter(candidates))
        return None
    return m


def rollup(
    *,
    audit_dir: Optional[Path] = None,
    plan_filter: Optional[str] = None,
    since: Optional[timedelta] = None,
    by_wave: bool = False,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Compute the cumulative rollup.

    Returns a JSON-serializable dict. See module docstring for output
    shape.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    # Materialize so we can do two passes (attribution + rollup).
    all_events: List[Dict[str, Any]] = list(iter_unique_events(log_paths))
    # Sort ascending by ts (stable on equal ts).
    all_events.sort(key=lambda e: (e.get("ts") or "", e.get("action") or ""))

    attribution = build_plan_attribution(all_events)

    tot_in = 0
    tot_out = 0
    tot_total = 0
    tot_cost = 0.0
    cost_known = False
    spawn_count = 0
    codex_event_count = 0
    unknown_plan_count = 0

    per_plan: Dict[str, Dict[str, Any]] = {}
    per_session: Dict[str, Dict[str, Any]] = {}
    per_wave: Dict[str, Dict[str, Any]] = {}

    for idx, ev in enumerate(all_events):
        action = ev.get("action") or ""
        if action not in _TOKEN_BEARING_ACTIONS:
            continue

        ts = _parse_ts(ev.get("ts"))
        if cutoff is not None and ts is not None and ts < cutoff:
            continue

        # plan_id attribution
        attributed = attribution.get(idx)
        if plan_filter:
            if attributed != plan_filter:
                continue
        plan_label = attributed or "(unknown)"
        if attributed is None:
            unknown_plan_count += 1

        # Tokens — None coerced to 0
        t_in_raw = ev.get("tokens_in")
        t_out_raw = ev.get("tokens_out")
        t_total_raw = ev.get("tokens_total")
        t_in = int(t_in_raw) if isinstance(t_in_raw, (int, float)) and t_in_raw else 0
        t_out = int(t_out_raw) if isinstance(t_out_raw, (int, float)) and t_out_raw else 0
        t_total = int(t_total_raw) if isinstance(t_total_raw, (int, float)) and t_total_raw else 0

        spawn_count += 1
        if action == "pair_rail_case":
            codex_event_count += 1

        tot_in += t_in
        tot_out += t_out
        tot_total += t_total or (t_in + t_out)

        model = ev.get("model") or ev.get("agent_model") or ""
        if isinstance(model, str) and not model and action == "pair_rail_case":
            # Codex events default to gpt-5-codex when model not annotated.
            model = "gpt-5-codex"
        cost = compute_cost_usd(model if isinstance(model, str) else None,
                                t_in, t_out, pricing=pricing,
                                ts=ev.get("ts"))
        if cost is not None:
            cost_known = True
            tot_cost += cost

        # Per-plan
        prow = per_plan.setdefault(plan_label, {
            "plan_id": plan_label,
            "event_count": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
            "cost_known": False,
        })
        prow["event_count"] += 1
        prow["tokens_in"] += t_in
        prow["tokens_out"] += t_out
        prow["tokens_total"] += t_total or (t_in + t_out)
        if cost is not None:
            prow["cost_usd"] = round(prow["cost_usd"] + cost, 6)
            prow["cost_known"] = True

        # Per-session
        sid = ev.get("session_id") or "(unknown)"
        srow = per_session.setdefault(sid, {
            "session_id": sid,
            "event_count": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
        })
        srow["event_count"] += 1
        srow["tokens_total"] += t_total or (t_in + t_out)
        if cost is not None:
            srow["cost_usd"] = round(srow["cost_usd"] + cost, 6)

        # Per-wave (optional aggregation)
        if by_wave:
            wave = _extract_wave_id(ev)
            if wave:
                wrow = per_wave.setdefault(wave, {
                    "wave": wave,
                    "event_count": 0,
                    "tokens_total": 0,
                    "cost_usd": 0.0,
                })
                wrow["event_count"] += 1
                wrow["tokens_total"] += t_total or (t_in + t_out)
                if cost is not None:
                    wrow["cost_usd"] = round(wrow["cost_usd"] + cost, 6)

    result: Dict[str, Any] = {
        "audit_dir": str(audit_dir or default_audit_dir()),
        "log_files_read": [p.name for p in log_paths],
        "plan_filter": plan_filter,
        "since": None,  # filled by caller who knows the expr
        "total_events": spawn_count,
        "codex_event_count": codex_event_count,
        "unknown_plan_count": unknown_plan_count,
        "total_tokens_in": tot_in,
        "total_tokens_out": tot_out,
        "total_tokens": tot_total,
        "total_cost_usd": round(tot_cost, 6) if cost_known else None,
        "cost_source": "default-pricing-table" if cost_known else "unknown",
        "per_plan": sorted(per_plan.values(), key=lambda r: r["plan_id"]),
        "per_session": sorted(per_session.values(), key=lambda r: r["session_id"]),
    }
    if by_wave:
        result["per_wave"] = sorted(per_wave.values(), key=lambda r: r["wave"])

    return result


def _bench_cost_usd(r: Dict[str, Any]) -> float:
    """Per-run benchmark cost in USD. Prefers int-encoded
    ``cost_usd_cents`` (÷100); falls back to a legacy float ``cost_usd``."""
    cents = r.get("cost_usd_cents")
    if cents is not None:
        try:
            return int(cents) / 100.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_duration_s(r: Dict[str, Any]) -> float:
    """Per-run wall-clock (the harbor 'compute' column) in seconds.
    Prefers int-encoded ``duration_ms`` (÷1000); falls back to legacy
    float ``duration_s``."""
    ms = r.get("duration_ms")
    if ms is not None:
        try:
            return int(ms) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("duration_s") or 0.0)
    except (TypeError, ValueError):
        return 0.0



