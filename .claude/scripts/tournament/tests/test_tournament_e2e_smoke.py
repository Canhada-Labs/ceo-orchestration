"""End-to-end smoke test (QA A6 / F-QA6 closure).

Full pipeline: loader → dispatcher (Fake) → runner → scorer → reporter.
Must complete in <10s with FakeLLMDispatcher (no live API calls).
Serves as the regression anchor for Phase 3/4 refactors.
"""
from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import runner
from ..loader import Fixture, load_fixture_file
from ..reporter import load_report, make_task_record, compute_win_rate_matrix, validate_adr052
from ..scorer import score_strict
from ._fake_dispatcher import FakeLLMDispatcher


class TestE2ESmoke(unittest.TestCase):
    def test_full_pipeline_under_10s(self):
        start = time.monotonic()

        # 1. Build 3 minimal fixtures across 3 task-types
        fixtures = [
            Fixture(
                fixture_id="e2e-sec-001",
                task_type="security-review",
                prompt="Review this auth code for bypass risks carefully now.",
                acceptance_strict=["bypass"],
                acceptance_llm_judge="OK?",
                expected_tier="opus",
                max_tokens=500,
                seed=1,
            ),
            Fixture(
                fixture_id="e2e-code-001",
                task_type="code-review",
                prompt="Review this function for style issues and idiomatic problems please.",
                acceptance_strict=["style"],
                acceptance_llm_judge="OK?",
                expected_tier="sonnet",
                max_tokens=500,
                seed=2,
            ),
            Fixture(
                fixture_id="e2e-docs-001",
                task_type="docs-writing",
                prompt="Write a concise README quick-start for a hypothetical tool carefully please.",
                acceptance_strict=["quick-start"],
                acceptance_llm_judge="OK?",
                expected_tier="haiku",
                max_tokens=500,
                seed=3,
            ),
        ]

        # 2. Inject FakeLLMDispatcher with known verdicts
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_response(
            "claude-haiku-4-5-20251001",
            "e2e-sec-001",
            content="I identified the bypass risk in the code clearly.",
            tokens_in=200,
            tokens_out=50,
        )
        dispatcher.register_response(
            "claude-haiku-4-5-20251001",
            "e2e-code-001",
            content="The code style is not idiomatic; recommend refactor.",
            tokens_in=200,
            tokens_out=50,
        )
        dispatcher.register_response(
            "claude-haiku-4-5-20251001",
            "e2e-docs-001",
            content="## Quick-Start\n\n1. Install\n2. Use",
            tokens_in=200,
            tokens_out=50,
        )

        # 3. Run tournament with strict-mode scorer
        with TemporaryDirectory() as d:
            out_path = Path(d) / "e2e-report.jsonl"
            aggregate = runner.run_tournament(
                fixtures=fixtures,
                dispatcher=dispatcher,
                output_path=out_path,
                models=["claude-haiku-4-5-20251001"],
                judge_runs=1,
                budget_usd=10.0,
                concurrency=3,
                check_killswitch_flag=False,
                scorer=score_strict,
            )

            # 4. Assert pipeline outputs present
            self.assertEqual(aggregate["fixtures_count"], 3)
            self.assertEqual(aggregate["models_count"], 1)
            self.assertEqual(aggregate["tasks_completed"], 3)

            # 5. Load + validate JSONL structure
            report = load_report(out_path)
            self.assertEqual(len(report["tasks"]), 3)
            self.assertIsNotNone(report["aggregate"])

            # 6. Compute win-rate matrix from tasks
            matrix = compute_win_rate_matrix(report["tasks"])
            self.assertIn("security-review", matrix)
            self.assertIn("code-review", matrix)
            self.assertIn("docs-writing", matrix)

            # 7. Validate ADR-052 signals
            signals = validate_adr052(matrix)
            self.assertIn("security-review", signals)

            # 8. Each task record has required strict-schema fields
            for task in report["tasks"]:
                self.assertIn("fixture_id", task)
                self.assertIn("fixture_sha256", task)
                self.assertIn("output_sha256", task)
                self.assertIn("verdict", task)
                self.assertIn("tokens_in", task)
                self.assertIn("tokens_out", task)
                self.assertIn("cost_usd", task)
                self.assertIn("wall_clock_ms", task)
                # No raw content
                self.assertNotIn("prompt", task)
                # NOTE: runner.py emits "output_text" doesn't exist; task has
                # "output_sha256" but not "output" raw. Confirm:
                self.assertNotIn("output", task)

            # 9. Dispatcher called exactly 3 times (1 model × 3 fixtures)
            self.assertEqual(dispatcher.call_count, 3)

        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed,
            10.0,
            f"E2E smoke took {elapsed:.2f}s; target <10s with FakeLLMDispatcher",
        )


if __name__ == "__main__":
    unittest.main()
