#!/usr/bin/env python3
"""architect-bundle-validate.py — verify an Architect draft bundle.

Sprint 5 Phase 7. Validates the 5-file bundle the Agent Architect
emits into `.claude/plans/PLAN-NNN/architect/round-1/`. Used by the
`/architect` slash command after the meta-agent returns; can be run
manually before the Owner copies `approved.md.template` to the actual
sentinel.

## Checks

1. Bundle directory matches `.claude/plans/PLAN-*/architect/round-*/`.
2. All 5 required draft files present + parseable:
     - team.draft.md
     - pitfalls.draft.yaml
     - skill-selection.draft.md
     - personas.draft.md
     - rationale.md
3. `team.draft.md` contains ≥5 persona sections (`### `).
4. `pitfalls.draft.yaml` parses as YAML and has ≥10 entries under
   `pitfalls:`.
5. `skill-selection.draft.md` lists ≥3 skills (heuristic: ≥3 lines
   matching `^- \`<id>\``).
6. No file references real-person names (heuristic against a small
   curated deny-list of public real names — Owner-extensible).
7. No file uses paid-tier marketing language (heuristic: phrases like
   "enterprise tier", "paid plan", "pro feature").

## Exit codes

- 0 — bundle passes all checks
- 1 — one or more checks failed (reasons printed)
- 2 — fatal error (bad path, no read access)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Required draft files
_REQUIRED_FILES = [
    "team.draft.md",
    "pitfalls.draft.yaml",
    "skill-selection.draft.md",
    "personas.draft.md",
    "rationale.md",
]

# Bundle dir glob
_BUNDLE_PATTERN = re.compile(
    r".*/\.claude/plans/PLAN-\d{3}[^/]*/architect/round-\d+/?$"
)

# Real-person deny-list (curated, owner-extensible). Keep minimal —
# the goal is to catch obvious leaks, not maintain an exhaustive list.
_REAL_NAMES_DENY = {
    "Sam Altman",
    "Dario Amodei",
    "Elon Musk",
    "Sundar Pichai",
    "Satya Nadella",
    "Mark Zuckerberg",
    "Tim Cook",
    "Jeff Bezos",
    "Andy Jassy",
}

# Paid-tier marketing phrases (case-insensitive substrings)
_PAID_TIER_PHRASES = [
    "enterprise tier",
    "paid plan",
    "pro feature",
    "pricing tier",
    "premium subscription",
    "upgrade to pro",
    "enterprise plan",
]


def _load_yaml_pitfalls(path: Path) -> List[str]:
    """Return the list of pitfall ids from a YAML file.

    No PyYAML dependency: parse the simple list syntax used by every
    pitfalls.yaml in the repo.
    """
    ids: List[str] = []
    text = path.read_text(encoding="utf-8")
    in_pitfalls = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("pitfalls:"):
            in_pitfalls = True
            continue
        if in_pitfalls and stripped.startswith("- id:"):
            # Capture the id token (trim quotes)
            m = re.match(r"-\s*id:\s*[\"']?([^\"'\s]+)[\"']?", stripped)
            if m:
                ids.append(m.group(1))
    return ids


def _count_personas(path: Path) -> int:
    """Count `### ` headings in a markdown file."""
    text = path.read_text(encoding="utf-8")
    return sum(1 for line in text.splitlines() if line.startswith("### "))


def _count_skills(path: Path) -> int:
    """Count list lines that look like skill identifiers (`- \\`<id>\\``)."""
    text = path.read_text(encoding="utf-8")
    pat = re.compile(r"^- `[^`]+`")
    return sum(1 for line in text.splitlines() if pat.match(line.strip()))


def _scan_real_names(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8")
    found = []
    for name in _REAL_NAMES_DENY:
        if name in text:
            found.append(name)
    return found


def _scan_paid_tier(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8").lower()
    return [p for p in _PAID_TIER_PHRASES if p in text]


def validate(bundle_dir: Path) -> Tuple[bool, List[str]]:
    """Return (passed, reasons)."""
    reasons: List[str] = []

    # Check 1: dir naming
    abs_dir = str(bundle_dir.resolve())
    if not _BUNDLE_PATTERN.match(abs_dir + "/"):
        reasons.append(
            f"bundle dir does not match .claude/plans/PLAN-NNN/architect/round-N/: {bundle_dir}"
        )

    # Check 2: required files
    missing = [f for f in _REQUIRED_FILES if not (bundle_dir / f).is_file()]
    if missing:
        reasons.append(f"missing required files: {missing}")
        # Bail early — can't run content checks
        return (False, reasons)

    # Check 3: personas count
    personas = _count_personas(bundle_dir / "team.draft.md")
    if personas < 5:
        reasons.append(
            f"team.draft.md has {personas} '### ' personas; need >=5"
        )

    # Check 4: pitfalls count
    pitfall_ids = _load_yaml_pitfalls(bundle_dir / "pitfalls.draft.yaml")
    if len(pitfall_ids) < 10:
        reasons.append(
            f"pitfalls.draft.yaml has {len(pitfall_ids)} entries; need >=10"
        )

    # Check 5: skills count
    skills = _count_skills(bundle_dir / "skill-selection.draft.md")
    if skills < 3:
        reasons.append(
            f"skill-selection.draft.md lists {skills} skills; need >=3"
        )

    # Check 6: real names across all files
    for f in _REQUIRED_FILES:
        hits = _scan_real_names(bundle_dir / f)
        if hits:
            reasons.append(
                f"{f} mentions real-person name(s): {hits} "
                "(use fictional composite names per ADR-009)"
            )

    # Check 7: paid-tier phrases across all files
    for f in _REQUIRED_FILES:
        hits = _scan_paid_tier(bundle_dir / f)
        if hits:
            reasons.append(
                f"{f} contains paid-tier phrase(s): {hits} "
                "(squads must not advertise paid tiers per ADR-009)"
            )

    return (not reasons, reasons)


def main(argv=None) -> int:
    """CLI entrypoint — validate a squad-architect bundle against the contract."""
    parser = argparse.ArgumentParser(
        description="Validate an Agent Architect draft bundle"
    )
    parser.add_argument(
        "bundle_dir",
        help="Path to the architect/round-N/ directory",
    )
    args = parser.parse_args(argv)

    bundle_dir = Path(args.bundle_dir)
    if not bundle_dir.is_dir():
        print(
            f"FATAL: bundle dir does not exist or is not a directory: {bundle_dir}",
            file=sys.stderr,
        )
        return 2

    passed, reasons = validate(bundle_dir)
    if passed:
        print(f"✓ Bundle valid: {bundle_dir}")
        return 0

    print(f"❌ Bundle invalid: {bundle_dir}")
    for r in reasons:
        print(f"  - {r}")
    print()
    print("See ADR-009 §positioning + ADR-010 (canonical-edit sentinel)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
