#!/usr/bin/env python3
"""
check-agents-md.py — verify AGENTS.md (cross-LLM reviewer contract) freshness.

AGENTS.md at the repo root is the contract read by the pair-rail reviewer
(ADR-107). Its §3 repo map and §4 guarded-surfaces table are derived from
disk, so they can drift when directories are renamed or guarded files move.
This gate keeps the contract honest.

Checks:

    (a) AGENTS.md exists at the repo root;
    (b) both marked sections parse (markers present, at least one path row
        each) — a contract the checker cannot parse is drift, not a pass;
    (c) every directory named in the repo-map section exists on disk and
        IS a directory;
    (d) every guarded-surface path listed exists on disk (file or dir).

Parsing contract (kept deliberately dumb, stdlib-only): inside each marked
region, the FIRST backtick-quoted cell of every markdown table row is a
repo-root-relative path. Rows without a backtick cell (header, separator)
are skipped.

Exit codes:
    0 — clean
    1 — drift found
    2 — usage / arg error

Output modes:
    text (default, human)
    json (machine — {"problems":[{"kind","path","detail"}],
                     "checked_paths": N, "problem_count": N})
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import List, Optional, Sequence

AGENTS_MD = "AGENTS.md"

REPO_MAP_BEGIN = "<!-- agents-md:repo-map:begin -->"
REPO_MAP_END = "<!-- agents-md:repo-map:end -->"
GUARDED_BEGIN = "<!-- agents-md:guarded:begin -->"
GUARDED_END = "<!-- agents-md:guarded:end -->"

_CELL_PATH_RE = re.compile(r"`([^`]+)`")


# ---------- parsing ---------------------------------------------------------


def extract_section(text: str, begin: str, end: str) -> Optional[str]:
    """Return the text between the begin/end markers, or None if absent."""
    start = text.find(begin)
    if start == -1:
        return None
    stop = text.find(end, start + len(begin))
    if stop == -1:
        return None
    return text[start + len(begin) : stop]


def extract_paths(section: str) -> List[str]:
    """First backtick-quoted cell of each table row, trailing '/' stripped."""
    out: List[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        m = _CELL_PATH_RE.search(line)
        if not m:
            continue  # header / separator row
        path = m.group(1).strip().rstrip("/")
        if path:
            out.append(path)
    return out


# ---------- checks ----------------------------------------------------------


def check_repo(root: Path) -> List[dict]:
    """Return list of problem dicts ({"kind","path","detail"}); empty = clean."""
    agents = root / AGENTS_MD
    if not agents.is_file():
        return [
            {
                "kind": "missing-agents-md",
                "path": AGENTS_MD,
                "detail": f"{AGENTS_MD} not found at repo root {root}",
            }
        ]

    try:
        text = agents.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [
            {
                "kind": "unreadable-agents-md",
                "path": AGENTS_MD,
                "detail": f"cannot read {AGENTS_MD}: {e}",
            }
        ]

    problems: List[dict] = []
    problems.extend(_check_section(
        root, text, REPO_MAP_BEGIN, REPO_MAP_END,
        label="repo-map", require_dir=True,
    ))
    problems.extend(_check_section(
        root, text, GUARDED_BEGIN, GUARDED_END,
        label="guarded-surfaces", require_dir=False,
    ))
    return problems


def _check_section(
    root: Path,
    text: str,
    begin: str,
    end: str,
    label: str,
    require_dir: bool,
) -> List[dict]:
    section = extract_section(text, begin, end)
    if section is None:
        return [
            {
                "kind": "missing-markers",
                "path": AGENTS_MD,
                "detail": f"{label} markers not found ({begin} … {end})",
            }
        ]
    paths = extract_paths(section)
    if not paths:
        return [
            {
                "kind": "empty-section",
                "path": AGENTS_MD,
                "detail": f"{label} section parsed to zero path rows",
            }
        ]
    problems: List[dict] = []
    for rel in paths:
        # Codex pair-rail P2 (S261): the contract says rows are repo-root-
        # relative. An absolute path or a `..` escape must surface as DRIFT,
        # never resolve outside the repo and pass as false-green.
        pure = PurePosixPath(rel)
        if pure.is_absolute() or ".." in pure.parts:
            problems.append(
                {
                    "kind": f"{label}-escapes-root",
                    "path": rel,
                    "detail": "row is not repo-root-relative (absolute or contains '..')",
                }
            )
            continue
        candidate = root / rel
        if not candidate.exists():
            problems.append(
                {
                    "kind": f"{label}-missing",
                    "path": rel,
                    "detail": f"listed in {label} section but not on disk",
                }
            )
        elif require_dir and not candidate.is_dir():
            problems.append(
                {
                    "kind": f"{label}-not-a-dir",
                    "path": rel,
                    "detail": f"listed in {label} section but is not a directory",
                }
            )
    return problems


def count_listed_paths(root: Path) -> int:
    """How many paths AGENTS.md lists (0 if the file/markers are absent)."""
    agents = root / AGENTS_MD
    try:
        text = agents.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    total = 0
    for begin, end in ((REPO_MAP_BEGIN, REPO_MAP_END), (GUARDED_BEGIN, GUARDED_END)):
        section = extract_section(text, begin, end)
        if section is not None:
            total += len(extract_paths(section))
    return total


# ---------- main ------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint — flag AGENTS.md drift against the on-disk tree."""
    parser = argparse.ArgumentParser(
        description="Verify AGENTS.md repo-map + guarded-surface paths exist on disk.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root (default: nearest ancestor with a .git dir; else cwd).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    root = (args.root or _find_repo_root(Path.cwd())).resolve()
    if not root.is_dir():
        print(f"error: --root is not a directory: {root}", file=sys.stderr)
        return 2

    problems = check_repo(root)
    checked = count_listed_paths(root)

    if args.format == "json":
        payload = {
            "checked_paths": checked,
            "problem_count": len(problems),
            "problems": problems,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if not problems:
            print(f"OK: AGENTS.md fresh — {checked} listed path(s) all exist.")
        else:
            print(f"DRIFT: {len(problems)} problem(s) in {AGENTS_MD}:")
            for p in problems:
                print(f"  [{p['kind']}] {p['path']}  — {p['detail']}")
            print("")
            print("Hint: AGENTS.md is derived from disk. If a path was renamed")
            print("or removed, update the table row in the same change.")

    return 1 if problems else 0


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


if __name__ == "__main__":
    sys.exit(main())
