"""PLAN-124 WS-2 (ECC value-harvest) — adopter config-protection hook tests.

Covers the AC (plan §WS-2):

* block-any-edit of an EXISTING allowlisted linter/formatter config;
* ENOENT (first-time creation) → ALLOW;
* non-allowlisted / ambiguous shared files (pyproject.toml, package.json,
  setup.cfg) and governance configs (.claude/settings.json, pytest.ini) →
  ALLOW (not this hook's job — MF-L / debate K6);
* dangling-symlink target → BLOCK (treat as existing);
* truncation / no-usable-file-path on a write tool → fail-CLOSED block (bounded);
* raw tool input is NEVER echoed (only the basename + resolved path appear);
* escape hatches (env kill-switch + per-repo disable file) tested ON and OFF;
* advisory mode (user ceremony) never blocks — allow + systemMessage steer.

All tests isolate env/HOME/CLAUDE_PROJECT_DIR via ``TestEnvContext`` so no real
config or audit state is touched.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import check_config_protection as ccp  # noqa: E402
from _lib import contract as _contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _event(
    tool_name: str,
    *,
    file_path: Optional[str] = None,
    new_string: str = "",
) -> _contract.NormalizedEvent:
    """Build a minimal NormalizedEvent for a write tool."""
    tool_input: dict = {}
    if file_path is not None:
        tool_input["file_path"] = file_path
    if new_string:
        tool_input["new_string"] = new_string
    return _contract.NormalizedEvent(
        session_id="sess-test",
        phase="PreToolUse",
        tool_name=tool_name,
        tool_input=tool_input,
        file_path=file_path or "",
        new_string=new_string,
    )


class _ConfigBase(TestEnvContext):
    """Builds an isolated adopter repo under the sandbox project dir."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = self.project_dir

    def _env(
        self,
        *,
        kill: bool = False,
        advisory: bool = False,
        disable_file: bool = False,
    ) -> dict:
        env = {"CLAUDE_PROJECT_DIR": str(self.repo)}
        if kill:
            env[ccp.KILL_SWITCH_ENV] = "0"
        if advisory:
            env[ccp.ADVISORY_ENV] = "1"
        if disable_file:
            df = self.repo / ccp.DISABLE_FILE
            df.parent.mkdir(parents=True, exist_ok=True)
            df.write_text("opt out\n", encoding="utf-8")
        return env

    def _touch(self, rel: str) -> Path:
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}\n", encoding="utf-8")
        return p


# ---------------------------------------------------------------------------
# 1. Block-any-edit of an EXISTING allowlisted config.
# ---------------------------------------------------------------------------


class TestBlockExisting(_ConfigBase):
    def test_existing_eslintrc_json_blocked(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow, "edit of existing .eslintrc.json must be BLOCKED")
        self.assertIn(".eslintrc.json", d.reason or "")
        self.assertIn("fix the code, not the config", (d.reason or "").lower())

    def test_existing_prettierrc_blocked(self):
        self._touch(".prettierrc")
        ev = _event("Write", file_path=str(self.repo / ".prettierrc"))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)

    def test_existing_ruff_toml_blocked(self):
        self._touch("ruff.toml")
        ev = _event("Edit", file_path=str(self.repo / "ruff.toml"))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)

    def test_existing_biome_jsonc_blocked(self):
        self._touch("biome.jsonc")
        ev = _event("MultiEdit", file_path=str(self.repo / "biome.jsonc"))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)

    def test_eslint_flat_config_mjs_blocked(self):
        self._touch("eslint.config.mjs")
        ev = _event("Edit", file_path=str(self.repo / "eslint.config.mjs"))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)

    def test_relative_path_resolves_against_project_dir(self):
        # A relative file_path must resolve under CLAUDE_PROJECT_DIR and still
        # match the existing on-disk config.
        self._touch(".flake8")
        ev = _event("Edit", file_path=".flake8")
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow, "relative path must resolve + block")


# ---------------------------------------------------------------------------
# 2. ENOENT (first-time creation) → ALLOW.
# ---------------------------------------------------------------------------


class TestCreateAllowed(_ConfigBase):
    def test_create_new_eslintrc_allowed(self):
        # File does NOT exist on disk → first-time creation → ALLOW.
        ev = _event("Write", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow, "creating a new config must be ALLOWED (ENOENT)")

    def test_create_new_ruff_toml_allowed(self):
        ev = _event("Write", file_path=str(self.repo / ".ruff.toml"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow)


# ---------------------------------------------------------------------------
# 3. Non-allowlisted / ambiguous-shared / governance files → ALLOW.
# ---------------------------------------------------------------------------


class TestNonAllowlistedAllowed(_ConfigBase):
    def test_existing_source_file_allowed(self):
        self._touch("src/index.js")
        ev = _event("Edit", file_path=str(self.repo / "src" / "index.js"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow, "ordinary source edits must be ALLOWED")

    def test_existing_pyproject_toml_allowed(self):
        # Ambiguous shared file — NOT in this hook's allowlist (plan §WS-2).
        self._touch("pyproject.toml")
        ev = _event("Edit", file_path=str(self.repo / "pyproject.toml"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow, "pyproject.toml is ambiguous-shared → ALLOW")

    def test_existing_package_json_allowed(self):
        self._touch("package.json")
        ev = _event("Edit", file_path=str(self.repo / "package.json"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow)

    def test_existing_setup_cfg_allowed(self):
        self._touch("setup.cfg")
        ev = _event("Edit", file_path=str(self.repo / "setup.cfg"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow)

    def test_governance_settings_json_not_our_job(self):
        # .claude/settings.json belongs to the canonical guard, NOT this hook
        # (debate K6 / MF-L). This hook must ALLOW it (the canonical guard fires
        # separately).
        self._touch(".claude/settings.json")
        ev = _event("Edit", file_path=str(self.repo / ".claude" / "settings.json"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow, "governance config is the canonical guard's job")

    def test_governance_pytest_ini_not_our_job(self):
        self._touch("pytest.ini")
        ev = _event("Edit", file_path=str(self.repo / "pytest.ini"))
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow)


# ---------------------------------------------------------------------------
# 4. Dangling symlink → BLOCK (treat as existing).
# ---------------------------------------------------------------------------


class TestDanglingSymlink(_ConfigBase):
    def test_dangling_symlink_config_blocked(self):
        link = self.repo / ".eslintrc.json"
        missing_target = self.repo / "does-not-exist-target.json"
        os.symlink(str(missing_target), str(link))
        self.assertFalse(missing_target.exists(), "precondition: target is missing")
        ev = _event("Edit", file_path=str(link))
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow, "dangling symlink config slot must be BLOCKED")


# ---------------------------------------------------------------------------
# 5. Truncation / no usable file path → fail-CLOSED block (bounded).
# ---------------------------------------------------------------------------


class TestFailClosedTruncation(_ConfigBase):
    def test_write_tool_no_file_path_fail_closed(self):
        # A write tool with NO file_path = truncated / ambiguous input → block.
        ev = _event("Edit", file_path="")
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow, "no resolvable file_path must fail-CLOSED")
        self.assertIn("fail-CLOSED", d.reason or "")

    def test_write_tool_missing_file_path_key_fail_closed(self):
        ev = _event("Write")  # no file_path key at all
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)

    def test_non_write_tool_allowed(self):
        # A non-write tool (should never reach here given the matcher) → ALLOW,
        # NOT fail-closed.
        ev = _event("Read", file_path="")
        d = ccp.decide(ev, env=self._env())
        self.assertTrue(d.allow, "a non-write tool must not be fail-closed")


# ---------------------------------------------------------------------------
# 6. Raw tool input is NEVER echoed (only basename + resolved path).
# ---------------------------------------------------------------------------


class TestNoInputEcho(_ConfigBase):
    def test_block_reason_does_not_echo_new_string(self):
        self._touch(".eslintrc.json")
        secret = "SUPER_SECRET_DIFF_CONTENT_rules:{no-console:off}"
        ev = _event(
            "Edit",
            file_path=str(self.repo / ".eslintrc.json"),
            new_string=secret,
        )
        d = ccp.decide(ev, env=self._env())
        self.assertFalse(d.allow)
        self.assertNotIn(secret, d.reason or "")
        self.assertNotIn("SUPER_SECRET", d.reason or "")


# ---------------------------------------------------------------------------
# 7. Escape hatches — tested ON and OFF.
# ---------------------------------------------------------------------------


class TestEscapeHatches(_ConfigBase):
    def test_kill_switch_off_blocks(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env(kill=False))
        self.assertFalse(d.allow, "without kill-switch the edit is BLOCKED")

    def test_kill_switch_on_allows(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env(kill=True))
        self.assertTrue(d.allow, "CEO_CONFIG_PROTECTION=0 must ALLOW")

    def test_per_repo_disable_file_allows(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env(disable_file=True))
        self.assertTrue(d.allow, "per-repo disable file must ALLOW")

    def test_no_disable_file_blocks(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env(disable_file=False))
        self.assertFalse(d.allow)


# ---------------------------------------------------------------------------
# 8. Advisory mode (user ceremony) — never blocks.
# ---------------------------------------------------------------------------


class TestAdvisoryMode(_ConfigBase):
    def test_advisory_existing_config_allows_with_steer(self):
        self._touch(".eslintrc.json")
        ev = _event("Edit", file_path=str(self.repo / ".eslintrc.json"))
        d = ccp.decide(ev, env=self._env(advisory=True))
        self.assertTrue(d.allow, "advisory mode must NEVER block")
        self.assertTrue(d.system_message, "advisory mode must attach a steer")
        self.assertIn("config-protection", (d.system_message or "").lower())

    def test_advisory_truncation_allows_with_steer(self):
        ev = _event("Edit", file_path="")
        d = ccp.decide(ev, env=self._env(advisory=True))
        self.assertTrue(d.allow, "advisory mode must not block on truncation either")
        self.assertTrue(d.system_message)


# ---------------------------------------------------------------------------
# 9. is_protected_basename unit coverage (allowlist boundaries).
# ---------------------------------------------------------------------------


class TestAllowlistUnit(_ConfigBase):
    def test_protected_examples(self):
        for name in (
            ".eslintrc", ".eslintrc.json", ".eslintrc.yml", "eslint.config.js",
            "eslint.config.ts", ".prettierrc", ".prettierrc.toml",
            "prettier.config.cjs", "biome.json", "biome.jsonc", "tslint.json",
            ".ruff.toml", "ruff.toml", ".flake8", ".stylelintrc",
            ".stylelintrc.yaml", ".markdownlint.json", ".markdownlintrc",
            ".shellcheckrc",
        ):
            self.assertTrue(
                ccp.is_protected_basename(name), f"{name} should be protected"
            )

    def test_unprotected_examples(self):
        for name in (
            "", "pyproject.toml", "setup.cfg", "package.json", "tox.ini",
            "settings.json", "pytest.ini", "index.js", "README.md",
            ".eslintrc.bak", "eslint.config.exe", "my.eslintrc",
            "notbiome.json", ".prettierignore",
        ):
            self.assertFalse(
                ccp.is_protected_basename(name), f"{name} should NOT be protected"
            )


# ---------------------------------------------------------------------------
# 10. main() smoke — fail-open on parse error, never raises.
# ---------------------------------------------------------------------------


class TestMainEntryPoint(_ConfigBase):
    def test_main_callable_and_returns_zero(self):
        # Drive main() with an empty stdin (parse path) — must fail-OPEN (return
        # 0) and never raise. We redirect stdin/stdout so the real streams are
        # untouched.
        import io
        import sys as _sys

        old_in, old_out = _sys.stdin, _sys.stdout
        try:
            _sys.stdin = io.StringIO("")  # empty → adapter parse handling
            _sys.stdout = io.StringIO()
            rc = ccp.main()
            self.assertEqual(rc, 0, "main() must always return 0 (fail-open)")
        finally:
            _sys.stdin, _sys.stdout = old_in, old_out
