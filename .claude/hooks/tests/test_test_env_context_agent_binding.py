"""PLAN-106-FOLLOWUP Wave A.3 — TestEnvContext agent-binding helper tests."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_HOOKS_DIR = _HERE.parent.parent  # .claude/hooks/
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from tests._agent_fixture import materialize_agent_binding  # noqa: E402


class TestEnvContextDefaultsHaveNoAgentDir(TestEnvContext):
    """Case (a): default empty list → no .claude/agents/ in sandbox."""

    def test_default_no_agents_dir_materialized(self) -> None:
        agents_dir = self.project_dir / ".claude" / "agents"
        self.assertFalse(
            agents_dir.exists(),
            f"sandbox agents dir was created when AGENT_BINDINGS_TO_"
            f"MATERIALIZE was empty: {agents_dir}",
        )


class TestEnvContextMaterializesCodeReviewer(TestEnvContext):
    """Case (b): one name → file present + frontmatter has model + veto_floor."""

    AGENT_BINDINGS_TO_MATERIALIZE = ["code-reviewer"]

    def test_code_reviewer_binding_materialized(self) -> None:
        path = self.project_dir / ".claude" / "agents" / "code-reviewer.md"
        self.assertTrue(path.is_file(), f"expected fixture at {path}")
        text = path.read_text(encoding="utf-8")
        # Disk source has model: claude-fable-5 (ADR-149 W0) + veto_floor: true
        self.assertIn("model: claude-fable-5", text)
        self.assertIn("veto_floor: true", text)
        self.assertIn("name: code-reviewer", text)


class TestEnvContextMaterializesQaArchitect(TestEnvContext):
    """Case (b'): disk-sourced model is faithful (sonnet, not opus)."""

    AGENT_BINDINGS_TO_MATERIALIZE = ["qa-architect"]

    def test_qa_architect_model_disk_sourced(self) -> None:
        path = self.project_dir / ".claude" / "agents" / "qa-architect.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        # qa-architect ships with sonnet on disk — the fixture MUST NOT
        # hardcode opus.
        self.assertIn("model: claude-sonnet-4-6", text)
        self.assertNotIn("model: claude-opus-4-8", text)


class TestMaterializeRefusesEscape(TestEnvContext):
    """Case (containment): sandbox-root containment refuses escape.

    PLAN-108 S145 Codex Fix #6: inherit TestEnvContext (was bare unittest.TestCase)
    to satisfy check-test-env-hygiene.py contract per ADR-031 mandate.
    """

    def test_materialize_refuses_outside_tmp_root(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="test-agent-escape-") as tmp_root:
            outside_dir = Path(tmp_root).parent  # escape: parent of tmp_root
            with self.assertRaises(ValueError):
                materialize_agent_binding(
                    outside_dir,
                    "code-reviewer",
                    tmp_root=Path(tmp_root),
                )


class TestMaterializeMissingBindingRaises(TestEnvContext):
    """Case (negative): unknown agent name raises FileNotFoundError.

    PLAN-108 S145 Codex Fix #6: inherit TestEnvContext (was bare unittest.TestCase).
    """

    def test_materialize_unknown_raises(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="test-agent-missing-") as tmp_root:
            sandbox = Path(tmp_root) / "sandbox"
            sandbox.mkdir()
            with self.assertRaises(FileNotFoundError):
                materialize_agent_binding(
                    sandbox,
                    "nonexistent-agent-xyz",
                    tmp_root=Path(tmp_root),
                )


# ---- AC-VETO: end-to-end check_agent_spawn.decide allow path ---------------


class CheckAgentSpawnAllowsWithFixture(TestEnvContext):
    """AC-VETO: after materializing code-reviewer, decide() returns allow."""

    AGENT_BINDINGS_TO_MATERIALIZE = ["code-reviewer"]

    def test_decide_allow_with_fixture(self) -> None:
        import check_agent_spawn  # noqa: F401 — local import after sys.path setup
        prompt = (
            "PERSONA: code-reviewer specialist\n"
            "Please review this code.\n"
            "## SKILL CONTENT\n"
            "name: code-review-checklist\n"
            + ("body " * 200)
            + "\n"
        )
        # Point check_agent_spawn at the sandbox project_dir explicitly.
        # PLAN-108 S145 Codex Fix #6: use mock.patch.dict instead of bare env
        # assignment to satisfy check-test-env-hygiene.py contract.
        from unittest import mock
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            d = check_agent_spawn.decide(
                description="code-reviewer review request",
                prompt=prompt,
                names_regex=None,
                env=dict(os.environ),
                subagent_type="code-reviewer",
            )
        # The contract is: with the fixture present, decide() does NOT
        # return reason='veto_floor_demoted'. It may still return another
        # reason in degraded contexts (e.g. names_regex=None) — the
        # invariant under test is the VETO-floor gate specifically.
        self.assertNotEqual(
            getattr(d, "reason", ""),
            "veto_floor_demoted",
            f"VETO floor still blocks with fixture present: {d!r}",
        )


if __name__ == "__main__":
    unittest.main()
