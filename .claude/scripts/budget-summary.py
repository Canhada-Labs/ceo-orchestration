#!/usr/bin/env python3
"""budget-summary.py — multi-rotation FinOps rollup (PLAN-083 Wave 0b sub-0.8).

This is the **PLAN-083 reissue** of ``.claude/scripts/budget-summary.py``.
It supersedes the prior ADR-033 implementation in three dimensions per
PLAN-083 §5.2 row 0.8:

1. **Multi-rotation read** — globs ``audit-log*.jsonl`` in the audit dir
   so cumulative spend reflects all 12 backup rotations + the active
   log. The prior script read only ``audit-log.jsonl`` and therefore
   reported ``$0.28`` against a memory claim of ``~$1003-1543`` for the
   S82-S99 window.

2. **Dedup by event sha256** — per PLAN-083 §13 risk register row
   "FinOps backup glob double-counts events across rotations". On a
   rotation boundary the tail of the previous log may be partially
   mirrored in the next rotation's head (atomic rename + retry
   semantics). We canonicalize each event (drop ``hmac``, ``hmac_error``,
   ``hook_duration_ms``) and compute sha256 over the sorted-keys JSON
   form; first occurrence wins.

3. **Codex MCP tokens included** — ``pair_rail_case`` action events
   contribute ``tokens_in`` / ``tokens_out`` to the rollup. Combined
   with the companion ``codex-adapter-token-wire.patch`` that
   actually populates those fields, this closes the
   "tokens not tracked for Codex" half of the observability gap.

4. **plan_id auto-attribution** — events that carry an explicit
   ``plan_id`` field win. Otherwise we infer ``plan_id`` from the
   nearest preceding ``plan_status_transition`` event in the same
   ``session_id`` whose status is ``executing`` (per ADR-058). Only
   when both signals are absent do we fall back to ``(unknown)``.

## Usage

::

    python3 budget-summary.py summary
    python3 budget-summary.py summary --since 30d
    python3 budget-summary.py summary --plan-id PLAN-081
    python3 budget-summary.py summary --by-wave
    python3 budget-summary.py summary --json
    python3 budget-summary.py summary --validate-memory-claim

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: ``--since`` time-expression parser.
_SINCE_RE = re.compile(r"^(\d+)\s*([mhd])$")

#: PLAN-id syntactic check (Sec MF-3 — bound any plan_id we display).
_PLAN_ID_RE = re.compile(r"^PLAN-[0-9]{3}$")

#: Wave-id parser (e.g. ``"wave-0a"``, ``"wave-1"``, ``"wave-minus-1"``).
_WAVE_ID_RE = re.compile(r"^wave-[a-z0-9-]{1,16}$")

#: Memory-claim band per CLAUDE.md §6 (S82-S99 cumulative).
MEMORY_CLAIM_LOW_USD: float = 1003.0
MEMORY_CLAIM_HIGH_USD: float = 1543.0
MEMORY_CLAIM_PASS_RATIO_LOW: float = 0.5
MEMORY_CLAIM_PASS_RATIO_HIGH: float = 1.5

#: Audit-log filename glob.
AUDIT_LOG_GLOB: str = "audit-log*.jsonl"

#: Fields stripped before computing event sha256 (rotation overlap dedup).
#: ``hmac`` and ``hmac_error`` differ between rotations because they're
#: chained off prior_hmac; ``hook_duration_ms`` is observation-time noise.
_DEDUP_STRIP_FIELDS: Tuple[str, ...] = ("hmac", "hmac_error", "hook_duration_ms")

#: Default per-1k-token pricing (USD). Falls back to these if the
#: pricing doc is unavailable. Numbers are conservative midpoints from
#: Anthropic + OpenAI public pricing as of 2026-05; intent here is
#: *order-of-magnitude correctness*, not pricing engine.
#: PLAN-120 WS-C: refreshed to current Anthropic slugs + rates (per-1k tokens,
#: USD). claude-opus-4-8 = current flagship $5/$25 per MTok (0.005/0.025 per-1k);
#: claude-opus-4-7 RETAINED HISTORICAL ($15/$75) for log replay of pre-4.8
#: sessions; Sonnet 4.6 = $3/$15; Haiku 4.5 = $1/$5 (was 4x underpriced).
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


# ---------------------------------------------------------------------------
# --since parser
# ---------------------------------------------------------------------------


def parse_since(expr: str) -> timedelta:
    """Parse ``Nm`` / ``Nh`` / ``Nd`` into a timedelta. Raises ValueError."""
    m = _SINCE_RE.match(expr.strip().lower())
    if not m:
        raise ValueError(
            f"bad --since value: {expr!r} (expected Nm / Nh / Nd, e.g. 30d)"
        )
    n = int(m.group(1))
    unit = m.group(2)
    if n < 0:
        raise ValueError(f"--since must be non-negative: {expr!r}")
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"unknown unit: {unit!r}")  # pragma: no cover


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
# Audit-log discovery
# ---------------------------------------------------------------------------


def default_audit_dir() -> Path:
    """Return the canonical audit-log directory.

    Honors ``CEO_AUDIT_LOG_DIR`` env override (used by tests). Otherwise
    defaults to ``~/.claude/projects/ceo-orchestration/``.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def discover_logs(audit_dir: Optional[Path] = None) -> List[Path]:
    """Return all ``audit-log*.jsonl`` files in the audit dir, sorted.

    Ordering: ``audit-log.jsonl`` (the active log) is read LAST so that
    when an event is duplicated across rotation boundary the *backup*
    version wins (it's the immutable, GPG-friendly historical record).
    Backups are sorted lexicographically (which equals chronological
    for the ``audit-log-YYYY-MM-N.jsonl`` rotation convention).
    """
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


# ---------------------------------------------------------------------------
# Event canonicalization + dedup
# ---------------------------------------------------------------------------


def canonical_event_sha256(event: Dict[str, Any]) -> str:
    """Compute sha256 over the canonical form of an event.

    Strips ``_DEDUP_STRIP_FIELDS`` (hmac/hmac_error/hook_duration_ms)
    so that the *same logical event* mirrored across a rotation
    boundary canonicalizes identically.

    Returns a 64-char hex digest.
    """
    canonical = {k: v for k, v in event.items() if k not in _DEDUP_STRIP_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_unique_events(
    log_paths: Iterable[Path],
    seen: Optional[Set[str]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield deduplicated events across multiple log files.

    Tolerates malformed JSON lines (silently skipped — matches
    ``audit_emit.iter_events`` behavior for forward compatibility).
    """
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


# ---------------------------------------------------------------------------
# plan_id inference
# ---------------------------------------------------------------------------


def _safe_plan_id(value: Any) -> Optional[str]:
    """Return value if it matches PLAN-NNN, else None (Sec MF-3 boundary)."""
    if not isinstance(value, str):
        return None
    if _PLAN_ID_RE.match(value):
        return value
    return None


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


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


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


#: Audit actions that contribute tokens to the rollup.
_TOKEN_BEARING_ACTIONS: Tuple[str, ...] = (
    "agent_spawn",        # Claude sub-agent dispatches
    "pair_rail_case",     # Codex MCP cross-LLM gate (post-wire)
    "pair_rail_promotion",  # Phase 4 promotion gate runs
)


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
                                t_in, t_out, pricing=pricing)
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


# ---------------------------------------------------------------------------
# PLAN-133 C4 — benchmark co-report (harbor-style row)
#
# Default-OFF behavioral surface, gated by the ``--benchmarks`` flag (and the
# ``CEO_BUDGET_BENCHMARKS=1`` env opt-in). When OFF, the rollup output is
# byte-for-byte unchanged. When ON, a ``benchmarks`` block is appended that
# co-reports **cost + compute + turns alongside pass-rate** per skill so a
# benchmark is never read as a bare scalar — the same harbor-style row the
# ``audit-query benchmarks`` reader emits (PLAN-133 C4). $0, read-only,
# derives only from fields already on the ``benchmark_run`` event.
# ---------------------------------------------------------------------------


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


def _bench_pass_rate(r: Dict[str, Any]) -> float:
    """Per-run pass-rate. Prefers int-encoded ``pass_rate_bps`` (÷1000);
    falls back to legacy float ``pass_rate``."""
    bps = r.get("pass_rate_bps")
    if bps is not None:
        try:
            return int(bps) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("pass_rate") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_turns(r: Dict[str, Any]) -> int:
    """Per-run scenario count (the harbor 'turns' column). Tolerant."""
    try:
        return int(r.get("pass_count") or 0) + int(r.get("fail_count") or 0)
    except (TypeError, ValueError):
        return 0


def benchmark_rollup(
    *,
    audit_dir: Optional[Path] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Co-report cost + compute + turns alongside pass-rate per benchmark
    skill (PLAN-133 C4, harbor-style row). Read-only; fail-open on infra.

    Returns a JSON-serializable dict with a per-skill list. Each row carries
    the latest pass-rate plus the cumulative + latest cost/compute/turns so
    an operator sees both the marginal and trend cost of a benchmark.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for ev in iter_unique_events(log_paths):
            if ev.get("action") != "benchmark_run":
                continue
            ts = _parse_ts(ev.get("ts"))
            if cutoff is not None and ts is not None and ts < cutoff:
                continue
            skill = str(ev.get("skill") or "?")
            by_skill.setdefault(skill, []).append(ev)
    except Exception:
        # fail-open-on-infra: a malformed log never crashes the rollup.
        by_skill = {}

    rows: List[Dict[str, Any]] = []
    tot_cost = 0.0
    tot_compute = 0.0
    tot_turns = 0
    for skill in sorted(by_skill.keys()):
        runs = sorted(by_skill[skill], key=lambda r: r.get("ts") or "")
        latest = runs[-1]
        s_cost = sum(_bench_cost_usd(r) for r in runs)
        s_compute = sum(_bench_duration_s(r) for r in runs)
        s_turns = sum(_bench_turns(r) for r in runs)
        tot_cost += s_cost
        tot_compute += s_compute
        tot_turns += s_turns
        rows.append({
            "skill": skill,
            "runs": len(runs),
            "latest_pass_rate": round(_bench_pass_rate(latest), 3),
            "latest_cost_usd": round(_bench_cost_usd(latest), 6),
            "total_cost_usd": round(s_cost, 6),
            "latest_compute_s": round(_bench_duration_s(latest), 3),
            "total_compute_s": round(s_compute, 3),
            "latest_turns": _bench_turns(latest),
            "total_turns": s_turns,
            "latest_ts": latest.get("ts"),
        })
    return {
        "per_skill": rows,
        "total_cost_usd": round(tot_cost, 6),
        "total_compute_s": round(tot_compute, 3),
        "total_turns": tot_turns,
        "skill_count": len(rows),
    }


def _extract_wave_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract a wave-id from an event if present.

    Heuristic: check ``wave_id``, ``wave``, then scan
    ``desc_preview``/``description`` for a ``wave-X`` substring.
    """
    for key in ("wave_id", "wave"):
        v = event.get(key)
        if isinstance(v, str) and _WAVE_ID_RE.match(v):
            return v
    for key in ("desc_preview", "description", "task_description"):
        v = event.get(key)
        if isinstance(v, str):
            m = re.search(r"\b(wave-[a-z0-9-]{1,16})\b", v)
            if m and _WAVE_ID_RE.match(m.group(1)):
                return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Memory-claim validator
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _fmt_tokens(n: int) -> str:
    return f"{n:>14,}"


def format_human(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    """Render the rollup as a human-readable text block."""
    lines: List[str] = []
    scope = data.get("plan_filter") or "(all plans)"
    since = data.get("since") or "(all time)"
    lines.append(f"FinOps summary — scope={scope} since={since}")
    lines.append("-" * 70)
    lines.append(f"Audit dir       : {data.get('audit_dir')}")
    files = data.get("log_files_read") or []
    lines.append(f"Logs read       : {len(files)} file(s)")
    for f in files:
        lines.append(f"                  - {f}")
    lines.append(f"Events          : {data['total_events']:>14,}")
    lines.append(f"Codex events    : {data['codex_event_count']:>14,}")
    lines.append(f"Unknown plan_id : {data['unknown_plan_count']:>14,}")
    lines.append(f"Tokens in       : {_fmt_tokens(data['total_tokens_in'])}")
    lines.append(f"Tokens out      : {_fmt_tokens(data['total_tokens_out'])}")
    lines.append(f"Tokens total    : {_fmt_tokens(data['total_tokens'])}")
    cost = data.get("total_cost_usd")
    src = data.get("cost_source") or "unknown"
    if cost is None:
        lines.append(f"Cost (USD)      : -              (source={src})")
    else:
        lines.append(f"Cost (USD)      : ${cost:>13,.4f} (source={src})")

    per_plan = data.get("per_plan") or []
    if per_plan and not data.get("plan_filter"):
        lines.append("")
        lines.append("Per plan:")
        lines.append(
            f"  {'plan_id':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_plan:
            cost_col = (
                f"${row['cost_usd']:.4f}" if row.get("cost_known") else "-"
            )
            lines.append(
                f"  {row['plan_id']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    per_wave = data.get("per_wave")
    if per_wave:
        lines.append("")
        lines.append("Per wave:")
        lines.append(
            f"  {'wave':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_wave:
            cost_col = f"${row['cost_usd']:.4f}" if row['cost_usd'] else "-"
            lines.append(
                f"  {row['wave']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    # PLAN-133 C4 — harbor-style benchmark co-report (only when --benchmarks).
    benchmarks = data.get("benchmarks")
    if benchmarks is not None:
        rows = benchmarks.get("per_skill") or []
        lines.append("")
        lines.append("Benchmarks (harbor-style — pass-rate never read alone):")
        if not rows:
            lines.append("  (no benchmark_run events in scope)")
        else:
            lines.append(
                f"  {'skill':<24}  {'runs':>4}  {'pass_rate':>9}  "
                f"{'cost_usd':>10}  {'compute_s':>10}  {'turns':>7}"
            )
            for row in rows:
                lines.append(
                    f"  {str(row['skill'])[:24]:<24}  {row['runs']:>4}  "
                    f"{row['latest_pass_rate']:>9.3f}  "
                    f"${row['total_cost_usd']:>9.4f}  "
                    f"{row['total_compute_s']:>10.1f}  "
                    f"{row['total_turns']:>7,}"
                )
            lines.append(
                f"  {'TOTAL':<24}  {'':>4}  {'':>9}  "
                f"${benchmarks['total_cost_usd']:>9.4f}  "
                f"{benchmarks['total_compute_s']:>10.1f}  "
                f"{benchmarks['total_turns']:>7,}"
            )

    if memory_claim is not None:
        lines.append("")
        lines.append("Memory-claim validation:")
        lines.append(f"  status  : {memory_claim['status']}")
        lines.append(f"  message : {memory_claim['message']}")

    return "\n".join(lines)


def format_json(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    payload = dict(data)
    if memory_claim is not None:
        payload["memory_claim_validation"] = memory_claim
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="budget-summary",
        description=(
            "FinOps rollup across all audit-log rotations "
            "(PLAN-083 Wave 0b sub-0.8)."
        ),
    )
    sub = p.add_subparsers(dest="subcommand")

    sp = sub.add_parser("summary", help="Print cumulative summary.")
    sp.add_argument("--since", metavar="EXPR", default=None,
                    help="Time window (Nm/Nh/Nd, e.g. 30d).")
    sp.add_argument("--plan-id", metavar="PLAN-NNN", default=None,
                    help="Limit rollup to a single plan_id.")
    sp.add_argument("--by-wave", action="store_true",
                    help="Include per-wave aggregates.")
    sp.add_argument("--json", action="store_true",
                    help="Emit JSON (default: human table).")
    sp.add_argument("--validate-memory-claim", action="store_true",
                    help="Cross-check rollup against CLAUDE.md memory claim band.")
    sp.add_argument("--audit-dir", metavar="PATH", default=None,
                    help="Override audit-log directory.")
    # PLAN-133 C4 — default-OFF harbor-style benchmark co-report.
    sp.add_argument("--benchmarks", action="store_true",
                    help=(
                        "Append a harbor-style benchmark co-report "
                        "(cost + compute + turns alongside pass-rate per "
                        "skill). Default-OFF; also enabled by "
                        "CEO_BUDGET_BENCHMARKS=1 (PLAN-133 C4)."
                    ))
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    if args.subcommand is None:
        # Default to "summary" when invoked bare.
        args.subcommand = "summary"
        args.since = None
        args.plan_id = None
        args.by_wave = False
        args.json = False
        args.validate_memory_claim = False
        args.audit_dir = None
        args.benchmarks = False

    if args.subcommand != "summary":
        sys.stderr.write(f"budget-summary: unknown subcommand {args.subcommand!r}\n")
        return 2

    since_delta: Optional[timedelta] = None
    if args.since:
        try:
            since_delta = parse_since(args.since)
        except ValueError as e:
            sys.stderr.write(f"budget-summary: {e}\n")
            return 2

    if args.plan_id and not _PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"budget-summary: --plan-id must look like PLAN-NNN "
            f"(got {args.plan_id!r})\n"
        )
        return 2

    audit_dir = Path(args.audit_dir) if args.audit_dir else None

    data = rollup(
        audit_dir=audit_dir,
        plan_filter=args.plan_id,
        since=since_delta,
        by_wave=args.by_wave,
    )
    data["since"] = args.since

    # PLAN-133 C4 — default-OFF benchmark co-report. Enabled by --benchmarks
    # or CEO_BUDGET_BENCHMARKS=1. When OFF, output is byte-for-byte unchanged.
    benchmarks_on = bool(getattr(args, "benchmarks", False)) or (
        os.environ.get("CEO_BUDGET_BENCHMARKS", "") == "1"
    )
    if benchmarks_on:
        data["benchmarks"] = benchmark_rollup(
            audit_dir=audit_dir,
            since=since_delta,
        )

    memory_claim: Optional[Dict[str, Any]] = None
    if args.validate_memory_claim:
        memory_claim = validate_memory_claim(data.get("total_cost_usd"))

    if args.json:
        print(format_json(data, memory_claim))
    else:
        print(format_human(data, memory_claim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
