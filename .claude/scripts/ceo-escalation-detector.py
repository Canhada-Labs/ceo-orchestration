#!/usr/bin/env python3
"""ceo-escalation-detector — PLAN-048 Phase 2 harness.

Standalone stdlib CLI that scans a session's audit-log.jsonl slice for
6 escalation signals defined in PLAN-048 §Phase 2. Designed to run in
both modes:

  * **observe-only** (baseline period, CEO = Opus 4.7) — detect which
    turns WOULD have triggered an Opus re-dispatch under downshifted
    CEO. Produces `experiment-metrics.jsonl` records.
  * **active** (experiment period, CEO = Sonnet 4.6 via
    ``CEO_MODEL_DOWNSHIFT=1``) — emit incident records consumed by the
    future Stop hook (staged) to request one-time Opus boost on the
    next turn.

The detector is **intentionally audit-log-driven** (not hook-resident):
it is a post-session forensic report + next-turn advisor. The runtime
escalation mechanism (next-turn Opus boost) is a staged deliverable
pending Owner sentinel (see ``staged-code/escalation_signals.py``).

**Six signals** (PLAN-048 plan §Phase 2 lines 114-124):

  1. ``gate_skip`` — Session missed Gate 1-3 reading (no CLAUDE.md +
     PROTOCOL.md reads in the first 10 events of a non-trivial session).
  2. ``canonical_edit_block`` — Canonical-edit sentinel fired
     (``response_kind: block_canonical_edit`` OR action
     ``check_canonical_edit_block``).
  3. ``debate_skip_l3`` — L3+ plan executed spawns without a prior
     ``debate_event`` with matching ``plan_id``.
  4. ``strike_counter`` — ``strike_events`` reached ``>= 3`` cumulative
     in the session (3-strike policy trigger).
  5. ``veto_non_opus`` — ``agent_spawn`` targeting a VETO role
     (code-reviewer, security-engineer) with ``model`` ≠ ``claude-opus-*``.
  6. ``shortcut_language`` — Advisory pattern match on recent
     ``prompt_submitted`` / output scan events (``I'll just``,
     ``quick fix``, ``skip debate``, ``trust me``). Advisory-only;
     never blocks.

**Fail-open** — any parse error / IO error logs a breadcrumb to stderr
and returns exit 0 with empty incident list. Detection must never block
the session.

Usage::

    ceo-escalation-detector.py                          # scan current session
    ceo-escalation-detector.py --session-id <id>        # explicit id
    ceo-escalation-detector.py --format markdown        # human-readable table
    ceo-escalation-detector.py --format jsonl           # one incident per line
    ceo-escalation-detector.py --format count           # signal totals only
    ceo-escalation-detector.py --audit-log /path.jsonl  # custom audit path
    ceo-escalation-detector.py --plans-dir .claude/plans # for L3+ lookup
    ceo-escalation-detector.py --emit-metrics           # append an
                                                        # experiment-metrics
                                                        # record to --metrics-out

Exit codes::

    0 — scan completed (incidents may be present; not an error)
    2 — fatal config error (missing audit-log + no fallback)

Env::

    CEO_ESCALATION_FORMAT   default output format (json|jsonl|markdown|count)
    CEO_ESCALATION_QUIET    when set, suppress stderr breadcrumbs

Stdlib-only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_SCHEMA_VERSION = "plan-048-experiment-metrics.v1"

# VETO roles that MUST be Opus 4.8 per ADR-142 hardcoded floor (was 4.7/ADR-052).
_VETO_ROLES = frozenset({"code-reviewer", "security-engineer"})

# Model prefix that satisfies the VETO floor.
# ADR-149: floor-tier model FAMILIES — keep bit-equivalent with
# _lib/escalation_signals.py (staged-copy contract).
_FLOOR_TIER_PREFIXES = ("claude-opus-", "claude-fable-")
_OPUS_PREFIX = _FLOOR_TIER_PREFIXES[0]  # legacy name, kept for back-compat

# Gate-1/2 file reads the protocol demands.
_GATE_1_FILES = (
    "CLAUDE.md",
    "PROTOCOL.md",
)

# Shortcut-language phrases (advisory). Case-insensitive substring match.
# Curated for low false-positive density — phrases a careful CEO would
# almost never emit in reasoned prose.
_SHORTCUT_PHRASES = (
    "i'll just",
    "quick fix",
    "skip debate",
    "trust me",
    "let me just",
    "one-liner",
    "no need to test",
)

# L3+ plan frontmatter values recognized as warranting debate.
_L3_PLUS_LEVELS = frozenset({"L3", "L3+", "L4", "L4+", "L5"})


def _log_breadcrumb(msg: str) -> None:
    """Write a stderr breadcrumb unless CEO_ESCALATION_QUIET is set."""
    if os.environ.get("CEO_ESCALATION_QUIET"):
        return
    print(f"ceo-escalation-detector: {msg}", file=sys.stderr)


def default_audit_log_path() -> Path:
    """Resolve the per-project audit-log path."""
    home = Path.home()
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def default_plans_dir() -> Path:
    """Resolve .claude/plans/ relative to CWD."""
    return Path.cwd() / ".claude" / "plans"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file; skip malformed lines silently."""
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    records.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        _log_breadcrumb(f"load_jsonl({path}) failed: {exc}")
        return []
    return records


def auto_detect_recent_session(records: List[Dict[str, Any]]) -> Optional[str]:
    """Return the session_id with the most events in the tail."""
    counts: Counter[str] = Counter()
    for r in records:
        sid = r.get("session_id") or ""
        if sid and sid not in ("unknown", "t", "f"):
            counts[sid] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def filter_by_session(
    records: List[Dict[str, Any]], session_id: str
) -> List[Dict[str, Any]]:
    """Keep only events for the given session_id."""
    return [r for r in records if r.get("session_id") == session_id]


def _event_ts(r: Dict[str, Any]) -> str:
    """Best-effort ts extraction."""
    return str(r.get("ts") or r.get("timestamp") or "")


def _extract_plan_level(plan_md_path: Path) -> Optional[str]:
    """Parse `level:` from plan frontmatter. None if unreadable."""
    if not plan_md_path.is_file():
        return None
    try:
        with plan_md_path.open("r", encoding="utf-8") as fh:
            in_front = False
            for ln in fh:
                if ln.strip() == "---":
                    if not in_front:
                        in_front = True
                        continue
                    break
                if in_front:
                    m = re.match(r"^\s*level\s*:\s*(.+?)\s*$", ln)
                    if m:
                        return m.group(1).strip().strip("'\"")
    except OSError:
        return None
    return None


def _lookup_plan_level(plan_id: str, plans_dir: Path) -> Optional[str]:
    """Resolve PLAN-NNN → level via frontmatter.

    Tries ``plans_dir/PLAN-NNN-*.md`` glob (monotonic slug pattern).
    """
    if not plans_dir.is_dir():
        return None
    for candidate in sorted(plans_dir.glob(f"{plan_id}-*.md")):
        lvl = _extract_plan_level(candidate)
        if lvl:
            return lvl
    return None


def detect_gate_skip(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 1 — Gate 1-3 reading skipped.

    Heuristic: scan the first 15 events of the session. If we see
    non-trivial work (``agent_spawn``, ``plan_transition``, or
    ``check_canonical_edit_*``) before any Read action on CLAUDE.md or
    PROTOCOL.md, flag.

    The audit-log does not emit file-read events by default, so the
    check is conservative: we look for `session_start` tagged events
    that include a ``files_read`` list OR `prompt_submitted` with
    a ``read_paths`` annotation. If neither surface exists, we emit a
    low-severity advisory incident rather than silently pass (so
    absence of instrumentation does not falsely mark compliance).
    """
    if not events:
        return []
    head = events[:15]
    triggered_work = False
    read_protocol = False
    first_work_ts = ""
    for e in head:
        act = e.get("action") or ""
        if act in {"agent_spawn", "plan_transition", "canonical_edit_blocked"}:
            triggered_work = True
            if not first_work_ts:
                first_work_ts = _event_ts(e)
        files_hint = e.get("files_read") or e.get("read_paths") or []
        if isinstance(files_hint, str):
            files_hint = [files_hint]
        for fh in files_hint:
            for gf in _GATE_1_FILES:
                if gf in str(fh):
                    read_protocol = True
                    break
    if triggered_work and not read_protocol:
        return [
            {
                "signal": "gate_skip",
                "severity": "high",
                "ts": first_work_ts,
                "details": {
                    "hint": (
                        "first 15 events show work (spawn/plan_transition) "
                        "but no Gate-1 read of CLAUDE.md/PROTOCOL.md captured"
                    ),
                    "head_actions": [e.get("action") for e in head],
                },
            }
        ]
    return []


def detect_canonical_edit_block(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 2 — canonical-edit sentinel violations."""
    out: List[Dict[str, Any]] = []
    for e in events:
        act = e.get("action") or ""
        rk = e.get("response_kind") or ""
        if (
            act in {"canonical_edit_blocked", "check_canonical_edit_block"}
            or rk == "block_canonical_edit"
        ):
            out.append(
                {
                    "signal": "canonical_edit_block",
                    "severity": "high",
                    "ts": _event_ts(e),
                    "details": {
                        "action": act,
                        "response_kind": rk,
                        "path": e.get("path") or e.get("tool_file_path"),
                    },
                }
            )
    return out


def detect_debate_skip_l3(
    events: List[Dict[str, Any]],
    plans_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Signal 3 — L3+ plan dispatched execution spawns before any debate.

    For each plan_id appearing in a ``plan_transition`` to ``executing``
    or any ``agent_spawn`` with ``plan_id`` set, check if the plan is
    L3+ (via frontmatter lookup) AND if there is a ``debate_event``
    event with the same plan_id anywhere in the session *before* the
    first execution-phase activity. If no prior debate → flag.
    """
    if not events:
        return []
    plans_dir = plans_dir or default_plans_dir()
    debate_by_plan: Dict[str, str] = {}
    first_exec_by_plan: Dict[str, str] = {}
    for e in events:
        pid = (e.get("plan_id") or "").strip()
        if not pid:
            continue
        act = e.get("action") or ""
        ts = _event_ts(e)
        if act == "debate_event" and pid not in debate_by_plan:
            debate_by_plan[pid] = ts
        if act in {"agent_spawn", "plan_transition"} and pid not in first_exec_by_plan:
            first_exec_by_plan[pid] = ts
    out: List[Dict[str, Any]] = []
    for pid, exec_ts in first_exec_by_plan.items():
        level = _lookup_plan_level(pid, plans_dir)
        if level not in _L3_PLUS_LEVELS:
            continue
        debate_ts = debate_by_plan.get(pid)
        if not debate_ts or debate_ts > exec_ts:
            out.append(
                {
                    "signal": "debate_skip_l3",
                    "severity": "high",
                    "ts": exec_ts,
                    "details": {
                        "plan_id": pid,
                        "level": level,
                        "first_exec_ts": exec_ts,
                        "debate_ts": debate_ts,
                    },
                }
            )
    return out


def detect_strike_counter(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 4 — 3-strike counter trigger (cumulative >=3 strike_events)."""
    count = 0
    out: List[Dict[str, Any]] = []
    for e in events:
        if (e.get("action") or "") == "strike_recorded":
            count += 1
            if count >= 3:
                out.append(
                    {
                        "signal": "strike_counter",
                        "severity": "high",
                        "ts": _event_ts(e),
                        "details": {
                            "cumulative_strikes": count,
                            "agent": e.get("agent") or e.get("subagent_type"),
                        },
                    }
                )
                break
    return out


def _is_floor_tier(model: str) -> bool:
    """ADR-149: True when ``model`` belongs to a floor-tier family."""
    return bool(model) and model.lower().startswith(_FLOOR_TIER_PREFIXES)


# Legacy alias — existing callers/tests import _is_opus by name.
_is_opus = _is_floor_tier


def detect_veto_non_opus(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 5 — VETO-role spawn with non-Opus model (ADR-052 floor)."""
    out: List[Dict[str, Any]] = []
    for e in events:
        if (e.get("action") or "") != "agent_spawn":
            continue
        role = (
            e.get("subagent_type")
            or e.get("agent_type")
            or e.get("agent")
            or ""
        )
        if role not in _VETO_ROLES:
            continue
        model = e.get("model") or e.get("model_id") or ""
        if not _is_floor_tier(model):
            out.append(
                {
                    "signal": "veto_non_opus",
                    "severity": "high",
                    "ts": _event_ts(e),
                    "details": {
                        "role": role,
                        "model": model or "<unset>",
                        "expected_prefix": "|".join(_FLOOR_TIER_PREFIXES),
                    },
                }
            )
    return out


def detect_shortcut_language(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 6 — advisory pattern match on prompt text + output scans.

    This is **advisory-only** (severity: low). False-positive rate is
    higher than other signals because we scan free text. We look at
    ``prompt_submitted`` events (user+CEO turn text snippets if the
    hook captures them) and ``output_scan_finding`` events (redactions
    may include shortcut phrases).
    """
    out: List[Dict[str, Any]] = []
    for e in events:
        act = e.get("action") or ""
        if act not in {"prompt_submitted", "output_scan_finding"}:
            continue
        blob = " ".join(
            str(e.get(k) or "")
            for k in ("preview", "text_preview", "prompt_preview", "content_preview")
        ).lower()
        if not blob:
            continue
        hits = [p for p in _SHORTCUT_PHRASES if p in blob]
        if hits:
            out.append(
                {
                    "signal": "shortcut_language",
                    "severity": "low",
                    "ts": _event_ts(e),
                    "details": {
                        "phrases": hits,
                        "source_action": act,
                    },
                }
            )
    return out


_DETECTORS = (
    detect_gate_skip,
    detect_canonical_edit_block,
    detect_debate_skip_l3,
    detect_strike_counter,
    detect_veto_non_opus,
    detect_shortcut_language,
)


def detect_all(
    events: List[Dict[str, Any]],
    plans_dir: Optional[Path] = None,
    session_id: str = "",
    project: str = "",
) -> List[Dict[str, Any]]:
    """Run every detector in a fail-open loop and aggregate incidents.

    Emits ``escalation_detected`` for each incident via audit_emit
    (best-effort, fail-open).
    """
    out: List[Dict[str, Any]] = []
    for fn in _DETECTORS:
        try:
            if fn is detect_debate_skip_l3:
                out.extend(fn(events, plans_dir))  # type: ignore[arg-type]
            else:
                out.extend(fn(events))  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover — fail-open invariant
            _log_breadcrumb(f"detector {fn.__name__} failed: {exc}")

    # PLAN-113 WIRE-AUDIT: emit escalation_detected for each incident.
    if session_id and out:
        try:
            import sys as _sys
            _hooks_dir = str(Path(__file__).resolve().parent.parent / "hooks")
            if _hooks_dir not in _sys.path:
                _sys.path.insert(0, _hooks_dir)
            from _lib import audit_emit as _ae  # type: ignore[import]
            for inc in out:
                _ae.emit_escalation_detected(
                    signal=inc.get("signal", ""),
                    severity=inc.get("severity", ""),
                    plan_id=(inc.get("details") or {}).get("plan_id", ""),
                    session_id=session_id,
                    project=project,
                )
        except Exception as _e:  # pragma: no cover
            _log_breadcrumb(f"emit_escalation_detected failed: {_e}")

    return out


def summarize(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute per-signal counts + highest severity summary."""
    by_signal: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    for inc in incidents:
        by_signal[inc["signal"]] += 1
        by_severity[inc["severity"]] += 1
    return {
        "total_incidents": len(incidents),
        "by_signal": dict(by_signal),
        "by_severity": dict(by_severity),
    }


def build_experiment_record(
    session_id: str,
    incidents: List[Dict[str, Any]],
    ceo_model: str,
    session_tag_primary: str,
    notes: str,
) -> Dict[str, Any]:
    """Assemble an experiment-metrics v1 record (extends baseline schema)."""
    summ = summarize(incidents)
    return {
        "schema": _SCHEMA_VERSION,
        "session_id": session_id,
        "ceo_model": ceo_model,
        "session_tag_primary": session_tag_primary,
        "escalation_events_count": summ["total_incidents"],
        "escalation_by_signal": summ["by_signal"],
        "escalation_by_severity": summ["by_severity"],
        "incidents": incidents,
        "collected_at_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": notes,
    }


def format_markdown(incidents: List[Dict[str, Any]]) -> str:
    """Render incidents as a grouped markdown table."""
    if not incidents:
        return "_No escalation incidents detected._\n"
    by_signal: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for inc in incidents:
        by_signal[inc["signal"]].append(inc)
    out: List[str] = ["# CEO Escalation Incidents\n"]
    summ = summarize(incidents)
    out.append(f"**Total:** {summ['total_incidents']} incident(s).\n")
    out.append("")
    for sig in sorted(by_signal):
        rows = by_signal[sig]
        sev = rows[0]["severity"]
        out.append(f"## `{sig}` ({len(rows)} × severity={sev})\n")
        out.append("| ts | details |")
        out.append("|---|---|")
        for inc in rows:
            det = json.dumps(inc["details"], ensure_ascii=False, sort_keys=True)
            out.append(f"| {inc['ts']} | `{det}` |")
        out.append("")
    return "\n".join(out) + "\n"


def format_count(incidents: List[Dict[str, Any]]) -> str:
    """Render counts-only output for quick inspection."""
    summ = summarize(incidents)
    lines = [f"total={summ['total_incidents']}"]
    for sig, n in sorted(summ["by_signal"].items()):
        lines.append(f"{sig}={n}")
    for sev, n in sorted(summ["by_severity"].items()):
        lines.append(f"severity_{sev}={n}")
    return "\n".join(lines) + "\n"


def format_jsonl(incidents: List[Dict[str, Any]]) -> str:
    """Render one JSON object per line."""
    return (
        "\n".join(json.dumps(inc, ensure_ascii=False, sort_keys=True) for inc in incidents)
        + ("\n" if incidents else "")
    )


def format_json(incidents: List[Dict[str, Any]]) -> str:
    """Render single JSON object summary + incidents."""
    return json.dumps(
        {
            "summary": summarize(incidents),
            "incidents": incidents,
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


_FORMATTERS = {
    "json": format_json,
    "jsonl": format_jsonl,
    "markdown": format_markdown,
    "count": format_count,
}


def build_parser() -> argparse.ArgumentParser:
    """Build argparse CLI surface."""
    p = argparse.ArgumentParser(
        prog="ceo-escalation-detector",
        description=(
            "Scan a CEO session's audit-log slice for 6 escalation signals "
            "(PLAN-048 Phase 2 harness)."
        ),
    )
    p.add_argument(
        "--session-id",
        default="current",
        help="Session id to scan ('current' auto-detects most recent)",
    )
    p.add_argument(
        "--audit-log",
        default=str(default_audit_log_path()),
        help="Path to audit-log.jsonl",
    )
    p.add_argument(
        "--plans-dir",
        default=str(default_plans_dir()),
        help="Path to .claude/plans (needed for L3+ debate-skip lookup)",
    )
    p.add_argument(
        "--format",
        default=os.environ.get("CEO_ESCALATION_FORMAT", "markdown"),
        choices=sorted(_FORMATTERS),
        help="Output format (default: markdown; env: CEO_ESCALATION_FORMAT)",
    )
    p.add_argument(
        "--emit-metrics",
        action="store_true",
        help="Append an experiment-metrics record to --metrics-out",
    )
    p.add_argument(
        "--metrics-out",
        default=str(
            Path(__file__).resolve().parent.parent
            / "plans"
            / "PLAN-048"
            / "experiment-metrics.jsonl"
        ),
        help="Destination JSONL for experiment-metrics records",
    )
    p.add_argument(
        "--ceo-model",
        default=os.environ.get("CEO_MODEL_ID", "claude-opus-4-8[1m]"),
        help="CEO model for metrics record (env: CEO_MODEL_ID)",
    )
    p.add_argument(
        "--session-tag-primary",
        default="unlabeled",
        help="Session tag for metrics record",
    )
    p.add_argument(
        "--notes",
        default="",
        help="Free-form notes captured with the metrics record",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    audit_path = Path(args.audit_log)
    plans_dir = Path(args.plans_dir)

    all_events = load_jsonl(audit_path)
    session_id = args.session_id
    if session_id == "current":
        detected = auto_detect_recent_session(all_events)
        if not detected:
            _log_breadcrumb(
                "could not auto-detect session_id; audit-log empty. "
                "Pass --session-id explicitly."
            )
            # Fail-open: emit empty incident set + exit 0
            print(_FORMATTERS[args.format]([]), end="")
            return 0
        session_id = detected

    events = filter_by_session(all_events, session_id)
    project = os.environ.get("CLAUDE_PROJECT_DIR", "")
    incidents = detect_all(
        events, plans_dir=plans_dir,
        session_id=session_id, project=project,
    )

    print(_FORMATTERS[args.format](incidents), end="")

    # PLAN-113 WIRE-AUDIT: emit escalation_dispatched / escalation_suppressed /
    # escalation_baseline_recorded based on mode.
    _is_active_mode = os.environ.get("CEO_MODEL_DOWNSHIFT") == "1"
    try:
        import sys as _sys
        _hooks_dir = str(Path(__file__).resolve().parent.parent / "hooks")
        if _hooks_dir not in _sys.path:
            _sys.path.insert(0, _hooks_dir)
        from _lib import audit_emit as _ae  # type: ignore[import]
        if _is_active_mode and incidents:
            # Active mode: at least one signal would trigger Opus re-dispatch.
            _ae.emit_escalation_dispatched(
                signal=incidents[0].get("signal", ""),
                target_model="claude-opus-4-8",
                plan_id=(incidents[0].get("details") or {}).get("plan_id", ""),
                session_id=session_id,
                project=project,
            )
        elif _is_active_mode and not incidents:
            # Active mode + no incidents → nothing to suppress; still audit-trail.
            _ae.emit_escalation_suppressed(
                signal="none",
                reason_code="no_incidents_detected",
                session_id=session_id,
                project=project,
            )
        elif not _is_active_mode:
            # Baseline (observe-only) mode.
            _ae.emit_escalation_baseline_recorded(
                signals_count=len(incidents),
                session_id=session_id,
                project=project,
            )
    except Exception as _e:  # pragma: no cover
        _log_breadcrumb(f"escalation audit-emit failed: {_e}")

    if args.emit_metrics:
        rec = build_experiment_record(
            session_id=session_id,
            incidents=incidents,
            ceo_model=args.ceo_model,
            session_tag_primary=args.session_tag_primary,
            notes=args.notes or "auto-captured via ceo-escalation-detector",
        )
        out_path = Path(args.metrics_out)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            _log_breadcrumb(f"appended experiment-metrics record to {out_path}")
        except OSError as exc:
            _log_breadcrumb(f"--emit-metrics append failed ({exc}); fail-open")

    return 0


if __name__ == "__main__":
    sys.exit(main())
