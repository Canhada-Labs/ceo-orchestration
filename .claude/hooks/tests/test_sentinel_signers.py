"""Unit tests for _lib/sentinel_signers.py (PLAN-089 Wave C.2).

Coverage targets (per plan section 7, >=30 cases):

- is_valid_signer: valid / unknown / revoked / expired (with precedence) /
  boundary STRICT > / malformed fpr / _now injection
- quorum_verify: met / short / overshoot / duplicate-signer collusion /
  hot-key in cold-quorum / unknown-signer / revoked-signer / expired-signer /
  empty signatures / invalid threshold
- load_registry: YAML happy-path / JSON fallback / missing file /
  malformed YAML (both) / duplicate signer / extra unknown fields /
  missing required field / malformed datetime / hot+cold mix
- multi-quorum: 2 calls in same session don't share state
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
import unittest
from pathlib import Path

# Ensure `.claude/hooks/` is on sys.path so `from _lib.sentinel_signers ...`
# resolves under both pytest (conftest handles it) and direct unittest.
_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import sentinel_signers as ss  # noqa: E402

from _lib.testing import TestEnvContext  # noqa: E402


UTC = _dt.timezone.utc


# Three reference 40-hex fingerprints (uppercase, no spaces).
HOT_OWNER = "0000000000000000000000000000000000000000"
COLD_A = "AAAA1111BBBB2222CCCC3333DDDD4444EEEE5555"
COLD_B = "BBBB1111CCCC2222DDDD3333EEEE4444FFFF5555"
COLD_C = "CCCC1111DDDD2222EEEE3333FFFF4444AAAA5555"


def _ts(year: int, month: int, day: int) -> _dt.datetime:
    return _dt.datetime(year, month, day, 0, 0, 0, tzinfo=UTC)


def _make_registry() -> dict:
    """Build a 4-entry registry: 1 hot + 3 cold, all not-yet-expired."""
    return {
        HOT_OWNER: ss.SignerRecord(
            key_id=HOT_OWNER,
            key_type="hot",
            created_at=_ts(2026, 1, 1),
            expires_at=_ts(2027, 6, 1),
        ),
        COLD_A: ss.SignerRecord(
            key_id=COLD_A,
            key_type="cold",
            created_at=_ts(2026, 1, 1),
            expires_at=_ts(2028, 1, 1),
        ),
        COLD_B: ss.SignerRecord(
            key_id=COLD_B,
            key_type="cold",
            created_at=_ts(2026, 1, 1),
            expires_at=_ts(2028, 1, 1),
        ),
        COLD_C: ss.SignerRecord(
            key_id=COLD_C,
            key_type="cold",
            created_at=_ts(2026, 1, 1),
            expires_at=_ts(2028, 1, 1),
        ),
    }


class TestIsValidSigner(TestEnvContext):
    """is_valid_signer single-signer validity gate."""

    def setUp(self) -> None:
        super().setUp()
        self.registry = _make_registry()
        self.now = _ts(2026, 5, 13)

    def test_valid_hot_signer_passes(self):
        ok, reason = ss.is_valid_signer(
            HOT_OWNER, now=self.now, registry=self.registry
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")

    def test_valid_cold_signer_passes(self):
        ok, reason = ss.is_valid_signer(
            COLD_A, now=self.now, registry=self.registry
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")

    def test_unknown_signer_fails(self):
        ok, reason = ss.is_valid_signer(
            "F" * 40, now=self.now, registry=self.registry
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "unknown_key")

    def test_empty_registry_fails(self):
        ok, reason = ss.is_valid_signer(
            HOT_OWNER, now=self.now, registry={}
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "unknown_key")

    def test_none_registry_fails(self):
        ok, reason = ss.is_valid_signer(
            HOT_OWNER, now=self.now, registry=None
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "unknown_key")

    def test_revoked_signer_fails(self):
        reg = _make_registry()
        reg[COLD_A].revoked_at = _ts(2026, 4, 1)
        ok, reason = ss.is_valid_signer(
            COLD_A, now=self.now, registry=reg
        )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("revoked:"))
        # Embeds the revocation timestamp.
        self.assertIn("2026-04-01T00:00:00", reason)

    def test_expired_signer_fails(self):
        reg = _make_registry()
        reg[COLD_A].expires_at = _ts(2026, 4, 1)
        ok, reason = ss.is_valid_signer(
            COLD_A, now=self.now, registry=reg
        )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("expired:"))
        self.assertIn("2026-04-01T00:00:00", reason)

    def test_expires_at_exactly_now_is_expired_strict_gt(self):
        """STRICT > boundary: at exactly expires_at the key is expired."""
        reg = _make_registry()
        reg[COLD_A].expires_at = self.now
        ok, reason = ss.is_valid_signer(
            COLD_A, now=self.now, registry=reg
        )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("expired:"))

    def test_revoked_and_expired_revoked_wins(self):
        """Precedence: revocation reason wins when both apply."""
        reg = _make_registry()
        reg[COLD_A].expires_at = _ts(2026, 4, 1)
        reg[COLD_A].revoked_at = _ts(2026, 4, 2)
        ok, reason = ss.is_valid_signer(
            COLD_A, now=self.now, registry=reg
        )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("revoked:"))
        self.assertNotIn("expired", reason)

    def test_now_injection_default_is_utc_now(self):
        """Default now=None should NOT raise (uses _utc_now under the hood)."""
        # Use a registry whose Owner key won't be expired any time soon.
        reg = _make_registry()
        reg[HOT_OWNER].expires_at = _dt.datetime.now(UTC) + _dt.timedelta(
            days=365
        )
        ok, reason = ss.is_valid_signer(HOT_OWNER, registry=reg)
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")

    def test_now_injection_custom_future_datetime(self):
        """Custom future `now` should make a near-expiry signer expired."""
        reg = _make_registry()
        reg[COLD_A].expires_at = _ts(2026, 6, 1)
        ok, _ = ss.is_valid_signer(
            COLD_A, now=_ts(2026, 7, 1), registry=reg
        )
        self.assertFalse(ok)

    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            ss.is_valid_signer(
                COLD_A,
                now=_dt.datetime(2026, 5, 13, 0, 0, 0),
                registry=self.registry,
            )

    def test_malformed_fpr_treated_as_unknown(self):
        ok, reason = ss.is_valid_signer(
            "not-a-fingerprint", now=self.now, registry=self.registry
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "unknown_key")

    def test_fpr_with_whitespace_normalised(self):
        spaced = "00000000 00000000 00000000 00000000 00000000"
        ok, reason = ss.is_valid_signer(
            spaced, now=self.now, registry=self.registry
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")

    def test_fpr_lowercase_normalised(self):
        ok, reason = ss.is_valid_signer(
            HOT_OWNER.lower(), now=self.now, registry=self.registry
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")


class TestQuorumVerify(TestEnvContext):
    """quorum_verify N-of-M cold-key cardinality + distinct + validity."""

    def setUp(self) -> None:
        super().setUp()
        self.registry = _make_registry()
        self.now = _ts(2026, 5, 13)

    def _sig(self, key_id: str) -> ss.Signature:
        return ss.Signature(key_id=key_id, sig_bytes=b"opaque")

    def test_quorum_2_of_3_met(self):
        sigs = [self._sig(COLD_A), self._sig(COLD_B)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertTrue(met)
        self.assertEqual(reason, "quorum_met:2")

    def test_quorum_1_of_3_short(self):
        sigs = [self._sig(COLD_A)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertEqual(reason, "quorum_short:got=1;need=2")

    def test_quorum_3_of_3_overshoot_passes(self):
        """Threshold = 2, providing 3 distinct valid cold signatures."""
        sigs = [self._sig(COLD_A), self._sig(COLD_B), self._sig(COLD_C)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertTrue(met)
        self.assertEqual(reason, "quorum_met:3")

    def test_quorum_duplicate_signer_rejected_collusion(self):
        """R1 IDA P1 fold — duplicate-signer collusion case."""
        sigs = [self._sig(COLD_A), self._sig(COLD_A)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertTrue(reason.startswith("duplicate_signer:"))
        self.assertIn(COLD_A, reason)

    def test_quorum_duplicate_signer_normalised_keys(self):
        """Duplicate detection works across case/whitespace normalisation."""
        sigs = [
            self._sig(COLD_A),
            self._sig(COLD_A.lower()),
        ]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertTrue(reason.startswith("duplicate_signer:"))

    def test_quorum_hot_key_in_cold_quorum_rejected(self):
        """Hot key MUST NOT count toward cold-key quorum."""
        sigs = [self._sig(COLD_A), self._sig(HOT_OWNER)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertTrue(reason.startswith("wrong_key_type:"))
        self.assertIn(HOT_OWNER, reason)

    def test_quorum_unknown_signer_rejected(self):
        sigs = [self._sig(COLD_A), self._sig("F" * 40)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertIn("unknown_key", reason)

    def test_quorum_revoked_signer_rejected(self):
        reg = _make_registry()
        reg[COLD_A].revoked_at = _ts(2026, 4, 1)
        sigs = [self._sig(COLD_A), self._sig(COLD_B)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=reg
        )
        self.assertFalse(met)
        self.assertIn("revoked", reason)

    def test_quorum_expired_signer_rejected(self):
        reg = _make_registry()
        reg[COLD_A].expires_at = _ts(2026, 4, 1)
        sigs = [self._sig(COLD_A), self._sig(COLD_B)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=reg
        )
        self.assertFalse(met)
        self.assertIn("expired", reason)

    def test_quorum_empty_signatures(self):
        met, reason = ss.quorum_verify(
            [], threshold=2, now=self.now, registry=self.registry
        )
        self.assertFalse(met)
        self.assertEqual(reason, "empty_signatures")

    def test_quorum_threshold_zero_rejected(self):
        met, reason = ss.quorum_verify(
            [self._sig(COLD_A)],
            threshold=0,
            now=self.now,
            registry=self.registry,
        )
        self.assertFalse(met)
        self.assertEqual(reason, "threshold_invalid")

    def test_quorum_threshold_negative_rejected(self):
        met, reason = ss.quorum_verify(
            [self._sig(COLD_A)],
            threshold=-1,
            now=self.now,
            registry=self.registry,
        )
        self.assertFalse(met)
        self.assertEqual(reason, "threshold_invalid")

    def test_quorum_isolated_across_calls(self):
        """Two consecutive quorum_verify calls must not share state."""
        sigs1 = [self._sig(COLD_A), self._sig(COLD_B)]
        met1, _ = ss.quorum_verify(
            sigs1, threshold=2, now=self.now, registry=self.registry
        )
        # First call should have passed.
        self.assertTrue(met1)
        # Re-using the same cold keys in a 2nd call MUST still pass —
        # the duplicate-signer check is per-call, not session-wide.
        sigs2 = [self._sig(COLD_A), self._sig(COLD_C)]
        met2, reason2 = ss.quorum_verify(
            sigs2, threshold=2, now=self.now, registry=self.registry
        )
        self.assertTrue(met2)
        self.assertEqual(reason2, "quorum_met:2")

    def test_quorum_none_registry_unknown(self):
        sigs = [self._sig(COLD_A), self._sig(COLD_B)]
        met, reason = ss.quorum_verify(
            sigs, threshold=2, now=self.now, registry=None
        )
        self.assertFalse(met)
        self.assertIn("unknown_key", reason)


class TestLoadRegistry(TestEnvContext):
    """load_registry YAML/JSON parsing + invariant checks."""

    def _yaml_path(self, content: str) -> Path:
        p = Path(self.project_dir) / "registry.yaml"
        p.write_text(content, encoding="utf-8")
        return p

    def _json_path(self, content: str) -> Path:
        p = Path(self.project_dir) / "registry.json"
        p.write_text(content, encoding="utf-8")
        return p

    def test_yaml_simple_registry_parses(self):
        yaml = (
            "# Registry header comment\n"
            "signers:\n"
            "  - key_id: " + HOT_OWNER + "\n"
            "    key_type: hot\n"
            "    created_at: 2026-01-01T00:00:00Z\n"
            "    expires_at: 2027-06-01T00:00:00Z\n"
            "    revoked_at: null\n"
            "    notes: \"Owner hot key\"\n"
            "  - key_id: " + COLD_A + "\n"
            "    key_type: cold\n"
            "    created_at: 2026-01-01T00:00:00Z\n"
            "    expires_at: 2028-01-01T00:00:00Z\n"
            "    notes: \"Cold A\"\n"
        )
        path = self._yaml_path(yaml)
        reg = ss.load_registry(path)
        self.assertIn(HOT_OWNER, reg)
        self.assertIn(COLD_A, reg)
        self.assertEqual(reg[HOT_OWNER].key_type, "hot")
        self.assertEqual(reg[COLD_A].key_type, "cold")
        self.assertEqual(reg[HOT_OWNER].notes, "Owner hot key")
        self.assertIsNone(reg[HOT_OWNER].revoked_at)
        self.assertEqual(
            reg[HOT_OWNER].expires_at.year, 2027
        )

    def test_yaml_with_inline_comments_parses(self):
        yaml = (
            "signers:\n"
            "  - key_id: " + COLD_A + "  # primary cold key\n"
            "    key_type: cold\n"
            "    created_at: 2026-01-01T00:00:00Z\n"
            "    expires_at: 2028-01-01T00:00:00Z\n"
        )
        reg = ss.load_registry(self._yaml_path(yaml))
        self.assertIn(COLD_A, reg)

    def test_yaml_with_revoked_at_set_parses(self):
        yaml = (
            "signers:\n"
            "  - key_id: " + COLD_A + "\n"
            "    key_type: cold\n"
            "    created_at: 2026-01-01T00:00:00Z\n"
            "    expires_at: 2028-01-01T00:00:00Z\n"
            "    revoked_at: 2026-04-15T12:00:00Z\n"
        )
        reg = ss.load_registry(self._yaml_path(yaml))
        rec = reg[COLD_A]
        self.assertIsNotNone(rec.revoked_at)
        self.assertEqual(rec.revoked_at.month, 4)

    def test_json_fallback_when_yaml_unparseable(self):
        """Malformed YAML should fall through to JSON if JSON parses."""
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "cold",
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                    "revoked_at": None,
                    "notes": "JSON shape",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        reg = ss.load_registry(path)
        self.assertIn(COLD_A, reg)
        self.assertEqual(reg[COLD_A].notes, "JSON shape")

    def test_missing_file_raises_file_not_found(self):
        path = Path(self.project_dir) / "does-not-exist.yaml"
        with self.assertRaises(FileNotFoundError):
            ss.load_registry(path)

    def test_neither_yaml_nor_json_parses_raises(self):
        path = self._yaml_path("this is not @ valid \xff yaml or json {[")
        with self.assertRaises(ss.RegistryParseError):
            ss.load_registry(path)

    def test_root_missing_signers_key_raises(self):
        path = self._yaml_path("foo: bar\n")
        with self.assertRaises(ss.RegistryParseError):
            ss.load_registry(path)

    def test_signers_not_a_list_raises(self):
        path = self._json_path(json.dumps({"signers": "not-a-list"}))
        with self.assertRaises(ss.RegistryParseError):
            ss.load_registry(path)

    def test_duplicate_signer_rejected_at_load(self):
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "cold",
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                },
                {
                    "key_id": COLD_A,  # duplicate
                    "key_type": "cold",
                    "created_at": "2026-02-01T00:00:00Z",
                    "expires_at": "2028-02-01T00:00:00Z",
                },
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError) as ctx:
            ss.load_registry(path)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_missing_required_field_rejected(self):
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    # missing key_type
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError) as ctx:
            ss.load_registry(path)
        self.assertIn("key_type", str(ctx.exception))

    def test_invalid_key_type_rejected(self):
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "warm",  # not hot|cold
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError) as ctx:
            ss.load_registry(path)
        self.assertIn("hot|cold", str(ctx.exception))

    def test_malformed_datetime_rejected(self):
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "cold",
                    "created_at": "not-a-date",
                    "expires_at": "2028-01-01T00:00:00Z",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError) as ctx:
            ss.load_registry(path)
        self.assertIn("datetime", str(ctx.exception).lower())

    def test_naive_datetime_rejected(self):
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "cold",
                    "created_at": "2026-01-01T00:00:00",  # no tz
                    "expires_at": "2028-01-01T00:00:00Z",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError) as ctx:
            ss.load_registry(path)
        self.assertIn("naive", str(ctx.exception).lower())

    def test_invalid_key_id_rejected(self):
        payload = {
            "signers": [
                {
                    "key_id": "not-40-hex",
                    "key_type": "cold",
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        with self.assertRaises(ss.RegistryParseError):
            ss.load_registry(path)

    def test_extra_unknown_fields_ignored_forward_compat(self):
        """Forward-compat: future schema fields must not break old parsers."""
        payload = {
            "signers": [
                {
                    "key_id": COLD_A,
                    "key_type": "cold",
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2028-01-01T00:00:00Z",
                    "future_field_v3": "ignored",
                    "another_future": {"nested": "value"},
                }
            ]
        }
        path = self._json_path(json.dumps(payload))
        reg = ss.load_registry(path)
        self.assertIn(COLD_A, reg)
        # Forward-compat fields silently dropped from the dataclass.

    def test_yaml_with_quoted_keys_and_z_suffix(self):
        yaml = (
            "signers:\n"
            "  - key_id: \"" + COLD_A + "\"\n"
            "    key_type: \"cold\"\n"
            "    created_at: \"2026-01-01T00:00:00Z\"\n"
            "    expires_at: \"2028-01-01T00:00:00Z\"\n"
        )
        reg = ss.load_registry(self._yaml_path(yaml))
        self.assertIn(COLD_A, reg)

    def test_registry_round_trip_with_is_valid_signer(self):
        """Loaded registry must work end-to-end with is_valid_signer."""
        yaml = (
            "signers:\n"
            "  - key_id: " + COLD_A + "\n"
            "    key_type: cold\n"
            "    created_at: 2026-01-01T00:00:00Z\n"
            "    expires_at: 2028-01-01T00:00:00Z\n"
        )
        reg = ss.load_registry(self._yaml_path(yaml))
        ok, reason = ss.is_valid_signer(
            COLD_A, now=_ts(2026, 5, 13), registry=reg
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "valid")


class TestSignerDataclasses(TestEnvContext):
    """SignerRecord / Signature dataclass smoke tests."""

    def test_signer_record_defaults(self):
        rec = ss.SignerRecord(
            key_id=COLD_A,
            key_type="cold",
            created_at=_ts(2026, 1, 1),
            expires_at=_ts(2028, 1, 1),
        )
        self.assertIsNone(rec.revoked_at)
        self.assertEqual(rec.notes, "")

    def test_signature_defaults_empty_bytes(self):
        sig = ss.Signature(key_id=COLD_A)
        self.assertEqual(sig.sig_bytes, b"")

    def test_signature_carries_opaque_bytes(self):
        sig = ss.Signature(key_id=COLD_A, sig_bytes=b"\x01\x02\x03")
        self.assertEqual(sig.sig_bytes, b"\x01\x02\x03")


if __name__ == "__main__":
    unittest.main()
