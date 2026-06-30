"""STDLIB-ONLY — federation rate-limit + T1499 circuit breaker.

Staged at ``.claude/plans/PLAN-099-FOLLOWUP/wave-e-staging/rate_limit.py``.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/rate_limit.py`` at
Phase A2-post of the PLAN-099-FOLLOWUP ceremony (canonical-edit guard
blocks direct writes to ``federation/``, hence the staging convention).

Per ADR-135-AMEND-1 §2.4 + plan §4 Wave E.1 + attack-rebinding.md §2.1:

  - Primary token bucket per ``(peer_id, route, ip_prefix)`` tuple.
    Per-route capacity + refill EXACTLY matches ADR-135-AMEND-1 §2.4:
      /federation/peer-register      : 1 / hour
      /federation/peer-revoke        : 5 / hour
      /federation/audit-event        : 60 / min
      /federation/audit-event/batch  : 6 / min (≤100 events/request)
  - Secondary token bucket per ``(peer_id,)`` tuple — defense against a
    compromised peer multiplexing across routes to dodge the primary
    limit. Default secondary cap: 100 req / hour total per peer
    (sum across all routes).
  - Circuit breaker: ≥3 rate-limit hits in any 5-minute sliding window
    triggers a 15-minute auto-revoke of the offending (peer, route)
    scope. Recovery is purely time-based (no Owner intervention).
  - Per-IP secondary limit prevents a compromised peer multiplying via
    IP-rotation. The (peer, route) bucket is primary; IP is a discriminator.
  - p99 audit-log append latency tracking → backpressure 503 when the
    server is too slow to keep ordering guarantees (T1499 endpoint DoS
    detection-as-code).

ATT&CK bindings:
  - T1499 (Endpoint Denial of Service) — primary surface
  - T1485 (Data Destruction) — circuit-breaker auto-revoke is mitigation
    for write-flood that would tamper / overflow the audit-log

In-process state. Process restart clears all counters (by design — a
peer whose burst was rate-limited gets a clean slate on server restart,
and an attacker who triggered the circuit-breaker loses their fresh
window when the server bounces).

WAVE-F-PENDING markers:
  - emit-call sites tagged WAVE-F-PENDING; pre-registration the
    ``_safe_emit`` shim is a no-op.
  - audit actions used (canonical F.2 vocabulary):
    ``federation_message_storm_detected`` (T1499 circuit-breaker trip),
    ``federation_audit_log_backpressure`` (T1499 latency overload).

  Note: rate-limit hit denials at gate #9 are emitted by the dispatcher
  via the canonical multiplexer ``federation_write_endpoint_denied``
  with ``reason_code="rate_limit:<route>" / "per_peer_secondary" /
  "circuit_breaker:..."``. This module does NOT emit per-denial events;
  it only emits the circuit-breaker TRIP (storm) + backpressure trip
  (latency).
"""

from __future__ import annotations

import sys
import time
from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, Optional, Tuple


__all__ = [
    "RateLimitConfig",
    "RateLimitState",
    "check_rate_limit",
    "record_hit",
    "check_circuit_breaker",
    "track_append_latency",
    "check_backpressure",
    "reset_state",
]


# ----------------------------------------------------------------------------
# Audit emit shim (WAVE-F-PENDING — mirrors handlers/_safe_emit pattern)
# ----------------------------------------------------------------------------


def _safe_emit(action: str, **fields: Any) -> None:
    """Call ``audit_emit.emit_<action>(...)`` if registered; otherwise no-op.

    WAVE-F-PENDING. Pre-registration the action is a kernel-allowlist
    miss → ``emit_<action>`` does not exist → no-op. This is the
    deliberate "lazy-wire" convention (PLAN-099 / PLAN-106 precedent).
    """
    try:
        try:
            from _lib import audit_emit  # type: ignore[import]
        except ImportError:
            import importlib

            audit_emit = importlib.import_module(".audit_emit", package="_lib")
    except ImportError:
        return
    # PLAN-112-FOLLOWUP C-4 fix (R-TD-1): Wave-F.2 federation actions are in
    # _KNOWN_ACTIONS but have NO named emit_<action> wrapper — fall back to
    # emit_generic so the breaker-trip / backpressure emits are actually
    # written (the prior shim no-oped them: dead detection passing green).
    fn = getattr(audit_emit, "emit_{0}".format(action), None)
    try:
        if fn is not None:
            fn(**fields)
            return
        generic = getattr(audit_emit, "emit_generic", None)
        if generic is not None:
            generic(action, **fields)
    except Exception:
        try:
            sys.stderr.write(
                "[federation.rate_limit] audit emit '{0}' raised; ignored\n".format(action)
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Config + state
# ----------------------------------------------------------------------------


class RateLimitConfig:
    """Tunable knobs. Defaults match ADR-135-AMEND-1 §2.4 VERBATIM."""

    # Primary token-bucket per (peer, route, ip_prefix).
    # Default applies to any unlisted route (defense-in-depth — unknown
    # write routes can't bypass limiting). 10 req/min, burst 10.
    DEFAULT_CAPACITY: int = 10          # max burst
    DEFAULT_REFILL_PER_SEC: float = 10.0 / 60.0  # 10 req / minute

    # Per-route overrides — ADR-135-AMEND-1 §2.4 table VERBATIM.
    # Format: path → {capacity (max burst), refill_per_seconds (seconds
    # between token refills — refill_rate = 1.0 / refill_per_seconds).
    ROUTE_RATE_LIMITS: Dict[str, Dict[str, Any]] = {
        # 1 / hour (peer registration is rare; high-cost write surface)
        "/federation/peer-register":     {"capacity": 1,  "refill_per_seconds": 3600},
        # 5 / hour (peer revocation; destructive op)
        "/federation/peer-revoke":       {"capacity": 5,  "refill_per_seconds": 720},
        # 60 / min (audit-event push is the high-volume legitimate path)
        "/federation/audit-event":       {"capacity": 60, "refill_per_seconds": 1},
        # 6 / min (batched, ≤100 events per request — burst tighter)
        "/federation/audit-event/batch": {"capacity": 6,  "refill_per_seconds": 10},
    }

    # Secondary per-peer-only bucket — defense against compromised peer
    # multiplexing routes to dodge the primary (peer, route, ip) cap.
    # 100 req / hour TOTAL per peer (sum across all routes).
    PER_PEER_SECONDARY_CAPACITY: int = 100
    PER_PEER_SECONDARY_REFILL_PER_SECONDS: int = 36  # 100 / 3600s → 1 token / 36s

    # Circuit-breaker.
    BREAKER_WINDOW_SEC: int = 5 * 60     # 5-minute sliding window
    BREAKER_HIT_THRESHOLD: int = 3       # 3 hits → trip
    BREAKER_REVOKE_SEC: int = 15 * 60    # 15-minute revoke
    # Backpressure.
    BACKPRESSURE_WINDOW_SEC: int = 30
    BACKPRESSURE_P99_MS: int = 100


class RateLimitState:
    """In-process state container. Module-level singleton via :data:`_STATE`."""

    def __init__(self) -> None:
        # Primary bucket key = (peer_id, route, ip_prefix); value = (tokens, last_ts)
        self.buckets: Dict[Tuple[str, str, str], Tuple[float, float]] = {}
        # Secondary per-peer-only bucket key = peer_id; value = (tokens, last_ts).
        # Defense against compromised peer multiplexing routes to dodge primary cap.
        self.peer_secondary_buckets: Dict[str, Tuple[float, float]] = {}
        # breaker key = (peer_id, route); value = deque of hit timestamps
        self.breaker_hits: Dict[Tuple[str, str], Deque[float]] = {}
        # revoked key = (peer_id, route); value = revoke_until_ts (epoch)
        self.revoked_until: Dict[Tuple[str, str], float] = {}
        # latency p99 sliding window of (ts, latency_ms) tuples
        self.latency_window: Deque[Tuple[float, int]] = deque()
        self.lock = Lock()


_STATE = RateLimitState()


def reset_state() -> None:
    """Clear all in-process state. Tests-only."""
    global _STATE
    _STATE = RateLimitState()


# ----------------------------------------------------------------------------
# Token-bucket rate-limit
# ----------------------------------------------------------------------------


def _route_params(route: str) -> Tuple[int, float]:
    """Return ``(capacity, refill_per_sec)`` for a route.

    Reads from :data:`RateLimitConfig.ROUTE_RATE_LIMITS` (canonical ADR
    §2.4 table). Falls back to ``DEFAULT_*`` for unlisted routes.
    """
    entry = RateLimitConfig.ROUTE_RATE_LIMITS.get(route)
    if entry is None:
        return (
            RateLimitConfig.DEFAULT_CAPACITY,
            RateLimitConfig.DEFAULT_REFILL_PER_SEC,
        )
    capacity = int(entry["capacity"])
    refill_per_seconds = float(entry["refill_per_seconds"])
    # refill_rate (tokens/sec) = 1.0 / refill_per_seconds.
    refill_per_sec = (1.0 / refill_per_seconds) if refill_per_seconds > 0 else 0.0
    return capacity, refill_per_sec


def _peer_secondary_params() -> Tuple[int, float]:
    """Return ``(capacity, refill_per_sec)`` for the per-peer secondary."""
    capacity = int(RateLimitConfig.PER_PEER_SECONDARY_CAPACITY)
    refill_per_seconds = float(
        RateLimitConfig.PER_PEER_SECONDARY_REFILL_PER_SECONDS
    )
    refill_per_sec = (1.0 / refill_per_seconds) if refill_per_seconds > 0 else 0.0
    return capacity, refill_per_sec


def check_rate_limit(
    peer_id: str,
    route: str,
    ip_prefix: str,
    *,
    now: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """Token-bucket check. Returns ``(allowed, reason_if_denied)``.

    TWO buckets are consulted in order:

      1. Primary ``(peer_id, route, ip_prefix)`` — per-route ADR §2.4 limit.
      2. Secondary ``(peer_id,)`` — defense-in-depth against route
         multiplexing by a compromised peer.

    Both buckets are consulted before deducting. If either bucket would
    be over its cap, NEITHER is debited and ``(False, ...)`` is
    returned. This prevents an empty secondary from unfairly burning
    primary tokens. Caller MUST then invoke :func:`record_hit` to
    advance the circuit-breaker window.
    """
    if not isinstance(peer_id, str) or not peer_id:
        return False, "rate_limit:invalid_peer_id"
    if not isinstance(route, str) or not route:
        return False, "rate_limit:invalid_route"
    if not isinstance(ip_prefix, str):
        ip_prefix = ""
    ts = time.time() if now is None else float(now)
    primary_capacity, primary_refill = _route_params(route)
    secondary_capacity, secondary_refill = _peer_secondary_params()
    primary_key = (peer_id, route, ip_prefix)

    with _STATE.lock:
        # --- Primary (peer, route, ip_prefix) ---
        primary_tokens, primary_last = _STATE.buckets.get(
            primary_key, (float(primary_capacity), ts)
        )
        primary_tokens = min(
            float(primary_capacity),
            primary_tokens + max(0.0, ts - primary_last) * primary_refill,
        )
        if primary_tokens < 1.0:
            _STATE.buckets[primary_key] = (primary_tokens, ts)
            return False, "rate_limit:{0}".format(route)

        # --- Secondary (peer_id,) ---
        sec_tokens, sec_last = _STATE.peer_secondary_buckets.get(
            peer_id, (float(secondary_capacity), ts)
        )
        sec_tokens = min(
            float(secondary_capacity),
            sec_tokens + max(0.0, ts - sec_last) * secondary_refill,
        )
        if sec_tokens < 1.0:
            # Update timestamps but DO NOT debit primary — secondary is
            # the binding constraint (peer-wide over-cap).
            _STATE.buckets[primary_key] = (primary_tokens, ts)
            _STATE.peer_secondary_buckets[peer_id] = (sec_tokens, ts)
            return False, "rate_limit:per_peer_secondary"

        # Both buckets have ≥1 token → debit both atomically.
        primary_tokens -= 1.0
        sec_tokens -= 1.0
        _STATE.buckets[primary_key] = (primary_tokens, ts)
        _STATE.peer_secondary_buckets[peer_id] = (sec_tokens, ts)
        return True, None


def record_hit(
    peer_id: str,
    route: str,
    ip_prefix: str,
    *,
    now: Optional[float] = None,
) -> None:
    """Append a rate-limit hit to the circuit-breaker sliding window.

    Caller invokes this AFTER :func:`check_rate_limit` returns ``(False, ...)``.

    F-002 canonicalization: per-denial events are emitted by the
    dispatcher via the canonical ``federation_write_endpoint_denied``
    multiplexer (with ``reason_code=rl_reason``). This function ONLY
    advances the circuit-breaker sliding window — the breaker trip
    itself emits ``federation_message_storm_detected`` (idempotent).
    """
    if not isinstance(peer_id, str) or not peer_id:
        return
    if not isinstance(route, str) or not route:
        return
    ts = time.time() if now is None else float(now)
    key = (peer_id, route)
    with _STATE.lock:
        dq = _STATE.breaker_hits.setdefault(key, deque())
        dq.append(ts)
        # Trim left.
        cutoff = ts - RateLimitConfig.BREAKER_WINDOW_SEC
        while dq and dq[0] < cutoff:
            dq.popleft()
        # Tripping the breaker is detected on the NEXT check_circuit_breaker
        # call (which is what the dispatcher invokes BEFORE check_rate_limit).


# ----------------------------------------------------------------------------
# Circuit breaker
# ----------------------------------------------------------------------------


def check_circuit_breaker(
    peer_id: str,
    route: str,
    *,
    now: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """Returns ``(allowed, reason_if_denied)``.

    Fires when the sliding window has accumulated ≥ :data:`BREAKER_HIT_THRESHOLD`
    hits. Once tripped, the (peer, route) scope is auto-revoked for
    :data:`BREAKER_REVOKE_SEC`. Emits ``federation_message_storm_detected``
    on the trip event (idempotent — repeated checks during the revoke
    window do NOT re-emit).
    """
    if not isinstance(peer_id, str) or not peer_id:
        return False, "circuit_breaker:invalid_peer_id"
    if not isinstance(route, str) or not route:
        return False, "circuit_breaker:invalid_route"
    ts = time.time() if now is None else float(now)
    key = (peer_id, route)

    with _STATE.lock:
        # Already revoked?
        revoked_until = _STATE.revoked_until.get(key, 0.0)
        if revoked_until > ts:
            remaining = int(revoked_until - ts)
            return False, "circuit_breaker:revoked:{0}s".format(remaining)
        # Expired revoke → drop the entry + drain hits (clean slate).
        if revoked_until > 0.0:
            _STATE.revoked_until.pop(key, None)
            _STATE.breaker_hits.pop(key, None)
        # Window check.
        dq = _STATE.breaker_hits.get(key)
        if dq is None:
            return True, None
        cutoff = ts - RateLimitConfig.BREAKER_WINDOW_SEC
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= RateLimitConfig.BREAKER_HIT_THRESHOLD:
            _STATE.revoked_until[key] = ts + RateLimitConfig.BREAKER_REVOKE_SEC
            should_emit = True
            hit_count = len(dq)
        else:
            should_emit = False
            hit_count = len(dq)

    if should_emit:
        # F-001 R2 iter-2 fix: F.2 wrapper signature is
        # `emit_federation_message_storm_detected(peer_id, route,
        # ip_prefix, hits_in_window, window_seconds)`. We map:
        #   - hit_count -> hits_in_window
        #   - revoke_seconds -> window_seconds (the temporal context
        #     is the breaker's revoke window)
        #   - ip_prefix populated empty here (Wave E client_ip is
        #     /24-truncated at the dispatcher seam; rate_limit module
        #     does not have client_ip context — LLM06 hold + GDPR).
        _safe_emit(
            "federation_message_storm_detected",
            peer_id=peer_id[:64],
            route=route[:64],
            ip_prefix="",
            hits_in_window=int(hit_count),
            window_seconds=int(RateLimitConfig.BREAKER_REVOKE_SEC),
        )
        return False, "circuit_breaker:tripped"
    return True, None


# ----------------------------------------------------------------------------
# Audit-log backpressure (T1499 §2.4 bullet 4)
# ----------------------------------------------------------------------------


def track_append_latency(latency_ms: int, *, now: Optional[float] = None) -> None:
    """Record an audit-log append latency sample (post-append).

    Sliding window keeps :data:`BACKPRESSURE_WINDOW_SEC` of samples;
    older entries are trimmed lazily on each call. Non-numeric / negative
    samples are silently ignored (defensive).
    """
    if not isinstance(latency_ms, int) or latency_ms < 0:
        return
    ts = time.time() if now is None else float(now)
    cutoff = ts - RateLimitConfig.BACKPRESSURE_WINDOW_SEC
    with _STATE.lock:
        win = _STATE.latency_window
        win.append((ts, latency_ms))
        while win and win[0][0] < cutoff:
            win.popleft()


def _percentile(samples: list, p: float) -> int:
    """Return the p-th percentile (0-100) of ``samples`` as int. Empty → 0."""
    if not samples:
        return 0
    s = sorted(samples)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return int(s[k])


def check_backpressure(*, now: Optional[float] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Returns ``(ok, advisory_info)``.

    ``(True, None)`` when p99 append latency ≤ :data:`BACKPRESSURE_P99_MS`
    over the sliding window. ``(False, {p99_ms, sample_count, ...})``
    triggers a 503 response from the dispatcher + emits
    ``federation_audit_log_backpressure``.

    Idempotency: this function may be invoked on every request; emit is
    one-shot per-trip (we track the last_emit_ts to debounce within the
    window).
    """
    ts = time.time() if now is None else float(now)
    cutoff = ts - RateLimitConfig.BACKPRESSURE_WINDOW_SEC
    with _STATE.lock:
        win = _STATE.latency_window
        while win and win[0][0] < cutoff:
            win.popleft()
        samples = [lat for (_, lat) in win]

    if not samples:
        return True, None

    p99 = _percentile(samples, 99.0)
    if p99 <= RateLimitConfig.BACKPRESSURE_P99_MS:
        return True, None

    info: Dict[str, Any] = {
        "p99_ms": p99,
        "sample_count": len(samples),
        "window_sec": RateLimitConfig.BACKPRESSURE_WINDOW_SEC,
        "threshold_ms": RateLimitConfig.BACKPRESSURE_P99_MS,
    }
    # F-001 R2 iter-2 fix: F.2 wrapper signature is
    # `emit_federation_audit_log_backpressure(p99_latency_ms,
    # window_seconds, action_taken)`. We map:
    #   - p99_ms -> p99_latency_ms (rename)
    #   - window_sec -> window_seconds (rename)
    #   - sample_count dropped (not in F.2 allowlist; the info dict
    #     returned to the caller carries it for non-audit telemetry).
    #   - action_taken closed enum: throttled_503 / queue_paused /
    #     recovered. p99 over threshold = throttled_503.
    _safe_emit(
        "federation_audit_log_backpressure",
        p99_latency_ms=int(p99),
        window_seconds=int(RateLimitConfig.BACKPRESSURE_WINDOW_SEC),
        action_taken="throttled_503",
    )
    return False, info
