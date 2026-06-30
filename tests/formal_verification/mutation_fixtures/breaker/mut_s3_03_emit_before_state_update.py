"""Mutation S3-03: emit fires BEFORE state becomes OPEN.

ADR-040 §7 contract: audit event snapshot reflects the POST-transition
state. The mutated path emits with ``state=closed`` still live (before
``self._state = OPEN`` runs), so the event's ``failures_in_window``
is read pre-transition but the event itself carries a stale snapshot.

More importantly: the S3 conformance test asserts that at the moment
of emit, ``self._state == BreakerState.OPEN``. The test inspects a
SnapshotProbe on the emit call; if the snapshot reports ``closed``,
the test fails.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "emit_breaker_opened fires BEFORE state transition; snapshot carries "
    "stale closed state."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S3-03 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _open_locked(self, now: float) -> None:
            from _lib import audit_emit
            from _lib.adapters.live._breaker import BreakerState

            # MUTATION: emit BEFORE state update. Observer sees state=closed.
            audit_emit.emit_breaker_opened(
                provider=getattr(self, "_provider", "test"),
                failures_in_window=len(self._failures),
                threshold=self._threshold,
                reason="server_error",
            )
            # (state transition happens AFTER the emit — wrong order)
            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False

    Mutant.__name__ = "CircuitBreakerMut_S3_03"
    return Mutant
