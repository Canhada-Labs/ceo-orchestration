"""Tests for the consolidated _lib/frontmatter stdlib YAML parser.

PLAN-025 Batch E (F-scripts-14 P2) — ensures the new consolidated parser
matches expected behaviour across the 10 hand-rolled call sites in
scripts/ that will migrate to it during Sprint 26.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


from _lib.frontmatter import (  # noqa: E402
    extract_body,
    extract_metadata,
    parse_frontmatter,
)


class TestParseFrontmatter(unittest.TestCase):
    def test_empty_string(self):
        meta, body = parse_frontmatter("")
        self.assertEqual(meta, {})
        self.assertEqual(body, "")

    def test_no_frontmatter_returns_empty_and_original(self):
        raw = "# heading\nbody content\n"
        meta, body = parse_frontmatter(raw)
        self.assertEqual(meta, {})
        self.assertEqual(body, raw)

    def test_minimal_frontmatter(self):
        raw = "---\nid: X-001\n---\nbody\n"
        meta, body = parse_frontmatter(raw)
        self.assertEqual(meta, {"id": "X-001"})
        self.assertEqual(body, "body\n")

    def test_multiple_keys(self):
        raw = "---\nid: X-001\ntitle: My Title\nstatus: draft\n---\n"
        meta, _ = parse_frontmatter(raw)
        self.assertEqual(
            meta, {"id": "X-001", "title": "My Title", "status": "draft"}
        )

    def test_empty_value(self):
        raw = "---\nid:\ntitle: present\n---\nbody"
        meta, _ = parse_frontmatter(raw)
        self.assertEqual(meta, {"id": "", "title": "present"})

    def test_quoted_values_stripped(self):
        raw = '---\ntitle: "Hello World"\nsubtitle: \'q-subtitle\'\n---\n'
        meta, _ = parse_frontmatter(raw)
        self.assertEqual(meta, {"title": "Hello World", "subtitle": "q-subtitle"})

    def test_comment_and_blank_lines_skipped(self):
        raw = "---\n# comment\nkey1: v1\n\n# another comment\nkey2: v2\n---\n"
        meta, _ = parse_frontmatter(raw)
        self.assertEqual(meta, {"key1": "v1", "key2": "v2"})

    def test_malformed_line_skipped(self):
        raw = "---\nvalid: yes\nnot a key=value pair\nalso_valid: true\n---\n"
        meta, _ = parse_frontmatter(raw)
        # Line "not a key=value pair" has no colon matching _KEY_RE -> skipped
        self.assertEqual(meta, {"valid": "yes", "also_valid": "true"})

    def test_no_closing_delim(self):
        raw = "---\nid: X-001\ntitle: no close\nbody here\n"
        meta, body = parse_frontmatter(raw)
        # No closing `---` -> treat entire text as body, no frontmatter
        self.assertEqual(meta, {})
        self.assertEqual(body, raw)

    def test_key_with_dash_and_underscore(self):
        raw = "---\nplan_id: PLAN-001\nreviewed-by: Owner\n---\n"
        meta, _ = parse_frontmatter(raw)
        self.assertEqual(meta, {"plan_id": "PLAN-001", "reviewed-by": "Owner"})

    def test_body_preserves_multiple_newlines(self):
        raw = "---\nid: X\n---\nline1\n\nline2\n\n\nline3\n"
        _, body = parse_frontmatter(raw)
        self.assertEqual(body, "line1\n\nline2\n\n\nline3\n")

    def test_body_starts_with_markdown(self):
        raw = "---\nid: X\n---\n# Title\n\nParagraph\n"
        _, body = parse_frontmatter(raw)
        self.assertIn("# Title", body)
        self.assertIn("Paragraph", body)


class TestExtractBody(unittest.TestCase):
    def test_with_frontmatter(self):
        body = extract_body("---\nid: X\n---\nbody\n")
        self.assertEqual(body, "body\n")

    def test_without_frontmatter(self):
        body = extract_body("raw text")
        self.assertEqual(body, "raw text")


class TestExtractMetadata(unittest.TestCase):
    def test_with_frontmatter(self):
        meta = extract_metadata("---\nid: X\ntitle: T\n---\nbody\n")
        self.assertEqual(meta, {"id": "X", "title": "T"})

    def test_without_frontmatter(self):
        meta = extract_metadata("body only")
        self.assertEqual(meta, {})


class TestParserRejects(unittest.TestCase):
    """Deliberately unsupported shapes must not raise; just skip gracefully."""

    def test_nested_mapping_flattened(self):
        # Nested: `config:\n  key: value` — parser flattens indented keys
        # into the top level (`strip()` removes leading whitespace). This
        # is a known limitation documented in the module docstring
        # ("Unsupported: Nested mappings"); callers with nested needs
        # should use _lib/policy.py or write purpose-specific parsers.
        raw = "---\nid: X\nconfig:\n  key: val\nother: present\n---\n"
        meta, _ = parse_frontmatter(raw)
        self.assertIn("id", meta)
        self.assertIn("config", meta)
        self.assertEqual(meta["config"], "")
        # Indented `key: val` is flattened to top-level (limitation).
        self.assertEqual(meta.get("key"), "val")
        self.assertEqual(meta.get("other"), "present")

    def test_list_value_skipped(self):
        raw = "---\nitems:\n  - one\n  - two\n---\n"
        meta, _ = parse_frontmatter(raw)
        # `items:` is accepted (empty value); the `- one` / `- two` lines are
        # skipped because they don't start with a key.
        self.assertEqual(meta.get("items"), "")


if __name__ == "__main__":
    unittest.main()
