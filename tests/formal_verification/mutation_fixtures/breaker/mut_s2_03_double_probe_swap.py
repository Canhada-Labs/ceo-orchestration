"""Mutation S2-03: probe consumption removed.

Original ``_breaker.py:171-173`` consumes ``probe_available`` by
setting it to ``False`` as part of the True-return branch. The
mutated path never sets it False, so EVERY caller in HALF_OPEN sees
True — the singleton invariant collapses even in single-threaded mode.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "probe consumption line `self._probe_available = False` commented out; "
    "every HALF_OPEN caller gets True."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S2-03 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def should_allow(self) -> bool:
            from _lib.adapters.live._breaker import BreakerState

            with self._lock:
                self._refresh_state_locked()
                if self._state == BreakerState.CLOSED:
                    return True
                if self._state == BreakerState.OPEN:
                    return False
                if self._probe_available:
                    # MUTATION: `self._probe_available = False` removed.
                    # Probe flag never consumed → every caller sees True.
                    return True
                return False

    Mutant.__name__ = "CircuitBreakerMut_S2_03"
    return Mutant
