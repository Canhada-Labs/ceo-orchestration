"""Tests for ``check-sdk-compat.sh`` (PLAN-056 Phase 2)."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-sdk-compat.sh"


def _run(version: str = "", extra_env: dict = None, timeout: int = 10) -> subprocess.CompletedProcess:
    env = {**os.environ}
    env["CLAUDE_VERSION"] = version
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(REPO_ROOT),
    )


class CheckSdkCompatTest(unittest.TestCase):

    def test_script_exists_and_executable(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_listed_green_v14_exits_zero_with_info(self):
        result = _run(version="1.4.0")
        self.assertEqual(result.returncode, 0)
        out = result.stdout + result.stderr
        self.assertIn("INFO", out)
        self.assertIn("listed-green", out)

    def test_listed_green_v21_exits_zero(self):
        # Currently-running CLI version on dev machine.
        result = _run(version="2.1.119")
        self.assertEqual(result.returncode, 0)
        self.assertIn("listed-green", result.stdout)

    def test_unlisted_future_exits_zero_with_warn(self):
        result = _run(version="3.0.0")
        # fail-open
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN", result.stdout)
        self.assertIn("unlisted", result.stdout)

    def test_unlisted_old_exits_zero_with_warn(self):
        result = _run(version="0.9.0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("unlisted", result.stdout)

    def test_malformed_version_falls_open(self):
        # Empty string in env triggers binary lookup; if no `claude` we
        # get "skipping". If `claude` is in PATH, we get a real version.
        # Either way, exit must be 0.
        result = _run(version="")
        self.assertEqual(result.returncode, 0)

    def test_missing_binary_silent_skip(self):
        # Force missing claude binary by restricting PATH to /usr/bin
        # only (bash is there but claude isn't on most systems).
        result = _run(version="", extra_env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 0)
        # Either skipping (missing binary) OR warn (binary present somewhere).
        out = result.stdout + result.stderr
        self.assertTrue(
            "skipping" in out or "WARN" in out or "INFO" in out,
            f"unexpected output: {out}",
        )

    def test_patch_version_uses_major_minor_match(self):
        # 1.4.99 should still match 1.4 matrix entry.
        result = _run(version="1.4.99")
        self.assertEqual(result.returncode, 0)
        self.assertIn("listed-green", result.stdout)


if __name__ == "__main__":
    unittest.main()
