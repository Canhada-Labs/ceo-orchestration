"""PLAN-043 Phase 0.5 — _lib.audit_hmac.verify_chain unit tests.

Validates the library-level chain verification API extracted from
`.claude/scripts/audit-verify-chain.py::verify()` per Round 1 debate
convergent finding C-P0-7.

Covers:
- Happy-path chain verification
- Tamper detection (bit flip on recorded hmac)
- Tamper detection (bit flip on covered field)
- Transition-entry rule violation (hmac → no hmac)
- Malformed JSON line
- Malformed hmac field (wrong length)
- Missing key file
- Bad key perms
- Missing log file
- Empty log file
- Pre-v2.9 only log (no hmac entries)
- Mixed pre-v2.9 then CHAIN_ACTIVE transition
- Since-parameter skip-ahead
- Explicit key bytes override
- key_path_override parameter
- VerifyResult.is_intact property
- Status constants stable
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    GENESIS_PREV,
    HMAC_BYTES,
    KEY_BYTES,
    STATUS_INTACT,
    STATUS_KEY_MISSING,
    STATUS_MALFORMED,
    STATUS_PERM_ERROR,
    STATUS_TAMPER,
    VerifyResult,
    compute_entry_hmac,
    hex_digest,
    verify_chain,
)


class VerifyChainTestBase(unittest.TestCase):
    """Shared tmpdir + env isolation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(
            prefix="plan-043-verify-chain-"
        )
        self.tmp = Path(self._tmp.name)
        self._saved_env = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_KEY_PATH",
                "CEO_AUDIT_LAST_HMAC_PATH",
                "HOME",
                "CEO_PROJECT_STATE_DIR",
            )
        }
        self.log_path = self.tmp / "audit-log.jsonl"
        self.key_path = self.tmp / "audit-key"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log_path)
        os.environ["CEO_AUDIT_KEY_PATH"] = str(self.key_path)
        os.environ["CEO_AUDIT_LAST_HMAC_PATH"] = str(
            self.tmp / "audit-log.last-hmac"
        )
        audit_hmac._reset_key_cache_for_test()

        # Fixed test key (deterministic across runs).
        self.key = b"\x01" * KEY_BYTES
        self.key_path.write_bytes(self.key)
        os.chmod(self.key_path, 0o600)

    def tearDown(self):
        audit_hmac._reset_key_cache_for_test()
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def _append_entry(self, entry_without_hmac, prev_hmac):
        """Compute HMAC + write entry as JSONL line; return new prev."""
        digest = compute_entry_hmac(self.key, prev_hmac, entry_without_hmac)
        entry = dict(entry_without_hmac)
        entry["hmac"] = hex_digest(digest)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        return digest


class TestVerifyChainHappyPath(VerifyChainTestBase):
    def test_empty_log_intact(self):
        self.log_path.touch()
        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.status, STATUS_INTACT)
        self.assertEqual(result.verified_count, 0)
        self.assertEqual(result.pre_v29_count, 0)

    def test_single_entry_chain(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "test_one"},
            GENESIS_PREV,
        )
        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.verified_count, 1)

    def test_multi_entry_chain(self):
        prev = GENESIS_PREV
        for i in range(5):
            prev = self._append_entry(
                {"ts": "2026-04-19T00:00:0{}Z".format(i),
                 "action": "test_{}".format(i)},
                prev,
            )
        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.verified_count, 5)

    def test_empty_lines_skipped(self):
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:01Z", "action": "a"},
            GENESIS_PREV,
        )
        # Inject blank lines.
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write("\n\n   \n")
        self._append_entry(
            {"ts": "2026-04-19T00:00:02Z", "action": "b"},
            prev,
        )
        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.verified_count, 2)

    def test_result_has_expected_fields_on_intact(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "t"},
            GENESIS_PREV,
        )
        result = verify_chain(self.log_path, key=self.key)
        self.assertIsNone(result.line)
        self.assertIsNone(result.reason)
        self.assertIsNone(result.expected_hmac)


class TestVerifyChainTamper(VerifyChainTestBase):
    def test_bit_flip_on_recorded_hmac(self):
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "t"},
            GENESIS_PREV,
        )
        self._append_entry(
            {"ts": "2026-04-19T00:00:01Z", "action": "u"},
            prev,
        )
        # Corrupt the first entry's hmac.
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        flipped = list(entry["hmac"])
        flipped[0] = "f" if flipped[0] != "f" else "e"
        entry["hmac"] = "".join(flipped)
        lines[0] = json.dumps(entry, separators=(",", ":"))
        self.log_path.write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_TAMPER)
        self.assertEqual(result.line, 1)
        self.assertEqual(result.reason, "hmac_mismatch")
        self.assertIsNotNone(result.expected_hmac)
        self.assertIsNotNone(result.actual_hmac)

    def test_bit_flip_on_covered_field(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "original"},
            GENESIS_PREV,
        )
        # Flip the action field while keeping the HMAC.
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        entry["action"] = "tampered"
        lines[0] = json.dumps(entry, separators=(",", ":"))
        self.log_path.write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_TAMPER)
        self.assertEqual(result.reason, "hmac_mismatch")
        self.assertEqual(result.entry_action, "tampered")

    def test_transition_violation_hmac_then_no_hmac(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "first"},
            GENESIS_PREV,
        )
        # Append an entry WITHOUT an hmac field.
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"ts": "2026-04-19T00:00:01Z", "action": "no_hmac"}
            ) + "\n")

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_TAMPER)
        self.assertEqual(result.reason, "transition_violation")
        self.assertEqual(result.line, 2)
        self.assertEqual(result.entry_action, "no_hmac")


class TestVerifyChainMalformed(VerifyChainTestBase):
    def test_invalid_json_line(self):
        with self.log_path.open("w", encoding="utf-8") as f:
            f.write("not json at all\n")

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_MALFORMED)
        self.assertEqual(result.reason, "line_not_json")
        self.assertEqual(result.line, 1)

    def test_line_is_array_not_object(self):
        with self.log_path.open("w", encoding="utf-8") as f:
            f.write('["not", "an", "object"]\n')

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_MALFORMED)
        self.assertEqual(result.reason, "line_not_object")

    def test_hmac_field_wrong_length(self):
        entry = {
            "ts": "2026-04-19T00:00:00Z",
            "action": "bad",
            "hmac": "shorthex",
        }
        with self.log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_MALFORMED)
        self.assertEqual(result.reason, "hmac_field_malformed")
        self.assertEqual(result.actual_hmac, "shorthex")

    def test_hmac_field_non_string(self):
        entry = {
            "ts": "2026-04-19T00:00:00Z",
            "action": "bad",
            "hmac": 12345,
        }
        with self.log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        result = verify_chain(self.log_path, key=self.key)
        self.assertEqual(result.status, STATUS_MALFORMED)
        self.assertEqual(result.reason, "hmac_field_malformed")

    def test_missing_log_file(self):
        missing = self.tmp / "nonexistent.jsonl"
        result = verify_chain(missing, key=self.key)
        self.assertEqual(result.status, STATUS_MALFORMED)
        self.assertEqual(result.reason, "log_not_found")


class TestVerifyChainKeyHandling(VerifyChainTestBase):
    def test_explicit_key_bytes_overrides_all(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "t"},
            GENESIS_PREV,
        )
        # Pass a different (wrong) key via bytes → tamper at line 1.
        wrong_key = b"\x02" * KEY_BYTES
        result = verify_chain(self.log_path, key=wrong_key)
        self.assertEqual(result.status, STATUS_TAMPER)

    def test_key_path_override(self):
        # Write a second key file; verify_chain should use it.
        alt_key_path = self.tmp / "alt-key"
        alt_key_path.write_bytes(b"\x03" * KEY_BYTES)
        os.chmod(alt_key_path, 0o600)

        # Chain was signed with self.key (b'\x01'); alt_key (b'\x03')
        # should fail at line 1.
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "t"},
            GENESIS_PREV,
        )
        result = verify_chain(
            self.log_path, key_path_override=alt_key_path
        )
        self.assertEqual(result.status, STATUS_TAMPER)

    def test_missing_key_file(self):
        missing = self.tmp / "not-a-key"
        result = verify_chain(
            self.log_path, key_path_override=missing
        )
        self.assertEqual(result.status, STATUS_KEY_MISSING)
        self.assertEqual(result.reason, "key_not_found")

    def test_key_file_bad_perms(self):
        bad_perm_key = self.tmp / "bad-key"
        bad_perm_key.write_bytes(b"\x04" * KEY_BYTES)
        os.chmod(bad_perm_key, 0o644)  # group + world readable

        result = verify_chain(
            self.log_path, key_path_override=bad_perm_key
        )
        self.assertEqual(result.status, STATUS_PERM_ERROR)
        self.assertEqual(result.reason, "key_bad_perms")

    def test_key_bad_length(self):
        short_key = b"\x05" * 16  # half the required length
        result = verify_chain(
            self.log_path, key=short_key
        )
        self.assertEqual(result.status, STATUS_PERM_ERROR)
        self.assertEqual(result.reason, "key_bad_length")


class TestVerifyChainPreV29(VerifyChainTestBase):
    def test_pre_v29_only_entries_tolerated(self):
        # Entries without hmac field at head → CHAIN_START; tolerated.
        for i in range(3):
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": "2026-04-19T00:00:0{}Z".format(i),
                    "action": "legacy_{}".format(i),
                }) + "\n")

        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.verified_count, 0)
        self.assertEqual(result.pre_v29_count, 3)

    def test_pre_v29_then_chain_active_mixed(self):
        # 2 pre-v2.9 entries, then 2 CHAIN_ACTIVE entries.
        with self.log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": "2026-04-19T00:00:00Z", "action": "legacy1"
            }) + "\n")
            f.write(json.dumps({
                "ts": "2026-04-19T00:00:01Z", "action": "legacy2"
            }) + "\n")
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:02Z", "action": "active1"},
            GENESIS_PREV,
        )
        self._append_entry(
            {"ts": "2026-04-19T00:00:03Z", "action": "active2"},
            prev,
        )

        result = verify_chain(self.log_path, key=self.key)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.pre_v29_count, 2)
        self.assertEqual(result.verified_count, 2)


class TestVerifyChainSinceParameter(VerifyChainTestBase):
    def test_since_skips_head(self):
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "a"},
            GENESIS_PREV,
        )
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:01Z", "action": "b"},
            prev,
        )
        prev = self._append_entry(
            {"ts": "2026-04-19T00:00:02Z", "action": "c"},
            prev,
        )

        # Verify from line 2 — note: skip-ahead does NOT reset
        # prev_hmac to the correct value; result should flag tamper
        # or mismatch because prev starts at GENESIS_PREV but line 2
        # was computed from line 1's HMAC.
        result = verify_chain(self.log_path, key=self.key, since=2)
        self.assertEqual(result.status, STATUS_TAMPER)

    def test_since_beyond_eof_is_intact(self):
        self._append_entry(
            {"ts": "2026-04-19T00:00:00Z", "action": "a"},
            GENESIS_PREV,
        )
        # since=999 means we skip everything → vacuously intact.
        result = verify_chain(self.log_path, key=self.key, since=999)
        self.assertTrue(result.is_intact)
        self.assertEqual(result.verified_count, 0)


class TestVerifyResultShape(unittest.TestCase):
    def test_is_intact_property(self):
        self.assertTrue(
            VerifyResult(status=STATUS_INTACT).is_intact
        )
        self.assertFalse(
            VerifyResult(status=STATUS_TAMPER).is_intact
        )
        self.assertFalse(
            VerifyResult(status=STATUS_MALFORMED).is_intact
        )
        self.assertFalse(
            VerifyResult(status=STATUS_KEY_MISSING).is_intact
        )
        self.assertFalse(
            VerifyResult(status=STATUS_PERM_ERROR).is_intact
        )

    def test_status_constants_stable(self):
        # Regression guard: PLAN-043 loader imports these by name.
        self.assertEqual(STATUS_INTACT, "intact")
        self.assertEqual(STATUS_TAMPER, "tamper")
        self.assertEqual(STATUS_MALFORMED, "malformed")
        self.assertEqual(STATUS_KEY_MISSING, "key_missing")
        self.assertEqual(STATUS_PERM_ERROR, "perm_error")

    def test_dataclass_defaults(self):
        r = VerifyResult(status=STATUS_INTACT)
        self.assertEqual(r.verified_count, 0)
        self.assertEqual(r.pre_v29_count, 0)
        self.assertIsNone(r.line)
        self.assertIsNone(r.reason)


if __name__ == "__main__":
    unittest.main()
