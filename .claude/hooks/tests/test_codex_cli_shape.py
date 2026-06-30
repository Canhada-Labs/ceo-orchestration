"""PLAN-142 — tests for the NEW non-kernel CLI-shape helper + 0.139 golden fixtures.

Covers (PLAN-142 §3 [P0]/[P1] tests):
  - codex_cli_shape.build_exec_argv / build_verdict_argv / build_verdict_usage_argv
    argv shapes for codex-cli 0.139 (verdict-only vs +usage, --output-schema).
  - LOUD unknown-model coercion (C3) + conservative sandbox coercion.
  - the make_invoke_command legacy adapter (json_events, resume retirement).
  - a structured 0.139 last-message object round-trips through
    parse_verdict_strict (the verdict the rail reads from the -o file).
  - the rewritten parse_usage_from_codex_stdout over a JSONL event stream
    (the "Extra data line 2" regression fixed; P1).

Offline only — no live binary, no network, no paid spend.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import codex_cli_shape as shape  # noqa: E402
from _lib.adapters import codex as adapter  # noqa: E402


class TestBuildExecArgv(TestEnvContext):
    """The 0.139 argv shape — verified flag surface, no dead flags."""

    _OUT = "/tmp/ceo_out.json"

    def _pairs(self, argv):
        """Return {flag: value} for two-token flags, for order-free asserts."""
        out = {}
        i = 0
        while i < len(argv) - 1:
            if argv[i].startswith("-") and argv[i] != "--":
                out[argv[i]] = argv[i + 1]
            i += 1
        return out

    def test_verdict_mode_shape(self):
        argv = shape.build_verdict_argv("review this", output_file=self._OUT)
        self.assertEqual(argv[0], "exec")
        p = self._pairs(argv)
        self.assertEqual(p["--color"], "never")
        self.assertEqual(p["--sandbox"], "read-only")
        self.assertEqual(p["-o"], self._OUT)
        # PLAN-142 D5 (smoke-resolved): --model is OMITTED by default so the
        # Codex account uses its own default (forcing a catalog id 400s on a
        # ChatGPT-login account).
        self.assertNotIn("--model", argv)
        # No usage stream on the live rail.
        self.assertNotIn("--json", argv)
        # No dead 0.128 flags.
        for dead in ("--no-color", "--strict-json", "--read-only", "--resume"):
            self.assertNotIn(dead, argv)
        # Prompt is the trailing positional after the -- sentinel.
        self.assertEqual(argv[argv.index("--") + 1], "review this")

    def test_explicit_model_emitted(self):
        # An explicit, allowlisted override IS emitted.
        argv = shape.build_verdict_argv("p", output_file=self._OUT, model="o3")
        self.assertIn("--model", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "o3")

    def test_usage_mode_adds_json(self):
        argv = shape.build_verdict_usage_argv("p", output_file=self._OUT)
        self.assertIn("--json", argv)

    def test_output_schema_emitted_when_provided(self):
        argv = shape.build_verdict_argv("p", output_file=self._OUT, schema_file="/tmp/s.json")
        self.assertIn("--output-schema", argv)
        self.assertEqual(argv[argv.index("--output-schema") + 1], "/tmp/s.json")

    def test_empty_prompt_raises(self):
        with self.assertRaises(ValueError):
            shape.build_verdict_argv("", output_file=self._OUT)

    def test_empty_output_file_raises(self):
        with self.assertRaises(ValueError):
            shape.build_verdict_argv("p", output_file="")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            shape.build_exec_argv("p", mode="bogus", model=None, sandbox_mode="read-only", output_file=self._OUT)


class TestCoercion(TestEnvContext):
    """LOUD model coercion (C3) + conservative sandbox coercion."""

    def test_model_none_omits(self):
        # None / "" → None ("use account default"; DEFAULT_MODEL is None).
        self.assertIsNone(shape.coerce_model(None))
        self.assertIsNone(shape.coerce_model(""))
        self.assertIsNone(shape.DEFAULT_MODEL)

    def test_model_valid_passthrough(self):
        self.assertEqual(shape.coerce_model("o3"), "o3")
        # gpt-5.5 (the Owner account default) is an allowlisted explicit id.
        self.assertEqual(shape.coerce_model("gpt-5.5"), "gpt-5.5")

    def test_model_unknown_is_loud(self):
        with self.assertRaises(shape.UnknownCodexModel):
            shape.coerce_model("gpt-99-super")

    def test_sandbox_unknown_coerces_conservative(self):
        self.assertEqual(shape.coerce_sandbox_mode("nonsense"), shape.DEFAULT_SANDBOX_MODE)
        self.assertEqual(shape.coerce_sandbox_mode(None), shape.DEFAULT_SANDBOX_MODE)

    def test_sandbox_valid_passthrough(self):
        self.assertEqual(shape.coerce_sandbox_mode("workspace-write"), "workspace-write")


class TestLegacyAdapter(TestEnvContext):
    """make_invoke_command adapter: json_events, resume retirement, output path."""

    _OUT = "/tmp/ceo_out.json"

    def test_json_events_selects_usage_mode(self):
        argv = shape.make_invoke_command("p", output_last_message_path=self._OUT, json_events=True)
        self.assertIn("--json", argv)
        argv2 = shape.make_invoke_command("p", output_last_message_path=self._OUT, json_events=False)
        self.assertNotIn("--json", argv2)

    def test_resume_thread_id_retired(self):
        with self.assertRaises(NotImplementedError):
            shape.make_invoke_command("p", output_last_message_path=self._OUT, resume_thread_id="x")

    def test_output_schema_path_forwarded(self):
        argv = shape.make_invoke_command("p", output_last_message_path=self._OUT, output_schema_path="/tmp/s.json")
        self.assertIn("--output-schema", argv)


class TestVerdictSchema(TestEnvContext):
    """The --output-schema payload is valid, deterministic JSON."""

    def test_schema_json_is_valid_and_sorted(self):
        s = shape.verdict_output_schema_json()
        obj = json.loads(s)
        self.assertEqual(obj["type"], "object")
        self.assertIn("verdict", obj["required"])
        # deterministic: sorted keys -> re-serialize identical
        self.assertEqual(s, json.dumps(json.loads(s), sort_keys=True, ensure_ascii=False))


class TestGolden0139LastMessage(TestEnvContext):
    """A structured 0.139 last-message object round-trips to a verdict.

    This is the offline stand-in for a captured real -o file: exactly ONE
    JSON object, the final agent message. The live smoke test (V1) validates
    the real binary writes this shape; here we pin the parser contract.
    """

    def test_pass_object_round_trips(self):
        last_message = json.dumps({"verdict": "PASS", "findings": [], "summary": "clean"})
        r = adapter.parse_verdict_strict(last_message)
        self.assertEqual(r["verdict"], "PASS")
        self.assertIsNone(r["parse_error"])

    def test_block_object_with_findings(self):
        last_message = json.dumps({
            "verdict": "BLOCK",
            "findings": [
                {"rubric_violation_id": "RV-7", "severity": "P0",
                 "file": "x.py", "line": 12, "rationale": "secret literal"},
            ],
            "summary": "one P0",
        })
        r = adapter.parse_verdict_strict(last_message)
        self.assertEqual(r["verdict"], "BLOCK")
        self.assertEqual(len(r["findings"]), 1)
        self.assertEqual(r["findings"][0]["rubric_violation_id"], "RV-7")
        self.assertEqual(r["findings"][0]["line"], 12)

    def test_fenced_object_still_parses(self):
        # A chatty model may wrap the object in a ```json fence — stripped.
        last_message = "```json\n" + json.dumps({"verdict": "PASS", "findings": [], "summary": ""}) + "\n```"
        r = adapter.parse_verdict_strict(last_message)
        self.assertEqual(r["verdict"], "PASS")


class TestParseUsageJsonl(TestEnvContext):
    """P1 — parse_usage over a 0.139 JSONL event stream (no 'Extra data line 2')."""

    def test_last_usage_event_wins(self):
        stream = "\n".join([
            json.dumps({"type": "task_started"}),
            json.dumps({"type": "token_count", "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}, "model": "gpt-5-codex"}),
            json.dumps({"type": "task_complete"}),
        ])
        u = adapter.parse_usage_from_codex_stdout(stream)
        self.assertEqual(u["tokens_in"], 100)
        self.assertEqual(u["tokens_out"], 50)
        self.assertEqual(u["tokens_total"], 150)
        self.assertEqual(u["model"], "gpt-5-codex")
        self.assertIsNone(u["parse_error"])

    def test_non_json_banner_lines_tolerated(self):
        stream = "Starting codex...\n" + json.dumps({"usage": {"total_tokens": 7}})
        u = adapter.parse_usage_from_codex_stdout(stream)
        self.assertEqual(u["tokens_total"], 7)

    def test_no_usage_event_returns_zeros(self):
        stream = json.dumps({"type": "task_started"}) + "\n" + json.dumps({"type": "done"})
        u = adapter.parse_usage_from_codex_stdout(stream)
        self.assertEqual(u["tokens_total"], 0)
        self.assertIsNone(u["parse_error"])  # absence is not an error


if __name__ == "__main__":
    unittest.main()
