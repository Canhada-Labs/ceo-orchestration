"""rendering audit-query declarations."""

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

__all__ = ('render', '_format_dict', '_format_list_under', '_format_table')

def render(result: Any, *, as_json: bool, as_csv: bool) -> str:
    """Render query results into the requested output format (text / json / markdown)."""
    if as_json:
        return json.dumps(result, indent=2, ensure_ascii=True)
    if as_csv and isinstance(result, list) and result and isinstance(result[0], dict):
        buf = io.StringIO()
        fieldnames = sorted({k for e in result for k in e.keys()})
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in result:
            writer.writerow(e)
        return buf.getvalue()

    # Default: pretty-print
    if isinstance(result, dict):
        # by-domain: prefer the embedded markdown table for human output
        if result.get("query") == "by-domain" and "markdown_table" in result:
            lines = [
                f"window: {result.get('window', '')}",
                f"total_spawns: {result.get('total_spawns_in_window', 0)}",
                f"overall_hint_coverage: {result.get('overall_hint_coverage_pct', 0)}%",
                f"domain_count: {result.get('domain_count', 0)}",
                "",
                result["markdown_table"],
            ]
            if "check_reopen" in result:
                cr = result["check_reopen"]
                lines += [
                    "--- Reopen check ---",
                    f"sunset_domains_loaded: {cr.get('sunset_domains_loaded', 0)}",
                    f"reopen_candidates: {cr.get('reopen_count', 0)}",
                ]
                for row in cr.get("reopen_candidates", []):
                    lines.append(f"  * {row['domain']} ({row['spawns']} spawns)")
            return "\n".join(lines)
        return _format_dict(result)
    if isinstance(result, list):
        if not result:
            return "(no results)"
        if isinstance(result[0], dict):
            return _format_table(result)
        return "\n".join(str(x) for x in result)
    return str(result)


def _format_dict(d: Dict[str, Any]) -> str:
    lines = []
    for key, value in d.items():
        if isinstance(value, (list, dict)):
            lines.append(f"{key}:")
            sub = _format_dict(value) if isinstance(value, dict) else _format_list_under(value)
            for ln in sub.split("\n"):
                lines.append(f"  {ln}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_list_under(items: List[Any]) -> str:
    if not items:
        return "(empty)"
    if isinstance(items[0], dict):
        return _format_table(items)
    return "\n".join(f"- {x}" for x in items)


def _format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"
    fieldnames = list(rows[0].keys())
    # Compute column widths
    widths = {f: len(f) for f in fieldnames}
    str_rows = []
    for r in rows:
        str_row = {}
        for f in fieldnames:
            s = str(r.get(f, ""))
            str_row[f] = s
            if len(s) > widths[f]:
                widths[f] = min(len(s), 80)
        str_rows.append(str_row)
    header = " | ".join(f.ljust(widths[f]) for f in fieldnames)
    sep = "-+-".join("-" * widths[f] for f in fieldnames)
    body = "\n".join(
        " | ".join(str(r[f])[: widths[f]].ljust(widths[f]) for f in fieldnames)
        for r in str_rows
    )
    return f"{header}\n{sep}\n{body}"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PLAN-081 Phase 6-bis — Pair-Rail label store + fp-rate aggregator + Codex
# writeguard summary (R1 S-TDE-3 + S-TDE Q2). Owner labels Case B verdicts
# post-hoc; fp-rate computes lower/upper bounds; codex-writeguard-summary
# aggregates deny-list hits.
# ---------------------------------------------------------------------------

