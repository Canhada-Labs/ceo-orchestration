"""Tests for check-active-hooks-executable.py (Session 75 Finding 9).

Smoke-tests the dynamic hook-enumeration logic that replaces the
hardcoded 4-hook list in `.github/workflows/validate.yml`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-active-hooks-executable.py"


def _run(env: dict, cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


class CheckActiveHooksExecutableTest(TestEnvContext):
    def test_real_repo_settings_pass(self) -> None:
        result = _run(env={**os.environ}, cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("active hook reference", result.stdout)

    def test_missing_hook_fails_closed(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "hooks").mkdir(parents=True)
            settings = tdp / ".claude" / "settings.json"
            # Reference a hook that doesn't exist on disk.
            settings.write_text(json.dumps({
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Edit",
                         "hooks": [{"type": "command",
                                    "command": "bash .claude/hooks/_python-hook.sh check_missing_xyz.py"}]}
                    ]
                }
            }), encoding="utf-8")
            # Copy (not symlink) the real script into the temp tree so
            # __file__-based REPO_ROOT resolution lands in tdp.
            import shutil
            real_scripts = tdp / ".claude" / "scripts"
            real_scripts.mkdir()
            copy_path = real_scripts / "check-active-hooks-executable.py"
            shutil.copy2(SCRIPT, copy_path)
            result = subprocess.run(
                [sys.executable, str(copy_path)],
                cwd=str(tdp),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(
                result.returncode, 0,
                msg=f"expected non-zero exit; stdout={result.stdout!r} stderr={result.stderr!r}",
            )
            self.assertIn("MISSING", result.stdout)


if __name__ == "__main__":
    unittest.main()
