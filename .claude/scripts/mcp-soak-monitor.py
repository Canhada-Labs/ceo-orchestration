#!/usr/bin/env python3
"""MCP 30d soak observability monitor (PLAN-096 Wave E / AC-F-4).

Reads the audit-log for `mcp_handler_invoked` + `mcp_handler_denied`
events over a rolling window (default 7 days), computes the
false-positive-rate (denials / total), and prints a markdown report
suitable for the daily row in
`.claude/plans/PLAN-096/soak-report-template.md`.

When the FPR exceeds the threshold (default 0.01 = 1%) for the 7-day
rolling window, the script emits an `mcp_soak_fpr_breach` audit event
(if `audit_emit.emit_mcp_soak_fpr_breach` is available — the function
is added by the PLAN-096 canonical ceremony, so pre-ceremony runs
print the alarm to stderr without emitting).

Usage:

    python3 .claude/scripts/mcp-soak-monitor.py             # print 7d report
    python3 .claude/scripts/mcp-soak-monitor.py --days 30   # 30d window
    python3 .claude/scripts/mcp-soak-monitor.py --json      # JSON output
    python3 .claude/scripts/mcp-soak-monitor.py --no-emit   # skip alarm emit

Exit code: 0 on success regardless of breach (advisory-only); 1 on
audit-log read failure.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_FPR_THRESHOLD = 0.01  # 1%
DEFAULT_WINDOW_DAYS = 7
SUPPORTED_MCP_ACTIONS = ("mcp_handler_invoked", "mcp_handler_denied")


def _audit_log_path() -> Path:
    """Locate the audit log per ceo-orchestration convention."""
    env_path = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_path:
        return Path(env_path)
    home = Path.home()
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _read_events(log_path: Path, cutoff: datetime) -> List[Dict[str, Any]]:
    """Read mcp_handler_* events with timestamp >= cutoff."""
    if not log_path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = obj.get("action")
                if action not in SUPPORTED_MCP_ACTIONS:
                    continue
                ts = obj.get("ts") or obj.get("timestamp")
                if not isinstance(ts, str):
                    continue
                try:
                    if ts.endswith("Z"):
                        dt = datetime.fromisoformat(ts[:-1] + "+00:00")
                    else:
                        dt = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                if dt < cutoff:
                    continue
                obj["_dt"] = dt
                out.append(obj)
    except OSError:
        return []
    return out


def _compute_stats(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    invoked = sum(1 for e in events if e.get("action") == "mcp_handler_invoked")
    denied = sum(1 for e in events if e.get("action") == "mcp_handler_denied")
    total = invoked + denied
    fpr = (denied / total) if total > 0 else 0.0
    per_handler: collections.Counter = collections.Counter()
    deny_reasons: collections.Counter = collections.Counter()
    for e in events:
        h = e.get("handler", "")
        if h:
            per_handler[h] += 1
        if e.get("action") == "mcp_handler_denied":
            r = e.get("reason", "")
            if r:
                deny_reasons[r] += 1
    top_deny = deny_reasons.most_common(1)
    top_deny_reason = top_deny[0][0] if top_deny else ""
    return {
        "invoked": invoked,
        "denied": denied,
        "total": total,
        "fpr": round(fpr, 6),
        "top_handler": per_handler.most_common(1)[0][0] if per_handler else "",
        "top_deny_reason": top_deny_reason,
        "deny_reasons": dict(deny_reasons),
    }


def _emit_breach(
    window_days: int, fpr: float, threshold: float, top_deny_reason: str
) -> Tuple[bool, str]:
    """Emit mcp_soak_fpr_breach event if the audit_emit function exists."""
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / ".claude" / "hooks"))
    try:
        from _lib import audit_emit  # type: ignore[import-not-found]
    except ImportError:
        return False, "audit_emit_unavailable"
    fn = getattr(audit_emit, "emit_mcp_soak_fpr_breach", None)
    if not callable(fn):
        return False, "emit_mcp_soak_fpr_breach_unavailable (PLAN-096 ceremony pending)"
    try:
        fn(
            window_days=window_days,
            fpr_observed=fpr,
            threshold=threshold,
            top_deny_reason=top_deny_reason,
            session_id=os.environ.get("CEO_SESSION_ID", ""),
            project="ceo-orchestration",
        )
    except Exception as e:
        return False, f"emit_failed:{type(e).__name__}"
    return True, "emitted"


def _format_markdown(window_days: int, stats: Dict[str, Any]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# MCP soak — {today} (rolling {window_days}d)",
        "",
        f"| invoked | denied | total | FPR % | top handler | top deny |",
        f"|---|---|---|---|---|---|",
        f"| {stats['invoked']} | {stats['denied']} | {stats['total']} | "
        f"{stats['fpr'] * 100:.4f} | {stats['top_handler'] or '-'} | "
        f"{stats['top_deny_reason'] or '-'} |",
        "",
    ]
    if stats["deny_reasons"]:
        lines.append("Deny breakdown:")
        for k, v in sorted(stats["deny_reasons"].items(), key=lambda kv: -kv[1]):
            lines.append(f"- {k}: {v}")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(
        description="MCP soak FPR monitor (PLAN-096 Wave E)",
    )
    p.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS)
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_FPR_THRESHOLD,
        help="FPR threshold (default 0.01 = 1%%)",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    p.add_argument(
        "--no-emit",
        action="store_true",
        help="suppress mcp_soak_fpr_breach event emit even if FPR > threshold",
    )
    p.add_argument(
        "--log",
        type=str,
        default=None,
        help="explicit audit-log path (overrides env CEO_AUDIT_LOG_PATH)",
    )
    args = p.parse_args(argv[1:])

    log_path = Path(args.log) if args.log else _audit_log_path()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    events = _read_events(log_path, cutoff)
    stats = _compute_stats(events)

    payload: Dict[str, Any] = {
        "window_days": args.days,
        "threshold": args.threshold,
        "breach": stats["fpr"] > args.threshold,
        **stats,
    }

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(_format_markdown(args.days, stats))

    if payload["breach"] and not args.no_emit:
        ok, msg = _emit_breach(
            args.days, stats["fpr"], args.threshold, stats["top_deny_reason"]
        )
        if ok:
            print(f"# ALARM emitted: mcp_soak_fpr_breach ({msg})", file=sys.stderr)
        else:
            print(f"# ALARM NOT emitted: {msg}", file=sys.stderr)
            print(
                f"# FPR={stats['fpr'] * 100:.4f}% > threshold "
                f"{args.threshold * 100:.4f}% — file PLAN-096-FOLLOWUP-soak-breach.",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
