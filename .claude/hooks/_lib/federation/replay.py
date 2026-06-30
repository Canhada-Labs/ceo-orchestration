"""PLAN-099 Wave A — HMAC + nonce + timestamp replay protection (AC13).

All primitives stdlib: :mod:`hmac` + :mod:`secrets` + :mod:`hashlib` +
:mod:`time` + :mod:`collections`. No third-party crypto.

Wire model
----------

Each peer-→-server request MUST carry three headers:

- ``X-CEO-Federation-Nonce``    — ``secrets.token_urlsafe(24)`` ≥128-bit,
                                  single-use.
- ``X-CEO-Federation-Timestamp`` — RFC3339 issuance time. Server rejects
                                   ``|Δt| > MAX_CLOCK_SKEW_SECONDS`` (30s
                                   default) vs server wall clock.
- ``X-CEO-Federation-Signature`` — hex HMAC-SHA256 over the canonical
                                   string defined by :func:`canonical_signing_payload`.

The canonical string is::

    METHOD \\n PATH \\n TIMESTAMP \\n NONCE \\n BODY_SHA256_HEX

Comparison is via :func:`hmac.compare_digest` (constant-time).

Replay cache
------------

Per-peer ring buffer of ``(nonce, server_stored_ts)``. On every accept,
the cache:

1. Prunes entries older than ``2 * MAX_CLOCK_SKEW_SECONDS + 1`` (~61s
   conservatively covers the full replay-attack window). Reasoning: a
   nonce accepted with ``request_ts == T0 + max_skew`` could be replayed
   at any server time up to ``T0 + 2*max_skew`` and still pass the
   ``|Δt| <= max_skew`` check. The cache MUST retain entries for that
   full window or replay is possible.
2. Rejects if ``(nonce, peer_id)`` is already present (replay).

Cache is in-memory; restart wipes it. AC13 invariant: "within the 60s
window, no nonce reuse". Sufficient for MVP. Cross-restart replay
defense is non-MVP scope (would require persistent nonce ledger).
"""

from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional, Tuple

__all__ = [
    "ReplayCache",
    "ReplayDecision",
    "canonical_signing_payload",
    "sign_request",
    "verify_signature",
    "parse_rfc3339_utc",
    "generate_nonce",
    "MAX_CLOCK_SKEW_SECONDS",
]


# Imported from package __init__ would create a cycle here; mirror the
# canonical value verbatim. Any drift caught by test_federation_replay.py.
MAX_CLOCK_SKEW_SECONDS = 30


# ---------------------------------------------------------------------------
# Canonical-string + HMAC
# ---------------------------------------------------------------------------


def canonical_signing_payload(
    method: str,
    path: str,
    timestamp_rfc3339: str,
    nonce: str,
    body_sha256_hex: str,
) -> bytes:
    """Compose the canonical signing string per AC13.

    All five fields are stringified; the separator is a single ``\\n``.
    The output is the bytes fed into :func:`hmac.new` and
    :func:`hmac.compare_digest`.

    Inputs are NOT validated here; callers MUST ensure each is non-empty
    + correctly normalised (uppercase method, leading-slash path, etc.)
    """
    s = "\n".join((method, path, timestamp_rfc3339, nonce, body_sha256_hex))
    return s.encode("utf-8")


def sign_request(
    method: str,
    path: str,
    timestamp_rfc3339: str,
    nonce: str,
    body: bytes,
    hmac_secret_hex: str,
) -> str:
    """Compute the HMAC-SHA256 signature for a federation request.

    Returns the hex-encoded MAC. The body is hashed via SHA-256 (also
    hex) before inclusion in the canonical string — pre-hashing keeps
    the signing-string length bounded regardless of body size.

    ``hmac_secret_hex`` is the per-peer secret from ``peers.yaml``
    (64-hex = 32 bytes). Empty / malformed secret → raises ValueError
    (callers MUST refuse to start the server with unsigned peers).
    """
    if not hmac_secret_hex or not isinstance(hmac_secret_hex, str):
        raise ValueError("hmac_secret_hex must be non-empty hex string")
    try:
        secret_bytes = bytes.fromhex(hmac_secret_hex)
    except ValueError as e:
        raise ValueError("hmac_secret_hex not valid hex: {0}".format(e))

    body_hash = hashlib.sha256(body or b"").hexdigest()
    payload = canonical_signing_payload(
        method, path, timestamp_rfc3339, nonce, body_hash,
    )
    mac = hmac.new(secret_bytes, payload, hashlib.sha256)
    return mac.hexdigest()


def verify_signature(
    method: str,
    path: str,
    timestamp_rfc3339: str,
    nonce: str,
    body: bytes,
    hmac_secret_hex: str,
    presented_signature_hex: str,
) -> bool:
    """Constant-time verify of a federation request signature.

    Returns ``True`` iff the recomputed HMAC matches the presented
    signature under :func:`hmac.compare_digest`. Any input error
    (malformed secret, malformed signature) returns ``False`` — never
    raises (used inside request-dispatch path).
    """
    if not presented_signature_hex or not isinstance(presented_signature_hex, str):
        return False
    try:
        expected = sign_request(
            method, path, timestamp_rfc3339, nonce, body, hmac_secret_hex,
        )
    except (ValueError, TypeError):
        return False
    if len(expected) != len(presented_signature_hex):
        return False
    return hmac.compare_digest(expected, presented_signature_hex.lower())


# ---------------------------------------------------------------------------
# Nonce + timestamp helpers
# ---------------------------------------------------------------------------


def generate_nonce(nbytes: int = 24) -> str:
    """Generate a ≥128-bit URL-safe nonce (default 24 bytes = 192 bits)."""
    if nbytes < 16:
        raise ValueError("nonce must be at least 128 bits (16 bytes)")
    return secrets.token_urlsafe(nbytes)


def parse_rfc3339_utc(value: str) -> _dt.datetime:
    """Parse an RFC3339 timestamp into a UTC-aware datetime.

    Naive input rejected; trailing ``Z`` accepted.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("empty timestamp")
    if raw.endswith("Z") or raw.endswith("z"):
        raw = raw[:-1] + "+00:00"
    parsed = _dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("naive timestamp")
    return parsed.astimezone(_dt.timezone.utc)


# ---------------------------------------------------------------------------
# Replay cache
# ---------------------------------------------------------------------------


@dataclass
class ReplayDecision:
    """Outcome of :meth:`ReplayCache.check_and_record`."""

    accepted: bool
    reason: str = ""  # one of: clock_skew, replay, signature_invalid, ok


@dataclass
class ReplayCache:
    """Per-peer single-use-nonce ring buffer.

    Bounded by wall-clock — entries older than ``2 * MAX_CLOCK_SKEW_SECONDS
    + 1`` (~61s with default 30s skew) are pruned on every access. The
    2x window is REQUIRED: an attacker who captures a request issued at
    ``request_ts = server_time + max_skew`` can replay it any time up
    to ``server_time + 2*max_skew`` and still pass the ``|Δt| <=
    max_skew`` freshness check (Codex R2 iter-1 P0#1 fix).

    Thread-safe — server runs under ``ThreadingHTTPServer`` so
    concurrent peers will contend. The cache key for nonces is
    ``peer_id``; each peer gets its own deque, so peer-isolation is
    enforced (different peers can use the same nonce string without
    collision; same peer cannot reuse a nonce inside the 2x window).
    """

    max_skew_seconds: int = MAX_CLOCK_SKEW_SECONDS
    _cache: Dict[str, Deque[Tuple[str, float]]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check_and_record(
        self,
        peer_id: str,
        nonce: str,
        request_timestamp_rfc3339: str,
        now_epoch: Optional[float] = None,
    ) -> ReplayDecision:
        """Validate + record a single nonce. Returns the decision.

        Two failures:

        - ``clock_skew`` — request timestamp is more than
          ``max_skew_seconds`` from server wall clock (in either
          direction).
        - ``replay`` — the same ``(peer_id, nonce)`` pair was already
          recorded inside the rolling window.

        On success, the nonce is recorded with the server timestamp
        (not the request timestamp — defends against an attacker who
        sets a high `iat` to keep the nonce alive for longer than the
        clock-skew window).
        """
        if not peer_id or not nonce:
            return ReplayDecision(False, "missing_peer_or_nonce")

        try:
            ts = parse_rfc3339_utc(request_timestamp_rfc3339)
        except ValueError:
            return ReplayDecision(False, "malformed_timestamp")

        now = now_epoch if now_epoch is not None else time.time()
        skew = abs(ts.timestamp() - now)
        if skew > self.max_skew_seconds:
            return ReplayDecision(False, "clock_skew")

        with self._lock:
            bucket = self._cache.setdefault(peer_id, collections.deque())
            self._prune_locked(bucket, now)
            for existing_nonce, _ts in bucket:
                if hmac.compare_digest(existing_nonce, nonce):
                    return ReplayDecision(False, "replay")
            bucket.append((nonce, now))

        return ReplayDecision(True, "ok")

    def _prune_locked(
        self,
        bucket: Deque[Tuple[str, float]],
        now: float,
    ) -> None:
        """Remove entries older than the full replay window.

        Cutoff is ``2 * max_skew_seconds + 1`` because an attacker who
        captured a request issued at ``request_ts = server_time +
        max_skew`` can replay it any time up to
        ``server_time + 2*max_skew`` and still satisfy the
        ``|Δt| <= max_skew`` freshness check. Pruning earlier than that
        leaves a replay window open.
        """
        cutoff = now - (2 * self.max_skew_seconds + 1)
        while bucket and bucket[0][1] < cutoff:
            bucket.popleft()
