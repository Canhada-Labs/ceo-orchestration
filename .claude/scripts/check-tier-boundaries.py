#!/usr/bin/env python3
"""check-tier-boundaries.py — enforce the core → domains dependency rule.

No file under `.claude/skills/core/**` or `.claude/skills/frontend/**` may
reference a path like `.claude/skills/domains/<name>/...` in prose. The
rule exists so that core/frontend skills remain portable across projects
that don't install a particular domain profile.

## Exempt from the check (allowlist)

- Code examples inside fenced blocks (``` or ~~~) — illustrative only
- YAML block scalars (`content: |` with indented payload) — test input
- `frontend-data-layer/SKILL.md` referencing its domain extension (the
  legitimate extension pattern documented in the frontend team.md)
- `.claude/skills/*/benchmarks/**/*.yaml` — scenario YAML files
- `.claude/plans/examples/**` — fixture content may reference any path
- `.claude/plans/PLAN-*.md` — plans reference any path as planning
- This script itself + its test file
- README / INSTALL that describe the architecture

## Detection pattern

Non-fenced line matching:
    `domains/<kebab>/skills/<kebab>`
    OR
    `../../domains/` (and longer relative paths)

The non-fenced state is tracked by a simple fence-open/close state machine
that supports backticks (``` or ````) and tildes (~~~ or ~~~~).

## Exit codes

- 0 — clean, no violations
- 1 — violations found (printed as path:line:snippet)
- 2 — fatal error (bad args, can't read a file)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Sprint 3 Item E: share file walking with contamination check via _lib.
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.file_walker import FileWalker  # noqa: E402


# Detection: domain path references in non-fenced prose.
# Matches both forward references (domains/foo/skills/bar) and relative
# (../../domains/..., .../domains/foo...).
_DOMAIN_REF_RE = re.compile(
    r"(?:domains/[a-z][a-z0-9-]*/skills/[a-z][a-z0-9-]*"
    r"|\.\./(?:\.\./)*domains/[a-z][a-z0-9-]*)"
)

# Fenced block open/close — backticks or tildes, 3+ of them.
_FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")


# Paths where a core/frontend skill is allowed to reference a domain
# (legitimate extension patterns).
_FILE_ALLOWLIST_CONTAINS = {
    # frontend/frontend-data-layer/SKILL.md documents the extension
    # pattern explicitly, with live references to fintech extension.
    "frontend/frontend-data-layer/SKILL.md",
    # frontend-patterns similarly references fintech
    "frontend/frontend-patterns/SKILL.md",
}


def is_allowlisted(path: Path) -> bool:
    """Return True if the file is in a zone where domain refs are allowed."""
    s = str(path)
    for token in _FILE_ALLOWLIST_CONTAINS:
        if token in s:
            return True
    return False


def preprocess_yaml(text: str) -> str:
    """Strip `content: |` block scalar payloads from YAML files.

    Benchmark scenarios contain code samples in `content: |` blocks that
    may mention domain paths as test input. Those are NOT tier-boundary
    violations, so we erase the block scalar bodies before running the
    fence state machine.

    Heuristic (simple and deterministic):
    - A line matching `^\\s*content:\\s*\\|` starts a block scalar
    - Subsequent lines that are indented deeper than the `content:` line
      are part of the block and are replaced with a blank line
    - The first line indented at or below the `content:` indent level
      ends the block
    """
    out = []
    in_block = False
    block_indent = -1
    for line in text.split("\n"):
        if not in_block:
            m = re.match(r"^(\s*)content:\s*\|", line)
            if m:
                block_indent = len(m.group(1))
                in_block = True
                out.append(line)
                continue
            out.append(line)
        else:
            if line.strip() == "":
                out.append("")
                continue
            # Count leading whitespace
            stripped_idx = len(line) - len(line.lstrip())
            if stripped_idx <= block_indent:
                # End of block scalar
                in_block = False
                block_indent = -1
                out.append(line)
            else:
                # Inside the block — erase
                out.append("")
    return "\n".join(out)


def find_violations(
    path: Path,
) -> List[Tuple[int, str, str]]:
    """Return a list of (lineno, line, match_text) violations in `path`."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[check-tier-boundaries] WARN: cannot read {path}: {e}", file=sys.stderr)
        return []

    # YAML preprocessing for scenario files
    if path.suffix in (".yaml", ".yml"):
        text = preprocess_yaml(text)

    violations: List[Tuple[int, str, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), start=1):
        if _FENCE_OPEN_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _DOMAIN_REF_RE.search(line)
        if match:
            violations.append((lineno, line.rstrip(), match.group(0)))
    return violations


def discover_files(repo_root: Path) -> List[Path]:
    """Walk core/ and frontend/ skill trees (not domains/).

    Refactored in Sprint 3 Item E to delegate iteration to the shared
    FileWalker (`.claude/hooks/_lib/file_walker.py`). The walker handles
    suffix filtering and the benchmarks/ subdir skip; this function
    remains to compose the two tier-specific walkers.
    """
    targets: List[Path] = []
    for tier in ("core", "frontend"):
        tier_root = repo_root / ".claude" / "skills" / tier
        if not tier_root.is_dir():
            continue
        walker = FileWalker(
            repo_root=tier_root,
            mode="filesystem",
            suffixes={".md", ".yaml", ".yml"},
            skip_subdir_names={"benchmarks"},
        )
        targets.extend(walker.iter_files())
    return targets


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert core/frontend skills do not leak into domains/."""
    parser = argparse.ArgumentParser(
        prog="check-tier-boundaries.py",
        description=(
            "Enforce core/frontend → domains import invariant. Core and "
            "frontend skills may not reference domain paths in prose."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Path to repo root (default: auto-detect from script path)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print every file checked"
    )
    args = parser.parse_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent
    if not (repo_root / ".claude" / "skills").is_dir():
        print(
            f"ERROR: .claude/skills not found under {repo_root}",
            file=sys.stderr,
        )
        return 2

    files = discover_files(repo_root)
    total_violations = 0
    for path in files:
        if is_allowlisted(path):
            if args.verbose:
                print(f"  (allowlisted) {path.relative_to(repo_root)}")
            continue
        violations = find_violations(path)
        if args.verbose:
            print(f"  checked {path.relative_to(repo_root)}")
        for lineno, line, match in violations:
            rel = path.relative_to(repo_root)
            print(f"{rel}:{lineno}:{match}  {line[:120]}")
            total_violations += 1

    if total_violations == 0:
        print(f"✓ Tier boundaries clean ({len(files)} files scanned)")
        return 0
    print(f"❌ Found {total_violations} tier-boundary violation(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
