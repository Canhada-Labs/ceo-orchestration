"""Per-hook fail-open contract tests.

PLAN-006 Phase 1 pre-work (ADR-014). Every hook MUST fail open on
malformed stdin: exit 0, emit `{"decision":"allow"}` (or nothing,
for PostToolUse observers). No hook may block the user session on
infrastructure bugs (CLAUDE.md §5 critical rule).

This test feeds each hook three malformed payloads:
- empty stdin
- non-JSON garbage
- JSON that parses but has missing fields

Each case must exit 0 and NOT emit `{"decision":"block",...}`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

HOOKS = [
    "check_bash_safety",
    "check_canonical_edit",
    "check_plan_edit",
    "check_read_injection",
    "check_agent_spawn",
    "audit_log",
]

MALFORMED_PAYLOADS = [
    ("empty", b""),
    ("garbage", b"not json at all {{{"),
    ("json_missing_fields", b'{"weird":"shape"}'),
    ("null_tool_input", b'{"tool_name":"X","tool_input":null}'),
]


def _run_hook(hook_name: str, stdin_bytes: bytes) -> tuple[int, bytes]:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    hook_path = HOOKS_DIR / f"{hook_name}.py"
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=stdin_bytes,
        capture_output=True,
        env=env,
        timeout=10,
    )
    return result.returncode, result.stdout


class TestFailOpenContract(unittest.TestCase):
    """Every hook fails open on every malformed payload."""

    def _assert_fail_open(self, hook_name: str, payload_label: str, payload: bytes):
        exit_code, stdout = _run_hook(hook_name, payload)
        self.assertEqual(
            exit_code,
            0,
            f"{hook_name}/{payload_label}: expected exit 0 (fail-open), "
            f"got {exit_code}; stdout={stdout!r}",
        )
        # If stdout is non-empty, it must NOT be a block decision.
        text = stdout.decode("utf-8", errors="replace").strip()
        if text:
            try:
                parsed = json.loads(text)
                self.assertNotEqual(
                    parsed.get("decision"),
                    "block",
                    f"{hook_name}/{payload_label}: emitted block on malformed stdin: {text!r}",
                )
            except json.JSONDecodeError:
                # Some hooks (audit_log) emit nothing; others may emit a
                # non-JSON breadcrumb. As long as decision is not "block",
                # fail-open is honored.
                pass

    def test_check_bash_safety_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("check_bash_safety", label, payload)

    def test_check_canonical_edit_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("check_canonical_edit", label, payload)

    def test_check_plan_edit_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("check_plan_edit", label, payload)

    def test_check_read_injection_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("check_read_injection", label, payload)

    def test_check_agent_spawn_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("check_agent_spawn", label, payload)

    def test_audit_log_fail_open(self):
        for label, payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=label):
                self._assert_fail_open("audit_log", label, payload)


if __name__ == "__main__":
    unittest.main()
