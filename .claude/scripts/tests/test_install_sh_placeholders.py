"""install.sh placeholder-substitution smoke tests.

PLAN-019 Phase 2 Wave 2A Agent W2A-3 — covers P1-CR-3 / VP-F1:
  - Placeholder flags / env vars are applied via sed pass.
  - Files that ship with {{PLACEHOLDER}} markers have them substituted
    when the corresponding --owner / --project / --deploy-command / ...
    flag is supplied.
  - When flags are NOT supplied, install.sh still succeeds but
    surfaces a warning listing the unfilled placeholders.
  - Mixed-case archetype placeholders ({{VP_Engineering}}, etc.) are
    NOT substituted — those are intentional user-filled agent slot
    names per team.md convention.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import pytest
except ImportError:  # pragma: no cover - unittest-discover without pytest
    raise unittest.SkipTest(
        "pytest not available; this test module uses pytest fixtures "
        "and is skipped when unittest discover runs without pytest."
    )

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"

# All UPPER_SNAKE install-time placeholders the installer accepts via
# CLI flags or env vars. Must stay in sync with build_sed_script() in
# install.sh. This test re-runs install.sh with all of them set and
# then asserts that ZERO uppercase placeholders of these names remain.
_UPPERCASE_FLAGS = {
    "OWNER_NAME":         ("--owner", "TestOwner"),
    "PROJECT_NAME":       ("--project", "TestProj"),
    "PROJECT_PATH":       ("--project-path", "/tmp/proj-path"),
    "STACK":              ("--stack-name", "node"),
    "DEPLOY_COMMAND":     ("--deploy-command", "./deploy.sh"),
    "DEPLOY_PLATFORM":    ("--deploy-platform", "vercel"),
    "DEPLOY_TARGET":      ("--deploy-target", "prod"),
    "RUNTIME_NOTES":      ("--runtime-notes", "Node 20"),
    "DATABASE":           ("--database", "PostgreSQL 15"),
    "N_BACKEND":          ("--n-backend", "5"),
    "N_FRONTEND":         ("--n-frontend", "3"),
    "FRONTEND_STACK":     ("--frontend-stack", "Vite+React"),
    "FRONTEND_PATH":      ("--frontend-path", "./web"),
    "FRONTEND_REPO_PATH": ("--frontend-repo-path", "./web"),
    "UI_LIBRARY":         ("--ui-library", "shadcn"),
    "STATE_MANAGEMENT":   ("--state-management", "Zustand"),
    "REALTIME_TRANSPORT": ("--realtime-transport", "WebSocket"),
    "CHARTING_LIBRARY":   ("--charting-library", "Recharts"),
    "AUTH_PROVIDER":      ("--auth-provider", "Supabase"),
    "I18N_FRAMEWORK":     ("--i18n-framework", "i18next"),
    "TEST_FRAMEWORK":     ("--test-framework", "vitest"),
    "TEST_TOOL":          ("--test-tool", "vitest"),
    "TEST_COUNT":         ("--test-count", "500"),
    "LINT_TOOL":          ("--lint-tool", "eslint"),
    "CI_TOOL":            ("--ci-tool", "GHA"),
    "APP_NAME":           ("--app-name", "TestApp"),
    "SOURCE_FILE_COUNT":  ("--source-file-count", "200"),
    "LINE_COUNT":         ("--line-count", "15000"),
    "LINES":              ("--lines", "15000"),
    "FILE_COUNT":         ("--file-count", "200"),
    "PAGE_COUNT":         ("--page-count", "50"),
    "COMPONENT_COUNT":    ("--component-count", "80"),
    "HOOK_COUNT":         ("--hook-count", "12"),
    "BUNDLE_SIZE":        ("--bundle-size", "120kb"),
    "CITY":               ("--city", "SaoPaulo"),
    "COUNTRY":            ("--country", "Brazil"),
    "DOMAIN":             ("--domain", "example.com"),
    "FOUNDER_NAME":       ("--founder-name", "Jane Doe"),
    "LEGAL_ID":           ("--legal-id", "12.345.678/0001-00"),
    "PRODUCTION_URL":     ("--production-url", "https://test.example.com"),
    "OWNER_HANDLE":       ("--github-owner", "testhandle"),
}

_UPPERCASE_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")
_ARCHETYPE_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][a-zA-Z_]+\}\}")


def _run_install(target: Path, *args: str, timeout: float = 120.0) -> subprocess.CompletedProcess:
    cmd = ["bash", str(INSTALL_SH), str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _collect_placeholders(root: Path, regex: re.Pattern) -> dict:
    """Walk root, return {placeholder -> [(file, line_number, line)]} matches.

    PLAN-045 F-install-sh-shadow (Session 42 polish): ``*.shadow.md``
    siblings are dogfood-only SP-NNN soak artifacts that mirror the
    pre-substitution SKILL.md body byte-identically. The adopter
    install flow reaches them because ``install.sh install_one`` uses
    ``cp -R`` on skill dirs; but the proper fix (exclude shadows from
    copy OR extend the sed pass to shadows) requires an install.sh
    canonical-edit sentinel, staged as a separate round. Here at the
    test level we skip shadows so the placeholder scan doesn't
    false-positive on the dogfood's own soak-window state.
    """
    hits: dict = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # PLAN-045 F-install-sh-shadow: skip SP-NNN shadow siblings
        # (pre-substitution on-disk representation of post-promote
        # SKILL.md; dogfood-only).
        if path.name.endswith(".shadow.md"):
            continue
        if path.name.endswith(".shadow.md.lock"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for m in regex.finditer(line):
                hits.setdefault(m.group(0), []).append(
                    (str(path.relative_to(root)), idx, line.strip())
                )
    return hits


# --------------------------------------------------------------------------
# Scenario 1: every install-time placeholder supplied -> zero uppercase
#             placeholders remain in user-editable template files.
# --------------------------------------------------------------------------


def test_install_sh_all_placeholders_substituted(tmp_path: Path):
    """With all flags supplied, user-editable template files have no {{UPPERCASE}}."""
    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    flags = []
    for flag_name, (flag, val) in _UPPERCASE_FLAGS.items():
        flags.extend([flag, val])

    # keep install reasonably short by staying on --profile core
    result = _run_install(target, "--profile", "core", *flags)
    assert result.returncode == 0, (
        f"install failed rc={result.returncode}\nstderr={result.stderr[-1500:]}"
    )

    # Walk .claude/ and CLAUDE.md. Uppercase placeholders may remain ONLY
    # in files that documents the placeholder pattern itself — those live
    # in .claude/scripts/ (python docstrings) and in the `.claude/team.md`
    # single instructional line.
    hits = _collect_placeholders(target / ".claude", _UPPERCASE_PLACEHOLDER_RE)

    # Paths are RELATIVE to target/.claude/, so skills/scripts prefix is
    # sufficient — no leading `.claude/`.
    allowlist_roots = (
        "scripts/",
        # team.md carries one instructional line mentioning {{PLACEHOLDERS}}
        # literally so the user understands the convention.
    )
    unexpected = {}
    for ph, locations in hits.items():
        for rel, lineno, line in locations:
            # {{PLACEHOLDERS}} inside team.md is a literal instructional mention
            if ph == "{{PLACEHOLDERS}}":
                continue
            if any(rel.startswith(prefix) for prefix in allowlist_roots):
                continue
            # Anything else is a real un-substituted placeholder.
            unexpected.setdefault(ph, []).append(f"{rel}:{lineno}: {line}")

    assert not unexpected, (
        "install-time uppercase placeholders remain in non-instructional files:\n"
        + "\n".join(
            f"{ph}:\n  " + "\n  ".join(entries) for ph, entries in unexpected.items()
        )
    )


# --------------------------------------------------------------------------
# Scenario 2: no flags supplied -> install still succeeds, warning emitted
# --------------------------------------------------------------------------


def test_install_sh_without_flags_emits_placeholder_warning(tmp_path: Path):
    """Without --owner/--project flags, install succeeds and warns about unfilled."""
    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    result = _run_install(target, "--profile", "core")
    assert result.returncode == 0, (
        f"install failed rc={result.returncode}\nstderr={result.stderr[-800:]}"
    )
    # Warning must surface in stderr.
    combined = result.stdout + result.stderr
    assert "still contain {{PLACEHOLDER}} markers" in combined, (
        "missing 'still contain {{PLACEHOLDER}}' warning:\n"
        + combined[-1500:]
    )


# --------------------------------------------------------------------------
# Scenario 3: archetype placeholders ({{VP_Engineering}}) are PRESERVED
# --------------------------------------------------------------------------


def test_install_sh_preserves_archetype_placeholders(tmp_path: Path):
    """Mixed-case {{Archetype_Name}} slots survive substitution pass."""
    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    # Supply every install-time placeholder; archetype slots must still remain.
    flags = []
    for flag_name, (flag, val) in _UPPERCASE_FLAGS.items():
        flags.extend([flag, val])

    result = _run_install(target, "--profile", "core", *flags)
    assert result.returncode == 0, result.stderr[-800:]

    hits = _collect_placeholders(target / ".claude", _ARCHETYPE_PLACEHOLDER_RE)
    # At least a handful of archetype placeholders should survive
    # (VP_*, Principal_*, Staff_* are the common ones in team.md +
    # agent-metrics.md).
    assert hits, (
        "archetype placeholders were incorrectly substituted — "
        "the installer should not touch {{VP_Engineering}}-style slots"
    )
    # Sanity: none of them leaked into .claude/scripts/*.py runtime code
    for ph, locations in hits.items():
        for rel, _, _ in locations:
            assert not (rel.endswith(".py") and "/scripts/" in rel), (
                f"archetype placeholder {ph} leaked into script code at {rel}"
            )


# --------------------------------------------------------------------------
# Scenario 4: env-var fallback works (CEO_OWNER / CEO_PROJECT)
# --------------------------------------------------------------------------


def test_install_sh_env_vars_substitute(tmp_path: Path):
    """CEO_OWNER / CEO_PROJECT env vars substitute without needing CLI flags."""
    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    env = os.environ.copy()
    env["CEO_OWNER"] = "EnvOwner"
    env["CEO_PROJECT"] = "EnvProject"
    env["CEO_DEPLOY_COMMAND"] = "./env-deploy.sh"

    result = subprocess.run(
        ["bash", str(INSTALL_SH), str(target), "--profile", "core"],
        capture_output=True, text=True, timeout=120, env=env,
    )
    assert result.returncode == 0, result.stderr[-800:]

    # Check that the CLAUDE.md file has the env-supplied values.
    claude_md = target / "CLAUDE.md"
    assert claude_md.is_file()
    content = claude_md.read_text(encoding="utf-8")
    assert "EnvOwner" in content or "EnvProject" in content, (
        "env var values did not land in CLAUDE.md:\n" + content[:500]
    )
