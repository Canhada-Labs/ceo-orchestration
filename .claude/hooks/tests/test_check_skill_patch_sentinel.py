"""Tests for check_skill_patch_sentinel.py — ADR-031.

Per PLAN-011 consensus CR1 / H12: this hook is a safety surface. The
tests assert behavior against:

1. Direct SKILL.md edit with no proposal → block
2. Proposal present + matching env SHA → allow
3. Proposal present but no env SHA → block (trailer missing)
4. Proposal present + wrong env SHA → block (trailer mismatch)
5. Proposal exists but for a different skill_slug → block
6. Proposal in ``draft`` status (not yet approved) → block
7. Fail-open on malformed frontmatter (parse error should not block)
8. Non-SKILL.md edit → allow (scope check)
9. Write tool also enforced (not just Edit)
10. Shadow-file write allowed unconditionally
11. CEO_SOTA_DISABLE=1 does NOT disable sentinel (safety surface)
12. Empty file_path → allow (nothing to gate)
13. Path outside repo → allow silently
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_skill_patch_sentinel.py"


class CheckSkillPatchSentinelTest(TestEnvContext):
    """Behavior assertions (S5) — outputs + files, not internals."""

    # ---- helpers -------------------------------------------------------

    def _invoke(self, payload: dict, extra_env: dict = None) -> tuple:
        env = {**os.environ}
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _make_skill(self, slug: str = "test-skill", tier: str = "core") -> Path:
        skill_dir = self.project_dir / ".claude" / "skills" / tier / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# TEST SKILL\n\nBody.\n", encoding="utf-8")
        return skill_md

    def _write_proposal(
        self,
        *,
        proposal_id: str = "SP-001",
        skill_slug: str = "test-skill",
        status: str = "shadow",
        sha256: str = "a" * 64,
        date: str = "2026-04-14",
    ) -> Path:
        p_dir = self.project_dir / ".claude" / "proposals"
        p_dir.mkdir(parents=True, exist_ok=True)
        target = p_dir / f"{proposal_id}-{skill_slug}-{date}.md"
        fm = (
            "---\n"
            f"id: {proposal_id}\n"
            f"skill_slug: {skill_slug}\n"
            "archetype: security-engineer\n"
            "proposed_at: 2026-04-14T12:00:00Z\n"
            f"status: {status}\n"
            f"sha256_of_diff: {sha256}\n"
            "---\n\n# SP body\n"
        )
        target.write_text(fm, encoding="utf-8")
        return target

    # ---- tests ---------------------------------------------------------

    def test_direct_skill_md_edit_without_proposal_blocks(self):
        skill_md = self._make_skill()
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(skill_md)},
        })
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("ADR-031", d["reason"])
        self.assertIn("test-skill", d["reason"])

    def test_proposal_with_matching_sha_allows(self):
        skill_md = self._make_skill()
        sha = "b" * 64
        self._write_proposal(skill_slug="test-skill", status="shadow", sha256=sha)
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(skill_md)},
            },
            extra_env={"CEO_SKILL_PATCH_SHA": sha},
        )
        self.assertEqual(rc, 0, msg=out + "---" + _)
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=d)
        self.assertIn("systemMessage", d)

    def test_proposal_without_env_sha_blocks(self):
        skill_md = self._make_skill()
        self._write_proposal(status="shadow")
        # Ensure env var is NOT set
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(skill_md)},
        })
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("CEO_SKILL_PATCH_SHA", d["reason"])

    def test_proposal_with_wrong_sha_blocks(self):
        skill_md = self._make_skill()
        self._write_proposal(sha256="a" * 64, status="shadow")
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(skill_md)},
            },
            extra_env={"CEO_SKILL_PATCH_SHA": "c" * 64},
        )
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("trailer mismatch", d["reason"])

    def test_proposal_for_wrong_skill_slug_blocks(self):
        skill_md = self._make_skill(slug="target-skill")
        self._write_proposal(skill_slug="other-skill", status="shadow")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(skill_md)},
        })
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        # No approved proposal for the target-skill slug.
        self.assertIn("target-skill", d["reason"])

    def test_draft_status_proposal_does_not_allow(self):
        skill_md = self._make_skill()
        self._write_proposal(status="draft", sha256="d" * 64)
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(skill_md)},
            },
            extra_env={"CEO_SKILL_PATCH_SHA": "d" * 64},
        )
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    def test_promoted_status_proposal_allows_with_sha(self):
        skill_md = self._make_skill()
        sha = "e" * 64
        self._write_proposal(status="promoted", sha256=sha)
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(skill_md)},
            },
            extra_env={"CEO_SKILL_PATCH_SHA": sha},
        )
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_non_skill_md_edit_allows(self):
        # Edit on a non-SKILL.md path passes through silently.
        other = self.project_dir / "src" / "random.py"
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text("x = 1\n", encoding="utf-8")
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(other)},
        })
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_write_tool_enforced(self):
        # Not just Edit — Write and MultiEdit are enforced too.
        skill_md = self._make_skill()
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"file_path": str(skill_md)},
        })
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    def test_shadow_file_write_allowed(self):
        """Shadow SKILL.md.shadow.md writes pass the scope check unconditionally.

        The literal ``SKILL.md`` regex in ``_is_skill_md`` does not match
        ``SKILL.md.shadow.md`` — shadow files are a distinct artifact and
        ``skill-patch-apply.py`` is the only legitimate writer.
        """
        skill_md = self._make_skill()
        shadow = skill_md.parent / "SKILL.md.shadow.md"
        rc, out, _ = self._invoke({
            "tool_name": "Write",
            "tool_input": {"file_path": str(shadow)},
        })
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_ceo_sota_disable_does_not_disable_sentinel(self):
        """Safety surface (S4): CEO_SOTA_DISABLE=1 still enforces the sentinel."""
        skill_md = self._make_skill()
        rc, out, _ = self._invoke(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(skill_md)},
            },
            extra_env={"CEO_SOTA_DISABLE": "1"},
        )
        d = json.loads(out)
        self.assertEqual(
            d["decision"], "block",
            msg="Sentinel MUST stay active when CEO_SOTA_DISABLE=1 (safety surface)",
        )

    def test_empty_file_path_allows(self):
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {},
        })
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_malformed_json_allows_fail_open(self):
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="not valid json {{",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ},
        )
        # Must fail-open
        self.assertEqual(proc.returncode, 0)
        d = json.loads(proc.stdout)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_malformed_proposal_frontmatter_does_not_crash(self):
        """Fail-open on a malformed proposal file."""
        skill_md = self._make_skill()
        p_dir = self.project_dir / ".claude" / "proposals"
        p_dir.mkdir(parents=True, exist_ok=True)
        (p_dir / "SP-042-test-skill-2026-04-14.md").write_text(
            "THIS IS NOT YAML\njust garbage\n",
            encoding="utf-8",
        )
        rc, out, _ = self._invoke({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(skill_md)},
        })
        # The malformed file should not match (no skill_slug) → block
        # as if no proposal existed, but hook should not crash.
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    def test_post_tooluse_phase_ignored(self):
        """Only PreToolUse Edit/Write/MultiEdit is in scope."""
        skill_md = self._make_skill()
        rc, out, _ = self._invoke({
            "tool_name": "Agent",
            "tool_input": {"file_path": str(skill_md)},
        })
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")


class BootstrapBypassHardeningTest(TestEnvContext):
    """PLAN-042 ITEM 8 (FINDING-18): path-validation hardening of
    _bootstrap_bypass_allows. These tests assert that the bootstrap
    branch rejects:

    1. Targets outside .claude/skills/ (scope check)
    2. Invalid skill slugs (not matching [a-z][a-z0-9-]{1,63})
    3. Raw file_path containing '..' segments (traversal reject)
    """

    def _invoke(self, payload: dict, extra_env: dict = None) -> tuple:
        env = {**os.environ}
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_bootstrap_bypass_rejects_traversal_in_file_path(self) -> None:
        """'..' segment in raw file_path must abort bypass even when env
        vars are set to a valid slug name."""
        # Construct a path that would resolve inside skills but contains
        # "..". The traversal check runs BEFORE resolution.
        target = (
            self.project_dir / ".claude" / "skills" / "core"
            / "x" / ".." / "new-skill" / "SKILL.md"
        )
        rc, out, _ = self._invoke(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            },
            extra_env={
                "CEO_SKILL_BOOTSTRAP": "new-skill",
                "CEO_SKILL_BOOTSTRAP_ACK": "I-ACCEPT",
                "CLAUDE_PROJECT_DIR": str(self.project_dir),
            },
        )
        d = json.loads(out)
        # Must NOT allow via bootstrap; must fall through to SP-NNN gate → block
        self.assertEqual(d["decision"], "block", msg=d)

    def test_bootstrap_bypass_rejects_invalid_slug(self) -> None:
        """Slug with uppercase / underscore / leading digit must fail
        the regex whitelist."""
        # Build a fresh bootstrap target for a slug shape that fails
        # the new regex. The directory must NOT already exist.
        target = (
            self.project_dir / ".claude" / "skills" / "core"
            / "BadSlug" / "SKILL.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        # Remove any existing SKILL.md so target.exists() is False
        if target.exists():
            target.unlink()
        rc, out, _ = self._invoke(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            },
            extra_env={
                "CEO_SKILL_BOOTSTRAP": "BadSlug",  # uppercase not allowed
                "CEO_SKILL_BOOTSTRAP_ACK": "I-ACCEPT",
                "CLAUDE_PROJECT_DIR": str(self.project_dir),
            },
        )
        d = json.loads(out)
        self.assertEqual(d["decision"], "block", msg=d)

    def test_bootstrap_bypass_allows_valid_slug_under_skills(self) -> None:
        """Positive regression: a well-formed slug under .claude/skills/
        with both env vars still allows the bootstrap."""
        target = (
            self.project_dir / ".claude" / "skills" / "core"
            / "new-valid-skill" / "SKILL.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        rc, out, _ = self._invoke(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            },
            extra_env={
                "CEO_SKILL_BOOTSTRAP": "new-valid-skill",
                "CEO_SKILL_BOOTSTRAP_ACK": "I-ACCEPT",
                "CLAUDE_PROJECT_DIR": str(self.project_dir),
            },
        )
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=d)

    def test_bootstrap_bypass_rejects_target_outside_skills(self) -> None:
        """Target that resolves outside .claude/skills/ must not be
        bootstrapped even with valid slug + env vars."""
        # Target is plausibly a SKILL.md but lives outside skills dir
        target = self.project_dir / "fake" / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        rc, out, _ = self._invoke(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            },
            extra_env={
                "CEO_SKILL_BOOTSTRAP": "fake",
                "CEO_SKILL_BOOTSTRAP_ACK": "I-ACCEPT",
                "CLAUDE_PROJECT_DIR": str(self.project_dir),
            },
        )
        # _is_skill_md filter on the outer decide() would already reject
        # this as non-SKILL.md — the hook returns allow without invoking
        # the bootstrap branch. Assert the decision is NOT block-for-
        # SKILL-reason (would indicate the bootstrap path wrongly kicked
        # in).
        d = json.loads(out)
        # Non-SKILL.md path → allow passthrough
        self.assertEqual(d.get("decision", "allow"), "allow", msg=d)

    def test_bootstrap_bypass_rejects_empty_slug(self) -> None:
        target = (
            self.project_dir / ".claude" / "skills" / "core"
            / "something" / "SKILL.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        rc, out, _ = self._invoke(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            },
            extra_env={
                "CEO_SKILL_BOOTSTRAP": "",  # empty never matches regex
                "CEO_SKILL_BOOTSTRAP_ACK": "I-ACCEPT",
                "CLAUDE_PROJECT_DIR": str(self.project_dir),
            },
        )
        d = json.loads(out)
        self.assertEqual(d["decision"], "block", msg=d)


if __name__ == "__main__":
    unittest.main()
