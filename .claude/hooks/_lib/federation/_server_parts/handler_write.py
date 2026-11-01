"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

class _HandlerWrite:
    def _dispatch_write(self, method: str) -> None:
        """ADR-135-AMEND-1 §2.2 11-gate chain for write endpoints."""
        if _fed_scopes is None:
            # Partial install — scopes module absent. Fail-CLOSED.
            self._emit_write_blocked()
            self._send_405()
            return

        raw_path = self.path or ""
        path = raw_path.split("?", 1)[0].split("#", 1)[0]

        # Gate #2 — resolve peer (also refreshes peer list per R-IT-B).
        peer = self._resolve_peer()
        if peer is None:
            self._emit_connection_rejected("peer_unresolved")
            self._send_status(401, "unauthorized")
            return

        peers_extra = getattr(self.server, "federation_peers_extra", {}) or {}
        extra = peers_extra.get(peer.peer_id, {}) if peers_extra else {}
        peer_row = {
            "peer_id": peer.peer_id,
            "peer_id_spki_fingerprint": extra.get(
                "peer_id_spki_fingerprint", ""
            ),
            "peer_id_cert_fingerprint": peer.peer_id_cert_fingerprint,
            "scopes": list(extra.get("scopes", [])),
            "audit_event_push_allowlist": list(
                extra.get("audit_event_push_allowlist", [])
            ),
            "revoked": bool(extra.get("revoked", peer.revoked)),
        }

        # GATE #3a — non-mutating timestamp-window preflight (R-SE-a).
        pf_reason = self._replay_freshness_preflight(peer)
        if pf_reason is not None:
            _safe_emit(
                "federation_connection_replay_suspected",
                peer_id=peer.peer_id[:64],
                reason=pf_reason[:64],
                client_ip=self._client_ip(),
            )
            self._send_status(401, "hmac_or_replay")
            return

        # GATE #3b — body read (capped).
        body = self._read_body_capped(max_bytes=1024 * 1024)
        if body is None:
            self._send_status(413, "payload_too_large")
            return

        # GATE #3c — HMAC signature verify (needs body, no mutation).
        sig_reason = self._verify_signature_only(peer, body)
        if sig_reason is not None:
            _safe_emit(
                "federation_connection_replay_suspected",
                peer_id=peer.peer_id[:64],
                reason=sig_reason[:64],
                client_ip=self._client_ip(),
            )
            self._send_status(401, "hmac_or_replay")
            return

        # GATE #3d — MUTATING nonce commit (ONLY after HMAC passes).
        nonce_reason = self._commit_nonce(peer)
        if nonce_reason is not None:
            _safe_emit(
                "federation_connection_replay_suspected",
                peer_id=peer.peer_id[:64],
                reason=nonce_reason[:64],
                client_ip=self._client_ip(),
            )
            self._send_status(401, "hmac_or_replay")
            return

        # GATE #4 — method + path → scope.
        required_scope = _fed_scopes.route_required_scope(method, path)
        if required_scope is None:
            self._emit_write_blocked()
            self._send_405()
            return

        # GATE #5 — X-CEO-Federation-Scope header presence + match.
        if not _fed_scopes.validate_scope_header(self.headers, required_scope):
            self._emit_scope_denied(peer.peer_id, path, required_scope, peer_row)
            self._send_status(400, "scope_header")
            return

        # GATE #6 — peer's scopes list grants the required scope.
        if not _fed_scopes.peer_has_scope(peer_row, required_scope):
            self._emit_write_endpoint_denied(
                peer.peer_id, path, gate_failed=6, reason_code="write_unauthorized",
            )
            self._send_status(403, "scope")
            return

        # GATE #7 — peer not revoked (reloaded list per P0-1).
        if peer_row.get("revoked") is True:
            self._emit_write_endpoint_denied(
                peer.peer_id, path, gate_failed=7, reason_code="peer_revoked",
            )
            self._send_status(403, "revoked")
            return

        # GATE #8 — write-enable sentinel valid (also enforced at 0a).
        if not self._write_enable_sentinel_valid():
            self._emit_write_disabled_sentinel_invalid("gpg_verify_failed")
            self._send_status(503, "write_disabled")
            return

        # GATE #9 — rate-limit (REAL — Wave E; default-DENY on exception).
        ok, rl_reason = self._rate_limit_check(method, path, self.headers, peer_row)
        if not ok:
            self._emit_write_endpoint_denied(
                peer.peer_id, path, gate_failed=9,
                reason_code=(rl_reason or "rate_limited")[:32],
            )
            self._send_status(429, "rate_limited")
            return

        # GATE #10a — CLAIM + VERIFY (destructive routes; BEFORE handler).
        cosign_inflight_paths = None
        if _fed_scopes.is_destructive_route(method, path):
            ok, reason, cosign_inflight_paths = self._verify_owner_cosign_claim(
                method, path,
            )
            if not ok:
                self._emit_write_endpoint_denied(
                    peer.peer_id, path, gate_failed=10,
                    reason_code="destructive_unauthz:{0}".format(reason[:12]),
                )
                self._send_status(403, "owner_cosign")
                return

        # GATE #11 — handler executes.
        # PLAN-112-FOLLOWUP P0 #1 + P1 #2 (Codex BLOCK): pass the
        # SERVER-CONFIGURED state paths route-specifically so a non-default
        # config mutates the RIGHT trust-root file (peers.yaml) and the
        # tamper check inspects the SAME audit-log the handler appends to.
        # Without this the handlers fall back to PEERS_FILE_DEFAULT /
        # their own audit-log resolution and the revocation-propagation +
        # T1565 claims become false.
        handler = self._route_handler(method, path)
        if handler is None:
            self._send_405()
            return
        handler_kwargs = self._handler_state_kwargs(path)
        try:
            status, reason, response_body = handler.handle(
                peer_row, self.headers, body, **handler_kwargs
            )
        except Exception as exc:
            sys.stderr.write(
                "[federation.dispatch] handler crashed: {0}: {1}\n".format(
                    type(exc).__name__, str(exc)[:200]
                )
            )
            self._send_status(500, "handler_crash")
            return

        # GATE #10b — CONSUME (AFTER handler success only).
        if cosign_inflight_paths is not None and status < 400:
            self._consume_owner_cosign_sentinel(cosign_inflight_paths)

        # POST-handler T1565 — audit-chain tamper detection (W4). We walk
        # the SAME canonical audit-log the push handler just appended to
        # (handler_kwargs["audit_log_path"]) so the check is guaranteed to
        # inspect the freshly-written record — F-7.10 critical detection
        # must be REACHABLE, not merely plumbed.
        if status < 400 and path in (
            "/federation/audit-event", "/federation/audit-event/batch",
        ):
            self._maybe_check_audit_chain(
                peer.peer_id, path, handler_kwargs.get("audit_log_path"),
            )

        self._send_response_bytes(status, response_body)

    def _resolve_audit_log_path(self) -> Optional[Path]:
        """Return the ONE canonical audit-log path (P0 #1).

        Precedence: server-config ``audit_log_path`` → the audit handler's
        own resolver (``CEO_AUDIT_LOG_PATH`` / platform default), so the
        write handlers + the T1565 tamper check ALWAYS agree on the path.
        """
        cfg = getattr(self.server, "federation_config", None)
        path = getattr(self.server, "federation_audit_log_path", None)
        if path is None and cfg is not None:
            path = getattr(cfg, "audit_log_path", None)
        if path is not None:
            return Path(path)
        # Mirror the handler's resolver so both sides land on the same file.
        try:
            try:
                from .handlers import audit_event_push as _aep  # type: ignore
            except ImportError:
                import importlib
                _aep = importlib.import_module(
                    "_lib.federation.handlers.audit_event_push"
                )
            resolver = getattr(_aep, "_resolve_audit_log_path", None)
            if resolver is not None:
                return Path(resolver())
        except Exception:
            pass
        return None

    def _handler_state_kwargs(self, path: str) -> Dict[str, Any]:
        """Route-specific server-state kwargs for the gate-#11 handler.

        P1 #2: peer_register/peer_revoke get the configured ``peers_path``
        (NOT PEERS_FILE_DEFAULT). P0 #1: audit-event push/batch get the ONE
        canonical ``audit_log_path``. Only paths that the target handler's
        ``handle(...)`` accepts are passed (kwargs are route-matched).
        """
        cfg = getattr(self.server, "federation_config", None)
        if path in ("/federation/peer-register", "/federation/peer-revoke"):
            peers_path = getattr(self.server, "federation_peers_path", None)
            if peers_path is None and cfg is not None:
                peers_path = getattr(cfg, "peers_path", None)
            if peers_path is not None:
                return {"peers_path": Path(peers_path)}
            return {}
        if path in (
            "/federation/audit-event", "/federation/audit-event/batch",
        ):
            log_path = self._resolve_audit_log_path()
            if log_path is not None:
                return {"audit_log_path": log_path}
            return {}
        return {}

    def _route_handler(self, method: str, path: str):
        """Map (method, path) → handler module."""
        key = (method.upper(), path)
        if key == ("POST", "/federation/peer-register"):
            return _h_peer_register
        if key == ("POST", "/federation/audit-event"):
            return _h_audit_event_push
        if key == ("POST", "/federation/audit-event/batch"):
            return _h_audit_event_batch
        if key == ("POST", "/federation/peer-revoke"):
            return _h_peer_revoke
        return None

    # -- Gate #8 — write-enable sentinel verify ------------------------

    def _write_enable_sentinel_valid(self) -> bool:
        """Gate #8 / Layer 0b — verify the write-enable sentinel pair.

        Fail-CLOSED on any error. No caching (ADR-121 §6 v1.x no-cache).
        """
        cfg = getattr(self.server, "federation_config", None)
        signed_path = getattr(self.server, "write_enabled_sentinel", None)
        if signed_path is None and cfg is not None:
            signed_path = getattr(cfg, "write_enabled_sentinel", None)
        if signed_path is None:
            signed_path = Path(".claude/data/federation/write-enabled.md")
        signed_path = Path(signed_path)

        sig_path = getattr(self.server, "write_enabled_sentinel_asc", None)
        if sig_path is None and cfg is not None:
            sig_path = getattr(cfg, "write_enabled_sentinel_asc", None)
        if sig_path is None:
            sig_path = Path(str(signed_path) + ".asc")
        sig_path = Path(sig_path)

        if not signed_path.exists() or not sig_path.exists():
            return False

        try:
            owner_fpr = getattr(self.server, "owner_fpr", OWNER_GPG_FPR)
            registry_path = getattr(self.server, "signer_registry_path", None)
            if registry_path is None and cfg is not None:
                registry_path = getattr(cfg, "signer_registry_path", None)
            ok, _reason = verify_enable_sentinel_pair(
                signed_path,
                sig_path,
                [owner_fpr],
                signer_registry_path=registry_path,
            )
        except Exception:
            return False
        return bool(ok)

    # -- Gate #10 — Owner co-sign claim / consume (split TOCTOU) --------

    def _verify_owner_cosign_claim(
        self, method: str, path: str,
    ) -> Tuple[bool, str, Optional[Tuple[Path, Path, Path, Path, str]]]:
        """Gate #10a — CLAIM + VERIFY per-request Owner-co-sign sentinel."""
        sigref = ""
        for k, v in self.headers.items():
            if isinstance(k, str) and k.lower() == "x-ceo-owner-sigref":
                sigref = str(v) if isinstance(v, str) else ""
                break
        if not sigref:
            return False, "missing_header:x_ceo_owner_sigref", None
        if not re.match(r"^[A-Za-z0-9_-]{1,64}$", sigref):
            return False, "sigref_charset", None

        cfg = getattr(self.server, "federation_config", None)
        base = getattr(self.server, "federation_sentinels_dir", None)
        if base is None and cfg is not None:
            base = getattr(cfg, "federation_sentinels_dir", None)
        if base is None:
            base = Path(".claude/data/federation/sentinels")
        base_dir = Path(base) / sigref
        md_path = base_dir / "approval.md"
        asc_path = base_dir / "approval.md.asc"

        if not md_path.exists() or not asc_path.exists():
            return False, "sentinel_not_found", None

        md_inflight = md_path.with_suffix(md_path.suffix + ".inflight")
        try:
            os.rename(str(md_path), str(md_inflight))
        except OSError:
            return False, "sentinel_inflight_collision", None

        asc_inflight = asc_path.with_suffix(asc_path.suffix + ".inflight")
        try:
            os.rename(str(asc_path), str(asc_inflight))
        except OSError:
            try:
                os.rename(str(md_inflight), str(md_path))
            except OSError:
                pass
            return False, "sentinel_asc_claim_failed", None

        # PLAN-112-FOLLOWUP P2 #4 (Codex BLOCK): every failure path AFTER
        # both files are renamed to .inflight (verify failure, read failure,
        # missing signed_at, TTL expiry, unexpected exception) must REVERT
        # the .inflight pair to its original names — best-effort — so the
        # sentinel is NOT left stuck. The sentinel was NOT consumed (verify
        # failed), so reverting is correct: it restores the recoverable
        # pre-claim state. The 5-min reaper (REMAINING) is the backstop for
        # the residual crash-between-rename window only.
        def _revert_inflight() -> None:
            try:
                if md_inflight.exists() and not md_path.exists():
                    os.rename(str(md_inflight), str(md_path))
            except OSError:
                pass
            try:
                if asc_inflight.exists() and not asc_path.exists():
                    os.rename(str(asc_inflight), str(asc_path))
            except OSError:
                pass

        try:
            owner_fpr = getattr(self.server, "owner_fpr", OWNER_GPG_FPR)
            registry_path = getattr(self.server, "signer_registry_path", None)
            if registry_path is None and cfg is not None:
                registry_path = getattr(cfg, "signer_registry_path", None)
            ok, reason = verify_enable_sentinel_pair(
                md_inflight, asc_inflight, [owner_fpr],
                signer_registry_path=registry_path,
            )
            if not ok:
                _revert_inflight()
                return False, "verify_failed:{0}".format(reason[:64]), None
            try:
                md_text = md_inflight.read_text(encoding="utf-8")
            except OSError as exc:
                _revert_inflight()
                return False, "read_md_failed:{0}".format(
                    exc.errno or "unknown",
                ), None
            signed_at = self._parse_signed_at(md_text)
            if signed_at is None:
                _revert_inflight()
                return False, "missing_signed_at", None
            age_seconds = time.time() - signed_at
            if age_seconds > 24 * 3600:
                _revert_inflight()
                return False, "ttl_expired:{0:.0f}s".format(age_seconds), None
        except Exception as exc:
            _revert_inflight()
            return False, "verify_call_failed:{0}".format(
                type(exc).__name__,
            ), None

        return True, "verified", (
            md_path, asc_path, md_inflight, asc_inflight, sigref,
        )

    def _consume_owner_cosign_sentinel(
        self,
        inflight_paths: Tuple[Path, Path, Path, Path, str],
    ) -> None:
        """Gate #10b — CONSUME the verified .inflight sentinel pair."""
        md_path, asc_path, md_inflight, asc_inflight, sigref = inflight_paths
        consumed_md = md_path.with_suffix(
            md_path.suffix + ".consumed-{0}".format(sigref)
        )
        consumed_asc = asc_path.with_suffix(
            asc_path.suffix + ".consumed-{0}".format(sigref)
        )
        try:
            os.rename(str(md_inflight), str(consumed_md))
        except OSError:
            return
        try:
            os.rename(str(asc_inflight), str(consumed_asc))
        except OSError:
            pass

    def _parse_signed_at(self, md_text: str) -> Optional[float]:
        """Parse a ``signed_at: <iso-8601>`` line from cleartext .md."""
        for line in md_text.splitlines():
            line = line.strip()
            if not line.startswith("signed_at:"):
                continue
            ts_raw = line.split(":", 1)[1].strip().strip('"').strip("'")
            if ts_raw.endswith("Z"):
                ts_raw = ts_raw[:-1] + "+00:00"
            try:
                dt = _dt.datetime.fromisoformat(ts_raw)
                return dt.timestamp()
            except (ValueError, TypeError):
                return None
        return None

    # -- Gate #9 — REAL rate-limit (Wave E; PLAN-112-FOLLOWUP W4) -------

