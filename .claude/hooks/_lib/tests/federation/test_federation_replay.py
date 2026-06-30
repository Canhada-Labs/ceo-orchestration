"""PLAN-099 Wave A.5 — replay protection tests (AC13).

Coverage:

- HMAC signature round-trip + constant-time mismatch
- Nonce ≥128-bit generation
- Clock-skew reject (|Δt| > 30s)
- Replay reject (same (peer, nonce) in window)
- Cache prune on wall-clock advance
"""
from __future__ import annotations

import importlib.util
import sys
import time
import unittest
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / ".claude").is_dir() and (parent / "VERSION").is_file():
            return parent
    raise RuntimeError("repo root not found from " + str(cur))


_REPO_ROOT = _repo_root()
_FED_CANONICAL = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
_FED_DRAFT = _REPO_ROOT / ".claude" / "plans" / "PLAN-099" / "federation"


def _resolve(name: str) -> Path:
    canon = _FED_CANONICAL / "{0}.py".format(name)
    draft = _FED_DRAFT / "{0}.py.draft".format(name)
    if canon.exists():
        return canon
    if draft.exists():
        return draft
    raise RuntimeError("could not find " + name + ".py or " + name + ".py.draft")


def _load(name: str, p: Path):
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


replay = _load("federation_replay", _resolve("replay"))


SECRET = "a1b2c3d4" * 8  # 64-hex


class TestSignAndVerify(unittest.TestCase):
    def test_signature_round_trip(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        body = b"hello"
        sig = replay.sign_request("GET", "/federation/identity", ts, nonce, body, SECRET)
        self.assertTrue(replay.verify_signature(
            "GET", "/federation/identity", ts, nonce, body, SECRET, sig,
        ))

    def test_signature_mismatch_method(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        sig = replay.sign_request("GET", "/federation/identity", ts, nonce, b"", SECRET)
        self.assertFalse(replay.verify_signature(
            "POST", "/federation/identity", ts, nonce, b"", SECRET, sig,
        ))

    def test_signature_mismatch_path(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        sig = replay.sign_request("GET", "/federation/identity", ts, nonce, b"", SECRET)
        self.assertFalse(replay.verify_signature(
            "GET", "/federation/status", ts, nonce, b"", SECRET, sig,
        ))

    def test_signature_empty_returns_false(self):
        self.assertFalse(replay.verify_signature(
            "GET", "/x", "2026-01-01T00:00:00Z", "n", b"", SECRET, "",
        ))

    def test_signature_malformed_secret_raises(self):
        with self.assertRaises(ValueError):
            replay.sign_request("GET", "/x", "2026-01-01T00:00:00Z", "n", b"", "not-hex-zz")

    def test_signature_body_sensitivity(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        sig = replay.sign_request("GET", "/federation/audit-summary", ts, nonce, b"a=1", SECRET)
        self.assertFalse(replay.verify_signature(
            "GET", "/federation/audit-summary", ts, nonce, b"a=2", SECRET, sig,
        ))


class TestNonceGeneration(unittest.TestCase):
    def test_nonce_min_128_bits(self):
        nonce = replay.generate_nonce()
        # urlsafe base64 of 24 bytes → ~32 chars; ≥22 enforces 128-bit.
        self.assertGreaterEqual(len(nonce), 22)

    def test_nonce_below_128_bits_rejected(self):
        with self.assertRaises(ValueError):
            replay.generate_nonce(nbytes=8)


class TestReplayCache(unittest.TestCase):
    def setUp(self):
        self.cache = replay.ReplayCache(max_skew_seconds=30)
        self.peer = "peer-test"

    def test_first_accept(self):
        now = time.time()
        ts = _rfc3339(now)
        d = self.cache.check_and_record(self.peer, "nonce-1", ts, now_epoch=now)
        self.assertTrue(d.accepted)

    def test_clock_skew_reject(self):
        now = time.time()
        ts = _rfc3339(now - 120)  # 2min in the past
        d = self.cache.check_and_record(self.peer, "nonce-late", ts, now_epoch=now)
        self.assertFalse(d.accepted)
        self.assertEqual(d.reason, "clock_skew")

    def test_replay_reject(self):
        now = time.time()
        ts = _rfc3339(now)
        d1 = self.cache.check_and_record(self.peer, "nonce-X", ts, now_epoch=now)
        d2 = self.cache.check_and_record(self.peer, "nonce-X", ts, now_epoch=now)
        self.assertTrue(d1.accepted)
        self.assertFalse(d2.accepted)
        self.assertEqual(d2.reason, "replay")

    def test_different_peer_same_nonce_accepted(self):
        now = time.time()
        ts = _rfc3339(now)
        d1 = self.cache.check_and_record("peer-a", "nonce-shared", ts, now_epoch=now)
        d2 = self.cache.check_and_record("peer-b", "nonce-shared", ts, now_epoch=now)
        self.assertTrue(d1.accepted)
        self.assertTrue(d2.accepted)

    def test_cache_prune_after_window(self):
        now = time.time()
        d1 = self.cache.check_and_record(self.peer, "nonce-old", _rfc3339(now), now_epoch=now)
        self.assertTrue(d1.accepted)
        future = now + 120  # 2min later — well past 2*30s + 1
        d2 = self.cache.check_and_record(self.peer, "nonce-old", _rfc3339(future), now_epoch=future)
        # Old nonce pruned; same value reusable (we accept post-prune).
        self.assertTrue(d2.accepted)

    def test_replay_rejected_through_full_2x_skew_window(self):
        """Codex R2 iter-1 P0#1 fold — entry retained for the FULL replay window.

        An attacker who captured a request issued at ``request_ts =
        server_time + max_skew`` (forward skew = +30s) can replay it any
        time up to ``server_time + 2*max_skew`` (= +60s) and still pass
        the ``|Δt| <= max_skew`` freshness check. The cache MUST retain
        the entry for that full 60s window or the replay slips through.
        """
        import datetime as _dt
        now = 1_000_000.0
        # Original request issued at ts = now + 30 (max forward skew).
        original_ts = _dt.datetime.fromtimestamp(
            now + 30, tz=_dt.timezone.utc,
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        d1 = self.cache.check_and_record(self.peer, "captured-nonce", original_ts, now_epoch=now)
        self.assertTrue(d1.accepted, "original request rejected: " + d1.reason)

        # 45s later, attacker replays the SAME (nonce, ts) pair. The
        # freshness check still passes (|30 - 75| ... wait, 45s later
        # server_time = now + 45, request_ts = now + 30 → |Δt| = 15 ≤ 30).
        # Without the 2x cache window, the cache entry at server-stored
        # time=now would have been pruned; with the fix, it's retained.
        d2 = self.cache.check_and_record(
            self.peer, "captured-nonce", original_ts, now_epoch=now + 45,
        )
        self.assertFalse(d2.accepted, "replay through 2x window not rejected")
        self.assertEqual(d2.reason, "replay")

    def test_malformed_timestamp_rejected(self):
        d = self.cache.check_and_record(
            self.peer, "n", "not-rfc3339", now_epoch=time.time(),
        )
        self.assertFalse(d.accepted)
        self.assertEqual(d.reason, "malformed_timestamp")


def _rfc3339(epoch: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(epoch, tz=_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


if __name__ == "__main__":
    unittest.main()
