"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

class _HandlerAuth:
    """Per-request handler. Wired by :class:`FederationServer`."""

    server_version = "CEOFederation/1.0"
    sys_version = ""  # don't leak Python version

    # AC16 — fail-fast timeout per request.
    timeout = HANDSHAKE_TIMEOUT_SECONDS

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # silent — audit-log is the canonical record

    # AC15 mechanical method allowlist. PLAN-112-FOLLOWUP W1: POST is
    # admitted ONLY when write-mode is active (Layer 0a env AND Layer 0b
    # sentinel). When write-mode is OFF, the module constant
    # ALLOWED_HTTP_METHODS = ("GET",) is the effective set and POST → 405.
    def parse_request(self) -> bool:
        ok = http.server.BaseHTTPRequestHandler.parse_request(self)
        if not ok:
            return ok
        method = (self.command or "").upper()
        if method in ALLOWED_HTTP_METHODS:
            return True
        # Non-GET. POST is conditionally allowed when write-mode active.
        if method == "POST" and self._write_mode_active():
            return True
        self._emit_write_blocked()
        self._send_405()
        return False

    # -- Write-mode activation gates (PLAN-112-FOLLOWUP W1) -------------

    def _write_mode_active(self) -> bool:
        """Layer 0a AND Layer 0b — write-mode is reachable.

        Default-OFF (AC1/AC7): BOTH the env switch (Layer 0a) AND the
        write-enable sentinel (Layer 0b / Gate #8) must pass. Either OFF
        → False → POST stays 405. Fail-CLOSED on any error.
        """
        try:
            if not write_mode_enabled_from_env():
                return False
            return self._write_enable_sentinel_valid()
        except Exception:
            return False

    def _emit_write_blocked(self) -> None:
        # AC15 — every non-allowed method-allowlist violation emits.
        peer_fpr = self._lookup_peer_fpr()
        correlation = self.headers.get(CORRELATION_ID_HEADER, "") or ""
        _safe_emit(
            "federation_write_attempt_blocked",
            method=str(self.command)[:16] if self.command else "",
            path=str(self.path)[:128] if self.path else "",
            peer_id_cert_fingerprint=peer_fpr,
            client_ip=self._client_ip(),
            fed_correlation_id=correlation[:64],
        )

    def _send_405(self) -> None:
        self.send_response(405)
        # Advertise POST only when write-mode is active.
        allow = "GET, POST" if self._write_mode_active() else "GET"
        self.send_header("Allow", allow)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        body = b'{"error":"method_not_allowed"}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 — base-class convention
        # PLAN-112-FOLLOWUP W1/W2 — when write-mode is OFF, behave exactly
        # as before (emit blocked + 405). When ON, run the 11-gate
        # dispatcher.
        if not self._write_mode_active():
            self._emit_write_blocked()
            self._send_405()
            return
        self._dispatch_write(method="POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._emit_write_blocked()
        self._send_405()

    def do_PATCH(self) -> None:  # noqa: N802
        self._emit_write_blocked()
        self._send_405()

    def do_DELETE(self) -> None:  # noqa: N802
        self._emit_write_blocked()
        self._send_405()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._emit_write_blocked()
        self._send_405()

    def do_HEAD(self) -> None:  # noqa: N802
        self._emit_write_blocked()
        self._send_405()

    # -- Common helpers --------------------------------------------------

    def _client_ip(self) -> str:
        try:
            return self.client_address[0] if self.client_address else ""
        except (AttributeError, IndexError):
            return ""

    def _ip_prefix(self) -> str:
        """Return a /24 (v4) or /48 (v6) prefix of the client IP.

        Used as the rate-limit discriminator (LLM06/GDPR — never log the
        full client IP). Best-effort; empty on any error.
        """
        ip = self._client_ip()
        if not ip:
            return ""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return ""
        try:
            if addr.version == 4:
                net = ipaddress.ip_network(ip + "/24", strict=False)
            else:
                net = ipaddress.ip_network(ip + "/48", strict=False)
            return str(net.network_address)
        except ValueError:
            return ""

    def _lookup_peer_fpr(self) -> str:
        try:
            der = self.connection.getpeercert(True)  # type: ignore[union-attr]
        except (AttributeError, ssl.SSLError):
            return ""
        if not der:
            return ""
        return hashlib.sha256(der).hexdigest()

    def _presented_cert_pem_bytes(self) -> bytes:
        try:
            der = self.connection.getpeercert(True)  # type: ignore[union-attr]
        except (AttributeError, ssl.SSLError):
            return b""
        if not der:
            return b""
        try:
            return ssl.DER_cert_to_PEM_cert(der).encode("ascii")
        except (TypeError, ValueError, UnicodeEncodeError):
            return b""

    def _lookup_peer_record(self) -> Optional[PeerRecord]:
        # PLAN-112-FOLLOWUP W3/R-IT-B: refresh the peer list before SPKI
        # match so a revocation propagates at the connection-accept layer
        # too (not only Gate #7).
        try:
            _maybe_reload_peers(self.server)
        except Exception:
            pass  # reload is best-effort; fail-open on infra only
        peers = getattr(self.server, "federation_peers", {})
        peers_extra = getattr(self.server, "federation_peers_extra", {}) or {}
        if not peers:
            return None

        presented_der_fpr = self._lookup_peer_fpr()
        if not presented_der_fpr:
            return None

        presented_pem = self._presented_cert_pem_bytes()
        presented_spki_fpr = ""
        spki_compute_attempted = False
        spki_compute_error: Optional[str] = None

        for peer in peers.values():
            if peer.revoked:
                continue
            extra = peers_extra.get(peer.peer_id, {}) if peers_extra else {}
            spki_from_record = peer.peer_id_spki_fingerprint
            spki_from_extra = extra.get("peer_id_spki_fingerprint", "") if isinstance(extra, dict) else ""
            effective_spki = spki_from_record or spki_from_extra or ""
            peer_row = {
                "peer_id": peer.peer_id,
                "peer_id_spki_fingerprint": effective_spki,
                "peer_id_cert_fingerprint": peer.peer_id_cert_fingerprint,
            }
            try:
                pin_type, pin_value = select_pin_for_peer(peer_row)
            except PinSelectionError:
                self._emit_peer_invalid_no_fingerprint(peer.peer_id)
                continue

            if pin_type == "spki":
                if not spki_compute_attempted:
                    spki_compute_attempted = True
                    if presented_pem:
                        try:
                            presented_spki_fpr = compute_spki_fingerprint(
                                presented_pem
                            )
                        except (ImportError, ValueError, TypeError) as exc:
                            spki_compute_error = (
                                "{0}:{1}".format(
                                    type(exc).__name__, str(exc)[:64]
                                )
                            )
                            presented_spki_fpr = ""
                if not presented_spki_fpr:
                    self._emit_spki_fingerprint_mismatch(
                        peer.peer_id,
                        reason="presented_spki_compute_failed:{0}".format(
                            spki_compute_error or "no_pem"
                        ),
                    )
                    continue
                if compare_fingerprints(presented_spki_fpr, pin_value):
                    return peer
                self._emit_spki_fingerprint_mismatch(
                    peer.peer_id, reason="spki_mismatch"
                )
                continue

            if compare_fingerprints(presented_der_fpr, pin_value):
                self._emit_pin_legacy_used(peer.peer_id)
                return peer
            continue

        return None

    def _resolve_peer(self) -> Optional[PeerRecord]:
        """Public alias for :meth:`_lookup_peer_record` (Wave D contract)."""
        return self._lookup_peer_record()

    # Wave C audit emit wrappers.
    def _emit_spki_fingerprint_mismatch(
        self, peer_id: str, reason: str = "spki_mismatch",
    ) -> None:
        presented_fpr = self._lookup_peer_fpr() or ""
        _safe_emit(
            "federation_spki_fingerprint_mismatch",
            peer_id=peer_id[:64],
            expected_prefix="",
            presented_prefix=presented_fpr[:16],
            route=str(self.path or "")[:64],
        )

    def _emit_pin_legacy_used(self, peer_id: str) -> None:
        der_fpr = self._lookup_peer_fpr() or ""
        _safe_emit(
            "federation_pin_legacy_used",
            peer_id=peer_id[:64],
            route=str(self.path or "")[:64],
            der_fingerprint_prefix=der_fpr[:16],
        )

    def _emit_peer_invalid_no_fingerprint(self, peer_id: str) -> None:
        source_path = str(getattr(
            getattr(self, "server", None),
            "federation_peers_path",
            ".claude/data/federation/peers.yaml",
        ))
        _safe_emit(
            "federation_peer_invalid_no_fingerprint",
            peer_id=peer_id[:64],
            source_path=source_path[:128],
        )

    def _emit_connection_rejected(self, reason: str) -> None:
        _safe_emit(
            "federation_connection_rejected",
            peer_id_cert_fingerprint=self._lookup_peer_fpr(),
            client_ip=self._client_ip(),
            reason=reason[:64],
        )

    def _emit_connection_accepted(self, peer_id: str) -> None:
        correlation = self.headers.get(CORRELATION_ID_HEADER, "") or ""
        _safe_emit(
            "federation_connection_accepted",
            peer_id=peer_id[:64],
            client_ip=self._client_ip(),
            fed_correlation_id=correlation[:64],
        )

    # -- Replay + signature verification (AC13) -------------------------

    def _replay_freshness_preflight(
        self, peer: PeerRecord,
    ) -> Optional[str]:
        """R-SE-a Gate #3a — NON-mutating timestamp-window preflight.

        Runs BEFORE the body read. Returns None if fresh, else a reason.
        Does NOT touch the nonce ring (no state mutation) so an unauth /
        replayed peer cannot poison the ring before HMAC verification.
        """
        nonce = self.headers.get("X-CEO-Federation-Nonce", "")
        ts = self.headers.get("X-CEO-Federation-Timestamp", "")
        sig = self.headers.get("X-CEO-Federation-Signature", "")
        if not (nonce and ts and sig):
            return "missing_replay_headers"
        try:
            parsed = parse_rfc3339_utc(ts)
        except ValueError:
            return "malformed_timestamp"
        skew = abs(parsed.timestamp() - time.time())
        if skew > MAX_CLOCK_SKEW_SECONDS:
            return "clock_skew"
        return None

    def _verify_signature_only(
        self, peer: PeerRecord, body: bytes,
    ) -> Optional[str]:
        """R-SE-a Gate #3c — HMAC signature verify (needs body). No mutation."""
        nonce = self.headers.get("X-CEO-Federation-Nonce", "")
        ts = self.headers.get("X-CEO-Federation-Timestamp", "")
        sig = self.headers.get("X-CEO-Federation-Signature", "")
        try:
            from .replay import verify_signature  # type: ignore[import]
        except ImportError:
            from replay import verify_signature  # type: ignore[no-redef]
        ok = verify_signature(
            self.command or "", self.path or "", ts, nonce, body,
            peer.hmac_secret_hex, sig,
        )
        return None if ok else "signature_invalid"

    def _commit_nonce(self, peer: PeerRecord) -> Optional[str]:
        """R-SE-a Gate #3d — MUTATING nonce commit. Runs ONLY after HMAC."""
        replay = getattr(self.server, "federation_replay_cache", None)
        if replay is None:
            return "replay_cache_missing"
        nonce = self.headers.get("X-CEO-Federation-Nonce", "")
        ts = self.headers.get("X-CEO-Federation-Timestamp", "")
        decision: ReplayDecision = replay.check_and_record(peer.peer_id, nonce, ts)
        return None if decision.accepted else decision.reason

    def _verify_replay_and_signature(
        self, peer: PeerRecord, body: bytes,
    ) -> Optional[str]:
        """Legacy combined check (read path, GET). Kept for do_GET."""
        replay = getattr(self.server, "federation_replay_cache", None)
        if replay is None:
            return "replay_cache_missing"
        nonce = self.headers.get("X-CEO-Federation-Nonce", "")
        ts = self.headers.get("X-CEO-Federation-Timestamp", "")
        sig = self.headers.get("X-CEO-Federation-Signature", "")
        if not (nonce and ts and sig):
            return "missing_replay_headers"
        decision: ReplayDecision = replay.check_and_record(peer.peer_id, nonce, ts)
        if not decision.accepted:
            return decision.reason
        try:
            from .replay import verify_signature  # type: ignore[import]
        except ImportError:
            from replay import verify_signature  # type: ignore[no-redef]
        ok = verify_signature(
            self.command or "", self.path or "", ts, nonce, body,
            peer.hmac_secret_hex, sig,
        )
        if not ok:
            return "signature_invalid"
        return None

    # ===================================================================
    # Wave D 11-gate write dispatcher (PLAN-112-FOLLOWUP W2/W3/W4/W6b)
    # ===================================================================

