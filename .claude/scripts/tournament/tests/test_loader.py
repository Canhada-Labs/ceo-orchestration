"""Tests for loader.py — fixture schema hard-caps + contract validation.

Round 1 C-P0-5 + QA contract-test surface. ~18 tests covering:
- required fields
- task_type enum
- prompt length bounds (min 32 / max 8192 utf-8 bytes)
- max_tokens bounds (32-4000)
- seed required (no default)
- expected_tier enum
- acceptance_llm_judge byte cap
- JSONL parse errors
- fixture_id uniqueness across corpus
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import loader


def _valid_record(**over) -> dict:
    """Return a minimal valid fixture record; apply `over` to mutate fields."""
    base = {
        "fixture_id": "test-001",
        "task_type": "security-review",
        "prompt": "Review the following auth middleware for bypass risks carefully please.",
        "acceptance_strict": ["token not logged"],
        "acceptance_llm_judge": "Does the review cover OWASP A01-A10?",
        "expected_tier": "opus",
        "max_tokens": 2000,
        "seed": 42,
    }
    base.update(over)
    return base


class TestValidateRecord(unittest.TestCase):
    def test_valid_record_parses(self):
        fixture = loader._validate_record(_valid_record())
        self.assertEqual(fixture.fixture_id, "test-001")
        self.assertEqual(fixture.task_type, "security-review")
        self.assertEqual(fixture.max_tokens, 2000)
        self.assertEqual(fixture.seed, 42)

    def test_missing_fixture_id_raises(self):
        rec = _valid_record()
        del rec["fixture_id"]
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(rec)
        self.assertEqual(ctx.exception.field_name, "fixture_id")

    def test_empty_fixture_id_raises(self):
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(fixture_id=""))

    def test_invalid_task_type_raises(self):
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(task_type="unknown-type"))
        self.assertEqual(ctx.exception.field_name, "task_type")

    def test_all_5_valid_task_types_accepted(self):
        for tt in [
            "security-review",
            "code-review",
            "performance-triage",
            "test-design",
            "docs-writing",
        ]:
            fixture = loader._validate_record(_valid_record(task_type=tt))
            self.assertEqual(fixture.task_type, tt)

    def test_prompt_below_min_bytes_raises(self):
        # Below 32 byte min
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(prompt="a" * 31))
        self.assertIn("too short", ctx.exception.reason)

    def test_prompt_at_exactly_min_bytes_passes(self):
        # Exactly 32 bytes
        fixture = loader._validate_record(_valid_record(prompt="a" * 32))
        self.assertEqual(fixture.prompt_bytes, 32)

    def test_prompt_above_max_bytes_raises(self):
        # 8193 bytes > 8192 max
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(prompt="a" * 8193))
        self.assertIn("too long", ctx.exception.reason)

    def test_prompt_at_exactly_max_bytes_passes(self):
        fixture = loader._validate_record(_valid_record(prompt="a" * 8192))
        self.assertEqual(fixture.prompt_bytes, 8192)

    def test_acceptance_strict_must_be_list_of_strings(self):
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(acceptance_strict="not a list"))
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(acceptance_strict=[1, 2, 3]))

    def test_acceptance_llm_judge_byte_cap(self):
        over_cap = "x" * 1025
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(acceptance_llm_judge=over_cap))
        self.assertEqual(ctx.exception.field_name, "acceptance_llm_judge")

    def test_invalid_tier_raises(self):
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(expected_tier="gpt4"))
        self.assertEqual(ctx.exception.field_name, "expected_tier")

    def test_max_tokens_below_min_raises(self):
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(max_tokens=31))
        self.assertIn("too small", ctx.exception.reason)

    def test_max_tokens_above_cap_raises(self):
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(_valid_record(max_tokens=4001))
        self.assertIn("exceeds cap", ctx.exception.reason)

    def test_max_tokens_bool_rejected(self):
        # isinstance(True, int) is True in Python — explicit bool check
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(max_tokens=True))

    def test_seed_missing_raises(self):
        # Seed is REQUIRED per Round 1 C-P0-5 — no default allowed
        rec = _valid_record()
        del rec["seed"]
        with self.assertRaises(loader.FixtureSchemaError) as ctx:
            loader._validate_record(rec)
        self.assertIn("required", ctx.exception.reason)

    def test_seed_bool_rejected(self):
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(seed=False))

    def test_seed_non_int_rejected(self):
        with self.assertRaises(loader.FixtureSchemaError):
            loader._validate_record(_valid_record(seed="42"))


class TestLoadFixtureFile(unittest.TestCase):
    def test_load_valid_jsonl(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "fixtures.jsonl"
            records = [_valid_record(fixture_id=f"fx-{i:03d}") for i in range(3)]
            path.write_text(
                "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
            )
            fixtures = loader.load_fixture_file(path)
            self.assertEqual(len(fixtures), 3)
            self.assertEqual(fixtures[0].fixture_id, "fx-000")

    def test_blank_and_comment_lines_skipped(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "fixtures.jsonl"
            content = (
                "\n"
                "# this is a comment\n"
                + json.dumps(_valid_record(fixture_id="fx-a"))
                + "\n"
                "\n"
                + json.dumps(_valid_record(fixture_id="fx-b"))
                + "\n"
            )
            path.write_text(content, encoding="utf-8")
            fixtures = loader.load_fixture_file(path)
            self.assertEqual(len(fixtures), 2)

    def test_invalid_json_raises_with_location(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "fixtures.jsonl"
            path.write_text(
                json.dumps(_valid_record()) + "\n{ malformed json\n",
                encoding="utf-8",
            )
            with self.assertRaises(loader.FixtureSchemaError) as ctx:
                loader.load_fixture_file(path)
            self.assertIn("JSON parse error", ctx.exception.reason)
            self.assertIn(":2:", ctx.exception.reason)  # line 2 is malformed

    def test_missing_file_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            loader.load_fixture_file(Path("/nonexistent/fixtures.jsonl"))


class TestLoadCorpus(unittest.TestCase):
    def test_load_corpus_merges_files_in_lex_order(self):
        with TemporaryDirectory() as d:
            Path(d, "b-second.jsonl").write_text(
                json.dumps(_valid_record(fixture_id="fx-b")) + "\n", encoding="utf-8"
            )
            Path(d, "a-first.jsonl").write_text(
                json.dumps(_valid_record(fixture_id="fx-a")) + "\n", encoding="utf-8"
            )
            fixtures = loader.load_corpus(Path(d))
            self.assertEqual(len(fixtures), 2)
            # Lex order: a-first before b-second
            self.assertEqual(fixtures[0].fixture_id, "fx-a")
            self.assertEqual(fixtures[1].fixture_id, "fx-b")

    def test_duplicate_fixture_id_across_corpus_raises(self):
        with TemporaryDirectory() as d:
            Path(d, "a.jsonl").write_text(
                json.dumps(_valid_record(fixture_id="dup")) + "\n", encoding="utf-8"
            )
            Path(d, "b.jsonl").write_text(
                json.dumps(_valid_record(fixture_id="dup")) + "\n", encoding="utf-8"
            )
            with self.assertRaises(loader.FixtureSchemaError) as ctx:
                loader.load_corpus(Path(d))
            self.assertIn("duplicate fixture_id", ctx.exception.reason)

    def test_missing_dir_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            loader.load_corpus(Path("/nonexistent/dir"))


if __name__ == "__main__":
    unittest.main()
