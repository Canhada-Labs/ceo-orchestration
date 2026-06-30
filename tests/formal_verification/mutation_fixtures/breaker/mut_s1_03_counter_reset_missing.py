"""Mutation S1-03: counter reset missing on healing path (both clear points removed).

The real ``_breaker.py`` has TWO clear points on the healing path:

- ``_refresh_state_locked:266`` clears failures on OPEN->HALF_OPEN.
- ``record_success:221`` clears failures on HALF_OPEN->CLOSED.

Either point alone is sufficient to keep the deque clean across a heal.
The real bug S1-03 models is the regression where BOTH defensive
clears are skipped — stale failures survive the heal and re-trip the
threshold on the next transient failure.

The mutation also touches the non-healing HALF_OPEN->OPEN path through
``record_failure``: by leaving the ``_prune_window_locked`` untouched
while disabling the heal-time clear, stale failures remain inside the
window and cause premature reopens.

The S1 conformance test Phase C exercises this directly: `threshold`
failures -> OPEN -> wait half_open_s -> HALF_OPEN -> record_success ->
CLOSED -> `threshold-1` fresh failures MUST still leave the breaker
CLOSED. Under the mutation, stale entries persist and trip the gate.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "Both heal-clear points removed: _refresh_state_locked on OPEN->HALF_OPEN "
    "and record_success on HALF_OPEN->CLOSED both skip `self._failures.clear()`. "
    "Stale pre-open failures survive the heal cycle and re-trip the threshold."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-03 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _refresh_state_locked(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            if self._state != BreakerState.OPEN or self._opened_at is None:
                return
            now = self._now()
            if (now - self._opened_at) >= self._half_open_s:
                self._state = BreakerState.HALF_OPEN
                self._probe_available = True
                # MUTATION: `self._failures.clear()` removed from refresh

        def record_success(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            with self._lock:
                self._refresh_state_locked()
                if self._state == BreakerState.HALF_OPEN:
                    self._state = BreakerState.CLOSED
                    self._opened_at = None
                    self._probe_available = False
                    # MUTATION: `self._failures.clear()` removed from success
                    return
                if self._state == BreakerState.CLOSED:
                    return
                self._state = BreakerState.CLOSED
                self._opened_at = None
                self._probe_available = False
                self._failures.clear()

    Mutant.__name__ = "CircuitBreakerMut_S1_03"
    return Mutant
