"""FU144 coverage for diagnose-output-hook's child audit isolation."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude" / "scripts" / "diagnose-output-hook.py"
_HOOKS = _REPO / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import test_isolation  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _load_diagnostic():
    spec = importlib.util.spec_from_file_location("diagnose_output_hook", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diagnostic = _load_diagnostic()


class TestDiagnoseOutputHookIsolation(TestEnvContext):
    def _inherited_locations_fu144(self, root: Path) -> dict:
        values = {}
        for key in diagnostic._CHILD_LOCATION_CARRIERS:
            values[key] = "1" if key.endswith("_DISABLE") else str(root / key)
        return values

    def test_fu144_child_environment_clears_full_location_carrier_set(self) -> None:
        foreign = self.project_dir / "foreign"
        base = self._inherited_locations_fu144(foreign)
        clean = diagnostic._isolated_child_env(base, str(self.home_dir), self.project_dir)
        expected = (
            test_isolation.ALL_AUDIT_CARRIERS
            + test_isolation.WHOLE_DIR_OVERRIDE_CARRIERS
        )
        self.assertEqual(diagnostic._CHILD_LOCATION_CARRIERS, expected)
        self.assertEqual(clean["HOME"], str(self.home_dir))
        self.assertEqual(clean["CEO_AUDIT_LOG_DIR"], str(self.home_dir / "audit"))
        self.assertEqual(clean["CEO_PROJECT_STATE_DIR"], str(self.home_dir / "state"))
        self.assertEqual(clean["CLAUDE_PROJECT_DIR"], str(self.project_dir))
        for key in expected:
            if key not in ("HOME", "CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR"):
                self.assertNotIn(key, clean)

    def test_fu144_external_audit_canary_survives_real_diagnostic_child(self) -> None:
        foreign = self.project_dir / "external-audit-family"
        foreign.mkdir()
        canary = foreign / "audit-log.jsonl"
        canary.write_bytes(b"before-diagnostic\n")
        native = foreign / "native-state"
        native.mkdir()
        (native / "canary").write_bytes(b"native-before\n")
        before = {str(path.relative_to(foreign)): path.read_bytes()
                  for path in foreign.rglob("*") if path.is_file()}
        env = dict(os.environ)
        env.update(self._inherited_locations_fu144(foreign))
        env["CEO_AUDIT_LOG_PATH"] = str(canary)
        env["CLAUDE_PROJECT_DIR_NATIVE"] = str(native)
        env["CLAUDE_PROJECT_DIR"] = str(_REPO)
        with mock.patch.dict(os.environ, {}, clear=False):
            child = subprocess.run(
                [sys.executable, str(_SCRIPT), "--iterations", "1"],
                cwd=str(_REPO), env=env, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertNotIn("Fatal Python error", child.stderr)
        self.assertEqual(child.stdout.count("(1 cold then 0 warm)"), 2)
        after = {str(path.relative_to(foreign)): path.read_bytes()
                 for path in foreign.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
