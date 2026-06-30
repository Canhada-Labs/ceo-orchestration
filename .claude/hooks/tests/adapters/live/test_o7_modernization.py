"""PLAN-135 W5 O7 — live-adapter modernization regression tests.

Covers the five O7 items implemented in the Claude live adapter:

  (1) stop_reason / stop_details parsing — refusal != completion
      (LiveAdapterResult.is_complete() / is_refusal()) + the closed-enum
      ``model_refusal_observed`` audit breadcrumb.
  (3) automatic top-level cache_control:{"type":"ephemeral"} (default ON;
      kill switch CEO_CACHE_CONTROL_AUTO_DISABLE=1).
  (4) count_tokens() preflight — measured ceiling under
      CEO_COUNT_TOKENS_PREFLIGHT=1 (the endpoint bills zero tokens).
  (5) request_id capture on the HTTP-error path.

Same harness conventions as ``test_adapters.py``: a stdlib ``http.server``
mock server (no real credentials, no network), activation env set per
test, :class:`LiveAdapterResult` asserted frozen, credential never echoed.

Selector compatibility (PLAN-135 W5 Check line):
``pytest -k "live_adapter or stop_reason or output_config"`` matches every
test class/method here — each name embeds ``live_adapter``, ``stop_reason``,
or ``output_config``.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import unittest
from dataclasses import FrozenInstanceError, replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

_HOOKS_DIR = Path(__file__).resolve().parents[3]

from _lib.adapters.live import (  # noqa: E402
    BreakerState,
    ClaudeLiveAdapter,
    LiveAdapterResult,
    LiveTransport,
)
from _lib.adapters.live._policy import ClaudeLivePolicy  # noqa: E402
from _lib.adapters.live._result import COMPLETION_STOP_REASONS  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Mock server (per-test scriptable response + last-request capture)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(BaseHTTPRequestHandler):
    # Path-scriptable: the count_tokens preflight and the messages POST hit
    # different paths against the same server, so responses are keyed by a
    # substring match on the request path.
    response_status: int = 200
    response_body: bytes = b"{}"
    count_status: int = 200
    count_body: bytes = b'{"input_tokens": 11}'
    response_headers: Dict[str, str] = {}
    requests: List[Dict[str, Any]] = []

    def log_message(self, format, *args):  # noqa: N802 - silence
        return

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        _Handler.requests.append(
            {
                "path": self.path,
                "headers": {k: v for k, v in self.headers.items()},
                "body": raw.decode("utf-8", errors="replace"),
            }
        )
        if self.path.endswith("/count_tokens"):
            status, body = _Handler.count_status, _Handler.count_body
        else:
            status, body = _Handler.response_status, _Handler.response_body
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for hk, hv in _Handler.response_headers.items():
            self.send_header(hk, hv)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


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


class _ClaudeO7Case(TestEnvContext):
    """Shared setup: mock server + activated Claude adapter + allowlist."""

    def setUp(self) -> None:
        super().setUp()
        self.server = _MockServer()
        self.server.start()
        _Handler.response_status = 200
        _Handler.response_body = b"{}"
        _Handler.count_status = 200
        _Handler.count_body = b'{"input_tokens": 11}'
        _Handler.response_headers = {}
        _Handler.requests = []
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-test-key-not-real"
        # PLAN-085 Wave C.1 live_adapter_allowlist runtime gate — write an
        # isolated settings.json under TestEnvContext.project_dir.
        settings = self.project_dir / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({"live_adapter_allowlist": ["claude"]}), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.server.stop()
        super().tearDown()

    @property
    def messages_url(self) -> str:
        return f"http://127.0.0.1:{self.server.port}/v1/messages"

    def _adapter(self, **kw) -> ClaudeLiveAdapter:
        kw.setdefault("url", self.messages_url)
        return ClaudeLiveAdapter(**kw)

    @staticmethod
    def _msg_request() -> Dict[str, Any]:
        for req in _Handler.requests:
            if not req["path"].endswith("/count_tokens"):
                return req
        raise AssertionError("no /v1/messages request captured")

    @staticmethod
    def _msg_body() -> Dict[str, Any]:
        return json.loads(_ClaudeO7Case._msg_request()["body"])


# ---------------------------------------------------------------------------
# O7-(1) — stop_reason / stop_details parsing (refusal != completion)
# ---------------------------------------------------------------------------


class TestLiveAdapterStopReasonParsing(_ClaudeO7Case):
    def test_live_adapter_end_turn_is_complete_not_refusal(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "done"}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
                "stop_reason": "end_turn",
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertEqual(r.stop_reason, "end_turn")
        self.assertIsNone(r.stop_details)
        self.assertTrue(r.is_complete())
        self.assertFalse(r.is_refusal())

    def test_live_adapter_refusal_stop_reason_success_but_not_complete(self):
        # The O7-(1) latent bug: pre-O7 a refusal parsed as a normal
        # completion. success=True (spend incurred) but NOT complete.
        _Handler.response_body = json.dumps(
            {
                "content": [],
                "usage": {"input_tokens": 4, "output_tokens": 0},
                "stop_reason": "refusal",
                "stop_details": {
                    "category": "cyber",
                    "explanation": "model free text — must NOT reach the audit log",
                },
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)  # transport+parse success
        self.assertTrue(r.is_refusal())
        self.assertFalse(r.is_complete())
        self.assertEqual(r.stop_reason, "refusal")
        self.assertEqual(r.stop_details.get("category"), "cyber")

    def test_live_adapter_max_tokens_stop_reason_not_complete(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "trunc"}],
                "usage": {"input_tokens": 4, "output_tokens": 64},
                "stop_reason": "max_tokens",
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertFalse(r.is_complete())  # truncation is not a completion
        self.assertFalse(r.is_refusal())

    def test_live_adapter_pause_turn_not_complete(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "..."}],
                "usage": {"input_tokens": 4, "output_tokens": 1},
                "stop_reason": "pause_turn",
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertFalse(r.is_complete())

    def test_live_adapter_tool_use_stop_reason_is_complete(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "calling"}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
                "stop_reason": "tool_use",
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.is_complete())
        self.assertIn("tool_use", COMPLETION_STOP_REASONS)

    def test_live_adapter_unknown_stop_reason_conservatively_not_complete(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "?"}],
                "usage": {"input_tokens": 4, "output_tokens": 1},
                "stop_reason": "some_future_reason",
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertFalse(r.is_complete())

    def test_live_adapter_missing_stop_reason_backcompat_complete(self):
        # Provider omits stop_reason → preserve pre-O7 meaning of success.
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 4, "output_tokens": 1},
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertIsNone(r.stop_reason)
        self.assertTrue(r.is_complete())

    def test_live_adapter_nonstr_stop_reason_degrades_to_none(self):
        _Handler.response_body = json.dumps(
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 4, "output_tokens": 1},
                "stop_reason": 12345,
                "stop_details": ["not", "a", "dict"],
                "model": "claude-haiku-4-5",
            }
        ).encode("utf-8")
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertIsNone(r.stop_reason)
        self.assertIsNone(r.stop_details)

    def test_live_adapter_result_is_frozen(self):
        r = LiveAdapterResult(
            success=True,
            text="x",
            tokens_in=1,
            tokens_out=1,
            cost_usd=0.0,
            duration_ms=1,
            failure_mode=None,
            http_status=200,
            breaker_state="closed",
            provider="anthropic",
            retry_count=0,
            fixture_fallback=False,
            stop_reason="refusal",
        )
        with self.assertRaises(FrozenInstanceError):
            r.stop_reason = "end_turn"  # type: ignore[misc]


class TestModelRefusalObservedAudit(_ClaudeO7Case):
    """O7-(1) closed-enum ``model_refusal_observed`` breadcrumb.

    Wired through the injected audit recorder. The action is declared in
    ``staged/w5/actions-added.md`` and only becomes a written event once
    arc consolidation lands it in ``_KNOWN_ACTIONS`` — the adapter calls
    ``emit_generic`` regardless (fail-open). These tests assert the call
    happens on refusal, does NOT happen on a normal completion, and never
    forwards ``stop_details.explanation`` free text.
    """

    def _recorder_adapter(self, sink: List[Dict[str, Any]]):
        def recorder(action, fields):
            sink.append({"action": action, "fields": fields})

        transport = LiveTransport(ClaudeLivePolicy(), on_audit=recorder)
        return self._adapter(transport=transport)

    def test_live_adapter_refusal_emits_only_category_no_explanation(self):
        # Capture emit_generic via monkeypatching the module the adapter
        # imports lazily (``from _lib import audit_emit``).
        from _lib import audit_emit as _ae

        calls: List[Dict[str, Any]] = []
        orig = getattr(_ae, "emit_generic", None)

        def fake_emit_generic(action, **fields):
            calls.append({"action": action, "fields": fields})

        _ae.emit_generic = fake_emit_generic  # type: ignore[attr-defined]
        try:
            _Handler.response_body = json.dumps(
                {
                    "content": [],
                    "usage": {"input_tokens": 4, "output_tokens": 0},
                    "stop_reason": "refusal",
                    "stop_details": {
                        "category": "bio",
                        "explanation": "SECRET-MODEL-FREE-TEXT-must-not-leak",
                    },
                    "model": "claude-haiku-4-5",
                }
            ).encode("utf-8")
            self._adapter().call(
                messages=[{"role": "user", "content": "x"}],
                model="claude-haiku-4-5",
            )
        finally:
            if orig is not None:
                _ae.emit_generic = orig  # type: ignore[attr-defined]

        refusal_calls = [c for c in calls if c["action"] == "model_refusal_observed"]
        self.assertEqual(len(refusal_calls), 1)
        fields = refusal_calls[0]["fields"]
        self.assertEqual(fields.get("stop_reason"), "refusal")
        self.assertEqual(fields.get("stop_category"), "bio")
        # explanation free text must NEVER be forwarded
        dump = json.dumps(fields, default=str)
        self.assertNotIn("SECRET-MODEL-FREE-TEXT-must-not-leak", dump)
        self.assertNotIn("explanation", fields)

    def test_live_adapter_completion_emits_no_refusal_event(self):
        from _lib import audit_emit as _ae

        calls: List[Dict[str, Any]] = []
        orig = getattr(_ae, "emit_generic", None)
        _ae.emit_generic = lambda action, **f: calls.append(  # type: ignore
            {"action": action}
        )
        try:
            _Handler.response_body = json.dumps(
                {
                    "content": [{"type": "text", "text": "fine"}],
                    "usage": {"input_tokens": 4, "output_tokens": 1},
                    "stop_reason": "end_turn",
                    "model": "claude-haiku-4-5",
                }
            ).encode("utf-8")
            self._adapter().call(
                messages=[{"role": "user", "content": "x"}],
                model="claude-haiku-4-5",
            )
        finally:
            if orig is not None:
                _ae.emit_generic = orig  # type: ignore[attr-defined]
        self.assertNotIn(
            "model_refusal_observed", [c["action"] for c in calls]
        )

    def test_live_adapter_refusal_emit_failure_never_breaks_call(self):
        # Fail-open: a broken emit_generic must not break the call path.
        from _lib import audit_emit as _ae

        orig = getattr(_ae, "emit_generic", None)

        def boom(action, **fields):
            raise RuntimeError("audit sink down")

        _ae.emit_generic = boom  # type: ignore[attr-defined]
        try:
            _Handler.response_body = json.dumps(
                {
                    "content": [],
                    "usage": {"input_tokens": 4, "output_tokens": 0},
                    "stop_reason": "refusal",
                    "stop_details": {"category": "cyber"},
                    "model": "claude-haiku-4-5",
                }
            ).encode("utf-8")
            r = self._adapter().call(
                messages=[{"role": "user", "content": "x"}],
                model="claude-haiku-4-5",
            )
        finally:
            if orig is not None:
                _ae.emit_generic = orig  # type: ignore[attr-defined]
        self.assertTrue(r.is_refusal())  # call still returned a typed result


# ---------------------------------------------------------------------------
# O7-(3) — automatic top-level cache_control
# ---------------------------------------------------------------------------


class TestLiveAdapterAutoCacheControl(_ClaudeO7Case):
    def test_live_adapter_default_sends_top_level_cache_control(self):
        _Handler.response_body = b'{"content":[],"usage":{}}'
        self._adapter().call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        body = self._msg_body()
        self.assertEqual(body.get("cache_control"), {"type": "ephemeral"})

    def test_live_adapter_kill_switch_restores_uncached_body(self):
        os.environ["CEO_CACHE_CONTROL_AUTO_DISABLE"] = "1"
        _Handler.response_body = b'{"content":[],"usage":{}}'
        self._adapter().call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        body = self._msg_body()
        self.assertNotIn("cache_control", body)

    def test_live_adapter_explicit_breakpoints_suppress_top_level(self):
        # cache_control=True (legacy per-block stamping) wins — no top-level
        # field (mutually exclusive paths).
        _Handler.response_body = b'{"content":[],"usage":{}}'
        self._adapter().call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-haiku-4-5",
            cache_control=True,
        )
        body = self._msg_body()
        self.assertNotIn("cache_control", body)


# ---------------------------------------------------------------------------
# O7-(4) — count_tokens() preflight (measured ceiling; bills zero tokens)
# ---------------------------------------------------------------------------


class TestLiveAdapterCountTokensPreflight(_ClaudeO7Case):
    def test_live_adapter_count_tokens_returns_measured_int(self):
        _Handler.count_body = b'{"input_tokens": 137}'
        n = self._adapter().count_tokens(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertEqual(n, 137)
        # request hit the /count_tokens path
        self.assertTrue(
            any(r["path"].endswith("/count_tokens") for r in _Handler.requests)
        )

    def test_live_adapter_count_tokens_failsoft_on_bad_body(self):
        _Handler.count_body = b"not-json"
        n = self._adapter().count_tokens(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertIsNone(n)

    def test_live_adapter_count_tokens_failsoft_on_missing_field(self):
        _Handler.count_body = b'{"no_input_tokens_here": 1}'
        n = self._adapter().count_tokens(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertIsNone(n)

    def test_live_adapter_count_tokens_dormant_when_activation_off(self):
        os.environ.pop("CEO_LIVE_CLAUDE", None)
        n = self._adapter().count_tokens(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertIsNone(n)
        # No network when the adapter is gated off.
        self.assertEqual(_Handler.requests, [])

    def test_live_adapter_preflight_env_off_skips_count_tokens(self):
        # Without CEO_COUNT_TOKENS_PREFLIGHT, the heuristic estimate is used
        # and no count_tokens request is made.
        os.environ.pop("CEO_COUNT_TOKENS_PREFLIGHT", None)
        _Handler.response_body = b'{"content":[],"usage":{}}'
        self._adapter().call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertFalse(
            any(r["path"].endswith("/count_tokens") for r in _Handler.requests)
        )

    def test_live_adapter_preflight_env_on_consults_count_tokens(self):
        os.environ["CEO_COUNT_TOKENS_PREFLIGHT"] = "1"
        _Handler.count_body = b'{"input_tokens": 9}'
        _Handler.response_body = b'{"content":[{"type":"text","text":"ok"}],"usage":{}}'
        r = self._adapter().call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        # both the preflight count and the real messages POST happened
        self.assertTrue(
            any(req["path"].endswith("/count_tokens") for req in _Handler.requests)
        )
        self.assertTrue(
            any(not req["path"].endswith("/count_tokens") for req in _Handler.requests)
        )

    def test_live_adapter_preflight_measured_ceiling_blocks_overbudget(self):
        # A huge measured input → budget_hard_stop, and the real messages
        # POST is never sent (only the count_tokens preflight ran). Inject a
        # tight per-spawn ceiling via the SpawnCostTracker.
        from _lib.adapters.live._cost import SpawnCostTracker

        os.environ["CEO_COUNT_TOKENS_PREFLIGHT"] = "1"
        _Handler.count_body = b'{"input_tokens": 100000000}'
        tracker = SpawnCostTracker(ceiling_usd=0.000001)
        r = self._adapter(spawn_tracker=tracker).call(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        self.assertFalse(r.success)
        self.assertEqual(r.failure_mode, "budget_hard_stop")
        self.assertFalse(
            any(
                not req["path"].endswith("/count_tokens")
                for req in _Handler.requests
            )
        )

    def test_live_adapter_count_tokens_credential_never_echoed(self):
        events: List[Dict[str, Any]] = []
        transport = LiveTransport(
            ClaudeLivePolicy(),
            on_audit=lambda a, f: events.append({"a": a, "f": f}),
        )
        _Handler.count_body = b'{"input_tokens": 5}'
        self._adapter(transport=transport).count_tokens(
            messages=[{"role": "user", "content": "hi"}], model="claude-haiku-4-5"
        )
        dump = json.dumps(events, default=str)
        self.assertNotIn("sk-ant-fake-test-key-not-real", dump)


# ---------------------------------------------------------------------------
# O7-(5) — request_id capture on the error path
# ---------------------------------------------------------------------------


class TestLiveAdapterRequestIdOnError(_ClaudeO7Case):
    def test_live_adapter_request_id_from_header_on_500(self):
        _Handler.response_status = 500
        _Handler.response_body = b'{"error":"boom"}'
        _Handler.response_headers = {"request-id": "req_018HeaderId"}
        pol = replace(ClaudeLivePolicy(), max_retries=0)
        r = self._adapter(policy=pol).call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertFalse(r.success)
        self.assertEqual(r.request_id, "req_018HeaderId")

    def test_live_adapter_request_id_from_error_body_when_no_header(self):
        _Handler.response_status = 500
        _Handler.response_body = b'{"error":"boom","request_id":"req_018BodyId"}'
        _Handler.response_headers = {}
        pol = replace(ClaudeLivePolicy(), max_retries=0)
        r = self._adapter(policy=pol).call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertFalse(r.success)
        self.assertEqual(r.request_id, "req_018BodyId")

    def test_live_adapter_request_id_x_request_id_header_fallback(self):
        _Handler.response_status = 503
        _Handler.response_body = b'{"error":"overloaded"}'
        _Handler.response_headers = {"x-request-id": "req_018XReq"}
        pol = replace(ClaudeLivePolicy(), max_retries=0)
        r = self._adapter(policy=pol).call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertFalse(r.success)
        self.assertEqual(r.request_id, "req_018XReq")

    def test_live_adapter_request_id_empty_on_clean_success(self):
        _Handler.response_status = 200
        _Handler.response_body = b'{"content":[],"usage":{},"stop_reason":"end_turn"}'
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertTrue(r.success)
        self.assertEqual(r.request_id, "")

    def test_live_adapter_request_id_never_carries_credential(self):
        _Handler.response_status = 401
        _Handler.response_body = b'{"error":"unauthorized"}'
        _Handler.response_headers = {"request-id": "req_018Auth"}
        r = self._adapter().call(
            messages=[{"role": "user", "content": "x"}], model="claude-haiku-4-5"
        )
        self.assertFalse(r.success)
        self.assertNotIn("sk-ant-fake-test-key-not-real", r.request_id or "")


# ---------------------------------------------------------------------------
# O7-(2) probe guard — response_format pass-through is INTENTIONALLY still
# the legacy param (NOT migrated to output_config.format). This test pins
# the un-migrated state so the prepared migration in
# research/O7-output-config-prepared.md is a deliberate, reviewed flip and
# not an accidental drift. Named with ``output_config`` for selector match.
# ---------------------------------------------------------------------------


class TestLiveAdapterOutputConfigNotYetMigrated(_ClaudeO7Case):
    def test_live_adapter_response_format_still_legacy_passthrough(self):
        _Handler.response_body = b'{"content":[],"usage":{}}'
        schema = {"type": "json_schema", "schema": {"type": "object"}}
        self._adapter().call(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-haiku-4-5",
            response_format=schema,
        )
        body = self._msg_body()
        # Pre-migration invariant: legacy key present, canonical key absent.
        self.assertEqual(body.get("response_format"), schema)
        self.assertNotIn(
            "format", (body.get("output_config") or {}),
            msg=(
                "output_config.format appeared — the O7-(2) migration must "
                "land via research/O7-output-config-prepared.md behind the "
                "probe verdict, not by drift."
            ),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
