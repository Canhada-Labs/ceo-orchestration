"""Bounded FIFO queue with pluggable overflow policy.

Used by the OTEL bounded exporter (PLAN-012 Phase 3 D4.2 / CRITICAL-3)
to isolate the audit primary path from OTEL collector latency or
unavailability. ``queue.Queue`` cannot be used directly because it
lacks a drop-oldest overflow semantic.

Thread-safety: every mutator / reader takes a single module-local
``threading.Lock``. Contention is negligible because the queue holds
small dict payloads (OTLP spans) and operations are O(1) on
``collections.deque`` from the head and tail.

Overflow policies (``OverflowPolicy``):

- ``DROP_OLDEST`` (default) — when full, dequeue the oldest item
  before enqueue. ``enqueue`` returns True; ``dropped_count`` +1;
  ``overflow_count`` +1.
- ``DROP_NEWEST`` — when full, refuse the new item.
  ``enqueue`` returns False; ``dropped_count`` +1; no overflow event.
- ``BLOCK`` — when full, wait up to ``timeout_s`` for space. On
  timeout, return False (no drop).

All three policies are stdlib-pure (``collections.deque`` + Lock).
"""

from __future__ import annotations

import enum
import threading
import time
from collections import deque
from typing import Callable, Deque, Generic, List, Optional, TypeVar

T = TypeVar("T")


class OverflowPolicy(str, enum.Enum):
    """How to handle enqueue when at maxsize."""

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"


# Accepted string aliases for the ``on_overflow`` kwarg. Strings keep
# the public API stable if a caller prefers not to import the enum.
_POLICY_BY_NAME = {
    "drop_oldest": OverflowPolicy.DROP_OLDEST,
    "drop_newest": OverflowPolicy.DROP_NEWEST,
    "block": OverflowPolicy.BLOCK,
}


class BoundedQueue(Generic[T]):
    """Bounded FIFO with explicit overflow policy.

    Public surface:

    - ``enqueue(item, *, timeout_s=0.0) -> bool``
    - ``drain(*, max_items=100) -> List[T]``
    - ``__len__()`` — current size
    - ``dropped_count`` — items removed by any overflow policy since
      construction (``DROP_OLDEST`` + ``DROP_NEWEST`` both increment).
    - ``overflow_count`` — successful enqueues that *caused* a drop
      (only ``DROP_OLDEST`` increments this — it's the "accepted but
      at the cost of an older item" signal).
    - ``maxsize`` / ``policy`` — introspection.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        on_overflow: "str | OverflowPolicy" = OverflowPolicy.DROP_OLDEST,
        *,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if not isinstance(maxsize, int):
            raise TypeError(f"maxsize must be int, got {type(maxsize).__name__}")
        if maxsize <= 0:
            raise ValueError(f"maxsize must be > 0, got {maxsize}")

        if isinstance(on_overflow, OverflowPolicy):
            policy = on_overflow
        else:
            try:
                policy = _POLICY_BY_NAME[str(on_overflow)]
            except KeyError as e:
                raise ValueError(
                    f"unknown overflow policy: {on_overflow!r}"
                ) from e

        self._maxsize = maxsize
        self._policy: OverflowPolicy = policy
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        # `deque` gives us O(1) popleft() + append() for drop-oldest.
        self._items: Deque[T] = deque()
        self._dropped = 0
        self._overflow = 0
        # Condition variable for BLOCK mode. Shares the lock so we can
        # atomically "check full → wait → re-check".
        self._not_full = threading.Condition(self._lock)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def policy(self) -> OverflowPolicy:
        return self._policy

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped

    @property
    def overflow_count(self) -> int:
        with self._lock:
            return self._overflow

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def enqueue(self, item: T, *, timeout_s: float = 0.0) -> bool:
        """Enqueue ``item``. Return True if accepted, False if rejected.

        Accepted semantics per policy:

        - DROP_OLDEST: always accepted; ``overflow_count`` increments
          if an older item had to be dropped to make room.
        - DROP_NEWEST: accepted iff under capacity; else rejected.
        - BLOCK: accepted iff space appears within ``timeout_s``.
        """
        if self._policy is OverflowPolicy.DROP_OLDEST:
            with self._lock:
                if len(self._items) >= self._maxsize:
                    # Make room by dropping head. This is O(1).
                    self._items.popleft()
                    self._dropped += 1
                    self._overflow += 1
                self._items.append(item)
                self._not_full.notify()
                return True

        if self._policy is OverflowPolicy.DROP_NEWEST:
            with self._lock:
                if len(self._items) >= self._maxsize:
                    self._dropped += 1
                    return False
                self._items.append(item)
                self._not_full.notify()
                return True

        # BLOCK
        deadline = self._clock() + max(0.0, float(timeout_s))
        with self._not_full:
            while len(self._items) >= self._maxsize:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return False
                # wait() releases the lock while blocked.
                self._not_full.wait(timeout=remaining)
            self._items.append(item)
            self._not_full.notify()
            return True

    def drain(self, *, max_items: int = 100) -> List[T]:
        """Remove and return up to ``max_items`` from the head.

        Returns empty list when queue is empty. Thread-safe; BLOCK
        producers waiting on space are woken up after a drain.
        """
        if not isinstance(max_items, int) or max_items <= 0:
            raise ValueError("max_items must be positive int")

        out: List[T] = []
        with self._not_full:
            # popleft is O(1); don't slice the deque.
            limit = min(max_items, len(self._items))
            for _ in range(limit):
                out.append(self._items.popleft())
            if out:
                # Wake up BLOCK producers that may be waiting on space.
                self._not_full.notify_all()
        return out

    def drain_all(self) -> List[T]:
        """Shortcut for drain() until the queue is empty. Unbounded."""
        collected: List[T] = []
        while True:
            chunk = self.drain(max_items=256)
            if not chunk:
                break
            collected.extend(chunk)
        return collected

    def clear(self) -> int:
        """Empty the queue. Return number of items cleared.

        Does NOT increment dropped_count — this is an admin op, not an
        overflow.
        """
        with self._not_full:
            n = len(self._items)
            self._items.clear()
            if n:
                self._not_full.notify_all()
            return n

    # ------------------------------------------------------------------
    # Debug / introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Point-in-time stats (thread-safe)."""
        with self._lock:
            return {
                "size": len(self._items),
                "maxsize": self._maxsize,
                "policy": self._policy.value,
                "dropped": self._dropped,
                "overflow": self._overflow,
            }
