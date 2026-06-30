"""Tests for the governance-waivers.yaml awk range parser.

PLAN-063 Phase 5b — DIM-20 #2 follow-up. The Phase 4 round-1 ceremony
consolidated `rc-hold-waivers.yaml` (flat list) into
`governance-waivers.yaml` (two top-level keys: `rc_hold:` and
`workflow_staleness:`). The release.yml gate parses each section via
awk:

    # OLD (broken): start pattern also matches end pattern, range
    # collapses to 1 line — all waivers silently fail the lookup.
    awk '/^rc_hold:/,/^[a-z_]+:/'

    # NEW (fixed): flag-based parser; flag set on start, cleared on
    # SUBSEQUENT match of the end pattern, prints lines while flag set.
    awk '/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f'

These tests cover the AWK PATTERN itself (run via subprocess so any
awk implementation is tested in situ) plus regression cases for each
known shape of governance-waivers.yaml.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from textwrap import dedent

import sys

_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


# The awk pattern under test, copied verbatim from the ceremony patch
# applied to release.yml line 87 + 291. Test failure here is a signal
# that release.yml needs to be re-aligned with this fix.
AWK_RC_HOLD = (
    r"/^rc_hold:/{f=1; next} f && /^[a-z_]+:/{f=0} f"
)
AWK_WORKFLOW_STALENESS = (
    r"/^workflow_staleness:/{f=1; next} f && /^[a-z_]+:/{f=0} f"
)


def _run_awk(pattern: str, text: str) -> str:
    """Run `awk '<pattern>'` against text via subprocess; return stdout."""
    result = subprocess.run(
        ["awk", pattern],
        input=text,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise AssertionError(f"awk failed: {result.stderr}")
    return result.stdout


def _make_waivers_yaml(versions: list) -> str:
    """Build a minimal governance-waivers.yaml shape (both sections)."""
    parts = ["# header comment\n", "\n", "rc_hold:\n"]
    for v in versions:
        parts.append(f"  - version: {v}\n")
        parts.append(f'    reason: "test reason for {v}"\n')
        parts.append(f'    authorized_by: "test"\n')
        parts.append(f"    authorized_at: 2026-04-30\n")
    parts.append("\n")
    parts.append("workflow_staleness:\n")
    for v in versions:
        parts.append(f"  - version: {v}\n")
        parts.append(f'    reason: "test reason for {v}"\n')
        parts.append(f'    authorized_by: "test"\n')
        parts.append(f"    authorized_at: 2026-04-30\n")
    return "".join(parts)


class TestAwkRangeGate(TestEnvContext):
    """Regression coverage for the rc_hold / workflow_staleness awk gates."""

    def test_rc_hold_range_includes_all_entries(self) -> None:
        """NEW awk parser captures all rc_hold entries between header
        and the next top-level key. Old buggy parser captured only 1."""
        yaml = _make_waivers_yaml(["1.0.0", "1.1.0", "1.11.5-rc.1"])
        out = _run_awk(AWK_RC_HOLD, yaml)
        # Should include all 3 version entries.
        self.assertIn("- version: 1.0.0", out)
        self.assertIn("- version: 1.1.0", out)
        self.assertIn("- version: 1.11.5-rc.1", out)
        # Should NOT include workflow_staleness header (terminator).
        self.assertNotIn("workflow_staleness:", out)

    def test_workflow_staleness_range_includes_all_entries(self) -> None:
        yaml = _make_waivers_yaml(["1.0.0", "1.11.5-rc.1"])
        out = _run_awk(AWK_WORKFLOW_STALENESS, yaml)
        self.assertIn("- version: 1.0.0", out)
        self.assertIn("- version: 1.11.5-rc.1", out)
        # Should NOT spill into the rc_hold section (it's BEFORE
        # workflow_staleness, so the start match is later in the file).

    def test_old_buggy_awk_collapses_to_one_line(self) -> None:
        """Regression evidence: the OLD pattern that shipped in Phase 4
        round-1 ceremony degenerates because start pattern also matches
        end pattern. Documents the bug this fix addresses."""
        yaml = _make_waivers_yaml(["1.0.0"])
        # The OLD buggy pattern.
        old_pattern = r"/^rc_hold:/,/^[a-z_]+:/"
        out = _run_awk(old_pattern, yaml)
        # Old buggy: yields ONLY the rc_hold: header — entries are lost.
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(lines, ["rc_hold:"])

    def test_grep_match_after_awk_extraction_finds_version(self) -> None:
        """End-to-end mimicking release.yml line 87 lookup."""
        yaml = _make_waivers_yaml(["1.11.5-rc.1"])
        section = _run_awk(AWK_RC_HOLD, yaml)
        # release.yml uses: grep -qE "^[[:space:]]*-[[:space:]]*version:[[:space:]]*${VERSION}[[:space:]]*$"
        # Verify a literal-version match works.
        result = subprocess.run(
            ["grep", "-qE",
             r"^[[:space:]]*-[[:space:]]*version:[[:space:]]*1\.11\.5-rc\.1[[:space:]]*$"],
            input=section,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"grep failed: section={section!r}")

    def test_partial_version_match_does_not_false_positive(self) -> None:
        """Regression: ensure the grep anchor `$` prevents partial match
        (e.g. "1.11" should not match "1.11.5-rc.1")."""
        yaml = _make_waivers_yaml(["1.11.5-rc.1"])
        section = _run_awk(AWK_RC_HOLD, yaml)
        result = subprocess.run(
            ["grep", "-qE",
             r"^[[:space:]]*-[[:space:]]*version:[[:space:]]*1\.11[[:space:]]*$"],
            input=section,
            capture_output=True,
            text=True,
        )
        # "1.11" is NOT a literal version in our test fixture.
        self.assertNotEqual(
            result.returncode, 0,
            f"unexpected partial match: section={section!r}",
        )

    def test_real_governance_waivers_yaml_parseable(self) -> None:
        """The real governance-waivers.yaml at canonical path parses
        cleanly under the NEW awk pattern. Both sections yield content."""
        repo_root = Path(__file__).resolve().parents[3]
        yaml_path = (
            repo_root / ".claude/governance/governance-waivers.yaml"
        )
        if not yaml_path.is_file():
            self.skipTest(f"governance-waivers.yaml not at {yaml_path}")
        text = yaml_path.read_text(encoding="utf-8")

        rc_hold_out = _run_awk(AWK_RC_HOLD, text)
        ws_out = _run_awk(AWK_WORKFLOW_STALENESS, text)

        # Each section should have at least 4 lines of content (one complete
        # bootstrap entry: version + reason/authorized_by/authorized_at).
        self.assertGreaterEqual(len(rc_hold_out.splitlines()), 4,
                           "rc_hold section unexpectedly short")
        self.assertGreaterEqual(len(ws_out.splitlines()), 4,
                           "workflow_staleness section unexpectedly short")

        # Sanity: rc_hold section should NOT include workflow_staleness:
        self.assertNotIn("workflow_staleness:", rc_hold_out)


if __name__ == "__main__":
    unittest.main()
