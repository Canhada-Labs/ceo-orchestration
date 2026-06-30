"""Unit tests for handlers/list_agents.py — team.md table parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Bootstrap sys.path.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

from handlers import list_agents  # type: ignore[import-not-found]  # noqa: E402


_TEAM_MD_FIXTURE = """\
# Team

## ICs

| Archetype | Reports to | Focus | Primary skill | Secondary |
|-----------|-----------|-------|---------------|-----------|
| **Staff Backend Engineer** | VP Engineering | APIs | `public-api-design` | — |
| **Principal QA Architect** | VP Engineering | Tests | `testing-strategy` | — |

## Leadership

| Role | Reports to | Area | Primary skill |
|------|-----------|------|---------------|
| **VP Engineering** | CEO | Architecture | `architecture-decisions` |
"""


_FRONTEND_MD_FIXTURE = """\
# Frontend Team

| Archetype | Reports to | Focus | Primary skill | Secondary |
|-----------|-----------|-------|---------------|-----------|
| **UI/UX Lead** | VP Product | Design system | `frontend-architecture` | — |
"""


class TestListAgents(TestEnvContext):

    def test_returns_archetypes_from_both_files(self):
        team = self.project_dir / ".claude" / "team.md"
        team.parent.mkdir(parents=True, exist_ok=True)
        team.write_text(_TEAM_MD_FIXTURE, encoding="utf-8")
        ft = self.project_dir / ".claude" / "frontend-team.md"
        ft.write_text(_FRONTEND_MD_FIXTURE, encoding="utf-8")
        result = list_agents.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        names = {a["name"] for a in result["archetypes"]}
        self.assertIn("Staff Backend Engineer", names)
        self.assertIn("Principal QA Architect", names)
        self.assertIn("VP Engineering", names)
        self.assertIn("UI/UX Lead", names)

    def test_handles_missing_team_md_gracefully(self):
        # No team.md at all — return empty list, no error.
        result = list_agents.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        self.assertEqual(result["archetypes"], [])
        self.assertEqual(result["total"], 0)

    def test_skill_slugs_extracted_from_backticks(self):
        team = self.project_dir / ".claude" / "team.md"
        team.parent.mkdir(parents=True, exist_ok=True)
        team.write_text(_TEAM_MD_FIXTURE, encoding="utf-8")
        result = list_agents.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        sba = next(
            a for a in result["archetypes"]
            if a["name"] == "Staff Backend Engineer"
        )
        self.assertEqual(sba["skill_primary"], "public-api-design")
        self.assertEqual(sba["tier"], "backend")


if __name__ == "__main__":
    unittest.main()
