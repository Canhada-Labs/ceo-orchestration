"""PLAN-045 Wave 1 — _lib.agent_frontmatter unit tests.

Covers:
- `resolve_agent_file`: path traversal rejection, invalid names.
- `parse_agent_file`: happy path, symlink reject, missing file, empty
  file, malformed frontmatter.
- `check_veto_floor_for_role`: every failure-mode string + happy path.
- `validate_veto_floor_models`: aggregated rollup, default roles,
  override roles, partial failure ordering.
- Constant invariants: VETO_FLOOR_ROLES frozenset, VETO_FLOOR_MODEL
  string — ensure no accidental mutation.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import agent_frontmatter  # noqa: E402
from _lib.agent_frontmatter import (  # noqa: E402
    AgentFrontmatterError,
    VETO_FLOOR_MODEL,
    VETO_FLOOR_ROLES,
    check_veto_floor_for_role,
    parse_agent_file,
    resolve_agent_file,
    validate_veto_floor_models,
)


_COMPLIANT_FRONTMATTER = """\
---
name: security-engineer
description: Principal Security Engineer with auth/crypto VETO authority.
version: anthropic-subagent-v1
tools: [Read, Grep, Glob, Bash]
model: claude-opus-4-8
---

# Principal Security Engineer
"""

_DEMOTED_FRONTMATTER = """\
---
name: security-engineer
description: Principal Security Engineer.
model: claude-haiku-4-5-20251001
---
"""

_NO_MODEL_FRONTMATTER = """\
---
name: security-engineer
description: Principal Security Engineer.
---
"""


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_veto_floor_roles_has_both(self) -> None:
        self.assertIn("code-reviewer", VETO_FLOOR_ROLES)
        self.assertIn("security-engineer", VETO_FLOOR_ROLES)

    def test_veto_floor_roles_is_frozen(self) -> None:
        with self.assertRaises(AttributeError):
            VETO_FLOOR_ROLES.add("new-role")  # type: ignore[attr-defined]

    def test_veto_floor_model_is_opus(self) -> None:
        self.assertEqual(VETO_FLOOR_MODEL, "claude-opus-4-8")


# --------------------------------------------------------------------------
# resolve_agent_file
# --------------------------------------------------------------------------


class TestResolveAgentFile(unittest.TestCase):
    def test_resolves_simple_name(self) -> None:
        p = resolve_agent_file(
            "security-engineer", Path("/tmp/agents")
        )
        self.assertEqual(p, Path("/tmp/agents/security-engineer.md"))

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaises(AgentFrontmatterError):
            resolve_agent_file("../etc/passwd", Path("/tmp/agents"))

    def test_rejects_slash(self) -> None:
        with self.assertRaises(AgentFrontmatterError):
            resolve_agent_file("nested/role", Path("/tmp/agents"))

    def test_rejects_empty(self) -> None:
        with self.assertRaises(AgentFrontmatterError):
            resolve_agent_file("", Path("/tmp/agents"))


# --------------------------------------------------------------------------
# parse_agent_file
# --------------------------------------------------------------------------


class TestParseAgentFile(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_happy_path(self) -> None:
        p = self.tmpdir / "security-engineer.md"
        p.write_text(_COMPLIANT_FRONTMATTER)
        fm = parse_agent_file(p)
        self.assertEqual(fm.get("name"), "security-engineer")
        self.assertEqual(fm.get("model"), "claude-opus-4-8")

    def test_missing_file(self) -> None:
        fm = parse_agent_file(self.tmpdir / "nope.md")
        self.assertEqual(fm, {})

    def test_empty_file(self) -> None:
        p = self.tmpdir / "empty.md"
        p.write_text("")
        fm = parse_agent_file(p)
        self.assertEqual(fm, {})

    def test_no_frontmatter(self) -> None:
        p = self.tmpdir / "bare.md"
        p.write_text("# Just a markdown file\n\nNo frontmatter here.\n")
        fm = parse_agent_file(p)
        self.assertEqual(fm, {})

    def test_symlink_leaf_rejected(self) -> None:
        real = self.tmpdir / "real.md"
        real.write_text(_COMPLIANT_FRONTMATTER)
        link = self.tmpdir / "link.md"
        link.symlink_to(real)
        fm = parse_agent_file(link)
        self.assertEqual(fm.get("__symlink_rejected__"), "leaf")

    def test_parent_symlink_rejected(self) -> None:
        real_parent = self.tmpdir / "real_parent"
        real_parent.mkdir()
        real = real_parent / "file.md"
        real.write_text(_COMPLIANT_FRONTMATTER)
        link_parent = self.tmpdir / "link_parent"
        link_parent.symlink_to(real_parent)
        fm = parse_agent_file(link_parent / "file.md")
        self.assertEqual(fm.get("__symlink_rejected__"), "parent")


# --------------------------------------------------------------------------
# check_veto_floor_for_role
# --------------------------------------------------------------------------


class TestCheckVetoFloorForRole(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.agents = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, role: str, content: str) -> Path:
        p = self.agents / f"{role}.md"
        p.write_text(content)
        return p

    def test_non_veto_role_passes(self) -> None:
        # Even if frontmatter is absent, non-VETO roles are exempt.
        ok, reason = check_veto_floor_for_role(
            "qa-architect", self.agents
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "not_veto_role")

    def test_compliant_file_passes(self) -> None:
        self._write("security-engineer", _COMPLIANT_FRONTMATTER)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_missing_file(self) -> None:
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "file_missing")

    def test_demoted_model(self) -> None:
        self._write("security-engineer", _DEMOTED_FRONTMATTER)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("model_mismatch:"))
        self.assertIn("haiku", reason)

    def test_model_field_missing(self) -> None:
        self._write("security-engineer", _NO_MODEL_FRONTMATTER)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "model_field_missing")

    def test_frontmatter_missing(self) -> None:
        self._write("security-engineer", "# Just markdown\n")
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "frontmatter_missing")

    def test_file_symlink_rejected(self) -> None:
        real = self.agents / "real.md"
        real.write_text(_COMPLIANT_FRONTMATTER)
        link = self.agents / "security-engineer.md"
        link.symlink_to(real)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "file_symlink_rejected")

    def test_parent_symlink_rejected(self) -> None:
        real_parent = Path(self._tmp.name).parent / f"agents-{os.getpid()}"
        real_parent.mkdir(exist_ok=True)
        self.addCleanup(lambda: real_parent.exists() and real_parent.rmdir())
        real_file = real_parent / "security-engineer.md"
        real_file.write_text(_COMPLIANT_FRONTMATTER)
        self.addCleanup(real_file.unlink)
        link_dir = self.agents / "link_agents"
        link_dir.symlink_to(real_parent)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", link_dir
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "parent_symlink_rejected")

    def test_custom_expected_model(self) -> None:
        self._write("security-engineer", _COMPLIANT_FRONTMATTER)
        ok, reason = check_veto_floor_for_role(
            "security-engineer", self.agents,
            expected_model="claude-haiku-4-5-20251001",
        )
        self.assertFalse(ok)
        self.assertIn("model_mismatch", reason)
        self.assertIn("opus", reason)

    def test_custom_veto_roles_scope(self) -> None:
        # Role is VETO per custom list → must pass model check.
        self._write("qa-architect", _DEMOTED_FRONTMATTER)
        ok, reason = check_veto_floor_for_role(
            "qa-architect", self.agents,
            veto_roles=["qa-architect"],
        )
        self.assertFalse(ok)
        self.assertIn("model_mismatch", reason)

    def test_invalid_role_name(self) -> None:
        ok, reason = check_veto_floor_for_role(
            "../../evil", self.agents,
            veto_roles=["../../evil"],
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid_role_name")


# --------------------------------------------------------------------------
# validate_veto_floor_models
# --------------------------------------------------------------------------


class TestValidateVetoFloorModels(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.agents = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, role: str, content: str) -> None:
        (self.agents / f"{role}.md").write_text(content)

    # PLAN-074 Wave 0 (S82, ADR-098 ceremony) extended VETO_FLOOR_ROLES from
    # the original 2 (code-reviewer + security-engineer) to 6 (added
    # threat-detection-engineer / identity-trust-architect / incident-commander
    # / llm-finops-architect). Existing legacy tests scope to the original 2
    # via `veto_roles=` param to preserve their semantic invariants.
    _LEGACY_VETO_ROLES = ["code-reviewer", "security-engineer"]

    def test_all_compliant(self) -> None:
        self._write("code-reviewer", _COMPLIANT_FRONTMATTER.replace(
            "security-engineer", "code-reviewer"
        ))
        self._write("security-engineer", _COMPLIANT_FRONTMATTER)
        ok, violations = validate_veto_floor_models(
            self.agents, veto_roles=self._LEGACY_VETO_ROLES
        )
        self.assertTrue(ok)
        self.assertEqual(violations, [])

    def test_one_missing(self) -> None:
        self._write("security-engineer", _COMPLIANT_FRONTMATTER)
        # code-reviewer missing
        ok, violations = validate_veto_floor_models(
            self.agents, veto_roles=self._LEGACY_VETO_ROLES
        )
        self.assertFalse(ok)
        self.assertEqual(len(violations), 1)
        self.assertIn("code-reviewer", violations[0])
        self.assertIn("file_missing", violations[0])

    def test_both_demoted(self) -> None:
        self._write("code-reviewer", _DEMOTED_FRONTMATTER.replace(
            "security-engineer", "code-reviewer"
        ))
        self._write("security-engineer", _DEMOTED_FRONTMATTER)
        ok, violations = validate_veto_floor_models(
            self.agents, veto_roles=self._LEGACY_VETO_ROLES
        )
        self.assertFalse(ok)
        self.assertEqual(len(violations), 2)

    def test_violations_sorted_by_role(self) -> None:
        # All missing — violations must be sorted.
        ok, violations = validate_veto_floor_models(
            self.agents, veto_roles=self._LEGACY_VETO_ROLES
        )
        self.assertFalse(ok)
        self.assertEqual(
            [v.split(":", 1)[0] for v in violations],
            sorted(self._LEGACY_VETO_ROLES),
        )

    def test_custom_roles_filter(self) -> None:
        # Only check security-engineer; missing code-reviewer should
        # NOT be a violation if it's not in the scoped list.
        self._write("security-engineer", _COMPLIANT_FRONTMATTER)
        ok, violations = validate_veto_floor_models(
            self.agents, veto_roles=["security-engineer"]
        )
        self.assertTrue(ok)

    def test_real_agents_dir_integration(self) -> None:
        """Smoke test against the live .claude/agents/ directory.

        Not strict — just asserts the validator runs cleanly and reports
        either all-pass or specific known violations. Useful as a
        canary that the actual shipped agents/*.md files comply.
        """
        repo_agents = Path(__file__).resolve().parents[3] / ".claude" / "agents"
        if not repo_agents.is_dir():
            self.skipTest("live agents dir not found")
        ok, violations = validate_veto_floor_models(repo_agents)
        # Either fully compliant or deliberately documenting mismatch.
        # Either way the validator must not crash.
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(violations, list)


if __name__ == "__main__":
    unittest.main()
