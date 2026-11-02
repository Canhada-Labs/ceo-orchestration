"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

class _HandlerRead:
    def _rate_limit_check(
        self,
        method: str,
        path: str,
        headers,
        peer_row: dict,
    ) -> Tuple[bool, Optional[str]]:
        """Gate #9 — token-bucket + circuit-breaker + backpressure.

        DEFAULT-DENY on any exception (R-SE-b: no gate fails OPEN). Bridges
        the dispatcher seam signature ``(method, path, headers, peer_row)``
        to ``rate_limit.py``'s ``(peer_id, route, ip_prefix, *, now=)``.
        Emits ``federation_message_storm_detected`` (breaker trip) +
        ``federation_audit_log_backpressure`` from inside rate_limit.py via
        the C-4-fixed _safe_emit fallback.
        """
        rl = _load_rate_limit()
        if rl is None:
            # Partial install — no limiter. Fail-CLOSED (deny).
            return False, "rate_limit:module_missing"
        try:
            peer_id = str(peer_row.get("peer_id", ""))
            route = path
            ip_prefix = self._ip_prefix()
            now_fn = getattr(self.server, "federation_clock", None)
            now = now_fn() if callable(now_fn) else None

            # 1. Backpressure (T1499 latency overload).
            ok_bp, _info = rl.check_backpressure(now=now)
            if not ok_bp:
                return False, "audit_log_backpressure"

            # 2. Circuit-breaker — already-tripped / trip-on-this-check.
            ok_cb, cb_reason = rl.check_circuit_breaker(peer_id, route, now=now)
            if not ok_cb:
                return False, (cb_reason or "circuit_breaker")[:32]

            # 3. Token bucket.
            ok_rl, rl_reason = rl.check_rate_limit(
                peer_id, route, ip_prefix, now=now,
            )
            if not ok_rl:
                # Advance breaker window so a sustained storm trips it.
                rl.record_hit(peer_id, route, ip_prefix, now=now)
                return False, (rl_reason or "rate_limit")[:32]
            return True, None
        except Exception as exc:
            sys.stderr.write(
                "[federation.dispatch] rate_limit raised {0}; "
                "DEFAULT-DENY\n".format(type(exc).__name__)
            )
            return False, "rate_limit:exception"

    def _maybe_check_audit_chain(
        self, peer_id: str, path: str,
        audit_log_path: Optional[Path] = None,
    ) -> None:
        """POST-handler T1565 — bounded audit-chain tamper walk (W4).

        P0 #1 (Codex BLOCK): the path is the SAME canonical audit-log the
        push handler just appended to (passed from the dispatcher). We
        fall back to ``_resolve_audit_log_path()`` so the check still runs
        even if the caller didn't thread it through — it must NEVER be a
        no-op just because ``self.server.federation_audit_log_path`` is
        unset (the prior bug).
        """
        ace = _load_audit_chain_ext()
        if ace is None:
            return
        log_path = audit_log_path or self._resolve_audit_log_path()
        if log_path is None:
            return
        try:
            ok, _info = ace.check_chain(Path(log_path), max_events=500)
            # check_chain itself emits federation_tamper_detected on break
            # via its own _safe_emit (also C-4-fixed). Nothing to do here
            # on the happy path.
            _ = ok
        except Exception:
            pass

    # -- Wave D emit shims (canonical F.2 vocabulary) ------------------

    def _emit_scope_denied(
        self,
        peer_id: str,
        route: str,
        required_scope: str,
        peer_row: Mapping[str, Any],
    ) -> None:
        scopes_list = peer_row.get("scopes", []) if peer_row else []
        if not isinstance(scopes_list, (list, tuple)):
            scopes_list = []
        _safe_emit(
            "federation_scope_denied",
            peer_id=peer_id[:64],
            route=route[:64],
            required_scope=required_scope[:32],
            peer_scopes_count=int(len(scopes_list)),
        )

    def _emit_write_endpoint_denied(
        self,
        peer_id: str,
        route: str,
        *,
        gate_failed: int,
        reason_code: str,
    ) -> None:
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=peer_id[:64],
            route=route[:64],
            gate_failed=int(gate_failed),
            reason_code=reason_code[:32],
        )

    def _emit_write_disabled_sentinel_invalid(
        self,
        reason_code: str = "gpg_verify_failed",
    ) -> None:
        sentinel_path = str(getattr(
            self.server,
            "write_enabled_sentinel",
            ".claude/data/federation/write-enabled.md",
        ))
        _safe_emit(
            "federation_write_disabled_sentinel_invalid",
            reason_code=reason_code[:32],
            sentinel_path=sentinel_path[:128],
        )

    # -- Body / response helpers (Wave D) ------------------------------

    def _read_body_capped(self, max_bytes: int) -> Optional[bytes]:
        """Read request body with a hard cap. Returns None on overflow."""
        cl_header = self.headers.get("Content-Length", "")
        try:
            content_length = int(cl_header) if cl_header else 0
        except (TypeError, ValueError):
            return None
        if content_length > max_bytes:
            return None
        if content_length <= 0:
            return b""
        try:
            return self.rfile.read(content_length)
        except (OSError, ValueError):
            return None

    def _send_status(self, status: int, reason: str) -> None:
        body = json.dumps({"error": reason}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_response_bytes(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if body:
            self.wfile.write(body)

    # -- Dispatch (read path) -------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        if self.command not in ALLOWED_HTTP_METHODS:
            self._emit_write_blocked()
            self._send_405()
            return

        peer = self._lookup_peer_record()
        if peer is None:
            self._emit_connection_rejected("peer_unknown_or_revoked")
            self._send_403()
            return

        body = b""
        cl = self.headers.get("Content-Length")
        if cl and cl.isdigit():
            try:
                body = self.rfile.read(min(int(cl), 4096))
            except OSError:
                body = b""

        replay_reason = self._verify_replay_and_signature(peer, body)
        if replay_reason is not None:
            _safe_emit(
                "federation_connection_replay_suspected",
                peer_id=peer.peer_id[:64],
                reason=replay_reason[:64],
                client_ip=self._client_ip(),
            )
            self._send_401(replay_reason)
            return

        self._emit_connection_accepted(peer.peer_id)

        if self.path == "/federation/identity":
            self._handle_identity()
        elif self.path == "/federation/status":
            self._handle_status()
        elif self.path.startswith("/federation/audit-summary"):
            self._handle_audit_summary(peer)
        else:
            self._send_404()

    # -- Endpoints ------------------------------------------------------

    def _handle_identity(self) -> None:
        server_fpr = getattr(self.server, "federation_server_fingerprint", "")
        payload = {"peer_id_cert_fingerprint": server_fpr}
        self._send_json(200, payload)

    def _handle_status(self) -> None:
        peer = self._lookup_peer_record()
        peer_id = peer.peer_id if peer else ""
        started_at = getattr(self.server, "federation_started_at", 0.0)
        uptime_s = max(0, int(time.time() - started_at)) if started_at else 0
        last_events_digest = getattr(self.server, "federation_status_digest", "")
        last_events_count = getattr(self.server, "federation_status_count", 0)
        payload = {
            "peer_id": peer_id,
            "uptime_seconds": uptime_s,
            "last_event_opaque_sha256": last_events_digest,
            "last_event_count": int(last_events_count),
        }
        self._send_json(200, payload)

    def _handle_audit_summary(self, peer: PeerRecord) -> None:
        rl = getattr(self.server, "federation_rate_limiter", None)
        if rl is not None and not rl.allow(
            peer.peer_id_cert_fingerprint, self._client_ip(),
        ):
            self._send_429()
            return

        fetch: Optional[Callable[[Optional[str]], List[Dict[str, Any]]]] = (
            getattr(self.server, "federation_audit_fetch", None)
        )
        since = ""
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            for kv in qs.split("&"):
                if kv.startswith("since="):
                    since = kv.split("=", 1)[1][:64]
                    break

        events: List[Dict[str, Any]] = []
        if fetch is not None:
            try:
                events = fetch(since or None) or []
            except Exception:
                events = []

        events = _apply_redaction_pipeline(events)
        payload = {"events": events, "count": len(events)}
        self._send_json(200, payload)

    # -- Response helpers ------------------------------------------------

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_403(self) -> None:
        body = b'{"error":"forbidden"}'
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_401(self, reason: str) -> None:
        body = json.dumps(
            {"error": "unauthorized", "reason": reason[:64]},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_404(self) -> None:
        body = b'{"error":"not_found"}'
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_429(self) -> None:
        body = b'{"error":"rate_limited"}'
        self.send_response(429)
        self.send_header("Content-Type", "application/json")
        self.send_header("Retry-After", "60")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# AC6 fail-CLOSED contract.
