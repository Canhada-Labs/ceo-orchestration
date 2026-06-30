"""PLAN-099 Wave A.2 — stdlib federation client (mTLS + signed requests).

Counterpart to :mod:`federation.server`. The client speaks the same
HMAC+nonce+timestamp wire envelope (AC13) and propagates a
correlation-id for cross-node audit stitching (Wave C).

Stdlib-only: :mod:`http.client` + :mod:`ssl` + :mod:`hashlib` +
:mod:`json`. No ``requests`` / ``httpx`` / third-party HTTP libs.

The client is INTENTIONALLY restricted to GET — there is no ``post()``
/ ``put()`` API surface. Write-mode is PLAN-099-FOLLOWUP scope.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import http.client
import json
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from .audit_chain import (
        CORRELATION_ID_HEADER,
        FEDERATION_CORRELATION_ID_KEY,
        generate_correlation_id,
        tag_remote_event,
    )
    from .replay import generate_nonce, sign_request
    from .identity import (
        compute_cert_fingerprint,
        # Wave C (PLAN-099-FOLLOWUP) — SPKI dispatcher primitives.
        compute_spki_fingerprint,
        compute_der_fingerprint_from_pem,
        compare_fingerprints,
    )
    from . import HANDSHAKE_TIMEOUT_SECONDS
except ImportError:
    from audit_chain import (  # type: ignore[no-redef]
        CORRELATION_ID_HEADER,
        FEDERATION_CORRELATION_ID_KEY,
        generate_correlation_id,
        tag_remote_event,
    )
    from replay import generate_nonce, sign_request  # type: ignore[no-redef]
    from identity import (  # type: ignore[no-redef]
        compute_cert_fingerprint,
        # Wave C (PLAN-099-FOLLOWUP) — SPKI dispatcher primitives.
        compute_spki_fingerprint,
        compute_der_fingerprint_from_pem,
        compare_fingerprints,
    )
    HANDSHAKE_TIMEOUT_SECONDS = 5.0


__all__ = [
    "FederationClient",
    "FederationClientConfig",
    "FederationClientError",
    "FederationResponse",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FederationClientError(RuntimeError):
    """Raised on any HTTP / TLS / verification failure during a request."""


# ---------------------------------------------------------------------------
# Config + response shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FederationClientConfig:
    """One peer endpoint + the credentials needed to call it.

    Fields
    ------
    peer_id
        Used for audit-chain tagging (local emits associate the response
        with this peer).
    host
        DNS/IP of the remote node.
    port
        TCP port.
    client_cert
        PEM cert presented for mTLS.
    client_key
        PEM private key.
    ca_file
        Bundle of server-CA certs we trust.
    server_cert_fingerprint
        Expected DER ``peer_id_cert_fingerprint`` of the remote (legacy
        v1.x pin). Compared post-handshake when SPKI pin is empty.
        Pin-mismatch → :class:`FederationClientError`.
    hmac_secret_hex
        Per-peer shared secret used to sign requests.
    server_spki_fingerprint
        Wave C (PLAN-099-FOLLOWUP) — expected SPKI SHA-256 fingerprint
        of the remote (v2.0 primary pin). When non-empty, SPKI MUST
        match — DER is NOT consulted (no downgrade). When empty,
        client falls back to ``server_cert_fingerprint`` (DER) pin.
        Default ``""`` preserves PLAN-099 v1.32.0 caller compat.
    """

    peer_id: str
    host: str
    port: int
    client_cert: Path
    client_key: Path
    ca_file: Path
    server_cert_fingerprint: str
    hmac_secret_hex: str
    # Wave C (PLAN-099-FOLLOWUP) — SPKI primary pin (default-empty for
    # legacy-caller compat; new callers SHOULD populate this).
    server_spki_fingerprint: str = ""


@dataclass
class FederationResponse:
    status: int
    body: Dict[str, Any]
    correlation_id: str = ""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FederationClient:
    """Stdlib mTLS client for read-only federation endpoints.

    Usage
    -----

        cfg = FederationClientConfig(peer_id="peer-east-01", ...)
        client = FederationClient(cfg)
        ident = client.get_identity()
        status = client.get_status()
        summary = client.get_audit_summary(since="2026-05-17T00:00:00Z")
    """

    def __init__(self, config: FederationClientConfig) -> None:
        self.config = config

    # -- SSLContext (mTLS, TLSv1.3 min) ---------------------------------

    def _build_ctx(self) -> ssl.SSLContext:
        cfg = self.config
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = True
        ctx.load_verify_locations(cafile=str(cfg.ca_file))
        ctx.load_cert_chain(
            certfile=str(cfg.client_cert),
            keyfile=str(cfg.client_key),
        )
        return ctx

    # -- Generic GET ----------------------------------------------------

    def _get(self, path: str) -> FederationResponse:
        cfg = self.config
        ctx = self._build_ctx()
        timestamp = _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        nonce = generate_nonce()
        body = b""
        signature = sign_request(
            "GET", path, timestamp, nonce, body, cfg.hmac_secret_hex,
        )
        correlation_id = generate_correlation_id()

        conn = http.client.HTTPSConnection(
            cfg.host,
            cfg.port,
            context=ctx,
            timeout=HANDSHAKE_TIMEOUT_SECONDS,
        )
        try:
            conn.connect()
            # Post-handshake: verify presented server cert matches the
            # pinned fingerprint. stdlib `getpeercert(True)` returns DER.
            sock = conn.sock
            der: Optional[bytes] = None
            if sock is not None and hasattr(sock, "getpeercert"):
                try:
                    der = sock.getpeercert(True)  # type: ignore[union-attr]
                except (ssl.SSLError, OSError):
                    der = None
            if not der:
                raise FederationClientError("no peer cert presented")
            presented_der_fp = hashlib.sha256(der).hexdigest()

            # Wave C (PLAN-099-FOLLOWUP) SPKI dispatcher START
            #
            # Per peers-yaml-schema-migration.md §3 client-side mirror:
            # mirror the server's dispatcher chain so a malicious peer
            # cannot present a DER-matching cert when we have an SPKI
            # pin configured (defends against DOWNGRADE on client side
            # too — symmetric to server.py §3).
            #
            # Wave C gate #1: mTLS handshake (existing — conn.connect()).
            # Wave C gate #2: SPKI fingerprint match (NEW — this wave).
            # Wave D (PLAN-099-FOLLOWUP) gate #3+: HMAC + scope + ...
            spki_pin = (cfg.server_spki_fingerprint or "").strip()
            der_pin = (cfg.server_cert_fingerprint or "").strip()

            if spki_pin:
                # SPKI primary pin configured — DER NOT consulted regardless
                # of how it compares (no downgrade).
                try:
                    pem_bytes = ssl.DER_cert_to_PEM_cert(der).encode("ascii")
                except (TypeError, ValueError, UnicodeEncodeError) as exc:
                    raise FederationClientError(
                        "client SPKI pin: cannot re-encode presented DER "
                        "as PEM ({0})".format(type(exc).__name__)
                    )
                try:
                    presented_spki_fp = compute_spki_fingerprint(pem_bytes)
                except (ImportError, ValueError, TypeError) as exc:
                    # Could not compute SPKI of presented cert — fail-CLOSED
                    # (do NOT downgrade to DER comparison).
                    raise FederationClientError(
                        "client SPKI pin: compute_spki_fingerprint failed "
                        "({0}: {1}); refusing to downgrade to DER".format(
                            type(exc).__name__, str(exc)[:64],
                        )
                    )
                if not compare_fingerprints(presented_spki_fp, spki_pin):
                    raise FederationClientError(
                        "server SPKI pin mismatch: expected {0!s:.16}.., "
                        "got {1!s:.16}.. (downgrade blocked: DER pin NOT "
                        "consulted when SPKI declared)".format(
                            spki_pin, presented_spki_fp,
                        )
                    )
                # SPKI match — gate #2 PASS.
            elif der_pin:
                # Legacy v1.x DER fallback (no SPKI pin configured).
                if not compare_fingerprints(presented_der_fp, der_pin):
                    raise FederationClientError(
                        "server fingerprint pin mismatch: expected "
                        "{0!s:.16}.., got {1!s:.16}..".format(
                            der_pin, presented_der_fp,
                        )
                    )
            else:
                # Neither pin configured — fail-CLOSED.
                raise FederationClientError(
                    "client config has neither server_spki_fingerprint nor "
                    "server_cert_fingerprint; refusing to connect"
                )
            # Wave C SPKI dispatcher END

            headers = {
                "X-CEO-Federation-Nonce": nonce,
                "X-CEO-Federation-Timestamp": timestamp,
                "X-CEO-Federation-Signature": signature,
                CORRELATION_ID_HEADER: correlation_id,
                "Accept": "application/json",
                "User-Agent": "CEOFederationClient/1.0",
                "Connection": "close",
            }
            conn.request("GET", path, body=None, headers=headers)
            resp = conn.getresponse()
            raw = resp.read()
            try:
                parsed = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(parsed, dict):
                    parsed = {"_raw": parsed}
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed = {"_raw_bytes_len": len(raw)}
            return FederationResponse(
                status=resp.status,
                body=parsed,
                correlation_id=correlation_id,
            )
        finally:
            try:
                conn.close()
            except OSError:
                pass

    # -- Public surface (3 RO endpoints) --------------------------------

    def get_identity(self) -> FederationResponse:
        return self._get("/federation/identity")

    def get_status(self) -> FederationResponse:
        return self._get("/federation/status")

    def get_audit_summary(
        self, since: Optional[str] = None,
    ) -> FederationResponse:
        path = "/federation/audit-summary"
        if since:
            from urllib.parse import quote
            path += "?since={0}".format(quote(since, safe=""))
        resp = self._get(path)
        # Wave C — tag every remote event with our peer's federation_origin
        # before the caller forwards to the local emit pipeline.
        events = resp.body.get("events") if isinstance(resp.body, dict) else None
        if isinstance(events, list):
            tagged = [
                tag_remote_event(
                    ev,
                    federation_origin=self.config.server_cert_fingerprint,
                    correlation_id=resp.correlation_id,
                )
                for ev in events
                if isinstance(ev, dict)
            ]
            resp.body["events"] = tagged
        return resp
