"""Unit tests for benchmark-fallback-scorer.py (PLAN-011 Phase 3 / §H7).

Deterministic keyword-match scorer — never calls a real judge.

Covers:
- keyword extraction (stopwords filtered, short tokens dropped)
- weighted-average scoring
- all_or_nothing scoring
- unicode response handling
- empty rubric raises
- output shape matches benchmark-judge (forward + reverse + delta)
- CLI exit codes
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_HOOKS = _SCRIPTS.parent / "hooks"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _load():
    path = _SCRIPTS / "benchmark-fallback-scorer.py"
    spec = importlib.util.spec_from_file_location("benchmark_fallback_scorer", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fs = _load()


class TestKeywordExtraction(TestEnvContext):

    def test_stopwords_filtered(self):
        kws = fs.extract_keywords("the code compiles and has tests")
        self.assertNotIn("the", kws)
        self.assertNotIn("and", kws)
        self.assertNotIn("has", kws)
        self.assertIn("code", kws)
        self.assertIn("compiles", kws)
        self.assertIn("tests", kws)

    def test_short_tokens_dropped(self):
        kws = fs.extract_keywords("a b c de fgh")
        # 'de' is 2 chars, 'fgh' is 3 — only 'fgh' keeps
        self.assertNotIn("a", kws)
        self.assertNotIn("de", kws)
        self.assertIn("fgh", kws)

    def test_case_folded(self):
        kws = fs.extract_keywords("Compiles COMPILES compiles")
        self.assertEqual(kws, ["compiles"])

    def test_empty_input(self):
        self.assertEqual(fs.extract_keywords(""), [])
        self.assertEqual(fs.extract_keywords(None), [])


class TestScoringWeightedAverage(TestEnvContext):

    def test_all_items_match_gives_10(self):
        rubric = {
            "version": 1,
            "rubric_id": "t",
            "items": [
                {"id": "r1", "description": "compiles cleanly", "weight": 0.5},
                {"id": "r2", "description": "passes lint", "weight": 0.5},
            ],
            "scoring": "weighted_average",
        }
        resp = "the code compiles cleanly and passes lint"
        out = fs.score_rubric(rubric, resp)
        self.assertAlmostEqual(out["score"], 10.0, places=1)

    def test_no_items_match_gives_0(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles cleanly", "weight": 1.0},
            ],
            "scoring": "weighted_average",
        }
        resp = "entirely unrelated text about cats"
        out = fs.score_rubric(rubric, resp)
        self.assertEqual(out["score"], 0.0)

    def test_partial_credit(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles and runs tests", "weight": 1.0},
            ],
            "scoring": "weighted_average",
        }
        # "compiles" matches (1/3 keywords); "runs" "tests" do not
        resp = "the code compiles"
        out = fs.score_rubric(rubric, resp)
        self.assertGreater(out["score"], 0.0)
        self.assertLess(out["score"], 10.0)

    def test_weighted_contribution(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles", "weight": 0.9},
                {"id": "r2", "description": "tests", "weight": 0.1},
            ],
            "scoring": "weighted_average",
        }
        # Only the high-weight item matches
        resp = "the code compiles"
        out = fs.score_rubric(rubric, resp)
        # 0.9 weight * 1.0 fraction / 1.0 total = 0.9 → 9.0 on 0..10
        self.assertAlmostEqual(out["score"], 9.0, places=1)


class TestScoringAllOrNothing(TestEnvContext):

    def test_all_match_gives_10(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles", "weight": 0.5},
                {"id": "r2", "description": "tests", "weight": 0.5},
            ],
            "scoring": "all_or_nothing",
        }
        resp = "compiles and tests everything"
        out = fs.score_rubric(rubric, resp)
        self.assertEqual(out["score"], 10.0)

    def test_partial_match_gives_0(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles", "weight": 0.5},
                {"id": "r2", "description": "tests", "weight": 0.5},
            ],
            "scoring": "all_or_nothing",
        }
        resp = "compiles only"
        out = fs.score_rubric(rubric, resp)
        self.assertEqual(out["score"], 0.0)


class TestUnicodeAndEdges(TestEnvContext):

    def test_unicode_response(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles", "weight": 1.0},
            ],
            "scoring": "weighted_average",
        }
        resp = "The code compiles — café naïve résumé 世界"
        out = fs.score_rubric(rubric, resp)
        self.assertGreater(out["score"], 0.0)

    def test_empty_rubric_items_raises(self):
        rubric = {
            "items": [],
            "scoring": "weighted_average",
        }
        with self.assertRaises(ValueError):
            fs.score_rubric(rubric, "any response")

    def test_non_dict_rubric_raises(self):
        with self.assertRaises(ValueError):
            fs.score_rubric("not a dict", "response")

    def test_zero_total_weight_raises(self):
        rubric = {
            "items": [
                {"id": "r1", "description": "compiles", "weight": 0.0},
            ],
            "scoring": "weighted_average",
        }
        with self.assertRaises(ValueError):
            fs.score_rubric(rubric, "text")

    def test_empty_description_grants_half_credit(self):
        """Items with no extractable keywords get 0.5 weight credit."""
        rubric = {
            "items": [
                {"id": "r1", "description": "a the", "weight": 1.0},
            ],
            "scoring": "weighted_average",
        }
        out = fs.score_rubric(rubric, "anything")
        # 0.5 fraction → 5.0 normalised
        self.assertAlmostEqual(out["score"], 5.0, places=1)


class TestOutputShape(TestEnvContext):
    """Fallback output must match benchmark-judge envelope."""

    def test_grade_has_forward_reverse_delta(self):
        rubric = {
            "items": [{"id": "r1", "description": "compiles", "weight": 1.0}],
            "scoring": "weighted_average",
        }
        out = fs.grade("the code compiles", rubric, benchmark_slug="test")
        self.assertIn("forward", out)
        self.assertIn("reverse", out)
        self.assertIn("delta", out)
        self.assertIn("judge_adapter", out)
        self.assertEqual(out["judge_adapter"], "fallback")
        self.assertEqual(out["delta"], 0.0)  # deterministic
        self.assertFalse(out["recommend_human_review"])

    def test_grade_score_fields_match_judge_shape(self):
        rubric = {
            "items": [{"id": "r1", "description": "compiles", "weight": 1.0}],
            "scoring": "weighted_average",
        }
        out = fs.grade("compiles", rubric)
        fwd = out["forward"]
        self.assertIn("score", fwd)
        self.assertIn("reasoning", fwd)
        self.assertIn("refused", fwd)
        self.assertIn("flags", fwd)
        self.assertIn("fallback", fwd["flags"])
        self.assertIsInstance(fwd["score"], float)
        self.assertFalse(fwd["refused"])

    def test_forward_equals_reverse(self):
        rubric = {
            "items": [{"id": "r1", "description": "compiles tests pass", "weight": 1.0}],
            "scoring": "weighted_average",
        }
        out = fs.grade("tests pass and code compiles", rubric)
        self.assertEqual(out["forward"]["score"], out["reverse"]["score"])


class TestCli(TestEnvContext):

    def _setup(self):
        rubric_path = self.project_dir / "rubric.json"
        rubric_path.write_text(
            json.dumps({
                "version": 1,
                "rubric_id": "t",
                "items": [
                    {"id": "r1", "description": "compiles", "weight": 1.0},
                ],
                "scoring": "weighted_average",
            }),
            encoding="utf-8",
        )
        response_path = self.project_dir / "response.txt"
        response_path.write_text("the code compiles", encoding="utf-8")
        return rubric_path, response_path

    def test_cli_happy_path(self):
        rubric, response = self._setup()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = fs.main([
                "--benchmark", "test",
                "--response-file", str(response),
                "--rubric-file", str(rubric),
            ])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["benchmark"], "test")
        self.assertEqual(out["judge_adapter"], "fallback")

    def test_cli_missing_response_exits_2(self):
        rubric, _ = self._setup()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = fs.main([
                "--benchmark", "t",
                "--response-file", str(self.project_dir / "nope.txt"),
                "--rubric-file", str(rubric),
            ])
        self.assertEqual(rc, 2)

    def test_cli_missing_rubric_exits_2(self):
        _, response = self._setup()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = fs.main([
                "--benchmark", "t",
                "--response-file", str(response),
                "--rubric-file", str(self.project_dir / "nope.json"),
            ])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
