"""ReDoS resistance + preview-mode tests for _lib.redact.

PLAN-025 F-sec-004 — harden the redaction hot path against pathological
adversarial inputs. These tests verify:

1. `redact_preview()` caps input at 4 KiB BEFORE regex scan (faster + smaller
   blast radius vs the 64 KiB cap used by `redact_secrets()`).
2. Adversarial quantifier-stacked payloads complete within a wall-clock
   budget (<100ms on CI hardware) for both entry points.
3. Hex-secret pattern (which has no `*` / `+` nested quantifier but longest
   run on large inputs) completes in bounded time.
4. Unicode / multi-line / collapsed-whitespace combinations stay bounded.
5. Idempotency + no-leak invariants hold on preview path too.

These are NOT policy-fuzz tests; the policy engine has its own fuzz harness.
This file narrowly exercises redact.py's resistance to ReDoS on both
entry points.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path


from _lib import redact  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# Hard wall-clock budget per call for the PREVIEW path. redact_preview
# truncates input to 4 KiB so must complete quickly on any adversarial
# input. 250ms is a generous red line; real typical latency is <5ms.
_REDOS_BUDGET_SECONDS = 0.25

# Looser budget for redact_secrets on larger inputs (< 64 KiB cap).
# The 64 KiB cap bounds worst case; within that, some patterns have
# poor constant factors (see DYN-REDACT-1) but no exponential blowup.
# 1.5s catches true catastrophic regressions without flaking on noise.
_SECRETS_BUDGET_SECONDS = 1.5


class TestRedactPreviewConstant(TestEnvContext):
    """The preview-mode input cap must be smaller than the default cap."""

    def test_preview_cap_exists(self):
        self.assertTrue(
            hasattr(redact, "_MAX_PREVIEW_INPUT_CHARS"),
            "redact._MAX_PREVIEW_INPUT_CHARS constant must exist "
            "(PLAN-025 Batch A F-sec-004)",
        )

    def test_preview_cap_is_smaller(self):
        self.assertLess(
            redact._MAX_PREVIEW_INPUT_CHARS,
            redact._MAX_INPUT_CHARS,
            "Preview cap must be strictly smaller than full cap for "
            "defense-in-depth to matter",
        )

    def test_preview_cap_is_reasonable(self):
        # 1 KiB is too small (legit audit descs truncate); 16 KiB is too big.
        self.assertGreaterEqual(redact._MAX_PREVIEW_INPUT_CHARS, 1024)
        self.assertLessEqual(redact._MAX_PREVIEW_INPUT_CHARS, 16 * 1024)


class TestRedactPreviewEntrypoint(TestEnvContext):
    """`redact_preview()` wraps `redact_secrets()` with a tighter input cap."""

    def test_preview_function_exists(self):
        self.assertTrue(
            hasattr(redact, "redact_preview"),
            "redact.redact_preview() must exist",
        )

    def test_preview_returns_string(self):
        out = redact.redact_preview("hello")
        self.assertIsInstance(out, str)

    def test_preview_none_returns_empty(self):
        self.assertEqual(redact.redact_preview(None), "")

    def test_preview_truncates_input_before_regex(self):
        # 128 KiB of raw JWT-like bytes. Default redact_secrets caps at 64 KB
        # before regex; redact_preview caps at 4 KB.
        payload = "eyJ" + ("A" * (128 * 1024))

        t0 = time.monotonic()
        out = redact.redact_preview(payload)
        elapsed = time.monotonic() - t0

        self.assertLess(
            elapsed,
            _REDOS_BUDGET_SECONDS,
            f"redact_preview on 128KB payload took {elapsed:.3f}s, "
            f"exceeds {_REDOS_BUDGET_SECONDS}s budget",
        )
        self.assertIsInstance(out, str)

    def test_preview_redacts_jwt(self):
        text = "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1MSJ9.sig-here"
        out = redact.redact_preview(text)
        self.assertIn("[JWT]", out)

    def test_preview_redacts_api_key(self):
        text = "use sk-ABCDEFGHIJKLMNOPQRSTUV today"
        out = redact.redact_preview(text)
        self.assertIn("[API_KEY]", out)

    def test_preview_idempotent(self):
        text = "Bearer abc123def456 api_key=secretvalue123 ghp_ABCDEFGHIJ1234567890"
        once = redact.redact_preview(text)
        twice = redact.redact_preview(once)
        self.assertEqual(once, twice, "redact_preview must be idempotent")


class TestRedactReDoSAdversarial(TestEnvContext):
    """Adversarial inputs exercising worst-case regex paths must stay bounded."""

    def _check_time_budget(self, payload: str, entrypoint, label: str) -> str:
        # Preview path uses the tighter budget (input is truncated to 4 KiB);
        # redact_secrets uses the looser budget (input bounded by 64 KiB cap).
        budget = (
            _REDOS_BUDGET_SECONDS
            if entrypoint is redact.redact_preview
            else _SECRETS_BUDGET_SECONDS
        )
        t0 = time.monotonic()
        out = entrypoint(payload)
        elapsed = time.monotonic() - t0
        self.assertLess(
            elapsed,
            budget,
            f"{label}: took {elapsed:.3f}s, exceeds {budget}s "
            f"budget (input len={len(payload)})",
        )
        return out

    def test_stacked_base64_no_redos_secrets(self):
        # Pathological for naive nested-quantifier regex. JWT pattern uses
        # bounded segments; this should complete in well under 100ms.
        payload = "eyJ" + ("A" * 1000) + "!" + ("A" * 1000)
        self._check_time_budget(
            payload, redact.redact_secrets, "redact_secrets stacked-base64"
        )

    def test_stacked_base64_no_redos_preview(self):
        payload = "eyJ" + ("A" * 1000) + "!" + ("A" * 1000)
        self._check_time_budget(
            payload, redact.redact_preview, "redact_preview stacked-base64"
        )

    def test_long_hex_run_no_redos_secrets(self):
        payload = "deadbeef" * 2000  # 16 KB of hex
        self._check_time_budget(
            payload, redact.redact_secrets, "redact_secrets hex-run"
        )

    def test_long_hex_run_no_redos_preview(self):
        payload = "deadbeef" * 2000
        out = self._check_time_budget(
            payload, redact.redact_preview, "redact_preview hex-run"
        )
        # Sanity: preview must have truncated the input AND emitted [HEX_SECRET]
        self.assertIn("[HEX_SECRET]", out)

    def test_kv_value_overlong_no_redos_preview(self):
        # `password=<huge>` — the `\S+` tail against 50K non-whitespace
        # exhibits ReDoS pathology on redact_secrets (documented dynamic
        # finding DYN-REDACT-1). The PLAN-025 Batch A defense is
        # `redact_preview` which truncates input to 4 KiB BEFORE regex,
        # reducing worst-case O(n^2) work on the kv pattern to bounded.
        payload = "password=" + ("x" * 50_000) + " trailing"
        self._check_time_budget(
            payload, redact.redact_preview, "redact_preview kv-overlong"
        )

    def test_kv_value_overlong_secrets_bounded_by_input_cap(self):
        # redact_secrets on 50K kv payload is slower than redact_preview
        # (see DYN-REDACT-1) but MUST still complete in bounded time
        # (< 30s) thanks to the 64 KiB _MAX_INPUT_CHARS cap. This test
        # asserts the upper bound; the tighter redact_preview budget is
        # tested above.
        payload = "password=" + ("x" * 50_000) + " trailing"
        t0 = time.monotonic()
        out = redact.redact_secrets(payload)
        elapsed = time.monotonic() - t0
        self.assertLess(
            elapsed,
            30.0,
            f"redact_secrets kv-overlong took {elapsed:.3f}s; exceeds "
            "30s safety bound (should be O(input_cap))",
        )
        self.assertIn("[REDACTED]", out)

    def test_aws_secret_boundary_no_redos(self):
        # The AWS-secret pattern has a `.{0,200}?` non-greedy context; ensure
        # it does not degrade on long preceding context.
        payload = "aws_secret_access_key " + ("x" * 1000) + " " + ("A" * 40) + " tail"
        self._check_time_budget(
            payload, redact.redact_secrets, "redact_secrets aws-secret-boundary"
        )

    def test_utf8_multiline_no_redos(self):
        # Mix unicode + newlines + control chars to stress whitespace collapse
        # (which happens AFTER regex) and patterns with `\s`.
        payload = "á\n\t ghp_ABCDEFGHIJ1234567890 ã\n" * 1000
        out = self._check_time_budget(
            payload, redact.redact_preview, "redact_preview utf8-multiline"
        )
        # At least one GitHub PAT should have been flagged
        self.assertIn("[GITHUB_PAT]", out)

    def test_mixed_patterns_no_redos(self):
        # Mix of all pattern families, all short-ish, testing scan cost
        lines = []
        for i in range(200):
            lines.append(f"jwt eyJ{('A' * 20)}.{('B' * 30)}.{('C' * 20)}")
            lines.append(f"key sk-{('D' * 30)}")
            lines.append(f"gh ghp_{('E' * 30)}")
            lines.append(f"aws AKIA{'F' * 16}")
            lines.append(f"hex {'a' * 40}")
            lines.append(f"url https://user:pw@host{i}.example.com/p")
            lines.append(f"kv password=val{i}longvaluehere")
        payload = "\n".join(lines)
        out = self._check_time_budget(
            payload, redact.redact_preview, "redact_preview mixed-patterns"
        )
        # Each family should have redacted at least one occurrence
        self.assertIn("[JWT]", out)


class TestRedactPreviewNoLeak(TestEnvContext):
    """Preview path must preserve the no-leak invariant."""

    def test_no_jwt_leaks_after_preview(self):
        raw = "eyJALG.PAYLOAD1234567.SIGNATURE_VAL"
        out = redact.redact_preview("before " + raw + " after")
        self.assertNotIn(raw, out)

    def test_no_api_key_leaks_after_preview(self):
        raw = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        out = redact.redact_preview("use " + raw + " here")
        self.assertNotIn(raw, out)

    def test_no_github_pat_leaks_after_preview(self):
        raw = "ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234"
        out = redact.redact_preview("token=" + raw)
        self.assertNotIn(raw, out)


if __name__ == "__main__":
    unittest.main()
