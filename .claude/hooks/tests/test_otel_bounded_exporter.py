"""Unit tests for _lib/otel/bounded_exporter.py (PLAN-012 Phase 3 D4.2).

Covers the fire-and-forget contract:

- ``enqueue_span`` returns in <10ms even with a slow/broken exporter.
- Background thread drains + calls the mocked exporter.
- Collector down: queue grows to maxsize, drops begin, counters match.
- ``flush`` blocks until empty or times out.
- ``shutdown`` stops the thread cleanly (idempotent).
- ``get_bounded_exporter`` is a singleton.
- Post-shutdown ``enqueue_span`` is a no-op (returns False).
- Audit primary path is untouched by exporter failures.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.otel import bounded_exporter as bx  # noqa: E402
from _lib.otel.bounded_exporter import (  # noqa: E402
    BoundedExporter,
    get_bounded_exporter,
    _reset_singleton_for_tests,
)


class _FakeExporter:
    """Minimal stand-in for ``otel_emit.try_export_events``.

    Captures calls, optionally raises, optionally sleeps.
    """

    def __init__(
        self,
        *,
        should_fail: bool = False,
        sleep_s: float = 0.0,
        return_disabled: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.sleep_s = sleep_s
        self.return_disabled = return_disabled
        self.calls: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def __call__(
        self,
        endpoint: str,
        events,
        *,
        allowed_hosts=None,
        timeout: float = 2.0,
    ) -> Dict[str, Any]:
        if self.sleep_s:
            time.sleep(self.sleep_s)
        if self.should_fail:
            # try_export_events swallows and returns None on failure.
            with self.lock:
                self.calls.append(
                    {
                        "endpoint": endpoint,
                        "batch_size": len(list(events)),
                        "result": None,
                    }
                )
            return None
        batch = list(events)
        with self.lock:
            self.calls.append(
                {
                    "endpoint": endpoint,
                    "batch_size": len(batch),
                    "result": "ok",
                }
            )
        return {
            "disabled": self.return_disabled,
            "exported": len(batch),
            "dropped_fields": 0,
            "endpoint_host": "mock",
            "dry_run": False,
        }


def _make_span(i: int) -> Dict[str, Any]:
    return {"action": "agent_spawn", "ts": f"2026-04-14T10:{i:02d}:00Z", "seq": i}


class TestEnqueueLatency(TestEnvContext):
    def test_enqueue_returns_fast_when_exporter_slow(self) -> None:
        # 1 second per send on the background thread must NOT back up
        # enqueue. 10ms budget per enqueue_span.
        fake = _FakeExporter(sleep_s=1.0)
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            maxsize=2000,
            drain_interval_s=0.01,
            batch_size=50,
            auto_start=True,
        )
        try:
            timings: List[float] = []
            for i in range(100):
                t0 = time.monotonic()
                exporter.enqueue_span(_make_span(i))
                timings.append(time.monotonic() - t0)

            timings_sorted = sorted(timings)
            median = timings_sorted[len(timings_sorted) // 2]
            p95 = timings_sorted[int(len(timings_sorted) * 0.95)]
            worst = timings_sorted[-1]
            # Typical enqueue must be non-blocking-fast (<10ms). Assert the
            # MEDIAN, not a single-sample "p99" (= sorted[99] of 100 = the max):
            # one scheduler/GC hiccup on a loaded shared CI runner spikes a
            # single sample to ~100ms and flakes the old worst-of-100 gate
            # (S157: perf microbench bias under load). Median proves the
            # typical-case contract robustly.
            self.assertLess(
                median,
                0.010,
                f"enqueue_span median={median*1000:.2f}ms exceeds 10ms budget",
            )
            # p95 tolerates moderate jitter but still bounds the tail.
            self.assertLess(
                p95,
                0.050,
                f"enqueue_span p95={p95*1000:.2f}ms exceeds 50ms tolerance",
            )
            # The load-bearing invariant: enqueue NEVER blocks on the 1s/send
            # exporter. Even the worst sample must stay far below the exporter
            # sleep — a regression that made enqueue wait on the drain would
            # spike toward 1000ms. 500ms is a generous jitter ceiling that
            # still catches a real blocking regression.
            self.assertLess(
                worst,
                0.500,
                f"enqueue_span worst={worst*1000:.2f}ms — enqueue is blocking "
                "on the slow exporter (contract violation), not just jitter",
            )
        finally:
            exporter.shutdown(grace_s=0.5)

    def test_enqueue_with_fast_exporter_still_fast(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            auto_start=True,
            drain_interval_s=0.01,
        )
        try:
            timings = []
            for i in range(50):
                t0 = time.monotonic()
                exporter.enqueue_span(_make_span(i))
                timings.append(time.monotonic() - t0)
            # Median/p95/worst, NOT a per-sample worst-of-50 gate: one worker
            # descheduling under xdist -n auto spikes a single sample past 10ms
            # and flakes the per-iteration assert (S157 microbench-bias-under-load
            # — same fix the sibling test above already uses).
            timings_sorted = sorted(timings)
            median = timings_sorted[len(timings_sorted) // 2]
            p95 = timings_sorted[int(len(timings_sorted) * 0.95)]
            worst = timings_sorted[-1]
            self.assertLess(median, 0.010, f"enqueue median={median*1000:.2f}ms exceeds 10ms budget")
            self.assertLess(p95, 0.050, f"enqueue p95={p95*1000:.2f}ms exceeds 50ms tolerance")
            self.assertLess(worst, 0.500, f"enqueue worst={worst*1000:.2f}ms — enqueue blocking, not jitter")
        finally:
            exporter.shutdown(grace_s=1.0)


class TestBackgroundDrain(TestEnvContext):
    def test_drainer_invokes_exporter(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            drain_interval_s=0.01,
            batch_size=10,
            auto_start=True,
        )
        try:
            for i in range(20):
                exporter.enqueue_span(_make_span(i))
            # Flush to force all batches through the drainer.
            remaining = exporter.flush(timeout_s=2.0)
            self.assertEqual(remaining, 0)
        finally:
            exporter.shutdown(grace_s=1.0)

        self.assertGreaterEqual(len(fake.calls), 1)
        total_sent = sum(c["batch_size"] for c in fake.calls)
        self.assertEqual(total_sent, 20)
        for c in fake.calls:
            self.assertEqual(
                c["endpoint"], "https://mock.example.com/v1/traces"
            )


class TestCollectorDown(TestEnvContext):
    def test_queue_saturates_and_drops_with_failing_exporter(self) -> None:
        fake = _FakeExporter(should_fail=True, sleep_s=0.05)
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            maxsize=50,
            drain_interval_s=0.5,  # slow drain to encourage queue growth
            batch_size=10,
            auto_start=True,
        )
        try:
            # Flood far more than maxsize.
            for i in range(500):
                self.assertTrue(exporter.enqueue_span(_make_span(i)))
            # PLAN-086 Wave G.4 — deterministic bounded wait (M-12 fold).
            # Event never set; expires after 0.2s. Replaces time.sleep(0.2)
            # to eliminate CI flake on variable-load runners.
            threading.Event().wait(timeout=0.2)
            snap = exporter.snapshot()
            # Queue must never exceed maxsize.
            self.assertLessEqual(snap["queue"]["size"], 50)
            # Drops must have occurred since 500 > 50.
            self.assertGreater(snap["queue"]["dropped"], 0)
        finally:
            exporter.shutdown(grace_s=1.0)

    def test_queue_never_exceeds_maxsize(self) -> None:
        """Tight stress — even under 5000 spans we stay at maxsize."""
        fake = _FakeExporter(should_fail=True)
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            maxsize=100,
            drain_interval_s=10.0,  # effectively disable background drain
            auto_start=True,
        )
        try:
            for i in range(5000):
                exporter.enqueue_span(_make_span(i))
            snap = exporter.snapshot()
            self.assertLessEqual(snap["queue"]["size"], 100)
            self.assertGreaterEqual(snap["queue"]["dropped"], 4900)
        finally:
            exporter.shutdown(grace_s=0.5)


class TestFlush(TestEnvContext):
    def test_flush_blocks_until_empty(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            drain_interval_s=10.0,  # background thread won't help
            batch_size=10,
            auto_start=True,
        )
        try:
            for i in range(30):
                exporter.enqueue_span(_make_span(i))
            self.assertGreater(len(exporter._queue), 0)
            remaining = exporter.flush(timeout_s=2.0)
            self.assertEqual(remaining, 0)
            self.assertEqual(len(exporter._queue), 0)
        finally:
            exporter.shutdown(grace_s=0.5)

    def test_flush_respects_timeout(self) -> None:
        # Exporter that sleeps longer than our flush timeout.
        fake = _FakeExporter(sleep_s=0.5)
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            drain_interval_s=10.0,
            batch_size=5,
            auto_start=True,
        )
        try:
            for i in range(100):
                exporter.enqueue_span(_make_span(i))
            t0 = time.monotonic()
            remaining = exporter.flush(timeout_s=0.1)
            elapsed = time.monotonic() - t0
            # Don't block forever.
            self.assertLess(elapsed, 0.8)
            # Some items likely still in queue because sends are slow.
            # (Could be 0 if the first send completes in time; just
            # assert we returned within budget either way.)
            self.assertGreaterEqual(remaining, 0)
        finally:
            exporter.shutdown(grace_s=1.0)


class TestShutdown(TestEnvContext):
    def test_shutdown_stops_thread(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            auto_start=True,
        )
        self.assertTrue(exporter.snapshot()["thread_alive"])
        exporter.shutdown(grace_s=1.0)
        # Give the join a moment.
        self.assertFalse(exporter.snapshot()["thread_alive"])

    def test_shutdown_idempotent(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            auto_start=True,
        )
        exporter.shutdown(grace_s=0.5)
        # Second call must not raise.
        exporter.shutdown(grace_s=0.5)

    def test_enqueue_after_shutdown_returns_false(self) -> None:
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            auto_start=True,
        )
        exporter.shutdown(grace_s=0.5)
        # Post-shutdown enqueues are silently dropped (no block, no raise).
        self.assertFalse(exporter.enqueue_span(_make_span(1)))


class TestSingleton(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        _reset_singleton_for_tests()

    def tearDown(self) -> None:
        _reset_singleton_for_tests()
        super().tearDown()

    def test_get_bounded_exporter_returns_same_instance(self) -> None:
        fake = _FakeExporter()
        a = get_bounded_exporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            auto_start=False,
        )
        b = get_bounded_exporter()  # no kwargs — should return same instance
        self.assertIs(a, b)
        a.shutdown(grace_s=0.1)


class TestAuditPrimaryUnaffected(TestEnvContext):
    """Audit jsonl path must not be affected by exporter failures.

    We simulate the audit-primary path by writing to the isolated
    audit-log.jsonl via `audit_emit` while the exporter is thrashing
    against an unreachable collector, then assert the jsonl is
    well-formed and contains exactly the events we emitted.
    """

    def test_audit_jsonl_integrity_during_exporter_failure(self) -> None:
        import json

        from _lib import audit_emit as _audit

        # Fire up an exporter that always fails — emulates a down collector.
        fake = _FakeExporter(should_fail=True)
        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake,
            maxsize=200,
            drain_interval_s=0.05,
            batch_size=20,
            auto_start=True,
        )
        try:
            # Run two workloads concurrently:
            #   producer A: primary audit events (the real contract)
            #   producer B: OTEL span enqueues (the shadow path, failing)
            stop = threading.Event()
            primary_count = [0]
            shadow_count = [0]

            def primary():
                while not stop.is_set():
                    _audit.emit_benchmark_run(
                        benchmark_id="chaos-probe",
                        skill="dummy",
                        pass_count=1,
                        fail_count=0,
                        pass_rate=1.0,
                        median_score=1.0,
                        floor=0.5,
                    )
                    primary_count[0] += 1
                    time.sleep(0.001)

            def shadow():
                while not stop.is_set():
                    exporter.enqueue_span(_make_span(shadow_count[0]))
                    shadow_count[0] += 1

            tp = threading.Thread(target=primary, daemon=True)
            ts = threading.Thread(target=shadow, daemon=True)
            tp.start()
            ts.start()
            # PLAN-086 Wave G.4 — deterministic bounded run window.
            threading.Event().wait(timeout=0.3)
            stop.set()
            tp.join(timeout=2.0)
            ts.join(timeout=2.0)
        finally:
            exporter.shutdown(grace_s=1.0)

        # Audit jsonl must be internally consistent despite the
        # exporter failing in parallel.
        log_path = self.audit_dir / "audit-log.jsonl"
        self.assertTrue(log_path.is_file(), "audit log was not created")
        lines = log_path.read_text().splitlines()
        # Primary count must match the number of benchmark_run rows.
        parsed = [json.loads(line) for line in lines if line.strip()]
        bench_rows = [e for e in parsed if e.get("action") == "benchmark_run"]
        self.assertEqual(
            len(bench_rows),
            primary_count[0],
            f"primary audit events lost: {len(bench_rows)} vs "
            f"{primary_count[0]} emitted",
        )
        # And nothing corrupted.
        for i, row in enumerate(parsed):
            self.assertIn("action", row, f"line {i} missing action")


class TestNoEndpointDropsSilently(TestEnvContext):
    def test_sends_fail_without_endpoint(self) -> None:
        # No endpoint anywhere → every send must be marked failed,
        # but NOT raise and NOT back-pressure.
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        fake = _FakeExporter()
        exporter = BoundedExporter(
            endpoint=None,
            exporter=fake,
            drain_interval_s=0.01,
            batch_size=5,
            auto_start=True,
        )
        try:
            for i in range(10):
                exporter.enqueue_span(_make_span(i))
            # PLAN-086 Wave G.4 — deterministic drainer wait window.
            threading.Event().wait(timeout=0.15)
            snap = exporter.snapshot()
            # Drainer marked them failed; real exporter was never called.
            self.assertEqual(len(fake.calls), 0)
            self.assertGreaterEqual(snap["sends_failed"], 1)
        finally:
            exporter.shutdown(grace_s=0.5)


class TestOverflowAuditBatching(TestEnvContext):
    def test_overflow_audit_is_batched(self) -> None:
        """1000 overflows must NOT produce 1000 audit writes.

        We inject a fake audit_emit to count calls.
        """
        fake_exporter = _FakeExporter(should_fail=True)
        audit_calls: List[Dict[str, Any]] = []
        audit_lock = threading.Lock()

        def fake_audit(**kwargs: Any) -> None:
            with audit_lock:
                audit_calls.append(kwargs)

        exporter = BoundedExporter(
            endpoint="https://mock.example.com/v1/traces",
            allowed_hosts=["mock.example.com"],
            exporter=fake_exporter,
            audit_emit=fake_audit,
            maxsize=10,
            drain_interval_s=10.0,
            overflow_audit_batch=500,
            auto_start=True,
        )
        try:
            for i in range(2000):
                exporter.enqueue_span(_make_span(i))
            # 1990 drops expected (2000 - 10 capacity). With batch=500
            # we should see ~3 audit events, not 1990.
            snap = exporter.snapshot()
            self.assertGreater(snap["queue"]["dropped"], 1900)
            self.assertLessEqual(
                len(audit_calls),
                5,
                f"overflow audit not batched: {len(audit_calls)} calls",
            )
            # Each call must report a non-zero batch count.
            for c in audit_calls:
                self.assertGreaterEqual(c.get("fields_dropped_count", 0), 1)
                self.assertEqual(c.get("reason"), "queue_overflow")
        finally:
            exporter.shutdown(grace_s=0.5)
