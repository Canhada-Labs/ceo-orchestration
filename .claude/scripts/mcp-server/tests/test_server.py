"""Unit tests for mcp-server/server.py — entry point + kill-switch + bind safety.

ADR-042 §Cost.4 + §Transport. Tests cover:
- CEO_SOTA_DISABLE=1 → exit 0 + mcp_server_disabled_by_kill_switch event
- Transport selection from env (http vs stdio vs unknown→http)
- 0.0.0.0 bind rejected without CEO_MCP_ALLOW_PUBLIC=1
- Startup audit event emitted on stdio path

Stdio variant is tested via run() with empty stdin (clean shutdown);
HTTP server is verified by inspecting host/port resolution rather than
binding (the http_transport tests cover the actual socket).
"""

from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Bootstrap sys.path so mcp-server modules import cleanly.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import server  # type: ignore[import-not-found]  # noqa: E402


class TestKillSwitch(TestEnvContext):

    def test_kill_switch_set_returns_zero_and_emits_event(self):
        with mock.patch.dict(os.environ, {"CEO_SOTA_DISABLE": "1"}):
            # Replace stderr so we don't pollute test output.
            sys.stderr = io.StringIO()
            try:
                rc = server.run(project_dir=self.project_dir)
            finally:
                sys.stderr = sys.__stderr__
        self.assertEqual(rc, 0)
        log = self.read_audit_log()
        self.assertIn("mcp_server_disabled_by_kill_switch", log)

    def test_kill_switch_unset_proceeds_to_transport(self):
        # Unset + use stdio with empty stdin → clean shutdown.
        os.environ.pop("CEO_SOTA_DISABLE", None)
        with mock.patch.dict(os.environ, {"CEO_MCP_TRANSPORT": "stdio"}):
            # Patch stdin to empty stream so the loop exits at EOF.
            original_stdin = sys.stdin
            sys.stdin = io.StringIO("")
            try:
                rc = server.run(project_dir=self.project_dir)
            finally:
                sys.stdin = original_stdin
        self.assertEqual(rc, 0)
        # No kill-switch event; should have a started event.
        log = self.read_audit_log()
        self.assertNotIn("mcp_server_disabled_by_kill_switch", log)
        self.assertIn("mcp_server_started", log)


class TestTransportSelection(TestEnvContext):

    def test_default_transport_is_http(self):
        os.environ.pop("CEO_MCP_TRANSPORT", None)
        self.assertEqual(server._resolve_transport(), "http")

    def test_stdio_explicit(self):
        with mock.patch.dict(os.environ, {"CEO_MCP_TRANSPORT": "stdio"}):
            self.assertEqual(server._resolve_transport(), "stdio")

    def test_unknown_falls_back_to_http(self):
        with mock.patch.dict(os.environ, {"CEO_MCP_TRANSPORT": "websocket"}):
            self.assertEqual(server._resolve_transport(), "http")

    def test_case_insensitive(self):
        with mock.patch.dict(os.environ, {"CEO_MCP_TRANSPORT": "STDIO"}):
            self.assertEqual(server._resolve_transport(), "stdio")


class TestHostPortResolution(TestEnvContext):

    def test_default_host_is_loopback(self):
        os.environ.pop("CEO_MCP_HOST", None)
        os.environ.pop("CEO_MCP_PORT", None)
        host, port = server._resolve_host_port()
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, 9000)

    def test_public_bind_rejected_without_allow(self):
        os.environ.pop("CEO_MCP_ALLOW_PUBLIC", None)
        with mock.patch.dict(os.environ, {"CEO_MCP_HOST": "0.0.0.0"}):
            host, _port = server._resolve_host_port()
            # Falls back to loopback unless CEO_MCP_ALLOW_PUBLIC=1 is set.
            self.assertEqual(host, "127.0.0.1")

    def test_public_bind_allowed_with_explicit_flag(self):
        with mock.patch.dict(
            os.environ, {"CEO_MCP_HOST": "0.0.0.0", "CEO_MCP_ALLOW_PUBLIC": "1"}
        ):
            host, _port = server._resolve_host_port()
            self.assertEqual(host, "0.0.0.0")

    def test_invalid_port_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"CEO_MCP_PORT": "not-a-port"}):
            _host, port = server._resolve_host_port()
            self.assertEqual(port, 9000)

    def test_out_of_range_port_falls_back(self):
        with mock.patch.dict(os.environ, {"CEO_MCP_PORT": "70000"}):
            _host, port = server._resolve_host_port()
            self.assertEqual(port, 9000)
        with mock.patch.dict(os.environ, {"CEO_MCP_PORT": "0"}):
            _host, port = server._resolve_host_port()
            self.assertEqual(port, 9000)


if __name__ == "__main__":
    unittest.main()
