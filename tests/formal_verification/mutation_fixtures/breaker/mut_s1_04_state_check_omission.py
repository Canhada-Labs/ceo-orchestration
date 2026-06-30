"""Mutation S1-04: state check omission in threshold branch.

Original ``_breaker.py:207-211`` gates the open transition on BOTH
``state == CLOSED`` AND ``len(failures) >= threshold``. The mutated
path drops the state check, so a record_failure while HALF_OPEN (where
the failures deque carries probe-phase failures but the HALF_OPEN
branch above already handled the transition) can re-call
``_open_locked`` spuriously — but more importantly, calling
record_failure after the breaker just opened (state=OPEN) re-enters
``_open_locked`` and resets ``opened_at`` to the new `now`, pushing
the half_open_hold_s deadline out. The S1 test asserts a closed->open
transition uses the correct path.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "closed->open threshold branch drops the `state == CLOSED` guard, so "
    "record_failure on an already-OPEN breaker re-opens and resets the "
    "half_open_hold_s timer, preventing heal."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-04 applied."""

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

                # MUTATION: `state == CLOSED` guard removed. This makes
                # the gate fire on any threshold crossing regardless of
                # current state. In the S1 test we drive threshold+K
                # failures; without the state guard the Kth extra call
                # after the breaker is already OPEN re-enters
                # `_open_locked` and resets opened_at → breaker never
                # reaches HALF_OPEN within the expected window.
                if len(self._failures) >= self._threshold:
                    self._open_locked(now)

    Mutant.__name__ = "CircuitBreakerMut_S1_04"
    return Mutant
