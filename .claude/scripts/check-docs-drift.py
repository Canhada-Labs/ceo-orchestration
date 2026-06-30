#!/usr/bin/env python3
"""Advisory cross-doc count-drift checker for ceo-orchestration.

PLAN-045 F-05-01/02/03 — "repo-wide skill count / ADR count / test
count drift" — ships mechanical verification that prose numbers in
canonical docs match disk truth.

Scope:
  - ADR count: `\\*\\*\\d+ ADRs?\\*\\*` patterns in canonical docs
  - Skill counts: `\\d+ (core|frontend|fintech|universal) skills?`
  - Total skills: `\\*\\*\\d+ skills\\*\\*` or `\\d+ reusable skills`

Docs scanned:
  - CLAUDE.md
  - README.md
  - README.pt-BR.md
  - INSTALL.md
  - docs/ROADMAP.md
  - docs/HONEST-LIMITATIONS.md
  - docs/CTO-GUIDE.md
  - docs/GUIA-COMPLETO.md / GUIA-COMPLETO.pt-BR.md

Advisory — exits 0 regardless of findings; prints drift report.
Wire into validate-governance.sh as a WARN-only step.

Stdlib-only. Python 3.9+.

Usage:
  python3 .claude/scripts/check-docs-drift.py
  python3 .claude/scripts/check-docs-drift.py --strict   # exit 1 on drift
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DOCS_TO_CHECK = [
    "CLAUDE.md",
    "README.md",
    "README.pt-BR.md",
    "INSTALL.md",
    "docs/ROADMAP.md",
    "docs/HONEST-LIMITATIONS.md",
    "docs/CTO-GUIDE.md",
    "docs/GUIA-COMPLETO.md",
    "docs/GUIA-COMPLETO.pt-BR.md",
]


def _disk_truth() -> Dict[str, int]:
    """Count disk-resident skills / ADRs / domain slices."""
    result: Dict[str, int] = {}

    # Core skills
    core_dir = REPO_ROOT / ".claude" / "skills" / "core"
    if core_dir.is_dir():
        result["core"] = sum(
            1 for p in core_dir.iterdir()
            if p.is_dir() and (p / "SKILL.md").exists()
        )

    # Frontend skills
    front_dir = REPO_ROOT / ".claude" / "skills" / "frontend"
    if front_dir.is_dir():
        result["frontend"] = sum(
            1 for p in front_dir.iterdir()
            if p.is_dir() and (p / "SKILL.md").exists()
        )

    # Domain skills
    domains_dir = REPO_ROOT / ".claude" / "skills" / "domains"
    domain_total = 0
    if domains_dir.is_dir():
        for d in domains_dir.iterdir():
            if not d.is_dir():
                continue
            skills_root = d / "skills"
            if skills_root.is_dir():
                dc = sum(
                    1 for p in skills_root.iterdir()
                    if p.is_dir() and (p / "SKILL.md").exists()
                )
                result["domain_" + d.name] = dc
                domain_total += dc
            else:
                # Skills directly under domain/ (no wrapper)
                dc = sum(
                    1 for p in d.iterdir()
                    if p.is_dir() and (p / "SKILL.md").exists()
                )
                if dc > 0:
                    result["domain_" + d.name] = dc
                    domain_total += dc
    result["domain_total"] = domain_total

    # ADR count
    adr_dir = REPO_ROOT / ".claude" / "adr"
    if adr_dir.is_dir():
        result["adrs"] = sum(
            1 for p in adr_dir.glob("ADR-*.md")
        )

    # Total skills (core + frontend + all domains)
    result["total_skills"] = (
        result.get("core", 0)
        + result.get("frontend", 0)
        + domain_total
    )

    return result


def _find_drifts(doc_path: Path, truth: Dict[str, int]) -> List[str]:
    """Return a list of drift-report lines for a single doc."""
    out: List[str] = []
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return out

    # ADR count: `**N ADRs**` or `**N ADR**`
    for m in re.finditer(r"\*\*(\d+) ADRs?\*\*", text):
        claimed = int(m.group(1))
        if claimed != truth.get("adrs", 0):
            line = text[: m.start()].count("\n") + 1
            out.append(
                "  {p}:{ln} claims {c} ADRs; disk={d}".format(
                    p=doc_path.name, ln=line, c=claimed, d=truth.get("adrs", "?")
                )
            )

    # Core skill count: `N core skills?` or `N universal` (core)
    for m in re.finditer(
        r"(\d+)\s+(core|universal backend|universal core)\s+skills?",
        text, re.IGNORECASE,
    ):
        claimed = int(m.group(1))
        if claimed != truth.get("core", 0):
            line = text[: m.start()].count("\n") + 1
            out.append(
                "  {p}:{ln} claims {c} core skills; disk={d}".format(
                    p=doc_path.name, ln=line, c=claimed,
                    d=truth.get("core", "?"),
                )
            )

    # Frontend skill count
    for m in re.finditer(
        r"(\d+)\s+(frontend|universal frontend)\s+skills?",
        text, re.IGNORECASE,
    ):
        claimed = int(m.group(1))
        if claimed != truth.get("frontend", 0):
            line = text[: m.start()].count("\n") + 1
            out.append(
                "  {p}:{ln} claims {c} frontend skills; disk={d}".format(
                    p=doc_path.name, ln=line, c=claimed,
                    d=truth.get("frontend", "?"),
                )
            )

    # Fintech domain
    fintech_n = truth.get("domain_fintech", 0)
    if fintech_n:
        for m in re.finditer(r"(\d+)\s+fintech\s+skills?", text, re.IGNORECASE):
            claimed = int(m.group(1))
            if claimed != fintech_n:
                line = text[: m.start()].count("\n") + 1
                out.append(
                    "  {p}:{ln} claims {c} fintech skills; disk={d}".format(
                        p=doc_path.name, ln=line, c=claimed, d=fintech_n,
                    )
                )

    # Total skills: `**N skills**` or `N reusable skills`
    for m in re.finditer(
        r"(?:\*\*)?(\d+)(?:\*\*)?\s*(?:reusable\s+)?skills?\b",
        text,
    ):
        claimed = int(m.group(1))
        # Filter false positives: numbers like `8 frontend skills` already
        # matched above; don't double-report if claimed == known tier count.
        # Only report if the context says "total" or matches the bolded **N skills** form.
        prefix = text[max(0, m.start() - 10): m.start()]
        suffix = text[m.end(): m.end() + 10]
        is_bold = "**" in prefix and "**" in suffix
        is_total_context = bool(re.search(
            r"(total|reusable|library|catalog|tiered)",
            text[max(0, m.start() - 80): m.start()],
            re.IGNORECASE,
        ))
        if not (is_bold or is_total_context):
            continue
        # Skip if it's actually a per-tier count we already checked
        if claimed in (
            truth.get("core", -1),
            truth.get("frontend", -1),
            truth.get("domain_fintech", -1),
        ):
            continue
        if claimed != truth.get("total_skills", 0):
            line = text[: m.start()].count("\n") + 1
            out.append(
                "  {p}:{ln} claims {c} total skills; disk={d}".format(
                    p=doc_path.name, ln=line, c=claimed,
                    d=truth.get("total_skills", "?"),
                )
            )

    return out


def main() -> int:
    """CLI entrypoint — scan canonical docs for count drifts vs disk truth."""
    parser = argparse.ArgumentParser(
        prog="check-docs-drift",
        description="Advisory count-drift checker for canonical docs.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 if any drift found (default: exit 0 / advisory).",
    )
    args = parser.parse_args()

    truth = _disk_truth()

    print("Disk truth:")
    for k, v in sorted(truth.items()):
        print("  {k:24s} = {v}".format(k=k, v=v))
    print("")

    total_drifts = 0
    for rel in DOCS_TO_CHECK:
        doc = REPO_ROOT / rel
        if not doc.exists():
            continue
        drifts = _find_drifts(doc, truth)
        if drifts:
            print("DRIFTS in {p}:".format(p=rel))
            for line in drifts:
                print(line)
            total_drifts += len(drifts)

    print("")
    if total_drifts == 0:
        print("OK: no count-drift in canonical docs.")
        return 0
    print("WARN: {n} drift(s) across canonical docs.".format(n=total_drifts))
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
