"""PLAN-045 F-01-06 — tests for audit_log.py symlink + uid defense.

Covers:
- Symlink directory rejection
- Symlink log file rejection
- UID mismatch rejection (via mock on lstat)
- Safe path proceeds normally
- _is_safe_audit_path unit coverage
- Fallback breadcrumb written on all rejection paths
"""
from __future__ import annotations

import getpass
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

from _lib.testing import TestEnvContext  # noqa: E402

import audit_log as al  # noqa: E402

# These tests share ONE global fallback breadcrumb path
# (/tmp/ceo-audit-fallback-<user>.log, mirrored from audit_log.py). Several
# classes DELIBERATELY trigger a fallback write while TestSafePathProceeds
# asserts its ABSENCE — under xdist those race across workers (a pre-existing
# flake surfaced by finish-plan135.sh's parallel not-serial pass: the dry-run
# passed, a later identical run failed on a different test). Mark the whole
# module serial per pytest.ini's shared-repo-state contract (S220) so these run
# in the isolated serial pass with no concurrent writer.
pytestmark = pytest.mark.serial


def _fallback_path() -> Path:
    try:
        user = getpass.getuser() or "unknown"
    except Exception:
        user = os.environ.get("USER") or "unknown"
    user = "".join(c for c in user if c.isalnum() or c in ("-", "_", "."))
    return Path("/tmp") / f"ceo-audit-fallback-{user}.log"


class _FallbackCleanupMixin:
    """Ensure /tmp fallback is cleaned before + after each test."""

    def _clear_fallback(self) -> None:
        p = _fallback_path()
        try:
            p.unlink()
        except FileNotFoundError:
            pass

    def setUp(self) -> None:  # type: ignore[override]
        super().setUp()
        self._clear_fallback()

    def tearDown(self) -> None:  # type: ignore[override]
        self._clear_fallback()
        super().tearDown()


class TestSymlinkRejection(_FallbackCleanupMixin, TestEnvContext):
    """F-01-06: audit dir/log symlinks must be refused."""

    def _run_main(self, payload):
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload))
        sys.stdout = io.StringIO()
        try:
            rc = al.main()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        return rc

    def test_audit_dir_symlink_refuses_write(self) -> None:
        # Real target outside the audit path + symlink audit dir to it
        evil_target = Path(tempfile.mkdtemp(prefix="evil-target-"))
        self.addCleanup(shutil.rmtree, str(evil_target), ignore_errors=True)

        audit_dir = Path(os.environ["CEO_AUDIT_LOG_DIR"])
        # Remove existing real dir (TestEnvContext may have pre-created)
        if audit_dir.exists():
            shutil.rmtree(audit_dir)
        audit_dir.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(evil_target), str(audit_dir))

        payload = {
            "session_id": "t",
            "tool_name": "Agent",
            "tool_input": {"description": "d", "prompt": "SKILL: x\n"},
        }
        rc = self._run_main(payload)
        self.assertEqual(rc, 0)  # fail-open on session
        # Audit-log file was NOT created in the evil target
        self.assertFalse((evil_target / "audit-log.jsonl").exists())
        # Fallback breadcrumb was written to /tmp
        fallback = _fallback_path()
        self.assertTrue(fallback.exists())
        content = fallback.read_text()
        self.assertIn("symlink_rejected", content)
        self.assertIn("audit dir unsafe", content)

    def test_audit_log_symlink_refuses_write(self) -> None:
        # Real dir, but log path is a symlink to /dev/null
        audit_dir = Path(os.environ["CEO_AUDIT_LOG_DIR"])
        audit_dir.mkdir(parents=True, exist_ok=True)
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if log_path.exists() or log_path.is_symlink():
            log_path.unlink()
        os.symlink("/dev/null", str(log_path))

        payload = {
            "session_id": "t",
            "tool_name": "Agent",
            "tool_input": {"description": "d", "prompt": "SKILL: x\n"},
        }
        rc = self._run_main(payload)
        self.assertEqual(rc, 0)
        fallback = _fallback_path()
        self.assertTrue(fallback.exists())
        content = fallback.read_text()
        self.assertIn("symlink_rejected", content)
        self.assertIn("audit log unsafe", content)


class TestUidMismatch(_FallbackCleanupMixin, TestEnvContext):
    """F-01-06: foreign-uid ownership must be refused (simulated via mock)."""

    def _run_main(self, payload):
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload))
        sys.stdout = io.StringIO()
        try:
            rc = al.main()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        return rc

    def test_audit_dir_uid_mismatch_refuses_write(self) -> None:
        audit_dir = Path(os.environ["CEO_AUDIT_LOG_DIR"])
        audit_dir.mkdir(parents=True, exist_ok=True)

        real_geteuid = os.geteuid
        foreign_uid = 99999
        # Monkey-patch geteuid so current proc "is" uid=0, but the dir's
        # lstat.st_uid is the real user — guaranteeing uid_mismatch.
        with patch.object(al.os, "geteuid", lambda: real_geteuid() + 12345):
            payload = {
                "session_id": "t",
                "tool_name": "Agent",
                "tool_input": {"description": "d", "prompt": "SKILL: x\n"},
            }
            rc = self._run_main(payload)
        self.assertEqual(rc, 0)
        fallback = _fallback_path()
        self.assertTrue(fallback.exists())
        content = fallback.read_text()
        self.assertIn("uid_mismatch", content)


class TestSafePathProceeds(_FallbackCleanupMixin, TestEnvContext):
    """Negative control — safe real dir + log path writes normally."""

    def test_safe_path_writes_normally(self) -> None:
        # TestEnvContext sets up real temp dir owned by current user
        payload = {
            "session_id": "t",
            "tool_name": "Agent",
            "tool_input": {
                "description": "d",
                "prompt": "SKILL: test-skill\n## AGENT PROFILE\n## FILE ASSIGNMENT\n- x",
            },
        }
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload))
        sys.stdout = io.StringIO()
        try:
            rc = al.main()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        self.assertEqual(rc, 0)
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(log_path.exists())
        self.assertGreater(log_path.stat().st_size, 0)
        # No fallback breadcrumb should exist for the happy path
        self.assertFalse(_fallback_path().exists())


class TestIsSafeAuditPath(unittest.TestCase):
    """Unit tests for the pure helper."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._dir = Path(self._td.name)

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_nonexistent_path_is_safe(self) -> None:
        p = self._dir / "nonexistent"
        ok, reason = al._is_safe_audit_path(p, os.geteuid())
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_real_dir_is_safe(self) -> None:
        p = self._dir / "subdir"
        p.mkdir()
        ok, reason = al._is_safe_audit_path(p, os.geteuid())
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_real_file_is_safe(self) -> None:
        p = self._dir / "file.log"
        p.write_text("hello")
        ok, reason = al._is_safe_audit_path(p, os.geteuid())
        self.assertTrue(ok)

    def test_symlink_to_dir_is_unsafe(self) -> None:
        real = self._dir / "real"
        real.mkdir()
        link = self._dir / "link"
        os.symlink(str(real), str(link))
        ok, reason = al._is_safe_audit_path(link, os.geteuid())
        self.assertFalse(ok)
        self.assertEqual(reason, "symlink_rejected")

    def test_symlink_to_file_is_unsafe(self) -> None:
        real = self._dir / "target.log"
        real.write_text("hi")
        link = self._dir / "link.log"
        os.symlink(str(real), str(link))
        ok, reason = al._is_safe_audit_path(link, os.geteuid())
        self.assertFalse(ok)
        self.assertEqual(reason, "symlink_rejected")

    def test_broken_symlink_is_unsafe(self) -> None:
        # Symlink pointing to a nonexistent target — lstat still sees it
        # as a symlink regardless of target presence.
        link = self._dir / "broken"
        os.symlink("/nonexistent/path", str(link))
        ok, reason = al._is_safe_audit_path(link, os.geteuid())
        self.assertFalse(ok)
        self.assertEqual(reason, "symlink_rejected")

    def test_uid_mismatch_is_unsafe(self) -> None:
        p = self._dir / "file.log"
        p.write_text("hi")
        # Simulate the real uid being different from what we expect.
        foreign_uid = os.geteuid() + 99999
        ok, reason = al._is_safe_audit_path(p, foreign_uid)
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("uid_mismatch:"))


class TestFallbackBreadcrumb(_FallbackCleanupMixin, unittest.TestCase):
    """Direct coverage of _fallback_security_breadcrumb."""

    def test_breadcrumb_writes_to_tmp_fallback(self) -> None:
        al._fallback_security_breadcrumb("test message")
        p = _fallback_path()
        self.assertTrue(p.exists())
        content = p.read_text()
        self.assertIn("test message", content)
        self.assertIn("audit-log security:", content)

    def test_breadcrumb_appends_multiple_entries(self) -> None:
        al._fallback_security_breadcrumb("msg1")
        al._fallback_security_breadcrumb("msg2")
        content = _fallback_path().read_text()
        self.assertIn("msg1", content)
        self.assertIn("msg2", content)
        self.assertEqual(content.count("audit-log security:"), 2)


if __name__ == "__main__":
    unittest.main()
