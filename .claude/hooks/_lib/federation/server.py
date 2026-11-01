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



# Mechanically extracted declarations retain this module's globals: patching a
# facade helper/constant must affect methods even after extraction.
import importlib.util as _importlib_util
from types import FunctionType as _FunctionType


def _bind_function(_original):
    _bound = _FunctionType(
        _original.__code__, globals(), _original.__name__,
        _original.__defaults__, _original.__closure__,
    )
    _bound.__kwdefaults__ = _original.__kwdefaults__
    _bound.__annotations__ = dict(_original.__annotations__)
    _bound.__dict__.update(_original.__dict__)
    _bound.__qualname__ = _original.__qualname__
    _bound.__module__ = __name__
    return _bound


def _bind_class(_class):
    for _name, _member in vars(_class).copy().items():
        if isinstance(_member, _FunctionType):
            setattr(_class, _name, _bind_function(_member))
        elif isinstance(_member, staticmethod):
            setattr(_class, _name, staticmethod(_bind_function(_member.__func__)))
        elif isinstance(_member, classmethod):
            setattr(_class, _name, classmethod(_bind_function(_member.__func__)))
    _class.__module__ = __name__
    return _class


def _load_part(_part, _names):
    _location = Path(__file__).resolve().parent / "_server_parts" / (_part + ".py")
    _spec = _importlib_util.spec_from_file_location(
        __name__ + "._server_parts." + _part, _location,
    )
    if _spec is None or _spec.loader is None:
        raise ImportError("cannot load federation server part " + _part)
    _module = _importlib_util.module_from_spec(_spec)
    # Class bases and class-level defaults are resolved while the templates
    # are declared; method globals are rebound to this facade immediately.
    _module.__dict__.update({
        _key: _value for _key, _value in globals().items()
        if not _key.startswith("__")
    })
    _spec.loader.exec_module(_module)
    for _name in _names:
        _value = getattr(_module, _name)
        globals()[_name] = _bind_class(_value) if isinstance(_value, type) else (
            _bind_function(_value) if isinstance(_value, _FunctionType) else _value
        )


_load_part("configuration", (
    "FederationConfig", "resolve_bind_is_loopback", "JointKeyRateLimiter",
    "_peers_file_signature", "_reload_peers_now", "_maybe_reload_peers",
    "_reap_orphaned_inflight",
))
_load_part("handler_auth", ("_HandlerAuth",))
_load_part("handler_write", ("_HandlerWrite",))
_load_part("handler_read", ("_HandlerRead",))


class _FederationHandler(
    _HandlerAuth, _HandlerWrite, _HandlerRead,
    http.server.BaseHTTPRequestHandler,
):
    """Per-request handler, composed from independently bounded method groups."""


_load_part("redaction", ("_REDACTION_FAIL_CLOSED_MARKER", "_apply_redaction_pipeline"))
_load_part("lifecycle", ("FederationServer",))
del _HandlerAuth, _HandlerWrite, _HandlerRead
