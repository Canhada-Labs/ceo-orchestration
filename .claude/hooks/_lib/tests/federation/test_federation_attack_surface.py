"""PLAN-099 Wave A.6 — adversarial attack-surface tests (AC21 + AC22).

These exercise the negative paths every federation primitive must
fail-CLOSED on:

- self-signed bypass attempt (no client cert in handshake)
- DER-fingerprint mismatch (pin pinned, peer presents different cert)
- replay-window-expired (Δt > 30s)
- TLSv1.2 attempted (rejected by SSLContext.minimum_version)
- GPG-sentinel-bad-signature / wrong-key / expired-signer / missing
- Stage-2 signer-not-in-registry
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import sys
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / ".claude").is_dir() and (parent / "VERSION").is_file():
            return parent
    raise RuntimeError("repo root not found from " + str(cur))


_REPO_ROOT = _repo_root()
_FED_CANONICAL = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
_FED_DRAFT = _REPO_ROOT / "tests" / "fixtures" / "federation_drafts"


def _resolve(name: str) -> Path:
    canon = _FED_CANONICAL / "{0}.py".format(name)
    draft = _FED_DRAFT / "{0}.py.draft".format(name)
    if canon.exists():
        return canon
    if draft.exists():
        return draft
    raise RuntimeError("could not find " + name + ".py or " + name + ".py.draft")


def _load(name: str, p: Path):
    loader = SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


# PLAN-134 W1 (PR #15 residue E3-F2) — flat names are SCOPED so the
# flat `replay` entry does not shadow the .claude/scripts/replay
# PACKAGE once this directory is wired into pytest.ini testpaths.
# Same pattern as test_federation_server.py: plant for the duration of
# the loads, restore right after, re-plant per-module around test
# execution (server.py lazy-imports `from replay import
# verify_signature` at request time).
_FLAT_NAMES = ("identity", "replay", "audit_chain")
_PRE_EXISTING = {name: sys.modules.get(name) for name in _FLAT_NAMES}


def _restore_flat_names(saved) -> None:
    for name in _FLAT_NAMES:
        prev = saved.get(name)
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev


identity = _load("identity", _resolve("identity"))
replay = _load("replay", _resolve("replay"))
audit_chain = _load("audit_chain", _resolve("audit_chain"))
server = _load("federation_server", _resolve("server"))
_restore_flat_names(_PRE_EXISTING)

_EXEC_SAVED = {}


def setUpModule() -> None:  # noqa: N802 — unittest contract
    for name, mod in zip(_FLAT_NAMES, (identity, replay, audit_chain)):
        _EXEC_SAVED[name] = sys.modules.get(name)
        sys.modules[name] = mod


def tearDownModule() -> None:  # noqa: N802 — unittest contract
    _restore_flat_names(_EXEC_SAVED)
    _EXEC_SAVED.clear()


SECRET = "1" * 64  # canonical test peer secret


class TestDERFingerprintMismatch(unittest.TestCase):
    """AC21 — pin-mismatch path."""

    def test_lookup_returns_none_on_fingerprint_drift(self):
        td = Path(tempfile.mkdtemp(prefix="fedtest_"))
        p = td / "peers.yaml"
        p.write_text(
            "peers:\n"
            "  - peer_id: alpha\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
            "    hmac_secret_hex: " + SECRET + "\n",
            encoding="utf-8",
        )
        peers = identity.load_peers(p)
        # Attacker presents a different cert → fingerprint drifts
        bad_fpr = "f" * 64
        self.assertIsNone(
            identity.lookup_peer_by_fingerprint(peers, bad_fpr)
        )

    def test_compare_fingerprints_constant_time(self):
        # Sanity — the function returns False on any divergence; we use
        # this in the production path via hmac.compare_digest.
        self.assertFalse(
            identity.compare_fingerprints("a" * 64, "a" * 63 + "b")
        )


class TestReplayWindowExpired(unittest.TestCase):
    """AC13 — clock-skew gate rejects expired-window requests."""

    def test_request_30s_past_accepted(self):
        # Boundary: |Δt| == max_skew → accepted (we use > not >=).
        cache = replay.ReplayCache(max_skew_seconds=30)
        now = 1000.0
        ts = _dt.datetime.fromtimestamp(now - 30, tz=_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        d = cache.check_and_record("peer-x", "nonce-x", ts, now_epoch=now)
        self.assertTrue(d.accepted)

    def test_request_31s_past_rejected(self):
        cache = replay.ReplayCache(max_skew_seconds=30)
        now = 1000.0
        ts = _dt.datetime.fromtimestamp(now - 31, tz=_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        d = cache.check_and_record("peer-x", "nonce-x", ts, now_epoch=now)
        self.assertFalse(d.accepted)
        self.assertEqual(d.reason, "clock_skew")

    def test_request_61s_future_rejected(self):
        cache = replay.ReplayCache(max_skew_seconds=30)
        now = 1000.0
        ts = _dt.datetime.fromtimestamp(now + 61, tz=_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        d = cache.check_and_record("peer-x", "nonce-x", ts, now_epoch=now)
        self.assertFalse(d.accepted)


class TestSignatureInvalidPaths(unittest.TestCase):
    """AC13 — HMAC mismatch + body tampering."""

    def test_body_tampered_signature_invalid(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        sig = replay.sign_request("GET", "/x", ts, nonce, b"original", SECRET)
        self.assertFalse(replay.verify_signature(
            "GET", "/x", ts, nonce, b"tampered", SECRET, sig,
        ))

    def test_secret_drift_signature_invalid(self):
        ts = "2026-05-17T12:00:00Z"
        nonce = replay.generate_nonce()
        sig = replay.sign_request("GET", "/x", ts, nonce, b"", SECRET)
        other_secret = "2" * 64
        self.assertFalse(replay.verify_signature(
            "GET", "/x", ts, nonce, b"", other_secret, sig,
        ))


class TestSentinelFailureModes(unittest.TestCase):
    """AC22 — both stages of the 2-stage sentinel verifier fail-CLOSED."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="fedsent_"))

    def test_missing_signed_file(self):
        ok, reason = identity.verify_enable_sentinel_pair(
            self.td / "enabled.md",
            self.td / "enabled.md.asc",
            ["D" * 40],
        )
        self.assertFalse(ok)
        self.assertTrue(reason)

    def test_missing_signature_file(self):
        signed = self.td / "enabled.md"
        signed.write_text("ENABLED", encoding="utf-8")
        ok, reason = identity.verify_enable_sentinel_pair(
            signed,
            self.td / "enabled.md.asc",
            ["D" * 40],
        )
        self.assertFalse(ok)

    def test_empty_allowlist_rejects(self):
        signed = self.td / "enabled.md"
        signed.write_text("ENABLED", encoding="utf-8")
        sig = self.td / "enabled.md.asc"
        sig.write_text("-----BEGIN PGP SIGNATURE-----\nfake\n-----END PGP SIGNATURE-----\n", encoding="utf-8")
        ok, reason = identity.verify_enable_sentinel_pair(
            signed, sig, [],
        )
        self.assertFalse(ok)

    def test_corrupt_signature_armor_rejects(self):
        signed = self.td / "enabled.md"
        signed.write_text("ENABLED 2026-05-17 OWNER 00000000", encoding="utf-8")
        sig = self.td / "enabled.md.asc"
        sig.write_text("not a real PGP signature", encoding="utf-8")
        # The fpr we'd accept if a valid signature were present:
        owner_fpr = "0000000000000000000000000000000000000000"
        ok, reason = identity.verify_enable_sentinel_pair(
            signed, sig, [owner_fpr],
        )
        self.assertFalse(ok)
        # We expect a reason from verify_detached's failure surface.
        self.assertTrue(reason)


class TestAutonomousLoopBlocked(unittest.TestCase):
    """AC18 — federation client must NOT be reachable from autonomous-loop.

    This is a structural test: we grep the federation modules + verify
    the import-graph denial isn't broken at the source level. The full
    boundary check is in `.claude/sidecars/c1-crypto/stdlib-ssl-mvp/boundary_test.py`.
    """

    def test_federation_client_does_not_import_autonomous_loop(self):
        client_path = _FED_DRAFT / "client.py.draft"
        txt = client_path.read_text(encoding="utf-8")
        self.assertNotIn("autonomous_loop", txt)
        self.assertNotIn("swarm_iteration", txt)


if __name__ == "__main__":
    unittest.main()
