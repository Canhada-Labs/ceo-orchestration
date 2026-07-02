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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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
        """Garbage stdout → zeros + parse_error breadcrumb (never raises).

        PLAN-152 tests-02: this file was CI-dark (not in testpaths) since
        v1.0.0; wiring it into tests/unit surfaced that the parser now
        distinguishes 'no JSON lines' from a per-line 'JSON decode' error.
        Garbage with no JSON-looking line yields the former. The fail-open
        contract (zeros + non-None breadcrumb, never raises) is unchanged.
        """
        from _lib.adapters import codex
        usage = codex.parse_usage_from_codex_stdout("not json at all {{")
        self.assertEqual(usage["tokens_in"], 0)
        self.assertEqual(usage["tokens_out"], 0)
        self.assertEqual(usage["tokens_total"], 0)
        self.assertEqual(usage["model"], "")
        self.assertIsNotNone(usage["parse_error"])
        self.assertIn("no JSON lines", usage["parse_error"] or "")

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
            # PLAN-152 tests-02 (CI-dark drift): the current
            # make_invoke_command_redacted requires output_last_message_path
            # (build_exec_argv rejects an empty output file). The stale test
            # omitted it and never ran in CI.
            argv = codex.make_invoke_command_redacted(
                "review file with AKIAIOSFODNN7EXAMPLE leaked",
                model="gpt-5-codex",
                sandbox_mode="read-only",
                timeout_s=75,
                output_last_message_path="/tmp/codex-last-message.txt",
            )

        # This test (Case 5 — ADR-114 §AC9) certifies the redact→argv
        # ORDER, not the exact flag layout: assert on PRESENCE, not
        # position (the argv flag shape evolved — `--color never`, `-o
        # <file>`, reordered `--model`; the exact layout is covered by the
        # codex-shape suites, and any SPEC mcp-server.schema.md drift is a
        # separate docs-wave finding, not this callsite-coverage test's job).
        self.assertEqual(argv[0], "exec")
        self.assertIn("--model", argv)
        self.assertIn("gpt-5-codex", argv)
        self.assertIn("--", argv)
        # The PROMPT is the LAST argv element (after the `--` end-of-opts).
        # It MUST carry the redacted replacement, NOT the raw secret —
        # proving redact_outgoing ran BEFORE argv construction.
        prompt_arg = argv[-1]
        self.assertIn(sentinel_replacement, prompt_arg)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", prompt_arg)


if __name__ == "__main__":
    unittest.main()
