"""OTEL bounded-exporter package (PLAN-012 Phase 3 D4.2).

This package wraps the existing ``_lib.otel_emit`` sync library with a
fire-and-forget bounded-queue exporter so that OTEL collector latency
(or a fully unreachable collector) can never backpressure the audit
primary path (``audit-log.jsonl``).

Contract — PLAN-012 CRITICAL-3:

- Audit jsonl is primary; OTEL is shadow.
- ``enqueue_span`` NEVER blocks more than 10ms.
- On collector unreachable: queue saturates, drop-oldest kicks in, and
  audit_log p99 latency stays within ±20% of the no-OTEL baseline.
- ``CEO_SOTA_DISABLE=1`` short-circuits (mirrors the rest of the
  Sprint-11/12 SOTA surfaces).

Modules:

- ``queue`` — stdlib ``threading.Lock``-based bounded FIFO with an
  explicit overflow policy. ``queue.Queue`` is not used because it
  lacks drop-oldest semantics.
- ``bounded_exporter`` — background-thread drainer around ``queue``
  that calls ``_lib.otel_emit.export_events`` with a short socket
  timeout. Shared-singleton accessor ``get_bounded_exporter()``.
"""

from __future__ import annotations

from .queue import BoundedQueue, OverflowPolicy  # noqa: F401

__all__ = [
    "BoundedQueue",
    "OverflowPolicy",
]
