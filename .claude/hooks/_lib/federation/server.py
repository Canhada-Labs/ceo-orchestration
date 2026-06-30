"""PLAN-099 Wave A.1 + Wave B + PLAN-099-FOLLOWUP Wave D/E — stdlib federation server.

This module ships ``FederationServer``, a thin wrapper around
:class:`http.server.ThreadingHTTPServer` with:

- TLSv1.3 minimum (:class:`ssl.SSLContext` ``minimum_version``)
- mTLS mandatory (``CERT_REQUIRED``; server-side ``check_hostname=False``
  by design — stdlib SSLContext does not validate incoming-client SNI
  via this flag, so leaving it True would only add a confusing
  no-op. Client-side context (``federation.client``) DOES enable
  ``check_hostname=True`` for outbound peer-cert SAN validation.)
- Loopback-default bind; non-loopback bind gated by Owner-GPG LAN sentinel
- Mechanical HTTP method allowlist (GET always; POST ONLY when write-mode
  is active per the Layer 0a env + Layer 0b sentinel default-OFF chain —
  PLAN-112-FOLLOWUP-federation-wire-or-delete W1)
- 3 read-only endpoints: ``/federation/identity``, ``/federation/status``,
  ``/federation/audit-summary`` (Wave B)
- 4 write endpoints behind the 11-gate dispatcher (ADR-135-AMEND-1 §2.2;
  Wave D) — default-OFF.
- HMAC+nonce+timestamp replay protection (Wave A — AC13)
- Joint-key rate limit on /audit-summary (AC17) + per-route token-bucket +
  circuit-breaker + backpressure on writes (Wave E)
- Peer-list reload-watcher so a ``peer_revoke`` propagates to the running
  server in <60s without restart (PLAN-112-FOLLOWUP W3, P0-1).
- All emit paths gated through :mod:`audit_emit` with kernel-override-
  registered ``federation_*`` actions; the ``_safe_emit`` shim now falls
  back to ``emit_generic`` so the Wave-F.2 actions (which have NO named
  ``emit_*`` wrapper) are actually written (PLAN-112-FOLLOWUP C-4 fix —
  closes the R-TD-1 no-op trap).

Stdlib-only per ADR-126 §Part 6 (no ``cryptography`` package).
"""

from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import http.server
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple


def _read_max_cert_validity_days_from_init(*, default: int) -> int:
    """Single-source-of-truth read of ``MAX_CERT_VALIDITY_DAYS``.

    PLAN-113 W5 (F-5.8-mac-cert-validity-duplicate). The package
    ``__init__.py`` owns the literal value. The package-relative
    ``from . import MAX_CERT_VALIDITY_DAYS`` (in the try-block below)
    is the normal path; this helper covers ONLY the flat-import
    (test / draft) fallback where there is no ``federation`` package
    namespace to import from. Rather than re-declare the literal here
    (which can drift), parse it out of the sibling ``__init__.py`` by
    path so the number lives in exactly one place.

    Fail-soft: any read/parse failure returns ``default`` (the historical
    literal). server.py and __init__.py ship in the same directory, so
    a miss is never expected in a real install.
    """
    try:
        init_path = Path(__file__).resolve().parent / "__init__.py"
        text = init_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return default
    # Match a top-level `MAX_CERT_VALIDITY_DAYS = <int>` assignment.
    m = re.search(
        r"^MAX_CERT_VALIDITY_DAYS\s*=\s*(\d+)\s*$",
        text,
        re.MULTILINE,
    )
    if m is None:
        return default
    try:
        return int(m.group(1))
    except ValueError:  # pragma: no cover — regex guarantees digits
        return default


# Package-internal helpers — imports resolve via the canonical package
# path .claude/hooks/_lib/federation/ once the patcher installs the
# files. During unit tests the draft layout in .claude/plans/PLAN-099/
# is loaded directly.
try:
    from .identity import (
        PeerRecord,
        PeersFileError,
        compute_cert_fingerprint,
        compare_fingerprints,
        load_peers,
        lookup_peer_by_fingerprint,
        verify_enable_sentinel_pair,
        # Wave C (PLAN-099-FOLLOWUP) — SPKI dispatcher primitives.
        compute_spki_fingerprint,
        compute_der_fingerprint_from_pem,
        select_pin_for_peer,
        PinSelectionError,
        # Wave C P0 F-003 — specific subclass for no-pin parse-time
        # invariant violations (routed to the federation_peer_invalid_no_fingerprint
        # emit in _load_peers_or_raise).
        PeerHasNoFingerprintError,
    )
    from .replay import ReplayCache, ReplayDecision, parse_rfc3339_utc
    from .audit_chain import (
        CORRELATION_ID_HEADER,
        stamp_local_with_correlation,
    )
    # Wave D (PLAN-099-FOLLOWUP) — RBAC matrix + write-endpoint handlers.
    from . import scopes as _fed_scopes
    from .handlers import (
        peer_register as _h_peer_register,
        audit_event_push as _h_audit_event_push,
        audit_event_batch as _h_audit_event_batch,
        peer_revoke as _h_peer_revoke,
    )
    from . import (
        AUDIT_SUMMARY_RATE_PER_MIN,
        ALLOWED_HTTP_METHODS,
        CERT_EXPIRY_WARN_DAYS,
        DEFAULT_BIND,
        DEFAULT_PORT,
        FEDERATION_KILL_SWITCH_ENV,
        HANDSHAKE_TIMEOUT_SECONDS,
        MAX_CERT_VALIDITY_DAYS,
        MAX_CLOCK_SKEW_SECONDS,
        OWNER_GPG_FPR,
        FEDERATION_WRITE_KILL_SWITCH_ENV,
        WRITE_ALLOWED_HTTP_METHODS,
        PEER_RELOAD_MIN_INTERVAL_SECONDS,
    )
except ImportError:
    # Test / draft mode — flat-import fallback.
    from identity import (  # type: ignore[no-redef]
        PeerRecord,
        PeersFileError,
        compute_cert_fingerprint,
        compare_fingerprints,
        load_peers,
        lookup_peer_by_fingerprint,
        verify_enable_sentinel_pair,
        # Wave C (PLAN-099-FOLLOWUP) — SPKI dispatcher primitives.
        compute_spki_fingerprint,
        compute_der_fingerprint_from_pem,
        select_pin_for_peer,
        PinSelectionError,
        PeerHasNoFingerprintError,
    )
    from replay import ReplayCache, ReplayDecision, parse_rfc3339_utc  # type: ignore[no-redef]
    from audit_chain import (  # type: ignore[no-redef]
        CORRELATION_ID_HEADER,
        stamp_local_with_correlation,
    )
    try:
        import scopes as _fed_scopes  # type: ignore[no-redef]
        from handlers import (  # type: ignore[no-redef]
            peer_register as _h_peer_register,
            audit_event_push as _h_audit_event_push,
            audit_event_batch as _h_audit_event_batch,
            peer_revoke as _h_peer_revoke,
        )
    except ImportError:
        _fed_scopes = None  # type: ignore[assignment]
        _h_peer_register = None  # type: ignore[assignment]
        _h_audit_event_push = None  # type: ignore[assignment]
        _h_audit_event_batch = None  # type: ignore[assignment]
        _h_peer_revoke = None  # type: ignore[assignment]
    AUDIT_SUMMARY_RATE_PER_MIN = 10
    ALLOWED_HTTP_METHODS = frozenset(("GET",))
    CERT_EXPIRY_WARN_DAYS = 14
    DEFAULT_BIND = "127.0.0.1"
    DEFAULT_PORT = 8843
    FEDERATION_KILL_SWITCH_ENV = "CEO_FEDERATION_ENABLED"
    HANDSHAKE_TIMEOUT_SECONDS = 5.0
    # PLAN-113 W5 — F-5.8-mac-cert-validity-duplicate. The package
    # __init__.py is the SINGLE SOURCE OF TRUTH for MAX_CERT_VALIDITY_DAYS.
    # In flat-import (test/draft) mode the `from . import ...` above raised
    # ImportError, so we cannot use a package-relative import here. Instead
    # of redefining the literal (drift risk), source the value out of the
    # sibling __init__.py by path. The literal `90` then lives in exactly
    # ONE place. Fall back to the historical literal ONLY if the sibling
    # file is unreadable (never expected — server.py and __init__.py ship
    # in the same package directory).
    MAX_CERT_VALIDITY_DAYS = _read_max_cert_validity_days_from_init(default=90)
    MAX_CLOCK_SKEW_SECONDS = 30
    OWNER_GPG_FPR = "0000000000000000000000000000000000000000"
    FEDERATION_WRITE_KILL_SWITCH_ENV = "CEO_FEDERATION_WRITE_ENABLED"
    WRITE_ALLOWED_HTTP_METHODS = frozenset(("GET", "POST"))
    PEER_RELOAD_MIN_INTERVAL_SECONDS = 1.0


# Wave E modules — lazy-loaded inside the dispatcher to keep module
# import cheap and tolerant of partial installs.
# (rate_limit + audit_chain_ext resolved via _load_rate_limit / _load_audit_chain_ext)


__all__ = [
    "FederationConfig",
    "FederationServer",
    "FederationStartError",
    "build_ssl_context",
    "resolve_bind_is_loopback",
    "write_mode_enabled_from_env",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FederationStartError(RuntimeError):
    """Raised by :meth:`FederationServer.serve_forever` when any of the
    enable invariants fail. The audit-emit side-effect happens
    BEFORE the raise; the exception is the operator-facing surface."""


# ---------------------------------------------------------------------------
# Audit emit shims (hasattr-guarded to work pre + post canonical ceremony)
# ---------------------------------------------------------------------------


def _safe_emit(action: str, **fields: Any) -> None:
    """Call ``audit_emit.emit_<action>(...)`` if registered; else fall
    back to ``audit_emit.emit_generic(action, ...)``; else no-op.

    PLAN-112-FOLLOWUP-federation-wire-or-delete C-4 fix (closes R-TD-1):
    the Wave-F.2 federation actions are present in ``_KNOWN_ACTIONS`` but
    have NO named ``emit_<action>`` wrapper. The previous shim only tried
    the named wrapper, so EVERY Wave-D/E federation emit silently no-oped
    (dead detection that passes green). We now fall back to ``emit_generic``
    which validates against ``_KNOWN_ACTIONS`` and writes through the same
    filelock + HMAC chain. Unknown actions still no-op (emit_generic
    breadcrumbs + returns), preserving the fail-open-on-infra contract.
    """
    try:
        try:
            from _lib import audit_emit  # type: ignore[import]
        except ImportError:
            import importlib
            audit_emit = importlib.import_module(".audit_emit", package="_lib")
    except ImportError:
        return
    fn_name = "emit_{0}".format(action)
    fn = getattr(audit_emit, fn_name, None)
    try:
        if fn is not None:
            fn(**fields)
            return
        generic = getattr(audit_emit, "emit_generic", None)
        if generic is not None:
            generic(action, **fields)
    except Exception:
        # Audit-emit MUST NEVER block the server. Swallow + breadcrumb.
        try:
            sys.stderr.write(
                "[federation.server] audit emit '{0}' raised; ignored\n".format(
                    action
                )
            )
        except Exception:
            pass


def write_mode_enabled_from_env() -> bool:
    """Layer 0a — master write-mode env switch (fail-CLOSED default-OFF).

    PLAN-112-FOLLOWUP W1 (AC1/AC14). The ONLY accepted truthy value is the
    exact string ``"1"``. Unset / empty / ``"0"`` / ``"true"`` / any other
    value → write-mode OFF. This is deliberately STRICTER than the read-mode
    kill-switch (which accepts ``1/true/TRUE``) — write activation is a
    higher-blast-radius operation and must not be flipped by an ambient
    ``true`` left in a profile.

    Returns False on any error (fail-CLOSED).
    """
    try:
        v = os.environ.get(FEDERATION_WRITE_KILL_SWITCH_ENV, "")
        return v.strip() == "1"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Lazy Wave-E loaders
# ---------------------------------------------------------------------------


def _load_rate_limit():
    """Return the rate_limit module or None (partial-install tolerant)."""
    try:
        try:
            from . import rate_limit as _rl  # type: ignore
        except ImportError:
            import importlib
            _rl = importlib.import_module(
                "_lib.federation.rate_limit"
            )
        return _rl
    except Exception:
        return None


def _load_audit_chain_ext():
    """Return the audit_chain_ext module or None."""
    try:
        try:
            from . import audit_chain_ext as _ace  # type: ignore
        except ImportError:
            import importlib
            _ace = importlib.import_module(
                "_lib.federation.audit_chain_ext"
            )
        return _ace
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


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


class _ThreadingHTTPSServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer with dual-stack support."""

    address_family = socket.AF_INET  # default; overridden at instantiate

    def __init__(self, server_address, RequestHandlerClass, address_family=None):
        if address_family is not None:
            self.address_family = address_family
        super().__init__(server_address, RequestHandlerClass)


# ---------------------------------------------------------------------------
# SSLContext builder (AC1 / AC2)
# ---------------------------------------------------------------------------


def build_ssl_context(
    cert_file: Path,
    key_file: Path,
    ca_file: Path,
) -> ssl.SSLContext:
    """Construct a TLSv1.3-min mTLS SSLContext for the server side."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = False  # Server side: client SNI not validated by us
    ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    ctx.load_verify_locations(cafile=str(ca_file))
    return ctx


# ---------------------------------------------------------------------------
# Rate limiter — joint key (peer_id_cert_fingerprint, ip) — for /audit-summary
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


class _FederationHandler(http.server.BaseHTTPRequestHandler):
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
_REDACTION_FAIL_CLOSED_MARKER = object()


def _apply_redaction_pipeline(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Apply ``redact_secrets`` + ``pii_patterns.scan(...,mode="redact")``."""
    out: List[Dict[str, Any]] = []
    redact_secrets = None
    pii_scan = None
    load_error: Optional[str] = None
    try:
        try:
            from _lib import redact as _redact  # type: ignore[import]
            from _lib import pii_patterns as _pii  # type: ignore[import]
        except ImportError:
            import importlib
            _redact = importlib.import_module(".redact", package="_lib")
            _pii = importlib.import_module(".pii_patterns", package="_lib")
        redact_secrets = getattr(_redact, "redact_secrets", None)
        _pii_scan = getattr(_pii, "scan", None)
        if _pii_scan is not None:
            def _pii_redact_adapter(text: str) -> str:
                result = _pii_scan(text, mode="redact")
                return getattr(result, "redacted_text", text) or text
            pii_scan = _pii_redact_adapter
    except Exception as e:  # noqa: BLE001 — defense-in-depth
        load_error = "{0}:{1}".format(type(e).__name__, str(e)[:80])

    if redact_secrets is None or pii_scan is None:
        try:
            sys.stderr.write(
                "[federation.server] AC6 fail-CLOSED — redact_secrets={0!r} "
                "pii_scan={1!r} load_error={2!r}; refusing to serialise "
                "audit-summary events\n".format(
                    redact_secrets is not None,
                    pii_scan is not None,
                    load_error,
                )
            )
        except Exception:
            pass
        return []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        try:
            blob = json.dumps(ev, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
        try:
            blob = redact_secrets(blob)
        except Exception:
            continue
        try:
            blob = pii_scan(blob)
        except Exception:
            continue
        try:
            redacted = json.loads(blob)
        except (TypeError, ValueError):
            continue
        out.append(redacted)
    return out


# ---------------------------------------------------------------------------
# FederationServer — orchestrator
# ---------------------------------------------------------------------------


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
