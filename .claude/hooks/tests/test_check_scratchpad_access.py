"""Unit tests for `check_scratchpad_access.py` (PLAN-011 Phase 7).

Covers the PreToolUse Bash hook that blocks cross-plan scratchpad
access. Tests use the pure ``decide_command()`` function + end-to-end
``main()`` stdin/stdout round-trip.

Consensus M2: ``--plan PLAN-X`` overrides must match the session's
derived plan_id or be blocked.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path


import check_scratchpad_access as csa  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _append_plan_transition(
    audit_path: Path,
    *,
    plan_id: str,
    session_id: str,
    ts: str = "2026-04-14T00:00:00Z",
) -> None:
    event = {
        "action": "plan_transition",
        "plan_id": plan_id,
        "from_status": "reviewed",
        "to_status": "executing",
        "editor_tool": "Edit",
        "file_path": f".claude/plans/{plan_id}.md",
        "transition_legal": True,
        "session_id": session_id,
        "project": "",
        "event_schema": "v2",
        "ts": ts,
        "tokens_in": None,
        "tokens_out": None,
        "tokens_total": None,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


class ScratchpadHookTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_STATE_ROOT"] = str(self.home_dir / ".claude" / "state")
        self.audit_log = Path(os.environ["CEO_AUDIT_LOG_PATH"])


# --- decide_command — targeting heuristics ------------------------------


class TestTargeting(ScratchpadHookTest):
    def test_non_scratchpad_command_allowed(self) -> None:
        d = csa.decide_command("ls -la")
        self.assertTrue(d.allow)

    def test_echo_with_scratchpad_string_allowed(self) -> None:
        """Quoted string — the first token is echo, not python."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command('echo "scratchpad.py --plan PLAN-OTHER"')
        self.assertTrue(d.allow)

    def test_python_other_script_allowed(self) -> None:
        """Other .py invocations are untouched."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command("python3 .claude/scripts/audit-query.py")
        self.assertTrue(d.allow)

    def test_direct_exec_of_scratchpad_recognized(self) -> None:
        """./scratchpad.py (shebang exec) is still a scratchpad invocation."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command("./.claude/scripts/scratchpad.py get key --plan PLAN-999")
        self.assertFalse(d.allow)


# --- decide_command — cross-plan gate -----------------------------------


class TestCrossPlanGate(ScratchpadHookTest):
    def test_cross_plan_blocked(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command(
            "python3 .claude/scripts/scratchpad.py get mykey --plan PLAN-010"
        )
        self.assertFalse(d.allow)
        self.assertIn("PLAN-010", d.reason or "")
        self.assertIn("PLAN-011", d.reason or "")

    def test_same_plan_allowed(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command(
            "python3 .claude/scripts/scratchpad.py get mykey --plan PLAN-011"
        )
        self.assertTrue(d.allow)

    def test_plan_equals_syntax_supported(self) -> None:
        """`--plan=PLAN-X` should parse like `--plan PLAN-X`."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command(
            "python3 .claude/scripts/scratchpad.py list --plan=PLAN-999"
        )
        self.assertFalse(d.allow)
        self.assertIn("PLAN-999", d.reason or "")

    def test_plan_flag_omitted_allowed(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command(
            "python3 .claude/scripts/scratchpad.py list"
        )
        self.assertTrue(d.allow)

    def test_no_session_plan_fail_open(self) -> None:
        """When session plan cannot be derived, allow (no trust anchor)."""
        os.environ.pop("CLAUDE_SESSION_ID", None)
        d = csa.decide_command(
            "python3 .claude/scripts/scratchpad.py get k --plan PLAN-011"
        )
        self.assertTrue(d.allow)

    def test_cross_plan_in_compound_command_blocked(self) -> None:
        """Subcommand chaining: block even when not the first clause."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        d = csa.decide_command(
            "echo hi && python3 .claude/scripts/scratchpad.py get k --plan PLAN-ZZZ"
        )
        self.assertFalse(d.allow)

    def test_empty_command_allowed(self) -> None:
        d = csa.decide_command("")
        self.assertTrue(d.allow)

    def test_unparseable_subcommand_skipped(self) -> None:
        """shlex failure on one chunk must not crash — just skip it."""
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        # Unclosed quote on purpose
        d = csa.decide_command('echo "unterminated && python3 scratchpad.py get k')
        self.assertTrue(d.allow)


# --- end-to-end main() --------------------------------------------------


class TestHookMainEntrypoint(ScratchpadHookTest):
    def _run_main_with(self, payload: dict) -> dict:
        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = io.StringIO()
            rc = csa.main()
            self.assertEqual(rc, 0)
            out = sys.stdout.getvalue()
        finally:
            sys.stdin = sys_stdin_orig
            sys.stdout = sys_stdout_orig
        return json.loads(out.splitlines()[-1])

    def test_main_emits_block_json_on_cross_plan(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-011", session_id="sess"
        )
        payload = {
            "session_id": "sess",
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "python3 .claude/scripts/scratchpad.py "
                    "set k v --plan PLAN-ZZZ"
                )
            },
        }
        decision = self._run_main_with(payload)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("PLAN-ZZZ", decision["reason"])

    def test_main_emits_allow_on_non_scratchpad_command(self) -> None:
        payload = {
            "session_id": "sess",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
        decision = self._run_main_with(payload)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_main_fail_open_on_stdin_parse_error(self) -> None:
        sys_stdin_orig = sys.stdin
        sys_stdout_orig = sys.stdout
        sys_stderr_orig = sys.stderr
        try:
            sys.stdin = io.StringIO("not json at all {{{")
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            rc = csa.main()
            self.assertEqual(rc, 0)
            out = sys.stdout.getvalue()
        finally:
            sys.stdin = sys_stdin_orig
            sys.stdout = sys_stdout_orig
            sys.stderr = sys_stderr_orig
        decision = json.loads(out.splitlines()[-1])
        self.assertEqual(decision.get("decision", "allow"), "allow")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
