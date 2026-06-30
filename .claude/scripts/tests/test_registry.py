"""Unit tests for registry.py — skill + archetype manifest parser."""

from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import registry  # noqa: E402


class TestFrontmatterParser(unittest.TestCase):
    def test_single_line_values(self):
        text = "---\nname: foo\nowner: bar\n---\nbody"
        fm = registry._parse_frontmatter(text)
        self.assertEqual(fm, {"name": "foo", "owner": "bar"})

    def test_folded_scalar_joined_with_space(self):
        text = textwrap.dedent(
            """\
            ---
            name: skill-name
            description: first line
              continues here
              and here
            owner: CEO
            ---
            """
        )
        fm = registry._parse_frontmatter(text)
        self.assertEqual(fm["description"], "first line continues here and here")
        self.assertEqual(fm["owner"], "CEO")

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(registry._parse_frontmatter("no fm here"), {})

    def test_empty_file_returns_empty(self):
        self.assertEqual(registry._parse_frontmatter(""), {})

    def test_handles_colons_in_values(self):
        text = "---\nname: skill: awesome\n---\n"
        fm = registry._parse_frontmatter(text)
        self.assertEqual(fm["name"], "skill: awesome")


class TestSkillLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="reg-test-"))
        self.skills_dir = self.tmp / ".claude" / "skills"
        self.skills_dir.mkdir(parents=True)

    def _write_skill(self, rel_path: str, frontmatter: str) -> None:
        p = self.skills_dir / rel_path / "SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\n{frontmatter}\n---\nbody\n")

    def test_core_skill_resolved(self):
        self._write_skill("core/security-and-auth", "name: security-and-auth\nowner: sec")
        skills = registry.load_skills(self.tmp)
        self.assertIn("security-and-auth", skills)
        s = skills["security-and-auth"]
        self.assertEqual(s.tier, "core")
        self.assertEqual(s.owner, "sec")

    def test_frontend_skill_resolved(self):
        self._write_skill("frontend/design-system-and-components", "name: Design System\nowner: ui")
        skills = registry.load_skills(self.tmp)
        # Directory name is the stable ID
        self.assertIn("design-system-and-components", skills)
        self.assertEqual(skills["design-system-and-components"].name, "Design System")
        self.assertEqual(skills["design-system-and-components"].tier, "frontend")

    def test_domain_skill_resolved_with_tier_prefix(self):
        self._write_skill("domains/fintech/skills/trading-execution", "name: trading-execution")
        skills = registry.load_skills(self.tmp)
        self.assertIn("trading-execution", skills)
        self.assertEqual(skills["trading-execution"].tier, "domain:fintech")

    def test_name_collision_uses_tier_prefix(self):
        self._write_skill("core/shared", "name: shared")
        self._write_skill("domains/fintech/skills/shared", "name: shared")
        skills = registry.load_skills(self.tmp)
        # First wins with bare ID; second gets tier-prefixed
        ids = set(skills.keys())
        self.assertIn("shared", ids)
        self.assertTrue(any(i.startswith("domain:fintech:") for i in ids))


class TestArchetypeLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="reg-test-arch-"))
        (self.tmp / ".claude").mkdir()

    def test_backend_archetype_parsed(self):
        team_md = self.tmp / ".claude" / "team.md"
        team_md.write_text(textwrap.dedent(
            """\
            | Role | Focus | Primary skill |
            |------|-------|---------------|
            | **VP Engineering** | architecture | `architecture-decisions` |
            | **Security Engineer** | auth | `security-and-auth` |
            """
        ))
        archetypes = registry.load_archetypes(self.tmp)
        self.assertIn("vp-engineering", archetypes)
        self.assertEqual(archetypes["vp-engineering"].primary_skill, "architecture-decisions")
        self.assertEqual(archetypes["vp-engineering"].tier, "backend")
        self.assertIn("security-engineer", archetypes)

    def test_frontend_archetype_tier(self):
        (self.tmp / ".claude" / "frontend-team.md").write_text(
            "| **UI UX Lead** | ui | `design-system-and-components` |\n"
        )
        archetypes = registry.load_archetypes(self.tmp)
        self.assertEqual(archetypes["ui-ux-lead"].tier, "frontend")

    def test_header_row_ignored(self):
        (self.tmp / ".claude" / "team.md").write_text(
            "| **Role** | ... | `skill-id` |\n| **VP Eng** | ... | `architecture-decisions` |\n"
        )
        archetypes = registry.load_archetypes(self.tmp)
        # "Role" should not become an archetype
        self.assertNotIn("role", archetypes)

    def test_first_declaration_wins(self):
        (self.tmp / ".claude" / "team.md").write_text(
            "| **VP Eng** | a | `skill-a` |\n"
        )
        (self.tmp / ".claude" / "frontend-team.md").write_text(
            "| **VP Eng** | b | `skill-b` |\n"
        )
        archetypes = registry.load_archetypes(self.tmp)
        self.assertEqual(archetypes["vp-eng"].primary_skill, "skill-a")

    def test_primary_skill_is_first_backtick_not_secondary(self):
        """PLAN-113 W6 (F-11.14) regression: a row with BOTH a primary and a
        secondary backticked skill must capture the FIRST (primary), not the
        LAST (secondary). The old `\\|(.+?)\\|\\s*`(...)`` pattern greedily
        skipped to the last `|`-then-backtick and captured the secondary."""
        (self.tmp / ".claude" / "team.md").write_text(
            "| **VP Engineering** | `architecture-decisions` | `incremental-refactoring` |\n"
            "| **Security Engineer** | `security-and-auth` | `ai-llm-orchestration` |\n"
        )
        archetypes = registry.load_archetypes(self.tmp)
        self.assertEqual(
            archetypes["vp-engineering"].primary_skill, "architecture-decisions"
        )
        self.assertEqual(
            archetypes["security-engineer"].primary_skill, "security-and-auth"
        )

    def test_single_backtick_row_still_parses(self):
        """A row with only one backticked skill (primary, no secondary) keeps
        capturing that skill — the W6 fix must not regress single-skill rows."""
        (self.tmp / ".claude" / "team.md").write_text(
            "| **QA Architect** | `evidence-based-qa` | manual review |\n"
        )
        archetypes = registry.load_archetypes(self.tmp)
        self.assertEqual(
            archetypes["qa-architect"].primary_skill, "evidence-based-qa"
        )


class TestRegistryCrossValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="reg-test-xval-"))
        (self.tmp / ".claude" / "skills" / "core" / "known").mkdir(parents=True)
        (self.tmp / ".claude" / "skills" / "core" / "known" / "SKILL.md").write_text(
            "---\nname: known\n---\nbody"
        )

    def test_archetype_with_unknown_skill_errors(self):
        (self.tmp / ".claude" / "team.md").write_text(
            "| **VP Eng** | - | `does-not-exist` |\n"
        )
        reg = registry.load_registry(self.tmp)
        self.assertEqual(len(reg.errors), 1)
        self.assertIn("does-not-exist", reg.errors[0])

    def test_archetype_with_known_skill_passes(self):
        (self.tmp / ".claude" / "team.md").write_text(
            "| **VP Eng** | - | `known` |\n"
        )
        reg = registry.load_registry(self.tmp)
        self.assertEqual(reg.errors, [])


class TestRealRepository(unittest.TestCase):
    """Smoke test against the real ceo-orchestration repo."""

    def test_real_registry_loads_all_skills(self):
        repo = Path(__file__).resolve().parents[3]
        reg = registry.load_registry(repo)
        # Floor, not exact — squads may grow
        self.assertGreaterEqual(len(reg.skills), 35)
        self.assertGreaterEqual(len(reg.archetypes), 16)
        self.assertEqual(reg.errors, [], f"Real repo has errors: {reg.errors}")

    def test_real_registry_tier_distribution(self):
        repo = Path(__file__).resolve().parents[3]
        reg = registry.load_registry(repo)
        summary = reg.summary()
        # 35 core after PLAN-080 Phase 0a PII promotion + PLAN-081 Phase 2:
        # 31 baseline post Wave 1b + 3 PII skills (pii-data-flow,
        # consent-lifecycle, dpo-reporting) promoted from domains/lgpd-heavy-saas
        # to core (PLAN-080 / ADR-111) + 1 cross-llm-pair-review (PLAN-081
        # Phase 6-bis). Prior baseline: 21 post SP-019 terse-mode + 1
        # incident-management + 9 NEW Wave 1b core (minimal-change-discipline,
        # llm-routing-and-finops, mcp-server-authoring, codebase-onboarding,
        # git-workflow-discipline, technical-writing, code-intelligence-lsp,
        # evidence-based-qa, identity-and-trust-architecture).
        # S109 + S111: core skills 35 -> 37 (+2 during PLAN-085 ship).
        # PLAN-106 fix-up: 37 -> 38 (cookbook-advisor pre-existing drift surfaced by Phase B).
        # S147 (PLAN-110 spec-kit v1.39.0 commit e2c03be): 38 -> 41 (+3
        # spec-kit doctrine skills: coverage-audit, requirement-quality-checklist,
        # spec-clarify).
        # S170 (PLAN-115 superpowers borrow, commit a2986b8): 41 -> 42 (+1
        # core/receiving-review anti-sycophancy skill). This assertion was
        # missed in the S170 closeout and reddened Validate on e993cc1 — bumped
        # S171 ([[feedback-ci-green-claim-must-verify-gh-run]]).
        self.assertEqual(summary["skills_core"], 42)  # +receiving-review (PLAN-115 S170)
        self.assertEqual(summary["skills_frontend"], 8)
        # 12 fintech after PLAN-074 Wave 2 (S94): +3 (solidity-smart-contracts,
        # blockchain-security-audit, equity-research) on top of the 9 baseline.
        self.assertEqual(summary["skills_domain_fintech"], 12)


class TestCLI(unittest.TestCase):
    def test_summary_command(self):
        repo = Path(__file__).resolve().parents[3]
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = registry._cli(["--summary", "--repo-root", str(repo)])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertGreaterEqual(data["skills_total"], 35)

    def test_validate_command_passes(self):
        repo = Path(__file__).resolve().parents[3]
        rc = registry._cli(["--validate", "--repo-root", str(repo)])
        self.assertEqual(rc, 0)

    def test_get_unknown_skill_exits_1(self):
        repo = Path(__file__).resolve().parents[3]
        rc = registry._cli(["--get-skill", "nonexistent", "--repo-root", str(repo)])
        self.assertEqual(rc, 1)


class TestVetoFloorArchetypeParsing(unittest.TestCase):
    """F-11.14-slug-mismatch: _ARCHETYPE_ROW_RE must match annotation-text rows.

    VETO-floor archetypes in team.md have annotation text like
    '(PLAN-074 Wave 1c -- ...)' between the closing '**' and the first '|'.
    The old regex required bold-close then immediate pipe; the fix allows
    non-pipe text before the first pipe.
    """

    def test_veto_floor_archetypes_parsed(self):
        """Principal Incident Commander + others with annotation text are found."""
        archetypes = registry.load_archetypes(Path(__file__).resolve().parents[3])
        self.assertIn(
            "principal-incident-commander",
            archetypes,
            "Incident Commander missing — _ARCHETYPE_ROW_RE fails on annotation text",
        )
        self.assertIn("principal-identity-and-trust-architect", archetypes)
        self.assertIn("llm-finops-architect", archetypes)

    def test_veto_floor_primary_skills(self):
        """VETO-floor archetypes have correct primary skills."""
        archetypes = registry.load_archetypes(Path(__file__).resolve().parents[3])
        self.assertEqual(
            archetypes["principal-incident-commander"].primary_skill,
            "incident-management",
        )
        self.assertEqual(
            archetypes["llm-finops-architect"].primary_skill,
            "llm-routing-and-finops",
        )


if __name__ == "__main__":
    unittest.main()
