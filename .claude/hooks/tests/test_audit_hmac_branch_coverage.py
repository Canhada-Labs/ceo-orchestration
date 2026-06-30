"""Real-fs branch-coverage tests for ``_lib.audit_hmac`` (Session 71 cont³).

Closes audit-v2 P1 #7 audit_hmac.py portion remaining 2-3pp gap.
Wave D-4 Round 1 debate consensus: real-fs only (no mocks). These tests
target specific OSError + format-validation branches that the existing
v2.14 coverage suite doesn't exercise.

Targeted missing lines (per coverage report 2026-04-28, audit_hmac at
84% pre-this-file):

- 226: ``_check_parent_dir_owned_0700`` parent-not-a-directory branch
- 240: parent-perms-wrong branch (mode != 0o700)
- 345-346: ``read_prev_hmac`` OSError on read_text -> genesis fallback
- 351-352: ``read_prev_hmac`` ValueError on fromhex -> genesis fallback
- 383-391: ``write_last_hmac`` OSError on outer write -> AuditHmacError
- 413-416: ``reset_chain_on_rotation`` OSError swallowed best-effort

Stdlib-only. Real filesystem operations under TestEnvContext-managed
tmpdirs.
"""
from __future__ import annotations

import os
import stat as stat_mod
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_hmac  # noqa: E402


class CheckParentDirOwned0700Tests(TestEnvContext):
    """Branch coverage for ``_check_parent_dir_owned_0700``."""

    def test_raises_when_parent_is_a_regular_file(self) -> None:
        """Line 226: parent path exists but is a file, not a directory."""
        # Make `audit_dir/not-a-dir` a regular file, then ask the helper
        # to validate `audit_dir/not-a-dir/audit-key` (parent = file).
        sentinel = self.audit_dir / "not-a-dir"
        sentinel.write_text("placeholder", encoding="utf-8")
        target = sentinel / "audit-key"  # parent of target is the file
        with self.assertRaises(audit_hmac.AuditHmacError) as ctx:
            audit_hmac._check_parent_dir_owned_0700(target)
        # Implementation walks .is_symlink() then .is_dir(); on macOS a
        # path under a regular-file parent surfaces as "not a directory"
        # via either .is_dir() False OR an OSError on stat. Both paths
        # raise AuditHmacError; we accept either message.
        msg = str(ctx.exception).lower()
        self.assertTrue(
            "not a directory" in msg or "stat failed" in msg,
            "unexpected error: {m}".format(m=msg),
        )

    def test_raises_when_parent_perms_not_0700(self) -> None:
        """Line 240: parent dir mode != 0o700 (e.g. 0o755)."""
        parent = self.audit_dir / "wrong-perms-dir"
        parent.mkdir(mode=0o755)
        try:
            target = parent / "audit-key"
            with self.assertRaises(audit_hmac.AuditHmacError) as ctx:
                audit_hmac._check_parent_dir_owned_0700(target)
            self.assertIn("must be 0700", str(ctx.exception))
        finally:
            parent.chmod(0o700)  # restore so tearDown can clean


class ReadPrevHmacFallbackTests(TestEnvContext):
    """Branch coverage for ``read_prev_hmac`` graceful-degradation paths."""

    def setUp(self) -> None:
        super().setUp()
        # Wire sidecar under audit_dir.
        os.environ.update({
            "CEO_AUDIT_LAST_HMAC_PATH": str(self.audit_dir / "last-hmac"),
        })

    def test_returns_genesis_when_sidecar_unreadable(self) -> None:
        """Lines 345-346: OSError on read_text -> GENESIS_PREV."""
        sidecar = audit_hmac.last_hmac_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sidecar.write_text("a" * audit_hmac.HMAC_HEX_LEN, encoding="utf-8")
        sidecar.chmod(0o000)  # owner can't read either
        try:
            result = audit_hmac.read_prev_hmac()
            self.assertEqual(result, audit_hmac.GENESIS_PREV)
        finally:
            sidecar.chmod(0o600)  # restore for tearDown

    def test_returns_genesis_when_sidecar_invalid_hex(self) -> None:
        """Lines 351-352: ValueError on fromhex -> GENESIS_PREV.

        The pre-fromhex length check (line 347-348) requires exactly
        HMAC_HEX_LEN chars. To reach the fromhex ValueError branch we
        need a string of correct length but with non-hex chars.
        """
        sidecar = audit_hmac.last_hmac_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        non_hex = "Z" * audit_hmac.HMAC_HEX_LEN  # right length, bad chars
        sidecar.write_text(non_hex, encoding="utf-8")
        result = audit_hmac.read_prev_hmac()
        self.assertEqual(result, audit_hmac.GENESIS_PREV)


class WriteLastHmacErrorTests(TestEnvContext):
    """Branch coverage for ``write_last_hmac`` OSError path."""

    def setUp(self) -> None:
        super().setUp()
        # Wire sidecar under audit_dir.
        os.environ.update({
            "CEO_AUDIT_LAST_HMAC_PATH": str(self.audit_dir / "last-hmac"),
        })

    def test_raises_audit_error_on_unwritable_parent(self) -> None:
        """Lines 385-393: OSError on outer write -> AuditHmacError.

        Approach: point sidecar at a path under a parent dir we make
        read-only (0o500). mkdir(exist_ok=True) succeeds (no-op since
        parent exists), but the open(tmp, "w") fails with EACCES, and
        the resulting OSError is caught and re-raised as AuditHmacError.
        """
        ro_parent = self.audit_dir / "ro-parent"
        ro_parent.mkdir(mode=0o700, exist_ok=True)
        os.environ.update({
            "CEO_AUDIT_LAST_HMAC_PATH": str(ro_parent / "last-hmac"),
        })
        # First write succeeds (so the file exists with proper perms).
        digest = bytes.fromhex("a" * audit_hmac.HMAC_HEX_LEN)
        audit_hmac.write_last_hmac(digest)
        # Make parent un-writable.
        ro_parent.chmod(0o500)
        try:
            with self.assertRaises(audit_hmac.AuditHmacError) as ctx:
                audit_hmac.write_last_hmac(digest)
            self.assertIn("could not write", str(ctx.exception))
        finally:
            ro_parent.chmod(0o700)


class ResetChainOnRotationTests(TestEnvContext):
    """Branch coverage for ``reset_chain_on_rotation`` best-effort unlink."""

    def setUp(self) -> None:
        super().setUp()
        os.environ.update({
            "CEO_AUDIT_LAST_HMAC_PATH": str(self.audit_dir / "last-hmac"),
            "CEO_AUDIT_CHAIN_LENGTH_PATH": str(self.audit_dir / "chain-length"),
        })

    def test_swallows_oserror_when_unlink_fails(self) -> None:
        """Lines 413-416: OSError on unlink swallowed best-effort.

        Approach: place sidecar in a parent dir whose mode prevents
        unlink (mode 0o500 = read+execute, no write). On macOS the
        unlink fails with EACCES; the helper swallows + continues.
        """
        ro_parent = self.audit_dir / "rotation-ro-parent"
        ro_parent.mkdir(mode=0o700, exist_ok=True)
        # Wire BOTH sidecars under this RO parent.
        os.environ.update({
            "CEO_AUDIT_LAST_HMAC_PATH": str(ro_parent / "last-hmac"),
            "CEO_AUDIT_CHAIN_LENGTH_PATH": str(ro_parent / "chain-length"),
        })
        # Create both sidecars.
        digest = bytes.fromhex("b" * audit_hmac.HMAC_HEX_LEN)
        audit_hmac.write_last_hmac(digest)
        audit_hmac.write_chain_length(7)
        # Make parent un-writable so unlink fails.
        ro_parent.chmod(0o500)
        try:
            # Should NOT raise — best-effort swallow.
            audit_hmac.reset_chain_on_rotation()
        finally:
            ro_parent.chmod(0o700)


class ChainLengthMalformedTests(TestEnvContext):
    """Branch coverage for ``read_chain_length`` corrupt-sidecar paths.

    The canary is wired in production emitters as of Wave D-2; these
    tests cover the read-side fail-open invariant.
    """

    def setUp(self) -> None:
        super().setUp()
        os.environ.update({
            "CEO_AUDIT_CHAIN_LENGTH_PATH": str(self.audit_dir / "chain-length"),
        })

    def test_returns_zero_when_sidecar_unreadable(self) -> None:
        """``read_chain_length`` OSError on read_text -> 0."""
        sidecar = audit_hmac.chain_length_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sidecar.write_text("42", encoding="utf-8")
        sidecar.chmod(0o000)
        try:
            self.assertEqual(audit_hmac.read_chain_length(), 0)
        finally:
            sidecar.chmod(0o600)

    def test_returns_zero_when_sidecar_negative(self) -> None:
        """``read_chain_length`` returns 0 for negative integer values."""
        sidecar = audit_hmac.chain_length_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sidecar.write_text("-5", encoding="utf-8")
        self.assertEqual(audit_hmac.read_chain_length(), 0)

    def test_returns_zero_when_sidecar_empty(self) -> None:
        """``read_chain_length`` returns 0 on empty sidecar."""
        sidecar = audit_hmac.chain_length_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sidecar.write_text("", encoding="utf-8")
        self.assertEqual(audit_hmac.read_chain_length(), 0)
