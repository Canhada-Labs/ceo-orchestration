"""Single-FileLock-per-process contract assertion + docstring presence.

PLAN-025 F-sec-008 — document + exercise the contract that callers must
not nest two FileLock instances for the same path from the same process.

The contract is not mechanically enforced (advisory). These tests verify:

1. The "Single-instance-per-process contract" section exists in the module
   docstring (adopter-facing guarantee).
2. Basic sequential acquire/release works.
3. Two FileLock objects for DIFFERENT paths in the same process coexist.
4. Cross-process contention behaves correctly (the contract's real target).
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


from _lib import filelock  # noqa: E402
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestFileLockDocstringContract(TestEnvContext):
    """The module docstring must carry the contract statement."""

    def test_single_instance_section_exists(self):
        doc = filelock.__doc__ or ""
        self.assertIn(
            "Single-instance-per-process",
            doc,
            "_lib.filelock docstring must carry the single-instance "
            "contract section (PLAN-025 F-sec-008)",
        )

    def test_contract_explains_rationale(self):
        doc = filelock.__doc__ or ""
        self.assertIn("advisory", doc.lower())
        self.assertIn("acquire once per path per process", doc.lower())


class TestFileLockBasicBehavior(TestEnvContext):
    """Baseline sanity — acquire / release works, timeout honored."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="filelock-plan025-")
        self.lockpath = Path(self.tmpdir) / "test.lock"

    def tearDown(self):
        try:
            if self.lockpath.exists():
                self.lockpath.unlink()
            os.rmdir(self.tmpdir)
        except OSError:
            pass
        super().tearDown()

    def test_acquire_release_sequential(self):
        with FileLock(self.lockpath, timeout=1.0):
            self.assertTrue(self.lockpath.exists())
        self.assertTrue(self.lockpath.exists())

    def test_two_locks_different_paths_coexist(self):
        other = Path(self.tmpdir) / "other.lock"
        with FileLock(self.lockpath, timeout=1.0):
            with FileLock(other, timeout=1.0):
                self.assertTrue(self.lockpath.exists())
                self.assertTrue(other.exists())
        other.unlink(missing_ok=True)

    def test_release_is_idempotent(self):
        lock = FileLock(self.lockpath, timeout=1.0)
        lock.acquire()
        lock.release()
        lock.release()

    def test_context_manager_releases_on_exit(self):
        lock = FileLock(self.lockpath, timeout=1.0)
        with lock:
            self.assertIsNotNone(lock._fd)
        self.assertIsNone(lock._fd)


def _child_contender(lockpath_str: str, timeout: float, result_q) -> None:
    """Child process: try to acquire the lock; report outcome via queue."""
    try:
        with FileLock(Path(lockpath_str), timeout=timeout):
            result_q.put(("acquired", time.monotonic()))
    except FileLockTimeout:
        result_q.put(("timeout", time.monotonic()))
    except Exception as e:  # pragma: no cover
        result_q.put(("error", str(e)))


class TestFileLockCrossProcess(TestEnvContext):
    """Cross-process contention behaves correctly (contract's target)."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="filelock-xproc-")
        self.lockpath = Path(self.tmpdir) / "x.lock"

    def tearDown(self):
        try:
            if self.lockpath.exists():
                self.lockpath.unlink()
            os.rmdir(self.tmpdir)
        except OSError:
            pass
        super().tearDown()

    def test_two_processes_one_acquires_one_times_out(self):
        ctx = multiprocessing.get_context("spawn")
        result_q = ctx.Queue()

        with FileLock(self.lockpath, timeout=1.0):
            child = ctx.Process(
                target=_child_contender,
                args=(str(self.lockpath), 0.3, result_q),
            )
            child.start()
            child.join(timeout=3.0)

        self.assertFalse(child.is_alive(), "child did not terminate in time")
        self.assertFalse(result_q.empty(), "child produced no result")
        status, _ = result_q.get()
        self.assertEqual(
            status,
            "timeout",
            f"Child process should have timed out; got status={status}",
        )

    def test_child_acquires_after_parent_releases(self):
        ctx = multiprocessing.get_context("spawn")
        result_q = ctx.Queue()

        child = ctx.Process(
            target=_child_contender,
            args=(str(self.lockpath), 5.0, result_q),
        )

        lock = FileLock(self.lockpath, timeout=1.0)
        lock.acquire()
        try:
            child.start()
            time.sleep(0.2)
            lock.release()
            child.join(timeout=5.0)
        finally:
            if child.is_alive():
                child.terminate()
                child.join(timeout=1.0)

        self.assertFalse(result_q.empty(), "child produced no result")
        status, _ = result_q.get()
        self.assertEqual(
            status,
            "acquired",
            f"Child should have acquired after parent released; got status={status}",
        )


if __name__ == "__main__":
    unittest.main()
