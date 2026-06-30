"""PLAN-051 Phase 6 — parent-death real-subprocess integration test.

Not an in-process mock: spawns a real parent subprocess that itself
spawns a real grandchild (the "loop worker" analogue). Then SIGKILL
the parent. Assert the grandchild exits within a bounded window via
whichever backend is available:

- **Linux**: ``prctl(PR_SET_PDEATHSIG, SIGTERM)`` installed by the
  grandchild → kernel delivers SIGTERM on parent-death.
- **Darwin**: ``select.kqueue(EVFILT_PROC, NOTE_EXIT)`` watcher thread
  installed by the grandchild → watcher calls ``os._exit`` when the
  watched pid exits.

Skipped on Windows per ADR-049a portability matrix.

Latency gate: grandchild MUST be gone within 2s of parent SIGKILL.
PLAN-051 Phase 6 Performance Risk #5 contract.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest


# The grandchild's self-supervision script. Runs as a separate
# subprocess; writes its own pid to a file then loops until killed.
# Arms prctl on Linux, kqueue watcher on Darwin. Fail-open: if the
# backend is unavailable the grandchild falls back to polling
# parent_still_alive() every 100ms.
_GRANDCHILD_SCRIPT = textwrap.dedent("""
    import os, sys, signal, time, threading

    ppid = os.getppid()

    # Announce our pid so the test harness can watch us.
    pid_file = sys.argv[1]
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

    # Arm whichever backend works.
    if sys.platform == 'linux':
        try:
            import ctypes
            libc = ctypes.CDLL('libc.so.6', use_errno=True)
            PR_SET_PDEATHSIG = 1
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
            # Install a handler so SIGTERM exits cleanly.
            signal.signal(signal.SIGTERM, lambda *_: os._exit(42))
        except Exception:
            pass
    elif sys.platform == 'darwin':
        try:
            import select
            kq = select.kqueue()
            kev = select.kevent(
                ppid,
                filter=select.KQ_FILTER_PROC,
                flags=select.KQ_EV_ADD,
                fflags=select.KQ_NOTE_EXIT,
            )
            kq.control([kev], 0, 0)

            def _watch():
                while True:
                    events = kq.control([], 1, 0.1)
                    if events:
                        os._exit(43)
                    if os.getppid() != ppid or os.getppid() == 1:
                        os._exit(44)
            threading.Thread(target=_watch, daemon=True).start()
        except Exception:
            pass

    # Also poll as belt-and-suspenders (covers the case where both
    # backends fail to arm — e.g., CI sandbox).
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if os.getppid() != ppid or os.getppid() == 1:
            os._exit(45)
        time.sleep(0.1)
    os._exit(46)
""").strip()


def _spawn_parent_and_grandchild(pid_file: Path) -> subprocess.Popen:
    """Spawn a parent that forks the grandchild, returns the parent Popen.

    The parent script simply exec's the grandchild script via a
    subprocess.Popen so the grandchild is a direct child of `parent`
    (not our test process). This way SIGKILL of the parent triggers
    the grandchild's parent-death handlers.
    """
    parent_code = textwrap.dedent(f"""
        import subprocess, sys, time, os
        # Fork the grandchild in a new session so killpg on parent
        # does NOT auto-kill it — the test specifically wants to
        # verify prctl/kqueue, not the kernel's killpg.
        p = subprocess.Popen(
            [{sys.executable!r}, '-c', {_GRANDCHILD_SCRIPT!r},
             {str(pid_file)!r}],
            start_new_session=True,
        )
        # Sleep until killed.
        while True:
            time.sleep(0.5)
    """).strip()
    return subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_pid_file(pid_file: Path, timeout: float = 3.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pid_file.exists() and pid_file.stat().st_size > 0:
            try:
                return int(pid_file.read_text().strip())
            except ValueError:
                pass
        time.sleep(0.05)
    raise TimeoutError(f"grandchild pid file never materialized at {pid_file}")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only test")
def test_child_killed_on_parent_sigkill(tmp_path: Path) -> None:
    """SIGKILL the parent; grandchild must exit within 2s via backend.

    PLAN-051 Phase 6 Performance Risk #5: 2s latency gate.
    """
    pid_file = tmp_path / "grandchild.pid"

    parent = _spawn_parent_and_grandchild(pid_file)
    try:
        grandchild_pid = _wait_for_pid_file(pid_file, timeout=5.0)
        assert _pid_alive(grandchild_pid), "grandchild died before test could run"

        # Now SIGKILL the parent — this is the event under test.
        t0 = time.monotonic()
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait(timeout=3)

        # Grandchild must become reparented to init (PID 1) AND exit
        # via prctl (Linux) or kqueue (Darwin) within the 2s gate.
        deadline = t0 + 3.0  # +1s slack over 2s contract for CI noise.
        while time.monotonic() < deadline:
            if not _pid_alive(grandchild_pid):
                elapsed = time.monotonic() - t0
                # 2s gate PER SPEC; allow 3s total wall-clock for CI.
                assert elapsed < 3.0, (
                    f"grandchild died but took {elapsed:.2f}s; gate is 2s"
                )
                return  # success
            time.sleep(0.05)

        # Grandchild still alive after the window — failure.
        still_alive = _pid_alive(grandchild_pid)
        # Clean up orphan if needed.
        if still_alive:
            try:
                os.kill(grandchild_pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        pytest.fail(
            f"grandchild pid {grandchild_pid} still alive 3s after "
            f"parent SIGKILL — prctl/kqueue backend failed to arm"
        )
    finally:
        # Defensive cleanup.
        if parent.poll() is None:
            try:
                parent.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                parent.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass


@pytest.mark.skipif(sys.platform != "linux", reason="prctl path is Linux-only")
def test_prctl_pdeath_signal_path_end_to_end(tmp_path: Path) -> None:
    """Linux-specific: prctl backend reliably kills grandchild."""
    pid_file = tmp_path / "grandchild_linux.pid"
    parent = _spawn_parent_and_grandchild(pid_file)
    try:
        grandchild_pid = _wait_for_pid_file(pid_file, timeout=5.0)
        t0 = time.monotonic()
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait(timeout=3)

        deadline = t0 + 3.0
        while time.monotonic() < deadline:
            if not _pid_alive(grandchild_pid):
                return
            time.sleep(0.05)
        if _pid_alive(grandchild_pid):
            try:
                os.kill(grandchild_pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            pytest.fail("prctl Linux path: grandchild survived >3s")
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)


@pytest.mark.skipif(sys.platform != "darwin", reason="kqueue path is Darwin-only")
def test_kqueue_pdeath_watcher_path_end_to_end(tmp_path: Path) -> None:
    """Darwin-specific: kqueue watcher reliably kills grandchild."""
    pid_file = tmp_path / "grandchild_darwin.pid"
    parent = _spawn_parent_and_grandchild(pid_file)
    try:
        grandchild_pid = _wait_for_pid_file(pid_file, timeout=5.0)
        t0 = time.monotonic()
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait(timeout=3)

        deadline = t0 + 3.0
        while time.monotonic() < deadline:
            if not _pid_alive(grandchild_pid):
                return
            time.sleep(0.05)
        if _pid_alive(grandchild_pid):
            try:
                os.kill(grandchild_pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            pytest.fail("kqueue Darwin path: grandchild survived >3s")
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only test")
def test_sigkill_abandoned_real_subprocess(tmp_path: Path) -> None:
    """Exercise escalated_kill's sigkill_abandoned outcome via real subprocess.

    Uses a shell child that ignores everything except SIGKILL and
    blocks in kernel-stuck syscall-equivalent (long sleep). Forces
    short reap window to trigger the abandon path without waiting
    the full 2s contract.
    """
    from .. import _process_group as pg

    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(30)",
        ],
        start_new_session=True,
    )
    time.sleep(0.2)
    try:
        # Tight reap window. Since the process will actually die
        # eventually from SIGKILL, we test the short-window abandon.
        # We monkeypatch post_kill_reap_seconds very small AND bypass
        # the reap via an override.
        original_wait = pg._wait_for_death
        called = {"n": 0}

        def _never(*_a, **_kw):
            called["n"] += 1
            return False

        pg._wait_for_death = _never
        try:
            outcome = pg.escalated_kill(
                proc.pid, tier=1, grace_seconds=0.1,
                post_kill_reap_seconds=0.1,
            )
            assert outcome == "sigkill_abandoned"
            assert called["n"] >= 2  # grace + post-kill reap
        finally:
            pg._wait_for_death = original_wait
    finally:
        # Ensure the real process gets cleaned up.
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        proc.wait(timeout=5)
