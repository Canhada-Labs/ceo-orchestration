"""Installed CLIs must carry their split implementations in the core profile."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from _lib.testing import TestEnvContext


_REPO = Path(__file__).resolve().parents[3]
_PACKAGES = ("_audit_query", "_installer_write_safety", "_contamination")
_SCRIPTS = (
    "audit-query.py", "check-installer-write-safety.py", "check_contamination.py",
)


class TestInstalledScriptPackages(TestEnvContext):
    def test_core_install_runs_split_clis_without_source_tree(self) -> None:
        """Inspect delivered files and execute each CLI from the destination."""
        target = self.project_dir / "installed-core"
        target.mkdir()
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.update({
            "HOME": str(self.project_dir),
            "CLAUDE_PROJECT_DIR": str(target),
            "CLAUDE_PROJECT_DIR_NATIVE": "",
            "CEO_AUDIT_LOG_DIR": str(self.project_dir / "audit"),
        })
        with patch.dict(os.environ, env, clear=True):
            install = subprocess.run(
                ["bash", str(_REPO / "scripts/install.sh"), str(target),
                 "--profile", "core"],
                cwd=str(_REPO), env=env, capture_output=True, text=True,
                timeout=120, check=False,
            )
        self.assertEqual(install.returncode, 0, install.stderr[-1000:])

        for name in _PACKAGES:
            delivered = target / ".claude/hooks/_lib" / name
            original = _REPO / ".claude/hooks/_lib" / name
            self.assertTrue(delivered.is_dir(), name)
            original_modules = sorted(p.name for p in original.glob("*.py"))
            delivered_modules = sorted(p.name for p in delivered.glob("*.py"))
            self.assertTrue(original_modules, name)
            self.assertEqual(delivered_modules, original_modules, name)

        for name in _SCRIPTS:
            script = target / ".claude/scripts" / name
            self.assertTrue(script.is_file(), name)
            completed = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=str(target), env=env, capture_output=True, text=True,
                timeout=30, check=False,
            )
            self.assertEqual(
                completed.returncode, 0,
                f"{name}: {completed.stderr[-1000:]}",
            )
            self.assertIn("usage", completed.stdout.lower(), name)
