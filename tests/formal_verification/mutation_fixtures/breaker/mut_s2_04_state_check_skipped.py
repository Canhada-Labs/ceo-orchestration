"""Mutation S2-04: state check skipped — HALF_OPEN branch unreachable.

Original ``_breaker.py:168-174`` branches explicitly on HALF_OPEN.
The mutated path reverses the order so the HALF_OPEN branch runs for
OPEN too; both return True ignoring probe_available. Downstream this
lets multiple concurrent callers proceed in OPEN state, violating the
S2 singleton cardinality (since OPEN has no probe slot at all).
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "should_allow state ordering dropped: OPEN falls through to the "
    "HALF_OPEN probe gate, always returning True when probe_available."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S2-04 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def should_allow(self) -> bool:
            from _lib.adapters.live._breaker import BreakerState

            with self._lock:
                self._refresh_state_locked()
                if self._state == BreakerState.CLOSED:
                    return True
                # MUTATION: HALF_OPEN gate runs for both OPEN and
                # HALF_OPEN, so if probe_available is left True (as it is
                # between concurrent callers), two callers proceed.
                if self._probe_available:
                    # But we DO NOT consume the flag, letting multiple
                    # callers pass.
                    return True
                if self._state == BreakerState.OPEN:
                    return False
                return False

    Mutant.__name__ = "CircuitBreakerMut_S2_04"
    return Mutant
