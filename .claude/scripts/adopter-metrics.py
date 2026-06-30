#!/usr/bin/env python3
"""adopter-metrics — weekly metrics report for a ceo-orchestration adopter project.

Stdlib-only CLI that reads a target adopter's `audit-log.jsonl` and emits a
Markdown report (default) or JSON (via ``--json``) covering the 7 metrics
defined in PLAN-015 §0.1:

    1. Sessions count — distinct ``session_id`` values in window
    2. Spawns total — ``action == "agent_spawn"`` count
    3. Veto rate — vetoes / (spawns + vetoes); null if denom == 0
    4. Task completion ratio — ``to_status == "done"`` /
       ``to_status in {done, abandoned}``; null if no transitions
    5. Tokens actual vs predicted — aggregated ``tokens_total`` (or
       ``tokens_in + tokens_out``) from ``agent_spawn`` compared against
       ``prediction_queried`` bucket midpoints
    6. Custom skills count — skills under target ``.claude/skills/``
       whose basename is NOT in the framework baseline
    7. ADRs activated — distinct ``ADR-NNN`` tokens mentioned in
       ``desc_preview`` or ``reason_preview`` fields

Public CLI contract (PLAN-015 §0.1):

    python3 adopter-metrics.py \\
      --adopter-name adopter-1 \\
      --audit-log <path> \\
      --window {7d|14d|30d|all} \\
      --skills-baseline <dir> \\
      --output <path>

Optional flags:
    --json                 emit JSON to stdout instead of markdown
    --now <iso>            override "now" for deterministic tests

Exit codes:
    0 — success (empty audit-log is a valid report)
    1 — bad arguments OR baseline missing OR output parent cannot be created
    2 — audit-log exists but cannot be read (permissions)
"""

from __future__ import annotations

import argparse
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

_WINDOW_DAYS: Dict[str, Optional[int]] = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "all": None,
}

# Match ADR-NNN where N is exactly 3 digits. Word-boundary anchored so
# ADR-9999 (4 digits) and ADR-12 (2 digits) are excluded.
_ADR_PATTERN = re.compile(r"\bADR-\d{3}\b")

_ISO_SECOND_FMT = "%Y-%m-%dT%H:%M:%SZ"


# ---------------------------------------------------------------------------
# JSONL reader (adapted from audit-query.py:92-130 — tolerant of malformed lines)
# ---------------------------------------------------------------------------


def read_entries(
    path: Path,
    *,
    warn_stream=None,
) -> Iterator[Dict[str, Any]]:
    """Yield parsed JSON entries from the given log path, streaming.

    Malformed lines are skipped with a breadcrumb to warn_stream.
    Non-dict entries are ignored. If the file is missing, nothing is
    yielded (no exception — callers treat missing file as empty log).
    """
    if warn_stream is None:
        warn_stream = sys.stderr
    if not path.is_file():
        return
    try:
        f = open(path, "r", encoding="utf-8", errors="replace")
    except OSError as e:
        print(
            f"[adopter-metrics] WARN: cannot read {path}: {e}",
            file=warn_stream,
        )
        return
    try:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as e:
                print(
                    f"[adopter-metrics] WARN: {path}:{lineno}: "
                    f"skipping malformed JSONL ({e.msg})",
                    file=warn_stream,
                )
                continue
            if not isinstance(entry, dict):
                continue
            yield entry
    finally:
        f.close()


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp (with trailing Z or explicit offset).

    Returns a timezone-aware UTC datetime, or None on parse failure.
    """
    if not ts or not isinstance(ts, str):
        return None
    candidate = ts
    # Handle trailing Z (fromisoformat before 3.11 doesn't accept it)
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_now(now_override: Optional[str]) -> datetime:
    if now_override:
        parsed = _parse_iso(now_override)
        if parsed is None:
            raise ValueError(f"--now value is not ISO-8601: {now_override}")
        return parsed
    return datetime.now(timezone.utc)


def _window_bounds(
    window: str, now: datetime
) -> Tuple[Optional[datetime], datetime]:
    """Return (start, end) for a window relative to `now`.

    `window == "all"` → start is None (no lower bound).
    """
    end = now
    days = _WINDOW_DAYS.get(window)
    if days is None:
        return None, end
    return end - timedelta(days=days), end


def _in_window(
    ts_str: str,
    start: Optional[datetime],
    end: datetime,
) -> bool:
    """Return True iff the ts string falls in [start, end].

    Malformed or missing ts falls back to being included when start is
    None (all), excluded otherwise.

    PLAN-025 F-scripts-001 — previous implementation CLAMPED future-dated
    events to ``end`` then checked ``parsed >= start``, which caused
    future-fabricated events to be DOUBLE-COUNTED across windows (every
    window matched because clamped parsed == end ≥ every window's start).
    Future-dated events are now excluded entirely — they cannot be real
    (events happen at ts ≤ now by construction). Operator seeing future
    events should reset the clock or investigate the bad emitter, not
    see inflated counts.
    """
    parsed = _parse_iso(ts_str)
    if parsed is None:
        return start is None
    # PLAN-025 F-scripts-001: future-dated is malformed — exclude rather than clamp.
    if parsed > end:
        return False
    if start is not None and parsed < start:
        return False
    return True


# ---------------------------------------------------------------------------
# Bucket midpoint parser (for prediction_queried.bucket_range)
# ---------------------------------------------------------------------------


_BUCKET_PATTERN = re.compile(r"^(\d+)k-(\d+)k$")


def _bucket_midpoint(bucket_range: str) -> Optional[int]:
    """Parse a bucket string like ``"100k-130k"`` and return the midpoint
    in raw tokens (here: 115000). Returns None if unparseable or
    'unknown' (cold_start).
    """
    if not isinstance(bucket_range, str):
        return None
    s = bucket_range.strip().lower()
    if not s or s == "unknown":
        return None
    m = _BUCKET_PATTERN.match(s)
    if not m:
        return None
    lo_k = int(m.group(1))
    hi_k = int(m.group(2))
    if hi_k < lo_k:
        return None
    return ((lo_k + hi_k) // 2) * 1000


# ---------------------------------------------------------------------------
# Skill baseline walker
# ---------------------------------------------------------------------------


def _collect_skill_names(skills_dir: Path) -> Set[str]:
    """Walk `skills_dir` recursively looking for SKILL.md files. A skill's
    name is the basename of the directory containing SKILL.md.
    """
    names: Set[str] = set()
    if not skills_dir.is_dir():
        return names
    for root, _dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files:
            names.add(Path(root).name)
    return names


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_metrics(
    entries: Iterable[Dict[str, Any]],
    *,
    start: Optional[datetime],
    end: datetime,
    target_skills: Set[str],
    baseline_skills: Set[str],
) -> Dict[str, Any]:
    """Fold entries into the 7-metric payload. Pure function —
    no I/O. Entries outside [start, end] are filtered out here.
    """
    sessions: Set[str] = set()
    sessions_unknown_seen = False
    spawns_total = 0
    vetoes_total = 0
    plan_done = 0
    plan_abandoned = 0
    plan_other = 0
    actual_tokens = 0
    actual_tokens_seen = False
    predicted_tokens = 0
    predicted_seen = False
    adr_mentions: List[str] = []

    for entry in entries:
        ts = entry.get("ts", "")
        if not _in_window(ts, start, end):
            continue
        action = entry.get("action", "")

        # Sessions: every in-window event contributes (distinct session_id)
        sid = entry.get("session_id")
        if isinstance(sid, str) and sid:
            sessions.add(sid)
        else:
            sessions_unknown_seen = True

        # Spawns / vetoes (metrics #2 and #3)
        if action == "agent_spawn":
            spawns_total += 1
            # Metric #5 actual tokens — prefer tokens_total, fall back to in+out
            ttotal = entry.get("tokens_total")
            if isinstance(ttotal, int) and ttotal >= 0:
                actual_tokens += ttotal
                actual_tokens_seen = True
            else:
                tin = entry.get("tokens_in")
                tout = entry.get("tokens_out")
                tin_n = tin if isinstance(tin, int) and tin >= 0 else 0
                tout_n = tout if isinstance(tout, int) and tout >= 0 else 0
                if (isinstance(tin, int) and tin >= 0) or (
                    isinstance(tout, int) and tout >= 0
                ):
                    actual_tokens += tin_n + tout_n
                    actual_tokens_seen = True
        elif action == "veto_triggered":
            vetoes_total += 1
        elif action == "plan_transition":
            to_status = entry.get("to_status")
            if to_status == "done":
                plan_done += 1
            elif to_status == "abandoned":
                plan_abandoned += 1
            else:
                plan_other += 1
        elif action == "prediction_queried":
            mid = _bucket_midpoint(entry.get("bucket_range", ""))
            if mid is not None:
                predicted_tokens += mid
                predicted_seen = True

        # ADR mentions — scan any event's desc_preview and reason_preview
        for field in ("desc_preview", "reason_preview"):
            val = entry.get(field)
            if isinstance(val, str) and val:
                for m in _ADR_PATTERN.findall(val):
                    adr_mentions.append(m)

    # Sessions accounting — "unknown" bucket contributes at most 1 if any
    # in-window event had no session_id
    sessions_count = len(sessions) + (1 if sessions_unknown_seen else 0)

    # Veto rate
    spawns_plus_vetoes = spawns_total + vetoes_total
    if spawns_plus_vetoes == 0:
        veto_rate: Optional[float] = None
    else:
        veto_rate = vetoes_total / spawns_plus_vetoes

    # Task completion
    done_plus_abandoned = plan_done + plan_abandoned
    if done_plus_abandoned == 0:
        completion_rate: Optional[float] = None
    else:
        completion_rate = plan_done / done_plus_abandoned

    # Tokens ratio
    if not predicted_seen:
        tokens_ratio: Optional[float] = None
        predicted_tokens_out: Optional[int] = None
    else:
        predicted_tokens_out = predicted_tokens
        tokens_ratio = (
            actual_tokens / predicted_tokens if predicted_tokens > 0 else None
        )
    actual_tokens_out: Optional[int] = (
        actual_tokens if actual_tokens_seen else None
    )

    # Custom skills — target - baseline
    custom_names = sorted(target_skills - baseline_skills)

    # ADRs — distinct + total
    distinct_adrs = sorted(set(adr_mentions))

    return {
        "sessions_count": sessions_count,
        "spawns_total": spawns_total,
        "vetoes_total": vetoes_total,
        "spawns_plus_vetoes": spawns_plus_vetoes,
        "veto_rate": veto_rate,
        "plan_done": plan_done,
        "plan_abandoned": plan_abandoned,
        "plan_other_transitions": plan_other,
        "done_plus_abandoned": done_plus_abandoned,
        "completion_rate": completion_rate,
        "actual_tokens": actual_tokens_out,
        "predicted_tokens": predicted_tokens_out,
        "tokens_ratio": tokens_ratio,
        "custom_skills_count": len(custom_names),
        "custom_skills": custom_names,
        "adr_total_mentions": len(adr_mentions),
        "adr_distinct_count": len(distinct_adrs),
        "adr_distinct": distinct_adrs,
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _fmt_pct(ratio: Optional[float]) -> str:
    if ratio is None:
        return "N/A"
    return f"{round(ratio * 100, 1)}"


def _fmt_ratio(ratio: Optional[float]) -> str:
    if ratio is None:
        return "N/A"
    return f"{round(ratio, 3)}"


def _fmt_int_or_na(n: Optional[int]) -> str:
    if n is None:
        return "N/A"
    return str(n)


def render_markdown(
    *,
    adopter_name: str,
    window: str,
    start: Optional[datetime],
    end: datetime,
    now: datetime,
    audit_log_path: Path,
    metrics: Dict[str, Any],
) -> str:
    """Render the metrics payload into a human-readable markdown report.
    Structure matches PLAN-015 §0.1 template.
    """
    iso_end = end.strftime(_ISO_SECOND_FMT)
    iso_date_end = end.strftime("%Y-%m-%d")
    iso_start = start.strftime(_ISO_SECOND_FMT) if start is not None else "(unbounded)"
    now_iso = now.strftime(_ISO_SECOND_FMT)

    veto_pct = _fmt_pct(metrics["veto_rate"])
    comp_pct = _fmt_pct(metrics["completion_rate"])
    actual = _fmt_int_or_na(metrics["actual_tokens"])
    predicted = _fmt_int_or_na(metrics["predicted_tokens"])
    ratio = _fmt_ratio(metrics["tokens_ratio"])
    custom_count = metrics["custom_skills_count"]
    custom_csv = ", ".join(metrics["custom_skills"]) if metrics["custom_skills"] else "(none)"
    adr_distinct = metrics["adr_distinct_count"]
    adr_mentions = metrics["adr_total_mentions"]

    adr_list = metrics["adr_distinct"]
    if adr_list:
        adr_bullets = "\n".join(f"- {a}" for a in adr_list)
    else:
        adr_bullets = "(none mentioned in window)"

    skill_list = metrics["custom_skills"]
    if skill_list:
        skill_bullets = "\n".join(f"- {s}" for s in skill_list)
    else:
        skill_bullets = "(none — target has no skills beyond baseline)"

    return (
        f"# Adopter metrics — {adopter_name} — week ending {iso_date_end}\n"
        f"\n"
        f"**Window:** {window} ({iso_start} -> {iso_end})\n"
        f"**Generated:** {now_iso}\n"
        f"**Audit log:** {audit_log_path}\n"
        f"\n"
        f"## Summary table\n"
        f"\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Sessions | {metrics['sessions_count']} |\n"
        f"| Spawns | {metrics['spawns_total']} |\n"
        f"| Veto rate | {veto_pct}% ({metrics['vetoes_total']} / {metrics['spawns_plus_vetoes']}) |\n"
        f"| Task completion | {comp_pct}% ({metrics['plan_done']} done / {metrics['done_plus_abandoned']}) |\n"
        f"| Tokens actual vs predicted | {actual} / {predicted} ({ratio}) |\n"
        f"| Custom skills | {custom_count} ({custom_csv}) |\n"
        f"| ADRs activated | {adr_distinct} distinct / {adr_mentions} mentions |\n"
        f"\n"
        f"## ADRs activated in window\n"
        f"\n"
        f"{adr_bullets}\n"
        f"\n"
        f"## Custom skills (vs framework baseline)\n"
        f"\n"
        f"{skill_bullets}\n"
        f"\n"
        f"## Notes\n"
        f"\n"
        f"- Empty fields mean \"no events of that type in window\" (not \"metric failed\")\n"
        f"- For cold-start adopters (first week): most fields will be near-zero\n"
    )


def render_json(
    *,
    adopter_name: str,
    window: str,
    start: Optional[datetime],
    end: datetime,
    now: datetime,
    audit_log_path: Path,
    metrics: Dict[str, Any],
) -> str:
    """Serialize the full metrics payload to JSON, with envelope."""
    payload = {
        "adopter_name": adopter_name,
        "window": window,
        "window_start": start.strftime(_ISO_SECOND_FMT) if start is not None else None,
        "window_end": end.strftime(_ISO_SECOND_FMT),
        "generated_at": now.strftime(_ISO_SECOND_FMT),
        "audit_log_path": str(audit_log_path),
        "metrics": metrics,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the adopter-metrics CLI."""
    p = argparse.ArgumentParser(
        prog="adopter-metrics",
        description=(
            "Weekly metrics report for a ceo-orchestration adopter project. "
            "Reads the target's audit-log.jsonl, applies a time window, and "
            "emits a Markdown report (default) or JSON."
        ),
    )
    p.add_argument(
        "--adopter-name",
        required=True,
        help="Adopter project label (e.g. adopter-1). Goes into report header.",
    )
    p.add_argument(
        "--audit-log",
        required=True,
        type=Path,
        help="Path to the adopter's audit-log.jsonl. Missing file = empty log (exit 0).",
    )
    p.add_argument(
        "--window",
        default="7d",
        choices=sorted(_WINDOW_DAYS.keys()),
        help="Rolling window relative to --now. Default 7d.",
    )
    p.add_argument(
        "--skills-baseline",
        required=True,
        type=Path,
        help="Path to framework skills directory (for custom-skill diff).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown output path. If omitted, prints to stdout.",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit JSON to stdout instead of Markdown (ignores --output).",
    )
    p.add_argument(
        "--now",
        default=None,
        help="Override 'now' for deterministic tests (ISO-8601 UTC).",
    )
    p.add_argument(
        "--target-skills-dir",
        type=Path,
        default=None,
        help=(
            "Path to target project's .claude/skills/ dir (for metric #6). "
            "Defaults to sibling of --audit-log: "
            "<audit_log.parent>/../../.claude/skills if not provided."
        ),
    )
    return p


def _resolve_target_skills_dir(
    audit_log: Path, override: Optional[Path]
) -> Optional[Path]:
    """Pick the adopter's ``.claude/skills/`` dir.

    If ``--target-skills-dir`` was provided, honor it verbatim. Otherwise
    fall back to ``<audit_log.parent>/.claude/skills`` if that exists.
    Returns None if neither exists — metric #6 is then "0 custom skills".
    """
    if override is not None:
        return override
    # Heuristic: many adopters drop `audit-log.jsonl` in a sibling of
    # `.claude/` inside their repo root. Try that first.
    candidate = audit_log.parent / ".claude" / "skills"
    if candidate.is_dir():
        return candidate
    return None


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — compute and emit adopter-telemetry metrics."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse already wrote to stderr. Map its non-zero exit to 1.
        return int(e.code) if isinstance(e.code, int) and e.code != 0 else (
            0 if e.code == 0 else 1
        )

    # Validate --now
    try:
        now = _resolve_now(args.now)
    except ValueError as e:
        print(f"[adopter-metrics] ERROR: {e}", file=sys.stderr)
        return 1

    # Validate skills-baseline
    if not args.skills_baseline.is_dir():
        print(
            f"[adopter-metrics] ERROR: --skills-baseline is not a directory: "
            f"{args.skills_baseline}",
            file=sys.stderr,
        )
        return 1

    # Validate audit-log readability (missing = OK, unreadable = exit 2)
    audit_log: Path = args.audit_log
    if audit_log.exists():
        if not audit_log.is_file():
            print(
                f"[adopter-metrics] ERROR: --audit-log is not a regular file: {audit_log}",
                file=sys.stderr,
            )
            return 2
        if not os.access(audit_log, os.R_OK):
            print(
                f"[adopter-metrics] ERROR: --audit-log is not readable: {audit_log}",
                file=sys.stderr,
            )
            return 2

    # Validate / create output parent
    output: Optional[Path] = args.output
    if output is not None and not args.as_json:
        parent = output.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(
                    f"[adopter-metrics] ERROR: cannot create output parent dir "
                    f"{parent}: {e}",
                    file=sys.stderr,
                )
                return 1

    # Collect skills
    baseline_skills = _collect_skill_names(args.skills_baseline)
    target_skills_dir = _resolve_target_skills_dir(
        audit_log, args.target_skills_dir
    )
    target_skills = (
        _collect_skill_names(target_skills_dir)
        if target_skills_dir is not None
        else set()
    )

    # Window bounds
    start, end = _window_bounds(args.window, now)

    # Compute metrics (streaming over audit log)
    entries = read_entries(audit_log)
    metrics = compute_metrics(
        entries,
        start=start,
        end=end,
        target_skills=target_skills,
        baseline_skills=baseline_skills,
    )

    # Render
    if args.as_json:
        out_text = render_json(
            adopter_name=args.adopter_name,
            window=args.window,
            start=start,
            end=end,
            now=now,
            audit_log_path=audit_log,
            metrics=metrics,
        )
        sys.stdout.write(out_text)
        return 0

    out_text = render_markdown(
        adopter_name=args.adopter_name,
        window=args.window,
        start=start,
        end=end,
        now=now,
        audit_log_path=audit_log,
        metrics=metrics,
    )
    if output is None:
        sys.stdout.write(out_text)
    else:
        try:
            output.write_text(out_text, encoding="utf-8")
        except OSError as e:
            print(
                f"[adopter-metrics] ERROR: cannot write {output}: {e}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
