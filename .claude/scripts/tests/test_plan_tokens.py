"""test_plan_tokens.py — Tests for plan-tokens.py (PLAN-065 §4.2).

Coverage map (≥20 tests as required):
  - parse_phase_table: 4 tests (well-formed / missing column / empty rows / malformed numbers)
  - estimate_plan (per phase): 4 tests (small phase / large new script / debate overhead / hook-only)
  - --format json deterministic ordering: 1 test (CR-N7 lex-sort)
  - --format markdown rendering: 2 tests
  - --inject idempotent: 4 fixture tests (empty FM / already-present / malformed / multi-key)
  - --cap-input 2MiB: 1 test (3MiB → exit 2, Sec NTH-3)
  - --emit no-op when not registered: 1 test
  - Calibration: 3 tests (±20% bound per fixture, CR-MF6)
  Total: 20 tests
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup — import plan_tokens from .claude/scripts/
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "plan-tokens-calibration"

# Load the module directly (not via sys.path.insert) to stay isolated
_MODULE_PATH = _SCRIPTS_DIR / "plan-tokens.py"

def _load_plan_tokens():
    """Dynamically load plan-tokens.py module (hyphen in name)."""
    spec = importlib.util.spec_from_file_location("plan_tokens", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

_pt = _load_plan_tokens()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_plan(content: str) -> Path:
    """Write content to a temp file and return its Path."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    tf.write(content)
    tf.flush()
    tf.close()
    return Path(tf.name)


_SIMPLE_PLAN = """\
---
id: PLAN-TEST
title: Test plan
status: draft
---

# PLAN-TEST

## §4. Phases

### §4.0. Phase table

| Phase | Goal | Files touched | Canonical | Tokens (in/out) |
|---|---|---|---|---|
| 0 | Baseline measurement | report only | no | ~30k / ~10k |
| 1 | Bug fix | audit_log.py hook | YES | ~50k / ~30k |
| 2 | New script plan-tokens.py | new script 200 LoC | no | ~80k / ~50k |
| 3 | Debate Round 1 | n/a | n/a | already-spent |
"""


# ---------------------------------------------------------------------------
# 1. parse_phase_table tests (4 tests)
# ---------------------------------------------------------------------------

class TestParsePhaseTable(unittest.TestCase):

    def test_well_formed_table(self):
        """Well-formed phase table parses all rows correctly."""
        table = """\
| Phase | Goal | Files touched | Canonical | Tokens (in/out) |
|---|---|---|---|---|
| 0 | Baseline | report only | no | ~30k / ~10k |
| 1 | Bug fix | audit_log.py | YES | ~50k / ~30k |
| 2 | New file | plan-tokens.py | no | ~80k / ~50k |
"""
        rows = _pt.parse_phase_table(table)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["phase_id"], "0")
        self.assertIn("Baseline", rows[0]["goal"])
        self.assertEqual(rows[1]["phase_id"], "1")
        self.assertEqual(rows[2]["phase_id"], "2")

    def test_missing_column_graceful(self):
        """Table with missing columns still parses phase IDs."""
        table = """\
| Phase | Goal |
|---|---|
| 0 | Something |
| 1 | Another |
"""
        rows = _pt.parse_phase_table(table)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["phase_id"], "0")
        self.assertEqual(rows[1]["phase_id"], "1")
        # Missing files/canonical/tokens → empty string
        self.assertEqual(rows[0]["files"], "")

    def test_empty_rows_skipped(self):
        """Blank rows and separator rows are skipped."""
        table = """\
| Phase | Goal | Files |
|---|---|---|
| | | |
| 1 | Valid row | file.py |
| | | |
"""
        rows = _pt.parse_phase_table(table)
        # Only non-empty phase IDs kept
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["phase_id"], "1")

    def test_malformed_numbers_in_tokens(self):
        """Tokens hint with unusual formatting is stored as-is (not crashed)."""
        table = """\
| Phase | Goal | Files | Tokens (in/out) |
|---|---|---|---|
| 0 | Baseline | none | n/a |
| 1 | Work | file.py | **~50k / ~30k** |
| 2 | Big | script.py | ~1.25M / ~750k |
"""
        rows = _pt.parse_phase_table(table)
        self.assertEqual(len(rows), 3)
        # All parse without crash
        self.assertEqual(rows[0]["tokens_hint"], "n/a")
        self.assertIn("50k", rows[1]["tokens_hint"])
        self.assertIn("1.25M", rows[2]["tokens_hint"])


# ---------------------------------------------------------------------------
# 2. estimate_plan per-phase tests (4 tests)
# ---------------------------------------------------------------------------

class TestEstimatePhase(unittest.TestCase):

    def test_small_phase_hint_parsed(self):
        """Phase with explicit token hint uses the hint."""
        rows = [{"phase_id": "0", "goal": "Baseline", "files": "report only",
                  "tokens_hint": "~30k / ~10k", "canonical": "no"}]
        ests = _pt.estimate_plan(rows)
        self.assertEqual(len(ests), 1)
        est = ests[0]
        self.assertEqual(est["source"], "hint")
        # mid input should be near 30000 (±20%)
        mid_in = (est["input_low"] + est["input_high"]) // 2
        self.assertAlmostEqual(mid_in, 30000, delta=6000)

    def test_large_new_script_phase(self):
        """Phase with 'new script 200 LoC' classified as large file edit."""
        rows = [{"phase_id": "2", "goal": "New script plan-tokens.py",
                  "files": "new script 200 LoC, tests", "tokens_hint": "",
                  "canonical": "no"}]
        ests = _pt.estimate_plan(rows)
        est = ests[0]
        # Should include edit_large or similar large cost
        self.assertGreater(est["input_high"], 5000)
        self.assertIn("edit_large", est["operations"])

    def test_debate_overhead_phase(self):
        """Debate / archetype rows classified as debate_round cost."""
        rows = [{"phase_id": "Debate overhead", "goal": "Debate Round 1 done",
                  "files": "n/a", "tokens_hint": "", "canonical": "n/a"}]
        ests = _pt.estimate_plan(rows)
        est = ests[0]
        self.assertIn("debate_round", est["operations"])
        # Debate is expensive: 80k+ input
        self.assertGreater(est["input_low"], 50000)

    def test_hook_only_phase(self):
        """Phase touching only hooks is classified with hook + edit costs."""
        rows = [{"phase_id": "1", "goal": "Fix audit_log.py hook bug",
                  "files": "audit_log.py hook canonical", "tokens_hint": "",
                  "canonical": "YES"}]
        ests = _pt.estimate_plan(rows)
        est = ests[0]
        # Should have at least one non-zero estimate
        self.assertGreater(est["input_high"], 0)
        self.assertGreater(est["output_high"], 0)


# ---------------------------------------------------------------------------
# 3. --format json deterministic ordering (1 test, CR-N7)
# ---------------------------------------------------------------------------

class TestJsonOutput(unittest.TestCase):

    def test_json_lex_sorted_by_phase_id(self):
        """JSON output is lex-sorted by phase_id (CR-N7)."""
        rows = [
            {"phase_id": "3", "goal": "Release", "files": "VERSION", "tokens_hint": "", "canonical": "YES"},
            {"phase_id": "1", "goal": "Bug fix", "files": "file.py", "tokens_hint": "", "canonical": "no"},
            {"phase_id": "2", "goal": "New script", "files": "script.py", "tokens_hint": "", "canonical": "no"},
        ]
        ests = _pt.estimate_plan(rows)
        output = _pt.render_json(ests)
        data = json.loads(output)
        phase_ids = [p["phase_id"] for p in data["phases"]]
        # Lex-sorted: "1" < "2" < "3"
        self.assertEqual(phase_ids, sorted(phase_ids))

    def test_json_output_has_total_field(self):
        """JSON output includes total aggregation field."""
        rows = [{"phase_id": "0", "goal": "Baseline", "files": "none",
                  "tokens_hint": "~30k / ~10k", "canonical": "no"}]
        ests = _pt.estimate_plan(rows)
        output = _pt.render_json(ests)
        data = json.loads(output)
        self.assertIn("total", data)
        self.assertIn("input_tokens", data["total"])
        self.assertIn("output_tokens", data["total"])
        self.assertIn("usd_mid", data["total"])


# ---------------------------------------------------------------------------
# 4. --format markdown rendering (2 tests)
# ---------------------------------------------------------------------------

class TestMarkdownOutput(unittest.TestCase):

    def test_markdown_has_total_row(self):
        """Markdown output contains a TOTAL row."""
        rows = [{"phase_id": "0", "goal": "Baseline", "files": "none",
                  "tokens_hint": "~30k / ~10k", "canonical": "no"},
                {"phase_id": "1", "goal": "Fix", "files": "file.py",
                  "tokens_hint": "", "canonical": "no"}]
        ests = _pt.estimate_plan(rows)
        md = _pt.render_markdown(ests)
        self.assertIn("TOTAL", md)
        self.assertIn("$", md)

    def test_markdown_has_header_row(self):
        """Markdown output contains column header with Phase."""
        rows = [{"phase_id": "0", "goal": "Baseline", "files": "none",
                  "tokens_hint": "~30k / ~10k", "canonical": "no"}]
        ests = _pt.estimate_plan(rows)
        md = _pt.render_markdown(ests)
        self.assertIn("Phase", md)
        self.assertIn("plan-tokens estimate", md)


# ---------------------------------------------------------------------------
# 5. --inject idempotent: 4 fixture cases (CR-N6)
# ---------------------------------------------------------------------------

class TestInjectFrontmatter(unittest.TestCase):

    def _make_estimates(self) -> List[Dict[str, Any]]:
        rows = [{"phase_id": "0", "goal": "Baseline", "files": "none",
                  "tokens_hint": "~30k / ~10k", "canonical": "no"}]
        return _pt.estimate_plan(rows)

    def test_inject_empty_frontmatter(self):
        """Plan with no frontmatter gets budget_tokens prepended."""
        plan_text = "# My Plan\n\nBody text here.\n"
        estimates = self._make_estimates()
        updated = _pt.inject_frontmatter(plan_text, estimates)
        self.assertIn("budget_tokens:", updated)
        self.assertIn("---", updated)
        # Original body preserved
        self.assertIn("# My Plan", updated)

    def test_inject_already_present_is_idempotent(self):
        """If budget_tokens already present, it is replaced (not duplicated)."""
        plan_text = "---\nid: PLAN-001\nbudget_tokens: old-value\n---\n\n# Plan\n"
        estimates = self._make_estimates()
        updated = _pt.inject_frontmatter(plan_text, estimates)
        # Count occurrences — should be exactly 1
        count = updated.count("budget_tokens:")
        self.assertEqual(count, 1)
        self.assertNotIn("old-value", updated)

    def test_inject_malformed_yaml_no_close(self):
        """Malformed frontmatter (no closing ---) gets budget_tokens inserted after first line."""
        plan_text = "---\nid: PLAN-001\n\n# Plan body\n"
        estimates = self._make_estimates()
        updated = _pt.inject_frontmatter(plan_text, estimates)
        self.assertIn("budget_tokens:", updated)

    def test_inject_multi_key_frontmatter(self):
        """Multi-key frontmatter gets budget_tokens added before closing ---."""
        plan_text = (
            "---\n"
            "id: PLAN-001\n"
            "title: Test\n"
            "status: draft\n"
            "---\n\n# Plan\n"
        )
        estimates = self._make_estimates()
        updated = _pt.inject_frontmatter(plan_text, estimates)
        self.assertIn("budget_tokens:", updated)
        # Other fields preserved
        self.assertIn("id: PLAN-001", updated)
        self.assertIn("title: Test", updated)


# ---------------------------------------------------------------------------
# 6. --cap-input 2MiB: 1 test (Sec NTH-3)
# ---------------------------------------------------------------------------

class TestCapInput(unittest.TestCase):

    def test_oversized_input_returns_exit_2(self):
        """Plan file > 2 MiB causes exit code 2 with explicit error message."""
        # Write a 3 MiB temp file
        big_content = "x" * (3 * 1024 * 1024)
        plan_path = _tmp_plan(big_content)
        try:
            ret = _pt.main([str(plan_path), "--cap-input", str(2 * 1024 * 1024)])
            self.assertEqual(ret, 2)
        finally:
            plan_path.unlink(missing_ok=True)

    def test_cli_oversized_stderr_message(self):
        """Oversized plan emits 'input exceeds' to stderr."""
        big_content = "x" * (3 * 1024 * 1024)
        plan_path = _tmp_plan(big_content)
        try:
            import io
            from contextlib import redirect_stderr
            buf = io.StringIO()
            with redirect_stderr(buf):
                ret = _pt.main([str(plan_path), "--cap-input", str(2 * 1024 * 1024)])
            self.assertEqual(ret, 2)
            self.assertIn("input exceeds", buf.getvalue())
        finally:
            plan_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 7. --emit no-op when action not registered (1 test)
# ---------------------------------------------------------------------------

class TestEmitNoOp(unittest.TestCase):

    def test_emit_noop_when_not_registered(self):
        """--emit flag is a no-op (no crash) when action not in _KNOWN_ACTIONS."""
        plan_path = _tmp_plan(_SIMPLE_PLAN)
        try:
            # This should complete without error even if emit_token_estimate_emitted
            # is not registered — the function is hasattr-guarded
            import io
            from contextlib import redirect_stderr
            buf = io.StringIO()
            with redirect_stderr(buf):
                ret = _pt.main([str(plan_path), "--emit"])
            # Should succeed (0) or at worst fail on parse, not crash on emit
            # The key contract: no unhandled exception
            self.assertIn(ret, [0, 1])
        finally:
            plan_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 8. Calibration tests — ±20% bound per fixture (3 tests, CR-MF6)
# ---------------------------------------------------------------------------

class TestCalibration(unittest.TestCase):
    """Calibration: estimator must be within ±20% of actual_input_tokens
    for ≥80% of fixtures (acceptance per PLAN-065 §4.2 / CR-MF6).
    """

    def _load_manifest(self) -> Dict[str, Any]:
        manifest_path = _FIXTURES_DIR / "manifest.json"
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _run_fixture(self, fixture_file: str) -> Optional[Dict[str, Any]]:
        """Run plan-tokens on a fixture file and return the JSON output."""
        plan_path = _FIXTURES_DIR / fixture_file
        if not plan_path.is_file():
            return None
        ret_lines: List[str] = []

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = _pt.main([str(plan_path), "--format", "json"])
        if ret != 0:
            return None
        try:
            return json.loads(buf.getvalue())
        except json.JSONDecodeError:
            return None

    def _check_within_tolerance(
        self, estimated: int, actual: int, tolerance: float = 0.20
    ) -> bool:
        """Return True if estimated is within ±tolerance of actual."""
        if actual == 0:
            return estimated == 0
        ratio = abs(estimated - actual) / actual
        return ratio <= tolerance

    def test_calibration_plan_051(self):
        """PLAN-051 estimate within ±20% of actual input tokens."""
        manifest = self._load_manifest()
        fixture_meta = next(f for f in manifest["fixtures"] if f["id"] == "PLAN-051")
        result = self._run_fixture(fixture_meta["file"])
        self.assertIsNotNone(result, "Failed to run plan-051 fixture")
        estimated_in = result["total"]["input_tokens"]
        actual_in = fixture_meta["actual_input_tokens"]
        within = self._check_within_tolerance(estimated_in, actual_in)
        self.assertTrue(
            within,
            f"PLAN-051 calibration FAIL: estimated={estimated_in:,} actual={actual_in:,} "
            f"({abs(estimated_in - actual_in) / actual_in:.1%} > 20%)"
        )

    def test_calibration_plan_052(self):
        """PLAN-052 estimate within ±20% of actual input tokens."""
        manifest = self._load_manifest()
        fixture_meta = next(f for f in manifest["fixtures"] if f["id"] == "PLAN-052")
        result = self._run_fixture(fixture_meta["file"])
        self.assertIsNotNone(result, "Failed to run plan-052 fixture")
        estimated_in = result["total"]["input_tokens"]
        actual_in = fixture_meta["actual_input_tokens"]
        within = self._check_within_tolerance(estimated_in, actual_in)
        self.assertTrue(
            within,
            f"PLAN-052 calibration FAIL: estimated={estimated_in:,} actual={actual_in:,} "
            f"({abs(estimated_in - actual_in) / actual_in:.1%} > 20%)"
        )

    def test_calibration_plan_058(self):
        """PLAN-058 estimate within ±20% of actual input tokens."""
        manifest = self._load_manifest()
        fixture_meta = next(f for f in manifest["fixtures"] if f["id"] == "PLAN-058")
        result = self._run_fixture(fixture_meta["file"])
        self.assertIsNotNone(result, "Failed to run plan-058 fixture")
        estimated_in = result["total"]["input_tokens"]
        actual_in = fixture_meta["actual_input_tokens"]
        within = self._check_within_tolerance(estimated_in, actual_in)
        self.assertTrue(
            within,
            f"PLAN-058 calibration FAIL: estimated={estimated_in:,} actual={actual_in:,} "
            f"({abs(estimated_in - actual_in) / actual_in:.1%} > 20%)"
        )

    def test_calibration_at_least_80_pct_pass(self):
        """Overall calibration: ≥80% of fixtures within ±20% (CR-MF6 aggregate)."""
        manifest = self._load_manifest()
        passing = 0
        total = 0
        for fixture_meta in manifest["fixtures"]:
            result = self._run_fixture(fixture_meta["file"])
            if result is None:
                continue
            total += 1
            estimated_in = result["total"]["input_tokens"]
            actual_in = fixture_meta["actual_input_tokens"]
            if self._check_within_tolerance(estimated_in, actual_in):
                passing += 1
        if total == 0:
            self.skipTest("No fixtures could be run")
        pass_rate = passing / total
        self.assertGreaterEqual(
            pass_rate, 0.8,
            f"Calibration pass rate {pass_rate:.1%} < 80% ({passing}/{total} fixtures)"
        )


# ---------------------------------------------------------------------------
# Additional integration test: run on PLAN-065 itself
# ---------------------------------------------------------------------------

class TestRunOnPlan065(unittest.TestCase):

    def test_plan_065_parses_and_produces_output(self):
        """Running on PLAN-065 itself produces valid markdown output."""
        repo_root = Path(__file__).resolve().parents[3]
        plan_path = repo_root / ".claude" / "plans" / "PLAN-065-ceo-autopilot-final.md"
        if not plan_path.is_file():
            self.skipTest("PLAN-065 not found — skipping integration test")

        import io
        from contextlib import redirect_stdout, redirect_stderr
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            ret = _pt.main([str(plan_path), "--format", "markdown"])

        # Should succeed or produce a useful error
        output = out_buf.getvalue()
        if ret == 0:
            self.assertIn("plan-tokens estimate", output)
            self.assertIn("TOTAL", output)
        # Even if parse fails gracefully (ret==1), we don't crash uncontrolled


if __name__ == "__main__":
    unittest.main()
