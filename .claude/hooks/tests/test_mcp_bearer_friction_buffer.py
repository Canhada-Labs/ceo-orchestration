"""PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — friction buffer unit tests.

Covers the non-blocking buffer + retry-window dedup + drain contract
(AC5 + AC6) at the module level (the integration wire-up is exercised
in .claude/scripts/mcp-server/tests/test_dispatch_bearer_replay_wire.py).

  - observe_auth_failure enqueues WITHOUT emitting (non-blocking).
  - retry-window dedup: same (client_id, nonce) within window enqueues
    once; distinct keys each enqueue.
  - pre-parse branches get a stable dedup key via the token-hash
    sentinel (no client_id/nonce).
  - drain emits one event per buffered record (no-loss) and clears the
    buffer.
  - bounded deque cannot grow past maxlen under a flood.

Discipline: stdlib-only, Python >= 3.9, TestEnvContext isolation,
CEO_AUDIT_SYNC_MODE=1.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


class TestFrictionBuffer(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        from _lib import mcp_bearer_friction
        self.mf = mcp_bearer_friction
        self.mf._reset_state_for_test()

    def tearDown(self) -> None:
        self.mf._reset_state_for_test()
        super().tearDown()

    def test_observe_is_non_blocking_no_emit(self) -> None:
        """observe_auth_failure buffers but does NOT emit on its own."""
        enq = self.mf.observe_auth_failure(
            mcp_server="codex",
            failure_reason="auth_hmac_invalid",
            client_id="c1",
            nonce="n1",
        )
        self.assertTrue(enq)
        self.assertEqual(self.mf.buffer_len(), 1)
        # No emit happened yet.
        self.assertEqual(self.read_audit_log(), "")

    def test_dedup_same_key_within_window(self) -> None:
        """Same (client_id, nonce) within the window enqueues once."""
        first = self.mf.observe_auth_failure(
            mcp_server="codex", failure_reason="auth_hmac_invalid",
            client_id="c1", nonce="n1",
        )
        self.assertTrue(first)
        for _ in range(5):
            again = self.mf.observe_auth_failure(
                mcp_server="codex", failure_reason="auth_hmac_invalid",
                client_id="c1", nonce="n1",
            )
            self.assertFalse(again, "dedup failed to suppress retry")
        self.assertEqual(self.mf.buffer_len(), 1)

    def test_distinct_keys_each_enqueue(self) -> None:
        for i in range(4):
            ok = self.mf.observe_auth_failure(
                mcp_server="codex", failure_reason="auth_hmac_invalid",
                client_id="c%d" % i, nonce="n%d" % i,
            )
            self.assertTrue(ok)
        self.assertEqual(self.mf.buffer_len(), 4)

    def test_preparse_branch_stable_key_via_token_hash(self) -> None:
        """No client_id/nonce → dedup keyed by token hash sentinel."""
        # Same raw token, no client_id/nonce → deduped to one.
        first = self.mf.observe_auth_failure(
            mcp_server="stdio", failure_reason="auth_token_malformed",
            raw_token="v1.deadbeefdeadbeef.cafe.zzz",
        )
        self.assertTrue(first)
        again = self.mf.observe_auth_failure(
            mcp_server="stdio", failure_reason="auth_token_malformed",
            raw_token="v1.deadbeefdeadbeef.cafe.zzz",
        )
        self.assertFalse(again)
        # A DIFFERENT raw token → distinct key → enqueues.
        other = self.mf.observe_auth_failure(
            mcp_server="stdio", failure_reason="auth_token_malformed",
            raw_token="totally-different-token",
        )
        self.assertTrue(other)
        # And a no-token branch shares the sentinel-only key.
        none1 = self.mf.observe_auth_failure(
            mcp_server="stdio", failure_reason="auth_token_malformed",
            raw_token=None,
        )
        self.assertTrue(none1)
        none2 = self.mf.observe_auth_failure(
            mcp_server="stdio", failure_reason="auth_token_malformed",
            raw_token=None,
        )
        self.assertFalse(none2)

    def test_drain_emits_one_per_record_no_loss(self) -> None:
        n = 7
        for i in range(n):
            self.mf.observe_auth_failure(
                mcp_server="codex", failure_reason="auth_hmac_invalid",
                client_id="c%d" % i, nonce="n%d" % i,
            )
        self.assertEqual(self.mf.buffer_len(), n)
        emitted = self.mf.drain_observations()
        self.assertEqual(emitted, n)
        self.assertEqual(self.mf.buffer_len(), 0)
        log = self.read_audit_log()
        self.assertEqual(log.count('"mcp_bearer_friction_observed"'), n)

    def test_drain_empty_returns_zero(self) -> None:
        self.assertEqual(self.mf.drain_observations(), 0)

    def test_replay_suspected_flag_preserved_through_buffer(self) -> None:
        self.mf.observe_auth_failure(
            mcp_server="codex", failure_reason="nonce_reused",
            replay_suspected=True, client_id="c1", nonce="n1",
        )
        self.mf.drain_observations()
        log = self.read_audit_log().replace(" ", "")
        self.assertIn('"replay_suspected":true', log)

    def test_buffer_bounded_under_flood(self) -> None:
        """Buffer cannot exceed capacity even under a huge flood.

        With audit_emit available (sync mode), the drain-before-append on
        the at-capacity path frees room each time, so the live buffer
        stays bounded by capacity and nothing is dropped.
        """
        cap = self.mf._BUFFER_CAPACITY
        for i in range(cap + 500):
            self.mf.observe_auth_failure(
                mcp_server="codex", failure_reason="auth_hmac_invalid",
                client_id="c%d" % i, nonce="n%d" % i,
            )
        self.assertLessEqual(self.mf.buffer_len(), cap)

    def test_overflow_is_explicit_not_silent_when_drain_cannot_free(self) -> None:
        """Codex pair-rail P1 #3 + P2 — at capacity with a NON-freeing drain:

        - no enqueued (oldest) record is silently dropped — the first
          ``capacity`` distinct records remain buffered intact;
        - each overflow record returns the FALSEY drop status (``None``),
          so a truthiness consumer NEVER reads it as success; AND
          ``dropped_count()`` increments — the loss is explicit.
        """
        from unittest import mock
        small_cap = 4
        overflow = 3
        orig_cap = self.mf._BUFFER_CAPACITY
        self.mf._BUFFER_CAPACITY = small_cap
        try:
            # Make the drain-before-append a NO-OP so the buffer cannot be
            # freed (simulates audit backpressure / audit_emit down).
            with mock.patch.object(self.mf, "drain_observations", lambda: 0):
                results = []
                for i in range(small_cap + overflow):
                    results.append(
                        self.mf.observe_auth_failure(
                            mcp_server="codex",
                            failure_reason="auth_hmac_invalid",
                            client_id="c%d" % i, nonce="n%d" % i,
                        )
                    )
            # First `small_cap` enqueued (truthy True); the rest DROPPED.
            self.assertEqual(
                results[:small_cap],
                [self.mf.OBSERVE_ENQUEUED] * small_cap,
            )
            for r in results[small_cap:]:
                # P2: the drop is the FALSEY None — a truthiness consumer
                # MUST NOT read it as success.
                self.assertIs(
                    r, None,
                    "overflow must return the falsey None drop status",
                )
                self.assertEqual(r, self.mf.OBSERVE_DROPPED)
                self.assertFalse(
                    bool(r),
                    "DROPPED must be falsey (no false success — Codex P2)",
                )
            # No silent oldest-record loss: buffer holds exactly capacity.
            self.assertEqual(self.mf.buffer_len(), small_cap)
            # The drop is explicitly accounted for (counter still increments).
            self.assertEqual(self.mf.dropped_count(), overflow)
        finally:
            self.mf._BUFFER_CAPACITY = orig_cap

    def test_dropped_status_is_falsey_no_false_success(self) -> None:
        """Codex P2 — the three statuses: ONLY ENQUEUED is truthy; both
        not-enqueued cases (DEDUP_SUPPRESSED, DROPPED) are falsey, so an
        ``if observe_auth_failure(...)`` consumer never sees a false
        success."""
        self.assertIs(self.mf.OBSERVE_ENQUEUED, True)
        self.assertTrue(bool(self.mf.OBSERVE_ENQUEUED))
        self.assertIs(self.mf.OBSERVE_DEDUP_SUPPRESSED, False)
        self.assertFalse(bool(self.mf.OBSERVE_DEDUP_SUPPRESSED))
        self.assertIsNone(self.mf.OBSERVE_DROPPED)
        self.assertFalse(bool(self.mf.OBSERVE_DROPPED))
        # The three are mutually distinct so callers CAN still disambiguate
        # (True vs False vs None) when they need to.
        self.assertNotEqual(
            self.mf.OBSERVE_DEDUP_SUPPRESSED, self.mf.OBSERVE_DROPPED
        )

    def test_truthiness_consumer_does_not_treat_drop_as_success(self) -> None:
        """An ``if observe_auth_failure(...)`` consumer counts a genuine
        enqueue only — a capacity DROP is NOT counted as success."""
        from unittest import mock
        small_cap = 2
        orig_cap = self.mf._BUFFER_CAPACITY
        self.mf._BUFFER_CAPACITY = small_cap
        truthy_successes = 0
        try:
            with mock.patch.object(self.mf, "drain_observations", lambda: 0):
                for i in range(small_cap + 4):
                    if self.mf.observe_auth_failure(
                        mcp_server="codex",
                        failure_reason="auth_hmac_invalid",
                        client_id="c%d" % i, nonce="n%d" % i,
                    ):
                        truthy_successes += 1
            # Only the genuinely-enqueued records are truthy.
            self.assertEqual(truthy_successes, small_cap)
            self.assertEqual(self.mf.dropped_count(), 4)
        finally:
            self.mf._BUFFER_CAPACITY = orig_cap

    def test_no_loss_for_everything_reported_enqueued(self) -> None:
        """Every record reported ENQUEUED is emitted exactly once by a
        drain even when interleaved with drops (no-loss for enqueued)."""
        from unittest import mock
        small_cap = 3
        orig_cap = self.mf._BUFFER_CAPACITY
        self.mf._BUFFER_CAPACITY = small_cap
        enqueued = 0
        try:
            with mock.patch.object(self.mf, "drain_observations", lambda: 0):
                for i in range(small_cap + 5):
                    r = self.mf.observe_auth_failure(
                        mcp_server="codex",
                        failure_reason="auth_hmac_invalid",
                        client_id="c%d" % i, nonce="n%d" % i,
                    )
                    if r is self.mf.OBSERVE_ENQUEUED:
                        enqueued += 1
            # Real drain now flushes exactly the enqueued count.
            emitted = self.mf.drain_observations()
            self.assertEqual(emitted, enqueued)
            self.assertEqual(enqueued, small_cap)
            log = self.read_audit_log()
            self.assertEqual(
                log.count('"mcp_bearer_friction_observed"'), enqueued
            )
        finally:
            self.mf._BUFFER_CAPACITY = orig_cap


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
