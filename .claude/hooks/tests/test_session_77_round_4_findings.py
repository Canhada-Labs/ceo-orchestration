"""Tests for PLAN-063 round-4 ceremony — actionlint hard-fail full closure.

Round-3 SHA-pinned actionlint to 1.7.7 (was 1.7.1); the newer version
flagged additional pre-existing issues in tournament.yml + release.yml
that 1.7.1 was lenient on. Round-4 closes those residuals.

PLAN-086 Wave G.5: skip guards removed (PLAN-063 round-4 shipped at v1.19.0).

Findings covered:
- tournament.yml SC2002 useless cat × 2 (lines 136 + 177)
- tournament.yml SC2016 single-quote $-expansion (line 177)
- release.yml if-cond constant expressions × 3 (lines 391 + 398 + 426)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


class TournamentShellcheckCleanup(TestEnvContext):
    """tournament.yml passes SC2002 + SC2016 post-ceremony."""

    def setUp(self) -> None:
        super().setUp()
        self.tournament_yml = REPO_ROOT / ".github/workflows/tournament.yml"
        self.body = self.tournament_yml.read_text(encoding="utf-8")

    def test_sc2002_b1_no_useless_cat_head(self) -> None:
        """B1: useless cat → head -20 directly."""
        self.assertNotIn(
            "cat projection.txt | head -20",
            self.body,
            "tournament.yml still has cat projection.txt | head -20 (SC2002)",
        )
        self.assertIn(
            "head -20 projection.txt",
            self.body,
            "tournament.yml missing head -20 projection.txt replacement",
        )

    def test_sc2002_sc2016_b2_extract_to_var(self) -> None:
        """B2: cat+python pipe refactored to extract-to-var pattern."""
        self.assertIn(
            "PLAN-063 round-4 (SC2002+SC2016 fix)",
            self.body,
            "tournament.yml missing round-4 refactor marker",
        )
        # No more cat-pipe-python pattern at the projection echo site.
        self.assertNotIn(
            "cat projection.txt 2>/dev/null | python3 -c",
            self.body,
            "tournament.yml still has cat | python3 -c pattern",
        )
        # New extract-to-var pattern present.
        self.assertIn(
            "PROJECTION=$(python3 -c",
            self.body,
            "tournament.yml missing PROJECTION=$(python3 -c ...) extract pattern",
        )


class ReleaseYmlIfCondCleanup(TestEnvContext):
    """release.yml has no constant `if: true|false` expressions."""

    def setUp(self) -> None:
        super().setUp()
        self.release_yml = REPO_ROOT / ".github/workflows/release.yml"
        self.body = self.release_yml.read_text(encoding="utf-8")

    def test_b3_sbom_step_no_if_true(self) -> None:
        """B3: SBOM activation `if: true` removed."""
        # The SBOM step name is followed immediately by a comment, not
        # `if: true`.
        self.assertNotIn(
            '- name: Generate CycloneDX SBOM\n        if: true',
            self.body,
            "SBOM step still has `if: true`",
        )
        # Sanity: the step still exists and has the activation comment.
        self.assertIn(
            "Generate CycloneDX SBOM",
            self.body,
            "SBOM step itself disappeared (regression)",
        )

    def test_b4_sigstore_step_uses_vars_expression(self) -> None:
        """B4: sigstore STAGED `if: false` → vars.SIGSTORE_ACTIVATED expr."""
        self.assertNotIn(
            '- name: Sign release tarball with sigstore\n        if: false',
            self.body,
            "sigstore step still has constant `if: false`",
        )
        self.assertIn(
            "vars.SIGSTORE_ACTIVATED",
            self.body,
            "sigstore step missing vars.SIGSTORE_ACTIVATED dynamic gate",
        )

    def test_b5_verify_tag_step_no_if_true(self) -> None:
        """B5: verify-tag-GPG-signature `if: true` removed."""
        self.assertNotIn(
            '- name: Verify tag GPG signature\n        if: true',
            self.body,
            "verify-tag-GPG step still has `if: true`",
        )
        self.assertIn(
            "Verify tag GPG signature",
            self.body,
            "verify-tag-GPG step itself disappeared (regression)",
        )


if __name__ == "__main__":
    unittest.main()
