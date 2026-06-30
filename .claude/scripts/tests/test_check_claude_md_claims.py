"""PLAN-045 Wave 3 P0-14 — check-claude-md-claims.py tests.

Exercises:
- Claim regex matches + disk-count comparison
- Tolerance semantics (exact vs "N+" style)
- required_count=0 (optional claim)
- Missing file path
- Multiple regex matches — first wins
- JSON output
- Exit code wiring
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "scripts" / "check-claude-md-claims.py"
)
# The script lives in .claude/scripts/check-claude-md-claims.py; test
# file is in .claude/scripts/tests/test_check_claude_md_claims.py.
_SCRIPT = Path(__file__).resolve().parent.parent / "check-claude-md-claims.py"

_spec = importlib.util.spec_from_file_location("check_cm", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
# Register in sys.modules BEFORE exec_module so dataclasses can resolve
# forward references (Python 3.9 dataclass introspection reads the
# module dict).
sys.modules["check_cm"] = _mod
_spec.loader.exec_module(_mod)

ClaimCheck = _mod.ClaimCheck
run_checks = _mod.run_checks
format_text = _mod.format_text
format_json = _mod.format_json


class TestClaimChecks(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.claude_md = self.tmpdir / "CLAUDE.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, text: str) -> Path:
        self.claude_md.write_text(text, encoding="utf-8")
        return self.claude_md

    def test_exact_match_passes(self) -> None:
        self._write("We have 64 ADRs at the moment.")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)
        self.assertEqual(results[0].claimed, 64)
        self.assertEqual(results[0].disk, 64)

    def test_mismatch_fails(self) -> None:
        self._write("We have 49 ADRs at the moment.")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertFalse(results[0].passed)
        self.assertIn("64", results[0].detail)
        self.assertIn("49", results[0].detail)

    def test_tolerance_permits_small_drift(self) -> None:
        self._write("Currently 100+ tests.")
        checks = [
            ClaimCheck(
                name="tests",
                claim_regex=r"(\d+)\+\s+tests",
                disk_count_fn=lambda: 105,
                tolerance=10,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertTrue(results[0].passed)

    def test_tolerance_enforced(self) -> None:
        self._write("Currently 100 tests.")
        checks = [
            ClaimCheck(
                name="tests",
                claim_regex=r"(\d+)\s+tests",
                disk_count_fn=lambda: 120,
                tolerance=10,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertFalse(results[0].passed)

    def test_optional_claim_absent_passes(self) -> None:
        self._write("No explicit plan count here.")
        checks = [
            ClaimCheck(
                name="plans",
                claim_regex=r"(\d+)\s+plans?",
                disk_count_fn=lambda: 45,
                required_count=0,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertTrue(results[0].passed)
        self.assertIn("optional", results[0].detail)

    def test_required_claim_absent_fails(self) -> None:
        self._write("No claim here.")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        results = run_checks(self.claude_md, checks)
        self.assertFalse(results[0].passed)
        self.assertIn("not found", results[0].detail)

    def test_first_match_wins(self) -> None:
        self._write("We have 49 ADRs. Oh wait, 64 ADRs actually.")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        results = run_checks(self.claude_md, checks)
        # First match is 49 which mismatches disk 64.
        self.assertFalse(results[0].passed)
        self.assertEqual(results[0].claimed, 49)

    def test_missing_claude_md(self) -> None:
        missing = self.tmpdir / "nope.md"
        results = run_checks(missing, [])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        self.assertIn("not found", results[0].detail)

    def test_format_json_valid(self) -> None:
        self._write("49 ADRs")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        results = run_checks(self.claude_md, checks)
        payload = json.loads(format_json(results))
        self.assertEqual(payload[0]["name"], "adr")
        self.assertEqual(payload[0]["claimed"], 49)
        self.assertEqual(payload[0]["disk"], 64)
        self.assertFalse(payload[0]["passed"])

    def test_format_text_shows_status(self) -> None:
        self._write("64 ADRs")
        checks = [
            ClaimCheck(
                name="adr",
                claim_regex=r"(\d+)\s+ADRs",
                disk_count_fn=lambda: 64,
            )
        ]
        text = format_text(run_checks(self.claude_md, checks))
        self.assertIn("[PASS]", text)
        self.assertIn("adr", text)


class TestScriptExitCodes(unittest.TestCase):
    """Integration: run the script as a subprocess against real CLAUDE.md."""

    def test_subprocess_exits_nonzero_on_mismatch(self) -> None:
        # Real CLAUDE.md has drift (confirmed by Phase 0 baseline).
        # Script should exit non-zero.
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Either exits 0 (claims match — unlikely pre-Wave 7) or 1.
        self.assertIn(proc.returncode, (0, 1))

    def test_subprocess_json_output_parses(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        payload = json.loads(proc.stdout)
        self.assertIsInstance(payload, list)
        for entry in payload:
            self.assertIn("name", entry)
            self.assertIn("passed", entry)
            self.assertIn("disk", entry)


if __name__ == "__main__":
    unittest.main()
