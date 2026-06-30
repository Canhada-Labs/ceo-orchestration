"""Mutation S2-02: threading.Lock removed from should_allow.

Original ``_breaker.py:164`` acquires ``self._lock`` at the head of
should_allow. The mutated path removes the lock entirely, so
``_probe_available`` checks and mutations are non-atomic. Under
concurrent access the S2 singleton invariant fails.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "should_allow runs without holding self._lock; probe_available check + "
    "set is non-atomic under concurrent threads."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S2-02 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def should_allow(self) -> bool:
            from _lib.adapters.live._breaker import BreakerState

            # MUTATION: `with self._lock:` removed. _refresh_state_locked
            # expects caller to hold the lock but we skip it — the
            # probe_available check/set becomes non-atomic.
            self._refresh_state_locked()
            if self._state == BreakerState.CLOSED:
                return True
            if self._state == BreakerState.OPEN:
                return False
            # Force a yield so the scheduler interleaves threads.
            import time as _time

            _time.sleep(0.0001)
            if self._probe_available:
                # Second yield between read and write widens the race.
                _time.sleep(0.0001)
                self._probe_available = False
                return True
            return False

    Mutant.__name__ = "CircuitBreakerMut_S2_02"
    return Mutant
