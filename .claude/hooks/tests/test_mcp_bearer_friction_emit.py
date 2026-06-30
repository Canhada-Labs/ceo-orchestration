"""PLAN-090 Wave C.2 §B firing path — mcp_bearer_friction_observed tests.

R1 TDE P0 fold + R2 Codex iter-2 P1 fold: ADR-122 §B requires a real
firing path so "friction count" is observable, not paper. This test
asserts the emit + counter aggregation actually surface real bearer-
friction conditions.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


class TestMcpBearerFrictionEmit(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        # PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — observe_auth_failure
        # is now NON-BLOCKING (buffers + retry-window dedup); the emit
        # happens at drain_observations(). Reset the module buffer/dedup
        # per test so prior cases do not bleed, and drain explicitly
        # before asserting on the audit log.
        from _lib import mcp_bearer_friction
        mcp_bearer_friction._reset_state_for_test()

    def tearDown(self) -> None:
        from _lib import mcp_bearer_friction
        mcp_bearer_friction._reset_state_for_test()
        super().tearDown()

    def test_friction_condition_emits_event(self) -> None:
        from _lib import mcp_bearer_friction
        mcp_bearer_friction.observe_auth_failure(
            mcp_server="codex",
            failure_reason="bearer_expired",
            replay_suspected=False,
            client_id="c1", nonce="n1",
        )
        mcp_bearer_friction.drain_observations()
        log = self.read_audit_log()
        self.assertIn('"mcp_bearer_friction_observed"', log)
        # Tolerate json.dumps default separators (space after colon).
        self.assertTrue(
            '"failure_reason": "bearer_expired"' in log
            or '"failure_reason":"bearer_expired"' in log,
            f'expected failure_reason=bearer_expired in log; got: {log!r}',
        )

    def test_replay_attempt_emits_replay_flag(self) -> None:
        from _lib import mcp_bearer_friction
        mcp_bearer_friction.observe_auth_failure(
            mcp_server="codex",
            failure_reason="nonce_repeat",
            replay_suspected=True,
            client_id="c1", nonce="n1",
        )
        mcp_bearer_friction.drain_observations()
        log = self.read_audit_log()
        self.assertIn('"replay_suspected":true', log.replace(" ", ""))

    def test_multiple_failures_accumulate(self) -> None:
        from _lib import mcp_bearer_friction
        # Distinct (client_id, nonce) per call → distinct dedup keys, so
        # all three are enqueued + emitted (retry-window dedup only
        # collapses retries of the SAME key).
        for i, reason in enumerate(("bearer_expired", "bearer_unknown", "auth_403")):
            mcp_bearer_friction.observe_auth_failure(
                mcp_server="codex",
                failure_reason=reason,
                replay_suspected=False,
                client_id="c%d" % i, nonce="n%d" % i,
            )
        mcp_bearer_friction.drain_observations()
        log = self.read_audit_log()
        count = log.count('"mcp_bearer_friction_observed"')
        self.assertEqual(count, 3, f"expected 3 emits, got {count}")

    def test_mcp_server_field_sanitized(self) -> None:
        from _lib import mcp_bearer_friction
        # Bound to 64 chars; allowlist [a-z0-9_-].
        mcp_bearer_friction.observe_auth_failure(
            mcp_server="bad/path; rm -rf /",
            failure_reason="bearer_expired",
            replay_suspected=False,
            client_id="c1", nonce="n1",
        )
        mcp_bearer_friction.drain_observations()
        log = self.read_audit_log()
        # Sanitized: dangerous characters stripped or replaced.
        self.assertNotIn("rm -rf", log)

    def test_friction_count_aggregation(self) -> None:
        from _lib import mcp_bearer_friction
        # Distinct keys per call so dedup does not collapse them.
        for i in range(7):
            mcp_bearer_friction.observe_auth_failure(
                mcp_server="codex",
                failure_reason="bearer_expired",
                replay_suspected=False,
                client_id="c%d" % i, nonce="n%d" % i,
            )
        mcp_bearer_friction.drain_observations()
        count = mcp_bearer_friction.count_friction_in_window(window_hours=24)
        self.assertGreaterEqual(count, 7)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
