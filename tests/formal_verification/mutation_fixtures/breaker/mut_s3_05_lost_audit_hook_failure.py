"""Mutation S3-05: exception from emit swallowed without propagation.

The audit hook raises but the caller catches bare Exception and
continues. From the conformance-test POV this surfaces as NO audit
entry on disk for the transition — exceptions silently drop the
event. The S3 test asserts exactly-one event; zero events → fail.

Note: the real emit uses fail-open breadcrumbs (by design), but the
ADR-040 §7 contract requires the event land in audit-log.jsonl on
healthy paths. A mutation that injects a raise + swallow simulates a
regression where the emit path itself is broken but the caller masks
the failure.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "emit raises exception; _open_locked catches bare Exception and "
    "silently drops the event. No audit record lands on disk."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S3-05 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _open_locked(self, now: float) -> None:
            from _lib.adapters.live._breaker import BreakerState

            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False
            # MUTATION: emit raises and the caller swallows. Net effect:
            # zero audit events. We simulate the "raise + swallow" by
            # calling a stub that raises + catching bare Exception.
            try:
                raise RuntimeError("simulated emit failure; swallowed")
            except Exception:
                pass  # mutation: silent drop

    Mutant.__name__ = "CircuitBreakerMut_S3_05"
    return Mutant
