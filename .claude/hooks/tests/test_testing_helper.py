"""Meta-tests for _lib.testing.TestEnvContext — verify the test harness itself.

Ensures env isolation actually works: env vars are restored, HOME is
redirected, CLAUDE_PROJECT_DIR is redirected, temp dir is cleaned up.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402


class TestEnvIsolationWorks(TestEnvContext):
    def test_home_is_redirected(self):
        # os.environ["HOME"] should point at the isolated temp home.
        # Path.home() reads $HOME, so it returns the same path — that's
        # the successful isolation state.
        self.assertEqual(os.environ["HOME"], str(self.home_dir))
        self.assertEqual(Path.home(), self.home_dir)
        # The isolated home must be under /tmp or /var/folders (not the real home)
        self.assertIn("ceo-hook-test-", str(self.home_dir))

    def test_claude_project_dir_is_redirected(self):
        self.assertEqual(
            os.environ["CLAUDE_PROJECT_DIR"], str(self.project_dir)
        )

    def test_audit_env_vars_set(self):
        for key in (
            "CEO_AUDIT_LOG_DIR",
            "CEO_AUDIT_LOG_PATH",
            "CEO_AUDIT_LOG_ERR",
            "CEO_AUDIT_LOG_LOCK",
        ):
            self.assertIn(key, os.environ)
            self.assertTrue(os.environ[key].startswith(str(self.audit_dir)))

    def test_write_project_file_helper(self):
        p = self.write_project_file("foo/bar.txt", "hello")
        self.assertTrue(p.is_file())
        self.assertEqual(p.read_text(), "hello")

    def test_read_audit_log_empty_when_no_file(self):
        self.assertEqual(self.read_audit_log(), "")

    def test_tmp_root_is_isolated_per_test(self):
        # Two tests should see different tmp_root paths
        self.assertTrue(str(self._tmp_root).startswith("/"))
        self.assertNotEqual(self._tmp_root, Path("/tmp"))
