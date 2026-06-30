"""PLAN-023 Phase B — _lib.audit_hmac unit tests.

Covers:
- Happy-path chain walk: genesis → 3 entries → verify recomputation.
- Tamper detection: bit flip in an entry breaks verification.
- Reorder detection: swapping two entries breaks verification.
- Key generation: atomic, 0600, 32 bytes, idempotent.
- Key perm enforcement: rejects non-owner-only files.
- Sidecar read/write: round-trip, missing/malformed fall back to genesis.
- Rotation reset: clears sidecar, next read returns genesis.
- Kill-switch: `CEO_AUDIT_HMAC_DISABLE=1` observable.
- Hex helpers: exact widths + invalid input rejected.
- Process-level key cache: read_bytes called once per process lifecycle.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    AuditHmacError,
    GENESIS_PREV,
    HMAC_BYTES,
    HMAC_HEX_LEN,
    KEY_BYTES,
    compute_entry_hmac,
    from_hex,
    get_or_create_key,
    hex_digest,
    is_disabled,
    last_hmac_path,
    read_prev_hmac,
    reset_chain_on_rotation,
    write_last_hmac,
)


class AuditHmacTestBase(unittest.TestCase):
    """Share a TemporaryDirectory + env isolation for every test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-023-hmac-test-")
        self.tmp = Path(self._tmp.name)
        self._saved_env = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_KEY_PATH",
                "CEO_AUDIT_LAST_HMAC_PATH",
                "CEO_AUDIT_HMAC_DISABLE",
                "HOME",
                "CEO_PROJECT_STATE_DIR",
            )
        }
        # Redirect all audit paths into the temp dir.
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.tmp / "audit-log.jsonl")
        os.environ["CEO_AUDIT_KEY_PATH"] = str(self.tmp / "audit-key")
        os.environ["CEO_AUDIT_LAST_HMAC_PATH"] = str(
            self.tmp / "audit-log.last-hmac"
        )
        os.environ.pop("CEO_AUDIT_HMAC_DISABLE", None)
        audit_hmac._reset_key_cache_for_test()

    def tearDown(self):
        audit_hmac._reset_key_cache_for_test()
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()


class ConstantsTest(AuditHmacTestBase):

    def test_sizes(self):
        self.assertEqual(KEY_BYTES, 32)
        self.assertEqual(HMAC_BYTES, 32)
        self.assertEqual(HMAC_HEX_LEN, 64)

    def test_genesis_prev_is_zero_bytes(self):
        self.assertEqual(GENESIS_PREV, b"\x00" * 32)


class KillSwitchTest(AuditHmacTestBase):

    def test_is_disabled_default_false(self):
        self.assertFalse(is_disabled())

    def test_is_disabled_when_env_set(self):
        os.environ["CEO_AUDIT_HMAC_DISABLE"] = "1"
        self.assertTrue(is_disabled())

    def test_is_disabled_ignores_other_values(self):
        os.environ["CEO_AUDIT_HMAC_DISABLE"] = "true"
        self.assertFalse(is_disabled())


class KeyCreationTest(AuditHmacTestBase):

    def test_creates_32_bytes(self):
        key = get_or_create_key()
        self.assertEqual(len(key), KEY_BYTES)

    def test_creates_0600_perms(self):
        get_or_create_key()
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        mode = p.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_idempotent_across_calls(self):
        k1 = get_or_create_key()
        k2 = get_or_create_key()
        self.assertEqual(k1, k2)

    def test_reads_existing_key(self):
        # Pre-create key; library should read it, not regenerate.
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = bytes(range(32))
        p.write_bytes(payload)
        os.chmod(p, 0o600)
        self.assertEqual(get_or_create_key(), payload)

    def test_rejects_wrong_perms(self):
        # Write key with 0644 and expect AuditHmacError on get_or_create.
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x00" * 32)
        os.chmod(p, 0o644)
        with self.assertRaises(AuditHmacError) as cm:
            get_or_create_key()
        self.assertIn("unsafe perms", str(cm.exception))

    def test_rejects_wrong_size(self):
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x00" * 16)  # too small
        os.chmod(p, 0o600)
        with self.assertRaises(AuditHmacError) as cm:
            get_or_create_key()
        self.assertIn("bytes", str(cm.exception))


class HmacComputeTest(AuditHmacTestBase):

    def test_deterministic(self):
        key = get_or_create_key()
        entry = {"action": "agent_spawn", "ts": "2026-04-18T00:00:00Z"}
        h1 = compute_entry_hmac(key, GENESIS_PREV, entry)
        h2 = compute_entry_hmac(key, GENESIS_PREV, entry)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), HMAC_BYTES)

    def test_different_key_different_hmac(self):
        key1 = b"\x00" * 32
        key2 = b"\x11" * 32
        entry = {"a": 1}
        self.assertNotEqual(
            compute_entry_hmac(key1, GENESIS_PREV, entry),
            compute_entry_hmac(key2, GENESIS_PREV, entry),
        )

    def test_different_prev_different_hmac(self):
        key = b"\x00" * 32
        entry = {"a": 1}
        self.assertNotEqual(
            compute_entry_hmac(key, b"\x00" * 32, entry),
            compute_entry_hmac(key, b"\x01" * 32, entry),
        )

    def test_entry_bit_flip_breaks_hmac(self):
        key = b"\x00" * 32
        h_a = compute_entry_hmac(key, GENESIS_PREV, {"v": 1})
        h_b = compute_entry_hmac(key, GENESIS_PREV, {"v": 2})
        self.assertNotEqual(h_a, h_b)

    def test_rejects_short_key(self):
        with self.assertRaises(AuditHmacError):
            compute_entry_hmac(b"x" * 10, GENESIS_PREV, {"a": 1})

    def test_rejects_short_prev(self):
        with self.assertRaises(AuditHmacError):
            compute_entry_hmac(b"x" * 32, b"x" * 10, {"a": 1})


class ChainWalkTest(AuditHmacTestBase):
    """Simulate a 3-entry chain; verify each step re-computes correctly."""

    def _build_chain(self, key, entries):
        """Return list of (entry_copy_with_hmac, raw_hmac_bytes)."""
        out = []
        prev = GENESIS_PREV
        for entry in entries:
            h = compute_entry_hmac(key, prev, entry)
            entry_with = dict(entry)
            entry_with["hmac"] = h.hex()
            out.append((entry_with, h))
            prev = h
        return out

    def test_chain_of_three_verifies(self):
        key = get_or_create_key()
        entries = [{"n": 1}, {"n": 2}, {"n": 3}]
        chain = self._build_chain(key, entries)
        # Re-verify: recompute each using the previous raw hmac.
        prev = GENESIS_PREV
        for entry_with, h in chain:
            stripped = {k: v for k, v in entry_with.items() if k != "hmac"}
            recomputed = compute_entry_hmac(key, prev, stripped)
            self.assertEqual(recomputed, h)
            prev = h

    def test_tamper_detected(self):
        key = get_or_create_key()
        entries = [{"n": 1}, {"n": 2}, {"n": 3}]
        chain = self._build_chain(key, entries)
        # Tamper with entry 2 but keep its recorded hmac.
        entry_with, recorded_h = chain[1]
        tampered = {k: v for k, v in entry_with.items() if k != "hmac"}
        tampered["n"] = 99  # flipped value
        recomputed = compute_entry_hmac(key, chain[0][1], tampered)
        self.assertNotEqual(recomputed, recorded_h)

    def test_reorder_detected(self):
        key = get_or_create_key()
        entries = [{"n": 1}, {"n": 2}, {"n": 3}]
        chain = self._build_chain(key, entries)
        # Swap entry 1 and entry 2. After swap, the expected hmac for
        # new position[0] = compute(genesis, {"n":2}) != recorded[0].
        swapped_first = {k: v for k, v in chain[1][0].items() if k != "hmac"}
        recomputed = compute_entry_hmac(key, GENESIS_PREV, swapped_first)
        self.assertNotEqual(recomputed, chain[1][1])


class SidecarTest(AuditHmacTestBase):

    def test_read_missing_returns_genesis(self):
        self.assertEqual(read_prev_hmac(), GENESIS_PREV)

    def test_write_then_read_roundtrip(self):
        payload = bytes(range(32))
        write_last_hmac(payload)
        self.assertEqual(read_prev_hmac(), payload)

    def test_sidecar_file_is_0600(self):
        write_last_hmac(b"\x00" * 32)
        mode = last_hmac_path().stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_corrupt_sidecar_falls_back_to_genesis(self):
        p = last_hmac_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("not hex!!")
        self.assertEqual(read_prev_hmac(), GENESIS_PREV)

    def test_wrong_length_sidecar_falls_back_to_genesis(self):
        p = last_hmac_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("deadbeef")  # 8 chars, need 64
        self.assertEqual(read_prev_hmac(), GENESIS_PREV)

    def test_rotation_reset_clears_sidecar(self):
        write_last_hmac(b"\xaa" * 32)
        self.assertEqual(read_prev_hmac(), b"\xaa" * 32)
        reset_chain_on_rotation()
        self.assertEqual(read_prev_hmac(), GENESIS_PREV)

    def test_rotation_reset_missing_sidecar_is_noop(self):
        # reset_chain_on_rotation must not raise if the sidecar was
        # never written.
        reset_chain_on_rotation()  # should not raise
        self.assertEqual(read_prev_hmac(), GENESIS_PREV)

    def test_write_rejects_wrong_length(self):
        with self.assertRaises(AuditHmacError):
            write_last_hmac(b"\x00" * 16)


class HexHelpersTest(AuditHmacTestBase):

    def test_hex_digest_roundtrip(self):
        payload = bytes(range(32))
        self.assertEqual(from_hex(hex_digest(payload)), payload)

    def test_hex_digest_rejects_wrong_length(self):
        with self.assertRaises(AuditHmacError):
            hex_digest(b"\x00" * 16)

    def test_from_hex_rejects_wrong_length(self):
        with self.assertRaises(AuditHmacError):
            from_hex("deadbeef")

    def test_from_hex_rejects_non_hex(self):
        with self.assertRaises(AuditHmacError):
            from_hex("Z" * 64)


class KeyCacheTest(AuditHmacTestBase):

    def test_cache_hit_second_call(self):
        """Second call does NOT re-read the file.

        Covered by swapping the file content AFTER first call — the
        cached result should remain (module-level cache is the contract
        per performance-engineer review §3a).
        """
        k1 = get_or_create_key()
        # Overwrite on disk with a different 32-byte value (attacker
        # simulation).
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        p.write_bytes(b"\xff" * 32)
        os.chmod(p, 0o600)
        k2 = get_or_create_key()
        self.assertEqual(k1, k2)  # cached value returned

    def test_reset_cache_rereads(self):
        get_or_create_key()
        p = Path(os.environ["CEO_AUDIT_KEY_PATH"])
        p.write_bytes(b"\xff" * 32)
        os.chmod(p, 0o600)
        audit_hmac._reset_key_cache_for_test()
        self.assertEqual(get_or_create_key(), b"\xff" * 32)


if __name__ == "__main__":
    unittest.main()
