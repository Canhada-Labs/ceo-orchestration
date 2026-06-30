#!/usr/bin/env python3
"""ceo-cost — aggregate token spend from the audit log into $ figures.

Stdlib-only CLI that reads ``audit-log.jsonl`` (+ rotated siblings),
sums ``tokens_in`` / ``tokens_out`` per ``model`` (audit-log v2.7+v2.8
fields per ADR-051 + ADR-052), and prints a cost rollup.

Usage::

    ceo-cost.py                                 # last 7d, by-model
    ceo-cost.py --since 30d --by-model
    ceo-cost.py --since 30d --by-day
    ceo-cost.py --since 30d --by-skill
    ceo-cost.py --since 30d --by-session
    ceo-cost.py --since 1h --format json
    ceo-cost.py --include-rotated --since 90d

Pricing source: ADR-052 §Cost magnitude (Anthropic public pricing,
$/M tokens). Override via ``CEO_COST_PRICING_JSON=<path>`` to point
at a JSON file with shape::

    {
      "claude-opus-4-7": {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
      "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
      "claude-haiku-4-5-20251001": {"input_per_mtok": 1.00, "output_per_mtok": 5.00}
    }

Honest limitation (per ADR-016 + ADR-052):

- ``tokens_in`` / ``tokens_out`` are populated by the PostToolUse
  emitter from Anthropic ``usage_metadata`` headers. Not every spawn
  has them. Spawns with ``model`` absent OR ``tokens_*`` absent are
  counted under ``spawns_without_tokens`` and surfaced as a warning.
- ``model`` field arrived at audit-log v2.8 (PLAN-021). Pre-v2.8
  spawns have ``model: null`` and are bucketed under
  ``"unknown_model"`` for visibility.
- Cost from this script is a **lower bound**. Authoritative cost is
  the Anthropic console.

Exit codes::

    0 — success (including empty result)
    1 — log file missing OR malformed argument
    2 — unreadable log file
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# ADR-052 §Cost magnitude — Anthropic public pricing $/M tokens.
# PLAN-044 audit-v2 C3-P0-06 fix (Wave B): Haiku rate corrected from
# $0.25/$1.25 → $1.00/$5.00 per Mtok (matches docs/provider-pricing.md
# claude-haiku-4-5 row + Anthropic 2026-Q2 pricing). The pre-Wave-B
# rates were 4× under-priced — every cost rollup at v1.11.0 silently
# under-reported Haiku spend.
# PLAN-120 WS-C: added claude-opus-4-8 (current flagship, $5/$25 per Mtok,
# live-confirmed 2026-05-29). The claude-opus-4-7 rows ($15/$75) are RETAINED
# as HISTORICAL so cost rollups over audit logs of pre-4.8 sessions stay
# accurate (those sessions genuinely billed at the 4-7 rate).
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-opus-4-8[1m]": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-opus-4-7": {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
    "claude-opus-4-7[1m]": {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
    "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    "claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
}

_UNKNOWN_MODEL = "unknown_model"


# ---------------------------------------------------------------------------
# Path resolution (mirrors audit_log.py + audit-query.py conventions)
# ---------------------------------------------------------------------------


def default_log_path() -> Path:
    """Return the conventional audit log path from env vars / defaults.

    PLAN-044 audit-v2 C4-P0-02 fix (Wave B): resolve project-scoped
    audit-log path FIRST via $CLAUDE_PROJECT_DIR (so adopters with
    multiple framework instances get isolated cost reports), fall
    back to ~/.claude/projects/<slug>/ for the dogfood / single-
    project case. Pre-Wave-B the script always read the developer
    machine's hardcoded ~/.claude/projects/ceo-orchestration/ —
    leaking forensics across adopter projects.

    Resolution order:
      1. ``$CEO_AUDIT_LOG_PATH`` (explicit override) — wins all.
      2. ``$CEO_AUDIT_LOG_DIR/audit-log.jsonl`` — dir-level override.
      3. ``$CLAUDE_PROJECT_DIR``-derived slug → ~/.claude/projects/<slug>/audit-log.jsonl
      4. Legacy hardcoded ~/.claude/projects/ceo-orchestration/audit-log.jsonl
    """
    explicit = os.environ.get("CEO_AUDIT_LOG_PATH")
    if explicit:
        return Path(explicit)
    audit_dir_env = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir_env:
        return Path(audit_dir_env) / "audit-log.jsonl"
    home = Path(os.environ.get("HOME") or str(Path.home()))
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        # Mirror Claude Code's slug derivation: leading dash + path with
        # `/` replaced by `-` (e.g. `/Users/x/foo` → `-Users-x-foo`).
        try:
            abs_path = Path(project_dir).resolve()
            slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
            scoped = home / ".claude" / "projects" / slug / "audit-log.jsonl"
            if scoped.exists() or scoped.parent.is_dir():
                return scoped
        except OSError:
            pass
    # Legacy fallback (single-project dogfood / pre-PLAN-044).
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"
    return default_dir / "audit-log.jsonl"


def discover_logs(primary: Path, include_rotated: bool) -> List[Path]:
    """Return the list of log files to read, oldest first."""
    if not include_rotated:
        return [primary] if primary.is_file() else []
    if not primary.parent.is_dir():
        return []
    stem = primary.stem
    siblings = []
    for candidate in primary.parent.glob(f"{stem}*.jsonl"):
        if candidate.is_file():
            siblings.append(candidate)
    siblings.sort(key=lambda p: p.stat().st_mtime)
    return siblings


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def load_pricing() -> Dict[str, Dict[str, float]]:
    """Load pricing map. Honors ``CEO_COST_PRICING_JSON`` env override."""
    override = os.environ.get("CEO_COST_PRICING_JSON")
    if not override:
        return dict(_DEFAULT_PRICING)
    try:
        text = Path(override).read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("pricing JSON must be an object")
        out: Dict[str, Dict[str, float]] = {}
        for model_id, prices in data.items():
            if not isinstance(model_id, str) or not isinstance(prices, dict):
                continue
            try:
                ipt = float(prices.get("input_per_mtok"))
                opt = float(prices.get("output_per_mtok"))
            except (TypeError, ValueError):
                continue
            out[model_id] = {"input_per_mtok": ipt, "output_per_mtok": opt}
        if not out:
            print(
                f"warning: CEO_COST_PRICING_JSON={override} produced no usable rows; "
                "falling back to defaults",
                file=sys.stderr,
            )
            return dict(_DEFAULT_PRICING)
        return out
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"warning: failed to read CEO_COST_PRICING_JSON={override}: {exc}; "
            "falling back to defaults",
            file=sys.stderr,
        )
        return dict(_DEFAULT_PRICING)


def cost_usd(
    pricing: Dict[str, Dict[str, float]],
    model: str,
    tokens_in: int,
    tokens_out: int,
) -> float:
    """Return cost in USD; 0.0 for unknown models."""
    row = pricing.get(model)
    if not row:
        return 0.0
    return (tokens_in / 1_000_000.0) * row["input_per_mtok"] + (
        tokens_out / 1_000_000.0
    ) * row["output_per_mtok"]


# ---------------------------------------------------------------------------
# Time-window parsing
# ---------------------------------------------------------------------------


_SINCE_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$")


def parse_since(spec: Optional[str]) -> Optional[datetime]:
    """Parse ``--since`` like ``7d``, ``30d``, ``1h``, ``2w``.

    Returns a UTC ``datetime`` boundary; entries with ``ts >= boundary``
    are kept. Returns ``None`` for unset / "all" → no filter.
    """
    if not spec or spec == "all":
        return None
    if isinstance(spec, datetime):
        return spec
    m = _SINCE_RE.match(spec)
    if not m:
        try:
            # Allow ISO-8601 absolute ts as a power-user escape hatch
            return datetime.fromisoformat(spec.replace("Z", "+00:00"))
        except ValueError as exc:
            # PLAN-025 F-scripts-002: raise ValueError at the boundary, not
            # SystemExit. Library functions should not short-circuit the
            # process; the CLI wrapper at main() decides whether to exit
            # on a parse failure. Keeps this function testable in isolation.
            raise ValueError(f"invalid --since '{spec}': {exc}") from exc
    n, unit = int(m.group(1)), m.group(2)
    seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 86400 * 7}[unit]
    return datetime.now(timezone.utc) - timedelta(seconds=n * seconds)


# ---------------------------------------------------------------------------
# Reading entries
# ---------------------------------------------------------------------------


def read_entries(paths: Iterable[Path]) -> Iterator[Dict[str, Any]]:
    """Yield parsed JSON entries, skipping malformed lines silently."""
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def parse_ts(ts: Any) -> Optional[datetime]:
    """Parse audit-log ``ts`` (ISO-8601). Returns None if absent / bad."""
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(
    entries: Iterable[Dict[str, Any]],
    since: Optional[datetime],
    pricing: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """Return aggregation buckets keyed by model / day / skill / session."""
    by_model: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"spawns": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    )
    by_day: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"spawns": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    )
    by_skill: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"spawns": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    )
    by_session: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"spawns": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    )

    spawns_total = 0
    spawns_without_tokens = 0
    spawns_without_model = 0

    for entry in entries:
        if entry.get("action") != "agent_spawn":
            continue

        ts = parse_ts(entry.get("ts"))
        if since and (ts is None or ts < since):
            continue

        spawns_total += 1

        ti = entry.get("tokens_in")
        to = entry.get("tokens_out")
        if not isinstance(ti, int) or ti < 0:
            ti = None
        if not isinstance(to, int) or to < 0:
            to = None

        model = entry.get("model")
        if not isinstance(model, str) or not model:
            model = _UNKNOWN_MODEL
            spawns_without_model += 1

        if ti is None or to is None:
            spawns_without_tokens += 1
            ti = ti or 0
            to = to or 0

        c = cost_usd(pricing, model, ti, to)

        bm = by_model[model]
        bm["spawns"] += 1
        bm["tokens_in"] += ti
        bm["tokens_out"] += to
        bm["cost_usd"] += c

        skill = entry.get("skill") or "unknown_skill"
        bs = by_skill[skill]
        bs["spawns"] += 1
        bs["tokens_in"] += ti
        bs["tokens_out"] += to
        bs["cost_usd"] += c

        session = entry.get("session_id") or "unknown_session"
        bsess = by_session[session]
        bsess["spawns"] += 1
        bsess["tokens_in"] += ti
        bsess["tokens_out"] += to
        bsess["cost_usd"] += c

        if ts is not None:
            day = ts.astimezone(timezone.utc).date().isoformat()
            bd = by_day[day]
            bd["spawns"] += 1
            bd["tokens_in"] += ti
            bd["tokens_out"] += to
            bd["cost_usd"] += c

    totals = {
        "spawns": spawns_total,
        "spawns_without_tokens": spawns_without_tokens,
        "spawns_without_model": spawns_without_model,
        "tokens_in": sum(b["tokens_in"] for b in by_model.values()),
        "tokens_out": sum(b["tokens_out"] for b in by_model.values()),
        "cost_usd": sum(b["cost_usd"] for b in by_model.values()),
    }

    return {
        "totals": totals,
        "by_model": dict(by_model),
        "by_day": dict(by_day),
        "by_skill": dict(by_skill),
        "by_session": dict(by_session),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _format_cost(c: float) -> str:
    if c >= 0.01:
        return f"${c:,.2f}"
    if c > 0:
        return f"${c:.4f}"
    return "$0.00"


def _format_int(n: int) -> str:
    return f"{n:,}"


def render_text(
    agg: Dict[str, Any],
    bucket: str,
    since_label: str,
) -> str:
    """Render text-table output."""
    out: List[str] = []
    totals = agg["totals"]

    out.append(f"since={since_label}  by={bucket}")
    out.append("")

    if bucket == "by-model":
        rows = sorted(
            agg["by_model"].items(),
            key=lambda kv: kv[1]["cost_usd"],
            reverse=True,
        )
        out.append(f"{'model':<35} {'spawns':>7} {'in_tok':>13} {'out_tok':>12} {'cost':>10}")
        for k, v in rows:
            out.append(
                f"{k:<35} {_format_int(v['spawns']):>7} "
                f"{_format_int(v['tokens_in']):>13} "
                f"{_format_int(v['tokens_out']):>12} "
                f"{_format_cost(v['cost_usd']):>10}"
            )
    elif bucket == "by-day":
        rows = sorted(agg["by_day"].items(), key=lambda kv: kv[0])
        out.append(f"{'day':<12} {'spawns':>7} {'in_tok':>13} {'out_tok':>12} {'cost':>10}")
        for k, v in rows:
            out.append(
                f"{k:<12} {_format_int(v['spawns']):>7} "
                f"{_format_int(v['tokens_in']):>13} "
                f"{_format_int(v['tokens_out']):>12} "
                f"{_format_cost(v['cost_usd']):>10}"
            )
    elif bucket == "by-skill":
        rows = sorted(
            agg["by_skill"].items(),
            key=lambda kv: kv[1]["cost_usd"],
            reverse=True,
        )
        out.append(f"{'skill':<35} {'spawns':>7} {'in_tok':>13} {'out_tok':>12} {'cost':>10}")
        for k, v in rows:
            out.append(
                f"{k:<35} {_format_int(v['spawns']):>7} "
                f"{_format_int(v['tokens_in']):>13} "
                f"{_format_int(v['tokens_out']):>12} "
                f"{_format_cost(v['cost_usd']):>10}"
            )
    elif bucket == "by-session":
        rows = sorted(
            agg["by_session"].items(),
            key=lambda kv: kv[1]["cost_usd"],
            reverse=True,
        )
        out.append(f"{'session':<40} {'spawns':>7} {'in_tok':>13} {'out_tok':>12} {'cost':>10}")
        for k, v in rows:
            label = (k[:37] + "...") if len(k) > 40 else k
            out.append(
                f"{label:<40} {_format_int(v['spawns']):>7} "
                f"{_format_int(v['tokens_in']):>13} "
                f"{_format_int(v['tokens_out']):>12} "
                f"{_format_cost(v['cost_usd']):>10}"
            )

    out.append("")
    out.append(
        f"TOTAL: {_format_int(totals['spawns'])} spawns, "
        f"{_format_int(totals['tokens_in'])} in, "
        f"{_format_int(totals['tokens_out'])} out, "
        f"{_format_cost(totals['cost_usd'])}"
    )

    if totals["spawns_without_tokens"] > 0:
        out.append("")
        out.append(
            f"warning: {totals['spawns_without_tokens']} spawn(s) had no tokens_in/out — "
            "cost estimate is a lower bound. See ADR-016."
        )
    if totals["spawns_without_model"] > 0:
        out.append(
            f"warning: {totals['spawns_without_model']} spawn(s) had no model field — "
            "bucketed under 'unknown_model' (free). Pre-ADR-052 spawns lack this field."
        )

    out.append("")
    return "\n".join(out)


def render_json(agg: Dict[str, Any]) -> str:
    return json.dumps(agg, indent=2, sort_keys=True, default=str)


# ---------------------------------------------------------------------------
# Streaming mode (PLAN-040 / ADR-061)
# ---------------------------------------------------------------------------
#
# Design notes (per PLAN-040 Round-1 debate adjustments):
#
# - **Inode tracking (DevOps CONV-1):** the tailer compares fstat(fd).st_ino
#   against stat(path).st_ino on every poll. Mismatch → log rotation /
#   replacement → re-open at offset 0.
# - **`_http_post` DI seam (QA CONV-2):** OTLP emission factors through a
#   single `_http_post(url, headers, body, timeout)` function. Tests swap
#   it via a keyword argument to avoid mocking urllib internals.
# - **Auth redaction (DevOps P0-2):** logs surface only the url's
#   scheme://host[:port] — never the path, query, or bearer token.
# - **Bounded queue + fallback (DevOps P0-2):** if the OTLP endpoint
#   returns non-2xx, raises, or times out, events spill to a local
#   `cost-stream-fallback.jsonl` sibling of the audit log. Queue caps at
#   100 in-memory events before backpressure routes everything to the
#   fallback.
# - **Heartbeat (DevOps P0-3):** every `heartbeat_secs` (default 60s) a
#   `cost.stream.heartbeat` event is emitted to the sink carrying
#   last_cost_event_ts + session/daily running totals. External
#   monitoring can watch for stale heartbeats.
# - **Injectable tick_fn (QA CONV-1):** tail loop uses a caller-supplied
#   `tick_fn() -> bool` (True = continue, False = stop) instead of a
#   hard-coded `time.sleep`. Tests drive iterations synchronously.
# - **Kill-switch:** `CEO_COST_STREAMING=0` forces batch mode even if
#   `--stream` is passed, emitting a stderr warning.

_DEFAULT_ALERT_SESSION_USD = 25.0
_DEFAULT_ALERT_DAILY_USD = 100.0
_DEFAULT_HEARTBEAT_SECS = 60
_DEFAULT_QUEUE_CAP = 100
_DEFAULT_POLL_SECS = 1.0


def _http_post(
    url: str,
    headers: Dict[str, str],
    body: bytes,
    timeout: float = 5.0,
) -> Tuple[int, bytes]:
    """POST `body` (bytes) to `url` with given headers. Returns (status, body).

    Extracted as a seam for test DI (QA CONV-2). Any exception raised by
    urllib is re-raised; callers treat raises as "endpoint unavailable".
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""


def _redact_endpoint(url: str) -> str:
    """Return `scheme://host[:port]` only — strip path + query + auth."""
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        scheme = parts.scheme or "http"
        return f"{scheme}://{host}"
    except Exception:
        return "<redacted>"


def _otlp_metric_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Build an OTLP-compliant JSON metric payload from a cost event.

    Follows OTLP/HTTP v1.0 shape for a single gauge data point. The
    metric name is `ceo.cost.usd` and carries labels for model / skill /
    session. This is a minimal-compliant shape; adopter collectors may
    need to reshape per their vendor — see docs/OTLP-DASHBOARD-SAMPLES.md.
    """
    ts_ns = int(event.get("ts_unix_ms", 0) * 1_000_000)
    attrs: List[Dict[str, Any]] = []
    for key in ("model", "skill", "session_id", "plan_id", "event"):
        val = event.get(key)
        if val is not None:
            attrs.append({"key": key, "value": {"stringValue": str(val)}})
    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "ceo-orchestration"}},
                        {"key": "service.component", "value": {"stringValue": "ceo-cost"}},
                    ]
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "ceo-cost", "version": "1.0.0"},
                        "metrics": [
                            {
                                "name": "ceo.cost.usd",
                                "description": "Per-spawn cost estimate in USD",
                                "unit": "USD",
                                "gauge": {
                                    "dataPoints": [
                                        {
                                            "timeUnixNano": str(ts_ns),
                                            "asDouble": float(event.get("cost_usd", 0.0)),
                                            "attributes": attrs,
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }


class CostStreamer:
    """In-memory state machine for streaming cost events.

    Keeps per-session + per-day running totals, fires alert callbacks at
    configurable thresholds, and optionally forwards each event to an
    OTLP endpoint with a local-fallback JSONL on endpoint failure.

    Not thread-safe by design — caller drives `process_entry` + `maybe_heartbeat`
    serially from the tail loop.
    """

    def __init__(
        self,
        pricing: Dict[str, Dict[str, float]],
        alert_session_usd: float = _DEFAULT_ALERT_SESSION_USD,
        alert_daily_usd: float = _DEFAULT_ALERT_DAILY_USD,
        heartbeat_secs: int = _DEFAULT_HEARTBEAT_SECS,
        otlp_endpoint: Optional[str] = None,
        bearer_token: Optional[str] = None,
        http_post_fn: Any = None,
        fallback_path: Optional[Path] = None,
        sink: Any = None,
        queue_cap: int = _DEFAULT_QUEUE_CAP,
        time_fn: Any = None,
    ) -> None:
        self.pricing = pricing
        self.alert_session_usd = alert_session_usd
        self.alert_daily_usd = alert_daily_usd
        self.heartbeat_secs = heartbeat_secs
        self.otlp_endpoint = otlp_endpoint
        self.bearer_token = bearer_token
        self._http_post_fn = http_post_fn or _http_post
        self.fallback_path = fallback_path
        self.sink = sink if sink is not None else sys.stdout
        self.queue_cap = queue_cap
        self._time_fn = time_fn or _default_time_fn
        # Running state
        self._session_total: Dict[str, float] = defaultdict(float)
        self._day_total: Dict[str, float] = defaultdict(float)
        self._session_alerted: set = set()
        self._day_alerted: set = set()
        self._last_event_ts: Optional[float] = None
        self._last_heartbeat: float = self._time_fn()
        self._post_failures: int = 0
        # Bounded in-memory queue for retry (currently single-attempt; fallback on fail)
        self._inflight_queue: List[Dict[str, Any]] = []

    # ----------------------- public interface -----------------------

    def process_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process one audit-log entry and return the emitted cost event.

        Returns None if the entry is not cost-bearing (no model or no
        tokens). The cost event has keys:
            ts_unix_ms, ts_iso, event='spawn.cost',
            model, tokens_in, tokens_out, cost_usd,
            session_id, plan_id, skill,
            running_session_usd, running_day_usd.
        """
        model = entry.get("model")
        tokens_in = int(entry.get("tokens_in") or 0)
        tokens_out = int(entry.get("tokens_out") or 0)
        if not model or (tokens_in == 0 and tokens_out == 0):
            return None
        cost = cost_usd(self.pricing, model, tokens_in, tokens_out)
        session_id = str(entry.get("session_id") or "unknown")
        plan_id = entry.get("plan_id")
        skill = entry.get("skill_slug") or entry.get("skill")
        ts_iso = entry.get("ts") or entry.get("timestamp") or ""
        # Compute running totals
        self._session_total[session_id] += cost
        day_bucket = ts_iso[:10] if ts_iso else "unknown-day"
        self._day_total[day_bucket] += cost
        event = {
            "event": "spawn.cost",
            "ts_iso": ts_iso,
            "ts_unix_ms": int(self._time_fn() * 1000),
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 6),
            "session_id": session_id,
            "plan_id": plan_id,
            "skill": skill,
            "running_session_usd": round(self._session_total[session_id], 6),
            "running_day_usd": round(self._day_total[day_bucket], 6),
        }
        self._last_event_ts = self._time_fn()
        self._emit(event)
        # Alert firing
        alerts = self._check_alerts(session_id, day_bucket, event)
        for alert in alerts:
            self._emit(alert)
        return event

    def maybe_heartbeat(self) -> Optional[Dict[str, Any]]:
        """Emit a heartbeat if heartbeat_secs has elapsed. Returns event or None."""
        now = self._time_fn()
        if now - self._last_heartbeat < self.heartbeat_secs:
            return None
        self._last_heartbeat = now
        event = {
            "event": "cost.stream.heartbeat",
            "ts_unix_ms": int(now * 1000),
            "last_event_ts_unix_ms": int(self._last_event_ts * 1000)
            if self._last_event_ts
            else None,
            "session_totals_usd": {k: round(v, 6) for k, v in self._session_total.items()},
            "day_totals_usd": {k: round(v, 6) for k, v in self._day_total.items()},
            "post_failures_total": self._post_failures,
        }
        self._emit(event)
        return event

    # ----------------------- internals -----------------------

    def _emit(self, event: Dict[str, Any]) -> None:
        """Write to sink (stdout) + optionally POST to OTLP endpoint."""
        try:
            self.sink.write(json.dumps(event, sort_keys=True) + "\n")
            self.sink.flush()
        except Exception:
            pass
        if self.otlp_endpoint and event.get("event") == "spawn.cost":
            self._post_otlp_or_fallback(event)

    def _post_otlp_or_fallback(self, event: Dict[str, Any]) -> None:
        """Attempt OTLP POST; on failure, spill to fallback JSONL.

        Honors the bounded queue cap: if the in-memory queue is already
        full the event goes straight to fallback without a network try.
        """
        if len(self._inflight_queue) >= self.queue_cap:
            self._fallback_write(event)
            return
        self._inflight_queue.append(event)
        try:
            payload = _otlp_metric_payload(event)
            body = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.bearer_token:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            status, _body = self._http_post_fn(
                self.otlp_endpoint, headers, body, timeout=5.0
            )
            self._inflight_queue.remove(event)
            if status < 200 or status >= 300:
                self._post_failures += 1
                self._log_redacted_failure(status)
                self._fallback_write(event)
        except Exception as exc:  # network / TLS / DNS
            try:
                self._inflight_queue.remove(event)
            except ValueError:
                pass
            self._post_failures += 1
            self._log_redacted_failure(exc)
            self._fallback_write(event)

    def _log_redacted_failure(self, detail: Any) -> None:
        """Emit a failure breadcrumb with endpoint and auth redacted."""
        endpoint_safe = _redact_endpoint(self.otlp_endpoint or "")
        msg = {
            "event": "cost.stream.post_failure",
            "ts_unix_ms": int(self._time_fn() * 1000),
            "endpoint": endpoint_safe,
            "detail_class": type(detail).__name__
            if not isinstance(detail, int)
            else "http_status",
            "post_failures_total": self._post_failures,
        }
        try:
            self.sink.write(json.dumps(msg, sort_keys=True) + "\n")
            self.sink.flush()
        except Exception:
            pass

    def _fallback_write(self, event: Dict[str, Any]) -> None:
        """Write event to fallback JSONL if configured."""
        if self.fallback_path is None:
            return
        try:
            with self.fallback_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, sort_keys=True) + "\n")
        except Exception:
            pass

    def _check_alerts(
        self,
        session_id: str,
        day_bucket: str,
        event: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        if (
            session_id not in self._session_alerted
            and self._session_total[session_id] >= self.alert_session_usd
        ):
            self._session_alerted.add(session_id)
            alerts.append(
                {
                    "event": "cost.alert.session_threshold",
                    "ts_unix_ms": event["ts_unix_ms"],
                    "session_id": session_id,
                    "running_session_usd": round(self._session_total[session_id], 6),
                    "threshold_usd": self.alert_session_usd,
                }
            )
        if (
            day_bucket not in self._day_alerted
            and self._day_total[day_bucket] >= self.alert_daily_usd
        ):
            self._day_alerted.add(day_bucket)
            alerts.append(
                {
                    "event": "cost.alert.daily_threshold",
                    "ts_unix_ms": event["ts_unix_ms"],
                    "day": day_bucket,
                    "running_day_usd": round(self._day_total[day_bucket], 6),
                    "threshold_usd": self.alert_daily_usd,
                }
            )
        return alerts


def _default_time_fn() -> float:
    """time.time() — extracted for test DI."""
    import time as _time

    return _time.time()


def tail_entries(
    log_path: Path,
    tick_fn: Any,
    poll_secs: float = _DEFAULT_POLL_SECS,
    stat_fn: Any = None,
    time_sleep_fn: Any = None,
) -> Iterator[Dict[str, Any]]:
    """Tail `log_path` yielding parsed audit entries as they appear.

    Runs until `tick_fn()` returns False. Recovers from log rotation by
    comparing the open file descriptor's inode to the path's inode and
    re-opening on mismatch (CONV-1 mitigation).

    `stat_fn` / `time_sleep_fn` are test seams; default to os.stat and
    time.sleep.
    """
    import time as _time

    stat = stat_fn or os.stat
    sleep = time_sleep_fn or _time.sleep

    if not log_path.is_file():
        # Wait for the file to appear; yield nothing until it does.
        while tick_fn():
            if log_path.is_file():
                break
            sleep(poll_secs)
    if not log_path.is_file():
        return

    fd = log_path.open("r", encoding="utf-8")
    fd.seek(0, 2)  # seek to end; stream only NEW entries
    current_ino = stat(log_path).st_ino

    try:
        buffer = ""
        while tick_fn():
            chunk = fd.read()
            if chunk:
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        # Malformed line — skip; audit-log self-heals.
                        continue
                continue

            # No data — check for rotation / replacement.
            try:
                path_ino = stat(log_path).st_ino
            except OSError:
                path_ino = current_ino
            if path_ino != current_ino:
                try:
                    fd.close()
                except Exception:
                    pass
                if not log_path.is_file():
                    sleep(poll_secs)
                    continue
                fd = log_path.open("r", encoding="utf-8")
                fd.seek(0)  # read from start of rotated file
                current_ino = stat(log_path).st_ino
                continue
            sleep(poll_secs)
    finally:
        try:
            fd.close()
        except Exception:
            pass


def run_stream(
    log_path: Path,
    pricing: Dict[str, Dict[str, float]],
    *,
    alert_session_usd: float = _DEFAULT_ALERT_SESSION_USD,
    alert_daily_usd: float = _DEFAULT_ALERT_DAILY_USD,
    heartbeat_secs: int = _DEFAULT_HEARTBEAT_SECS,
    otlp_endpoint: Optional[str] = None,
    bearer_token: Optional[str] = None,
    fallback_path: Optional[Path] = None,
    sink: Any = None,
    tick_fn: Any = None,
    http_post_fn: Any = None,
    time_fn: Any = None,
    max_events: Optional[int] = None,
    poll_secs: float = _DEFAULT_POLL_SECS,
    stat_fn: Any = None,
    time_sleep_fn: Any = None,
) -> int:
    """High-level entrypoint for the streaming CLI.

    Invokes the tailer + streamer. Tests drive iterations by passing a
    `tick_fn` that returns False after N calls + a `time_sleep_fn` that
    does nothing (no real sleep). Returns the count of cost events
    emitted.
    """
    if tick_fn is None:
        tick_fn = lambda: True  # run forever by default

    streamer = CostStreamer(
        pricing=pricing,
        alert_session_usd=alert_session_usd,
        alert_daily_usd=alert_daily_usd,
        heartbeat_secs=heartbeat_secs,
        otlp_endpoint=otlp_endpoint,
        bearer_token=bearer_token,
        http_post_fn=http_post_fn,
        fallback_path=fallback_path,
        sink=sink,
        time_fn=time_fn,
    )

    emitted = 0
    for entry in tail_entries(
        log_path,
        tick_fn=tick_fn,
        poll_secs=poll_secs,
        stat_fn=stat_fn,
        time_sleep_fn=time_sleep_fn,
    ):
        event = streamer.process_entry(entry)
        if event is not None:
            emitted += 1
        streamer.maybe_heartbeat()
        if max_events is not None and emitted >= max_events:
            break
    return emitted


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the `ceo-cost` CLI."""
    p = argparse.ArgumentParser(
        prog="ceo-cost",
        description="Aggregate token spend from the audit log into $ figures.",
    )
    p.add_argument(
        "--since",
        default="7d",
        help="Time window (e.g. 1h, 24h, 7d, 30d, 12w, 'all'). Default 7d.",
    )
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--by-model", action="store_const", const="by-model", dest="bucket")
    grp.add_argument("--by-day", action="store_const", const="by-day", dest="bucket")
    grp.add_argument("--by-skill", action="store_const", const="by-skill", dest="bucket")
    grp.add_argument("--by-session", action="store_const", const="by-session", dest="bucket")
    p.set_defaults(bucket="by-model")
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    p.add_argument(
        "--log",
        default=None,
        help="Override audit log path (default from CEO_AUDIT_LOG_PATH env)",
    )
    p.add_argument(
        "--include-rotated",
        action="store_true",
        help="Aggregate across rotated audit-log*.jsonl siblings",
    )
    # --- PLAN-040 streaming flags (ADR-061) --------------------------------
    p.add_argument(
        "--stream",
        action="store_true",
        help=(
            "Stream mode: tail the audit log and emit cost events to stdout "
            "(JSON-per-line). Honors CEO_COST_STREAMING=0 kill-switch."
        ),
    )
    p.add_argument(
        "--otlp-endpoint",
        default=None,
        help=(
            "Optional OTLP/HTTP endpoint URL. When set in --stream mode, "
            "each cost event is POSTed as an OTLP JSON gauge. Bearer "
            "token via CEO_COST_OTLP_BEARER env. Fail-open to fallback "
            "JSONL."
        ),
    )
    p.add_argument(
        "--alert-session-usd",
        type=float,
        default=_DEFAULT_ALERT_SESSION_USD,
        help=f"Per-session threshold USD for alert events (default {_DEFAULT_ALERT_SESSION_USD}).",
    )
    p.add_argument(
        "--alert-daily-usd",
        type=float,
        default=_DEFAULT_ALERT_DAILY_USD,
        help=f"Daily threshold USD for alert events (default {_DEFAULT_ALERT_DAILY_USD}).",
    )
    p.add_argument(
        "--heartbeat-secs",
        type=int,
        default=_DEFAULT_HEARTBEAT_SECS,
        help=f"Heartbeat emit interval seconds (default {_DEFAULT_HEARTBEAT_SECS}).",
    )
    p.add_argument(
        "--fallback-log",
        default=None,
        help=(
            "Path for local fallback JSONL (written when OTLP endpoint "
            "returns non-2xx or fails). Default: cost-stream-fallback.jsonl "
            "next to audit-log."
        ),
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — aggregate + stream per-session cost telemetry."""
    parser = build_parser()
    args = parser.parse_args(argv)

    pricing = load_pricing()
    log_path = Path(args.log) if args.log else default_log_path()

    # --- PLAN-040: streaming path -----------------------------------------
    if args.stream:
        if os.environ.get("CEO_COST_STREAMING") == "0":
            print(
                "CEO_COST_STREAMING=0 kill-switch active; streaming disabled",
                file=sys.stderr,
            )
            return 0
        fallback_path = (
            Path(args.fallback_log)
            if args.fallback_log
            else log_path.parent / "cost-stream-fallback.jsonl"
        )
        bearer = os.environ.get("CEO_COST_OTLP_BEARER") or None
        try:
            run_stream(
                log_path,
                pricing,
                alert_session_usd=args.alert_session_usd,
                alert_daily_usd=args.alert_daily_usd,
                heartbeat_secs=args.heartbeat_secs,
                otlp_endpoint=args.otlp_endpoint,
                bearer_token=bearer,
                fallback_path=fallback_path,
            )
        except KeyboardInterrupt:
            return 0
        return 0

    # --- batch aggregation (pre-PLAN-040 path, unchanged) -----------------
    paths = discover_logs(log_path, args.include_rotated)
    if not paths:
        print(f"audit log not found: {log_path}", file=sys.stderr)
        return 1

    try:
        since = parse_since(args.since)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    entries = read_entries(paths)
    agg = aggregate(entries, since=since, pricing=pricing)

    if args.format == "json":
        print(render_json(agg))
    else:
        print(render_text(agg, args.bucket, args.since))
    return 0


if __name__ == "__main__":
    sys.exit(main())
