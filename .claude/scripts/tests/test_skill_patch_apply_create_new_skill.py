"""PLAN-047 P03 follow-up: create-new-skill branch coverage.

Tests the `proposal_type: create-new-skill` path of
`.claude/scripts/skill-patch-apply.py`:

- markdown-fence extractor (happy + missing + multiple + oversized)
- proposal_target parser (accept 3 tiers; reject traversal, absolute,
  malformed slugs, backslashes)
- target resolver (rejects path escape from skills root)
- shadow-apply materializes parent dir + writes shadow atomically
- promote --force-recover skips 7-day soak (§D1 pre-authorization)
- reject: target already exists
- reject: invalid GPG signature
- reject: unknown slug shape

Requires `gpg` on PATH (test skips otherwise).
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Optional

_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_APPLY = _REPO_ROOT / ".claude" / "scripts" / "skill-patch-apply.py"
_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_spec = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture", _FIXTURE_DIR / "gpg-keyring-fixture.py",
)
_gpg_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_gpg_mod)


def _load_apply_module():
    """Import skill-patch-apply.py as a module for helper-function tests."""
    spec = importlib.util.spec_from_file_location("skill_patch_apply", _APPLY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _today_iso() -> str:
    """Return current UTC date as ISO-8601 (midnight) for proposed_at.

    audit-v2 hot-fix #6 (2026-04-27): the previous hardcoded
    "2026-04-21T00:00:00Z" became older than 7 days on 2026-04-28
    and silently inverted the soak-window semantics in
    test_promote_force_recover_skips_soak_and_writes_real (which
    expects rc=4 from a <7d-old proposal). Compute "today" so the
    test stays correct as time advances.
    """
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT00:00:00Z")


def _proposal_body(
    proposal_id: str,
    proposal_target: str,
    skill_body: str,
    *,
    proposed_at: Optional[str] = None,
) -> str:
    if proposed_at is None:
        proposed_at = _today_iso()
    """Build a create-new-skill SP-NNN proposal body.

    Does NOT use textwrap.dedent: when the interpolated skill_body
    itself starts at column 0 (e.g. `---\\nname: ...`), dedent's
    common-prefix becomes 0 and the surrounding indent survives,
    corrupting the frontmatter. Build the string with explicit
    column-0 formatting instead.
    """
    return (
        "---\n"
        f"id: {proposal_id}\n"
        "kind: skill-patch\n"
        f"proposal_target: {proposal_target}\n"
        "proposal_type: create-new-skill\n"
        f"proposed_at: {proposed_at}\n"
        "status: draft\n"
        "---\n"
        "\n"
        f"# {proposal_id} — NEW skill fixture\n"
        "\n"
        "## Target file content\n"
        "\n"
        "```markdown\n"
        f"{skill_body}\n"
        "```\n"
    )


class ParseProposalTargetTest(TestEnvContext):
    """Pure helper tests for `_parse_proposal_target`."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_apply_module()

    def test_accepts_core_tier(self) -> None:
        got = self.mod._parse_proposal_target(
            ".claude/skills/core/terse-mode/SKILL.md"
        )
        self.assertEqual(got, ("core", "terse-mode"))

    def test_accepts_frontend_tier(self) -> None:
        got = self.mod._parse_proposal_target(
            ".claude/skills/frontend/my-widget/SKILL.md"
        )
        self.assertEqual(got, ("frontend", "my-widget"))

    def test_accepts_domain_tier(self) -> None:
        got = self.mod._parse_proposal_target(
            ".claude/skills/domains/fintech/skills/exchange-foo/SKILL.md"
        )
        self.assertEqual(got, ("domains/fintech/skills", "exchange-foo"))

    def test_rejects_traversal(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/core/../../SKILL.md"
        ))
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/core/../terse-mode/SKILL.md"
        ))

    def test_rejects_absolute(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            "/etc/passwd"
        ))
        self.assertIsNone(self.mod._parse_proposal_target(
            "/Users/x/.claude/skills/core/x/SKILL.md"
        ))

    def test_rejects_windows_sep(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude\\skills\\core\\x\\SKILL.md"
        ))

    def test_rejects_empty(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(""))

    def test_rejects_wrong_root(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            "src/skills/core/x/SKILL.md"
        ))

    def test_rejects_wrong_tier(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/magical/x/SKILL.md"
        ))

    def test_rejects_uppercase_slug(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/core/TerseMode/SKILL.md"
        ))

    def test_rejects_underscore_slug(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/core/terse_mode/SKILL.md"
        ))

    def test_rejects_non_skill_md(self) -> None:
        self.assertIsNone(self.mod._parse_proposal_target(
            ".claude/skills/core/x/README.md"
        ))


class ExtractMarkdownBlockTest(TestEnvContext):
    """Helper tests for the ```markdown fence extractor."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_apply_module()

    def test_happy_path(self) -> None:
        text = "prelude\n```markdown\n# hi\n\nbody\n```\ntrailer"
        self.assertEqual(self.mod._extract_markdown_block(text), "# hi\n\nbody")

    def test_missing_fence_returns_none(self) -> None:
        self.assertIsNone(self.mod._extract_markdown_block("no fence here"))
        self.assertIsNone(self.mod._extract_markdown_block(
            "```diff\n+foo\n```"
        ))

    def test_multiple_fences_returns_none(self) -> None:
        text = "```markdown\nA\n```\n\n```markdown\nB\n```"
        self.assertIsNone(self.mod._extract_markdown_block(text))

    def test_oversized_body_returns_none(self) -> None:
        big = "x" * (self.mod._CREATE_NEW_SKILL_MAX_BYTES + 1)
        text = f"```markdown\n{big}\n```"
        self.assertIsNone(self.mod._extract_markdown_block(text))

    def test_boundary_body_accepted(self) -> None:
        cap = self.mod._CREATE_NEW_SKILL_MAX_BYTES
        body = "x" * (cap - 1)  # -1 to leave room for newline framing
        text = f"```markdown\n{body}\n```"
        self.assertEqual(self.mod._extract_markdown_block(text), body)


class CreateNewSkillIntegrationTest(TestEnvContext):
    """End-to-end tests via subprocess against a test repo."""

    def setUp(self) -> None:
        super().setUp()
        try:
            self._keyring = _gpg_mod.GpgKeyringFixture().__enter__()
        except _gpg_mod.GpgUnavailable:
            self.skipTest("gpg binary not available on PATH")
        self.addCleanup(self._keyring.__exit__, None, None, None)
        # Restore GNUPGHOME on teardown — keyring __exit__ rmtree's the dir but
        # leaves the env var set; TestEnvContext doesn't snapshot GNUPGHOME, so
        # it leaks at a deleted dir into later sequential gpg subprocesses.
        self.addCleanup(
            lambda _g=os.environ.get("GNUPGHOME"):
            os.environ.__setitem__("GNUPGHOME", _g) if _g is not None
            else os.environ.pop("GNUPGHOME", None)
        )
        os.environ["GNUPGHOME"] = str(self._keyring.gnupg_home)

        hooks_lib = self.project_dir / ".claude" / "hooks" / "_lib"
        hooks_lib.mkdir(parents=True, exist_ok=True)
        src = _REPO_ROOT / ".claude" / "hooks" / "_lib"
        for fname in ("__init__.py", "filelock.py", "gpg_verify.py"):
            (hooks_lib / fname).write_text(
                (src / fname).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (self.project_dir / ".claude" / "hooks" / "__init__.py").write_text(
            "", encoding="utf-8"
        )
        signers_file = self.project_dir / ".claude" / "skill-patch-signers.txt"
        signers_file.write_text(
            f"# test fixture\n{self._keyring.fingerprint}\n",
            encoding="utf-8",
        )

        self.proposals_dir = self.project_dir / ".claude" / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)

    def _write_and_sign_proposal(
        self,
        proposal_id: str,
        proposal_target: str,
        body_text: str,
        *,
        proposed_at: Optional[str] = None,
    ) -> Path:
        if proposed_at is None:
            proposed_at = _today_iso()
        pp = self.proposals_dir / f"{proposal_id}-fixture.md"
        pp.write_text(
            _proposal_body(
                proposal_id, proposal_target, body_text,
                proposed_at=proposed_at,
            ),
            encoding="utf-8",
        )
        self._keyring.sign(pp)
        return pp

    def _cmd(self, proposal_id: str, *extra) -> list:
        asc = self.proposals_dir / f"{proposal_id}-fixture.md.asc"
        return [
            sys.executable, str(_APPLY),
            "--proposal", proposal_id,
            "--signature", str(asc),
            "--confirm", f"I have read {proposal_id}",
            *extra,
        ]

    def _env(self) -> dict:
        e = os.environ.copy()
        e["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        e["GNUPGHOME"] = str(self._keyring.gnupg_home)
        return e

    def test_shadow_apply_materializes_dir_and_shadow(self) -> None:
        target = ".claude/skills/core/newborn-skill/SKILL.md"
        body = "---\nname: Newborn\ndescription: test\n---\n\n# Body"
        self._write_and_sign_proposal("SP-900", target, body)

        p = subprocess.run(
            self._cmd("SP-900"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p.returncode, 0, msg=p.stderr)
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / "newborn-skill"
        self.assertTrue(skill_dir.is_dir())
        shadow = skill_dir / "SKILL.md.shadow.md"
        self.assertTrue(shadow.is_file())
        content = shadow.read_text(encoding="utf-8")
        self.assertIn("# Body", content)
        self.assertTrue(content.endswith("\n"))
        # Real SKILL.md NOT yet written (shadow-only).
        self.assertFalse((skill_dir / "SKILL.md").exists())
        # Frontmatter updated.
        prop = (self.proposals_dir / "SP-900-fixture.md").read_text(encoding="utf-8")
        self.assertIn("status: shadow", prop)

    def test_promote_force_recover_skips_soak_and_writes_real(self) -> None:
        target = ".claude/skills/core/quickborn/SKILL.md"
        body = "---\nname: Quickborn\ndescription: t\n---\n\nBody."
        # proposed_at = today → without --force-recover promote refuses.
        self._write_and_sign_proposal("SP-901", target, body)

        # Shadow first.
        p_shadow = subprocess.run(
            self._cmd("SP-901"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p_shadow.returncode, 0, msg=p_shadow.stderr)

        # Without --force-recover: promote refuses (<7d old).
        # Re-sign because shadow mutated frontmatter (applied_at/status).
        self._keyring.sign(self.proposals_dir / "SP-901-fixture.md")
        p_nosoak = subprocess.run(
            self._cmd("SP-901", "--promote"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p_nosoak.returncode, 4, msg=p_nosoak.stderr)

        # With --promote --force-recover: soak skipped.
        p_prom = subprocess.run(
            self._cmd("SP-901", "--promote", "--force-recover"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p_prom.returncode, 0, msg=p_prom.stderr)
        real = self.project_dir / ".claude" / "skills" / "core" / "quickborn" / "SKILL.md"
        self.assertTrue(real.is_file())
        self.assertIn("Body.", real.read_text(encoding="utf-8"))
        prop = (self.proposals_dir / "SP-901-fixture.md").read_text(encoding="utf-8")
        self.assertIn("status: promoted", prop)

    def test_reject_target_already_exists(self) -> None:
        target = ".claude/skills/core/already/SKILL.md"
        real = self.project_dir / ".claude" / "skills" / "core" / "already" / "SKILL.md"
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text("existing\n", encoding="utf-8")

        body = "---\nname: Already\n---\nNew body"
        self._write_and_sign_proposal("SP-902", target, body)
        p = subprocess.run(
            self._cmd("SP-902"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("already exists", p.stderr)

    def test_reject_bad_target_shape(self) -> None:
        # Absolute path — parser rejects.
        target = "/etc/passwd"
        body = "pwned"
        self._write_and_sign_proposal("SP-903", target, body)
        p = subprocess.run(
            self._cmd("SP-903"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p.returncode, 5)
        self.assertIn("unsupported shape", p.stderr)

    def test_reject_traversal_in_target(self) -> None:
        target = ".claude/skills/core/../../etc/SKILL.md"
        body = "nope"
        self._write_and_sign_proposal("SP-904", target, body)
        p = subprocess.run(
            self._cmd("SP-904"),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p.returncode, 5)

    def test_reject_missing_markdown_fence(self) -> None:
        # Hand-craft proposal without the ```markdown fence.
        pid = "SP-905"
        pp = self.proposals_dir / f"{pid}-fixture.md"
        pp.write_text(textwrap.dedent(f"""\
            ---
            id: {pid}
            kind: skill-patch
            proposal_target: .claude/skills/core/fenceless/SKILL.md
            proposal_type: create-new-skill
            proposed_at: 2026-04-21T00:00:00Z
            status: draft
            ---

            # No fence here
            """), encoding="utf-8")
        self._keyring.sign(pp)
        p = subprocess.run(
            self._cmd(pid),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p.returncode, 5)
        self.assertIn("markdown fence", p.stderr)

    def test_default_flow_still_works_for_diff_proposals(self) -> None:
        """Regression: existing `skill-patch` proposals unaffected."""
        # Set up an existing skill + diff-based SP-NNN.
        slug = "preexist"
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "# Pre\n\nBase.\n", encoding="utf-8"
        )
        pid = "SP-906"
        pp = self.proposals_dir / f"{pid}-fixture.md"
        pp.write_text(textwrap.dedent(f"""\
            ---
            id: {pid}
            skill_slug: {slug}
            archetype: test
            proposed_at: 2026-04-14T00:00:00Z
            source_lessons:
              - l-test
            scan_injection_pass: true
            diff_size_added: 1
            diff_size_removed: 0
            sha256_of_diff: 0000000000000000000000000000000000000000000000000000000000000000
            claims_declared: false
            status: draft
            approved_by: null
            applied_at: null
            promoted_at: null
            shadow_mode: true
            ---

            ```diff
            --- a/SKILL.md
            +++ b/SKILL.md
            @@ -3,0 +4,1 @@
            +- regression-guard lesson
            ```
            """), encoding="utf-8")
        self._keyring.sign(pp)
        p = subprocess.run(
            self._cmd(pid),
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        self.assertEqual(p.returncode, 0, msg=p.stderr)
        shadow = skill_dir / "SKILL.md.shadow.md"
        self.assertTrue(shadow.is_file())
        self.assertIn("regression-guard lesson",
                      shadow.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
