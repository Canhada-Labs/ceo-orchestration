"""PLAN-043 Phase 4 — Unit tests for check_tier_policy_staged.py hook.

The hook is staged at
``.claude/scripts/tier_policy_cli/check_tier_policy_staged.py``
(renamed from ``tier_policy/`` per PLAN-076 fork (f) for Python-
importable underscore form). Once promoted to canonical
``.claude/hooks/check_tier_policy.py`` (PLAN-043 Phase 5), the hook
blocks Edit/Write on VETO-class agent files without a dedicated
``VETO-CHANGE:`` sentinel.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent.parent


def _load_hook():
    """Late-load the canonical hook module (post PLAN-043 Phase 5 promote)."""
    canonical = _SCRIPTS.parent / "hooks" / "check_tier_policy.py"
    staged = _SCRIPTS / "tier_policy_cli" / "check_tier_policy_staged.py"
    path = canonical if canonical.exists() else staged
    spec = importlib.util.spec_from_file_location(
        "_hook_under_test", str(path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CheckTierPolicyHookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-043-hook-")
        self.repo_root = Path(self._tmp.name)
        (self.repo_root / ".claude" / "agents").mkdir(parents=True)
        (self.repo_root / ".claude" / "plans").mkdir(parents=True)
        self.hook = _load_hook()

    def tearDown(self):
        self._tmp.cleanup()

    def _write_sentinel(
        self,
        scope_paths,
        *,
        plan: str = "PLAN-999",
        approved_by: str = "@owner abcdef1234567890",
        veto_change: bool = True,
    ):
        sentinel = (
            self.repo_root / ".claude" / "plans"
            / plan / "architect" / "round-1" / "approved.md"
        )
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        body = [
            "Approved-By: {}".format(approved_by),
            "",
            "Scope:",
        ]
        for p in scope_paths:
            body.append("- {}".format(p))
        body.append("")
        if veto_change:
            body.append("VETO-CHANGE: intentional VETO floor demote")
        sentinel.write_text("\n".join(body), encoding="utf-8")

    def _write_agent(self, slug):
        p = self.repo_root / ".claude" / "agents" / f"{slug}.md"
        p.write_text(
            "---\nmodel: claude-opus-4-8\n---\n", encoding="utf-8"
        )
        return p

    def test_non_watched_tool_allowed(self):
        path = self._write_agent("code-reviewer")
        result = self.hook.decide(
            tool_name="Read",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        # PLAN-091-followup S116 fail-open contract: bare {} envelope
        # is the schema-compliant allow signal.
        self.assertEqual(json.loads(result).get("decision", "allow"), "allow")

    def test_non_veto_file_allowed(self):
        path = self._write_agent("qa-architect")
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result).get("decision", "allow"), "allow")

    def test_veto_file_without_sentinel_blocked(self):
        path = self._write_agent("code-reviewer")
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        decision = json.loads(result)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("VETO-FLOOR-BLOCKED", decision["reason"])

    def test_veto_file_with_matching_sentinel_allowed(self):
        path = self._write_agent("code-reviewer")
        self._write_sentinel([".claude/agents/code-reviewer.md"])
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result).get("decision", "allow"), "allow")

    def test_veto_file_with_sentinel_missing_veto_change_marker_blocked(
        self,
    ):
        path = self._write_agent("code-reviewer")
        self._write_sentinel(
            [".claude/agents/code-reviewer.md"],
            veto_change=False,
        )
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result)["decision"], "block")

    def test_veto_file_with_sentinel_for_other_agent_blocked(self):
        path = self._write_agent("security-engineer")
        self._write_sentinel([".claude/agents/code-reviewer.md"])
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result)["decision"], "block")

    def test_write_tool_watched(self):
        path = self._write_agent("code-reviewer")
        result = self.hook.decide(
            tool_name="Write",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result)["decision"], "block")

    def test_multiedit_tool_watched(self):
        path = self._write_agent("security-engineer")
        result = self.hook.decide(
            tool_name="MultiEdit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result)["decision"], "block")

    def test_empty_file_path_allowed(self):
        result = self.hook.decide(
            tool_name="Edit",
            file_path="",
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result).get("decision", "allow"), "allow")

    def test_approved_by_malformed_rejected(self):
        path = self._write_agent("code-reviewer")
        self._write_sentinel(
            [".claude/agents/code-reviewer.md"],
            approved_by="not-a-handle-no-sha",
        )
        result = self.hook.decide(
            tool_name="Edit",
            file_path=str(path),
            repo_root=self.repo_root,
        )
        self.assertEqual(json.loads(result)["decision"], "block")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
