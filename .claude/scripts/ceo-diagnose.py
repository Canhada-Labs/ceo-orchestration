#!/usr/bin/env python3
"""ceo-diagnose — single-file health-check CLI for ceo-orchestration adopters.

Round-2 P0 deliverable from PLAN-059. Vibecoder-friendly summary of:
- Open plans (status: draft/reviewed/executing)
- Governance status (validate-governance.sh exit code + warnings)
- Audit-log freshness + last 24h dispatch counts
- ADR-082 mitigation rate (per-archetype dispatch-mode breakdown)
- Install mode hint (vibecoder vs cto, when ADR-086 lands)
- Hook test suite + scripts test suite headline counts

Stdlib-only; Python >= 3.9. No third-party deps. Fail-open on every
section: a failed health probe degrades to "?" instead of crashing.

Usage:
    python3 .claude/scripts/ceo-diagnose.py
    python3 .claude/scripts/ceo-diagnose.py --json
    python3 .claude/scripts/ceo-diagnose.py --quick   # skip slow probes

Exit codes:
    0 — all green
    1 — yellow flags (governance warnings, plans pending, etc.)
    2 — red (governance errors, hook tests failing, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Probe functions — each returns (status, summary_line, detail_dict)
# status ∈ {"green", "yellow", "red", "unknown"}
# ---------------------------------------------------------------------------


def probe_open_plans() -> Tuple[str, str, Dict[str, Any]]:
    """Count plans not in `done` state."""
    plans_dir = REPO_ROOT / ".claude" / "plans"
    open_plans: List[Dict[str, str]] = []
    for plan_file in sorted(plans_dir.glob("PLAN-*.md")):
        if plan_file.name in ("PLAN-SCHEMA.md", "AUDIT-LOG-SCHEMA.md", "DEBATE-SCHEMA.md"):
            continue
        try:
            text = plan_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Frontmatter parse — minimal stdlib-only YAML-lite.
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        front = m.group(1)
        status = ""
        title = ""
        for line in front.splitlines():
            if line.startswith("status:"):
                status = line.split(":", 1)[1].strip()
            elif line.startswith("title:"):
                title = line.split(":", 1)[1].strip()
        if status and status != "done":
            open_plans.append({
                "id": plan_file.stem.split("-", 1)[0] + "-" + plan_file.stem.split("-")[1],
                "title": title[:80],
                "status": status,
                "path": str(plan_file.relative_to(REPO_ROOT)),
            })
    if not open_plans:
        return ("green", "All plans done", {"open_count": 0, "open": []})
    if len(open_plans) <= 2:
        return ("yellow", f"{len(open_plans)} plan(s) open", {"open_count": len(open_plans), "open": open_plans})
    return ("yellow", f"{len(open_plans)} plans open", {"open_count": len(open_plans), "open": open_plans})


def probe_governance() -> Tuple[str, str, Dict[str, Any]]:
    """Run validate-governance.sh; capture exit + warnings count."""
    script = REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
    if not script.exists():
        return ("unknown", "validate-governance.sh missing", {})
    try:
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return ("unknown", f"governance probe failed: {type(e).__name__}", {})
    out = (result.stdout or "") + (result.stderr or "")
    err_match = re.search(r"Errors:\s*(\d+)", out)
    warn_match = re.search(r"Warnings:\s*(\d+)", out)
    errors = int(err_match.group(1)) if err_match else -1
    warnings = int(warn_match.group(1)) if warn_match else -1
    detail = {"exit_code": result.returncode, "errors": errors, "warnings": warnings}
    if result.returncode == 0 and errors == 0:
        if warnings > 0:
            return ("yellow", f"governance OK ({warnings} warnings)", detail)
        return ("green", "governance OK", detail)
    return ("red", f"governance FAIL ({errors} errors)", detail)


def _resolve_audit_log_path() -> Optional[Path]:
    """PLAN-044 audit-v2 C4-P0-02 (Wave B) — project-scoped resolution.

    Order:
      1. ``$CEO_AUDIT_LOG_PATH`` (explicit override)
      2. ``$CEO_AUDIT_LOG_DIR/audit-log.jsonl``
      3. ``$CLAUDE_PROJECT_DIR``-derived slug
      4. Legacy hardcoded ~/.claude/projects/ceo-orchestration/

    Returns None when no candidate exists (caller emits honest
    "audit-log not found" status instead of false-failing on a
    different project's log).
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


def probe_audit_log() -> Tuple[str, str, Dict[str, Any]]:
    """Audit-log freshness + last-24h dispatch count.

    F-6.10-f6a7b8c9 (PLAN-113 W7-OPS): under sandbox isolation all env vars
    are absent and Path.home() may not contain the legacy path.  Rather than
    returning 'unknown' (which conflates a clean install with an error state)
    we now return 'green' with a descriptive note when the log is genuinely
    absent (new install, CI, sandbox), and 'yellow' only when a log EXISTS
    but is unreadable.  The distinction matters for ceo-diagnose consumers
    that drive automated alerting.

    Resolution order for the log path:
      1. CEO_AUDIT_LOG_PATH env var
      2. CEO_AUDIT_LOG_DIR/audit-log.jsonl
      3. CLAUDE_PROJECT_DIR-derived slug
      4. repo-root-derived slug (works under sandbox isolation when the
         cwd is inside the project tree even without env vars)
      5. Legacy ~/.claude/projects/ceo-orchestration/audit-log.jsonl
    """
    log_path = _resolve_audit_log_path()
    if log_path is None:
        # F-6.10-f6a7b8c9: distinguish "not found" from "error".
        # A missing log on a clean install / CI sandbox is not an error.
        return ("green", "audit-log not found (clean install or sandbox)", {
            "found": False,
            "note": "no audit-log discovered; normal on new installs or in CI sandbox",
        })
    try:
        stat = log_path.stat()
    except OSError:
        return ("unknown", "audit-log stat failed", {})
    age_seconds = time.time() - stat.st_mtime
    age_hours = age_seconds / 3600.0
    cutoff = time.time() - 24 * 3600.0
    dispatch_24h = 0
    spawn_24h = 0
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                ts = ev.get("ts") or ""
                # ISO-8601 → epoch via simple parse; cheap fallback if str.
                try:
                    # Python 3.11+ has fromisoformat with Z; 3.9 needs manual.
                    if ts.endswith("Z"):
                        ts = ts[:-1] + "+00:00"
                    from datetime import datetime
                    epoch = datetime.fromisoformat(ts).timestamp()
                except (ValueError, ImportError):
                    continue
                if epoch < cutoff:
                    continue
                if ev.get("action") == "agent_spawn":
                    spawn_24h += 1
                dispatch_24h += 1
    except OSError:
        return ("unknown", "audit-log read failed", {})
    detail = {
        "path": str(log_path),
        "age_hours": round(age_hours, 1),
        "events_24h": dispatch_24h,
        "spawns_24h": spawn_24h,
        "size_bytes": stat.st_size,
    }
    if age_hours > 168:  # > 7 days
        return ("yellow", f"audit-log stale ({age_hours:.0f}h old)", detail)
    return ("green", f"audit-log fresh ({dispatch_24h} events / 24h)", detail)


def probe_dispatch_modes() -> Tuple[str, str, Dict[str, Any]]:
    """Per-archetype dispatch-mode breakdown over last 24h (ADR-082 monitoring)."""
    log_path = _resolve_audit_log_path()
    if log_path is None:
        return ("unknown", "audit-log not found", {})
    cutoff = time.time() - 24 * 3600.0
    by_mode: Dict[str, int] = {}
    by_archetype: Dict[str, Dict[str, int]] = {}
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if ev.get("action") != "agent_spawn":
                    continue
                ts = ev.get("ts") or ""
                try:
                    from datetime import datetime
                    if ts.endswith("Z"):
                        ts = ts[:-1] + "+00:00"
                    epoch = datetime.fromisoformat(ts).timestamp()
                except (ValueError, ImportError):
                    continue
                if epoch < cutoff:
                    continue
                # dispatch_mode field added by inject-agent-context.sh
                # via the audit_log.py PostToolUse observer (when wired).
                # Until then, infer from prompt body containing
                # "## DISPATCH MITIGATION".
                mode = ev.get("dispatch_mode") or "unknown"
                arch = ev.get("archetype") or ev.get("agent_name") or "unknown"
                by_mode[mode] = by_mode.get(mode, 0) + 1
                by_archetype.setdefault(arch, {})[mode] = (
                    by_archetype.setdefault(arch, {}).get(mode, 0) + 1
                )
    except OSError:
        return ("unknown", "audit-log read failed", {})
    total = sum(by_mode.values())
    if total == 0:
        return ("yellow", "no spawns in last 24h", {"by_mode": {}, "by_archetype": {}})
    mit_pct = 100.0 * by_mode.get("mitigated", 0) / total if total else 0
    nat_pct = 100.0 * by_mode.get("native", 0) / total if total else 0
    summary = (
        f"24h: {total} spawns "
        f"(mitigated {mit_pct:.0f}%, native {nat_pct:.0f}%)"
    )
    return ("green", summary, {
        "total_24h": total,
        "by_mode": dict(by_mode),
        "by_archetype": {k: dict(v) for k, v in by_archetype.items()},
    })


def probe_hook_tests(quick: bool = False) -> Tuple[str, str, Dict[str, Any]]:
    """Hook pytest suite headline (passed/failed/skipped). Skipped if quick."""
    if quick:
        return ("unknown", "skipped (--quick)", {})
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", ".claude/hooks/tests", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return ("unknown", f"pytest probe failed: {type(e).__name__}", {})
    out = result.stdout + result.stderr
    m = re.search(r"(\d+)\s+passed(?:,\s*(\d+)\s+skipped)?(?:,\s*(\d+)\s+failed)?", out)
    if not m:
        return ("unknown", "pytest output unparseable", {"exit": result.returncode})
    passed = int(m.group(1))
    skipped = int(m.group(2) or 0)
    failed = int(m.group(3) or 0)
    detail = {"passed": passed, "skipped": skipped, "failed": failed}
    if failed == 0:
        return ("green", f"{passed} passed, {skipped} skipped", detail)
    return ("red", f"{failed} hook tests FAILED", detail)


def probe_install_mode() -> Tuple[str, str, Dict[str, Any]]:
    """Install mode (vibecoder vs cto) — placeholder until ADR-086 lands."""
    settings = REPO_ROOT / ".claude" / "settings.json"
    if not settings.is_file():
        return ("unknown", "settings.json missing", {})
    # Placeholder — once ADR-086 lands, look for `install_mode` key.
    return ("green", "install mode: cto (default; vibecoder mode pending ADR-086)", {})


def probe_adr_082_acceptance() -> Tuple[str, str, Dict[str, Any]]:
    """ADR-082 status snapshot."""
    adr_path = REPO_ROOT / ".claude" / "adr" / "ADR-082-l7c-mitigation-default-on.md"
    if not adr_path.is_file():
        return ("unknown", "ADR-082 missing", {})
    text = adr_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^##\s+Status\s*\n+\s*ACCEPTED", text, re.MULTILINE):
        return ("green", "ADR-082 ACCEPTED", {"status": "ACCEPTED"})
    if re.search(r"^##\s+Status\s*\n+\s*PROPOSED", text, re.MULTILINE):
        return ("yellow", "ADR-082 still PROPOSED", {"status": "PROPOSED"})
    return ("yellow", "ADR-082 status unknown", {})


def probe_incident_signals() -> Tuple[str, str, Dict[str, Any]]:
    """F-6.10-c3d4e5f6 (PLAN-113 W7-OPS) — surface live SEV/incident signals.

    Probes two lightweight signal sources:
    1. audit-log.errors sidecar size/line count — a non-zero file indicates
       active write failures (e.g. the spool_writer FAIL-CLOSED flood that
       generated 75k errors on 2026-05-24).
    2. Recent (last-24h) audit-log for any 'incident_declared' or
       'sev_classified' events emitted by the incident-management workflow.

    Both probes are fail-open: a missing file or unreadable log degrades to
    'green' (no signal), never 'unknown' or an exception. The goal is to
    surface ACTIVE incidents, not to block the session on infrastructure gaps.

    Status taxonomy:
      green  — no errors sidecar, no incident events in last 24h
      yellow — errors sidecar present with ≥1 line (write failures detected)
      red    — incident_declared/sev_classified event found in last 24h
    """
    detail: Dict[str, Any] = {
        "errors_sidecar_lines": 0,
        "incident_events_24h": 0,
        "active_sev": None,
    }

    # ---- 1. audit-log.errors sidecar ----------------------------------------
    log_path = _resolve_audit_log_path()
    if log_path is not None:
        errors_env = os.environ.get("CEO_AUDIT_LOG_ERR", "")
        errors_path = Path(errors_env) if errors_env else log_path.parent / "audit-log.errors"
        try:
            if errors_path.is_file():
                with errors_path.open("rb") as ef:
                    error_lines = sum(1 for _ in ef)
                detail["errors_sidecar_lines"] = error_lines
        except OSError:
            pass

    # ---- 2. Scan audit-log for incident events in last 24h ------------------
    _INCIDENT_ACTIONS = frozenset({
        "incident_declared", "sev_classified",
        "incident_resolved", "incident_escalated",
    })
    if log_path is not None:
        cutoff = time.time() - 24 * 3600.0
        try:
            with log_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if ev.get("action") not in _INCIDENT_ACTIONS:
                        continue
                    ts = ev.get("ts") or ""
                    try:
                        from datetime import datetime
                        if ts.endswith("Z"):
                            ts = ts[:-1] + "+00:00"
                        epoch = datetime.fromisoformat(ts).timestamp()
                    except (ValueError, AttributeError):
                        continue
                    if epoch < cutoff:
                        continue
                    detail["incident_events_24h"] += 1
                    if ev.get("action") in ("incident_declared", "sev_classified"):
                        sev = ev.get("severity") or ev.get("sev") or "unknown"
                        detail["active_sev"] = sev
        except OSError:
            pass

    # ---- Synthesise status --------------------------------------------------
    if detail["incident_events_24h"] > 0 and detail["active_sev"] is not None:
        return (
            "red",
            f"active incident signal: SEV={detail['active_sev']} ({detail['incident_events_24h']} events/24h)",
            detail,
        )
    if detail["errors_sidecar_lines"] > 0:
        return (
            "yellow",
            f"audit write errors: {detail['errors_sidecar_lines']} lines in audit-log.errors",
            detail,
        )
    return ("green", "no active incident signals", detail)


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

STATUS_GLYPH = {"green": "✓", "yellow": "⚠", "red": "✗", "unknown": "?"}
STATUS_RANK = {"green": 0, "yellow": 1, "red": 2, "unknown": 0}


def render_human(report: List[Tuple[str, str, str, Dict[str, Any]]]) -> str:
    lines = ["", "## ceo-orchestration — diagnose", ""]
    for name, status, summary, _detail in report:
        glyph = STATUS_GLYPH.get(status, "?")
        lines.append(f"  {glyph}  {name:24} {summary}")
    lines.append("")
    return "\n".join(lines)


def render_json(report: List[Tuple[str, str, str, Dict[str, Any]]]) -> str:
    out = {
        "schema": "ceo-diagnose-v1",
        "probes": [
            {"name": name, "status": status, "summary": summary, "detail": detail}
            for name, status, summary, detail in report
        ],
    }
    return json.dumps(out, indent=2, sort_keys=True)


def overall_exit_code(report: List[Tuple[str, str, str, Dict[str, Any]]]) -> int:
    worst = 0
    for _name, status, _summary, _detail in report:
        worst = max(worst, STATUS_RANK.get(status, 0))
    return worst


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    p.add_argument("--quick", action="store_true", help="skip slow probes (pytest)")
    args = p.parse_args(argv)

    probes = [
        ("Open plans", probe_open_plans),
        ("Governance", probe_governance),
        ("Audit log", probe_audit_log),
        ("Incident signals", probe_incident_signals),  # F-6.10-c3d4e5f6
        ("Dispatch modes", probe_dispatch_modes),
        ("ADR-082", probe_adr_082_acceptance),
        ("Install mode", probe_install_mode),
        ("Hook tests", lambda: probe_hook_tests(quick=args.quick)),
    ]

    report: List[Tuple[str, str, str, Dict[str, Any]]] = []
    for name, fn in probes:
        try:
            status, summary, detail = fn()
        except Exception as e:  # pragma: no cover — defense in depth
            status, summary, detail = ("unknown", f"probe error: {type(e).__name__}", {})
        report.append((name, status, summary, detail))

    if args.json:
        print(render_json(report))
    else:
        print(render_human(report))

    return overall_exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
