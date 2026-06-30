"""Unit tests for mcp-server/rate_limit.py — TokenBucket + memoized registry.

ADR-042 §Auth.3. Tests cover:
- TokenBucket single-consume / burst / exhaustion / retry_after
- TokenBucket refill over time with injected clock (no time.sleep)
- TokenBucket concurrent consumption thread-safe (threading.Barrier)
- get_bucket memoization per (client_id, handler_class) key
- get_bucket per-class separation
- Override resolution (rpm + burst; fallback on negative / type error)
- handler_to_class mapping

Every test subclasses TestEnvContext (xdist-safe). Zero time.sleep —
all timing is via a deterministic injected clock.
"""

from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

# Bootstrap sys.path so mcp-server modules import cleanly.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import rate_limit  # type: ignore[import-not-found]  # noqa: E402


class _Clock:
    """Mutable monotonic stand-in. Tests advance time by setting `value`."""

    def __init__(self, start: float = 1000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value


class TestTokenBucketBasic(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()

    def test_single_consume_succeeds(self):
        clock = _Clock()
        b = rate_limit.TokenBucket(rate_per_min=60, burst=10, clock=clock)
        ok, retry = b.try_consume(1)
        self.assertTrue(ok)
        self.assertEqual(retry, 0)

    def test_burst_then_exhaustion_returns_retry_after(self):
        clock = _Clock()
        b = rate_limit.TokenBucket(rate_per_min=60, burst=3, clock=clock)
        # Drain the burst.
        for _ in range(3):
            ok, _ = b.try_consume(1)
            self.assertTrue(ok)
        # 4th call must be denied with positive retry_after_ms.
        ok, retry_ms = b.try_consume(1)
        self.assertFalse(ok)
        self.assertGreater(retry_ms, 0)

    def test_zero_cost_always_passes(self):
        clock = _Clock()
        b = rate_limit.TokenBucket(rate_per_min=60, burst=1, clock=clock)
        # Drain.
        b.try_consume(1)
        # Zero-cost still passes.
        ok, retry = b.try_consume(0)
        self.assertTrue(ok)
        self.assertEqual(retry, 0)

    def test_refill_over_time_via_injected_clock(self):
        clock = _Clock(start=1000.0)
        # 60 rpm = 1 token / second.
        b = rate_limit.TokenBucket(rate_per_min=60, burst=2, clock=clock)
        # Drain.
        b.try_consume(1)
        b.try_consume(1)
        # Cannot consume now.
        ok, _ = b.try_consume(1)
        self.assertFalse(ok)
        # Advance clock by 2 seconds → 2 tokens refilled.
        clock.value += 2.0
        ok1, _ = b.try_consume(1)
        ok2, _ = b.try_consume(1)
        self.assertTrue(ok1)
        self.assertTrue(ok2)
        # Burst cap respected — third still denies.
        ok3, _ = b.try_consume(1)
        self.assertFalse(ok3)

    def test_invalid_rpm_raises(self):
        with self.assertRaises(ValueError):
            rate_limit.TokenBucket(rate_per_min=0, burst=10)

    def test_invalid_burst_raises(self):
        with self.assertRaises(ValueError):
            rate_limit.TokenBucket(rate_per_min=60, burst=-1)

    def test_reset_refills_to_capacity(self):
        clock = _Clock()
        b = rate_limit.TokenBucket(rate_per_min=60, burst=5, clock=clock)
        # Drain.
        for _ in range(5):
            b.try_consume(1)
        # Reset.
        b.reset()
        for _ in range(5):
            ok, _ = b.try_consume(1)
            self.assertTrue(ok)


class TestTokenBucketConcurrent(TestEnvContext):
    """Race exposure via threading.Barrier — NO sleep."""

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()

    def test_concurrent_consumption_no_double_consume(self):
        # 8 threads race on a single bucket of capacity 5.
        # Expectation: exactly 5 of the 8 succeed; the rest deny.
        # If the lock is broken, we'd see >5 successes (double-consume).
        N_THREADS = 8
        CAPACITY = 5
        clock = _Clock()
        # rpm low enough that no refill could happen during the race.
        bucket = rate_limit.TokenBucket(
            rate_per_min=1, burst=CAPACITY, clock=clock
        )
        barrier = threading.Barrier(N_THREADS)
        outcomes = []
        outcomes_lock = threading.Lock()

        def worker():
            barrier.wait()  # all threads release simultaneously
            ok, _ = bucket.try_consume(1)
            with outcomes_lock:
                outcomes.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
            self.assertFalse(t.is_alive(), "worker hung")

        successes = sum(1 for o in outcomes if o)
        denials = sum(1 for o in outcomes if not o)
        self.assertEqual(successes, CAPACITY)
        self.assertEqual(denials, N_THREADS - CAPACITY)


class TestRegistry(TestEnvContext):
    """get_bucket memoization + class separation."""

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()

    def test_get_bucket_memoizes_per_key(self):
        b1 = rate_limit.get_bucket("client-a", "readonly")
        b2 = rate_limit.get_bucket("client-a", "readonly")
        self.assertIs(b1, b2, "same key should yield same bucket")

    def test_get_bucket_separates_per_handler_class(self):
        b_read = rate_limit.get_bucket("client-a", "readonly")
        b_spawn = rate_limit.get_bucket("client-a", "spawn")
        self.assertIsNot(b_read, b_spawn)

    def test_get_bucket_separates_per_client(self):
        b_a = rate_limit.get_bucket("client-a", "readonly")
        b_b = rate_limit.get_bucket("client-b", "readonly")
        self.assertIsNot(b_a, b_b)

    def test_get_bucket_uses_defaults_when_no_overrides(self):
        b = rate_limit.get_bucket("client-x", "spawn")
        self.assertEqual(b.rate_per_min, 6)
        self.assertEqual(b.burst, 2)

    def test_get_bucket_applies_overrides(self):
        overrides = {
            "client-x": {
                "spawn": {"rpm": 12, "burst": 4},
            }
        }
        b = rate_limit.get_bucket("client-x", "spawn", overrides=overrides)
        self.assertEqual(b.rate_per_min, 12)
        self.assertEqual(b.burst, 4)

    def test_get_bucket_falls_back_on_invalid_override(self):
        overrides = {
            "client-x": {
                "spawn": {"rpm": -1, "burst": 0},
            }
        }
        b = rate_limit.get_bucket("client-x", "spawn", overrides=overrides)
        # Defaults restored (6, 2).
        self.assertEqual(b.rate_per_min, 6)
        self.assertEqual(b.burst, 2)

    def test_get_bucket_unknown_class_falls_back_to_readonly(self):
        b = rate_limit.get_bucket("client-x", "made_up_class")
        self.assertEqual(b.rate_per_min, 60)  # readonly default
        self.assertEqual(b.burst, 10)


class TestHandlerClassMapping(TestEnvContext):

    def test_handler_to_class_known(self):
        self.assertEqual(rate_limit.handler_to_class("list_skills"), "readonly")
        self.assertEqual(
            rate_limit.handler_to_class("get_audit_log"), "audit_read"
        )
        self.assertEqual(rate_limit.handler_to_class("spawn_agent"), "spawn")
        self.assertEqual(
            rate_limit.handler_to_class("server.capabilities"), "readonly"
        )

    def test_handler_to_class_unknown_falls_back_to_readonly(self):
        # Defense-in-depth — ACL should reject unknown methods earlier.
        self.assertEqual(
            rate_limit.handler_to_class("nonexistent_method"), "readonly"
        )


if __name__ == "__main__":
    unittest.main()
