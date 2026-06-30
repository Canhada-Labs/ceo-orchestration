"""Mutation S1-06: early return before `_open_locked` call.

Original ``_breaker.py:207-211`` computes the gate and falls through to
``_open_locked``. The mutated path returns immediately after the
threshold check, so the breaker NEVER opens via the normal path. The
S1 conformance test asserts the breaker reaches OPEN state after
threshold failures — this mutation leaves it CLOSED forever.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "closed->open branch falls through to an early `return` before "
    "`_open_locked` fires; breaker never opens on threshold crossing."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-06 applied."""

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

                if (
                    self._state == BreakerState.CLOSED
                    and len(self._failures) >= self._threshold
                ):
                    # MUTATION: early return before `_open_locked(now)`
                    return

    Mutant.__name__ = "CircuitBreakerMut_S1_06"
    return Mutant
