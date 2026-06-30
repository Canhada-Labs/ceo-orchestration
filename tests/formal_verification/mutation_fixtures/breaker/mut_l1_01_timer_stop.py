"""Mutation L1-01: timer stop — OPEN never transitions to HALF_OPEN.

Original ``_breaker.py:257-266`` flips OPEN→HALF_OPEN when
``(now - opened_at) >= half_open_s``. The mutated path neutralises
the refresh, so OPEN becomes a terminal state — liveness violated.
"""

from __future__ import annotations

PROPERTY = "L1"
DESCRIPTION = (
    "_refresh_state_locked is a no-op; OPEN breaker never transitions "
    "back to HALF_OPEN no matter how far the clock advances."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with L1-01 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _refresh_state_locked(self) -> None:
            # MUTATION: no-op. OPEN is terminal.
            return

    Mutant.__name__ = "CircuitBreakerMut_L1_01"
    return Mutant
