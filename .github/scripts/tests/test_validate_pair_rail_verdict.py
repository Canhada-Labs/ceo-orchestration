"""test_validate_pair_rail_verdict.py — S104 PLAN-081 GA tail.

Tests for the parent_sha / commit_sha bind redesign in
.github/scripts/validate-pair-rail-verdict.py. The legacy
`verdict.commit_sha` self-reference is replaced with `verdict.parent_sha`
to break the chicken-and-egg problem the v1.16.0 GA ceremony hit
(verdict file cannot declare its own commit SHA because the SHA is
only known AFTER the verdict file is committed).

Coverage:
- --parent-sha match → exit 0
- --parent-sha mismatch → exit VERDICT_INVALID (3)
- --parent-sha against verdict with no parent_sha field, legacy
  commit_sha present → ADVISORY (skip bind), exit 0 if rest valid
- --parent-sha against verdict with no parent_sha + no commit_sha →
  exit VERDICT_INVALID (3)
- Legacy --commit-sha path still works on legacy verdicts (exit 0)
- Legacy --commit-sha mismatch → exit VERDICT_INVALID (3)
- --parent-sha takes precedence when both args passed

Stdlib only. Python ≥3.9. Run via pytest from repo root.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "validate-pair-rail-verdict.py"

EXIT_OK = 0
EXIT_INFRA_ERROR = 1
EXIT_VERDICT_EXPIRED = 2
EXIT_VERDICT_INVALID = 3


def _make_verdict(
    *,
    release_tag: str = "v1.99.0",
    parent_sha: str = "",
    commit_sha: str = "",
    inputs_hash: str = "deadbeef" * 8,
    generated_at: str = "9999-01-01T00:00:00Z",
    ttl_hours: int = 87600,
    tool_versions_block: str = (
        "  codex_cli: 0.129.0\n"
        "  codex_cli_binary_sha256: " + "a" * 64
    ),
    include_signature: bool = True,
) -> str:
    """Build a verdict markdown file with the requested envelope."""
    lines = [
        "# Pair-Rail Verdict — test",
        "",
        "```yaml",
        "verdict: GO",
        f"generated_at: {generated_at}",
        f"ttl_hours: {ttl_hours}",
        f"release_tag: {release_tag}",
    ]
    if parent_sha:
        lines.append(f"parent_sha: {parent_sha}")
    if commit_sha:
        lines.append(f"commit_sha: {commit_sha}")
    lines.append(f"inputs_hash: {inputs_hash}")
    lines.append("tool_versions:")
    lines.append(tool_versions_block)
    if include_signature:
        lines.append("gpg_signature: |")
        lines.append("  -----BEGIN PGP SIGNATURE-----")
        lines.append("  fake-sig-for-test")
        lines.append("  -----END PGP SIGNATURE-----")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _run(args, verdict_text: str):
    """Run validator on a tmpdir-scoped verdict file. Returns CompletedProcess."""
    with tempfile.TemporaryDirectory() as td:
        verdict_path = Path(td) / "verdict.md"
        verdict_path.write_text(verdict_text, encoding="utf-8")
        cmd = [
            sys.executable, str(SCRIPT),
            "--verdict-file", str(verdict_path),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


class TestParentShaBind(unittest.TestCase):
    """S104 redesign: --parent-sha is the canonical bind."""

    PARENT = "abcdef0123456789abcdef0123456789abcdef01"

    def test_parent_sha_match_passes_bind(self):
        v = _make_verdict(parent_sha=self.PARENT, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        # Bind passes; other checks may still pass too (no pin files
        # requested → skipped). Expected exit 0.
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)

    def test_parent_sha_mismatch_returns_invalid(self):
        v = _make_verdict(parent_sha=self.PARENT, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", "f" * 40,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("parent_sha mismatch", r.stderr)

    def test_parent_sha_arg_with_legacy_commit_sha_only_advises(self):
        """v1.16.0-era verdict shipping commit_sha but not parent_sha,
        invoked with --parent-sha → ADVISORY skip, proceed."""
        v = _make_verdict(commit_sha="deadbeef" * 5, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)
        self.assertIn("ADVISORY", r.stderr)
        self.assertIn("legacy commit_sha", r.stderr)

    def test_parent_sha_arg_with_no_sha_fields_returns_invalid(self):
        v = _make_verdict(release_tag="v1.99.0")  # neither parent_sha nor commit_sha
        r = _run(
            [
                "--parent-sha", self.PARENT,
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("missing parent_sha field", r.stderr)


class TestLegacyCommitShaBind(unittest.TestCase):
    """Backward-compat with v1.16.0-era release.yml invocations."""

    COMMIT = "1234567890abcdef1234567890abcdef12345678"

    def test_legacy_commit_sha_match_passes(self):
        v = _make_verdict(commit_sha=self.COMMIT, release_tag="v1.16.0")
        r = _run(
            [
                "--commit-sha", self.COMMIT,
                "--release-tag", "v1.16.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)

    def test_legacy_commit_sha_mismatch_returns_invalid(self):
        v = _make_verdict(commit_sha=self.COMMIT, release_tag="v1.16.0")
        r = _run(
            [
                "--commit-sha", "f" * 40,
                "--release-tag", "v1.16.0",
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("commit_sha mismatch", r.stderr)


class TestPrecedenceParentOverCommit(unittest.TestCase):
    """When both --parent-sha + --commit-sha passed, --parent-sha wins."""

    def test_parent_sha_wins_when_both_passed(self):
        # Verdict has both fields; mismatch the commit_sha but match parent_sha.
        # Validator should accept based on parent_sha (precedence).
        parent = "a" * 40
        commit = "b" * 40
        v = _make_verdict(
            parent_sha=parent, commit_sha=commit, release_tag="v1.99.0"
        )
        r = _run(
            [
                "--parent-sha", parent,
                "--commit-sha", "f" * 40,  # would FAIL legacy bind
                "--release-tag", "v1.99.0",
            ],
            v,
        )
        # parent_sha matches → bind passes. commit_sha arg ignored.
        self.assertEqual(r.returncode, EXIT_OK, msg=r.stderr)


class TestReleaseTagReplayDefense(unittest.TestCase):
    """R1 S-Sec-3: release_tag bind survives the redesign."""

    def test_release_tag_mismatch_returns_invalid(self):
        v = _make_verdict(parent_sha="a" * 40, release_tag="v1.99.0")
        r = _run(
            [
                "--parent-sha", "a" * 40,
                "--release-tag", "v1.99.0-rc.1",  # different tag
            ],
            v,
        )
        self.assertEqual(r.returncode, EXIT_VERDICT_INVALID)
        self.assertIn("release_tag mismatch", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
