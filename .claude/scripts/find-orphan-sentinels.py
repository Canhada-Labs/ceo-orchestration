#!/usr/bin/env python3
"""Sentinel orphan discovery audit (PLAN-085 Wave E.5).

Enumerates every ``approved.md`` (and amendment file) under
``.claude/plans/`` then cross-checks each against the sentinel discovery
patterns in ``check_canonical_edit._find_sentinels``. Any orphan
(found-on-disk but NOT discovered) is reported. ``--ci`` flag exits 1
on any novel orphan (CI gate).

The 5 PLAN-083 historical orphans are grandfathered via the E.1 glob
union. Any future orphan represents either (a) a forgotten ceremony
artifact or (b) an attacker-planted sentinel that the discovery glob
intentionally rejects.

Discipline: stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


def _enumerate_on_disk(repo_root: Path) -> List[Path]:
    """Return every approved.md (+ amendment) file under .claude/plans/."""
    base = repo_root / ".claude" / "plans"
    if not base.is_dir():
        return []
    results: List[Path] = []
    for pat in ("PLAN-*/**/approved.md", "PLAN-*/**/approved-amendment-*.md"):
        for p in base.glob(pat):
            if p.is_file() and not p.is_symlink():
                results.append(p)
    return sorted(set(results))


def _enumerate_discovered(repo_root: Path) -> List[Path]:
    """Return what _find_sentinels() actually discovers post-E.1."""
    try:
        from check_canonical_edit import _find_sentinels
        return _find_sentinels(repo_root)
    except Exception as e:
        print(f"FATAL: _find_sentinels import failed: {e}", file=sys.stderr)
        return []


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Find orphan sentinel files (PLAN-085 Wave E.5)"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="exit 1 if any novel orphan found (CI gate)",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=REPO_ROOT,
        help="repository root (defaults to script's resolved parent)",
    )
    args = parser.parse_args(argv)

    on_disk = _enumerate_on_disk(args.repo_root)
    discovered = set(_enumerate_discovered(args.repo_root))

    orphans = [p for p in on_disk if p not in discovered]

    print(f"on-disk sentinel files:   {len(on_disk)}")
    print(f"discovered (via E.1 glob): {len(discovered)}")
    print(f"orphans (gap):             {len(orphans)}")
    print()
    if orphans:
        print("ORPHAN sentinels (NOT trusted by canonical-edit hook):")
        for p in orphans:
            print(f"  - {p.relative_to(args.repo_root)}")
        if args.ci:
            return 1
    else:
        print("OK — no orphans.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
