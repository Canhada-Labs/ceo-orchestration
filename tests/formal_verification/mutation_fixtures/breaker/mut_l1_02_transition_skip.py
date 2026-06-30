"""Mutation L1-02: transition from HALF_OPEN to CLOSED/OPEN skipped on probe.

Original record_success on HALF_OPEN transitions to CLOSED.
Original record_failure on HALF_OPEN transitions back to OPEN.
The mutated path skips both transitions — HALF_OPEN becomes a sink state.

The L1 conformance test drives a full heal cycle (open → wait →
HALF_OPEN probe → success → CLOSED) and asserts the breaker ends in
CLOSED. This mutation leaves it stuck in HALF_OPEN.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "record_success + record_failure on HALF_OPEN both become no-ops; "
    "HALF_OPEN is a stuck state after probe."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with L1-02 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def record_success(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            with self._lock:
                self._refresh_state_locked()
                if self._state == BreakerState.HALF_OPEN:
                    # MUTATION: no transition out of HALF_OPEN.
                    return
                if self._state == BreakerState.CLOSED:
                    return
                self._state = BreakerState.CLOSED
                self._opened_at = None
                self._probe_available = False
                self._failures.clear()

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
                    # MUTATION: no transition from HALF_OPEN to OPEN.
                    return

                if (
                    self._state == BreakerState.CLOSED
                    and len(self._failures) >= self._threshold
                ):
                    self._open_locked(now)

    Mutant.__name__ = "CircuitBreakerMut_L1_02"
    return Mutant
