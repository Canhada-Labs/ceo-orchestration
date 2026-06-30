"""Unit tests for handlers/get_skill.py — path-traversal + symlink defense."""

from __future__ import annotations

import os
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

from handlers import get_skill  # type: ignore[import-not-found]  # noqa: E402


def _seed_skill(project_dir: Path, tier: str, slug: str, body: str = "body") -> Path:
    skill_dir = project_dir / ".claude" / "skills" / tier / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        "---\ndescription: a skill\n---\n\n" + body, encoding="utf-8"
    )
    return md


class TestGetSkill(TestEnvContext):

    def test_happy_path_returns_content(self):
        _seed_skill(self.project_dir, "core", "my-skill", "actual body content")
        result = get_skill.handle(
            params={"tier": "core", "slug": "my-skill"},
            context={"project_dir": self.project_dir},
        )
        self.assertEqual(result["tier"], "core")
        self.assertEqual(result["slug"], "my-skill")
        self.assertIn("actual body content", result["content"])

    def test_skill_not_found_returns_error_sentinel(self):
        result = get_skill.handle(
            params={"tier": "core", "slug": "nonexistent"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "skill_not_found")

    def test_path_traversal_dot_dot_rejected(self):
        # The slug regex itself should reject `../`.
        result = get_skill.handle(
            params={"tier": "core", "slug": "../../etc"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "skill_not_found")

    def test_invalid_tier_rejected(self):
        result = get_skill.handle(
            params={"tier": "bogus", "slug": "anything"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "skill_not_found")

    def test_symlink_rejected(self):
        # Real file outside the skills tree; symlink it in place of SKILL.md.
        _seed_skill(self.project_dir, "core", "real", "real")
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / "linked"
        skill_dir.mkdir(parents=True, exist_ok=True)
        outside = self.project_dir / "outside_secret.md"
        outside.write_text("not a skill", encoding="utf-8")
        link = skill_dir / "SKILL.md"
        os.symlink(str(outside), str(link))
        result = get_skill.handle(
            params={"tier": "core", "slug": "linked"},
            context={"project_dir": self.project_dir},
        )
        # MUST refuse the symlink — even though it resolves to a real file.
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "skill_not_found")

    def test_domain_skill_requires_domain_param(self):
        # Missing domain on tier=domain — slug regex passes but build path
        # ends up at .../domains//skills/<slug>/SKILL.md (empty domain).
        result = get_skill.handle(
            params={"tier": "domain", "slug": "kyc"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "skill_not_found")

    def test_missing_project_dir_returns_internal_error(self):
        result = get_skill.handle(
            params={"tier": "core", "slug": "x"}, context={}
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["message"], "internal_error")


if __name__ == "__main__":
    unittest.main()
