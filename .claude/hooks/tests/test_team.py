"""Tests for _lib.team — team member name extraction."""

from __future__ import annotations

import sys
from pathlib import Path


from _lib import team  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestTeamNameExtraction(TestEnvContext):
    def test_extracts_single_name_from_team_md(self):
        self.write_project_file(
            ".claude/team.md",
            "### 1. VP Engineering — **Sofia**\n**Sofia Nakamura** leads engineering.",
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("Spawn Sofia to review"))

    def test_extracts_multiple_names(self):
        self.write_project_file(
            ".claude/team.md",
            "- **Alice** owns security\n- **Bob** owns CI\n- **Carol** owns data",
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        for name in ("Alice", "Bob", "Carol"):
            self.assertTrue(regex.search(f"ask {name} to help"))

    def test_ignores_all_caps_bold(self):
        """**NEVER**, **API**, **CEO** should not match (would be false positives)."""
        self.write_project_file(
            ".claude/team.md",
            "- **NEVER** commit secrets\n- **API** keys go in env\n- **Alice** reviews",
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("Alice should check"))
        # NEVER is all caps, shouldn't be in the regex
        names = team.extract_names(team.default_team_files(self.project_dir))
        self.assertNotIn("NEVER", names)
        self.assertNotIn("API", names)

    def test_case_insensitive_match(self):
        self.write_project_file(
            ".claude/team.md", "- **Sofia** leads"
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("SOFIA reviews"))
        self.assertTrue(regex.search("sofia reviews"))

    def test_whole_word_boundary(self):
        """'Alice' should match in 'Alice please' but not in 'aliceX'."""
        self.write_project_file(
            ".claude/team.md", "- **Alice** reviews"
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("Alice please"))
        self.assertFalse(regex.search("aliceX"))  # no word boundary

    def test_no_team_files_returns_none(self):
        # project_dir exists but has no team.md or frontend-team.md
        regex = team.load_names(self.project_dir)
        self.assertIsNone(regex)

    def test_accented_name_extraction(self):
        self.write_project_file(
            ".claude/team.md", "- **Amélie** leads"
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("spawn Amélie"))

    def test_domain_team_personas_included(self):
        self.write_project_file(
            ".claude/skills/domains/fintech/team-personas.md",
            "- **Viktor** owns financial math",
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("ask Viktor"))

    def test_frontend_team_included(self):
        self.write_project_file(
            ".claude/frontend-team.md",
            "- **Amara** leads frontend",
        )
        regex = team.load_names(self.project_dir)
        self.assertIsNotNone(regex)
        self.assertTrue(regex.search("Amara should review"))
