#!/usr/bin/env python3
"""audit-log-retain.py — Retention policy for rotated audit-log archives.

PLAN-113 W7-OPS F-6.1-audit-log-retention-002 closure.

``audit_rotation.py`` renames the active audit-log.jsonl when it exceeds
10 MiB, producing files like ``audit-log-2026-04.jsonl`` or
``audit-log-2026-04-1.jsonl``.  Over time these accumulate without bound
(134 MB+ observed on 2026-05-24).

This script applies a configurable retention policy to the rotated archive
files.  It never touches the ACTIVE ``audit-log.jsonl`` or the
``audit-log.errors`` sidecar.  It also never touches the HMAC chain-reset
markers because those live inside the active log's companion files, not in
the archive files themselves.

## Retention modes (exclusive)

``--keep-count N``   Keep the N most-recently-modified archives; delete
                     older ones. Default: 12 (one year of monthly files).

``--keep-days M``    Keep archives modified within the last M days; delete
                     older ones. Default: 365 days.

If both flags are supplied, BOTH policies apply (a file is deleted only if
it would be dropped by *both* policies, i.e. the more conservative of the
two wins).  To keep every file, pass ``--keep-count 0`` or ``--keep-days 0``
(zero = disabled for that policy).

## Protected archives (never deleted regardless of policy)

Two archives are always protected:

1. The NEWEST archive (most-recent by mtime) — preserves audit-history
   continuity so at least one archived record always survives.
2. The archive named by ``previous_archive_filename`` in
   ``audit-log.rotation-manifest.json`` (when that manifest is present in
   the same directory) — this is the chain-continuity anchor referenced by
   the active log's HMAC chain and must never be removed.

The protected set is subtracted from the candidate-deletable set after
policy evaluation, so it is impossible to delete these archives regardless
of how aggressive the policy flags are.

## Safety

- Fail-open: any OSError on stat or unlink is logged to stderr and skipped.
- Dry-run: default is ``--dry-run`` (print what would be deleted without
  deleting). Pass ``--apply`` to actually delete.
- Active log excluded: the script identifies archive files by their name
  pattern ``audit-log-YYYY-MM(-N)?.jsonl`` and never matches the plain
  ``audit-log.jsonl`` active log.
- audit-log.errors sidecar excluded: extension is ``.errors``, not matched.

## Env vars

``CEO_AUDIT_LOG_DIR``  — directory containing audit-log.jsonl (highest priority)
``CEO_AUDIT_LOG_PATH`` — path to audit-log.jsonl; directory derived from it
``CLAUDE_PROJECT_DIR`` — Claude Code project directory; slug-derived path used

Falls back to ``~/.claude/projects/ceo-orchestration/`` (legacy hardcode).

## Stdlib only (ADR-002). Python >= 3.9.

Usage:
    python3 .claude/scripts/audit-log-retain.py                  # dry-run, defaults
    python3 .claude/scripts/audit-log-retain.py --apply          # apply defaults
    python3 .claude/scripts/audit-log-retain.py --keep-count 6 --apply
    python3 .claude/scripts/audit-log-retain.py --keep-days 180 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Name pattern for rotated archive files produced by audit_rotation.py.
# Matches:
#   audit-log-2026-04.jsonl
#   audit-log-2026-04-1.jsonl
#   audit-log-2026-04-999.jsonl
# Does NOT match:
#   audit-log.jsonl           (active log)
#   audit-log.errors          (sidecar)
_ARCHIVE_RE = re.compile(r"^audit-log-\d{4}-\d{2}(?:-\d+)?\.jsonl$")

_DEFAULT_KEEP_COUNT = 12  # one year of monthly files
_DEFAULT_KEEP_DAYS = 365  # one year


# ---------------------------------------------------------------------------
# Path resolution (mirrors ceo-diagnose.py _resolve_audit_log_path)
# ---------------------------------------------------------------------------


def _resolve_audit_dir() -> Optional[Path]:
    """Resolve the directory containing audit-log.jsonl.

    Order:
      1. CEO_AUDIT_LOG_DIR env var (direct directory override)
      2. CEO_AUDIT_LOG_PATH env var (full file path; directory derived)
      3. CLAUDE_PROJECT_DIR env var (slug-derived)
      4. Legacy hardcoded ~/.claude/projects/ceo-orchestration/

    Returns None if no candidate directory exists.
    """
    audit_dir_env = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir_env:
        p = Path(audit_dir_env)
        if p.is_dir():
            return p

    log_path_env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if log_path_env:
        p = Path(log_path_env).parent
        if p.is_dir():
            return p

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        try:
            abs_path = Path(project_dir).resolve()
            slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
            scoped = Path.home() / ".claude" / "projects" / slug
            if scoped.is_dir():
                return scoped
        except OSError:
            pass

    legacy = Path.home() / ".claude" / "projects" / "ceo-orchestration"
    if legacy.is_dir():
        return legacy

    return None


# ---------------------------------------------------------------------------
# Archive discovery
# ---------------------------------------------------------------------------


def discover_archives(audit_dir: Path) -> List[Tuple[float, Path]]:
    """Return list of (mtime, path) for all rotated archive files.

    Sorted newest-first (highest mtime first).  Files that cannot be stat'd
    are silently skipped (fail-open).
    """
    result: List[Tuple[float, Path]] = []
    try:
        for entry in audit_dir.iterdir():
            if not entry.is_file():
                continue
            if not _ARCHIVE_RE.match(entry.name):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            result.append((mtime, entry))
    except OSError as exc:
        print(f"[audit-log-retain] ERROR: cannot list {audit_dir}: {exc}", file=sys.stderr)
    result.sort(key=lambda t: t[0], reverse=True)  # newest first
    return result


# ---------------------------------------------------------------------------
# Manifest anchor resolution
# ---------------------------------------------------------------------------


def _read_manifest_anchor(audit_dir: Path) -> Optional[str]:
    """Return the ``previous_archive_filename`` from the rotation manifest.

    Reads ``audit-log.rotation-manifest.json`` in *audit_dir* if present.
    Returns the bare filename (not a full path) or None if the manifest is
    absent, malformed, or does not contain the key.  Fail-open on any error.
    """
    manifest_path = audit_dir / "audit-log.rotation-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        value = data.get("previous_archive_filename")
        if isinstance(value, str) and value:
            # Strip any leading directory component — we only care about the
            # bare filename so we can compare against archive Path.name.
            return Path(value).name
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Retention logic
# ---------------------------------------------------------------------------


def compute_deletable(
    archives: List[Tuple[float, Path]],
    *,
    keep_count: int,
    keep_days: int,
    protected_names: Optional[Set[str]] = None,
) -> List[Path]:
    """Return paths that should be deleted under the given retention policy.

    ``keep_count=0`` disables the count policy (keep all by count).
    ``keep_days=0`` disables the age policy (keep all by age).

    When both policies are active a file must be outside BOTH thresholds to
    become a deletion candidate (AND semantics — more conservative than OR).
    When only one policy is active that policy alone decides.

    Two archives are ALWAYS protected and can never appear in the returned
    list regardless of policy settings:

    * The newest archive (index 0 after newest-first sort) — ensures at
      least one historical archive always survives, preserving audit-history
      continuity.
    * Any archive whose name appears in *protected_names* (e.g. the
      chain-continuity anchor read from the rotation manifest).

    Args:
        archives:        Sorted newest-first list of (mtime, path) tuples as
                         returned by :func:`discover_archives`.
        keep_count:      Keep this many of the most-recent archives (0 = off).
        keep_days:       Keep archives younger than this many days (0 = off).
        protected_names: Additional filenames (bare, not full paths) that must
                         never be deleted — e.g. the manifest anchor.
    """
    if not archives:
        return []

    # Build the immutable protected set.
    _protected: Set[str] = set(protected_names or [])
    # Always protect the single newest archive (index 0 = highest mtime).
    _protected.add(archives[0][1].name)

    count_active = keep_count > 0
    age_active = keep_days > 0

    now = time.time()
    deletable: List[Path] = []
    for idx, (mtime, path) in enumerate(archives):
        # Never delete a protected archive.
        if path.name in _protected:
            continue

        drop_by_count = count_active and (idx >= keep_count)
        age_days = (now - mtime) / 86400.0
        drop_by_age = age_active and (age_days > keep_days)

        # Deletion candidate logic:
        #   - Neither policy active → keep everything.
        #   - Only count active     → count decides.
        #   - Only age active       → age decides.
        #   - Both active           → must satisfy BOTH (AND semantics).
        if not count_active and not age_active:
            is_candidate = False
        elif count_active and age_active:
            is_candidate = drop_by_count and drop_by_age
        elif count_active:
            is_candidate = drop_by_count
        else:
            is_candidate = drop_by_age

        if is_candidate:
            deletable.append(path)
    return deletable


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--keep-count",
        type=int,
        default=_DEFAULT_KEEP_COUNT,
        metavar="N",
        help=(
            f"Keep the N most-recent archives (default: {_DEFAULT_KEEP_COUNT}). "
            "0 = disabled."
        ),
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=_DEFAULT_KEEP_DAYS,
        metavar="M",
        help=(
            f"Keep archives modified within M days (default: {_DEFAULT_KEEP_DAYS}). "
            "0 = disabled."
        ),
    )
    apply_group = parser.add_mutually_exclusive_group()
    apply_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually delete files. Default is dry-run (print only).",
    )
    apply_group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would be deleted without deleting (default).",
    )
    parser.add_argument(
        "--audit-dir",
        metavar="DIR",
        default=None,
        help="Explicit audit-log directory (overrides env-var resolution).",
    )
    args = parser.parse_args(argv)

    # Resolve audit directory.
    if args.audit_dir:
        audit_dir = Path(args.audit_dir)
        if not audit_dir.is_dir():
            print(
                f"[audit-log-retain] ERROR: --audit-dir {audit_dir!r} does not exist.",
                file=sys.stderr,
            )
            return 2
    else:
        audit_dir = _resolve_audit_dir()
        if audit_dir is None:
            print(
                "[audit-log-retain] INFO: no audit-log directory found; nothing to do.",
                file=sys.stderr,
            )
            return 0

    archives = discover_archives(audit_dir)
    if not archives:
        print(f"[audit-log-retain] INFO: no rotated archives in {audit_dir}")
        return 0

    # Collect the manifest chain-continuity anchor (if any).
    manifest_anchor = _read_manifest_anchor(audit_dir)
    protected_names: Set[str] = set()
    if manifest_anchor:
        protected_names.add(manifest_anchor)

    deletable = compute_deletable(
        archives,
        keep_count=args.keep_count,
        keep_days=args.keep_days,
        protected_names=protected_names,
    )

    total_bytes = 0
    dry_run = not args.apply
    label = "WOULD DELETE" if dry_run else "DELETING"
    for path in deletable:
        try:
            size = path.stat().st_size
            total_bytes += size
        except OSError:
            size = -1
        size_str = f"{size / (1024 * 1024):.1f} MB" if size >= 0 else "?"
        print(f"[audit-log-retain] {label}: {path.name} ({size_str})")
        if not dry_run:
            try:
                path.unlink()
            except OSError as exc:
                print(
                    f"[audit-log-retain] ERROR: unlink {path}: {exc}",
                    file=sys.stderr,
                )

    kept = len(archives) - len(deletable)
    total_mb = total_bytes / (1024 * 1024)
    action = "Would free" if dry_run else "Freed"
    print(
        f"[audit-log-retain] {len(archives)} archives found; "
        f"{kept} kept; {len(deletable)} {label.lower().replace(' ', '-')}; "
        f"{action} ~{total_mb:.1f} MB"
    )
    if dry_run and deletable:
        print("[audit-log-retain] (dry-run — pass --apply to actually delete)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
