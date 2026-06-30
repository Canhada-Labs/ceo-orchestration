"""PLAN-020 Phase 2 — `_has_skill_reference` 10 sub-check tests (ADR-051).

≥14 negative-path tests covering each of the 11 sub-checks plus the
`_has_skill_reference` wrapper API.

These tests skip if the kernel-protected `check_agent_spawn.py` has not
yet been patched with the Phase 2 functions (Owner applies via
CEO_KERNEL_OVERRIDE pattern; until then, tests skip).
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
    TestEnvContext = unittest.TestCase  # fallback


HAS_PHASE_2 = hasattr(check_agent_spawn, "_validate_skill_reference")


@unittest.skipUnless(
    HAS_PHASE_2,
    "PLAN-020 Phase 2 _validate_skill_reference not yet landed (kernel-blocked; needs CEO_KERNEL_OVERRIDE)",
)
class ValidateSkillReferenceTest(TestEnvContext):
    """10 sub-check coverage from ADR-051 §Synchronous validation."""

    def _make_skill(
        self,
        slug: str = "test-skill",
        body: str = (
            "This is a test skill body. It contains markdown content "
            "describing rules and patterns. The body is long enough to "
            "satisfy the five hundred and twelve byte non-whitespace "
            "floor required by the skill-reference validator in the "
            "framework's governance hook. Lines are intentionally "
            "short and use simple English words to avoid triggering "
            "any secret-pattern detection in the redaction scan "
            "sub-check. "
            "Rule 1: every named spawn requires a persona and a skill "
            "loaded. Rule 2: file assignments prevent collisions "
            "between parallel agents. Rule 3: errors must be explicit "
            "and propagate to the caller. Rule 4: tests cover both "
            "happy path and edge cases systematically. Rule 5: skills "
            "stay under the dot claude slash skills directory. "
            "This filler is added to ensure the non-whitespace byte "
            "count exceeds the minimum floor threshold. Additional "
            "sentences reinforce that the body is realistic markdown "
            "content a sub-agent would read and use to reason."
        ),
        with_frontmatter: bool = True,
    ) -> Path:
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        if with_frontmatter:
            content = f"---\nname: {slug}\ndescription: test skill\n---\n\n{body}"
        else:
            content = body
        skill_path.write_text(content, encoding="utf-8")
        return skill_path

    def _hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _make_prompt(self, ref_path: str, ref_hash: str) -> str:
        return (
            "## AGENT PROFILE\nName: test\n\n"
            f"## SKILL REFERENCE\n\n@{ref_path} sha256={ref_hash}\n"
        )

    def test_01_valid_reference_passes_all_checks(self):
        skill_path = self._make_skill()
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertTrue(ok, msg=f"unexpected fail: {reason}")

    def test_02_missing_header_returns_reference_missing(self):
        skill_path = self._make_skill()
        prompt = "## AGENT PROFILE\n\n(no SKILL REFERENCE here)\n"
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(reason, check_agent_spawn.REASON_REFERENCE_MISSING)

    def test_03_header_without_body_line_returns_reference_missing(self):
        prompt = "## AGENT PROFILE\n\n## SKILL REFERENCE\n\n(no body line)\n"
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(reason, check_agent_spawn.REASON_REFERENCE_MISSING)

    def test_04_path_outside_skills_root_returns_outside_skills_root(self):
        # Path resolves but lives outside .claude/skills/
        outside = self.project_dir / "scratch.md"
        outside.write_text("---\nname: x\n---\n" + "x" * 600, encoding="utf-8")
        h = self._hash(outside)
        prompt = self._make_prompt("scratch.md", h)
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_OUTSIDE_SKILLS_ROOT,
        )

    def test_05_wrong_filename_returns_wrong_filename(self):
        # File under skills/ but not named SKILL.md
        skills_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "test-skill"
        )
        skills_dir.mkdir(parents=True, exist_ok=True)
        wrong = skills_dir / "README.md"
        wrong.write_text("---\nname: x\n---\n" + "x" * 600, encoding="utf-8")
        h = self._hash(wrong)
        prompt = self._make_prompt(
            str(wrong.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_WRONG_FILENAME
        )

    def test_06_size_too_large_returns_too_large(self):
        # Exceeds 1 MiB cap
        huge_body = "x" * (1_048_577)
        skill_path = self._make_skill(body=huge_body)
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_TOO_LARGE
        )

    def test_07_byte_floor_underflow_returns_byte_floor_underflow(self):
        # Below 512-byte non-ws floor (use empty body but with frontmatter)
        skill_path = self._make_skill(body="short", with_frontmatter=True)
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_BYTE_FLOOR_UNDERFLOW,
        )

    def test_08_missing_frontmatter_returns_missing_frontmatter(self):
        skill_path = self._make_skill(with_frontmatter=False)
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_MISSING_FRONTMATTER,
        )

    def test_09_frontmatter_without_name_key_returns_missing_frontmatter(self):
        skill_dir = (
            self.project_dir / ".claude" / "skills" / "core" / "no-name"
        )
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(
            "---\ndescription: no name key\n---\n" + "x" * 600,
            encoding="utf-8",
        )
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_MISSING_FRONTMATTER,
        )

    def test_10_hash_mismatch_returns_hash_mismatch(self):
        skill_path = self._make_skill()
        wrong_hash = "0" * 64
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), wrong_hash
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_HASH_MISMATCH
        )

    def test_11_redaction_hit_returns_redaction_hit(self):
        # Insert an AWS access key ID — canonical test vector from AWS docs
        # (AKIA + 16 uppercase alphanumerics). Matches redact.py pattern
        # `\bAKIA[0-9A-Z]{16}\b` → replaces with `[AWS_KEY]` token.
        # Body must exceed 512 non-whitespace bytes to reach sub-check 11.
        secret_body = (
            "AKIAIOSFODNN7EXAMPLE is an AWS access key and must trigger "
            "the redaction scan subcheck in the skill reference validator. "
            "The rest of this body is filler text long enough to satisfy "
            "the non-whitespace byte floor requirement which sits at five "
            "hundred twelve bytes. Real skill content would describe rules "
            "and patterns in detail. This block repeats several clarifying "
            "sentences to push the non-whitespace count comfortably above "
            "the floor threshold. The AWS key above triggers the regex "
            "AKIA followed by sixteen uppercase alphanumerics which is the "
            "canonical access-key shape. When redact_secrets scans this "
            "body it replaces AKIAIOSFODNN7EXAMPLE with the bracketed "
            "AWS_KEY token and that token appearance is the signal we use "
            "for the redaction-hit decision. Additional filler text is "
            "included here to ensure the body survives both the size cap "
            "check and the byte-floor check before reaching sub-check 11."
        )
        skill_path = self._make_skill(body=secret_body)
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason,
            check_agent_spawn.REASON_REFERENCE_REDACTION_HIT,
        )

    def test_12_path_does_not_exist_returns_reference_missing(self):
        prompt = self._make_prompt(
            ".claude/skills/core/nonexistent/SKILL.md",
            "0" * 64,
        )
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(
            reason, check_agent_spawn.REASON_REFERENCE_MISSING
        )

    def test_13_has_skill_reference_wrapper_returns_bool(self):
        skill_path = self._make_skill()
        h = self._hash(skill_path)
        prompt = self._make_prompt(
            str(skill_path.relative_to(self.project_dir)), h
        )
        result = check_agent_spawn._has_skill_reference(
            prompt, repo_root=self.project_dir
        )
        self.assertIsInstance(result, bool)
        self.assertTrue(result)

    def test_14_empty_prompt_returns_reference_missing(self):
        ok, reason, _ = check_agent_spawn._validate_skill_reference(
            "", repo_root=self.project_dir
        )
        self.assertFalse(ok)
        self.assertEqual(reason, check_agent_spawn.REASON_REFERENCE_MISSING)


@unittest.skipUnless(
    HAS_PHASE_2,
    "PLAN-020 Phase 2 not landed",
)
class FrontmatterParserTest(unittest.TestCase):
    """`_has_valid_frontmatter_with_name` stdlib YAML check."""

    def test_basic_valid_frontmatter(self):
        text = "---\nname: test-skill\ndescription: x\n---\n\nbody"
        self.assertTrue(
            check_agent_spawn._has_valid_frontmatter_with_name(text)
        )

    def test_no_frontmatter_returns_false(self):
        self.assertFalse(
            check_agent_spawn._has_valid_frontmatter_with_name("body only")
        )

    def test_no_closing_fence_returns_false(self):
        text = "---\nname: x\ndescription: y\n\nbody (no closing ---)"
        self.assertFalse(
            check_agent_spawn._has_valid_frontmatter_with_name(text)
        )

    def test_missing_name_key_returns_false(self):
        text = "---\ndescription: only desc\n---\nbody"
        self.assertFalse(
            check_agent_spawn._has_valid_frontmatter_with_name(text)
        )

    def test_uppercase_name_key_returns_false(self):
        text = "---\nName: x\n---\nbody"
        self.assertFalse(
            check_agent_spawn._has_valid_frontmatter_with_name(text)
        )


if __name__ == "__main__":
    unittest.main()
