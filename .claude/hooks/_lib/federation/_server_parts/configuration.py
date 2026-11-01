"""Declarations extracted from federation.server; loaded by the facade."""
from __future__ import annotations

class FederationConfig:
    """Resolved server configuration (immutable after construction).

    Fields
    ------
    bind_host
        Host string (IP literal or hostname). Hostnames are resolved on
        bind to check loopback.
    bind_port
        TCP port (1..65535).
    cert_file
        Server cert (PEM).
    key_file
        Server private key (PEM).
    ca_file
        Bundle of trusted client-CA certs (PEM).
    peers_path
        Path to ``peers.yaml`` (allowlist for client cert fingerprints).
    enabled_sentinel
        Path to ``.claude/data/federation/enabled.md`` (signed cleartext).
    enabled_sentinel_asc
        Path to ``enabled.md.asc`` (detached signature).
    lan_enabled_sentinel
        Path to ``lan-enabled.md`` (LAN-bind additional pair).
    lan_enabled_sentinel_asc
        Path to ``lan-enabled.md.asc``.
    signer_registry_path
        Path to ``.claude/security/sentinel-signers-registry.yaml`` for
        Stage-2 signer expiry / revocation check.
    write_enabled_sentinel
        Path to ``.claude/data/federation/write-enabled.md`` (Layer 0b /
        Gate #8 third sentinel pair — PLAN-112-FOLLOWUP). Optional; when
        None, defaults are resolved at runtime.
    write_enabled_sentinel_asc
        Detached signature for the write-enable pair.
    federation_sentinels_dir
        Directory hosting per-request Owner-co-sign sentinels (Gate #10).
    audit_log_path
        Path to the local ``audit-log.jsonl`` that the audit-event write
        handlers append to AND the post-handler T1565 tamper check
        inspects (PLAN-112-FOLLOWUP P0 #1 — Codex BLOCK). MUST be the SAME
        path for both or the tamper check is a no-op. Optional; when None,
        the handlers' own ``CEO_AUDIT_LOG_PATH``/platform-default resolution
        is used AND the dispatcher resolves the identical path so the
        check inspects the log just appended.
    """

    __slots__ = (
        "bind_host", "bind_port", "cert_file", "key_file", "ca_file",
        "peers_path", "enabled_sentinel", "enabled_sentinel_asc",
        "lan_enabled_sentinel", "lan_enabled_sentinel_asc",
        "signer_registry_path",
        # PLAN-112-FOLLOWUP W1/W2 — write-mode activation surfaces.
        "write_enabled_sentinel", "write_enabled_sentinel_asc",
        "federation_sentinels_dir",
        # PLAN-112-FOLLOWUP P0 #1 — one canonical audit-log path.
        "audit_log_path",
    )

    def __init__(
        self,
        bind_host: str,
        bind_port: int,
        cert_file: Path,
        key_file: Path,
        ca_file: Path,
        peers_path: Path,
        enabled_sentinel: Path,
        enabled_sentinel_asc: Path,
        lan_enabled_sentinel: Path,
        lan_enabled_sentinel_asc: Path,
        signer_registry_path: Optional[Path] = None,
        write_enabled_sentinel: Optional[Path] = None,
        write_enabled_sentinel_asc: Optional[Path] = None,
        federation_sentinels_dir: Optional[Path] = None,
        audit_log_path: Optional[Path] = None,
    ) -> None:
        self.bind_host = bind_host
        self.bind_port = int(bind_port)
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.peers_path = peers_path
        self.enabled_sentinel = enabled_sentinel
        self.enabled_sentinel_asc = enabled_sentinel_asc
        self.lan_enabled_sentinel = lan_enabled_sentinel
        self.lan_enabled_sentinel_asc = lan_enabled_sentinel_asc
        self.signer_registry_path = signer_registry_path
        # Default-resolve write-mode sentinel paths relative to peers_path
        # parent so a single data-dir hosts all three sentinel pairs.
        data_dir = Path(peers_path).parent if peers_path else Path(
            ".claude/data/federation"
        )
        self.write_enabled_sentinel = (
            write_enabled_sentinel
            if write_enabled_sentinel is not None
            else data_dir / "write-enabled.md"
        )
        self.write_enabled_sentinel_asc = (
            write_enabled_sentinel_asc
            if write_enabled_sentinel_asc is not None
            else Path(str(self.write_enabled_sentinel) + ".asc")
        )
        self.federation_sentinels_dir = (
            federation_sentinels_dir
            if federation_sentinels_dir is not None
            else data_dir / "sentinels"
        )
        # PLAN-112-FOLLOWUP P0 #1 — one canonical audit-log path. None →
        # the dispatcher resolves the SAME path the audit handlers use
        # (CEO_AUDIT_LOG_PATH or platform default) at serve_forever time.
        self.audit_log_path = (
            Path(audit_log_path) if audit_log_path is not None else None
        )


# ---------------------------------------------------------------------------
# Bind-loopback resolver (AC3 — covers ALL non-loopback shapes)
# ---------------------------------------------------------------------------


def resolve_bind_is_loopback(bind_host: str) -> Tuple[bool, str]:
    """Return ``(is_loopback, resolved_ip_str)`` for a bind host.

    Resolves hostnames via :func:`socket.gethostbyname_ex` and tests
    EACH resolved address against :func:`ipaddress.ip_address.is_loopback`.
    A host with any non-loopback address counts as non-loopback (the
    server cannot bind to "loopback-only" without an explicit literal).
    """
    raw = (bind_host or "").strip()
    if not raw:
        return False, ""

    # Try literal IP first (covers IPv4 + IPv6 + "::").
    try:
        addr = ipaddress.ip_address(raw)
        # `unspecified` (0.0.0.0 / ::) is intentionally NOT loopback.
        return bool(addr.is_loopback), str(addr)
    except ValueError:
        pass

    # Hostname — resolve and check every A/AAAA.
    try:
        _, _, ips = socket.gethostbyname_ex(raw)
    except (socket.gaierror, OSError):
        return False, ""

    all_loopback = True
    first = ""
    for ip in ips:
        if not first:
            first = ip
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            all_loopback = False
            continue
        if not addr.is_loopback:
            all_loopback = False
    return all_loopback, first


# ---------------------------------------------------------------------------
# IPv6-aware threaded HTTPS server (AC3)
# ---------------------------------------------------------------------------



class JointKeyRateLimiter:
    """Bucket-by-minute joint-key rate limiter (AC17 — read path)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = int(per_minute)
        self._buckets: Dict[Tuple[str, str, int], int] = {}
        self._lock = threading.Lock()

    def allow(
        self,
        peer_fpr: str,
        client_ip: str,
        now_epoch: Optional[float] = None,
    ) -> bool:
        now = now_epoch if now_epoch is not None else time.time()
        bucket = int(now // 60)
        key = (peer_fpr.lower(), client_ip, bucket)
        with self._lock:
            self._prune_locked(bucket)
            current = self._buckets.get(key, 0)
            if current >= self.per_minute:
                return False
            self._buckets[key] = current + 1
            return True

    def _prune_locked(self, current_bucket: int) -> None:
        cutoff = current_bucket - 2
        stale = [k for k in self._buckets if k[2] < cutoff]
        for k in stale:
            del self._buckets[k]


# ---------------------------------------------------------------------------
# Peer-list reload-watcher (PLAN-112-FOLLOWUP W3 — P0-1 revocation <60s)
# ---------------------------------------------------------------------------


def _peers_file_signature(peers_path: Path) -> Tuple[float, int, str]:
    """Return a cheap (mtime, size, sha256-hex) signature of peers.yaml.

    Used by the reload-watcher to decide whether a reload is warranted
    WITHOUT re-parsing on every request. The sha256 is only computed when
    (mtime, size) changed — see :func:`_maybe_reload_peers`.
    """
    try:
        st = peers_path.stat()
    except OSError:
        return (0.0, -1, "")
    try:
        data = peers_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
    except OSError:
        digest = ""
    return (st.st_mtime, st.st_size, digest)


def _reload_peers_now(httpd: Any) -> bool:
    """Re-parse peers.yaml + refresh ``httpd.federation_peers`` +
    re-run cert-level revocation. Returns True on a successful refresh.

    PLAN-112-FOLLOWUP W3 / R-IT-A: this re-evaluates cert-level revocation
    (expiry → ``federation_cert_revoked``) on every reload, NOT just the
    ``peer.revoked`` boolean — so a CERT revocation (expiry past) also
    propagates without restart. R-IT-C: every reload emits
    ``federation_peer_list_reloaded`` so the SLO is forensically
    observable.

    Fail-CLOSED note: on a parse error we DO NOT wipe the existing peer
    set (that would open the federation to all-peers-denied DoS on a
    transient bad write) — we keep the last-good set + emit a rejected
    breadcrumb. A peer_revoke writes peers.yaml atomically (tmpfile +
    rename) so a torn read is not expected; the keep-last-good policy is
    purely defense-in-depth.
    """
    cfg = getattr(httpd, "federation_config", None)
    peers_path = getattr(cfg, "peers_path", None) if cfg else None
    if peers_path is None:
        peers_path = getattr(httpd, "federation_peers_path", None)
    if peers_path is None:
        return False
    peers_path = Path(peers_path)

    now_dt = _dt.datetime.now(_dt.timezone.utc)
    try:
        peers = load_peers(peers_path)
    except (FileNotFoundError, PeersFileError, PeerHasNoFingerprintError) as exc:
        _safe_emit(
            "federation_peer_list_reloaded",
            peer_count=len(getattr(httpd, "federation_peers", {}) or {}),
            reload_reason="parse_error_kept_last_good",
            source_path=str(peers_path)[:128],
        )
        try:
            sys.stderr.write(
                "[federation.reload] peers.yaml reload failed ({0}); "
                "kept last-good set\n".format(type(exc).__name__)
            )
        except Exception:
            pass
        return False

    # R-IT-A — re-run cert-level revocation on reload (mirror
    # _load_peers_or_raise's expiry handling).
    for peer in peers.values():
        try:
            days_left = (peer.not_valid_after - now_dt).days
        except Exception:
            continue
        if days_left < 0:
            _safe_emit(
                "federation_cert_revoked",
                peer_id=peer.peer_id[:64],
                reason="expired",
            )

    httpd.federation_peers = peers  # type: ignore[attr-defined]
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
    _safe_emit(
        "federation_peer_list_reloaded",
        peer_count=len(peers),
        reload_reason="content_changed",
        source_path=str(peers_path)[:128],
    )
    return True


def _maybe_reload_peers(httpd: Any, *, now: Optional[float] = None) -> None:
    """Reload peers.yaml IF it changed since the last check.

    R-IT-C: kill-switch + peer-list are NOT boot-cached — this runs at the
    TOP of every write dispatch (and could be wired into the read path)
    so the <60s SLO is bounded by the request cadence, not a poll thread.
    A poll thread is ALSO started in ``serve_forever`` (see
    :meth:`FederationServer._start_reload_thread`) so the SLO holds even
    with zero traffic.

    Debounced by ``PEER_RELOAD_MIN_INTERVAL_SECONDS`` to avoid hashing the
    file on every single request under load.
    """
    ts = time.time() if now is None else float(now)
    lock = getattr(httpd, "federation_reload_lock", None)
    if lock is None:
        return
    cfg = getattr(httpd, "federation_config", None)
    peers_path = getattr(cfg, "peers_path", None) if cfg else None
    if peers_path is None:
        return
    peers_path = Path(peers_path)
    with lock:
        last_check = getattr(httpd, "federation_peers_last_check", 0.0)
        if (ts - last_check) < PEER_RELOAD_MIN_INTERVAL_SECONDS:
            return
        httpd.federation_peers_last_check = ts  # type: ignore[attr-defined]
        sig = _peers_file_signature(peers_path)
        prev_sig = getattr(httpd, "federation_peers_signature", None)
        if prev_sig is not None and sig == prev_sig:
            return
        httpd.federation_peers_signature = sig  # type: ignore[attr-defined]
    # Reload OUTSIDE the debounce lock (load_peers may do I/O); the reload
    # itself mutates httpd attributes which are read-mostly + GIL-atomic
    # dict reassignment.
    _reload_peers_now(httpd)


def _reap_orphaned_inflight(
    sentinels_dir,
    *,
    max_age_seconds=300.0,
    now=None,
):
    """AC15 (PLAN-112-FOLLOWUP PHASE2) — housekeeping sweep for orphaned
    ``*.inflight`` co-sign markers.

    Gate #10's claim renames ``approval.md`` / ``approval.md.asc`` to
    ``*.inflight`` BEFORE verify. Verify-failure self-reverts (Codex P2 #4)
    and verify-success consumes to ``*.consumed-<sigref>``; so the ONLY way
    an ``.inflight`` persists is a hard crash BETWEEN the two claim renames
    or between claim and revert/consume. This sweep moves any ``*.inflight``
    older than ``max_age_seconds`` to a TERMINAL ``*.orphaned-<mtime>``
    marker.

    **Quarantine, NOT revert (Codex AC18 P1).** An earlier draft renamed the
    orphan back to ``approval.md`` to make the co-sign re-drivable. That is
    unsafe: a crash in the post-verify / post-handler-mutation / pre-consume
    window would let the reaper RESURRECT an already-admitted DESTRUCTIVE
    co-sign — a single-use-violation / replay. Fail-CLOSED is the only safe
    posture for a destructive admission: an orphaned co-sign is terminalized
    and the Owner must issue a FRESH co-sign. (The verify-FAILURE revert in
    ``_verify_owner_cosign_claim`` is still safe + kept — a co-sign that
    failed verification was never admitted, so restoring it merely lets the
    Owner retry; it cannot drive anything until it verifies.)

    Best-effort + fail-open; returns the count quarantined. The 5-min default
    leaves a legitimately in-flight claim (completes in ms) untouched.
    """
    if sentinels_dir is None:
        return 0
    base = Path(sentinels_dir)
    if not base.is_dir():
        return 0
    ts = time.time() if now is None else float(now)
    quarantined = 0
    suffix = ".inflight"
    try:
        candidates = list(base.glob("*/*" + suffix))
    except OSError:
        return 0
    for inflight in candidates:
        try:
            if not inflight.is_file():
                continue
            mtime = inflight.stat().st_mtime
            if (ts - mtime) <= max_age_seconds:
                continue
            terminal = inflight.with_name(
                inflight.name[: -len(suffix)]
                + ".orphaned-{0}".format(int(mtime))
            )
            try:
                os.rename(str(inflight), str(terminal))
                quarantined += 1
            except OSError:
                # Terminal target already exists (re-reap) — drop the stray.
                try:
                    inflight.unlink()
                except OSError:
                    pass
        except OSError:
            continue
    return quarantined


# ---------------------------------------------------------------------------
# Request handler — 3 read endpoints + 4 write endpoints + 11-gate chain
# ---------------------------------------------------------------------------


