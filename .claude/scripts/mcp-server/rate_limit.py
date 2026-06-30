"""Per-client token-bucket rate limiter (ADR-042 §Auth.3).

Stdlib-only. In-memory per-process — no Redis, no memcached. The
framework operates at a scale where a single MCP server process
handles the full client fleet; ADR-040 precedent for in-memory deque
state applies here.

## Handler classes

Per ADR-042 §Auth.3 every handler maps to exactly one class:

- ``readonly``: ``list_skills``, ``get_skill``, ``list_agents``,
  ``list_pitfalls``, ``server.capabilities``. Default 60 req/min,
  burst 10.
- ``audit_read``: ``get_audit_log``. Default 30 req/min, burst 5.
- ``spawn``: ``spawn_agent``. Default 6 req/min, burst 2.

Per-client overrides live in ``.claude/settings.json`` under
``mcp_rate_limits.<client_id>.<class>`` as
``{"rpm": int, "burst": int}``. Missing keys fall back to class
defaults.

## Token bucket semantics

Classic token bucket:

- Bucket capacity == ``burst``.
- Refill rate == ``rpm / 60`` tokens per second, continuous (not
  discrete tick).
- :meth:`TokenBucket.try_consume` returns ``(True, 0)`` on success or
  ``(False, retry_after_ms)`` on denial. ``retry_after_ms`` is the
  integer milliseconds until a single token would next be available,
  useful for the ``Retry-After`` HTTP response header.

Thread-safety via :class:`threading.Lock`. Clock is injected via the
constructor so tests can feed deterministic values.

## Registry

Module-level ``_BUCKETS`` maps ``(client_id, handler_class)`` → bucket
instance. :func:`get_bucket` is memoized and thread-safe. Buckets
persist for the process lifetime; restart clears state.
"""

from __future__ import annotations

import threading
import time as _time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple


# ADR-042 §Auth.3 + ADR-042-AMEND-1 (PLAN-096) defaults.
DEFAULT_LIMITS: Dict[str, Tuple[int, int]] = {
    # handler_class: (rpm, burst)
    "readonly": (60, 10),
    "audit_read": (30, 5),
    "spawn": (6, 2),
    # PLAN-096 Wave C — Read-only ≤10/min/client (debate snapshot
    # immutable post-sentinel; matches plan §3.E.5 table).
    "debate_read": (10, 3),
    # PLAN-096 Wave D — cost-budget stub; same as readonly bucket
    # (no token spend, no LLM call; can be re-tuned in PLAN-102).
    "cost_budget": (30, 5),
}


# Audit-query sub-commands enumerated in
# .claude/plans/PLAN-096/wave-a-mcp-subset.md §2 (27 read-only methods).
# Listed inline for grep-ability + so static tools can verify the count
# matches the source enumeration at CI time.
_AUDIT_QUERY_METHODS: Tuple[str, ...] = (
    "audit_query.summary",
    "audit_query.by_skill",
    "audit_query.compliance",
    "audit_query.by_day",
    "audit_query.search",
    "audit_query.since",
    "audit_query.errors",
    "audit_query.stats",
    "audit_query.export",
    "audit_query.debate",
    "audit_query.plans",
    "audit_query.vetoes",
    "audit_query.benchmarks",
    "audit_query.lessons",
    "audit_query.metrics",
    "audit_query.health",
    "audit_query.tokens",
    "audit_query.claims",
    "audit_query.prune_restore_ratio",
    "audit_query.architect_outcomes",
    "audit_query.lessons_effectiveness",
    "audit_query.weekly_summary",
    "audit_query.spawn_stats",
    "audit_query.by_domain",
    "audit_query.fp_rate",
    "audit_query.case_summary",
    "audit_query.codex_writeguard_summary",
)


# Handler → class mapping. Used by server.py before calling
# :func:`get_bucket`. Unknown handlers route to "readonly" as a safe
# default (they shouldn't reach here — ACL catches them first).
HANDLER_CLASS: Dict[str, str] = {
    "list_skills": "readonly",
    "get_skill": "readonly",
    "list_agents": "readonly",
    "list_pitfalls": "readonly",
    "server.capabilities": "readonly",
    "get_audit_log": "audit_read",
    "spawn_agent": "spawn",
    # PLAN-096 Wave B (4 methods).
    "list_plans": "readonly",
    "get_plan": "readonly",
    "get_plan_acs": "readonly",
    "get_plan_dependencies": "readonly",
    # PLAN-096 Wave C.
    "get_debate_state": "debate_read",
    # PLAN-096 Wave D.
    "get_cost_budget": "cost_budget",
}


# PLAN-096 Wave A — register 27 audit_query methods under audit_read
# class. Kept in a dedicated loop so additions/removals stay grep-able.
for _m in _AUDIT_QUERY_METHODS:
    HANDLER_CLASS[_m] = "audit_read"


@dataclass
class _BucketState:
    """Internal token-bucket state (mutable, protected by lock)."""

    tokens: float
    last_refill_s: float


class TokenBucket:
    """Thread-safe token-bucket rate limiter.

    Args:
        rate_per_min: continuous refill rate (tokens per 60s).
        burst: maximum capacity. Also the initial token count.
        clock: callable returning monotonic seconds (injectable).
            Defaults to :func:`time.monotonic`.
    """

    def __init__(
        self,
        rate_per_min: int,
        burst: int,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if rate_per_min <= 0:
            raise ValueError(
                f"rate_per_min must be >0, got {rate_per_min}"
            )
        if burst <= 0:
            raise ValueError(f"burst must be >0, got {burst}")
        self._rate_per_s: float = float(rate_per_min) / 60.0
        self._burst: float = float(burst)
        self._clock: Callable[[], float] = clock or _time.monotonic
        self._lock = threading.Lock()
        now = self._clock()
        self._state = _BucketState(tokens=self._burst, last_refill_s=now)

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @property
    def rate_per_min(self) -> int:
        """Return the configured rate (tokens per minute)."""
        return int(round(self._rate_per_s * 60.0))

    @property
    def burst(self) -> int:
        """Return the configured burst / capacity."""
        return int(round(self._burst))

    def tokens_available(self) -> float:
        """Return the current token count after refilling.

        Mainly useful for diagnostics / tests. :meth:`try_consume` is the
        gate.
        """
        with self._lock:
            self._refill_locked()
            return self._state.tokens

    def try_consume(self, cost: int = 1) -> Tuple[bool, int]:
        """Attempt to consume ``cost`` tokens.

        Returns:
            ``(allowed, retry_after_ms)``. On allow, ``retry_after_ms``
            is 0. On deny, it is the integer milliseconds until enough
            tokens accumulate to grant a call of size ``cost`` —
            suitable for an HTTP ``Retry-After`` header (rounded up to
            at least 1ms when non-zero).
        """
        if cost <= 0:
            # Zero-cost calls always pass — ensures the probe path
            # (e.g. health check) cannot be blocked.
            return True, 0
        with self._lock:
            self._refill_locked()
            if self._state.tokens >= cost:
                self._state.tokens -= cost
                return True, 0
            # Compute wait time until bucket refills enough.
            deficit = cost - self._state.tokens
            if self._rate_per_s <= 0:
                # Defensive: constructor forbids this, but if it ever
                # happens report a large wait so callers don't loop.
                return False, 60_000
            seconds_needed = deficit / self._rate_per_s
            ms = int(seconds_needed * 1000.0) + 1
            if ms < 1:
                ms = 1
            return False, ms

    def reset(self) -> None:
        """Force-refill the bucket to capacity. Test / admin helper."""
        with self._lock:
            now = self._clock()
            self._state.tokens = self._burst
            self._state.last_refill_s = now

    # ------------------------------------------------------------------
    # Internals (caller holds ``self._lock``)
    # ------------------------------------------------------------------

    def _refill_locked(self) -> None:
        now = self._clock()
        elapsed = now - self._state.last_refill_s
        if elapsed <= 0:
            # Clock skew / monotonic paranoia: just update the anchor.
            self._state.last_refill_s = now
            return
        refilled = elapsed * self._rate_per_s
        self._state.tokens = min(self._burst, self._state.tokens + refilled)
        self._state.last_refill_s = now


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------


_BUCKETS: Dict[Tuple[str, str], TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()


def get_bucket(
    client_id: str,
    handler_class: str,
    *,
    overrides: Optional[Dict[str, Dict[str, int]]] = None,
    clock: Optional[Callable[[], float]] = None,
) -> TokenBucket:
    """Return the memoized bucket for ``(client_id, handler_class)``.

    Args:
        client_id: the registry key (16-hex-char opaque id).
        handler_class: one of ``"readonly" | "audit_read" | "spawn"``.
        overrides: the ``mcp_rate_limits`` dict from
            ``.claude/settings.json`` (or a sub-dict keyed by class).
            Falls back to :data:`DEFAULT_LIMITS`.
        clock: test-only injectable clock.

    Unknown handler classes fall back to ``"readonly"`` defaults (safest
    low-volume class).
    """
    key = (client_id, handler_class)
    with _BUCKETS_LOCK:
        existing = _BUCKETS.get(key)
        if existing is not None:
            return existing
        rpm, burst = _resolve_limits(client_id, handler_class, overrides)
        bucket = TokenBucket(rate_per_min=rpm, burst=burst, clock=clock)
        _BUCKETS[key] = bucket
        return bucket


def reset_registry() -> None:
    """Drop all buckets. Test helper."""
    with _BUCKETS_LOCK:
        _BUCKETS.clear()


def _resolve_limits(
    client_id: str,
    handler_class: str,
    overrides: Optional[Dict[str, Dict[str, int]]],
) -> Tuple[int, int]:
    """Resolve (rpm, burst) given optional overrides.

    Overrides shape:
        ``{ "<client_id>": { "<class>": {"rpm": int, "burst": int}, ... }, ... }``

    Missing at any level falls through to :data:`DEFAULT_LIMITS`.
    Negative / zero values are rejected; we fall back to defaults.
    """
    default_rpm, default_burst = DEFAULT_LIMITS.get(
        handler_class, DEFAULT_LIMITS["readonly"]
    )
    if not isinstance(overrides, dict):
        return default_rpm, default_burst
    per_client = overrides.get(client_id)
    if not isinstance(per_client, dict):
        return default_rpm, default_burst
    per_class = per_client.get(handler_class)
    if not isinstance(per_class, dict):
        return default_rpm, default_burst
    rpm_raw = per_class.get("rpm", default_rpm)
    burst_raw = per_class.get("burst", default_burst)
    try:
        rpm = int(rpm_raw)
        burst = int(burst_raw)
    except (TypeError, ValueError):
        return default_rpm, default_burst
    if rpm <= 0 or burst <= 0:
        return default_rpm, default_burst
    return rpm, burst


def handler_to_class(handler_name: str) -> str:
    """Return the handler class for ``handler_name``.

    Falls back to ``"readonly"`` for unknown handlers (defense-in-depth;
    ACL should already have rejected them).
    """
    return HANDLER_CLASS.get(handler_name, "readonly")


__all__ = [
    "TokenBucket",
    "DEFAULT_LIMITS",
    "HANDLER_CLASS",
    "get_bucket",
    "reset_registry",
    "handler_to_class",
]
