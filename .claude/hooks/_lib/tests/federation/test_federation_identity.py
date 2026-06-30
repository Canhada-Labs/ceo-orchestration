"""PLAN-099 Wave A.5 — identity primitives tests (AC4 + AC11 + AC22 stage-1).

Coverage:

- AC4 :func:`compute_cert_fingerprint` returns deterministic 64-hex
- AC4 :func:`compare_fingerprints` constant-time + case-insensitive
- AC11 peers.yaml parser — invariant violations fail-CLOSED
- AC22 Stage-1 sentinel verify_detached missing-files / bad-sig
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import importlib.util
import ssl
import sys
import tempfile
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
    """Find a federation module by basename — canonical first, draft fallback."""
    canon = _FED_CANONICAL / "{0}.py".format(name)
    draft = _FED_DRAFT / "{0}.py.draft".format(name)
    if canon.exists():
        return canon
    if draft.exists():
        return draft
    raise RuntimeError("could not find " + name + ".py or " + name + ".py.draft")


def _load_module(name: str, source: Path):
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, str(source))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


# Load federation modules — canonical post-ceremony, drafts pre-ceremony.
identity = _load_module("federation_identity", _resolve("identity"))


class TestComputeCertFingerprint(unittest.TestCase):
    def test_fingerprint_is_64_hex_lowercase(self):
        # Use a known PEM from python's stdlib test fixtures via ssl.create_default_context
        # We synthesise a tiny PEM by hand for determinism.
        # We use a hash of the DER-equivalent bytes directly here, not
        # a real cert — the function only requires bytes input for
        # compute_der_fingerprint.
        der = b"\x30\x82\x01\x0a"  # fake DER prefix bytes
        fp = identity.compute_der_fingerprint(der)
        self.assertEqual(len(fp), 64)
        self.assertEqual(fp, fp.lower())
        # Deterministic across calls.
        self.assertEqual(fp, hashlib.sha256(der).hexdigest())

    def test_compute_cert_fingerprint_rejects_bytes_input(self):
        with self.assertRaises(TypeError):
            identity.compute_cert_fingerprint(b"-----BEGIN CERT-----")

    def test_compute_der_fingerprint_rejects_str_input(self):
        with self.assertRaises(TypeError):
            identity.compute_der_fingerprint("not bytes")  # type: ignore[arg-type]


class TestCompareFingerprints(unittest.TestCase):
    def test_equal_same_case(self):
        a = "abc" * 21 + "a"  # 64 chars
        self.assertTrue(identity.compare_fingerprints(a, a))

    def test_equal_mixed_case(self):
        a = "abc" * 21 + "a"
        self.assertTrue(identity.compare_fingerprints(a.upper(), a.lower()))

    def test_unequal_different_length(self):
        self.assertFalse(identity.compare_fingerprints("abc", "abcd"))

    def test_empty_strings_false(self):
        self.assertFalse(identity.compare_fingerprints("", ""))

    def test_non_string_returns_false(self):
        self.assertFalse(identity.compare_fingerprints(None, "a" * 64))  # type: ignore[arg-type]
        self.assertFalse(identity.compare_fingerprints("a" * 64, 12345))  # type: ignore[arg-type]


class TestLoadPeers(unittest.TestCase):
    def _write_peers(self, contents: str) -> Path:
        td = tempfile.mkdtemp(prefix="fedtest_")
        p = Path(td) / "peers.yaml"
        p.write_text(contents, encoding="utf-8")
        return p

    def test_well_formed_peers_parses(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-a\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
            "    revoked: false\n"
            "    hmac_secret_hex: " + "c" * 64 + "\n"
        )
        peers = identity.load_peers(p)
        self.assertEqual(len(peers), 1)
        rec = peers["peer-a"]
        self.assertEqual(rec.peer_id_cert_fingerprint, "a" * 64)
        self.assertEqual(rec.ca_pin_sha256, "b" * 64)
        self.assertEqual(rec.hmac_secret_hex, "c" * 64)
        self.assertFalse(rec.revoked)

    def test_missing_required_field_raises(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-a\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            # missing ca_pin_sha256
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
        )
        with self.assertRaises(identity.PeersFileError):
            identity.load_peers(p)

    def test_invalid_fingerprint_raises(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-a\n"
            "    peer_id_cert_fingerprint: \"too short\"\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
        )
        with self.assertRaises(identity.PeersFileError):
            identity.load_peers(p)

    def test_revoked_peer_filtered_by_lookup(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-rev\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
            "    revoked: true\n"
            "    hmac_secret_hex: " + "c" * 64 + "\n"
        )
        peers = identity.load_peers(p)
        # Revoked peers still load in the map (audit visibility),
        # but lookup_peer_by_fingerprint skips them.
        self.assertIn("peer-rev", peers)
        self.assertIsNone(
            identity.lookup_peer_by_fingerprint(peers, "a" * 64)
        )

    def test_not_valid_after_before_swap_rejected(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-a\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2026-01-01T00:00:00Z\"\n"  # before "before"
            "    not_valid_before: \"2027-01-01T00:00:00Z\"\n"
        )
        with self.assertRaises(identity.PeersFileError):
            identity.load_peers(p)

    def test_duplicate_peer_id_rejected(self):
        p = self._write_peers(
            "peers:\n"
            "  - peer_id: peer-dup\n"
            "    peer_id_cert_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
            "  - peer_id: peer-dup\n"
            "    peer_id_cert_fingerprint: " + "d" * 64 + "\n"
            "    ca_pin_sha256: " + "e" * 64 + "\n"
            "    not_valid_after: \"2027-01-01T00:00:00Z\"\n"
            "    not_valid_before: \"2026-01-01T00:00:00Z\"\n"
        )
        with self.assertRaises(identity.PeersFileError):
            identity.load_peers(p)

    def test_missing_file_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            identity.load_peers(Path("/nonexistent/peers.yaml"))


class TestSentinelVerifyMissingFiles(unittest.TestCase):
    """AC22 Stage-1 — missing-files / wrong-path paths fail-CLOSED."""

    def test_missing_signed_file(self):
        td = Path(tempfile.mkdtemp(prefix="fedtest_"))
        ok, reason = identity.verify_enable_sentinel_pair(
            td / "no-such.md",
            td / "no-such.md.asc",
            ["D" * 40],
        )
        self.assertFalse(ok)
        self.assertTrue(reason)
        # reason is from verify_detached: signature_file_missing or signed_file_missing

    def test_empty_allowlist_fails_closed(self):
        td = Path(tempfile.mkdtemp(prefix="fedtest_"))
        signed = td / "enabled.md"
        signed.write_text("ENABLED", encoding="utf-8")
        sig = td / "enabled.md.asc"
        sig.write_text("not a real sig", encoding="utf-8")
        ok, reason = identity.verify_enable_sentinel_pair(
            signed, sig, [],
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
