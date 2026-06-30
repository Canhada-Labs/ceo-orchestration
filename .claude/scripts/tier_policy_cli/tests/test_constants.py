"""PLAN-043 Phase 1 — tier_policy._constants unit tests.

Guards:
- VETO_HARDCODE contents (code-reviewer + security-engineer → opus-4-7)
- Frozen SHA256 anchor byte-identity
- assert_veto_hardcode_integrity happy path + tamper detection
- Canonical JSON encoding stability across platforms
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli._constants import (  # noqa: E402
    VETO_HARDCODE,
    VETO_HARDCODE_FROZEN_SHA256,
    _compute_canonical_sha256,
    assert_veto_hardcode_integrity,
)


class TestVetoHardcode(unittest.TestCase):
    def test_veto_hardcode_has_both_roles(self):
        self.assertIn("code-reviewer", VETO_HARDCODE)
        self.assertIn("security-engineer", VETO_HARDCODE)

    def test_veto_hardcode_tiers_are_opus_4_7(self):
        # ADR-149 (PLAN-134 W0 variant A): VETO hardcode on the running
        # generation. Test name kept for history (ADR-052→142→149 lineage).
        self.assertEqual(VETO_HARDCODE["code-reviewer"], "claude-fable-5")
        self.assertEqual(VETO_HARDCODE["security-engineer"], "claude-fable-5")

    def test_veto_hardcode_has_exactly_two_keys(self):
        # Regression guard: if a third VETO role is added without
        # ADR-052 amendment, this test MUST be updated in the same PR.
        self.assertEqual(len(VETO_HARDCODE), 2)


class TestFrozenAnchor(unittest.TestCase):
    def test_frozen_sha256_is_64_hex_chars(self):
        self.assertEqual(len(VETO_HARDCODE_FROZEN_SHA256), 64)
        int(VETO_HARDCODE_FROZEN_SHA256, 16)  # Must be valid hex

    def test_frozen_sha256_matches_canonical(self):
        actual = _compute_canonical_sha256(VETO_HARDCODE)
        self.assertEqual(actual, VETO_HARDCODE_FROZEN_SHA256)

    def test_canonical_encoding_sorted_keys(self):
        # Stability: two dicts with same contents but different key
        # insertion order should produce identical hashes.
        d1 = {"security-engineer": "claude-opus-4-8", "code-reviewer": "claude-opus-4-8"}
        d2 = {"code-reviewer": "claude-opus-4-8", "security-engineer": "claude-opus-4-8"}
        self.assertEqual(
            _compute_canonical_sha256(d1),
            _compute_canonical_sha256(d2),
        )


class TestIntegrityAssertion(unittest.TestCase):
    def test_happy_path(self):
        # assert_veto_hardcode_integrity(VETO_HARDCODE) should NOT raise
        try:
            assert_veto_hardcode_integrity(dict(VETO_HARDCODE))
        except AssertionError:
            self.fail("Byte-identity assertion raised on untampered dict")

    def test_tamper_demote_code_reviewer(self):
        tampered = dict(VETO_HARDCODE)
        tampered["code-reviewer"] = "claude-sonnet-4-6"
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity(tampered)

    def test_tamper_remove_security_engineer(self):
        tampered = dict(VETO_HARDCODE)
        del tampered["security-engineer"]
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity(tampered)

    def test_tamper_empty_dict(self):
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity({})

    def test_tamper_add_new_role(self):
        tampered = dict(VETO_HARDCODE)
        tampered["attacker-added-role"] = "claude-haiku-4-5-20251001"
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity(tampered)

    def test_custom_frozen_sha256_override(self):
        # apply.py uses its own frozen constant (defense in depth).
        # Verify override parameter works.
        other = {"only-role": "claude-opus-4-8"}
        other_sha = _compute_canonical_sha256(other)
        # Correct anchor → passes
        try:
            assert_veto_hardcode_integrity(other, frozen_sha256=other_sha)
        except AssertionError:
            self.fail("Override anchor failed on matching dict")
        # Wrong anchor → raises
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity(
                other, frozen_sha256="0" * 64
            )


if __name__ == "__main__":
    unittest.main()
