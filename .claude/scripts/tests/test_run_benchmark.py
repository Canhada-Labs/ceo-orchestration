"""Unit tests for run-skill-benchmark.py.

All API calls are mocked. Covers:
- YAML parse + validation
- Prompt building (system + user, content truncation)
- Response parsing (JSON extraction, fence tolerance, parse errors)
- Scoring logic (positive + control scenarios, all weight combinations)
- Cost estimation
- CLI happy path + error paths (missing key, missing file, cost cap)
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

_spec = importlib.util.spec_from_file_location(
    "run_skill_benchmark", str(SCRIPTS_DIR / "run-skill-benchmark.py")
)
rsb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rsb)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_POSITIVE = {
    "id": "TEST-001",
    "name": "sample positive",
    "category": "A03-injection",
    "severity": "HIGH",
    "version": 1,
    "validated_by": "2026-04-11",
    "input": {
        "type": "code",
        "language": "python",
        "content": "def q(u): return cur.execute(f'SELECT * FROM t WHERE id={u}')",
    },
    "prompt_template": "Review the code. Respond JSON {\"issues\": [...]}.",
    "expected": {
        "must_flag_tags": ["sql-injection"],
        "acceptable_alternative_tags": ["sqli"],
        "must_suggest_keywords": ["parameterized", "prepared statement"],
        "must_identify_severity": "CRITICAL",
    },
}

SAMPLE_CONTROL = {
    "id": "CTRL-TEST-001",
    "name": "sample control",
    "category": "CONTROL-parameterized",
    "control": True,
    "version": 1,
    "validated_by": "2026-04-11",
    "input": {
        "type": "code",
        "language": "python",
        "content": "def q(u): return cur.execute('SELECT * FROM t WHERE id=%s', (u,))",
    },
    "prompt_template": "Review the code. Respond JSON {\"issues\": [...]}.",
    "expected": {
        "must_not_flag_tags": ["sql-injection", "sqli"],
    },
}

SAMPLE_BENCH = {
    "skill": "security-and-auth",
    "benchmark_version": 1,
    "owner": "Principal Security Engineer",
    "scoring": {
        "pass_threshold": 0.7,
        "health_thresholds": {"critical": 0.4, "warning": 0.6, "healthy": 0.8},
        "tag_weight": 0.5,
        "suggestion_weight": 0.3,
        "severity_weight": 0.2,
    },
    "scenarios": [SAMPLE_POSITIVE, SAMPLE_CONTROL],
}


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


class TestLoadBenchmark(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_valid_yaml(self):
        import yaml

        path = self.tmp / "bench.yaml"
        path.write_text(yaml.dump(SAMPLE_BENCH))
        bench = rsb.load_benchmark(path)
        self.assertEqual(bench["skill"], "security-and-auth")
        self.assertEqual(len(bench["scenarios"]), 2)

    def test_load_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            rsb.load_benchmark(self.tmp / "nope.yaml")

    def test_load_missing_field(self):
        import yaml

        path = self.tmp / "bad.yaml"
        path.write_text(yaml.dump({"scenarios": [], "scoring": {}}))  # missing skill
        with self.assertRaises(ValueError) as ctx:
            rsb.load_benchmark(path)
        self.assertIn("skill", str(ctx.exception))

    def test_load_scenarios_not_list(self):
        import yaml

        path = self.tmp / "bad.yaml"
        path.write_text(yaml.dump({"skill": "s", "scenarios": "not a list", "scoring": {}}))
        with self.assertRaises(ValueError):
            rsb.load_benchmark(path)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


class TestCostEstimation(unittest.TestCase):
    def test_estimate_returns_nonzero(self):
        cost = rsb.estimate_cost_usd(SAMPLE_BENCH, max_tokens=2000, repetitions=3)
        self.assertGreater(cost, 0)
        self.assertLess(cost, 1.0)  # 2 scenarios × 3 reps is cheap

    def test_estimate_scales_with_scenarios(self):
        tiny = {"scenarios": [SAMPLE_POSITIVE]}
        big = {"scenarios": [SAMPLE_POSITIVE] * 20}
        cost_tiny = rsb.estimate_cost_usd(tiny, max_tokens=2000, repetitions=3)
        cost_big = rsb.estimate_cost_usd(big, max_tokens=2000, repetitions=3)
        self.assertGreater(cost_big, cost_tiny * 10)

    def test_estimate_scales_with_repetitions(self):
        c1 = rsb.estimate_cost_usd(SAMPLE_BENCH, max_tokens=2000, repetitions=1)
        c5 = rsb.estimate_cost_usd(SAMPLE_BENCH, max_tokens=2000, repetitions=5)
        self.assertAlmostEqual(c5 / c1, 5.0, places=2)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


class TestBuildPrompt(unittest.TestCase):
    def test_system_prompt_contains_skill_content(self):
        system, user = rsb.build_prompt("FAKE SKILL BODY", SAMPLE_POSITIVE, max_input_chars=4000)
        self.assertIn("FAKE SKILL BODY", system)
        self.assertIn("JSON only", system)

    def test_user_prompt_contains_code_and_template(self):
        _system, user = rsb.build_prompt("skill", SAMPLE_POSITIVE, max_input_chars=4000)
        self.assertIn("Review the code", user)
        self.assertIn("SELECT * FROM t", user)
        self.assertIn("```python", user)

    def test_content_truncation(self):
        big_scenario = dict(SAMPLE_POSITIVE)
        big_scenario["input"] = {"type": "code", "language": "python", "content": "x" * 10000}
        _system, user = rsb.build_prompt("skill", big_scenario, max_input_chars=100)
        self.assertIn("truncated for benchmark", user)
        self.assertLess(user.count("x"), 200)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestParseResponse(unittest.TestCase):
    def test_parse_clean_json(self):
        text = '{"issues": [{"tag": "sql-injection", "severity": "CRITICAL"}]}'
        data = rsb.parse_response(text)
        self.assertEqual(len(data["issues"]), 1)
        self.assertIsNone(data.get("_parse_error"))

    def test_parse_fenced_json(self):
        text = '```json\n{"issues": [{"tag": "xss"}]}\n```'
        data = rsb.parse_response(text)
        self.assertEqual(data["issues"][0]["tag"], "xss")

    def test_parse_with_trailing_prose(self):
        text = '{"issues": []}\nThis is extra text.'
        data = rsb.parse_response(text)
        self.assertEqual(data["issues"], [])

    def test_parse_malformed_returns_empty(self):
        data = rsb.parse_response("not json at all")
        self.assertEqual(data["issues"], [])
        self.assertIn("_parse_error", data)

    def test_parse_empty_string(self):
        data = rsb.parse_response("")
        self.assertEqual(data["issues"], [])


# ---------------------------------------------------------------------------
# Scoring — positive scenarios
# ---------------------------------------------------------------------------


class TestScoringPositive(unittest.TestCase):
    def _score(self, issues):
        return rsb.score_scenario(
            {"issues": issues},
            SAMPLE_POSITIVE["expected"],
            SAMPLE_BENCH["scoring"],
            is_control=False,
        )

    def test_perfect_response_scores_1_0(self):
        r = self._score([
            {
                "tag": "sql-injection",
                "severity": "CRITICAL",
                "suggestion": "use parameterized query",
            }
        ])
        self.assertAlmostEqual(r["score"], 1.0, places=3)
        self.assertTrue(r["passed"])

    def test_primary_tag_only_half_credit_from_tag(self):
        r = self._score([{"tag": "sql-injection", "severity": "LOW", "suggestion": ""}])
        # tag 0.5 + sugg 0 + sev 0 = 0.5 → below 0.7
        self.assertAlmostEqual(r["score"], 0.5, places=3)
        self.assertFalse(r["passed"])

    def test_alt_tag_is_half_of_primary(self):
        r = self._score([{"tag": "sqli", "severity": "CRITICAL", "suggestion": "parameterized"}])
        # tag = 0.25 (alt) + sugg 0.3 + sev 0.2 = 0.75 → passes
        self.assertAlmostEqual(r["score"], 0.75, places=3)
        self.assertTrue(r["passed"])

    def test_no_tag_match_no_tag_credit(self):
        r = self._score(
            [{"tag": "something-else", "severity": "CRITICAL", "suggestion": "parameterized"}]
        )
        # tag 0 + sugg 0.3 + sev 0.2 = 0.5
        self.assertAlmostEqual(r["score"], 0.5, places=3)

    def test_empty_issues_zero_score(self):
        r = self._score([])
        self.assertEqual(r["score"], 0.0)
        self.assertFalse(r["passed"])

    def test_suggestion_keyword_case_insensitive(self):
        r = self._score(
            [{"tag": "sql-injection", "severity": "CRITICAL", "suggestion": "Use PREPARED STATEMENT"}]
        )
        self.assertTrue(r["breakdown"]["suggestion_hit"])

    def test_substring_tag_match_both_directions(self):
        # "sql-injection-vulnerability" contains "sql-injection"
        r = self._score(
            [{"tag": "sql-injection-vulnerability", "severity": "CRITICAL", "suggestion": "parameterized"}]
        )
        self.assertTrue(r["breakdown"]["tag_hit_primary"])


# ---------------------------------------------------------------------------
# Scoring — control scenarios
# ---------------------------------------------------------------------------


class TestScoringControl(unittest.TestCase):
    def _score(self, issues):
        return rsb.score_scenario(
            {"issues": issues},
            SAMPLE_CONTROL["expected"],
            SAMPLE_BENCH["scoring"],
            is_control=True,
        )

    def test_control_passes_on_empty_issues(self):
        r = self._score([])
        self.assertEqual(r["score"], 1.0)
        self.assertTrue(r["passed"])

    def test_control_passes_on_unrelated_low_issue(self):
        r = self._score([{"tag": "code-style-nit", "severity": "LOW"}])
        self.assertEqual(r["score"], 1.0)

    def test_control_fails_on_forbidden_medium(self):
        r = self._score([{"tag": "sql-injection", "severity": "MEDIUM"}])
        self.assertEqual(r["score"], 0.0)

    def test_control_fails_on_forbidden_high(self):
        r = self._score([{"tag": "sqli", "severity": "HIGH"}])
        self.assertEqual(r["score"], 0.0)

    def test_control_ignores_forbidden_tag_at_low_severity(self):
        # LOW severity is tolerated (precision is about MED+ false positives)
        r = self._score([{"tag": "sql-injection", "severity": "LOW"}])
        self.assertEqual(r["score"], 1.0)


# ---------------------------------------------------------------------------
# Health label
# ---------------------------------------------------------------------------


class TestHealthLabel(unittest.TestCase):
    def test_critical_below_0_4(self):
        self.assertEqual(rsb._health_label(0.3, {"critical": 0.4, "warning": 0.6, "healthy": 0.8}), "CRITICAL")

    def test_warning_below_0_6(self):
        self.assertEqual(rsb._health_label(0.5, {"critical": 0.4, "warning": 0.6, "healthy": 0.8}), "WARNING")

    def test_ok_between_warning_and_healthy(self):
        self.assertEqual(rsb._health_label(0.7, {"critical": 0.4, "warning": 0.6, "healthy": 0.8}), "OK")

    def test_healthy_at_or_above_0_8(self):
        self.assertEqual(rsb._health_label(0.9, {"critical": 0.4, "warning": 0.6, "healthy": 0.8}), "HEALTHY")


# ---------------------------------------------------------------------------
# Markdown / JSON emitters
# ---------------------------------------------------------------------------


class TestEmitters(unittest.TestCase):
    def _fake_results(self):
        return {
            "benchmark": {"skill": "s", "version": 1, "owner": "X", "scenario_count": 1},
            "model": "claude-haiku-4-5-20251001",
            "repetitions": 3,
            "overall": {"passed": 1, "total": 1, "score": 1.0, "health": "HEALTHY"},
            "scenarios": [
                {
                    "id": "T-1",
                    "name": "sample",
                    "median_score": 1.0,
                    "passed": True,
                    "control": False,
                }
            ],
            "timestamp": "2026-04-11T12:00:00Z",
        }

    def test_emit_markdown(self):
        md = rsb.emit_markdown(self._fake_results())
        self.assertIn("## Benchmark:", md)
        self.assertIn("HEALTHY", md)
        self.assertIn("T-1", md)
        self.assertIn("PASS", md)

    def test_emit_json_is_valid(self):
        js = rsb.emit_json(self._fake_results())
        parsed = json.loads(js)
        self.assertEqual(parsed["benchmark"]["skill"], "s")


# ---------------------------------------------------------------------------
# run_one_scenario with mocked API client
# ---------------------------------------------------------------------------


class TestRunOneScenario(unittest.TestCase):
    def test_run_one_scenario_all_runs_succeed(self):
        """Mock the API to return a perfect JSON response 3 times."""
        fake_response_text = (
            '{"issues": [{"tag": "sql-injection", "severity": "CRITICAL", '
            '"suggestion": "use parameterized query"}]}'
        )

        async def fake_call_api(*args, **kwargs):
            return fake_response_text

        with patch.object(rsb, "call_api", new=fake_call_api):
            result = asyncio.run(
                rsb.run_one_scenario(
                    client=MagicMock(),
                    scenario=SAMPLE_POSITIVE,
                    skill_content="skill body",
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2000,
                    repetitions=3,
                    scoring=SAMPLE_BENCH["scoring"],
                    max_input_chars=4000,
                )
            )

        self.assertEqual(result["id"], "TEST-001")
        self.assertEqual(len(result["raw_scores"]), 3)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["median_score"], 1.0, places=3)

    def test_run_one_scenario_api_error_marks_skipped(self):
        async def fake_call_api(*args, **kwargs):
            raise RuntimeError("API failed")

        with patch.object(rsb, "call_api", new=fake_call_api):
            result = asyncio.run(
                rsb.run_one_scenario(
                    client=MagicMock(),
                    scenario=SAMPLE_POSITIVE,
                    skill_content="skill body",
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2000,
                    repetitions=3,
                    scoring=SAMPLE_BENCH["scoring"],
                    max_input_chars=4000,
                )
            )

        self.assertFalse(result["passed"])
        self.assertEqual(result["raw_scores"], [0.0, 0.0, 0.0])
        for run in result["raw_runs"]:
            self.assertTrue(run.get("skipped") or run.get("error"))


# ---------------------------------------------------------------------------
# PLAN-133 C1 — worst-of-N aggregation + flaky flag
# ---------------------------------------------------------------------------

_PERFECT_JSON = (
    '{"issues": [{"tag": "sql-injection", "severity": "CRITICAL", '
    '"suggestion": "use parameterized query"}]}'
)
# A response that flags nothing → scores 0.0 for SAMPLE_POSITIVE.
_EMPTY_JSON = '{"issues": []}'


class TestAggregateHelpers(unittest.TestCase):
    def test_aggregate_worst_is_min(self):
        self.assertEqual(rsb.aggregate_scores([1.0, 0.0, 0.5], mode="worst"), 0.0)
        self.assertEqual(rsb.aggregate_scores([0.8, 0.9], mode="worst"), 0.8)

    def test_aggregate_median_legacy(self):
        # upper-median for even N matches the historical sorted[len//2]
        self.assertEqual(rsb.aggregate_scores([0.0, 0.0, 1.0], mode="median"), 0.0)
        self.assertEqual(rsb.aggregate_scores([0.0, 1.0, 1.0], mode="median"), 1.0)

    def test_aggregate_empty_is_zero(self):
        self.assertEqual(rsb.aggregate_scores([], mode="worst"), 0.0)

    def test_aggregate_unknown_mode_falls_back_to_worst(self):
        self.assertEqual(rsb.aggregate_scores([1.0, 0.2], mode="bogus"), 0.2)

    def test_detect_flaky_true_on_disagreement(self):
        self.assertTrue(rsb.detect_flaky([True, False, True]))

    def test_detect_flaky_false_when_unanimous(self):
        self.assertFalse(rsb.detect_flaky([True, True, True]))
        self.assertFalse(rsb.detect_flaky([False, False]))

    def test_detect_flaky_false_single_run(self):
        self.assertFalse(rsb.detect_flaky([True]))
        self.assertFalse(rsb.detect_flaky([]))

    def test_resolve_aggregation_default_is_worst(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_BENCH_AGGREGATION", None)
            self.assertEqual(rsb._resolve_aggregation(), "worst")

    def test_resolve_aggregation_median_env(self):
        with patch.dict(os.environ, {"CEO_BENCH_AGGREGATION": "median"}):
            self.assertEqual(rsb._resolve_aggregation(), "median")

    def test_resolve_aggregation_bad_env_fails_open_to_worst(self):
        with patch.dict(os.environ, {"CEO_BENCH_AGGREGATION": "nonsense"}):
            self.assertEqual(rsb._resolve_aggregation(), "worst")


class TestWorstOfNAndFlaky(unittest.TestCase):
    def _run(self, responses, *, repetitions=3, env=None):
        """Run one scenario with a stateful fake API returning `responses`."""
        seq = list(responses)
        calls = {"n": 0}

        async def fake_call_api(*args, **kwargs):
            idx = min(calls["n"], len(seq) - 1)
            calls["n"] += 1
            return seq[idx]

        env = env or {}
        with patch.dict(os.environ, env, clear=False):
            if "CEO_BENCH_AGGREGATION" not in env:
                os.environ.pop("CEO_BENCH_AGGREGATION", None)
            with patch.object(rsb, "call_api", new=fake_call_api):
                return asyncio.run(
                    rsb.run_one_scenario(
                        client=MagicMock(),
                        scenario=SAMPLE_POSITIVE,
                        skill_content="skill body",
                        model="claude-haiku-4-5-20251001",
                        max_tokens=2000,
                        repetitions=repetitions,
                        scoring=SAMPLE_BENCH["scoring"],
                        max_input_chars=4000,
                    )
                )

    def test_worst_of_n_takes_minimum(self):
        # Two perfect runs + one empty (score 0.0). Worst-of-N = 0.0.
        result = self._run([_PERFECT_JSON, _PERFECT_JSON, _EMPTY_JSON])
        self.assertEqual(result["aggregation"], "worst")
        self.assertAlmostEqual(result["aggregated_score"], 0.0, places=3)
        self.assertAlmostEqual(result["median_score"], 0.0, places=3)
        self.assertFalse(result["passed"])  # floor pulled it under threshold

    def test_flaky_flag_on_disagreement(self):
        # One passing run, two failing → verdicts disagree → flaky True.
        result = self._run([_PERFECT_JSON, _EMPTY_JSON, _EMPTY_JSON])
        self.assertTrue(result["flaky"])
        # raw scores recorded for variance tracking
        self.assertEqual(len(result["raw_scores"]), 3)

    def test_not_flaky_when_unanimous_pass(self):
        result = self._run([_PERFECT_JSON, _PERFECT_JSON, _PERFECT_JSON])
        self.assertFalse(result["flaky"])
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["aggregated_score"], result["median_score"], places=3)

    def test_not_flaky_when_unanimous_fail(self):
        result = self._run([_EMPTY_JSON, _EMPTY_JSON, _EMPTY_JSON])
        self.assertFalse(result["flaky"])
        self.assertFalse(result["passed"])

    def test_median_escape_hatch_restores_legacy(self):
        # [1.0, 0.0, 0.0] → median(upper) = 0.0 ; but [1.0,1.0,0.0] → 1.0
        result = self._run(
            [_PERFECT_JSON, _PERFECT_JSON, _EMPTY_JSON],
            env={"CEO_BENCH_AGGREGATION": "median"},
        )
        self.assertEqual(result["aggregation"], "median")
        # sorted scores [0.0, 1.0, 1.0]; median sorted[3//2=1] = 1.0
        self.assertAlmostEqual(result["median_score"], 1.0, places=3)
        # still flaky (verdicts disagree) regardless of aggregation mode
        self.assertTrue(result["flaky"])


# ---------------------------------------------------------------------------
# CLI error paths
# ---------------------------------------------------------------------------


class TestCLIErrorPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._env_snapshot = {"ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY")}
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _run_cli(self, argv):
        buf = io.StringIO()
        err = io.StringIO()
        rc = 0
        with redirect_stdout(buf), redirect_stderr(err):
            try:
                rc = rsb.main(argv)
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 1
        return buf.getvalue(), err.getvalue(), rc

    def test_missing_key_without_skip_flag_exits_2(self):
        bench_path = self.tmp / "b.yaml"
        import yaml

        bench_path.write_text(yaml.dump(SAMPLE_BENCH))
        out, err, rc = self._run_cli([str(bench_path)])
        self.assertEqual(rc, 2)
        self.assertIn("ANTHROPIC_API_KEY not set", err)

    def test_skip_if_no_key_exits_0(self):
        bench_path = self.tmp / "b.yaml"
        import yaml

        bench_path.write_text(yaml.dump(SAMPLE_BENCH))
        out, err, rc = self._run_cli([str(bench_path), "--skip-if-no-key"])
        self.assertEqual(rc, 0)
        self.assertIn("SKIPPED", out)

    def test_missing_benchmark_file(self):
        os.environ["ANTHROPIC_API_KEY"] = "dummy"
        out, err, rc = self._run_cli([str(self.tmp / "nonexistent.yaml")])
        self.assertEqual(rc, 2)
        self.assertIn("not found", err)

    def test_cost_cap_blocks_expensive_run(self):
        os.environ["ANTHROPIC_API_KEY"] = "dummy"
        huge_bench = dict(SAMPLE_BENCH)
        # 49 scenarios × 3 reps × high max_tokens pushes estimate over $1
        huge_bench["scenarios"] = [SAMPLE_POSITIVE] * 49
        bench_path = self.tmp / "big.yaml"
        import yaml

        bench_path.write_text(yaml.dump(huge_bench))
        out, err, rc = self._run_cli(
            [str(bench_path), "--max-tokens", "8000", "--repetitions", "5"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("cost", err.lower())

    def test_too_many_scenarios_refused(self):
        os.environ["ANTHROPIC_API_KEY"] = "dummy"
        huge_bench = dict(SAMPLE_BENCH)
        huge_bench["scenarios"] = [SAMPLE_POSITIVE] * 51  # over the cap
        bench_path = self.tmp / "toobig.yaml"
        import yaml

        bench_path.write_text(yaml.dump(huge_bench))
        out, err, rc = self._run_cli([str(bench_path)])
        self.assertEqual(rc, 2)
        self.assertIn("cap", err)


if __name__ == "__main__":
    unittest.main()
