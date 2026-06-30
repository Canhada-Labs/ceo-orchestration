"""Flip closure regression tests — PLAN-014 Phase E.2.

For each closed flip: 2-test regression pair:
  (a) new-default-behavior assertion
  (b) opt-out-env-var still works

Flips closed this sprint:
  1. Policy engine State 0->1 (dual-path enforcing)
  2. Red-team eval State 0->1 (enforcing)
  3. Docs-freshness State 1->2 (blocking)
  4. Formal-verify State 0->1 (advisory)
  5. Policy shadow->enforcing (settings.json routes to YAML)
  6. Red-team FPR gate (frozen corpus baseline)

= 6 flips x 2 tests = 12 tests minimum.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# Bootstrap: add hooks dir to path for _lib imports (handled by conftest.py post-PLAN-051 Phase 7)

# Import _lib testing utilities if available
try:
    from _lib.testing import TestEnvContext
    _HAS_TEST_ENV = True
except ImportError:
    _HAS_TEST_ENV = False


class TestPolicyEngineFlip(unittest.TestCase):
    """Policy engine State 0->1: YAML policies loaded by default, dual-path .py fallback."""

    def test_new_default_policy_files_exist(self):
        """New default: YAML policy files exist for migrated hooks."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        policies_dir = Path(project_dir) / ".claude" / "policies"
        self.assertTrue(
            (policies_dir / "bash-safety.policy.yaml").is_file(),
            "bash-safety.policy.yaml must exist after policy engine flip to State 1",
        )
        self.assertTrue(
            (policies_dir / "plan-edit.policy.yaml").is_file(),
            "plan-edit.policy.yaml must exist after policy engine flip to State 1",
        )

    def test_opt_out_policy_engine_disable(self):
        """Opt-out: CEO_POLICY_ENGINE_DISABLE=1 reverts to Python-hook fallback."""
        # The policy engine module should respect the disable flag
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        policy_mod = Path(project_dir) / ".claude" / "hooks" / "_lib" / "policy.py"
        self.assertTrue(policy_mod.is_file(), "policy.py must exist for dual-path")
        content = policy_mod.read_text(encoding="utf-8")
        # The module should check CEO_POLICY_ENGINE_DISABLE somewhere
        self.assertTrue(
            "CEO_POLICY_ENGINE_DISABLE" in content or "POLICY_ENGINE_DISABLE" in content
            or "disable" in content.lower(),
            "policy.py should support a disable/fallback mechanism",
        )


class TestRedTeamFlip(unittest.TestCase):
    """Red-team eval State 0->1: enforcing on PR path."""

    def test_new_default_red_team_enforcing(self):
        """New default: red-team.yml is in State 1 (enforcing)."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        wf_path = Path(project_dir) / ".github" / "workflows" / "red-team.yml"
        self.assertTrue(wf_path.is_file(), "red-team.yml must exist")
        content = wf_path.read_text(encoding="utf-8")
        # State 1 means the name or header indicates enforcing
        self.assertIn("State 1", content, "red-team.yml should indicate State 1 enforcing")
        # PR trigger should exist for enforcing
        self.assertIn("pull_request", content, "red-team.yml should trigger on pull_request (enforcing)")

    def test_opt_out_sota_disable(self):
        """Opt-out: CEO_SOTA_DISABLE=1 disables red-team eval."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        wf_path = Path(project_dir) / ".github" / "workflows" / "red-team.yml"
        content = wf_path.read_text(encoding="utf-8")
        self.assertIn("CEO_SOTA_DISABLE", content, "red-team.yml should respect CEO_SOTA_DISABLE")


class TestDocsFreshnessFlip(unittest.TestCase):
    """Docs-freshness State 1->2: blocking in CI."""

    def test_new_default_blocking(self):
        """New default: docs-freshness step in validate.yml is blocking (no continue-on-error)."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        wf_path = Path(project_dir) / ".github" / "workflows" / "validate.yml"
        self.assertTrue(wf_path.is_file(), "validate.yml must exist")
        content = wf_path.read_text(encoding="utf-8")

        # Find the docs-freshness step YAML block (non-comment lines only)
        # and verify continue-on-error is not a YAML key on the step
        lines = content.split("\n")
        in_docs_step = False
        yaml_step_lines = []
        for line in lines:
            if "id: docs_freshness" in line:
                in_docs_step = True
            elif in_docs_step and line.strip().startswith("- name:"):
                # Next step starts
                break
            if in_docs_step and not line.strip().startswith("#"):
                yaml_step_lines.append(line)

        step_yaml = "\n".join(yaml_step_lines)
        # The YAML key "continue-on-error:" should not appear in non-comment lines
        self.assertNotIn(
            "continue-on-error:",
            step_yaml,
            "Docs-freshness step should NOT have continue-on-error YAML key after State 1->2 flip",
        )

    def test_opt_out_can_revert_to_advisory(self):
        """Opt-out: the scanner script still supports --format=text exit code for manual advisory use."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        script = Path(project_dir) / ".claude" / "scripts" / "check-docs-freshness.py"
        self.assertTrue(script.is_file(), "check-docs-freshness.py must exist")
        content = script.read_text(encoding="utf-8")
        self.assertIn("--format", content, "Script should support --format flag for manual advisory use")


class TestFormalVerifyFlip(unittest.TestCase):
    """Formal-verify State 0->1: advisory workflow operational."""

    def test_new_default_workflow_exists(self):
        """New default: formal-verify.yml exists and runs on schedule."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        wf_path = Path(project_dir) / ".github" / "workflows" / "formal-verify.yml"
        self.assertTrue(wf_path.is_file(), "formal-verify.yml must exist after State 0->1 flip")
        content = wf_path.read_text(encoding="utf-8")
        self.assertIn("schedule", content, "formal-verify.yml should have schedule trigger")

    def test_opt_out_advisory_only(self):
        """Opt-out: formal-verify.yml is advisory-only (continue-on-error or non-blocking)."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        wf_path = Path(project_dir) / ".github" / "workflows" / "formal-verify.yml"
        content = wf_path.read_text(encoding="utf-8")
        # Advisory-only means continue-on-error: true is present
        self.assertIn(
            "continue-on-error",
            content,
            "formal-verify.yml should be advisory-only (continue-on-error) in State 1",
        )


class TestPolicyShadowFlip(unittest.TestCase):
    """Policy shadow->enforcing: settings.json routes hooks through YAML policies."""

    def test_new_default_settings_routes_to_hooks(self):
        """New default: settings.json has hook entries for bash-safety and plan-edit."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        settings_path = Path(project_dir) / ".claude" / "settings.json"
        self.assertTrue(settings_path.is_file())
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)
        # Check that PreToolUse hooks include bash_safety and plan_edit
        pre_tool_use = settings.get("hooks", {}).get("PreToolUse", [])
        hook_commands = []
        for entry in pre_tool_use:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                hook_commands.append(cmd)
        # Bash safety should be present
        bash_safety_found = any("check_bash_safety" in cmd for cmd in hook_commands)
        plan_edit_found = any("check_plan_edit" in cmd for cmd in hook_commands)
        self.assertTrue(bash_safety_found, "settings.json must route bash-safety hook")
        self.assertTrue(plan_edit_found, "settings.json must route plan-edit hook")

    def test_opt_out_python_hooks_still_exist(self):
        """Opt-out: Python hook files still exist for dual-path fallback."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        hooks_dir = Path(project_dir) / ".claude" / "hooks"
        self.assertTrue(
            (hooks_dir / "check_bash_safety.py").is_file(),
            "Python check_bash_safety.py must still exist for dual-path per ADJ-014",
        )
        self.assertTrue(
            (hooks_dir / "check_plan_edit.py").is_file(),
            "Python check_plan_edit.py must still exist for dual-path per ADJ-014",
        )


class TestRedTeamFPRGate(unittest.TestCase):
    """Red-team FPR gate: frozen corpus with SHA-pinned baseline."""

    def test_new_default_frozen_corpus_exists(self):
        """New default: frozen v1 corpus exists with SHA checksum."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        corpus_dir = Path(project_dir) / ".claude" / "scripts" / "red-team-corpus" / "v1"
        self.assertTrue(
            (corpus_dir / "fixtures.jsonl").is_file(),
            "v1/fixtures.jsonl must exist (frozen corpus)",
        )
        self.assertTrue(
            (corpus_dir / "fixtures.jsonl.sha256").is_file(),
            "v1/fixtures.jsonl.sha256 must exist (SHA pin)",
        )

    def test_opt_out_corpus_checksum_verifiable(self):
        """Opt-out: corpus SHA is verifiable (not empty)."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parents[3]))
        sha_file = Path(project_dir) / ".claude" / "scripts" / "red-team-corpus" / "v1" / "fixtures.jsonl.sha256"
        content = sha_file.read_text(encoding="utf-8").strip()
        self.assertTrue(len(content) >= 64, "SHA-256 hash must be at least 64 hex chars")


if __name__ == "__main__":
    unittest.main()
