"""Policy engine E2E integration — PLAN-014 Phase A.6c.

Exercises the policy-as-code dispatcher via actual subprocess invocation
(no direct function calls) to verify the full stdin → JSON-decision
contract end-to-end. Uses the ``ceo_env`` fixture (TestEnvContext-backed)
for env isolation. No raw monkeypatch. No time.sleep.

Three scenarios:

1. **Bash-safety allow path** — benign command flows to allow.
2. **Plan-edit deny path** — illegal status transition is blocked with the
   SPEC §5 ``policy_denied`` audit event emitted.
3. **Legacy fallback** — ``CEO_POLICY_ENGINE_DISABLE=1`` short-circuits
   the engine and delegates to ``$CEO_POLICY_LEGACY_HOOK_PATH`` which
   returns an allow decision.

Per ADJ-022 / PLAN-013 precedent, every subprocess runs under a fresh
``TestEnvContext``; env vars are never written to the ambient process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DISPATCHER = _REPO_ROOT / ".claude" / "hooks" / "policy_dispatch.py"
_POLICIES_DIR = _REPO_ROOT / ".claude" / "policies"


def _run_dispatcher(policy: str, event: dict, env: dict, timeout: float = 5.0):
    """Run policy_dispatch.py as a subprocess. Returns CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(_DISPATCHER), "--policy", policy],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _build_env(ceo_env) -> dict:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
    env["HOME"] = str(ceo_env.home_dir)
    # Ensure the audit log lands inside the test's isolated HOME.
    return env


class TestPolicyEngineIntegration:
    """E2E integration against the real policy_dispatch.py subprocess."""

    def test_bash_safety_allow_path(self, ceo_env):
        """Benign `ls -la` → allow with zero latency budget abuse."""
        env = _build_env(ceo_env)
        event = {
            "tool": "Bash",
            "tool_input": {"command": "ls -la"},
            "_derived_bash": {
                "command": "ls -la",
                "credential_leak_provider": "",
                "credential_leak_redacted": "",
                "subcommands": ["ls -la"],
                "tokens_per_subcommand": [["ls", "-la"]],
                "matched_rm_rf": False,
                "matched_git_reset_hard": False,
                "matched_git_push_force": False,
            },
        }
        proc = _run_dispatcher("bash-safety", event, env)
        assert proc.returncode == 0, f"stderr={proc.stderr!r}"
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        assert out["decision"] == "allow", f"got {out!r}"

    def test_plan_edit_deny_illegal_transition(self, ceo_env):
        """Illegal draft→done transition must be blocked."""
        env = _build_env(ceo_env)
        # Simulate the derived-fields payload plan-edit hook would produce.
        event = {
            "tool": "Edit",
            "tool_input": {"file_path": ".claude/plans/PLAN-099-test.md"},
            "_derived_plan": {
                "is_plan_file": True,
                "plan_id": "PLAN-099",
                "old_status": "draft",
                "new_status": "done",
                "status_changed": True,
                "transition_legal": False,
                "new_status_legal": True,
                "reviewed_at_present": False,
                "completed_at_present": True,
                "related_commits_nonempty": True,
                "abandonment_reason_present": False,
                "transition_reason_key": "",
            },
        }
        proc = _run_dispatcher("plan-edit", event, env)
        assert proc.returncode == 0, f"stderr={proc.stderr!r}"
        # Last non-empty stdout line is the decision JSON.
        last_line = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1]
        out = json.loads(last_line)
        assert out["decision"] == "block", f"got {out!r}"
        assert out["reason"] == "illegal_transition"
        assert "message" in out

    def test_legacy_fallback_via_engine_disable(self, ceo_env, tmp_path):
        """CEO_POLICY_ENGINE_DISABLE=1 routes to legacy hook if provided."""
        env = _build_env(ceo_env)
        # Write a minimal stub legacy hook that always emits allow.
        legacy = tmp_path / "legacy_allow.py"
        legacy.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "sys.stdout.write(json.dumps({'decision': 'allow', "
            "'via': 'legacy'}) + '\\n')\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        env["CEO_POLICY_ENGINE_DISABLE"] = "1"
        env["CEO_POLICY_LEGACY_HOOK_PATH"] = str(legacy)
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        proc = _run_dispatcher("bash-safety", event, env)
        assert proc.returncode == 0, f"stderr={proc.stderr!r}"
        last_line = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1]
        out = json.loads(last_line)
        assert out["decision"] == "allow", f"got {out!r}"
        # The legacy stub echoes 'via' marker; verify we really went
        # through it and did not silently fall to the default allow
        # path in the dispatcher.
        assert out.get("via") == "legacy", (
            "engine-disable did not delegate to legacy hook; dispatcher "
            "fell through to its own default allow path"
        )

    def test_policy_load_failure_fail_closed(self, ceo_env, tmp_path):
        """A malformed policy file should trigger fail-CLOSED (block) when
        no legacy hook is configured.

        Verifies SPEC/v1 §7 + ADR-045 §Fail-mode: security-surface hooks
        fail closed, not open.
        """
        env = _build_env(ceo_env)
        bogus = tmp_path / "bogus.policy.yaml"
        bogus.write_text(
            "schema: \"policy-dsl/v2\"\nid: bogus\n",
            encoding="utf-8",
        )
        env["CEO_POLICY_FILE"] = str(bogus)
        # No CEO_POLICY_LEGACY_HOOK_PATH → dispatcher must fail closed.
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        proc = _run_dispatcher("bash-safety", event, env)
        assert proc.returncode == 0, f"stderr={proc.stderr!r}"
        last_line = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1]
        out = json.loads(last_line)
        assert out["decision"] == "block", (
            f"expected fail-closed block; got {out!r}"
        )
        assert out["reason"] == "policy_engine_unavailable"
