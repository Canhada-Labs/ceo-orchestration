"""PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — integration tests.

Covers plan §4 W5 (a)-(e) plus the no-loss drain contract (AC6):

  (a) replay attack: same signed token twice → 2nd BLOCKED + a
      ``mcp_bearer_replay_rejected`` audit event fires.
  (b) friction cascade: 5 auth failures in window → friction observed;
      deduped retries (identical client_id+nonce) do NOT inflate the
      friction count.
  (c) pre-HMAC poisoning: an unauthenticated loopback flood (bad HMAC)
      does NOT enter the nonce store (proves POST-HMAC ordering).
  (d) clock domain: a valid token within skew → ACCEPT (no random DENY
      from a ms-vs-ns clock-domain mismatch).
  (e) [store-level LRU capacity is covered in
      tests/test_mcp_bearer_nonce_replay.py::test_lru_capacity_bound]
      here we assert the wired store is the default bounded store.
  no-loss: N distinct enqueued friction events → N emitted after the
      per-call drain, within the same request.

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
TestEnvContext for env isolation. CEO_AUDIT_SYNC_MODE=1 so emits are
synchronously visible in the audit log.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import auth  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402
import rate_limit  # type: ignore[import-not-found]  # noqa: E402
from _lib import mcp_bearer_friction  # noqa: E402
from _lib.mcp import bearer_replay  # noqa: E402


_SECRET = b"\x42" * 32
_CLIENT_ID = "0123456789abcdef"


def _seed_secret(project_dir: Path, client_id: str = _CLIENT_ID) -> None:
    secrets_dir = project_dir / "state" / "mcp_client_secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    target = secrets_dir / f"{client_id}.key"
    target.write_bytes(_SECRET)
    os.chmod(str(target), 0o600)


def _write_settings(project_dir: Path, registry: dict) -> None:
    settings = {"mcp_client_registry": registry}
    sp = project_dir / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(settings), encoding="utf-8")


def _make_token(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    mac = auth.compute_hmac(client_id, nonce, ts_ms, secret)
    return f"v1.{client_id}.{nonce}.{mac}"


class _Base(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        rate_limit.reset_registry()
        # Fresh per-process replay store + clean friction buffer/dedup so
        # tests do not bleed state between cases.
        dispatch.set_replay_store_for_test(
            bearer_replay.BearerReplayStore()
        )
        mcp_bearer_friction._reset_state_for_test()

    def tearDown(self) -> None:
        dispatch.set_replay_store_for_test(None)
        mcp_bearer_friction._reset_state_for_test()
        super().tearDown()

    def _setup_client(self, handlers=("list_skills",)):
        _seed_secret(self.project_dir)
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": list(handlers)}},
        )

    def _auth(self, *, raw_token, ts_ms, method="list_skills", remote_addr="127.0.0.1"):
        return dispatch.authenticate(
            raw_token=raw_token,
            timestamp_ms=ts_ms,
            method=method,
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
            remote_addr=remote_addr,
        )


class TestReplayAttack(_Base):
    """(a) replay attack — same signed token twice."""

    def test_replay_same_token_second_blocked_and_emits(self) -> None:
        self._setup_client()
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, "aaaabbbbccccdddd", ts, _SECRET)

        # First presentation → ACCEPT (ctx populated, no deny).
        ctx1, reason1, _ = self._auth(raw_token=token, ts_ms=ts)
        self.assertIsNotNone(ctx1, f"first call unexpectedly denied: {reason1}")
        self.assertIsNone(reason1)

        # Second presentation of the SAME signed token → BLOCKED (replay).
        ctx2, reason2, _ = self._auth(raw_token=token, ts_ms=ts)
        self.assertIsNone(ctx2)
        self.assertIsNotNone(reason2)

        log = self.read_audit_log()
        self.assertIn('"mcp_bearer_replay_rejected"', log)
        # The reused-nonce reason is recorded.
        self.assertIn("nonce_reused", log)


class TestFrictionCascadeDedup(_Base):
    """(b) 5 auth failures → friction; deduped retries do NOT inflate."""

    def test_distinct_failures_emit_deduped_retries_do_not(self) -> None:
        self._setup_client()
        ts = int(time.time() * 1000)

        # 5 DISTINCT failures (distinct client_id+nonce via distinct
        # nonces, all with wrong secret → auth_hmac_invalid).
        for i in range(5):
            nonce = "deadbeefdeadbe%02x" % i
            bad = _make_token(_CLIENT_ID, nonce, ts, b"\x99" * 32)
            ctx, reason, _ = self._auth(raw_token=bad, ts_ms=ts)
            self.assertIsNone(ctx)
            self.assertEqual(reason, "auth_hmac_invalid")

        log = self.read_audit_log()
        distinct_count = log.count('"mcp_bearer_friction_observed"')
        self.assertEqual(
            distinct_count, 5,
            f"expected 5 distinct friction emits, got {distinct_count}",
        )

        # Now hammer the SAME (client_id, nonce) failure 10 more times —
        # retry-window dedup must suppress all of them (0 new emits).
        repeat_nonce = "cafecafecafecafe"
        bad_repeat = _make_token(_CLIENT_ID, repeat_nonce, ts, b"\x99" * 32)
        # First of the repeated key DOES emit (it is a new distinct key).
        self._auth(raw_token=bad_repeat, ts_ms=ts)
        baseline = self.read_audit_log().count('"mcp_bearer_friction_observed"')
        for _ in range(10):
            self._auth(raw_token=bad_repeat, ts_ms=ts)
        after = self.read_audit_log().count('"mcp_bearer_friction_observed"')
        self.assertEqual(
            after, baseline,
            f"deduped retries inflated friction: {baseline} -> {after}",
        )


class TestPreHmacNoPoison(_Base):
    """(c) unauth loopback flood pre-HMAC does NOT poison the store."""

    def test_bad_hmac_flood_does_not_grow_store(self) -> None:
        self._setup_client()
        ts = int(time.time() * 1000)
        store = dispatch._get_replay_store()
        self.assertEqual(len(store), 0)

        # Flood 50 distinct nonces with WRONG secret (HMAC will fail).
        for i in range(50):
            nonce = "f00df00df00df0%02x" % i
            bad = _make_token(_CLIENT_ID, nonce, ts, b"\x99" * 32)
            ctx, reason, _ = self._auth(raw_token=bad, ts_ms=ts)
            self.assertIsNone(ctx)
            self.assertEqual(reason, "auth_hmac_invalid")

        # POST-HMAC ordering ⇒ none of these reached the nonce store.
        self.assertEqual(
            len(store), 0,
            "pre-HMAC poisoning: unauthenticated tokens entered the store",
        )

        # A genuinely valid token still works afterwards (store usable).
        good = _make_token(_CLIENT_ID, "0a0a0a0a0a0a0a0a", ts, _SECRET)
        ctx, reason, _ = self._auth(raw_token=good, ts_ms=ts)
        self.assertIsNotNone(ctx, f"valid token denied after flood: {reason}")
        self.assertEqual(len(store), 1)


class TestClockDomainValidWithinSkew(_Base):
    """(d) valid token within skew → ACCEPT (no random clock-domain DENY)."""

    def test_valid_within_skew_accepts_repeatedly(self) -> None:
        self._setup_client()
        base = int(time.time() * 1000)
        # Several distinct fresh tokens at small skews inside ±60s — all
        # must ACCEPT. A ms-vs-ns domain mismatch would have produced a
        # spurious stale DENY here.
        for i, skew_ms in enumerate((-5000, -1000, 0, 1000, 5000)):
            ts = base + skew_ms
            nonce = "beefbeefbeefbe%02x" % i
            token = _make_token(_CLIENT_ID, nonce, ts, _SECRET)
            ctx, reason, _ = self._auth(raw_token=token, ts_ms=ts)
            self.assertIsNotNone(
                ctx, f"valid token at skew={skew_ms}ms denied: {reason}"
            )
            self.assertIsNone(reason)

    def test_default_wired_store_is_bounded(self) -> None:
        """(e) the production-wired store is the default bounded store."""
        dispatch.set_replay_store_for_test(None)  # force default rebuild
        store = dispatch._get_replay_store()
        self.assertEqual(store._maxsize, bearer_replay.DEFAULT_MAXSIZE)


class TestNoLossDrain(_Base):
    """AC6 — no-loss: N enqueued → N emitted by the per-request drain."""

    def test_n_distinct_enqueued_n_emitted(self) -> None:
        # Enqueue N distinct friction observations directly (distinct
        # client_id+nonce so dedup does not suppress any).
        n = 12
        enqueued = 0
        for i in range(n):
            ok = mcp_bearer_friction.observe_auth_failure(
                mcp_server="stdio",
                failure_reason="auth_hmac_invalid",
                client_id="client-%02x" % i,
                nonce="nonce-%02x" % i,
            )
            if ok:
                enqueued += 1
        self.assertEqual(enqueued, n)
        self.assertEqual(mcp_bearer_friction.buffer_len(), n)

        emitted = mcp_bearer_friction.drain_observations()
        self.assertEqual(emitted, n, "drain dropped events (no-loss violated)")
        self.assertEqual(mcp_bearer_friction.buffer_len(), 0)

        log = self.read_audit_log()
        self.assertEqual(log.count('"mcp_bearer_friction_observed"'), n)

    def test_authenticate_drains_within_same_request(self) -> None:
        """The mandatory drain fires within authenticate() (not at exit)."""
        self._setup_client()
        ts = int(time.time() * 1000)
        bad = _make_token(_CLIENT_ID, "1212121212121212", ts, b"\x99" * 32)
        # Single failing auth — friction must be emitted by the time
        # authenticate() returns (buffer empty + event in the log NOW).
        self._auth(raw_token=bad, ts_ms=ts)
        self.assertEqual(
            mcp_bearer_friction.buffer_len(), 0,
            "authenticate() did not drain the friction buffer",
        )
        log = self.read_audit_log()
        self.assertIn('"mcp_bearer_friction_observed"', log)


class _ExplodingStore:
    """A replay store whose check_request raises (P1 #2 fault injection)."""

    _maxsize = bearer_replay.DEFAULT_MAXSIZE

    def __len__(self) -> int:  # pragma: no cover - not asserted
        return 0

    def check_request(self, **_kwargs):
        raise RuntimeError("simulated replay-store / clock / state bug")


class TestReplayStoreErrorContained(_Base):
    """Codex pair-rail P1 #2 — a replay-store bug must NOT escape authenticate()."""

    def test_store_exception_fails_closed_no_propagation(self) -> None:
        self._setup_client()
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, "abcdabcdabcdabcd", ts, _SECRET)
        dispatch.set_replay_store_for_test(_ExplodingStore())

        # authenticate() must NOT raise — it fails CLOSED with a deny.
        try:
            ctx, reason, retry = self._auth(raw_token=token, ts_ms=ts)
        except Exception as exc:  # pragma: no cover - the bug we're guarding
            self.fail(f"authenticate() leaked a store exception: {exc!r}")

        self.assertIsNone(ctx, "store-error path must deny (fail-CLOSED)")
        self.assertEqual(reason, "auth_hmac_invalid", "generic deny, no oracle")
        self.assertEqual(retry, 0)

    def test_store_exception_still_drains_friction(self) -> None:
        """The mandatory finally-drain still runs even on the store-error
        path: friction is observed + emitted, buffer empty after return."""
        self._setup_client()
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, "bcdebcdebcdebcde", ts, _SECRET)
        dispatch.set_replay_store_for_test(_ExplodingStore())

        self._auth(raw_token=token, ts_ms=ts)
        # finally: _drain_friction() ran → buffer empty + event in log.
        self.assertEqual(
            mcp_bearer_friction.buffer_len(), 0,
            "store-error path skipped the mandatory friction drain",
        )
        log = self.read_audit_log()
        self.assertIn('"mcp_bearer_friction_observed"', log)
        self.assertIn("replay_store_error", log)
        # No replay-specific audit on a store ERROR (only on real DENYs).
        self.assertNotIn('"mcp_bearer_replay_rejected"', log)


class TestUnknownStoreDecisionFailsClosed(_Base):
    """Codex pair-rail P2 #4 — an unknown/future store decision fails closed
    WITHOUT a (mislabeled) replay-specific audit."""

    def test_unknown_decision_no_replay_audit(self) -> None:
        class _UnknownDecisionStore:
            _maxsize = bearer_replay.DEFAULT_MAXSIZE

            def __len__(self) -> int:  # pragma: no cover
                return 0

            def check_request(self, **_kwargs):
                # A value that is neither ACCEPT, DENY_NON_LOOPBACK, nor in
                # the replay-reject taxonomy (a future/unknown decision).
                return ("some_future_decision", "some_future_decision")

        self._setup_client()
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, "0f0f0f0f0f0f0f0f", ts, _SECRET)
        dispatch.set_replay_store_for_test(_UnknownDecisionStore())

        ctx, reason, _ = self._auth(raw_token=token, ts_ms=ts)
        self.assertIsNone(ctx, "unknown decision must fail CLOSED")
        self.assertEqual(reason, "auth_hmac_invalid")
        log = self.read_audit_log()
        # Generic friction recorded; NO replay-specific audit emitted.
        self.assertIn("replay_store_unknown_decision", log)
        self.assertNotIn('"mcp_bearer_replay_rejected"', log)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
