"""Tests for .claude/scripts/check-creative-rewrite.py — P1-05 Wave 0 PLAN-074.

Tests are skipped when the rewrite-checker script is absent
(adopter installs or pre-ceremony staging).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate the checker
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .claude/scripts/tests -> .claude/scripts -> .claude -> ceo-orchestration
_CANONICAL = _REPO_ROOT / ".claude" / "scripts" / "check-creative-rewrite.py"

if not _CANONICAL.exists():
    CHECKER = None
else:
    CHECKER = _CANONICAL

pytestmark = pytest.mark.skipif(
    CHECKER is None,
    reason="check-creative-rewrite.py not found — skipping in adopter install",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER)] + args,
        capture_output=True,
        text=True,
    )


def _write_skill(path: Path, body: str, description: str = "A sufficiently detailed description of this skill") -> Path:
    """Write a minimal SKILL.md at path and return the path."""
    content = f"---\ndescription: {description}\n---\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


def _write_upstream_file(path: Path, body: str) -> Path:
    """Write an upstream .md file and return the path."""
    path.write_text(f"# Upstream\n\n{body}\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Rule 3a — word match
# ---------------------------------------------------------------------------

def test_rule_3a_word_match_triggers_exit_1(tmp_path):
    """12+ consecutive words shared between target and upstream → exit 1 + DROP-3A-WORD-MATCH."""
    upstream_dir = tmp_path / "upstream"
    upstream_dir.mkdir()

    # Write a long shared phrase (>= 12 unique words)
    shared_phrase = "the quick brown fox jumps over the lazy dog near the river bank and"
    upstream_body = f"Some intro text. {shared_phrase} continued content here."
    target_body = f"## How It Works\n\nExplanation: {shared_phrase} continued content here.\n\n## Anti-Patterns\n\n" + "filler " * 50

    _write_upstream_file(upstream_dir / "source.md", upstream_body)
    target = _write_skill(tmp_path / "SKILL.md", target_body)

    result = _run(["--target", str(target), "--upstream-dir", str(upstream_dir), "--threshold-words", "12"])
    assert result.returncode == 1, f"Expected exit 1. stdout={result.stdout!r}"
    assert "DROP-3A-WORD-MATCH" in result.stdout, f"Expected DROP-3A finding. stdout={result.stdout!r}"


# ---------------------------------------------------------------------------
# Rule 3b — H2 SHA match
# ---------------------------------------------------------------------------

def test_rule_3b_h2_sha_match_triggers_exit_1(tmp_path):
    """Identical H2 section content between target and upstream → exit 1 + DROP-3B-H2-SHA-MATCH."""
    upstream_dir = tmp_path / "upstream"
    upstream_dir.mkdir()

    # Write identical H2 section body (non-trivial — must have content)
    section_body = textwrap.dedent("""\
        This section describes how the system handles authentication.
        First, validate the token. Then check permissions. Finally emit an audit event.
        This is a multi-sentence section to ensure the SHA is non-trivial.
        """)

    upstream_content = f"# Upstream\n\n## Authentication Flow\n\n{section_body}\n"
    (upstream_dir / "auth.md").write_text(upstream_content, encoding="utf-8")

    # Target has the SAME H2 section (identical body)
    target_body = (
        f"## Authentication Flow\n\n{section_body}\n"
        "## Other Section\n\nDifferent content here that is unique.\n\n"
        + "padding text " * 50
    )
    target = _write_skill(tmp_path / "SKILL.md", target_body)

    result = _run(["--target", str(target), "--upstream-dir", str(upstream_dir)])
    assert result.returncode == 1, f"Expected exit 1 for H2 SHA match. stdout={result.stdout!r}"
    assert "DROP-3B-H2-SHA-MATCH" in result.stdout, f"Expected DROP-3B finding. stdout={result.stdout!r}"


# ---------------------------------------------------------------------------
# Disjoint vocabulary → exit 0
# ---------------------------------------------------------------------------

def test_disjoint_vocabulary_exits_zero(tmp_path):
    """Completely different content between target and upstream → exit 0."""
    upstream_dir = tmp_path / "upstream"
    upstream_dir.mkdir()

    upstream_body = "legacy cobol batch processing mainframe EBCDIC punched card reader"
    target_body = (
        "## When to Apply\n\nUse Kubernetes with Helm charts for declarative deployments.\n\n"
        "## Anti-Patterns\n\nNever hardcode secrets in container images.\n\n"
        "```yaml\napiVersion: apps/v1\nkind: Deployment\n```\n"
        + "unique words " * 30
    )

    _write_upstream_file(upstream_dir / "legacy.md", upstream_body)
    target = _write_skill(tmp_path / "SKILL.md", target_body)

    result = _run(["--target", str(target), "--upstream-dir", str(upstream_dir)])
    assert result.returncode == 0, f"Expected exit 0 for disjoint. stdout={result.stdout!r}"
    assert "DROP-3A" not in result.stdout
    assert "DROP-3B" not in result.stdout


# ---------------------------------------------------------------------------
# Missing --upstream-dir → exit 2
# ---------------------------------------------------------------------------

def test_missing_upstream_source_exits_2(tmp_path):
    """Neither --upstream-dir nor --upstream-archive provided → exit 2 with diagnostic."""
    target = _write_skill(tmp_path / "SKILL.md", "## H1\n\nsome body\n\n## H2\n\nother body\n")

    result = _run(["--target", str(target)])
    assert result.returncode == 2, f"Expected exit 2. returncode={result.returncode}"
    # Diagnostic should mention the missing upstream
    stderr_lower = result.stderr.lower()
    assert "upstream" in stderr_lower or "no upstream" in stderr_lower, (
        f"Expected upstream diagnostic in stderr. stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# URLs in target are stripped (not matched against upstream)
# ---------------------------------------------------------------------------

def test_urls_in_target_stripped_from_matching(tmp_path):
    """
    A URL in the target body that appears nowhere in upstream should NOT trigger a finding.
    If URLs were not stripped, a URL shared by accident could produce false-positives.
    Conversely, a URL in target that is NOT in upstream must not fire.
    """
    upstream_dir = tmp_path / "upstream"
    upstream_dir.mkdir()

    # Upstream has no URLs at all
    upstream_body = "standard text about security patterns and practices without any links at all"
    _write_upstream_file(upstream_dir / "sec.md", upstream_body)

    # Target has a URL — this should be stripped and not cause a match
    target_body = (
        "## Documentation\n\nSee https://example.com/very/long/url/that/is/unique/to/target/skill.md "
        "for details.\n\n## Guidance\n\nFollow these steps carefully in your implementation.\n\n"
        + "fresh unique vocabulary " * 20
    )
    target = _write_skill(tmp_path / "SKILL.md", target_body)

    result = _run(["--target", str(target), "--upstream-dir", str(upstream_dir)])
    # The URL is only in the target — no match should fire
    assert "DROP-3A" not in result.stdout, (
        f"URL in target should not trigger word-match finding. stdout={result.stdout!r}"
    )
