"""PLAN-045 P0-09 (b) — tests for Artifact Paradox fluency SubagentStop hook.

Covers the 12 original scenarios from the staged test file PLUS 3
additional adversarial tests per approved.md round-8 §Artifact
Paradox self-review:

- Malformed JSON stdin → fail-open
- Output > 100KB → process without hanging; threshold still 8
- Unicode/homoglyph markers → should NOT match (ASCII-bounded)

Tests cover:
- Adaptive thresholds (short/medium/long outputs)
- Marker pattern detection (positive + negative + boundaries)
- Case insensitivity
- Word boundary correctness (e.g. "imperfection" should not match)
- Kill-switch short-circuit
- Fail-open on malformed stdin
- Large-output scan cap
- Unicode-homoglyph non-match invariant
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from _lib.testing import TestEnvContext  # noqa: E402


import check_fluency_nudge as fn  # noqa: E402


class ThresholdTests(unittest.TestCase):
    """Adaptive thresholds based on output length."""

    def test_short_output_threshold(self) -> None:
        self.assertEqual(fn._threshold_for_length(100), 2)
        self.assertEqual(fn._threshold_for_length(499), 2)

    def test_medium_output_threshold(self) -> None:
        self.assertEqual(fn._threshold_for_length(500), 4)
        self.assertEqual(fn._threshold_for_length(4999), 4)

    def test_long_output_threshold(self) -> None:
        self.assertEqual(fn._threshold_for_length(5000), 8)
        self.assertEqual(fn._threshold_for_length(50000), 8)


class MarkerCountingTests(unittest.TestCase):
    """Confidence-marker pattern detection."""

    def test_empty_text_no_markers(self) -> None:
        count, found = fn._count_markers("")
        self.assertEqual(count, 0)
        self.assertEqual(found, [])

    def test_single_marker(self) -> None:
        count, found = fn._count_markers("Implementation complete, all tests green!")
        self.assertGreaterEqual(count, 1)
        self.assertTrue(any("green" in f.lower() for f in found))

    def test_multiple_distinct_markers(self) -> None:
        text = (
            "All done! Tests are passing. No issues found. "
            "The implementation is perfect and ready to ship."
        )
        count, found = fn._count_markers(text)
        self.assertGreaterEqual(count, 4)

    def test_word_boundary_respected(self) -> None:
        # "perfect" is NOT word-bounded in "imperfection" so no match.
        count, _ = fn._count_markers("The imperfection is visible.")
        self.assertEqual(count, 0)

    def test_case_insensitive(self) -> None:
        count, _ = fn._count_markers("LGTM! All Done.")
        self.assertGreaterEqual(count, 2)

    def test_real_hallucination_sample(self) -> None:
        """A realistic polished sub-agent output trips the nudge."""
        sample = (
            "## Summary\n\n"
            "I've successfully completed the implementation as specified. "
            "All tests are green, no issues found. The diff is clean and "
            "ready to ship. Coverage is fully maintained — looks good to merge."
        )
        count, found = fn._count_markers(sample)
        self.assertGreaterEqual(count, 5)
        length = len(sample)
        threshold = fn._threshold_for_length(length)
        self.assertGreater(count, threshold)


class NegativeControlTests(unittest.TestCase):
    """Legitimate outputs that should NOT trip the nudge."""

    def test_technical_report_without_confidence_phrases(self) -> None:
        sample = (
            "The refactor touches 3 files: src/foo.ts, src/bar.ts, and "
            "__tests__/foo.test.ts. The function signature changed from "
            "(a, b) to (a, b, opts). Callers in 5 places were updated. "
            "Added 2 new tests covering the opts=undefined path and the "
            "opts={strict: true} path."
        )
        count, _ = fn._count_markers(sample)
        threshold = fn._threshold_for_length(len(sample))
        self.assertLess(count, threshold)

    def test_explicit_uncertainty_not_tripped(self) -> None:
        sample = (
            "I'm uncertain about the race condition in worker.ts:42. "
            "The mutex may need a timeout, but I don't have enough "
            "context to verify. Flagging for Chaos Engineer review."
        )
        count, _ = fn._count_markers(sample)
        self.assertEqual(count, 0)


class KillSwitchTests(TestEnvContext):
    """Env kill-switch short-circuit."""

    def test_kill_switch_short_circuits(self) -> None:
        with patch.dict(os.environ, {"CEO_FLUENCY_NUDGE": "0"}):
            # main() short-circuits BEFORE reading stdin when env=0.
            with patch.object(sys, "stdin", io.StringIO("{")):
                with patch.object(sys, "stdout", io.StringIO()) as fake_out:
                    rc = fn.main()
                self.assertEqual(rc, 0)
                # Output is the allow JSON — no nudge message.
                out = fake_out.getvalue().strip()
                parsed = json.loads(out)
                self.assertEqual(parsed, {})


class IntegrationMainTests(unittest.TestCase):
    """Drive main() end-to-end with real stdin/stdout."""

    def _run_main(self, stdin_str: str) -> dict:
        with patch.object(sys, "stdin", io.StringIO(stdin_str)):
            with patch.object(sys, "stdout", io.StringIO()) as fake_out:
                rc = fn.main()
                out = fake_out.getvalue().strip()
        self.assertEqual(rc, 0)
        if not out:
            return {}
        return json.loads(out)

    def test_main_nudges_on_many_markers_short_output(self) -> None:
        payload = {
            "session_id": "s",
            "tool_response": "All done! Tests green. Perfect. LGTM.",
        }
        result = self._run_main(json.dumps(payload))
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", result)
        self.assertIn("ARTIFACT-PARADOX-NUDGE", result["systemMessage"])

    def test_main_allows_on_few_markers(self) -> None:
        payload = {
            "session_id": "s",
            "tool_response": "Refactored src/foo.ts — one signature change, no test updates needed.",
        }
        result = self._run_main(json.dumps(payload))
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertNotIn("systemMessage", result)

    def test_main_empty_stdin_allows(self) -> None:
        result = self._run_main("")
        self.assertEqual(result.get("decision", "allow"), "allow")

    # --- NEW TESTS (Session 43 round-8 scope self-review) --------------------

    def test_malformed_json_stdin_fails_open(self) -> None:
        """Adversarial test #1: malformed JSON → fail-open with allow."""
        result = self._run_main("{not-json, truly: malformed")
        self.assertEqual(result, {})

    def test_large_output_over_100kb_does_not_hang(self) -> None:
        """Adversarial test #2: >100KB output processes in bounded time.

        Large outputs are scanned head+tail only (capped at _MAX_SCAN_BYTES
        total). This test builds a 500KB payload with markers at both
        ends — the tail-scan must still find them to produce the nudge.
        """
        # 150KB of filler + markers at both ends
        middle = "x" * (500 * 1024)
        text = (
            "All done! Tests green. Perfect. LGTM. No issues. Clean diff.\n"
            + middle
            + "\nReady to ship. Fully covered. Implemented as specified."
        )
        self.assertGreater(len(text), 500 * 1024)

        payload = {"session_id": "s", "tool_response": text}
        import time
        t0 = time.monotonic()
        result = self._run_main(json.dumps(payload))
        elapsed = time.monotonic() - t0
        # Must complete in under 1 second even for 500KB input.
        self.assertLess(elapsed, 1.0, f"scan took {elapsed:.3f}s, too slow")
        # And should still produce a nudge (markers at both ends).
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", result)
        self.assertIn("ARTIFACT-PARADOX-NUDGE", result["systemMessage"])

    def test_unicode_homoglyph_markers_do_not_match(self) -> None:
        """Adversarial test #3: Cyrillic lookalikes should NOT trip.

        Design invariant: markers are ASCII-bounded. i18n noise with
        similar-looking characters (e.g. Cyrillic 'а' for Latin 'a')
        should NOT trigger false-positives.
        """
        # "аll done" with Cyrillic 'а' (U+0430), "реrfect" with Cyrillic 'р'
        text = (
            "аll done! Tеsts grееn. реrfect. lgtm. no issuеs. clеan diff. "
            "rеady to ship. fully covеrеd. implеmеntеd as spеcifiеd."
        )
        count, _ = fn._count_markers(text)
        # Should be 0 or very low — homoglyphs break word boundaries.
        # Some Latin words remain (e.g. "done" has no Cyrillic) so a few
        # genuine matches are OK. The KEY invariant: count should be
        # FAR below the ~9 matches the ASCII version would produce.
        self.assertLess(
            count, 5,
            f"homoglyph text tripped {count} markers — pattern too loose",
        )


class RedactBeforeEmitTests(unittest.TestCase):
    """PLAN-050 Phase 3 C8 — redact-before-emit defense-in-depth."""

    def _run_main(self, stdin_str: str) -> dict:
        with patch.object(sys, "stdin", io.StringIO(stdin_str)):
            with patch.object(sys, "stdout", io.StringIO()) as fake_out:
                rc = fn.main()
                out = fake_out.getvalue().strip()
        self.assertEqual(rc, 0)
        if not out:
            return {}
        return json.loads(out)

    def test_redact_safe_identity_when_redact_unavailable(self) -> None:
        """_redact_safe fails open to identity when _lib.redact missing."""
        with patch.object(fn, "_REDACT_AVAILABLE", False), \
             patch.object(fn, "_redact", None):
            result = fn._redact_safe("sk-ant-api03-abc123-XYZ")
            self.assertEqual(result, "sk-ant-api03-abc123-XYZ")

    def test_redact_safe_redacts_when_available(self) -> None:
        """_redact_safe passes through to _lib.redact.redact_secrets."""
        sample = "All done. Token is sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890."
        redacted = fn._redact_safe(sample)
        # Must not leak the original token payload.
        self.assertNotIn("sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890", redacted)

    def test_count_markers_snippets_cannot_capture_secret(self) -> None:
        """C8 structural invariant: word-bounded markers never capture secrets.

        `_count_markers` does NOT redact the scanned text (that would cost
        >4s on 500KB inputs and break the SLA). Instead, the confidence
        patterns are word-bounded Latin idioms — ``\\ball\\s+done\\b``
        cannot structurally capture adjacent API-key substrings. This
        test verifies the structural invariant holds for the current
        pattern set. Defense-in-depth redact is applied on the emit
        side (see other tests in this class).
        """
        payload_text = (
            "All done! Tests green. Perfect. LGTM. "
            "Saved token sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890 ok."
        )
        count, found = fn._count_markers(payload_text)
        self.assertGreaterEqual(count, 3)
        # None of the returned match snippets may contain the leaked token.
        for snippet in found:
            self.assertNotIn(
                "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890",
                snippet,
                f"marker snippet leaked secret: {snippet!r}",
            )

    def test_main_nudge_message_does_not_leak_api_key(self) -> None:
        """End-to-end: systemMessage must not carry raw sk-ant-… token."""
        payload = {
            "session_id": "s",
            "tool_response": (
                "All done! Tests green. Perfect. LGTM. "
                "Token=sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890 "
                "ready to ship."
            ),
        }
        result = self._run_main(json.dumps(payload))
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", result)
        msg = result["systemMessage"]
        self.assertIn("ARTIFACT-PARADOX-NUDGE", msg)
        self.assertNotIn(
            "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890", msg,
            "systemMessage leaked anthropic key token",
        )

    def test_main_nudge_no_regression_on_clean_output(self) -> None:
        """Redact must not break detection on a standard confidence-heavy output."""
        payload = {
            "session_id": "s",
            "tool_response": (
                "All done! Tests green. Perfect. LGTM. "
                "Ready to ship. Fully covered."
            ),
        }
        result = self._run_main(json.dumps(payload))
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertIn("systemMessage", result)
        self.assertIn("ARTIFACT-PARADOX-NUDGE", result["systemMessage"])


if __name__ == "__main__":
    unittest.main()
