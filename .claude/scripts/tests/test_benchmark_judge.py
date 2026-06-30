"""Unit tests for benchmark-judge.py (PLAN-011 Phase 3).

Covers:
- Golden prompt hash stability (committed value asserted)
- Default-deny payload (exactly 3 top-level keys)
- Two-pass grading (forward + reverse) produces both scores
- Cross-provider guard rejects same adapter
- Mock judge is deterministic
- Redaction applied before payload reaches the adapter
- JSON schema validation (refused=bool, score=int)
- CLI exit codes (0 happy, 2 bad file, 3 cross-provider, 4 unreachable)
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent
_HOOKS_TESTS = _SCRIPTS.parent / "hooks"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_HOOKS_TESTS))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    path = _SCRIPTS / "benchmark-judge.py"
    spec = importlib.util.spec_from_file_location("benchmark_judge", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bj = _load_module()


# Pinned SHA-256 of `_schemas/judge-prompt.md`. If the committed prompt
# changes the test fails and the committer must explicitly update
# this line AND ADR-030's "golden prompt hash" entry.
GOLDEN_PROMPT_SHA256 = "297eabeffb4f0eec8c1ab5bc67f18627c563c72003151931317ce41a5ef0b1a1"


SAMPLE_RUBRIC = {
    "version": 1,
    "rubric_id": "test-sample",
    "items": [
        {"id": "r1", "description": "Compiles", "weight": 0.5},
        {"id": "r2", "description": "Tests pass", "weight": 0.5},
    ],
    "scoring": "weighted_average",
}


class TestGoldenPromptHash(TestEnvContext):
    """H5: golden prompt test — file content hash is pinned."""

    def test_committed_hash_matches(self):
        digest = bj.prompt_sha256()
        self.assertEqual(
            digest,
            GOLDEN_PROMPT_SHA256,
            "judge-prompt.md SHA-256 changed without updating the test; "
            "if this change is intentional, update GOLDEN_PROMPT_SHA256 "
            "and the ADR-030 hash line.",
        )

    def test_hash_is_64_hex_chars(self):
        digest = bj.prompt_sha256()
        self.assertEqual(len(digest), 64)
        int(digest, 16)  # Raises ValueError if not hex

    def test_custom_path_hash(self):
        tmp = Path(tempfile.mkdtemp(prefix="bj-hash-"))
        try:
            f = tmp / "fake-prompt.md"
            f.write_text("hello world", encoding="utf-8")
            expected = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(bj.prompt_sha256(f), expected)
        finally:
            import shutil
            shutil.rmtree(tmp)


class TestPayloadDefaultDeny(TestEnvContext):
    """H6: payload has exactly 3 top-level keys; extras raise."""

    def test_build_payload_has_exactly_three_keys(self):
        payload = bj.build_payload("task", SAMPLE_RUBRIC, "response text")
        self.assertEqual(
            set(payload.keys()),
            {"task_context", "rubric", "response"},
        )

    def test_extra_key_raises(self):
        bad = {
            "task_context": "x",
            "rubric": SAMPLE_RUBRIC,
            "response": "y",
            "leak": "secret",
        }
        with self.assertRaises(ValueError) as ctx:
            bj.validate_payload(bad)
        self.assertIn("default-deny", str(ctx.exception))

    def test_missing_key_raises(self):
        bad = {"task_context": "x", "rubric": SAMPLE_RUBRIC}
        with self.assertRaises(ValueError):
            bj.validate_payload(bad)

    def test_non_dict_payload_raises(self):
        with self.assertRaises(ValueError):
            bj.validate_payload(["task", SAMPLE_RUBRIC, "response"])

    def test_rubric_type_check(self):
        bad = {"task_context": "x", "rubric": "not-a-dict", "response": "y"}
        with self.assertRaises(ValueError):
            bj.validate_payload(bad)

    def test_reverse_marker_in_task_context(self):
        """Reverse pass carries the bit in task_context (no new key)."""
        payload = bj.build_payload("task", SAMPLE_RUBRIC, "response", reverse=True)
        self.assertEqual(
            set(payload.keys()),
            {"task_context", "rubric", "response"},
        )
        self.assertIn("REVERSE-PASS", payload["task_context"])


class TestRedactionBeforeSend(TestEnvContext):
    """Response strings are redacted before reaching the payload."""

    def test_api_key_redacted_in_response(self):
        secret_key = "sk-AbCdEfGhIjKlMnOpQrStUvWx0123456789"
        response = f"Here is the code with key {secret_key} embedded"
        payload = bj.build_payload("task", SAMPLE_RUBRIC, response)
        self.assertNotIn(secret_key, payload["response"])
        self.assertIn("[API_KEY]", payload["response"])

    def test_jwt_redacted(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJmb28iOiJiYXIifQ.abc123signaturepart"
        response = f"Token: {jwt}"
        payload = bj.build_payload("task", SAMPLE_RUBRIC, response)
        self.assertNotIn(jwt, payload["response"])

    def test_response_truncated_at_cap(self):
        # Response longer than RESPONSE_MAX_CHARS gets truncated
        long_resp = "x" * (bj.RESPONSE_MAX_CHARS + 500)
        payload = bj.build_payload("task", SAMPLE_RUBRIC, long_resp)
        self.assertLess(len(payload["response"]), bj.RESPONSE_MAX_CHARS + 100)
        self.assertIn("[truncated]", payload["response"])


class TestPromptRendering(TestEnvContext):
    """Prompt template substitutes placeholders; reverse swaps order."""

    def test_forward_pass_substitutes_placeholders(self):
        template = (
            "Task: <TASK_CONTEXT_REDACTED>\n"
            "## Rubric (authoritative)\n\n<RUBRIC_YAML>\n\n"
            "## Candidate response (redacted)\n\n<RESPONSE_REDACTED>\n"
        )
        payload = bj.build_payload("my task", SAMPLE_RUBRIC, "my response")
        rendered = bj.render_prompt(template, payload, reverse=False)
        self.assertIn("my task", rendered)
        self.assertIn("my response", rendered)
        self.assertNotIn("<TASK_CONTEXT_REDACTED>", rendered)
        self.assertNotIn("<RUBRIC_YAML>", rendered)
        # Forward: rubric appears before response
        self.assertLess(
            rendered.find("r1"),
            rendered.find("my response"),
        )

    def test_reverse_pass_swaps_order(self):
        template = (
            "Task: <TASK_CONTEXT_REDACTED>\n"
            "## Rubric (authoritative)\n\n<RUBRIC_YAML>\n\n"
            "## Candidate response (redacted)\n\n<RESPONSE_REDACTED>\n"
        )
        payload = bj.build_payload("my task", SAMPLE_RUBRIC, "my response", reverse=True)
        rendered = bj.render_prompt(template, payload, reverse=True)
        # Reverse: response appears before rubric
        self.assertLess(
            rendered.find("my response"),
            rendered.find("r1"),
        )


class TestMockJudgeDeterministic(TestEnvContext):
    """Mock judge returns the same grade for the same prompt."""

    def test_same_prompt_same_score(self):
        a = bj.mock_judge_call("some prompt", reverse=False)
        b = bj.mock_judge_call("some prompt", reverse=False)
        self.assertEqual(a, b)

    def test_forward_and_reverse_can_differ(self):
        """Mock intentionally shifts reverse by 1 to exercise delta tests."""
        fwd = bj.mock_judge_call("some prompt", reverse=False)
        rev = bj.mock_judge_call("some prompt", reverse=True)
        # Same base+1 or base-1 (edge-clamped)
        diff = abs(fwd["score"] - rev["score"])
        self.assertLessEqual(diff, 1)

    def test_mock_grade_schema(self):
        grade = bj.mock_judge_call("prompt")
        self.assertIn("score", grade)
        self.assertIn("reasoning", grade)
        self.assertIn("refused", grade)
        self.assertIn("flags", grade)
        self.assertIsInstance(grade["score"], int)
        self.assertIsInstance(grade["refused"], bool)
        self.assertIsInstance(grade["flags"], list)


class TestTwoPassGrading(TestEnvContext):
    """two_pass_grade returns forward + reverse + delta + review flag."""

    def _template(self):
        return bj.DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")

    def test_two_pass_returns_both_scores(self):
        grade = bj.two_pass_grade(
            task_context="t",
            rubric=SAMPLE_RUBRIC,
            response="some response",
            adapter_name="gemini",
            template_text=self._template(),
            mock=True,
        )
        self.assertIn("forward", grade)
        self.assertIn("reverse", grade)
        self.assertIn("delta", grade)
        self.assertIn("recommend_human_review", grade)
        self.assertIsInstance(grade["forward"]["score"], int)
        self.assertIsInstance(grade["reverse"]["score"], int)

    def test_large_delta_triggers_review(self):
        """Fake invoker that returns 10 forward, 2 reverse → delta 8 > 0.5."""
        def fake_invoke(adapter_name, prompt, *, reverse=False):
            return {
                "score": 2 if reverse else 10,
                "reasoning": "",
                "refused": False,
                "flags": [],
            }
        grade = bj.two_pass_grade(
            task_context="t",
            rubric=SAMPLE_RUBRIC,
            response="r",
            adapter_name="gemini",
            template_text=self._template(),
            mock=False,
            _inject_invoker=fake_invoke,
        )
        self.assertEqual(grade["delta"], 8.0)
        self.assertTrue(grade["recommend_human_review"])

    def test_small_delta_no_review(self):
        def fake_invoke(adapter_name, prompt, *, reverse=False):
            return {
                "score": 7 if reverse else 7,
                "reasoning": "",
                "refused": False,
                "flags": [],
            }
        grade = bj.two_pass_grade(
            task_context="t",
            rubric=SAMPLE_RUBRIC,
            response="r",
            adapter_name="gemini",
            template_text=self._template(),
            mock=False,
            _inject_invoker=fake_invoke,
        )
        self.assertEqual(grade["delta"], 0.0)
        self.assertFalse(grade["recommend_human_review"])


class TestCrossProviderGuard(TestEnvContext):
    """Judge adapter MUST differ from main adapter."""

    def test_same_adapter_raises(self):
        with self.assertRaises(bj.CrossProviderCollision):
            bj.assert_cross_provider("gemini", "gemini")

    def test_same_adapter_case_insensitive(self):
        with self.assertRaises(bj.CrossProviderCollision):
            bj.assert_cross_provider("GEMINI", "gemini")

    def test_different_adapter_passes(self):
        # Should not raise
        bj.assert_cross_provider("gemini", "claude")
        bj.assert_cross_provider("openai", "claude")

    def test_empty_main_passes(self):
        # Allow when main adapter unset (stand-alone judge invocation)
        bj.assert_cross_provider("gemini", None)
        bj.assert_cross_provider("openai", "")


class TestRubricLoader(TestEnvContext):
    """Rubric JSON loader validates structure."""

    def _write_rubric(self, data) -> Path:
        f = self.project_dir / "rubric.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    def test_valid_rubric_loads(self):
        f = self._write_rubric(SAMPLE_RUBRIC)
        loaded = bj.load_rubric(f)
        self.assertEqual(loaded["rubric_id"], "test-sample")

    def test_missing_items_raises(self):
        f = self._write_rubric({"version": 1, "rubric_id": "x", "scoring": "weighted_average"})
        with self.assertRaises(ValueError):
            bj.load_rubric(f)

    def test_empty_items_raises(self):
        f = self._write_rubric({
            "version": 1,
            "rubric_id": "x",
            "items": [],
            "scoring": "weighted_average",
        })
        with self.assertRaises(ValueError):
            bj.load_rubric(f)

    def test_unknown_scoring_raises(self):
        f = self._write_rubric({
            "version": 1,
            "rubric_id": "x",
            "items": [{"id": "i", "description": "d", "weight": 1.0}],
            "scoring": "invalid",
        })
        with self.assertRaises(ValueError):
            bj.load_rubric(f)

    def test_missing_file_raises(self):
        with self.assertRaises(ValueError):
            bj.load_rubric(Path(self.project_dir) / "nope.json")


class TestCliHappyPath(TestEnvContext):
    """End-to-end CLI with mock judge."""

    def _setup_files(self):
        rubric = self.project_dir / "rubric.json"
        rubric.write_text(json.dumps(SAMPLE_RUBRIC), encoding="utf-8")
        response = self.project_dir / "response.txt"
        response.write_text("some response text", encoding="utf-8")
        return rubric, response

    def test_cli_mock_happy_path(self):
        rubric, response = self._setup_files()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bj.main([
                "--benchmark", "test-skill",
                "--response-file", str(response),
                "--rubric-file", str(rubric),
                "--judge-adapter", "gemini",
                "--mock-judge",
                "--task-context", "describe the task",
            ])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["benchmark"], "test-skill")
        self.assertEqual(out["judge_adapter"], "gemini")
        self.assertEqual(out["golden_prompt_hash"], GOLDEN_PROMPT_SHA256)
        self.assertIn("forward", out)
        self.assertIn("reverse", out)
        self.assertIn("delta", out)

    def test_cli_cross_provider_exits_3(self):
        rubric, response = self._setup_files()
        os.environ["CEO_HOOK_ADAPTER"] = "gemini"
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = bj.main([
                "--benchmark", "test",
                "--response-file", str(response),
                "--rubric-file", str(rubric),
                "--judge-adapter", "gemini",
                "--mock-judge",
            ])
        self.assertEqual(rc, 3)
        self.assertIn("differ", buf.getvalue())

    def test_cli_missing_response_file_exits_2(self):
        rubric, _ = self._setup_files()
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = bj.main([
                "--benchmark", "test",
                "--response-file", str(self.project_dir / "nope.txt"),
                "--rubric-file", str(rubric),
                "--judge-adapter", "gemini",
                "--mock-judge",
            ])
        self.assertEqual(rc, 2)

    def test_cli_missing_rubric_file_exits_2(self):
        _, response = self._setup_files()
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = bj.main([
                "--benchmark", "test",
                "--response-file", str(response),
                "--rubric-file", str(self.project_dir / "nope.json"),
                "--judge-adapter", "gemini",
                "--mock-judge",
            ])
        self.assertEqual(rc, 2)

    def test_cli_unreachable_real_judge_exits_4(self):
        """Without --mock-judge and no real SDK wired → exit 4."""
        rubric, response = self._setup_files()
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = bj.main([
                "--benchmark", "test",
                "--response-file", str(response),
                "--rubric-file", str(rubric),
                "--judge-adapter", "gemini",
            ])
        self.assertEqual(rc, 4)
        self.assertIn("unreachable", buf.getvalue().lower())

    def test_cli_sota_disable_skips(self):
        rubric, response = self._setup_files()
        os.environ["CEO_SOTA_DISABLE"] = "1"
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bj.main([
                "--benchmark", "test",
                "--response-file", str(response),
                "--rubric-file", str(rubric),
                "--judge-adapter", "gemini",
                "--mock-judge",
            ])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertTrue(out.get("skipped"))


class TestJudgeUnreachableFallsThrough(TestEnvContext):
    """JudgeUnreachable is the sentinel for §H7 fallback wiring."""

    def test_invoke_adapter_without_mock_raises(self):
        with self.assertRaises(bj.JudgeUnreachable):
            bj.invoke_adapter("gemini", "prompt", mock=False)

    def test_injected_invoker_used(self):
        def fake(adapter_name, prompt, *, reverse=False):
            return {
                "score": 9,
                "reasoning": "inj",
                "refused": False,
                "flags": [],
            }
        out = bj.invoke_adapter("gemini", "p", mock=False, _inject_invoker=fake)
        self.assertEqual(out["score"], 9)


class TestStructuredOutputsOptIn(TestEnvContext):
    """PLAN-136 SO1 — opt-in structured outputs (CEO_STRUCTURED_OUTPUTS).

    Default (env unset): build_grade_response_format() returns None, the
    real-judge call omits response_format, and existing injectors keep their
    original signature (legacy path preserved byte-for-byte).

    Opt-in (env=1): the strict json_schema grade payload is built and threaded
    through invoke_adapter -> the injected invoker (the real adapter's
    call(response_format=...) pass-through).
    """

    def test_env_unset_returns_none(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_STRUCTURED_OUTPUTS", None)
            self.assertFalse(bj.structured_outputs_enabled())
            self.assertIsNone(bj.build_grade_response_format())

    def test_env_set_builds_strict_json_schema(self):
        with mock.patch.dict(os.environ, {"CEO_STRUCTURED_OUTPUTS": "1"}):
            self.assertTrue(bj.structured_outputs_enabled())
            rf = bj.build_grade_response_format()
        self.assertEqual(rf["type"], "json_schema")
        self.assertEqual(rf["json_schema"]["name"], "grade")
        self.assertTrue(rf["json_schema"]["strict"])
        schema = rf["json_schema"]["schema"]
        # Strict-mode invariant: additionalProperties:false on the object.
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            set(schema["required"]), {"score", "reasoning", "refused", "flags"}
        )

    def test_env_other_value_is_off(self):
        # Only the literal "1" enables it; "0"/"true"/"" stay default-OFF.
        for val in ("0", "true", "yes", ""):
            with mock.patch.dict(os.environ, {"CEO_STRUCTURED_OUTPUTS": val}):
                self.assertFalse(bj.structured_outputs_enabled())
                self.assertIsNone(bj.build_grade_response_format())

    def test_default_path_injector_called_without_response_format(self):
        # Env unset → injector keyword set must NOT include response_format,
        # so a legacy injector (no response_format kwarg) keeps working.
        seen = {}

        def fake(adapter_name, prompt, *, reverse=False):
            seen["called"] = True
            return {"score": 7, "reasoning": "x", "refused": False, "flags": []}

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_STRUCTURED_OUTPUTS", None)
            out = bj.two_pass_grade(
                task_context="ctx",
                rubric={"r": 1},
                response="resp",
                adapter_name="gemini",
                template_text="<TASK_CONTEXT_REDACTED> <RUBRIC_YAML> <RESPONSE_REDACTED>",
                mock=False,
                _inject_invoker=fake,
            )
        self.assertTrue(seen.get("called"))
        self.assertIn("forward", out)
        self.assertIn("reverse", out)

    def test_optin_path_threads_response_format_to_injector(self):
        # Env=1 → the injector receives the strict json_schema payload (the
        # value the real adapter forwards to call(response_format=...)).
        captured = []

        def fake(adapter_name, prompt, *, reverse=False, response_format=None):
            captured.append(response_format)
            return {"score": 8, "reasoning": "y", "refused": False, "flags": []}

        with mock.patch.dict(os.environ, {"CEO_STRUCTURED_OUTPUTS": "1"}):
            bj.two_pass_grade(
                task_context="ctx",
                rubric={"r": 1},
                response="resp",
                adapter_name="gemini",
                template_text="<TASK_CONTEXT_REDACTED> <RUBRIC_YAML> <RESPONSE_REDACTED>",
                mock=False,
                _inject_invoker=fake,
            )
        # Both forward and reverse passes carry the payload.
        self.assertEqual(len(captured), 2)
        for rf in captured:
            self.assertIsNotNone(rf)
            self.assertEqual(rf["json_schema"]["name"], "grade")
            self.assertTrue(rf["json_schema"]["strict"])


if __name__ == "__main__":
    unittest.main()
