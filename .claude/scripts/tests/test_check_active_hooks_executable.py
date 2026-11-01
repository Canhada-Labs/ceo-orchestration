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
from typing import Optional

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
        a top-level non-object, NaN and a hooks shape that deviates (layer 1, by JSON
        path). Item 6a.2 of the 1.4.4 backlog moved the last case here from layer 2:
        a prompt hook is now judged by its own required field, not by a stray command."""
        not_obj = ".claude/settings.json: top-level JSON is not an object"
        cases = [(lit, not_obj) for lit in ("null", "[]", "1", '"s"', "true")] + [
            ('{"x": NaN}', "non-standard JSON constant NaN"),
            ('{"hooks":{"PreToolUse":[{"hooks":1}]}}', 'hooks["PreToolUse"][0].hooks: expected array'),
            ('{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":1}]}]}}',
             'hooks["PreToolUse"][0].hooks[0].command: expected string'),
            ('{"hooks":[]}', "hooks: expected object"),
            ('{"hooks":{"PreToolUse":"x"}}', 'hooks["PreToolUse"]: expected array'),
            ('{"hooks":{"Stop":[{"hooks":[{"type":"prompt","command":1}]}]}}',
             'hooks["Stop"][0].hooks[0].prompt: expected string'),
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

    def test_fu144_hook_schema_matches_the_loader_and_ignores_prompt_command(self) -> None:
        """Every supported hook type has its loader-required string fields.

        A prompt's unrelated ``command`` field is deliberately ignored: the
        loader does not execute it and this gate must inspect only commands.
        """
        failures = (
            ('{"hooks":{"Stop":[{"hooks":[{"command":"x"}]}]}}', ".type: required"),
            ('{"hooks":{"Stop":[{"hooks":[{"type":"function"}]}]}}', "unknown hook type"),
            ('{"hooks":{"Stop":[{"matcher":7,"hooks":[{"type":"prompt","prompt":"ok"}]}]}}', ".matcher: expected string"),
            ('{"hooks":{"Stop":[{"hooks":[{"type":"mcp_tool","server":"s"}]}]}}', ".tool: expected string"),
        )
        for body, message in failures:
            with self.subTest(body=body), TemporaryDirectory() as td:
                direct, _gate = self._direct_and_gate(Path(td), body)
                self.assertEqual(direct.returncode, 2, direct.stderr)
                self.assertIn(message, direct.stderr)
        body = '{"hooks":{"Stop":[{"hooks":[{"type":"prompt","prompt":"ok","command":1}]}]}}'
        with TemporaryDirectory() as td:
            direct, _gate = self._direct_and_gate(Path(td), body)
        self.assertEqual(direct.returncode, 0, direct.stderr)

    def test_fu144_settings_that_are_not_regular_files_fail_closed(self) -> None:
        """A directory and a dangling link cannot be mistaken for no settings."""
        import shutil
        for kind in ("directory", "dangling-link"):
            with self.subTest(kind=kind), TemporaryDirectory() as td:
                root = Path(td)
                script = root / ".claude/scripts/check-active-hooks-executable.py"
                script.parent.mkdir(parents=True)
                shutil.copy2(SCRIPT, script)
                settings = root / ".claude/settings.json"
                if kind == "directory":
                    settings.mkdir()
                else:
                    settings.symlink_to(root / "absent.json")
                result = subprocess.run([sys.executable, str(script)], cwd=str(root),
                                        capture_output=True, text=True, check=False, timeout=10)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("settings.json", result.stderr)
                self.assertIn("not a regular file" if kind == "directory" else "cannot stat", result.stderr)

    def test_fu144_symlink_loop_during_hook_resolution_is_named_rc2(self) -> None:
        """A hook path that cannot resolve is malformed input, never a traceback."""
        import shutil
        with TemporaryDirectory() as td:
            root = Path(td)
            script = root / ".claude/scripts/check-active-hooks-executable.py"
            script.parent.mkdir(parents=True)
            shutil.copy2(SCRIPT, script)
            hooks = root / ".claude/hooks"
            hooks.mkdir()
            (hooks / "loop.py").symlink_to("loop.py")
            (root / ".claude/settings.json").write_text(
                '{"hooks":{"Stop":[{"hooks":[{"type":"command",'
                '"command":"python3 .claude/hooks/loop.py"}]}]}}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(script)], cwd=str(root),
                                    capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("cannot stat hook file", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    # --- PLAN-194-FOLLOWUP-v1-4-4-backlog, item 6a ---------------------------

    def _copy_script(self, td: Path) -> Path:
        import shutil
        copy = td / ".claude" / "scripts" / "check-active-hooks-executable.py"
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCRIPT, copy)
        return copy

    def _run_copy(self, td: Path, timeout: int = 10) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            [sys.executable, str(self._copy_script(td))],
            cwd=str(td), capture_output=True, text=True, check=False, timeout=timeout,
        )

    def _settings(self, td: Path, hook: dict, matcher_entry: Optional[dict] = None) -> None:
        entry = {"hooks": [hook]}
        entry.update(matcher_entry or {})
        (td / ".claude").mkdir(parents=True, exist_ok=True)
        (td / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PreToolUse": [entry]}}), encoding="utf-8")

    def test_fu144_type_and_matcher_validated_like_the_loader_replica(self) -> None:
        """6a.1: the three shapes the loader replica treats as fatal used to pass
        green here (no ``type``, unknown ``type``, non-string ``matcher``)."""
        cases = [
            ({"command": "x"}, None, ".hooks[0].type: required"),
            ({"type": "function"}, None, '.hooks[0].type: unknown hook type "function"'),
            ({"type": 1}, None, ".hooks[0].type: expected string"),
            ({"type": "command", "command": "x"}, {"matcher": 7}, "[0].matcher: expected string"),
        ]
        for hook, extra, why in cases:
            with TemporaryDirectory() as td:
                self._settings(Path(td), hook, extra)
                result = self._run_copy(Path(td))
                self.assertEqual(result.returncode, 2, msg=f"{hook}: {result.stdout!r} {result.stderr!r}")
                self.assertTrue(result.stderr.startswith("::error::"), result.stderr)
                self.assertIn(why, result.stderr)

    def test_fu144_required_fields_of_each_type_follow_the_replica_table(self) -> None:
        """The schema lives in TWO files, so its parity is asserted, not assumed:
        adding a type or a required field to the replica turns this red."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ceo_settings_guard_replica", str(Path(__file__).with_name("test_settings_guard_loadability.py")))
        replica = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replica)
        spec2 = importlib.util.spec_from_file_location("ceo_active_hooks_probe", str(SCRIPT))
        gate = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(gate)
        expected = {t: tuple(sorted(replica._TYPE_FIELDS[t][0])) for t in replica.HOOK_TYPES}
        self.assertEqual(
            {t: tuple(sorted(f)) for t, f in gate._REQUIRED_FIELDS.items()}, expected)
        for hook_type, fields in expected.items():
            for field in fields:
                hook = {"type": hook_type}
                hook.update({other: "x" for other in fields if other != field})
                with TemporaryDirectory() as td:
                    self._settings(Path(td), hook)
                    result = self._run_copy(Path(td))
                    self.assertEqual(result.returncode, 2, msg=f"{hook_type}: {result.stderr!r}")
                    self.assertIn(f".hooks[0].{field}: expected string", result.stderr)

    def test_fu144_command_is_read_only_from_type_command(self) -> None:
        """6a.2: the loader discards an extra ``command`` on another type, so it is
        neither RED (``command: 1``) nor a reference to a hook file."""
        for extra in (1, ".claude/hooks/check_missing_xyz.py"):
            with TemporaryDirectory() as td:
                self._settings(Path(td), {"type": "prompt", "prompt": "p", "command": extra})
                result = self._run_copy(Path(td))
                self.assertEqual(result.returncode, 0, msg=f"{extra!r}: {result.stdout!r} {result.stderr!r}")
                self.assertIn("OK: 0 active hook reference(s)", result.stdout)

    def test_fu144_stat_failure_is_a_named_exit_2(self) -> None:
        """6a.3: a symlink loop or a forbidden directory used to leave main() as a
        traceback. ``hooks`` loses its search bit, so the stat itself is refused."""
        cmd = "bash .claude/hooks/_python-hook.sh check_x.py"
        with TemporaryDirectory() as td:
            tdp = Path(td)
            self._settings(tdp, {"type": "command", "command": cmd})
            hooks = tdp / ".claude" / "hooks"
            hooks.mkdir()
            os.symlink("check_x.py", hooks / "check_x.py")
            result = self._run_copy(tdp)
            self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
            self.assertIn("::error::cannot stat hook file .claude/hooks/check_x.py", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        if os.geteuid() == 0:
            self.skipTest("root ignores the directory mode")
        with TemporaryDirectory() as td:
            tdp = Path(td)
            self._settings(tdp, {"type": "command", "command": cmd})
            hooks = tdp / ".claude" / "hooks"
            hooks.mkdir()
            self._copy_script(tdp)
            os.chmod(hooks, 0)
            try:
                result = self._run_copy(tdp)
            finally:
                os.chmod(hooks, 0o700)
            self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
            self.assertIn("PermissionError", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_fu144_settings_that_is_not_a_file_is_not_skipped(self) -> None:
        """6a.4: only real ABSENCE is skipped. A directory, a dangling symlink and a
        FIFO in the settings path are named exit 2 (the FIFO without hanging)."""
        def directory(p: Path) -> None:
            p.mkdir()

        def dangling(p: Path) -> None:
            os.symlink("gone.json", p)

        for make in (directory, dangling, lambda p: os.mkfifo(p)):
            with TemporaryDirectory() as td:
                tdp = Path(td)
                (tdp / ".claude").mkdir()
                make(tdp / ".claude" / "settings.json")
                result = self._run_copy(tdp)
                self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
                self.assertTrue(result.stderr.startswith("::error::"), result.stderr)
                self.assertIn("settings.json", result.stderr)
        with TemporaryDirectory() as td:
            result = self._run_copy(Path(td))
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("OK: 0 active hook reference(s) across 0 settings file(s)", result.stdout)

    def test_fu144_symlink_to_a_regular_settings_file_stays_valid(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude").mkdir()
            (tdp / "real.json").write_text('{"hooks": {}}', encoding="utf-8")
            os.symlink(tdp / "real.json", tdp / ".claude" / "settings.json")
            result = self._run_copy(tdp)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
