#!/usr/bin/env python3
"""cc-analytics-pull.py — Claude Code Analytics API client (PLAN-135 W5 unit O3).

Official org-level telemetry for the §7 honesty harness: pulls the daily per-user
Claude Code analytics report (sessions, lines of code, commits/PRs **by Claude
Code** = the free §7 numerator, tool accept/reject rates, per-model tokens +
``estimated_cost``) and tees it into a local SNAPSHOT JSON that downstream
read-only consumers use WITHOUT network:

  • ``measure_multiplier.py --source analytics-api``  (PLAN-128 §7 cross-check)
  • ``/status``        — official-numbers step (snapshot-read, fail-soft)
  • ``/agent-budget``  — estimated-cost cross-check column (snapshot-read)

API contract (verified against the platform docs, 2026-06-12):
  GET https://api.anthropic.com/v1/organizations/usage_report/claude_code
      ?starting_at=YYYY-MM-DD       (required; ONE UTC day per request)
      &limit=N                      (default 20, max 1000)
      &page=<opaque cursor>         (from previous response's ``next_page``)
  headers: x-api-key: <ADMIN key> · anthropic-version: 2023-06-01
  response: {"data": [<user-day record>...], "has_more": bool, "next_page": str|null}

BUILT-BUT-DORMANT (PLAN-135 OQ4). Key custody — THREAT-MODEL-WORKSHEET §3
(admin-keys): this endpoint needs an org **Admin API key** (``sk-ant-admin…``),
blast radius categorically larger than inference keys. The key therefore:
  • comes from the environment ONLY (``CEO_ANALYTICS_ADMIN_KEY``) — never argv,
    never a file, never settings.json, NEVER committed;
  • is provisioned by the Owner at launch (OS keychain → env), name + cadence
    documented in ``docs/rotation-log.md`` (ADR-054 admin-key tier = O9);
  • is never echoed: not in snapshots, not in logs, redacted from error text;
  • this client is READ-ONLY (analytics report only; no key-management scopes).
Fail-soft: with the key absent every pull exits 0 with a dormant message.
Per the platform docs FAQ the Analytics Admin API is free (no token billing);
it is still a live org-wide-usage READ — runs only when the Owner provisions
the key (OQ4 puts that decision on the Owner explicitly).

Stdlib only · Python >= 3.9 · no _lib imports (standalone, like ceo-info.py).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

_API_BASE = "https://api.anthropic.com"
_ALLOWED_NETLOC = urllib.parse.urlsplit(_API_BASE).netloc   # the ONLY host the admin key may reach
_ENDPOINT = "/v1/organizations/usage_report/claude_code"
_ANTHROPIC_VERSION = "2023-06-01"
_USER_AGENT = "ceo-orchestration/cc-analytics-pull (PLAN-135 W5 O3)"
_ENV_KEY = "CEO_ANALYTICS_ADMIN_KEY"          # the ONLY key source — see module docstring
_ENV_SNAPSHOT = "CEO_ANALYTICS_SNAPSHOT"
_DEFAULT_SNAPSHOT = "~/.claude/projects/ceo-orchestration/cc-analytics-snapshot.json"
_SNAPSHOT_SCHEMA = "cc-analytics-snapshot/v1"
_TIMEOUT_S = 30
_MAX_PAGES_PER_DAY = 50                       # runaway-cursor guard (50 × limit=1000 users/day is plenty)
_MAX_DAYS = 92                                # one quarter per pull — keep the snapshot bounded

_TOOL_KEYS = ("edit_tool", "multi_edit_tool", "write_tool", "notebook_edit_tool")

# DI seam — tests patch THIS symbol (mock urlopen); production = urllib.request.urlopen.
_urlopen = urllib.request.urlopen

DORMANT_MSG = (
    "cc-analytics: DORMANT — %s is not set (built-but-dormant per PLAN-135 OQ4).\n"
    "  To activate: Owner provisions an org Admin API key (sk-ant-admin…, READ scope),\n"
    "  custody per .claude/plans/PLAN-135/research/THREAT-MODEL-WORKSHEET.md §3 admin-keys\n"
    "  + docs/rotation-log.md (key name + rotation cadence; ADR-054 admin tier), exports it\n"
    "  at launch (OS keychain -> env, NEVER committed), then runs: cc-analytics-pull.py --days 7"
    % _ENV_KEY
)


def default_snapshot_path() -> str:
    return os.path.expanduser(os.environ.get(_ENV_SNAPSHOT) or _DEFAULT_SNAPSHOT)


def _redact(text: str, key: Optional[str]) -> str:
    """Strip the admin key from any outbound text (error bodies, URLs in tracebacks)."""
    if not text:
        return ""
    out = text
    if key:
        out = out.replace(key, "<redacted-admin-key>")
    return out


def _http_get(url: str, key: str) -> Dict:
    """One authenticated GET → parsed JSON dict. Key travels in the header ONLY.

    Host-allowlist guard (PLAN-135 Codex R1 P0): the org Admin key is attached
    ONLY when the URL is exactly ``https://api.anthropic.com``. Any other
    scheme/host raises BEFORE the request is built — this closes the
    egress-option-arg exfil class (a crafted ``base_url`` would otherwise leak
    the Admin key in the ``x-api-key`` header to an attacker endpoint).
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != _ALLOWED_NETLOC:
        raise ValueError(
            "refusing to attach admin key: non-canonical analytics host %r "
            "(only https://%s permitted)" % (parsed.netloc or parsed.scheme, _ALLOWED_NETLOC)
        )
    req = urllib.request.Request(url, headers={
        "x-api-key": key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "User-Agent": _USER_AGENT,
    }, method="GET")
    with _urlopen(req, timeout=_TIMEOUT_S) as resp:   # noqa: S310 — scheme+host allowlisted to api.anthropic.com immediately above
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("non-object JSON page from analytics endpoint")
    return payload


def fetch_day(day: str, key: str, limit: int = 1000, base_url: str = _API_BASE) -> Tuple[List[Dict], Dict]:
    """All records for ONE UTC day, following the opaque cursor until has_more=false.

    Returns (records, meta) where meta = {"pages": n, "truncated": bool}. Guards:
    page cap (_MAX_PAGES_PER_DAY) + repeated-cursor break, so a misbehaving cursor
    can never loop forever (meta["truncated"]=True instead).
    """
    records: List[Dict] = []
    cursor: Optional[str] = None
    seen_cursors = set()
    pages = 0
    truncated = False
    while True:
        params = {"starting_at": day, "limit": str(int(limit))}
        if cursor:
            params["page"] = cursor
        url = "%s%s?%s" % (base_url, _ENDPOINT, urllib.parse.urlencode(params))
        payload = _http_get(url, key)
        pages += 1
        data = payload.get("data")
        if isinstance(data, list):
            records.extend(r for r in data if isinstance(r, dict))
        if not payload.get("has_more"):
            break
        nxt = payload.get("next_page")
        if not nxt or nxt in seen_cursors or pages >= _MAX_PAGES_PER_DAY:
            truncated = True                      # runaway/repeated cursor — stop, keep what we have
            break
        seen_cursors.add(nxt)
        cursor = nxt
    return records, {"pages": pages, "truncated": truncated}


def day_list(starting_at: Optional[str], days: int, now: Optional[datetime] = None) -> List[str]:
    """The UTC days to pull. With --starting-at: N days FORWARD from that date
    (deterministic). Without: the N days ENDING today (UTC)."""
    days = max(1, min(int(days), _MAX_DAYS))
    if starting_at:
        d0 = datetime.strptime(starting_at, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    now = now or datetime.now(timezone.utc)
    return [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]


def _actor_label(actor) -> str:
    if isinstance(actor, dict):
        return actor.get("email_address") or actor.get("api_key_name") or actor.get("type") or "unknown"
    return "unknown"


def summarize(records: List[Dict]) -> Dict:
    """Aggregate user-day records into the three §7 surfaces:
    estimated_cost per user/day · commits/PRs-by-CC (free numerator) ·
    accept/reject per tool (accelerator cross-check). Cost amounts are CENTS USD
    in the API → converted to USD here (documented field: estimated_cost.amount)."""
    total_cost = 0.0
    commits = prs = sessions = added = removed = 0
    tool_actions: Dict[str, Dict[str, int]] = {t: {"accepted": 0, "rejected": 0} for t in _TOOL_KEYS}
    tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
    models: Dict[str, Dict] = {}
    by_user_day: List[Dict] = []
    users = set()
    days = set()
    customer_types: Dict[str, int] = {}
    for r in records:
        core = r.get("core_metrics") or {}
        loc = core.get("lines_of_code") or {}
        row_cost = 0.0
        for mb in (r.get("model_breakdown") or []):
            if not isinstance(mb, dict):
                continue
            tk = mb.get("tokens") or {}
            ec = mb.get("estimated_cost") or {}
            usd = float(ec.get("amount") or 0) / 100.0     # API documents CENTS USD
            row_cost += usd
            mname = mb.get("model") or "unknown"
            mrow = models.setdefault(mname, {"cost_usd": 0.0, "input": 0, "output": 0,
                                             "cache_read": 0, "cache_creation": 0})
            mrow["cost_usd"] = round(mrow["cost_usd"] + usd, 6)
            for f in ("input", "output", "cache_read", "cache_creation"):
                v = int(tk.get(f) or 0)
                mrow[f] += v
                tokens[f] += v
        total_cost += row_cost
        commits += int(core.get("commits_by_claude_code") or 0)
        prs += int(core.get("pull_requests_by_claude_code") or 0)
        sessions += int(core.get("num_sessions") or 0)
        added += int(loc.get("added") or 0)
        removed += int(loc.get("removed") or 0)
        for t in _TOOL_KEYS:
            ta = (r.get("tool_actions") or {}).get(t) or {}
            tool_actions[t]["accepted"] += int(ta.get("accepted") or 0)
            tool_actions[t]["rejected"] += int(ta.get("rejected") or 0)
        day = (r.get("date") or "")[:10]
        actor = _actor_label(r.get("actor"))
        ct = r.get("customer_type") or "unknown"
        users.add(actor)
        if day:
            days.add(day)
        customer_types[ct] = customer_types.get(ct, 0) + 1
        by_user_day.append({
            "date": day, "actor": actor, "customer_type": ct,
            "terminal_type": r.get("terminal_type"),
            "estimated_cost_usd": round(row_cost, 4),
            "commits_by_cc": int(core.get("commits_by_claude_code") or 0),
            "prs_by_cc": int(core.get("pull_requests_by_claude_code") or 0),
            "sessions": int(core.get("num_sessions") or 0),
        })
    acc = sum(t["accepted"] for t in tool_actions.values())
    rej = sum(t["rejected"] for t in tool_actions.values())
    return {
        "records": len(records),
        "users": len(users),
        "days": sorted(days),
        "customer_types": customer_types,
        "estimated_cost_usd": round(total_cost, 4),
        "commits_by_cc": commits,
        "prs_by_cc": prs,
        "sessions": sessions,
        "lines_added": added,
        "lines_removed": removed,
        "tool_actions": {
            "by_tool": tool_actions,
            "accepted": acc,
            "rejected": rej,
            "acceptance_rate": round(acc / (acc + rej), 4) if (acc + rej) else None,
        },
        "tokens": tokens,
        "models": models,
        "by_user_day": by_user_day,
    }


def write_snapshot(path: str, snapshot: Dict) -> None:
    """Atomic-ish snapshot write (tmp + os.replace); parent dir created."""
    p = os.path.expanduser(path)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, p)


def load_snapshot(path: str) -> Optional[Dict]:
    p = os.path.expanduser(path)
    try:
        with open(p, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError):
        return None


def _print_summary(summary: Dict, meta: Dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"meta": meta, "summary": summary}, indent=2, sort_keys=True))
        return
    days = summary.get("days") or []
    print("cc-analytics summary (%s)" % (meta.get("source", "snapshot")))
    print("  window days     : %s%s" % (", ".join(days[:7]) or "—", " …" if len(days) > 7 else ""))
    print("  user-day records: %d (%d distinct users)" % (summary.get("records", 0), summary.get("users", 0)))
    print("  estimated cost  : $%.2f (official, per model_breakdown)" % summary.get("estimated_cost_usd", 0.0))
    print("  commits by CC   : %d   PRs by CC: %d   sessions: %d"
          % (summary.get("commits_by_cc", 0), summary.get("prs_by_cc", 0), summary.get("sessions", 0)))
    print("  lines of code   : +%d / -%d" % (summary.get("lines_added", 0), summary.get("lines_removed", 0)))
    ta = summary.get("tool_actions") or {}
    rate = ta.get("acceptance_rate")
    print("  tool actions    : %d accepted / %d rejected%s"
          % (ta.get("accepted", 0), ta.get("rejected", 0),
             "  (acceptance %.1f%%)" % (rate * 100) if rate is not None else ""))
    if meta.get("truncated_days"):
        print("  ⚠ truncated days: %s (cursor guard hit — partial data)" % ", ".join(meta["truncated_days"]))


def cmd_summary(snapshot_path: str, as_json: bool) -> int:
    """Snapshot-read mode (NO network) — what /status + /agent-budget call."""
    snap = load_snapshot(snapshot_path)
    if snap is None:
        if as_json:
            print(json.dumps({"available": False, "dormant": True, "reason": "no snapshot",
                              "snapshot_path": os.path.expanduser(snapshot_path)}))
        else:
            print("cc-analytics: DORMANT — no snapshot at %s." % os.path.expanduser(snapshot_path))
            print(DORMANT_MSG)
        return 0
    summary = snap.get("summary") or summarize(snap.get("records") or [])
    meta = {"source": "snapshot", "snapshot_path": os.path.expanduser(snapshot_path),
            "generated_at": snap.get("generated_at"), "schema": snap.get("schema"),
            "truncated_days": snap.get("truncated_days") or []}
    _print_summary(summary, meta, as_json)
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    key = (os.environ.get(_ENV_KEY) or "").strip()
    if not key:
        print(DORMANT_MSG)
        return 0                                   # fail-soft by contract (plan W5 O3)
    days = day_list(args.starting_at, args.days)
    records: List[Dict] = []
    truncated_days: List[str] = []
    pages_total = 0
    try:
        for day in days:
            recs, meta = fetch_day(day, key, limit=args.limit)
            records.extend(recs)
            pages_total += meta["pages"]
            if meta["truncated"]:
                truncated_days.append(day)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        sys.stderr.write("cc-analytics: HTTP %s %s — %s\n"
                         % (e.code, _redact(str(e.reason), key), _redact(body, key)))
        if e.code in (401, 403):
            sys.stderr.write("  hint: %s must be an ORG ADMIN key (sk-ant-admin…) — custody per "
                             "THREAT-MODEL-WORKSHEET §3 + docs/rotation-log.md\n" % _ENV_KEY)
        return 3
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        sys.stderr.write("cc-analytics: network/parse error — %s\n" % _redact(str(e), key))
        return 3
    snapshot = {
        "schema": _SNAPSHOT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "claude_code_analytics_api",
        "endpoint": _ENDPOINT,
        "anthropic_version": _ANTHROPIC_VERSION,
        "days_requested": days,
        "pages_fetched": pages_total,
        "truncated_days": truncated_days,
        "records": records,
        "summary": summarize(records),
    }
    out = args.out or default_snapshot_path()
    write_snapshot(out, snapshot)
    sys.stderr.write("cc-analytics: wrote %d user-day records (%d pages, %d days) -> %s\n"
                     % (len(records), pages_total, len(days), os.path.expanduser(out)))
    _print_summary(snapshot["summary"],
                   {"source": "live pull", "truncated_days": truncated_days}, args.json)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Claude Code Analytics API client (PLAN-135 W5 O3) — pulls the official "
                    "daily per-user report into a local snapshot; --summary reads the snapshot "
                    "with NO network. Dormant (exit 0) without %s." % _ENV_KEY)
    ap.add_argument("--days", type=int, default=7, help="UTC days to pull (default 7, max %d)" % _MAX_DAYS)
    ap.add_argument("--starting-at", default=None,
                    help="first UTC day YYYY-MM-DD (with --days N: N days forward; default: window ends today)")
    ap.add_argument("--limit", type=int, default=1000, help="records per page (API max 1000)")
    ap.add_argument("--out", default=None,
                    help="snapshot path (default: $%s or %s)" % (_ENV_SNAPSHOT, _DEFAULT_SNAPSHOT))
    ap.add_argument("--snapshot", default=None, help="snapshot to READ in --summary mode")
    ap.add_argument("--summary", action="store_true",
                    help="summarize the existing snapshot (NO network — safe for /status, /agent-budget)")
    ap.add_argument("--json", action="store_true")
    # NOTE (PLAN-135 Codex R1 P0): no `--base-url` CLI arg. The endpoint host is
    # fixed to https://api.anthropic.com and enforced in _http_get's allowlist;
    # the base_url override survives ONLY as a test-only function seam (fetch_day),
    # never as operator-reachable input — closes the admin-key egress class.
    args = ap.parse_args(argv)
    if args.summary:
        return cmd_summary(args.snapshot or args.out or default_snapshot_path(), args.json)
    return cmd_pull(args)


if __name__ == "__main__":
    sys.exit(main())
