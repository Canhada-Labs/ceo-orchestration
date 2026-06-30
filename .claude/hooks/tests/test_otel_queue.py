"""Unit tests for _lib/otel/queue.py (PLAN-012 Phase 3 D4.2).

Covers:

- Empty + under-capacity + at-capacity + overflow behaviour.
- DROP_OLDEST vs DROP_NEWEST vs BLOCK semantics.
- Clock injection for timeout-based BLOCK tests.
- Thread safety under concurrent producers + drainers.
- Drain max_items bound.
- ``clear()`` does not increment dropped_count.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.otel.queue import BoundedQueue, OverflowPolicy  # noqa: E402


class TestConstruction(TestEnvContext):
    def test_default_maxsize_and_policy(self) -> None:
        q = BoundedQueue()
        self.assertEqual(q.maxsize, 1000)
        self.assertIs(q.policy, OverflowPolicy.DROP_OLDEST)
        self.assertEqual(len(q), 0)
        self.assertEqual(q.dropped_count, 0)
        self.assertEqual(q.overflow_count, 0)

    def test_string_policy_accepted(self) -> None:
        q = BoundedQueue(maxsize=10, on_overflow="drop_newest")
        self.assertIs(q.policy, OverflowPolicy.DROP_NEWEST)

    def test_enum_policy_accepted(self) -> None:
        q = BoundedQueue(maxsize=10, on_overflow=OverflowPolicy.BLOCK)
        self.assertIs(q.policy, OverflowPolicy.BLOCK)

    def test_unknown_policy_raises(self) -> None:
        with self.assertRaises(ValueError):
            BoundedQueue(on_overflow="burn_it_all")

    def test_invalid_maxsize_raises(self) -> None:
        with self.assertRaises(ValueError):
            BoundedQueue(maxsize=0)
        with self.assertRaises(ValueError):
            BoundedQueue(maxsize=-1)
        with self.assertRaises(TypeError):
            BoundedQueue(maxsize="ten")  # type: ignore[arg-type]


class TestEmptyAndUnderCapacity(TestEnvContext):
    def test_empty_drain_returns_empty_list(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=5)
        self.assertEqual(q.drain(), [])
        self.assertEqual(len(q), 0)

    def test_under_capacity_accepted(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=5)
        for i in range(3):
            self.assertTrue(q.enqueue(i))
        self.assertEqual(len(q), 3)
        self.assertEqual(q.dropped_count, 0)
        self.assertEqual(q.overflow_count, 0)

    def test_drain_returns_fifo_order(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=5)
        for i in range(5):
            q.enqueue(i)
        items = q.drain(max_items=10)
        self.assertEqual(items, [0, 1, 2, 3, 4])
        self.assertEqual(len(q), 0)


class TestDropOldest(TestEnvContext):
    def test_overflow_drops_oldest_and_accepts_new(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=3, on_overflow="drop_oldest")
        for i in range(5):
            self.assertTrue(q.enqueue(i))
        # We enqueued 0..4 into a 3-slot queue. Oldest 0, 1 should have
        # been evicted; remaining is [2, 3, 4].
        self.assertEqual(len(q), 3)
        self.assertEqual(q.dropped_count, 2)
        self.assertEqual(q.overflow_count, 2)
        self.assertEqual(q.drain(), [2, 3, 4])

    def test_overflow_count_only_on_drop_oldest(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=2, on_overflow="drop_oldest")
        q.enqueue("a")  # type: ignore[arg-type]
        q.enqueue("b")  # type: ignore[arg-type]
        q.enqueue("c")  # type: ignore[arg-type]  # forces a drop
        self.assertEqual(q.overflow_count, 1)
        self.assertEqual(q.dropped_count, 1)


class TestDropNewest(TestEnvContext):
    def test_overflow_rejects_new(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=3, on_overflow="drop_newest")
        for i in range(3):
            self.assertTrue(q.enqueue(i))
        # 4th should be rejected.
        self.assertFalse(q.enqueue(99))
        self.assertEqual(len(q), 3)
        self.assertEqual(q.dropped_count, 1)
        # overflow_count is specific to DROP_OLDEST.
        self.assertEqual(q.overflow_count, 0)
        # Oldest item survives; newest rejected.
        self.assertEqual(q.drain(), [0, 1, 2])


class TestBlockPolicy(TestEnvContext):
    def test_block_succeeds_when_drained_in_time(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=1, on_overflow=OverflowPolicy.BLOCK)
        q.enqueue(0)

        # Drainer thread empties after 50ms so the enqueue can proceed.
        def drainer():
            time.sleep(0.05)
            q.drain(max_items=1)

        t = threading.Thread(target=drainer, daemon=True)
        t.start()
        started = time.monotonic()
        # Generous timeout so xdist CPU-starvation of the daemon drainer thread
        # cannot flip accepted to False. The load-bearing invariant is that the
        # enqueue eventually proceeds once drained (accepted + it blocked >=0.04),
        # not that it is fast — so the upper bound is a loose jitter ceiling.
        accepted = q.enqueue(1, timeout_s=5.0)
        elapsed = time.monotonic() - started
        t.join(timeout=5.0)

        self.assertTrue(accepted)
        self.assertLess(elapsed, 5.0, "BLOCK should not time out")
        self.assertGreaterEqual(elapsed, 0.04)  # tolerate scheduling jitter

    def test_block_times_out(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=1, on_overflow=OverflowPolicy.BLOCK)
        q.enqueue(0)
        started = time.monotonic()
        accepted = q.enqueue(1, timeout_s=0.05)
        elapsed = time.monotonic() - started
        self.assertFalse(accepted)
        self.assertGreaterEqual(elapsed, 0.04)
        # Loose upper bound (was 0.5): a starved xdist worker can be descheduled
        # at the timeout-fire moment; >=0.04 already proves it blocked ~the timeout.
        self.assertLess(elapsed, 2.0)

    def test_block_with_clock_injection(self) -> None:
        """BLOCK with a custom clock: zero timeout returns immediately."""
        fake_time = [1000.0]

        def fake_clock() -> float:
            return fake_time[0]

        q: BoundedQueue[int] = BoundedQueue(
            maxsize=1,
            on_overflow=OverflowPolicy.BLOCK,
            clock=fake_clock,
        )
        q.enqueue(0)
        # Zero timeout + fake clock at rest → instant False.
        self.assertFalse(q.enqueue(1, timeout_s=0.0))


class TestDrain(TestEnvContext):
    def test_drain_max_items_caps_output(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=100)
        for i in range(50):
            q.enqueue(i)
        batch = q.drain(max_items=10)
        self.assertEqual(len(batch), 10)
        self.assertEqual(batch, list(range(10)))
        self.assertEqual(len(q), 40)

    def test_drain_max_items_greater_than_size(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=10)
        for i in range(5):
            q.enqueue(i)
        batch = q.drain(max_items=100)
        self.assertEqual(batch, [0, 1, 2, 3, 4])
        self.assertEqual(len(q), 0)

    def test_drain_all(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=1000)
        for i in range(700):
            q.enqueue(i)
        all_items = q.drain_all()
        self.assertEqual(len(all_items), 700)
        self.assertEqual(len(q), 0)

    def test_drain_zero_raises(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=10)
        with self.assertRaises(ValueError):
            q.drain(max_items=0)


class TestClear(TestEnvContext):
    def test_clear_empties_without_counting_drops(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=10)
        for i in range(5):
            q.enqueue(i)
        n = q.clear()
        self.assertEqual(n, 5)
        self.assertEqual(len(q), 0)
        # clear() is an admin op; drops stay at 0.
        self.assertEqual(q.dropped_count, 0)


class TestSnapshot(TestEnvContext):
    def test_snapshot_returns_consistent_view(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=3, on_overflow="drop_oldest")
        for i in range(5):
            q.enqueue(i)
        snap = q.snapshot()
        self.assertEqual(snap["size"], 3)
        self.assertEqual(snap["maxsize"], 3)
        self.assertEqual(snap["policy"], "drop_oldest")
        self.assertEqual(snap["dropped"], 2)
        self.assertEqual(snap["overflow"], 2)


class TestThreadSafety(TestEnvContext):
    """4 producers + 2 drainers for 1 second — no corruption, all accounted."""

    def test_concurrent_producers_and_drainers(self) -> None:
        # Large enough queue to absorb some without forcing every
        # enqueue to evict; we still want to exercise both code paths.
        q: BoundedQueue[int] = BoundedQueue(maxsize=256, on_overflow="drop_oldest")
        stop = threading.Event()
        produced = [0] * 4
        drained_batches: list = []
        drained_lock = threading.Lock()

        def producer(idx: int) -> None:
            i = 0
            while not stop.is_set():
                # Pack the thread id into the value so we can track provenance.
                q.enqueue(idx * 1_000_000 + i)
                produced[idx] += 1
                i += 1

        def drainer() -> None:
            while not stop.is_set():
                batch = q.drain(max_items=32)
                if batch:
                    with drained_lock:
                        drained_batches.append(batch)
                # Yield so we don't hot-loop.
                time.sleep(0.001)

        threads = [
            threading.Thread(target=producer, args=(i,), daemon=True)
            for i in range(4)
        ] + [
            threading.Thread(target=drainer, daemon=True) for _ in range(2)
        ]
        for t in threads:
            t.start()

        time.sleep(0.5)  # 500ms is enough to force contention
        stop.set()
        for t in threads:
            t.join(timeout=1.0)

        # Final drain — catch what the drainers missed at stop signal.
        tail = q.drain_all()
        if tail:
            drained_batches.append(tail)

        total_drained = sum(len(b) for b in drained_batches)
        total_produced = sum(produced)
        total_dropped = q.dropped_count

        # Invariant: produced = drained + dropped + currently-in-queue(0).
        self.assertEqual(
            total_produced,
            total_drained + total_dropped,
            f"accounting mismatch: produced={total_produced} "
            f"drained={total_drained} dropped={total_dropped}",
        )
        # Sanity: we actually produced something.
        self.assertGreater(total_produced, 1000)

    def test_concurrent_enqueues_no_lost_items_under_capacity(self) -> None:
        """Each of 8 producers enqueues 100 items; queue is 1000-deep.

        With policy DROP_NEWEST and well under capacity, the queue must
        receive every item exactly once.
        """
        q: BoundedQueue[tuple] = BoundedQueue(maxsize=1000, on_overflow="drop_newest")

        def producer(idx: int) -> None:
            for i in range(100):
                q.enqueue((idx, i))

        threads = [
            threading.Thread(target=producer, args=(i,), daemon=True)
            for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 800 enqueued, queue capacity 1000 → nothing dropped.
        self.assertEqual(len(q), 800)
        self.assertEqual(q.dropped_count, 0)
        # Drain and verify each (idx, i) appears exactly once.
        all_items = q.drain_all()
        self.assertEqual(len(all_items), 800)
        self.assertEqual(len(set(all_items)), 800)


class TestFifoUnderOverflow(TestEnvContext):
    def test_drop_oldest_preserves_newest_window(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=10, on_overflow="drop_oldest")
        for i in range(100):
            q.enqueue(i)
        # Only the most recent 10 should survive.
        remaining = q.drain()
        self.assertEqual(remaining, list(range(90, 100)))

    def test_drop_newest_preserves_oldest_window(self) -> None:
        q: BoundedQueue[int] = BoundedQueue(maxsize=10, on_overflow="drop_newest")
        for i in range(100):
            q.enqueue(i)
        # Only the first 10 survive.
        remaining = q.drain()
        self.assertEqual(remaining, list(range(10)))
