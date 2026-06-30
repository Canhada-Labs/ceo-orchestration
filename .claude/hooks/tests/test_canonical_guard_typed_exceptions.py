"""PLAN-086 Wave F.1 — Typed exception hierarchy tests.

Verifies the 5 typed exception classes exist with correct inheritance +
carry stable `reason` attribute. 10 cases.

veto_case: B (auth/crypto). Cite ADR-040 §6.3 + RFC 9449.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.mcp import canonical_guard  # noqa: E402


class TestExceptionHierarchy(unittest.TestCase):
    """5 classes — class shape + inheritance."""

    def test_canonical_guard_error_is_base(self) -> None:
        self.assertTrue(issubclass(canonical_guard.CanonicalGuardError, Exception))
        exc = canonical_guard.CanonicalGuardError("test_reason")
        self.assertEqual(exc.reason, "test_reason")
        self.assertEqual(str(exc), "test_reason")
        exc2 = canonical_guard.CanonicalGuardError("r", "human msg")
        self.assertEqual(exc2.reason, "r")
        self.assertEqual(str(exc2), "human msg")

    def test_kill_switch_active_subclass(self) -> None:
        self.assertTrue(issubclass(
            canonical_guard.KillSwitchActive,
            canonical_guard.CanonicalGuardError,
        ))
        exc = canonical_guard.KillSwitchActive("kill_switch_tripped")
        self.assertIsInstance(exc, canonical_guard.CanonicalGuardError)
        self.assertEqual(exc.reason, "kill_switch_tripped")

    def test_path_outside_allowlist_subclass(self) -> None:
        self.assertTrue(issubclass(
            canonical_guard.PathOutsideAllowlist,
            canonical_guard.CanonicalGuardError,
        ))
        exc = canonical_guard.PathOutsideAllowlist(
            canonical_guard._REASON_PATH_ESCAPES_REPO,
        )
        self.assertIsInstance(exc, canonical_guard.CanonicalGuardError)
        self.assertEqual(exc.reason, canonical_guard._REASON_PATH_ESCAPES_REPO)

    def test_invalid_patch_blob_subclass(self) -> None:
        self.assertTrue(issubclass(
            canonical_guard.InvalidPatchBlob,
            canonical_guard.CanonicalGuardError,
        ))
        exc = canonical_guard.InvalidPatchBlob(
            canonical_guard._REASON_BLOB_AUTH_PARSE_FAILED,
        )
        self.assertIsInstance(exc, canonical_guard.CanonicalGuardError)

    def test_policy_violation_subclass(self) -> None:
        self.assertTrue(issubclass(
            canonical_guard.PolicyViolation,
            canonical_guard.CanonicalGuardError,
        ))
        exc = canonical_guard.PolicyViolation(
            canonical_guard._REASON_CANONICAL_NO_SENTINEL,
        )
        self.assertIsInstance(exc, canonical_guard.CanonicalGuardError)


class TestStrictModeRaise(unittest.TestCase):
    """5 classes — strict-mode raisability."""

    def test_strict_raise_disabled_by_default(self) -> None:
        import os
        os.environ.pop("CANONICAL_GUARD_STRICT_RAISE", None)
        self.assertFalse(canonical_guard._strict_raise_enabled())

    def test_strict_raise_enabled_by_env_var(self) -> None:
        import os
        os.environ["CANONICAL_GUARD_STRICT_RAISE"] = "1"
        try:
            self.assertTrue(canonical_guard._strict_raise_enabled())
        finally:
            os.environ.pop("CANONICAL_GUARD_STRICT_RAISE", None)

    def test_kill_switch_active_raisable(self) -> None:
        with self.assertRaises(canonical_guard.KillSwitchActive):
            raise canonical_guard.KillSwitchActive("test")

    def test_path_outside_allowlist_raisable(self) -> None:
        with self.assertRaises(canonical_guard.PathOutsideAllowlist):
            raise canonical_guard.PathOutsideAllowlist(
                canonical_guard._REASON_PATH_ESCAPES_REPO,
            )

    def test_invalid_patch_blob_raisable(self) -> None:
        with self.assertRaises(canonical_guard.InvalidPatchBlob):
            raise canonical_guard.InvalidPatchBlob(
                canonical_guard._REASON_BLOB_AUTH_PARSE_FAILED,
            )

    def test_policy_violation_raisable_and_caught_as_base(self) -> None:
        with self.assertRaises(canonical_guard.CanonicalGuardError) as ctx:
            raise canonical_guard.PolicyViolation(
                canonical_guard._REASON_CANONICAL_NO_SENTINEL,
                "canonical path lacks sentinel grant",
            )
        self.assertEqual(ctx.exception.reason, canonical_guard._REASON_CANONICAL_NO_SENTINEL)


if __name__ == "__main__":
    unittest.main()
