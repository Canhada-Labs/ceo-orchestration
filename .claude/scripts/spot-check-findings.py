#!/usr/bin/env python3
"""PLAN-025 Batch L — CEO_OPUS_SPOT_CHECK_P1 orthogonal flag.

Reads a findings file (typically .claude/plans/PLAN-NNN/audit/
consolidated-findings.md) and emits a list of P1+ findings that were
originally scored by a non-Opus model — these are candidates for an
Opus re-audit.

The script does NOT spawn agents directly (that requires the Claude
Code session context). It emits MARKERS that a calling CEO session can
consume to decide which findings to re-spawn Opus against.

## Usage

    # Normal mode: produces stdout list of re-audit candidates
    python3 .claude/scripts/spot-check-findings.py <findings-file>

    # With flag active: same output + exit code 0 if candidates exist
    # (so a calling CEO session can branch on it)
    CEO_OPUS_SPOT_CHECK_P1=1 python3 .claude/scripts/spot-check-findings.py <findings-file>

## Parser behaviour

The findings file is expected to use the PLAN-024 schema:

    ### F-<area>-<nnn> [P0|P1|P2|P3] — <title>
    **File:** <path>
    **Root cause:** <text>
    **Source model:** <model-id>  (optional — PLAN-025+ only)
    ...

If `source model:` is absent, the finding is assumed to be Opus
(pre-multi-model era) and is NOT flagged for re-audit.

Severity >= P1 triggers re-audit eligibility; P2 / P3 are ignored.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_FINDING_HEADER_RE = re.compile(
    r"^###\s+(F-[a-zA-Z0-9_\-]+)\s+\[(P[0-3])\]\s+—\s+(.+)$"
)
_SOURCE_MODEL_RE = re.compile(
    r"^\*\*Source model:\*\*\s*`?([a-zA-Z0-9_\-\.]+)`?"
)

_OPUS_IDS = frozenset({
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
})


def _parse_findings(text: str) -> List[Dict[str, Optional[str]]]:
    """Extract finding records from a consolidated-findings.md file.

    Returns a list of dicts per finding:
      {
        "id": "F-sec-001",
        "severity": "P1",
        "title": "...",
        "source_model": "claude-sonnet-4-6" | None,
        "line_no": 142
      }

    Fail-open: malformed sections contribute nothing.
    """
    findings: List[Dict[str, Optional[str]]] = []
    lines = text.splitlines()
    current: Optional[Dict[str, Optional[str]]] = None

    for line_no, raw in enumerate(lines, start=1):
        m = _FINDING_HEADER_RE.match(raw)
        if m:
            if current is not None:
                findings.append(current)
            current = {
                "id": m.group(1),
                "severity": m.group(2),
                "title": m.group(3).strip(),
                "source_model": None,
                "line_no": line_no,
            }
            continue
        if current is None:
            continue
        sm = _SOURCE_MODEL_RE.match(raw)
        if sm:
            current["source_model"] = sm.group(1)

    if current is not None:
        findings.append(current)

    return findings


def _is_reaudit_candidate(f: Dict[str, Optional[str]]) -> bool:
    """True if finding should be re-audited by Opus."""
    sev = f.get("severity") or ""
    if sev not in ("P0", "P1"):
        return False
    src = f.get("source_model")
    # No source_model metadata → pre-multi-model finding; skip
    if not src:
        return False
    # Opus-originated findings don't need Opus re-audit
    if src in _OPUS_IDS:
        return False
    return True


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — random-sample audit findings for Owner spot-check."""
    parser = argparse.ArgumentParser(
        prog="spot-check-findings.py",
        description=(
            "Identify P1+ findings originally scored by non-Opus models; "
            "emit re-audit candidates for CEO_OPUS_SPOT_CHECK_P1 workflow."
        ),
    )
    parser.add_argument(
        "findings_file",
        type=Path,
        help="Path to a PLAN-NNN/audit/consolidated-findings.md file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    if not args.findings_file.is_file():
        print(
            f"ERROR: findings file not found: {args.findings_file}",
            file=sys.stderr,
        )
        return 2

    flag_active = (os.environ.get("CEO_OPUS_SPOT_CHECK_P1") or "").strip() == "1"

    text = args.findings_file.read_text(encoding="utf-8")
    findings = _parse_findings(text)
    candidates = [f for f in findings if _is_reaudit_candidate(f)]

    if args.json:
        import json
        payload = {
            "flag_active": flag_active,
            "total_findings": len(findings),
            "reaudit_candidates": [
                {
                    "id": c["id"],
                    "severity": c["severity"],
                    "title": c["title"],
                    "source_model": c["source_model"],
                    "line_no": c["line_no"],
                }
                for c in candidates
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Findings file: {args.findings_file}")
        print(f"Total findings parsed: {len(findings)}")
        print(
            f"CEO_OPUS_SPOT_CHECK_P1 flag: "
            f"{'ACTIVE' if flag_active else 'not set'}"
        )
        print(f"Re-audit candidates (P1+ scored by non-Opus): {len(candidates)}")
        print("")
        if not candidates:
            print("No re-audit candidates; audit already Opus-scored for P1+.")
            return 0
        print("Candidates:")
        for c in candidates:
            print(
                f"  - {c['id']} [{c['severity']}] source_model="
                f"{c['source_model']}  ({c['title'][:80]})"
            )
        print("")
        if flag_active:
            print(
                "ACTION: re-spawn Opus 4.8 via the canonical-5 "
                "code-reviewer / security-engineer archetype with each "
                "finding as context; aggregate the re-verdict into the "
                "next wave synthesis."
            )
        else:
            print(
                "HINT: set CEO_OPUS_SPOT_CHECK_P1=1 to activate the "
                "re-audit workflow (orthogonal to quality profile)."
            )

    # Exit code convention:
    #   0 — no candidates, or flag not set (advisory-only)
    #   0 — flag active + candidates (CEO session branches on stdout, not exit)
    # We don't use non-zero here to avoid blocking callers.
    return 0


if __name__ == "__main__":
    sys.exit(main())
