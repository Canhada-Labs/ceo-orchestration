"""Tests for scorer.py — strict-mode classification + adversarial safety.

Round 1 C-P0-7 mutation target; QA F-QA adversarial-safe requirement.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from .. import scorer


def _make_fixture(acceptance_strict=None):
    return SimpleNamespace(
        fixture_id="fx-001",
        task_type="security-review",
        prompt="test",
        acceptance_strict=acceptance_strict if acceptance_strict is not None else ["pass"],
        acceptance_llm_judge="ok?",
        expected_tier="opus",
        max_tokens=1000,
        seed=1,
    )


def _make_response(content):
    return SimpleNamespace(content=content)


class TestScoreStrict(unittest.TestCase):
    def test_pass_when_all_acceptance_present(self):
        fixture = _make_fixture(["alpha", "beta"])
        response = _make_response("alpha is present and beta is here too")
        self.assertEqual(scorer.score_strict(fixture, response), "pass")

    def test_fail_when_missing_one_needle(self):
        fixture = _make_fixture(["alpha", "beta"])
        response = _make_response("alpha only — beta not mentioned as required keyword here")
        # 'beta' IS in there — check it reports fail when truly missing
        fixture2 = _make_fixture(["alpha", "delta"])
        self.assertEqual(scorer.score_strict(fixture2, response), "fail")

    def test_errored_on_empty_content(self):
        fixture = _make_fixture(["alpha"])
        response = _make_response("")
        self.assertEqual(scorer.score_strict(fixture, response), "errored")

    def test_errored_on_whitespace_only_content(self):
        fixture = _make_fixture(["alpha"])
        response = _make_response("   \n\t   ")
        self.assertEqual(scorer.score_strict(fixture, response), "errored")

    def test_errored_on_none_response(self):
        fixture = _make_fixture(["alpha"])
        self.assertEqual(scorer.score_strict(fixture, None), "errored")

    def test_errored_on_response_with_no_content_attr(self):
        fixture = _make_fixture(["alpha"])
        response = SimpleNamespace()  # no .content
        self.assertEqual(scorer.score_strict(fixture, response), "errored")

    def test_pass_with_empty_acceptance_vacuously(self):
        fixture = _make_fixture([])
        response = _make_response("anything")
        self.assertEqual(scorer.score_strict(fixture, response), "pass")

    def test_case_insensitive_match(self):
        fixture = _make_fixture(["Password"])
        response = _make_response("the password handling here is reasonable")
        self.assertEqual(scorer.score_strict(fixture, response), "pass")

    def test_homoglyph_substitution_does_not_trick_via_nfkc(self):
        # Cyrillic 'а' (U+0430) should be normalized-distinct from Latin 'a'
        # WAIT — NFKC does NOT map Cyrillic-а → Latin-a (distinct scripts).
        # So this test verifies that homoglyph SUBSTITUTION in acceptance
        # does NOT spuriously match Latin content. Acceptance "pаssword"
        # with Cyrillic-а should NOT pass when response has Latin "password".
        fixture = _make_fixture(["p\u0430ssword"])  # Cyrillic а
        response = _make_response("the password is hashed carefully")  # Latin a
        # Expected: FAIL (they are genuinely different characters post-NFKC)
        self.assertEqual(scorer.score_strict(fixture, response), "fail")

    def test_nfkc_handles_compatibility_forms(self):
        # Full-width Latin FF01 etc. NFKC maps to ASCII
        # Full-width 'Ａ' (U+FF21) → 'A' under NFKC
        fixture = _make_fixture(["A"])
        response = _make_response("the \uff21 variable is used")  # full-width
        self.assertEqual(scorer.score_strict(fixture, response), "pass")

    def test_non_utf8_bytes_content_errored(self):
        # bytes with invalid UTF-8 should mark errored, not crash
        fixture = _make_fixture(["alpha"])
        response = SimpleNamespace(content=b"\xff\xfe invalid")
        # _safe_text will fail to decode bytes with errors='strict' → None
        result = scorer.score_strict(fixture, response)
        self.assertEqual(result, "errored")

    def test_invalid_acceptance_item_type_errored(self):
        fixture = _make_fixture([123, "alpha"])  # int not str
        response = _make_response("alpha")
        self.assertEqual(scorer.score_strict(fixture, response), "errored")

    def test_never_raises_on_weird_input(self):
        """Adversarial-safe: no exception bubbles out of scorer."""
        fixture = _make_fixture(["x"])
        # Various weird inputs — all must return a string verdict
        for weird in [None, 0, [], {}, "", SimpleNamespace()]:
            with self.subTest(weird=weird):
                result = scorer.score_strict(fixture, weird)
                self.assertIn(result, {"pass", "fail", "errored"})


class TestClassifyBulk(unittest.TestCase):
    def test_classify_pass_returns_verdict_only(self):
        fixture = _make_fixture(["alpha"])
        response = _make_response("alpha is there")
        result = scorer.classify_bulk(fixture, response)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["mode"], "strict")
        self.assertNotIn("missing_needles", result)

    def test_classify_fail_reports_missing_needles(self):
        fixture = _make_fixture(["alpha", "beta", "gamma"])
        response = _make_response("only alpha is here")
        result = scorer.classify_bulk(fixture, response)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(set(result["missing_needles"]), {"beta", "gamma"})

    def test_classify_errored_empty(self):
        fixture = _make_fixture(["alpha"])
        response = _make_response("")
        result = scorer.classify_bulk(fixture, response)
        self.assertEqual(result["verdict"], "errored")
        self.assertEqual(result["reason"], "empty_output")


if __name__ == "__main__":
    unittest.main()
