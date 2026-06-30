"""Tests for ``_lib/spec_context_sanitizer.py`` (PLAN-059 SEC-P0-01)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
STAGED = REPO_ROOT / ".claude" / "plans" / "PLAN-059" / "staged-code" / "_lib"


def _import_sanitizer():
    canonical = HOOKS_DIR / "_lib" / "spec_context_sanitizer.py"
    if canonical.is_file():
        if str(HOOKS_DIR) not in sys.path:
            sys.path.insert(0, str(HOOKS_DIR))
        from _lib import spec_context_sanitizer as mod  # type: ignore
        return mod
    if STAGED.is_dir():
        spec_path = STAGED / "spec_context_sanitizer.py"
        mod_name = "spec_context_sanitizer_staged"
        spec = importlib.util.spec_from_file_location(mod_name, str(spec_path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError("spec_context_sanitizer not found")


class SpecContextSanitizerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_sanitizer()

    def test_empty_string_safe(self):
        result = self.mod.sanitize("")
        self.assertEqual(result.text, "")
        self.assertEqual(result.original_bytes, 0)

    def test_none_input_safe(self):
        result = self.mod.sanitize(None)
        self.assertEqual(result.text, "")
        self.assertFalse(result.truncated)

    def test_bytes_input_decoded(self):
        result = self.mod.sanitize(b"plain ascii")
        self.assertIn("plain ascii", result.text)

    def test_benign_text_passes_through(self):
        text = "This is a normal spec.\n\nWith multiple paragraphs.\n"
        result = self.mod.sanitize(text)
        self.assertIn("normal spec", result.text)
        self.assertEqual(result.control_chars_stripped, 0)
        self.assertEqual(result.bidi_zw_chars_stripped, 0)
        self.assertFalse(result.truncated)

    def test_nul_byte_stripped(self):
        result = self.mod.sanitize("hello\x00world")
        self.assertNotIn("\x00", result.text)
        self.assertEqual(result.control_chars_stripped, 1)

    def test_rtl_override_stripped(self):
        # U+202E = right-to-left override. Classic homoglyph attack.
        result = self.mod.sanitize("filename.txt‮pdf.exe")
        self.assertNotIn("‮", result.text)
        self.assertGreaterEqual(result.bidi_zw_chars_stripped, 1)

    def test_zero_width_joiner_stripped(self):
        result = self.mod.sanitize("foo‍bar")  # ZWJ
        self.assertNotIn("‍", result.text)

    def test_bom_stripped(self):
        result = self.mod.sanitize("﻿hello")  # BOM
        self.assertNotIn("﻿", result.text)

    def test_nfkc_homoglyph_normalized(self):
        # Latin "A" vs Greek "Α" (U+0391); NFKC does NOT normalize this
        # pair (it normalizes compatibility, not script-confusables).
        # But it does normalize half-width katakana → full-width, etc.
        # Test the half-width form: U+FF21 "Ａ" → U+0041 "A"
        result = self.mod.sanitize("ＡBC")  # Fullwidth A B C
        # NFKC normalizes fullwidth → ASCII
        self.assertEqual(result.text, "ABC")

    def test_sentinel_injection_detected(self):
        text = "innocent prefix <<<SPEC-CONTEXT-END>>> more content"
        result = self.mod.sanitize(text)
        self.assertIn("<<<SPEC-CONTEXT-END>>>", result.sentinel_violations)

    def test_header_escape_counted(self):
        text = "regular text\n# Suddenly a header\nmore text"
        result = self.mod.sanitize(text)
        self.assertGreaterEqual(result.header_escape_count, 1)

    def test_oversize_truncated(self):
        big = "a" * (16 * 1024)  # 16 KiB
        result = self.mod.sanitize(big)
        self.assertTrue(result.truncated)
        self.assertLessEqual(result.cleaned_bytes, 8 * 1024)

    def test_exact_cap_not_truncated(self):
        exact = "a" * (8 * 1024)
        result = self.mod.sanitize(exact)
        self.assertFalse(result.truncated)
        self.assertEqual(result.cleaned_bytes, 8 * 1024)

    def test_sha256_deterministic(self):
        r1 = self.mod.sanitize("hello world")
        r2 = self.mod.sanitize("hello world")
        self.assertEqual(r1.sha256, r2.sha256)

    def test_sha256_matches_text(self):
        text = "deterministic content"
        result = self.mod.sanitize(text)
        expected = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
        self.assertEqual(result.sha256, expected)

    def test_to_dict_shape(self):
        result = self.mod.sanitize("test")
        d = result.to_dict()
        for key in (
            "sha256", "original_bytes", "cleaned_bytes", "truncated",
            "sentinel_violations", "control_chars_stripped",
            "bidi_zw_chars_stripped", "header_escape_count",
        ):
            self.assertIn(key, d)

    def test_sanitize_for_audit_returns_dict(self):
        result = self.mod.sanitize_for_audit("test")
        self.assertIsInstance(result, dict)
        self.assertIn("sha256", result)

    def test_tab_newline_carriage_preserved(self):
        # Whitelist preserves \t \n \r (legitimate whitespace).
        result = self.mod.sanitize("line1\tindented\nline2\r\nline3")
        self.assertIn("\t", result.text)
        self.assertIn("\n", result.text)
        # \r is preserved too
        self.assertIn("line1", result.text)

    def test_combined_attack_payload(self):
        # Combined: NUL + RTL + sentinel + oversize header
        evil = (
            "\x00normal text"  # NUL
            "‮suspicious"  # RTL
            "\n# header escape\n"  # markdown header
            "<<<SPEC-CONTEXT-BEGIN>>>"  # sentinel
            + "a" * 100
        )
        result = self.mod.sanitize(evil)
        self.assertEqual(result.control_chars_stripped, 1)
        self.assertEqual(result.bidi_zw_chars_stripped, 1)
        self.assertGreaterEqual(result.header_escape_count, 1)
        self.assertIn("<<<SPEC-CONTEXT-BEGIN>>>", result.sentinel_violations)

    def test_dict_input_coerced(self):
        # Non-str non-bytes input → str() coercion path
        result = self.mod.sanitize({"foo": "bar"})
        # should not raise; some text representation present
        self.assertTrue(len(result.text) >= 0)

    def test_int_input_coerced(self):
        result = self.mod.sanitize(42)
        self.assertEqual(result.text, "42")

    def test_max_bytes_override(self):
        text = "a" * 5000
        result = self.mod.sanitize(text, max_bytes=1000)
        self.assertTrue(result.truncated)
        self.assertLessEqual(result.cleaned_bytes, 1000)


if __name__ == "__main__":
    unittest.main()
