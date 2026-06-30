"""Unit tests for _lib/tokens.py — spawn response token extraction.

PLAN-006 Phase 5a (ADR-016, R-SB4 null semantics).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


from _lib import tokens  # noqa: E402


class TestExtractClaudeShape(unittest.TestCase):
    def test_usage_input_output_tokens(self):
        r = {"usage": {"input_tokens": 100, "output_tokens": 250}}
        self.assertEqual(tokens.extract_tokens(r), (100, 250))

    def test_usage_partial_input_only(self):
        r = {"usage": {"input_tokens": 42}}
        self.assertEqual(tokens.extract_tokens(r), (42, None))

    def test_usage_partial_output_only(self):
        r = {"usage": {"output_tokens": 88}}
        self.assertEqual(tokens.extract_tokens(r), (None, 88))


class TestExtractGeminiShape(unittest.TestCase):
    def test_usage_metadata_camelcase(self):
        r = {"usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 1200}}
        self.assertEqual(tokens.extract_tokens(r), (500, 1200))

    def test_usage_metadata_snake_case(self):
        r = {"usageMetadata": {"prompt_token_count": 50, "completion_token_count": 75}}
        self.assertEqual(tokens.extract_tokens(r), (50, 75))

    def test_nested_usage_with_gemini_field_names(self):
        r = {"usage": {"promptTokenCount": 10, "candidatesTokenCount": 20}}
        self.assertEqual(tokens.extract_tokens(r), (10, 20))


class TestExtractOpenAIShape(unittest.TestCase):
    def test_prompt_tokens_completion_tokens(self):
        r = {"usage": {"prompt_tokens": 333, "completion_tokens": 444}}
        self.assertEqual(tokens.extract_tokens(r), (333, 444))


class TestExtractLegacyShape(unittest.TestCase):
    def test_top_level_totalTokens_only(self):
        r = {"totalTokens": 2000}
        self.assertEqual(tokens.extract_tokens(r), (None, 2000))


class TestFailOpenContract(unittest.TestCase):
    def test_none_input(self):
        self.assertEqual(tokens.extract_tokens(None), (None, None))

    def test_empty_dict(self):
        self.assertEqual(tokens.extract_tokens({}), (None, None))

    def test_not_a_dict(self):
        self.assertEqual(tokens.extract_tokens("weird"), (None, None))
        self.assertEqual(tokens.extract_tokens([1, 2, 3]), (None, None))
        self.assertEqual(tokens.extract_tokens(42), (None, None))

    def test_unknown_shape(self):
        r = {"foo": "bar", "baz": 42}
        self.assertEqual(tokens.extract_tokens(r), (None, None))

    def test_malformed_usage_block(self):
        r = {"usage": "not a dict"}
        self.assertEqual(tokens.extract_tokens(r), (None, None))

    def test_negative_values_rejected(self):
        r = {"usage": {"input_tokens": -5, "output_tokens": 10}}
        self.assertEqual(tokens.extract_tokens(r), (None, 10))

    def test_nan_rejected(self):
        r = {"usage": {"input_tokens": float("nan"), "output_tokens": 42}}
        self.assertEqual(tokens.extract_tokens(r), (None, 42))

    def test_string_numeric_accepted(self):
        r = {"usage": {"input_tokens": "100", "output_tokens": "200"}}
        self.assertEqual(tokens.extract_tokens(r), (100, 200))

    def test_string_non_numeric_rejected(self):
        r = {"usage": {"input_tokens": "lots", "output_tokens": "more"}}
        self.assertEqual(tokens.extract_tokens(r), (None, None))

    def test_bool_rejected(self):
        r = {"usage": {"input_tokens": True, "output_tokens": False}}
        self.assertEqual(tokens.extract_tokens(r), (None, None))


class TestTotalTokens(unittest.TestCase):
    def test_explicit_totalTokens(self):
        self.assertEqual(tokens.total_tokens({"totalTokens": 999}), 999)

    def test_total_tokens_snake_case(self):
        self.assertEqual(tokens.total_tokens({"total_tokens": 500}), 500)

    def test_sum_of_in_and_out(self):
        r = {"usage": {"input_tokens": 100, "output_tokens": 200}}
        self.assertEqual(tokens.total_tokens(r), 300)

    def test_out_only_when_no_sum(self):
        r = {"usage": {"output_tokens": 77}}
        self.assertEqual(tokens.total_tokens(r), 77)

    def test_none_when_no_data(self):
        self.assertIsNone(tokens.total_tokens({}))
        self.assertIsNone(tokens.total_tokens(None))


if __name__ == "__main__":
    unittest.main()
