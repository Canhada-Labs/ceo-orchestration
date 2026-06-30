"""Mutation S3-01: emit_breaker_opened call removed.

The S3 conformance test assumes Gap #4 is fixed: ``_open_locked``
invokes ``emit_breaker_opened``. The base class used by the conformance
harness is wrapped so the emit happens; this mutation overrides
``_open_locked`` to SKIP the emit, simulating the missing wire-up. The
S3 test asserts exactly one audit event is emitted per transition.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "emit_breaker_opened call skipped in _open_locked; state transitions "
    "but no audit event is written."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S3-01 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _open_locked(self, now: float) -> None:
            from _lib.adapters.live._breaker import BreakerState

            # MUTATION: no emit. State transitions silently.
            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False

    Mutant.__name__ = "CircuitBreakerMut_S3_01"
    return Mutant
