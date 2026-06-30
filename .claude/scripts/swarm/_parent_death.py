"""PLAN-050 Phase 7a (C4) — parent-death watchdog.

Two backends:
- Linux: `prctl(PR_SET_PDEATHSIG, signal)` via ctypes.
- Darwin: `select.kqueue` watching `EVFILT_PROC` on parent PID.

Windows is unsupported (ADR-049a portability matrix): on Windows the
module's public helpers degrade to inert `False`/no-op; the higher-
level kill_switch.py continues with other layers.

The watchdog is best-effort — if the backend is unavailable (e.g.
missing libc symbol or platform mismatch), helpers return False/None
and the swarm coordinator's kill_switch layer 1/2/3 still guard the
normal failure modes.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
from typing import Callable, Optional


# Public signal default — SIGTERM gives the child 5s to shutdown gracefully
# before the process-group tier escalates to SIGKILL (per C4 tiering).
DEFAULT_PDEATH_SIGNAL = signal.SIGTERM


def current_ppid() -> int:
    """Return current parent PID.

    Returns 1 on platforms where the parent has died and the child has
    been reparented to init (orphaned process). Callers use this to
    detect "parent died while I was running".
    """
    return os.getppid()


def parent_still_alive(expected_ppid: int) -> bool:
    """Return True if the expected parent PID is still our parent.

    When a parent dies, the child is reparented (Linux → init/systemd,
    Darwin → launchd = PID 1). Comparing current ppid to the expected
    captured-at-init ppid detects this robustly across backends.
    """
    if expected_ppid <= 0:
        return False
    current = current_ppid()
    return current == expected_ppid and current != 1


# ---------------------------------------------------------------------------
# Linux backend — prctl(PR_SET_PDEATHSIG)
# ---------------------------------------------------------------------------
def _prctl_backend(death_signal: int = DEFAULT_PDEATH_SIGNAL) -> bool:
    """Ask the kernel to send `death_signal` when our parent exits.

    Returns True on success. Returns False on any failure (non-Linux
    platform, missing libc symbol, prctl return nonzero). Never raises.

    Per prctl(2): `PR_SET_PDEATHSIG` is inherited by fork but cleared
    after exec — callers that exec must re-invoke this helper.
    """
    if sys.platform != "linux":
        return False
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        PR_SET_PDEATHSIG = 1
        rc = libc.prctl(PR_SET_PDEATHSIG, death_signal, 0, 0, 0)
        return rc == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Darwin backend — select.kqueue(EVFILT_PROC, NOTE_EXIT)
# ---------------------------------------------------------------------------
def _kqueue_backend(
    parent_pid: int,
    *,
    on_death: Callable[[], None],
    poll_interval_s: float = 0.5,
) -> Optional[threading.Thread]:
    """Spawn a daemon thread that fires `on_death()` when parent_pid exits.

    Returns the thread handle on macOS (kqueue available); returns None
    on any other platform OR if kqueue is unavailable. The thread is
    marked daemon so it does not block interpreter exit.

    The thread polls kqueue with a short timeout so shutdown is prompt
    when the swarm ends voluntarily (coordinator sets a stop-event
    the caller checks — not modeled here to keep this helper pure).
    """
    if sys.platform != "darwin":
        return None
    try:
        import select
        if not hasattr(select, "kqueue"):
            return None
        kq = select.kqueue()
        KQ_EV_ADD = select.KQ_EV_ADD
        KQ_EVFILT_PROC = select.KQ_FILTER_PROC
        KQ_NOTE_EXIT = select.KQ_NOTE_EXIT
        kev = select.kevent(
            parent_pid,
            filter=KQ_EVFILT_PROC,
            flags=KQ_EV_ADD,
            fflags=KQ_NOTE_EXIT,
        )
        kq.control([kev], 0, 0)
    except Exception:
        return None

    def _watcher() -> None:
        try:
            while True:
                events = kq.control([], 1, poll_interval_s)
                if events:
                    try:
                        on_death()
                    except Exception:
                        pass
                    return
                # Also poll ppid as a fallback — belt-and-suspenders.
                if not parent_still_alive(parent_pid):
                    try:
                        on_death()
                    except Exception:
                        pass
                    return
        finally:
            try:
                kq.close()
            except Exception:
                pass

    t = threading.Thread(target=_watcher, name="parent-death-watcher", daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Unified public entry point
# ---------------------------------------------------------------------------
def install_parent_death_watchdog(
    *,
    parent_pid: Optional[int] = None,
    on_death: Optional[Callable[[], None]] = None,
    death_signal: int = DEFAULT_PDEATH_SIGNAL,
) -> str:
    """Install whichever parent-death mechanism is available for this OS.

    Returns the backend slug actually armed:
    - ``"prctl"`` — Linux kernel will deliver `death_signal` on ppid death
    - ``"kqueue"`` — macOS kqueue thread will call `on_death()` when ppid dies
    - ``"none"`` — no backend available; caller falls back to `parent_still_alive`
      polling inside the coordinator tick

    `on_death` is only called on the kqueue backend — prctl delivers a
    real signal which the process should handle via signal.signal.
    """
    ppid = parent_pid if parent_pid is not None else current_ppid()
    if sys.platform == "linux":
        if _prctl_backend(death_signal):
            return "prctl"
        return "none"
    if sys.platform == "darwin":
        if on_death is None:
            return "none"
        t = _kqueue_backend(ppid, on_death=on_death)
        if t is not None:
            return "kqueue"
        return "none"
    return "none"
