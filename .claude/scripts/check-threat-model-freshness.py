#!/usr/bin/env python3
"""check-threat-model-freshness — status-flip accepted->stale on ADR drift.

PLAN-014 Phase C.4 (ADJ-021). Counts new in-scope ADRs merged since
the threat-model.md ``last_updated`` date. If >=2 new ADRs have landed
without a corresponding threat-model review, **flips** the status field
from ``accepted`` to ``stale`` (not just warns).

Emits ``threat_model_freshness_breach`` audit event on breach via
``_lib.audit_emit`` if available (fail-open if import fails).

## Exit codes

  0 — threat model is fresh (< 2 new in-scope ADRs since last_updated)
  1 — STALE: >=2 new in-scope ADRs without review; status flipped
  2 — internal error (missing file, parse failure, git error)

## Algorithm

1. Parse ``last_updated`` date from threat-model.md frontmatter.
2. List all ADR files in ``.claude/adr/ADR-*.md``.
3. For each ADR, use ``git log --diff-filter=A --format=%aI`` to find
   the commit date when the file was first added.
4. Count ADRs added AFTER ``last_updated`` whose status is not
   ``SUPERSEDED`` and not tagged ``N/A`` in the per-ADR table.
5. If count >= threshold (default 2), flip status and emit audit event.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

THREAT_MODEL_REL = Path("docs/threat-model.md")
ADR_DIR_REL = Path(".claude/adr")
DEFAULT_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk up from start to find the repo root (.git marker)."""
    p = (start or Path.cwd()).resolve()
    while p != p.parent:
        if (p / ".git").exists() or (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    return Path.cwd()


def parse_last_updated(content: str) -> Optional[date]:
    """Extract the last_updated date from threat-model.md frontmatter.

    Looks for '**Last updated:** YYYY-MM-DD' line.
    Falls back to '**Date:** YYYY-MM-DD' if last_updated missing.
    """
    # Try last_updated first
    m = re.search(
        r"^\*\*Last updated:\*\*\s+(\d{4}-\d{2}-\d{2})",
        content,
        re.MULTILINE,
    )
    if m:
        return date.fromisoformat(m.group(1))
    # Fallback to Date
    m = re.search(
        r"^\*\*Date:\*\*\s+(\d{4}-\d{2}-\d{2})",
        content,
        re.MULTILINE,
    )
    if m:
        return date.fromisoformat(m.group(1))
    return None


def parse_status(content: str) -> str:
    """Extract the Status field value."""
    m = re.search(r"^\*\*Status:\*\*\s+(\S+)", content, re.MULTILINE)
    return m.group(1).rstrip() if m else ""


def list_adr_files(repo_root: Path) -> List[Path]:
    """List all ADR-*.md files in the ADR directory."""
    adr_dir = repo_root / ADR_DIR_REL
    if not adr_dir.is_dir():
        return []
    return sorted(adr_dir.glob("ADR-*.md"))


def get_file_first_commit_date(
    repo_root: Path, file_path: Path
) -> Optional[date]:
    """Get the date when a file was first added to git.

    Uses git log to find the earliest commit touching the file.
    Returns None if file is untracked or git fails.
    """
    rel = file_path.relative_to(repo_root)
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%aI",
                "--follow",
                "--",
                str(rel),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        # Last line is the earliest (git log is newest-first)
        lines = result.stdout.strip().splitlines()
        date_str = lines[-1].strip()
        # Parse ISO date (may have timezone info)
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.date()
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None


def is_adr_superseded(adr_path: Path) -> bool:
    """Check if an ADR has status SUPERSEDED."""
    try:
        content = adr_path.read_text(encoding="utf-8")
        return bool(re.search(r"\*\*Status:\*\*.*SUPERSEDED", content, re.IGNORECASE))
    except OSError:
        return False


def count_new_adrs_since(
    repo_root: Path, since_date: date, use_git: bool = True
) -> Tuple[int, List[str]]:
    """Count ADR files added after since_date.

    Returns (count, list_of_new_adr_names).
    Excludes SUPERSEDED ADRs.
    """
    new_adrs: List[str] = []
    for adr_path in list_adr_files(repo_root):
        if is_adr_superseded(adr_path):
            continue
        if use_git:
            commit_date = get_file_first_commit_date(repo_root, adr_path)
            if commit_date is None:
                # Untracked file — treat as new (conservative)
                new_adrs.append(adr_path.name)
                continue
            if commit_date > since_date:
                new_adrs.append(adr_path.name)
        else:
            # Fallback: use file mtime
            mtime = datetime.fromtimestamp(adr_path.stat().st_mtime).date()
            if mtime > since_date:
                new_adrs.append(adr_path.name)
    return len(new_adrs), new_adrs


def flip_status_to_stale(repo_root: Path) -> bool:
    """Rewrite threat-model.md status from accepted to stale.

    Returns True if flip was performed.
    """
    path = repo_root / THREAT_MODEL_REL
    try:
        content = path.read_text(encoding="utf-8")
        new_content = re.sub(
            r"^(\*\*Status:\*\*)\s+accepted",
            r"\1 stale",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if new_content != content:
            path.write_text(new_content, encoding="utf-8")
            return True
    except OSError:
        pass
    return False


def emit_freshness_breach(new_adr_count: int, new_adrs: List[str]) -> None:
    """Emit threat_model_freshness_breach audit event (fail-open)."""
    try:
        _hooks_dir = Path(__file__).resolve().parents[1] / "hooks"
        if str(_hooks_dir) not in sys.path:
            sys.path.insert(0, str(_hooks_dir))
        from _lib.audit_emit import _write_event  # type: ignore

        _write_event(
            "threat_model_freshness_breach",
            new_adr_count=new_adr_count,
            new_adrs=new_adrs[:10],  # cap for payload size
            threshold=DEFAULT_THRESHOLD,
        )
    except Exception:
        # Fail-open: audit emission must never block CI
        pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert threat-model docs are fresher than their referents."""
    parser = argparse.ArgumentParser(
        description="Check threat-model.md freshness against ADR timeline."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (auto-detected if omitted).",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Number of new ADRs that triggers stale flip (default: {DEFAULT_THRESHOLD}).",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Use file mtime instead of git log (for testing).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report but do not flip status.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root or find_repo_root()
    tm_path = repo_root / THREAT_MODEL_REL

    if not tm_path.is_file():
        print(f"ERROR: threat-model.md not found at {tm_path}", file=sys.stderr)
        return 2

    content = tm_path.read_text(encoding="utf-8")
    status = parse_status(content)
    last_updated = parse_last_updated(content)

    if last_updated is None:
        print(
            "ERROR: could not parse last_updated or Date from threat-model.md",
            file=sys.stderr,
        )
        return 2

    if status not in ("accepted", "stale"):
        if args.verbose:
            print(f"SKIP: status is '{status}' (not accepted/stale). No check needed.")
        return 0

    use_git = not args.no_git
    count, new_adrs = count_new_adrs_since(repo_root, last_updated, use_git=use_git)

    if args.verbose:
        print(f"Threat model last_updated: {last_updated}")
        print(f"New in-scope ADRs since then: {count}")
        if new_adrs:
            for adr in new_adrs:
                print(f"  - {adr}")

    if count >= args.threshold:
        print(
            f"STALE: {count} new ADR(s) since {last_updated} (threshold={args.threshold}): "
            + ", ".join(new_adrs[:5])
        )
        if not args.dry_run:
            flipped = flip_status_to_stale(repo_root)
            if flipped:
                print("STATUS FLIPPED: accepted -> stale in threat-model.md")
            emit_freshness_breach(count, new_adrs)
        else:
            print("DRY-RUN: would flip status to stale.")
        return 1

    if args.verbose:
        print(f"OK: {count} new ADR(s) < threshold {args.threshold}. Threat model is fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
