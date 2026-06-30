"""PLAN-085 Wave D.2 — Codex token-wire + egress-symmetry tests.

5 cases verifying ``parse_usage_from_codex_stdout`` extracts token
counts correctly + the ``make_invoke_command_redacted`` defensive
wrapper applies ``redact_outgoing`` BEFORE argv construction (ADR-114
§AC9 callsite-coverage symmetry).

  1. test_parse_usage_extracts_full_usage_object
  2. test_parse_usage_handles_missing_usage_block_returns_zeros
  3. test_parse_usage_fails_open_on_malformed_json
  4. test_parse_usage_coerces_non_int_token_fields
  5. test_make_invoke_command_redacted_applies_redact_before_argv

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


class TestParseUsageFromCodexStdout(TestEnvContext):
    """Cases 1-4 — token-count extraction from Codex MCP JSON envelope."""

    def test_parse_usage_extracts_full_usage_object(self) -> None:
        """OpenAI-shape ``usage`` sub-object → tokens_in/out/total populated."""
        from _lib.adapters import codex
        payload = (
            '{"verdict":"PASS","findings":[],"summary":"ok",'
            '"usage":{"input_tokens":1234,"output_tokens":567,'
            '"total_tokens":1801},"model":"gpt-5-codex"}'
        )
        usage = codex.parse_usage_from_codex_stdout(payload)
        self.assertEqual(usage["tokens_in"], 1234)
        self.assertEqual(usage["tokens_out"], 567)
        self.assertEqual(usage["tokens_total"], 1801)
        self.assertEqual(usage["model"], "gpt-5-codex")
        self.assertIsNone(usage["parse_error"])

    def test_parse_usage_handles_missing_usage_block_returns_zeros(self) -> None:
        """Older Codex CLI versions omit the usage block — must NOT error."""
        from _lib.adapters import codex
        payload = (
            '{"verdict":"PASS","findings":[],"summary":"ok",'
            '"model":"gpt-5-codex"}'
        )
        usage = codex.parse_usage_from_codex_stdout(payload)
        self.assertEqual(usage["tokens_in"], 0)
        self.assertEqual(usage["tokens_out"], 0)
        self.assertEqual(usage["tokens_total"], 0)
        # Model still surfaced even when usage absent.
        self.assertEqual(usage["model"], "gpt-5-codex")
        self.assertIsNone(usage["parse_error"])

    def test_parse_usage_fails_open_on_malformed_json(self) -> None:
        """Garbage stdout → zeros + parse_error breadcrumb (never raises)."""
        from _lib.adapters import codex
        usage = codex.parse_usage_from_codex_stdout("not json at all {{")
        self.assertEqual(usage["tokens_in"], 0)
        self.assertEqual(usage["tokens_out"], 0)
        self.assertEqual(usage["tokens_total"], 0)
        self.assertEqual(usage["model"], "")
        self.assertIsNotNone(usage["parse_error"])
        self.assertIn("JSON decode", usage["parse_error"] or "")

    def test_parse_usage_coerces_non_int_token_fields(self) -> None:
        """Mis-typed usage fields (str, None, negative) → coerced to >=0 ints.

        Defensive: Codex CLI versions / proxies sometimes emit floats or
        strings. parse_usage must NEVER raise on type mismatch + must
        floor at zero.
        """
        from _lib.adapters import codex
        payload = (
            '{"verdict":"PASS","findings":[],"summary":"ok",'
            '"usage":{"input_tokens":"not-a-number",'
            '"output_tokens":-99,"total_tokens":null},'
            '"model":"gpt-5-codex"}'
        )
        usage = codex.parse_usage_from_codex_stdout(payload)
        self.assertEqual(usage["tokens_in"], 0)
        self.assertEqual(usage["tokens_out"], 0)
        self.assertEqual(usage["tokens_total"], 0)
        self.assertIsNone(usage["parse_error"])


class TestMakeInvokeCommandRedacted(TestEnvContext):
    """Case 5 — ADR-114 §AC9 callsite-coverage: defensive redact-then-argv."""

    def test_make_invoke_command_redacted_applies_redact_before_argv(self) -> None:
        """``redact_outgoing`` MUST be applied BEFORE ``make_invoke_command``.

        We patch ``_lib.codex_egress_redact.redact_outgoing`` to verify:
        (a) the redactor is invoked exactly once with the raw prompt;
        (b) the redacted text flows into the argv vector (so a leaked
            secret in the prompt never reaches Codex's subprocess argv).
        """
        from _lib.adapters import codex
        from _lib import codex_egress_redact as _redact

        sentinel_replacement = "<REDACTED-AKIA>"

        def _fake_redact(text: str) -> str:
            # Confirm raw text reaches the redactor exactly once.
            self.assertIn("AKIAIOSFODNN7EXAMPLE", text)
            return text.replace("AKIAIOSFODNN7EXAMPLE", sentinel_replacement)

        with mock.patch.object(_redact, "redact_outgoing", side_effect=_fake_redact):
            argv = codex.make_invoke_command_redacted(
                "review file with AKIAIOSFODNN7EXAMPLE leaked",
                model="gpt-5-codex",
                sandbox_mode="read-only",
                timeout_s=75,
            )

        # argv shape per SPEC mcp-server.schema.md: ["exec", "--model",
        # MODEL, "--sandbox", MODE, "--json", "--no-color", "--", PROMPT].
        self.assertEqual(argv[0], "exec")
        self.assertEqual(argv[1], "--model")
        self.assertEqual(argv[2], "gpt-5-codex")
        # The PROMPT is the LAST argv element. It MUST contain the
        # redacted replacement, NOT the raw secret.
        prompt_arg = argv[-1]
        self.assertIn(sentinel_replacement, prompt_arg)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", prompt_arg)


if __name__ == "__main__":
    unittest.main()
