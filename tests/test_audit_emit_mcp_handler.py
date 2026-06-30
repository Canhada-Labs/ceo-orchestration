"""PLAN-085 Wave D.1 — ``mcp_handler_invoked`` production callsite tests.

4 cases verifying the emit primitive is registered, callable, and wired
into the MCP server dispatch pipeline (.claude/scripts/mcp-server/dispatch.py).

  1. test_mcp_handler_invoked_registered_in_known_actions
  2. test_emit_mcp_handler_invoked_writes_expected_fields
  3. test_dispatch_emit_invoke_calls_audit_emit
  4. test_emit_mcp_handler_invoked_never_raises_on_audit_log_fault

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
_MCP_SERVER = REPO_ROOT / ".claude" / "scripts" / "mcp-server"
for _p in (_HOOKS, _MCP_SERVER):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _lib.testing import TestEnvContext  # noqa: E402


class TestMcpHandlerInvokedRegistered(TestEnvContext):
    """Case 1 — ``mcp_handler_invoked`` MUST be in ``_KNOWN_ACTIONS``.

    Wave D.1 acceptance: the registration was authored in earlier PLANs
    (ADR-042 §Auth) but this test pins it as a hard invariant so a
    refactor of ``audit_emit._KNOWN_ACTIONS`` cannot silently drop it.
    """

    def test_mcp_handler_invoked_registered_in_known_actions(self) -> None:
        from _lib.audit_emit import _KNOWN_ACTIONS  # type: ignore
        self.assertIn(
            "mcp_handler_invoked",
            _KNOWN_ACTIONS,
            "PLAN-085 Wave D.1: mcp_handler_invoked must remain registered "
            "in audit_emit._KNOWN_ACTIONS (ADR-042 §Auth.5).",
        )


class TestEmitMcpHandlerInvokedFields(TestEnvContext):
    """Case 2 — emit primitive writes the expected canonical fields."""

    def _read_log(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_emit_mcp_handler_invoked_writes_expected_fields(self) -> None:
        from _lib import audit_emit  # type: ignore
        audit_emit.emit_mcp_handler_invoked(
            handler="list_skills",
            client_id="0123456789abcdef",
            transport="http",
            duration_ms=42,
            session_id="S-test-D1",
        )
        events = self._read_log()
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["action"], "mcp_handler_invoked")
        self.assertEqual(e["handler"], "list_skills")
        self.assertEqual(e["client_id"], "0123456789abcdef")
        self.assertEqual(e["transport"], "http")
        self.assertEqual(e["duration_ms"], 42)
        self.assertEqual(e["session_id"], "S-test-D1")


class TestDispatchEmitInvokeCallsiteWiring(TestEnvContext):
    """Case 3 — ``.claude/scripts/mcp-server/dispatch.py:emit_invoke`` forwards
    every kwarg to ``audit_emit.emit_mcp_handler_invoked``.

    This is the production callsite contract. We patch the audit_emit
    function in the dispatch module's namespace and verify the kwargs
    arrive verbatim (modulo client_id hashing).
    """

    def test_dispatch_emit_invoke_calls_audit_emit(self) -> None:
        # Lazy import — dispatch.py performs a sys.path bootstrap on
        # module load and imports peer handlers; only do that inside
        # the test so collection stays cheap.
        import dispatch  # type: ignore

        captured: Dict[str, Any] = {}

        def _fake_emit(**kw: Any) -> None:
            captured.update(kw)

        with mock.patch.object(
            dispatch.audit_emit, "emit_mcp_handler_invoked", side_effect=_fake_emit
        ):
            dispatch.emit_invoke(
                handler="get_skill",
                client_id="raw-client-token-not-hashed-yet",
                transport="stdio",
                duration_ms=17,
                session_id="S-dispatch",
                project="/tmp/project",
            )

        self.assertEqual(captured["handler"], "get_skill")
        self.assertEqual(captured["transport"], "stdio")
        self.assertEqual(captured["duration_ms"], 17)
        self.assertEqual(captured["session_id"], "S-dispatch")
        self.assertEqual(captured["project"], "/tmp/project")
        # client_id is hashed via auth.hash_client_id BEFORE reaching
        # audit_emit (ADR-042 §Auth.6 hygiene — raw token MUST NOT be
        # persisted). We don't assert the exact hash, only that the raw
        # token is NOT what was forwarded.
        self.assertNotEqual(captured["client_id"], "raw-client-token-not-hashed-yet")


class TestEmitMcpHandlerInvokedFailOpen(TestEnvContext):
    """Case 4 — emit primitive NEVER raises on audit-log write fault.

    ADR-005 fail-open contract: any exception inside the emit path must
    be swallowed silently. dispatch.emit_invoke wraps audit_emit in a
    bare ``except Exception: pass``; this case pins that contract.
    """

    def test_emit_mcp_handler_invoked_never_raises_on_audit_log_fault(self) -> None:
        import dispatch  # type: ignore

        def _raise(**kw: Any) -> None:
            raise RuntimeError("simulated audit-log write fault")

        with mock.patch.object(
            dispatch.audit_emit, "emit_mcp_handler_invoked", side_effect=_raise
        ):
            # MUST NOT raise.
            dispatch.emit_invoke(
                handler="list_skills",
                client_id="fedcba9876543210",
                transport="http",
                duration_ms=1,
                session_id="S-failopen",
                project="/tmp/p",
            )


if __name__ == "__main__":
    unittest.main()
