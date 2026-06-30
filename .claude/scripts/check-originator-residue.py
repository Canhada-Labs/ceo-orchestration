#!/usr/bin/env python3
"""check-originator-residue.py — governance lint for template contamination.

PLAN-019 VP-F2 (part 4). Templates are a governance surface: if the
framework ships skill docstrings, team rosters, or pitfall catalogs
that mention the originator project's proper nouns (company name,
product name, repo slug, Owner GitHub handle, etc.), adopter projects
inherit that vocabulary and decisions.

This script scans distribution-facing content for a denylist of
originator-specific tokens and fails on any match. It is intended to
run in CI (wrapped by validate.yml) and locally before pushing.

It is deliberately SEPARATE from ``check-contamination.sh`` — that
script's denylist and scope are fixed by a long history of allowlist
entries; we do not want to perturb it. This script focuses on the
Owner-specific vocabulary flagged in the PLAN-018 audit (VP-F2).

stdlib only. Exit 0 if clean, 2 if matches found, 1 on internal
error.

Usage:
    python3 .claude/scripts/check-originator-residue.py
    # or
    python3 .claude/scripts/check-originator-residue.py --verbose
    # or with explicit repo root:
    CLAUDE_PROJECT_DIR=/path/to/repo \\
        python3 .claude/scripts/check-originator-residue.py

Denylist design:
    * Case-insensitive match on literal tokens that should NEVER appear
      in distribution-facing files.
    * Exemptions: CLAUDE_FULL.md, CLAUDE.md CHANGELOG, memory files,
      the README.md's "by @<handle>" attribution, audit records under
      .claude/plans/PLAN-*/audit/, docs/research/ (external audit
      research — allowed to name external repos/orgs), and
      ``.github/CODEOWNERS`` (intentionally carries the live handle).
    * Scope: .claude/skills/, .claude/team.md, .claude/frontend-team.md,
      .claude/pitfalls-catalog.yaml, templates/, .claude/commands/,
      .claude/task-chains.yaml.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# Originator-project proper nouns that must never land in distribution
# files. Keep this list MINIMAL — any new entry needs an ADR-level
# discussion. Uppercase/lowercase are matched case-insensitively below.
#
# These are EXAMPLE placeholders: a maintainer publishing their own fork
# should replace them with their personal handle / private project names
# so this lint keeps THEIR identity out of the distributed skill content.
# Real third-party brand names that are legitimate domain knowledge inside
# a squad (e.g. exchange names in a fintech squad) deliberately do NOT
# belong here — only the originator's own private identifiers do.
_DENYLIST: Tuple[str, ...] = (
    "example-owner",
    "@example-owner",
    "acme-internal",
)

# Distribution-facing roots (scanned). The script walks these and tests
# every text file.
_DEFAULT_SCAN_ROOTS: Tuple[str, ...] = (
    ".claude/skills",
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/pitfalls-catalog.yaml",
    ".claude/task-chains.yaml",
    ".claude/commands",
    "templates",
)

# Relative paths (prefix match) where the denylist is intentionally
# allowed. Examples: the repo's live CODEOWNERS carries the Owner
# handle; research audit files quote external/originator names;
# session-narrative files (CLAUDE_FULL.md) may carry the handle by
# design.
_EXEMPT_PREFIXES: Tuple[str, ...] = (
    ".github/CODEOWNERS",
    "CLAUDE.md",
    "CLAUDE_FULL.md",
    "docs/research/",
    "docs/rotation-log.md",
    ".claude/plans/",  # plans can quote audit material; skills cannot
    "scripts/",  # install/upgrade scripts legitimately carry owner fallback
)

# Binary / generated file extensions we refuse to scan.
_SKIP_EXTENSIONS: Tuple[str, ...] = (
    ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".tgz",
    ".pyc", ".pyo",
    ".jar", ".class",
    ".woff", ".woff2", ".ttf",
)


def _is_exempt(rel_path: str) -> bool:
    for prefix in _EXEMPT_PREFIXES:
        if rel_path == prefix or rel_path.startswith(prefix):
            return True
    return False


def _should_scan(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in _SKIP_EXTENSIONS:
        return False
    try:
        # Cheap binary-detection: reject files with NUL bytes in the
        # first 2 KB.
        with path.open("rb") as f:
            sample = f.read(2048)
        if b"\x00" in sample:
            return False
    except OSError:
        return False
    return True


def _iter_scan_targets(repo_root: Path, roots: Iterable[str]) -> Iterable[Path]:
    """Yield every file under the given roots, honoring skip rules."""
    for rel in roots:
        base = repo_root / rel
        if base.is_file():
            if _should_scan(base):
                yield base
            continue
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not _should_scan(path):
                continue
            yield path


def _build_pattern() -> "re.Pattern[str]":
    # Use word-boundary-ish guards so "acme" in "acmecoin" would still
    # match (intentional — substring of an originator-string is still
    # contamination).
    alternatives = "|".join(re.escape(tok) for tok in _DENYLIST)
    return re.compile(alternatives, flags=re.IGNORECASE)


def scan(
    repo_root: Path,
    roots: Iterable[str] = _DEFAULT_SCAN_ROOTS,
) -> List[Tuple[Path, int, str, str]]:
    """Return a list of (path, line_no, matched_token, line_preview).

    Exempt paths are skipped.
    """
    pattern = _build_pattern()
    findings: List[Tuple[Path, int, str, str]] = []
    for target in _iter_scan_targets(repo_root, roots):
        try:
            rel = str(target.relative_to(repo_root))
        except ValueError:
            rel = str(target)
        if _is_exempt(rel.replace(os.sep, "/")):
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                preview = line.strip()
                if len(preview) > 160:
                    preview = preview[:160] + "..."
                findings.append((target, idx, m.group(0), preview))
    return findings


def main(argv: List[str]) -> int:
    """CLI entrypoint — scan templates for residue of the originator repo."""
    parser = argparse.ArgumentParser(
        description="Lint for originator-project residue in "
        "distribution-facing framework files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print scanned file count even on clean runs.",
    )
    parser.add_argument(
        "--root",
        help="Optional repo root override (defaults to $CLAUDE_PROJECT_DIR "
        "or current working directory).",
    )
    args = parser.parse_args(argv)

    if args.root:
        repo_root = Path(args.root).resolve()
    else:
        env_root = os.environ.get("CLAUDE_PROJECT_DIR", "")
        repo_root = Path(env_root).resolve() if env_root else Path.cwd().resolve()

    if not repo_root.is_dir():
        print(
            f"ERROR: repo root '{repo_root}' is not a directory",
            file=sys.stderr,
        )
        return 1

    findings = scan(repo_root)
    if findings:
        print(
            "FAIL: originator-project residue detected "
            "(see PLAN-019 VP-F2):",
            file=sys.stderr,
        )
        for path, line_no, tok, preview in findings:
            try:
                rel = path.relative_to(repo_root)
            except ValueError:
                rel = path
            print(
                f"  {rel}:{line_no}  [{tok}]  {preview}",
                file=sys.stderr,
            )
        print(
            "\nFix: replace with {{PROJECT_NAME}} / {{OWNER_NAME}} / "
            "generic phrasing, then re-run.",
            file=sys.stderr,
        )
        return 2

    if args.verbose:
        # Cheap count of scanned files for CI logs.
        count = sum(1 for _ in _iter_scan_targets(repo_root, _DEFAULT_SCAN_ROOTS))
        print(f"PASS: no originator residue found ({count} files scanned).")
    else:
        print("PASS: no originator residue found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
