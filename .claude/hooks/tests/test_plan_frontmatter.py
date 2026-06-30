"""Unit tests for _lib/plan_frontmatter.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


from _lib import plan_frontmatter as fm  # noqa: E402


class TestExtractFrontmatter(unittest.TestCase):

    def test_simple(self):
        text = "---\nid: PLAN-001\nstatus: draft\n---\n\n# Body"
        self.assertIn("id: PLAN-001", fm.extract_frontmatter_text(text))

    def test_no_frontmatter(self):
        self.assertEqual(fm.extract_frontmatter_text("# Just a body"), "")

    def test_empty(self):
        self.assertEqual(fm.extract_frontmatter_text(""), "")


class TestParseFrontmatter(unittest.TestCase):

    def test_basic_key_value(self):
        text = "---\nid: PLAN-001\nstatus: draft\nowner: CEO\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["id"], "PLAN-001")
        self.assertEqual(d["status"], "draft")
        self.assertEqual(d["owner"], "CEO")

    def test_inline_list(self):
        text = "---\nrelated_commits: [abc123, def456]\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["related_commits"], ["abc123", "def456"])

    def test_empty_inline_list(self):
        text = "---\ndepends_on: []\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["depends_on"], [])

    def test_multiline_list(self):
        text = (
            "---\n"
            "related_commits:\n"
            "  - abc123\n"
            "  - def456\n"
            "  - 789abc\n"
            "---\n"
        )
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["related_commits"], ["abc123", "def456", "789abc"])

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(fm.parse_frontmatter("no dashes here"), {})

    def test_quoted_string(self):
        text = '---\ntitle: "My Title"\n---\n'
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["title"], "My Title")

    def test_empty_frontmatter(self):
        text = "---\n\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d, {})

    def test_comment_line_ignored(self):
        text = "---\n# a comment\nid: PLAN-001\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["id"], "PLAN-001")
        self.assertNotIn("# a comment", d)


class TestAbandonmentReason(unittest.TestCase):

    def test_present_header(self):
        text = "# Title\n\n## Abandonment reason\n\nSuperseded by PLAN-006."
        self.assertTrue(fm.has_abandonment_reason(text))

    def test_absent(self):
        text = "# Title\n\n## Context\n\nSome content."
        self.assertFalse(fm.has_abandonment_reason(text))

    def test_case_insensitive(self):
        text = "## abandonment REASON\nyep"
        self.assertTrue(fm.has_abandonment_reason(text))

    def test_empty(self):
        self.assertFalse(fm.has_abandonment_reason(""))


# ---------------------------------------------------------------------------
# PLAN-019 P1-QA-2 — edge-case extensions per testing-strategy skill rule
# (≥5 tests per public function). Public API covered:
#   - extract_frontmatter_text  (edge: CRLF, missing closer, unicode)
#   - parse_frontmatter          (edge: duplicate keys, ISO date variants,
#     unknown status-like values, malformed list, field-order sensitivity)
#   - has_abandonment_reason     (edge: whitespace variants, nested header)
# ---------------------------------------------------------------------------


class TestExtractFrontmatterEdgeCases(unittest.TestCase):

    def test_crlf_line_endings_accepted(self):
        """Windows CRLF-terminated frontmatter still extracted."""
        text = "---\r\nid: PLAN-050\r\n---\r\n\r\n# Body"
        extracted = fm.extract_frontmatter_text(text)
        self.assertIn("id: PLAN-050", extracted)

    def test_missing_closer_returns_empty(self):
        """`---` open without matching close → no frontmatter found."""
        text = "---\nid: PLAN-001\nstatus: draft\n\n# Body (no closer)"
        self.assertEqual(fm.extract_frontmatter_text(text), "")

    def test_opener_not_at_top_returns_empty(self):
        """Frontmatter must begin at offset 0 (regex uses ^)."""
        text = "# Title\n---\nid: PLAN-001\n---\n"
        self.assertEqual(fm.extract_frontmatter_text(text), "")

    def test_unicode_body_preserved(self):
        """Non-ASCII scalar values pass through intact."""
        text = "---\ntitle: Ada Lovelaçe\n---\n"
        extracted = fm.extract_frontmatter_text(text)
        self.assertIn("Ada Lovelaçe", extracted)


class TestParseFrontmatterEdgeCases(unittest.TestCase):

    def test_duplicate_keys_last_wins(self):
        """Regex extractor walks top-down; later duplicates overwrite earlier.

        Documents current behavior — validate-governance will enforce plan
        schema elsewhere, but parser must not crash on malformed input.
        """
        text = "---\nstatus: draft\nstatus: reviewed\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["status"], "reviewed")

    def test_iso8601_date_variants_are_preserved_as_strings(self):
        """No type coercion — dates stay as raw strings (per module docstring)."""
        for date_str in ["2026-04-17", "2026-4-17", "2026-04-17T00:00:00"]:
            text = f"---\ncompleted_at: {date_str}\n---\n"
            d = fm.parse_frontmatter(text)
            self.assertEqual(d["completed_at"], date_str)

    def test_unknown_status_value_parses_without_error(self):
        """Parser is schema-agnostic — any string value accepted.

        Schema enforcement lives in plan_edit hook / policy — not here.
        """
        text = "---\nstatus: quantum-superposition\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["status"], "quantum-superposition")

    def test_list_with_whitespace_entries_stripped(self):
        """Inline list items strip surrounding whitespace + quotes."""
        text = '---\nrelated_commits: [ "abc123" , def456 ,  ghi789 ]\n---\n'
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["related_commits"], ["abc123", "def456", "ghi789"])

    def test_multiline_list_preserves_order(self):
        """Multi-line bullet list retains declared order (first→last)."""
        text = (
            "---\n"
            "depends_on:\n"
            "  - PLAN-010\n"
            "  - PLAN-011\n"
            "  - PLAN-009\n"
            "---\n"
        )
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["depends_on"], ["PLAN-010", "PLAN-011", "PLAN-009"])

    def test_field_order_insensitive(self):
        """Swapping declaration order must yield equivalent dict values."""
        a = "---\nid: PLAN-1\nstatus: draft\n---\n"
        b = "---\nstatus: draft\nid: PLAN-1\n---\n"
        self.assertEqual(fm.parse_frontmatter(a), fm.parse_frontmatter(b))

    def test_empty_key_value_is_empty_string(self):
        """Key with empty inline value → empty string (not None)."""
        text = "---\nowner:\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["owner"], "")

    def test_malformed_input_returns_empty_dict(self):
        """Non-frontmatter text → {}."""
        self.assertEqual(fm.parse_frontmatter("completely unstructured text"), {})

    def test_value_with_embedded_colon_is_preserved(self):
        """URL-like values with `:` keep everything after the first `:`."""
        text = "---\nhomepage: https://example.com/foo\n---\n"
        d = fm.parse_frontmatter(text)
        self.assertEqual(d["homepage"], "https://example.com/foo")


class TestAbandonmentReasonEdgeCases(unittest.TestCase):

    def test_leading_whitespace_in_header_rejected(self):
        """Markdown header must start at column 0 — indented headers aren't real."""
        text = "   ## Abandonment reason\nsomething"
        self.assertFalse(fm.has_abandonment_reason(text))

    def test_multiple_hash_levels_not_matched(self):
        """### (h3) is NOT matched — only ## (h2) per module contract."""
        text = "### Abandonment reason\nsomething"
        self.assertFalse(fm.has_abandonment_reason(text))

    def test_additional_trailing_content_on_line_rejected(self):
        """Header line with trailing non-whitespace is rejected by strict `$` anchor."""
        text = "## Abandonment reason — for PLAN-099\nbody"
        # The regex requires `^##\s+Abandonment\s+reason\s*$` — trailing
        # em-dash content violates `$` anchor.
        self.assertFalse(fm.has_abandonment_reason(text))
