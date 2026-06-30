"""Unit tests for debate-converge.py CLI + compute_convergence API.

PLAN-011 Phase 5 (M1 anti-groupthink gate). Tests cover:

- Jaccard arithmetic (symmetry, identity, empty sets, disjoint sets)
- Threshold boundary at 0.7
- Normalization: ID prefix stripping, punctuation, whitespace
- Red-team flag semantics (red_team_needed iff converged AND round <= 2)
- Fixture-based end-to-end for converged / not-converged / partial-overlap
- CLI exit codes + JSON output shape
- Plan ID validation + bad-args rejection
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_SCRIPT = _SCRIPTS / "debate-converge.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "debate_convergence"

_spec = importlib.util.spec_from_file_location("debate_converge", _SCRIPT)
assert _spec is not None and _spec.loader is not None
dc = importlib.util.module_from_spec(_spec)
# Register module in sys.modules BEFORE exec so @dataclass annotation
# resolution (Python 3.9 _is_type) can look it up during class build.
sys.modules["debate_converge"] = dc
_spec.loader.exec_module(dc)


def _fixture_plans_root_from(fixture_name: str) -> Path:
    """Copy a fixture into a tempdir shaped as .claude/plans/PLAN-NNN/debate.

    Returns the tempdir path to use as --plans-root.
    """
    src = _FIXTURES / fixture_name
    tmp = Path(tempfile.mkdtemp(prefix=f"converge-test-{fixture_name}-"))
    # Shape: tmp/PLAN-999/debate/round-1/*  tmp/PLAN-999/debate/round-2/*
    target_base = tmp / "PLAN-999" / "debate"
    target_base.mkdir(parents=True)
    for sub in src.iterdir():
        if sub.is_dir() and sub.name.startswith("round-"):
            shutil.copytree(sub, target_base / sub.name)
    return tmp


class TestJaccardMath(unittest.TestCase):

    def test_identity_returns_one(self):
        s = {"a", "b", "c"}
        self.assertEqual(dc.jaccard(s, s), 1.0)

    def test_disjoint_sets_return_zero(self):
        self.assertEqual(dc.jaccard({"a"}, {"b"}), 0.0)

    def test_empty_both_returns_one(self):
        # Convention: no evidence of divergence
        self.assertEqual(dc.jaccard(set(), set()), 1.0)

    def test_empty_one_returns_zero(self):
        self.assertEqual(dc.jaccard({"a"}, set()), 0.0)
        self.assertEqual(dc.jaccard(set(), {"a"}), 0.0)

    def test_symmetry(self):
        a = {"alpha", "beta"}
        b = {"beta", "gamma"}
        self.assertEqual(dc.jaccard(a, b), dc.jaccard(b, a))

    def test_half_overlap_is_point_three_three(self):
        # {a,b} vs {b,c} -> 1/3
        self.assertAlmostEqual(dc.jaccard({"a", "b"}, {"b", "c"}), 1.0 / 3.0, places=6)


class TestNormalizeRisk(unittest.TestCase):

    def test_strip_id_prefix_then_match(self):
        # Same substance, different ID prefix -> same normalized form
        a = dc._normalize_risk("R-VP1: token logging leaks credentials")
        b = dc._normalize_risk("R-SEC2 - token logging leaks credentials")
        self.assertEqual(a, b)

    def test_punctuation_stripped(self):
        a = dc._normalize_risk("Missing rate-limit!!!")
        b = dc._normalize_risk("missing rate limit")
        self.assertEqual(a, b)

    def test_whitespace_collapsed(self):
        a = dc._normalize_risk("foo   bar\t\tbaz")
        b = dc._normalize_risk("foo bar baz")
        self.assertEqual(a, b)


class TestExtractRisks(unittest.TestCase):

    def test_extract_simple_risks(self):
        md = """## Summary

- Not a risk

## Risks

- R-A1 — HIGH — something
- R-A2 — MEDIUM — other

## Must-fix

- This is a must-fix item not a risk
"""
        risks = dc.extract_risks(md)
        self.assertEqual(len(risks), 2)
        # Both normalized, no bullet dash/ID leaked
        for r in risks:
            self.assertFalse(r.startswith("r-"))

    def test_no_risks_section_yields_empty(self):
        md = "## Summary\n\n- just a note\n"
        self.assertEqual(dc.extract_risks(md), [])

    def test_risks_closes_on_next_heading(self):
        md = "## Risks\n\n- one\n- two\n\n## Other\n\n- three\n"
        risks = dc.extract_risks(md)
        self.assertEqual(len(risks), 2)
        # 'three' is under ## Other, not Risks
        self.assertFalse(any("three" in r for r in risks))


class TestFixtureBased(unittest.TestCase):

    def tearDown(self):
        pass

    def test_converged_pair_hits_threshold(self):
        root = _fixture_plans_root_from("converged-pair-1")
        try:
            result = dc.compute_convergence(root, "PLAN-999", 2, threshold=0.7)
            self.assertGreaterEqual(result["jaccard"], 0.7)
            self.assertTrue(result["converged"])
            # round 2 <= 2 AND converged -> red_team_needed
            self.assertTrue(result["red_team_needed"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_not_converged_pair_below_threshold(self):
        root = _fixture_plans_root_from("not-converged-pair-1")
        try:
            result = dc.compute_convergence(root, "PLAN-999", 2, threshold=0.7)
            self.assertLess(result["jaccard"], 0.7)
            self.assertFalse(result["converged"])
            self.assertFalse(result["red_team_needed"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_partial_overlap_below_threshold(self):
        # Round-1 {R1,R2,R3} vs round-2 {R1,R2,R4,R5} -> |inter|=2 |union|=5 -> 0.4
        root = _fixture_plans_root_from("partial-overlap")
        try:
            result = dc.compute_convergence(root, "PLAN-999", 2, threshold=0.7)
            self.assertAlmostEqual(result["jaccard"], 2.0 / 5.0, places=3)
            self.assertFalse(result["converged"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestRedTeamGateSemantics(unittest.TestCase):
    """red_team_needed = converged AND round <= 2."""

    def _make_min_tree(self, tmp: Path, round_num: int, risks: list) -> None:
        """Create round-1 and round-N directories with identical risks."""
        base = tmp / "PLAN-999" / "debate"
        for r in range(1, round_num + 1):
            d = base / f"round-{r}"
            d.mkdir(parents=True, exist_ok=True)
            bullets = "\n".join(f"- {x}" for x in risks)
            (d / "a.md").write_text(
                f"## Risks\n\n{bullets}\n", encoding="utf-8"
            )

    def test_converged_at_round_2_triggers_red_team(self):
        tmp = Path(tempfile.mkdtemp(prefix="rt-gate-"))
        try:
            self._make_min_tree(tmp, 2, ["risk one", "risk two", "risk three"])
            result = dc.compute_convergence(tmp, "PLAN-999", 2, threshold=0.7)
            self.assertEqual(result["jaccard"], 1.0)
            self.assertTrue(result["converged"])
            self.assertTrue(result["red_team_needed"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_converged_at_round_3_does_not_trigger_red_team(self):
        tmp = Path(tempfile.mkdtemp(prefix="rt-gate-r3-"))
        try:
            self._make_min_tree(tmp, 3, ["risk a", "risk b"])
            result = dc.compute_convergence(tmp, "PLAN-999", 3, threshold=0.7)
            self.assertTrue(result["converged"])
            # round > 2 -> red_team_needed=False even though converged=True
            self.assertFalse(result["red_team_needed"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_threshold_boundary_exact_0_7(self):
        # Build a 7/10 overlap: 7 shared + 3 unique each side -> Jaccard = 7/13 ~= 0.538
        # Easier: 7 shared + 0 unique -> 1.0; craft 7 shared + 3 unique in one to get 0.7.
        # 7 shared, 3 unique in round-2 only: |inter|=7 |union|=10 -> 0.7 exact.
        tmp = Path(tempfile.mkdtemp(prefix="rt-boundary-"))
        try:
            base = tmp / "PLAN-999" / "debate"
            r1 = base / "round-1"
            r1.mkdir(parents=True)
            shared = [f"shared risk {i}" for i in range(7)]
            (r1 / "a.md").write_text(
                "## Risks\n\n"
                + "\n".join(f"- {s}" for s in shared)
                + "\n",
                encoding="utf-8",
            )
            r2 = base / "round-2"
            r2.mkdir(parents=True)
            unique = [f"unique r2 {i}" for i in range(3)]
            (r2 / "a.md").write_text(
                "## Risks\n\n"
                + "\n".join(f"- {s}" for s in shared + unique)
                + "\n",
                encoding="utf-8",
            )
            result = dc.compute_convergence(tmp, "PLAN-999", 2, threshold=0.7)
            self.assertAlmostEqual(result["jaccard"], 0.7, places=3)
            self.assertTrue(result["converged"])  # >= 0.7 is converged
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestCLI(unittest.TestCase):
    """CLI JSON output + exit codes."""

    def test_cli_prints_json_on_success(self):
        root = _fixture_plans_root_from("converged-pair-1")
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = dc.main(
                    [
                        "--plan",
                        "PLAN-999",
                        "--round",
                        "2",
                        "--plans-root",
                        str(root),
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue())
            self.assertIn("jaccard", out)
            self.assertIn("converged", out)
            self.assertIn("red_team_needed", out)
            self.assertTrue(out["red_team_needed"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_cli_bad_plan_format_rejects(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = dc.main(["--plan", "notaplan", "--round", "2"])
        self.assertEqual(rc, 1)

    def test_cli_round_less_than_2_rejects(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = dc.main(["--plan", "PLAN-999", "--round", "1"])
        self.assertEqual(rc, 1)

    def test_cli_missing_round_returns_error(self):
        tmp = Path(tempfile.mkdtemp(prefix="cli-missing-"))
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                rc = dc.main(
                    [
                        "--plan",
                        "PLAN-999",
                        "--round",
                        "2",
                        "--plans-root",
                        str(tmp),
                    ]
                )
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cli_custom_threshold(self):
        # With threshold=1.0, anything < 1.0 won't converge even if high-overlap
        root = _fixture_plans_root_from("converged-pair-1")
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = dc.main(
                    [
                        "--plan",
                        "PLAN-999",
                        "--round",
                        "2",
                        "--plans-root",
                        str(root),
                        "--threshold",
                        "1.0",
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue())
            self.assertEqual(out["threshold"], 1.0)
            # 1.0 threshold: strictly identical sets -> converged=True; our
            # converged-pair has slightly different R1 vs R2 risk sets, so < 1.0.
            self.assertFalse(out["converged"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestMaxRoundsHardStop(unittest.TestCase):
    """MAX_ROUNDS=5 hard stop — PLAN-012 Phase 1 D3.5 + chaos CRITICAL-2."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="maxr-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, highest: int, risks=None) -> None:
        """Populate round-1..N; risks=None -> per-round unique (Jaccard=0)."""
        base = self.tmp / "PLAN-999" / "debate"
        for r in range(1, highest + 1):
            d = base / f"round-{r}"
            d.mkdir(parents=True, exist_ok=True)
            body = ("\n".join(f"- {x}" for x in risks) + "\n"
                    if risks is not None else f"- unique risk round {r}\n")
            (d / "a.md").write_text(f"## Risks\n\n{body}", encoding="utf-8")

    def test_module_exports_max_rounds_constant(self):
        self.assertTrue(hasattr(dc, "MAX_ROUNDS"))
        self.assertEqual(dc.MAX_ROUNDS, 5)

    def test_max_rounds_reached_at_round_5_returns_true(self):
        self._seed(5)
        r = dc.compute_convergence(self.tmp, "PLAN-999", 5, threshold=0.7)
        self.assertTrue(r["max_rounds_reached"])
        self.assertEqual(r["outcome"], "max_rounds_reached")
        self.assertFalse(r["convergence_met"])
        self.assertFalse(r["converged"])
        self.assertEqual(r["round_number"], 5)

    def test_max_rounds_not_reached_at_round_4(self):
        self._seed(4)
        r = dc.compute_convergence(self.tmp, "PLAN-999", 4, threshold=0.7)
        self.assertFalse(r["max_rounds_reached"])
        self.assertEqual(r["outcome"], "diverged")
        self.assertEqual(r["round_number"], 4)

    def test_max_rounds_overrides_jaccard(self):
        # Identical risks -> Jaccard=1.0 but terminal outcome wins.
        self._seed(5, ["alpha", "beta", "gamma"])
        r = dc.compute_convergence(self.tmp, "PLAN-999", 5, threshold=0.7)
        self.assertEqual(r["jaccard_score"], 1.0)
        self.assertEqual(r["jaccard"], 1.0)
        self.assertTrue(r["max_rounds_reached"])
        self.assertEqual(r["outcome"], "max_rounds_reached")
        self.assertFalse(r["convergence_met"])
        self.assertFalse(r["converged"])
        self.assertFalse(r["red_team_needed"])

    def test_convergence_at_round_3_before_max(self):
        self._seed(3, ["r1", "r2", "r3"])
        r = dc.compute_convergence(self.tmp, "PLAN-999", 3, threshold=0.7)
        self.assertFalse(r["max_rounds_reached"])
        self.assertEqual(r["outcome"], "converged")
        self.assertTrue(r["convergence_met"])
        self.assertTrue(r["converged"])

    def test_cli_exit_code_3_on_max_rounds(self):
        self._seed(5)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dc.main(["--plan", "PLAN-999", "--round", "5",
                          "--plans-root", str(self.tmp)])
        self.assertEqual(rc, 3)
        out = json.loads(buf.getvalue())
        self.assertTrue(out["max_rounds_reached"])
        self.assertEqual(out["outcome"], "max_rounds_reached")


if __name__ == "__main__":
    unittest.main()
