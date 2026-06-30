"""Tests for ``_lib/credentials.py`` — Sprint 12 Phase 1 / CRITICAL-2.

Verifies pattern recall, precision, context heuristic, env access,
Unicode/case edges. Fixtures are NOT real keys.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import credentials as C  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

ANTHROPIC_FIX = "sk-ant-api03-" + "A1b2C3d4E5f6G7h8I9j0" * 4 + "_-"
GOOGLE_FIX = "AIza" + "B1c2D3e4F5g6H7i8J9k0L1m2N3o4P5q6R7s"  # 35 body
OPENAI_PROJ_FIX = "sk-proj-" + "Z9y8X7w6V5u4T3s2R1q0" * 4 + "_-"
OPENAI_LEGACY_FIX = "sk-" + "P1o2I3u4Y5t6R7e8W9q0" * 3  # 60 body
AWS_FIX = "AKIAIOSFODNN7EXAMPLE"


def _providers(hits):
    return [h[0] for h in hits]


class TestKeyPatterns(TestEnvContext):
    def test_detect_anthropic(self):
        self.assertIn("anthropic", _providers(C.detect_keys(f"curl '{ANTHROPIC_FIX}'")))

    def test_detect_google(self):
        self.assertIn("google", _providers(C.detect_keys(f"KEY={GOOGLE_FIX}")))

    def test_detect_openai_proj(self):
        self.assertIn("openai_proj", _providers(C.detect_keys(f"K={OPENAI_PROJ_FIX}")))

    def test_detect_openai_legacy(self):
        ps = _providers(C.detect_keys(f"echo {OPENAI_LEGACY_FIX}"))
        self.assertIn("openai_legacy", ps)
        self.assertNotIn("openai_proj", ps)  # must not double-match

    def test_detect_aws(self):
        self.assertIn("aws", _providers(C.detect_keys(f"AWS_KEY={AWS_FIX}")))

    def test_multiple_providers(self):
        ps = set(_providers(C.detect_keys(f"{ANTHROPIC_FIX} and {GOOGLE_FIX}")))
        self.assertIn("anthropic", ps)
        self.assertIn("google", ps)

    def test_offsets_sorted_document_order(self):
        hits = C.detect_keys(f"first={ANTHROPIC_FIX} second={GOOGLE_FIX}")
        offs = [h[2] for h in hits]
        self.assertEqual(offs, sorted(offs))


class TestLengthThresholds(TestEnvContext):
    """Short/invalid patterns MUST NOT match — precision guard."""

    def test_short_sk_rejected(self):
        self.assertEqual(C.detect_keys("git checkout sk-foo"), [])

    def test_short_sk_ant_rejected(self):
        self.assertNotIn("anthropic", _providers(C.detect_keys("sk-ant-short")))

    def test_aiza_wrong_length_rejected(self):
        self.assertNotIn("google", _providers(C.detect_keys("AIza" + "x" * 10)))

    def test_akia_wrong_length_rejected(self):
        self.assertEqual(C.detect_keys("AKIA" + "ABC123"), [])


class TestIsLikelyRealKey(TestEnvContext):
    """Context-aware heuristic — False for doc, True for live."""

    def test_example_token_rejected(self):
        body = "sk-ant-EXAMPLE" + "x" * 50
        self.assertFalse(C.is_likely_real_key(body, body))

    def test_your_key_placeholder_rejected(self):
        ctx = f"export KEY=YOUR_KEY_HERE {ANTHROPIC_FIX}"
        self.assertFalse(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_replace_me_rejected(self):
        ctx = f"# REPLACE_ME with real key: {GOOGLE_FIX}"
        self.assertFalse(C.is_likely_real_key(GOOGLE_FIX, ctx))

    def test_plain_shell_accepted(self):
        ctx = f"curl -H 'x-api-key: {ANTHROPIC_FIX}' https://api"
        self.assertTrue(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_fenced_yaml_doc_rejected(self):
        ctx = f"Example:\n```yaml\napi_key: {ANTHROPIC_FIX}\n```\n"
        self.assertFalse(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_fenced_bash_accepted(self):
        ctx = f"Run:\n```bash\nexport K={ANTHROPIC_FIX}\n```\n"
        self.assertTrue(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_unlabeled_fence_accepted(self):
        ctx = f"```\nexport K={ANTHROPIC_FIX}\n```"
        self.assertTrue(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_all_same_char_body_rejected(self):
        placeholder = "sk-ant-" + "A" * 80
        self.assertFalse(C.is_likely_real_key(placeholder, placeholder))

    def test_angle_bracket_placeholder_rejected(self):
        ctx = f"--header '<your-key> {ANTHROPIC_FIX}'"
        self.assertFalse(C.is_likely_real_key(ANTHROPIC_FIX, ctx))

    def test_empty_match_false(self):
        self.assertFalse(C.is_likely_real_key("", ""))


class TestReadEnvSafely(TestEnvContext):
    """No caching, required semantics, error shape."""

    def test_read_existing(self):
        os.environ["CEO_TEST_CRED"] = "s3cret"
        self.assertEqual(C.read_env_safely("CEO_TEST_CRED"), "s3cret")

    def test_read_unset_returns_none(self):
        os.environ.pop("CEO_TEST_CRED", None)
        self.assertIsNone(C.read_env_safely("CEO_TEST_CRED"))

    def test_read_unset_with_default(self):
        os.environ.pop("CEO_TEST_CRED", None)
        self.assertEqual(C.read_env_safely("CEO_TEST_CRED", default="fb"), "fb")

    def test_required_raises_when_unset(self):
        os.environ.pop("CEO_TEST_CRED", None)
        with self.assertRaises(C.MissingCredentialError) as cm:
            C.read_env_safely("CEO_TEST_CRED", required=True)
        self.assertEqual(cm.exception.var_name, "CEO_TEST_CRED")
        self.assertIn("CEO_TEST_CRED", str(cm.exception))

    def test_required_raises_when_empty(self):
        os.environ["CEO_TEST_CRED"] = ""
        with self.assertRaises(C.MissingCredentialError):
            C.read_env_safely("CEO_TEST_CRED", required=True)

    def test_no_caching_respects_unset(self):
        """Unsetting env MUST take effect on next call (ADR-040)."""
        os.environ["CEO_TEST_CRED"] = "first"
        self.assertEqual(C.read_env_safely("CEO_TEST_CRED"), "first")
        del os.environ["CEO_TEST_CRED"]
        self.assertIsNone(C.read_env_safely("CEO_TEST_CRED"))

    def test_error_does_not_contain_value(self):
        """Error contains var name only, never the (missing) value."""
        os.environ["CEO_TEST_CRED"] = "s3cret-leak"
        del os.environ["CEO_TEST_CRED"]
        try:
            C.read_env_safely("CEO_TEST_CRED", required=True)
        except C.MissingCredentialError as e:
            self.assertNotIn("s3cret", str(e))


class TestRedactedDisplay(TestEnvContext):
    def test_anthropic(self):
        out = C.redacted_display("anthropic", ANTHROPIC_FIX)
        self.assertEqual(out, "anthropic:sk-ant-****")
        self.assertNotIn(ANTHROPIC_FIX[8:], out)

    def test_google(self):
        self.assertEqual(C.redacted_display("google", GOOGLE_FIX), "google:AIza****")

    def test_unknown_provider(self):
        out = C.redacted_display("unknown_prov", "whatever")
        self.assertTrue(out.startswith("unknown_prov:") and out.endswith("****"))


class TestEdgeCases(TestEnvContext):
    def test_empty_text(self):
        self.assertEqual(C.detect_keys(""), [])

    def test_none_text(self):
        self.assertEqual(C.detect_keys(None), [])  # type: ignore[arg-type]

    def test_unicode_around_key(self):
        hits = C.detect_keys(f"eh! {ANTHROPIC_FIX} aqui")
        self.assertIn("anthropic", _providers(hits))

    def test_case_sensitive_google(self):
        self.assertNotIn("google", _providers(C.detect_keys("aiza" + "x" * 35)))

    def test_case_sensitive_aws(self):
        self.assertEqual(C.detect_keys("akia" + "A" * 16), [])


if __name__ == "__main__":
    unittest.main()
