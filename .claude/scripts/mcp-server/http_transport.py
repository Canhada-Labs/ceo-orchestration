"""HTTP transport for the MCP server (ADR-042 §Transport).

Hand-rolled JSON-RPC 2.0 over ``http.server.BaseHTTPRequestHandler``
per A.0 spike verdict (stdlib UPHELD). Thread model:
``ThreadingHTTPServer`` — one thread per request. Handlers are pure
dispatch; rate-limit buckets are thread-safe.

Path routing: POST ``/rpc`` only — all other paths return 404.
Maximum request body 1 MiB (slow-loris protection).

Auth flow:
- ``Authorization: Bearer <token>`` header.
- ``MCP-Timestamp-Ms`` header (integer milliseconds since epoch).
- ``MCP-Session-Id`` header (UUID recommended; server generates if absent).
- ``Origin`` header (optional; CORS default-deny).

Response headers include ``Cache-Control: no-store``,
``X-Content-Type-Options: nosniff``, and ``Retry-After`` on 429.

## P2-SEC-K transport-security invariants (PLAN-019 Phase 3 Wave 3B)

``make_server()`` enforces one of the following at construction time:

1. **Loopback bind** (``127.0.0.1`` / ``::1`` / ``localhost``) — TLS
   optional because no packets leave the host.
2. **Non-loopback bind** — requires either
   (a) a TLS cert/key via ``CEO_MCP_TLS_CERT`` + ``CEO_MCP_TLS_KEY``
       (wrapped via ``ssl.SSLContext``), OR
   (b) explicit ``CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1`` kill-switch for
       local testing — logged with a loud stderr banner.

Rationale: HMAC tokens are bearer-equivalent on the wire. Without TLS,
any on-path attacker can replay the ``Authorization: Bearer ...``
header within the ±60s skew window. The prior behaviour accepted
plaintext HTTP on any bind address once ``CEO_MCP_ALLOW_PUBLIC=1`` was
set; that was a lie-by-omission vs. what docs/threat-model.md claimed.

## PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — remote_addr threading

The replay store (``dispatch.authenticate``) needs the network remote
address for its loopback gate. ``BaseHTTPRequestHandler.client_address``
is a ``(host, port)`` tuple; this transport passes ``client_address[0]``
(the host) into ``authenticate(remote_addr=...)``. Loopback HTTP binds
report ``127.0.0.1`` / ``::1`` (whitelisted in the store).
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

_SERVER_DIR = Path(__file__).resolve().parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

import auth  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402


_REQUEST_BODY_CAP = 1 * 1024 * 1024  # 1 MiB

# Codex pair-rail P1 #1 — HTTP address-extraction failure MUST fail CLOSED.
# When ``client_address`` is unavailable/malformed for an HTTP request we
# return this NON-loopback sentinel so the replay store's loopback gate
# returns ``DENY_NON_LOOPBACK`` instead of trusting it as loopback. It is
# DELIBERATELY not in ``bearer_replay._LOOPBACK_ADDRS`` (the stdio-local
# sentinel is for the stdio transport ONLY — an HTTP request has a real
# socket, so a missing address there is an anomaly, never trusted).
_HTTP_ADDR_UNAVAILABLE = "unknown-http"


class McpHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for POST ``/rpc``.

    Deliberately tiny — the work is in :mod:`dispatch`. The only
    transport-specific logic here is:

    - Path routing (``/rpc`` only).
    - Header extraction (``Authorization``, ``MCP-Timestamp-Ms``,
      ``MCP-Session-Id``, ``Origin``).
    - Remote-address extraction for the replay-store loopback gate.
    - Status-code mapping for deny reasons.
    - Response header set (``Content-Type``, cache, CORS-safe defaults,
      ``Retry-After`` on rate-limit denial).
    """

    server_version = "MCP/1.0.0-rc.1"

    def log_message(self, format, *args) -> None:  # noqa: D401 (http.server shape)
        # Silence default access log — audit_emit is our observability.
        return

    def _remote_addr(self) -> str:
        """Return the client host for the replay-store loopback gate.

        ``self.client_address`` is a ``(host, port)`` tuple set by
        ``socketserver``. Codex pair-rail P1 #1: if it is unavailable or
        malformed we fail CLOSED — we return the NON-loopback sentinel
        ``_HTTP_ADDR_UNAVAILABLE`` ("unknown-http") so the store returns
        ``DENY_NON_LOOPBACK`` rather than treating an HTTP
        address-extraction failure as trusted loopback. A real HTTP
        request always has a socket address; a missing one is an anomaly,
        never a loopback equivalence.
        """
        try:
            addr = self.client_address
            if isinstance(addr, (tuple, list)) and addr:
                host = addr[0]
                if isinstance(host, str) and host:
                    return host
        except Exception:
            pass
        return _HTTP_ADDR_UNAVAILABLE

    def _send(
        self,
        status: int,
        payload: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: D401 (http.server shape)
        try:
            self._handle_post()
        except Exception:
            # Defense-in-depth — dispatch layer already catches.
            try:
                self._send(
                    500,
                    dispatch.rpc_error(None, dispatch.ERR_INTERNAL, "internal_error"),
                )
            except Exception:
                pass

    def _handle_post(self) -> None:
        if self.path != "/rpc":
            self._send(
                int(HTTPStatus.NOT_FOUND),
                dispatch.rpc_error(None, dispatch.ERR_METHOD_NOT_FOUND, "Not Found"),
            )
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0 or content_length > _REQUEST_BODY_CAP:
            self._send(
                400,
                dispatch.rpc_error(None, dispatch.ERR_INVALID_REQUEST, "Invalid Request"),
            )
            return

        try:
            body_bytes = self.rfile.read(content_length)
            body_text = body_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            self._send(
                400,
                dispatch.rpc_error(None, dispatch.ERR_PARSE, "Parse error"),
            )
            return

        envelope, err_resp = dispatch.parse_envelope(body_text)
        if err_resp is not None:
            self._send(400, err_resp)
            return
        assert envelope is not None

        raw_token = auth.parse_bearer(self.headers.get("Authorization"))
        timestamp_ms = self.headers.get("MCP-Timestamp-Ms") or ""
        origin = self.headers.get("Origin")
        session_id = self.headers.get("MCP-Session-Id") or str(uuid.uuid4())
        project_dir = self.server.mcp_project_dir  # type: ignore[attr-defined]
        project = str(project_dir)

        ctx, deny_reason, retry_ms = dispatch.authenticate(
            raw_token=raw_token,
            timestamp_ms=timestamp_ms,
            method=envelope["method"],
            origin=origin,
            transport="http",
            session_id=session_id,
            project_dir=project_dir,
            remote_addr=self._remote_addr(),
        )

        if deny_reason is not None:
            client_id_for_audit = ""
            if raw_token:
                parsed = auth.parse_token(raw_token)
                if parsed is not None:
                    client_id_for_audit = parsed["client_id"]
            dispatch.emit_deny(
                handler=envelope["method"],
                client_id=client_id_for_audit,
                transport="http",
                reason=deny_reason,
                session_id=session_id,
                project=project,
            )
            headers: Optional[Dict[str, str]] = None
            if deny_reason == "rate_limit":
                status = 429
                headers = {"Retry-After": str(max(1, (retry_ms + 999) // 1000))}
            elif deny_reason in ("acl_missing_handler", "cors_default_deny"):
                status = 403
            else:
                status = 401
            code = dispatch.DENY_CODE_MAP.get(deny_reason, dispatch.ERR_APP_AUTH)
            self._send(
                status,
                dispatch.rpc_error(envelope.get("id"), code, deny_reason),
                extra_headers=headers,
            )
            return

        assert ctx is not None
        response = dispatch.dispatch(envelope, ctx, project)
        status_ok = 200 if "result" in response else 400
        self._send(status_ok, response)


_LOOPBACK_HOSTS = frozenset({
    "127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1",
})


class TransportSecurityError(RuntimeError):
    """Raised by :func:`make_server` when TLS invariants are violated.

    P2-SEC-K (PLAN-019 Phase 3 Wave 3B). The server MUST NOT start when:

    - Bind host is non-loopback, AND
    - No TLS cert/key is configured, AND
    - The ``CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1`` kill-switch is not set.

    The error message explains the three remediation paths (bind
    loopback / provide TLS / opt-in plaintext).
    """


def _is_loopback(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in _LOOPBACK_HOSTS


def _load_tls_context(env: Optional[Dict[str, str]] = None) -> Optional[ssl.SSLContext]:
    """Return an ``ssl.SSLContext`` when TLS is configured via env, else None.

    Reads ``CEO_MCP_TLS_CERT`` and ``CEO_MCP_TLS_KEY`` — both must be
    present and point at readable files. On any load failure we raise
    :class:`TransportSecurityError` (fail-closed, do not silently fall
    back to plaintext).
    """
    src = env if env is not None else os.environ
    cert = (src.get("CEO_MCP_TLS_CERT") or "").strip()
    key = (src.get("CEO_MCP_TLS_KEY") or "").strip()
    if not cert and not key:
        return None
    if not cert or not key:
        raise TransportSecurityError(
            "CEO_MCP_TLS_CERT and CEO_MCP_TLS_KEY must BOTH be set "
            "(got one without the other)."
        )
    if not Path(cert).is_file() or not Path(key).is_file():
        raise TransportSecurityError(
            f"CEO_MCP_TLS_CERT / CEO_MCP_TLS_KEY point at missing files: "
            f"cert={cert!r} key={key!r}"
        )
    ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    # Disable client-auth; we verify clients via HMAC bearer, not mTLS.
    ctx.verify_mode = ssl.CERT_NONE
    # Require TLS 1.2+ (SPEC/threat-model.md invariant).
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ctx.load_cert_chain(certfile=cert, keyfile=key)
    except (ssl.SSLError, OSError) as e:
        raise TransportSecurityError(
            f"TLS cert/key load failed: {type(e).__name__}: {e}"
        )
    return ctx


def make_server(
    host: str,
    port: int,
    project_dir: Path,
    *,
    env: Optional[Dict[str, str]] = None,
) -> ThreadingHTTPServer:
    """Construct a ThreadingHTTPServer wired to the MCP handler.

    Stashes ``project_dir`` on the server instance so the request
    handler (which is constructed per request) can reach it via
    ``self.server.mcp_project_dir``.

    P2-SEC-K enforcement (PLAN-019 Phase 3 Wave 3B):

    * Loopback (127.0.0.1 / ::1 / localhost) → plaintext OK.
    * Non-loopback + TLS cert/key configured → wrap socket in TLS.
    * Non-loopback + no TLS + ``CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1`` →
      start plaintext with a loud stderr banner (opt-in testing only).
    * Non-loopback + no TLS + no kill-switch → :class:`TransportSecurityError`.

    ``env`` kwarg lets tests inject deterministic values without
    mutating ``os.environ``. Production callers omit it.
    """
    src = env if env is not None else os.environ
    tls_ctx = _load_tls_context(src)

    if not _is_loopback(host) and tls_ctx is None:
        allow_plain = (src.get("CEO_MCP_ALLOW_PLAINTEXT_PUBLIC") or "").strip() == "1"
        if not allow_plain:
            raise TransportSecurityError(
                f"refusing to bind HTTP (plaintext) on non-loopback host "
                f"{host!r}. Options:\n"
                "  1. Bind loopback: CEO_MCP_HOST=127.0.0.1 (default).\n"
                "  2. Configure TLS: CEO_MCP_TLS_CERT=<path> + CEO_MCP_TLS_KEY=<path>.\n"
                "  3. Opt-in plaintext (testing only): "
                "CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1\n"
                "See P2-SEC-K / docs/threat-model.md for rationale."
            )
        sys.stderr.write(
            "\n"
            "=" * 72 + "\n"
            "[mcp-server] WARNING (P2-SEC-K): plaintext HTTP on non-loopback\n"
            f"             host={host!r} port={port}\n"
            "             Authorization: Bearer tokens will travel in plaintext.\n"
            "             Any on-path attacker can replay them within ±60s.\n"
            "             This mode is opt-in via CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1\n"
            "             for LOCAL TESTING only.  Do NOT use in production.\n"
            + "=" * 72 + "\n\n"
        )

    server = ThreadingHTTPServer((host, port), McpHTTPHandler)
    server.mcp_project_dir = project_dir  # type: ignore[attr-defined]

    if tls_ctx is not None:
        server.socket = tls_ctx.wrap_socket(server.socket, server_side=True)
        sys.stderr.write(
            f"[mcp-server] TLS enabled (TLSv1.2+) on {host}:{port}\n"
        )

    return server


__all__ = [
    "McpHTTPHandler",
    "make_server",
    "TransportSecurityError",
    "_is_loopback",
    "_load_tls_context",
    "_HTTP_ADDR_UNAVAILABLE",
]
