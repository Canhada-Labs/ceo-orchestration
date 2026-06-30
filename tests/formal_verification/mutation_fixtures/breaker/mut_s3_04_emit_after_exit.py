"""Mutation S3-04: early return causes emit to be skipped.

Original contract: every ``_open_locked`` call emits. The mutated
path returns early BEFORE the emit (e.g. simulating a conditional
guard against "already open" that also swallows the very transition
it was gating). The S3 conformance test asserts one emit per fresh
closed->open transition.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "_open_locked returns early (before emit) when a bogus `already_dirty` "
    "flag is set after state update; emit is skipped."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S3-04 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _open_locked(self, now: float) -> None:
            from _lib.adapters.live._breaker import BreakerState

            # MUTATION: state transitions, then an early return skips emit.
            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False
            # Simulated faulty guard that always trips:
            return  # emit skipped

    Mutant.__name__ = "CircuitBreakerMut_S3_04"
    return Mutant
