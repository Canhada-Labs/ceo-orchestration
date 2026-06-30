"""Mutation L1-04: half_open_hold_s compared with `<` instead of `>=`.

Original ``_breaker.py:262`` uses ``>=`` to fire OPEN→HALF_OPEN when
enough time has passed. The mutated path uses ``<`` so the transition
fires ONLY while the hold timer is still live, and NOT after it
elapses — the exact opposite of correctness. HALF_OPEN is unreachable
after the first elapsed-hold tick.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "_refresh_state_locked compares (now - opened_at) with `<` instead of "
    "`>=`, so OPEN->HALF_OPEN fires only within the hold window (where "
    "the breaker should stay OPEN) and never after it elapses."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with L1-04 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _refresh_state_locked(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            if self._state != BreakerState.OPEN or self._opened_at is None:
                return
            now = self._now()
            # MUTATION: `>=` flipped to `<`. Transition fires only while
            # the hold is still active; never after elapse.
            if (now - self._opened_at) < self._half_open_s:
                self._state = BreakerState.HALF_OPEN
                self._probe_available = True
                self._failures.clear()

    Mutant.__name__ = "CircuitBreakerMut_L1_04"
    return Mutant
