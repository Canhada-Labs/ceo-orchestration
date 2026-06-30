"""Unit tests for handlers/list_skills.py."""

from __future__ import annotations

import sys
import time
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

from handlers import list_skills  # type: ignore[import-not-found]  # noqa: E402


def _make_skill(project_dir: Path, tier: str, slug: str, description: str = "") -> Path:
    """Create a SKILL.md fixture under .claude/skills/<tier>/<slug>/."""
    skill_dir = project_dir / ".claude" / "skills" / tier / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    fm = (
        "---\n"
        f"description: {description}\n"
        "---\n\n"
        "# Skill body\n"
    )
    md.write_text(fm, encoding="utf-8")
    return md


def _make_domain_skill(
    project_dir: Path, domain: str, slug: str, description: str = ""
) -> Path:
    skill_dir = (
        project_dir
        / ".claude"
        / "skills"
        / "domains"
        / domain
        / "skills"
        / slug
    )
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f"---\ndescription: {description}\n---\n\n# Body\n",
        encoding="utf-8",
    )
    return md


class TestListSkills(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        list_skills._reset_cache()

    def test_returns_all_seeded_skills(self):
        _make_skill(self.project_dir, "core", "alpha", "alpha desc")
        _make_skill(self.project_dir, "core", "beta", "beta desc")
        _make_skill(self.project_dir, "frontend", "gamma", "gamma desc")
        _make_domain_skill(
            self.project_dir, "fintech", "kyc", "kyc desc"
        )
        result = list_skills.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        slugs = sorted(s["slug"] for s in result["skills"])
        self.assertEqual(slugs, ["alpha", "beta", "gamma", "kyc"])
        self.assertEqual(result["total"], 4)
        # Verify domain skill is tagged.
        kyc = next(s for s in result["skills"] if s["slug"] == "kyc")
        self.assertEqual(kyc["tier"], "domain")
        self.assertEqual(kyc["domain"], "fintech")

    def test_missing_skills_dir_returns_empty(self):
        # No skills tree at all.
        result = list_skills.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        self.assertEqual(result["skills"], [])
        self.assertEqual(result["total"], 0)

    def test_cache_refreshes_on_stale(self):
        _make_skill(self.project_dir, "core", "alpha", "first")
        # First call populates cache.
        result1 = list_skills.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        self.assertEqual(len(result1["skills"]), 1)
        # Add a second skill while cache is hot.
        _make_skill(self.project_dir, "core", "beta", "second")
        # Cache is fresh — stays as 1 (we do NOT bust here, just observe).
        result2 = list_skills.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        self.assertEqual(len(result2["skills"]), 1, "cache should still be hot")
        # Reset and verify fresh walk picks up new skill.
        list_skills._reset_cache()
        result3 = list_skills.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        self.assertEqual(len(result3["skills"]), 2)

    def test_missing_project_dir_returns_warning(self):
        result = list_skills.handle(params={}, context={})
        self.assertEqual(result["skills"], [])
        self.assertEqual(result["warning"], "project_dir_missing")


if __name__ == "__main__":
    unittest.main()
