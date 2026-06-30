#!/usr/bin/env python3
"""Local read-only dashboard for audit-log.jsonl event stream v2.

PLAN-004 Phase 5. Stdlib-only HTTP server on loopback with a URL token,
serving one HTML page + a Server-Sent Events `/events` endpoint that
tails the JSONL and streams updates to the browser.

## Design contract

- **Read-only.** No write endpoints. POST/PUT/DELETE return 405.
- **Loopback only.** Default bind `127.0.0.1`; random port unless
  `--port` specified. No TLS (localhost only).
- **URL token.** Single-use ephemeral token printed to stdout. Every
  request must carry `?t=<token>` or get 401.
- **Never a gate.** Hook/plan/spawn behavior is unaffected whether this
  dashboard is running or not.
- **Zero deps.** `http.server`, `json`, `secrets`, stdlib only.

## Usage

    python3 .claude/scripts/audit-dashboard.py
    # → prints http://127.0.0.1:<port>/?t=<token>
    # → open in browser; tailing starts automatically

    # Options:
    --port N        # port (default: 0 = random)
    --bind ADDR     # bind address (default: 127.0.0.1)
    --tail N        # replay last N events on connect (default: 500)
    --token-file P  # write token to file instead of stdout

## Security notes

- Token is 32 random url-safe chars (secrets.token_urlsafe). Rotates
  on each server restart. If leaked via shell history, restart the
  dashboard; previous token is invalidated.
- Loopback bind rejects 0.0.0.0 explicitly.
- Connection count capped (--max-connections 4 default).
- No browser caching (Cache-Control: no-store) so redacted previews
  don't persist.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import socket
import sys
import threading
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs


# -----------------------------------------------------------------------------
# Constants (debate C12: auth + race + timeout required)
# -----------------------------------------------------------------------------

# Per-connection server-side socket timeout. Applies to the underlying socket
# (BaseHTTPRequestHandler sets self.connection.settimeout). SSE connections
# expect heartbeats within 15s; anything over 30s is treated as stalled.
PANEL_REQUEST_TIMEOUT_S = 30

# Default concurrent-client cap. Each panel aggregation reads the JSONL once
# and returns a static HTML snapshot (no long-lived connection). The SSE
# endpoint uses its own cap via DashboardState.max_connections; this limits
# the combined total so a burst of panel requests cannot starve SSE.
PANEL_MAX_CLIENTS = 5

# PLAN-019 F-CHAOS-7: bound the in-memory panel aggregation cache.
# The dashboard is a long-lived process; without a cap, repeated hits on
# /panel/* with varying log states would accrete aggregation snapshots
# into RAM without bound. OrderedDict with .move_to_end() + LRU trim at
# PANEL_CACHE_MAX keeps memory predictable. 100 entries × ~4 panels ×
# typical 20-50KB snapshot ≈ 2-5MB steady state.
PANEL_CACHE_MAX = 100


# -----------------------------------------------------------------------------
# Log file resolution (mirrors audit_emit.py)
# -----------------------------------------------------------------------------


def _log_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


# -----------------------------------------------------------------------------
# Bounded reverse-scan for SSE initial-replay (Perf-P1-003)
# -----------------------------------------------------------------------------

# Chunk size for reverse-scan (64 KiB). Large enough to amortise seek cost on
# typical audit events (500-1500 bytes/line) and small enough that scratch
# memory stays microscopic. Do NOT raise past ~1 MiB — we trade memory for
# latency and the whole point is to cap memory for SSE connects.
_TAIL_CHUNK_BYTES = 64 * 1024


def _tail_lines_reverse(log: Path, n: int) -> List[str]:
    """Return the last ``n`` non-empty lines of ``log`` without loading it all.

    Opens the file in binary mode, seeks from EOF, reads fixed-size chunks
    walking backwards, and accumulates until there are ``n`` terminated
    lines or the file head is reached. Memory growth is bounded by
    ``n * max_line_size`` + one scratch chunk (~64 KiB).

    Robustness:
    - Missing file / n<=0 → returns ``[]`` (caller contract).
    - OSError on open/read → returns ``[]`` (fail-open; matches prior behaviour).
    - Lines with embedded ``\r`` stripped along with surrounding whitespace.
    - Empty lines (``""`` after strip) excluded, matching pre-perf behaviour.
    - Handles files smaller than one chunk by reading once from offset 0.
    - Handles files without a trailing newline (last line still returned).

    Mirrors the external contract of the old ``read_text().splitlines()[-n:]``
    path — tests that pre-existed should still pass.
    """
    if n <= 0 or not log.exists():
        return []

    try:
        size = log.stat().st_size
    except OSError:
        return []
    if size == 0:
        return []

    try:
        f = log.open("rb")
    except OSError:
        return []

    try:
        pos = size
        buf = bytearray()
        collected: List[bytes] = []
        # We keep walking back until we have at least n lines OR we reach
        # the head. We require one extra newline than n so we know we've
        # seen the full text of the first included line (no partial prefix).
        while pos > 0 and len(collected) <= n:
            read_size = _TAIL_CHUNK_BYTES if pos >= _TAIL_CHUNK_BYTES else pos
            pos -= read_size
            try:
                f.seek(pos)
                chunk = f.read(read_size)
            except OSError:
                return []
            # Prepend chunk; note we do NOT preserve any stray partial
            # state across chunks because we only split on newlines at
            # the very end.
            buf[0:0] = chunk
            # Count newlines cheaply to decide whether to stop early.
            # bytearray.count returns int; stop when we have n+1 newlines
            # (so the earliest line is complete) OR have reached head.
            if buf.count(b"\n") > n:
                break
    finally:
        try:
            f.close()
        except OSError:
            pass

    # Split the accumulated buffer on newlines, drop empty lines after
    # strip, and return the last n.
    text = buf.decode("utf-8", errors="replace")
    # splitlines() handles \n, \r\n, \r uniformly and DOES NOT emit a
    # trailing empty element when the file ends in \n — matching the
    # previous read_text().splitlines() contract exactly.
    lines = text.splitlines()
    out: List[str] = []
    for line in lines[-n:]:
        if line.strip():
            out.append(line)
    return out


# -----------------------------------------------------------------------------
# HTML template (vanilla; no frameworks)
# -----------------------------------------------------------------------------

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ceo-orchestration — audit dashboard</title>
<style>
  :root { --bg:#0b0d10; --fg:#e8ecef; --mute:#6b7480; --accent:#4ea3ff; --warn:#ffa94d; --err:#ff6b6b; --ok:#3bd671; }
  *{box-sizing:border-box} body{margin:0;padding:16px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);color:var(--fg);font-size:13px;line-height:1.4}
  header{display:flex;justify-content:space-between;align-items:center;padding-bottom:12px;border-bottom:1px solid #1e2429;margin-bottom:16px}
  h1{font-size:14px;margin:0;font-weight:600}
  h1 small{color:var(--mute);font-weight:400;margin-left:8px}
  #status{font-size:11px;color:var(--mute)}
  #status.live::before{content:"● ";color:var(--ok)}
  #status.err::before{content:"● ";color:var(--err)}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px}
  .card{background:#11161b;border:1px solid #1e2429;border-radius:4px;padding:12px}
  .card h3{font-size:11px;margin:0 0 6px 0;color:var(--mute);font-weight:500;text-transform:uppercase;letter-spacing:.5px}
  .card .n{font-size:22px;font-weight:600}
  main{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .col h2{font-size:12px;margin:0 0 8px 0;color:var(--mute);font-weight:500;text-transform:uppercase;letter-spacing:.5px}
  .row{padding:6px 8px;border-left:2px solid transparent;border-radius:2px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .row:hover{background:#161b21}
  .row .t{color:var(--mute);margin-right:8px;font-size:11px}
  .row .a{color:var(--accent)}
  .row.veto{border-left-color:var(--err)} .row.veto .a{color:var(--err)}
  .row.debate{border-left-color:var(--accent)}
  .row.plan{border-left-color:var(--ok)} .row.plan .a{color:var(--ok)}
  .row.bench{border-left-color:var(--warn)} .row.bench .a{color:var(--warn)}
  footer{margin-top:20px;padding-top:12px;border-top:1px solid #1e2429;color:var(--mute);font-size:11px}
</style>
</head>
<body>
<header>
  <h1>ceo-orchestration <small>audit dashboard · v2 event stream</small></h1>
  <span id="status">connecting…</span>
</header>

<div class="grid" id="kpis">
  <div class="card"><h3>spawns</h3><div class="n" id="k-spawn">0</div></div>
  <div class="card"><h3>vetoes</h3><div class="n" id="k-veto">0</div></div>
  <div class="card"><h3>debate events</h3><div class="n" id="k-debate">0</div></div>
  <div class="card"><h3>plan transitions</h3><div class="n" id="k-plan">0</div></div>
  <div class="card"><h3>benchmarks</h3><div class="n" id="k-bench">0</div></div>
  <div class="card"><h3>lessons</h3><div class="n" id="k-lesson">0</div></div>
</div>

<main>
  <section class="col">
    <h2>Live event stream</h2>
    <div id="stream"></div>
  </section>
  <section class="col">
    <h2>Vetoes by reason</h2>
    <div id="veto-list"></div>
  </section>
</main>

<footer>Loopback-only · read-only observer · CLI-first governance · dashboard never gates</footer>

<script>
(function(){
  const q = new URLSearchParams(location.search);
  const t = q.get('t') || '';
  const kpi = {spawn:0, veto:0, debate:0, plan:0, bench:0, lesson:0};
  const vetoBy = new Map();
  const status = document.getElementById('status');
  const stream = document.getElementById('stream');
  const vlist = document.getElementById('veto-list');

  function setKPI(){
    document.getElementById('k-spawn').textContent = kpi.spawn;
    document.getElementById('k-veto').textContent = kpi.veto;
    document.getElementById('k-debate').textContent = kpi.debate;
    document.getElementById('k-plan').textContent = kpi.plan;
    document.getElementById('k-bench').textContent = kpi.bench;
    document.getElementById('k-lesson').textContent = kpi.lesson;
  }
  function renderVetoes(){
    vlist.innerHTML = '';
    [...vetoBy.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).forEach(([k,v])=>{
      const d=document.createElement('div');d.className='row veto';
      d.innerHTML='<span class="t">'+v+'×</span><span class="a">'+k+'</span>';
      vlist.appendChild(d);
    });
  }
  function addRow(ev){
    const d = document.createElement('div');
    const a = ev.action || 'unknown';
    let cls = 'row';
    let label = a;
    if (a === 'agent_spawn') { kpi.spawn++; label = 'spawn · ' + (ev.skill||ev.subagent_type||'?'); }
    else if (a === 'veto_triggered') { kpi.veto++; cls += ' veto'; label = 'veto · ' + (ev.reason_code||''); vetoBy.set(ev.reason_code||'?', (vetoBy.get(ev.reason_code||'?')||0)+1); renderVetoes(); }
    else if (a === 'debate_event') { kpi.debate++; cls += ' debate'; label = 'debate · ' + (ev.plan_id||'?') + ' r' + (ev.round||'?') + ' · ' + (ev.agent||'?'); }
    else if (a === 'plan_transition') { kpi.plan++; cls += ' plan'; label = 'plan · ' + (ev.plan_id||'?') + ' ' + (ev.from_status||'?') + '→' + (ev.to_status||'?'); }
    else if (a === 'benchmark_run') { kpi.bench++; cls += ' bench'; var _pr = ev.pass_rate_bps!=null ? (ev.pass_rate_bps/1000).toFixed(3) : (ev.pass_rate!=null ? Number(ev.pass_rate).toFixed(2) : '?'); label = 'benchmark · ' + (ev.skill||'?') + ' pass_rate=' + _pr; }
    else if (a === 'lesson_write') { kpi.lesson++; label = 'lesson · ' + (ev.archetype||'?') + ' · ' + (ev.trigger||''); }
    d.className = cls;
    const ts = (ev.ts||'').replace('T',' ').replace('Z','');
    d.innerHTML = '<span class="t">'+ts+'</span><span class="a">'+escapeHTML(label)+'</span>';
    stream.insertBefore(d, stream.firstChild);
    while (stream.children.length > 500) stream.removeChild(stream.lastChild);
    setKPI();
  }
  function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}

  if (!t) { status.textContent='missing token'; status.className='err'; return; }
  const ev = new EventSource('/events?t=' + encodeURIComponent(t));
  ev.onopen = () => { status.textContent = 'live'; status.className = 'live'; };
  ev.onerror = () => { status.textContent = 'disconnected'; status.className = 'err'; };
  ev.onmessage = (m) => {
    try { addRow(JSON.parse(m.data)); } catch(e) {}
  };
})();
</script>
</body>
</html>
"""


# -----------------------------------------------------------------------------
# HTTP handler
# -----------------------------------------------------------------------------


class DashboardState:
    """Shared server state (token, log path, options)."""

    def __init__(
        self,
        token: str,
        log_path: Path,
        tail_n: int,
        max_connections: int,
        panel_max_clients: int = PANEL_MAX_CLIENTS,
        panel_cache_max: int = PANEL_CACHE_MAX,
    ):
        self.token = token
        self.log_path = log_path
        self.tail_n = tail_n
        self.max_connections = max_connections
        self.panel_max_clients = panel_max_clients
        self.active_sse = 0
        self.active_panel = 0
        self._lock = threading.Lock()
        # PLAN-019 F-CHAOS-7: bounded LRU panel cache.
        # Keyed by (panel_name, log_mtime_ns, log_size) so any append to
        # the JSONL invalidates stale entries automatically. Values are
        # already-rendered HTML strings. Trim at `panel_cache_max`.
        self.panel_cache_max = panel_cache_max
        self._panel_cache: "OrderedDict[tuple, str]" = OrderedDict()

    def panel_cache_get(self, key: tuple) -> Optional[str]:
        """Return cached panel HTML for `key`, touching LRU order on hit."""
        with self._lock:
            if key in self._panel_cache:
                # LRU touch.
                self._panel_cache.move_to_end(key)
                return self._panel_cache[key]
            return None

    def panel_cache_put(self, key: tuple, value: str) -> None:
        """Cache rendered panel HTML under `key`, evicting oldest over cap."""
        with self._lock:
            self._panel_cache[key] = value
            self._panel_cache.move_to_end(key)
            # Trim from the oldest end until within cap.
            while len(self._panel_cache) > self.panel_cache_max:
                self._panel_cache.popitem(last=False)

    def sse_acquire(self) -> bool:
        """Reserve one SSE slot; return False if the connection cap is full."""
        with self._lock:
            if self.active_sse >= self.max_connections:
                return False
            self.active_sse += 1
            return True

    def sse_release(self) -> None:
        """Release a previously-acquired SSE slot (floored at zero)."""
        with self._lock:
            self.active_sse = max(0, self.active_sse - 1)

    def panel_acquire(self) -> bool:
        """Reserve one panel-client slot; return False if the cap is full."""
        with self._lock:
            if self.active_panel >= self.panel_max_clients:
                return False
            self.active_panel += 1
            return True

    def panel_release(self) -> None:
        """Release a previously-acquired panel-client slot (floored at zero)."""
        with self._lock:
            self.active_panel = max(0, self.active_panel - 1)


# -----------------------------------------------------------------------------
# JSONL reader (fail-open on malformed lines; concurrent-reader safe)
# -----------------------------------------------------------------------------


# PLAN-025 Batch D F-obs-007: expose malformed-line counter to the UI panel
# so adopters can see forensic-integrity degradation at a glance (not only in
# stderr logs that most dashboard users never read).
_MALFORMED_COUNT = 0


def get_malformed_count() -> int:
    """Return the total malformed-line count observed since process start."""
    return _MALFORMED_COUNT


def reset_malformed_count() -> None:
    """Reset the counter (tests call this between cases)."""
    global _MALFORMED_COUNT
    _MALFORMED_COUNT = 0


def _iter_events(log_path: Path) -> Iterable[Dict[str, Any]]:
    """Yield one event per line, skipping malformed lines.

    Fail-open contract: a truncated / corrupted line does NOT abort the
    whole read. A breadcrumb is written to stderr so the operator can see
    parse errors in the dashboard launch terminal.

    Concurrent-reader safety: we open+read+close in one call. The writer
    side holds fcntl.flock when appending (audit_emit.py via _lib/filelock);
    read-side opens are never locked. A rotation that happens mid-read
    produces either the pre-rotation bytes OR the post-rotation bytes
    depending on timing — both are valid JSONL snapshots. A simultaneous
    partial write shows up as a malformed final line, which we skip.

    PLAN-025 Batch D F-obs-007: increments module-level ``_MALFORMED_COUNT``
    on each skipped line so the dashboard UI can surface the tally.
    """
    global _MALFORMED_COUNT
    if not log_path.exists():
        return
    try:
        with log_path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    yield json.loads(raw)
                except Exception as exc:  # noqa: BLE001
                    # Fail-open: log and continue
                    _MALFORMED_COUNT += 1
                    sys.stderr.write(
                        f"[audit-dashboard] skipping malformed line "
                        f"{log_path}:{lineno}: {exc} "
                        f"(total malformed this session: {_MALFORMED_COUNT})\n"
                    )
                    continue
    except OSError as exc:
        sys.stderr.write(f"[audit-dashboard] read failed {log_path}: {exc}\n")
        return


def _parse_ts(s: str) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    raw = s.strip()
    if raw.endswith("Z") or raw.endswith("z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# -----------------------------------------------------------------------------
# Panel aggregations (pure functions — easy to unit-test)
# -----------------------------------------------------------------------------


def aggregate_tokens(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate `usage.total_tokens` per archetype per day from agent_spawn.

    Supports both shapes:
      - PLAN-006 flat: event["tokens_in"] / event["tokens_out"]
      - External adapter: event["usage"]["total_tokens"]
    """
    per_archetype_day: Dict[Tuple[str, str], int] = defaultdict(int)
    per_archetype_total: Dict[str, int] = defaultdict(int)
    spawn_count = 0
    without_tokens = 0
    for e in events:
        if e.get("action") != "agent_spawn":
            continue
        spawn_count += 1
        archetype = str(e.get("archetype") or e.get("subagent_type") or e.get("skill") or "unknown")
        # Day bucket (UTC)
        dt = _parse_ts(str(e.get("ts") or ""))
        day = dt.strftime("%Y-%m-%d") if dt else "unknown"
        # Token extraction
        total = None
        usage = e.get("usage")
        if isinstance(usage, dict):
            t = usage.get("total_tokens")
            if isinstance(t, int):
                total = t
        if total is None:
            tin = e.get("tokens_in")
            tout = e.get("tokens_out")
            if isinstance(tin, int) or isinstance(tout, int):
                total = (tin if isinstance(tin, int) else 0) + (tout if isinstance(tout, int) else 0)
        if total is None:
            without_tokens += 1
            continue
        per_archetype_day[(archetype, day)] += total
        per_archetype_total[archetype] += total
    # Shape
    rows = sorted(
        [{"archetype": a, "day": d, "total_tokens": t} for (a, d), t in per_archetype_day.items()],
        key=lambda r: (r["day"], -r["total_tokens"]),
        reverse=False,
    )
    totals = sorted(
        [{"archetype": a, "total_tokens": t} for a, t in per_archetype_total.items()],
        key=lambda r: -r["total_tokens"],
    )
    return {
        "spawn_count": spawn_count,
        "records_without_tokens": without_tokens,
        "per_archetype_day": rows,
        "per_archetype_total": totals,
    }


def aggregate_reflexion(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Lesson hit/miss/ratio + top-10 by effectiveness.

    Mirrors audit-query lessons-effectiveness default filter
    (excludes inference_mode="window-only" gaming-risk data).
    """
    agg: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"hit": 0, "miss": 0, "injections": 0, "last": ""}
    )
    global_hit = 0
    global_miss = 0
    for e in events:
        action = e.get("action")
        if action == "lesson_outcome":
            mode = e.get("inference_mode", "")
            if mode == "window-only":
                continue
            lid = e.get("lesson_id") or ""
            if not lid:
                continue
            for part in str(lid).split(","):
                part = part.strip()
                if not part:
                    continue
                a = agg[part]
                if e.get("hit"):
                    a["hit"] += 1
                    global_hit += 1
                else:
                    a["miss"] += 1
                    global_miss += 1
                ts = e.get("ts", "")
                if isinstance(ts, str) and ts > a["last"]:
                    a["last"] = ts
        elif action == "lesson_read":
            for lid in e.get("lesson_ids", []) or []:
                agg[str(lid)]["injections"] += 1
    total = global_hit + global_miss
    ratio = (global_hit / total) if total > 0 else None
    lessons = []
    for lid, a in agg.items():
        t = a["hit"] + a["miss"]
        eff = (a["hit"] / t) if t > 0 else None
        lessons.append({
            "lesson_id": lid,
            "hit_count": a["hit"],
            "miss_count": a["miss"],
            "effectiveness": eff,
            "injection_count": a["injections"],
            "last_outcome_at": a["last"],
        })
    lessons.sort(key=lambda x: (x["effectiveness"] is None, -(x["effectiveness"] or 0.0)))
    return {
        "global_hit": global_hit,
        "global_miss": global_miss,
        "hit_miss_ratio": ratio,
        "top_10": lessons[:10],
        "lesson_count": len(lessons),
    }


def aggregate_pruning(events: Iterable[Dict[str, Any]], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Restore ratio for 24h / 7d / 30d windows + safety guard triggers.

    Reads `lesson_archived` and `lesson_restored` events, plus any
    `prune_safety_guard_triggered` metadata embedded on lesson_archived
    events (PLAN-009 ADR-020 `--force-dangerous-threshold` flag).
    """
    now = now or datetime.now(timezone.utc)
    windows = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    cutoffs = {k: now - v for k, v in windows.items()}

    per_window: Dict[str, Dict[str, Any]] = {
        k: {"archived": 0, "restored_unique": set(), "restore_events": 0}
        for k in windows
    }
    safety_guards = 0
    events_list = list(events)
    for e in events_list:
        ts = _parse_ts(str(e.get("ts") or ""))
        if ts is None:
            continue
        action = e.get("action")
        if action == "lesson_archived":
            for win, cut in cutoffs.items():
                if ts >= cut:
                    per_window[win]["archived"] += 1
            if e.get("force_dangerous_threshold") or e.get("safety_guard_triggered"):
                safety_guards += 1
        elif action == "lesson_restored":
            lid = e.get("lesson_id", "")
            for win, cut in cutoffs.items():
                if ts >= cut:
                    per_window[win]["restore_events"] += 1
                    if lid:
                        per_window[win]["restored_unique"].add(lid)

    out_windows = {}
    for win, d in per_window.items():
        archived = d["archived"]
        unique_restored = len(d["restored_unique"])
        ratio = (unique_restored / archived) if archived > 0 else None
        out_windows[win] = {
            "archived_count": archived,
            "unique_restored": unique_restored,
            "restore_events": d["restore_events"],
            "restore_ratio": ratio,
        }
    return {
        "windows": out_windows,
        "safety_guard_triggers": safety_guards,
    }


def aggregate_architect_outcomes(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Session-correlated vs window-only + per-consumer breakdown."""
    by_mode: Dict[str, int] = defaultdict(int)
    by_consumer: Dict[str, int] = defaultdict(int)
    by_consumer_mode: Dict[Tuple[str, str], int] = defaultdict(int)
    hits_by_consumer: Dict[str, int] = defaultdict(int)
    misses_by_consumer: Dict[str, int] = defaultdict(int)
    total = 0
    for e in events:
        if e.get("action") != "lesson_outcome":
            continue
        total += 1
        mode = e.get("inference_mode") or "unspecified"
        consumer = e.get("consumer") or "benchmark"
        by_mode[mode] += 1
        by_consumer[consumer] += 1
        by_consumer_mode[(consumer, mode)] += 1
        if e.get("hit"):
            hits_by_consumer[consumer] += 1
        else:
            misses_by_consumer[consumer] += 1

    per_consumer = []
    for c, n in by_consumer.items():
        h = hits_by_consumer[c]
        m = misses_by_consumer[c]
        eff = (h / (h + m)) if (h + m) > 0 else None
        per_consumer.append({
            "consumer": c,
            "outcome_count": n,
            "hits": h,
            "misses": m,
            "effectiveness": eff,
        })
    per_consumer.sort(key=lambda x: -x["outcome_count"])

    return {
        "total_outcomes": total,
        "by_inference_mode": dict(by_mode),
        "by_consumer": per_consumer,
        "by_consumer_and_mode": {f"{c}|{m}": n for (c, m), n in by_consumer_mode.items()},
    }


# -----------------------------------------------------------------------------
# Panel HTML rendering (stdlib string formatting — no external templating)
# -----------------------------------------------------------------------------


_PANEL_CSS = """<style>
body{margin:0;padding:16px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#0b0d10;color:#e8ecef;font-size:13px;line-height:1.4}
h1{font-size:14px;margin:0 0 4px 0}
h2{font-size:12px;color:#6b7480;margin:18px 0 6px 0;text-transform:uppercase;letter-spacing:.5px}
.nav{color:#6b7480;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #1e2429}
.nav a{color:#4ea3ff;margin-right:12px;text-decoration:none}
.empty{color:#6b7480;font-style:italic;padding:20px;text-align:center;border:1px dashed #1e2429;border-radius:4px}
table{border-collapse:collapse;width:100%;margin-bottom:12px}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid #1e2429;vertical-align:top}
th{color:#6b7480;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.kpi{display:inline-block;margin:0 16px 8px 0}
.kpi b{font-size:20px;display:block}
.kpi span{color:#6b7480;font-size:11px}
.warn{color:#ffa94d}
.err{color:#ff6b6b}
.ok{color:#3bd671}
</style>"""


def _esc(v: Any) -> str:
    return html.escape(str(v), quote=True)


def _nav_html(token: str) -> str:
    t = _esc(token)
    return (
        '<div class="nav">'
        f'<a href="/?t={t}">overview</a>'
        f'<a href="/panel/tokens?t={t}">tokens</a>'
        f'<a href="/panel/reflexion?t={t}">reflexion</a>'
        f'<a href="/panel/pruning?t={t}">pruning</a>'
        f'<a href="/panel/architect-outcomes?t={t}">architect-outcomes</a>'
        '</div>'
    )


def _fmt_ratio(r: Optional[float]) -> str:
    if r is None:
        return "—"
    return f"{r:.1%}"


def _fmt_num(n: Optional[int]) -> str:
    if n is None:
        return "—"
    return f"{n:,}"


def render_tokens_panel(agg: Dict[str, Any], token: str) -> str:
    """Render the SSE dashboard panel for per-session token spend."""
    body: List[str] = []
    body.append(_nav_html(token))
    body.append("<h1>Token usage</h1>")
    body.append(
        '<div class="kpi"><b>{}</b><span>agent_spawn events</span></div>'.format(
            _fmt_num(agg["spawn_count"])
        )
    )
    body.append(
        '<div class="kpi"><b>{}</b><span>records without tokens</span></div>'.format(
            _fmt_num(agg["records_without_tokens"])
        )
    )
    if not agg["per_archetype_total"]:
        body.append('<div class="empty">no token data yet</div>')
    else:
        body.append("<h2>Totals by archetype</h2>")
        body.append("<table><tr><th>archetype</th><th>total tokens</th></tr>")
        for r in agg["per_archetype_total"]:
            body.append(
                f'<tr><td>{_esc(r["archetype"])}</td>'
                f'<td class="num">{_fmt_num(r["total_tokens"])}</td></tr>'
            )
        body.append("</table>")
        body.append("<h2>By archetype × day</h2>")
        body.append("<table><tr><th>day</th><th>archetype</th><th>tokens</th></tr>")
        for r in agg["per_archetype_day"]:
            body.append(
                f'<tr><td>{_esc(r["day"])}</td><td>{_esc(r["archetype"])}</td>'
                f'<td class="num">{_fmt_num(r["total_tokens"])}</td></tr>'
            )
        body.append("</table>")
    return _page("tokens", "".join(body))


def render_reflexion_panel(agg: Dict[str, Any], token: str) -> str:
    """Render the SSE dashboard panel for Reflexion-v2 lesson outcomes."""
    body: List[str] = []
    body.append(_nav_html(token))
    body.append("<h1>Reflexion lessons</h1>")
    body.append(
        '<div class="kpi"><b>{}</b><span>hits</span></div>'.format(_fmt_num(agg["global_hit"]))
    )
    body.append(
        '<div class="kpi"><b>{}</b><span>misses</span></div>'.format(_fmt_num(agg["global_miss"]))
    )
    body.append(
        '<div class="kpi"><b>{}</b><span>hit/miss ratio</span></div>'.format(
            _fmt_ratio(agg["hit_miss_ratio"])
        )
    )
    body.append(
        '<div class="kpi"><b>{}</b><span>lessons with outcomes</span></div>'.format(
            _fmt_num(agg["lesson_count"])
        )
    )
    body.append("<h2>Top-10 effectiveness</h2>")
    if not agg["top_10"]:
        body.append('<div class="empty">no lesson_outcome events yet</div>')
    else:
        body.append(
            "<table><tr><th>lesson_id</th><th>hits</th><th>misses</th>"
            "<th>effectiveness</th><th>injections</th><th>last outcome</th></tr>"
        )
        for r in agg["top_10"]:
            body.append(
                f'<tr><td>{_esc(r["lesson_id"])}</td>'
                f'<td class="num">{_fmt_num(r["hit_count"])}</td>'
                f'<td class="num">{_fmt_num(r["miss_count"])}</td>'
                f'<td class="num">{_fmt_ratio(r["effectiveness"])}</td>'
                f'<td class="num">{_fmt_num(r["injection_count"])}</td>'
                f'<td>{_esc(r["last_outcome_at"] or "—")}</td></tr>'
            )
        body.append("</table>")
    return _page("reflexion", "".join(body))


def render_pruning_panel(agg: Dict[str, Any], token: str) -> str:
    """Render the SSE dashboard panel for lesson-pruning activity."""
    body: List[str] = []
    body.append(_nav_html(token))
    body.append("<h1>Pruning (restore ratio)</h1>")
    body.append(
        '<div class="kpi"><b class="{}">{}</b><span>safety-guard triggers</span></div>'.format(
            "warn" if agg["safety_guard_triggers"] else "",
            _fmt_num(agg["safety_guard_triggers"]),
        )
    )
    empty = all(w["archived_count"] == 0 for w in agg["windows"].values())
    if empty:
        body.append('<div class="empty">no lesson_archived events yet</div>')
    else:
        body.append("<h2>Restore ratio by window</h2>")
        body.append(
            "<table><tr><th>window</th><th>archived</th><th>unique restored</th>"
            "<th>restore events</th><th>ratio</th></tr>"
        )
        for win in ("24h", "7d", "30d"):
            w = agg["windows"][win]
            ratio_cls = ""
            r = w["restore_ratio"]
            if r is not None and r > 0.10:
                ratio_cls = "err"
            elif r is not None and r > 0.05:
                ratio_cls = "warn"
            body.append(
                f'<tr><td>{win}</td>'
                f'<td class="num">{_fmt_num(w["archived_count"])}</td>'
                f'<td class="num">{_fmt_num(w["unique_restored"])}</td>'
                f'<td class="num">{_fmt_num(w["restore_events"])}</td>'
                f'<td class="num {ratio_cls}">{_fmt_ratio(w["restore_ratio"])}</td></tr>'
            )
        body.append("</table>")
    return _page("pruning", "".join(body))


def aggregate_swarm(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """PLAN-017 Phase 4 — aggregate swarm_* audit events by swarm_id.

    Counts started/iteration/halted/killed/tournament per swarm.
    Active swarms = started without subsequent halted/killed/aborted.
    """
    swarm_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    swarm_started = 0
    swarm_halted = 0
    swarm_killed = 0
    swarm_aborted = 0
    swarm_iterations = 0
    swarm_tournament_selected = 0
    for e in events:
        action = e.get("action", "")
        if not action.startswith("swarm_"):
            continue
        sid = e.get("swarm_id", "unknown")
        swarm_events[sid].append(e)
        if action == "swarm_started":
            swarm_started += 1
        elif action == "swarm_iteration":
            swarm_iterations += 1
        elif action.startswith("swarm_halted_"):
            swarm_halted += 1
        elif action == "swarm_killed":
            swarm_killed += 1
        elif action == "swarm_aborted_error":
            swarm_aborted += 1
        elif action == "swarm_tournament_selected":
            swarm_tournament_selected += 1

    per_swarm = []
    for sid, evts in swarm_events.items():
        actions = [e.get("action", "") for e in evts]
        status = "running"
        if any(a == "swarm_killed" for a in actions):
            status = "killed"
        elif any(a == "swarm_aborted_error" for a in actions):
            status = "errored"
        elif any(a.startswith("swarm_halted_") for a in actions):
            status = "halted"
        elif any(a == "swarm_tournament_selected" for a in actions):
            status = "completed"
        per_swarm.append({
            "swarm_id": sid,
            "status": status,
            "events": len(evts),
            "iterations": sum(1 for a in actions if a == "swarm_iteration"),
        })
    per_swarm.sort(key=lambda x: x["swarm_id"])

    return {
        "swarm_started": swarm_started,
        "swarm_iterations": swarm_iterations,
        "swarm_halted": swarm_halted,
        "swarm_killed": swarm_killed,
        "swarm_aborted": swarm_aborted,
        "swarm_tournament_selected": swarm_tournament_selected,
        "per_swarm": per_swarm,
        "total_swarms": len(swarm_events),
    }


def render_swarm_panel(agg: Dict[str, Any], token: str) -> str:
    """PLAN-017 Phase 4 — render swarm loops panel."""
    body: List[str] = []
    body.append(_nav_html(token))
    body.append("<h1>Swarm loops (PLAN-017)</h1>")
    body.append(
        '<div class="kpi"><b>{}</b><span>total swarms observed</span></div>'.format(
            _fmt_num(agg["total_swarms"])
        )
    )
    if agg["total_swarms"] == 0:
        body.append('<div class="empty">no swarm_* events yet — '
                    'CEO_SWARM=1 + .claude/scripts/swarm/coordinator.py</div>')
    else:
        body.append("<h2>Event totals</h2>")
        body.append("<table><tr><th>action</th><th>count</th></tr>")
        for label, n in [
            ("swarm_started", agg["swarm_started"]),
            ("swarm_iteration", agg["swarm_iterations"]),
            ("swarm_halted_*", agg["swarm_halted"]),
            ("swarm_killed", agg["swarm_killed"]),
            ("swarm_aborted_error", agg["swarm_aborted"]),
            ("swarm_tournament_selected", agg["swarm_tournament_selected"]),
        ]:
            body.append(
                f'<tr><td>{_esc(label)}</td>'
                f'<td class="num">{_fmt_num(n)}</td></tr>'
            )
        body.append("</table>")
        body.append("<h2>Per-swarm status</h2>")
        body.append(
            "<table><tr><th>swarm_id</th><th>status</th>"
            "<th>events</th><th>iterations</th></tr>"
        )
        for r in agg["per_swarm"]:
            st_cls = {
                "running": "ok",
                "completed": "ok",
                "halted": "warn",
                "killed": "err",
                "errored": "err",
            }.get(r["status"], "")
            body.append(
                f'<tr><td>{_esc(r["swarm_id"])}</td>'
                f'<td class="{st_cls}">{_esc(r["status"])}</td>'
                f'<td class="num">{_fmt_num(r["events"])}</td>'
                f'<td class="num">{_fmt_num(r["iterations"])}</td></tr>'
            )
        body.append("</table>")
    return _page("swarm", "".join(body))


def render_architect_outcomes_panel(agg: Dict[str, Any], token: str) -> str:
    """Render the SSE dashboard panel for architect-bundle outcomes."""
    body: List[str] = []
    body.append(_nav_html(token))
    body.append("<h1>Architect outcomes</h1>")
    body.append(
        '<div class="kpi"><b>{}</b><span>total lesson_outcome events</span></div>'.format(
            _fmt_num(agg["total_outcomes"])
        )
    )
    if agg["total_outcomes"] == 0:
        body.append('<div class="empty">no lesson_outcome events yet</div>')
    else:
        body.append("<h2>By inference mode</h2>")
        body.append("<table><tr><th>mode</th><th>count</th></tr>")
        for mode, n in sorted(agg["by_inference_mode"].items(), key=lambda x: -x[1]):
            cls = "ok" if mode == "session-correlated" else ("warn" if mode == "window-only" else "")
            body.append(
                f'<tr><td class="{cls}">{_esc(mode)}</td>'
                f'<td class="num">{_fmt_num(n)}</td></tr>'
            )
        body.append("</table>")
        body.append("<h2>By consumer</h2>")
        body.append(
            "<table><tr><th>consumer</th><th>outcomes</th><th>hits</th>"
            "<th>misses</th><th>effectiveness</th></tr>"
        )
        for r in agg["by_consumer"]:
            body.append(
                f'<tr><td>{_esc(r["consumer"])}</td>'
                f'<td class="num">{_fmt_num(r["outcome_count"])}</td>'
                f'<td class="num">{_fmt_num(r["hits"])}</td>'
                f'<td class="num">{_fmt_num(r["misses"])}</td>'
                f'<td class="num">{_fmt_ratio(r["effectiveness"])}</td></tr>'
            )
        body.append("</table>")
    return _page("architect-outcomes", "".join(body))


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>ceo-orchestration — {_esc(title)}</title>"
        f"{_PANEL_CSS}</head><body>{body}</body></html>"
    )


def _render_panel_body(
    state: "DashboardState",
    name: str,
    aggregator,
    renderer,
) -> "Tuple[int, bytes]":
    """Build the (status, body_bytes) tuple for a panel request.

    PLAN-023 Phase E decomposition: pulls the LRU-cache-and-aggregate
    logic out of the Handler class so ``_make_handler`` stays < 150 LoC.
    """
    cache_key: Optional[tuple] = None
    try:
        st = state.log_path.stat()
        cache_key = (name, st.st_mtime_ns, st.st_size)
    except OSError:
        cache_key = None
    if cache_key is not None:
        hit = state.panel_cache_get(cache_key)
        if hit is not None:
            return 200, hit.encode("utf-8")

    events = _iter_events(state.log_path)
    try:
        agg = aggregator(events)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[audit-dashboard] panel {name} failed: {exc}\n")
        agg = None
    if agg is None:
        body = _page(name, _nav_html(state.token) +
                     f'<h1>{_esc(name)}</h1>'
                     '<div class="empty">panel unavailable — see dashboard stderr</div>')
    else:
        body = renderer(agg, state.token)
        if cache_key is not None:
            state.panel_cache_put(cache_key, body)
    return 200, body.encode("utf-8")


def _sse_tail_loop(handler, state: "DashboardState") -> None:
    """Perf-P2-003 exponential-backoff tailing loop for SSE.

    Factored out of the Handler class (PLAN-023 Phase E) so
    ``_make_handler`` stays under 150 LoC. Semantics unchanged:
    100ms–2s adaptive wait, rotation detection, 15s heartbeat,
    malformed-line tolerance, BrokenPipe termination.

    NOTE on stdlib ``selectors``: the module works for sockets and
    pipes but NOT for regular files on Linux/macOS. Native file-
    change notification is not in stdlib. Exponential backoff with
    a 2s cap is the practical stdlib-only ceiling.
    """
    POLL_MIN = 0.1
    POLL_MAX = 2.0
    log = state.log_path
    wait = POLL_MIN
    pos = log.stat().st_size if log.exists() else 0
    heartbeat = time.monotonic()
    while True:
        try:
            if not log.exists():
                time.sleep(POLL_MAX)
                continue
            size = log.stat().st_size
            if size < pos:
                pos = 0  # rotation — restart from head
            had_new_bytes = False
            if size > pos:
                with log.open("r", encoding="utf-8") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                had_new_bytes = bool(chunk)
                for line in chunk.splitlines():
                    if line.strip():
                        if not handler._write_sse(line):
                            return
            if time.monotonic() - heartbeat > 15:
                try:
                    handler.wfile.write(b": heartbeat\n\n")
                    handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                heartbeat = time.monotonic()
            # Adaptive backoff: new content = fast loop, idle = slow.
            if had_new_bytes:
                wait = POLL_MIN
            else:
                wait = min(POLL_MAX, wait * 2)
            time.sleep(wait)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                "[audit-dashboard] SSE inner-loop aborted: "
                f"{type(exc).__name__}: {exc}\n"
            )
            return


def _make_handler(state: DashboardState) -> "type[BaseHTTPRequestHandler]":
    """Construct the per-state BaseHTTPRequestHandler subclass.

    PLAN-023 Phase E decomposition: panel-render + SSE-tail loops
    live at module level (``_render_panel_body`` + ``_sse_tail_loop``);
    the Handler class is now a thin routing shell.
    """
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args) -> None:
            return  # silence default stdout logging

        def setup(self) -> None:
            super().setup()
            try:
                # Debate C12: per-connection server-side socket timeout.
                self.connection.settimeout(PANEL_REQUEST_TIMEOUT_S)
            except (OSError, AttributeError):
                pass

        def _auth(self, parsed) -> bool:
            q = parse_qs(parsed.query)
            tok = (q.get("t") or [""])[0]
            return bool(tok) and secrets.compare_digest(tok, state.token)

        def _send(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8", extra_headers=None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self) -> None:
            """HTTP GET handler — dispatches to render_*_panel or the stream endpoint."""
            parsed = urlparse(self.path)
            if not self._auth(parsed):
                self._send(401, b"401 unauthorized (pass ?t=<token>)\n")
                return

            if parsed.path in ("/", "/index.html"):
                self._send(200, _HTML.encode("utf-8"), "text/html; charset=utf-8")
                return

            if parsed.path == "/events":
                self._stream_events()
                return

            panel_map = {
                "/panel/tokens": ("tokens", aggregate_tokens, render_tokens_panel),
                "/panel/reflexion": ("reflexion", aggregate_reflexion, render_reflexion_panel),
                "/panel/pruning": ("pruning", aggregate_pruning, render_pruning_panel),
                "/panel/architect-outcomes": (
                    "architect-outcomes",
                    aggregate_architect_outcomes,
                    render_architect_outcomes_panel,
                ),
                "/panel/swarm": ("swarm", aggregate_swarm, render_swarm_panel),
            }
            if parsed.path in panel_map:
                self._serve_panel(*panel_map[parsed.path])
                return

            self._send(404, b"404 not found\n")

        def _serve_panel(self, name, aggregator, renderer) -> None:
            # Debate C12: concurrent-client cap (max 5) — reject 6th with 503.
            if not state.panel_acquire():
                self._send(503, b"503 too many clients\n")
                return
            try:
                code, body = _render_panel_body(state, name, aggregator, renderer)
                self._send(code, body, "text/html; charset=utf-8")
            finally:
                state.panel_release()

        def do_POST(self) -> None:
            self._send(405, b"405 method not allowed (read-only dashboard)\n")

        def do_PUT(self) -> None:
            self._send(405, b"405 method not allowed (read-only dashboard)\n")

        def do_DELETE(self) -> None:
            self._send(405, b"405 method not allowed (read-only dashboard)\n")

        def _stream_events(self) -> None:
            if not state.sse_acquire():
                self._send(503, b"503 too many connections\n")
                return
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store, no-transform")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()

                # Initial replay
                tail = self._read_tail(state.log_path, state.tail_n)
                for line in tail:
                    if not self._write_sse(line):
                        return

                # Follow new lines via the extracted tail loop.
                _sse_tail_loop(self, state)
            finally:
                state.sse_release()

        def _read_tail(self, log: Path, n: int) -> List[str]:
            """Return the last ``n`` non-empty lines via bounded reverse-scan
            (Perf-P1-004 — memory-bounded vs full-file materialization)."""
            return _tail_lines_reverse(log, n)

        def _write_sse(self, raw_line: str) -> bool:
            try:
                json.loads(raw_line)  # validate; skip malformed silently
            except json.JSONDecodeError:
                return True
            except ValueError as exc:
                sys.stderr.write(
                    f"[audit-dashboard] SSE validate skip (ValueError): {exc}\n"
                )
                return True
            try:
                data = f"data: {raw_line}\n\n".encode("utf-8")
                self.wfile.write(data)
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

    return Handler


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="ceo-orchestration local audit dashboard")
    parser.add_argument("--port", type=int, default=0, help="port (default: 0 = random)")
    parser.add_argument("--bind", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--tail", type=int, default=500, help="replay last N events (default: 500)")
    parser.add_argument("--max-connections", type=int, default=4, help="max concurrent SSE connections (default: 4)")
    parser.add_argument("--token-file", metavar="PATH", help="write token to file instead of stdout")
    args = parser.parse_args(argv)

    # Enforce loopback
    if args.bind not in ("127.0.0.1", "::1", "localhost"):
        print(f"ERROR: --bind must be loopback (got {args.bind!r})", file=sys.stderr)
        return 2

    token = secrets.token_urlsafe(32)
    state = DashboardState(
        token=token,
        log_path=_log_path(),
        tail_n=args.tail,
        max_connections=args.max_connections,
    )

    # Start server
    handler_cls = _make_handler(state)
    server = ThreadingHTTPServer((args.bind, args.port), handler_cls)
    actual_port = server.server_port

    url = f"http://{args.bind}:{actual_port}/?t={token}"
    if args.token_file:
        Path(args.token_file).write_text(token + "\n")
        try:
            os.chmod(args.token_file, 0o600)
        except OSError:
            pass
        print(f"dashboard: http://{args.bind}:{actual_port}/  (token written to {args.token_file})")
    else:
        print(url)

    print(f"log: {state.log_path}")
    print(f"tail: last {args.tail} events replayed on connect; max {args.max_connections} concurrent SSE")
    print("read-only · loopback · ctrl-c to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping.", file=sys.stderr)
        server.shutdown()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
