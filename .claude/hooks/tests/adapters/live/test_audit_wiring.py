"""PLAN-120 E2-F2 regression — live-adapter audit telemetry is actually wired.

Before S185, every production live adapter instantiated ``LiveTransport(self.policy)``
WITHOUT an ``on_audit=`` kwarg, so the transport fell back to its no-op default
lambda and the three ``live_adapter_call_started`` / ``_succeeded`` / ``_failed``
events (registered in ``_KNOWN_ACTIONS`` + emitted from ``_transport.py``) NEVER
reached the audit log. The fix wires
:func:`_lib.adapters.live._transport.audit_emit_dispatch` into each adapter's
default transport.

This test asserts the contract for all four adapters so the wiring cannot
silently regress again.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[3]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.adapters.live import (  # noqa: E402
    ClaudeLiveAdapter,
    GeminiLiveAdapter,
    LocalLiveAdapter,
    OpenAILiveAdapter,
)
from _lib.adapters.live._transport import audit_emit_dispatch  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class AdapterAuditWiringTest(TestEnvContext):
    """Each adapter's DEFAULT transport must route audit to audit_emit_dispatch.

    Subclasses TestEnvContext (PLAN-119 isolation) so the audit_emit_dispatch
    calls below land in the isolated audit dir, never the live ~/.claude chain.
    """

    def _assert_wired(self, adapter) -> None:
        got = adapter._transport._on_audit
        self.assertIs(
            got,
            audit_emit_dispatch,
            f"{type(adapter).__name__} default LiveTransport must wire "
            f"on_audit=audit_emit_dispatch (PLAN-120 E2-F2); got "
            f"{getattr(got, '__name__', got)!r} — live_adapter_call_* telemetry "
            f"would be silently dropped.",
        )

    def test_claude_wires_audit(self) -> None:
        self._assert_wired(ClaudeLiveAdapter())

    def test_gemini_wires_audit(self) -> None:
        self._assert_wired(GeminiLiveAdapter())

    def test_openai_wires_audit(self) -> None:
        self._assert_wired(OpenAILiveAdapter())

    def test_local_wires_audit(self) -> None:
        self._assert_wired(LocalLiveAdapter())

    def test_explicit_transport_override_still_honored(self) -> None:
        # A caller-supplied transport must NOT be overridden by the default wiring.
        from _lib.adapters.live._transport import LiveTransport
        from _lib.adapters.live._policy import ClaudeLivePolicy

        sentinel = LiveTransport(ClaudeLivePolicy(), on_audit=lambda *_a, **_k: None)
        adapter = ClaudeLiveAdapter(transport=sentinel)
        self.assertIs(adapter._transport, sentinel)

    def test_dispatch_is_fail_open(self) -> None:
        # Must never raise into the live-call path, even on an unknown action
        # or malformed fields (telemetry must not break the request).
        audit_emit_dispatch("not_a_real_action", {})
        audit_emit_dispatch("live_adapter_call_started", {})  # missing fields → defaults


if __name__ == "__main__":
    unittest.main()
