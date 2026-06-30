"""End-to-end test: real subprocess.run() of check_agent_spawn.py + audit_log.py.

This is the integration test that exercises the full wiring:
1. Spawn check_agent_spawn.py as a real subprocess with piped stdin
2. Verify the decision JSON returns on stdout
3. Spawn audit_log.py as a real subprocess with piped stdin
4. Verify a JSONL row lands in the isolated audit log

Both hooks must run under the TestEnvContext temp dirs so nothing leaks
into the real $HOME.

No mocks — this is the "does the python interpreter actually run our
files end-to-end with the right env" test.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402


HOOKS_DIR = Path(__file__).resolve().parent.parent
CHECK_HOOK = HOOKS_DIR / "check_agent_spawn.py"
AUDIT_HOOK = HOOKS_DIR / "audit_log.py"


@unittest.skipUnless(os.name == "posix", "POSIX only (subprocess + fcntl)")
class TestE2EHookChain(TestEnvContext):
    def _run_hook(self, script_path, stdin_text):
        """Run a Python hook as a subprocess with isolated env."""
        env = os.environ.copy()
        # Ensure the hook can find _lib via the hooks dir (it does its
        # own sys.path insertion, but we set PYTHONPATH as defense).
        env["PYTHONPATH"] = str(HOOKS_DIR)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        return result

    def test_check_agent_spawn_allows_generic(self):
        payload = json.dumps({
            "session_id": "e2e-1",
            "tool_name": "Agent",
            "tool_input": {
                "description": "Research an API spec",
                "prompt": "Look at the docs and summarize",
            },
        })
        result = self._run_hook(CHECK_HOOK, payload)
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout.strip())
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_check_agent_spawn_blocks_named_without_skill(self):
        # Need a team file so the name detection fires
        self.write_project_file(
            ".claude/team.md", "- **Sofia** leads security"
        )
        payload = json.dumps({
            "session_id": "e2e-2",
            "tool_name": "Agent",
            "tool_input": {
                "description": "Ask Sofia to review auth.ts",
                "prompt": "please review",
            },
        })
        result = self._run_hook(CHECK_HOOK, payload)
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout.strip())
        self.assertEqual(decision["decision"], "block")
        self.assertIn("GOVERNANCE", decision["reason"])

    def test_audit_log_writes_jsonl_row(self):
        payload = json.dumps({
            "session_id": "e2e-3",
            "tool_name": "Agent",
            "tool_input": {
                "description": "End-to-end audit log test",
                "prompt": (
                    "## AGENT PROFILE\nSofia\n\n"
                    "## SKILL CONTENT\nSKILL: testing-strategy\n"
                    + ("rule-word " * 40) + "\n\n"
                    "## FILE ASSIGNMENT\n- tests/e2e.py"
                ),
                "subagent_type": "general-purpose",
            },
            "tool_response": {"type": "text", "content": "ok"},
        })
        result = self._run_hook(AUDIT_HOOK, payload)
        self.assertEqual(result.returncode, 0)
        # Silent stdout is part of the contract
        self.assertEqual(result.stdout, "")

        # The entry should have landed in the isolated audit dir
        log_text = self.read_audit_log()
        self.assertTrue(log_text)
        lines = [ln for ln in log_text.split("\n") if ln]
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["session_id"], "e2e-3")
        self.assertEqual(entry["skill"], "testing-strategy")
        self.assertTrue(entry["has_profile"])
        self.assertTrue(entry["has_file_assignment"])
        self.assertIn("hook_duration_ms", entry)

    def test_chain_check_then_audit_roundtrip(self):
        """Simulate Claude Code firing PreToolUse + PostToolUse in sequence."""
        # The same payload would be sent to both hooks — check first, then audit.
        payload = json.dumps({
            "session_id": "e2e-chain",
            "tool_name": "Agent",
            "tool_input": {
                "description": "Chain test, compliant spawn",
                "prompt": (
                    "## AGENT PROFILE\nSome Named Person\n\n"
                    "## SKILL CONTENT\nSKILL: code-review-checklist\n"
                    + ("rule-word " * 40) + "\n\n"
                    "## FILE ASSIGNMENT\n- src/foo.ts"
                ),
            },
            "tool_response": {"type": "text"},
        })

        # PreToolUse — check_agent_spawn
        check_result = self._run_hook(CHECK_HOOK, payload)
        self.assertEqual(check_result.returncode, 0)
        check_decision = json.loads(check_result.stdout.strip())
        self.assertEqual(check_decision.get("decision", "allow"), "allow")

        # PostToolUse — audit_log
        audit_result = self._run_hook(AUDIT_HOOK, payload)
        self.assertEqual(audit_result.returncode, 0)
        self.assertEqual(audit_result.stdout, "")

        # Verify the audit entries.
        # PreToolUse (check_agent_spawn) emits spawn_confidence_advisory;
        # PostToolUse (audit_log) emits the agent_spawn event — 2 lines total.
        log_text = self.read_audit_log()
        lines = [ln for ln in log_text.split("\n") if ln]
        self.assertEqual(len(lines), 2)
        entries = [json.loads(ln) for ln in lines]
        spawn_entries = [e for e in entries if e.get("action") == "agent_spawn"]
        self.assertEqual(len(spawn_entries), 1)
        entry = spawn_entries[0]
        self.assertEqual(entry["session_id"], "e2e-chain")
        self.assertEqual(entry["skill"], "code-review-checklist")

    def test_shim_script_runs_check_hook(self):
        """Verify _python-hook.sh shim resolves + forwards stdin correctly."""
        shim = HOOKS_DIR / "_python-hook.sh"
        payload = json.dumps({
            "session_id": "e2e-shim",
            "tool_name": "Agent",
            "tool_input": {
                "description": "Generic task via shim",
                "prompt": "do the thing",
            },
        })
        result = subprocess.run(
            ["bash", str(shim), "check_agent_spawn.py"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout.strip())
        self.assertEqual(decision.get("decision", "allow"), "allow")


if __name__ == "__main__":
    unittest.main()
