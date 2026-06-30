#!/usr/bin/env python3
"""audit-query — query the ceo-orchestration agent spawn audit log.

Stdlib-only CLI that reads `audit-log.jsonl` (+ rotated siblings) and
answers common operator questions:

    audit-query.py summary
    audit-query.py by-skill [--top N]
    audit-query.py compliance
    audit-query.py by-day [--days N]
    audit-query.py search <regex>
    audit-query.py since <ISO-date>
    audit-query.py errors
    audit-query.py stats
    audit-query.py export [--format csv|json|tsv]
    audit-query.py by-domain [--window=30d|--start=YYYY-MM-DD --end=YYYY-MM-DD]
                              [--check-reopen]

Default input path:
    ${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/ceo-orchestration/audit-log.jsonl}

Pass `--log <path>` to override or `--include-rotated` to aggregate
across all `audit-log*.jsonl` in the audit directory.

Output formats:
    - Default: human-readable tab-separated table
    - `--json` flag: machine-readable JSON
    - `--csv` flag: CSV

Exit codes:
    0 — success (including empty result set)
    1 — log file missing OR bad query
    2 — unreadable log file (permissions, etc.)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path resolution (mirrors audit_log.py conventions)
# ---------------------------------------------------------------------------


def default_log_path() -> Path:
    """Return the conventional audit log path from env vars / defaults."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"
    return Path(
        os.environ.get("CEO_AUDIT_LOG_PATH") or str(default_dir / "audit-log.jsonl")
    )


def default_errors_path() -> Path:
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"
    return Path(
        os.environ.get("CEO_AUDIT_LOG_ERR") or str(default_dir / "audit-log.errors")
    )


def discover_logs(primary: Path, include_rotated: bool) -> List[Path]:
    """Return the list of log files to read, sorted by modification time."""
    if not include_rotated:
        return [primary] if primary.is_file() else []
    if not primary.parent.is_dir():
        return []
    stem = primary.stem  # "audit-log"
    siblings = []
    for candidate in primary.parent.glob(f"{stem}*.jsonl"):
        if candidate.is_file():
            siblings.append(candidate)
    # Sort: primary file last so its entries are newest in the stream
    siblings.sort(key=lambda p: p.stat().st_mtime)
    return siblings


# ---------------------------------------------------------------------------
# Streaming reader — tolerates malformed lines with a stderr breadcrumb
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Perf-P1-002 — large-log materialization warning threshold.
#
# Subcommands that need FULL context (median, percentile, debate grouping,
# weekly-summary) still materialize the list. At this size threshold we
# emit a stderr hint so operators learn the log grew past the streaming
# regime and consider `--include-rotated=false` or log rotation.
# Value = 100_000 entries ≈ ~40-80 MB typical ≈ ~500-900ms parse on a
# modern laptop. Under this bar the materialization is unnoticeable.
_MATERIALIZATION_WARN_THRESHOLD = 100_000


def read_entries(
    paths: Iterable[Path],
    *,
    warn_stream=None,
) -> Iterator[Dict[str, Any]]:
    """Yield parsed JSON entries from the given log paths, streaming.

    Malformed lines are skipped with a breadcrumb to warn_stream.
    Large logs are read line-by-line so memory stays constant.

    Note: warn_stream defaults to None → resolved to sys.stderr at call
    time, not definition time, so test harness stderr redirection works.
    """
    if warn_stream is None:
        warn_stream = sys.stderr
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(
                            f"[audit-query] WARN: {path}:{lineno}: "
                            f"skipping malformed JSONL ({e.msg})",
                            file=warn_stream,
                        )
                        continue
                    if not isinstance(entry, dict):
                        continue
                    yield entry
        except OSError as e:
            print(
                f"[audit-query] WARN: cannot read {path}: {e}",
                file=warn_stream,
            )


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------


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


def _bench_cost_usd(r: Dict[str, Any]) -> float:
    """Per-run benchmark cost in USD. Prefers the int-encoded
    ``cost_usd_cents`` (÷100); falls back to a legacy float ``cost_usd``.
    Returns 0.0 when neither is present (pre-cost-instrumented runs)."""
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


def _bench_turns(r: Dict[str, Any]) -> int:
    """Per-run scenario count (the harbor 'turns' column). Each scenario
    is one model interaction unit; pass+fail covers every scored
    scenario. Tolerates missing counts."""
    try:
        return int(r.get("pass_count") or 0) + int(r.get("fail_count") or 0)
    except (TypeError, ValueError):
        return 0


def cmd_benchmarks(
    entries: List[Dict[str, Any]], args
) -> List[Dict[str, Any]]:
    """Aggregate benchmark_run rows by skill. Sprint 5 A.2; PLAN-133 C4.

    Reports run count, latest pass_rate, median across runs, cumulative
    lessons_written per skill.

    PLAN-133 C4 (harbor-style row): co-reports **cost + compute + turns
    alongside pass-rate** so a benchmark is never read as a bare scalar.
    The added columns are strictly additive (existing keys unchanged) and
    derive only from fields already on the ``benchmark_run`` event
    (``cost_usd_cents``, ``duration_ms``, ``pass_count``/``fail_count``) —
    no SPEC change is required, so this reader stays $0 and canonical-free.
    """
    by_skill: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e.get("action") != "benchmark_run":
            continue
        by_skill[e.get("skill", "?")].append(e)
    out = []
    for skill in sorted(by_skill.keys()):
        runs = sorted(by_skill[skill], key=lambda r: r.get("ts") or "")
        # Prefer new int-encoded fields (bps ÷ 1000 → float); fall back to
        # the legacy float fields for logs written before the migration.
        def _pass_rate(r: Dict[str, Any]) -> float:
            bps = r.get("pass_rate_bps")
            if bps is not None:
                return int(bps) / 1000.0
            return float(r.get("pass_rate") or 0.0)

        def _floor_rate(r: Dict[str, Any]) -> float:
            bps = r.get("floor_bps")
            if bps is not None:
                return int(bps) / 1000.0
            return float(r.get("floor") or 0.0)

        rates = [_pass_rate(r) for r in runs]
        if rates:
            med = _percentile(sorted(rates), 50)
        else:
            med = 0.0
        latest = runs[-1]
        # PLAN-133 C4 — harbor-style compute/cost/turns co-report.
        # Cumulative across all runs for the skill + the latest single run,
        # so an operator sees both the trend cost and the marginal cost.
        total_cost = sum(_bench_cost_usd(r) for r in runs)
        total_compute_s = sum(_bench_duration_s(r) for r in runs)
        total_turns = sum(_bench_turns(r) for r in runs)
        out.append(
            {
                "skill": skill,
                "runs": len(runs),
                "latest_pass_rate": round(_pass_rate(latest), 3),
                "median_pass_rate": med,
                "last_floor": _floor_rate(latest),
                "latest_ts": latest.get("ts"),
                "total_lessons_written": sum(
                    int(r.get("lessons_written") or 0) for r in runs
                ),
                # --- PLAN-133 C4 harbor-style row (additive) ---
                "latest_cost_usd": round(_bench_cost_usd(latest), 6),
                "total_cost_usd": round(total_cost, 6),
                "latest_compute_s": round(_bench_duration_s(latest), 3),
                "total_compute_s": round(total_compute_s, 3),
                "latest_turns": _bench_turns(latest),
                "total_turns": total_turns,
            }
        )
    return out


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


def cmd_health(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """High-level framework health. Sprint 5 A.2.

    Rolls up several gates into an overall PASS/WARN/FAIL verdict so
    `audit-dashboard.py` and ops tooling have one call to make.
    """
    total = len(entries)
    if total == 0:
        return {"verdict": "NO_DATA", "total_events": 0, "gates": {}}

    compliance = cmd_compliance(entries, args)
    metrics = cmd_metrics(entries, args)

    gates: Dict[str, str] = {}

    # Gate 1: compliance rate >= 0.95
    known_rate = compliance.get("known_skill_rate")
    if known_rate is None:
        gates["compliance"] = "NO_DATA"
    elif known_rate >= 0.95:
        gates["compliance"] = "PASS"
    elif known_rate >= 0.8:
        gates["compliance"] = "WARN"
    else:
        gates["compliance"] = "FAIL"

    # Gate 2: veto rate < 0.15
    veto_rate = metrics.get("veto_rate")
    if veto_rate is None:
        gates["vetoes"] = "NO_DATA"
    elif veto_rate < 0.05:
        gates["vetoes"] = "PASS"
    elif veto_rate < 0.15:
        gates["vetoes"] = "WARN"
    else:
        gates["vetoes"] = "FAIL"

    # Gate 3: debate completion rate >= 0.8 (if any rounds started)
    dc = metrics.get("debate_completion_rate")
    if dc is None:
        gates["debate_completion"] = "NO_DATA"
    elif dc >= 0.8:
        gates["debate_completion"] = "PASS"
    elif dc >= 0.5:
        gates["debate_completion"] = "WARN"
    else:
        gates["debate_completion"] = "FAIL"

    # Verdict reduction
    if any(v == "FAIL" for v in gates.values()):
        verdict = "FAIL"
    elif any(v == "WARN" for v in gates.values()):
        verdict = "WARN"
    elif all(v in ("PASS", "NO_DATA") for v in gates.values()):
        verdict = "PASS"
    else:
        verdict = "WARN"

    return {
        "verdict": verdict,
        "total_events": total,
        "gates": gates,
        "known_skill_rate": known_rate,
        "veto_rate": veto_rate,
        "debate_completion_rate": dc,
        "action_counts": metrics.get("action_counts", {}),
    }


def cmd_export(entries: List[Dict[str, Any]], args) -> Any:
    """Handle the `audit-query export` sub-command — emit filtered audit-log slices."""
    fmt = args.export_format
    if fmt == "json":
        return entries
    if fmt == "csv":
        buf = io.StringIO()
        if not entries:
            return ""
        fieldnames = sorted({k for e in entries for k in e.keys()})
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            writer.writerow(e)
        return buf.getvalue()
    if fmt == "tsv":
        buf = io.StringIO()
        if not entries:
            return ""
        fieldnames = sorted({k for e in entries for k in e.keys()})
        writer = csv.DictWriter(
            buf, fieldnames=fieldnames, extrasaction="ignore", delimiter="\t"
        )
        writer.writeheader()
        for e in entries:
            writer.writerow(e)
        return buf.getvalue()
    raise ValueError(f"unsupported export format: {fmt}")


# ---------------------------------------------------------------------------
# PLAN-080 Phase 1 — by-domain sub-command
# ---------------------------------------------------------------------------

# Default window for by-domain (calendar days, trailing from UTC midnight)
_BY_DOMAIN_DEFAULT_WINDOW_DAYS = 30

# Sentinel used when no dispatch_archetype_hint is available
_UNKNOWN_BUCKET = "UNKNOWN"

# Default policy file location (relative to repo root, resolved at runtime)
_GRANDFATHER_POLICY_RELPATH = ".claude/policies/grandfather-cap.policy.yaml"


def _parse_domain_date(raw: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD into a UTC-aware datetime (midnight UTC).

    Returns None on failure (not sys.exit — caller handles the error).
    """
    try:
        dt = datetime.strptime(raw.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _resolve_window_bounds(
    args,
) -> Tuple[Optional[datetime], Optional[datetime], str]:
    """Resolve --window / --start / --end into (start_dt, end_dt, window_label).

    Returns (start_dt, end_dt, label) where:
      - start_dt: inclusive lower bound (UTC midnight); None means no lower bound
      - end_dt:   inclusive upper bound (UTC now for default windows)
      - label:    human-readable description of the window

    Validates start <= end; prints error + sys.exit(1) on invalid input.
    """
    now = datetime.now(timezone.utc)
    # --start / --end take precedence over --window
    start_raw = getattr(args, "start", None)
    end_raw = getattr(args, "end", None)
    window_raw = getattr(args, "window", None) or f"{_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d"

    if start_raw or end_raw:
        if not start_raw or not end_raw:
            print(
                "[audit-query] ERROR: by-domain: --start and --end must both be provided",
                file=sys.stderr,
            )
            sys.exit(1)
        start_dt = _parse_domain_date(start_raw)
        end_dt = _parse_domain_date(end_raw)
        if start_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --start date {start_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        if end_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --end date {end_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        # Make end_dt the end of that calendar day (23:59:59 UTC)
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        if start_dt > end_dt:
            print(
                f"[audit-query] ERROR: by-domain: --start ({start_raw}) is after "
                f"--end ({end_raw})",
                file=sys.stderr,
            )
            sys.exit(1)
        label = f"{start_raw} to {end_raw}"
        return start_dt, end_dt, label

    # Parse --window (e.g. "30d", "7d")
    m = re.fullmatch(r"(\d+)([dhm])", window_raw.strip().lower())
    if not m:
        print(
            f"[audit-query] ERROR: by-domain: invalid --window {window_raw!r}; "
            "expected e.g. 30d, 7d, 14d",
            file=sys.stderr,
        )
        sys.exit(1)
    n, unit = int(m.group(1)), m.group(2)
    delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
    start_dt = now - delta
    label = f"trailing {window_raw}"
    return start_dt, now, label


def _load_sunset_domains(args) -> Optional[List[str]]:
    """Load sunset domain list for --check-reopen.

    Sources (in priority order):
    1. CEO_GRANDFATHER_POLICY_PATH env var
    2. <repo_root>/.claude/policies/grandfather-cap.policy.yaml (if exists)
    3. stdin JSON list (if CEO_BY_DOMAIN_SUNSET_STDIN=1)

    Returns a list of domain slugs, or None if the policy file is not found
    and stdin mode is not active. An empty list [] means "policy found but
    no sunset members".
    """
    # Check env override
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    if policy_path_env:
        p = Path(policy_path_env)
        if p.is_file():
            return _parse_sunset_from_policy(p)
        print(
            f"[audit-query] WARN: CEO_GRANDFATHER_POLICY_PATH={policy_path_env!r} "
            "not found; no sunset list loaded",
            file=sys.stderr,
        )
        return []

    # Try conventional project-relative path via CLAUDE_PROJECT_DIR or cwd
    for base_env in ("CLAUDE_PROJECT_DIR",):
        base = os.environ.get(base_env)
        if base:
            p = Path(base) / _GRANDFATHER_POLICY_RELPATH
            if p.is_file():
                return _parse_sunset_from_policy(p)

    # Try cwd-relative (developer convenience)
    p = Path(_GRANDFATHER_POLICY_RELPATH)
    if p.is_file():
        return _parse_sunset_from_policy(p)

    # Stdin JSON fallback (CEO_BY_DOMAIN_SUNSET_STDIN=1 for testing)
    if os.environ.get("CEO_BY_DOMAIN_SUNSET_STDIN") == "1":
        try:
            raw = sys.stdin.read()
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except (json.JSONDecodeError, OSError):
            pass
        return []

    return None  # policy not found — caller will skip reopen check


def _parse_sunset_from_policy(path: Path) -> List[str]:
    """Extract sunset domain members from grandfather-cap.policy.yaml.

    Parses the YAML manually using stdlib (no PyYAML dependency).
    Looks for `domain_bundles.members:` list block.

    Returns list of domain slug strings (may be empty).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Simple line-based YAML parser for the members list.
    # We scan for "members:" under "domain_bundles:" section.
    in_domain_bundles = False
    in_members = False
    members: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "domain_bundles:":
            in_domain_bundles = True
            in_members = False
            continue
        if in_domain_bundles:
            # Another top-level key → leave domain_bundles section
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_domain_bundles = False
                in_members = False
                continue
            if stripped == "members:":
                in_members = True
                continue
            if in_members:
                if stripped.startswith("- "):
                    member = stripped[2:].strip()
                    if member:
                        members.append(member)
                elif stripped and not stripped.startswith("-"):
                    # End of list
                    in_members = False

    return members


def _load_sunset_reopen_options(args) -> Optional[Dict[str, bool]]:
    """M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1) — load reopen filter flags.

    Returns dict with `requires_hint_match` and `unknown_excluded` boolean
    flags read from the same grandfather-cap.policy.yaml as
    `_load_sunset_domains`. Defaults to {True, True} if either flag is
    missing/unparseable. Returns None if the policy file is not found.
    """
    # Reuse the same path resolution as _load_sunset_domains for consistency
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    candidates: List[Path] = []
    if policy_path_env:
        candidates.append(Path(policy_path_env))
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    if base:
        candidates.append(Path(base) / _GRANDFATHER_POLICY_RELPATH)
    candidates.append(Path(_GRANDFATHER_POLICY_RELPATH))

    for p in candidates:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        return _parse_sunset_reopen_flags(text)
    return None


def _parse_sunset_reopen_flags(text: str) -> Dict[str, bool]:
    """Parse `sunset_reopen_requires_hint_match` and `sunset_reopen_unknown_excluded`.

    Both flags default to True if missing (defensive — secure-by-default).
    """
    requires_hint_match = True
    unknown_excluded = True
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if s.startswith("sunset_reopen_requires_hint_match:"):
            v = s.split(":", 1)[1].strip().lower()
            requires_hint_match = (v == "true" or v.startswith("true"))
        elif s.startswith("sunset_reopen_unknown_excluded:"):
            v = s.split(":", 1)[1].strip().lower()
            unknown_excluded = (v == "true" or v.startswith("true"))
    return {
        "requires_hint_match": requires_hint_match,
        "unknown_excluded": unknown_excluded,
    }


def _entry_ts_to_dt(ts: str) -> Optional[datetime]:
    """Parse a log entry `ts` field into a UTC datetime."""
    if not ts:
        return None
    try:
        s = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cmd_by_domain(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query by-domain` — spawn activity grouped by dispatch_archetype_hint.

    PLAN-080 Phase 1 — domain-level observability for squad-bundle governance.

    Groups `agent_spawn` events by `dispatch_archetype_hint` field if present;
    falls back to `archetype` field, then to the "UNKNOWN" bucket. Entries
    outside the requested time window are excluded.

    Output columns:
      Domain | Spawns | First seen | Last seen | hint_coverage_pct

    Sorted deterministically by domain name (alphabetic, UNKNOWN last).

    With --check-reopen: additionally filters to domains present in the sunset
    list from grandfather-cap.policy.yaml. Reports domains with >= 1 spawn
    where hint matches a sunset domain (UNKNOWN excluded per M2-CDX-7).
    """
    start_dt, end_dt, window_label = _resolve_window_bounds(args)

    # Load sunset list + reopen options if --check-reopen requested
    check_reopen = getattr(args, "check_reopen", False)
    sunset_domains: Optional[List[str]] = None
    # M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1): honor policy flags.
    # Defaults match policy semantics when flags missing/unparseable.
    requires_hint_match = True       # sunset_reopen_requires_hint_match (default true per §8)
    unknown_excluded = True          # sunset_reopen_unknown_excluded (M2-CDX-7 default true)
    if check_reopen:
        sunset_domains = _load_sunset_domains(args)
        sunset_options = _load_sunset_reopen_options(args)
        if sunset_options is not None:
            requires_hint_match = sunset_options.get("requires_hint_match", True)
            unknown_excluded = sunset_options.get("unknown_excluded", True)
        if sunset_domains is None:
            print(
                "[audit-query] WARN: by-domain --check-reopen: no sunset policy file "
                "found; skipping reopen filter. Set CEO_GRANDFATHER_POLICY_PATH or "
                "place grandfather-cap.policy.yaml at "
                f"{_GRANDFATHER_POLICY_RELPATH}",
                file=sys.stderr,
            )

    # Aggregation state per domain bucket
    # domain → {spawns, first_ts, last_ts, with_hint, total}
    domain_agg: Dict[str, Dict[str, Any]] = {}

    total_in_window = 0
    total_with_hint = 0

    for e in entries:
        if e.get("action") != "agent_spawn":
            continue

        ts_raw = e.get("ts", "")
        entry_dt = _entry_ts_to_dt(ts_raw)

        # Apply window filter
        if start_dt is not None and entry_dt is not None:
            if entry_dt < start_dt:
                continue
        if end_dt is not None and entry_dt is not None:
            if entry_dt > end_dt:
                continue

        total_in_window += 1

        # Determine domain bucket
        hint = e.get("dispatch_archetype_hint")
        if hint and isinstance(hint, str) and hint.strip():
            domain = hint.strip()
            has_hint = True
            total_with_hint += 1
        else:
            # Fallback: archetype field
            arch = e.get("archetype")
            if arch and isinstance(arch, str) and arch.strip():
                domain = arch.strip()
            else:
                domain = _UNKNOWN_BUCKET
            has_hint = False

        bucket = domain_agg.setdefault(
            domain,
            {
                "spawns": 0,
                "first_ts": ts_raw or "",
                "last_ts": ts_raw or "",
                "with_hint": 0,
                "total": 0,
            },
        )
        bucket["spawns"] += 1
        bucket["total"] += 1
        if has_hint:
            bucket["with_hint"] += 1
        if ts_raw:
            if not bucket["first_ts"] or ts_raw < bucket["first_ts"]:
                bucket["first_ts"] = ts_raw
            if ts_raw > bucket["last_ts"]:
                bucket["last_ts"] = ts_raw

    # Build output rows
    rows: List[Dict[str, Any]] = []
    for domain in sorted(domain_agg.keys(), key=lambda d: ("" if d != _UNKNOWN_BUCKET else "\xff") + d):
        b = domain_agg[domain]
        hint_pct = round(b["with_hint"] / b["total"] * 100, 1) if b["total"] > 0 else 0.0
        row: Dict[str, Any] = {
            "domain": domain,
            "spawns": b["spawns"],
            "first_seen": b["first_ts"][:10] if b["first_ts"] else "",
            "last_seen": b["last_ts"][:10] if b["last_ts"] else "",
            "hint_coverage_pct": hint_pct,
        }
        rows.append(row)

    # Apply --check-reopen filter
    # M2-CDX-7: UNKNOWN excluded when sunset_reopen_unknown_excluded=true (default)
    # M2-CDX-4: When sunset_reopen_requires_hint_match=true (default), only
    #   spawns whose ORIGINAL audit row carried `dispatch_archetype_hint`
    #   (has_hint=True) qualify for reopen. archetype-fallback rows do not
    #   trigger reopen (per PLAN-080 §8: "spawn carries dispatch_archetype_hint
    #   matching the sunset domain's archetype set").
    if check_reopen and sunset_domains is not None:
        sunset_set = set(sunset_domains)
        reopen_rows = []
        for r in rows:
            if unknown_excluded and r["domain"] == _UNKNOWN_BUCKET:
                continue
            if r["domain"] not in sunset_set:
                continue
            if r["spawns"] < 1:
                continue
            if requires_hint_match:
                # Reopen requires at least one hint-source spawn matching this
                # sunset domain. Use the per-bucket `with_hint` count from the
                # aggregation — bucket["with_hint"] tracks how many spawns in
                # this domain bucket arrived with dispatch_archetype_hint set.
                bucket = domain_agg.get(r["domain"], {})
                if int(bucket.get("with_hint", 0)) < 1:
                    continue
            reopen_rows.append(r)
    else:
        reopen_rows = []

    # Build markdown table
    def _md_table(table_rows: List[Dict[str, Any]]) -> str:
        if not table_rows:
            return "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |\n" \
                   "| ------ | ------ | ---------- | --------- | ----------------- |\n" \
                   "| (no results) | - | - | - | - |\n"
        lines = [
            "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |",
            "| ------ | ------ | ---------- | --------- | ----------------- |",
        ]
        for r in table_rows:
            lines.append(
                f"| {r['domain']} | {r['spawns']} | {r['first_seen']} "
                f"| {r['last_seen']} | {r['hint_coverage_pct']}% |"
            )
        return "\n".join(lines) + "\n"

    output: Dict[str, Any] = {
        "query": "by-domain",
        "version": "1",
        "window": window_label,
        "total_spawns_in_window": total_in_window,
        "overall_hint_coverage_pct": (
            round(total_with_hint / total_in_window * 100, 1)
            if total_in_window > 0
            else 0.0
        ),
        "domain_count": len(rows),
        "domains": rows,
        "markdown_table": _md_table(rows),
    }

    if check_reopen:
        output["check_reopen"] = {
            "sunset_domains_loaded": len(sunset_domains) if sunset_domains is not None else 0,
            "reopen_candidates": reopen_rows,
            "reopen_count": len(reopen_rows),
            "note": (
                "Domains from sunset list with >= 1 spawn in window. "
                "UNKNOWN bucket excluded per M2-CDX-7."
            ),
        }

    return output


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def render(result: Any, *, as_json: bool, as_csv: bool) -> str:
    """Render query results into the requested output format (text / json / markdown)."""
    if as_json:
        return json.dumps(result, indent=2, ensure_ascii=True)
    if as_csv and isinstance(result, list) and result and isinstance(result[0], dict):
        buf = io.StringIO()
        fieldnames = sorted({k for e in result for k in e.keys()})
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in result:
            writer.writerow(e)
        return buf.getvalue()

    # Default: pretty-print
    if isinstance(result, dict):
        # by-domain: prefer the embedded markdown table for human output
        if result.get("query") == "by-domain" and "markdown_table" in result:
            lines = [
                f"window: {result.get('window', '')}",
                f"total_spawns: {result.get('total_spawns_in_window', 0)}",
                f"overall_hint_coverage: {result.get('overall_hint_coverage_pct', 0)}%",
                f"domain_count: {result.get('domain_count', 0)}",
                "",
                result["markdown_table"],
            ]
            if "check_reopen" in result:
                cr = result["check_reopen"]
                lines += [
                    "--- Reopen check ---",
                    f"sunset_domains_loaded: {cr.get('sunset_domains_loaded', 0)}",
                    f"reopen_candidates: {cr.get('reopen_count', 0)}",
                ]
                for row in cr.get("reopen_candidates", []):
                    lines.append(f"  * {row['domain']} ({row['spawns']} spawns)")
            return "\n".join(lines)
        return _format_dict(result)
    if isinstance(result, list):
        if not result:
            return "(no results)"
        if isinstance(result[0], dict):
            return _format_table(result)
        return "\n".join(str(x) for x in result)
    return str(result)


def _format_dict(d: Dict[str, Any]) -> str:
    lines = []
    for key, value in d.items():
        if isinstance(value, (list, dict)):
            lines.append(f"{key}:")
            sub = _format_dict(value) if isinstance(value, dict) else _format_list_under(value)
            for ln in sub.split("\n"):
                lines.append(f"  {ln}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_list_under(items: List[Any]) -> str:
    if not items:
        return "(empty)"
    if isinstance(items[0], dict):
        return _format_table(items)
    return "\n".join(f"- {x}" for x in items)


def _format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"
    fieldnames = list(rows[0].keys())
    # Compute column widths
    widths = {f: len(f) for f in fieldnames}
    str_rows = []
    for r in rows:
        str_row = {}
        for f in fieldnames:
            s = str(r.get(f, ""))
            str_row[f] = s
            if len(s) > widths[f]:
                widths[f] = min(len(s), 80)
        str_rows.append(str_row)
    header = " | ".join(f.ljust(widths[f]) for f in fieldnames)
    sep = "-+-".join("-" * widths[f] for f in fieldnames)
    body = "\n".join(
        " | ".join(str(r[f])[: widths[f]].ljust(widths[f]) for f in fieldnames)
        for r in str_rows
    )
    return f"{header}\n{sep}\n{body}"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PLAN-081 Phase 6-bis — Pair-Rail label store + fp-rate aggregator + Codex
# writeguard summary (R1 S-TDE-3 + S-TDE Q2). Owner labels Case B verdicts
# post-hoc; fp-rate computes lower/upper bounds; codex-writeguard-summary
# aggregates deny-list hits.
# ---------------------------------------------------------------------------

_LABEL_STORE_PATH = (
    Path(__file__).resolve().parent / "audit-log-labels.jsonl"
)
# ADR-108 §Operational labeling protocol: Owner labels Case-B verdicts with
# fp (false-positive — Codex was wrong; close as advisory), tp (true-positive
# — block stands), or triage_pending (extends grace by 24h; max 1 extension
# before mechanical close-as-advisory). retracted is added for explicit Owner
# revocation of a prior label (creates a new chain entry that supersedes).
_LABEL_VALID_CASES = frozenset(["A", "B", "C", "D", "E", "F"])
_LABEL_VALID_LABELS = frozenset(["fp", "tp", "triage_pending", "retracted"])


def _label_store_path() -> Path:
    """Return the labels jsonl path; env override for tests."""
    override = os.environ.get("CEO_PAIR_RAIL_LABEL_STORE_PATH")
    return Path(override) if override else _LABEL_STORE_PATH


def _canonical_json_for_chain(record: Dict[str, Any]) -> str:
    """Canonical JSON for HMAC chain — sort keys + no whitespace + UTF-8."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _compute_label_hmac(prev_hmac_hex: str, record: Dict[str, Any]) -> str:
    """Compute HMAC-SHA256 over (prev_hmac || canonical_record) using
    the same key as `audit_hmac.get_or_create_key()`. Each record's
    `hmac` field links to the previous record's hmac forming a chain.

    Hexlified output for jsonl-friendly storage.
    """
    import hmac as _hmac
    import hashlib as _hashlib
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
    try:
        import audit_hmac  # type: ignore
        key = audit_hmac.get_or_create_key()
    except Exception:
        # Fallback: deterministic per-project SHA-256 chain when key infra
        # unavailable (e.g. fresh adopter clone). This still provides
        # tamper-evidence (mutating an old record breaks subsequent chain
        # verification) but is not authenticated against an external key.
        key = b"ceo-pair-rail-label-chain-fallback-key-v1"
    msg = (prev_hmac_hex + _canonical_json_for_chain(record)).encode("utf-8")
    return _hmac.new(key, msg, _hashlib.sha256).hexdigest()


def _load_label_records() -> List[Dict[str, Any]]:
    """Read label jsonl + verify HMAC chain. Returns list of records or [].

    On HMAC mismatch, raises ValueError with the offending record index.
    """
    p = _label_store_path()
    if not p.exists():
        return []
    records: List[Dict[str, Any]] = []
    prev_hmac = ""  # genesis
    with p.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"audit-log-labels.jsonl record {idx}: invalid JSON: {e}"
                ) from e
            stored_hmac = rec.pop("hmac", "")
            record_for_compute = dict(rec)
            expected_hmac = _compute_label_hmac(prev_hmac, record_for_compute)
            if stored_hmac != expected_hmac:
                raise ValueError(
                    f"audit-log-labels.jsonl record {idx}: HMAC chain broken "
                    f"(stored={stored_hmac[:16]}, computed={expected_hmac[:16]})"
                )
            rec["hmac"] = stored_hmac
            records.append(rec)
            prev_hmac = stored_hmac
    return records


def _append_label_record(record: Dict[str, Any]) -> str:
    """Append a record to label store with HMAC chain link. Returns the new HMAC."""
    p = _label_store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    records = _load_label_records()
    prev_hmac = records[-1]["hmac"] if records else ""
    new_hmac = _compute_label_hmac(prev_hmac, record)
    full_record = dict(record)
    full_record["hmac"] = new_hmac
    with p.open("a", encoding="utf-8") as fh:
        fh.write(_canonical_json_for_chain(full_record) + "\n")
    return new_hmac


def cmd_label(entries, args) -> Dict[str, Any]:
    """Owner labels a pair_rail_case event post-hoc. PLAN-081 Phase 6-bis.

    Append-only via HMAC chain to `.claude/scripts/audit-log-labels.jsonl`.
    The Owner labels Case B (Claude PASS + Codex BLOCK) verdicts per
    ADR-108 §Owner labeling protocol with one of:

    - fp (false-positive — Codex was wrong; close as advisory)
    - tp (true-positive — block stands)
    - triage_pending (extends grace by 24h; max 1 extension before
      mechanical close-as-advisory)
    - retracted (creates new chain entry that supersedes the latest
      prior label for the same run_id; if retracted is the most-recent
      entry, the event reverts to unlabeled status in fp-rate computations)

    fp-rate aggregator (cmd_fp_rate) denominator behavior: case_b_total
    ALWAYS includes every Case-B event in the window. The numerator
    counts only `fp` labels for the lower bound; unlabeled +
    triage_pending count as worst-case FP for the upper bound. See
    cmd_fp_rate docstring for the Wilson 95% bounds details.
    """
    run_id = getattr(args, "run_id", None)
    case = getattr(args, "case", None)
    label = getattr(args, "label", None)
    note = getattr(args, "note", "") or ""

    if not run_id:
        return {"verdict": "ERROR", "reason": "--run-id required"}
    if case not in _LABEL_VALID_CASES:
        return {
            "verdict": "ERROR",
            "reason": f"--case must be one of {sorted(_LABEL_VALID_CASES)}, got {case!r}",
        }
    if label not in _LABEL_VALID_LABELS:
        return {
            "verdict": "ERROR",
            "reason": f"--label must be one of {sorted(_LABEL_VALID_LABELS)}, got {label!r}",
        }

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "ts": ts,
        "run_id": run_id,
        "case": case,
        "label": label,
        "note_bucket": "empty" if not note else (
            "short" if len(note) <= 50 else "medium" if len(note) <= 200 else "long"
        ),
    }
    new_hmac = _append_label_record(record)
    return {
        "verdict": "OK",
        "run_id": run_id,
        "case": case,
        "label": label,
        "ts": ts,
        "hmac_prefix": new_hmac[:16],
    }


def _wilson_bounds(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for binomial proportion (ADR-108 §FP-rate).

    More accurate than naive (p ± z·sqrt(p(1-p)/n)) at small n or
    extreme p. Returns (lower, upper) ∈ [0, 1].
    """
    if n <= 0:
        return 0.0, 0.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half_width = (z * ((p * (1.0 - p) + z2 / (4.0 * n)) / n) ** 0.5) / denom
    lo = max(0.0, center - half_width)
    hi = min(1.0, center + half_width)
    return lo, hi


def cmd_fp_rate(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (R1 S-TDE-3 + ADR-108 §FP-rate): Case-B
    false-positive rate aggregator with 95% Wilson score interval.

    The Wilson interval provides robust lower/upper bounds at small n or
    extreme proportions, which a simple Laplace bound underestimates. Per
    ADR-108 §FP-rate, the reopen criterion fires when fp_rate_30d > 30%
    via `disable_predicate_eval.py` `fp_rate_30d_above_30pct` predicate.

    Labels per ADR-108 §Owner labeling protocol:
    - `fp` = labeled false-positive — counted in numerator + denominator
    - `tp` = labeled true-positive — counted in denominator (not in fp num)
    - `triage_pending` = grace extended — counted in denominator (still
      provisional; treated as labeled-pending for Wilson computation)
    - `retracted` = supersedes prior label — most-recent non-retracted
      label wins; if retracted is the latest entry for a run_id, the
      event reverts to unlabeled
    The denominator (case_b_total) ALWAYS includes every Case-B event in
    the window — labeled or not. Wilson upper bound treats unlabeled +
    triage_pending as worst-case FP.

    Window selection via --window-days (default 30).
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 30  # default 30-day window per ADR-108 §FP-rate

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter pair_rail_case events in window — only Case B (asymmetric case)
    case_b_total = 0
    case_b_run_ids: List[str] = []
    for e in entries:
        if e.get("action") != "pair_rail_case":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        if e.get("case") != "B":
            continue
        case_b_total += 1
        rid = str(e.get("run_id") or e.get("pair_rail_run_id") or "")
        if rid:
            case_b_run_ids.append(rid)

    # Load labels + match by run_id (latest label wins per run_id; retracted
    # entries supersede prior labels)
    try:
        labels = _load_label_records()
    except ValueError as exc:
        return {"verdict": "ERROR", "reason": str(exc)}

    label_index: Dict[str, str] = {}  # run_id → most-recent non-retracted label
    for r in labels:
        if r.get("case") != "B":
            continue
        rid = str(r.get("run_id", ""))
        lab = str(r.get("label", ""))
        if lab == "retracted":
            label_index.pop(rid, None)
        else:
            label_index[rid] = lab

    labeled_fp = 0
    labeled_tp = 0
    labeled_triage = 0
    unlabeled = 0
    for rid in case_b_run_ids:
        lab = label_index.get(rid)
        if lab == "fp":
            labeled_fp += 1
        elif lab == "tp":
            labeled_tp += 1
        elif lab == "triage_pending":
            labeled_triage += 1
        else:
            unlabeled += 1

    # Wilson 95% bounds: numerator = labeled_fp, denominator = case_b_total
    # Upper bound assumes both unlabeled AND triage_pending are worst-case
    # FP per ADR-108 §FP-rate + cmd_label/cmd_fp_rate docstring contract
    # (Codex iter-6 P2 fix — implementation now matches docstring).
    fp_lo, _ = _wilson_bounds(labeled_fp, case_b_total)
    worst_case_fp = labeled_fp + unlabeled + labeled_triage
    _, fp_hi_via_worst = _wilson_bounds(worst_case_fp, case_b_total)
    fp_hi = fp_hi_via_worst

    # Reopen threshold per ADR-108 §FP-rate (default 0.30 — the 30% bar that
    # triggers `fp_rate_30d_above_30pct` predicate in disable_predicate_eval.py)
    threshold = float(getattr(args, "reopen_threshold", None) or 0.30)
    trigger_reopen = fp_lo > threshold

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case_b_total": case_b_total,
        "case_b_labeled_fp": labeled_fp,
        "case_b_labeled_tp": labeled_tp,
        "case_b_labeled_triage": labeled_triage,
        "case_b_unlabeled": unlabeled,
        "fp_rate_lower_bound": round(fp_lo, 4),
        "fp_rate_upper_bound": round(fp_hi, 4),
        "wilson_z": 1.96,
        "reopen_threshold": threshold,
        "trigger_reopen": trigger_reopen,
        "predicate_ref": "fp_rate_30d_above_30pct",
    }


def cmd_case_summary(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (ADR-108 §Operational): Cases A-F distribution.

    Aggregates `pair_rail_case` audit events over the window and returns
    counts + percentages for each Case (A=both PASS, B=Claude PASS+Codex
    BLOCK, C=Claude BLOCK+Codex PASS, D=both BLOCK, E=Jaccard divergence,
    F=Codex outage). Operators use this to monitor healthy distribution
    per ADR-108 §Operational (Case A typically 70-85%; Case F < 2%).
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 7  # default 7-day window (faster operational signal)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    per_case: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    unknown_case = 0
    precondition_met_count = 0
    precondition_not_met_count = 0  # Case B'
    for e in entries:
        if e.get("action") != "pair_rail_case":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        case = str(e.get("case") or "")
        if case in per_case:
            per_case[case] += 1
            if case == "B":
                pm = e.get("precondition_met")
                if pm is True or pm == "true":
                    precondition_met_count += 1
                elif pm is False or pm == "false":
                    precondition_not_met_count += 1
        else:
            unknown_case += 1

    total = sum(per_case.values()) + unknown_case
    per_case_pct = {
        k: round(v / total * 100.0, 2) if total else 0.0
        for k, v in per_case.items()
    }

    # Healthy distribution sentinels per ADR-108 §Operational
    healthy_ranges = {
        "A": (70.0, 85.0),
        "B": (1.0, 8.0),
        "C": (2.0, 10.0),
        "D": (1.0, 5.0),
        "E": (1.0, 5.0),
        "F": (0.0, 2.0),
    }
    health = {}
    for k, pct in per_case_pct.items():
        lo, hi = healthy_ranges[k]
        if total == 0:
            health[k] = "NO_DATA"
        elif lo <= pct <= hi:
            health[k] = "OK"
        elif pct < lo:
            health[k] = "LOW"
        else:
            health[k] = "HIGH"

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_pair_rail_case_events": total,
        "case_counts": per_case,
        "case_percentages": per_case_pct,
        "unknown_case_count": unknown_case,
        "case_b_precondition_met": precondition_met_count,
        "case_b_precondition_not_met": precondition_not_met_count,
        "health_per_case": health,
    }


def cmd_codex_writeguard_summary(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (R1 S-TDE Q2): Codex codando deny-list hit summary.

    Aggregates `pair_rail_codex_denylist_hit` audit events by target_path
    bucket. Surfaces top-attempted forbidden paths so operators can detect
    deny-list coverage gaps.
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 30

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    per_path: Dict[str, int] = {}
    total_hits = 0
    for e in entries:
        if e.get("action") != "pair_rail_codex_denylist_hit":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        path = str(e.get("target_path_bucket") or e.get("target_path") or "unknown")
        per_path[path] = per_path.get(path, 0) + 1
        total_hits += 1

    top_n = int(getattr(args, "top", None) or 10)
    top_paths = sorted(per_path.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_hits": total_hits,
        "unique_paths": len(per_path),
        "top_paths": [{"path_bucket": p, "hits": c} for p, c in top_paths],
    }


# ---------------------------------------------------------------------------
# PLAN-113 Phase B, Wave W1 — critical-security-action reader (audit-reader
# coverage). These 38 actions are emitted by hooks but had NO reader handler
# in this CLI, so an operator could not surface them (PLAN-112 finding class
# "Critical action has no reader handler"). cmd_critical reads the registry
# below and surfaces, per action, count + first/last timestamp + a compact
# set of SAFE summary fields ALREADY PRESENT on the event (never invented).
# Actions with ZERO occurrences are still listed (count=0) so a
# missing-but-expected critical event is visible — surfacing ABSENCE is the
# whole point.
# ---------------------------------------------------------------------------

_CRITICAL_SECURITY_ACTIONS: Tuple[str, ...] = (
    # --- federation (cross-machine peer trust / write-mode) ---
    "federation_autonomous_call_blocked",
    "federation_cert_revoked",
    "federation_event_action_blocked",
    "federation_hmac_secret_rotated",
    "federation_key_floor_rejected",
    "federation_lan_bind_denied",
    "federation_peer_revoked_remote",
    "federation_scope_denied",
    "federation_spki_fingerprint_mismatch",
    "federation_tamper_detected",
    "federation_write_attempt_blocked",
    "federation_write_endpoint_denied",
    # --- mcp (bearer-token / tenant isolation) ---
    "mcp_bearer_replay_rejected",
    "mcp_cross_tenant_denied",
    "mcp_non_loopback_rejected",
    # --- sentinel-signer (GPG quorum / rotation / revocation) ---
    "gpg_signed",
    "gpg_verified",
    "sentinel_signer_expiry_warned",
    "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed",
    "sentinel_signer_revoked",
    "sentinel_signer_rotated",
    # --- trading (kill-switch / write-override) ---
    "trading_kill_switch_disabled",
    "trading_kill_switch_invoked",
    "trading_write_override_used",
    # --- credential (age / emergency override) ---
    "credential_blocked_due_to_age",
    "credential_emergency_override_used",
    # --- audit-spool (tamper detection) ---
    "audit_spool_tamper_detected",
    # --- governance (kernel / kill-switch / overrides / pair-rail / swarm) ---
    "anti_ceo_overhead_override_used",
    "bash_canonical_bypass_invoked",
    "confidence_gate_blocked",
    "kernel_extension_landed",
    "kill_switch_invoked",
    "live_adapter_blocked",
    "pair_rail_codex_injection_detected",
    "pair_rail_outgoing_redaction_applied",
    "phase_c_enforcing_flipped",
    "swarm_layer_3_4_blocked",
)

# Map each critical action to its domain group (for the table/json output).
# Domains mirror the comment blocks in _CRITICAL_SECURITY_ACTIONS above.
_CRITICAL_ACTION_DOMAIN: Dict[str, str] = {
    # federation
    "federation_autonomous_call_blocked": "federation",
    "federation_cert_revoked": "federation",
    "federation_event_action_blocked": "federation",
    "federation_hmac_secret_rotated": "federation",
    "federation_key_floor_rejected": "federation",
    "federation_lan_bind_denied": "federation",
    "federation_peer_revoked_remote": "federation",
    "federation_scope_denied": "federation",
    "federation_spki_fingerprint_mismatch": "federation",
    "federation_tamper_detected": "federation",
    "federation_write_attempt_blocked": "federation",
    "federation_write_endpoint_denied": "federation",
    # mcp
    "mcp_bearer_replay_rejected": "mcp",
    "mcp_cross_tenant_denied": "mcp",
    "mcp_non_loopback_rejected": "mcp",
    # sentinel-signer
    "gpg_signed": "sentinel-signer",
    "gpg_verified": "sentinel-signer",
    "sentinel_signer_expiry_warned": "sentinel-signer",
    "sentinel_signer_quorum_attempted": "sentinel-signer",
    "sentinel_signer_quorum_failed": "sentinel-signer",
    "sentinel_signer_revoked": "sentinel-signer",
    "sentinel_signer_rotated": "sentinel-signer",
    # trading
    "trading_kill_switch_disabled": "trading",
    "trading_kill_switch_invoked": "trading",
    "trading_write_override_used": "trading",
    # credential
    "credential_blocked_due_to_age": "credential",
    "credential_emergency_override_used": "credential",
    # audit-spool
    "audit_spool_tamper_detected": "audit-spool",
    # governance
    "anti_ceo_overhead_override_used": "governance",
    "bash_canonical_bypass_invoked": "governance",
    "confidence_gate_blocked": "governance",
    "kernel_extension_landed": "governance",
    "kill_switch_invoked": "governance",
    "live_adapter_blocked": "governance",
    "pair_rail_codex_injection_detected": "governance",
    "pair_rail_outgoing_redaction_applied": "governance",
    "phase_c_enforcing_flipped": "governance",
    "swarm_layer_3_4_blocked": "governance",
}

# Allowlist of SAFE, schema-stable scalar summary keys to echo when present
# on a critical event. We never echo arbitrary fields (avoids surfacing
# large/unexpected payloads) and never INVENT a field — only keys in this set
# that actually exist on the event dict are surfaced, and only scalar values
# (str/int/float/bool). These keys are all part of audit_emit's per-action
# allowlists (already scrubbed at emit time) so echoing them is safe.
_CRITICAL_SAFE_SUMMARY_KEYS: Tuple[str, ...] = (
    "session_id",
    "project",
    "reason",
    "reason_code",
    "scope",
    "phase",
    "migration_phase",
    "env_value",
    "mode",
    "outcome",
    "decision",
    "peer_id",
    "endpoint",
    "tenant",
    "signer",
    "key_id",
    "fingerprint",
    "loop_id",
    "redaction_count",
    "field_count",
)


def cmd_critical(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query critical` — surface the 38 critical-security actions.

    PLAN-113 Phase B, Wave W1 (audit-reader-coverage). Each action in
    ``_CRITICAL_SECURITY_ACTIONS`` is emitted by a hook but had no reader
    handler, so an operator could not query it. This command aggregates,
    per critical action that appears in the log: ``count``, first/last ISO
    timestamp, and a compact set of SAFE summary fields drawn from the
    LATEST matching event (only keys in ``_CRITICAL_SAFE_SUMMARY_KEYS`` that
    are actually present + scalar — no invented fields).

    Actions with ZERO occurrences are STILL emitted with ``count=0`` so a
    missing-but-expected critical event is visible (surfacing absence is the
    whole point of the reader-coverage gap PLAN-112 found).

    ``--action <name>`` drills into one action; the name must be in the
    registry (else error). Output is a table (default) or JSON (``--json``).

    Output envelope (mirrors the other v-era commands):
        {"query": "critical", "version": "1",
         "data": {"action_filter": ..., "total_critical_events": N,
                  "present_action_count": M, "registry_size": 38,
                  "actions": [{action, domain, count, first_ts, last_ts,
                               last_summary: {...}}, ...]}}
    """
    action_filter = getattr(args, "action", None)
    if action_filter is not None:
        if action_filter not in _CRITICAL_SECURITY_ACTION_SET:
            print(
                f"[audit-query] ERROR: critical: unknown --action "
                f"{action_filter!r}; must be one of the "
                f"{len(_CRITICAL_SECURITY_ACTIONS)} registry actions",
                file=sys.stderr,
            )
            sys.exit(1)
        registry: Tuple[str, ...] = (action_filter,)
    else:
        registry = _CRITICAL_SECURITY_ACTIONS

    # Single pass: accumulate count / first_ts / last_ts / latest-event
    # safe-summary per critical action. We only track actions in `registry`.
    registry_set = set(registry)
    agg: Dict[str, Dict[str, Any]] = {
        a: {"count": 0, "first_ts": "", "last_ts": "", "last_summary": {}}
        for a in registry
    }
    total_critical_events = 0

    for e in entries:
        action = e.get("action")
        if action not in registry_set:
            continue
        a = agg[action]
        a["count"] += 1
        total_critical_events += 1
        ts = str(e.get("ts") or "")
        if ts:
            if not a["first_ts"] or ts < a["first_ts"]:
                a["first_ts"] = ts
            if ts >= a["last_ts"]:
                a["last_ts"] = ts
                a["last_summary"] = _critical_safe_summary(e)

    actions: List[Dict[str, Any]] = []
    present_action_count = 0
    # Stable order: by domain, then action name (registry is the universe).
    for action in sorted(
        registry,
        key=lambda x: (_CRITICAL_ACTION_DOMAIN.get(x, "zzz"), x),
    ):
        a = agg[action]
        if a["count"] > 0:
            present_action_count += 1
        actions.append(
            {
                "action": action,
                "domain": _CRITICAL_ACTION_DOMAIN.get(action, "unknown"),
                "count": a["count"],
                "first_ts": a["first_ts"],
                "last_ts": a["last_ts"],
                "last_summary": a["last_summary"],
            }
        )

    data = {
        "action_filter": action_filter,
        "registry_size": len(_CRITICAL_SECURITY_ACTIONS),
        "total_critical_events": total_critical_events,
        "present_action_count": present_action_count,
        "absent_action_count": len(registry) - present_action_count,
        "actions": actions,
    }
    return {
        "query": "critical",
        "version": "1",
        "data": data,
    }


# Set form for O(1) membership tests (validation + per-entry filter).
_CRITICAL_SECURITY_ACTION_SET = frozenset(_CRITICAL_SECURITY_ACTIONS)


def _critical_safe_summary(event: Dict[str, Any]) -> Dict[str, Any]:
    """Echo only the SAFE, scalar summary keys present on a critical event.

    Never invents a field: iterates ``_CRITICAL_SAFE_SUMMARY_KEYS`` and copies
    a key only when it exists on the event AND its value is a scalar
    (str/int/float/bool). This keeps the per-action summary compact and avoids
    surfacing large/unexpected payloads.
    """
    out: Dict[str, Any] = {}
    for key in _CRITICAL_SAFE_SUMMARY_KEYS:
        if key not in event:
            continue
        val = event[key]
        if isinstance(val, bool) or isinstance(val, (str, int, float)):
            out[key] = val
    return out


def _build_shared_parser() -> argparse.ArgumentParser:
    """Return the parent parser with the shared flags.

    Parent parser carrying the shared flags. These are added to each
    sub-command via ``parents=[]``, so users can write either::

        audit-query.py summary --json
        audit-query.py --json summary          # also works
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--log",
        default=None,
        help="Path to audit-log.jsonl (default: CEO_AUDIT_LOG_PATH or ~)",
    )
    shared.add_argument(
        "--include-rotated",
        action="store_true",
        help="Also read audit-log-YYYY-MM*.jsonl siblings",
    )
    shared.add_argument("--json", dest="as_json", action="store_true")
    shared.add_argument("--csv", dest="as_csv", action="store_true")
    shared.add_argument(
        "--errors-path",
        default=None,
        help="Override path for the `errors` sub-command",
    )
    return shared


def _add_v1_subparsers(sub: "argparse._SubParsersAction",
                       shared: argparse.ArgumentParser) -> None:
    """Register the original v1 sub-commands (summary/by-skill/... export)."""
    sub.add_parser(
        "summary",
        parents=[shared],
        help="Overview: count, range, top skills, compliance",
    )

    byskill = sub.add_parser("by-skill", parents=[shared], help="Rank skills by usage count")
    byskill.add_argument("--top", type=int, default=10)

    sub.add_parser("compliance", parents=[shared], help="Governance compliance breakdown")

    byday = sub.add_parser("by-day", parents=[shared], help="Spawns-per-day histogram")
    byday.add_argument("--days", type=int, default=14)

    search = sub.add_parser("search", parents=[shared], help="Regex-match against desc_preview")
    search.add_argument("regex")

    since = sub.add_parser("since", parents=[shared], help="Entries on or after a date")
    since.add_argument("iso_date", help="YYYY-MM-DD or full ISO 8601")

    sub.add_parser("errors", parents=[shared], help="Tail the audit-log.errors breadcrumb file")

    stats_p = sub.add_parser(
        "stats",
        parents=[shared],
        help="Prompt-length + response_kind distributions + latency; "
             "--tool-latency for per-tool lifecycle buckets",
    )
    # PLAN-125 WS-1 — per-tool-call lifecycle latency view. Bucket-counts ONLY
    # (the tool_call_lifecycle_recorded action carries NO raw duration_ms per
    # MF-SEC-3), so this is a histogram, NOT percentiles.
    stats_p.add_argument(
        "--tool-latency",
        dest="tool_latency",
        action="store_true",
        help="Per-tool_name_enum duration_bucket histogram (+ success / orphan "
             "rollups) from tool_call_lifecycle_recorded rows. Bucket-counts "
             "only — no percentiles (raw duration_ms is never recorded).",
    )

    export = sub.add_parser("export", parents=[shared], help="Dump all entries in csv/json/tsv")
    export.add_argument(
        "--format", dest="export_format", choices=["csv", "json", "tsv"], default="json"
    )


def _add_v2_subparsers(sub: "argparse._SubParsersAction",
                       shared: argparse.ArgumentParser) -> None:
    """Register Sprint 5 A.2 v2 event-stream sub-commands."""
    sub.add_parser(
        "debate",
        parents=[shared],
        help="Debate rounds: grouped by (plan_id, round) with agents + consensus",
    )
    sub.add_parser(
        "plans",
        parents=[shared],
        help="Plan status transitions per plan_id",
    )
    sub.add_parser(
        "vetoes",
        parents=[shared],
        help="Veto events aggregated by (hook, reason_code)",
    )
    sub.add_parser(
        "benchmarks",
        parents=[shared],
        help=(
            "Benchmark runs aggregated by skill — harbor-style row: "
            "pass_rate + cost + compute + turns (PLAN-133 C4)"
        ),
    )
    sub.add_parser(
        "lessons",
        parents=[shared],
        help="Lesson-write events grouped by archetype + trigger",
    )
    sub.add_parser(
        "metrics",
        parents=[shared],
        help="Cross-cutting derived metrics (veto rate, debate completion)",
    )
    sub.add_parser(
        "health",
        parents=[shared],
        help="Framework health verdict (PASS / WARN / FAIL / NO_DATA)",
    )
    sub.add_parser(
        "tokens",
        parents=[shared],
        help="Spawn token aggregates (PLAN-006 Phase 5a / ADR-016)",
    )


def _add_sprint8_9_subparsers(sub: "argparse._SubParsersAction",
                               shared: argparse.ArgumentParser) -> None:
    """Register confidence-gate + ADR-020 + lesson-effectiveness commands."""
    # Sprint 8 Phase 2 — confidence_gate aggregates (ADR-018)
    claims = sub.add_parser(
        "claims",
        parents=[shared],
        help="Confidence-gate verification aggregates (pass/fail by kind + agent)",
    )
    claims.add_argument("--kind", help="Filter by claim kind (e.g. path_exists)")
    claims.add_argument("--agent", help="Filter by agent name")
    claims.add_argument(
        "--failed-only",
        action="store_true",
        help="Only include events with ≥1 failed claim",
    )

    # Sprint 9 Phase 2 (ADR-020) — prune-restore-ratio measurement
    prr = sub.add_parser(
        "prune-restore-ratio",
        parents=[shared],
        help="Ratio of restored/archived lessons over a time window (ADR-020)",
    )
    prr.add_argument(
        "--since", default="24h",
        help="Window start: 24h / 7d / 30m / ISO 8601 / 'all' (default 24h)",
    )
    prr.add_argument(
        "--until", default=None,
        help="Window end: ISO 8601 (default: now)",
    )

    # Sprint 9 Phase 3 (PLAN-009 P3.4) — Architect outcome tracking
    aout = sub.add_parser(
        "architect-outcomes",
        parents=[shared],
        help="Per-lesson hit/miss from Architect spawns (ADR-015 amended)",
    )
    aout.add_argument(
        "--since", default="24h",
        help="Window start: 24h / 7d / 30m / ISO 8601 / 'all' (default 24h)",
    )
    aout.add_argument(
        "--consumer", default="architect",
        choices=["architect", "benchmark"],
        help="Filter by consumer (default: architect)",
    )
    aout.add_argument(
        "--include-window-only", action="store_true",
        help="Include pre-Sprint-9 window-only events (dirty signal)",
    )

    # Sprint 9 Phase 5 (PLAN-009 P5.1) — lessons effectiveness ranking
    leff = sub.add_parser(
        "lessons-effectiveness",
        parents=[shared],
        help="Per-lesson effectiveness ranking (PLAN-009 Phase 5)",
    )
    leff.add_argument("--since", default="24h",
                      help="Window start (default 24h; 'all' for no filter)")
    leff.add_argument("--include-window-only", action="store_true")
    leff.add_argument("--by", default="effectiveness",
                      choices=["effectiveness", "recency", "injections"],
                      help="Sort axis (default: effectiveness)")
    leff.add_argument("--top", type=int, default=0, help="Return top N")
    leff.add_argument("--bottom", type=int, default=0, help="Return bottom N")


def _add_plan015_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-015 adopter-triage sub-commands."""
    # PLAN-015 Phase 0.5 — adopter-side weekly triage
    wks = sub.add_parser(
        "weekly-summary",
        parents=[shared],
        help="Week-over-week spawn/veto/plan trend for adopter triage (PLAN-015)",
    )
    wks.add_argument("--window", default="7d",
                     help="Window length: 7d (default), 14d, 30d, or 'all'")
    wks.add_argument("--now", default=None,
                     help="Override 'now' with an ISO-8601 timestamp (testing)")

    # PLAN-025 Batch D F-obs-001 — ADR-052 multi-model spawn distribution.
    # Referenced from SLO-SLA.md + DAY-1-CHECKLIST; was missing pre-Batch-D.
    spawn_stats = sub.add_parser(
        "spawn-stats",
        parents=[shared],
        help="Spawn distribution by skill + model (PLAN-025 F-obs-001; ADR-052)",
    )
    spawn_stats.add_argument(
        "--since",
        default=None,
        help="Filter to entries at or after this ISO-8601 timestamp or relative (e.g. '7d')",
    )
    spawn_stats.add_argument(
        "--by",
        default="model",
        choices=("model", "skill", "both"),
        help="Group-by dimension (default: model)",
    )


def _add_plan080_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-080 Phase 1 sub-commands.

    by-domain: group spawn events by dispatch_archetype_hint for squad-bundle
    governance observability (PLAN-080 Phase 1 / ADR-112).
    """
    by_domain = sub.add_parser(
        "by-domain",
        parents=[shared],
        help=(
            "Group agent_spawn events by dispatch_archetype_hint domain "
            "(PLAN-080 Phase 1 / ADR-112)"
        ),
    )
    # Window options — mutually exclusive groups handled in cmd_by_domain
    by_domain.add_argument(
        "--window",
        default=f"{_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d",
        metavar="WINDOW",
        help=(
            "Trailing window (e.g. 30d, 7d, 14d). "
            f"Default: {_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d. "
            "Ignored when --start/--end are provided."
        ),
    )
    by_domain.add_argument(
        "--start",
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive). Must be paired with --end.",
    )
    by_domain.add_argument(
        "--end",
        default=None,
        metavar="YYYY-MM-DD",
        help="End date (inclusive). Must be paired with --start.",
    )
    by_domain.add_argument(
        "--check-reopen",
        action="store_true",
        dest="check_reopen",
        help=(
            "Filter output to sunset domains (from grandfather-cap.policy.yaml) "
            "with >= 1 spawn. UNKNOWN bucket excluded per M2-CDX-7."
        ),
    )


def _add_plan081_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-081 Phase 6-bis sub-commands.

    label: Owner labels a pair_rail_case event post-hoc (R1 S-TDE-3).
    fp-rate: false-positive rate aggregator with reopen-trigger threshold.
    codex-writeguard-summary: aggregates pair_rail_codex_denylist_hit events
                              by target_path bucket (R1 S-TDE Q2).
    """
    # --- label ---
    label_p = sub.add_parser(
        "label",
        parents=[shared],
        help="Append a Case-B verdict label to audit-log-labels.jsonl (PLAN-081 Phase 6-bis)",
    )
    label_p.add_argument(
        "--run-id", required=True, dest="run_id",
        help="pair_rail_promotion_run_id (UUID hex) of the event being labeled",
    )
    label_p.add_argument(
        "--case", required=True, choices=sorted(_LABEL_VALID_CASES),
        help="Case letter A-F to label",
    )
    label_p.add_argument(
        "--label", required=True, choices=sorted(_LABEL_VALID_LABELS),
        help="Verdict label: fp | tp | triage_pending | retracted (per ADR-108 §Owner labeling protocol)",
    )
    label_p.add_argument(
        "--note", default="",
        help="Optional free-form note (length is bucketed in audit emit; content NOT stored)",
    )

    # --- fp-rate ---
    fp_p = sub.add_parser(
        "fp-rate",
        parents=[shared],
        help="Case-B false-positive rate aggregator (PLAN-081 Phase 6-bis R1 S-TDE-3)",
    )
    fp_p.add_argument(
        "--window-days", type=int, default=30, dest="window_days",
        help="Trailing window in days (default 30)",
    )
    fp_p.add_argument(
        "--reopen-threshold", type=float, default=0.30, dest="reopen_threshold",
        help="trigger_reopen=true when fp_rate_lower_bound > threshold (default 0.30 per ADR-108 §FP-rate)",
    )

    # --- case-summary ---
    cs_p = sub.add_parser(
        "case-summary",
        parents=[shared],
        help="Cases A-F distribution rollup over window (PLAN-081 Phase 6-bis ADR-108 §Operational)",
    )
    cs_p.add_argument(
        "--window-days", type=int, default=7, dest="window_days",
        help="Trailing window in days (default 7 — faster operational signal than 30d)",
    )

    # --- codex-writeguard-summary ---
    cw_p = sub.add_parser(
        "codex-writeguard-summary",
        parents=[shared],
        help="Codex codando deny-list hit summary by path bucket (PLAN-081 Phase 6-bis R1 S-TDE Q2)",
    )
    cw_p.add_argument(
        "--window-days", type=int, default=30, dest="window_days",
        help="Trailing window in days (default 30)",
    )
    cw_p.add_argument(
        "--top", type=int, default=10,
        help="Top N most-attempted forbidden paths (default 10)",
    )


def _add_plan113_subparsers(sub: "argparse._SubParsersAction",
                            shared: argparse.ArgumentParser) -> None:
    """Register PLAN-113 Phase B Wave W1 sub-command.

    critical: surface the 38 critical-security actions (count + first/last
    ts + safe summary), listing zero-occurrence actions so missing-but-
    expected critical events are visible (audit-reader-coverage gap).
    """
    crit = sub.add_parser(
        "critical",
        parents=[shared],
        help=(
            "Surface critical-security actions (count + last-seen + safe "
            "summary); absent actions listed with count=0 (PLAN-113 W1)"
        ),
    )
    crit.add_argument(
        "--action",
        default=None,
        metavar="ACTION",
        help=(
            "Drill into a single critical action (must be one of the "
            "registry actions; errors otherwise)"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the full audit-query argparse tree.

    Delegates each era of sub-commands to a private helper
    (``_add_v1_subparsers`` / ``_add_v2_subparsers`` /
    ``_add_sprint8_9_subparsers`` / ``_add_plan015_subparsers`` /
    ``_add_plan080_subparsers`` / ``_add_plan081_subparsers``). The
    public contract of this function is unchanged — callers get back
    an ``argparse.ArgumentParser`` with ``cmd`` as the required
    subcommand.
    """
    shared = _build_shared_parser()

    parser = argparse.ArgumentParser(
        prog="audit-query.py",
        parents=[shared],
        description="Query the ceo-orchestration agent spawn audit log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  audit-query.py summary\n"
            "  audit-query.py by-skill --top 10\n"
            "  audit-query.py compliance --json\n"
            "  audit-query.py search 'security' --include-rotated\n"
            "  audit-query.py by-day --days 7\n"
            "  audit-query.py since 2026-04-01\n"
            "  audit-query.py export --format csv > spawns.csv\n"
            "  audit-query.py stats --json\n"
            "  audit-query.py errors\n"
            "  audit-query.py by-domain --window 30d\n"
            "  audit-query.py by-domain --start 2026-04-01 --end 2026-05-01\n"
            "  audit-query.py by-domain --window 30d --check-reopen\n"
            "  audit-query.py critical\n"
            "  audit-query.py critical --action kill_switch_invoked --json\n"
        ),
    )

    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_v1_subparsers(sub, shared)
    _add_v2_subparsers(sub, shared)
    _add_sprint8_9_subparsers(sub, shared)
    _add_plan015_subparsers(sub, shared)
    _add_plan080_subparsers(sub, shared)
    _add_plan081_subparsers(sub, shared)
    _add_plan113_subparsers(sub, shared)

    return parser


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — dispatch audit-query sub-commands."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # `errors` subcommand reads a different file, doesn't need the jsonl
    if args.cmd == "errors":
        result = cmd_errors(args)
        print(render(result, as_json=args.as_json, as_csv=args.as_csv))
        return 0

    log_path = Path(args.log) if args.log else default_log_path()
    log_files = discover_logs(log_path, args.include_rotated)

    # Perf-P1-002 — streamable subcommands consume the iterator directly so
    # a 100k-row log does not sit in RAM as a Python list.  Non-streamable
    # subcommands (median / percentile / cross-reference) still materialize
    # but emit a stderr hint when the log crosses the warn threshold.
    _STREAMABLE_CMDS = frozenset({
        "summary", "by-skill", "by-day", "search", "since",
    })

    if not log_files:
        entries_iter: Iterable[Dict[str, Any]] = iter(())
        entries: List[Dict[str, Any]] = []
    elif args.cmd in _STREAMABLE_CMDS:
        entries_iter = read_entries(log_files)
        entries = []  # sentinel — not used on streaming path
    else:
        entries = list(read_entries(log_files))
        entries_iter = entries
        if len(entries) >= _MATERIALIZATION_WARN_THRESHOLD:
            print(
                "[audit-query] NOTE: loaded {n} entries into RAM for "
                "subcommand {cmd!r} (threshold {thr}). Consider rotating "
                "older logs or running a streamable subcommand.".format(
                    n=len(entries),
                    cmd=args.cmd,
                    thr=_MATERIALIZATION_WARN_THRESHOLD,
                ),
                file=sys.stderr,
            )

    if args.cmd == "summary":
        result = cmd_summary(entries_iter, args)
    elif args.cmd == "by-skill":
        result = cmd_by_skill(entries_iter, args)
    elif args.cmd == "compliance":
        result = cmd_compliance(entries, args)
    elif args.cmd == "by-day":
        result = cmd_by_day(entries_iter, args)
    elif args.cmd == "search":
        result = cmd_search(entries_iter, args)
    elif args.cmd == "since":
        result = cmd_since(entries_iter, args)
    elif args.cmd == "stats":
        result = cmd_stats(entries, args)
    elif args.cmd == "export":
        result = cmd_export(entries, args)
        # Export handles its own formatting
        if args.export_format in ("csv", "tsv"):
            sys.stdout.write(result)
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    # Sprint 5 A.2 — 7 new sub-commands
    elif args.cmd == "debate":
        result = cmd_debate(entries, args)
    elif args.cmd == "plans":
        result = cmd_plans(entries, args)
    elif args.cmd == "vetoes":
        result = cmd_vetoes(entries, args)
    elif args.cmd == "benchmarks":
        result = cmd_benchmarks(entries, args)
    elif args.cmd == "lessons":
        result = cmd_lessons(entries, args)
    elif args.cmd == "metrics":
        result = cmd_metrics(entries, args)
    elif args.cmd == "health":
        result = cmd_health(entries, args)
    elif args.cmd == "tokens":
        result = cmd_tokens(entries, args)
    elif args.cmd == "claims":
        result = cmd_claims(entries, args)
    elif args.cmd == "prune-restore-ratio":
        result = cmd_prune_restore_ratio(entries, args)
    elif args.cmd == "architect-outcomes":
        result = cmd_architect_outcomes(entries, args)
    elif args.cmd == "lessons-effectiveness":
        result = cmd_lessons_effectiveness(entries, args)
    elif args.cmd == "weekly-summary":
        result = cmd_weekly_summary(entries, args)
    elif args.cmd == "spawn-stats":
        result = cmd_spawn_stats(entries, args)
    # PLAN-080 Phase 1
    elif args.cmd == "by-domain":
        result = cmd_by_domain(entries, args)
    # PLAN-081 Phase 6-bis
    elif args.cmd == "label":
        result = cmd_label(entries, args)
    elif args.cmd == "fp-rate":
        result = cmd_fp_rate(entries, args)
    elif args.cmd == "case-summary":
        result = cmd_case_summary(entries, args)
    elif args.cmd == "codex-writeguard-summary":
        result = cmd_codex_writeguard_summary(entries, args)
    # PLAN-113 Phase B Wave W1 — critical-security-action reader
    elif args.cmd == "critical":
        result = cmd_critical(entries, args)
    else:  # pragma: no cover — argparse prevents this
        parser.error(f"unknown cmd: {args.cmd}")

    print(render(result, as_json=args.as_json, as_csv=args.as_csv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
