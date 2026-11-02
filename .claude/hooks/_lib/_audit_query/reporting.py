"""Aggregations used by the audit-query compatibility facade."""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
def cmd_spawn_stats(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """PLAN-025 Batch D F-obs-001 — spawn distribution by model/skill.

    Reads audit-log entries, filters to `action == "agent_spawn"`, and
    aggregates counts by `model` (ADR-052 v2.8 field), `skill`, or both.

    Respects `--since` with either ISO-8601 timestamps or relative
    offsets ("7d", "30d", "1h"). Renders a human-friendly table (or JSON
    via `--json`).
    """
    import re as _re
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz

    # Resolve --since
    since_dt: Optional[_dt] = None
    if getattr(args, "since", None):
        raw = str(args.since).strip()
        m = _re.match(r"^(\d+)([hdwm])$", raw)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = {"h": _td(hours=n), "d": _td(days=n),
                     "w": _td(weeks=n), "m": _td(days=30 * n)}[unit]
            since_dt = _dt.now(tz=_tz.utc) - delta
        else:
            try:
                since_dt = _dt.fromisoformat(raw.replace("Z", "+00:00"))
                if since_dt.tzinfo is None:
                    since_dt = since_dt.replace(tzinfo=_tz.utc)
            except ValueError:
                return {"error": f"unparseable --since: {raw!r}"}

    by_model: Dict[str, int] = {}
    by_skill: Dict[str, int] = {}
    by_pair: Dict[str, int] = {}  # "model|skill"
    total = 0

    for ev in entries:
        if ev.get("action") != "agent_spawn":
            continue
        if since_dt is not None:
            ts_s = ev.get("ts") or ev.get("timestamp") or ""
            try:
                ev_ts = _dt.fromisoformat(str(ts_s).replace("Z", "+00:00"))
                if ev_ts.tzinfo is None:
                    ev_ts = ev_ts.replace(tzinfo=_tz.utc)
            except (ValueError, TypeError):
                continue
            if ev_ts < since_dt:
                continue

        total += 1
        model = ev.get("model") or "unknown_model"
        skill = ev.get("skill") or "unknown_skill"
        by_model[model] = by_model.get(model, 0) + 1
        by_skill[skill] = by_skill.get(skill, 0) + 1
        by_pair[f"{model}|{skill}"] = by_pair.get(f"{model}|{skill}", 0) + 1

    out: Dict[str, Any] = {
        "since": str(since_dt) if since_dt else "all-time",
        "total_spawns": total,
    }
    by = getattr(args, "by", "model")
    if by in ("model", "both"):
        out["by_model"] = dict(sorted(by_model.items(), key=lambda kv: -kv[1]))
    if by in ("skill", "both"):
        out["by_skill"] = dict(sorted(by_skill.items(), key=lambda kv: -kv[1]))
    if by == "both":
        out["by_model_and_skill"] = dict(sorted(by_pair.items(), key=lambda kv: -kv[1]))
    return out


# ---------------------------------------------------------------------------
# weekly-summary helpers (PLAN-023 Phase E decomposition)
# ---------------------------------------------------------------------------


def _weekly_parse_ts(e: Dict[str, Any]) -> Optional[datetime]:
    """Parse ISO-8601 ``ts`` from an audit entry (None on missing/malformed)."""
    raw = e.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        s = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _weekly_parse_window(window_raw: str) -> "Optional[timedelta]":
    """Translate ``7d``/``14d``/``30m``/``all`` into a timedelta (or None)."""
    if window_raw == "all":
        return None
    m = re.fullmatch(r"(\d+)([mhd])", window_raw.strip().lower())
    if not m:
        print(
            "[audit-query] ERROR: weekly-summary: bad --window {0!r}; "
            "expected 7d/14d/30m/all".format(window_raw),
            file=sys.stderr,
        )
        sys.exit(1)
    n, unit = int(m.group(1)), m.group(2)
    return {"m": timedelta(minutes=n), "h": timedelta(hours=n),
            "d": timedelta(days=n)}[unit]


def _weekly_empty_bucket() -> Dict[str, Any]:
    return {
        "spawns": 0,
        "vetoes": 0,
        "plan_transitions": 0,
        "confidence_total": 0,
        "confidence_failed": 0,
        "veto_reasons": Counter(),
    }


def _weekly_collect_buckets(
    entries: List[Dict[str, Any]],
    current_start: Optional[datetime],
    prior_start: Optional[datetime],
    prior_end: Optional[datetime],
    now: datetime,
) -> "Tuple[Dict[str, Any], Dict[str, Any]]":
    """Single-pass accumulation of audit events into current/prior buckets."""
    current = _weekly_empty_bucket()
    prior = _weekly_empty_bucket()
    for e in entries:
        dt = _weekly_parse_ts(e)
        if dt is None:
            continue
        if current_start is None:
            bucket_name = "current"  # --window all
        elif current_start <= dt <= now:
            bucket_name = "current"
        elif (
            prior_start is not None
            and prior_end is not None
            and prior_start <= dt < prior_end
        ):
            bucket_name = "prior"
        else:
            continue
        bucket = current if bucket_name == "current" else prior
        action = e.get("action")
        if action == "agent_spawn":
            bucket["spawns"] += 1
        elif action == "veto_triggered":
            bucket["vetoes"] += 1
            reason = e.get("reason_code") or "unknown"
            bucket["veto_reasons"][reason] += 1
        elif action == "plan_transition":
            bucket["plan_transitions"] += 1
        elif action == "confidence_gate":
            bucket["confidence_total"] += 1
            if e.get("outcome") == "fail" or e.get("failed_claim_count"):
                bucket["confidence_failed"] += 1
    return current, prior


def _weekly_render_bucket(bucket: Dict[str, Any]) -> Dict[str, Any]:
    """Compute derived rates for one accumulator bucket."""
    denom = bucket["spawns"] + bucket["vetoes"]
    veto_rate = bucket["vetoes"] / denom if denom else None
    conf_total = bucket["confidence_total"]
    conf_fail_rate = bucket["confidence_failed"] / conf_total if conf_total else None
    return {
        "spawns": bucket["spawns"],
        "vetoes": bucket["vetoes"],
        "veto_rate": round(veto_rate, 3) if veto_rate is not None else None,
        "plan_transitions": bucket["plan_transitions"],
        "confidence_total": bucket["confidence_total"],
        "confidence_failed": bucket["confidence_failed"],
        "confidence_fail_rate": round(conf_fail_rate, 3) if conf_fail_rate is not None else None,
    }


def _weekly_delta(
    a: Optional[float], b: Optional[float], *, pp: bool = False,
) -> "Optional[float]":
    """Signed delta between two optional floats (pp=True → ×100 rounded 1dp)."""
    if a is None or b is None:
        return None
    d = a - b
    if pp:
        return round(d * 100.0, 1)
    return round(d, 3) if isinstance(d, float) else int(d)


def cmd_weekly_summary(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query weekly-summary` — adopter-side weekly triage metrics.

    PLAN-015 Phase 0.5. Compares a current window against the prior window
    of the same length and reports signed deltas so the Owner can see
    week-over-week trends (spawn growth, veto-rate shifts, plan velocity,
    confidence-gate health, top vetoed reasons).

    Window sizing: ``--window`` accepts the shared `_parse_since_arg`
    shorthand (``7d`` default, ``14d``, ``30d``) or ``all`` (disables
    the prior-window comparison — current-window only).
    ``--now ISO`` overrides "now" for deterministic tests.

    PLAN-023 Phase E decomposition: delegates window parsing, bucket
    accumulation, rendering, and delta computation to module-level
    helpers (``_weekly_parse_window``, ``_weekly_collect_buckets``,
    ``_weekly_render_bucket``, ``_weekly_delta``). Behavior byte-
    identical to the pre-decomposition 151-LoC monolith.
    """
    window_raw = str(getattr(args, "window", "7d"))
    now_raw = getattr(args, "now", None)
    now = _parse_since_arg(now_raw) if now_raw else datetime.now(timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)

    window_delta = _weekly_parse_window(window_raw)

    if window_delta is None:
        current_start: Optional[datetime] = None
        prior_start: Optional[datetime] = None
        prior_end: Optional[datetime] = None
    else:
        current_start = now - window_delta
        prior_start = now - (2 * window_delta)
        prior_end = current_start

    current, prior = _weekly_collect_buckets(
        entries, current_start, prior_start, prior_end, now,
    )
    cur = _weekly_render_bucket(current)
    pri = _weekly_render_bucket(prior)

    trend = {
        "spawn_delta": cur["spawns"] - pri["spawns"],
        "veto_rate_delta_pp": _weekly_delta(cur["veto_rate"], pri["veto_rate"], pp=True),
        "plan_transition_delta": cur["plan_transitions"] - pri["plan_transitions"],
        "confidence_fail_rate_delta_pp": _weekly_delta(
            cur["confidence_fail_rate"], pri["confidence_fail_rate"], pp=True
        ),
    }

    top_vetoed = [
        {"reason_code": code, "count": count}
        for code, count in current["veto_reasons"].most_common(3)
    ]

    return {
        "query": "weekly-summary",
        "version": "1",
        "window": window_raw,
        "now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "current_window": cur,
        "previous_window": pri,
        "trend": trend,
        "top_vetoed_reasons_current": top_vetoed,
    }


def cmd_architect_outcomes(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query architect-outcomes` — per-lesson hit/miss from Architect spawns.

    PLAN-009 P3.4. Aggregates `lesson_outcome` events filtered by
    `consumer="architect"` (default) and `inference_mode` (default
    "session-correlated" — dirty window-only data excluded unless
    `--include-window-only` is passed).

    Output envelope (SPEC/v1/audit-query.schema.md):
        {"query": "architect-outcomes", "version": "1",
         "data": {"lessons": [{lesson_id, hit_count, miss_count,
                               effectiveness, last_outcome_at,
                               inference_modes: {...}}, ...]}}
    """
    since = _parse_since_arg(getattr(args, "since", "24h"))
    include_window_only = getattr(args, "include_window_only", False)
    consumer_filter = getattr(args, "consumer", "architect")

    def _in_window(e: Dict[str, Any]) -> bool:
        if since is None:
            return True
        ts = _parse_since_arg(e.get("ts", ""))
        return ts is None or ts >= since

    # Aggregate per lesson_id
    from collections import defaultdict
    per_lesson: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"hit_count": 0, "miss_count": 0,
                 "last_outcome_at": "",
                 "inference_modes": {}, "archetype": ""}
    )

    for e in entries:
        if e.get("action") != "lesson_outcome":
            continue
        if e.get("consumer", "benchmark") != consumer_filter:
            continue
        mode = e.get("inference_mode", "")
        if not include_window_only and mode == "window-only":
            continue
        if not _in_window(e):
            continue
        lid = e.get("lesson_id", "")
        if not lid:
            continue
        agg = per_lesson[lid]
        if e.get("hit"):
            agg["hit_count"] += 1
        else:
            agg["miss_count"] += 1
        agg["inference_modes"][mode or "unspecified"] = (
            agg["inference_modes"].get(mode or "unspecified", 0) + 1
        )
        ts = e.get("ts", "")
        if ts > agg["last_outcome_at"]:
            agg["last_outcome_at"] = ts
        if not agg["archetype"]:
            agg["archetype"] = e.get("archetype", "")

    lessons = []
    for lid, agg in per_lesson.items():
        total = agg["hit_count"] + agg["miss_count"]
        effectiveness = (agg["hit_count"] / total) if total > 0 else None
        lessons.append({
            "lesson_id": lid,
            "archetype": agg["archetype"],
            "hit_count": agg["hit_count"],
            "miss_count": agg["miss_count"],
            "effectiveness": effectiveness,
            "last_outcome_at": agg["last_outcome_at"],
            "inference_modes": agg["inference_modes"],
        })
    lessons.sort(key=lambda x: (x["effectiveness"] is None, -(x["effectiveness"] or 0)))

    data = {
        "consumer": consumer_filter,
        "include_window_only": include_window_only,
        "since": since.isoformat() if since else "all",
        "lesson_count": len(lessons),
        "lessons": lessons,
    }
    return {
        "query": "architect-outcomes",
        "version": "1",
        "data": data,
    }


def cmd_prune_restore_ratio(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query prune-restore-ratio` — ADR-020 measurement hook.

    Reads `lesson_archived` + `lesson_restored` events; computes
    restored/archived. Default window 24h (PLAN-009 A18). Dedupes
    by lesson_id; warns on >1 restore event per lesson (C12/A13).

    Output shape (SPEC/v1/audit-query.schema.md envelope):
        {"query": "prune-restore-ratio", "version": "1",
         "data": { ... }}
    """
    since = _parse_since_arg(getattr(args, "since", "24h"))
    until = _parse_since_arg(getattr(args, "until", None)) if getattr(args, "until", None) else None

    def _in_window(e: Dict[str, Any]) -> bool:
        ts = e.get("ts", "")
        if not ts:
            return True
        dt = _parse_since_arg(ts)
        if dt is None:
            return True
        if since and dt < since:
            return False
        if until and dt > until:
            return False
        return True

    archived = [e for e in entries if e.get("action") == "lesson_archived" and _in_window(e)]
    restored = [e for e in entries if e.get("action") == "lesson_restored" and _in_window(e)]

    # Dedupe restored by lesson_id + count multi-restore warnings
    restored_counts: Dict[str, int] = {}
    for e in restored:
        lid = e.get("lesson_id", "")
        if lid:
            restored_counts[lid] = restored_counts.get(lid, 0) + 1
    unique_restored = len(restored_counts)
    multi_restored = {lid: n for lid, n in restored_counts.items() if n > 1}

    archived_count = len(archived)
    if archived_count == 0:
        ratio: Optional[float] = None
    else:
        ratio = unique_restored / archived_count

    data = {
        "archived_count": archived_count,
        "restored_count": len(restored),
        "unique_restored_lesson_ids": unique_restored,
        "restore_ratio": ratio,
        "since": since.isoformat() if since else "all",
        "until": until.isoformat() if until else "now",
        "multi_restore_warnings": multi_restored,
    }
    return {
        "query": "prune-restore-ratio",
        "version": "1",
        "data": data,
    }


def cmd_claims(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Confidence-gate events aggregated (Sprint 8 Phase 2, ADR-018).

    Returns totals + per-kind counts + pass/fail breakdown + per-agent
    aggregates. Filters via --kind / --agent / --failed-only.
    """
    kind_filter = getattr(args, "kind", None)
    agent_filter = getattr(args, "agent", None)
    failed_only = getattr(args, "failed_only", False)

    total = 0
    claim_count = 0
    pass_count = 0
    fail_count = 0
    per_kind: Dict[str, Dict[str, int]] = {}
    per_agent: Dict[str, Dict[str, int]] = {}

    for e in entries:
        if e.get("action") != "confidence_gate":
            continue
        if failed_only and int(e.get("fail_count", 0)) == 0:
            continue
        if agent_filter and e.get("agent_name", "") != agent_filter:
            continue

        kind_counts = e.get("verifier_kind_counts", {}) or {}
        if kind_filter:
            if kind_filter not in kind_counts:
                continue

        total += 1
        claim_count += int(e.get("claim_count", 0))
        pass_count += int(e.get("pass_count", 0))
        fail_count += int(e.get("fail_count", 0))

        for kind, cnt in kind_counts.items():
            g = per_kind.setdefault(kind, {"total": 0, "events": 0})
            g["total"] += int(cnt)
            g["events"] += 1

        agent = e.get("agent_name", "") or "(unnamed)"
        a = per_agent.setdefault(agent, {"events": 0, "pass": 0, "fail": 0, "claims": 0})
        a["events"] += 1
        a["pass"] += int(e.get("pass_count", 0))
        a["fail"] += int(e.get("fail_count", 0))
        a["claims"] += int(e.get("claim_count", 0))

    fpr = (fail_count / claim_count) if claim_count else None

    return {
        "event_count": total,
        "claim_count": claim_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "failure_rate": fpr,
        "per_kind": per_kind,
        "per_agent": per_agent,
    }


def cmd_metrics(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Cross-cutting derived metrics. Sprint 5 A.2.

    Action-type distribution, total veto rate, average duration per
    benchmark_run, debate completion rate (rounds that reached consensus).
    """
    action_counts = Counter(e.get("action", "unknown") for e in entries)

    # Veto rate: vetoes / (spawns + vetoes)
    spawns = action_counts.get("agent_spawn", 0)
    vetoes = action_counts.get("veto_triggered", 0)
    denom = spawns + vetoes
    veto_rate = (vetoes / denom) if denom else None

    # Debate completion: rounds that reached consensus / rounds started
    rounds_started: set = set()
    rounds_concluded: set = set()
    for e in entries:
        if e.get("action") != "debate_event":
            continue
        key = (e.get("plan_id"), e.get("round"))
        if e.get("phase") == "start":
            rounds_started.add(key)
        elif e.get("phase") == "consensus":
            rounds_concluded.add(key)
    debate_completion = (
        len(rounds_concluded) / len(rounds_started) if rounds_started else None
    )

    # Benchmark duration avg — prefer new duration_ms (÷1000 → s), fall back
    # to legacy duration_s float for logs written before the migration.
    durations = []
    for e in entries:
        if e.get("action") != "benchmark_run":
            continue
        dur_ms = e.get("duration_ms")
        if dur_ms is not None:
            durations.append(int(dur_ms) / 1000.0)
        elif e.get("duration_s") is not None:
            durations.append(float(e.get("duration_s")))
    avg_bench_duration = (
        round(sum(durations) / len(durations), 3) if durations else None
    )

    return {
        "action_counts": dict(action_counts),
        "veto_rate": round(veto_rate, 3) if veto_rate is not None else None,
        "debate_rounds_started": len(rounds_started),
        "debate_rounds_concluded": len(rounds_concluded),
        "debate_completion_rate": (
            round(debate_completion, 3) if debate_completion is not None else None
        ),
        "benchmark_run_count": action_counts.get("benchmark_run", 0),
        "benchmark_avg_duration_s": avg_bench_duration,
        "lesson_write_count": action_counts.get("lesson_write", 0),
    }


def cmd_tokens(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Spawn token aggregates — PLAN-006 Phase 5a (ADR-016).

    Groups `agent_spawn` events by archetype / skill / day and sums
    `tokens_in` / `tokens_out`. Null fields are counted under
    `records_without_tokens` so the operator knows adapter coverage.
    """
    per_skill: Dict[str, Dict[str, int]] = {}
    per_subagent: Dict[str, Dict[str, int]] = {}
    per_day: Dict[str, Dict[str, int]] = {}
    total_in = 0
    total_out = 0
    with_tokens = 0
    without_tokens = 0

    for e in entries:
        if e.get("action") != "agent_spawn":
            continue
        tin = e.get("tokens_in")
        tout = e.get("tokens_out")
        tin_n = tin if isinstance(tin, int) else 0
        tout_n = tout if isinstance(tout, int) else 0
        has_any = isinstance(tin, int) or isinstance(tout, int)
        if has_any:
            with_tokens += 1
            total_in += tin_n
            total_out += tout_n
        else:
            without_tokens += 1

        skill = str(e.get("skill") or "unknown")
        sk = per_skill.setdefault(skill, {"tokens_in": 0, "tokens_out": 0, "spawns": 0})
        sk["tokens_in"] += tin_n
        sk["tokens_out"] += tout_n
        sk["spawns"] += 1

        sub = str(e.get("subagent_type") or "unknown")
        su = per_subagent.setdefault(sub, {"tokens_in": 0, "tokens_out": 0, "spawns": 0})
        su["tokens_in"] += tin_n
        su["tokens_out"] += tout_n
        su["spawns"] += 1

        ts = str(e.get("ts") or "")
        day = ts[:10] if len(ts) >= 10 else "unknown"
        dy = per_day.setdefault(day, {"tokens_in": 0, "tokens_out": 0, "spawns": 0})
        dy["tokens_in"] += tin_n
        dy["tokens_out"] += tout_n
        dy["spawns"] += 1

    return {
        "totals": {
            "tokens_in": total_in,
            "tokens_out": total_out,
            "tokens_total": total_in + total_out,
            "spawns_with_tokens": with_tokens,
            "spawns_without_tokens": without_tokens,
        },
        "per_skill": dict(sorted(per_skill.items())),
        "per_subagent_type": dict(sorted(per_subagent.items())),
        "per_day": dict(sorted(per_day.items())),
    }
