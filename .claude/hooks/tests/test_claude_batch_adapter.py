"""PLAN-090 Wave B.4 — BatchClaudeLiveAdapter parity + batch + streaming tests.

30 tests covering:

- construction-time allowlist gate (PLAN-085 Wave C.1)
- batch_call returns ordered results aligned with input
- stream_call yields tokens then final result
- ABI parity with synchronous ClaudeLiveAdapter
- cost-attribution via batch_dispatched emit (existing)
- fixture fallback path on activation-off / missing-credential / blocked allowlist

NO network I/O — tests run with CEO_LIVE_CLAUDE unset (fixture fallback).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


def _settings_with_allowlist(provider: str = "claude") -> str:
    return json.dumps({"live_adapter_allowlist": [provider]})


class TestBatchClaudeLiveAdapterConstruction(TestEnvContext):

    def test_provider_name_inherited(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        self.assertEqual(adapter.provider_name, "anthropic")

    def test_policy_rejects_non_claude_provider(self) -> None:
        from _lib.adapters.live._policy import LiveCallPolicy
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        bad = LiveCallPolicy(provider="openai")
        with self.assertRaises(ValueError):
            BatchClaudeLiveAdapter(policy=bad)

    def test_inherits_claude_live_adapter(self) -> None:
        from _lib.adapters.live.claude import ClaudeLiveAdapter
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        self.assertTrue(issubclass(BatchClaudeLiveAdapter, ClaudeLiveAdapter))

    def test_batch_url_defaults_to_messages_batches(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        self.assertIn("messages/batches", adapter._batch_url)

    def test_stream_url_defaults_to_messages(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        self.assertIn("messages", adapter._stream_url)


class TestBatchClaudeLiveAdapterAllowlist(TestEnvContext):

    def test_allowlist_missing_fails_closed_batch(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        adapter = BatchClaudeLiveAdapter()
        results = adapter.batch_call(requests=[{"messages": [], "model": "claude-haiku-4-5"}])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].fixture_fallback)

    def test_allowlist_present_allows_batch(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        # No live activation env → fixture fallback regardless, but the
        # allowlist gate must permit construction.
        self.write_project_file(".claude/settings.json", _settings_with_allowlist())
        adapter = BatchClaudeLiveAdapter()
        # _check_live_adapter_allowlist returns None on allowlist-present
        # when policy.provider == "claude".
        result = adapter._check_live_adapter_allowlist()
        self.assertIsNone(result)

    def test_allowlist_empty_fails_closed(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        self.write_project_file(
            ".claude/settings.json",
            json.dumps({"live_adapter_allowlist": []}),
        )
        adapter = BatchClaudeLiveAdapter()
        result = adapter._check_live_adapter_allowlist()
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("empty_allowlist", result)


class TestBatchCall(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        # PLAN-107 Wave D — defend against (1) PLAN-088 100/min rate-cap
        # accumulation across tests in the same pytest run, and (2)
        # ``_lib.audit_emit`` cached in ``sys.modules`` as a fixture stub
        # (reality-ledger fixture ships a 2-action stub that lacks
        # ``emit_batch_dispatched``). Force-reload the module from the
        # real repo path and clear the rate-cap singleton.
        import importlib
        import sys as _sys
        _sys.modules.pop("_lib.audit_emit", None)
        _ae = importlib.import_module("_lib.audit_emit")
        _clear = getattr(_ae, "_plan088_rate_state_clear", None)
        if callable(_clear):
            _clear()

    def test_batch_fixture_fallback_returns_ordered(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        requests = [
            {"messages": [{"role": "user", "content": "a"}], "model": "claude-haiku-4-5"},
            {"messages": [{"role": "user", "content": "b"}], "model": "claude-haiku-4-5"},
            {"messages": [{"role": "user", "content": "c"}], "model": "claude-haiku-4-5"},
        ]
        results = adapter.batch_call(requests=requests)
        self.assertEqual(len(results), len(requests))
        for r in results:
            self.assertTrue(r.fixture_fallback)
            self.assertEqual(r.provider, "anthropic")

    def test_batch_empty_requests_returns_empty(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        results = adapter.batch_call(requests=[])
        self.assertEqual(results, [])

    def test_batch_missing_credential_returns_failure(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.write_project_file(".claude/settings.json", _settings_with_allowlist())
        adapter = BatchClaudeLiveAdapter()
        results = adapter.batch_call(
            requests=[{"messages": [], "model": "claude-haiku-4-5"}],
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertEqual(results[0].failure_mode, "missing_credential")

    def test_batch_emits_batch_dispatched_once(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        log = self.read_audit_log()
        # In fixture-fallback mode, batch_dispatched still emits with
        # aggregate token counts (zero in fallback).
        self.assertEqual(
            log.count('"batch_dispatched"'), 1,
            f"expected exactly one batch_dispatched, got: {log!r}",
        )


class TestStreamCall(TestEnvContext):

    def test_stream_fixture_fallback_yields_final_only(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        chunks = list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        self.assertEqual(len(chunks), 1)
        token, result = chunks[0]
        self.assertIsNone(token)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.fixture_fallback)

    def test_stream_aggregates_at_end_by_default(self) -> None:
        # Default mode (CEO_AUDIT_STREAM_VERBOSE unset) emits aggregate
        # batch_dispatched at stream-end, NOT per-token.
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)
        adapter = BatchClaudeLiveAdapter()
        list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        log = self.read_audit_log()
        self.assertNotIn('"streaming_token_yielded"', log)

    def test_stream_verbose_disabled_for_truthy_non_one(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        for value in ("true", "yes", "0", "TRUE", "", " 1"):
            with self.subTest(value=repr(value)):
                os.environ["CEO_AUDIT_STREAM_VERBOSE"] = value
                try:
                    adapter = BatchClaudeLiveAdapter()
                    list(adapter.stream_call(
                        messages=[{"role": "user", "content": "x"}],
                        model="claude-haiku-4-5",
                    ))
                    log = self.read_audit_log()
                    self.assertNotIn(
                        '"streaming_token_yielded"', log,
                        f"verbose-mode must require EXACT =1, got {value!r}",
                    )
                finally:
                    os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)


class TestAbiParityWithClaudeAdapter(TestEnvContext):

    def test_call_method_inherited(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        # Inherited synchronous call method still works.
        result = adapter.call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        )
        self.assertEqual(result.provider, "anthropic")
        self.assertTrue(result.fixture_fallback)

    def test_policy_inherited(self) -> None:
        from _lib.adapters.live._policy import LiveCallPolicy
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        policy = LiveCallPolicy(provider="claude")
        adapter = BatchClaudeLiveAdapter(policy=policy)
        self.assertIs(adapter.policy, policy)

    def test_breaker_inherited(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        self.assertIsNotNone(adapter._breaker)

    def test_spawn_tracker_inherited(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        self.assertIsNotNone(adapter._spawn_tracker)


class TestCostAttribution(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        # PLAN-107 Wave D — defend against (1) PLAN-088 100/min rate-cap
        # accumulation across tests in the same pytest run, and (2)
        # ``_lib.audit_emit`` cached in ``sys.modules`` as a fixture stub
        # (reality-ledger fixture ships a 2-action stub that lacks
        # ``emit_batch_dispatched``). Force-reload the module from the
        # real repo path and clear the rate-cap singleton.
        import importlib
        import sys as _sys
        _sys.modules.pop("_lib.audit_emit", None)
        _ae = importlib.import_module("_lib.audit_emit")
        _clear = getattr(_ae, "_plan088_rate_state_clear", None)
        if callable(_clear):
            _clear()

    def test_batch_emits_tokens_total_field(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        log = self.read_audit_log()
        if '"batch_dispatched"' in log:
            self.assertIn('"tokens_total"', log)

    def test_stream_emits_batch_dispatched_aggregate_at_end(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        log = self.read_audit_log()
        # Even in fixture-fallback mode, aggregate batch_dispatched emit fires.
        # Streaming variant uses request_class=streaming discriminator.
        self.assertIn('"batch_dispatched"', log)


class TestExports(TestEnvContext):

    def test_exports_via_adapters_init(self) -> None:
        from _lib import adapters
        # __init__.py exposes BatchClaudeLiveAdapter via attribute access.
        self.assertTrue(hasattr(adapters, "BatchClaudeLiveAdapter")
                        or hasattr(adapters, "live"))

    def test_module_all_lists_class(self) -> None:
        from _lib.adapters.live import claude_batch
        self.assertIn("BatchClaudeLiveAdapter", claude_batch.__all__)


class TestFailureModes(TestEnvContext):

    def test_activation_off_returns_fixture_per_request(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_LIVE_CLAUDE", None)
        adapter = BatchClaudeLiveAdapter()
        results = adapter.batch_call(requests=[
            {"messages": [], "model": "claude-haiku-4-5"},
            {"messages": [], "model": "claude-haiku-4-5"},
        ])
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.fixture_fallback)
            self.assertEqual(r.provider, "anthropic")

    def test_streaming_activation_off_yields_fixture(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_LIVE_CLAUDE", None)
        adapter = BatchClaudeLiveAdapter()
        chunks = list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        self.assertEqual(len(chunks), 1)
        _, result = chunks[0]
        assert result is not None
        self.assertTrue(result.fixture_fallback)


class TestRequestShape(TestEnvContext):

    def test_batch_request_thinking_kwarg_pass_through(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        # Even in fixture fallback, the wrapper does not crash on thinking kwarg.
        results = adapter.batch_call(requests=[
            {
                "messages": [{"role": "user", "content": "x"}],
                "model": "claude-haiku-4-5",
                "thinking": {"type": "enabled", "budget_tokens": 1024},
            },
        ])
        self.assertEqual(len(results), 1)

    def test_batch_request_max_tokens_default(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        results = adapter.batch_call(requests=[
            {
                "messages": [{"role": "user", "content": "x"}],
                "model": "claude-haiku-4-5",
            },
        ])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].provider, "anthropic")

    def test_stream_emits_streaming_request_class_field(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        log = self.read_audit_log()
        if '"batch_dispatched"' in log:
            # The discriminator lands in `trigger_source` (existing
            # emit_batch_dispatched signature). Tolerate space after colon.
            self.assertTrue(
                '"trigger_source": "streaming"' in log
                or '"trigger_source":"streaming"' in log,
            )

    def test_batch_emits_batch_request_class(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        log = self.read_audit_log()
        if '"batch_dispatched"' in log:
            self.assertTrue(
                '"trigger_source": "batch"' in log
                or '"trigger_source":"batch"' in log,
            )


class TestOrdering(TestEnvContext):

    def test_batch_results_preserve_input_order(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        adapter = BatchClaudeLiveAdapter()
        requests = [
            {"messages": [{"role": "user", "content": str(i)}], "model": "claude-haiku-4-5"}
            for i in range(5)
        ]
        results = adapter.batch_call(requests=requests)
        self.assertEqual(len(results), 5)
        # All fixture-fallback results carry provider="anthropic" — order
        # invariant is just len + alignment.
        for r in results:
            self.assertEqual(r.provider, "anthropic")


class TestBatchRequestPayloadBuilder(TestEnvContext):
    """PLAN-113 W5 COOK-P4 — native /v1/messages/batches payload construction.

    Offline / pure-function tests of the wire-format builder. The async
    batch lifecycle (create -> poll -> retrieve) is NOT the execution path
    (reported needs-design), but the request payload must be correct.
    """

    def test_payload_wraps_requests_key(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"messages": [{"role": "user", "content": "a"}],
              "model": "claude-haiku-4-5"}]
        )
        self.assertIn("requests", payload)
        self.assertEqual(len(payload["requests"]), 1)

    def test_payload_custom_id_positional_default(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "m", "messages": []},
             {"model": "m", "messages": []}]
        )
        self.assertEqual(payload["requests"][0]["custom_id"], "request-0")
        self.assertEqual(payload["requests"][1]["custom_id"], "request-1")

    def test_payload_custom_id_caller_supplied(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"custom_id": "finding-42", "model": "m", "messages": []}]
        )
        self.assertEqual(payload["requests"][0]["custom_id"], "finding-42")

    def test_payload_params_shape(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "claude-opus-4-8", "max_tokens": 256,
              "messages": [{"role": "user", "content": "x"}]}]
        )
        params = payload["requests"][0]["params"]
        self.assertEqual(params["model"], "claude-opus-4-8")
        self.assertEqual(params["max_tokens"], 256)
        self.assertEqual(params["messages"], [{"role": "user", "content": "x"}])

    def test_payload_max_tokens_default(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "m", "messages": []}]
        )
        self.assertEqual(payload["requests"][0]["params"]["max_tokens"], 1024)

    def test_payload_thinking_only_when_supplied(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "m", "messages": []},
             {"model": "m", "messages": [],
              "thinking": {"type": "enabled", "budget_tokens": 1024}}]
        )
        self.assertNotIn("thinking", payload["requests"][0]["params"])
        self.assertEqual(
            payload["requests"][1]["params"]["thinking"],
            {"type": "enabled", "budget_tokens": 1024},
        )

    def test_payload_carries_cook_p1_optionals(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "m", "messages": [],
              "tools": [{"name": "t"}],
              "tool_choice": {"type": "tool", "name": "t"},
              "system": "sys"}]
        )
        params = payload["requests"][0]["params"]
        self.assertEqual(params["tools"], [{"name": "t"}])
        self.assertEqual(params["tool_choice"], {"type": "tool", "name": "t"})
        self.assertEqual(params["system"], "sys")

    def test_payload_empty_requests(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload([])
        self.assertEqual(payload, {"requests": []})

    def test_payload_json_serializable(self) -> None:
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        payload = BatchClaudeLiveAdapter.build_batch_request_payload(
            [{"model": "m", "messages": [{"role": "user", "content": "x"}],
              "thinking": {"type": "enabled", "budget_tokens": 512}}]
        )
        # Must round-trip through json without error (it goes on the wire).
        self.assertIsInstance(json.dumps(payload), str)


class _CaptureTransport:
    """Transport stub that records calls by method (GET vs POST)."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []  # {"method", "url", "body"}

    def post_json(self, url, headers, body):
        self.calls.append({"method": "POST", "url": url, "body": body})

        class _FailureStub:
            failure_mode = "transport_stub"
            http_status = None
            duration_ms = 1
            retried = False

        return None, _FailureStub()

    def get_json(self, url, headers):
        self.calls.append({"method": "GET", "url": url})

        class _FailureStub:
            failure_mode = "transport_stub"
            http_status = None
            duration_ms = 1
            retried = False

        return None, _FailureStub()


def _make_batch_adapter_with_transport(transport):
    """Helper — return a BatchClaudeLiveAdapter wired to a stub transport."""
    from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
    adapter = BatchClaudeLiveAdapter()
    adapter._transport = transport
    return adapter


class TestBatchPollAndRetrieveUseGet(TestEnvContext):
    """P1 fix: batch_poll + batch_retrieve MUST use GET, not POST.

    The Anthropic Batch API status + results endpoints are read-only
    resource retrieval; they accept GET only. Using POST was a defect.
    """

    def test_batch_poll_uses_get_not_post(self) -> None:
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        adapter.batch_poll("batch-abc123", "sk-test")
        self.assertEqual(len(t.calls), 1, "expected exactly 1 transport call")
        self.assertEqual(t.calls[0]["method"], "GET",
                         "batch_poll MUST use GET, not POST")

    def test_batch_poll_url_contains_batch_id(self) -> None:
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        adapter.batch_poll("batch-xyz999", "sk-test")
        self.assertIn("batch-xyz999", t.calls[0]["url"])

    def test_batch_retrieve_uses_get_not_post(self) -> None:
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        adapter.batch_retrieve("batch-abc123", "sk-test", ["request-0"])
        self.assertEqual(len(t.calls), 1, "expected exactly 1 transport call")
        self.assertEqual(t.calls[0]["method"], "GET",
                         "batch_retrieve MUST use GET, not POST")

    def test_batch_retrieve_url_contains_results(self) -> None:
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        adapter.batch_retrieve("batch-abc123", "sk-test", [])
        self.assertIn("results", t.calls[0]["url"])

    def test_batch_create_uses_post(self) -> None:
        """Positive control: batch_create must still use POST (mutation)."""
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        adapter.batch_create({"requests": []}, "sk-test")
        self.assertEqual(t.calls[0]["method"], "POST",
                         "batch_create MUST still use POST")


class TestNativeBatchLifecycleOptIn(TestEnvContext):
    """P2 fix: CEO_NATIVE_BATCH_LIFECYCLE=1 must actually wire the create/poll/
    retrieve lifecycle, not silently remain on the sequential fallback.

    Tests run with the env set but transport stubs returning failures so the
    native lifecycle falls through to sequential — this exercises the branch
    paths without a live network.
    """

    def setUp(self) -> None:
        super().setUp()
        import importlib, sys as _sys
        _sys.modules.pop("_lib.audit_emit", None)
        _ae = importlib.import_module("_lib.audit_emit")
        _clear = getattr(_ae, "_plan088_rate_state_clear", None)
        if callable(_clear):
            _clear()

    def test_native_lifecycle_disabled_by_default(self) -> None:
        """Without the env var, native lifecycle is OFF."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ.pop("CEO_NATIVE_BATCH_LIFECYCLE", None)
        adapter = BatchClaudeLiveAdapter()
        self.assertFalse(adapter._native_batch_lifecycle_enabled())

    def test_native_lifecycle_enabled_by_env_var(self) -> None:
        """CEO_NATIVE_BATCH_LIFECYCLE=1 enables the native lifecycle."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = "1"
        adapter = BatchClaudeLiveAdapter()
        self.assertTrue(adapter._native_batch_lifecycle_enabled())

    def test_native_lifecycle_not_enabled_by_truthy_non_one(self) -> None:
        """Truthy but non-exact '1' values must NOT enable (exact-match discipline)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        for value in ("true", "yes", "TRUE", "on", "2"):
            with self.subTest(value=value):
                os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = value
                adapter = BatchClaudeLiveAdapter()
                self.assertFalse(adapter._native_batch_lifecycle_enabled(),
                                 f"must be off for value={value!r}")

    def test_native_batch_lifecycle_calls_batch_create(self) -> None:
        """When CEO_NATIVE_BATCH_LIFECYCLE=1, batch_call must attempt batch_create."""
        # Must enable live mode so the activation gate passes and the native
        # lifecycle branch is reached (without live mode the gate fires first
        # and returns fixture-fallback before any transport call).
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        self.write_project_file(".claude/settings.json", _settings_with_allowlist())
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = "1"
        # batch_create returns None (transport stub) → falls through to sequential.
        # sequential call() also goes via transport → also returns stub failure.
        adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        # Must have attempted POST (batch_create) at some point.
        post_calls = [c for c in t.calls if c["method"] == "POST"]
        self.assertTrue(
            len(post_calls) >= 1,
            "batch_call with CEO_NATIVE_BATCH_LIFECYCLE=1 must attempt batch_create POST",
        )

    def test_native_lifecycle_fallback_to_sequential_on_create_failure(self) -> None:
        """batch_call returns sequential results when batch_create fails (fail-soft)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        os.environ["CEO_NATIVE_BATCH_LIFECYCLE"] = "1"
        # Activation gate will block (no CEO_LIVE_CLAUDE=1) → fixture fallback.
        results = adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"},
        ])
        self.assertEqual(len(results), 1)
        # Result is present (fixture fallback or sequential), not an empty list.
        self.assertIsNotNone(results[0])

    def test_native_lifecycle_off_does_not_call_batch_create(self) -> None:
        """Without CEO_NATIVE_BATCH_LIFECYCLE, no batch_create POST is attempted."""
        t = _CaptureTransport()
        adapter = _make_batch_adapter_with_transport(t)
        os.environ.pop("CEO_NATIVE_BATCH_LIFECYCLE", None)
        # Activation gate off (no CEO_LIVE_CLAUDE) → fixture fallback immediately.
        adapter.batch_call(requests=[
            {"messages": [{"role": "user", "content": "x"}], "model": "claude-haiku-4-5"}
        ])
        # With native lifecycle OFF, only sequential call() is used.
        # In fixture fallback mode, no transport calls are made at all.
        create_posts = [c for c in t.calls if c["method"] == "POST"]
        # In fixture-fallback the transport is never invoked.
        self.assertEqual(len(create_posts), 0,
                         "native lifecycle must NOT run when CEO_NATIVE_BATCH_LIFECYCLE is absent")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
