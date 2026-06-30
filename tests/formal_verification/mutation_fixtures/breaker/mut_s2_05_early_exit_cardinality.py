"""Mutation S2-05: early exit cardinality check — returns True unconditionally.

Original ``_breaker.py:170-174`` returns True only if
``probe_available`` is True, then consumes it. The mutated path
returns True unconditionally in HALF_OPEN, violating the singleton
bound.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "HALF_OPEN branch returns True unconditionally (ignores "
    "probe_available); cardinality exceeds 1."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S2-05 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def should_allow(self) -> bool:
            from _lib.adapters.live._breaker import BreakerState

            with self._lock:
                self._refresh_state_locked()
                if self._state == BreakerState.CLOSED:
                    return True
                if self._state == BreakerState.OPEN:
                    return False
                # MUTATION: return True irrespective of probe_available
                return True

    Mutant.__name__ = "CircuitBreakerMut_S2_05"
    return Mutant
