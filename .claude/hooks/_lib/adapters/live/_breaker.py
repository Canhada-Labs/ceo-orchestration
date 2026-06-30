"""Per-provider circuit breaker — ADR-040 §2.

Three-state breaker (closed → open → half_open → {closed, open}) with a
sliding failure window. Thread-safe via :class:`threading.Lock`. The
clock is injected (callable returning monotonic seconds) so tests can
drive deterministic state transitions without :mod:`time.sleep`.

Failure semantics (ADR-040 §2):

- **Transient failures** (5xx, 429, timeout, connection-refused) count
  toward threshold. ``record_failure(reason="server_error")`` etc.
- **Permanent failures** (``auth_permanent``) open the breaker
  IMMEDIATELY regardless of count. This protects against a key-rotation
  in flight + retry storm.
- **Parse errors** do NOT count — they are prompt-triggered (potential
  DoS surface) and would let an adversary open the breaker by malformed
  responses they cause.

The breaker is per (provider, instance) — the adapter ``__init__``
constructs one. There is no global breaker registry; each
``ClaudeLiveAdapter()`` etc. carries its own.
"""

from __future__ import annotations

import threading
import time as _time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Deque, Optional, Tuple

from ... import audit_emit  # noqa: E402  (relative: _lib/adapters/live → _lib)


class BreakerState(str, Enum):
    """Closed = pass through. Open = fail-fast. Half-open = single probe."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# Reason strings that open the breaker IMMEDIATELY irrespective of
# current failure count. ADR-040 §2 row "auth_permanent".
_PERMANENT_OPEN_REASONS = frozenset({"auth_permanent"})

# Reasons that do NOT count toward threshold (prompt-triggered DoS guard).
_NON_COUNTING_REASONS = frozenset({"parse_error", "scope_misconfigured", "invalid_policy"})

# Module-level test-only clock override. Chaos tests that don't own
# breaker construction (adapter builds its own) set this to a float
# to freeze the clock across ALL breaker instances. Set to None to
# fall back to the instance-level override or the injected clock.
# Never touched in production paths.
_now_override: Optional[float] = None


@dataclass(frozen=True)
class BreakerSnapshot:
    """Read-only view of breaker state — handy for audit emission."""

    state: str  # "closed" | "open" | "half_open"
    failures_in_window: int
    opened_at: Optional[float]  # monotonic seconds; None if not open


class CircuitBreaker:
    """Thread-safe sliding-window circuit breaker per ADR-040 §2.

    Args:
        threshold: failure count within ``window_s`` that opens breaker.
        window_s: sliding window in seconds.
        half_open_s: how long after opening before allowing a probe.
        clock: callable returning monotonic seconds (injectable for tests).
            Defaults to :func:`time.monotonic`.

    Example::

        b = CircuitBreaker(threshold=5, window_s=30, half_open_s=60)
        for _ in range(5):
            b.record_failure("server_error")
        assert b.state == BreakerState.OPEN
        assert not b.should_allow()
    """

    def __init__(
        self,
        *,
        threshold: int = 5,
        window_s: int = 30,
        half_open_s: int = 60,
        clock: Optional[Callable[[], float]] = None,
        provider: str = "",
    ) -> None:
        if threshold < 2:
            raise ValueError(f"threshold must be >=2, got {threshold}")
        if window_s <= 0 or half_open_s <= 0:
            raise ValueError("window_s and half_open_s must be positive")
        self._threshold = int(threshold)
        self._window_s = float(window_s)
        self._half_open_s = float(half_open_s)
        self._provider = str(provider)
        self._clock: Callable[[], float] = clock or _time.monotonic
        # Test-only override: attribute-based clock injection for chaos
        # tests that don't own the breaker construction (adapter builds
        # its own). Set to a float to freeze the clock; set to None to
        # fall back to ``self._clock``. Never used in production.
        self._now_override: Optional[float] = None
        self._lock = threading.Lock()

        self._state: BreakerState = BreakerState.CLOSED
        # Deque of (timestamp, reason). Pruned on every record/should_allow.
        self._failures: Deque[Tuple[float, str]] = deque()
        self._opened_at: Optional[float] = None
        # Half-open probe is one-shot: True means "probe permitted, not
        # yet consumed". Once consumed it flips False until success or
        # failure resolves the state.
        self._probe_available: bool = False

    def _now(self) -> float:
        """Return current time.

        Precedence (tests only): module-level ``_now_override`` >
        instance-level ``self._now_override`` > injected ``self._clock``.
        """
        mod_override = globals().get("_now_override")
        if mod_override is not None:
            return float(mod_override)
        if self._now_override is not None:
            return self._now_override
        return self._clock()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @property
    def state(self) -> BreakerState:
        """Current breaker state.

        Reads are advisory — :meth:`should_allow` is the gate.
        """
        with self._lock:
            self._refresh_state_locked()
            return self._state

    def snapshot(self) -> BreakerSnapshot:
        """Return a frozen point-in-time view (audit-safe)."""
        with self._lock:
            self._refresh_state_locked()
            return BreakerSnapshot(
                state=self._state.value,
                failures_in_window=len(self._failures),
                opened_at=self._opened_at,
            )

    def should_allow(self) -> bool:
        """Return True iff the next call should be issued.

        - CLOSED → always True.
        - OPEN → False until ``half_open_s`` elapsed since opening,
          at which point we transition to HALF_OPEN and return True
          EXACTLY ONCE (the probe).
        - HALF_OPEN → True the first call, then False until
          :meth:`record_success` or :meth:`record_failure` resolves.
        """
        with self._lock:
            self._refresh_state_locked()
            if self._state == BreakerState.CLOSED:
                return True
            if self._state == BreakerState.OPEN:
                return False
            # HALF_OPEN: allow probe exactly once
            if self._probe_available:
                self._probe_available = False
                return True
            return False

    def record_failure(self, reason: str = "server_error") -> None:
        """Note a failure. May open the breaker.

        Args:
            reason: classification per ADR-040 §2. Permanent reasons
                (``auth_permanent``) open the breaker immediately;
                non-counting reasons (``parse_error``,
                ``scope_misconfigured``, ``invalid_policy``) are
                ignored entirely.
        """
        with self._lock:
            now = self._now()
            self._refresh_state_locked()

            if reason in _NON_COUNTING_REASONS:
                # Do not count, do not transition. This protects against
                # adversarial parse_error spam opening the breaker.
                return

            if reason in _PERMANENT_OPEN_REASONS:
                self._open_locked(now)
                return

            self._failures.append((now, reason))
            self._prune_window_locked(now)

            if self._state == BreakerState.HALF_OPEN:
                # Probe failed → re-open and reset 60s clock
                self._open_locked(now)
                return

            if (
                self._state == BreakerState.CLOSED
                and len(self._failures) >= self._threshold
            ):
                self._open_locked(now)

    def record_success(self) -> None:
        """Note a success. Closes a HALF_OPEN breaker; resets failure deque."""
        with self._lock:
            self._refresh_state_locked()
            if self._state == BreakerState.HALF_OPEN:
                self._state = BreakerState.CLOSED
                self._opened_at = None
                self._probe_available = False
                self._failures.clear()
                # PLAN-114 F-1-1.8-c6fe879b — symmetric close event
                # (ADR-040 §2). Fail-open like emit_breaker_opened.
                try:
                    audit_emit.emit_breaker_closed(
                        provider=self._provider,
                        from_state="half_open",
                    )
                except Exception:  # pragma: no cover — audit is fail-open
                    pass
                return
            if self._state == BreakerState.CLOSED:
                # Slow-drain: do not touch counters mid-window — the
                # sliding window is the load-bearing pruner.
                return
            # OPEN + success ⇒ unreachable (should_allow blocked the
            # call). If it happens (race), close.
            self._state = BreakerState.CLOSED
            self._opened_at = None
            self._probe_available = False
            self._failures.clear()
            # PLAN-114 F-1-1.8-c6fe879b — close event for the OPEN race path.
            try:
                audit_emit.emit_breaker_closed(
                    provider=self._provider,
                    from_state="open",
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass

    def reset(self) -> None:
        """Force-close the breaker. Used for tests + admin escape hatch."""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._opened_at = None
            self._probe_available = False
            self._failures.clear()
            # PLAN-114 F-1-1.8-c6fe879b — close event for the admin/reset path.
            try:
                audit_emit.emit_breaker_closed(
                    provider=self._provider,
                    from_state="reset",
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass

    # ------------------------------------------------------------------
    # Internals — caller MUST hold ``self._lock``
    # ------------------------------------------------------------------

    def _open_locked(self, now: float) -> None:
        self._state = BreakerState.OPEN
        self._opened_at = now
        self._probe_available = False
        # Keep failure history for audit; window pruner cleans it next pass.
        # Emit audit event (ADR-040 §2.4 + §7 — Gap #4 fix closing Session 22).
        # Fail-open: any emission exception never breaks breaker state machine.
        try:
            audit_emit.emit_breaker_opened(
                provider=self._provider,
                failures_in_window=len(self._failures),
                threshold=self._threshold,
                reason="server_error",
            )
        except Exception:  # pragma: no cover — audit is fail-open
            pass

    def _prune_window_locked(self, now: float) -> None:
        cutoff = now - self._window_s
        while self._failures and self._failures[0][0] < cutoff:
            self._failures.popleft()

    def _refresh_state_locked(self) -> None:
        """Maybe transition OPEN→HALF_OPEN if half_open_s elapsed."""
        if self._state != BreakerState.OPEN or self._opened_at is None:
            return
        now = self._now()
        if (now - self._opened_at) >= self._half_open_s:
            self._state = BreakerState.HALF_OPEN
            self._probe_available = True
            # Clear failure deque — fresh start for the probe window.
            self._failures.clear()


__all__ = ["CircuitBreaker", "BreakerState", "BreakerSnapshot"]
