#!/usr/bin/env python3
"""PLAN-066 DIM-02 — SPEC drift guard between PLAN-SCHEMA.md and SPEC/v1/plan.schema.md.

The published `SPEC/v1/plan.schema.md` is a normative summary mirror
of `.claude/plans/PLAN-SCHEMA.md`. They drift independently when a
contributor updates one without the other.

This script asserts that a hardcoded set of canonical invariants
(frontmatter fields, lifecycle states, reopen mechanism, subdirectory
namespace) appears as word-boundary tokens in BOTH files. If any
invariant is missing from either surface, the script exits non-zero
with a human-readable diff.

The invariant list is the single source of truth for drift detection.
Adding a new invariant to PLAN-SCHEMA requires updating this script
AND adding a mention to SPEC/v1/plan.schema.md (caught by paired test).

Exit codes:
    0   Both surfaces mention every canonical invariant.
    1   Drift detected (one or more invariants missing on either side).

If a surface file is missing or unreadable, FileNotFoundError /
OSError propagates as a Python traceback (PLAN-066 Round 1 C5 — exit
codes >1 collapse to "step failed" in GitHub Actions UI).

Usage:
    python3 .claude/scripts/check-spec-drift.py
    python3 .claude/scripts/check-spec-drift.py --verbose
    python3 .claude/scripts/check-spec-drift.py --plan-schema PATH --spec PATH
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PLAN_SCHEMA = REPO_ROOT / ".claude" / "plans" / "PLAN-SCHEMA.md"
DEFAULT_SPEC = REPO_ROOT / "SPEC" / "v1" / "plan.schema.md"

# Canonical invariants. Each must be mentioned (word-boundary) in BOTH
# PLAN-SCHEMA.md and SPEC/v1/plan.schema.md. Updating this list requires
# updating both surfaces (paired test catches drift).
CANONICAL_INVARIANTS: List[Tuple[str, str]] = [
    # (category, token)
    ("frontmatter_required", "id"),
    ("frontmatter_required", "title"),
    ("frontmatter_required", "status"),
    ("frontmatter_required", "created"),
    ("frontmatter_required", "owner"),
    ("frontmatter_required", "depends_on"),
    ("lifecycle_state", "draft"),
    ("lifecycle_state", "reviewed"),
    ("lifecycle_state", "executing"),
    ("lifecycle_state", "done"),
    ("lifecycle_state", "abandoned"),
    ("lifecycle_state", "refused"),
    ("reopen_mechanism", "reopen_via"),
    ("reopen_mechanism", "reopen_trigger"),
    ("subdirectory_namespace", "examples"),
    ("subdirectory_namespace", "archive"),
]


def _read_or_raise(path: Path) -> str:
    """Read file contents; let FileNotFoundError / OSError propagate.

    PLAN-066 Phase 2 (Round 1 C5): exit-code 2 was invisible to GitHub
    Actions (any non-zero collapses to "fail" in step UI). Letting the
    Python traceback surface gives a clearer CI annotation than a custom
    exit code that disappears.
    """
    return path.read_text(encoding="utf-8")


def _mentions(body: str, token: str) -> bool:
    """Word-boundary match for token in body."""
    return bool(re.search(rf"\b{re.escape(token)}\b", body))


def _check(plan_schema_body: str, spec_body: str) -> List[Tuple[str, str, str]]:
    """Return a list of (category, token, surface) tuples for missing items."""
    missing: List[Tuple[str, str, str]] = []
    for category, token in CANONICAL_INVARIANTS:
        if not _mentions(plan_schema_body, token):
            missing.append((category, token, "PLAN-SCHEMA.md"))
        if not _mentions(spec_body, token):
            missing.append((category, token, "SPEC/v1/plan.schema.md"))
    return missing


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--plan-schema",
        type=Path,
        default=DEFAULT_PLAN_SCHEMA,
        help="Path to PLAN-SCHEMA.md (default: .claude/plans/PLAN-SCHEMA.md)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC,
        help="Path to SPEC plan.schema.md (default: SPEC/v1/plan.schema.md)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show passing checks too."
    )
    args = parser.parse_args(argv)

    plan_schema_body = _read_or_raise(args.plan_schema)
    spec_body = _read_or_raise(args.spec)

    missing = _check(plan_schema_body, spec_body)

    if args.verbose:
        print(
            f"Checked {len(CANONICAL_INVARIANTS)} canonical invariants "
            f"across:\n  - {args.plan_schema}\n  - {args.spec}"
        )

    if not missing:
        if args.verbose:
            print("OK: SPEC parity. No drift detected.")
        return 0

    print("FAIL: SPEC drift detected.", file=sys.stderr)
    print(
        f"{len(missing)} invariant(s) missing across surfaces:",
        file=sys.stderr,
    )
    for category, token, surface in missing:
        print(f"  [{category}] '{token}' missing in {surface}", file=sys.stderr)
    print(
        "\nFix: add the missing invariant to the surface(s) above, OR "
        "update CANONICAL_INVARIANTS in this script if the invariant was "
        "intentionally retired (and update the paired test).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
