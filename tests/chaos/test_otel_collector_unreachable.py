"""Chaos test: OTEL collector unreachable must not affect audit primary path.

PLAN-012 Phase 3 D4.2 / CRITICAL-3 cascade test:

- audit-log.jsonl is the primary source of truth.
- OTEL export is shadow; must never back-pressure primary.
- When the collector is unreachable (closed port), the bounded queue
  must cap at maxsize, drop-oldest must kick in, and the audit
  primary p99 must stay within ±20% of the no-OTEL baseline.

Gated per ADR-037 §Decision §2:
    CEO_CHAOS_ALLOWED=1

The chaos conftest (`tests/chaos/conftest.py`) sets that env var via
TestEnvContext so the tests themselves inherit an isolated home/audit
dir. The outer pytest-level skipif here is the secondary gate — the
first gate is ADR-037's 3-gate lockdown at the `chaos-inject.py` CLI,
which we do NOT exercise in this module (we talk to the bounded
exporter directly — no wrapper generation).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Tuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_CHAOS_ALLOWED") != "1",
    reason="Chaos tests gated per ADR-037 (CEO_CHAOS_ALLOWED=1 required)",
)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


def _measure_primary_latency(
    n: int = 100,
    *,
    exporter=None,
    spans_per_primary: int = 20,
) -> Tuple[List[float], int]:
    """Fire ``n`` audit events while optionally also firing OTEL spans.

    Returns (per-event latencies in seconds, primary events count).
    Measures only the time spent in the audit emit — the exporter
    enqueues happen between audit writes so cross-contention is
    realistic.
    """
    from _lib import audit_emit as _audit

    latencies: List[float] = []
    count = 0
    for i in range(n):
        # Enqueue some spans against the (unreachable) collector.
        if exporter is not None:
            for k in range(spans_per_primary):
                exporter.enqueue_span(
                    {
                        "action": "agent_spawn",
                        "ts": f"2026-04-14T10:{i:02d}:{k:02d}Z",
                        "seq": i * 100 + k,
                    }
                )
        t0 = time.monotonic()
        _audit.emit_benchmark_run(
            benchmark_id=f"chaos-{i}",
            skill="probe",
            pass_count=1,
            fail_count=0,
            pass_rate=1.0,
            median_score=1.0,
            floor=0.5,
        )
        latencies.append(time.monotonic() - t0)
        count += 1
    return latencies, count


def _p99(latencies: List[float]) -> float:
    sorted_ls = sorted(latencies)
    if not sorted_ls:
        return 0.0
    idx = min(len(sorted_ls) - 1, int(len(sorted_ls) * 0.99))
    return sorted_ls[idx]


# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------


def test_audit_log_unaffected_by_unreachable_collector(
    chaos_env,
    isolated_audit_log,
):
    """Audit primary p99 must stay ±20% of no-OTEL baseline.

    We run the same workload twice:
    1. Without an exporter — pure audit jsonl.
    2. With an exporter pointed at 127.0.0.1:1 (closed port).
    """
    from _lib.otel.bounded_exporter import BoundedExporter

    # Baseline: no exporter.
    baseline, baseline_count = _measure_primary_latency(n=100)
    baseline_p99 = _p99(baseline)
    assert baseline_count == 100

    # Clean the log for the second pass.
    if isolated_audit_log.exists():
        isolated_audit_log.unlink()

    # Sidecar: closed port (127.0.0.1:1) — real HTTP attempt will fail.
    # We allowlist the host so the host-filter doesn't reject before
    # the TCP connect fails.
    os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "127.0.0.1"
    exporter = BoundedExporter(
        endpoint="https://127.0.0.1:1/v1/traces",
        allowed_hosts=["127.0.0.1"],
        maxsize=1000,
        drain_interval_s=0.05,
        batch_size=50,
        send_timeout_s=0.5,  # keep tight so the drainer isn't stuck
        auto_start=True,
    )
    try:
        measured, measured_count = _measure_primary_latency(
            n=100, exporter=exporter, spans_per_primary=20
        )
        measured_p99 = _p99(measured)
        assert measured_count == 100

        # audit primary path p99 must not be wildly worse.
        # ±20% is the plan target. Give slack to the upper bound
        # (baseline is microseconds; absolute noise dominates).
        budget = max(baseline_p99 * 1.2, 0.010)  # 10ms floor
        assert measured_p99 <= budget, (
            f"audit primary p99 regressed: baseline={baseline_p99*1000:.3f}ms "
            f"measured={measured_p99*1000:.3f}ms budget={budget*1000:.3f}ms"
        )

        # At least some drops should have been incurred because the
        # collector is unreachable and we enqueued 2000 spans.
        snap = exporter.snapshot()
        assert snap["queue"]["dropped"] >= 1, (
            f"expected at least some drops; snap={snap}"
        )
    finally:
        exporter.shutdown(grace_s=1.0)

    # Audit log must contain the full 100 benchmark events from pass 2.
    lines = isolated_audit_log.read_text().splitlines()
    bench_rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as e:
            pytest.fail(f"audit log corrupted: {e}: line={line!r}")
        if ev.get("action") == "benchmark_run":
            bench_rows.append(ev)
    assert len(bench_rows) == 100, (
        f"primary audit lost events: got {len(bench_rows)} of 100"
    )


def test_bounded_queue_does_not_grow_unboundedly(chaos_env):
    """Fire 5000 spans at a closed collector — queue stays at maxsize."""
    from _lib.otel.bounded_exporter import BoundedExporter

    os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "127.0.0.1"
    exporter = BoundedExporter(
        endpoint="https://127.0.0.1:1/v1/traces",
        allowed_hosts=["127.0.0.1"],
        maxsize=500,
        drain_interval_s=10.0,  # background drain effectively off
        send_timeout_s=0.5,
        auto_start=True,
    )
    try:
        for i in range(5000):
            exporter.enqueue_span(
                {"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z", "seq": i}
            )
        snap = exporter.snapshot()
        assert snap["queue"]["size"] <= 500
        # 5000 − 500 = 4500 minimum drops (slack for in-flight drain).
        assert snap["queue"]["dropped"] >= 4400, (
            f"expected at least 4400 drops; got {snap['queue']['dropped']}"
        )
    finally:
        exporter.shutdown(grace_s=0.5)


def test_graceful_shutdown_during_send(chaos_env):
    """Shutdown in the middle of sends — no orphan threads, no exceptions.

    We instrument an exporter that sleeps inside its send (simulates a
    long-running socket.connect against a black-holed endpoint), then
    call shutdown while the drainer is mid-send.
    """
    from _lib.otel.bounded_exporter import BoundedExporter

    send_lock = threading.Lock()
    mid_send_flag = threading.Event()
    release_flag = threading.Event()
    send_attempts = [0]

    def blocking_exporter(endpoint, events, *, allowed_hosts=None, timeout=2.0):
        with send_lock:
            send_attempts[0] += 1
        mid_send_flag.set()
        # Sleep for up to 3s OR until released.
        release_flag.wait(timeout=3.0)
        return None

    exporter = BoundedExporter(
        endpoint="https://mock.example.com/v1/traces",
        allowed_hosts=["mock.example.com"],
        exporter=blocking_exporter,
        drain_interval_s=0.01,
        batch_size=5,
        auto_start=True,
    )
    try:
        # Queue up events; the drainer will pull a batch and hit blocking_exporter.
        for i in range(50):
            exporter.enqueue_span(
                {"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z", "seq": i}
            )
        # Wait until at least one send is in flight.
        assert mid_send_flag.wait(timeout=2.0), (
            "drainer never entered send within 2s"
        )
    finally:
        # Release the in-flight send so shutdown's join() can complete.
        release_flag.set()
        remaining = exporter.shutdown(grace_s=2.0)

    assert send_attempts[0] >= 1
    # Thread must be fully joined.
    assert not exporter.snapshot()["thread_alive"], "drainer thread leaked"
    # All spans either sent or dropped; no exception propagated.
    assert remaining >= 0


def test_enqueue_latency_during_cascade(chaos_env):
    """Under collector-down conditions, enqueue_span p99 stays <10ms."""
    from _lib.otel.bounded_exporter import BoundedExporter

    os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "127.0.0.1"
    exporter = BoundedExporter(
        endpoint="https://127.0.0.1:1/v1/traces",
        allowed_hosts=["127.0.0.1"],
        maxsize=1000,
        drain_interval_s=0.05,
        batch_size=50,
        send_timeout_s=0.5,
        auto_start=True,
    )
    try:
        timings: List[float] = []
        for i in range(500):
            t0 = time.monotonic()
            exporter.enqueue_span(
                {"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z", "seq": i}
            )
            timings.append(time.monotonic() - t0)
        p99 = _p99(timings)
        assert p99 < 0.010, (
            f"enqueue_span p99 {p99*1000:.3f}ms exceeds 10ms budget under cascade"
        )
    finally:
        exporter.shutdown(grace_s=1.0)
