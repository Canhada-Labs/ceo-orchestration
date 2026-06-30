"""End-to-end tests for `run-skill-benchmark.py --judge-mode` (Phase 3).

Exercises the glue between the fixture runner and the LLM judge /
fallback subsystems. Real API calls never happen — we invoke
`_emit_benchmark_audit_event` + `_run_judge_mode` directly with
constructed fixture results.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_HOOKS = _SCRIPTS.parent / "hooks"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_rsb():
    path = _SCRIPTS / "run-skill-benchmark.py"
    spec = importlib.util.spec_from_file_location("run_skill_benchmark", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rsb = _load_rsb()


def _fake_results(skill="testing-strategy", passed=8, total=10) -> dict:
    """Fixture-run results envelope matching the real runner output."""
    return {
        "benchmark": {"skill": skill, "version": "1.0.0", "owner": "qa"},
        "model": "claude-opus-4-6",
        "repetitions": 3,
        "overall": {
            "passed": passed,
            "total": total,
            "score": passed / total,
            "health": "OK",
        },
        "scenarios": [
            {
                "id": f"s{i}",
                "name": f"scenario {i}",
                "passed": i < passed,
                "median_score": 1.0 if i < passed else 0.0,
            }
            for i in range(total)
        ],
        "timestamp": "2026-04-14T12:00:00Z",
    }


def _fake_bench(skill="testing-strategy", n_scenarios=4) -> dict:
    """Benchmark YAML (already parsed) envelope."""
    return {
        "skill": skill,
        "benchmark_version": 1,
        "owner": "qa",
        "scenarios": [
            {
                "id": f"s{i}",
                "name": f"scenario {i}",
                "control": False,
            }
            for i in range(n_scenarios)
        ],
    }


def _ns(**kw) -> argparse.Namespace:
    """Build an argparse namespace with fixture-mode defaults."""
    ns = argparse.Namespace(
        judge_mode="fixture",
        judge_adapter="gemini",
        judge_mock=True,
        judge_rubric_file=None,
        floor=0.6,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


class TestJudgeModeResolver(TestEnvContext):

    def test_fixture_mode_is_default(self):
        args = _ns()
        self.assertEqual(rsb._judge_mode_resolved(args), "fixture")

    def test_sota_disable_forces_fixture(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        args = _ns(judge_mode="llm")
        resolved = rsb._judge_mode_resolved(args)
        self.assertEqual(resolved, "fixture")

    def test_no_sota_disable_passes_through(self):
        args = _ns(judge_mode="llm")
        self.assertEqual(rsb._judge_mode_resolved(args), "llm")

    def test_judge_mode_both_passes_through(self):
        args = _ns(judge_mode="both")
        self.assertEqual(rsb._judge_mode_resolved(args), "both")


class TestSynthRubric(TestEnvContext):

    def test_synthesised_rubric_has_items(self):
        bench = _fake_bench(n_scenarios=3)
        rubric = rsb._synth_rubric_from_bench(bench)
        self.assertEqual(len(rubric["items"]), 3)
        self.assertEqual(rubric["scoring"], "weighted_average")
        # Weights sum to ~1.0
        total = sum(item["weight"] for item in rubric["items"])
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_synthesised_rubric_empty_scenarios(self):
        bench = {"skill": "x", "scenarios": []}
        rubric = rsb._synth_rubric_from_bench(bench)
        self.assertGreaterEqual(len(rubric["items"]), 1)


class TestJudgeModeRun(TestEnvContext):

    def setUp(self):
        super().setUp()
        # Judge adapter must differ from main
        os.environ["CEO_HOOK_ADAPTER"] = "claude"

    def test_judge_mode_fixture_returns_none(self):
        args = _ns(judge_mode="fixture")
        out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNone(out)

    def test_judge_mode_llm_mock_returns_grade(self):
        args = _ns(judge_mode="llm", judge_adapter="gemini", judge_mock=True)
        out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNotNone(out)
        self.assertIn("forward", out)
        self.assertIn("reverse", out)
        self.assertIn("delta", out)
        self.assertEqual(out["judge_adapter"], "gemini")

    def test_judge_mode_fallback_returns_grade(self):
        args = _ns(judge_mode="fallback")
        out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNotNone(out)
        self.assertEqual(out["judge_adapter"], "fallback")
        self.assertEqual(out["delta"], 0.0)

    def test_judge_mode_both_returns_grade(self):
        args = _ns(judge_mode="both", judge_adapter="gemini", judge_mock=True)
        out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNotNone(out)
        self.assertIn("forward", out)

    def test_judge_mode_llm_unreachable_returns_none(self):
        """With no mock and no injected invoker, llm mode → None (caller falls
        back). The audit event still records judge_mode='llm'."""
        args = _ns(judge_mode="llm", judge_adapter="gemini", judge_mock=False)
        out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNone(out)

    def test_cross_provider_collision_returns_none(self):
        """If judge adapter == main adapter, skip without raising."""
        os.environ["CEO_HOOK_ADAPTER"] = "gemini"
        args = _ns(judge_mode="llm", judge_adapter="gemini", judge_mock=True)
        buf = io.StringIO()
        with redirect_stderr(buf):
            out = rsb._run_judge_mode(_fake_bench(), _fake_results(), args)
        self.assertIsNone(out)
        self.assertIn("differ", buf.getvalue())


class TestAuditEventShape(TestEnvContext):

    def _read_events(self):
        log = self.audit_dir / "audit-log.jsonl"
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_judge_mode_field_written_in_fixture_mode(self):
        args = _ns(judge_mode="fixture")
        rsb._emit_benchmark_audit_event(
            _fake_results(), args, duration_s=1.0, lessons_written=0
        )
        events = self._read_events()
        # Should have benchmark_run; no veto because fixture mode.
        bench_events = [e for e in events if e["action"] == "benchmark_run"]
        self.assertEqual(len(bench_events), 1)
        self.assertEqual(bench_events[0]["judge_mode"], "fixture")

    def test_both_mode_records_judge_scores(self):
        """Both mode writes judge_score_forward, judge_score_reverse, judge_delta."""
        args = _ns(judge_mode="both", judge_adapter="gemini")
        judge_result = {
            "judge_adapter": "gemini",
            "forward": {"score": 8, "refused": False, "flags": [], "reasoning": ""},
            "reverse": {"score": 7, "refused": False, "flags": [], "reasoning": ""},
            "delta": 1.0,
            "recommend_human_review": True,
        }
        rsb._emit_benchmark_audit_event(
            _fake_results(passed=8, total=10),
            args,
            duration_s=0.5,
            lessons_written=0,
            judge_result=judge_result,
        )
        events = self._read_events()
        bench = [e for e in events if e["action"] == "benchmark_run"][0]
        self.assertEqual(bench["judge_mode"], "both")
        self.assertEqual(bench["judge_adapter"], "gemini")
        # Judge scores are 0..10; normalized to 0..1 then ×1000 for bps encoding.
        # score=8 → int(round((8/10.0) * 1000)) = 800 bps.
        # score=7 → int(round((7/10.0) * 1000)) = 700 bps.
        # delta=1.0 (on 0..10 scale) → int(round((1.0/10.0) * 1000)) = 100 bps.
        self.assertEqual(bench["judge_score_forward_bps"], 800)
        self.assertEqual(bench["judge_score_reverse_bps"], 700)
        self.assertEqual(bench["judge_delta_bps"], 100)

    def test_disagreement_emits_veto(self):
        """Fixture 0.8 vs judge (3/10 → 0.3) → delta 0.5 > 0.2 → veto."""
        args = _ns(judge_mode="both", judge_adapter="gemini")
        judge_result = {
            "judge_adapter": "gemini",
            "forward": {"score": 3, "refused": False, "flags": [], "reasoning": ""},
            "reverse": {"score": 3, "refused": False, "flags": [], "reasoning": ""},
            "delta": 0.0,
            "recommend_human_review": False,
        }
        rsb._emit_benchmark_audit_event(
            _fake_results(passed=8, total=10),  # fixture score 0.8
            args,
            duration_s=0.5,
            lessons_written=0,
            judge_result=judge_result,
        )
        events = self._read_events()
        vetoes = [e for e in events if e["action"] == "veto_triggered"]
        self.assertEqual(len(vetoes), 1)
        self.assertEqual(vetoes[0]["reason_code"], "benchmark_judge_disagreement")

    def test_no_disagreement_no_veto(self):
        """Fixture 0.8 vs judge (8/10 → 0.8) → delta 0.0 → no veto."""
        args = _ns(judge_mode="both", judge_adapter="gemini")
        judge_result = {
            "judge_adapter": "gemini",
            "forward": {"score": 8, "refused": False, "flags": [], "reasoning": ""},
            "reverse": {"score": 8, "refused": False, "flags": [], "reasoning": ""},
            "delta": 0.0,
            "recommend_human_review": False,
        }
        rsb._emit_benchmark_audit_event(
            _fake_results(passed=8, total=10),
            args,
            duration_s=0.5,
            lessons_written=0,
            judge_result=judge_result,
        )
        events = self._read_events()
        vetoes = [e for e in events if e["action"] == "veto_triggered"]
        self.assertEqual(len(vetoes), 0)

    def test_llm_mode_without_result_sets_judge_mode_only(self):
        """judge_mode=llm + None result → event still tagged; no veto."""
        args = _ns(judge_mode="llm")
        rsb._emit_benchmark_audit_event(
            _fake_results(), args, duration_s=0.3, lessons_written=0, judge_result=None
        )
        events = self._read_events()
        bench = [e for e in events if e["action"] == "benchmark_run"][0]
        self.assertEqual(bench["judge_mode"], "llm")
        self.assertNotIn("judge_score_forward_bps", bench)


class TestCeoSotaDisableForcesFixture(TestEnvContext):

    def test_sota_disable_prints_warning(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        args = _ns(judge_mode="both", judge_adapter="gemini", judge_mock=True)
        buf = io.StringIO()
        with redirect_stderr(buf):
            resolved = rsb._judge_mode_resolved(args)
        self.assertEqual(resolved, "fixture")
        self.assertIn("CEO_SOTA_DISABLE", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
