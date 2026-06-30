"""PLAN-039 tests — owasp-llm-top-10.yaml benchmark structural validation.

Ensures the benchmark file is well-formed, mapped across all 10 OWASP
LLM categories per the Round-1 debate convergent findings, and carries
literal adversarial payload cues where LLM01 / LLM06 specifically
require them.

Stdlib-only test harness; runs under pytest. No live-API runs here —
this is structural validation only. Live-run regression detection is
governed by `model_baseline_version` + future `baseline_results` per
qa P0-3 of the debate.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_PATH = (
    REPO_ROOT
    / ".claude"
    / "skills"
    / "core"
    / "security-and-auth"
    / "benchmarks"
    / "owasp-llm-top-10.yaml"
)
RUBRIC_DOC = REPO_ROOT / "docs" / "OWASP-LLM-TOP-10.md"

POSITIVE_SCENARIO_IDS = [f"LLM-BENCH-{i:03d}" for i in range(1, 15)]  # 001-014
CONTROL_SCENARIO_IDS = [f"LLM-CTRL-{i:03d}" for i in range(1, 7)]      # 001-006

EXPECTED_CATEGORY_COUNTS = {
    "LLM01-prompt-injection": 2,
    "LLM02-insecure-output-handling": 2,
    "LLM03-training-data-poisoning": 1,
    "LLM04-model-denial-of-service": 1,
    "LLM05-supply-chain-vulnerabilities": 1,
    "LLM06-sensitive-information-disclosure": 2,
    "LLM07-insecure-plugin-design": 2,
    "LLM08-excessive-agency": 1,
    "LLM09-overreliance": 1,
    "LLM10-model-theft": 1,
}


@pytest.fixture(scope="module")
def benchmark_text() -> str:
    return BENCHMARK_PATH.read_text(encoding="utf-8")


def test_benchmark_file_exists() -> None:
    assert BENCHMARK_PATH.is_file(), f"missing benchmark: {BENCHMARK_PATH}"
    assert BENCHMARK_PATH.stat().st_size > 5_000, (
        "benchmark suspiciously small; expected > 5 KiB"
    )


def test_benchmark_skill_field(benchmark_text: str) -> None:
    assert re.search(
        r"^skill:\s*security-and-auth\s*$", benchmark_text, re.MULTILINE
    ), "benchmark must target skill: security-and-auth"


def test_benchmark_version_and_baseline(benchmark_text: str) -> None:
    assert re.search(
        r"^benchmark_version:\s*1\s*$", benchmark_text, re.MULTILINE
    ), "benchmark_version must be 1 on first release"
    assert re.search(
        r"^model_baseline_version:\s*claude-opus-4-7\b",
        benchmark_text,
        re.MULTILINE,
    ), "model_baseline_version must anchor to claude-opus-4-7 per qa P0-3"


def test_scoring_block_has_control_threshold(benchmark_text: str) -> None:
    assert re.search(
        r"^\s*control_threshold:\s*0\.85\s*$",
        benchmark_text,
        re.MULTILINE,
    ), "scoring.control_threshold must be 0.85 (stricter than owasp-basics)"


def test_all_14_positive_scenarios_present(benchmark_text: str) -> None:
    for sid in POSITIVE_SCENARIO_IDS:
        assert (
            f"id: {sid}" in benchmark_text
        ), f"missing positive scenario: {sid}"


def test_all_6_control_scenarios_present(benchmark_text: str) -> None:
    for sid in CONTROL_SCENARIO_IDS:
        assert (
            f"id: {sid}" in benchmark_text
        ), f"missing control scenario: {sid}"


@pytest.mark.parametrize(
    "category,expected_count",
    list(EXPECTED_CATEGORY_COUNTS.items()),
    ids=list(EXPECTED_CATEGORY_COUNTS.keys()),
)
def test_category_coverage_matches_debate_target(
    benchmark_text: str, category: str, expected_count: int
) -> None:
    occurrences = benchmark_text.count(f"category: {category}")
    assert occurrences == expected_count, (
        f"category {category}: expected {expected_count} positive scenarios "
        f"per Round-1 debate, got {occurrences}"
    )


def test_llm01_indirect_injection_has_adversarial_payload_markers(
    benchmark_text: str,
) -> None:
    """qa P0-2 convergent finding: LLM01 scenarios must cue adversarial
    payload shapes (bidi / zero-width / tag chars / 'Ignore previous'
    markers) in the prompt_template so the scorer tests payload
    recognition, not just structural pattern match."""
    # Find the LLM-BENCH-002 scenario block.
    block_start = benchmark_text.index("id: LLM-BENCH-002")
    block_end = benchmark_text.index("id: LLM-BENCH-003")
    block = benchmark_text[block_start:block_end]
    for cue in ("bidi", "zero-width", "tag char", "Ignore previous"):
        assert cue.lower() in block.lower(), (
            f"LLM-BENCH-002 must cue {cue!r} adversarial payload shape"
        )


def test_llm01_direct_injection_has_literal_payload_string(
    benchmark_text: str,
) -> None:
    block_start = benchmark_text.index("id: LLM-BENCH-001")
    block_end = benchmark_text.index("id: LLM-BENCH-002")
    block = benchmark_text[block_start:block_end]
    assert "Ignore previous instructions" in block, (
        "LLM-BENCH-001 must embed a literal adversarial payload string"
    )


def test_llm06_secret_leak_scenarios_cite_distinct_attack_shapes(
    benchmark_text: str,
) -> None:
    # LLM-BENCH-008 = PII in prompt; LLM-BENCH-009 = secret in spawn.
    block_008 = benchmark_text[
        benchmark_text.index("id: LLM-BENCH-008") :
        benchmark_text.index("id: LLM-BENCH-009")
    ]
    block_009 = benchmark_text[
        benchmark_text.index("id: LLM-BENCH-009") :
        benchmark_text.index("id: LLM-BENCH-010")
    ]
    # Shape 1: PII fields in a prompt template.
    assert "ssn" in block_008.lower(), "LLM-BENCH-008 must include PII payload"
    # Shape 2: secret (DB URL / API key) in a spawn prompt.
    assert "postgres://" in block_009.lower(), (
        "LLM-BENCH-009 must include a DB URL with embedded credential"
    )
    assert "sk-live" in block_009.lower(), (
        "LLM-BENCH-009 must include an API key payload"
    )


def test_every_scenario_has_prompt_template_and_expected_block(
    benchmark_text: str,
) -> None:
    all_ids = POSITIVE_SCENARIO_IDS + CONTROL_SCENARIO_IDS
    # Find (scenario_id, next_scenario_id_or_EOF) windows.
    for i, sid in enumerate(all_ids):
        start = benchmark_text.index(f"id: {sid}")
        if i + 1 < len(all_ids):
            end = benchmark_text.index(f"id: {all_ids[i + 1]}")
        else:
            end = len(benchmark_text)
        block = benchmark_text[start:end]
        assert "prompt_template:" in block, f"{sid} missing prompt_template"
        assert "expected:" in block, f"{sid} missing expected block"


def test_every_positive_scenario_has_must_flag_tags(benchmark_text: str) -> None:
    for sid in POSITIVE_SCENARIO_IDS:
        start = benchmark_text.index(f"id: {sid}")
        # look in the next ~120 lines
        window = "\n".join(
            benchmark_text[start:].splitlines()[:120]
        )
        assert "must_flag_tags:" in window, (
            f"{sid} positive scenario missing must_flag_tags"
        )


def test_every_control_has_must_not_flag_tags(benchmark_text: str) -> None:
    for sid in CONTROL_SCENARIO_IDS:
        start = benchmark_text.index(f"id: {sid}")
        window = "\n".join(benchmark_text[start:].splitlines()[:120])
        assert "must_not_flag_tags:" in window, (
            f"{sid} control scenario missing must_not_flag_tags"
        )
        assert "control_rationale:" in window, (
            f"{sid} control scenario missing control_rationale"
        )


def test_rubric_doc_exists_and_references_benchmark() -> None:
    assert RUBRIC_DOC.is_file(), f"missing rubric doc: {RUBRIC_DOC}"
    text = RUBRIC_DOC.read_text(encoding="utf-8")
    assert "owasp-llm-top-10.yaml" in text, (
        "rubric doc must reference the benchmark YAML"
    )
    for lm in range(1, 11):
        tag = f"LLM{lm:02d}"
        assert tag in text, f"rubric doc must document {tag}"


def test_rubric_doc_documents_deferred_skill_md() -> None:
    """Debate P0-1 mitigation: rubric doc must explicitly explain that
    SKILL.md amendment is deferred AND that the benchmark embeds rubric
    cues in prompt_template — so reviewers understand the shape is not
    defense theater."""
    text = RUBRIC_DOC.read_text(encoding="utf-8")
    assert "ADR-031" in text, "rubric doc must cite ADR-031 sentinel"
    assert "SP-NNN" in text, "rubric doc must cite SP-NNN chain"
    assert "prompt_template" in text, (
        "rubric doc must explain the benchmark-embeds-rubric mitigation"
    )


def test_total_scenario_count() -> None:
    assert len(POSITIVE_SCENARIO_IDS) == 14, "must ship 14 positive scenarios"
    assert len(CONTROL_SCENARIO_IDS) == 6, "must ship 6 control scenarios"
    assert (
        sum(EXPECTED_CATEGORY_COUNTS.values()) == 14
    ), "category counts must sum to 14 positive scenarios"
