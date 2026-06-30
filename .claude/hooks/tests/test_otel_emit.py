"""Unit tests for _lib/otel_emit.py (PLAN-011 Phase 8, CR3 library path).

Scope:
- try_export_events is fail-open on bad endpoint (ADR-005)
- sota_disabled kill-switch
- double_redact semantics (idempotent, applied twice)
- validate_endpoint rejects scheme + host correctly
- otel_export_dropped emission path
- event_to_span drops description_hash and produces valid OTLP attrs
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import otel_emit  # noqa: E402
from _lib import audit_emit as _audit  # noqa: E402


class TestKillSwitch(TestEnvContext):
    def test_sota_disable_returns_disabled_summary(self) -> None:
        os.environ["CEO_SOTA_DISABLE"] = "1"
        summary = otel_emit.export_events(
            "https://tempo.example.com/v1/traces",
            [{"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z"}],
            dry_run=True,
            allowed_hosts=["tempo.example.com"],
        )
        self.assertTrue(summary["disabled"])
        self.assertEqual(summary["exported"], 0)

    def test_sota_disable_false_when_unset(self) -> None:
        os.environ.pop("CEO_SOTA_DISABLE", None)
        self.assertFalse(otel_emit.sota_disabled())


class TestValidateEndpoint(TestEnvContext):
    def test_https_required(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        with self.assertRaises(otel_emit.OtelExportError) as cm:
            otel_emit.validate_endpoint("http://tempo.example.com/v1/traces")
        self.assertIn("scheme http not allowed", str(cm.exception))

    def test_allowlist_empty_rejects(self) -> None:
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        with self.assertRaises(otel_emit.OtelExportError) as cm:
            otel_emit.validate_endpoint("https://tempo.example.com/v1/traces")
        self.assertIn("not in allowlist", str(cm.exception))

    def test_allowlist_explicit_param(self) -> None:
        # Explicit allowed_hosts param beats env var.
        host, url = otel_emit.validate_endpoint(
            "https://tempo.example.com/v1/traces",
            allowed_hosts=["tempo.example.com"],
        )
        self.assertEqual(host, "tempo.example.com")
        self.assertEqual(url, "https://tempo.example.com/v1/traces")

    def test_no_hostname_rejected(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "x"
        with self.assertRaises(otel_emit.OtelExportError):
            otel_emit.validate_endpoint("https:///only-path")


class TestDoubleRedact(TestEnvContext):
    def test_idempotent_and_redacts(self) -> None:
        raw = "call with sk-abcdef1234567890abcdef and Bearer xyz9"
        r1 = otel_emit.double_redact(raw)
        r2 = otel_emit.double_redact(r1)
        self.assertEqual(r1, r2)
        self.assertNotIn("sk-abcdef1234567890abcdef", r1)
        self.assertIn("[API_KEY]", r1)
        self.assertIn("Bearer [TOKEN]", r1)

    def test_empty_string(self) -> None:
        self.assertEqual(otel_emit.double_redact(""), "")

    def test_non_secret_unchanged(self) -> None:
        self.assertEqual(otel_emit.double_redact("hello world"), "hello world")


class TestEventToSpan(TestEnvContext):
    def test_description_hash_dropped(self) -> None:
        event = {
            "action": "agent_spawn",
            "ts": "2026-04-14T10:00:00Z",
            "description_hash": "deadbeef" * 8,
            "desc_preview": "hello",
            "project": "ceo-orchestration",
            "session_id": "sess",
        }
        span, dropped = otel_emit.event_to_span(event)
        self.assertGreaterEqual(dropped, 1)
        keys = {a["key"] for a in span["attributes"]}
        self.assertNotIn("description_hash", keys)
        self.assertIn("desc_preview", keys)
        # project/session_id are resource attrs, not span attrs
        self.assertNotIn("project", keys)
        self.assertNotIn("session_id", keys)

    def test_none_values_dropped(self) -> None:
        event = {
            "action": "agent_spawn",
            "ts": "2026-04-14T10:00:00Z",
            "tokens_in": None,
            "tokens_out": None,
        }
        span, _ = otel_emit.event_to_span(event)
        keys = {a["key"] for a in span["attributes"]}
        self.assertNotIn("tokens_in", keys)
        self.assertNotIn("tokens_out", keys)

    def test_int_value_preserved_as_string(self) -> None:
        """OTLP intValue is a string (preserves i64 precision over JSON)."""
        event = {
            "action": "agent_spawn",
            "ts": "2026-04-14T10:00:00Z",
            "retry_count": 3,
        }
        span, _ = otel_emit.event_to_span(event)
        attrs = {a["key"]: a["value"] for a in span["attributes"]}
        self.assertEqual(attrs["retry_count"], {"intValue": "3"})


class TestFailOpen(TestEnvContext):
    def test_try_export_swallows_errors(self) -> None:
        """ADR-005: library integration path must never raise."""
        # Bad endpoint (http scheme) — would raise from export_events
        result = otel_emit.try_export_events(
            "http://attacker.example.com/v1/traces",
            [{"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z"}],
            dry_run=True,
        )
        self.assertIsNone(result)

    def test_try_export_none_endpoint(self) -> None:
        result = otel_emit.try_export_events(
            None, [{"action": "agent_spawn"}], dry_run=True
        )
        self.assertIsNone(result)

    def test_try_export_happy_path(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        result = otel_emit.try_export_events(
            "https://tempo.example.com/v1/traces",
            [{"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z"}],
            dry_run=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["exported"], 1)


class TestDropEmission(TestEnvContext):
    def test_scheme_reject_emits_drop_event(self) -> None:
        """A scheme reject MUST emit otel_export_dropped."""
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "x"
        try:
            otel_emit.validate_endpoint("http://attacker.example.com/")
        except otel_emit.OtelExportError:
            pass
        events = [
            e
            for e in _audit.iter_events()
            if e.get("action") == "otel_export_dropped"
        ]
        self.assertGreaterEqual(len(events), 1)
        self.assertIn("scheme_rejected", events[-1]["reason"])

    def test_host_reject_emits_drop_event(self) -> None:
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        try:
            otel_emit.validate_endpoint("https://evil.example.com/")
        except otel_emit.OtelExportError:
            pass
        events = [
            e
            for e in _audit.iter_events()
            if e.get("action") == "otel_export_dropped"
        ]
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[-1]["reason"], "host_rejected")
        # Host-only — never any URL path
        self.assertEqual(events[-1]["endpoint_host"], "evil.example.com")


class TestBatchToOtlp(TestEnvContext):
    def test_structure(self) -> None:
        events = [
            {
                "action": "agent_spawn",
                "ts": "2026-04-14T10:00:00Z",
                "project": "ceo-orchestration",
                "session_id": "s1",
            },
            {
                "action": "plan_transition",
                "ts": "2026-04-14T10:00:01Z",
                "project": "ceo-orchestration",
                "session_id": "s1",
            },
        ]
        payload, dropped = otel_emit.batch_to_otlp(events)
        self.assertEqual(dropped, 0)
        self.assertIn("resourceSpans", payload)
        scope_spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual(len(scope_spans), 2)
        # Resource attrs contain service.name + ceo.project
        resource = payload["resourceSpans"][0]["resource"]
        keys = {a["key"] for a in resource["attributes"]}
        self.assertIn("service.name", keys)
        self.assertIn("ceo.project", keys)


class TestHeadersRedact(TestEnvContext):
    def test_bearer_header_redacted(self) -> None:
        sanitized = otel_emit._sanitize_headers(
            {"Authorization": "Bearer abcdefabcdef1234"}
        )
        self.assertEqual(sanitized["Authorization"], "Bearer [TOKEN]")

    def test_api_key_header_redacted(self) -> None:
        sanitized = otel_emit._sanitize_headers(
            {"X-API-Key": "api_key=sk-abcdefabcdef1234567890"}
        )
        # The redactor rewrites api_key=... into api_key=[REDACTED]
        self.assertIn("[REDACTED]", sanitized["X-API-Key"])
        self.assertNotIn("sk-abcdefabcdef1234567890", sanitized["X-API-Key"])

    def test_non_string_header_skipped(self) -> None:
        sanitized = otel_emit._sanitize_headers({"X-Int": 42})  # type: ignore[dict-item]
        self.assertNotIn("X-Int", sanitized)


if __name__ == "__main__":
    import unittest

    unittest.main()
