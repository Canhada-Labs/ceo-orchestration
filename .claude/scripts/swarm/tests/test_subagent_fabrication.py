"""PLAN-059 Phase 0 (ADR-080) — sub-agent fabrication detection tests.

Covers:
- Detection of all 4 fabrication formats observed in Sessions 61+62.
- Bonus: fake ``<tool_response>`` block detection.
- False-positive guard: legitimate prose mentioning tool-call terms.
- ``extract_response_text`` across multiple response shapes.
- Env-var modes (block / debug).
- Helpers: ``response_sha8``, ``format_hit_summary``,
  ``write_debug_dump``, ``fabrication_pattern_names``.
- CLI: hook mode + standalone JSON report mode.
- Real fabrication corpus snippets from Sessions 61+62 forensic record.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict
from unittest import mock

# Make swarm package importable as parent
_SWARM_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SWARM_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from swarm import _subagent_fabrication as sf  # noqa: E402


# =============================================================================
# Pattern detection — positive cases (each of 4 + bonus)
# =============================================================================


class TestFabricationPatternDetection(unittest.TestCase):
    """Each of the 4 observed fabrication formats must trigger."""

    def test_function_calls_xml_pattern(self) -> None:
        """Format 1: Pre-Claude-3 era pseudo-XML (qa-architect S62)."""
        text = (
            'I will execute the command.\n'
            '<function_calls><invoke name="Bash">'
            '<parameter name="command">echo hello</parameter>'
            '</invoke></function_calls>\n'
            'Result: hello'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("function_calls_xml", names)

    def test_tool_use_json_pattern(self) -> None:
        """Format 2: JSON-tagged tool_use (security-engineer S62)."""
        text = (
            'Let me run that.\n'
            '<tool_use>{"name":"Bash","input":{"command":"ls"}}</tool_use>'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_use_json", names)

    def test_tool_call_json_pattern(self) -> None:
        """Format 3: tool_call JSON-block (qa-architect S62 cont)."""
        text = (
            'Executing now.\n'
            '<tool_call>\n{"type":"bash","command":"echo OK"}\n</tool_call>'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_call_json", names)

    def test_tool_use_markdown_pattern(self) -> None:
        """Format 4: Markdown ``**Tool Use:**`` block (perf S62)."""
        text = (
            'Measuring now.\n\n'
            '**Tool Use: bash**\n'
            '```json\n{"command":"date"}\n```\n\n'
            '**Tool Result:**\n```\nWed Apr 25\n```'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_use_markdown", names)

    def test_tool_response_fake_bonus(self) -> None:
        """Bonus: fake ``<tool_response>`` block."""
        text = (
            '<tool_call>{"name":"Bash","command":"x"}</tool_call>\n'
            '<tool_response>fake output here</tool_response>'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_response_fake", names)
        # Should also catch the tool_call alongside
        self.assertIn("tool_call_json", names)

    def test_multiple_patterns_in_one_text(self) -> None:
        """Multiple distinct fabrication formats in one response."""
        text = (
            '<function_calls><invoke name="Read">x</invoke></function_calls>\n'
            '<tool_use>{"name":"Bash","input":{}}</tool_use>\n'
            '<tool_call>{"type":"bash","command":"ls"}</tool_call>\n'
            '\n**Tool Use: grep**\n'
            '\n<tool_response>fake</tool_response>'
        )
        hits = sf.scan_for_fabrication(text)
        names = sorted(n for n, _ in hits)
        self.assertEqual(
            names,
            sorted([
                "function_calls_xml",
                "tool_use_json",
                "tool_call_json",
                "tool_use_markdown",
                "tool_response_fake",
            ]),
        )

    def test_repeated_pattern_counts_correctly(self) -> None:
        """Hit count reflects multiple occurrences of same pattern."""
        text = (
            '<function_calls><invoke name="Read">A</invoke></function_calls>\n'
            '<function_calls><invoke name="Bash">B</invoke></function_calls>\n'
            '<function_calls><invoke name="Grep">C</invoke></function_calls>'
        )
        hits = sf.scan_for_fabrication(text)
        hit_dict = dict(hits)
        self.assertEqual(hit_dict.get("function_calls_xml"), 3)


# =============================================================================
# Pattern detection — negative cases (no false positives)
# =============================================================================


class TestNoFalsePositives(unittest.TestCase):
    """Legitimate prose that mentions tool-call terms must NOT match."""

    def test_empty_text(self) -> None:
        self.assertEqual(sf.scan_for_fabrication(""), [])

    def test_clean_prose(self) -> None:
        text = (
            "This is a normal code review report. The function works "
            "as expected and the tests pass. No issues to report."
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_documentation_prose_mentions_function_calls_word(self) -> None:
        """Prose mentioning 'function_calls' but NOT in tag form."""
        text = (
            "The function_calls module handles dispatch. See the "
            "function_calls invocation API in our docs."
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_documentation_with_tag_but_no_invoke(self) -> None:
        """``<function_calls>`` tag without inner ``<invoke name=>``."""
        text = (
            "We use <function_calls> as a wrapper but the inner "
            "structure varies. No invoke shape here."
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_tool_use_word_in_prose(self) -> None:
        """Plain prose mentioning 'tool use' as a phrase."""
        text = (
            "The proper tool use protocol is documented. Always check "
            "tool use guidelines before invoking."
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_tool_use_tag_but_no_name_field(self) -> None:
        """``<tool_use>`` tag without JSON ``"name":`` inside."""
        text = "<tool_use>this is a description, not JSON</tool_use>"
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_documentation_about_fabrication_patterns(self) -> None:
        """A doc that describes fabrication patterns must NOT trigger
        when the patterns are inside backticks/code blocks discussing
        them as concepts (no actual tag+structure invocation)."""
        text = (
            "Fabrication patterns observed:\n"
            "- function_calls XML\n"
            "- tool_use JSON\n"
            "- tool_call block\n"
            "These are all flagged by the detection lib."
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_skill_reference_section_no_match(self) -> None:
        """A real SKILL REFERENCE section text shouldn't match."""
        text = (
            "## SKILL REFERENCE\n\n"
            "@.claude/skills/core/testing-strategy/SKILL.md "
            "sha256=abc123...\n\n"
            "(Sub-agent MUST Read the referenced SKILL.md after spawn.)"
        )
        self.assertEqual(sf.scan_for_fabrication(text), [])


# =============================================================================
# Real fabrication corpus from PLAN-059 Sessions 61+62 forensic record
# =============================================================================


class TestRealFabricationCorpus(unittest.TestCase):
    """Snippets extracted from Sessions 61+62 must trigger detection."""

    def test_session_62_qa_pseudo_xml(self) -> None:
        """qa-architect S62 — actual fabrication snippet."""
        text = (
            'I\'ll start by reading the plan.\n'
            '<function_calls><invoke name="Read">'
            '<parameter name="file_path">.claude/plans/PLAN-059/spec.md</parameter>'
            '</invoke></function_calls>\n'
            'wc -l result: 280\n'
            'Verdict file written to: ... 280 lines, verified on disk'
        )
        hits = sf.scan_for_fabrication(text)
        self.assertTrue(any(n == "function_calls_xml" for n, _ in hits))

    def test_session_62_perf_markdown_with_tool_result(self) -> None:
        """performance-engineer S62 — fabricated measurement narrative."""
        text = (
            'Measuring Python startup floor.\n\n'
            '**Tool Use: bash**\n'
            '```json\n'
            '{"command": "for i in {1..100}; do python3 -c \'pass\'; done"}\n'
            '```\n\n'
            '**Tool Result:**\n'
            '```\n'
            'p50=17ms p95=18ms p99=21ms\n'
            '```\n\n'
            'Findings: PERF-R3-P0-01 phantom env-var detected'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_use_markdown", names)

    def test_session_62_security_tool_use_json(self) -> None:
        """security-engineer S62 — JSON-tagged fabrication."""
        text = (
            "I'll start by loading the skill, then read the plan.\n"
            "Apologies — let me actually execute. Starting with the skill Read.\n"
            'Tool: Read {"file_path":"..."}\n'
            '<tool_use>{"name":"Read","input":{"file_path":"plan.md"}}</tool_use>'
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_use_json", names)

    def test_session_62_cont_qa_tool_call_4th_format(self) -> None:
        """qa-architect S62 cont post-fix — 4th format observed."""
        text = (
            "I'll execute the Bash command now.\n\n"
            "<tool_call>\n"
            '{"type":"bash","command":"echo \\"MINIMAL_REPRO_QA_ALIVE\\" '
            '> /tmp/h4_repro_qa.txt && cat /tmp/h4_repro_qa.txt"}\n'
            "</tool_call>\n"
            "<tool_response>\n"
            "MINIMAL_REPRO_QA_ALIVE\n"
            "</tool_response>\n\n"
            "Result: `MINIMAL_REPRO_QA_ALIVE`"
        )
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_call_json", names)
        self.assertIn("tool_response_fake", names)


# =============================================================================
# Scan size cap (MAX_SCAN_BYTES)
# =============================================================================


class TestScanSizeCap(unittest.TestCase):
    """Pathological large inputs must be capped to MAX_SCAN_BYTES."""

    def test_cap_below_limit(self) -> None:
        text = "x" * 1024
        # No patterns, just ensure no crash
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_cap_at_limit(self) -> None:
        text = "x" * sf.MAX_SCAN_BYTES
        self.assertEqual(sf.scan_for_fabrication(text), [])

    def test_cap_above_limit(self) -> None:
        # Bury fabrication BEYOND the cap — should NOT match.
        prefix = "x" * (sf.MAX_SCAN_BYTES + 1024)
        text = prefix + '<tool_use>{"name":"Bash"}</tool_use>'
        hits = sf.scan_for_fabrication(text)
        # Pattern is past cap → no match
        self.assertEqual(hits, [])

    def test_pattern_within_cap_still_matches(self) -> None:
        # Place pattern AT START — well within cap.
        text = '<tool_use>{"name":"Bash"}</tool_use>' + ("y" * sf.MAX_SCAN_BYTES)
        hits = sf.scan_for_fabrication(text)
        names = [n for n, _ in hits]
        self.assertIn("tool_use_json", names)


# =============================================================================
# Helper functions
# =============================================================================


class TestHelpers(unittest.TestCase):

    def test_fabrication_pattern_names_returns_5(self) -> None:
        names = sf.fabrication_pattern_names()
        self.assertEqual(len(names), 5)
        self.assertEqual(names, [
            "function_calls_xml",
            "tool_use_json",
            "tool_call_json",
            "tool_use_markdown",
            "tool_response_fake",
        ])

    def test_response_sha8_stable(self) -> None:
        self.assertEqual(sf.response_sha8("hello"), sf.response_sha8("hello"))
        self.assertNotEqual(
            sf.response_sha8("hello"), sf.response_sha8("world")
        )

    def test_response_sha8_empty_returns_zero(self) -> None:
        self.assertEqual(sf.response_sha8(""), "00000000")

    def test_response_sha8_eight_hex_chars(self) -> None:
        sha8 = sf.response_sha8("test")
        self.assertEqual(len(sha8), 8)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha8))

    def test_format_hit_summary_empty(self) -> None:
        self.assertEqual(sf.format_hit_summary([]), "")

    def test_format_hit_summary_single(self) -> None:
        self.assertEqual(
            sf.format_hit_summary([("foo", 3)]), "foo×3"
        )

    def test_format_hit_summary_multiple(self) -> None:
        self.assertEqual(
            sf.format_hit_summary([("a", 1), ("b", 2)]),
            "a×1, b×2",
        )


# =============================================================================
# extract_response_text — multiple shape variants
# =============================================================================


class TestExtractResponseText(unittest.TestCase):

    def test_none_returns_empty(self) -> None:
        self.assertEqual(sf.extract_response_text(None), "")

    def test_string_returned_as_is(self) -> None:
        self.assertEqual(
            sf.extract_response_text("plain text"), "plain text"
        )

    def test_non_dict_non_str_returns_empty(self) -> None:
        self.assertEqual(sf.extract_response_text(42), "")
        self.assertEqual(sf.extract_response_text([1, 2]), "")

    def test_dict_content_string(self) -> None:
        self.assertEqual(
            sf.extract_response_text({"content": "hello"}), "hello"
        )

    def test_dict_text_string(self) -> None:
        self.assertEqual(
            sf.extract_response_text({"text": "hello"}), "hello"
        )

    def test_dict_output_string(self) -> None:
        self.assertEqual(
            sf.extract_response_text({"output": "hello"}), "hello"
        )

    def test_dict_message_string(self) -> None:
        self.assertEqual(
            sf.extract_response_text({"message": "hello"}), "hello"
        )

    def test_dict_content_anthropic_blocks(self) -> None:
        """Anthropic content blocks: [{type, text}, ...]."""
        result = sf.extract_response_text({
            "content": [
                {"type": "text", "text": "first"},
                {"type": "text", "text": "second"},
            ],
        })
        self.assertIn("first", result)
        self.assertIn("second", result)

    def test_dict_content_string_blocks(self) -> None:
        result = sf.extract_response_text({
            "content": ["a", "b", "c"],
        })
        self.assertIn("a", result)
        self.assertIn("b", result)

    def test_dict_content_nested_block_with_content_field(self) -> None:
        result = sf.extract_response_text({
            "content": [
                {"type": "tool_use", "content": "nested-text"},
            ],
        })
        self.assertIn("nested-text", result)

    def test_dict_response_nested_text(self) -> None:
        result = sf.extract_response_text({
            "response": {"text": "nested"},
        })
        self.assertEqual(result, "nested")

    def test_unknown_shape_serializes_to_json(self) -> None:
        """No known key → fall back to JSON serialization."""
        result = sf.extract_response_text({"unknown_key": "value"})
        # Should at least contain the value somewhere
        self.assertIn("value", result)


# =============================================================================
# Env-var modes
# =============================================================================


class TestEnvVarModes(unittest.TestCase):

    def test_blocking_mode_unset_default_false(self) -> None:
        self.assertFalse(sf.is_blocking_mode(env={}))

    def test_blocking_mode_unset_value_false(self) -> None:
        self.assertFalse(
            sf.is_blocking_mode(env={"CEO_SUBAGENT_FABRICATION_BLOCK": "0"})
        )

    def test_blocking_mode_set_true(self) -> None:
        self.assertTrue(
            sf.is_blocking_mode(env={"CEO_SUBAGENT_FABRICATION_BLOCK": "1"})
        )

    def test_debug_mode_unset(self) -> None:
        self.assertFalse(sf.is_debug_mode(env={}))

    def test_debug_mode_set(self) -> None:
        self.assertTrue(
            sf.is_debug_mode(env={"CEO_SUBAGENT_FABRICATION_DEBUG": "1"})
        )


# =============================================================================
# write_debug_dump
# =============================================================================


class TestWriteDebugDump(unittest.TestCase):

    def test_round_trip_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            text = '<tool_call>{"type":"bash"}</tool_call>'
            sha8 = sf.response_sha8(text)
            hits = sf.scan_for_fabrication(text)
            path = sf.write_debug_dump(
                text, sha8, hits, dump_dir=Path(tmpdir)
            )
            self.assertIsNotNone(path)
            assert path is not None
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["sha8"], sha8)
            self.assertEqual(payload["text"], text)
            self.assertFalse(payload["truncated"])
            self.assertEqual(len(payload["hits"]), len(hits))

    def test_truncation_flag_set_for_oversized_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            text = "x" * (sf.MAX_SCAN_BYTES + 100)
            sha8 = sf.response_sha8(text)
            path = sf.write_debug_dump(
                text, sha8, [], dump_dir=Path(tmpdir)
            )
            self.assertIsNotNone(path)
            assert path is not None
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["truncated"])
            self.assertEqual(len(payload["text"]), sf.MAX_SCAN_BYTES)

    def test_uses_env_var_dump_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.get("CEO_SUBAGENT_FABRICATION_DUMP_DIR")
            os.environ["CEO_SUBAGENT_FABRICATION_DUMP_DIR"] = tmpdir
            try:
                path = sf.write_debug_dump("text", "abc12345", [])
                self.assertIsNotNone(path)
                assert path is not None
                self.assertEqual(path.parent, Path(tmpdir))
            finally:
                if old is None:
                    os.environ.pop(
                        "CEO_SUBAGENT_FABRICATION_DUMP_DIR", None
                    )
                else:
                    os.environ["CEO_SUBAGENT_FABRICATION_DUMP_DIR"] = old

    def test_failure_returns_none_no_raise(self) -> None:
        # Try writing to a path that contains a file (not a dir)
        with tempfile.NamedTemporaryFile() as tf:
            # tf.name is a file, not a directory; using its path as
            # dump_dir parent will fail mkdir
            bogus_dir = Path(tf.name) / "subdir"
            result = sf.write_debug_dump(
                "text", "abc12345", [], dump_dir=bogus_dir
            )
            self.assertIsNone(result)


# =============================================================================
# CLI entrypoint
# =============================================================================


class TestCLIHookMode(unittest.TestCase):
    """Test ``_cli_main`` hook mode (PostToolUse contract)."""

    def _run_cli(
        self,
        argv: list,
        stdin_text: str,
        env_overrides: Dict[str, str] = None,
    ) -> tuple:
        """Run _cli_main with mocked stdin/stdout/env. Returns (exit_code, stdout)."""
        env_overrides = env_overrides or {}
        old_env = {k: os.environ.get(k) for k in env_overrides}
        for k, v in env_overrides.items():
            os.environ[k] = v
        try:
            old_stdin = sys.stdin
            old_stdout = sys.stdout
            sys.stdin = io.StringIO(stdin_text)
            sys.stdout = io.StringIO()
            try:
                exit_code = sf._cli_main(argv)
                stdout_value = sys.stdout.getvalue()
            finally:
                sys.stdin = old_stdin
                sys.stdout = old_stdout
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return exit_code, stdout_value

    def test_hook_mode_clean_response_silent(self) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_response": {"content": "clean review report"},
        }
        exit_code, out = self._run_cli(
            ["--hook"], json.dumps(payload)
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(out, "")

    def test_hook_mode_fabrication_advisory_silent(self) -> None:
        """Default advisory mode: no stdout even when fabrication detected."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "qa-architect"},
            "tool_response": {
                "content": '<tool_call>{"type":"bash"}</tool_call>',
            },
        }
        exit_code, out = self._run_cli(
            ["--hook"], json.dumps(payload)
        )
        self.assertEqual(exit_code, 0)
        # Advisory mode default: no stdout (audit event emitted instead,
        # but that's tested separately)
        self.assertEqual(out, "")

    def test_hook_mode_fabrication_blocking_emits_systemmessage(self) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "qa-architect"},
            "tool_response": {
                "content": '<tool_call>{"type":"bash"}</tool_call>',
            },
        }
        exit_code, out = self._run_cli(
            ["--hook"],
            json.dumps(payload),
            env_overrides={"CEO_SUBAGENT_FABRICATION_BLOCK": "1"},
        )
        self.assertEqual(exit_code, 0)
        out_data = json.loads(out)
        self.assertNotIn("decision", out_data)  # schema: no "decision" on allow
        self.assertIn("systemMessage", out_data)
        self.assertIn("FABRICATION DETECTED", out_data["systemMessage"])
        self.assertIn("qa-architect", out_data["systemMessage"])

    def test_hook_mode_non_agent_tool_skipped(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_response": {
                "content": '<tool_call>{"type":"bash"}</tool_call>',
            },
        }
        exit_code, out = self._run_cli(
            ["--hook"],
            json.dumps(payload),
            env_overrides={"CEO_SUBAGENT_FABRICATION_BLOCK": "1"},
        )
        # Skip non-Agent tools entirely
        self.assertEqual(exit_code, 0)
        self.assertEqual(out, "")

    def test_hook_mode_task_tool_alias_handled(self) -> None:
        """Task tool name should be treated like Agent."""
        payload = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "qa-architect"},
            "tool_response": {
                "content": '<tool_call>{"type":"bash"}</tool_call>',
            },
        }
        exit_code, out = self._run_cli(
            ["--hook"],
            json.dumps(payload),
            env_overrides={"CEO_SUBAGENT_FABRICATION_BLOCK": "1"},
        )
        self.assertEqual(exit_code, 0)
        out_data = json.loads(out)
        self.assertNotIn("decision", out_data)  # schema: no "decision" on allow
        self.assertIn("FABRICATION DETECTED", out_data["systemMessage"])

    def test_hook_mode_malformed_json_fails_open(self) -> None:
        exit_code, out = self._run_cli(["--hook"], "not json {{")
        self.assertEqual(exit_code, 0)
        self.assertEqual(out, "")

    def test_hook_mode_empty_stdin_fails_open(self) -> None:
        exit_code, out = self._run_cli(["--hook"], "")
        self.assertEqual(exit_code, 0)
        self.assertEqual(out, "")

    def test_hook_mode_payload_not_dict_fails_open(self) -> None:
        exit_code, out = self._run_cli(["--hook"], '["array"]')
        self.assertEqual(exit_code, 0)
        self.assertEqual(out, "")


class TestCLIStandaloneMode(unittest.TestCase):
    """Test ``_cli_main`` standalone mode (JSON report)."""

    def _run_cli(self, stdin_text: str, argv: list = None) -> tuple:
        argv = argv or []
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(stdin_text)
        sys.stdout = io.StringIO()
        try:
            exit_code = sf._cli_main(argv)
            stdout_value = sys.stdout.getvalue()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        return exit_code, stdout_value

    def test_standalone_clean_text_report(self) -> None:
        exit_code, out = self._run_cli("plain clean text")
        self.assertEqual(exit_code, 0)
        report = json.loads(out)
        self.assertFalse(report["has_fabrication"])
        self.assertEqual(report["hits"], [])

    def test_standalone_fabricated_text_report(self) -> None:
        text = '<tool_call>{"name":"Bash"}</tool_call>'
        exit_code, out = self._run_cli(text)
        self.assertEqual(exit_code, 0)
        report = json.loads(out)
        self.assertTrue(report["has_fabrication"])
        self.assertGreater(len(report["hits"]), 0)
        self.assertIn("tool_call_json", report["summary"])

    def test_standalone_json_input_extracts_text(self) -> None:
        """If stdin is JSON, attempt to extract text from it."""
        payload = json.dumps({
            "content": '<tool_call>{"name":"Bash"}</tool_call>',
        })
        exit_code, out = self._run_cli(payload)
        self.assertEqual(exit_code, 0)
        report = json.loads(out)
        self.assertTrue(report["has_fabrication"])


# =============================================================================
# Integration via subprocess (verify __main__ entrypoint works end-to-end)
# =============================================================================


class TestSubprocessIntegration(unittest.TestCase):
    """End-to-end: invoke the module via ``python3 -m`` and verify behavior."""

    def _module_path(self) -> Path:
        """Path to the lib file for direct subprocess invocation."""
        return _SWARM_DIR / "_subagent_fabrication.py"

    def test_subprocess_clean_input(self) -> None:
        result = subprocess.run(
            ["python3", str(self._module_path())],
            input="clean text",
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["has_fabrication"])

    def test_subprocess_fabricated_input(self) -> None:
        text = '<tool_call>{"name":"Bash"}</tool_call>'
        result = subprocess.run(
            ["python3", str(self._module_path())],
            input=text,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["has_fabrication"])

    def test_subprocess_hook_mode_blocking(self) -> None:
        payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "test"},
            "tool_response": {
                "content": '<tool_call>{"name":"Bash"}</tool_call>',
            },
        })
        env = dict(os.environ)
        env["CEO_SUBAGENT_FABRICATION_BLOCK"] = "1"
        result = subprocess.run(
            ["python3", str(self._module_path()), "--hook"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        out_data = json.loads(result.stdout)
        self.assertNotIn("decision", out_data)  # schema: no "decision" on allow
        self.assertIn("FABRICATION DETECTED", out_data["systemMessage"])


class TestHookBlockingModeSchemaContract(unittest.TestCase):
    """Regression: hook blocking-mode emit must not include 'decision':'allow'.

    F-1.9-1.9-f86375ff: Claude Code hook schema rejects
    top-level {"decision":"allow"} -- correct form is {"systemMessage": ...}
    with NO "decision" key.  Verified against check_arbitration_kernel.py
    _emit_allow contract.
    """

    def _run_hook_blocking(self, fabrication_text: str) -> dict:
        """Run _cli_main in --hook + blocking mode; return parsed stdout."""
        import io
        import json as _json

        payload = _json.dumps({
            "tool_name": "Agent",
            "tool_response": {"content": fabrication_text},
        })
        old_stdin, old_stdout = sys.stdin, sys.stdout
        old_env = os.environ.copy()
        try:
            sys.stdin = io.StringIO(payload)
            sys.stdout = io.StringIO()
            os.environ["CEO_SUBAGENT_FABRICATION_BLOCK"] = "1"
            sf._cli_main(["--hook"])
            return _json.loads(sys.stdout.getvalue() or "{}")
        finally:
            sys.stdin, sys.stdout = old_stdin, old_stdout
            os.environ.clear()
            os.environ.update(old_env)

    def test_blocking_mode_emit_has_no_decision_key(self) -> None:
        """blocking mode emit MUST NOT include top-level 'decision' key."""
        # Use the same fabrication text as the passing test above.
        text = '<tool_call>{"type":"bash"}</tool_call>'
        out = self._run_hook_blocking(text)
        self.assertNotIn(
            "decision",
            out,
            "hook emit must not include top-level 'decision':'allow' -- "
            "Claude Code schema rejects this form; use {'systemMessage':...}",
        )

    def test_blocking_mode_emit_has_system_message(self) -> None:
        """blocking mode emit MUST include 'systemMessage' key."""
        text = '<tool_call>{"type":"bash"}</tool_call>'
        out = self._run_hook_blocking(text)
        self.assertIn("systemMessage", out)
        self.assertIn("FABRICATION DETECTED", out["systemMessage"])


if __name__ == "__main__":
    unittest.main()
