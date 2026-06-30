"""Behavior tests for ``_lib/adapters/live/_breaker.py``.

Drives state transitions deterministically via injected clock — never
calls :func:`time.sleep`. Threading test exercises concurrent failure
records to assert the lock is load-bearing.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parents[3]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.adapters.live._breaker import BreakerState, CircuitBreaker  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class _FakeClock:
    """Monotonic-ish clock returning whatever ``now`` is set to."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestBaseStates(unittest.TestCase):
    def test_starts_closed(self):
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60)
        self.assertEqual(b.state, BreakerState.CLOSED)
        self.assertTrue(b.should_allow())

    def test_opens_after_threshold_failures_in_window(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.CLOSED)
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)
        self.assertFalse(b.should_allow())

    def test_failures_outside_window_dropped(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        # advance past the window
        clock.advance(31)
        b.record_failure("server_error")
        # only 1 failure in current window — should still be closed
        self.assertEqual(b.state, BreakerState.CLOSED)

    def test_auth_permanent_opens_immediately(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=10, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("auth_permanent")
        self.assertEqual(b.state, BreakerState.OPEN)


class TestParseErrorDoesNotCount(unittest.TestCase):
    def test_parse_error_alone_never_opens_breaker(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60, clock=clock)
        for _ in range(20):
            b.record_failure("parse_error")
        self.assertEqual(b.state, BreakerState.CLOSED)


class TestHalfOpenTransition(unittest.TestCase):
    def test_open_to_half_open_after_half_open_s(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=2, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)
        clock.advance(60)
        # state lookup triggers refresh
        self.assertEqual(b.state, BreakerState.HALF_OPEN)

    def test_probe_allowed_exactly_once_in_half_open(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=2, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        clock.advance(60)
        self.assertTrue(b.should_allow())  # probe permitted
        self.assertFalse(b.should_allow())  # second call blocked

    def test_half_open_success_closes_breaker(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=2, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        clock.advance(60)
        b.should_allow()  # consume the probe
        b.record_success()
        self.assertEqual(b.state, BreakerState.CLOSED)
        # New traffic flows
        self.assertTrue(b.should_allow())

    def test_half_open_failure_re_opens_breaker(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=2, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        clock.advance(60)
        b.should_allow()  # probe consumed
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)
        # New 60s clock — no probe yet
        self.assertFalse(b.should_allow())


class TestSnapshot(unittest.TestCase):
    def test_snapshot_reports_open_state_and_count(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        b.record_failure("server_error")
        snap = b.snapshot()
        self.assertEqual(snap.state, "open")
        self.assertGreaterEqual(snap.failures_in_window, 3)
        self.assertIsNotNone(snap.opened_at)


class TestThreadSafety(unittest.TestCase):
    def test_concurrent_record_failure_open_state_consistent(self):
        b = CircuitBreaker(threshold=10, window_s=30, half_open_s=60)
        # 4 threads * 10 failures each = 40 — should open after threshold reached
        barrier = threading.Barrier(4)

        def worker():
            barrier.wait()
            for _ in range(10):
                b.record_failure("server_error")

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All 40 attempts were transient → breaker opened
        self.assertEqual(b.state, BreakerState.OPEN)


class TestReset(unittest.TestCase):
    def test_reset_returns_to_closed(self):
        clock = _FakeClock()
        b = CircuitBreaker(threshold=2, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)
        b.reset()
        self.assertEqual(b.state, BreakerState.CLOSED)
        self.assertTrue(b.should_allow())


class TestRecordSuccessClosed(unittest.TestCase):
    def test_record_success_in_closed_does_not_clear_window(self):
        # Sliding window is the load-bearing pruner; success in CLOSED is
        # a no-op for counters (matches breaker spec).
        clock = _FakeClock()
        b = CircuitBreaker(threshold=3, window_s=30, half_open_s=60, clock=clock)
        b.record_failure("server_error")
        b.record_failure("server_error")
        b.record_success()
        # One more failure → still opens (window state preserved)
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)


class TestInvalidConstructor(unittest.TestCase):
    def test_threshold_below_2_rejected(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(threshold=1, window_s=30, half_open_s=60)


# =============================================================================
# PLAN-114 F-1-1.8-c6fe879b — breaker_closed audit emit wire
#
# Verifies that record_success() calls audit_emit.emit_breaker_closed with
# the correct from_state argument on both the HALF_OPEN→CLOSED path and the
# OPEN race path.  Uses mock.patch to avoid real I/O; the end-to-end
# audit-log assertion lives in test_plan114_wires.py::TestBreakerClosedWire.
# =============================================================================

class TestBreakerClosedAuditEmitWire(TestEnvContext):
    """PLAN-114 — emit_breaker_closed called on record_success() transitions."""

    def test_half_open_to_closed_calls_emit_breaker_closed(self):
        """record_success() from HALF_OPEN state must call
        audit_emit.emit_breaker_closed(provider, from_state='half_open').
        """
        clock = _FakeClock()
        b = CircuitBreaker(
            provider="wire_provider",
            threshold=2,
            window_s=30,
            half_open_s=60,
            clock=clock,
        )
        b.record_failure("server_error")
        b.record_failure("server_error")
        clock.advance(61)
        b.should_allow()  # consume probe → HALF_OPEN
        self.assertEqual(b.state, BreakerState.HALF_OPEN)

        # Patch the EXACT audit_emit module object record_success() resolves at
        # call time — read from the function's __globals__, never via sys.modules.
        # Sibling tests pop/reassign sys.modules["_lib.audit_emit"] and evict the
        # _lib.* package tree (identity swaps), so any sys.modules- or string-routed
        # patch target can diverge from what the breaker actually calls. __globals__
        # is the module dict where record_success was defined and is immune to all
        # of that. See PLAN-114 / S210.
        _audit_mod = CircuitBreaker.record_success.__globals__["audit_emit"]
        with mock.patch.object(_audit_mod, "emit_breaker_closed") as mock_emit:
            b.record_success()
            mock_emit.assert_called_once_with(
                provider="wire_provider",
                from_state="half_open",
            )
        self.assertEqual(b.state, BreakerState.CLOSED)

    def test_open_race_calls_emit_breaker_closed(self):
        """record_success() while OPEN (race) must call
        audit_emit.emit_breaker_closed(provider, from_state='open').
        """
        clock = _FakeClock()
        b = CircuitBreaker(
            provider="race_wire_provider",
            threshold=2,
            window_s=30,
            half_open_s=60,
            clock=clock,
        )
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)

        # See note in test_half_open_to_closed_calls_emit_breaker_closed: read the
        # audit_emit object from record_success.__globals__ so no sys.modules
        # identity swap by a sibling test can hide the real call.
        _audit_mod = CircuitBreaker.record_success.__globals__["audit_emit"]
        with mock.patch.object(_audit_mod, "emit_breaker_closed") as mock_emit:
            b.record_success()
            mock_emit.assert_called_once_with(
                provider="race_wire_provider",
                from_state="open",
            )
        self.assertEqual(b.state, BreakerState.CLOSED)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(threshold=3, window_s=0, half_open_s=60)


if __name__ == "__main__":
    unittest.main()
