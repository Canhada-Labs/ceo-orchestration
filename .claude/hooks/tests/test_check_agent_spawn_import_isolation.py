"""PLAN-094 Wave E.7 — import-graph regression test for check_agent_spawn.

Closes PLAN-090 v1.24.0 AC9c spawn-hook microbench regression.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


class CheckAgentSpawnImportIsolationTests(unittest.TestCase):

    def test_dispatch_shim_does_not_import_audit_emit_at_module_load(self) -> None:
        probe = (
            "import sys;"
            "sys.path.insert(0, '.claude/hooks');"
            "import _lib.audit_emit_dispatch;"
            "print('audit_emit_imported=' + str('_lib.audit_emit' in sys.modules))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "CEO_AUDIT_EMIT_LAZY_IMPORT_DISABLED": ""},
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        self.assertIn("audit_emit_imported=False", proc.stdout,
                      "dispatch shim leaked audit_emit at module-load")

    def test_first_emit_call_triggers_lazy_load(self) -> None:
        # Redirect emit target to tmpdir — without this, the test=probe events
        # land in the canonical audit-log and poison the skill_unknown_ratio
        # detector (see /ceo-boot Fix B / S127 follow-up).
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="ceo-audit-isolation-")
        probe = (
            "import sys;"
            "sys.path.insert(0, '.claude/hooks');"
            "import _lib.audit_emit_dispatch as d;"
            "pre = '_lib.audit_emit' in sys.modules;"
            "d.emit_generic('agent_spawn', test='probe');"
            "post = '_lib.audit_emit' in sys.modules;"
            "print(f'pre={pre} post={post}')"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=15,
            env={
                **os.environ,
                "CEO_AUDIT_EMIT_LAZY_IMPORT_DISABLED": "",
                "CEO_AUDIT_LOG_DIR": tmpdir,
            },
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        self.assertIn("pre=False post=True", proc.stdout,
                      f"lazy-load contract broken: {proc.stdout!r}")

    def test_kill_switch_eager_import(self) -> None:
        probe = (
            "import sys;"
            "sys.path.insert(0, '.claude/hooks');"
            "import _lib.audit_emit_dispatch;"
            "print('audit_emit_imported=' + str('_lib.audit_emit' in sys.modules))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "CEO_AUDIT_EMIT_LAZY_IMPORT_DISABLED": "1"},
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        self.assertIn("audit_emit_imported=True", proc.stdout,
                      "kill-switch eager-import failed")


if __name__ == "__main__":
    unittest.main()
