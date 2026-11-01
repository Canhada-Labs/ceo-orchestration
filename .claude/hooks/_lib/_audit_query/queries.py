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
def cmd_summary(entries, args) -> Dict[str, Any]:
    """Summary aggregates — single-pass streaming (Perf-P1-002).

    Accepts any iterable of entries. Computes total / first_ts / last_ts /
    top 5 skills / compliant count in one pass so a 100k-row log does not
    need to be fully materialized.
    """
    total = 0
    first_ts = ""
    last_ts = ""
    skill_counts: Counter = Counter()
    compliant = 0
    for e in entries:
        total += 1
        ts = e.get("ts", "")
        if ts:
            if not first_ts or ts < first_ts:
                first_ts = ts
            if ts > last_ts:
                last_ts = ts
        skill_counts[e.get("skill", "unknown")] += 1
        if (
            e.get("has_profile")
            and e.get("has_file_assignment")
            and e.get("skill") != "unknown"
        ):
            compliant += 1

    if total == 0:
        return {
            "total_spawns": 0,
            "date_range": None,
            "top_skills": [],
            "compliance_rate": None,
        }

    top_skills = skill_counts.most_common(5)
    compliance_rate = compliant / total
    return {
        "total_spawns": total,
        "date_range": {"from": first_ts, "to": last_ts},
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "compliance_rate": round(compliance_rate, 3),
        "compliant_spawns": compliant,
    }


def cmd_by_skill(entries, args) -> List[Dict[str, Any]]:
    """Streamable — single-pass Counter aggregation (Perf-P1-002)."""
    counts: Counter = Counter()
    for e in entries:
        counts[e.get("skill", "unknown")] += 1
    top = counts.most_common(args.top)
    return [{"skill": s, "count": c} for s, c in top]


def cmd_compliance(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Handle the `audit-query compliance` sub-command — SOC2/LGPD evidence pack."""
    total = len(entries)
    if total == 0:
        return {
            "total": 0,
            "has_profile_rate": None,
            "has_file_assignment_rate": None,
            "known_skill_rate": None,
        }

    with_profile = sum(1 for e in entries if e.get("has_profile"))
    with_fa = sum(1 for e in entries if e.get("has_file_assignment"))
    with_skill = sum(1 for e in entries if e.get("skill") != "unknown")

    non_compliant = [
        {
            "ts": e.get("ts"),
            "skill": e.get("skill", "unknown"),
            "has_profile": e.get("has_profile", False),
            "has_file_assignment": e.get("has_file_assignment", False),
            "desc_preview": e.get("desc_preview", ""),
        }
        for e in entries
        if not (
            e.get("has_profile")
            and e.get("has_file_assignment")
            and e.get("skill") != "unknown"
        )
    ]

    return {
        "total": total,
        "has_profile": with_profile,
        "has_profile_rate": round(with_profile / total, 3),
        "has_file_assignment": with_fa,
        "has_file_assignment_rate": round(with_fa / total, 3),
        "known_skill": with_skill,
        "known_skill_rate": round(with_skill / total, 3),
        "non_compliant_count": len(non_compliant),
        "non_compliant": non_compliant[:20],  # cap preview
    }


def cmd_by_day(entries, args) -> List[Dict[str, Any]]:
    """Streamable — single-pass histogram (Perf-P1-002).

    Fast-path: cutoff is compared as a fixed YYYY-MM-DD string (since our
    `ts` format is lexicographically sortable). We only fall back to
    ``datetime.strptime`` when the raw timestamp doesn't match the
    expected 20-char ISO-Z shape — a rare case (parse errors / rotated
    schemas) that does not dominate 100k-entry runs.
    """
    days = args.days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    cutoff_day = cutoff.strftime("%Y-%m-%d")
    histogram: Dict[str, int] = defaultdict(int)
    for e in entries:
        ts = e.get("ts", "")
        if not ts:
            continue
        # Fast path: YYYY-MM-DDTHH:MM:SSZ is 20 chars with day at 0..10
        if len(ts) >= 20 and ts.endswith("Z") and ts[10:11] == "T":
            day_key = ts[:10]
            # Lexicographic compare works because YYYY-MM-DD is fixed width.
            if day_key < cutoff_day:
                continue
        else:
            try:
                when = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            if when < cutoff:
                continue
            day_key = when.strftime("%Y-%m-%d")
        histogram[day_key] += 1

    result = [
        {"date": day, "count": count}
        for day, count in sorted(histogram.items())
    ]
    return result


def cmd_search(entries, args) -> List[Dict[str, Any]]:
    """Streamable — filter via regex (Perf-P1-002)."""
    try:
        pattern = re.compile(args.regex, flags=re.IGNORECASE)
    except re.error as e:
        print(f"[audit-query] ERROR: bad regex: {e}", file=sys.stderr)
        sys.exit(1)
    matches = []
    for e in entries:
        preview = e.get("desc_preview", "")
        if pattern.search(preview):
            matches.append(
                {
                    "ts": e.get("ts"),
                    "skill": e.get("skill"),
                    "desc_preview": preview,
                    "desc_hash": e.get("desc_hash"),
                }
            )
    return matches


def cmd_since(entries, args) -> List[Dict[str, Any]]:
    """Streamable — filter by date cutoff (Perf-P1-002)."""
    # Parse the input date (supports YYYY-MM-DD, YYYY-MM-DDTHH:MM:SSZ)
    raw = args.iso_date
    parsed = None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            continue
    if parsed is None:
        print(
            f"[audit-query] ERROR: cannot parse date {raw!r} "
            "(use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Fast path: both parsed cutoff and entry ts are ISO-Z → string compare
    # is equivalent to datetime compare (fixed-width YYYY-MM-DDTHH:MM:SSZ).
    # Falls back to strptime for non-canonical ts shapes.
    cutoff_str = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for e in entries:
        ts = e.get("ts", "")
        if len(ts) >= 20 and ts.endswith("Z") and ts[10:11] == "T":
            if ts >= cutoff_str:
                out.append(e)
            continue
        try:
            when = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if when >= parsed:
            out.append(e)
    return out


def cmd_stats(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """Handle the `audit-query stats` sub-command — aggregate counts by action."""
    # PLAN-125 WS-1 — per-tool-call lifecycle latency view (--tool-latency).
    if getattr(args, "tool_latency", False):
        return _tool_latency_stats(entries)

    total = len(entries)
    if total == 0:
        return {"total": 0}

    bucket_counts = Counter(
        e.get("prompt_len_bucket", "unknown") for e in entries
    )
    response_kinds = Counter(e.get("response_kind", "absent") for e in entries)

    # hook_duration_ms stats (tolerates missing — older entries don't have it)
    durations = [
        e.get("hook_duration_ms")
        for e in entries
        if isinstance(e.get("hook_duration_ms"), (int, float))
    ]
    duration_summary: Dict[str, Any]
    if durations:
        durations_sorted = sorted(durations)
        duration_summary = {
            "count": len(durations_sorted),
            "min_ms": durations_sorted[0],
            "max_ms": durations_sorted[-1],
            "mean_ms": round(sum(durations_sorted) / len(durations_sorted), 1),
            "p50_ms": _percentile(durations_sorted, 50),
            "p95_ms": _percentile(durations_sorted, 95),
            "p99_ms": _percentile(durations_sorted, 99),
        }
    else:
        duration_summary = {"count": 0}

    return {
        "total": total,
        "prompt_len_buckets": dict(bucket_counts),
        "response_kinds": dict(response_kinds),
        "hook_duration_ms": duration_summary,
    }


def _tool_latency_stats(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """PLAN-125 WS-1 — per-tool lifecycle bucket histogram.

    Reads ``tool_call_lifecycle_recorded`` rows and rolls up, per
    ``tool_name_enum``, a Counter of ``duration_bucket`` plus success / orphan
    tallies. Bucket-counts ONLY — the action never records a raw
    ``duration_ms`` (MF-SEC-3), so there are no percentiles to compute.
    """
    rows = [
        e for e in entries
        if e.get("action") == "tool_call_lifecycle_recorded"
    ]
    per_tool: Dict[str, Dict[str, Any]] = {}
    for e in rows:
        tool = e.get("tool_name_enum", "other")
        if not isinstance(tool, str):
            tool = "other"
        slot = per_tool.setdefault(
            tool,
            {"count": 0, "duration_buckets": Counter(),
             "success": 0, "failure": 0, "orphan": 0},
        )
        slot["count"] += 1
        bucket = e.get("duration_bucket", "unknown")
        if not isinstance(bucket, str):
            bucket = "unknown"
        slot["duration_buckets"][bucket] += 1
        if e.get("orphan") is True:
            slot["orphan"] += 1
        if e.get("success") is True:
            slot["success"] += 1
        elif e.get("success") is False:
            slot["failure"] += 1

    # Materialize Counters to plain dicts for JSON / display.
    tool_latency = {
        tool: {
            "count": slot["count"],
            "duration_buckets": dict(slot["duration_buckets"]),
            "success": slot["success"],
            "failure": slot["failure"],
            "orphan": slot["orphan"],
        }
        for tool, slot in sorted(per_tool.items())
    }
    return {
        "total_lifecycle_rows": len(rows),
        "tool_latency": tool_latency,
    }


def _percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return round(float(sorted_values[f]), 1)
    return round(
        sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f),
        1,
    )


def cmd_errors(args) -> Dict[str, Any]:
    err_path = Path(args.errors_path) if args.errors_path else default_errors_path()
    if not err_path.is_file():
        return {"errors_path": str(err_path), "count": 0, "lines": []}
    try:
        text = err_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[audit-query] ERROR: cannot read {err_path}: {e}", file=sys.stderr)
        sys.exit(2)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    return {
        "errors_path": str(err_path),
        "count": len(lines),
        "lines": lines[-50:],  # tail
    }


def cmd_debate(entries: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """Group debate_event rows by (plan_id, round). Sprint 5 A.2."""
    groups: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for e in entries:
        if e.get("action") != "debate_event":
            continue
        key = (e.get("plan_id", "?"), int(e.get("round") or 0))
        g = groups.setdefault(
            key,
            {
                "plan_id": key[0],
                "round": key[1],
                "start_ts": None,
                "consensus_ts": None,
                "agents": [],
                "consensus_adjustments": None,
            },
        )
        phase = e.get("phase")
        ts = e.get("ts")
        if phase == "start":
            g["start_ts"] = ts
        elif phase == "agent-done":
            agent = e.get("agent")
            if agent and agent not in g["agents"]:
                g["agents"].append(agent)
        elif phase == "consensus":
            g["consensus_ts"] = ts
            if e.get("consensus_adjustments_count") is not None:
                g["consensus_adjustments"] = e["consensus_adjustments_count"]
    # Sort by (plan_id, round)
    return [groups[k] for k in sorted(groups.keys())]


def cmd_plans(entries: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """Show plan status transitions over time. Sprint 5 A.2."""
    by_plan: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e.get("action") != "plan_transition":
            continue
        by_plan[e.get("plan_id", "?")].append(
            {
                "ts": e.get("ts"),
                "from": e.get("from_status"),
                "to": e.get("to_status"),
                "editor": e.get("editor_tool"),
            }
        )
    # Sort transitions by ts, then emit one row per plan with a chain summary
    out = []
    for plan_id in sorted(by_plan.keys()):
        trans = sorted(by_plan[plan_id], key=lambda t: t.get("ts") or "")
        chain = "→".join(
            [t["from"] for t in trans] + [trans[-1]["to"]] if trans else []
        )
        out.append(
            {
                "plan_id": plan_id,
                "transitions": len(trans),
                "chain": chain,
                "first_ts": trans[0]["ts"] if trans else None,
                "last_ts": trans[-1]["ts"] if trans else None,
                "current_status": trans[-1]["to"] if trans else None,
            }
        )
    return out


def cmd_vetoes(entries: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """Aggregate veto_triggered rows by (hook, reason_code). Sprint 5 A.2."""
    counts: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in entries:
        if e.get("action") != "veto_triggered":
            continue
        key = (e.get("hook", "?"), e.get("reason_code", "?"))
        g = counts.setdefault(
            key,
            {
                "hook": key[0],
                "reason_code": key[1],
                "count": 0,
                "first_ts": None,
                "last_ts": None,
                "sample_preview": "",
            },
        )
        g["count"] += 1
        ts = e.get("ts") or ""
        if g["first_ts"] is None or ts < g["first_ts"]:
            g["first_ts"] = ts
        if g["last_ts"] is None or ts > g["last_ts"]:
            g["last_ts"] = ts
        if not g["sample_preview"] and e.get("reason_preview"):
            g["sample_preview"] = e["reason_preview"]
    return sorted(
        counts.values(),
        key=lambda g: (-g["count"], g["hook"], g["reason_code"]),
    )


def cmd_lessons(entries: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """Aggregate lesson_write rows by archetype. Sprint 5 A.2."""
    by_arch: Dict[str, Dict[str, Any]] = {}
    triggers = Counter()
    for e in entries:
        if e.get("action") != "lesson_write":
            continue
        arch = e.get("archetype", "?")
        g = by_arch.setdefault(
            arch,
            {
                "archetype": arch,
                "count": 0,
                "triggers": Counter(),
                "last_ts": None,
            },
        )
        g["count"] += 1
        g["triggers"][e.get("trigger", "unknown")] += 1
        ts = e.get("ts") or ""
        if g["last_ts"] is None or ts > g["last_ts"]:
            g["last_ts"] = ts
        triggers[e.get("trigger", "unknown")] += 1

    out = []
    for arch in sorted(by_arch.keys(), key=lambda a: (-by_arch[a]["count"], a)):
        g = by_arch[arch]
        # Collapse the Counter to a dict for JSON-friendly rendering
        g["triggers"] = dict(g["triggers"])
        out.append(g)
    return out


def _parse_since_arg(raw: str) -> Optional[datetime]:
    """Parse `--since` value: ``24h`` / ``7d`` / ``30m`` / ISO 8601 / ``all``.

    Returns a timezone-aware UTC datetime cutoff, or None for "all time".
    PLAN-009 A18 (shared across new sub-commands).
    """
    if not raw or raw == "all":
        return None
    raw = raw.strip().lower()
    # Shorthand: <int><unit>  (m=minutes, h=hours, d=days)
    if re.fullmatch(r"\d+[mhd]", raw):
        n = int(raw[:-1])
        unit = raw[-1]
        delta = {"m": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n)}[unit]
        return datetime.now(timezone.utc) - delta
    # Try ISO 8601 parse
    try:
        if raw.endswith("z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def cmd_lessons_effectiveness(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query lessons-effectiveness` — per-lesson effectiveness ranking.

    PLAN-009 Phase 5 P5.1. Aggregates `lesson_outcome` + `lesson_read`
    events per `lesson_id`; computes effectiveness + injection count +
    recency; sorts by operator-chosen axis.

    Output envelope (SPEC/v1/audit-query.schema.md):
        {"query": "lessons-effectiveness", "version": "1",
         "data": {"lessons": [...]}}
    """
    since = _parse_since_arg(getattr(args, "since", "24h"))
    include_window_only = getattr(args, "include_window_only", False)
    sort_by = getattr(args, "by", "effectiveness")
    top_n = int(getattr(args, "top", 0) or 0)
    bottom_n = int(getattr(args, "bottom", 0) or 0)

    def _in_window(e: Dict[str, Any]) -> bool:
        if since is None:
            return True
        ts = _parse_since_arg(e.get("ts", ""))
        return ts is None or ts >= since

    from collections import defaultdict
    agg: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"hit": 0, "miss": 0, "injections": 0,
                 "last": "", "modes": {}}
    )

    for e in entries:
        action = e.get("action")
        if action == "lesson_outcome":
            mode = e.get("inference_mode", "") or "unspecified"
            if not include_window_only and mode == "window-only":
                continue
            if not _in_window(e):
                continue
            lid = e.get("lesson_id", "")
            if not lid:
                continue
            # When lesson_id is comma-separated (emit_architect_outcome
            # aggregate emit), split into component ids
            for lid_part in lid.split(","):
                lid_part = lid_part.strip()
                if not lid_part:
                    continue
                a = agg[lid_part]
                if e.get("hit"):
                    a["hit"] += 1
                else:
                    a["miss"] += 1
                a["modes"][mode] = a["modes"].get(mode, 0) + 1
                ts = e.get("ts", "")
                if ts > a["last"]:
                    a["last"] = ts
        elif action == "lesson_read":
            if not _in_window(e):
                continue
            for lid in e.get("lesson_ids", []) or []:
                agg[lid]["injections"] += 1

    # Compute effectiveness + days-since-last
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    lessons = []
    for lid, a in agg.items():
        total = a["hit"] + a["miss"]
        eff = (a["hit"] / total) if total > 0 else None
        days_since = None
        last_dt = _parse_since_arg(a["last"]) if a["last"] else None
        if last_dt is not None:
            days_since = (now - last_dt).total_seconds() / 86400.0
        lessons.append({
            "lesson_id": lid,
            "hit_count": a["hit"],
            "miss_count": a["miss"],
            "effectiveness": eff,
            "days_since_last_outcome": days_since,
            "injection_count": a["injections"],
            "inference_mode_breakdown": a["modes"],
        })

    # Sorting — null effectiveness sorts AFTER non-null (A5/A9)
    warning = None
    if sort_by == "effectiveness":
        lessons.sort(key=lambda x: (
            x["effectiveness"] is None,
            -(x["effectiveness"] or 0.0),
        ))
    elif sort_by == "recency":
        lessons.sort(key=lambda x: (
            x["days_since_last_outcome"] is None,
            x["days_since_last_outcome"] or float("inf"),
        ))
    elif sort_by == "injections":
        # VP unseen #4 — warn about gameable axis
        warning = "sorting by 'injections' is a gameable axis; use with caution"
        lessons.sort(key=lambda x: -x["injection_count"])

    if top_n > 0:
        lessons = lessons[:top_n]
    elif bottom_n > 0:
        lessons = lessons[-bottom_n:][::-1]

    data = {
        "sort_by": sort_by,
        "include_window_only": include_window_only,
        "since": since.isoformat() if since else "all",
        "lesson_count": len(lessons),
        "lessons": lessons,
    }
    if warning:
        data["warning"] = warning
    return {
        "query": "lessons-effectiveness",
        "version": "1",
        "data": data,
    }
