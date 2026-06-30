"""Unit tests for _lib/adapters/live/__init__.py — live LLM invokers.

Uses a stdlib ``http.server`` mock receiver (same pattern as Phase 8
otel-smoke) to exercise the invoker code without hitting real providers.
Every test asserts ≥1 behavior beyond exit code (consensus S5).
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib.adapters import live  # noqa: E402
from _lib.adapters.live import (  # noqa: E402
    LiveAdapterAuthError,
    LiveAdapterError,
    LiveAdapterHTTPError,
    LiveAdapterParseError,
    LiveAdapterTimeoutError,
    LiveAdaptersDisabled,
    invoke,
)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _MockHandler(BaseHTTPRequestHandler):
    """Reflect request body + replies with canned JSON per path."""

    # Class-level configuration set by tests before start
    response_json = None
    response_status = 200
    record = None  # {"method","path","headers","body"}
    delay_seconds = 0.0

    def log_message(self, format, *args):  # noqa: N802 — suppress stdout
        return

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        _MockHandler.record = {
            "method": "POST",
            "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
            "body": raw,
        }
        if _MockHandler.delay_seconds:
            import time
            time.sleep(_MockHandler.delay_seconds)
        self.send_response(_MockHandler.response_status)
        self.send_header("Content-Type", "application/json")
        payload = json.dumps(_MockHandler.response_json or {}).encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class _MockServer:
    def __init__(self):
        self.port = _free_port()
        self.srv = HTTPServer(("127.0.0.1", self.port), _MockHandler)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


class _LiveAdapterCase(TestEnvContext):
    """Base: spin up a mock server + set CEO_LIVE_ADAPTERS=1 + timeout 2s."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_LIVE_ADAPTERS"] = "1"
        os.environ["CEO_LIVE_TIMEOUT"] = "2.0"
        self.server = _MockServer()
        self.server.start()
        _MockHandler.response_status = 200
        _MockHandler.response_json = {}
        _MockHandler.record = None
        _MockHandler.delay_seconds = 0.0

    def tearDown(self) -> None:
        self.server.stop()
        super().tearDown()


class TestFeatureGate(TestEnvContext):

    def test_disabled_by_default_raises(self):
        if "CEO_LIVE_ADAPTERS" in os.environ:
            del os.environ["CEO_LIVE_ADAPTERS"]
        with self.assertRaises(LiveAdaptersDisabled):
            invoke([{"role": "user", "content": "hi"}])

    def test_enabled_requires_literal_1(self):
        os.environ["CEO_LIVE_ADAPTERS"] = "true"  # not "1"
        with self.assertRaises(LiveAdaptersDisabled):
            invoke([{"role": "user", "content": "hi"}])


class TestAuth(_LiveAdapterCase):

    def test_anthropic_missing_key_raises_auth(self):
        for k in ("ANTHROPIC_API_KEY",):
            os.environ.pop(k, None)
        with self.assertRaises(LiveAdapterAuthError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )

    def test_openai_missing_key_raises_auth(self):
        os.environ.pop("OPENAI_API_KEY", None)
        with self.assertRaises(LiveAdapterAuthError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="openai",
                endpoint=self.server.url,
            )

    def test_gemini_missing_key_raises_auth(self):
        os.environ.pop("GEMINI_API_KEY", None)
        with self.assertRaises(LiveAdapterAuthError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="gemini",
                endpoint=self.server.url + "/v1beta/models/{model}:generateContent",
            )

    def test_local_does_not_require_key(self):
        # Local Ollama has no API key
        _MockHandler.response_json = {
            "message": {"role": "assistant", "content": "hi"},
            "done": True, "model": "llama3",
        }
        res = invoke(
            [{"role": "user", "content": "x"}],
            provider="local",
            endpoint=self.server.url,
        )
        self.assertEqual(res["content"], "hi")


class TestAnthropic(_LiveAdapterCase):

    def setUp(self) -> None:
        super().setUp()
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-anthropic"

    def test_round_trip_normalizes_envelope(self):
        _MockHandler.response_json = {
            "model": "claude-sonnet-4-6",
            "content": [{"type": "text", "text": "hello from claude"}],
            "usage": {"input_tokens": 11, "output_tokens": 3},
            "stop_reason": "end_turn",
        }
        res = invoke(
            [{"role": "user", "content": "hi"}],
            provider="anthropic",
            endpoint=self.server.url,
        )
        self.assertEqual(res["content"], "hello from claude")
        self.assertEqual(res["tokens_in"], 11)
        self.assertEqual(res["tokens_out"], 3)
        self.assertEqual(res["provider"], "anthropic")
        self.assertEqual(res["stop_reason"], "end_turn")

    def test_api_key_sent_as_x_api_key_header(self):
        _MockHandler.response_json = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        invoke(
            [{"role": "user", "content": "hi"}],
            provider="anthropic",
            endpoint=self.server.url,
        )
        rec = _MockHandler.record
        self.assertIn("x-api-key", {k.lower() for k in rec["headers"]})
        # Case-insensitive header retrieval
        key_header = next(v for k, v in rec["headers"].items() if k.lower() == "x-api-key")
        self.assertEqual(key_header, "sk-test-anthropic")

    def test_system_message_sent_separately(self):
        _MockHandler.response_json = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        invoke(
            [{"role": "user", "content": "hi"}],
            provider="anthropic",
            endpoint=self.server.url,
            system="you are helpful",
            max_tokens=50,
        )
        body = json.loads(_MockHandler.record["body"])
        self.assertEqual(body["system"], "you are helpful")
        self.assertEqual(body["max_tokens"], 50)


class TestOpenAI(_LiveAdapterCase):

    def setUp(self) -> None:
        super().setUp()
        os.environ["OPENAI_API_KEY"] = "sk-test-openai"

    def test_round_trip_extracts_first_choice(self):
        _MockHandler.response_json = {
            "model": "gpt-4o",
            "choices": [{"message": {"content": "hi there"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        }
        res = invoke(
            [{"role": "user", "content": "hi"}],
            provider="openai",
            endpoint=self.server.url,
        )
        self.assertEqual(res["content"], "hi there")
        self.assertEqual(res["tokens_in"], 5)
        self.assertEqual(res["tokens_out"], 2)
        self.assertEqual(res["stop_reason"], "stop")

    def test_bearer_auth_used(self):
        _MockHandler.response_json = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        invoke(
            [{"role": "user", "content": "hi"}],
            provider="openai",
            endpoint=self.server.url,
        )
        rec = _MockHandler.record
        auth = next(v for k, v in rec["headers"].items() if k.lower() == "authorization")
        self.assertTrue(auth.startswith("Bearer "))
        self.assertIn("sk-test-openai", auth)


class TestGemini(_LiveAdapterCase):

    def setUp(self) -> None:
        super().setUp()
        os.environ["GEMINI_API_KEY"] = "gemini-test-key"

    def test_round_trip_extracts_candidate_text(self):
        _MockHandler.response_json = {
            "candidates": [{
                "content": {"parts": [{"text": "from gemini"}]},
                "finishReason": "STOP",
            }],
            "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 4},
        }
        res = invoke(
            [{"role": "user", "content": "hi"}],
            provider="gemini",
            endpoint=self.server.url + "/v1beta/models/{model}:generateContent",
            model="gemini-2.5-flash",
        )
        self.assertEqual(res["content"], "from gemini")
        self.assertEqual(res["tokens_in"], 7)
        self.assertEqual(res["tokens_out"], 4)
        self.assertEqual(res["stop_reason"], "STOP")

    def test_system_becomes_system_instruction(self):
        _MockHandler.response_json = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
        }
        invoke(
            [
                {"role": "system", "content": "you are helpful"},
                {"role": "user", "content": "hi"},
            ],
            provider="gemini",
            endpoint=self.server.url + "/v1beta/models/{model}:generateContent",
            model="gemini-2.5-flash",
        )
        body = json.loads(_MockHandler.record["body"])
        self.assertIn("system_instruction", body)
        self.assertEqual(body["system_instruction"]["parts"][0]["text"], "you are helpful")
        # System MUST NOT also appear in contents
        for content in body["contents"]:
            self.assertNotEqual(content.get("role"), "system")


class TestLocal(_LiveAdapterCase):

    def test_ollama_round_trip(self):
        _MockHandler.response_json = {
            "model": "llama3",
            "message": {"role": "assistant", "content": "local says hi"},
            "done": True,
            "prompt_eval_count": 12,
            "eval_count": 3,
        }
        res = invoke(
            [{"role": "user", "content": "hi"}],
            provider="local",
            endpoint=self.server.url,
        )
        self.assertEqual(res["content"], "local says hi")
        self.assertEqual(res["tokens_in"], 12)
        self.assertEqual(res["tokens_out"], 3)
        self.assertEqual(res["stop_reason"], "stop")

    def test_options_passed_as_ollama_options(self):
        _MockHandler.response_json = {
            "message": {"content": "ok"},
            "done": True,
        }
        invoke(
            [{"role": "user", "content": "hi"}],
            provider="local",
            endpoint=self.server.url,
            temperature=0.2,
            max_tokens=256,
        )
        body = json.loads(_MockHandler.record["body"])
        self.assertEqual(body["options"]["temperature"], 0.2)
        self.assertEqual(body["options"]["num_predict"], 256)
        self.assertFalse(body["stream"])


class TestErrorPaths(_LiveAdapterCase):

    def setUp(self) -> None:
        super().setUp()
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"

    def test_http_500_raises_httperror(self):
        _MockHandler.response_status = 500
        _MockHandler.response_json = {"error": "boom"}
        with self.assertRaises(LiveAdapterHTTPError) as ctx:
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )
        self.assertEqual(ctx.exception.status, 500)

    def test_http_401_raises_autherror(self):
        _MockHandler.response_status = 401
        _MockHandler.response_json = {"error": "bad key"}
        with self.assertRaises(LiveAdapterAuthError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )

    def test_malformed_json_raises_parseerror(self):
        class Broken(BaseHTTPRequestHandler):
            def log_message(self, *a): return
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                body = b"not json at all"
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        self.server.stop()
        self.server.srv = HTTPServer(("127.0.0.1", self.server.port), Broken)
        self.server.thread = threading.Thread(target=self.server.srv.serve_forever, daemon=True)
        self.server.start()
        with self.assertRaises(LiveAdapterParseError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )

    def test_timeout_raises_timeouterror(self):
        os.environ["CEO_LIVE_TIMEOUT"] = "0.5"
        _MockHandler.delay_seconds = 1.5
        _MockHandler.response_json = {
            "content": [{"type": "text", "text": "late"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        with self.assertRaises(LiveAdapterTimeoutError):
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )

    def test_unknown_provider_raises(self):
        with self.assertRaises(LiveAdapterError):
            invoke([{"role": "user", "content": "x"}], provider="does-not-exist")


class TestCredentialHygiene(_LiveAdapterCase):
    """Consensus H8: keys NEVER in result envelope, NEVER in exception messages beyond a generic flag."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-SUPERSECRET-12345"
        os.environ["OPENAI_API_KEY"] = "sk-openai-SUPERSECRET-67890"

    def test_result_envelope_does_not_contain_key(self):
        _MockHandler.response_json = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        res = invoke(
            [{"role": "user", "content": "hi"}],
            provider="anthropic",
            endpoint=self.server.url,
        )
        serialized = json.dumps(res)
        self.assertNotIn("SUPERSECRET", serialized)

    def test_http_error_message_does_not_echo_key(self):
        _MockHandler.response_status = 500
        _MockHandler.response_json = {"error": "upstream failure"}
        try:
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )
            self.fail("expected HTTPError")
        except LiveAdapterHTTPError as e:
            self.assertNotIn("SUPERSECRET", str(e))

    def test_missing_key_error_does_not_echo_stale_value(self):
        # Delete then attempt → message should NOT include any prior value
        os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            invoke(
                [{"role": "user", "content": "x"}],
                provider="anthropic",
                endpoint=self.server.url,
            )
            self.fail("expected AuthError")
        except LiveAdapterAuthError as e:
            self.assertNotIn("SUPERSECRET", str(e))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
