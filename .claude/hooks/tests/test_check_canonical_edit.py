"""Tests for check_canonical_edit.py — sentinel-gated canonical edits.

Sprint 5 Phase 7 (ADR-010). Verifies:
1. Non-canonical paths pass silently
2. Canonical paths without sentinel are blocked
3. Canonical paths with valid sentinel are allowed
4. Sentinel without Approved-By is rejected
5. Sentinel that doesn't list the path in Scope: is rejected
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

_HOOK = _HOOKS_DIR / "check_canonical_edit.py"


class CheckCanonicalEditTest(TestEnvContext):

    def _invoke(self, payload: dict) -> tuple[int, str, str]:
        """Run the hook as subprocess, returning (rc, stdout, stderr).

        PLAN-045 Wave 1 P0-01: the hook now requires a detached `.asc`
        GPG signature alongside every sentinel OR an explicit
        ``CEO_SENTINEL_UNLOCK`` + ``CEO_SENTINEL_UNLOCK_ACK`` env pair
        (the documented interim dual-auth bypass per ADR-010 amendment).
        These tests create PLAINTEXT sentinels — they exercise the
        Approved-By + Scope plaintext path only, not GPG — so we set
        the bypass env by default. Tests that need to exercise the GPG
        verification explicitly should override these env vars.
        """
        env = {**os.environ}
        # PLAN-086 Wave I.1 (ADR-119) tightened the env-override regex to
        # ^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$. Older "PLAN-TEST"
        # value fails the new pattern; use a compliant test fixture slug.
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _make_repo_layout(self) -> Path:
        """Set up a minimal repo layout under self.project_dir."""
        # Create canonical files
        (self.project_dir / ".claude").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "team.md").write_text("team", encoding="utf-8")
        (self.project_dir / ".claude" / "frontend-team.md").write_text("front", encoding="utf-8")
        (self.project_dir / ".claude" / "pitfalls-catalog.yaml").write_text("pf", encoding="utf-8")
        # A canonical SKILL.md
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("skill", encoding="utf-8")
        return self.project_dir

    def _write_sentinel(self, plan_id: str, scope_paths: list, approved_by: str = "@Canhada-Labs deadbeef"):
        sentinel_dir = self.project_dir / ".claude" / "plans" / plan_id / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        scope_block = "\n".join(f"  - {p}" for p in scope_paths)
        body = (
            "---\nplan: " + plan_id + "\nround: 1\ntype: architect-sentinel\n---\n\n"
            f"Approved-By: {approved_by}\n"
            "Approved-At: 2026-04-13T15:30:00Z\n"
            "Scope:\n"
            f"{scope_block}\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        return sentinel_dir / "approved.md"

    def test_non_canonical_path_allows(self):
        self._make_repo_layout()
        unrelated = self.project_dir / "src" / "foo.ts"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("// noop", encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(unrelated)}})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_canonical_path_without_sentinel_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "team.md"
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("CANONICAL-EDIT-BLOCKED", d["reason"])
        self.assertIn(".claude/team.md", d["reason"])

    def test_canonical_skill_md_blocks(self):
        self._make_repo_layout()
        target = self.project_dir / ".claude" / "skills" / "core" / "test-skill" / "SKILL.md"
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_canonical_path_with_valid_sentinel_allows(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        self._write_sentinel("PLAN-099", [target_rel])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", d)
        self.assertIn("sentinel", d["systemMessage"])

    def test_sentinel_without_approved_by_rejected(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        # Write sentinel manually without Approved-By line
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        (sentinel_dir / "approved.md").write_text(
            "---\nplan: PLAN-099\n---\n\nScope:\n  - " + target_rel + "\n",
            encoding="utf-8",
        )
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    def test_sentinel_without_path_in_scope_rejected(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        # Sentinel exists but Scope doesn't include team.md
        self._write_sentinel("PLAN-099", [".claude/skills/core/test-skill/SKILL.md"])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    def test_no_file_path_allows_silently(self):
        self._make_repo_layout()
        rc, out, _ = self._invoke({"tool_input": {}})
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_malformed_payload_allows(self):
        self._make_repo_layout()
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="garbage{{{",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ},
        )
        self.assertEqual(json.loads(proc.stdout).get("decision", "allow"), "allow")


class CanonicalGuardsExpansionTest(TestEnvContext):
    """PLAN-019 P1-SEC-A: regression tests for each expanded guard pattern.

    Every new path added to `_CANONICAL_GUARDS` must block by default
    (no sentinel). The hook is invoked in-process via the `decide()`
    function with `_is_canonical` to avoid spawning a subprocess per
    test (faster + still covers the segment-glob matcher).
    """

    def _make_repo_layout(self) -> None:
        # Just the .claude root + a .github + SPEC/v1 skeleton
        (self.project_dir / ".claude").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "hooks").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "hooks" / "_lib").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "hooks" / "_lib" / "adapters").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "policies").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "policies" / "fixtures").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "adr").mkdir(exist_ok=True)
        (self.project_dir / "SPEC" / "v1").mkdir(parents=True, exist_ok=True)
        (self.project_dir / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (self.project_dir / "scripts").mkdir(exist_ok=True)

    def _assert_canonical(self, rel: str) -> None:
        """Create a file at `rel` and assert that `_is_canonical` is True."""
        import check_canonical_edit as cce  # local import for hooks path
        target = self.project_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# canonical", encoding="utf-8")
        self.assertTrue(
            cce._is_canonical(str(target), self.project_dir),
            msg=f"Expected '{rel}' to match _CANONICAL_GUARDS",
        )

    def _assert_blocks(self, rel: str) -> None:
        """End-to-end: invoke the hook and assert a block decision."""
        import check_canonical_edit as cce  # local import
        target = self.project_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# canonical", encoding="utf-8")
        out = cce.decide(file_path=str(target), repo_root=self.project_dir)
        d = json.loads(out)
        self.assertEqual(
            d["decision"],
            "block",
            msg=f"Expected '{rel}' to be blocked (no sentinel)",
        )
        self.assertIn("CANONICAL-EDIT-BLOCKED", d["reason"])

    def test_hook_py_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/hooks/check_agent_spawn.py")
        self._assert_canonical(".claude/hooks/audit_log.py")
        self._assert_canonical(".claude/hooks/check_budget.py")

    def test_python_hook_shim_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/hooks/_python-hook.sh")

    def test_lib_modules_are_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/hooks/_lib/policy.py")
        self._assert_canonical(".claude/hooks/_lib/redact.py")
        self._assert_canonical(".claude/hooks/_lib/audit_emit.py")
        self._assert_canonical(".claude/hooks/_lib/contract.py")
        self._assert_canonical(".claude/hooks/_lib/adapters/claude.py")

    def test_policies_yaml_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/policies/bash-safety.policy.yaml")
        self._assert_canonical(".claude/policies/plan-edit.policy.yaml")

    def test_policies_fixtures_are_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(
            ".claude/policies/fixtures/bash-safety.fixtures.jsonl"
        )

    def test_settings_json_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/settings.json")

    def test_adr_files_are_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".claude/adr/ADR-099-test.md")
        self._assert_canonical(".claude/adr/README.md")

    def test_spec_v1_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical("SPEC/v1/plan.schema.md")
        self._assert_canonical("SPEC/v1/README.md")

    def test_ci_workflows_are_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".github/workflows/validate.yml")
        self._assert_canonical(".github/workflows/release.yml")

    def test_codeowners_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical(".github/CODEOWNERS")

    def test_install_scripts_are_canonical(self):
        self._make_repo_layout()
        self._assert_canonical("scripts/install.sh")
        self._assert_canonical("scripts/install-npm.sh")
        self._assert_canonical("scripts/upgrade.sh")

    def test_protocol_md_is_canonical(self):
        self._make_repo_layout()
        self._assert_canonical("PROTOCOL.md")

    def test_claude_md_is_NOT_canonical(self):
        """CLAUDE.md intentionally excluded — see DYN-SEC1."""
        import check_canonical_edit as cce
        self._make_repo_layout()
        target = self.project_dir / "CLAUDE.md"
        target.write_text("# claude", encoding="utf-8")
        self.assertFalse(cce._is_canonical(str(target), self.project_dir))

    def test_expanded_hook_py_blocks_end_to_end(self):
        """End-to-end block for a newly-guarded path (regression)."""
        self._make_repo_layout()
        self._assert_blocks(".claude/hooks/check_agent_spawn.py")

    def test_expanded_settings_json_blocks_end_to_end(self):
        self._make_repo_layout()
        self._assert_blocks(".claude/settings.json")

    def test_expanded_adr_blocks_end_to_end(self):
        self._make_repo_layout()
        self._assert_blocks(".claude/adr/ADR-050-example.md")

    def test_expanded_workflow_blocks_end_to_end(self):
        self._make_repo_layout()
        self._assert_blocks(".github/workflows/release.yml")


if __name__ == "__main__":
    unittest.main()
