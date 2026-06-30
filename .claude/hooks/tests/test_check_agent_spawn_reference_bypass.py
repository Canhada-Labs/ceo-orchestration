"""PLAN-020 Phase 2 — `_has_skill_reference` bypass-vector tests (ADR-051).

≥30 bypass vectors across 14 attack classes. Each vector represents a
specific attack pattern documented in ADR-051 §Threat model. The
expected behavior is that ALL vectors are blocked by `_validate_skill_reference`.

Tests skip until Phase 2 lands.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import check_agent_spawn  # noqa: E402

try:
    from _lib.testing import TestEnvContext  # noqa: E402
except ImportError:
    TestEnvContext = unittest.TestCase


HAS_PHASE_2 = hasattr(check_agent_spawn, "_validate_skill_reference")


@unittest.skipUnless(
    HAS_PHASE_2,
    "PLAN-020 Phase 2 not yet landed (kernel-blocked)",
)
class ReferenceBypassTest(TestEnvContext):
    """30+ bypass vectors across 14 attack classes."""

    def _make_legit_skill(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "legit"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(
            "---\nname: legit\ndescription: x\n---\n\n" + "x" * 700,
            encoding="utf-8",
        )
        return skill_path, hashlib.sha256(
            skill_path.read_bytes()
        ).hexdigest()

    def _validate(self, prompt: str):
        return check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )

    # ----- Attack class 1: path traversal -----

    def test_001_path_traversal_etc_passwd(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@../../../../etc/passwd sha256=" + "0" * 64
        )
        self.assertFalse(ok)

    def test_002_path_traversal_relative(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@../skills/core/x/SKILL.md sha256=" + "0" * 64
        )
        self.assertFalse(ok)

    def test_003_path_traversal_double_slash(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@.claude//../../etc/passwd sha256=" + "0" * 64
        )
        self.assertFalse(ok)

    # ----- Attack class 2: symlink escape -----

    def test_004_symlink_to_outside(self):
        skill_path, _ = self._make_legit_skill()
        symlink_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "linked"
        )
        symlink_dir.mkdir(parents=True, exist_ok=True)
        symlink_path = symlink_dir / "SKILL.md"
        try:
            symlink_path.symlink_to(skill_path)
        except OSError:
            self.skipTest("symlinks unsupported on this filesystem")
        h = hashlib.sha256(skill_path.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            "## SKILL REFERENCE\n@.claude/skills/core/linked/SKILL.md sha256=" + h
        )
        self.assertFalse(ok)

    # ----- Attack class 3: hash mismatch -----

    def test_005_hash_all_zeros(self):
        skill_path, _ = self._make_legit_skill()
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/legit/SKILL.md sha256={'0' * 64}"
        )
        self.assertFalse(ok)

    def test_006_hash_off_by_one_char(self):
        skill_path, h = self._make_legit_skill()
        bad_hash = "0" + h[1:]
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/legit/SKILL.md sha256={bad_hash}"
        )
        self.assertFalse(ok)

    def test_007_hash_uppercase_hex(self):
        # Regex requires lowercase hex
        skill_path, h = self._make_legit_skill()
        upper = h.upper()
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/legit/SKILL.md sha256={upper}"
        )
        self.assertFalse(ok)

    # ----- Attack class 4: file size DoS -----

    def test_008_oversize_file(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "huge"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(
            "---\nname: huge\n---\n" + "x" * (1_048_580),
            encoding="utf-8",
        )
        h = hashlib.sha256(skill_path.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/huge/SKILL.md sha256={h}"
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_TOO_LARGE
        )

    # ----- Attack class 5: undersize file (stub-only) -----

    def test_009_empty_skill_file(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "empty"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(
            "---\nname: empty\n---\n", encoding="utf-8"
        )
        h = hashlib.sha256(skill_path.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/empty/SKILL.md sha256={h}"
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_BYTE_FLOOR_UNDERFLOW,
        )

    def test_010_only_whitespace_skill(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "ws"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(
            "---\nname: ws\n---\n" + "\n" * 1000, encoding="utf-8"
        )
        h = hashlib.sha256(skill_path.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/ws/SKILL.md sha256={h}"
        )
        self.assertFalse(ok)

    # ----- Attack class 6: filename mismatch -----

    def test_011_referencing_README_md(self):
        skills_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "fake"
        )
        skills_dir.mkdir(parents=True, exist_ok=True)
        readme = skills_dir / "README.md"
        readme.write_text(
            "---\nname: x\n---\n" + "x" * 600, encoding="utf-8"
        )
        h = hashlib.sha256(readme.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/fake/README.md sha256={h}"
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_WRONG_FILENAME
        )

    def test_012_referencing_skill_md_lowercase(self):
        skills_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "lower"
        )
        skills_dir.mkdir(parents=True, exist_ok=True)
        f = skills_dir / "skill.md"
        f.write_text("---\nname: x\n---\n" + "x" * 600, encoding="utf-8")
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/lower/skill.md sha256={h}"
        )
        # On case-sensitive FS this should fail at filename check
        self.assertFalse(ok)

    # ----- Attack class 7: outside skills root -----

    def test_013_outside_skills_root_team_md(self):
        team = self.project_dir / ".claude" / "team.md"
        if team.exists():
            h = hashlib.sha256(team.read_bytes()).hexdigest()
        else:
            team.parent.mkdir(parents=True, exist_ok=True)
            team.write_text("---\nname: t\n---\n" + "x" * 600, encoding="utf-8")
            h = hashlib.sha256(team.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/team.md sha256={h}"
        )
        self.assertFalse(ok)

    def test_014_outside_skills_root_random_path(self):
        f = self.project_dir / "random.md"
        f.write_text("---\nname: r\n---\n" + "x" * 600, encoding="utf-8")
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@random.md sha256={h}"
        )
        self.assertFalse(ok)

    # ----- Attack class 8: missing frontmatter -----

    def test_015_no_frontmatter_at_all(self):
        skills_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "nofm"
        )
        skills_dir.mkdir(parents=True, exist_ok=True)
        f = skills_dir / "SKILL.md"
        f.write_text("body only no frontmatter " + "x" * 700, encoding="utf-8")
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/nofm/SKILL.md sha256={h}"
        )
        self.assertFalse(ok)

    def test_016_frontmatter_no_name_key(self):
        skills_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "noname"
        )
        skills_dir.mkdir(parents=True, exist_ok=True)
        f = skills_dir / "SKILL.md"
        f.write_text(
            "---\ndescription: no name\n---\n" + "x" * 700,
            encoding="utf-8",
        )
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/noname/SKILL.md sha256={h}"
        )
        self.assertFalse(ok)

    # ----- Attack class 9: malformed sentinel -----

    def test_017_no_sha256_keyword(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@.claude/skills/core/x/SKILL.md " + "0" * 64
        )
        self.assertFalse(ok)

    def test_018_short_hash(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@.claude/skills/core/x/SKILL.md sha256=" + "0" * 32
        )
        self.assertFalse(ok)

    def test_019_long_hash(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n@.claude/skills/core/x/SKILL.md sha256=" + "0" * 128
        )
        self.assertFalse(ok)

    def test_020_at_symbol_missing(self):
        ok, _, _ = self._validate(
            "## SKILL REFERENCE\n.claude/skills/core/x/SKILL.md sha256=" + "0" * 64
        )
        self.assertFalse(ok)

    def test_021_no_header_only_body(self):
        ok, _, _ = self._validate(
            "@.claude/skills/core/x/SKILL.md sha256=" + "0" * 64
        )
        self.assertFalse(ok)

    # ----- Attack class 10: header inside fence/comment -----

    def test_022_header_inside_fence_ignored(self):
        skill_path, h = self._make_legit_skill()
        # Header inside code fence — should NOT count
        prompt = (
            "```markdown\n## SKILL REFERENCE\n"
            f"@.claude/skills/core/legit/SKILL.md sha256={h}\n```"
        )
        ok, _, _ = self._validate(prompt)
        self.assertFalse(ok)

    def test_023_header_inside_html_comment_ignored(self):
        skill_path, h = self._make_legit_skill()
        prompt = (
            f"<!--## SKILL REFERENCE\n@.claude/skills/core/legit/SKILL.md "
            f"sha256={h}-->"
        )
        ok, _, _ = self._validate(prompt)
        self.assertFalse(ok)

    # ----- Attack class 11: nonexistent path -----

    def test_024_nonexistent_skill_dir(self):
        ok, reason, _ = self._validate(
            f"## SKILL REFERENCE\n@.claude/skills/core/nonexistent/SKILL.md sha256={'0' * 64}"
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_MISSING
        )

    def test_025_relative_path_outside_repo(self):
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@/etc/passwd sha256={'0' * 64}"
        )
        self.assertFalse(ok)

    # ----- Attack class 12: case-sensitivity tricks -----

    def test_026_skill_reference_lowercase_header(self):
        # Header must be exact case
        ok, _, _ = self._validate(
            f"## skill reference\n@.claude/skills/core/x/SKILL.md sha256={'0' * 64}"
        )
        self.assertFalse(ok)

    # ----- Attack class 13: whitespace in path -----

    def test_027_path_with_spaces_rejected(self):
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@path with spaces/SKILL.md sha256={'0' * 64}"
        )
        self.assertFalse(ok)

    def test_028_path_with_tab(self):
        ok, _, _ = self._validate(
            f"## SKILL REFERENCE\n@path\twith\ttab sha256={'0' * 64}"
        )
        self.assertFalse(ok)

    # ----- Attack class 14: misleading content -----

    def test_029_inline_skill_content_does_not_satisfy_reference(self):
        # Reference path is selected if SKILL REFERENCE is present;
        # presence of inline SKILL CONTENT is NOT a fallback.
        skill_path, h = self._make_legit_skill()
        prompt = (
            "## SKILL CONTENT\n" + "x" * 400 +
            f"\n## SKILL REFERENCE\n@bad/path sha256={'0' * 64}"
        )
        ok, _, _ = self._validate(prompt)
        self.assertFalse(ok)

    def test_030_two_references_first_wins(self):
        # Two reference body lines — first match used; if first is bad, fails
        skill_path, h = self._make_legit_skill()
        prompt = (
            f"## SKILL REFERENCE\n@bad/path sha256={'0' * 64}\n"
            f"@.claude/skills/core/legit/SKILL.md sha256={h}\n"
        )
        ok, _, _ = self._validate(prompt)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
