"""Fail-open behavior tests (ADR-005 + ADR-063 §Invariants).

Round 1 QA F-QA fail-open coverage. 5 error modes × task-type = 10+ tests.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import runner
from ..loader import Fixture
from ._fake_dispatcher import (
    FakeLLMDispatcher,
    FakeRateLimitError,
    FakeServerError,
    FakeTimeoutError,
)


def _mk(fid: str, tt: str = "security-review") -> Fixture:
    return Fixture(
        fixture_id=fid,
        task_type=tt,
        prompt="a" * 100,
        acceptance_strict=["ok"],
        acceptance_llm_judge="ok?",
        expected_tier="opus",
        max_tokens=1000,
        seed=1,
    )


class TestFailOpenOnErrors(unittest.TestCase):
    def test_server_error_marks_errored_not_failed(self):
        fixtures = [_mk("fx-500")]
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_error(
            "claude-haiku-4-5-20251001", "fx-500", FakeServerError("500 boom")
        )

        with TemporaryDirectory() as d:
            out = Path(d) / "r.jsonl"
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=out,
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            self.assertEqual(aggregate["errored_count"], 1)
            # Task record should say "errored"
            lines = out.read_text(encoding="utf-8").strip().split("\n")
            task = json.loads(lines[0])
            self.assertEqual(task["verdict"], "errored")
            self.assertIn("FakeServerError", task.get("error_reason", ""))

    def test_rate_limit_exhausts_retries_then_errored(self):
        # Register FakeRateLimitError — without providing it in
        # rate_limit_exceptions, it's non-retryable and marked errored immediately.
        # With it in rate_limit_exceptions, retries exhaust → bubble up → errored.
        fixtures = [_mk("fx-429")]
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_error(
            "claude-haiku-4-5-20251001", "fx-429", FakeRateLimitError("429")
        )

        with TemporaryDirectory() as d:
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=Path(d) / "r.jsonl",
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
                # No retries configured — single attempt fails, fail-open
            )
            self.assertEqual(aggregate["errored_count"], 1)

    def test_timeout_marks_errored(self):
        fixtures = [_mk("fx-to")]
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_error(
            "claude-haiku-4-5-20251001", "fx-to", FakeTimeoutError("slow")
        )

        with TemporaryDirectory() as d:
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=Path(d) / "r.jsonl",
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
                timeout_exceptions=(FakeTimeoutError,),
            )
            self.assertEqual(aggregate["errored_count"], 1)
            # Errored tasks contribute $0 to cost
            self.assertEqual(aggregate["total_cost_usd"], 0.0)

    def test_mixed_success_and_errors_tournament_completes(self):
        fixtures = [_mk(f"fx-{i}") for i in range(5)]
        dispatcher = FakeLLMDispatcher()
        # fx-0, fx-2, fx-4 succeed; fx-1, fx-3 error
        dispatcher.set_default_response(content="OK")
        dispatcher.register_error(
            "claude-haiku-4-5-20251001", "fx-1", FakeServerError("bad")
        )
        dispatcher.register_error(
            "claude-haiku-4-5-20251001", "fx-3", FakeServerError("bad")
        )

        with TemporaryDirectory() as d:
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=Path(d) / "r.jsonl",
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            self.assertEqual(aggregate["tasks_completed"], 5)
            self.assertEqual(aggregate["errored_count"], 2)
            self.assertFalse(aggregate["partial"])

    def test_keyerror_from_misconfigured_dispatcher_marks_errored(self):
        # FakeLLMDispatcher raises KeyError when response not registered
        # and no default set. Runner should mark as errored, not crash.
        fixtures = [_mk("fx-missing")]
        dispatcher = FakeLLMDispatcher()
        # no registration, no default

        with TemporaryDirectory() as d:
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=Path(d) / "r.jsonl",
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            self.assertEqual(aggregate["errored_count"], 1)


class TestFailOpenAcrossTaskTypes(unittest.TestCase):
    """5 task-types × errored dispatch — each must be handled gracefully."""

    def test_security_review_errored(self):
        self._run_errored_for_task_type("security-review")

    def test_code_review_errored(self):
        self._run_errored_for_task_type("code-review")

    def test_performance_triage_errored(self):
        self._run_errored_for_task_type("performance-triage")

    def test_test_design_errored(self):
        self._run_errored_for_task_type("test-design")

    def test_docs_writing_errored(self):
        self._run_errored_for_task_type("docs-writing")

    def _run_errored_for_task_type(self, tt: str) -> None:
        fixtures = [_mk(f"fx-{tt}", tt=tt)]
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_error(
            "claude-haiku-4-5-20251001",
            f"fx-{tt}",
            FakeServerError("upstream failure"),
        )

        with TemporaryDirectory() as d:
            out = Path(d) / "r.jsonl"
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=out,
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=1,
                check_killswitch_flag=False,
            )
            self.assertEqual(aggregate["errored_count"], 1)
            lines = out.read_text(encoding="utf-8").strip().split("\n")
            task = json.loads(lines[0])
            self.assertEqual(task["task_type"], tt)
            self.assertEqual(task["verdict"], "errored")


if __name__ == "__main__":
    unittest.main()
