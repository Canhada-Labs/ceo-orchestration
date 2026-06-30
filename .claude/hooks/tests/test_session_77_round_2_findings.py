"""Tests for PLAN-063 Phase 5 round-2 ceremony — release.yml awk gate fix.

These tests assert the canonical patch LANDED via the Owner-run
`OWNER-SESSION-77-AUDIT-V3-DEEP-REFACTOR-CEREMONY.sh` script. They use
class-level `@unittest.skipUnless` guards (Session 75 lesson #2 —
`skipTest()` in `setUp()` does NOT call `tearDown()` and leaks env
state across tests) so the file is harmless pre-ceremony (skip-by-default)
and becomes hard-fail post-ceremony.

The ceremony script sets `CEO_PHASE_5_77_LANDED=1` BEFORE running
pytest; after it has applied both awk patches (line 87 + 293).
Pre-ceremony (default) the env var is unset, so all tests skip cleanly.

Findings covered (per PLAN-063 round-2 sentinel):
- **DIM-20 #2 follow-up** — release.yml awk range gate degenerate fix.
  OLD pattern `awk '/^rc_hold:/,/^[a-z_]+:/'` collapses to 1 line
  because the start regex also matches the end regex. NEW pattern
  `awk '/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f` is flag-based.
  Same substitution at line 293 for `workflow_staleness:`.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Import TestEnvContext for env-hygiene compliance.
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

# Skip guard — set by ceremony script after both blocks applied.
PHASE_5_LANDED = os.environ.get("CEO_PHASE_5_77_LANDED", "0") == "1"


# ---------------------------------------------------------------------------
# DIM-20 #2 follow-up — release.yml awk gate flag-based parser
# ---------------------------------------------------------------------------


@unittest.skipUnless(PHASE_5_LANDED, "Phase 5 round-2 ceremony not yet landed")
class DIM20AwkGateFix(TestEnvContext):
    """release.yml awk range gate uses flag-based parser at line 87 + 293."""

    def setUp(self) -> None:
        super().setUp()
        self.release_yml = REPO_ROOT / ".github/workflows/release.yml"
        self.release_text = self.release_yml.read_text(encoding="utf-8")

    def test_release_yml_no_legacy_awk_range_pattern(self) -> None:
        """OLD broken `awk '/^rc_hold:/,/^[a-z_]+:/'` removed from release.yml."""
        # The legacy pattern is a 2-regex range expression.
        legacy_rc_hold = "awk '/^rc_hold:/,/^[a-z_]+:/'"
        legacy_ws = "awk '/^workflow_staleness:/,/^[a-z_]+:/'"
        self.assertNotIn(
            legacy_rc_hold, self.release_text,
            "OLD broken awk range pattern (rc_hold) still in release.yml",
        )
        self.assertNotIn(
            legacy_ws, self.release_text,
            "OLD broken awk range pattern (workflow_staleness) still in "
            "release.yml",
        )

    def test_release_yml_uses_flag_based_awk_for_rc_hold(self) -> None:
        """NEW flag-based pattern present at line 87 (rc_hold gate)."""
        # The new pattern unique substring (post-application marker).
        new_pattern = "/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f"
        self.assertIn(
            new_pattern, self.release_text,
            "NEW flag-based awk pattern (rc_hold) missing from release.yml",
        )

    def test_release_yml_uses_flag_based_awk_for_workflow_staleness(
            self) -> None:
        """NEW flag-based pattern present at line 293 (workflow_staleness)."""
        new_pattern = (
            "/^workflow_staleness:/{f=1; next} f && /^[a-z_]+:/{f=0} f"
        )
        self.assertIn(
            new_pattern, self.release_text,
            "NEW flag-based awk pattern (workflow_staleness) missing from "
            "release.yml",
        )

    def test_release_yml_awk_pattern_count_matches_expected(self) -> None:
        """Exactly 2 occurrences of the flag-based pattern (one per gate)."""
        rc_count = self.release_text.count("/^rc_hold:/{f=1; next}")
        ws_count = self.release_text.count(
            "/^workflow_staleness:/{f=1; next}"
        )
        self.assertEqual(
            rc_count, 1,
            f"expected 1 rc_hold flag-based awk, found {rc_count}",
        )
        self.assertEqual(
            ws_count, 1,
            f"expected 1 workflow_staleness flag-based awk, found {ws_count}",
        )

    def test_real_governance_waivers_yields_entries_via_new_awk(self) -> None:
        """Sanity: the post-ceremony release.yml + canonical waivers
        yield ≥5 lines per section. Catches regression where awk pattern
        is syntactically valid but semantically wrong."""
        import subprocess
        waivers = REPO_ROOT / ".claude/governance/governance-waivers.yaml"
        text = waivers.read_text(encoding="utf-8")

        # Mirror release.yml line 87 logic:
        rc_result = subprocess.run(
            ["awk", "/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f"],
            input=text, capture_output=True, text=True, timeout=5,
        )
        ws_result = subprocess.run(
            ["awk",
             "/^workflow_staleness:/{f=1; next} f && /^[a-z_]+:/{f=0} f"],
            input=text, capture_output=True, text=True, timeout=5,
        )
        rc_lines = [ln for ln in rc_result.stdout.splitlines() if ln.strip()]
        ws_lines = [ln for ln in ws_result.stdout.splitlines() if ln.strip()]

        self.assertGreater(
            len(rc_lines), 5,
            f"rc_hold section unexpectedly short: {rc_lines!r}",
        )
        self.assertGreater(
            len(ws_lines), 5,
            f"workflow_staleness section unexpectedly short: {ws_lines!r}",
        )


if __name__ == "__main__":
    unittest.main()
