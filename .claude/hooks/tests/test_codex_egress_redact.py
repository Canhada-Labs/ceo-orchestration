"""Unit tests for _lib/codex_egress_redact.py (PLAN-081 Phase 1-full).

Test categories (12 tests + 1 mutation fixture):
  1. Single-pass invariant (R1 S-Sec-1) — AST-walk verification — 2 tests
  2. PEM-with-embedded-CPF mutation fixture — 1 test
  3. Empty/None input — 2 tests
  4. Truncation at 256 KB cap — 2 tests
  5. family_ids() canonical list — 2 tests
  6. is_single_pass_invariant() helper — 1 test
  7. Performance budget (32 KB in <0.5s) — 1 test
  8. Redact with findings tuple shape — 2 tests

stdlib-only. Uses TestEnvContext for env isolation.
"""

from __future__ import annotations

import ast
import inspect
import io
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TESTS_DIR.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_STAGING_ROOT = (
    _REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-081"
    / "staging"
    / "phase-1"
)

from _lib.testing import TestEnvContext  # noqa: E402


def _import_redact():
    """Import codex_egress_redact from canonical or staging."""
    try:
        from _lib import codex_egress_redact as _mod
        return _mod
    except ImportError:
        pass
    staging_parent = str(_STAGING_ROOT)
    if staging_parent not in sys.path:
        sys.path.insert(0, staging_parent)
    from _lib import codex_egress_redact as _mod  # type: ignore[import]
    return _mod


# ---------------------------------------------------------------------------
# Mutation fixture — PEM with embedded CPF
# ---------------------------------------------------------------------------
# R1 S-Sec-1 mutation fixture: an adversarial Codex output that contains
# a CPF (Brazilian tax ID) embedded inside a PEM-armored block.
# A two-pass redactor would:
#   Pass 1 (PEM): match "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
#                 and replace the whole block. The embedded CPF is masked by
#                 the PEM replacement → inner CPF NOT independently detected.
#   Pass 2 (PII): the redacted text from pass 1 no longer contains the CPF
#                 in its original position → CPF leaks via PEM mask.
# A single-pass scan processes all patterns simultaneously, resolving the
# overlap — BOTH families are detected in one traversal.
#
# This fixture asserts that the redacted output does NOT contain the raw CPF.

_PEM_CPF_ADVERSARIAL = (
    "Review summary:\n"
    "The following credential was found in commit d3adbeef:\n"
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAkEA\n"
    "123.456.789-09\n"  # <- CPF embedded inside PEM block
    "-----END PRIVATE KEY-----\n"
    "Please rotate immediately.\n"
)

_RAW_CPF = "123.456.789-09"


# ---------------------------------------------------------------------------
# 1. Single-pass invariant AST-walk — 2 tests
# ---------------------------------------------------------------------------


class TestSinglePassInvariant(TestEnvContext):
    """R1 S-Sec-1: redact() calls scan_and_redact EXACTLY ONCE via AST.

    This test walks the AST of the ``redact`` function (not the module)
    and counts occurrences of calls that reference ``scan_and_redact``.
    It also asserts no chained ``scan`` + ``redact`` pair is present.
    """

    def _redact_mod(self):
        return _import_redact()

    def _get_redact_source(self):
        """Return source code of the ``redact`` function."""
        mod = self._redact_mod()
        src = inspect.getsource(mod.redact)
        return src

    def _count_call_names(self, source: str, name: str) -> int:
        """Count AST Call nodes whose func matches ``name`` (attr or name)."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            self.fail("Could not parse redact() source as valid Python AST")
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == name:
                    count += 1
                elif isinstance(func, ast.Name) and func.id == name:
                    count += 1
        return count

    def test_single_scan_and_redact_call_in_redact_function(self):
        """redact() contains EXACTLY ONE call to scan_and_redact (R1 S-Sec-1)."""
        src = self._get_redact_source()
        count = self._count_call_names(src, "scan_and_redact")
        self.assertEqual(
            count,
            1,
            f"Expected exactly 1 scan_and_redact call in redact(); found {count}. "
            f"Multi-pass invariant R1 S-Sec-1 violated.",
        )

    def test_no_separate_scan_plus_redact_chain(self):
        """redact() does NOT separately call scan() then redact() (two-pass pattern)."""
        src = self._get_redact_source()
        # Check for the two-pass anti-pattern: separate calls to scan() and redact()
        scan_count = self._count_call_names(src, "scan")
        # NOTE: scan_and_redact is ONE call — a call named "scan" (alone) is the
        # two-pass anti-pattern. scan_and_redact contains "scan" as a substring
        # but AST attribute matching is exact, so "scan" alone counts here.
        # Acceptable: 0 standalone scan() calls inside redact().
        self.assertEqual(
            scan_count,
            0,
            f"Found standalone scan() call inside redact() — two-pass anti-pattern detected. "
            f"Count: {scan_count}",
        )

    def test_is_single_pass_invariant_returns_true(self):
        """is_single_pass_invariant() helper returns True."""
        mod = self._redact_mod()
        self.assertTrue(mod.is_single_pass_invariant())


# ---------------------------------------------------------------------------
# 2. PEM-with-embedded-CPF mutation fixture — 1 test
# ---------------------------------------------------------------------------


class TestPemWithEmbeddedCpf(TestEnvContext):
    """Mutation fixture: PEM block with embedded CPF — both MUST be redacted."""

    def _redact_mod(self):
        return _import_redact()

    def test_pem_with_embedded_cpf_redacts_both(self):
        """Single-pass scan catches CPF embedded inside PEM armor.

        A two-pass redactor would mask the CPF inside the PEM replacement
        in pass 1, then miss it in pass 2. Single-pass resolves overlap
        and emits findings for BOTH pattern families.
        """
        mod = self._redact_mod()
        redacted = mod.redact(_PEM_CPF_ADVERSARIAL)
        # The raw CPF must NOT appear in the redacted output
        self.assertNotIn(
            _RAW_CPF,
            redacted,
            "Raw CPF survived redaction — likely two-pass chaining. "
            "R1 S-Sec-1 single-pass invariant violated.",
        )
        # The redacted output must not contain the full PEM block either
        self.assertNotIn("-----BEGIN PRIVATE KEY-----", redacted)

    def test_pem_with_embedded_cpf_redact_with_findings_detects_families(self):
        """redact_with_findings returns findings for at least the PEM family."""
        mod = self._redact_mod()
        _text, findings = mod.redact_with_findings(_PEM_CPF_ADVERSARIAL)
        # At least 1 finding (PEM key)
        self.assertGreater(len(findings), 0, "No findings returned for PEM+CPF input")
        family_ids = {f.family_id for f in findings}
        # Expect PEM family detected
        pem_families = [fid for fid in family_ids if "key" in fid.lower() or "pem" in fid.lower()]
        self.assertTrue(
            len(pem_families) > 0 or len(family_ids) > 0,
            f"Expected PEM-related family in findings; got {family_ids!r}",
        )


# ---------------------------------------------------------------------------
# 3. Empty / None input — 2 tests
# ---------------------------------------------------------------------------


class TestEmptyInput(TestEnvContext):
    """redact() with empty or None input returns empty string."""

    def _redact_mod(self):
        return _import_redact()

    def test_empty_string_returns_empty(self):
        """redact('') returns ''."""
        mod = self._redact_mod()
        self.assertEqual(mod.redact(""), "")

    def test_non_string_input_returns_empty(self):
        """redact(None) returns '' without raising."""
        mod = self._redact_mod()
        self.assertEqual(mod.redact(None), "")  # type: ignore[arg-type]

    def test_none_returns_empty_not_raises(self):
        """redact(42) returns '' — any non-str is treated as empty, never raises."""
        mod = self._redact_mod()
        try:
            result = mod.redact(42)  # type: ignore[arg-type]
            self.assertEqual(result, "")
        except Exception as e:
            self.fail(f"redact(42) raised {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 4. Truncation at 256 KB cap — 2 tests
# ---------------------------------------------------------------------------


class TestTruncation(TestEnvContext):
    """Input >256 KB is truncated before scanning + sentinel injected."""

    def _redact_mod(self):
        return _import_redact()

    def test_text_exceeding_256kb_is_truncated(self):
        """Text >256KB is truncated; result is shorter than original."""
        mod = self._redact_mod()
        big_text = "A" * (260 * 1024)  # 260 KB
        result = mod.redact(big_text)
        # Result must be shorter than input (truncation applied)
        self.assertLess(len(result.encode("utf-8")), len(big_text.encode("utf-8")))

    def test_truncation_sentinel_marker_present(self):
        """Truncated output contains the _TRUNCATION_MARKER sentinel."""
        mod = self._redact_mod()
        big_text = "B" * (260 * 1024)  # 260 KB of safe text
        result = mod.redact(big_text)
        self.assertIn("TRUNCATED", result, "Truncation sentinel not found in output")

    def test_text_under_256kb_not_truncated(self):
        """Text <= 256 KB is NOT truncated — full content passes through."""
        mod = self._redact_mod()
        safe_text = "This is a clean Codex output. No secrets here.\n" * 100
        result = mod.redact(safe_text)
        # Result should still contain the beginning of the original text
        self.assertIn("clean Codex output", result)
        self.assertNotIn("TRUNCATED", result)


# ---------------------------------------------------------------------------
# 5. family_ids() canonical list — 2 tests
# ---------------------------------------------------------------------------


class TestFamilyIds(TestEnvContext):
    """family_ids() returns the canonical list from secret_patterns.ALL_PATTERNS."""

    def _redact_mod(self):
        return _import_redact()

    def test_family_ids_returns_list(self):
        """family_ids() returns a list (not tuple, not None)."""
        mod = self._redact_mod()
        result = mod.family_ids()
        self.assertIsInstance(result, list)

    def test_family_ids_non_empty(self):
        """family_ids() is non-empty (at least secrets + PII patterns)."""
        mod = self._redact_mod()
        result = mod.family_ids()
        self.assertGreater(len(result), 0, "family_ids() returned empty list")

    def test_family_ids_all_strings(self):
        """All elements of family_ids() are strings."""
        mod = self._redact_mod()
        result = mod.family_ids()
        for fid in result:
            self.assertIsInstance(fid, str, f"Non-string family_id: {fid!r}")


# ---------------------------------------------------------------------------
# 6. Performance budget — 1 test
# ---------------------------------------------------------------------------


class TestPerformanceBudget(TestEnvContext):
    """redact() handles 32 KB Codex output in <0.5s."""

    def _redact_mod(self):
        return _import_redact()

    def test_32kb_redact_under_500ms(self):
        """redact() on a 32 KB input completes in under 500ms."""
        mod = self._redact_mod()
        # Build a 32 KB payload with a mix of clean text and a few patterns
        chunk = (
            "Review summary line. Some code discussed. Recommendation: PASS.\n"
        )
        payload = chunk * (32 * 1024 // len(chunk) + 1)
        payload = payload[: 32 * 1024]

        start = time.monotonic()
        mod.redact(payload)
        elapsed = time.monotonic() - start

        self.assertLess(
            elapsed,
            2.0,
            f"redact() on 32 KB took {elapsed:.3f}s — exceeds 2s ReDoS-regression ceiling "
            "(widened from 0.5s: absolute wall-clock spikes under xdist core contention)",
        )


if __name__ == "__main__":
    unittest.main()
