#!/usr/bin/env python3
"""PLAN-084 R2 CODEX-P1-2 — findings-pretty-print.

Auto-generates a human-readable markdown view of
PLAN-084-findings-master.jsonl (canonical format).

Stdlib only.

Usage:
  python3 .claude/scripts/local/findings-pretty-print.py \
    --jsonl .claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl \
    --output .claude/plans/PLAN-084/canonical/PLAN-084-findings-master.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    if not args.jsonl.exists():
        print(f"jsonl not found: {args.jsonl}", file=sys.stderr)
        return 3

    entries = []
    for line in args.jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    by_severity = defaultdict(list)
    for e in entries:
        by_severity[e.get("severity", "?")].append(e)

    with args.output.open("w", encoding="utf-8") as out:
        out.write(f"# PLAN-084 findings-master (auto-generated view)\n\n")
        out.write(f"Total findings: {len(entries)}\n\n")
        out.write(f"## Counts by severity\n\n")
        out.write(f"| Severity | Count |\n|---|---|\n")
        for sev in ("P0", "P1", "P2", "P3", "minor"):
            out.write(f"| {sev} | {len(by_severity.get(sev, []))} |\n")
        out.write(f"\n")

        for sev in ("P0", "P1", "P2", "P3", "minor"):
            lst = by_severity.get(sev, [])
            if not lst:
                continue
            out.write(f"\n## {sev} findings ({len(lst)})\n\n")
            for e in lst:
                out.write(f"### {e.get('id', '?')} — {e.get('category', '?')} ({e.get('archetype', '?')})\n\n")
                out.write(f"- **File:** `{e.get('file', '?')}`\n")
                out.write(f"- **Lines:** {e.get('line_range', 'n/a')}\n")
                out.write(f"- **Subcorpus:** {e.get('subcorpus', '?')}\n")
                out.write(f"- **Intent:** {e.get('intent', '?')}\n")
                out.write(f"- **Codex verdict:** {e.get('codex_verdict', 'pending')}\n")
                desc = e.get('description', '')
                if desc:
                    out.write(f"\n{desc[:500]}{'...' if len(desc) > 500 else ''}\n\n")

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
