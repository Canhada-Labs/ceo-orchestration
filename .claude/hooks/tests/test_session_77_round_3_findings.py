"""Tests for PLAN-063 round-3 ceremony — Task #18 + DIM-20 #1 partial closure.

These tests assert the canonical patches LANDED via the Owner-run
`OWNER-SESSION-77-ROUND-3-ACTIONLINT-CLEANUP.sh` script. They use
class-level `@unittest.skipUnless` guards so the file is harmless
pre-ceremony and becomes hard-fail post-ceremony.

The ceremony script sets `CEO_PHASE_5_BIS_77_LANDED=1` BEFORE running
pytest. Pre-ceremony (default) the env var is unset, so all tests skip
cleanly.

Findings covered:
- **Task #18 closure**: tier-policy.yml SC2012 (ls -t disable directive)
  + SC2129 (group $GITHUB_STEP_SUMMARY redirects).
- **DIM-20 #1 partial closure**: actionlint.yml SHA-pin 1.7.7 +
  hard-fail name + summary text cleanup.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

PHASE_5_BIS_LANDED = os.environ.get("CEO_PHASE_5_BIS_77_LANDED", "0") == "1"


# ---------------------------------------------------------------------------
# Task #18 — tier-policy.yml shellcheck cleanup
# ---------------------------------------------------------------------------


@unittest.skipUnless(PHASE_5_BIS_LANDED, "Round-3 ceremony not yet landed")
class Task18TierPolicyShellcheckCleanup(TestEnvContext):
    """tier-policy.yml passes shellcheck SC2012 + SC2129 post-ceremony."""

    def setUp(self) -> None:
        super().setUp()
        self.tier_policy = REPO_ROOT / ".github/workflows/tier-policy.yml"
        self.body = self.tier_policy.read_text(encoding="utf-8")

    def test_sc2012_disable_directive_present(self) -> None:
        """SC2012 disable directive precedes the `ls -t` invocation."""
        self.assertIn(
            "shellcheck disable=SC2012",
            self.body,
            "tier-policy.yml missing SC2012 disable directive",
        )
        # Sanity: the original ls -t invocation is still present
        # (semantic preservation — we disable the lint, not the logic).
        self.assertIn(
            "ls -t benchmarks/tournament-",
            self.body,
            "tier-policy.yml ls -t invocation removed by mistake",
        )

    def test_sc2129_group_redirect_block_present(self) -> None:
        """7 individual >> redirects consolidated into a { ... } >> block."""
        # The new block opens with `{` indented + has the consolidated
        # marker comment.
        self.assertIn(
            "SC2129: group redirects (PLAN-063 round-3, Task #18)",
            self.body,
            "tier-policy.yml SC2129 group-redirect block missing",
        )
        # Sanity: no surviving individual redirects to GITHUB_STEP_SUMMARY
        # in the Summary step (count tolerance: <=1 for any unrelated
        # references in comments).
        sumref_count = self.body.count('>> "$GITHUB_STEP_SUMMARY"')
        self.assertLessEqual(
            sumref_count, 1,
            f"too many individual >> $GITHUB_STEP_SUMMARY redirects "
            f"({sumref_count}); expected consolidated block",
        )


# ---------------------------------------------------------------------------
# DIM-20 #1 partial — actionlint.yml SHA-pin + hard-fail text
# ---------------------------------------------------------------------------


@unittest.skipUnless(PHASE_5_BIS_LANDED, "Round-3 ceremony not yet landed")
class DIM20_1ActionlintShaPin(TestEnvContext):
    """actionlint.yml uses SHA-pinned 1.7.7 + hard-fail text."""

    def setUp(self) -> None:
        super().setUp()
        self.actionlint_yml = REPO_ROOT / ".github/workflows/actionlint.yml"
        self.body = self.actionlint_yml.read_text(encoding="utf-8")

    def test_job_name_hard_fail(self) -> None:
        """Job name reflects post-Phase-4 hard-fail mode."""
        self.assertIn(
            "actionlint static analysis (hard-fail)",
            self.body,
            "actionlint.yml job name not updated to (hard-fail)",
        )
        self.assertNotIn(
            "actionlint static analysis (soft-fail)",
            self.body,
            "actionlint.yml still has stale (soft-fail) job name",
        )

    def test_install_uses_sha_pinned_1_7_7(self) -> None:
        """Install step uses SHA-pinned vendored release asset 1.7.7."""
        self.assertIn(
            'VERSION="1.7.7"',
            self.body,
            "actionlint.yml install step missing VERSION=1.7.7",
        )
        self.assertIn(
            "023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757",
            self.body,
            "actionlint.yml install step missing SHA-256 expected hash",
        )
        # No more bash <(curl ...) main pattern.
        self.assertNotIn(
            "raw.githubusercontent.com/rhysd/actionlint/main",
            self.body,
            "actionlint.yml still pulls from rhysd/actionlint main branch",
        )
        # Old install pattern: `download-actionlint.bash) 1.7.1`.
        # We assert the literal install-command pattern is gone, not
        # the bare version string (a comment may legitimately mention
        # the old version as historical context).
        self.assertNotIn(
            "download-actionlint.bash) 1.7.1",
            self.body,
            "actionlint.yml still uses the old download-actionlint.bash 1.7.1 pattern",
        )

    def test_summary_text_hard_fail(self) -> None:
        """Summary text matches the post-Phase-4 hard-fail state."""
        self.assertIn(
            "actionlint (hard-fail)",
            self.body,
            "actionlint.yml summary text not updated to (hard-fail)",
        )
        # Obsolete "1 green week" flip target line removed (Phase 4
        # round-1 already flipped).
        self.assertNotIn(
            "Flip target: hard-fail after 1 green week",
            self.body,
            "actionlint.yml still has obsolete 1-green-week flip target",
        )
        self.assertNotIn(
            "soft-fail (continue-on-error: true)",
            self.body,
            "actionlint.yml still has stale soft-fail summary text",
        )


if __name__ == "__main__":
    unittest.main()
