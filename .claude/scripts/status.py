#!/usr/bin/env python3
"""`/status` — single-glance project overview.

PLAN-007 Phase C. Reads audit log, plans, lessons, CI — renders
human-readable snapshot. Always exits 0 (advisory).

Usage:
    python3 .claude/scripts/status.py            # human
    python3 .claude/scripts/status.py --json     # machine
    python3 .claude/scripts/status.py --since 7d # last 7 days
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"
PLANS_DIR = REPO_ROOT / ".claude" / "plans"


def _audit_log_path() -> Path:
    home = Path(os.environ.get("HOME") or str(Path.home()))
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _audit_errors_path() -> Path:
    home = Path(os.environ.get("HOME") or str(Path.home()))
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.errors"


def _load_recent_events(hours: int = 24) -> List[Dict[str, Any]]:
    """Load audit events from last N hours. Returns [] on any error."""
    path = _audit_log_path()
    if not path.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = event.get("ts", "")
                if ts:
                    try:
                        event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if event_time < cutoff:
                            continue
                    except ValueError:
                        pass
                events.append(event)
    except OSError:
        return []
    return events


def _find_active_plan() -> Optional[Dict[str, Any]]:
    """Find the plan with status: executing (or most recent done)."""
    if not PLANS_DIR.is_dir():
        return None
    executing = None
    most_recent_done = None
    for plan_file in sorted(PLANS_DIR.glob("PLAN-*.md"), reverse=True):
        try:
            text = plan_file.read_text(encoding="utf-8")
        except OSError:
            continue
        # Parse frontmatter status
        m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if not m:
            continue
        status = m.group(1).strip()
        title_m = re.search(r"^title:\s*(.+?)$", text, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else plan_file.stem
        sprint_m = re.search(r"^sprint:\s*(\d+)", text, re.MULTILINE)
        sprint = int(sprint_m.group(1)) if sprint_m else None
        # Count success checkboxes
        done = len(re.findall(r"- \[x\]", text, re.IGNORECASE))
        total = len(re.findall(r"- \[[ xX]\]", text))
        progress = int(100 * done / total) if total else None

        entry = {
            "id": plan_file.stem.split("-")[0] + "-" + plan_file.stem.split("-")[1],
            "title": title,
            "status": status,
            "sprint": sprint,
            "progress_pct": progress,
            "file": str(plan_file.relative_to(REPO_ROOT)),
        }
        if status == "executing" and executing is None:
            executing = entry
        elif status == "done" and most_recent_done is None:
            most_recent_done = entry
    return executing or most_recent_done


def _count_action(events: List[Dict[str, Any]], action: str) -> int:
    return sum(1 for e in events if e.get("action") == action)


def _filter_action(events: List[Dict[str, Any]], action: str) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("action") == action]


def _token_totals(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    spawns = _filter_action(events, "agent_spawn")
    total_in = sum(e.get("tokens_in") or 0 for e in spawns if isinstance(e.get("tokens_in"), int))
    total_out = sum(e.get("tokens_out") or 0 for e in spawns if isinstance(e.get("tokens_out"), int))
    by_skill: Dict[str, int] = {}
    for e in spawns:
        skill = e.get("skill", "unknown")
        ti = e.get("tokens_in") or 0
        to = e.get("tokens_out") or 0
        by_skill[skill] = by_skill.get(skill, 0) + (ti if isinstance(ti, int) else 0) + (to if isinstance(to, int) else 0)
    top = sorted(by_skill.items(), key=lambda kv: -kv[1])[:3]
    return {"total_in": total_in, "total_out": total_out, "top_skills": top}


def _reflexion_stats(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    outcomes = _filter_action(events, "lesson_outcome")
    hits = sum(1 for e in outcomes if e.get("hit"))
    misses = sum(1 for e in outcomes if not e.get("hit"))
    total = hits + misses
    hit_rate = (hits / total) if total else None
    return {
        "written": _count_action(events, "lesson_write"),
        "outcomes": total,
        "hits": hits,
        "misses": misses,
        "hit_rate": hit_rate,
    }


def _audit_errors_count() -> int:
    path = _audit_errors_path()
    if not path.is_file():
        return 0
    try:
        return sum(1 for _ in open(path, "r", encoding="utf-8"))
    except OSError:
        return 0


def _health_verdict() -> str:
    """Invoke audit-query.py health; extract verdict."""
    aq = SCRIPTS_DIR / "audit-query.py"
    if not aq.is_file():
        return "UNKNOWN"
    try:
        result = subprocess.run(
            [sys.executable, str(aq), "health", "--as-json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return "UNKNOWN"
        data = json.loads(result.stdout)
        return data.get("verdict", "UNKNOWN")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return "UNKNOWN"


def _ci_status() -> Dict[str, Any]:
    """Invoke gh CLI to get last 3 runs."""
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--branch", "main", "--limit", "3",
             "--json", "conclusion,name,createdAt,displayTitle"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return {"available": False, "reason": "gh CLI error"}
        runs = json.loads(result.stdout)
        latest = runs[0] if runs else None
        all_green = all(r.get("conclusion") == "success" for r in runs[:3])
        return {
            "available": True,
            "latest_run": latest,
            "last_3_all_green": all_green,
            "runs": runs,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"available": False, "reason": "gh CLI not installed or timeout"}


def build_status(hours: int = 24) -> Dict[str, Any]:
    """Build the /status snapshot dict from repo + plan + agent state."""
    events = _load_recent_events(hours=hours)
    return {
        "active_plan": _find_active_plan(),
        "health": _health_verdict(),
        "ci": _ci_status(),
        "spawns_recent": [
            {
                "ts": e.get("ts"),
                "subagent_type": e.get("subagent_type"),
                "skill": e.get("skill"),
                "has_profile": e.get("has_profile"),
            }
            for e in _filter_action(events, "agent_spawn")[-5:]
        ],
        "reflexion": _reflexion_stats(events),
        "tokens": _token_totals(events),
        "warnings": {
            "vetos_in_window": _count_action(events, "veto_triggered"),
            "injection_flags_in_window": _count_action(events, "injection_flag"),
            "audit_errors_total": _audit_errors_count(),
        },
        "window_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def render_human(data: Dict[str, Any]) -> str:
    """Render the `/status` snapshot as a human-readable text block."""
    out = []
    out.append(f"## /status — {data['generated_at'][:16]} UTC (janela {data['window_hours']}h)")
    out.append("")
    plan = data.get("active_plan")
    if plan:
        status = plan.get("status", "?")
        progress = plan.get("progress_pct")
        prog_str = f", {progress}% done" if progress is not None else ""
        out.append(f"**Plan:** {plan['id']} \"{plan['title']}\" [{status}{prog_str}]")
    else:
        out.append("**Plan:** nenhum em execução")
    out.append(f"**Health:** {data['health']}")
    ci = data.get("ci", {})
    if ci.get("available"):
        latest = ci.get("latest_run") or {}
        concl = latest.get("conclusion", "?")
        title = latest.get("displayTitle", "?")
        marker = "✅" if concl == "success" else ("❌" if concl == "failure" else "⏳")
        out.append(f"**CI:** {marker} {concl} — {title[:60]}")
    else:
        out.append(f"**CI:** indisponível ({ci.get('reason', '?')})")
    out.append("")
    spawns = data.get("spawns_recent", [])
    if spawns:
        out.append(f"### Últimas {len(spawns)} spawns")
        for s in spawns:
            ts = (s.get("ts") or "")[:16]
            out.append(f"- {ts}  {s.get('subagent_type', '?'):<18}  skill={s.get('skill', '?')}")
    else:
        out.append("### Spawns: 0 na janela")
    out.append("")
    rf = data.get("reflexion", {})
    hr = rf.get("hit_rate")
    hr_str = f"{hr*100:.0f}%" if hr is not None else "—"
    out.append(f"### Reflexion: {rf.get('written', 0)} escritas, "
               f"{rf.get('outcomes', 0)} outcomes ({rf.get('hits', 0)} hit / "
               f"{rf.get('misses', 0)} miss, rate={hr_str})")
    out.append("")
    tk = data.get("tokens", {})
    total = tk.get("total_in", 0) + tk.get("total_out", 0)
    out.append(f"### Tokens: {tk.get('total_in', 0):,} in + {tk.get('total_out', 0):,} out = {total:,}")
    for skill, n in tk.get("top_skills", [])[:3]:
        out.append(f"  - {skill}: {n:,}")
    out.append("")
    w = data.get("warnings", {})
    v = w.get("vetos_in_window", 0)
    inj = w.get("injection_flags_in_window", 0)
    err = w.get("audit_errors_total", 0)
    out.append("### Warnings")
    out.append(f"  {'⚠' if v else '✓'} {v} vetos disparados na janela")
    out.append(f"  {'⚠' if inj else '✓'} {inj} injection flags na janela")
    out.append(f"  {'⚠' if err > 20 else '✓'} {err} breadcrumbs em audit-log.errors (total)")
    out.append("")
    # Sprint 9 Phase 7 P7.4 — surface the 3 new audit-query sub-commands
    out.append("### Drill-down (Sprint 9)")
    out.append("  audit-query prune-restore-ratio    # ADR-020 pruning safety metric")
    out.append("  audit-query architect-outcomes     # /architect hit/miss per lesson")
    out.append("  audit-query lessons-effectiveness  # top-K / bottom-K ranking")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — render /status snapshot to stdout."""
    parser = argparse.ArgumentParser(description="/status — project overview")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--since", default="24h",
                        help="window: Nh (hours) or Nd (days). Default 24h")
    args = parser.parse_args(argv)

    # Parse window
    m = re.match(r"^(\d+)([hd])$", args.since.strip().lower())
    hours = 24
    if m:
        n = int(m.group(1))
        hours = n * (24 if m.group(2) == "d" else 1)

    data = build_status(hours=hours)
    if args.json:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    else:
        print(render_human(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
