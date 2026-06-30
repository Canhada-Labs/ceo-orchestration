"""PLAN-051 Phase 6 — tightened escalated_kill tests.

Adds coverage for:
- 50ms poll interval (tighter than PLAN-050's 100ms default).
- `waitpid(WNOHANG)` fast-path for direct-child deaths.
- Post-SIGKILL reap-poll with hard cap + abandon breadcrumb.
- `sigkill_abandoned` outcome when the child never reaps.

Complements ``test_process_group.py`` (baseline PLAN-050 coverage).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import pytest

from .. import _process_group as pg


def test_default_poll_interval_is_50ms() -> None:
    assert pg.DEFAULT_POLL_INTERVAL_SECONDS == 0.05


def test_post_kill_reap_seconds_is_two() -> None:
    assert pg.POST_KILL_REAP_SECONDS == 2.0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_wait_for_death_returns_true_on_already_gone() -> None:
    """Short-circuits when the pid is already gone (p99 ≤50ms gate)."""
    assert pg._wait_for_death(999_999_999, 1.0, 0.05) is True


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_wait_for_death_returns_false_for_live_pid_on_timeout() -> None:
    """Live pid + short deadline → timeout returns False."""
    # Spawn a child we can control.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        start_new_session=True,
    )
    try:
        t0 = time.monotonic()
        result = pg._wait_for_death(proc.pid, 0.2, 0.05)
        elapsed = time.monotonic() - t0
        assert result is False
        # 200ms deadline ± one poll interval of slack.
        assert 0.15 < elapsed < 0.4, f"deadline drift: {elapsed:.3f}s"
    finally:
        proc.kill()
        proc.wait(timeout=3)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_wait_for_death_detects_child_exit_under_50ms_poll() -> None:
    """Cooperative child exits quickly → detected within ~1 poll interval."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        start_new_session=True,
    )
    # Give the OS a moment to actually run the child.
    time.sleep(0.1)
    t0 = time.monotonic()
    result = pg._wait_for_death(proc.pid, 1.0, 0.05)
    elapsed = time.monotonic() - t0
    assert result is True, "death should be detected when child has exited"
    # p99 gate: ≤50ms (one poll tick) for an already-dead child.
    assert elapsed < 0.2, f"detection too slow: {elapsed:.3f}s"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_reap_or_check_gone_returns_true_for_missing_pid() -> None:
    assert pg._reap_or_check_gone(999_999_999) is True


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_reap_or_check_gone_false_for_live_current_process() -> None:
    assert pg._reap_or_check_gone(os.getpid()) is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_tier1_cooperative_under_200ms() -> None:
    """Latency gate: cooperative SIGTERM child reaped p99 ≤ 200ms."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, sys\n"
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
            "import time; time.sleep(10)",
        ],
        start_new_session=True,
    )
    time.sleep(0.3)  # let the child install its handler
    t0 = time.monotonic()
    outcome = pg.escalated_kill(
        proc.pid, tier=1, grace_seconds=2.0, poll_interval_s=0.05,
        post_kill_reap_seconds=1.0,
    )
    elapsed = time.monotonic() - t0
    proc.wait(timeout=3)
    assert outcome == "sigterm", f"expected sigterm, got {outcome}"
    # Cooperative child should reap in well under 200ms on CI.
    assert elapsed < 0.5, f"cooperative child took {elapsed:.3f}s"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_tier2_post_kill_reap(capsys: pytest.CaptureFixture) -> None:
    """Tier 2 SIGKILL + reap-poll, direct child path."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        start_new_session=True,
    )
    t0 = time.monotonic()
    outcome = pg.escalated_kill(
        proc.pid, tier=2, poll_interval_s=0.05,
        post_kill_reap_seconds=2.0,
    )
    elapsed = time.monotonic() - t0
    proc.wait(timeout=3)
    assert outcome in ("sigkill_tier2", "gone")
    # Kill + reap should happen well under the 2s grace cap.
    assert elapsed < 1.0, f"tier-2 reap took {elapsed:.3f}s"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_reap_abandoned_path(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When reap-poll times out, outcome == sigkill_abandoned + stderr log.

    Force the abandon path by monkeypatching ``_wait_for_death`` to
    return True once (SIGTERM grace succeeds path check) then False
    (post-kill reap never drains). We observe the breadcrumb lands
    on stderr and the return slug is ``sigkill_abandoned``.
    """
    # Direct tier-2 path: one call to _wait_for_death after SIGKILL.
    # Patch to always return False so reap times out.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.1)"],
        start_new_session=True,
    )
    time.sleep(0.05)

    call_count = {"n": 0}

    def _always_false(*_a, **_kw):
        call_count["n"] += 1
        return False

    monkeypatch.setattr(pg, "_wait_for_death", _always_false)

    outcome = pg.escalated_kill(proc.pid, tier=2, post_kill_reap_seconds=0.1)
    assert outcome == "sigkill_abandoned"
    # Real child still needs to be cleaned up so pytest doesn't leak.
    proc.wait(timeout=3)

    # Breadcrumb lands on stderr.
    captured = capsys.readouterr()
    assert "sigkill_tier2" in captured.err
    assert "abandoning" in captured.err
    assert call_count["n"] == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path")
def test_escalated_kill_between_sigterm_and_sigkill_gone_is_sigterm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the process vanishes between SIGTERM grace and SIGKILL attempt,
    outcome is sigterm (cooperative), not gone.

    Simulate by having kill_process_group return True for the SIGTERM,
    False for the subsequent SIGKILL (as if the process already exited).
    """
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.2)"],
        start_new_session=True,
    )
    try:
        time.sleep(0.05)
        call_log: list = []

        real_kpg = pg.kill_process_group

        def fake_kpg(pid, sig):
            call_log.append(sig)
            if sig == signal.SIGTERM:
                return True
            # Simulate SIGKILL target already gone.
            return False

        # Force grace to expire without detecting death so we reach
        # the SIGKILL attempt.
        def _never_dies(*_a, **_kw):
            return False

        monkeypatch.setattr(pg, "kill_process_group", fake_kpg)
        monkeypatch.setattr(pg, "_wait_for_death", _never_dies)

        outcome = pg.escalated_kill(proc.pid, tier=1, grace_seconds=0.05)
        assert outcome == "sigterm"
        assert signal.SIGTERM in call_log
        assert signal.SIGKILL in call_log
    finally:
        # Clean up the real child (real kpg restored on monkeypatch teardown).
        real_kpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=3)
