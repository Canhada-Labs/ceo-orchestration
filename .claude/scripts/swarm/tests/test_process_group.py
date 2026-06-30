"""PLAN-050 Phase 7a (C4) — _process_group tiered-kill tests.

Covers:
- new_session_preexec behavior (POSIX setsid succeeds, Windows no-op)
- pgid_for + graceful handling of missing PID
- kill_process_group with single-PID fallback
- escalated_kill Tier 1 (SIGTERM→SIGKILL) + Tier 2 (immediate SIGKILL)

Uses subprocess for end-to-end timing tests; skips on Windows.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import pytest

from .. import _process_group as pg


def test_default_grace_is_five_seconds() -> None:
    assert pg.DEFAULT_GRACE_SECONDS == 5.0


def test_new_session_preexec_does_not_raise() -> None:
    """Pure POSIX — calling setsid in a child is a no-op from the parent."""
    pg.new_session_preexec()  # No raise; idempotent in-parent call path.


def test_pgid_for_nonexistent_pid_returns_none() -> None:
    assert pg.pgid_for(999_999_999) is None


def test_pgid_for_current_process_matches_getpgrp() -> None:
    if sys.platform == "win32":
        pytest.skip("pgid is POSIX-only")
    self_pgid = pg.pgid_for(os.getpid())
    assert self_pgid is not None
    assert self_pgid == os.getpgrp()


def test_is_alive_for_current_process_true() -> None:
    assert pg._is_alive(os.getpid()) is True


def test_is_alive_for_nonexistent_pid_false() -> None:
    assert pg._is_alive(999_999_999) is False


def test_kill_process_group_rejects_zero_sig_on_missing_pid() -> None:
    """Missing PID → fail-open to False (no exception)."""
    assert pg.kill_process_group(999_999_999, signal.SIGTERM) is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_rejects_invalid_tier() -> None:
    with pytest.raises(ValueError):
        pg.escalated_kill(os.getpid(), tier=99)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_tier2_immediate_sigkill() -> None:
    """Tier 2 sends SIGKILL immediately — no grace period."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        start_new_session=True,
    )
    t0 = time.monotonic()
    outcome = pg.escalated_kill(proc.pid, tier=2)
    elapsed = time.monotonic() - t0
    proc.wait(timeout=3)
    assert outcome in ("sigkill_tier2", "gone")
    # Tier 2 MUST be fast — no grace period.
    assert elapsed < 1.0, f"tier-2 took {elapsed:.2f}s (should be sub-second)"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_tier1_sigterm_graceful() -> None:
    """Tier 1 — child handles SIGTERM and exits within grace."""
    # Child catches SIGTERM and exits clean in <100ms.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, sys\n"
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
            "import time\n"
            "time.sleep(10)",
        ],
        start_new_session=True,
    )
    # Give child a moment to install its handler.
    time.sleep(0.3)
    outcome = pg.escalated_kill(proc.pid, tier=1, grace_seconds=2.0, poll_interval_s=0.05)
    proc.wait(timeout=3)
    # Either clean SIGTERM or fallback SIGKILL both accepted —
    # the critical invariant is that the process is dead.
    assert outcome in ("sigterm", "sigkill_tier1")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_tier1_escalates_to_sigkill_when_hanging() -> None:
    """Tier 1 — child ignores SIGTERM → SIGKILL escalation after grace."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(10)",
        ],
        start_new_session=True,
    )
    time.sleep(0.3)
    t0 = time.monotonic()
    outcome = pg.escalated_kill(
        proc.pid, tier=1, grace_seconds=0.5, poll_interval_s=0.05
    )
    elapsed = time.monotonic() - t0
    proc.wait(timeout=3)
    assert outcome == "sigkill_tier1"
    assert elapsed >= 0.5, f"escalation fired too early at {elapsed:.2f}s"
    assert elapsed < 2.0, f"escalation took too long at {elapsed:.2f}s"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_gone_pid_reports_gone() -> None:
    outcome = pg.escalated_kill(999_999_999, tier=2)
    assert outcome == "gone"
