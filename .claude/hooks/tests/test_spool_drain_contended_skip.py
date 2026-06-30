"""ADR-055-AMEND-3 — opportunistic spool-drain non-blocking lock.

Regression suite for the force=False / force=True drain split. Contention is
made DETERMINISTIC by holding the REAL canonical lock on a sibling fd (no
sleeps, no fork-for-timing — per debate R-QA4). Proves:

  1. contended force=False yields (contended_skip=True, ok=True) and a FRESH
     spool writes ZERO audit-log.errors lines (benign contention is silent).
  2. no-loss across the yield: a NON-EMPTY spool keeps its k records on disk
     while contended, and those exact k records reach the canonical log after
     the lock releases (R-QA1).
  3. dead-PID orphan sweep: a spool owned by a non-alive PID IS swept into
     canonical — the terminal backstop for the SIGKILL/OOM window (R-QA2).
  4. forced semantics preserved: force=True still blocks, returns
     ok=False/error, and writes the benign breadcrumb.
  5. SEC veto-floor MF-1: under SUSTAINED starvation (own spool stale past
     DRAIN_TRIGGER_MTIME_MS) the force=False path writes exactly ONE distinct
     STARVED breadcrumb, keeping a wedge observable; a fresh spool writes none.
  6. sync-mode guard: CEO_AUDIT_SYNC_MODE=1 force=False never sets
     contended_skip (R-QA5).

Lands at .claude/hooks/tests/test_spool_drain_contended_skip.py once the Owner
GPG-signs the ceremony sentinel.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from unittest import mock

from _lib import spool_writer
from _lib.testing import TestEnvContext

# Holder runs in a SEPARATE process (debate R-QA4 + Codex pair-rail round-2):
# a sibling fd in the SAME process is not a portable contention proof —
# FileLock's own contract (filelock.py:11) warns threads/same-process opens may
# share the flock. A distinct process guarantees a distinct open file
# description, so drain_now's timeout=0 try-lock provably fails. Synchronization
# is deterministic via stdout/stdin barriers (no sleeps, no fork-in-thread):
# the child prints READY once it holds LOCK_EX, then blocks on stdin until the
# parent tells it to release. Stdlib-only one-liner — no PYTHONPATH dependency.
_HOLDER_SRC = (
    "import sys,os,fcntl;"
    "fd=os.open(sys.argv[1],os.O_CREAT|os.O_RDWR,0o600);"
    "fcntl.flock(fd,fcntl.LOCK_EX);"
    "sys.stdout.write('READY\\n');sys.stdout.flush();"
    "sys.stdin.readline();"
    "fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)"
)


@contextlib.contextmanager
def _external_lock_holder():
    """Hold the REAL canonical lock from a child process for the with-block."""
    lock_path = spool_writer._canonical_log_lock()
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLDER_SRC, str(lock_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        line = proc.stdout.readline().strip()  # deterministic barrier
        assert line == "READY", f"holder failed to acquire lock: {line!r}"
        yield
    finally:
        try:
            proc.stdin.write("go\n")
            proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _emitted_i_values() -> list:
    """The exact `i` payloads of our test events on the canonical log, sorted.

    Proves record IDENTITY (not just a row count): a drop loses an `i`, a
    duplicate repeats one — both diverge from list(range(k)) (Codex round-2).
    """
    return sorted(
        e["i"] for e in _canonical_actions()
        if e.get("action") == "plan145_test_event" and "i" in e
    )


def _errors_line_count() -> int:
    p = spool_writer._errors_path()
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())


def _starved_breadcrumb_count() -> int:
    p = spool_writer._errors_path()
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if "STARVED" in ln)


def _spool_body_line_count(pid: int) -> int:
    p = spool_writer._spool_path(pid)
    if not p.exists():
        return 0
    # body = total lines minus the 1 header line
    n = sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())
    return max(0, n - 1)


def _canonical_actions() -> list:
    p = spool_writer._canonical_log_path()
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return out


class _Base(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()
        # Pin sync-mode ABSENT for every non-sync case (R-QA5): the early-return
        # at drain_now() top would otherwise shadow contended_skip.
        os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
        spool_writer._state_dir().mkdir(parents=True, exist_ok=True)

    def _emit(self, n: int) -> None:
        for i in range(n):
            spool_writer.spool_append({"action": "plan145_test_event", "i": i})


class TestContendedFreshSpoolIsSilent(_Base):
    def test_yield_sets_contended_skip_no_breadcrumb(self) -> None:
        self._emit(1)  # non-empty, fresh mtime
        with _external_lock_holder():
            with mock.patch.object(spool_writer, "should_drain", return_value=True):
                stats = spool_writer.drain_now(force=False)
        self.assertTrue(stats.contended_skip, "force=False must yield on contention")
        self.assertTrue(stats.ok, "yield is NOT an error — ok stays True")
        self.assertIsNone(stats.error)
        self.assertEqual(stats.appended, 0, "nothing drained while contended")
        self.assertEqual(_starved_breadcrumb_count(), 0,
                         "fresh-spool benign contention must be silent")


class TestNoLossAcrossYield(_Base):
    def test_events_survive_yield_and_reach_canonical(self) -> None:
        pid = os.getpid()
        self._emit(3)
        self.assertEqual(_spool_body_line_count(pid), 3)
        with _external_lock_holder():
            with mock.patch.object(spool_writer, "should_drain", return_value=True):
                stats = spool_writer.drain_now(force=False)
            # Contended: events MUST remain on the spool, none lost.
            self.assertTrue(stats.contended_skip)
            self.assertEqual(_spool_body_line_count(pid), 3,
                             "no event may be dropped while contended")
        # Lock free: the next drain flushes the 3 events to canonical.
        stats2 = spool_writer.drain_now(force=True)
        self.assertTrue(stats2.ok)
        # Exact identity — not just a count: the 3 distinct payloads i=0,1,2
        # each appear exactly once (a drop loses one; a dup repeats one).
        self.assertEqual(_emitted_i_values(), [0, 1, 2],
                         "exactly the 3 emitted events (no drop, no dup) must reach canonical")


class TestDeadPidOrphanSweep(_Base):
    def test_dead_pid_spool_is_swept(self) -> None:
        """The :1252 live-peer skip must NOT apply to a dead PID — the terminal
        backstop for the unclean-death window (R-QA2)."""
        pid = os.getpid()
        self._emit(2)
        # Relocate our spool to a foreign PID number, then mark it dead.
        fake = 999_000
        src = spool_writer._spool_path(pid)
        dst = spool_writer._spool_path(fake)
        os.replace(str(src), str(dst))
        real_alive = spool_writer._is_alive_pid

        def fake_alive(p: int) -> bool:
            if p == fake:
                return False  # orphan: dead owner
            return real_alive(p)

        with mock.patch.object(spool_writer, "_is_alive_pid", side_effect=fake_alive):
            stats = spool_writer.drain_now(force=True)
        self.assertTrue(stats.ok)
        self.assertEqual(_emitted_i_values(), [0, 1],
                         "dead-PID orphan spool must be swept to canonical (exact payloads, no dup)")


class TestForcedSemanticsPreserved(_Base):
    def test_force_true_still_blocks_errors_and_breadcrumbs(self) -> None:
        self._emit(1)
        with _external_lock_holder():
            stats = spool_writer.drain_now(force=True)
        self.assertFalse(stats.ok, "forced drain that times out IS an error")
        self.assertEqual(stats.error, "canonical_lock_timeout")
        self.assertFalse(stats.contended_skip, "contended_skip is force=False only")
        p = spool_writer._errors_path()
        body = p.read_text(encoding="utf-8") if p.exists() else ""
        self.assertIn("drain canonical lock timeout", body)
        self.assertNotIn("STARVED", body, "forced path uses the benign breadcrumb")


class TestSustainedStarvationBreadcrumb(_Base):
    def test_stale_own_spool_emits_one_starved_breadcrumb(self) -> None:
        pid = os.getpid()
        self._emit(1)
        # Age our own spool past the staleness trigger → genuine starvation.
        sp = spool_writer._spool_path(pid)
        old = time.time() - (spool_writer.DRAIN_TRIGGER_MTIME_MS / 1000.0) - 5.0
        os.utime(str(sp), (old, old))
        with _external_lock_holder():
            stats = spool_writer.drain_now(force=False)  # should_drain True via staleness
        self.assertTrue(stats.contended_skip)
        self.assertEqual(_starved_breadcrumb_count(), 1,
                         "sustained starvation must surface exactly one STARVED breadcrumb")

    def test_fresh_spool_emits_no_starved_breadcrumb(self) -> None:
        self._emit(1)  # fresh mtime → not starved
        with _external_lock_holder():
            with mock.patch.object(spool_writer, "should_drain", return_value=True):
                spool_writer.drain_now(force=False)
        self.assertEqual(_starved_breadcrumb_count(), 0)


class TestSyncModeGuard(_Base):
    def test_sync_mode_force_false_does_not_set_contended_skip(self) -> None:
        with mock.patch.dict(os.environ, {"CEO_AUDIT_SYNC_MODE": "1"}):
            self._emit(1)
            with _external_lock_holder():
                stats = spool_writer.drain_now(force=False)
        self.assertFalse(stats.contended_skip,
                         "sync-mode force=False returns before the try-lock path")
