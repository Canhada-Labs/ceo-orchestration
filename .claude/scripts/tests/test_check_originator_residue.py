"""Tests for check-originator-residue.py (PLAN-019 VP-F2).

stdlib only, ~100ms total.
"""

from __future__ import annotations

import os
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
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-originator-residue.py"


def _seed_minimal_tree(root: Path) -> None:
    (root / ".claude" / "skills" / "core" / "sample").mkdir(parents=True)
    (root / ".claude" / "skills" / "frontend").mkdir(parents=True)
    (root / ".claude" / "commands").mkdir(parents=True)
    (root / ".claude" / "team.md").write_text("# team\n", encoding="utf-8")
    (root / ".claude" / "frontend-team.md").write_text("# fe team\n", encoding="utf-8")
    (root / ".claude" / "pitfalls-catalog.yaml").write_text("pitfalls: []\n", encoding="utf-8")
    (root / ".claude" / "task-chains.yaml").write_text("chains: []\n", encoding="utf-8")
    (root / "templates").mkdir()


def _run(root: Path, verbose: bool = False) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRIPT)]
    if verbose:
        args.append("--verbose")
    args.extend(["--root", str(root)])
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=20.0,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)},
    )


@pytest.fixture()
def clean_tree(tmp_path: Path) -> Path:
    _seed_minimal_tree(tmp_path)
    # Populate with clean skill
    (tmp_path / ".claude" / "skills" / "core" / "sample" / "SKILL.md").write_text(
        "# Sample\n\nUse when the user mentions {{PROJECT_NAME}}.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_clean_tree_passes(clean_tree: Path) -> None:
    result = _run(clean_tree, verbose=True)
    assert result.returncode == 0, (
        f"clean tree unexpectedly failed:\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "PASS: no originator residue found" in result.stdout


def test_skill_with_originator_handle_fails(clean_tree: Path) -> None:
    (clean_tree / ".claude" / "skills" / "core" / "sample" / "SKILL.md").write_text(
        "# Sample\n\nContact @example-owner for questions.\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    assert result.returncode == 2
    assert "originator-project residue detected" in result.stderr
    assert "@example-owner" in result.stderr


def test_skill_with_originator_handle_case_insensitive(clean_tree: Path) -> None:
    (clean_tree / ".claude" / "skills" / "core" / "sample" / "SKILL.md").write_text(
        "# Sample\n\nHandle: Example-Owner\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    assert result.returncode == 2


def test_team_md_with_originator_fails(clean_tree: Path) -> None:
    (clean_tree / ".claude" / "team.md").write_text(
        "## Owner\nCurrent Owner: @example-owner\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    assert result.returncode == 2
    assert "team.md" in result.stderr


def test_acme_internal_hits(clean_tree: Path) -> None:
    (clean_tree / ".claude" / "skills" / "core" / "sample" / "SKILL.md").write_text(
        "See acme-internal integration\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    assert result.returncode == 2
    assert "acme-internal" in result.stderr.lower()


def test_codeowners_is_exempt(clean_tree: Path) -> None:
    # .github/CODEOWNERS is legitimately the handle-carrying file
    (clean_tree / ".github").mkdir()
    (clean_tree / ".github" / "CODEOWNERS").write_text(
        "* @example-owner\n", encoding="utf-8"
    )
    result = _run(clean_tree)
    # CODEOWNERS is outside scan roots, so this is de-facto exempt.
    assert result.returncode == 0


def test_claude_md_is_exempt(clean_tree: Path) -> None:
    # Root CLAUDE.md is session-narrative; allowed
    (clean_tree / "CLAUDE.md").write_text(
        "Owner: @example-owner\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    assert result.returncode == 0


def test_docs_research_is_exempt(clean_tree: Path) -> None:
    (clean_tree / "docs" / "research").mkdir(parents=True)
    (clean_tree / "docs" / "research" / "external-foo.md").write_text(
        "Audit of example-owner's external repo.\n",
        encoding="utf-8",
    )
    result = _run(clean_tree)
    # docs/research/ is outside default scan roots; default behavior
    assert result.returncode == 0


def test_binary_file_skipped(clean_tree: Path) -> None:
    # A PNG-named file with a NUL byte should be silently skipped.
    binpath = clean_tree / ".claude" / "skills" / "core" / "sample" / "logo.png"
    binpath.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00@example-owner")
    result = _run(clean_tree)
    # .png is in _SKIP_EXTENSIONS; must not crash or flag.
    assert result.returncode == 0


def test_real_repo_passes() -> None:
    """Sanity: current repo has no originator residue in distribution files."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--verbose"],
        capture_output=True,
        text=True,
        timeout=30.0,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT)},
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        "Real repo flags originator residue:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
