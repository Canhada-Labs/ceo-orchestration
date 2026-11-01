"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

class FederationServer:
    """Top-level orchestrator for the federation server."""

    def __init__(
        self,
        config: FederationConfig,
        audit_fetch: Optional[Callable[[Optional[str]], List[Dict[str, Any]]]] = None,
        now: Optional[_dt.datetime] = None,
    ) -> None:
        self.config = config
        self._audit_fetch = audit_fetch
        self._now = now or _dt.datetime.now(_dt.timezone.utc)
        self._httpd: Optional[http.server.HTTPServer] = None
        self._reload_thread: Optional[threading.Thread] = None
        self._reload_stop = threading.Event()

    # -- Pre-start invariants ------------------------------------------

    def _check_kill_switch(self) -> None:
        v = os.environ.get(FEDERATION_KILL_SWITCH_ENV, "0").strip()
        if v not in ("1", "true", "TRUE"):
            raise FederationStartError(
                "kill-switch {0} not set; refusing to start".format(
                    FEDERATION_KILL_SWITCH_ENV
                )
            )

    def _check_enable_sentinel(self) -> None:
        cfg = self.config
        ok, reason = verify_enable_sentinel_pair(
            cfg.enabled_sentinel,
            cfg.enabled_sentinel_asc,
            [OWNER_GPG_FPR],
            signer_registry_path=cfg.signer_registry_path,
            now=self._now,
        )
        if not ok:
            _safe_emit(
                "federation_enable_sentinel_invalid",
                sentinel_kind="enable",
                reason=reason[:96],
            )
            raise FederationStartError(
                "enable sentinel invalid: {0}".format(reason)
            )

    def _check_lan_sentinel_if_required(self) -> None:
        cfg = self.config
        is_loopback, resolved = resolve_bind_is_loopback(cfg.bind_host)
        if is_loopback:
            return
        ok, reason = verify_enable_sentinel_pair(
            cfg.lan_enabled_sentinel,
            cfg.lan_enabled_sentinel_asc,
            [OWNER_GPG_FPR],
            signer_registry_path=cfg.signer_registry_path,
            now=self._now,
        )
        if not ok:
            _safe_emit(
                "federation_lan_bind_denied",
                bind_host=cfg.bind_host[:64],
                resolved_ip=resolved[:64],
                reason=reason[:96],
            )
            raise FederationStartError(
                "LAN bind denied: {0}".format(reason)
            )

    def _load_peers_or_raise(self) -> Dict[str, PeerRecord]:
        try:
            peers = load_peers(self.config.peers_path)
        except FileNotFoundError:
            _safe_emit(
                "federation_connection_rejected",
                reason="peers_yaml_missing",
                peer_id_cert_fingerprint="",
                client_ip="",
            )
            raise FederationStartError(
                "peers.yaml missing at {0}".format(self.config.peers_path)
            )
        except PeerHasNoFingerprintError as e:
            _safe_emit(
                "federation_peer_invalid_no_fingerprint",
                peer_id=(getattr(e, "peer_id", "") or "")[:64],
                source_path=str(self.config.peers_path)[:128],
            )
            raise FederationStartError(
                "peers.yaml no-fingerprint invariant: {0}".format(e)
            )
        except PeersFileError as e:
            _safe_emit(
                "federation_connection_rejected",
                reason="peers_yaml_parse_error",
                peer_id_cert_fingerprint="",
                client_ip="",
            )
            raise FederationStartError(
                "peers.yaml parse error: {0}".format(e)
            )

        now = self._now
        for peer in peers.values():
            days_left = (peer.not_valid_after - now).days
            if days_left <= CERT_EXPIRY_WARN_DAYS:
                _safe_emit(
                    "federation_cert_expiry_warned",
                    peer_id=peer.peer_id[:64],
                    days_remaining=int(days_left),
                )
            if days_left < 0:
                _safe_emit(
                    "federation_cert_revoked",
                    peer_id=peer.peer_id[:64],
                    reason="expired",
                )
        return peers

    # -- Lifecycle -----------------------------------------------------

    def _start_reload_thread(self, httpd: Any) -> None:
        """P0-1 — start a low-frequency poll thread so revocation
        propagates in <60s even with zero traffic."""
        def _poll() -> None:
            while not self._reload_stop.is_set():
                # Poll every 5s; debounce inside _maybe_reload_peers means
                # an unchanged file is a cheap stat+hash, not a re-parse.
                self._reload_stop.wait(5.0)
                if self._reload_stop.is_set():
                    break
                try:
                    _maybe_reload_peers(httpd)
                except Exception:
                    pass
                try:
                    _reap_orphaned_inflight(
                        getattr(httpd, "federation_sentinels_dir", None)
                    )
                except Exception:
                    pass
        t = threading.Thread(
            target=_poll, name="federation-peer-reload", daemon=True,
        )
        self._reload_thread = t
        t.start()

    def serve_forever(self) -> None:
        """Start the server and serve until ``shutdown()`` is called."""
        self._check_kill_switch()
        self._check_enable_sentinel()
        self._check_lan_sentinel_if_required()
        peers = self._load_peers_or_raise()
        cfg = self.config

        ctx = build_ssl_context(cfg.cert_file, cfg.key_file, cfg.ca_file)

        try:
            with open(cfg.cert_file, "r", encoding="utf-8") as fh:
                pem = fh.read()
            server_fpr = compute_cert_fingerprint(pem)
        except OSError:
            server_fpr = ""

        bind_family = socket.AF_INET
        try:
            if ipaddress.ip_address(cfg.bind_host).version == 6:
                bind_family = socket.AF_INET6
        except ValueError:
            pass

        httpd = _ThreadingHTTPSServer(
            (cfg.bind_host, cfg.bind_port),
            _FederationHandler,
            address_family=bind_family,
        )
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

        httpd.federation_config = cfg  # type: ignore[attr-defined]
        httpd.federation_peers = peers  # type: ignore[attr-defined]
        httpd.federation_peers_path = cfg.peers_path  # type: ignore[attr-defined]
        httpd.federation_peers_extra = {  # type: ignore[attr-defined]
            peer.peer_id: {
                "peer_id_spki_fingerprint": peer.peer_id_spki_fingerprint,
                "peer_id_cert_fingerprint": peer.peer_id_cert_fingerprint,
                "scopes": list(getattr(peer, "scopes", []) or []),
                "audit_event_push_allowlist": list(
                    getattr(peer, "audit_event_push_allowlist", []) or []
                ),
                "revoked": bool(peer.revoked),
            }
            for peer in peers.values()
        }
        httpd.federation_replay_cache = ReplayCache(  # type: ignore[attr-defined]
            max_skew_seconds=MAX_CLOCK_SKEW_SECONDS,
        )
        httpd.federation_rate_limiter = JointKeyRateLimiter(  # type: ignore[attr-defined]
            AUDIT_SUMMARY_RATE_PER_MIN,
        )
        httpd.federation_started_at = time.time()  # type: ignore[attr-defined]
        httpd.federation_server_fingerprint = server_fpr  # type: ignore[attr-defined]
        httpd.federation_status_digest = ""  # type: ignore[attr-defined]
        httpd.federation_status_count = 0  # type: ignore[attr-defined]
        httpd.federation_audit_fetch = self._audit_fetch  # type: ignore[attr-defined]
        # PLAN-112-FOLLOWUP W1/W2/W3 — write-mode + reload-watcher state.
        httpd.write_enabled_sentinel = cfg.write_enabled_sentinel  # type: ignore[attr-defined]
        httpd.write_enabled_sentinel_asc = cfg.write_enabled_sentinel_asc  # type: ignore[attr-defined]
        httpd.federation_sentinels_dir = cfg.federation_sentinels_dir  # type: ignore[attr-defined]
        httpd.signer_registry_path = cfg.signer_registry_path  # type: ignore[attr-defined]
        httpd.owner_fpr = OWNER_GPG_FPR  # type: ignore[attr-defined]
        # PLAN-112-FOLLOWUP P0 #1 — ONE canonical audit-log path shared by
        # the audit-event handlers (gate #11) AND the T1565 tamper walk.
        # If cfg.audit_log_path is None we resolve the SAME path the
        # handlers use so the check inspects the log just appended (never a
        # no-op). When an explicit env CEO_AUDIT_LOG_PATH is set the handler
        # honours it; we mirror it here for the tamper walk.
        _resolved_audit_log: Optional[Path] = (
            Path(cfg.audit_log_path) if cfg.audit_log_path is not None
            else None
        )
        if _resolved_audit_log is None:
            try:
                try:
                    from .handlers import audit_event_push as _aep  # type: ignore
                except ImportError:
                    import importlib
                    _aep = importlib.import_module(
                        "_lib.federation.handlers.audit_event_push"
                    )
                _r = getattr(_aep, "_resolve_audit_log_path", None)
                if _r is not None:
                    _resolved_audit_log = Path(_r())
            except Exception:
                _resolved_audit_log = None
        httpd.federation_audit_log_path = _resolved_audit_log  # type: ignore[attr-defined]
        httpd.federation_reload_lock = threading.Lock()  # type: ignore[attr-defined]
        httpd.federation_peers_last_check = time.time()  # type: ignore[attr-defined]
        httpd.federation_peers_signature = _peers_file_signature(  # type: ignore[attr-defined]
            Path(cfg.peers_path)
        )

        self._httpd = httpd
        self._start_reload_thread(httpd)
        try:
            httpd.serve_forever()
        finally:
            self._reload_stop.set()
            try:
                httpd.server_close()
            except OSError:
                pass

    def shutdown(self) -> None:
        self._reload_stop.set()
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
            except (OSError, RuntimeError):
                pass
