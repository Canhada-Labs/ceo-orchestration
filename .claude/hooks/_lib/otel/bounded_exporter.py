"""Fire-and-forget OTEL exporter with bounded queue (PLAN-012 CRITICAL-3).

Wraps the existing ``_lib.otel_emit`` sync library so hook / library
callers can enqueue spans without blocking. The queue is drained by a
single background thread; send failures are swallowed so the primary
audit-log.jsonl path is never back-pressured.

## Why a separate thread vs asyncio

The existing hook runtime is stdlib-only and synchronous. Starting an
event loop per hook invocation would break the fail-open timing budget
(ADR-005, 5s ceiling). A daemon thread is cheap, stdlib-pure, and
matches the "fire-and-forget" semantics the audit path demands.

## Contract (debate CRITICAL-3)

1. ``enqueue_span`` must return in <10ms even when the collector is
   unreachable. Measured at the unit-test level.
2. Queue is bounded. Drop-oldest at maxsize so the audit primary path
   never sees backpressure.
3. ``otel_export_dropped`` is emitted only for explicit drops (host/
   scheme rejects, payload redaction). Queue overflows emit a separate
   ``otel_export_dropped`` with reason ``"queue_overflow"`` — but
   batched so a burst of 1000 overflows produces one audit event, not
   1000 (cascade-prevention).
4. ``shutdown()`` flushes within ``grace_s`` then stops the thread. It
   is idempotent and safe to call from ``atexit``.

## Global singleton

``get_bounded_exporter()`` returns a lazily-constructed process-wide
instance. Tests that need isolation can construct their own via
``BoundedExporter(...)`` or reset via ``_reset_singleton_for_tests()``.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import otel_emit as _otel  # noqa: E402
from .queue import BoundedQueue, OverflowPolicy  # noqa: E402


# Default knobs — per PLAN-012 Phase 3 D4.2.
DEFAULT_MAXSIZE = 1000
DEFAULT_DRAIN_INTERVAL_S = 0.5
DEFAULT_BATCH_SIZE = 100
DEFAULT_SEND_TIMEOUT_S = 2.0


# Public type alias for what we enqueue. A "span" is any mapping the
# downstream ``otel_emit.export_events`` will accept — historically
# this is an event-shaped dict (``{"action": ..., "ts": ..., ...}``).
Span = Mapping[str, Any]


class BoundedExporter:
    """Non-blocking OTEL exporter over a bounded queue + drainer thread.

    Public API:

    - ``enqueue_span(span)`` — non-blocking, best-effort.
    - ``flush(timeout_s=5.0)`` — block until empty or timeout.
    - ``shutdown()`` — flush then stop the thread.
    - ``snapshot()`` — introspection (queue stats + send counters).
    """

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        allowed_hosts: Optional[Iterable[str]] = None,
        maxsize: int = DEFAULT_MAXSIZE,
        drain_interval_s: float = DEFAULT_DRAIN_INTERVAL_S,
        batch_size: int = DEFAULT_BATCH_SIZE,
        send_timeout_s: float = DEFAULT_SEND_TIMEOUT_S,
        exporter: Optional[Callable[..., Any]] = None,
        audit_emit: Optional[Callable[..., None]] = None,
        auto_start: bool = True,
        overflow_audit_batch: int = 1000,
    ) -> None:
        # Endpoint + host allowlist are read lazily each send so env-var
        # rotations take effect without restarting the exporter.
        self._endpoint = endpoint
        self._allowed_hosts: Optional[List[str]] = (
            list(allowed_hosts) if allowed_hosts else None
        )
        self._send_timeout_s = float(send_timeout_s)
        self._drain_interval_s = float(drain_interval_s)
        self._batch_size = int(batch_size)

        # Dependency injection for tests — default to the real exporter.
        self._exporter = exporter or _otel.try_export_events
        # Same trick for the audit breadcrumb emitter so tests can count.
        self._audit_emit = audit_emit

        self._queue: BoundedQueue[Span] = BoundedQueue(
            maxsize=maxsize, on_overflow=OverflowPolicy.DROP_OLDEST
        )

        # Thread control.
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._shutdown_lock = threading.Lock()

        # Counters — accessed under self._counter_lock.
        self._counter_lock = threading.Lock()
        self._sends_ok = 0
        self._sends_failed = 0
        self._spans_sent = 0
        # Bucketed overflow audit so a 1000-burst → one event, not 1000.
        self._overflow_last_seen = 0  # dropped_count checkpoint
        self._overflow_audit_batch = int(overflow_audit_batch)

        if auto_start:
            self.start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background drainer thread. Idempotent."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._drain_loop,
            name="otel-bounded-exporter",
            daemon=True,
        )
        self._thread.start()

    def shutdown(self, *, grace_s: float = 5.0) -> int:
        """Flush then stop the thread. Return #remaining spans.

        Idempotent: second call is a no-op. Safe from ``atexit``.
        """
        with self._shutdown_lock:
            if self._thread is None:
                # Never started. Drain what we can synchronously.
                return len(self._queue)
            # Signal stop and attempt a final flush on the way out.
            remaining = self.flush(timeout_s=grace_s)
            self._stop_event.set()
            try:
                self._thread.join(timeout=max(0.1, grace_s))
            except RuntimeError:
                pass
            self._thread = None
            return remaining

    def flush(self, *, timeout_s: float = 5.0) -> int:
        """Block until queue is empty or timeout elapses.

        Returns the number of items still in the queue on exit.
        """
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        while len(self._queue) > 0:
            # Drain synchronously in the caller's thread so flush()
            # works even if the worker hit an exception and stopped.
            batch = self._queue.drain(max_items=self._batch_size)
            if batch:
                self._send_batch(batch)
            if len(self._queue) == 0:
                return 0
            if time.monotonic() >= deadline:
                return len(self._queue)
            # Small sleep to avoid a hot spin.
            time.sleep(0.005)
        return 0

    # ------------------------------------------------------------------
    # Public producer-side API
    # ------------------------------------------------------------------

    def enqueue_span(self, span: Span) -> bool:
        """Enqueue a span. Returns True if accepted.

        DROP_OLDEST policy means this ALWAYS returns True unless the
        exporter has been shut down. Must complete in <10ms — no I/O,
        no network, only a memory write under a ``threading.Lock``.
        """
        if self._stop_event.is_set() and self._thread is None:
            # Post-shutdown: silently drop. Producer never blocks.
            return False
        accepted = self._queue.enqueue(span)
        # Bucket queue-overflow audit events to prevent cascade
        # (1000 overflows → 1 audit write, not 1000).
        self._maybe_emit_overflow_audit()
        return accepted

    def snapshot(self) -> Dict[str, Any]:
        """Read-only counters + queue stats. Cheap."""
        qs = self._queue.snapshot()
        with self._counter_lock:
            stats = {
                "queue": qs,
                "sends_ok": self._sends_ok,
                "sends_failed": self._sends_failed,
                "spans_sent": self._spans_sent,
                "thread_alive": bool(
                    self._thread is not None and self._thread.is_alive()
                ),
                "endpoint_set": bool(self._endpoint),
            }
        return stats

    # ------------------------------------------------------------------
    # Drainer loop
    # ------------------------------------------------------------------

    def _drain_loop(self) -> None:
        """Background thread body — drain + send on a cadence."""
        while not self._stop_event.is_set():
            try:
                batch = self._queue.drain(max_items=self._batch_size)
                if batch:
                    self._send_batch(batch)
            except Exception:
                # Thread must not die; counters live in try blocks.
                with self._counter_lock:
                    self._sends_failed += 1
            # Sleep between drains — don't spin.
            self._stop_event.wait(timeout=self._drain_interval_s)

    def _send_batch(self, batch: List[Span]) -> None:
        """Best-effort send — failures are swallowed.

        We call ``otel_emit.try_export_events`` which itself catches
        ``OtelExportError`` and returns None; we count the outcome.
        Cascade-prevention: never raise, never retry inline, never
        re-enqueue — if the collector is down, it stays down and we
        drop rather than build an unbounded memory back-pressure.
        """
        endpoint = self._endpoint or os.environ.get("CEO_OTEL_ENDPOINT")
        if not endpoint:
            # No endpoint configured → drop silently (no collector set up).
            with self._counter_lock:
                self._sends_failed += 1
            return

        try:
            result = self._exporter(
                endpoint,
                batch,
                allowed_hosts=self._allowed_hosts,
                timeout=self._send_timeout_s,
            )
        except Exception:
            # try_export_events should swallow, but double-guard here.
            result = None

        with self._counter_lock:
            if result and isinstance(result, dict) and not result.get("disabled"):
                self._sends_ok += 1
                self._spans_sent += int(result.get("exported", 0))
            else:
                self._sends_failed += 1

    # ------------------------------------------------------------------
    # Overflow audit (batched to prevent cascade)
    # ------------------------------------------------------------------

    def _maybe_emit_overflow_audit(self) -> None:
        """Emit one ``otel_export_dropped`` per batch of N overflows.

        Without batching, a 1000-span burst against an unreachable
        collector would produce 1000 audit writes which could itself
        saturate the audit filelock — a self-inflicted cascade.
        """
        current_dropped = self._queue.dropped_count
        with self._counter_lock:
            delta = current_dropped - self._overflow_last_seen
            if delta < self._overflow_audit_batch:
                return
            # Checkpoint up to the current count.
            self._overflow_last_seen = current_dropped

        # Emit the breadcrumb outside the lock so a slow filelock doesn't
        # serialize all the producers.
        emitter = self._audit_emit or _otel._safe_emit_drop
        try:
            emitter(
                fields_dropped_count=delta,
                endpoint_host="",
                reason="queue_overflow",
            )
        except Exception:
            # Fail-open per ADR-005.
            pass


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_singleton_lock = threading.Lock()
_singleton: Optional[BoundedExporter] = None


def get_bounded_exporter(**kwargs: Any) -> BoundedExporter:
    """Return a process-wide ``BoundedExporter``.

    Default-OFF: when ``CEO_OTEL_ENDPOINT`` is absent and no ``endpoint``
    kwarg is supplied, the exporter is constructed with ``auto_start=False``
    so NO background thread is created.  This satisfies the WIRE-OTEL
    contract: zero behaviour change (no thread, no overhead) until an
    endpoint is explicitly configured.

    Activation: set ``CEO_OTEL_ENDPOINT=https://<host>/v1/traces`` and
    ``CEO_OTEL_ALLOWED_HOSTS=<host>`` before the first call (or pass
    ``endpoint=`` + ``allowed_hosts=`` as kwargs).

    First caller wins on kwargs; subsequent callers get the same instance.
    Tests that need an isolated instance should construct
    ``BoundedExporter(...)`` directly or call
    ``_reset_singleton_for_tests()`` first.
    """
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            # Default-OFF: suppress thread start when no endpoint is configured.
            endpoint_from_env = os.environ.get("CEO_OTEL_ENDPOINT", "")
            endpoint_from_kwargs = kwargs.get("endpoint") or ""
            if not endpoint_from_env and not endpoint_from_kwargs:
                # No endpoint → no thread, no overhead, strict no-op on send.
                kwargs.setdefault("auto_start", False)
            _singleton = BoundedExporter(**kwargs)
        return _singleton


def maybe_enqueue_span(span: Span) -> bool:
    """Convenience wrapper — enqueue a span only when OTEL is configured.

    Default-OFF contract:
    - ``CEO_OTEL_ENDPOINT`` not set → immediate return False, zero I/O,
      zero thread created (singleton is constructed without auto_start).
    - ``CEO_OTEL_ENDPOINT`` set → delegate to the singleton exporter.

    This is the intended hook-side call site; hooks import this function
    and call it in one line without needing to manage the singleton
    directly.  Fail-open per ADR-005: any exception is swallowed.
    """
    endpoint = os.environ.get("CEO_OTEL_ENDPOINT", "")
    if not endpoint:
        return False  # strict no-op — no singleton created, no thread
    try:
        return get_bounded_exporter().enqueue_span(span)
    except Exception:
        return False


def _reset_singleton_for_tests() -> None:
    """Shutdown + clear the process-wide singleton. Tests only."""
    global _singleton
    with _singleton_lock:
        if _singleton is not None:
            try:
                _singleton.shutdown(grace_s=0.5)
            except Exception:
                pass
        _singleton = None
