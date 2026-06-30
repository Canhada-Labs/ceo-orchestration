"""In-process coverage uplift for audit_log.py utility functions.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 Tier-1.

audit_log.py is exercised mostly through build_entry/append_entry happy
paths; the rotation, breadcrumb, sanitize and validation helpers carry
fail-open `except` branches and bucket edges that the subprocess suite
does not reach. These tests call those helpers directly in-process.
"""

from __future__ import annotations

import os
import stat
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import audit_log as al  # noqa: E402


class AuditLogHelpersTest(TestEnvContext):

    # --- rotate_threshold ------------------------------------------------

    def test_rotate_threshold_bad_env_falls_back(self):
        with mock.patch.dict(os.environ, {"CEO_AUDIT_LOG_ROTATE_BYTES": "notanint"}):
            self.assertEqual(al.rotate_threshold(), al.DEFAULT_ROTATE_AT_BYTES)

    def test_rotate_threshold_good_env(self):
        with mock.patch.dict(os.environ, {"CEO_AUDIT_LOG_ROTATE_BYTES": "12345"}):
            self.assertEqual(al.rotate_threshold(), 12345)

    # --- bucket_prompt_length (all buckets) ------------------------------

    def test_bucket_prompt_length_all_buckets(self):
        self.assertEqual(al.bucket_prompt_length(10), "<256")
        self.assertEqual(al.bucket_prompt_length(500), "<1024")
        self.assertEqual(al.bucket_prompt_length(2000), "<4096")
        self.assertEqual(al.bucket_prompt_length(10000), "<16384")
        self.assertEqual(al.bucket_prompt_length(40000), "<65536")
        self.assertEqual(al.bucket_prompt_length(100000), ">=65536")

    # --- _sanitize_prompt ------------------------------------------------

    def test_sanitize_prompt_non_string(self):
        self.assertIsNone(al._sanitize_prompt(12345))  # type: ignore[arg-type]

    def test_sanitize_prompt_empty(self):
        self.assertIsNone(al._sanitize_prompt("   "))

    def test_sanitize_prompt_over_char_cap(self):
        self.assertIsNone(al._sanitize_prompt("a" * (al._MAX_INPUT_CHARS + 1)))

    def test_sanitize_prompt_nul_byte(self):
        self.assertIsNone(al._sanitize_prompt("hello\x00world"))

    def test_sanitize_prompt_ok(self):
        self.assertEqual(al._sanitize_prompt("normal prompt"), "normal prompt")

    # --- _validate_skill_name --------------------------------------------

    def test_validate_skill_name_too_long(self):
        self.assertFalse(al._validate_skill_name("a" * (al._MAX_SKILL_NAME_CHARS + 1)))

    def test_validate_skill_name_traversal(self):
        self.assertFalse(al._validate_skill_name("../etc"))
        self.assertFalse(al._validate_skill_name("a/b"))
        self.assertFalse(al._validate_skill_name("a\\b"))

    def test_validate_skill_name_bad_charset(self):
        self.assertFalse(al._validate_skill_name("bad name!"))

    def test_validate_skill_name_ok(self):
        self.assertTrue(al._validate_skill_name("security-engineer"))

    # --- _legacy_rotate_inline -------------------------------------------

    def test_legacy_rotate_inline_nonexistent(self):
        missing = self.project_dir / "nope.jsonl"
        self.assertIsNone(al._legacy_rotate_inline(missing, 10))

    def test_legacy_rotate_inline_under_threshold(self):
        small = self.project_dir / "small.jsonl"
        small.write_text("x", encoding="utf-8")
        self.assertIsNone(al._legacy_rotate_inline(small, 1024))

    def test_legacy_rotate_inline_rotates(self):
        big = self.project_dir / "audit-log.jsonl"
        big.write_text("y" * 200, encoding="utf-8")
        rotated = al._legacy_rotate_inline(big, 50)
        self.assertIsNotNone(rotated)
        self.assertTrue(rotated.exists())
        self.assertFalse(big.exists())

    def test_legacy_rotate_inline_collision_suffix(self):
        big = self.project_dir / "audit-log.jsonl"
        big.write_text("z" * 200, encoding="utf-8")
        # Pre-create the primary rotated name so the collision loop fires.
        month = al.now_month_slug()
        (self.project_dir / f"audit-log-{month}.jsonl").write_text("old", encoding="utf-8")
        rotated = al._legacy_rotate_inline(big, 50)
        self.assertIsNotNone(rotated)
        self.assertIn(f"{month}-1", rotated.name)

    # --- rotate_if_needed ------------------------------------------------

    def test_rotate_if_needed_import_fallback(self):
        big = self.project_dir / "audit-log.jsonl"
        big.write_text("q" * 200, encoding="utf-8")
        with mock.patch.dict("sys.modules", {"_lib.audit_rotation": None}):
            rotated = al.rotate_if_needed(big, 50)
        self.assertIsNotNone(rotated)

    def test_rotate_if_needed_no_rotation(self):
        small = self.project_dir / "audit-log.jsonl"
        small.write_text("x", encoding="utf-8")
        self.assertIsNone(al.rotate_if_needed(small, 100000))

    # --- write_breadcrumb ------------------------------------------------

    def test_write_breadcrumb_ok(self):
        err = self.audit_dir / "audit-log.errors"
        al.write_breadcrumb(err, "test message")
        self.assertIn("test message", err.read_text(encoding="utf-8"))

    def test_write_breadcrumb_oserror_falls_back_to_stderr(self):
        # Parent is a regular file -> mkdir(parents=True) raises OSError.
        blocker = self.project_dir / "blocker"
        blocker.write_text("f", encoding="utf-8")
        bad = blocker / "sub" / "err.log"
        # Must not raise.
        al.write_breadcrumb(bad, "breadcrumb under file")

    # --- _is_safe_audit_path ---------------------------------------------

    def test_is_safe_audit_path_nonexistent(self):
        ok, reason = al._is_safe_audit_path(self.project_dir / "ghost", os.getuid())
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_is_safe_audit_path_symlink_rejected(self):
        target = self.project_dir / "real.jsonl"
        target.write_text("x", encoding="utf-8")
        link = self.project_dir / "link.jsonl"
        link.symlink_to(target)
        ok, reason = al._is_safe_audit_path(link, os.getuid())
        self.assertFalse(ok)
        self.assertEqual(reason, "symlink_rejected")

    def test_is_safe_audit_path_uid_mismatch(self):
        target = self.project_dir / "owned.jsonl"
        target.write_text("x", encoding="utf-8")
        ok, reason = al._is_safe_audit_path(target, os.getuid() + 999999)
        self.assertFalse(ok)
        self.assertIn("uid_mismatch", reason)

    # --- _fallback_security_breadcrumb -----------------------------------

    def test_fallback_security_breadcrumb_ok(self):
        # Must not raise.
        al._fallback_security_breadcrumb("unit-test security breadcrumb")

    def test_fallback_security_breadcrumb_getuser_raises(self):
        with mock.patch("getpass.getuser", side_effect=OSError("no user")), \
                mock.patch.dict(os.environ, {"USER": "fallbackuser"}):
            al._fallback_security_breadcrumb("getuser raised path")


if __name__ == "__main__":
    unittest.main()
