"""Fixture JSONL loader with schema hard caps.

ADR-063 §Fixture Trust Boundary + §Fixture corpus + C-P0-1 + C-P0-5
defenses. Fixture schema:

```
{
  "fixture_id": "security-review-001",
  "task_type": "security-review",
  "prompt": "...",                 # 32 <= len(utf8_bytes) <= 8192
  "acceptance_strict": ["..."],    # list[str], substring match targets
  "acceptance_llm_judge": "...",   # <= 1024 utf8 bytes
  "expected_tier": "opus",         # "opus"|"sonnet"|"haiku"
  "max_tokens": 2000,              # 32 <= int <= 4000
  "seed": 42                       # int, required — no default (reproducibility)
}
```

Stdlib-only. No external deps. Fail-closed on schema violation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional

# Round 1 C-P0-5 hard caps — fixture-controlled fields bounded to prevent
# DoS of the validation pipeline AND runaway cost post-dispatch.
MAX_TOKENS_CAP = 4000
MAX_TOKENS_MIN = 32
PROMPT_MIN_BYTES = 32
PROMPT_MAX_BYTES = 8192
ACCEPTANCE_JUDGE_MAX_BYTES = 1024
VALID_TASK_TYPES = frozenset(
    {
        "security-review",
        "code-review",
        "performance-triage",
        "test-design",
        "docs-writing",
    }
)
VALID_TIERS = frozenset({"opus", "sonnet", "haiku"})


class FixtureSchemaError(ValueError):
    """Raised when a fixture record violates the ADR-063 schema.

    Attributes preserved:
    - `fixture_id`: the id field if parseable; otherwise None
    - `field`: which schema field failed
    - `reason`: human-readable reason
    """

    def __init__(
        self,
        reason: str,
        fixture_id: Optional[str] = None,
        field_name: Optional[str] = None,
    ) -> None:
        super().__init__(reason)
        self.fixture_id = fixture_id
        self.field_name = field_name
        self.reason = reason


@dataclass(frozen=True)
class Fixture:
    """A single tournament fixture record (validated per ADR-063)."""

    fixture_id: str
    task_type: str
    prompt: str
    acceptance_strict: List[str]
    acceptance_llm_judge: str
    expected_tier: str
    max_tokens: int
    seed: int

    @property
    def prompt_bytes(self) -> int:
        return len(self.prompt.encode("utf-8"))

    @property
    def judge_bytes(self) -> int:
        return len(self.acceptance_llm_judge.encode("utf-8"))


def _validate_record(record: dict) -> Fixture:
    """Validate a raw dict against ADR-063 schema.

    Raises FixtureSchemaError on any violation. Returns Fixture on success.
    """
    fixture_id = record.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id:
        raise FixtureSchemaError(
            "fixture_id missing or not a non-empty string",
            fixture_id=None,
            field_name="fixture_id",
        )

    task_type = record.get("task_type")
    if task_type not in VALID_TASK_TYPES:
        raise FixtureSchemaError(
            f"task_type {task_type!r} not in {sorted(VALID_TASK_TYPES)}",
            fixture_id=fixture_id,
            field_name="task_type",
        )

    prompt = record.get("prompt")
    if not isinstance(prompt, str):
        raise FixtureSchemaError(
            "prompt missing or not a string",
            fixture_id=fixture_id,
            field_name="prompt",
        )
    prompt_bytes = len(prompt.encode("utf-8"))
    if prompt_bytes < PROMPT_MIN_BYTES:
        raise FixtureSchemaError(
            f"prompt too short: {prompt_bytes} bytes < {PROMPT_MIN_BYTES} min "
            "(prevents empty-prompt projection gaming)",
            fixture_id=fixture_id,
            field_name="prompt",
        )
    if prompt_bytes > PROMPT_MAX_BYTES:
        raise FixtureSchemaError(
            f"prompt too long: {prompt_bytes} bytes > {PROMPT_MAX_BYTES} max",
            fixture_id=fixture_id,
            field_name="prompt",
        )

    acceptance_strict = record.get("acceptance_strict")
    if not isinstance(acceptance_strict, list) or not all(
        isinstance(x, str) for x in acceptance_strict
    ):
        raise FixtureSchemaError(
            "acceptance_strict must be list[str]",
            fixture_id=fixture_id,
            field_name="acceptance_strict",
        )

    acceptance_llm_judge = record.get("acceptance_llm_judge")
    if not isinstance(acceptance_llm_judge, str):
        raise FixtureSchemaError(
            "acceptance_llm_judge missing or not a string",
            fixture_id=fixture_id,
            field_name="acceptance_llm_judge",
        )
    if len(acceptance_llm_judge.encode("utf-8")) > ACCEPTANCE_JUDGE_MAX_BYTES:
        raise FixtureSchemaError(
            f"acceptance_llm_judge too long: > {ACCEPTANCE_JUDGE_MAX_BYTES} bytes",
            fixture_id=fixture_id,
            field_name="acceptance_llm_judge",
        )

    expected_tier = record.get("expected_tier")
    if expected_tier not in VALID_TIERS:
        raise FixtureSchemaError(
            f"expected_tier {expected_tier!r} not in {sorted(VALID_TIERS)}",
            fixture_id=fixture_id,
            field_name="expected_tier",
        )

    max_tokens = record.get("max_tokens")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool):
        raise FixtureSchemaError(
            "max_tokens must be int (not bool)",
            fixture_id=fixture_id,
            field_name="max_tokens",
        )
    if max_tokens < MAX_TOKENS_MIN:
        raise FixtureSchemaError(
            f"max_tokens too small: {max_tokens} < {MAX_TOKENS_MIN}",
            fixture_id=fixture_id,
            field_name="max_tokens",
        )
    if max_tokens > MAX_TOKENS_CAP:
        raise FixtureSchemaError(
            f"max_tokens exceeds cap: {max_tokens} > {MAX_TOKENS_CAP}",
            fixture_id=fixture_id,
            field_name="max_tokens",
        )

    # Round 1 C-P0-5 — seed REQUIRED, no default. Missing seed breaks
    # reproducibility claim. Default-deny.
    if "seed" not in record:
        raise FixtureSchemaError(
            "seed is required — no default allowed (breaks reproducibility)",
            fixture_id=fixture_id,
            field_name="seed",
        )
    seed = record["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise FixtureSchemaError(
            "seed must be int (not bool)",
            fixture_id=fixture_id,
            field_name="seed",
        )

    return Fixture(
        fixture_id=fixture_id,
        task_type=task_type,
        prompt=prompt,
        acceptance_strict=list(acceptance_strict),
        acceptance_llm_judge=acceptance_llm_judge,
        expected_tier=expected_tier,
        max_tokens=max_tokens,
        seed=seed,
    )


def load_fixture_file(path: Path) -> List[Fixture]:
    """Load + validate a single JSONL file. Raises on first violation.

    Returns list of Fixture records. Blank lines are skipped. JSON parse
    errors are wrapped in FixtureSchemaError for uniform handling.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Fixture file not found: {path}")

    fixtures: List[Fixture] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FixtureSchemaError(
                    f"JSON parse error at {path}:{line_no}: {exc}",
                    field_name="__json_parse__",
                ) from exc
            fixtures.append(_validate_record(record))
    return fixtures


def load_corpus(fixtures_dir: Path) -> List[Fixture]:
    """Load + validate all *.jsonl fixture files under a directory.

    Files are loaded in lexicographic order for determinism. fixture_id
    uniqueness is enforced across the corpus.
    """
    fixtures_dir = Path(fixtures_dir)
    if not fixtures_dir.is_dir():
        raise FileNotFoundError(f"Fixtures dir not found: {fixtures_dir}")

    all_fixtures: List[Fixture] = []
    seen_ids: set = set()
    for jsonl_path in sorted(fixtures_dir.glob("*.jsonl")):
        for fixture in load_fixture_file(jsonl_path):
            if fixture.fixture_id in seen_ids:
                raise FixtureSchemaError(
                    f"duplicate fixture_id across corpus: {fixture.fixture_id}",
                    fixture_id=fixture.fixture_id,
                    field_name="fixture_id",
                )
            seen_ids.add(fixture.fixture_id)
            all_fixtures.append(fixture)
    return all_fixtures
