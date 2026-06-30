"""Tests for _lib.filelock — POSIX fcntl.flock context manager.

Concurrent-write test uses multiprocessing.Process (NOT threading) because
Python fcntl.flock on the same fd is shared within a process — threads
would give a false positive per PLAN-002 §8 finding #10.

Worker functions are at MODULE level so multiprocessing 'spawn' can pickle
them (macOS default is spawn; nested local functions cannot be pickled).
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
import unittest
from pathlib import Path


from _lib import filelock  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Module-level worker functions for multiprocessing (must be picklable)
# ---------------------------------------------------------------------------


def _hold_lock_worker(pipe, lock_path_str):
    """Child: acquire the lock, signal 'held', sleep 2s, release."""
    from _lib.filelock import FileLock

    with FileLock(lock_path_str, timeout=1.0):
        pipe.send("held")
        time.sleep(2.0)
        pipe.send("done")


def _append_worker(worker_id, log_path_str, lock_path_str, iterations):
    """Child: append N lines to a log file, each guarded by the lock."""
    from _lib.filelock import FileLock

    for i in range(iterations):
        with FileLock(lock_path_str, timeout=5.0):
            line = f"worker-{worker_id}-iter-{i}-payload-{'x' * 50}\n"
            with open(log_path_str, "a", encoding="utf-8") as f:
                f.write(line)


# ---------------------------------------------------------------------------


@unittest.skipUnless(os.name == "posix", "POSIX only")
class TestFileLock(TestEnvContext):
    def test_acquire_and_release(self):
        lock_path = self.audit_dir / "a.lock"
        lock = filelock.FileLock(lock_path, timeout=1.0)
        lock.acquire()
        self.assertTrue(lock_path.exists())
        lock.release()

    def test_context_manager(self):
        lock_path = self.audit_dir / "b.lock"
        with filelock.FileLock(lock_path, timeout=1.0):
            self.assertTrue(lock_path.exists())

    def test_double_release_is_safe(self):
        lock_path = self.audit_dir / "c.lock"
        lock = filelock.FileLock(lock_path, timeout=1.0)
        lock.acquire()
        lock.release()
        lock.release()  # idempotent

    def test_lock_file_has_owner_rw(self):
        lock_path = self.audit_dir / "perms.lock"
        with filelock.FileLock(lock_path, timeout=1.0):
            mode = os.stat(lock_path).st_mode & 0o777
            # umask may mask group/other bits; owner rw must be set.
            self.assertTrue(mode & 0o600)

    def test_timeout_raises_when_contended(self):
        """Second acquire attempt from a different process raises timeout."""
        lock_path = self.audit_dir / "contended.lock"
        parent_conn, child_conn = multiprocessing.Pipe()
        proc = multiprocessing.Process(
            target=_hold_lock_worker, args=(child_conn, str(lock_path))
        )
        proc.start()
        try:
            self.assertEqual(parent_conn.recv(), "held")
            t0 = time.monotonic()
            with self.assertRaises(filelock.FileLockTimeout):
                with filelock.FileLock(lock_path, timeout=0.3):
                    pass
            elapsed = time.monotonic() - t0
            self.assertGreaterEqual(elapsed, 0.25)
            self.assertLess(elapsed, 1.5)
        finally:
            proc.join(timeout=5)
            if proc.is_alive():
                proc.terminate()

    def test_concurrent_writes_no_interleaving(self):
        """N workers × M iters each → N*M intact lines, no interleaving."""
        log_path = self.audit_dir / "concurrent.log"
        lock_path = self.audit_dir / "concurrent.lock"
        workers = 4
        iters = 25

        procs = []
        for wid in range(workers):
            p = multiprocessing.Process(
                target=_append_worker,
                args=(wid, str(log_path), str(lock_path), iters),
            )
            procs.append(p)
            p.start()
        for p in procs:
            p.join(timeout=30)
            self.assertFalse(p.is_alive(), "worker did not finish in 30s")

        text = log_path.read_text(encoding="utf-8")
        lines = [ln for ln in text.split("\n") if ln]
        self.assertEqual(len(lines), workers * iters)
        for ln in lines:
            self.assertRegex(ln, r"^worker-\d-iter-\d+-payload-x{50}$")


if __name__ == "__main__":
    unittest.main()
