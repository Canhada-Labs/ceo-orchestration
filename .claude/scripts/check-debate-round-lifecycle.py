#!/usr/bin/env python3
"""check-debate-round-lifecycle.py — validate debate round contiguity.

PLAN-019 F-CHAOS-9. Walks `.claude/plans/PLAN-NNN/debate/round-N/` and
`.claude/plans/PLAN-NNN/architect/round-N/` directories, and confirms:

1. Round numbering is **contiguous** starting at 1 (no gaps: round-1
   must exist before round-2, etc.).
2. `debate/round-N/` must contain a `consensus.md` AT LEAST ONCE the
   next round exists (round-1 can be in flight without consensus.md,
   but the presence of round-2 means round-1 must have converged).
3. `architect/round-N/` must contain an `approved.md` if it is not
   the in-flight round (same logic: round-1 can be unapproved if it
   is the only round; round-2 existence implies round-1 approved.md).
4. Round numbers must be zero-positive integers (no `round-0`, no
   `round-01` padded names — exactly `round-<N>` with N >= 1 unpadded).

Exit codes:
    0  valid
    1  broken lifecycle — one or more errors

Usage:
    python3 .claude/scripts/check-debate-round-lifecycle.py [--plans-dir PATH]

stdlib only; Python 3.9 compatible.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PLANS_DIR = REPO_ROOT / ".claude" / "plans"

PLAN_DIR_RE = re.compile(r"^PLAN-(\d{3})$")
ROUND_DIR_RE = re.compile(r"^round-(\d+)$")


def _collect_rounds(parent: Path) -> List[Tuple[int, Path]]:
    """List (round_number, path) for each round-<N> subdir under `parent`.

    Returns sorted by round number ascending. Flags rounds with padded
    numbers (e.g. round-01) as errors via a dedicated caller check.
    """
    out: List[Tuple[int, Path]] = []
    if not parent.is_dir():
        return out
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        m = ROUND_DIR_RE.match(child.name)
        if not m:
            # Unknown subdir — caller reports separately.
            continue
        n_str = m.group(1)
        # Reject zero-padded names like round-01, round-02.
        # Exception: round-0 is rejected too (below).
        if len(n_str) > 1 and n_str.startswith("0"):
            # Caller will flag.
            out.append((-int(n_str), child))
            continue
        try:
            n = int(n_str)
        except ValueError:
            continue
        out.append((n, child))
    out.sort(key=lambda t: t[0])
    return out


def validate_plan(plan_dir: Path) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings) for one PLAN-NNN directory."""
    errors: List[str] = []
    warnings: List[str] = []

    for kind, sentinel_name in (("debate", "consensus.md"), ("architect", "approved.md")):
        parent = plan_dir / kind
        if not parent.is_dir():
            continue  # It's fine to not have both.

        # Flag unexpected subdir names (non round-<N>).
        for child in parent.iterdir():
            if child.is_dir() and not ROUND_DIR_RE.match(child.name):
                warnings.append(
                    f"{child}: not a round-<N> directory (ignored)"
                )

        rounds = _collect_rounds(parent)
        if not rounds:
            continue

        # Padded / zero / non-positive numbers.
        for n, path in rounds:
            if n <= 0:
                if n == 0:
                    errors.append(f"{path}: round-0 is invalid (rounds start at 1)")
                else:
                    errors.append(
                        f"{path}: zero-padded round name (use round-{abs(n)} without leading zero)"
                    )

        valid_rounds = [(n, p) for n, p in rounds if n >= 1 and not (len(p.name.split("-")[1]) > 1 and p.name.split("-")[1].startswith("0"))]
        numbers = sorted({n for n, _ in valid_rounds})
        if not numbers:
            continue

        # Contiguity: must start at 1, no gaps.
        if numbers[0] != 1:
            errors.append(
                f"{parent}: first round is round-{numbers[0]} — must start at round-1"
            )
        for prev, curr in zip(numbers, numbers[1:]):
            if curr != prev + 1:
                errors.append(
                    f"{parent}: gap between round-{prev} and round-{curr} "
                    f"(missing round-{prev + 1})"
                )

        # Sentinel presence for all-but-last (in-flight) rounds.
        # Exception: if a later round exists, earlier rounds MUST have the
        # sentinel because they implicitly converged.
        if numbers:
            for n in numbers[:-1]:
                round_path = parent / f"round-{n}"
                if not (round_path / sentinel_name).is_file():
                    errors.append(
                        f"{round_path}: later round exists but missing "
                        f"`{sentinel_name}` — previous round must have converged"
                    )
            # Last round: sentinel optional (round may be in-flight).

    return errors, warnings


def validate_all(plans_dir: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if not plans_dir.is_dir():
        return [f"plans dir not found: {plans_dir}"], []
    for child in sorted(plans_dir.iterdir()):
        if not child.is_dir():
            continue
        if not PLAN_DIR_RE.match(child.name):
            continue
        e, w = validate_plan(child)
        errors.extend(e)
        warnings.extend(w)
    return errors, warnings


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — enforce debate round lifecycle state transitions."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--plans-dir",
        type=Path,
        default=DEFAULT_PLANS_DIR,
        help=f"Plans directory (default: {DEFAULT_PLANS_DIR})",
    )
    args = p.parse_args(argv)

    errors, warnings = validate_all(args.plans_dir)

    for w in warnings:
        sys.stderr.write(f"WARN: {w}\n")
    for e in errors:
        sys.stderr.write(f"ERROR: {e}\n")

    if errors:
        sys.stderr.write(
            f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)\n"
        )
        return 1
    sys.stderr.write(
        f"PASS: debate/architect round lifecycle clean ({len(warnings)} warning(s))\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
