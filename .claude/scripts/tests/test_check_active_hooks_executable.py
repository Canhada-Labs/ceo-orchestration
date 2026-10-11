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

    def test_non_json_constants_are_malformed_exit_2(self) -> None:
        """NaN/Infinity/-Infinity are not JSON: the settings file is malformed
        (exit 2, named), never enumerated as valid (rail r3 of PLAN-183 W7a —
        the harness-config gate delegates to this script)."""
        import shutil
        for const in ("NaN", "Infinity", "-Infinity"):
            with TemporaryDirectory() as td:
                tdp = Path(td)
                (tdp / ".claude" / "scripts").mkdir(parents=True)
                (tdp / ".claude" / "settings.json").write_text(
                    '{"rail_probe": %s, "hooks": {}}' % const, encoding="utf-8")
                copy_path = tdp / ".claude" / "scripts" / "check-active-hooks-executable.py"
                shutil.copy2(SCRIPT, copy_path)
                result = subprocess.run(
                    [sys.executable, str(copy_path)],
                    cwd=str(tdp), capture_output=True, text=True, check=False, timeout=10,
                )
                self.assertEqual(result.returncode, 2, msg=f"{const}: {result.stdout!r} {result.stderr!r}")
                self.assertIn(f"non-standard JSON constant {const}", result.stderr)

    def _direct_and_gate(self, td: Path, body: str):
        """Run this script directly, and check_harness_config.py --static (which
        delegates to it) with a clean --settings, over a temp tree whose
        .claude/settings.json is ``body``."""
        import shutil
        for rel in (".claude/scripts/check-active-hooks-executable.py",
                    ".claude/hooks/check_harness_config.py"):
            (td / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / rel, td / rel)
        (td / ".claude" / "settings.json").write_text(body, encoding="utf-8")
        (td / "probe.json").write_text("{}", encoding="utf-8")
        direct = subprocess.run(
            [sys.executable, str(td / ".claude/scripts/check-active-hooks-executable.py")],
            cwd=str(td), capture_output=True, text=True, check=False, timeout=10,
        )
        gate = subprocess.run(
            [sys.executable, str(td / ".claude/hooks/check_harness_config.py"),
             "--repo-root", str(td), "--static", "--settings", str(td / "probe.json")],
            cwd=str(td), capture_output=True, text=True, check=False, timeout=60,
        )
        return direct, gate

    def test_malformed_settings_red_through_the_harness_gate_delegation(self) -> None:
        """Malformed settings are exit 2 here and RED — never a WARN-green rc 0 — in
        check_harness_config.py, which delegates to this script (subgate rails r1/r2):
        a top-level non-object, NaN, a hooks shape that deviates (layer 1, by JSON
        path) and a form layer 1 does not foresee (layer 2, by exception type)."""
        not_obj = ".claude/settings.json: top-level JSON is not an object"
        cases = [(lit, not_obj) for lit in ("null", "[]", "1", '"s"', "true")] + [
            ('{"x": NaN}', "non-standard JSON constant NaN"),
            ('{"hooks":{"PreToolUse":[{"hooks":1}]}}', 'hooks["PreToolUse"][0].hooks: expected array'),
            ('{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":1}]}]}}',
             'hooks["PreToolUse"][0].hooks[0].command: expected string'),
            ('{"hooks":[]}', "hooks: expected object"),
            ('{"hooks":{"PreToolUse":"x"}}', 'hooks["PreToolUse"]: expected array'),
            ('{"hooks":{"Stop":[{"hooks":[{"type":"prompt","command":1}]}]}}', "TypeError while reading"),
        ]
        for body, why in cases:
            with TemporaryDirectory() as td:
                direct, gate = self._direct_and_gate(Path(td), body)
                self.assertEqual(direct.returncode, 2, msg=f"{body}: {direct.stderr!r}")
                self.assertTrue(direct.stderr.startswith("::error::"), direct.stderr)
                self.assertIn(why, direct.stderr)
                self.assertEqual(gate.returncode, 1, msg=f"{body}: {gate.stdout!r}")
                self.assertIn("exec-bit gate rc=2", gate.stdout)

    def test_legitimate_settings_stay_green_through_the_delegation(self) -> None:
        """Converse controls: settings WITHOUT a ``hooks`` key (0 refs) and the real
        repo settings (hooks present) stay green, directly and through the gate."""
        with TemporaryDirectory() as td:
            direct, gate = self._direct_and_gate(Path(td), '{"permissions": {}}')
            self.assertEqual((direct.returncode, gate.returncode), (0, 0), msg=direct.stderr + gate.stdout)
            self.assertIn("OK: 0 active hook reference(s)", direct.stdout)
        with TemporaryDirectory() as td:
            (Path(td) / "probe.json").write_text("{}", encoding="utf-8")
            gate = subprocess.run(
                [sys.executable, str(REPO_ROOT / ".claude/hooks/check_harness_config.py"),
                 "--repo-root", str(REPO_ROOT), "--static", "--settings", str(Path(td) / "probe.json")],
                cwd=str(REPO_ROOT), capture_output=True, text=True, check=False, timeout=60,
            )
            self.assertEqual(gate.returncode, 0, msg=gate.stdout)
            self.assertNotIn("exec_bit", gate.stdout)

if __name__ == "__main__":
    unittest.main()
