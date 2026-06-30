"""MCP bearer-token replay defense — PLAN-085 Wave C.3.

Loopback-only nonce + 60s skew window. DPoP RFC 9449 full implementation
DEFERRED to PLAN-090 per evolution-roadmap.

# TARGET PATH (apply via Owner-signed sentinel ceremony):
#   .claude/hooks/_lib/mcp/bearer_replay.py

## Acceptance rule (R2 iter-1 C1 — corrected from logical-AND bug):

1. Reject stale ``iat`` regardless of nonce uniqueness:
   ``abs(now_ns - iat_ns) > skew_window_ns`` → DENY (stale_iat)
2. Reject seen nonce regardless of ``iat`` freshness:
   nonce ∈ seen-set → DENY (nonce_reused)
3. Both stale AND seen → DENY (stale_iat_and_nonce_reused)
4. Accept ONLY when ``iat`` is fresh AND nonce is unique;
   atomic insert into seen-set on accept.

## Loopback enforcement

Handler entry: ``request.remote_addr in _LOOPBACK_ADDRS`` →
fail-CLOSED non-loopback. Emits ``mcp_non_loopback_rejected``.

The whitelist contains the IPv4/IPv6 loopback literals AND the
``"stdio-local"`` sentinel (PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire
§3a): a local stdio pipe is loopback-equivalent trust — there is no
remote network address for the stdio transport, so the dispatcher
passes ``"stdio-local"`` and the store treats it as loopback.

## Clock source (PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — clock reconcile)

``time.time_ns()`` — WALL-CLOCK nanoseconds. This is the central bug
fix from the wire-up plan: the MCP bearer token carries a wall-clock
``timestamp_ms`` (see ``auth.compute_hmac`` body
``client_id+nonce+str(timestamp_ms)``), and ``dispatch.authenticate``
validates skew against ``_now_ms() = int(time.time()*1000)`` — both
are wall-clock. The store MUST be in the SAME clock domain so the
caller can pass ``iat_ns = timestamp_ms * 1_000_000`` and compare it
against the store's ``now_ns`` without a domain mismatch (which would
produce random ACCEPT/DENY). The store therefore defaults to
``time.time_ns`` (NOT ``time.monotonic_ns`` as the original PLAN-085
implementation assumed). The caller MUST pass ``iat_ns`` sourced from
the SAME wall clock; tests inject a deterministic clock.

## Single freshness window (PLAN-112-FOLLOWUP — single-window reconcile)

The default ``skew_window_ns`` is derived from the auth-layer skew
constant (``auth._SKEW_MS`` = 60_000 ms) so the store window and the
``verify_timestamp_skew`` window cannot diverge. The module reads the
auth constant at import time with a stdlib-only fallback (60s) when the
auth module is not importable (e.g. the store used standalone in unit
tests). The constructor still accepts an explicit override.

## Nonce store + bounded LRU (PLAN-112-FOLLOWUP — CWE-400 cap)

In-memory ``OrderedDict`` keyed by ``nonce``; entry purged when
``abs(now_ns - iat_ns) > bearer_token_max_age_ns`` (TTL eviction). On
top of TTL there is an explicit ``maxsize`` LRU cap (default 10_000):
when an accept would exceed ``maxsize`` the oldest-inserted nonce is
evicted. This bounds memory under a unique-nonce flood that TTL alone
(24h default) would not contain. Seen-nonce retention is still backed
by the policy lifetime (R1 Sec-1 / handoff §9.1 hardening) up to the
cap.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Optional, Tuple


# ---------------------------------------------------------------------
# Freshness window — single source of truth reconciled with auth layer.
#
# PLAN-112-FOLLOWUP §3 "single freshness window": the store window is
# derived from the MCP auth-layer skew constant so the two ±60s windows
# cannot drift apart. ``auth._SKEW_MS`` lives in
# ``.claude/scripts/mcp-server/auth.py`` and is expressed in
# milliseconds; convert to ns. Fall back to the historical 60s literal
# when auth is not importable (standalone unit-test usage of the store).
# ---------------------------------------------------------------------


def _resolve_auth_skew_ns() -> int:
    """Return the auth-layer skew window in ns (fallback 60s).

    Reads ``auth._SKEW_MS`` (milliseconds) and converts to nanoseconds.
    The auth module lives under ``.claude/scripts/mcp-server`` which is
    added to ``sys.path`` by the MCP server bootstrap; when that module
    is not on the path (pure-unit usage of the store), we fall back to
    the documented 60s literal so the store is still usable standalone.
    """
    try:
        import auth  # type: ignore[import-not-found]

        skew_ms = int(getattr(auth, "_SKEW_MS"))
        if skew_ms > 0:
            return skew_ms * 1_000_000
    except Exception:  # noqa: BLE001 — any import/attr failure → fallback
        pass
    return 60 * 1_000_000_000


# Skew window per ADR-040-MCP-Auth subsection annotation. Derived from
# the auth-layer constant at import time (single freshness window).
SKEW_WINDOW_NS: int = _resolve_auth_skew_ns()

# Bearer-token max age = nonce-store TTL (R1 Sec-1 / handoff §9.1).
# Default 24h; caller may override via constructor.
DEFAULT_BEARER_TOKEN_MAX_AGE_NS: int = 24 * 3600 * 1_000_000_000

# PLAN-112-FOLLOWUP §3 — bounded LRU cardinality cap (CWE-400). On top
# of TTL eviction; oldest-inserted nonce evicted when an accept would
# exceed this many live entries.
DEFAULT_MAXSIZE: int = 10_000

# Loopback whitelist — explicit fail-CLOSED on anything else.
# PLAN-112-FOLLOWUP §3a — ``"stdio-local"`` is the stdio-transport
# sentinel (a local pipe has no remote address; treated loopback-equiv).
_LOOPBACK_ADDRS = frozenset({"127.0.0.1", "::1", "stdio-local"})

# Public sentinel for the stdio transport's remote_addr (re-exported so
# callers thread the SAME literal the whitelist recognizes).
STDIO_LOCAL_ADDR = "stdio-local"


# Decision sentinel values returned by check_request.
ACCEPT = "accept"
DENY_STALE_IAT = "stale_iat"
DENY_NONCE_REUSED = "nonce_reused"
DENY_STALE_AND_REUSED = "stale_iat_and_nonce_reused"
DENY_NON_LOOPBACK = "non_loopback"


class BearerReplayStore:
    """Thread-safe nonce store with TTL eviction + bounded LRU cap.

    Stateless across processes; per-process protection only. Loopback-
    only deployment per ADR-040-MCP-Auth — multi-process replay defense
    is DEFERRED to PLAN-090 (DPoP RFC 9449 implementation).

    Clock domain: WALL-CLOCK ns (``time.time_ns``) so the caller can
    reconcile token ``timestamp_ms`` (wall-clock) against the store's
    ``now_ns`` without a monotonic-vs-wall mismatch
    (PLAN-112-FOLLOWUP §3).
    """

    def __init__(
        self,
        bearer_token_max_age_ns: int = DEFAULT_BEARER_TOKEN_MAX_AGE_NS,
        skew_window_ns: int = SKEW_WINDOW_NS,
        maxsize: int = DEFAULT_MAXSIZE,
        clock_ns: Optional[object] = None,
    ) -> None:
        if bearer_token_max_age_ns <= 0:
            raise ValueError(
                f"bearer_token_max_age_ns must be >0, got {bearer_token_max_age_ns}"
            )
        if skew_window_ns <= 0:
            raise ValueError(
                f"skew_window_ns must be >0, got {skew_window_ns}"
            )
        if maxsize <= 0:
            raise ValueError(f"maxsize must be >0, got {maxsize}")
        self._max_age_ns: int = int(bearer_token_max_age_ns)
        self._skew_ns: int = int(skew_window_ns)
        self._maxsize: int = int(maxsize)
        # OrderedDict preserves insertion order so the oldest-inserted
        # nonce is the LRU eviction victim. nonce -> iat_ns.
        self._seen: "OrderedDict[str, int]" = OrderedDict()
        self._lock = RLock()
        # Injectable clock for testing — defaults to WALL-CLOCK
        # time.time_ns (PLAN-112-FOLLOWUP clock reconcile).
        self._clock_ns = clock_ns or time.time_ns

    def _now_ns(self) -> int:
        return int(self._clock_ns())

    def _evict_expired(self, now_ns: int) -> None:
        """Drop entries whose iat is older than bearer_token_max_age."""
        expired = [
            nonce
            for nonce, iat in self._seen.items()
            if abs(now_ns - iat) > self._max_age_ns
        ]
        for nonce in expired:
            self._seen.pop(nonce, None)

    def _evict_lru_overflow(self) -> None:
        """Evict oldest-inserted nonces until len <= maxsize (CWE-400)."""
        while len(self._seen) > self._maxsize:
            # popitem(last=False) removes the oldest-inserted entry.
            self._seen.popitem(last=False)

    def check_request(
        self,
        *,
        remote_addr: str,
        nonce: str,
        iat_ns: int,
    ) -> Tuple[str, Optional[str]]:
        """Atomically validate a bearer-token request.

        Returns ``(decision, reason)`` where:

        - ``decision`` is one of ``ACCEPT`` / ``DENY_STALE_IAT`` /
          ``DENY_NONCE_REUSED`` / ``DENY_STALE_AND_REUSED`` /
          ``DENY_NON_LOOPBACK``.
        - ``reason`` is the same string (or None on ACCEPT) — caller
          forwards verbatim into the audit emit field ``reason``.

        Order of checks (R2 iter-1 C1 — independent invariants):

        1. Loopback check first (rejects non-loopback regardless of token).
        2. Compute stale-flag and seen-flag INDEPENDENTLY.
        3. If both flags set → DENY_STALE_AND_REUSED.
        4. If only stale → DENY_STALE_IAT.
        5. If only seen → DENY_NONCE_REUSED.
        6. If neither → ACCEPT and atomic-insert nonce (LRU-capped).

        NOTE (PLAN-112-FOLLOWUP §3 ordering): the production caller
        (``dispatch.authenticate``) only invokes this AFTER
        ``verify_hmac`` + ``verify_timestamp_skew`` succeed, so an
        unauthenticated request can never reach the seen-set insert and
        therefore cannot poison/grow the store (CWE-770 DoS).
        """
        # Loopback gate (handler-entry fail-CLOSED).
        if remote_addr not in _LOOPBACK_ADDRS:
            return (DENY_NON_LOOPBACK, DENY_NON_LOOPBACK)

        # Nonce must be a non-empty string.
        if not isinstance(nonce, str) or not nonce:
            # Treat malformed-input as stale_iat (fail-CLOSED, no leak).
            return (DENY_STALE_IAT, DENY_STALE_IAT)
        if not isinstance(iat_ns, int):
            return (DENY_STALE_IAT, DENY_STALE_IAT)

        with self._lock:
            now_ns = self._now_ns()

            # Evict expired entries before deciding (keeps store bounded).
            self._evict_expired(now_ns)

            stale = abs(now_ns - iat_ns) > self._skew_ns
            seen = nonce in self._seen

            if stale and seen:
                return (DENY_STALE_AND_REUSED, DENY_STALE_AND_REUSED)
            if stale:
                return (DENY_STALE_IAT, DENY_STALE_IAT)
            if seen:
                return (DENY_NONCE_REUSED, DENY_NONCE_REUSED)

            # Atomic insert on accept — within the same lock context.
            # OrderedDict insert appends at the end (most-recent); LRU
            # overflow eviction drops oldest-inserted entries.
            self._seen[nonce] = int(iat_ns)
            self._evict_lru_overflow()
            return (ACCEPT, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._seen)


__all__ = [
    "BearerReplayStore",
    "SKEW_WINDOW_NS",
    "DEFAULT_BEARER_TOKEN_MAX_AGE_NS",
    "DEFAULT_MAXSIZE",
    "STDIO_LOCAL_ADDR",
    "ACCEPT",
    "DENY_STALE_IAT",
    "DENY_NONCE_REUSED",
    "DENY_STALE_AND_REUSED",
    "DENY_NON_LOOPBACK",
]
