"""Mutation S3-02: action string mismatch (typo `breaker_close`).

The S3 conformance test asserts the emitted audit event carries
``action == "breaker_opened"``. Mutated variant emits a wrong action
string — ``_write_event`` in audit_emit.py rejects unknown actions
(falls to breadcrumb), so the audit log never gets the event → test
assertion fails. Even if the event made it through, the action string
would not match the assertion.
"""

from __future__ import annotations

from typing import Any, Dict

PROPERTY = "S3"
DESCRIPTION = (
    "emit writes `action='breaker_close'` typo (also not in _KNOWN_ACTIONS "
    "registry, so the event is dropped)."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S3-02 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _open_locked(self, now: float) -> None:
            from _lib import audit_emit
            from _lib.adapters.live._breaker import BreakerState

            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False
            # MUTATION: action string typo. _write_event rejects unknown
            # actions → event dropped to breadcrumb.
            bad_event: Dict[str, Any] = {
                "action": "breaker_close",  # typo; correct is "breaker_opened"
                "provider": getattr(self, "_provider", "test"),
                "failures_in_window": len(self._failures),
                "threshold": self._threshold,
                "reason": "server_error",
                "session_id": "",
                "project": "",
            }
            audit_emit._write_event(bad_event)

    Mutant.__name__ = "CircuitBreakerMut_S3_02"
    return Mutant
