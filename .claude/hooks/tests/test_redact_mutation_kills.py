"""Mutation-kill tests for `_lib.redact` (weekly mutation gate, floor 80%).

Targets the 36 mutants that survived the 2026-08-03 measurement (90 total,
kill-rate 60.0%). Each test pins an EXACT contract value — an exact
replacement token, an exact numeric boundary, or exact side-effect content —
rather than a loose `assertIn` that a "wrap the string in XX...XX" or
"nudge a constant by 1" mutant can still satisfy.

Construction notes:
- Filler characters are chosen to be inert against every pattern in
  `_PATTERNS`: `"z"` is not a hex digit and matches no keyword, so it never
  triggers accidental redaction that would corrupt an exact-output
  assertion.
- Numeric boundaries (`_MAX_INPUT_CHARS`, `_MAX_PREVIEW_INPUT_CHARS`,
  `DEFAULT_PREVIEW_CHARS`, the bounded-growth floor of 64) are HARDCODED as
  literals in the assertions, never read back from the (mutatable) module
  constants — reading them back would make the test pass trivially under
  the exact mutation it is meant to kill.

Equivalent mutants (unkillable by construction, listed per instructions
rather than covered by vacuous tests):

- **Mutant 46** (`_lib/redact.py`: `original_len > _MAX_INPUT_CHARS` →
  `>=`): only diverges when `len(text) == _MAX_INPUT_CHARS` exactly. At
  that exact length, the branch body (`text = text[:_MAX_INPUT_CHARS]`;
  `original_len = _MAX_INPUT_CHARS`) is a no-op whether or not it runs,
  because slicing a string to its own current length returns the same
  string and reassigning `original_len` to its current value changes
  nothing. No downstream code observes whether the branch fired. No input
  can produce a different final state between `>` and `>=` here.
- **Mutant 61** (`_truncate_to = max(_growth_cap - _tail_len, 0)` → floor
  `1`): `_growth_cap` is itself `max(original_len * 2, 64)`, i.e. always
  `>= 64`, and `_tail_len` is fixed at `len("[REDACTED:overflow]") == 20`.
  So `_growth_cap - _tail_len` is always `>= 44`, strictly greater than
  both `0` and `1` — the `max(..., 0)` floor can never be the winning
  operand for any input, so changing it to `1` is unreachable dead code.
- **Mutant 89** (`_lib/redact.py` `redact_preview`: `len(text) >
  _MAX_PREVIEW_INPUT_CHARS` → `>=`): identical shape to mutant 46 — at
  `len(text) == _MAX_PREVIEW_INPUT_CHARS` exactly, `text =
  text[:_MAX_PREVIEW_INPUT_CHARS]` is a no-op, and the truncated `text` is
  immediately handed to `redact_secrets`, so no observable difference
  exists between entering and skipping the branch.
"""

from __future__ import annotations

import unittest

from _lib import redact  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestExactReplacementTokens(TestEnvContext):
    """Class: replacement-token mutations (`"[X]"` -> `"XX[X]XX"`).

    `assertIn("[LABEL]", out)` still passes when the mutant wraps the label
    in `"XX...XX"`, because `"[LABEL]"` remains a substring. Each test here
    instead builds an input that is *fully consumed* by exactly one pattern
    and asserts the COMPLETE output string, so any extra character anywhere
    in the replacement fails the assertion.
    """

    def test_jwt_token_exact(self):
        """Kills mutant 2 ("[JWT]" -> "XX[JWT]XX")."""
        out = redact.redact_secrets("eyJA.B.C", max_chars=0)
        self.assertEqual(out, "[JWT]")

    def test_api_key_token_exact(self):
        """Kills mutant 4 ("[API_KEY]" -> "XX[API_KEY]XX")."""
        out = redact.redact_secrets("sk-" + "a" * 20, max_chars=0)
        self.assertEqual(out, "[API_KEY]")

    def test_github_pat_ghp_token_exact(self):
        """Kills mutant 6 ("[GITHUB_PAT]" -> "XX[GITHUB_PAT]XX", ghp_ form)."""
        out = redact.redact_secrets("ghp_" + "a" * 20, max_chars=0)
        self.assertEqual(out, "[GITHUB_PAT]")

    def test_github_pat_fine_grained_token_exact(self):
        """Kills mutant 8 ("[GITHUB_PAT]" -> "XX[GITHUB_PAT]XX", github_pat_ form)."""
        out = redact.redact_secrets("github_pat_" + "a" * 20, max_chars=0)
        self.assertEqual(out, "[GITHUB_PAT]")

    def test_aws_key_token_exact(self):
        """Kills mutant 10 ("[AWS_KEY]" -> "XX[AWS_KEY]XX")."""
        out = redact.redact_secrets("AKIA" + "A" * 16, max_chars=0)
        self.assertEqual(out, "[AWS_KEY]")

    def test_url_with_creds_token_exact(self):
        """Kills mutant 14 ("[URL_WITH_CREDS]" -> "XX[URL_WITH_CREDS]XX")."""
        out = redact.redact_secrets("a://b:c@d", max_chars=0)
        self.assertEqual(out, "[URL_WITH_CREDS]")

    def test_hex_secret_token_exact(self):
        """Kills mutant 16 ("[HEX_SECRET]" -> "XX[HEX_SECRET]XX")."""
        out = redact.redact_secrets("a" * 32, max_chars=0)
        self.assertEqual(out, "[HEX_SECRET]")

    def test_slack_bot_token_exact(self):
        """Kills mutant 21 ("[SLACK_BOT]" -> "XX[SLACK_BOT]XX")."""
        text = "xoxb-" + "0" * 10 + "-" + "0" * 10 + "-" + "a" * 24
        out = redact.redact_secrets(text, max_chars=0)
        self.assertEqual(out, "[SLACK_BOT]")

    def test_stripe_key_token_exact(self):
        """Kills mutant 23 ("[STRIPE_KEY]" -> "XX[STRIPE_KEY]XX")."""
        out = redact.redact_secrets("sk_live_" + "A" * 24, max_chars=0)
        self.assertEqual(out, "[STRIPE_KEY]")

    def test_google_refresh_token_exact(self):
        """Kills mutant 25 ("[GOOGLE_REFRESH]" -> "XX[GOOGLE_REFRESH]XX").

        Filler must be non-hex ("z", not "a"-"f"/digits): the hex pattern
        runs before this one in `_PATTERNS` and would otherwise consume the
        "0" + filler run first (both are valid hex digits), starving this
        pattern of its match.
        """
        out = redact.redact_secrets("1//0" + "z" * 40, max_chars=0)
        self.assertEqual(out, "[GOOGLE_REFRESH]")

    def test_ssh_private_key_header_token_exact(self):
        """Kills mutant 27 ("[SSH_PRIVATE_KEY_HEADER]" -> wrapped)."""
        out = redact.redact_secrets("-----BEGIN PRIVATE KEY-----", max_chars=0)
        self.assertEqual(out, "[SSH_PRIVATE_KEY_HEADER]")

    def test_aws_secret_access_key_token_exact(self):
        """Kills mutant 31 (r"\\1[AWS_SECRET]" -> r"XX\\1[AWS_SECRET]XX").

        Filler must be non-hex ("Z") and contain no "=" / ":" so neither the
        hex pattern nor the kv pattern (both run earlier in `_PATTERNS`)
        consume the tail before the AWS-secret pattern gets to match it.
        """
        text = "aws_secret_access_key" + "Z" * 40
        out = redact.redact_secrets(text, max_chars=0)
        self.assertEqual(out, "aws_secret_access_key[AWS_SECRET]")


class TestInputCapBoundaries(TestEnvContext):
    """Class: DoS-guard input-cap boundary mutations.

    Cap values are HARDCODED (64 * 1024, 4 * 1024) rather than read from
    `redact._MAX_INPUT_CHARS` / `redact._MAX_PREVIEW_INPUT_CHARS`, so a
    mutation to those constants cannot make the assertion trivially agree
    with the mutant.
    """

    def test_max_input_chars_clamp_boundary_exact(self):
        """Kills mutants 33 (64*1024 -> 65*1024) and 35 (64*1024 -> 64*1025).

        One char past the real 64 KiB cap: correct code clamps to exactly
        65536; both mutants' inflated caps let the extra char through,
        producing length 65537 instead.
        """
        text = "z" * (64 * 1024 + 1)
        out = redact.redact_secrets(text, max_chars=0)
        self.assertEqual(len(out), 64 * 1024)

    def test_oversized_input_does_not_crash(self):
        """Kills mutants 47 (`text = None` in the clamp branch) and 48
        (`original_len = None` in the clamp branch).

        Either mutation only fires when the clamp branch is entered (input
        longer than the cap). Once `text` is `None`, the `_PATTERNS` loop's
        `pattern.sub(replacement, text)` raises `TypeError`. Once
        `original_len` is `None`, the later `original_len *
        _BOUNDED_GROWTH_FACTOR` raises `TypeError`. Both crash unconditionally
        for any oversized input; correct code returns a bounded string.
        """
        text = "z" * (64 * 1024 + 100)
        out = redact.redact_secrets(text, max_chars=0)
        self.assertIsInstance(out, str)
        self.assertEqual(len(out), 64 * 1024)

    def test_max_preview_input_chars_clamp_boundary_exact(self):
        """Kills mutants 37 (4*1024 -> 5*1024) and 39 (4*1024 -> 4*1025).

        One char past the real 4 KiB preview cap: correct code clamps to
        exactly 4096 before ever reaching `redact_secrets`; both mutants'
        inflated caps pass the extra char through unclamped.
        """
        text = "z" * (4 * 1024 + 1)
        out = redact.redact_preview(text, max_chars=0)
        self.assertEqual(len(out), 4 * 1024)

    def test_default_preview_chars_boundary_exact(self):
        """Kills mutant 41 (DEFAULT_PREVIEW_CHARS 120 -> 121).

        No `max_chars` argument is passed, so the default governs. Correct
        code truncates to 120 total (117 chars + "..."); the mutant
        truncates to 121.
        """
        out = redact.redact_secrets("z" * 200)
        self.assertEqual(len(out), 120)
        self.assertTrue(out.endswith("..."))


class TestBoundedGrowthCapBoundaries(TestEnvContext):
    """Class: F-7.6 bounded-growth safety-cap boundary mutations.

    `growth_cap = max(original_len * 2, 64)` is recomputed in each test
    using the SAME hardcoded formula (factor 2, floor 64) the production
    code uses today, independent of whichever single constant/operator a
    given mutant perturbs — that is what lets one test isolate one mutant.

    All inputs use `"pwd=1 "` units: the kv pattern
    (`password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret`)
    blanks the 1-char value into the fixed 10-char literal `"[REDACTED]"`,
    so `"pwd=1 "` (6 chars in) deterministically becomes `"pwd=[REDACTED] "`
    (15 chars out) regardless of the value's content — a clean, precisely
    computable growth ratio for constructing exact boundary lengths.
    """

    def test_growth_cap_floor_boundary_exact(self):
        """Kills mutant 54 (floor 64 -> 65 in `max(original_len * 2, 64)`).

        original_len=29 keeps `original_len * 2 == 58 < 64`, so the floor
        constant is what actually determines growth_cap. Growth from 4x
        "pwd=1 " + 5 filler chars lands post_redact_len at exactly 65:
        correct code's floor (64) makes 65 > 64 -> triggers the overflow
        truncation; the mutant's floor (65) makes 65 > 65 false -> no
        truncation, leaving the output untruncated and one char longer.
        """
        text_in = "pwd=1 " * 4 + "z" * 5  # original_len = 29
        out = redact.redact_secrets(text_in, max_chars=0)
        self.assertEqual(len(out), 64)
        self.assertTrue(out.endswith("[REDACTED:overflow]"))

    def test_growth_cap_operator_boundary_exact(self):
        """Kills mutant 56 (`post_redact_len > _growth_cap` -> `>=`).

        original_len=36 (>=32, so the floor doesn't apply: growth_cap is
        exactly `36 * 2 == 72`). Growth from 4x "pwd=1 " + 12 filler chars
        lands post_redact_len at exactly 72 too: correct code's `>` makes
        72 > 72 false -> untouched output; the mutant's `>=` makes 72 >= 72
        true -> spurious truncation with the overflow marker appended.
        """
        text_in = "pwd=1 " * 4 + "z" * 12  # original_len = 36, growth_cap = 72
        out = redact.redact_secrets(text_in, max_chars=0)
        self.assertNotIn("[REDACTED:overflow]", out)
        self.assertEqual(len(out), 72)

    def test_overflow_tail_and_breadcrumb_exact(self):
        """Kills mutants 57, 65, 66, 67, 68 (overflow-tail / breadcrumb
        f-string segments each wrapped in "XX...XX").

        10x "pwd=1 " (original_len=60) grows to 150 chars, well past
        growth_cap=max(120,64)=120, guaranteeing the overflow branch fires
        for both `>` and `>=` variants (this test is about the branch's
        BODY, not its trigger condition). The expected truncated body and
        the expected stderr breadcrumb are both reconstructed here from
        hardcoded literals, so any injected "XX" in either produces a
        mismatch.
        """
        unit_in = "pwd=1 "
        unit_out = "pwd=[REDACTED] "
        text_in = unit_in * 10  # original_len = 60
        full_pre_cap = unit_out * 10  # 150 chars, pre-truncation
        growth_cap = max(60 * 2, 64)  # 120
        tail = "[REDACTED:overflow]"  # 20 chars
        truncate_to = max(growth_cap - len(tail), 0)  # 100
        expected_out = full_pre_cap[:truncate_to] + tail

        import io
        import sys as _sys

        captured = io.StringIO()
        old_stderr = _sys.stderr
        _sys.stderr = captured
        try:
            out = redact.redact_secrets(text_in, max_chars=0)
        finally:
            _sys.stderr = old_stderr

        self.assertEqual(out, expected_out)

        expected_stderr_msg = (
            "redact_secrets: bounded-growth cap triggered — "
            "output 150 chars exceeded 2× "
            "input 60 chars; truncated to 120. "
            "breadcrumb=redact_overflow"
        )
        self.assertIn(expected_stderr_msg, captured.getvalue())


class TestMaxCharsTruncationBoundaries(TestEnvContext):
    """Class: final preview-truncation boundary mutations.

    Every test here uses inert `"z"` filler so the input reaches the
    truncation block completely unchanged by any `_PATTERNS` substitution,
    isolating the truncation logic itself.
    """

    def test_max_chars_gt_zero_boundary_exact(self):
        """Kills mutant 72 (`max_chars > 0` -> `max_chars > 1`).

        At max_chars=1: correct code's `1 > 0` is true -> enters the block
        and (since `1 > 3` is false) takes the else-branch `text[:1]`. The
        mutant's `1 > 1` is false -> skips truncation entirely, returning
        the full untruncated input.
        """
        out = redact.redact_secrets("z" * 10, max_chars=1)
        self.assertEqual(out, "z")

    def test_len_gt_max_chars_boundary_exact(self):
        """Kills mutant 73 (`len(text) > max_chars` -> `>=`).

        At max_chars=10 with a 10-char input: correct code's `10 > 10` is
        false -> no truncation, output unchanged. The mutant's `10 >= 10`
        is true -> enters the block and (since `10 > 3`) replaces the last
        3 chars with "...", producing different content at the same length.
        """
        out = redact.redact_secrets("z" * 10, max_chars=10)
        self.assertEqual(out, "z" * 10)

    def test_inner_max_chars_gt_3_lower_boundary_exact(self):
        """Kills mutant 75 (`max_chars > 3` -> `max_chars >= 3`).

        At max_chars=3: correct code's `3 > 3` is false -> else-branch
        `text[:3]` = "zzz". The mutant's `3 >= 3` is true -> takes the
        "..." branch with a zero-length prefix, producing "...".
        """
        out = redact.redact_secrets("z" * 10, max_chars=3)
        self.assertEqual(out, "zzz")

    def test_inner_max_chars_gt_3_upper_boundary_exact(self):
        """Kills mutant 76 (`max_chars > 3` -> `max_chars > 4`).

        At max_chars=4: correct code's `4 > 3` is true -> "..." branch,
        `text[:1] + "..."` = "z...". The mutant's `4 > 4` is false ->
        else-branch `text[:4]` = "zzzz".
        """
        out = redact.redact_secrets("z" * 10, max_chars=4)
        self.assertEqual(out, "z...")

    def test_truncate_offset_exact(self):
        """Kills mutant 78 (`text[:max_chars - 3]` -> `text[:max_chars - 4]`).

        At max_chars=10 with a 20-char input: correct code takes
        `text[:7] + "..."` = "zzzzzzz..." (10 chars total). The mutant
        takes `text[:6] + "..."` = "zzzzzz..." (9 chars total) — one
        character short.
        """
        out = redact.redact_secrets("z" * 20, max_chars=10)
        self.assertEqual(out, "zzzzzzz...")

    def test_else_branch_slice_not_none_exact(self):
        """Kills mutant 82 (`text = text[:max_chars]` -> `text = None`).

        At max_chars=2 (<=3, so the else-branch runs): correct code
        returns `text[:2]` = "zz". The mutant returns `None`.
        """
        out = redact.redact_secrets("z" * 10, max_chars=2)
        self.assertEqual(out, "zz")


class TestHashDescriptionErrorsHandler(TestEnvContext):
    """Class: `hash_description`'s `errors=` codec-handler-name mutation."""

    def test_replace_error_handler_survives_lone_surrogate(self):
        """Kills mutant 86 (`errors="replace"` -> `errors="XXreplaceXX"`).

        A plain ASCII/UTF-8-clean string never invokes the error handler at
        all (CPython only looks up `errors=` lazily, when an actual
        encoding error occurs), so an invalid handler NAME is invisible on
        clean input — that is exactly why this mutant survived the
        existing `test_hash_*` tests. A lone surrogate forces
        `str.encode("utf-8", ...)` to actually invoke the handler: correct
        code's valid "replace" name substitutes U+FFFD and returns a normal
        digest; the mutant's invalid name raises
        `LookupError: unknown error handler name`.
        """
        digest = redact.hash_description("\ud800")
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in digest))


if __name__ == "__main__":
    unittest.main()
