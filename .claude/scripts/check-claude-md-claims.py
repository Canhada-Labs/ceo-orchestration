#!/usr/bin/env python3
"""check-claude-md-claims — mechanical gate for CLAUDE.md claim drift.

PLAN-045 Wave 3 P0-14. Closes PLAN-044 F-06-01 + F-06-02 + F-06-03 +
F-06-06 + F-05-01 + F-15-04: 6 dimensions independently flagged that
CLAUDE.md claims (ADR count, skill count, test count, plan count) had
drifted from disk truth, and `validate-governance.sh` was not checking.

## What it does

Reads CLAUDE.md + a manifest of claim-vs-disk checks, extracts numeric
claims via regex, compares to the disk count, and exits:

- **0** if every claim matches (within a documented tolerance where
  applicable — e.g. "~X" or "X+" allow a small drift).
- **1** if any claim mismatches disk. Prints the first mismatch per
  check so operators can fix one at a time.

## Usage

```bash
python3 .claude/scripts/check-claude-md-claims.py
python3 .claude/scripts/check-claude-md-claims.py --verbose
python3 .claude/scripts/check-claude-md-claims.py --json        # CI mode
python3 .claude/scripts/check-claude-md-claims.py --file CLAUDE.md
```

## CI integration

Wire into `.github/workflows/validate.yml` as a separate step:

```yaml
- name: Check CLAUDE.md drift
  run: python3 .claude/scripts/check-claude-md-claims.py
```

Fail-CLOSED: a green exit means claims are verifiably within spec.

## Stdlib-only (ADR-002)

Uses ``pathlib``, ``re``, ``subprocess``, ``argparse``, ``json``. No
third-party deps. Compatible with Python ≥ 3.9.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[2]


@dataclass
class ClaimCheck:
    """One claim → disk-count comparison.

    Attributes:
        name: human-readable label, e.g. "ADR count".
        claim_regex: regex pattern to find the claim in CLAUDE.md.
            The first capture group MUST be the integer count.
        disk_count_fn: callable that returns the authoritative disk count.
        tolerance: int tolerance (absolute). Default 0 (exact match).
            Use >0 when the CLAUDE.md convention says "N+" or "~N".
        required_count: if >0, insist on finding at least this many
            matches in CLAUDE.md (catches claim-deletion regressions).
    """

    name: str
    claim_regex: str
    disk_count_fn: Callable[[], int]
    tolerance: int = 0
    required_count: int = 1


def _count_adrs() -> int:
    """Count .claude/adr/ADR-*.md excluding README.md and .shadow files."""
    files = list(_REPO.glob(".claude/adr/ADR-*.md"))
    return len([f for f in files if ".shadow" not in f.name])


def _count_skills() -> int:
    """Count SKILL.md across core + frontend + domains, excluding shadows."""
    files = list(_REPO.glob(".claude/skills/**/SKILL.md"))
    return len([f for f in files if ".shadow" not in f.name])


def _count_skills_by_tier(tier_glob: str) -> int:
    """Count SKILL.md under a specific tier glob, excluding shadows."""
    files = list(_REPO.glob(tier_glob))
    return len([f for f in files if ".shadow" not in f.name])


def _count_plans() -> int:
    """Count top-level PLAN-NNN-<slug>.md under .claude/plans/."""
    return len(list(_REPO.glob(".claude/plans/PLAN-*.md")))


def _count_tests() -> int:
    """Count pytest-collectable tests across the tree.

    Runs ``pytest --collect-only -q`` on the standard Wave 1 tree:
    ``.claude/hooks .claude/scripts tests``. Returns the integer from
    the "N tests collected" line, or 0 on any failure. The 0-on-failure
    ensures the check fails loudly (mismatch vs claim) rather than
    silently returning stale data.
    """
    cmd = [
        sys.executable, "-m", "pytest",
        ".claude/hooks", ".claude/scripts", "tests",
        "--collect-only", "-q",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=str(_REPO), capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return 0
    if proc.returncode != 0:
        return 0
    m = re.search(r"(\d+)\s+tests?\s+collected", proc.stdout)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Claim manifest
# ---------------------------------------------------------------------------
#
# Each ClaimCheck pairs a CLAUDE.md regex with a live disk count. Add
# entries here when CLAUDE.md gains a new verifiable numeric claim.
# Tolerance > 0 when CLAUDE.md conventionally uses "N+" or "~N" forms;
# tolerance = 0 forces exact match.

CHECKS: List[ClaimCheck] = [
    ClaimCheck(
        name="ADR count",
        # Matches "49 ADRs" or "64 ADRs" anywhere in CLAUDE.md.
        # Uses a word boundary to avoid matching dates.
        claim_regex=r"\b(\d+)\s+ADRs\b",
        disk_count_fn=_count_adrs,
        tolerance=0,
        required_count=1,
    ),
    ClaimCheck(
        name="Core skill count",
        # Matches "19 core" inside a skill-count breakdown like
        # "42 skills (19 core + 8 frontend + …)".
        claim_regex=r"\((\d+)\s+core",
        disk_count_fn=lambda: _count_skills_by_tier(
            ".claude/skills/core/*/SKILL.md"
        ),
        tolerance=0,
    ),
    ClaimCheck(
        name="Frontend skill count",
        claim_regex=r"(\d+)\s+frontend\s+\+",
        disk_count_fn=lambda: _count_skills_by_tier(
            ".claude/skills/frontend/*/SKILL.md"
        ),
        tolerance=0,
    ),
    ClaimCheck(
        name="Total skill count",
        # "42 skills" — tolerate small drift for domain-add churn.
        claim_regex=r"\*\*(\d+)\s+skills",
        disk_count_fn=_count_skills,
        tolerance=0,
    ),
    ClaimCheck(
        name="PLAN count",
        # "39 plan files" or "45 PLAN files"
        claim_regex=r"(\d+)\s+PLAN\s+files",
        disk_count_fn=_count_plans,
        tolerance=0,
        required_count=0,  # claim is optional; skip if absent
    ),
]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    claimed: Optional[int]
    disk: int
    tolerance: int
    detail: str


def run_checks(
    claude_md_path: Path,
    checks: List[ClaimCheck],
) -> List[CheckResult]:
    """Run all checks; return structured results."""
    if not claude_md_path.is_file():
        return [
            CheckResult(
                name="CLAUDE.md present",
                passed=False,
                claimed=None,
                disk=0,
                tolerance=0,
                detail=f"CLAUDE.md not found at {claude_md_path}",
            )
        ]
    text = claude_md_path.read_text(encoding="utf-8")

    out: List[CheckResult] = []
    for c in checks:
        matches = re.findall(c.claim_regex, text)
        disk = c.disk_count_fn()
        if not matches:
            passed = c.required_count == 0
            out.append(CheckResult(
                name=c.name,
                passed=passed,
                claimed=None,
                disk=disk,
                tolerance=c.tolerance,
                detail=(
                    "claim not found in CLAUDE.md"
                    if not passed
                    else "optional claim absent (ok)"
                ),
            ))
            continue
        try:
            claimed = int(matches[0])
        except ValueError:
            out.append(CheckResult(
                name=c.name,
                passed=False,
                claimed=None,
                disk=disk,
                tolerance=c.tolerance,
                detail=f"regex matched non-int: {matches[0]!r}",
            ))
            continue
        diff = abs(claimed - disk)
        if diff <= c.tolerance:
            out.append(CheckResult(
                name=c.name,
                passed=True,
                claimed=claimed,
                disk=disk,
                tolerance=c.tolerance,
                detail="ok",
            ))
        else:
            out.append(CheckResult(
                name=c.name,
                passed=False,
                claimed=claimed,
                disk=disk,
                tolerance=c.tolerance,
                detail=(
                    f"CLAUDE.md claims {claimed} but disk has {disk} "
                    f"(diff {diff} > tolerance {c.tolerance})"
                ),
            ))
    return out


def format_text(results: List[CheckResult]) -> str:
    """Format claim-check results as one PASS/FAIL line per result."""
    lines: List[str] = []
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.claimed is None:
            lines.append(f"[{status}] {r.name}: {r.detail}")
        else:
            lines.append(
                f"[{status}] {r.name}: claim={r.claimed} disk={r.disk} "
                f"(tolerance={r.tolerance}) — {r.detail}"
            )
    return "\n".join(lines)


def format_json(results: List[CheckResult]) -> str:
    """Format claim-check results as a pretty-printed JSON array."""
    payload = [
        {
            "name": r.name,
            "passed": r.passed,
            "claimed": r.claimed,
            "disk": r.disk,
            "tolerance": r.tolerance,
            "detail": r.detail,
        }
        for r in results
    ]
    return json.dumps(payload, indent=2)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — validate numerical claims in CLAUDE.md against disk truth."""
    parser = argparse.ArgumentParser(
        description="Check CLAUDE.md numeric claims against disk."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=_REPO / "CLAUDE.md",
        help="Path to CLAUDE.md (default: repo root)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print even on pass (default: only on fail)",
    )
    args = parser.parse_args(argv)

    results = run_checks(args.file, CHECKS)
    all_pass = all(r.passed for r in results)

    if args.json:
        print(format_json(results))
    else:
        if args.verbose or not all_pass:
            print(format_text(results))
        if not all_pass:
            print("")
            print("FAIL: CLAUDE.md drift detected. Run with --verbose for all.")
            print("See PLAN-045 P0-14 for remediation workflow (Gate-1 cache")
            print("discipline — edit CLAUDE.md only at session closeout).")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
