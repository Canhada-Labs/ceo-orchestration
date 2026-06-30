"""Mutation S1-05: boolean flip on threshold condition.

Original ``_breaker.py:207-211`` opens the breaker when count >=
threshold. The mutated path flips the boolean sense — opens when count
< threshold — which is catastrophic: first failure opens the breaker.
The S1 test feeds exactly `threshold` failures and asserts open after
the N-th (not the 1st). This mutation violates that directly.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "closed->open threshold branch sense flipped: `>=` becomes `<`, so the "
    "breaker opens on the FIRST failure and never accumulates."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-05 applied."""

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

                # MUTATION: `>=` flipped to `<` — breaker opens on first
                # failure (1 < threshold) and never accumulates.
                if (
                    self._state == BreakerState.CLOSED
                    and len(self._failures) < self._threshold
                ):
                    self._open_locked(now)

    Mutant.__name__ = "CircuitBreakerMut_S1_05"
    return Mutant
