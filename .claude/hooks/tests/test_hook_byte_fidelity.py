"""Per-hook byte-identity fixture tests.

PLAN-006 Phase 1 pre-work (ADR-014). Guards against silent stdout
drift during hook migration to the Adapter Layer. Each hook has a
captured (stdin, stdout) pair; this test feeds the stdin to the
current hook binary and asserts the stdout is byte-identical to
the frozen capture.

If this test fails after a migration commit, the migration changed
observable behavior — revert or fix before the commit lands.

Hook inventory (7 hooks, 1 fixture pair each):
- check_bash_safety (PreToolUse, Bash)
- check_canonical_edit (PreToolUse, Edit)
- check_plan_edit (PreToolUse, Edit)
- check_read_injection (PreToolUse, Read)
- check_agent_spawn (PreToolUse, Task)
- audit_log (PostToolUse, Task)
- check_confidence_gate (PostToolUse, Agent) — PLAN-009 C1.1
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
FIXTURES_DIR = HOOKS_DIR / "tests" / "fixtures" / "hooks"

HOOKS = [
    "check_bash_safety",
    "check_canonical_edit",
    "check_plan_edit",
    "check_read_injection",
    "check_agent_spawn",
    "audit_log",
    "check_confidence_gate",
]


def _run_hook(hook_name: str, stdin_bytes: bytes, env_extra: dict = None) -> tuple[int, bytes]:
    """Run a hook binary with stdin, return (exit_code, stdout_bytes)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    if env_extra:
        env.update(env_extra)
    hook_path = HOOKS_DIR / f"{hook_name}.py"
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=stdin_bytes,
        capture_output=True,
        env=env,
        timeout=10,
    )
    return result.returncode, result.stdout


class TestHookByteFidelity(unittest.TestCase):
    """Each hook's stdout must match its frozen fixture byte-for-byte."""

    def _check_hook(self, hook_name: str):
        fixture_dir = FIXTURES_DIR / hook_name
        in_path = fixture_dir / "in.json"
        out_path = fixture_dir / "out.json"
        self.assertTrue(in_path.exists(), f"missing fixture: {in_path}")
        self.assertTrue(out_path.exists(), f"missing fixture: {out_path}")

        stdin_bytes = in_path.read_bytes()
        expected_stdout = out_path.read_bytes()

        exit_code, actual_stdout = _run_hook(hook_name, stdin_bytes)

        # Exit code must be 0 (allow) on well-formed fixtures.
        self.assertEqual(
            exit_code,
            0,
            f"{hook_name}: expected exit 0, got {exit_code}; stdout={actual_stdout!r}",
        )
        # Stdout must be byte-identical.
        self.assertEqual(
            actual_stdout,
            expected_stdout,
            f"{hook_name}: stdout drift\n  expected: {expected_stdout!r}\n  actual:   {actual_stdout!r}",
        )

    def test_check_bash_safety_byte_fidelity(self):
        self._check_hook("check_bash_safety")

    def test_check_canonical_edit_byte_fidelity(self):
        self._check_hook("check_canonical_edit")

    def test_check_plan_edit_byte_fidelity(self):
        self._check_hook("check_plan_edit")

    def test_check_read_injection_byte_fidelity(self):
        self._check_hook("check_read_injection")

    def test_check_agent_spawn_byte_fidelity(self):
        self._check_hook("check_agent_spawn")

    def test_audit_log_byte_fidelity(self):
        self._check_hook("audit_log")

    def test_check_confidence_gate_byte_fidelity(self):
        self._check_hook("check_confidence_gate")


if __name__ == "__main__":
    unittest.main()
