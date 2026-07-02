"""PLAN-SCHEMA §1 mechanical enforcement — validate-governance.sh.

PLAN-019 VP-F4: the PLAN-SCHEMA §1 directory + filename invariants
were documentary-only from Sprint 1. This test pins the Sprint-14
commitment ("Sprint 3+ may enforce") into Sprint-14-era mechanical
enforcement inside ``validate-governance.sh``.

The test builds a temporary repo that contains the minimum skeleton
``validate-governance.sh`` expects (team.md + hooks + a non-empty
skills tree + .claude/plans/) and then seeds deliberate invariant
violations, asserting the script exits non-zero with the expected
error lines.

stdlib only. No network. ~200ms total.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
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
VALIDATE_SH = REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"


def _seed_minimal_repo(root: Path) -> None:
    """Build the minimum file tree validate-governance.sh expects.

    Mirrors the REQUIRED_FILES list in the script; we use empty or
    minimally valid contents so the earlier sections emit PASS/WARN
    (not ERROR) and the only errors come from the PLAN-SCHEMA section.
    """
    # .claude skeleton
    (root / ".claude").mkdir()
    (root / ".claude" / "team.md").write_text("# team\n", encoding="utf-8")
    (root / ".claude" / "pitfalls-catalog.yaml").write_text("pitfalls: []\n", encoding="utf-8")
    (root / ".claude" / "task-chains.yaml").write_text("chains: []\n", encoding="utf-8")
    (root / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")

    # hooks
    hooks = root / ".claude" / "hooks"
    hooks.mkdir()
    (hooks / "_python-hook.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (hooks / "_python-hook.sh").chmod(0o755)
    (hooks / "check_agent_spawn.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (hooks / "check_agent_spawn.py").chmod(0o755)
    (hooks / "audit_log.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (hooks / "audit_log.py").chmod(0o755)

    # skills — at least one valid SKILL.md so skill inventory > 0.
    skill_dir = root / ".claude" / "skills" / "core" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# sample\n", encoding="utf-8")

    (root / ".claude" / "skills" / "frontend").mkdir()

    # scripts
    scripts = root / ".claude" / "scripts"
    scripts.mkdir()
    shutil.copy2(VALIDATE_SH, scripts / "validate-governance.sh")
    os.chmod(scripts / "validate-governance.sh", 0o755)

    # PLAN-081 Phase 2 — dispatcher canonical surface (stub files for fixture).
    # validate-governance.sh only checks existence via `[ -f ]`.
    dispatcher = root / ".claude" / "dispatcher"
    dispatcher.mkdir()
    (dispatcher / "routing-matrix.yaml").write_text("archetypes: []\n", encoding="utf-8")
    (dispatcher / "routing-matrix-loader.py").write_text("# stub\n", encoding="utf-8")
    (dispatcher / "disable_predicate_eval.py").write_text("# stub\n", encoding="utf-8")

    # plans dir with one valid plan so normal case passes
    plans = root / ".claude" / "plans"
    plans.mkdir()
    (plans / "README.md").write_text("# plans\n", encoding="utf-8")
    (plans / "PLAN-SCHEMA.md").write_text("---\nid: PLAN-SCHEMA\n---\n", encoding="utf-8")
    (plans / "PLAN-001-example-slug.md").write_text(
        textwrap.dedent(
            """\
            ---
            id: PLAN-001
            title: Example
            status: draft
            created: 2026-04-17
            owner: CEO
            depends_on: []
            ---

            # Example plan
            """
        ),
        encoding="utf-8",
    )

    # empty CLAUDE.md so size check passes
    (root / "CLAUDE.md").write_text("# claude md\n", encoding="utf-8")


def _run_validate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", ".claude/scripts/validate-governance.sh"],
        cwd=str(root),
        capture_output=True,
        text=True,
        # validate-governance.sh is a full-tree governance pass (~16s idle vs
        # the real repo); a 20s ceiling has only ~3s headroom and SIGKILL-times-
        # out under the finish-ceremony's loaded sequential scripts pass. 180s is
        # a generous, correctness-inert bound (assertions check FAIL lines, not duration).
        timeout=180.0,
    )


@pytest.fixture()
def minimal_repo(tmp_path: Path) -> Path:
    _seed_minimal_repo(tmp_path)
    return tmp_path


def test_valid_plan_tree_passes(minimal_repo: Path) -> None:
    """Baseline: a well-formed .claude/plans/ tree → validate-governance PASS."""
    result = _run_validate(minimal_repo)
    assert result.returncode == 0, (
        f"validate-governance.sh failed on a valid tree:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "PASS: Governance files validated." in result.stdout


def test_invalid_subdirectory_fails(minimal_repo: Path) -> None:
    """.claude/plans/INVALID_DIR_TEST/ → non-zero exit + error message."""
    (minimal_repo / ".claude" / "plans" / "INVALID_DIR_TEST").mkdir()
    result = _run_validate(minimal_repo)
    assert result.returncode != 0, (
        "validate-governance.sh unexpectedly passed with an "
        "invalid PLAN subdir:\n" + result.stdout
    )
    assert "PLAN-SCHEMA §1 invalid subdir" in result.stdout
    assert "INVALID_DIR_TEST" in result.stdout


def test_valid_subdirectories_allowed(minimal_repo: Path) -> None:
    """PLAN-NNN/, examples/, archive/ subdirs all pass."""
    (minimal_repo / ".claude" / "plans" / "PLAN-001").mkdir()
    (minimal_repo / ".claude" / "plans" / "examples").mkdir()
    (minimal_repo / ".claude" / "plans" / "archive").mkdir()
    result = _run_validate(minimal_repo)
    assert result.returncode == 0, (
        "validate-governance.sh unexpectedly failed with all-valid "
        "subdirs:\n" + result.stdout
    )
    assert "OK: no invalid subdirectories" in result.stdout
    assert "OK: every PLAN-NNN subdir has a matching plan file" in result.stdout


def test_orphan_plan_dir_fails(minimal_repo: Path) -> None:
    """PLAN-002/ with no matching PLAN-002-*.md plan file → orphan error.

    PLAN-152 governance-05 / dead-code-03: PLAN-SCHEMA §1 subdir rule 1
    requires a ``PLAN-<NNN>/`` subdir to match an EXISTING top-level plan
    file. The seeded repo ships only PLAN-001-example-slug.md, so PLAN-002/
    is an orphan (the PLAN-128 clean-room-migration class).
    """
    (minimal_repo / ".claude" / "plans" / "PLAN-002").mkdir()
    result = _run_validate(minimal_repo)
    assert result.returncode != 0, (
        "validate-governance.sh unexpectedly passed with an orphan "
        "PLAN-NNN subdir:\n" + result.stdout
    )
    assert "PLAN-SCHEMA §1 orphan PLAN-<NNN> subdir" in result.stdout
    assert "PLAN-002" in result.stdout


def test_invalid_filename_wrong_nnn_width_fails(minimal_repo: Path) -> None:
    """PLAN-1-foo.md (1 digit instead of 3) → error."""
    (minimal_repo / ".claude" / "plans" / "PLAN-1-foo.md").write_text(
        "---\nid: PLAN-001\n---\n", encoding="utf-8"
    )
    result = _run_validate(minimal_repo)
    assert result.returncode != 0
    assert "PLAN-SCHEMA §1 invalid filename" in result.stdout
    assert "PLAN-1-foo.md" in result.stdout


def test_invalid_filename_no_slug_fails(minimal_repo: Path) -> None:
    """PLAN-002.md (missing slug) → error."""
    (minimal_repo / ".claude" / "plans" / "PLAN-002.md").write_text(
        "---\nid: PLAN-002\n---\n", encoding="utf-8"
    )
    result = _run_validate(minimal_repo)
    assert result.returncode != 0
    assert "PLAN-SCHEMA §1 invalid filename" in result.stdout
    assert "PLAN-002.md" in result.stdout


def test_invalid_filename_uppercase_slug_fails(minimal_repo: Path) -> None:
    """PLAN-003-FooBar.md (uppercase slug) → error."""
    (minimal_repo / ".claude" / "plans" / "PLAN-003-FooBar.md").write_text(
        "---\nid: PLAN-003\n---\n", encoding="utf-8"
    )
    result = _run_validate(minimal_repo)
    assert result.returncode != 0
    assert "PLAN-SCHEMA §1 invalid filename" in result.stdout
    assert "PLAN-003-FooBar.md" in result.stdout


def test_stray_markdown_file_fails(minimal_repo: Path) -> None:
    """Random .md at .claude/plans/NOTES.md → error."""
    (minimal_repo / ".claude" / "plans" / "NOTES.md").write_text(
        "# stray\n", encoding="utf-8"
    )
    result = _run_validate(minimal_repo)
    assert result.returncode != 0
    assert "PLAN-SCHEMA §1 invalid filename" in result.stdout
    assert "NOTES.md" in result.stdout


def test_known_governance_files_allowed(minimal_repo: Path) -> None:
    """README/PLAN-SCHEMA/AUDIT-LOG-SCHEMA/DEBATE-SCHEMA all pass."""
    (minimal_repo / ".claude" / "plans" / "AUDIT-LOG-SCHEMA.md").write_text(
        "# audit log\n", encoding="utf-8"
    )
    (minimal_repo / ".claude" / "plans" / "DEBATE-SCHEMA.md").write_text(
        "# debate\n", encoding="utf-8"
    )
    result = _run_validate(minimal_repo)
    assert result.returncode == 0, (
        "validate-governance.sh unexpectedly failed with standard "
        "governance files:\n" + result.stdout
    )
    assert "all filenames match" in result.stdout


@pytest.mark.serial
def test_real_repo_passes() -> None:
    """Sanity: the actual repo's .claude/plans/ passes the new checks.

    This guards against a false positive slipping in: if the new
    invariant flags a file that shipped, the rest of the agent's work
    must normalize that file BEFORE this test can land.
    """
    result = subprocess.run(
        ["bash", str(VALIDATE_SH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        # 20s -> 180s: full-tree validate-governance.sh is ~16s idle; under the
        # finish-ceremony load this SIGKILL-timed-out. Generous, correctness-inert.
        timeout=180.0,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT)},
    )
    # We only assert the PLAN-SCHEMA §1 section printed no FAIL lines.
    # The overall rc may be 0 or 1 depending on other unrelated warnings
    # in the repo; what matters here is that the new section is clean.
    assert "PLAN-SCHEMA §1 invalid subdir" not in result.stdout, (
        "Real repo triggers false-positive invalid-subdir:\n" + result.stdout
    )
    assert "PLAN-SCHEMA §1 invalid filename" not in result.stdout, (
        "Real repo triggers false-positive invalid-filename:\n" + result.stdout
    )
    assert "PLAN-SCHEMA §1 orphan PLAN-<NNN> subdir" not in result.stdout, (
        "Real repo triggers false-positive orphan PLAN-NNN subdir "
        "(is a PLAN-<NNN>/ dir missing its PLAN-<NNN>-*.md plan file?):\n"
        + result.stdout
    )
