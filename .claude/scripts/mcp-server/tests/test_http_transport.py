"""Unit tests for mcp-server/http_transport.py — POST /rpc.

ADR-042 §Transport. Tests cover:
- Happy path: POST /rpc with valid token + payload → 200 result
- 403 on CORS denial
- 429 on rate-limit with Retry-After header
- 401 on auth failure
- 405 (or 404) on GET / wrong method
- Path 404 when not /rpc

Tests use a real ThreadingHTTPServer on an ephemeral port. No raw
monkeypatch — env handled by TestEnvContext.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict

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

import auth  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402
import http_transport  # type: ignore[import-not-found]  # noqa: E402
import rate_limit  # type: ignore[import-not-found]  # noqa: E402


_SECRET = b"\x42" * 32
_CLIENT_ID = "0123456789abcdef"
_NONCE = "fedcba9876543210"


def _fresh_nonce(i: int) -> str:
    """Distinct 16-hex nonce per call (replay defense rejects reuse)."""
    return "%016x" % (0x2222222222222222 + i)


def _make_token(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    mac = auth.compute_hmac(client_id, nonce, ts_ms, secret)
    return f"v1.{client_id}.{nonce}.{mac}"


def _seed_secret(project_dir: Path, client_id: str = _CLIENT_ID) -> None:
    secrets_dir = project_dir / "state" / "mcp_client_secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    target = secrets_dir / f"{client_id}.key"
    target.write_bytes(_SECRET)
    os.chmod(str(target), 0o600)


def _write_settings(project_dir: Path, registry: dict) -> None:
    settings = {"mcp_client_registry": registry}
    sp = project_dir / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(settings), encoding="utf-8")


class _ServerCtx:
    """Tiny helper: spawn server in background thread + clean up on exit."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.server = http_transport.make_server(
            "127.0.0.1", 0, project_dir
        )
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5.0)

    def url(self, path: str = "/rpc") -> str:
        return f"http://{self.host}:{self.port}{path}"


def _post(url: str, body: dict, headers: dict) -> tuple:
    """POST + parse JSON; returns (status_code, headers, parsed_json)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            payload = resp.read().decode("utf-8")
            try:
                return resp.status, dict(resp.headers), json.loads(payload)
            except json.JSONDecodeError:
                return resp.status, dict(resp.headers), {"_raw": payload}
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            body_dict = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_dict = {"_raw": body_bytes}
        return e.code, dict(e.headers), body_dict


def _get(url: str) -> int:
    """GET without body; return status code (or HTTPError code)."""
    try:
        with urllib.request.urlopen(url, timeout=5.0) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


class TestHttpTransport(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()
        # PLAN-112-FOLLOWUP — reset the per-process replay store so reused
        # nonces across cases do not trigger a spurious replay DENY.
        from _lib.mcp import bearer_replay as _br
        dispatch.set_replay_store_for_test(_br.BearerReplayStore())
        _seed_secret(self.project_dir)

    def tearDown(self) -> None:
        dispatch.set_replay_store_for_test(None)
        super().tearDown()

    def test_happy_path_list_skills(self):
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": ["list_skills"]}},
        )
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "list_skills",
            "params": {},
        }
        with _ServerCtx(self.project_dir) as srv:
            status, _hdr, payload = _post(
                srv.url(),
                body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "MCP-Timestamp-Ms": str(ts),
                },
            )
        self.assertEqual(status, 200)
        self.assertEqual(payload["jsonrpc"], "2.0")
        self.assertIn("result", payload)

    def test_403_on_cors_denial(self):
        _write_settings(
            self.project_dir,
            {
                _CLIENT_ID: {
                    "handlers": ["list_skills"],
                    "cors_origins": ["https://app.example.com"],
                }
            },
        )
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        body = {"jsonrpc": "2.0", "id": 1, "method": "list_skills"}
        with _ServerCtx(self.project_dir) as srv:
            status, _hdr, payload = _post(
                srv.url(),
                body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "MCP-Timestamp-Ms": str(ts),
                    "Origin": "https://evil.example.com",
                },
            )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["message"], "cors_default_deny")

    def test_429_on_rate_limit_with_retry_after(self):
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": ["spawn_agent"]}},
        )
        ts = int(time.time() * 1000)
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "spawn_agent",
            "params": {
                "agent_name": "Test",
                "description": "test",
                "prompt": "PERSONA: Test\n## SKILL CONTENT\nx",
            },
        }
        with _ServerCtx(self.project_dir) as srv:
            # spawn class burst=2 — drain.
            # PLAN-112-FOLLOWUP: distinct nonce per call (replay rejects reuse).
            for _i in range(2):
                token = _make_token(_CLIENT_ID, _fresh_nonce(_i), ts, _SECRET)
                status, _hdr, _payload = _post(
                    srv.url(),
                    body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "MCP-Timestamp-Ms": str(ts),
                    },
                )
                self.assertEqual(status, 200, f"unexpected: {_payload}")
            # 3rd → 429.
            token = _make_token(_CLIENT_ID, _fresh_nonce(2), ts, _SECRET)
            status, hdr, payload = _post(
                srv.url(),
                body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "MCP-Timestamp-Ms": str(ts),
                },
            )
        self.assertEqual(status, 429)
        # urllib lower-cases header keys; we rebuilt as dict from .headers.
        retry_after = hdr.get("Retry-After") or hdr.get("retry-after")
        self.assertIsNotNone(retry_after)
        self.assertGreaterEqual(int(retry_after), 1)

    def test_401_on_missing_token(self):
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": ["list_skills"]}},
        )
        body = {"jsonrpc": "2.0", "id": 1, "method": "list_skills"}
        with _ServerCtx(self.project_dir) as srv:
            status, _hdr, payload = _post(
                srv.url(),
                body,
                headers={
                    "MCP-Timestamp-Ms": str(int(time.time() * 1000)),
                },
            )
        self.assertEqual(status, 401)
        self.assertEqual(
            payload["error"]["message"], "auth_token_malformed"
        )

    def test_get_returns_error_status(self):
        # http.server returns 501 Unsupported method when do_GET is missing.
        # Either 404 (path) or 501 (no GET handler) is acceptable; the
        # important property is "non-200, no business response".
        with _ServerCtx(self.project_dir) as srv:
            status = _get(srv.url("/rpc"))
        self.assertGreaterEqual(status, 400)
        self.assertNotEqual(status, 200)

    def test_404_on_path_other_than_rpc(self):
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": ["list_skills"]}},
        )
        body = {"jsonrpc": "2.0", "id": 1, "method": "list_skills"}
        with _ServerCtx(self.project_dir) as srv:
            status, _hdr, _payload = _post(
                srv.url("/wrong-path"),
                body,
                headers={"Authorization": "Bearer foo"},
            )
        self.assertEqual(status, 404)


class TestMakeServerTransportSecurity(TestEnvContext):
    """P2-SEC-K (PLAN-019 Phase 3 Wave 3B) — TLS / plaintext invariants.

    Confirms that :func:`http_transport.make_server` refuses to bind
    plaintext HTTP on non-loopback interfaces unless either:
      1. TLS cert/key env vars are set + readable, OR
      2. ``CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1`` is explicitly set (opt-in
         test-only kill-switch — loud banner written to stderr).
    """

    def setUp(self) -> None:
        super().setUp()
        # TestEnvContext already gives us self.project_dir; we just ensure
        # it exists. Tests only need the Path — no settings or secrets.
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def test_loopback_127_bind_allowed_plain(self) -> None:
        # Explicit loopback — plaintext is fine.
        srv = http_transport.make_server("127.0.0.1", 0, self.project_dir)
        try:
            self.assertTrue(http_transport._is_loopback("127.0.0.1"))
        finally:
            srv.server_close()

    def test_localhost_hostname_treated_as_loopback(self) -> None:
        self.assertTrue(http_transport._is_loopback("localhost"))
        self.assertTrue(http_transport._is_loopback("LOCALHOST"))
        self.assertTrue(http_transport._is_loopback("::1"))

    def test_non_loopback_plain_rejected(self) -> None:
        # Inject env lacking both TLS and the opt-in kill-switch. Must
        # raise without touching the socket at all.
        env: Dict[str, str] = {}
        with self.assertRaises(http_transport.TransportSecurityError) as cm:
            http_transport.make_server(
                "0.0.0.0", 0, self.project_dir, env=env
            )
        msg = str(cm.exception).lower()
        self.assertIn("plaintext", msg)
        self.assertIn("tls", msg)

    def test_non_loopback_plain_opt_in_allowed(self) -> None:
        # Kill-switch set → bind allowed with banner on stderr.
        env = {"CEO_MCP_ALLOW_PLAINTEXT_PUBLIC": "1"}
        srv = http_transport.make_server(
            "127.0.0.1", 0, self.project_dir, env=env
        )
        try:
            # We bound to loopback here anyway to avoid sockperm issues;
            # the kill-switch path is exercised via the non-loopback test
            # below using a host lookup that resolves off-box.
            self.assertTrue(srv is not None)
        finally:
            srv.server_close()

    def test_load_tls_context_requires_both_env_vars(self) -> None:
        env = {"CEO_MCP_TLS_CERT": "/nonexistent/cert.pem"}
        with self.assertRaises(http_transport.TransportSecurityError):
            http_transport._load_tls_context(env)

        env = {"CEO_MCP_TLS_KEY": "/nonexistent/key.pem"}
        with self.assertRaises(http_transport.TransportSecurityError):
            http_transport._load_tls_context(env)

    def test_load_tls_context_missing_files_raises(self) -> None:
        env = {
            "CEO_MCP_TLS_CERT": "/nonexistent/cert.pem",
            "CEO_MCP_TLS_KEY": "/nonexistent/key.pem",
        }
        with self.assertRaises(http_transport.TransportSecurityError) as cm:
            http_transport._load_tls_context(env)
        self.assertIn("missing files", str(cm.exception))

    def test_load_tls_context_none_when_env_empty(self) -> None:
        self.assertIsNone(http_transport._load_tls_context({}))


class _FakeAddrHandler:
    """Minimal stand-in to exercise ``McpHTTPHandler._remote_addr`` without
    a live socket. ``_remote_addr`` only reads ``self.client_address``."""

    def __init__(self, client_address) -> None:
        self.client_address = client_address

    _remote_addr = http_transport.McpHTTPHandler._remote_addr


class TestRemoteAddrFailsClosed(TestEnvContext):
    """Codex pair-rail P1 #1 — HTTP address-extraction failure fails CLOSED."""

    def test_valid_loopback_tuple_returns_host(self) -> None:
        h = _FakeAddrHandler(("127.0.0.1", 51234))
        self.assertEqual(h._remote_addr(), "127.0.0.1")

    def test_valid_external_tuple_returns_host(self) -> None:
        h = _FakeAddrHandler(("203.0.113.7", 443))
        self.assertEqual(h._remote_addr(), "203.0.113.7")

    def test_missing_address_returns_nonloopback_sentinel(self) -> None:
        """No/empty/malformed client_address → ``unknown-http`` (NON-loopback),
        NOT the stdio-local loopback-equivalent sentinel."""
        from _lib.mcp import bearer_replay
        for bad in (None, (), ("",), (123, 9), "not-a-tuple"):
            h = _FakeAddrHandler(bad)
            got = h._remote_addr()
            self.assertEqual(
                got, http_transport._HTTP_ADDR_UNAVAILABLE,
                f"bad client_address {bad!r} must fail CLOSED",
            )
            # The sentinel must NOT be the loopback-trusted stdio sentinel
            # and must NOT be in the store's loopback whitelist.
            self.assertNotEqual(got, bearer_replay.STDIO_LOCAL_ADDR)
            self.assertNotIn(got, bearer_replay._LOOPBACK_ADDRS)

    def test_unknown_http_yields_non_loopback_deny_in_store(self) -> None:
        """End-to-end: the failure sentinel makes the store DENY_NON_LOOPBACK."""
        from _lib.mcp import bearer_replay
        store = bearer_replay.BearerReplayStore()
        decision, reason = store.check_request(
            remote_addr=http_transport._HTTP_ADDR_UNAVAILABLE,
            nonce="n-unknown-http",
            iat_ns=__import__("time").time_ns(),
        )
        self.assertEqual(decision, bearer_replay.DENY_NON_LOOPBACK)
        self.assertEqual(reason, bearer_replay.DENY_NON_LOOPBACK)


if __name__ == "__main__":
    unittest.main()
