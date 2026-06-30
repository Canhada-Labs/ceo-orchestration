"""PLAN-099 Wave C — audit-chain stitching for cross-machine events.

When a remote peer's audit-summary is consumed locally, each remote
event is tagged with ``federation_origin: <peer_id_cert_fingerprint>``
(C.1) + a ``fed_correlation_id`` (C.2) propagated through the chain.

The local audit-log then carries the stitched record (C.3), correlating
with the upstream emit so an investigator can trace an event back to
the originating node.

Tagging strategy
----------------

This module is a pure helper — it does NOT touch the audit-log writer.
Callers (typically :mod:`federation.client`) pass remote-event dicts
through :func:`tag_remote_event` before forwarding them to the regular
emit pipeline.

The tag is appended at the top-level of the event dict (NOT nested
inside a "federation:" sub-dict) so existing audit-query filters can
match on a single key.

The ``fed_correlation_id`` is generated client-side and propagated to
the server via the ``X-CEO-Federation-Correlation-Id`` request header.
Server-emitted audit lines pick it up off the request and stamp it
locally, completing the chain.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, Optional

__all__ = [
    "FEDERATION_ORIGIN_KEY",
    "FEDERATION_CORRELATION_ID_KEY",
    "CORRELATION_ID_HEADER",
    "generate_correlation_id",
    "tag_remote_event",
    "stamp_local_with_correlation",
]


# Stable tag-keys for downstream audit-query filters.
FEDERATION_ORIGIN_KEY = "federation_origin"
FEDERATION_CORRELATION_ID_KEY = "fed_correlation_id"
CORRELATION_ID_HEADER = "X-CEO-Federation-Correlation-Id"


def generate_correlation_id() -> str:
    """Return a fresh opaque correlation id (URL-safe, ≥128 bits)."""
    return "fed-" + secrets.token_urlsafe(16)


def tag_remote_event(
    event: Dict[str, Any],
    *,
    federation_origin: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a copy of ``event`` with federation provenance stamps.

    Parameters
    ----------
    event
        The remote event as deserialised from ``/federation/audit-summary``
        response. MUST already have been redacted by the upstream node;
        this helper assumes the wire format is already PII-safe (the
        remote applies :mod:`pii_redact_full` before serialisation).
    federation_origin
        The peer's full-cert DER fingerprint (64-hex lowercase).
    correlation_id
        Optional explicit correlation id; otherwise the existing
        ``fed_correlation_id`` is preserved, or a new one generated.

    Returns
    -------
    dict
        A shallow copy of the input with the two keys stamped at the
        top level. If the input already carries either key, the helper
        does NOT overwrite — preserves upstream attribution.
    """
    if not isinstance(event, dict):
        raise TypeError("event must be a dict")
    if not federation_origin or not isinstance(federation_origin, str):
        raise ValueError("federation_origin must be non-empty string")

    out: Dict[str, Any] = dict(event)
    out.setdefault(FEDERATION_ORIGIN_KEY, federation_origin.lower())
    if correlation_id:
        out.setdefault(FEDERATION_CORRELATION_ID_KEY, correlation_id)
    else:
        out.setdefault(
            FEDERATION_CORRELATION_ID_KEY, generate_correlation_id()
        )
    return out


def stamp_local_with_correlation(
    event: Dict[str, Any],
    correlation_id: str,
) -> Dict[str, Any]:
    """Stamp a server-side emit with the request's correlation id.

    Used by the server when emitting ``federation_connection_accepted``
    + related events — the id comes off the incoming request's
    ``X-CEO-Federation-Correlation-Id`` header. Does NOT stamp
    ``federation_origin`` (that's a client-side tag for events FROM
    another node; server emits are about peers, keyed by
    ``peer_id_cert_fingerprint`` in their own field).
    """
    if not isinstance(event, dict):
        raise TypeError("event must be a dict")
    if not correlation_id:
        return dict(event)
    out: Dict[str, Any] = dict(event)
    out.setdefault(FEDERATION_CORRELATION_ID_KEY, correlation_id)
    return out
