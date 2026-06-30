"""Unit tests for backup-audit.py (PLAN-010 Phase 6).

Exercises rotation (keep-days), size cap, filelock contention, missing
audit-log graceful handling, and DST / UTC-date edge behavior.
"""

from __future__ import annotations

import gzip
import importlib.util
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

spec = importlib.util.spec_from_file_location(
    "backup_audit", SCRIPTS_DIR / "backup-audit.py"
)
backup_audit = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec.loader is not None
spec.loader.exec_module(backup_audit)  # type: ignore[union-attr]

from _lib.filelock import FileLock  # noqa: E402


def _make_audit_log(audit_dir: Path, content: str = '{"k":"v"}\n') -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    log = audit_dir / "audit-log.jsonl"
    log.write_text(content, encoding="utf-8")
    return log


def _seed_snapshot(backup_dir: Path, d: date, size_bytes: int = 100) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    p = backup_dir / f"audit-{d.isoformat()}.jsonl.gz"
    # Write a valid gzip blob of roughly the requested size
    payload = (b"x" * size_bytes)
    with gzip.open(p, "wb") as f:
        f.write(payload)
    # Pad on disk if needed so stat().st_size >= size_bytes when the
    # rotation math expects it.
    if p.stat().st_size < size_bytes:
        with open(p, "ab") as f:
            f.write(b"\0" * (size_bytes - p.stat().st_size))
    return p


class BackupAuditTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-backup-test-"))
        self.audit_dir = self.tmp / "audit"
        self.backup_dir = self.tmp / "backups"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestSnapshot(BackupAuditTestBase):
    def test_happy_snapshot(self) -> None:
        _make_audit_log(self.audit_dir, "row1\nrow2\n")
        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            today=date(2026, 4, 14),
        )
        self.assertIsNotNone(snap)
        self.assertTrue(snap.exists())
        self.assertEqual(snap.name, "audit-2026-04-14.jsonl.gz")
        # Verify gzip content matches source
        with gzip.open(snap, "rb") as f:
            self.assertEqual(f.read(), b"row1\nrow2\n")
        self.assertEqual(deleted, [])

    def test_missing_audit_log_graceful(self) -> None:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            today=date(2026, 4, 14),
        )
        self.assertIsNone(snap)
        self.assertEqual(deleted, [])


class TestRotationKeepDays(BackupAuditTestBase):
    def test_keep_days_zero_deletes_all_old(self) -> None:
        """keep_days=0 means 'only keep today-dated snapshots'."""
        today = date(2026, 4, 14)
        _seed_snapshot(self.backup_dir, today - timedelta(days=1))
        _seed_snapshot(self.backup_dir, today - timedelta(days=5))
        _make_audit_log(self.audit_dir)

        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            keep_days=0,
            today=today,
        )
        self.assertIsNotNone(snap)
        self.assertTrue(snap.exists())
        # The two old snapshots should be gone
        self.assertEqual(len(deleted), 2)

    def test_keep_days_31_keeps_30_days(self) -> None:
        """Boundary: day-30 kept, day-31 dropped."""
        today = date(2026, 4, 14)
        kept_path = _seed_snapshot(self.backup_dir, today - timedelta(days=30))
        dropped_path = _seed_snapshot(self.backup_dir, today - timedelta(days=31))
        _make_audit_log(self.audit_dir)

        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            keep_days=30,
            today=today,
        )
        self.assertTrue(kept_path.exists())
        self.assertFalse(dropped_path.exists())
        self.assertIn(dropped_path, deleted)


class TestSizeCap(BackupAuditTestBase):
    def test_max_total_bytes_enforced(self) -> None:
        today = date(2026, 4, 14)
        # Seed 3 old snapshots, each 1KB
        for i in range(1, 4):
            _seed_snapshot(self.backup_dir, today - timedelta(days=i), size_bytes=1024)
        _make_audit_log(self.audit_dir, "tiny\n")

        # Cap at 2000 bytes — oldest must be evicted
        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            keep_days=365,  # disable age sweep
            max_total_bytes=2000,
            today=today,
        )
        self.assertIsNotNone(snap)
        # Total bytes after should be <= cap OR only newest remains
        snaps_left = backup_audit._list_snapshots(self.backup_dir)
        total = sum(p.stat().st_size for p, _ in snaps_left)
        self.assertTrue(total <= 2000 or len(snaps_left) == 1)
        self.assertGreaterEqual(len(deleted), 1)

    def test_never_delete_only_snapshot(self) -> None:
        today = date(2026, 4, 14)
        _make_audit_log(self.audit_dir, "x" * 1000)
        # Microscopic cap
        snap, deleted = backup_audit.backup_audit(
            self.audit_dir,
            self.backup_dir,
            keep_days=365,
            max_total_bytes=1,
            today=today,
        )
        # The newest snapshot (today) must survive
        self.assertTrue(snap.exists())


class TestDstEdge(BackupAuditTestBase):
    def test_uses_utc_date(self) -> None:
        """Verify _today_utc() returns a UTC date — DST-safe."""
        d = backup_audit._today_utc()
        # Must match the UTC now's date (compare to wall-clock UTC)
        expected = datetime.now(timezone.utc).date()
        self.assertEqual(d, expected)

    def test_snapshot_filename_round_trip(self) -> None:
        """Ensure the DST-ambiguous spring-forward / fall-back dates parse fine."""
        for d in (date(2026, 3, 8), date(2026, 11, 1)):  # US DST transitions
            p = Path(f"audit-{d.isoformat()}.jsonl.gz")
            self.assertEqual(backup_audit._parse_snapshot_date(p), d)

    def test_ignores_non_snapshot_files(self) -> None:
        self.backup_dir.mkdir(parents=True)
        (self.backup_dir / "README.txt").write_text("notes", encoding="utf-8")
        (self.backup_dir / "audit-log.jsonl").write_text("x", encoding="utf-8")
        snaps = backup_audit._list_snapshots(self.backup_dir)
        self.assertEqual(snaps, [])


def _hold_lock_subprocess(lock_path: str, duration: float, ready_flag: str) -> None:
    """Helper: acquire the filelock, write a flag file, then sleep."""
    with FileLock(lock_path, timeout=2.0):
        Path(ready_flag).write_text("ok", encoding="utf-8")
        time.sleep(duration)


class TestFilelockContention(BackupAuditTestBase):
    def test_backup_waits_for_writer_lock(self) -> None:
        """A writer holding the lock MUST block backup_audit until released.

        We hold the lock ~0.6s in a subprocess. backup_audit runs with a
        generous timeout; it should succeed AFTER the subprocess releases.
        """
        _make_audit_log(self.audit_dir, "concurrent\n")
        lock_path = self.audit_dir / "audit-log.jsonl.lock"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        ready_flag = self.tmp / "ready.flag"

        proc = mp.Process(
            target=_hold_lock_subprocess,
            args=(str(lock_path), 0.6, str(ready_flag)),
        )
        proc.start()
        try:
            # Wait until the subprocess reports it actually holds the lock
            deadline = time.monotonic() + 2.0
            while not ready_flag.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready_flag.exists(), "holder did not acquire lock")

            t0 = time.monotonic()
            snap, _ = backup_audit.backup_audit(
                self.audit_dir,
                self.backup_dir,
                today=date(2026, 4, 14),
                lock_timeout=3.0,
            )
            elapsed = time.monotonic() - t0

            # Must have waited at least part of the hold duration
            self.assertGreater(
                elapsed, 0.2, f"backup did not wait for lock (elapsed={elapsed:.3f}s)"
            )
            self.assertIsNotNone(snap)
            self.assertTrue(snap.exists())
        finally:
            proc.join(timeout=5)
            if proc.is_alive():  # pragma: no cover
                proc.terminate()
                proc.join()

    def test_backup_times_out_on_permanent_contention(self) -> None:
        """If the lock is held longer than ``lock_timeout``, we raise."""
        _make_audit_log(self.audit_dir, "x\n")
        lock_path = self.audit_dir / "audit-log.jsonl.lock"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        ready_flag = self.tmp / "ready2.flag"

        proc = mp.Process(
            target=_hold_lock_subprocess,
            args=(str(lock_path), 2.0, str(ready_flag)),
        )
        proc.start()
        try:
            deadline = time.monotonic() + 2.0
            while not ready_flag.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready_flag.exists())

            with self.assertRaises(backup_audit.FileLockTimeout):
                backup_audit.backup_audit(
                    self.audit_dir,
                    self.backup_dir,
                    today=date(2026, 4, 14),
                    lock_timeout=0.3,
                )
        finally:
            proc.join(timeout=5)
            if proc.is_alive():  # pragma: no cover
                proc.terminate()
                proc.join()


class TestCliMain(BackupAuditTestBase):
    def test_main_happy(self) -> None:
        _make_audit_log(self.audit_dir, "row\n")
        rc = backup_audit.main(
            [
                "--audit-dir",
                str(self.audit_dir),
                "--backup-dir",
                str(self.backup_dir),
                "--keep-days",
                "30",
            ]
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
