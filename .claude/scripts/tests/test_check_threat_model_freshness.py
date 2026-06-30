"""Tests for check-threat-model-freshness.py — PLAN-014 Phase C.4.

>=8 unit tests covering: date parsing, status parsing, ADR counting,
status flipping, CLI exit codes, edge cases.

Stdlib only. TestEnvContext for isolation. Python 3.9+.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Bootstrap: make the script importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# Import the module under test — use importlib to handle the hyphenated filename
import importlib.util

_SCRIPT_PATH = _SCRIPTS_DIR / "check-threat-model-freshness.py"
_spec = importlib.util.spec_from_file_location(
    "check_threat_model_freshness", str(_SCRIPT_PATH)
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_mod)  # type: ignore

parse_last_updated = _mod.parse_last_updated
parse_status = _mod.parse_status
is_adr_superseded = _mod.is_adr_superseded
count_new_adrs_since = _mod.count_new_adrs_since
flip_status_to_stale = _mod.flip_status_to_stale
main = _mod.main


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParsing(TestEnvContext):
    """Parser unit tests for the freshness checker."""

    def test_parse_last_updated_present(self) -> None:
        content = "**Last updated:** 2026-04-15\n**Date:** 2026-04-10"
        result = parse_last_updated(content)
        self.assertEqual(result, date(2026, 4, 15))

    def test_parse_last_updated_fallback_to_date(self) -> None:
        content = "**Status:** accepted\n**Date:** 2026-03-01"
        result = parse_last_updated(content)
        self.assertEqual(result, date(2026, 3, 1))

    def test_parse_last_updated_missing(self) -> None:
        content = "# No date here\nJust text."
        result = parse_last_updated(content)
        self.assertIsNone(result)

    def test_parse_status_accepted(self) -> None:
        content = "**Status:** accepted\n**Date:** 2026-04-15"
        self.assertEqual(parse_status(content), "accepted")

    def test_parse_status_stale(self) -> None:
        content = "**Status:** stale\n"
        self.assertEqual(parse_status(content), "stale")

    def test_parse_status_draft(self) -> None:
        content = "**Status:** draft (PLAN-013)\n"
        self.assertEqual(parse_status(content), "draft")

    def test_parse_status_missing(self) -> None:
        content = "# Title\nNo status."
        self.assertEqual(parse_status(content), "")


class TestAdrSuperseded(TestEnvContext):
    """Test SUPERSEDED detection."""

    def test_superseded_detected(self) -> None:
        adr_path = self.project_dir / "test-adr.md"
        adr_path.write_text("# ADR-004\n\n**Status:** SUPERSEDED\n")
        self.assertTrue(is_adr_superseded(adr_path))

    def test_non_superseded(self) -> None:
        adr_path = self.project_dir / "test-adr.md"
        adr_path.write_text("# ADR-045\n\n**Status:** PROPOSED\n")
        self.assertFalse(is_adr_superseded(adr_path))

    def test_missing_file(self) -> None:
        adr_path = self.project_dir / "nonexistent.md"
        self.assertFalse(is_adr_superseded(adr_path))


class TestCountNewAdrs(TestEnvContext):
    """Test ADR counting with no-git mode (mtime-based)."""

    def _make_adr_dir(self) -> Path:
        adr_dir = self.project_dir / ".claude" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)
        return adr_dir

    def test_no_adrs_returns_zero(self) -> None:
        self._make_adr_dir()
        count, names = count_new_adrs_since(self.project_dir, date(2020, 1, 1), use_git=False)
        self.assertEqual(count, 0)

    def test_counts_new_adrs_by_mtime(self) -> None:
        adr_dir = self._make_adr_dir()
        # Create ADR files — mtime will be "now" which is after 2020
        (adr_dir / "ADR-045-policy.md").write_text("**Status:** PROPOSED\n")
        (adr_dir / "ADR-046-replay.md").write_text("**Status:** PROPOSED\n")
        count, names = count_new_adrs_since(self.project_dir, date(2020, 1, 1), use_git=False)
        self.assertEqual(count, 2)
        self.assertIn("ADR-045-policy.md", names)

    def test_excludes_superseded(self) -> None:
        adr_dir = self._make_adr_dir()
        (adr_dir / "ADR-004-legacy.md").write_text("**Status:** SUPERSEDED\n")
        (adr_dir / "ADR-045-policy.md").write_text("**Status:** PROPOSED\n")
        count, names = count_new_adrs_since(self.project_dir, date(2020, 1, 1), use_git=False)
        self.assertEqual(count, 1)
        self.assertNotIn("ADR-004-legacy.md", names)


class TestFlipStatus(TestEnvContext):
    """Test the status-flip mechanism."""

    def _write_threat_model(self, content: str) -> None:
        docs = self.project_dir / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "threat-model.md").write_text(content)

    def test_flip_accepted_to_stale(self) -> None:
        self._write_threat_model("**Status:** accepted\n**Date:** 2026-04-15\n")
        result = flip_status_to_stale(self.project_dir)
        self.assertTrue(result)
        new_content = (self.project_dir / "docs" / "threat-model.md").read_text()
        self.assertIn("**Status:** stale", new_content)
        self.assertNotIn("**Status:** accepted", new_content)

    def test_flip_noop_on_draft(self) -> None:
        self._write_threat_model("**Status:** draft\n**Date:** 2026-04-15\n")
        result = flip_status_to_stale(self.project_dir)
        self.assertFalse(result)

    def test_flip_noop_on_already_stale(self) -> None:
        self._write_threat_model("**Status:** stale\n**Date:** 2026-04-15\n")
        result = flip_status_to_stale(self.project_dir)
        self.assertFalse(result)

    def test_flip_missing_file(self) -> None:
        result = flip_status_to_stale(self.project_dir)
        self.assertFalse(result)


class TestMainCLI(TestEnvContext):
    """Test the CLI entry point exit codes."""

    def _setup_tm_and_adrs(self, status: str = "accepted", adr_count: int = 0) -> None:
        docs = self.project_dir / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "threat-model.md").write_text(
            f"**Status:** {status}\n**Last updated:** 2020-01-01\n"
        )
        adr_dir = self.project_dir / ".claude" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)
        for i in range(adr_count):
            (adr_dir / f"ADR-{100 + i:03d}-test.md").write_text("**Status:** PROPOSED\n")

    def test_main_exit_0_when_fresh(self) -> None:
        self._setup_tm_and_adrs(status="accepted", adr_count=1)
        rc = main([
            "--repo-root", str(self.project_dir),
            "--no-git",
            "--threshold", "2",
        ])
        self.assertEqual(rc, 0)

    def test_main_exit_1_when_stale(self) -> None:
        self._setup_tm_and_adrs(status="accepted", adr_count=3)
        rc = main([
            "--repo-root", str(self.project_dir),
            "--no-git",
            "--threshold", "2",
        ])
        self.assertEqual(rc, 1)

    def test_main_exit_2_on_missing_file(self) -> None:
        rc = main([
            "--repo-root", str(self.project_dir),
            "--no-git",
        ])
        self.assertEqual(rc, 2)

    def test_main_dry_run_does_not_flip(self) -> None:
        self._setup_tm_and_adrs(status="accepted", adr_count=3)
        rc = main([
            "--repo-root", str(self.project_dir),
            "--no-git",
            "--threshold", "2",
            "--dry-run",
        ])
        self.assertEqual(rc, 1)
        # Status should NOT have been flipped
        content = (self.project_dir / "docs" / "threat-model.md").read_text()
        self.assertIn("**Status:** accepted", content)

    def test_main_skip_on_draft_status(self) -> None:
        self._setup_tm_and_adrs(status="draft", adr_count=5)
        rc = main([
            "--repo-root", str(self.project_dir),
            "--no-git",
            "--verbose",
        ])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
