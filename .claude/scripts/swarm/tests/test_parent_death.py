"""PLAN-050 Phase 7a (C4) — _parent_death backend tests.

Linux prctl backend + Darwin kqueue backend + cross-platform helpers.
Tests use monkeypatch to avoid installing real signal handlers that
would survive across test cases.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
from unittest.mock import patch

import pytest

from .. import _parent_death as pd


def test_current_ppid_returns_positive_int() -> None:
    ppid = pd.current_ppid()
    assert isinstance(ppid, int)
    assert ppid > 0


def test_parent_still_alive_false_for_zero_or_negative() -> None:
    assert pd.parent_still_alive(0) is False
    assert pd.parent_still_alive(-1) is False


def test_parent_still_alive_true_for_real_ppid() -> None:
    """Our parent is whoever ran pytest; they're alive right now."""
    real_ppid = os.getppid()
    # real_ppid == 1 on containerized orphan test runs — that path
    # intentionally reports False (reparented to init). Otherwise True.
    expected = real_ppid != 1
    assert pd.parent_still_alive(real_ppid) is expected


def test_parent_still_alive_false_when_reparented() -> None:
    """When current ppid is 1 (reparented), any expected ≠ 1 returns False."""
    with patch.object(pd, "current_ppid", return_value=1):
        assert pd.parent_still_alive(os.getppid()) is False


def test_parent_still_alive_false_on_mismatch() -> None:
    """Mismatch between expected and current → parent has died."""
    with patch.object(pd, "current_ppid", return_value=98765):
        assert pd.parent_still_alive(12345) is False


def test_prctl_backend_returns_false_on_non_linux() -> None:
    """prctl is Linux-only; all other platforms fail-open to False."""
    if sys.platform == "linux":
        pytest.skip("Linux-only sanity check for the other-platform branch")
    assert pd._prctl_backend() is False


def test_prctl_backend_returns_false_when_libc_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On Linux, if ctypes fails to load libc.so.6 we fail-open to False."""
    # Patch sys.platform + simulate ctypes failure regardless of host OS.
    monkeypatch.setattr(sys, "platform", "linux")

    # Force the import to raise inside the backend body.
    import builtins
    real_import = builtins.__import__

    def _raising_import(name, *args, **kwargs):
        if name == "ctypes":
            raise ImportError("simulated missing ctypes")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _raising_import)
    assert pd._prctl_backend() is False


def test_kqueue_backend_returns_none_on_non_darwin() -> None:
    """kqueue is Darwin-only; other platforms return None."""
    if sys.platform == "darwin":
        pytest.skip("Darwin-only sanity check for the other-platform branch")
    t = pd._kqueue_backend(os.getpid(), on_death=lambda: None)
    assert t is None


def test_install_watchdog_reports_none_on_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On an exotic OS, install returns ``none`` without raising."""
    monkeypatch.setattr(sys, "platform", "freebsd")
    slug = pd.install_parent_death_watchdog(on_death=lambda: None)
    assert slug == "none"


def test_install_watchdog_no_on_death_on_darwin_yields_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Darwin kqueue backend requires `on_death` callback; else None."""
    monkeypatch.setattr(sys, "platform", "darwin")
    slug = pd.install_parent_death_watchdog(on_death=None)
    assert slug == "none"


@pytest.mark.skipif(sys.platform != "darwin", reason="kqueue only on macOS")
def test_kqueue_backend_fires_on_parent_exit() -> None:
    """Smoke test — kqueue thread signals when the watched PID exits.

    Uses a short-lived subprocess as the fake parent. Wait up to 3s
    for the watcher thread to fire; skip test if the kernel feature is
    unavailable (rare).
    """
    import subprocess
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.3)"],
    )
    fired = threading.Event()
    t = pd._kqueue_backend(proc.pid, on_death=fired.set, poll_interval_s=0.1)
    if t is None:
        pytest.skip("kqueue not available in this environment")
    proc.wait(timeout=2)
    assert fired.wait(timeout=3), "kqueue watcher failed to fire"
    t.join(timeout=2)


def test_default_pdeath_signal_is_sigterm() -> None:
    assert pd.DEFAULT_PDEATH_SIGNAL == signal.SIGTERM
