"""PLAN-043 Phase 1 — _agent_frontmatter unit tests.

Covers:
- parse_model_field happy path + edge cases (BOM, quotes, comments,
  missing file, no frontmatter, empty value)
- detect_adopter_override matrix (match, override, missing, conservative)
- CLI entrypoint --detect-override + --parse-model exit codes
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli._agent_frontmatter import (  # noqa: E402
    _serialize_for_identity_test,
    detect_adopter_override,
    parse_model_field,
)


class AgentFrontmatterTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(
            prefix="plan-043-frontmatter-"
        )
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, content):
        p = self.tmp / name
        p.write_text(content, encoding="utf-8")
        return p


class TestParseModelField(AgentFrontmatterTestBase):
    def test_simple_frontmatter(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            name: code-reviewer
            model: claude-opus-4-8
            ---

            Body here.
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-opus-4-8")

    def test_model_field_with_double_quotes(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            model: "claude-sonnet-4-6"
            ---
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-sonnet-4-6")

    def test_model_field_with_single_quotes(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            model: 'claude-haiku-4-5-20251001'
            ---
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-haiku-4-5-20251001")

    def test_model_field_with_inline_comment(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            model: claude-opus-4-8  # pinned per VETO floor
            ---
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-opus-4-8")

    def test_model_field_empty_means_none(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            name: x
            model:
            ---
        """).lstrip())
        self.assertIsNone(parse_model_field(p))

    def test_no_model_field(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            name: x
            description: y
            ---
        """).lstrip())
        self.assertIsNone(parse_model_field(p))

    def test_no_frontmatter(self):
        p = self._write("a.md", "Just body text, no frontmatter.\n")
        self.assertIsNone(parse_model_field(p))

    def test_missing_file(self):
        p = self.tmp / "does_not_exist.md"
        self.assertIsNone(parse_model_field(p))

    def test_bom_prefix(self):
        # utf-8-sig write mode prepends BOM bytes; reading with
        # utf-8-sig auto-strips. Helper uses utf-8-sig encoding.
        content = "---\nmodel: claude-opus-4-8\n---\n"
        p = self.tmp / "a.md"
        p.write_text(content, encoding="utf-8-sig")
        self.assertEqual(parse_model_field(p), "claude-opus-4-8")

    def test_hash_inside_quotes_not_comment(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            model: "claude-opus-4-8#with-hash"
            ---
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-opus-4-8#with-hash")

    def test_frontmatter_ends_at_second_fence(self):
        p = self._write("a.md", textwrap.dedent("""
            ---
            model: claude-opus-4-8
            ---

            ---
            model: never-read
            ---
        """).lstrip())
        self.assertEqual(parse_model_field(p), "claude-opus-4-8")


class TestDetectAdopterOverride(AgentFrontmatterTestBase):
    def _mk(self, name, model_value):
        content = "---\nmodel: {m}\n---\n".format(m=model_value)
        return self._write(name, content)

    def test_matching_models_not_override(self):
        a = self._mk("adopter.md", "claude-opus-4-8")
        b = self._mk("baseline.md", "claude-opus-4-8")
        self.assertFalse(detect_adopter_override(a, b))

    def test_different_models_is_override(self):
        a = self._mk("adopter.md", "claude-sonnet-4-6")
        b = self._mk("baseline.md", "claude-opus-4-8")
        self.assertTrue(detect_adopter_override(a, b))

    def test_baseline_missing_adopter_has_value_override(self):
        a = self._mk("adopter.md", "claude-opus-4-8")
        # baseline file not created
        b = self.tmp / "baseline_missing.md"
        self.assertTrue(detect_adopter_override(a, b))

    def test_adopter_missing_field_but_baseline_has_value_override(self):
        a = self._write("adopter.md", "---\nname: x\n---\n")
        b = self._mk("baseline.md", "claude-opus-4-8")
        self.assertTrue(detect_adopter_override(a, b))

    def test_both_missing_returns_false(self):
        a = self._write("adopter.md", "---\nname: x\n---\n")
        b = self._write("baseline.md", "---\nname: y\n---\n")
        self.assertFalse(detect_adopter_override(a, b))


class TestCliEntrypoint(AgentFrontmatterTestBase):
    def _run_cli(self, *args):
        module_path = (
            Path(__file__).resolve().parent.parent
            / "_agent_frontmatter.py"
        )
        return subprocess.run(
            [sys.executable, str(module_path), *args],
            capture_output=True,
            text=True,
        )

    def test_detect_override_no_override_exits_0(self):
        a = self._write(
            "a.md", "---\nmodel: claude-opus-4-8\n---\n"
        )
        b = self._write(
            "b.md", "---\nmodel: claude-opus-4-8\n---\n"
        )
        r = self._run_cli("--detect-override", str(a), str(b))
        self.assertEqual(r.returncode, 0)

    def test_detect_override_detects_override_exits_1(self):
        a = self._write(
            "a.md", "---\nmodel: claude-sonnet-4-6\n---\n"
        )
        b = self._write(
            "b.md", "---\nmodel: claude-opus-4-8\n---\n"
        )
        r = self._run_cli("--detect-override", str(a), str(b))
        self.assertEqual(r.returncode, 1)

    def test_parse_model_prints_value(self):
        p = self._write(
            "a.md", "---\nmodel: claude-haiku-4-5-20251001\n---\n"
        )
        r = self._run_cli("--parse-model", str(p))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "claude-haiku-4-5-20251001")

    def test_invalid_usage_exits_2(self):
        r = self._run_cli()
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)


class TestIdentitySerialization(AgentFrontmatterTestBase):
    def test_serializes_canonical_format(self):
        a = self._write("a.md", "---\nmodel: claude-sonnet-4-6\n---\n")
        b = self._write("b.md", "---\nmodel: claude-opus-4-8\n---\n")
        s = _serialize_for_identity_test(a, b)
        self.assertEqual(s, "claude-sonnet-4-6|claude-opus-4-8|1")

    def test_serializes_no_override(self):
        a = self._write("a.md", "---\nmodel: claude-opus-4-8\n---\n")
        b = self._write("b.md", "---\nmodel: claude-opus-4-8\n---\n")
        s = _serialize_for_identity_test(a, b)
        self.assertEqual(s, "claude-opus-4-8|claude-opus-4-8|0")


if __name__ == "__main__":
    unittest.main()
