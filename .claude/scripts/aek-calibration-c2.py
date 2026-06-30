#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLAN-101 Wave A — AEK Calibration C2 baseline analysis.

Reads `task_route_advised` events from the audit-log via
`audit-query.py since <CUTOFF>` and computes:

- Total event count (must satisfy N >= 200; else EXIT_INSUFFICIENT_VOLUME)
- Per-class distribution (S / M / L / XL) with count + percentage
- Per-cell sufficiency (cells with N < 30 marked `insufficient-data`)
- Classifier-runtime envelope from `duration_ms` field (p50 / p95 / p99)

Output: markdown report with anchor `## TASK-CLASS-BASELINE` (downstream
parse contract — mirrors PLAN-100 `## FPR-TABLE` precedent).

Per ADR-104-AMEND-1 §C — sample sufficiency is the substantive gate;
calendar windows are RETRACTED per ADR-095 doctrine.

Usage:
  python3 .claude/scripts/aek-calibration-c2.py \\
      --window-days 30 \\
      --output .claude/plans/PLAN-101/wave-a-c2-baseline.md

  python3 .claude/scripts/aek-calibration-c2.py --self-test

Exit codes:
  0 — baseline computed; report written
  2 — internal error
  3 — INSUFFICIENT_VOLUME (N < 200 total)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]

EXIT_OK = 0
EXIT_INTERNAL = 2
EXIT_INSUFFICIENT_VOLUME = 3

MIN_TOTAL_EVENTS = 200
MIN_PER_CELL = 30
KNOWN_CLASSES = ("S", "M", "L", "XL")


def _audit_query_since(cutoff_iso: str) -> List[Dict]:
    """Invoke audit-query.py since <cutoff> --json and parse stdout."""
    audit_query = REPO_ROOT / ".claude" / "scripts" / "audit-query.py"
    try:
        out = subprocess.check_output(
            ["python3", str(audit_query), "since", cutoff_iso, "--json"],
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[c2] audit-query failed: {exc.stderr[:500]}", file=sys.stderr)
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        print(f"[c2] audit-query JSON parse error: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    return [ev for ev in data if isinstance(ev, dict) and ev.get("action") == "task_route_advised"]


def _percentile(values: List[float], p: float) -> float:
    """Stdlib percentile (no numpy)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def _compute_baseline(events: List[Dict]) -> Dict:
    """Compute per-class distribution + classifier-runtime envelope."""
    by_class: Dict[str, int] = {c: 0 for c in KNOWN_CLASSES}
    by_class_unknown = 0
    durations_by_class: Dict[str, List[float]] = {c: [] for c in KNOWN_CLASSES}
    durations_all: List[float] = []

    for ev in events:
        cls = ev.get("classification")
        if cls in by_class:
            by_class[cls] += 1
        else:
            by_class_unknown += 1
            continue
        dur = ev.get("duration_ms")
        if isinstance(dur, (int, float)):
            durations_by_class[cls].append(float(dur))
            durations_all.append(float(dur))

    total = sum(by_class.values()) + by_class_unknown
    return {
        "total_events": total,
        "by_class": by_class,
        "by_class_unknown": by_class_unknown,
        "durations_by_class": durations_by_class,
        "durations_all": durations_all,
    }


def _format_baseline_md(b: Dict, window_iso: str) -> str:
    """Render markdown with TASK-CLASS-BASELINE anchor."""
    lines: List[str] = []
    lines.append("# PLAN-101 Wave A — Calibration C2 baseline")
    lines.append("")
    lines.append(f"**Window cutoff (since):** {window_iso}")
    lines.append(f"**Total `task_route_advised` events:** {b['total_events']}")
    lines.append("")
    lines.append("## TASK-CLASS-BASELINE")
    lines.append("")
    lines.append("Per-class distribution computed from `task_route_advised.classification` "
                 "field. Cells with N < 30 marked `insufficient-data` per "
                 "ADR-104-AMEND-1 §C.")
    lines.append("")
    lines.append("| Class | Count | % | Sufficient (N≥30) |")
    lines.append("| ----- | ----- | --- | ----------------- |")
    total = max(b["total_events"], 1)
    for cls in KNOWN_CLASSES:
        n = b["by_class"][cls]
        pct = 100.0 * n / total
        suf = "yes" if n >= MIN_PER_CELL else "insufficient-data"
        lines.append(f"| {cls} | {n} | {pct:.1f}% | {suf} |")
    if b["by_class_unknown"]:
        lines.append(f"| (unknown) | {b['by_class_unknown']} | "
                     f"{100.0*b['by_class_unknown']/total:.1f}% | excluded |")
    lines.append("")
    lines.append("## CLASSIFIER-RUNTIME-ENVELOPE")
    lines.append("")
    lines.append("Latency reported is the CLASSIFIER wall-clock (`duration_ms` "
                 "field per `SPEC/v1/audit-log.schema.md`), NOT task duration. "
                 "S134 P0 #4 semantic correction.")
    lines.append("")
    lines.append("| Class | N | p50 (ms) | p95 (ms) | p99 (ms) |")
    lines.append("| ----- | -- | -------- | -------- | -------- |")
    for cls in KNOWN_CLASSES:
        durs = b["durations_by_class"][cls]
        n = len(durs)
        if n == 0:
            lines.append(f"| {cls} | 0 | - | - | - |")
        else:
            lines.append(f"| {cls} | {n} | {_percentile(durs, 50):.2f} | "
                         f"{_percentile(durs, 95):.2f} | {_percentile(durs, 99):.2f} |")
    durs_all = b["durations_all"]
    if durs_all:
        lines.append(f"| (all) | {len(durs_all)} | {_percentile(durs_all, 50):.2f} | "
                     f"{_percentile(durs_all, 95):.2f} | {_percentile(durs_all, 99):.2f} |")
    lines.append("")
    lines.append("## METHODOLOGY")
    lines.append("")
    lines.append("- Source: audit-log `task_route_advised` events via "
                 "`audit-query.py since <CUTOFF> --json` (S134 P0 iter-1→iter-4 "
                 "fold — robust JSON parse, not grep-on-pretty-printed).")
    lines.append("- Sample sufficiency: N >= 200 total; N >= 30 per class. "
                 "Cells with N < 30 marked `insufficient-data` and EXCLUDED "
                 "from downstream FPR aggregate.")
    lines.append("- Anti-circularity (Wave A.5): synth corpus authored "
                 "BEFORE re-reading classify() decision tree; fixtures span "
                 "all 4 classes; ground-truth labels declared a priori per "
                 "fixture in `synthesize-corpus.py`.")
    lines.append("- Calendar gate retracted per ADR-095 / "
                 "[[feedback-no-calendar-gates-ai-workflow]]; sample volume "
                 "may be satisfied via synth corpus run through real "
                 "`classify()`.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="PLAN-101 Wave A AEK Calibration C2 baseline")
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Audit-log window (days; default 30; calendar-gate-soft per ADR-095)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".claude/plans/PLAN-101/wave-a-c2-baseline.md",
        help="Output markdown path",
    )
    parser.add_argument("--self-test", action="store_true", help="Run internal self-test")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=args.window_days)).strftime("%Y-%m-%d")
    events = _audit_query_since(cutoff)
    b = _compute_baseline(events)

    print(f"[c2] window cutoff: {cutoff}", file=sys.stderr)
    print(f"[c2] total task_route_advised events: {b['total_events']}", file=sys.stderr)
    for cls in KNOWN_CLASSES:
        print(f"[c2]   {cls}: {b['by_class'][cls]}", file=sys.stderr)
    if b["by_class_unknown"]:
        print(f"[c2]   (unknown classification): {b['by_class_unknown']}", file=sys.stderr)

    if b["total_events"] < MIN_TOTAL_EVENTS:
        print(
            f"[c2] INSUFFICIENT_VOLUME: N={b['total_events']} < {MIN_TOTAL_EVENTS}",
            file=sys.stderr,
        )
        return EXIT_INSUFFICIENT_VOLUME

    md = _format_baseline_md(b, cutoff)
    out_path = REPO_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"[c2] wrote {out_path}", file=sys.stderr)
    return EXIT_OK


def _self_test() -> int:
    """Inline self-test (no audit-log dependency)."""
    sample = [
        {"action": "task_route_advised", "classification": "S", "duration_ms": 12.0},
        {"action": "task_route_advised", "classification": "S", "duration_ms": 15.0},
        {"action": "task_route_advised", "classification": "M", "duration_ms": 20.0},
        {"action": "task_route_advised", "classification": "L", "duration_ms": 30.0},
        {"action": "task_route_advised", "classification": "XL", "duration_ms": 50.0},
    ]
    b = _compute_baseline(sample)
    assert b["total_events"] == 5
    assert b["by_class"]["S"] == 2
    assert b["by_class"]["M"] == 1
    assert b["by_class"]["L"] == 1
    assert b["by_class"]["XL"] == 1
    md = _format_baseline_md(b, "2026-04-18")
    assert "## TASK-CLASS-BASELINE" in md
    assert "## CLASSIFIER-RUNTIME-ENVELOPE" in md
    print("[c2] self-test PASS", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
