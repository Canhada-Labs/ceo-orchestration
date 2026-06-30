#!/usr/bin/env python3
"""backup-audit.py — Snapshot + rotate the audit log.

PLAN-010 Phase 6 (Security Engineer). Uses the shared ``_lib/filelock.py``
primitive to prevent races with a live ``audit_log.py`` writer (debate
C9 HIGH).

Rotation policy (ADR-001 amendment):

- Snapshots live under ``<audit-dir>/backups/`` by default (overridable
  via ``--backup-dir``).
- Named ``audit-YYYY-MM-DD.jsonl.gz`` (UTC date; avoids DST ambiguity).
- Deleted when older than ``--keep-days`` (default 30) OR when the total
  size of the backup directory exceeds ``--max-total-bytes`` (default
  500 MB). Always keep at least the newest snapshot when the size cap
  forces eviction.

Exit codes: 0 ok, 1 lock contention, 2 usage.
Stdlib only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# Resolve _lib/filelock.py import
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402


DEFAULT_AUDIT_DIR = Path.home() / ".claude" / "projects" / "ceo-orchestration"
DEFAULT_MAX_BYTES = 500_000_000  # 500 MB (debate C9)
DEFAULT_KEEP_DAYS = 30


def _today_utc() -> date:
    """Return today's date in UTC (DST-safe)."""
    return datetime.now(timezone.utc).date()


def _parse_snapshot_date(path: Path) -> Optional[date]:
    """Parse YYYY-MM-DD out of ``audit-YYYY-MM-DD.jsonl.gz``. None if it doesn't match."""
    name = path.name
    if not (name.startswith("audit-") and name.endswith(".jsonl.gz")):
        return None
    stem = name[len("audit-") : -len(".jsonl.gz")]
    try:
        return datetime.strptime(stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def _list_snapshots(backup_dir: Path) -> List[Tuple[Path, date]]:
    """Return (path, date) pairs, newest first."""
    if not backup_dir.exists():
        return []
    out: List[Tuple[Path, date]] = []
    for p in backup_dir.iterdir():
        d = _parse_snapshot_date(p)
        if d is not None:
            out.append((p, d))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def _rotate(
    backup_dir: Path,
    *,
    today: date,
    keep_days: int,
    max_total_bytes: int,
) -> List[Path]:
    """Apply rotation policy. Returns list of deleted paths.

    Policy (union):
      - Delete any snapshot older than ``today - keep_days`` days.
      - After that, if total bytes still exceed ``max_total_bytes``,
        delete oldest snapshots until under cap (always keep newest).
    """
    deleted: List[Path] = []
    snaps = _list_snapshots(backup_dir)

    # Age-based sweep
    if keep_days >= 0:
        cutoff = today - timedelta(days=keep_days)
        kept: List[Tuple[Path, date]] = []
        for p, d in snaps:
            if d < cutoff:
                try:
                    p.unlink()
                    deleted.append(p)
                except OSError:
                    pass
            else:
                kept.append((p, d))
        snaps = kept

    # Size-based sweep (oldest first; never drop the single newest)
    def _total() -> int:
        return sum(p.stat().st_size for p, _ in snaps if p.exists())

    while len(snaps) > 1 and _total() > max_total_bytes:
        oldest_p, _ = snaps[-1]
        try:
            oldest_p.unlink()
            deleted.append(oldest_p)
        except OSError:
            break
        snaps = snaps[:-1]

    return deleted


def backup_audit(
    audit_dir: Path,
    backup_dir: Path,
    *,
    keep_days: int = DEFAULT_KEEP_DAYS,
    max_total_bytes: int = DEFAULT_MAX_BYTES,
    today: Optional[date] = None,
    lock_timeout: float = 2.5,
) -> Tuple[Optional[Path], List[Path]]:
    """Produce today's snapshot and rotate. Returns (snapshot_path, deleted).

    Missing audit log → (None, []) with graceful no-op.
    Raises FileLockTimeout on lock contention.
    """
    today = today or _today_utc()
    audit_log = audit_dir / "audit-log.jsonl"
    lock_path = audit_dir / "audit-log.jsonl.lock"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not audit_log.exists():
        # Graceful: still rotate old snapshots if any exist.
        deleted = _rotate(
            backup_dir,
            today=today,
            keep_days=keep_days,
            max_total_bytes=max_total_bytes,
        )
        return None, deleted

    snapshot = backup_dir / f"audit-{today.isoformat()}.jsonl.gz"

    # Acquire lock to block concurrent audit_log.py writers during copy.
    try:
        with FileLock(lock_path, timeout=lock_timeout):
            # Stream-gzip the audit log. Use a temp path then rename for
            # atomicity on crash.
            tmp = snapshot.with_suffix(snapshot.suffix + ".tmp")
            try:
                with open(audit_log, "rb") as src, gzip.open(
                    tmp, "wb", compresslevel=9
                ) as dst:
                    shutil.copyfileobj(src, dst)
                os.replace(tmp, snapshot)
            finally:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
    except FileLockTimeout:
        raise

    deleted = _rotate(
        backup_dir,
        today=today,
        keep_days=keep_days,
        max_total_bytes=max_total_bytes,
    )
    return snapshot, deleted


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — backup audit-log + sidecar under a timestamped tarball."""
    parser = argparse.ArgumentParser(
        prog="backup-audit",
        description="Snapshot + rotate the ceo-orchestration audit log.",
    )
    parser.add_argument(
        "--audit-dir",
        default=str(DEFAULT_AUDIT_DIR),
        help=f"Audit log directory. Default: {DEFAULT_AUDIT_DIR}",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Backup directory. Default: <audit-dir>/backups/",
    )
    parser.add_argument(
        "--max-total-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Size cap for backup dir. Default: {DEFAULT_MAX_BYTES}",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=DEFAULT_KEEP_DAYS,
        help=f"Delete snapshots older than this many days. Default: {DEFAULT_KEEP_DAYS}",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    audit_dir = Path(args.audit_dir).expanduser()
    backup_dir = (
        Path(args.backup_dir).expanduser() if args.backup_dir else audit_dir / "backups"
    )

    try:
        snap, deleted = backup_audit(
            audit_dir,
            backup_dir,
            keep_days=args.keep_days,
            max_total_bytes=args.max_total_bytes,
        )
    except FileLockTimeout as exc:
        sys.stderr.write(f"error: could not acquire audit-log lock: {exc}\n")
        return 1

    if snap is None:
        sys.stdout.write(f"no audit-log found at {audit_dir}/audit-log.jsonl (noop)\n")
    else:
        sys.stdout.write(f"snapshot: {snap}\n")
    sys.stdout.write(f"deleted: {len(deleted)}\n")
    for p in deleted:
        sys.stdout.write(f"  - {p.name}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
