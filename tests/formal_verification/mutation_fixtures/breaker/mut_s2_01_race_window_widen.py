"""Mutation S2-01: race-window widening (lock release before probe consumed).

Original ``_breaker.py:154-174`` holds ``self._lock`` while consuming
``self._probe_available`` atomically. The mutated path releases the
lock before flipping the flag, creating a race window where two
concurrent callers both observe ``probe_available=True``. The S2
conformance test drives N threads concurrently and asserts exactly
one observes True.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "should_allow on HALF_OPEN releases self._lock BEFORE consuming the "
    "probe flag; two concurrent callers race and both see True."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S2-01 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def should_allow(self) -> bool:
            from _lib.adapters.live._breaker import BreakerState

            # MUTATION: lock scope shrunk — release before consuming probe.
            with self._lock:
                self._refresh_state_locked()
                state = self._state
                probe = self._probe_available
            # Lock released. Introduce a tiny sleep so the scheduler
            # has a chance to interleave; without it the GIL may mask
            # the bug on single-threaded runs.
            import time as _time

            _time.sleep(0.0001)
            if state == BreakerState.CLOSED:
                return True
            if state == BreakerState.OPEN:
                return False
            # HALF_OPEN outside the lock → race
            if probe:
                # Consume the flag AFTER lock release, allowing two
                # threads to both observe probe=True and both set it False.
                self._probe_available = False
                return True
            return False

    Mutant.__name__ = "CircuitBreakerMut_S2_01"
    return Mutant
