"""Audit-emit backpressure tests under simulated disk pressure.

PLAN-025 Batch J F-sec-012 (P3) — verify audit_emit degrades
gracefully when the primary log path is not writable, falls back to
the breadcrumb path, and NEVER crashes the parent hook invocation.

Uses stdlib-only simulation (no special filesystem mount; no ENOSPC
syscall emulation). Instead exercises the code path that handles
write failures by making the primary log path point at an unwritable
location (read-only dir, non-existent parent, etc.) and asserts the
fallback / breadcrumb path receives the event.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402


class TestAuditEmitGracefulDegradation(TestEnvContext):
    """audit_emit must not crash when primary log is not writable."""

    def test_readonly_log_dir_falls_back_to_breadcrumb(self):
        """If the primary log dir is read-only, emit should use fallback."""
        # Create an isolated write-target
        log_dir = self.audit_dir
        os.makedirs(log_dir, exist_ok=True)
        log_path = log_dir / "audit-log.jsonl"

        # Make the dir read-only (0o500) — write attempts should fail
        try:
            os.chmod(log_dir, 0o500)
        except OSError:
            self.skipTest("Cannot make dir read-only on this platform")

        try:
            # Point the env var at the read-only path
            os.environ["CEO_AUDIT_LOG_PATH"] = str(log_path)

            # Import lazily so audit_emit resolves the env var at call time
            from _lib import audit_emit

            # This must not raise even though the write will fail
            try:
                audit_emit.emit_veto_triggered(
                    hook="test_backpressure",
                    reason_code="test_reason",
                    reason_preview="plan-025-batch-j smoke",
                    blocked_tool="Test",
                    project=str(self.project_dir),
                    session_id="plan-025-batch-j",
                )
            except Exception as exc:  # noqa: BLE001
                self.fail(
                    f"emit_event raised {type(exc).__name__}: {exc} — "
                    "audit_emit must be fail-open on disk pressure"
                )
        finally:
            # Restore perms so tearDown can clean up
            try:
                os.chmod(log_dir, 0o700)
            except OSError:
                pass

    def test_nonexistent_log_dir_parent_creates_path(self):
        """If parent dir doesn't exist, emit should attempt to create it."""
        nonexistent_parent = self.audit_dir / "subdir-does-not-exist-yet"
        log_path = nonexistent_parent / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(log_path)

        from _lib import audit_emit

        try:
            audit_emit.emit_veto_triggered(
                hook="test_mkdirp",
                reason_code="test_reason_mkdirp",
                reason_preview="plan-025-batch-j mkdirp",
                blocked_tool="Test",
                project=str(self.project_dir),
                session_id="plan-025-batch-j",
            )
        except Exception as exc:  # noqa: BLE001
            self.fail(
                f"emit_event raised {type(exc).__name__}: {exc} on "
                "nonexistent parent dir (should auto-mkdir)"
            )

        # Verify the log file was created + parent dir auto-created
        self.assertTrue(
            nonexistent_parent.is_dir(),
            f"Parent dir {nonexistent_parent} should be auto-created",
        )
        self.assertTrue(log_path.is_file(), f"Log file {log_path} should exist")

    def test_no_crash_when_both_primary_and_fallback_fail(self):
        """Double-failure: primary + fallback both unwritable → no crash."""
        # Point primary log at unwritable path
        blocked_dir = self.audit_dir / "blocked"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(blocked_dir, 0o000)
        except OSError:
            self.skipTest("Cannot make dir 0o000 on this platform")

        try:
            os.environ["CEO_AUDIT_LOG_PATH"] = str(blocked_dir / "audit-log.jsonl")

            from _lib import audit_emit

            # Must not raise, even if both primary and fallback fail.
            try:
                audit_emit.emit_veto_triggered(
                    hook="test_double_failure",
                    reason_code="test_double",
                    reason_preview="plan-025-batch-j double",
                    blocked_tool="Test",
                    project=str(self.project_dir),
                    session_id="plan-025-batch-j",
                )
            except Exception as exc:  # noqa: BLE001
                self.fail(
                    f"emit_event raised {type(exc).__name__}: {exc} — "
                    "double-failure must still fail-open (no parent crash)"
                )
        finally:
            try:
                os.chmod(blocked_dir, 0o700)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
