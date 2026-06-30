#!/usr/bin/env python3
"""audit-telemetry — per-archetype dispatch & fabrication-rate analytics.

Reads ``audit-log.jsonl`` and emits aggregate telemetry over a window:

- Per-archetype dispatch counts (last 24h, last 7d, all-time)
- Dispatch-mode breakdown (mitigated vs native vs unknown)
- Fabrication rate signals (when subagent_fabrication detector events present)
- p50 / p95 latency per archetype (when ``hook_duration_ms`` field present)

PLAN-061 / ADR-082 monitoring deliverable. Stdlib-only; advisory; never
blocks a session. Used by ``ceo-diagnose`` plus ad-hoc Owner queries.

Usage:
    python3 .claude/scripts/audit-telemetry.py            # human text, last 24h
    python3 .claude/scripts/audit-telemetry.py --window 7d
    python3 .claude/scripts/audit-telemetry.py --json
    python3 .claude/scripts/audit-telemetry.py --archetype qa-architect
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# PLAN-044 audit-v2 C3-P0-06 (Wave B) — pricing constants for cost rollup.
# Mirrors `.claude/scripts/ceo-cost.py:_DEFAULT_PRICING` (Haiku at $1/$5 per
# Mtok, post-C3-P0-06 fix). Override via CEO_COST_PRICING_JSON to point at
# a JSON file with `{model_id: {input_per_mtok, output_per_mtok}}` shape.
_PRICING_PER_MTOK: Dict[str, Dict[str, float]] = {
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-opus-4-7[1m]": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def resolve_log_path() -> Optional[Path]:
    """PLAN-044 audit-v2 C4-P0-02 (Wave B) — project-scoped resolution.

    Order:
      1. ``$CEO_AUDIT_LOG_PATH`` (explicit override)
      2. ``$CEO_AUDIT_LOG_DIR/audit-log.jsonl`` — dir-level override
      3. ``$CLAUDE_PROJECT_DIR``-derived slug → ~/.claude/projects/<slug>/
      4. Legacy hardcoded ~/.claude/projects/ceo-orchestration/audit-log.jsonl

    Returns None when no candidate exists. Pre-Wave-B always returned
    the developer machine's hardcoded ceo-orchestration slug — leaking
    forensics across adopter projects.
    """
    explicit = os.environ.get("CEO_AUDIT_LOG_PATH", "")
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    audit_dir_env = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir_env:
        p = Path(audit_dir_env) / "audit-log.jsonl"
        if p.is_file():
            return p
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        try:
            abs_path = Path(project_dir).resolve()
            slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
            scoped = (
                Path.home() / ".claude" / "projects" / slug / "audit-log.jsonl"
            )
            if scoped.is_file():
                return scoped
        except OSError:
            pass
    legacy = (
        Path.home() / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    )
    if legacy.is_file():
        return legacy
    return None


def _compute_event_cost_usd(ev: Dict[str, Any]) -> float:
    """PLAN-044 audit-v2 C3-P0-02 (Wave B) — per-event cost in USD.

    Reads ``model`` + ``tokens_in`` + ``tokens_out`` from an audit-log
    entry and looks up the rate in ``_PRICING_PER_MTOK``. Returns 0.0
    on missing fields or unknown model (silent fallback — caller can
    surface the unknown_model count separately if needed). Mirrors the
    `actual_cost_usd` formula in `_lib/adapters/live/_cost.py`.
    """
    model = ev.get("model")
    if not isinstance(model, str) or not model:
        return 0.0
    rates = _PRICING_PER_MTOK.get(model)
    if rates is None:
        return 0.0
    t_in = ev.get("tokens_in") or 0
    t_out = ev.get("tokens_out") or 0
    try:
        t_in_f = float(t_in)
        t_out_f = float(t_out)
    except (TypeError, ValueError):
        return 0.0
    return (t_in_f / 1_000_000.0) * rates["input"] + (
        t_out_f / 1_000_000.0
    ) * rates["output"]


def parse_window(spec: str) -> int:
    """Convert ``24h`` / ``7d`` / ``30m`` to seconds."""
    m = re.match(r"^(\d+)([smhd])$", spec.strip().lower())
    if not m:
        raise ValueError(f"invalid window spec: {spec!r} (use e.g. 24h, 7d, 30m)")
    n, unit = int(m.group(1)), m.group(2)
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def iso_to_epoch(ts: str) -> Optional[float]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return None


def percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = int(round((pct / 100.0) * (len(s) - 1)))
    return s[max(0, min(len(s) - 1, k))]


def collect_telemetry(
    log_path: Path,
    window_seconds: int,
    archetype_filter: Optional[str] = None,
) -> Dict[str, Any]:
    cutoff = time.time() - window_seconds if window_seconds > 0 else 0
    by_archetype: Dict[str, Dict[str, Any]] = {}
    by_mode: Dict[str, int] = {}
    fabrication_events = 0
    total_spawn = 0
    total_dispatch = 0
    # PLAN-044 audit-v2 C3-P0-02 (Wave B) — cost accumulators.
    total_cost_usd = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    spawns_with_cost = 0  # subset that had model + tokens_*

    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = iso_to_epoch(ev.get("ts") or "")
                if ts is None:
                    continue
                if ts < cutoff:
                    continue

                action = ev.get("action") or ""

                if action == "agent_spawn":
                    total_spawn += 1
                    arch = ev.get("archetype") or ev.get("agent_name") or "unknown"
                    if archetype_filter and arch != archetype_filter:
                        continue
                    bucket = by_archetype.setdefault(arch, {
                        "total": 0,
                        "by_mode": {},
                        "duration_ms": [],
                        "cost_usd": 0.0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                    })
                    bucket["total"] += 1
                    mode = ev.get("dispatch_mode") or "unknown"
                    bucket["by_mode"][mode] = bucket["by_mode"].get(mode, 0) + 1
                    by_mode[mode] = by_mode.get(mode, 0) + 1
                    dur = ev.get("hook_duration_ms")
                    if isinstance(dur, (int, float)) and dur >= 0:
                        bucket["duration_ms"].append(float(dur))
                    # PLAN-044 audit-v2 C3-P0-02 (Wave B) — accumulate per-event
                    # cost. Falls back to 0.0 for spawns missing model or tokens.
                    cost = _compute_event_cost_usd(ev)
                    if cost > 0.0:
                        spawns_with_cost += 1
                        total_cost_usd += cost
                        bucket["cost_usd"] = bucket.get("cost_usd", 0.0) + cost
                        try:
                            bucket["tokens_in"] = bucket.get("tokens_in", 0) + int(
                                ev.get("tokens_in") or 0
                            )
                            bucket["tokens_out"] = bucket.get("tokens_out", 0) + int(
                                ev.get("tokens_out") or 0
                            )
                            total_tokens_in += int(ev.get("tokens_in") or 0)
                            total_tokens_out += int(ev.get("tokens_out") or 0)
                        except (TypeError, ValueError):
                            pass

                if action in ("subagent_fabrication", "rail_anomaly_detected"):
                    fabrication_events += 1

                total_dispatch += 1
    except OSError:
        return {"error": "log read failed"}

    # Compute derived metrics per archetype
    archetype_stats = {}
    for arch, bucket in by_archetype.items():
        durations = bucket["duration_ms"]
        archetype_stats[arch] = {
            "total": bucket["total"],
            "by_mode": bucket["by_mode"],
            "p50_ms": percentile(durations, 50),
            "p95_ms": percentile(durations, 95),
            "samples": len(durations),
            # PLAN-044 audit-v2 C3-P0-02 (Wave B) — per-archetype cost.
            "cost_usd": round(bucket.get("cost_usd", 0.0), 4),
            "tokens_in": bucket.get("tokens_in", 0),
            "tokens_out": bucket.get("tokens_out", 0),
        }

    fab_rate_pct = (
        100.0 * fabrication_events / total_spawn if total_spawn > 0 else 0.0
    )

    return {
        "schema": "audit-telemetry-v2",  # v2 adds cost rollup per audit-v2 C3-P0-02
        "window_seconds": window_seconds,
        "log_path": str(log_path),
        "totals": {
            "events": total_dispatch,
            "spawns": total_spawn,
            "spawns_with_cost": spawns_with_cost,  # subset with model + tokens_*
            "fabrication_events": fabrication_events,
            "fabrication_rate_pct": round(fab_rate_pct, 3),
            # PLAN-044 audit-v2 C3-P0-02 (Wave B) — global cost rollup.
            "cost_usd": round(total_cost_usd, 4),
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
        },
        "by_mode": by_mode,
        "by_archetype": archetype_stats,
    }


def render_human(report: Dict[str, Any]) -> str:
    if "error" in report:
        return f"ERROR: {report['error']}\n"
    lines: List[str] = []
    win = report["window_seconds"]
    win_h = win / 3600.0
    lines.append("")
    lines.append(f"## audit-telemetry — last {win_h:.1f}h")
    lines.append(f"   log: {report['log_path']}")
    t = report["totals"]
    lines.append(
        f"   totals: {t['events']} events, {t['spawns']} spawns, "
        f"fabrication {t['fabrication_events']} ({t['fabrication_rate_pct']}%)"
    )
    lines.append("")
    lines.append("### Dispatch modes")
    by_mode = report["by_mode"]
    if not by_mode:
        lines.append("   (no spawns in window)")
    else:
        for mode, count in sorted(by_mode.items(), key=lambda x: -x[1]):
            lines.append(f"   {mode:12} {count:5}")
    lines.append("")
    lines.append("### Per archetype")
    by_arch = report["by_archetype"]
    if not by_arch:
        lines.append("   (none)")
    else:
        for arch, stats in sorted(by_arch.items(), key=lambda x: -x[1]["total"]):
            mode_str = ", ".join(
                f"{m}={c}" for m, c in sorted(stats["by_mode"].items(), key=lambda x: -x[1])
            )
            p50 = stats["p50_ms"]
            p95 = stats["p95_ms"]
            lat = ""
            if p50 is not None and p95 is not None:
                lat = f"  p50={p50:.0f}ms p95={p95:.0f}ms (n={stats['samples']})"
            lines.append(f"   {arch:28} {stats['total']:4}  [{mode_str}]{lat}")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--window", default="24h", help="time window (e.g. 24h, 7d)")
    p.add_argument("--json", action="store_true", help="JSON output instead of human text")
    p.add_argument("--archetype", default=None, help="filter to a single archetype name")
    p.add_argument("--log-path", default=None, help="override audit-log path")
    args = p.parse_args(argv)

    try:
        window_s = parse_window(args.window)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    log_path = Path(args.log_path) if args.log_path else resolve_log_path()
    if log_path is None or not log_path.is_file():
        print("ERROR: audit-log.jsonl not found", file=sys.stderr)
        return 2

    report = collect_telemetry(log_path, window_s, args.archetype)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
