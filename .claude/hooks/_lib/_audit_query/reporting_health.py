"""Additional audit-query reports."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

def cmd_health(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """High-level framework health. Sprint 5 A.2.

    Rolls up several gates into an overall PASS/WARN/FAIL verdict so
    `audit-dashboard.py` and ops tooling have one call to make.
    """
    total = len(entries)
    if total == 0:
        return {"verdict": "NO_DATA", "total_events": 0, "gates": {}}

    compliance = cmd_compliance(entries, args)
    metrics = cmd_metrics(entries, args)

    gates: Dict[str, str] = {}

    # Gate 1: compliance rate >= 0.95
    known_rate = compliance.get("known_skill_rate")
    if known_rate is None:
        gates["compliance"] = "NO_DATA"
    elif known_rate >= 0.95:
        gates["compliance"] = "PASS"
    elif known_rate >= 0.8:
        gates["compliance"] = "WARN"
    else:
        gates["compliance"] = "FAIL"

    # Gate 2: veto rate < 0.15
    veto_rate = metrics.get("veto_rate")
    if veto_rate is None:
        gates["vetoes"] = "NO_DATA"
    elif veto_rate < 0.05:
        gates["vetoes"] = "PASS"
    elif veto_rate < 0.15:
        gates["vetoes"] = "WARN"
    else:
        gates["vetoes"] = "FAIL"

    # Gate 3: debate completion rate >= 0.8 (if any rounds started)
    dc = metrics.get("debate_completion_rate")
    if dc is None:
        gates["debate_completion"] = "NO_DATA"
    elif dc >= 0.8:
        gates["debate_completion"] = "PASS"
    elif dc >= 0.5:
        gates["debate_completion"] = "WARN"
    else:
        gates["debate_completion"] = "FAIL"

    # Verdict reduction
    if any(v == "FAIL" for v in gates.values()):
        verdict = "FAIL"
    elif any(v == "WARN" for v in gates.values()):
        verdict = "WARN"
    elif all(v in ("PASS", "NO_DATA") for v in gates.values()):
        verdict = "PASS"
    else:
        verdict = "WARN"

    return {
        "verdict": verdict,
        "total_events": total,
        "gates": gates,
        "known_skill_rate": known_rate,
        "veto_rate": veto_rate,
        "debate_completion_rate": dc,
        "action_counts": metrics.get("action_counts", {}),
    }


def cmd_export(entries: List[Dict[str, Any]], args) -> Any:
    """Handle the `audit-query export` sub-command — emit filtered audit-log slices."""
    fmt = args.export_format
    if fmt == "json":
        return entries
    if fmt == "csv":
        buf = io.StringIO()
        if not entries:
            return ""
        fieldnames = sorted({k for e in entries for k in e.keys()})
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            writer.writerow(e)
        return buf.getvalue()
    if fmt == "tsv":
        buf = io.StringIO()
        if not entries:
            return ""
        fieldnames = sorted({k for e in entries for k in e.keys()})
        writer = csv.DictWriter(
            buf, fieldnames=fieldnames, extrasaction="ignore", delimiter="\t"
        )
        writer.writeheader()
        for e in entries:
            writer.writerow(e)
        return buf.getvalue()
    raise ValueError(f"unsupported export format: {fmt}")
