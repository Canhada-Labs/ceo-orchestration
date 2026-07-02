"""PLAN-085 Wave C.3 — MCP bearer-token nonce + skew replay defense tests.

PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire UPDATE: the store clock was
reconciled from ``time.monotonic_ns`` to WALL-CLOCK ``time.time_ns`` so
the wall-clock token ``timestamp_ms`` reconciles (clock-domain fix).
``test_nonce_clock_monotonic`` is renamed/retargeted to assert the
wall-clock default. New cases cover the stdio-local whitelist, the
single-freshness-window reconcile, and the bounded-LRU cap.

Original 11 cases (all preserved; clock injection unchanged — they
inject a deterministic clock and never depend on the wall-clock vs
monotonic distinction except the renamed default-clock assertion):

  1. test_default_clock_is_wall_clock         — store uses time.time_ns (was monotonic)
  2. test_ttl_equals_max_age                  — nonce-store TTL == bearer_token_max_age
  3. test_non_loopback_rejected               — IPv4 external + IPv6 external both DENY
  4. test_separate_replay_audit_action        — distinct deny codes
  5. test_acceptable_loopback_v6              — ::1 accepted
  6. test_immediate_replay_same_nonce_denies  — R2-iter-1 truth table row 1
  7. test_stale_unseen_fresh_nonce_denies     — R2-iter-1 truth table row 2
  8. test_stale_seen_reused_nonce_denies      — R2-iter-1 truth table row 3
  9. test_fresh_unique_nonce_accepts          — R2-iter-1 truth table row 4
 10. test_atomic_insert_on_accept             — second call same nonce denies
 11. test_evict_expired_purges_old_nonces     — entries older than max_age dropped

New cases (PLAN-112-FOLLOWUP):
 12. test_stdio_local_accepts                 — "stdio-local" sentinel treated loopback
 13. test_single_freshness_window_from_auth   — default skew derived from auth._SKEW_MS
 14. test_lru_capacity_bound                  — unique-nonce flood bounded by maxsize
 15. test_lru_evicts_oldest_first            — eviction is LRU (oldest-inserted)

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation. NO time.sleep —
clock is injected via constructor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
_MCP_SERVER = REPO_ROOT / ".claude" / "scripts" / "mcp-server"
for _p in (_HOOKS, _MCP_SERVER):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _lib.testing import TestEnvContext  # noqa: E402


class _FakeClock:
    """Injectable wall-clock ``time_ns`` replacement."""

    def __init__(self, start_ns: int = 1_700_000_000_000_000_000) -> None:
        # Default start ~ a realistic wall-clock ns value (2023-ish) so
        # iat values derived from ms*1e6 land in the same magnitude.
        self.now_ns: int = int(start_ns)

    def __call__(self) -> int:
        return self.now_ns

    def advance(self, delta_ns: int) -> None:
        self.now_ns += int(delta_ns)


class TestMcpBearerNonceReplay(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        from _lib.mcp.bearer_replay import (
            BearerReplayStore,
            DEFAULT_BEARER_TOKEN_MAX_AGE_NS,
            SKEW_WINDOW_NS,
            ACCEPT,
            DENY_STALE_IAT,
            DENY_NONCE_REUSED,
            DENY_STALE_AND_REUSED,
            DENY_NON_LOOPBACK,
        )
        self.BearerReplayStore = BearerReplayStore
        self.DEFAULT_MAX_AGE_NS = DEFAULT_BEARER_TOKEN_MAX_AGE_NS
        self.SKEW_WINDOW_NS = SKEW_WINDOW_NS
        self.ACCEPT = ACCEPT
        self.DENY_STALE_IAT = DENY_STALE_IAT
        self.DENY_NONCE_REUSED = DENY_NONCE_REUSED
        self.DENY_STALE_AND_REUSED = DENY_STALE_AND_REUSED
        self.DENY_NON_LOOPBACK = DENY_NON_LOOPBACK
        self.clock = _FakeClock()
        self.store = BearerReplayStore(clock_ns=self.clock)

    # ------------------------------------------------------------------
    # Setup cases
    # ------------------------------------------------------------------

    def test_default_clock_is_wall_clock(self) -> None:
        """Default store uses time.time_ns (clock reconcile, NOT monotonic)."""
        import time as _time
        from _lib.mcp.bearer_replay import BearerReplayStore
        default_store = BearerReplayStore()
        # PLAN-112-FOLLOWUP clock reconcile: default ``_clock_ns`` must be
        # the WALL-CLOCK time.time_ns function so it reconciles with the
        # wall-clock token timestamp. Must NOT be monotonic_ns.
        self.assertIs(default_store._clock_ns, _time.time_ns)
        self.assertIsNot(default_store._clock_ns, _time.monotonic_ns)

    def test_ttl_equals_max_age(self) -> None:
        """Nonce-store TTL keyed on bearer_token_max_age, not skew window."""
        store = self.BearerReplayStore(
            bearer_token_max_age_ns=120 * 1_000_000_000,
            skew_window_ns=60 * 1_000_000_000,
            clock_ns=self.clock,
        )
        self.assertEqual(store._max_age_ns, 120 * 1_000_000_000)
        self.assertNotEqual(store._max_age_ns, store._skew_ns)

    def test_non_loopback_rejected(self) -> None:
        """IPv4 external + IPv6 external both DENY with non_loopback reason."""
        for addr in ("10.0.0.1", "192.168.1.1", "2001:db8::1", "fe80::1"):
            decision, reason = self.store.check_request(
                remote_addr=addr,
                nonce="any-nonce",
                iat_ns=self.clock.now_ns,
            )
            self.assertEqual(decision, self.DENY_NON_LOOPBACK, msg=addr)
            self.assertEqual(reason, self.DENY_NON_LOOPBACK)

    def test_separate_replay_audit_action(self) -> None:
        """Reject codes are distinct strings — caller emits separate actions."""
        self.assertNotEqual(self.DENY_NON_LOOPBACK, self.DENY_STALE_IAT)
        self.assertNotEqual(self.DENY_NON_LOOPBACK, self.DENY_NONCE_REUSED)
        self.assertNotEqual(self.DENY_STALE_IAT, self.DENY_NONCE_REUSED)
        self.assertNotEqual(self.DENY_STALE_IAT, self.DENY_STALE_AND_REUSED)
        self.assertNotEqual(self.DENY_NONCE_REUSED, self.DENY_STALE_AND_REUSED)

    def test_acceptable_loopback_v6(self) -> None:
        """::1 accepted as loopback."""
        decision, reason = self.store.check_request(
            remote_addr="::1",
            nonce="n-v6-loop",
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(decision, self.ACCEPT)

    # ------------------------------------------------------------------
    # R2-iter-1 C1 — 4-case mandatory truth table
    # ------------------------------------------------------------------

    def test_immediate_replay_same_nonce_denies(self) -> None:
        """Same nonce, fresh iat — DENY on nonce-reuse."""
        nonce = "test-nonce-1"
        d1, _ = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d1, self.ACCEPT)
        # Advance clock by 1s (still inside skew window).
        self.clock.advance(1_000_000_000)
        d2, reason = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d2, self.DENY_NONCE_REUSED)
        self.assertEqual(reason, self.DENY_NONCE_REUSED)

    def test_stale_unseen_fresh_nonce_denies(self) -> None:
        """Fresh nonce, stale iat (90s in the past) — DENY on stale_iat."""
        nonce = "test-nonce-fresh"
        stale_iat = self.clock.now_ns - 90 * 1_000_000_000
        d, reason = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=stale_iat,
        )
        self.assertEqual(d, self.DENY_STALE_IAT)
        self.assertEqual(reason, self.DENY_STALE_IAT)

    def test_stale_seen_reused_nonce_denies(self) -> None:
        """Reused nonce + stale iat — DENY reason=stale_iat_and_nonce_reused."""
        nonce = "test-nonce-replay"
        # First insert via accept.
        d1, _ = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d1, self.ACCEPT)
        # Now replay with stale iat AND same nonce.
        stale_iat = self.clock.now_ns - 90 * 1_000_000_000
        d2, reason = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=stale_iat,
        )
        self.assertEqual(d2, self.DENY_STALE_AND_REUSED)
        self.assertEqual(reason, self.DENY_STALE_AND_REUSED)

    def test_fresh_unique_nonce_accepts(self) -> None:
        """Fresh nonce + fresh iat — ACCEPT + atomic insert."""
        nonce = "fresh-unique-001"
        # iat slightly in the past (1s) → well within skew.
        d, reason = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns - 1_000_000_000,
        )
        self.assertEqual(d, self.ACCEPT)
        self.assertIsNone(reason)
        # Nonce now in store.
        self.assertEqual(len(self.store), 1)

    # ------------------------------------------------------------------
    # Additional safety cases
    # ------------------------------------------------------------------

    def test_atomic_insert_on_accept(self) -> None:
        """A second call with same nonce after accept always denies."""
        nonce = "atomic-test"
        d1, _ = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d1, self.ACCEPT)
        # Subsequent call with fresh iat AND same nonce → nonce_reused.
        self.clock.advance(500_000_000)  # +0.5s
        d2, _ = self.store.check_request(
            remote_addr="127.0.0.1",
            nonce=nonce,
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d2, self.DENY_NONCE_REUSED)

    def test_evict_expired_purges_old_nonces(self) -> None:
        """Entries older than bearer_token_max_age are evicted."""
        store = self.BearerReplayStore(
            bearer_token_max_age_ns=10 * 1_000_000_000,  # 10s
            skew_window_ns=60 * 1_000_000_000,
            clock_ns=self.clock,
        )
        # Insert nonce A at t0.
        d, _ = store.check_request(
            remote_addr="127.0.0.1",
            nonce="A",
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d, self.ACCEPT)
        self.assertEqual(len(store), 1)
        # Advance clock past max_age (10s + 5s buffer = 15s).
        self.clock.advance(15 * 1_000_000_000)
        # Insert a fresh nonce B at the new time — eviction sweep runs
        # before the decide; A must be purged.
        d, _ = store.check_request(
            remote_addr="127.0.0.1",
            nonce="B",
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(d, self.ACCEPT)
        # Store now has just B (A was evicted).
        self.assertEqual(len(store), 1)

    # ------------------------------------------------------------------
    # PLAN-112-FOLLOWUP new cases
    # ------------------------------------------------------------------

    def test_stdio_local_accepts(self) -> None:
        """``stdio-local`` sentinel is treated as loopback (not DENY)."""
        from _lib.mcp.bearer_replay import STDIO_LOCAL_ADDR
        self.assertEqual(STDIO_LOCAL_ADDR, "stdio-local")
        decision, reason = self.store.check_request(
            remote_addr="stdio-local",
            nonce="stdio-nonce-1",
            iat_ns=self.clock.now_ns,
        )
        self.assertEqual(decision, self.ACCEPT)
        self.assertIsNone(reason)
        # And it is NOT a non-loopback deny.
        self.assertNotEqual(decision, self.DENY_NON_LOOPBACK)

    def test_single_freshness_window_from_auth(self) -> None:
        """Default skew window derives from auth._SKEW_MS (single window)."""
        import auth  # type: ignore[import-not-found]
        from _lib.mcp.bearer_replay import SKEW_WINDOW_NS
        # auth._SKEW_MS is in ms; the store window is the same value in ns.
        self.assertEqual(SKEW_WINDOW_NS, int(auth._SKEW_MS) * 1_000_000)
        # And the default-constructed store uses that window.
        default_store = self.BearerReplayStore()
        self.assertEqual(default_store._skew_ns, int(auth._SKEW_MS) * 1_000_000)

    def test_lru_capacity_bound(self) -> None:
        """Unique-nonce flood is bounded by maxsize (CWE-400)."""
        cap = 5
        store = self.BearerReplayStore(
            bearer_token_max_age_ns=24 * 3600 * 1_000_000_000,
            skew_window_ns=60 * 1_000_000_000,
            maxsize=cap,
            clock_ns=self.clock,
        )
        # Insert 4*cap unique fresh nonces; len must never exceed cap.
        for i in range(cap * 4):
            d, _ = store.check_request(
                remote_addr="127.0.0.1",
                nonce=f"flood-{i}",
                iat_ns=self.clock.now_ns,
            )
            self.assertEqual(d, self.ACCEPT)
            self.assertLessEqual(len(store), cap)
        self.assertEqual(len(store), cap)

    def test_lru_evicts_oldest_first(self) -> None:
        """LRU eviction drops the oldest-inserted nonce first."""
        store = self.BearerReplayStore(
            bearer_token_max_age_ns=24 * 3600 * 1_000_000_000,
            skew_window_ns=60 * 1_000_000_000,
            maxsize=2,
            clock_ns=self.clock,
        )
        store.check_request(remote_addr="127.0.0.1", nonce="old", iat_ns=self.clock.now_ns)
        store.check_request(remote_addr="127.0.0.1", nonce="mid", iat_ns=self.clock.now_ns)
        # Third insert evicts "old" (oldest). len stays at 2.
        store.check_request(remote_addr="127.0.0.1", nonce="new", iat_ns=self.clock.now_ns)
        self.assertEqual(len(store), 2)
        # "old" was evicted → re-presenting it is ACCEPT (no longer seen),
        # which proves it left the store (NOT a nonce_reused DENY).
        d, _ = store.check_request(
            remote_addr="127.0.0.1", nonce="old", iat_ns=self.clock.now_ns
        )
        self.assertEqual(d, self.ACCEPT)
        # "new" is still present → re-presenting it DENIES on reuse.
        d2, _ = store.check_request(
            remote_addr="127.0.0.1", nonce="new", iat_ns=self.clock.now_ns
        )
        self.assertEqual(d2, self.DENY_NONCE_REUSED)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
