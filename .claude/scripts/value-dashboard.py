#!/usr/bin/env python3
"""value-dashboard.py — weekly value rollup for vibecoder-stable (PLAN-083 Wave 2 sub-2.4).

Renders four sections derived from the audit log + FinOps rollup:

1. **Cost** — USD per day (ASCII bar chart OR JSON timeseries) +
   per-plan breakdown + Codex pair-rail share.

2. **Hours saved (ESTIMATE, not measured)** — defensible methodology
   per Codex P1: explicit assumption rows visible in every output;
   every line of the dashboard that quotes "hours saved" is prefixed
   ``ESTIMATE`` so the AI-skeptic CTO reader knows the framing.

3. **Bugs caught** — count of audit events from the governance taxonomy
   (``anti_ceo_overhead_block`` / ``injection_flag`` / ``policy_denied``
   / ``pair_rail_codex_violation`` / ``policy_error`` /
   ``mcp_canonical_guard_blocked``).

4. **Throughput** — plans transitioned per week + sub-agent dispatches
   + commits + GPG ceremonies (commits + ceremonies are best-effort
   from audit; not authoritative — git log is authoritative).

## Methodology framing (per PLAN-083 §13 Codex P1 risk row)

Hours-saved is reported as an estimate based on three documented
baseline assumptions (visible in every output, not just the
``--for-ctov`` disclaimer file):

* ``baseline_serial`` — solo-CEO Opus-serial cost per substantive
  operation = 30s execute + 0.5min think time (= 60s per op).
* ``parallel_ceiling`` — 6 (matches PLAN-083 §5 dispatch cap).
* ``audit_overhead_pct`` — 5% (audit emit + canonical guard + hook
  fan-out add wall-clock on top of the framework-with path).

These three numbers are deliberately conservative; tuning them is
the CTO's job (the dashboard's job is to make them visible, not
to defend them).

## Usage

::

    python3 value-dashboard.py --period 7d
    python3 value-dashboard.py --period 7d --by-day
    python3 value-dashboard.py --period 7d --by-plan
    python3 value-dashboard.py --period 30d --json
    python3 value-dashboard.py --period 7d --for-ctov

## Sec MF-3 audit emit whitelist

When the dashboard emits a ``dashboard_rendered`` audit row, it ships
ONLY these five aggregate fields (NEVER raw audit content):

``period_days`` · ``cost_usd_int_cents`` · ``bugs_count`` ·
``dispatches_count`` · ``plans_count``.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: ``--period`` time-expression parser (mirrors budget-summary.py --since).
_PERIOD_RE = re.compile(r"^(\d+)\s*([hd])$")

#: PLAN-id syntactic check (Sec MF-3 — bound any plan_id we display).
_PLAN_ID_RE = re.compile(r"^PLAN-[0-9]{3}$")

#: Audit-log filename glob.
AUDIT_LOG_GLOB: str = "audit-log*.jsonl"

#: Dedup fields stripped before computing event sha256 (rotation overlap).
_DEDUP_STRIP_FIELDS: Tuple[str, ...] = ("hmac", "hmac_error", "hook_duration_ms")

#: Bugs-caught taxonomy (PLAN-083 §5.4 row 2.4).
#:
#: We count audit-log events whose ``action`` is in this set. The first
#: six are the canonical governance signals; ``policy_error`` is included
#: because it indicates a fail-closed policy block — also a "bug caught"
#: from a security-surface perspective.
BUGS_CAUGHT_ACTIONS: Tuple[str, ...] = (
    "anti_ceo_overhead_block",     # CEO-overhead detector (Wave 1)
    "injection_flag",              # ADR-011 prompt-injection signal
    "policy_denied",               # ADR-045 final deny
    "policy_error",                # ADR-045 fail-closed parse/predicate failure
    "pair_rail_codex_violation",   # check_pair_rail.py (PLAN-075)
    "mcp_canonical_guard_blocked", # canonical-guard kernel-override deny
)

#: Throughput-bearing actions.
DISPATCH_ACTIONS: Tuple[str, ...] = (
    "agent_spawn",
    "pair_rail_case",
    "pair_rail_promotion",
)

#: Methodology assumptions (visible in EVERY output mode per Codex P1).
METHODOLOGY_ASSUMPTIONS: Dict[str, Any] = {
    "baseline_serial": "Opus serial 30s + 0.5min thought (= 60s per substantive op)",
    "parallel_ceiling": 6,
    "audit_overhead_pct": 5,
    "framing": "ESTIMATE not measured outcome",
    "source": "PLAN-083 Wave 2 sub-2.4 + Codex P1 disclaimer requirement",
}

#: Per-op seconds in serial baseline (60 = 30 execute + 30 think).
_BASELINE_SERIAL_SECONDS_PER_OP: int = 60

#: Per-op overhead seconds with framework (audit emit + canonical guard).
#: 5% of 60s = 3s; rounded up to integer for stability.
_FRAMEWORK_OVERHEAD_SECONDS_PER_OP: int = 3

#: Sec MF-3 emit whitelist for dashboard_rendered audit row.
EMIT_WHITELIST_KEYS: Tuple[str, ...] = (
    "period_days",
    "cost_usd_int_cents",
    "bugs_count",
    "dispatches_count",
    "plans_count",
)


# ---------------------------------------------------------------------------
# --period parser
# ---------------------------------------------------------------------------


def parse_period(expr: str) -> timedelta:
    """Parse ``Nh`` / ``Nd`` into a timedelta. Raises ValueError."""
    m = _PERIOD_RE.match(expr.strip().lower())
    if not m:
        raise ValueError(
            f"bad --period value: {expr!r} (expected Nh / Nd, e.g. 7d)"
        )
    n = int(m.group(1))
    unit = m.group(2)
    if n <= 0:
        raise ValueError(f"--period must be positive: {expr!r}")
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"unknown unit: {unit!r}")  # pragma: no cover


def _period_to_days(period: timedelta) -> int:
    """Render a timedelta as a positive integer number of days (min 1)."""
    days = int(round(period.total_seconds() / 86400.0))
    return max(1, days)


def _parse_ts(ts: Any) -> Optional[datetime]:
    """Parse ISO8601 audit-log timestamp; returns None on miss."""
    if not isinstance(ts, str):
        return None
    normalized = ts.replace("Z", "+0000")
    try:
        return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Audit-log discovery (mirrors budget-summary.py)
# ---------------------------------------------------------------------------


def default_audit_dir() -> Path:
    """Return the canonical audit-log directory; honors CEO_AUDIT_LOG_DIR."""
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def discover_logs(audit_dir: Optional[Path] = None) -> List[Path]:
    """Return all ``audit-log*.jsonl`` files in the audit dir, sorted."""
    if audit_dir is None:
        audit_dir = default_audit_dir()
    if not audit_dir.is_dir():
        return []
    pattern = str(audit_dir / AUDIT_LOG_GLOB)
    paths = sorted(Path(p) for p in glob.glob(pattern))
    active: List[Path] = []
    backups: List[Path] = []
    for p in paths:
        if p.name == "audit-log.jsonl":
            active.append(p)
        else:
            backups.append(p)
    return backups + active


def canonical_event_sha256(event: Dict[str, Any]) -> str:
    """Compute sha256 over canonical event form for rotation-dedup."""
    canonical = {k: v for k, v in event.items() if k not in _DEDUP_STRIP_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_unique_events(
    log_paths: Iterable[Path],
    seen: Optional[Set[str]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield deduplicated events across multiple log files."""
    if seen is None:
        seen = set()
    for path in log_paths:
        try:
            with path.open("r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    digest = canonical_event_sha256(event)
                    if digest in seen:
                        continue
                    seen.add(digest)
                    yield event
        except OSError:
            continue


def _safe_plan_id(value: Any) -> Optional[str]:
    """Return value if it matches PLAN-NNN, else None (Sec MF-3 boundary)."""
    if not isinstance(value, str):
        return None
    if _PLAN_ID_RE.match(value):
        return value
    return None


# ---------------------------------------------------------------------------
# Cost estimation (pricing table mirrors budget-summary.py)
# ---------------------------------------------------------------------------

# PLAN-120 WS-C: refreshed to current Anthropic slugs + rates (per-1k tokens,
# USD); mirrors budget-summary.py. claude-opus-4-8 = current flagship
# $5/$25 per MTok; claude-opus-4-7 RETAINED HISTORICAL ($15/$75) for log
# replay; Sonnet 4.6 = $3/$15; Haiku 4.5 = $1/$5 (was 4x underpriced).
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8":             {"in": 0.005, "out": 0.025},
    "claude-opus-4-7":            {"in": 0.015, "out": 0.075},
    "claude-opus-4":              {"in": 0.015, "out": 0.075},
    "claude-sonnet-4-6":          {"in": 0.003, "out": 0.015},
    "claude-sonnet-4-5":          {"in": 0.003, "out": 0.015},
    "claude-sonnet-4":            {"in": 0.003, "out": 0.015},
    "claude-haiku-4-5-20251001":  {"in": 0.001, "out": 0.005},
    "claude-haiku-4-5":           {"in": 0.001, "out": 0.005},
    "claude-haiku-4":             {"in": 0.001, "out": 0.005},
    "gpt-5":             {"in": 0.005,  "out": 0.020},
    "gpt-5-codex":       {"in": 0.005,  "out": 0.020},
    "gpt-5-mini":        {"in": 0.0005, "out": 0.002},
    "o3":                {"in": 0.015,  "out": 0.060},
    "o4-mini":           {"in": 0.001,  "out": 0.004},
}


def compute_cost_usd(
    model: Optional[str],
    tokens_in: int,
    tokens_out: int,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[float]:
    """Compute USD cost from model + token counts; None on unknown model."""
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str) or not model:
        return None
    row = pricing.get(model.lower())
    if not row:
        return None
    cost = (tokens_in / 1000.0) * row.get("in", 0.0)
    cost += (tokens_out / 1000.0) * row.get("out", 0.0)
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Rollup
# ---------------------------------------------------------------------------


def rollup_value(
    *,
    audit_dir: Optional[Path] = None,
    period: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Compute the value-dashboard rollup.

    Returns a JSON-serializable dict shaped as:

    ::

      {
        "period_days": int,
        "audit_dir": str,
        "log_files_read": [filename],
        "methodology_assumptions": {...METHODOLOGY_ASSUMPTIONS...},

        # COST section
        "cost": {
          "total_usd": float,
          "by_day": [{"date": "YYYY-MM-DD", "usd": float}, ...],
          "by_plan": [{"plan_id": "PLAN-NNN", "usd": float,
                       "events": int}, ...],
          "codex_share_pct": float | None,
          "cost_source": "default-pricing-table" | "unknown",
        },

        # HOURS SAVED section (ESTIMATE)
        "hours_saved_estimate": {
          "framing": "ESTIMATE not measured outcome",
          "value_hours": float,
          "baseline_serial_hours": float,
          "framework_actual_hours": float,
          "dispatches_count": int,
          "assumptions": {...METHODOLOGY_ASSUMPTIONS...},
        },

        # BUGS CAUGHT section
        "bugs_caught": {
          "total": int,
          "by_action": [{"action": str, "count": int}, ...],
        },

        # THROUGHPUT section
        "throughput": {
          "plans_transitioned": int,
          "dispatches_count": int,
          "commits_observed": int,
          "gpg_ceremonies_observed": int,
        },

        # Sec MF-3 whitelist for audit emit
        "audit_emit_payload": {period_days, cost_usd_int_cents,
                                bugs_count, dispatches_count, plans_count},
      }
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - period) if period is not None else None
    period_days = _period_to_days(period) if period is not None else 0

    log_paths = discover_logs(audit_dir)
    all_events: List[Dict[str, Any]] = list(iter_unique_events(log_paths))
    all_events.sort(key=lambda e: (e.get("ts") or "", e.get("action") or ""))

    # ------------------------------------------------------------- COST
    cost_total = 0.0
    cost_known = False
    cost_by_day: Dict[str, float] = {}
    cost_by_plan: Dict[str, Dict[str, Any]] = {}
    codex_cost = 0.0
    dispatches_count = 0
    codex_event_count = 0

    # ------------------------------------------------------------- BUGS
    bugs_by_action: Dict[str, int] = {a: 0 for a in BUGS_CAUGHT_ACTIONS}

    # ------------------------------------------------------- THROUGHPUT
    plans_seen: Set[str] = set()
    commits_observed = 0
    gpg_ceremonies_observed = 0

    for ev in all_events:
        ts = _parse_ts(ev.get("ts"))
        if cutoff is not None and ts is not None and ts < cutoff:
            continue
        # Events with unparseable ts: include them (defensive — we
        # prefer to over-count than to drop policy_denied because
        # ts is missing).
        action = ev.get("action") or ""

        # COST + DISPATCH
        if action in DISPATCH_ACTIONS:
            dispatches_count += 1
            t_in_raw = ev.get("tokens_in")
            t_out_raw = ev.get("tokens_out")
            t_in = int(t_in_raw) if isinstance(t_in_raw, (int, float)) and t_in_raw else 0
            t_out = int(t_out_raw) if isinstance(t_out_raw, (int, float)) and t_out_raw else 0
            model = ev.get("model") or ev.get("agent_model") or ""
            if isinstance(model, str) and not model and action == "pair_rail_case":
                model = "gpt-5-codex"
            cost = compute_cost_usd(
                model if isinstance(model, str) else None,
                t_in, t_out, pricing=pricing,
            )
            if cost is not None:
                cost_total += cost
                cost_known = True
                if action == "pair_rail_case":
                    codex_cost += cost
                    codex_event_count += 1

                # Per-day
                if ts is not None:
                    day_key = ts.astimezone(timezone.utc).date().isoformat()
                    cost_by_day[day_key] = round(cost_by_day.get(day_key, 0.0) + cost, 6)

                # Per-plan
                pid = _safe_plan_id(ev.get("plan_id")) or "(unknown)"
                row = cost_by_plan.setdefault(pid, {
                    "plan_id": pid,
                    "usd": 0.0,
                    "events": 0,
                })
                row["usd"] = round(row["usd"] + cost, 6)
                row["events"] += 1

        # BUGS
        if action in bugs_by_action:
            bugs_by_action[action] += 1

        # THROUGHPUT — plan transitions
        if action == "plan_status_transition":
            pid = _safe_plan_id(ev.get("plan_id"))
            if pid:
                plans_seen.add(pid)

        # THROUGHPUT — best-effort commit/ceremony detection.
        # We don't have a dedicated "commit emitted" audit action;
        # we observe sentinel ceremony actions instead.
        if action == "sentinel_signed":
            gpg_ceremonies_observed += 1
        if action in ("ceremony_commit", "owner_ceremony"):
            commits_observed += 1

    # ----------------------------------------- Hours saved (ESTIMATE)
    # Methodology:
    #   baseline_hours = dispatches_count * 60s
    #   framework_hours = (dispatches_count / parallel_ceiling) * (60s + 3s overhead)
    # Diff is the "hours saved" estimate. We clamp negative to 0 to
    # avoid the (rare) case where framework overhead exceeds parallel
    # gain at very low dispatch counts.
    baseline_seconds = dispatches_count * _BASELINE_SERIAL_SECONDS_PER_OP
    if dispatches_count == 0:
        framework_seconds = 0
    else:
        per_op_with_overhead = (
            _BASELINE_SERIAL_SECONDS_PER_OP + _FRAMEWORK_OVERHEAD_SECONDS_PER_OP
        )
        # Ceiling division — even one op consumes a full parallel slot.
        parallel_slots_needed = (
            dispatches_count + METHODOLOGY_ASSUMPTIONS["parallel_ceiling"] - 1
        ) // METHODOLOGY_ASSUMPTIONS["parallel_ceiling"]
        framework_seconds = parallel_slots_needed * per_op_with_overhead

    baseline_hours = round(baseline_seconds / 3600.0, 2)
    framework_hours = round(framework_seconds / 3600.0, 2)
    value_hours = round(max(0.0, baseline_hours - framework_hours), 2)

    # ----------------------------------------- Cost shares
    codex_share_pct: Optional[float] = None
    if cost_known and cost_total > 0:
        codex_share_pct = round(100.0 * codex_cost / cost_total, 2)

    bugs_total = sum(bugs_by_action.values())

    # ----------------------------------------- Sec MF-3 whitelist payload
    # cost_usd_int_cents: total cost in integer cents (avoid float in audit).
    cost_int_cents = int(round(cost_total * 100.0)) if cost_known else 0
    audit_emit_payload: Dict[str, Any] = {
        "period_days": period_days,
        "cost_usd_int_cents": cost_int_cents,
        "bugs_count": bugs_total,
        "dispatches_count": dispatches_count,
        "plans_count": len(plans_seen),
    }
    # Defensive: enforce whitelist (catch programmer errors that add fields).
    assert set(audit_emit_payload.keys()) == set(EMIT_WHITELIST_KEYS), (
        f"audit_emit_payload keys drifted from EMIT_WHITELIST_KEYS: "
        f"got {sorted(audit_emit_payload)}, want {sorted(EMIT_WHITELIST_KEYS)}"
    )

    result: Dict[str, Any] = {
        "period_days": period_days,
        "audit_dir": str(audit_dir or default_audit_dir()),
        "log_files_read": [p.name for p in log_paths],
        "methodology_assumptions": dict(METHODOLOGY_ASSUMPTIONS),
        "cost": {
            "total_usd": round(cost_total, 6) if cost_known else 0.0,
            "by_day": [
                {"date": d, "usd": cost_by_day[d]}
                for d in sorted(cost_by_day.keys())
            ],
            "by_plan": sorted(cost_by_plan.values(), key=lambda r: r["plan_id"]),
            "codex_share_pct": codex_share_pct,
            "cost_source": "default-pricing-table" if cost_known else "unknown",
        },
        "hours_saved_estimate": {
            "framing": "ESTIMATE not measured outcome",
            "value_hours": value_hours,
            "baseline_serial_hours": baseline_hours,
            "framework_actual_hours": framework_hours,
            "dispatches_count": dispatches_count,
            "assumptions": dict(METHODOLOGY_ASSUMPTIONS),
        },
        "bugs_caught": {
            "total": bugs_total,
            "by_action": [
                {"action": a, "count": bugs_by_action[a]}
                for a in BUGS_CAUGHT_ACTIONS
            ],
        },
        "throughput": {
            "plans_transitioned": len(plans_seen),
            "dispatches_count": dispatches_count,
            "commits_observed": commits_observed,
            "gpg_ceremonies_observed": gpg_ceremonies_observed,
        },
        "audit_emit_payload": audit_emit_payload,
        "empty": (
            dispatches_count == 0
            and bugs_total == 0
            and len(plans_seen) == 0
            and commits_observed == 0
            and gpg_ceremonies_observed == 0
        ),
    }
    return result


# ---------------------------------------------------------------------------
# Disclaimer locator
# ---------------------------------------------------------------------------


def _disclaimer_path() -> Path:
    """Resolve the methodology-disclaimer.md path next to this script."""
    return Path(__file__).resolve().parent / "methodology-disclaimer.md"


def load_disclaimer() -> str:
    """Load the disclaimer markdown if present; else return a fallback."""
    p = _disclaimer_path()
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            pass
    return (
        "# Methodology disclaimer (fallback)\n\n"
        "The disclaimer file `methodology-disclaimer.md` is missing. "
        "Treat hours-saved as an ESTIMATE, not a measured outcome. "
        "Assumptions are visible in every dashboard output under "
        "`methodology_assumptions`.\n"
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _ascii_bar(value: float, max_value: float, width: int = 40) -> str:
    """Render a single ASCII bar of `width` characters."""
    if max_value <= 0:
        return ""
    n = int(round(width * value / max_value))
    n = max(0, min(width, n))
    return "#" * n


def render_text(data: Dict[str, Any], by_day: bool, by_plan: bool) -> str:
    """Render the rollup as a human-readable text dashboard."""
    lines: List[str] = []

    # Header
    lines.append("=" * 72)
    lines.append("CEO-orchestration weekly value dashboard")
    lines.append(f"Period: last {data['period_days']} day(s)")
    lines.append(f"Audit dir: {data['audit_dir']}")
    lines.append(f"Log files: {len(data['log_files_read'])}")
    lines.append("=" * 72)

    if data.get("empty"):
        lines.append("")
        lines.append("No data yet for the selected period.")
        lines.append("This is expected on a fresh install or if no")
        lines.append("dispatches/transitions occurred in the window.")
        lines.append("")
        lines.append("Methodology assumptions (visible regardless):")
        for k, v in data["methodology_assumptions"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        return "\n".join(lines) + "\n"

    # COST
    cost = data["cost"]
    lines.append("")
    lines.append("[1/4] COST")
    lines.append("-" * 72)
    total_usd = cost["total_usd"]
    lines.append(f"Total: ${total_usd:.2f} USD ({cost['cost_source']})")
    if cost["codex_share_pct"] is not None:
        lines.append(f"Codex pair-rail share: {cost['codex_share_pct']:.1f}%")
    else:
        lines.append("Codex pair-rail share: n/a (no priced events)")

    if by_day and cost["by_day"]:
        lines.append("")
        lines.append("Per-day spend (ASCII):")
        max_day = max(row["usd"] for row in cost["by_day"]) or 0.0
        for row in cost["by_day"]:
            bar = _ascii_bar(row["usd"], max_day)
            lines.append(f"  {row['date']}  ${row['usd']:>8.2f}  {bar}")

    if by_plan and cost["by_plan"]:
        lines.append("")
        lines.append("Per-plan spend:")
        for row in cost["by_plan"]:
            lines.append(
                f"  {row['plan_id']:<14} ${row['usd']:>8.2f}  "
                f"({row['events']} events)"
            )

    # HOURS SAVED (ESTIMATE)
    hs = data["hours_saved_estimate"]
    lines.append("")
    lines.append("[2/4] HOURS SAVED  (ESTIMATE — NOT MEASURED)")
    lines.append("-" * 72)
    lines.append(f"ESTIMATE: ~{hs['value_hours']} hours saved")
    lines.append(
        f"  baseline_serial_hours:  {hs['baseline_serial_hours']} "
        f"(solo-CEO Opus serial)"
    )
    lines.append(
        f"  framework_actual_hours: {hs['framework_actual_hours']} "
        f"(with sub-agent dispatch)"
    )
    lines.append(f"  dispatches_count:       {hs['dispatches_count']}")
    lines.append("")
    lines.append("Assumptions (per Codex P1 — defensible methodology):")
    for k, v in hs["assumptions"].items():
        lines.append(f"  assumption.{k} = {v}")
    lines.append("")
    lines.append("NOTE: Hours-saved is an ESTIMATE, not a measured outcome.")
    lines.append("See methodology-disclaimer.md (--for-ctov) for full caveats.")

    # BUGS CAUGHT
    bc = data["bugs_caught"]
    lines.append("")
    lines.append("[3/4] BUGS CAUGHT")
    lines.append("-" * 72)
    lines.append(f"Total: {bc['total']} governance signals fired")
    for row in bc["by_action"]:
        lines.append(f"  {row['action']:<32} {row['count']:>5}")

    # THROUGHPUT
    th = data["throughput"]
    lines.append("")
    lines.append("[4/4] THROUGHPUT")
    lines.append("-" * 72)
    lines.append(f"Plans transitioned:      {th['plans_transitioned']}")
    lines.append(f"Sub-agent dispatches:    {th['dispatches_count']}")
    lines.append(f"Commits observed:        {th['commits_observed']} (best-effort)")
    lines.append(f"GPG ceremonies observed: {th['gpg_ceremonies_observed']} (best-effort)")
    lines.append("")
    lines.append(
        "NOTE: commits + ceremonies counts are best-effort from audit log; "
        "git log + sentinel files are authoritative."
    )

    lines.append("")
    lines.append("=" * 72)
    lines.append(
        "Sec MF-3 audit emit payload (whitelisted aggregate fields only):"
    )
    for k in EMIT_WHITELIST_KEYS:
        lines.append(f"  {k}: {data['audit_emit_payload'][k]}")
    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


def render_json(data: Dict[str, Any]) -> str:
    """Render the rollup as pretty JSON."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dashboard",
        description=(
            "Weekly value dashboard — $ spent / hours saved (ESTIMATE) / "
            "bugs caught. Per PLAN-083 §5.4 sub-2.4."
        ),
    )
    p.add_argument(
        "--period",
        default="7d",
        help="Time window (e.g. 7d, 24h). Default 7d.",
    )
    p.add_argument(
        "--by-day",
        action="store_true",
        help="Include per-day cost breakdown (text mode).",
    )
    p.add_argument(
        "--by-plan",
        action="store_true",
        help="Include per-plan cost breakdown (text mode).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of formatted text.",
    )
    p.add_argument(
        "--for-ctov",
        action="store_true",
        help=(
            "Prepend methodology-disclaimer.md before the dashboard so an "
            "AI-skeptic CTO sees caveats first. Implies text mode."
        ),
    )
    p.add_argument(
        "--audit-dir",
        default=None,
        help="Override audit-log directory (test fixture support).",
    )
    p.add_argument(
        "--no-emit",
        action="store_true",
        help=(
            "Skip emitting the ``value_dashboard_summarized`` audit event "
            "(PLAN-085 Wave D.3). Default: emit on every invocation."
        ),
    )
    return p


# ---------------------------------------------------------------------------
# PLAN-085 Wave D.3 — value_dashboard_summarized production emit
# ---------------------------------------------------------------------------


def _emit_value_dashboard_summarized(payload: Dict[str, Any]) -> None:
    """Emit ``value_dashboard_summarized`` audit event.

    PLAN-085 Wave D.3 — production callsite. ``payload`` is the
    ``audit_emit_payload`` dict computed by ``rollup_value``. Sec MF-3
    whitelist enforcement happens twice: (1) ``rollup_value`` asserts
    ``set(audit_emit_payload.keys()) == set(EMIT_WHITELIST_KEYS)``; (2)
    ``audit_emit.emit_generic`` re-scrubs against
    ``_VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST``.

    Fail-open: any exception during emit is swallowed — the CLI MUST
    NOT block on audit-log infra faults. The dashboard render output
    is the user-visible product; the audit row is observability.
    """
    try:
        # Bootstrap path so ``_lib.audit_emit`` resolves regardless of
        # caller cwd. ``.claude/hooks`` is the canonical _lib host.
        _here = Path(__file__).resolve()
        _hooks_dir = _here.parent.parent / "hooks"
        if str(_hooks_dir) not in sys.path:
            sys.path.insert(0, str(_hooks_dir))
        from _lib import audit_emit as _ae  # type: ignore
        emit_fn = getattr(_ae, "emit_generic", None)
        if emit_fn is None:
            return
        emit_fn(
            "value_dashboard_summarized",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            period_days=int(payload.get("period_days", 0)),
            cost_usd_int_cents=int(payload.get("cost_usd_int_cents", 0)),
            bugs_count=int(payload.get("bugs_count", 0)),
            dispatches_count=int(payload.get("dispatches_count", 0)),
            plans_count=int(payload.get("plans_count", 0)),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        # Fail-open per ADR-005 / audit-log infra fault contract.
        return


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        period = parse_period(args.period)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    audit_dir = Path(args.audit_dir) if args.audit_dir else None
    data = rollup_value(audit_dir=audit_dir, period=period)
    data["since"] = args.period

    # PLAN-085 Wave D.3 — production callsite for value_dashboard_summarized.
    # Emit before render so the audit row lands even if the renderer
    # raises on a malformed payload (defensive).
    if not getattr(args, "no_emit", False):
        emit_payload = data.get("audit_emit_payload")
        if isinstance(emit_payload, dict):
            _emit_value_dashboard_summarized(emit_payload)

    if args.json:
        if args.for_ctov:
            print(
                "warning: --for-ctov ignored in --json mode "
                "(disclaimer is human-text only)",
                file=sys.stderr,
            )
        sys.stdout.write(render_json(data))
        return 0

    out = render_text(data, by_day=args.by_day, by_plan=args.by_plan)
    if args.for_ctov:
        disclaimer = load_disclaimer()
        sys.stdout.write(disclaimer)
        sys.stdout.write("\n")
        sys.stdout.write("=" * 72 + "\n")
        sys.stdout.write("DASHBOARD BELOW — read disclaimer above first.\n")
        sys.stdout.write("=" * 72 + "\n\n")
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
