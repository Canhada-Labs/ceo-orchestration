#!/usr/bin/env python3
"""KNOWN_ACTIONS floor lint (PLAN-086 Wave 0 / handoff §6).

Pre-commit lint that enforces `len(_KNOWN_ACTIONS) >= floor` against
`.claude/hooks/_lib/audit_emit.py`. Floor table is plan-versioned and
advances as each PLAN-NNN burn-down lands its audit-action additions.

Invoked by every Wave that mutates `_lib/audit_emit.py` (PLAN-086 Waves
A, B, C, E + future plans). Stdlib-only Python 3.9+ per CLAUDE.md §5.

Exit codes:
  0 - count >= floor
  1 - count < floor (regression)
  2 - parse failure / file missing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.filelock import FileLock  # type: ignore
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_EMIT = REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"

# Plan-versioned floor table. Each row pins a `len(_KNOWN_ACTIONS)` lower
# bound at that plan's ship. Lint takes the MAX(applicable floors).
_FLOOR_TABLE: Dict[str, int] = {
    "v1.18.0_baseline": 127,   # pre-PLAN-085 baseline (S106)
    "plan-085_ship":   147,    # PLAN-085 Wave G.1b + E.4 + C.1-C.3 (S111 v1.19.0)
    "plan-086_ship":   152,    # +5 actions (Wave E ceremony) — actual v1.20.0 ship
    "plan-088_ship":   164,    # placeholder per handoff §6 (god-mode)
}


def parse_known_actions_count(audit_emit_path: Path) -> Optional[int]:
    """Parse `_KNOWN_ACTIONS = { ... }` set literal and count members.

    Returns the count of non-comment, non-blank entries between the
    opening `{` and the matching closing `}`. Returns None on parse failure.
    """
    if not audit_emit_path.exists():
        return None
    try:
        text = audit_emit_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"^_KNOWN_ACTIONS\s*=\s*\{\s*$", text, re.MULTILINE)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0:
        return None
    body = text[start:i]
    count = 0
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Match `"action_name",` rows (allow trailing comments).
        if re.match(r'^"[a-z0-9_.-]+",?(?:\s*#.*)?$', line):
            count += 1
    return count


def resolve_floor(plan_tag: Optional[str]) -> Tuple[int, str]:
    """Compute floor by plan-tag selection or default to max-known floor."""
    if plan_tag and plan_tag in _FLOOR_TABLE:
        return _FLOOR_TABLE[plan_tag], plan_tag
    # Default: take the largest floor <= the plan tag, else baseline.
    if plan_tag and plan_tag.startswith("plan-"):
        # Use plan-085_ship as the live floor for in-flight work post-ship.
        return _FLOOR_TABLE["plan-085_ship"], "plan-085_ship (default)"
    return _FLOOR_TABLE["v1.18.0_baseline"], "v1.18.0_baseline"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="KNOWN_ACTIONS floor lint (PLAN-086 Wave 0)."
    )
    parser.add_argument(
        "--plan",
        default=None,
        help="Plan tag for floor lookup (e.g. plan-085_ship, plan-086_ship).",
    )
    parser.add_argument(
        "--floor",
        type=int,
        default=None,
        help="Explicit floor override (skips _FLOOR_TABLE lookup).",
    )
    parser.add_argument(
        "--audit-emit",
        type=Path,
        default=AUDIT_EMIT,
        help="Path to _lib/audit_emit.py (default: repo-relative).",
    )
    args = parser.parse_args()

    lock_path = REPO_ROOT / ".claude" / "scripts" / ".known_actions_floor.lock"
    locked_count: Optional[int] = None
    if FileLock is not None:
        try:
            with FileLock(str(lock_path), timeout=2.0):
                locked_count = parse_known_actions_count(args.audit_emit)
        except Exception:
            locked_count = parse_known_actions_count(args.audit_emit)
    else:
        locked_count = parse_known_actions_count(args.audit_emit)

    if locked_count is None:
        print(
            f"check_known_actions_floor: PARSE-FAIL {args.audit_emit}",
            file=sys.stderr,
        )
        return 2

    floor, src = (
        (args.floor, "cli-override")
        if args.floor is not None
        else resolve_floor(args.plan)
    )

    status = "OK" if locked_count >= floor else "REGRESSION"
    print(
        f"check_known_actions_floor: {status} "
        f"count={locked_count} floor={floor} src={src}"
    )
    return 0 if locked_count >= floor else 1


if __name__ == "__main__":
    sys.exit(main())
