"""Mutation L1-03: introduction of a terminal BROKEN state.

Original state machine is {CLOSED, OPEN, HALF_OPEN}, all non-terminal.
The mutation injects a new terminal state: after HALF_OPEN probe
failure, transition to a BROKEN sentinel state (modelled as a string
that bypasses the enum). The L1 conformance test asserts no terminal
state is reachable within the bounded harness.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "HALF_OPEN probe failure transitions to a new terminal `broken` state "
    "(string literal injected, enum bypassed); no subsequent transition "
    "paths reachable."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with L1-03 applied."""

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
                    # MUTATION: transition to a string-literal terminal
                    # state that no other branch handles. The breaker is
                    # now stuck in "broken".
                    self._state = "broken"  # type: ignore[assignment]
                    self._opened_at = None
                    return

                if (
                    self._state == BreakerState.CLOSED
                    and len(self._failures) >= self._threshold
                ):
                    self._open_locked(now)

        def _refresh_state_locked(self) -> None:
            from _lib.adapters.live._breaker import BreakerState

            # Terminal state bypasses all refresh logic.
            if self._state == "broken":  # type: ignore[comparison-overlap]
                return
            if self._state != BreakerState.OPEN or self._opened_at is None:
                return
            now = self._now()
            if (now - self._opened_at) >= self._half_open_s:
                self._state = BreakerState.HALF_OPEN
                self._probe_available = True
                self._failures.clear()

    Mutant.__name__ = "CircuitBreakerMut_L1_03"
    return Mutant
