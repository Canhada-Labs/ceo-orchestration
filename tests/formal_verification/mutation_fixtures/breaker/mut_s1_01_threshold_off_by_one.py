"""Mutation S1-01: threshold off-by-one.

Original ``_breaker.py:207-211`` uses ``>=`` (open on N-th failure).
Mutated path uses ``>`` (open only after N+1 failures). The S1
conformance test asserts that exactly ``threshold`` failures open the
breaker → this mutation must cause failure.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "threshold off-by-one: closed->open gate uses `>` instead of `>=`, so "
    "the breaker requires `threshold+1` failures before opening."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-01 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def record_failure(self, reason: str = "server_error") -> None:
            from _lib.adapters.live._breaker import (
                BreakerState,
                _NON_COUNTING_REASONS,
                _PERMANENT_OPEN_REASONS,
            )

            with self._lock:
                now = self._now()
                self._refresh_state_locked()

                if reason in _NON_COUNTING_REASONS:
                    return
                if reason in _PERMANENT_OPEN_REASONS:
                    self._open_locked(now)
                    return

                self._failures.append((now, reason))
                self._prune_window_locked(now)

                if self._state == BreakerState.HALF_OPEN:
                    self._open_locked(now)
                    return

                # MUTATION: was `>=` in unmutated source, now `>`
                if (
                    self._state == BreakerState.CLOSED
                    and len(self._failures) > self._threshold
                ):
                    self._open_locked(now)

    Mutant.__name__ = "CircuitBreakerMut_S1_01"
    return Mutant
