"""Mutation L1-05: clock regression — opened_at refreshed on every refresh.

Original ``_breaker.py:257-266`` reads ``opened_at`` once at open.
The mutated path silently resets ``opened_at = now`` each time
``_refresh_state_locked`` runs, so the hold timer never expires (it
constantly restarts). OPEN is effectively terminal.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "_refresh_state_locked silently resets opened_at to now at every "
    "call, so the half_open_hold_s timer never elapses."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with L1-05 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _refresh_state_locked(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            if self._state != BreakerState.OPEN or self._opened_at is None:
                return
            now = self._now()
            # MUTATION: reset opened_at every refresh. Timer never elapses.
            self._opened_at = now
            if (now - self._opened_at) >= self._half_open_s:
                # unreachable in practice because we just set opened_at = now
                self._state = BreakerState.HALF_OPEN
                self._probe_available = True
                self._failures.clear()

    Mutant.__name__ = "CircuitBreakerMut_L1_05"
    return Mutant
