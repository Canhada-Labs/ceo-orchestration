"""Behavior tests for the four ADR-040 live adapters.

Uses a stdlib ``http.server`` mock server (same pattern as
``test_live_adapters.py``) so we can drive every adapter through the
same wire surface without real credentials. Activation env vars are
set per test; the tests assert:

- fixture-fallback path returns a typed result without any network I/O
- HTTPError 500 → failed Result (never an exception)
- credential never appears in audit JSON
- ``provider_name`` correct
- :class:`LiveAdapterResult` is frozen / immutable
- breaker opens after threshold transient failures
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import unittest
from dataclasses import FrozenInstanceError
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

_HOOKS_DIR = Path(__file__).resolve().parents[3]

from _lib.adapters.live import (  # noqa: E402
    BreakerState,
    ClaudeLiveAdapter,
    GeminiLiveAdapter,
    LiveAdapterResult,
    LiveTransport,
    LocalLiveAdapter,
    OpenAILiveAdapter,
)
from _lib.adapters.live._policy import (  # noqa: E402
    ClaudeLivePolicy,
    GeminiLivePolicy,
    LocalLivePolicy,
    OpenAILivePolicy,
)
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Mock server (per-test scriptable response)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(BaseHTTPRequestHandler):
    response_status: int = 200
    response_body: bytes = b"{}"
    captured: Dict[str, Any] = {}

    def log_message(self, format, *args):  # noqa: N802 - silence
        return

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        _Handler.captured = {
            "path": self.path,
            "headers": {k: v for k, v in self.headers.items()},
            "body": raw.decode("utf-8", errors="replace"),
        }
        self.send_response(_Handler.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_Handler.response_body)))
        self.end_headers()
        self.wfile.write(_Handler.response_body)


class _MockServer:
    def __init__(self) -> None:
        self.port = _free_port()
        self.srv = HTTPServer(("127.0.0.1", self.port), _Handler)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


class _AdapterCase(TestEnvContext):
    """Shared setup: spin up a mock server + tight policy."""

    def setUp(self) -> None:
        super().setUp()
        self.server = _MockServer()
        self.server.start()
        _Handler.response_status = 200
        _Handler.response_body = b"{}"
        _Handler.captured = {}

    def tearDown(self) -> None:
        self.server.stop()
        super().tearDown()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.port}"


# ---------------------------------------------------------------------------
# Fixture fallback path (activation gate off)
# ---------------------------------------------------------------------------


class TestFixtureFallback(TestEnvContext):
    def test_claude_falls_back_when_activation_off(self):
        # CEO_LIVE_CLAUDE not set
        a = ClaudeLiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5")
        self.assertTrue(r.success)
        self.assertTrue(r.fixture_fallback)
        self.assertEqual(r.provider, "anthropic")

    def test_gemini_falls_back_when_activation_off(self):
        a = GeminiLiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="gemini-2.5-flash")
        self.assertTrue(r.success)
        self.assertTrue(r.fixture_fallback)
        self.assertEqual(r.provider, "google")

    def test_openai_falls_back_when_activation_off(self):
        a = OpenAILiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="gpt-4o")
        self.assertTrue(r.success)
        self.assertTrue(r.fixture_fallback)

    def test_local_falls_back_when_activation_off(self):
        a = LocalLiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="llama3")
        self.assertTrue(r.success)
        self.assertTrue(r.fixture_fallback)
        self.assertEqual(r.cost_usd, 0.0)

    def test_credential_missing_emits_failure_mode(self):
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        # ANTHROPIC_API_KEY intentionally absent
        os.environ.pop("ANTHROPIC_API_KEY", None)
        a = ClaudeLiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "missing_credential")
        self.assertTrue(r.fixture_fallback)

    def test_sota_disable_short_circuits_every_provider(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
        a = ClaudeLiveAdapter()
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertTrue(r.success)
        self.assertTrue(r.fixture_fallback)


# ---------------------------------------------------------------------------
# Provider names
# ---------------------------------------------------------------------------


class TestProviderNames(unittest.TestCase):
    def test_claude_provider_name(self):
        self.assertEqual(ClaudeLiveAdapter().provider_name, "anthropic")

    def test_gemini_provider_name(self):
        self.assertEqual(GeminiLiveAdapter().provider_name, "google")

    def test_openai_provider_name(self):
        self.assertEqual(OpenAILiveAdapter().provider_name, "openai")

    def test_local_provider_name(self):
        self.assertEqual(LocalLiveAdapter().provider_name, "local")


# ---------------------------------------------------------------------------
# Result immutability
# ---------------------------------------------------------------------------


class TestResultImmutability(unittest.TestCase):
    def test_result_is_frozen(self):
        r = LiveAdapterResult(success=True, provider="anthropic")
        with self.assertRaises(FrozenInstanceError):
            r.success = False  # type: ignore[misc]

    def test_default_failure_mode_is_none(self):
        r = LiveAdapterResult(success=True)
        self.assertIsNone(r.failure_mode)

    def test_is_retryable_only_for_transient(self):
        self.assertTrue(
            LiveAdapterResult(success=False, failure_mode="server_error").is_retryable()
        )
        self.assertTrue(
            LiveAdapterResult(success=False, failure_mode="rate_limited").is_retryable()
        )
        self.assertTrue(
            LiveAdapterResult(success=False, failure_mode="connect_timeout").is_retryable()
        )
        self.assertFalse(
            LiveAdapterResult(success=False, failure_mode="auth_permanent").is_retryable()
        )
        self.assertFalse(
            LiveAdapterResult(success=False, failure_mode="parse_error").is_retryable()
        )
        self.assertFalse(LiveAdapterResult(success=True).is_retryable())


# ---------------------------------------------------------------------------
# Live invocation (mocked) — happy + sad paths
# ---------------------------------------------------------------------------


class TestClaudeLive(_AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-test-key-not-real"
        # PLAN-085 Wave C.1 — live_adapter_allowlist runtime gate requires
        # settings.json present with the key. Without this fixture, the
        # adapter fail-CLOSEs at activation. Write isolated settings.json
        # under TestEnvContext.project_dir so the gate passes.
        import json as _json
        settings = self.project_dir / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_happy_path_returns_text_and_tokens(self):
        _Handler.response_status = 200
        _Handler.response_body = json.dumps({
            "content": [{"type": "text", "text": "hello back"}],
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "model": "claude-haiku-4-5",
        }).encode("utf-8")
        a = ClaudeLiveAdapter(url=self.base_url + "/v1/messages")
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5")
        self.assertTrue(r.success)
        self.assertEqual(r.text, "hello back")
        self.assertEqual(r.tokens_in, 5)
        self.assertEqual(r.tokens_out, 3)
        self.assertEqual(r.provider, "anthropic")
        self.assertGreater(r.cost_usd or 0, 0)
        self.assertEqual(r.http_status, 200)

    def test_500_returns_failed_result_not_exception(self):
        _Handler.response_status = 500
        _Handler.response_body = b'{"error":"boom"}'
        # Use policy with retries=0 so this is one shot
        from dataclasses import replace
        pol = replace(ClaudeLivePolicy(), max_retries=0)
        a = ClaudeLiveAdapter(policy=pol, url=self.base_url + "/v1/messages")
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "server_error")
        self.assertEqual(r.http_status, 500)
        self.assertIsNone(r.text)

    def test_401_classified_as_auth_permanent(self):
        _Handler.response_status = 401
        _Handler.response_body = b'{"error":"unauthorized"}'
        a = ClaudeLiveAdapter(url=self.base_url + "/v1/messages")
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "auth_permanent")
        self.assertEqual(a._breaker.state, BreakerState.OPEN)

    def test_credential_never_in_response_dict(self):
        # Explicitly check the audit-safe path: result has no key field.
        _Handler.response_status = 200
        _Handler.response_body = b'{"content":[{"type":"text","text":"ok"}],"usage":{}}'
        a = ClaudeLiveAdapter(url=self.base_url + "/v1/messages")
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5")
        # Result is a frozen dataclass — credentials never make it in
        for v in vars(r).values():
            if isinstance(v, str):
                self.assertNotIn("sk-ant-fake-test-key-not-real", v)

    def test_audit_payload_redacts_x_api_key(self):
        # Capture audit events by injecting a recorder into the transport.
        events: List[Dict[str, Any]] = []
        def recorder(action, fields):
            events.append({"action": action, "fields": fields})
        pol = ClaudeLivePolicy()
        transport = LiveTransport(pol, on_audit=recorder)
        _Handler.response_status = 200
        _Handler.response_body = b'{"content":[],"usage":{}}'
        a = ClaudeLiveAdapter(transport=transport, url=self.base_url + "/v1/messages")
        a.call(messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5")
        full_dump = json.dumps(events, default=str)
        self.assertNotIn("sk-ant-fake-test-key-not-real", full_dump)
        # Audit must have at least started + succeeded
        actions = [e["action"] for e in events]
        self.assertIn("live_adapter_call_started", actions)
        self.assertIn("live_adapter_call_succeeded", actions)


class TestOpenAILive(_AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_OPENAI"] = "1"
        os.environ["OPENAI_API_KEY"] = "sk-proj-fake-openai-test-token"

    def test_happy_chat_path(self):
        _Handler.response_status = 200
        _Handler.response_body = json.dumps({
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            "model": "gpt-4o",
        }).encode("utf-8")
        a = OpenAILiveAdapter(chat_url=self.base_url + "/v1/chat/completions")
        r = a.call(messages=[{"role": "user", "content": "hello"}], model="gpt-4o")
        self.assertTrue(r.success)
        self.assertEqual(r.text, "hi")
        self.assertEqual(r.tokens_in, 3)
        self.assertEqual(r.tokens_out, 1)
        self.assertEqual(r.provider, "openai")

    def test_opt_out_header_sent(self):
        _Handler.response_status = 200
        _Handler.response_body = b'{"choices":[{"message":{"content":""}}],"usage":{}}'
        a = OpenAILiveAdapter(chat_url=self.base_url + "/v1/chat/completions")
        a.call(messages=[{"role": "user", "content": "x"}], model="gpt-4o")
        captured_headers = _Handler.captured.get("headers", {})
        # http.server lowercases header names — check both
        keys_lower = {k.lower() for k in captured_headers}
        self.assertIn("openai-data-retention", keys_lower)

    def test_credential_never_in_result(self):
        _Handler.response_status = 200
        _Handler.response_body = b'{"choices":[{"message":{"content":""}}],"usage":{}}'
        a = OpenAILiveAdapter(chat_url=self.base_url + "/v1/chat/completions")
        r = a.call(messages=[{"role": "user", "content": "x"}], model="gpt-4o")
        for v in vars(r).values():
            if isinstance(v, str):
                self.assertNotIn("sk-proj-fake-openai-test-token", v)


class TestGeminiLive(_AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_GEMINI"] = "1"
        os.environ["GOOGLE_API_KEY"] = "AIza-FAKE-google-test-key-12345-67890-abc"

    def test_happy_path(self):
        _Handler.response_status = 200
        _Handler.response_body = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "ola"}]},
                "finishReason": "STOP",
            }],
            "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 1},
        }).encode("utf-8")
        a = GeminiLiveAdapter(base_url=self.base_url + "/v1beta/models/{model}:generateContent")
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="gemini-2.5-flash")
        self.assertTrue(r.success)
        self.assertEqual(r.text, "ola")
        self.assertEqual(r.tokens_in, 2)
        self.assertEqual(r.tokens_out, 1)

    def test_audit_does_not_carry_url_query_key(self):
        events: List[Dict[str, Any]] = []
        def recorder(action, fields):
            events.append({"action": action, "fields": fields})
        pol = GeminiLivePolicy()
        transport = LiveTransport(pol, on_audit=recorder)
        _Handler.response_status = 200
        _Handler.response_body = json.dumps({
            "candidates": [{"content": {"parts": [{"text": ""}]}}],
            "usageMetadata": {},
        }).encode("utf-8")
        a = GeminiLiveAdapter(
            transport=transport,
            base_url=self.base_url + "/v1beta/models/{model}:generateContent",
        )
        a.call(messages=[{"role": "user", "content": "x"}], model="gemini-2.5-flash")
        dump = json.dumps(events, default=str)
        # The fake key MUST NOT appear in the audit dump (URL was scrubbed)
        self.assertNotIn("AIza-FAKE-google-test-key-12345-67890-abc", dump)


class TestLocalLive(_AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_LOCAL"] = "1"

    def test_happy_path_zero_cost(self):
        _Handler.response_status = 200
        _Handler.response_body = json.dumps({
            "message": {"content": "local says hi"},
            "prompt_eval_count": 4,
            "eval_count": 5,
            "done": True,
        }).encode("utf-8")
        a = LocalLiveAdapter(url=self.base_url + "/api/chat")
        r = a.call(messages=[{"role": "user", "content": "hi"}], model="llama3")
        self.assertTrue(r.success)
        self.assertEqual(r.text, "local says hi")
        self.assertEqual(r.cost_usd, 0.0)
        self.assertEqual(r.provider, "local")


# ---------------------------------------------------------------------------
# Breaker integration through adapter
# ---------------------------------------------------------------------------


class TestBreakerOpensAfterTransientFailures(_AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
        # PLAN-085 Wave C.1 — live_adapter_allowlist gate fixture.
        import json as _json
        settings = self.project_dir / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_5_consecutive_500s_open_breaker(self):
        from dataclasses import replace
        _Handler.response_status = 500
        _Handler.response_body = b'{}'
        # Disable retries so each call counts as exactly one failure.
        pol = replace(ClaudeLivePolicy(), max_retries=0)
        a = ClaudeLiveAdapter(policy=pol, url=self.base_url + "/v1/messages")
        for _ in range(5):
            a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        # 6th call should hit the open breaker
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "breaker_open")


# ---------------------------------------------------------------------------
# Result contract sanity
# ---------------------------------------------------------------------------


class TestCallNeverRaises(_AdapterCase):
    """Per ADR-040: adapters MUST NEVER raise for network conditions."""

    def setUp(self):
        super().setUp()
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
        # PLAN-085 Wave C.1 — live_adapter_allowlist gate fixture.
        import json as _json
        settings = self.project_dir / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            _json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

    def test_garbage_response_does_not_raise(self):
        _Handler.response_status = 200
        _Handler.response_body = b"this is not JSON {{{{{{"
        a = ClaudeLiveAdapter(url=self.base_url + "/v1/messages")
        # Should NOT raise; should return parse_error result
        r = a.call(messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5")
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "parse_error")


if __name__ == "__main__":
    unittest.main()
