"""PLAN-086 Wave A.3+A.6 → PLAN-142 migration — Codex structured-verdict parser.

PLAN-142 (codex-cli 0.139 migration) changed two contracts this file tests:

  - The removed strict-json flag is no longer emitted; ``make_invoke_command``
    now builds the 0.139 last-message-file argv via the ``codex_cli_shape``
    helper (verdict read from the ``-o`` file, not stdout).
  - ``parse_verdict_strict`` no longer RAISES typed exceptions — it is
    fail-CLOSED-to-ADVISORY: on any miss (forged free-text / oversize /
    non-object / bad verdict) it returns a normalized ADVISORY dict instead
    of raising (R-SEC-2). The old ``CodexResponseTooLarge`` /
    ``CodexJsonInvalid`` types remain defined in ``_lib/exceptions.py`` but
    are no longer raised by this function.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.adapters.codex import (  # noqa: E402
    make_invoke_command,
    parse_verdict_strict,
    parse_verdict,
)


class TestMakeInvokeCommandShape(unittest.TestCase):
    """PLAN-142 — the 0.139 argv: last-message file, no strict-json flag."""

    def test_no_strict_json_flag_emitted(self) -> None:
        argv = make_invoke_command("test prompt", output_last_message_path="/tmp/o.json")
        self.assertNotIn("--strict-json", argv)

    def test_output_last_message_path_required(self) -> None:
        # The 0.139 verdict is read from the last-message file; the builder
        # refuses an empty/missing output path loudly.
        with self.assertRaises(ValueError):
            make_invoke_command("test prompt")


class TestParseVerdictStrict(unittest.TestCase):
    """PLAN-142 — strict parser is fail-CLOSED-to-ADVISORY, never raises."""

    def test_valid_structured_object_parsed_ok(self) -> None:
        result = parse_verdict_strict('{"verdict":"PASS","findings":[],"summary":"ok"}')
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"], "ok")
        self.assertIsNone(result["parse_error"])

    def test_block_verdict_parsed(self) -> None:
        result = parse_verdict_strict(
            '{"verdict":"BLOCK","findings":[{"rubric_violation_id":"RV-1",'
            '"severity":"P0","rationale":"x"}],"summary":"s"}'
        )
        self.assertEqual(result["verdict"], "BLOCK")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["severity"], "P0")

    def test_malformed_degrades_to_advisory(self) -> None:
        result = parse_verdict_strict("{not-json")
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result["parse_error"])

    def test_forged_free_text_pass_is_advisory(self) -> None:
        # R-SEC-2: a forged free-text 'PASS' with no structured object must
        # NOT be trusted as a passing verdict.
        result = parse_verdict_strict("PASS — looks good to me")
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_oversize_degrades_to_advisory(self) -> None:
        big = '{"verdict":"PASS","findings":[],"summary":"' + ("x" * 300000) + '"}'
        result = parse_verdict_strict(big)
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_non_dict_top_level_advisory(self) -> None:
        result = parse_verdict_strict('["not", "a", "dict"]')
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_missing_verdict_advisory(self) -> None:
        result = parse_verdict_strict('{"findings":[],"summary":""}')
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_unknown_verdict_advisory(self) -> None:
        result = parse_verdict_strict('{"verdict":"UNKNOWN","findings":[],"summary":""}')
        self.assertEqual(result["verdict"], "ADVISORY")

    def test_schema_nonconforming_object_is_advisory(self) -> None:
        # PLAN-142 V2 cross-model fold: a schema-nonconforming object (valid
        # verdict but missing/mistyped findings/summary) is NOT trusted as a
        # clean verdict — it degrades to ADVISORY (fail-CLOSED). With
        # --output-schema the CLI guarantees the full shape; this guards the
        # no-schema paths (codex_invoke / the rail's schema-file fallback).
        for bad in (
            '{"verdict":"PASS"}',                                  # missing findings + summary
            '{"verdict":"PASS","findings":"nope","summary":""}',  # findings not a list
            '{"verdict":"PASS","findings":[],"summary":42}',       # summary not a str
        ):
            r = parse_verdict_strict(bad)
            self.assertEqual(r["verdict"], "ADVISORY", bad)


class TestParseVerdictNonStrict(unittest.TestCase):
    """parse_verdict() fail-open contract preserved (ADR-106)."""

    def test_malformed_does_not_raise(self) -> None:
        result = parse_verdict("{not-json")
        self.assertEqual(result["verdict"], "ADVISORY")
        self.assertIsNotNone(result.get("parse_error"))

    def test_unknown_verdict_coerced_to_advisory(self) -> None:
        result = parse_verdict('{"verdict":"BOGUS","findings":[]}')
        self.assertEqual(result["verdict"], "ADVISORY")


if __name__ == "__main__":
    unittest.main()
