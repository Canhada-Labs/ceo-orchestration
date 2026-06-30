"""Tests for check_arbitration_kernel.py — HARD-DENY on kernel paths.

PLAN-019 P1-SEC-A defense-in-depth layer. This hook is strictly
stricter than the canonical-edit sentinel: no sentinel file can unlock
these paths; only a narrow env-var override `CEO_KERNEL_OVERRIDE +
CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` bypasses.

Test coverage:
- Non-kernel Edit/Write/MultiEdit passes silently.
- Kernel path without override → block.
- Kernel path with partial override (reason alone, or ACK alone) → block.
- Kernel path with malformed reason → block.
- Kernel path with wrong ACK token → block.
- Kernel path with full valid override → allow + systemMessage.
- Non-edit tool (Bash, Agent, etc.) → allow.
- Missing file_path on edit-class tool → fail-closed block.
- Parse error on stdin during edit-class → fail-closed block.
- Each kernel glob pattern: verify the intended path matches.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_arbitration_kernel.py"


class CheckArbitrationKernelTest(TestEnvContext):

    def _invoke(self, payload: dict, extra_env: dict = None) -> tuple:
        env = {**os.environ}
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _make_repo_layout(self) -> None:
        (self.project_dir / ".claude" / "hooks" / "_lib" / "adapters").mkdir(
            parents=True, exist_ok=True
        )
        (self.project_dir / ".claude" / "policies" / "fixtures").mkdir(
            parents=True, exist_ok=True
        )

    # ---- non-kernel / out-of-scope paths -------------------------------

    def test_non_edit_tool_always_allows(self):
        self._make_repo_layout()
        rc, out, _ = self._invoke({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_non_kernel_edit_allows(self):
        self._make_repo_layout()
        unrelated = self.project_dir / "src" / "foo.ts"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("x", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(unrelated), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_non_kernel_write_allows(self):
        self._make_repo_layout()
        unrelated = self.project_dir / "src" / "foo.ts"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("x", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"file_path": str(unrelated), "content": "hello"},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    # ---- kernel paths blocked without override -------------------------

    def test_kernel_governance_hook_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("ARBITRATION-KERNEL-BLOCKED", d["reason"])

    def test_kernel_canonical_edit_hook_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_canonical_edit.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_plan_edit_hook_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_plan_edit.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"file_path": str(target), "content": "new"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_self_hook_blocks(self):
        """The arbitration kernel hook cannot disable itself."""
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_arbitration_kernel.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_lib_policy_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "_lib" / "policy.py"
        target.write_text("# lib", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_lib_redact_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "_lib" / "redact.py"
        target.write_text("# lib", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(target),
                "edits": [{"old_string": "a", "new_string": "b"}],
            },
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_lib_audit_emit_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "_lib" / "audit_emit.py"
        target.write_text("# lib", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_lib_contract_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "_lib" / "contract.py"
        target.write_text("# lib", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_lib_claude_adapter_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "_lib" / "adapters" / "claude.py"
        target.write_text("# adapter", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_policy_yaml_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "policies" / "bash-safety.policy.yaml"
        target.write_text("# policy", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_kernel_policy_fixtures_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "policies" / "fixtures" / "x.jsonl"
        target.write_text('{"x":1}\n', encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"file_path": str(target), "content": "new"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    # ---- partial / malformed overrides still block ---------------------

    def test_override_reason_alone_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
            },
            extra_env={"CEO_KERNEL_OVERRIDE": "ADR-045-refactor"},
        )
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_override_ack_alone_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
            },
            extra_env={"CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT"},
        )
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_override_wrong_ack_token_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
            },
            extra_env={
                "CEO_KERNEL_OVERRIDE": "ADR-045-refactor",
                "CEO_KERNEL_OVERRIDE_ACK": "yes",  # wrong token
            },
        )
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_override_malformed_reason_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
            },
            extra_env={
                "CEO_KERNEL_OVERRIDE": "has spaces in reason",  # regex fails
                "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
            },
        )
        self.assertEqual(json.loads(out)["decision"], "block")

    # ---- valid override allows with systemMessage ---------------------

    def test_full_valid_override_allows(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "hooks" / "check_agent_spawn.py"
        target.write_text("# kernel", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
            },
            extra_env={
                "CEO_KERNEL_OVERRIDE": "ADR-045-refactor",
                "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
            },
        )
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", d)
        self.assertIn("override granted", d["systemMessage"])

    # ---- fail-closed posture -----------------------------------------

    def test_missing_file_path_on_edit_fails_closed(self):
        self._make_repo_layout()
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {},  # no file_path
        })
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("ARBITRATION-KERNEL-BLOCKED", d["reason"])

    def test_missing_file_path_on_write_fails_closed(self):
        self._make_repo_layout()
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"content": "x"},
        })
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_missing_file_path_on_non_edit_allows(self):
        """For non-edit tools, missing file_path is not fail-closed."""
        self._make_repo_layout()
        rc, out, _ = self._invoke({
            "tool_name": "Bash",
            "tool_input": {},
        })
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_malformed_payload_on_edit_fails_closed(self):
        """Stdin parse error + edit-class matcher → block (no tool_name
        available, but if the parse failed we cannot trust anything).
        """
        self._make_repo_layout()
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="garbage{{{",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ},
        )
        # Parse error path: tool_name defaults to "Edit" (event.tool_name
        # will be empty; main() falls back to "Edit"). Fail-closed block.
        d = json.loads(proc.stdout)
        self.assertEqual(d["decision"], "block")


class IsKernelPathUnitTest(unittest.TestCase):
    """Unit tests for _is_kernel_path glob coverage."""

    def setUp(self) -> None:
        import check_arbitration_kernel as cak
        self.cak = cak
        import tempfile
        self._tmp = Path(tempfile.mkdtemp(prefix="cak-test-"))
        # Create skeleton
        for rel in [
            ".claude/hooks/_lib/adapters",
            ".claude/policies/fixtures",
        ]:
            (self._tmp / rel).mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _touch(self, rel: str) -> Path:
        p = self._tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        return p

    def _assert_kernel(self, rel: str) -> None:
        p = self._touch(rel)
        self.assertTrue(
            self.cak._is_kernel_path(str(p), self._tmp),
            msg=f"Expected kernel match for '{rel}'",
        )

    def _assert_not_kernel(self, rel: str) -> None:
        p = self._touch(rel)
        self.assertFalse(
            self.cak._is_kernel_path(str(p), self._tmp),
            msg=f"Did not expect kernel match for '{rel}'",
        )

    def test_each_kernel_glob(self):
        self._assert_kernel(".claude/hooks/check_agent_spawn.py")
        self._assert_kernel(".claude/hooks/check_canonical_edit.py")
        self._assert_kernel(".claude/hooks/check_plan_edit.py")
        self._assert_kernel(".claude/hooks/check_arbitration_kernel.py")
        self._assert_kernel(".claude/hooks/check_skill_patch_sentinel.py")
        self._assert_kernel(".claude/hooks/_lib/policy.py")
        self._assert_kernel(".claude/hooks/_lib/redact.py")
        self._assert_kernel(".claude/hooks/_lib/audit_emit.py")
        self._assert_kernel(".claude/hooks/_lib/contract.py")
        self._assert_kernel(".claude/hooks/_lib/pii_patterns.py")
        self._assert_kernel(".claude/hooks/_lib/policy_preprocessors.py")
        self._assert_kernel(".claude/hooks/_lib/adapters/claude.py")
        self._assert_kernel(".claude/hooks/policy_dispatch.py")
        self._assert_kernel(".claude/policies/bash-safety.policy.yaml")
        self._assert_kernel(".claude/policies/fixtures/x.jsonl")
        # PLAN-089/PLAN-085 Wave A.4 / E.2 — promoted to kernel under
        # ADR-116-AMEND-1 kernel-extension-v2; previously listed as
        # non-kernel here when audit_log was an observer and check_budget
        # was advisory-only. PLAN-107 Wave D closeout aligned the test
        # fixture with the runtime _KERNEL_PATHS list.
        self._assert_kernel(".claude/hooks/audit_log.py")
        self._assert_kernel(".claude/hooks/check_budget.py")

    def test_non_kernel_paths(self):
        self._assert_not_kernel("src/app.ts")
        self._assert_not_kernel("docs/README.md")
        self._assert_not_kernel(".claude/plans/PLAN-099-x.md")

    def test_outside_repo_not_kernel(self):
        # Points to something outside the fake repo
        self.assertFalse(
            self.cak._is_kernel_path("/tmp/foo.py", self._tmp)
        )


class OverrideGrantedUnitTest(unittest.TestCase):
    """Unit tests for _override_granted env-var parsing."""

    def _check(self, env: dict) -> bool:
        import check_arbitration_kernel as cak
        return cak._override_granted(env)

    def test_both_missing(self):
        self.assertFalse(self._check({}))

    def test_reason_alone(self):
        self.assertFalse(self._check({"CEO_KERNEL_OVERRIDE": "x"}))

    def test_ack_alone(self):
        self.assertFalse(self._check({"CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT"}))

    def test_empty_reason(self):
        self.assertFalse(self._check({
            "CEO_KERNEL_OVERRIDE": "",
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }))

    def test_wrong_ack_case(self):
        self.assertFalse(self._check({
            "CEO_KERNEL_OVERRIDE": "ADR-045",
            "CEO_KERNEL_OVERRIDE_ACK": "i-accept",  # lowercase rejected
        }))

    def test_spaces_in_reason(self):
        self.assertFalse(self._check({
            "CEO_KERNEL_OVERRIDE": "with spaces",
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }))

    def test_very_long_reason_rejected(self):
        self.assertFalse(self._check({
            "CEO_KERNEL_OVERRIDE": "A" * 200,  # > 120 chars
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }))

    def test_valid_override(self):
        self.assertTrue(self._check({
            "CEO_KERNEL_OVERRIDE": "ADR-045-refactor",
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }))

    def test_valid_dots_underscores_dashes(self):
        self.assertTrue(self._check({
            "CEO_KERNEL_OVERRIDE": "plan-019.P1-SEC-A_v2",
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }))


if __name__ == "__main__":
    unittest.main()
