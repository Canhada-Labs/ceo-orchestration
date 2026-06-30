"""Golden byte-identity regression anchor (QA A2 / C-P0-8 closure).

Strict-mode scorer output should be byte-identical across runs given:
- Same fixture corpus
- Same seed
- Same FakeLLMDispatcher response map
- Same Python version (and stdlib json module behavior)

This test generates a golden-report fixture on first invocation if
missing; then asserts SHA-256 match on subsequent runs. Regression
anchor for any scorer/reporter refactor.

Golden file: tests/golden/strict_report_seed42.jsonl
"""
from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

from .. import reporter, scorer
from ..loader import Fixture

_GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
_GOLDEN_PATH = _GOLDEN_DIR / "strict_report_seed42.jsonl"


def _build_deterministic_report() -> bytes:
    """Build a byte-identical JSONL report from a fixed fixture set."""
    # Use 5 deterministic fixtures + 3 deterministic outputs + strict scorer
    fixtures_plus_outputs = [
        (
            Fixture(
                fixture_id="golden-001",
                task_type="security-review",
                prompt="Review auth middleware for bypass risks and report findings.",
                acceptance_strict=["authentication", "authorization"],
                acceptance_llm_judge="Does the review cover OWASP?",
                expected_tier="opus",
                max_tokens=1000,
                seed=42,
            ),
            "The authentication check is missing; authorization logic is also absent.",
        ),
        (
            Fixture(
                fixture_id="golden-002",
                task_type="code-review",
                prompt="Review this function for off-by-one errors thoroughly please.",
                acceptance_strict=["off-by-one", "index"],
                acceptance_llm_judge="Ok?",
                expected_tier="sonnet",
                max_tokens=500,
                seed=42,
            ),
            "I see an off-by-one issue at the loop index; use len(arr)-1.",
        ),
        (
            Fixture(
                fixture_id="golden-003",
                task_type="docs-writing",
                prompt="Write a README quick-start section for a CLI tool that's friendly.",
                acceptance_strict=["install", "example"],
                acceptance_llm_judge="Clear?",
                expected_tier="haiku",
                max_tokens=500,
                seed=42,
            ),
            "## Install\n\npip install foo\n\n## Example\n\nfoo --help\n",
        ),
        (
            Fixture(
                fixture_id="golden-004",
                task_type="performance-triage",
                prompt="Analyze this hot-path function for complexity and suggest fixes.",
                acceptance_strict=["O(n", "complexity"],
                acceptance_llm_judge="Correct?",
                expected_tier="sonnet",
                max_tokens=500,
                seed=42,
            ),
            "The nested loop is O(n^2); reduce complexity via a hash-set lookup.",
        ),
        (
            Fixture(
                fixture_id="golden-005",
                task_type="test-design",
                prompt="Design tests for this pagination helper with boundary conditions.",
                acceptance_strict=["edge case", "boundary"],
                acceptance_llm_judge="Solid?",
                expected_tier="sonnet",
                max_tokens=500,
                seed=42,
            ),
            # Intentionally missing "boundary" keyword → expect fail verdict
            "Include edge case: empty input, single item, 0 items per page.",
        ),
    ]

    # Generate task records deterministically
    from types import SimpleNamespace

    lines: list = []
    total_cost = 0.0
    for idx, (fixture, output) in enumerate(fixtures_plus_outputs):
        response = SimpleNamespace(content=output)
        verdict = scorer.score_strict(fixture, response)
        tokens_in = 100  # fixed for determinism
        tokens_out = 50
        cost = 0.001  # fixed
        rec = reporter.make_task_record(
            fixture_id=fixture.fixture_id,
            fixture_content=fixture.prompt,
            task_type=fixture.task_type,
            model="claude-haiku-4-5-20251001",
            verdict=verdict,
            output_text=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            wall_clock_ms=100 + idx,  # deterministic varying value
        )
        total_cost += cost
        # Canonical JSON — sort_keys ensures byte-identity
        lines.append(json.dumps(rec, sort_keys=True))

    # Aggregate record
    task_records = [json.loads(l) for l in lines]
    win_rate = reporter.compute_win_rate_matrix(task_records)
    aggregate = {
        "type": "aggregate",
        "run_id": "golden-seed42",
        "fixtures_count": len(fixtures_plus_outputs),
        "models_count": 1,
        "judge_runs": 1,
        "win_rate": win_rate,
        "total_cost_usd": round(total_cost, 6),
        "projected_cost_usd": 0.005,
        "budget_cap_usd": 75.0,
        "errored_count": sum(1 for r in task_records if r["verdict"] == "errored"),
        "tasks_completed": len(task_records),
        "partial": False,
        "adr052_validation": reporter.validate_adr052(win_rate),
    }
    lines.append(json.dumps(aggregate, sort_keys=True))

    return ("\n".join(lines) + "\n").encode("utf-8")


class TestGoldenByteIdentity(unittest.TestCase):
    """The strict-mode report JSONL must be byte-identical across runs."""

    def test_golden_matches_or_create(self):
        generated = _build_deterministic_report()

        if not _GOLDEN_PATH.exists():
            # First run: create the golden file, then skip assertion
            _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            _GOLDEN_PATH.write_bytes(generated)
            self.skipTest(
                f"golden fixture created at {_GOLDEN_PATH}; re-run to verify"
            )

        committed = _GOLDEN_PATH.read_bytes()
        gen_digest = hashlib.sha256(generated).hexdigest()
        com_digest = hashlib.sha256(committed).hexdigest()
        self.assertEqual(
            gen_digest,
            com_digest,
            f"Golden byte-identity regression.\n"
            f"  generated sha256 = {gen_digest}\n"
            f"  committed sha256 = {com_digest}\n"
            f"Either (a) intentionally refactor scorer/reporter and regenerate "
            f"the golden (delete {_GOLDEN_PATH} + rerun) OR (b) the change is "
            f"an unintended regression.",
        )


if __name__ == "__main__":
    unittest.main()
