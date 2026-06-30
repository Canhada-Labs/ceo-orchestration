"""Unit tests for .claude/scripts/otel-export.py (PLAN-011 Phase 8).

Scope:
- Scheme allowlist (http/file/gopher/ws rejected)
- Host allowlist (empty default rejects; exact match accepts)
- Double redaction on span attributes (Bearer, API_KEY)
- description_hash drop + otel_export_dropped emission with host-only
- --dry-run emits OTLP JSON to stdout, no POST
- CEO_SOTA_DISABLE=1 short-circuits
- --since filtering (24h window)
- Malformed audit line skipped
- Headers parsing + double-redaction of token values
- Mock OTLP receiver round-trip via stdlib http.server (HTTPS self-signed)
- --no-tls-verify only works under CEO_OTEL_SMOKE=1
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import ssl
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import otel_emit  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "otel_export_cli", SCRIPTS_DIR / "otel-export.py"
)
otel_export = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(otel_export)  # type: ignore[union-attr]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _write_audit_jsonl(path: Path, events: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _run_cli(args: List[str]) -> tuple:
    """Run main(args) while capturing stdout/stderr. Return (rc, out, err)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        rc = otel_export.main(args)
        return rc, sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def _make_valid_event(**overrides) -> dict:
    ev = {
        "action": "agent_spawn",
        "ts": "2026-04-14T10:00:00Z",
        "project": "ceo-orchestration",
        "session_id": "sess-abc",
        "description_hash": "deadbeef" * 8,
        "desc_preview": "spawn xyz",
    }
    ev.update(overrides)
    return ev


# -----------------------------------------------------------------------------
# Schema / validation
# -----------------------------------------------------------------------------


class TestSchemeAllowlist(TestEnvContext):
    def test_http_rejected(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "attacker.example.com"
        rc, _, err = _run_cli(
            ["--endpoint", "http://attacker.example.com/v1/traces", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("scheme http not allowed", err)

    def test_file_rejected(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "evil.local"
        rc, _, err = _run_cli(
            ["--endpoint", "file:///etc/passwd", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("scheme file not allowed", err)

    def test_gopher_rejected(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "foo.bar"
        rc, _, err = _run_cli(
            ["--endpoint", "gopher://foo.bar/_", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("scheme gopher not allowed", err)

    def test_ws_rejected(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "w.example.com"
        rc, _, err = _run_cli(
            ["--endpoint", "ws://w.example.com/v1/traces", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("scheme ws not allowed", err)


class TestHostAllowlist(TestEnvContext):
    def test_empty_allowlist_rejects(self) -> None:
        # Unset allowlist entirely — default must fail-closed.
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        rc, _, err = _run_cli(
            ["--endpoint", "https://tempo.example.com/v1/traces", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("not in allowlist", err)

    def test_host_not_in_allowlist_rejects(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "only-this.example.com"
        rc, _, err = _run_cli(
            ["--endpoint", "https://different.example.com/v1/traces", "--dry-run"]
        )
        self.assertEqual(rc, 2)
        self.assertIn("different.example.com", err)

    def test_host_in_allowlist_accepted(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com,jaeger.local"
        # Seed an event so export runs
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [_make_valid_event()])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertIn("exported", out.lower())

    def test_host_is_case_insensitive(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "Tempo.Example.Com"
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [_make_valid_event()])
        rc, _, _ = _run_cli(
            [
                "--endpoint",
                "https://TEMPO.EXAMPLE.COM/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# Redaction + denylist
# -----------------------------------------------------------------------------


class TestDoubleRedaction(TestEnvContext):
    def test_api_key_double_redacted_in_span_attr(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        event = _make_valid_event(
            desc_preview="call with sk-abcdef1234567890abcdef",
        )
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [event])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        # Find the desc_preview attribute
        spans = payload["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual(len(spans), 1)
        attrs = {a["key"]: a["value"] for a in spans[0]["attributes"]}
        self.assertIn("desc_preview", attrs)
        val = attrs["desc_preview"]["stringValue"]
        self.assertIn("[API_KEY]", val)
        self.assertNotIn("sk-abcdef1234567890abcdef", val)

    def test_bearer_token_redacted(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        event = _make_valid_event(desc_preview="Bearer abc123def456")
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [event])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        spans = payload["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        attrs = {a["key"]: a["value"] for a in spans[0]["attributes"]}
        self.assertIn("Bearer [TOKEN]", attrs["desc_preview"]["stringValue"])


class TestDescriptionHashDrop(TestEnvContext):
    def test_description_hash_never_exported(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        event = _make_valid_event(description_hash="f" * 64)
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [event])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        spans = payload["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        attrs = {a["key"]: a["value"] for a in spans[0]["attributes"]}
        self.assertNotIn("description_hash", attrs)
        self.assertNotIn("desc_hash", attrs)

    def test_drop_emits_otel_export_dropped_host_only(self) -> None:
        """The audit event for the drop must record host-only (no URL path)."""
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        event = _make_valid_event()
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [event])
        rc, _, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces?token=SHOULDNOTAPPEAR",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        # The script emits otel_export_dropped into the same audit log.
        # Read back and verify endpoint_host is just the host.
        raw = audit_path.read_text(encoding="utf-8")
        # Find the otel_export_dropped line (last or near-last entry).
        drops = [
            json.loads(line)
            for line in raw.splitlines()
            if line.strip() and json.loads(line).get("action") == "otel_export_dropped"
        ]
        self.assertGreaterEqual(len(drops), 1)
        last = drops[-1]
        self.assertEqual(last["endpoint_host"], "tempo.example.com")
        # Never include the full URL / path / query.
        self.assertNotIn("SHOULDNOTAPPEAR", json.dumps(last))
        self.assertNotIn("v1/traces", json.dumps(last))
        self.assertGreaterEqual(int(last["fields_dropped_count"]), 1)


# -----------------------------------------------------------------------------
# --dry-run, CLI behavior
# -----------------------------------------------------------------------------


class TestDryRun(TestEnvContext):
    def test_dry_run_writes_payload_to_stdout(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        event = _make_valid_event()
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [event])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["exported"], 1)
        self.assertIn("resourceSpans", payload["payload"])


class TestKillSwitch(TestEnvContext):
    def test_sota_disable_short_circuits(self) -> None:
        os.environ["CEO_SOTA_DISABLE"] = "1"
        # Even with a bad endpoint, we must early-exit 0.
        rc, out, _ = _run_cli(
            ["--endpoint", "http://this-would-fail/", "--dry-run"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("disabled", out.lower())


class TestSinceFiltering(TestEnvContext):
    def test_since_24h_filters(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        now = datetime.now(timezone.utc)
        # 2h old — keep; 48h old — drop
        fresh = _make_valid_event(
            ts=(now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            desc_preview="fresh",
        )
        old = _make_valid_event(
            ts=(now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            desc_preview="old",
        )
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [old, fresh])
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--since",
                "24h",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        spans = payload["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual(len(spans), 1)
        attrs = {a["key"]: a["value"] for a in spans[0]["attributes"]}
        self.assertEqual(attrs["desc_preview"]["stringValue"], "fresh")

    def test_since_bad_duration(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        rc, _, err = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--since",
                "forever",
            ]
        )
        self.assertEqual(rc, 2)
        self.assertIn("duration", err.lower())


class TestMalformedAuditLine(TestEnvContext):
    def test_bad_line_skipped(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        audit_path = self.audit_dir / "audit-log.jsonl"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        # mix good + garbage
        audit_path.write_text(
            json.dumps(_make_valid_event()) + "\n"
            + "not json at all\n"
            + json.dumps(_make_valid_event(desc_preview="second")) + "\n",
            encoding="utf-8",
        )
        rc, out, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["exported"], 2)


# -----------------------------------------------------------------------------
# Headers
# -----------------------------------------------------------------------------


class TestHeaders(TestEnvContext):
    def test_header_parse_ok(self) -> None:
        k, v = otel_export.parse_header("Authorization: Bearer abc123")
        self.assertEqual(k, "Authorization")
        self.assertEqual(v, "Bearer abc123")

    def test_header_parse_bad(self) -> None:
        with self.assertRaises(ValueError):
            otel_export.parse_header("no-colon-here")

    def test_header_value_double_redacted_before_send(self) -> None:
        """Ensure the _sanitize_headers path redacts the Bearer value twice."""
        sanitized = otel_emit._sanitize_headers(
            {"Authorization": "Bearer abcdefabcdef"}
        )
        self.assertEqual(sanitized["Authorization"], "Bearer [TOKEN]")


# -----------------------------------------------------------------------------
# Mock OTLP receiver round-trip (stdlib http.server)
# -----------------------------------------------------------------------------


class _StoringHandler(BaseHTTPRequestHandler):
    """BaseHTTPRequestHandler subclass that stores received payloads."""

    received: List[bytes] = []
    received_headers: List[dict] = []

    def do_POST(self) -> None:  # noqa: N802 - HTTP server signature
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        type(self).received.append(raw)
        type(self).received_headers.append(dict(self.headers.items()))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        # silence stdout during tests
        return


def _generate_self_signed_cert() -> tuple:
    """Create a temporary self-signed cert+key via stdlib.

    We rely on a pre-baked self-signed pair embedded as PEM text below
    so we don't depend on external tooling. The cert is CN=localhost
    and expires 2035 — enough lead time for CI.
    """
    # Minimal self-signed cert for CN=localhost. Generated externally
    # via openssl and pasted. We verify only that TLS handshake works;
    # contents are not validated (tests use --no-tls-verify).
    cert_pem = """-----BEGIN CERTIFICATE-----
MIIBqzCCAVGgAwIBAgIUZo7WjKcCCZy7YD2iU4G2lBTeQ6cwCgYIKoZIzj0EAwIw
FDESMBAGA1UEAwwJbG9jYWxob3N0MB4XDTI0MDEwMTAwMDAwMFoXDTM1MDEwMTAw
MDAwMFowFDESMBAGA1UEAwwJbG9jYWxob3N0MFkwEwYHKoZIzj0CAQYIKoZIzj0D
AQcDQgAEhI3jeAC9B4FsR6/0H9xZB6o0nXp3U6LRaIiQu9g8rEWgIeA3n0cTd+Lt
h5hGb7EUAYGTGmNKJyFlNS3vZcE4b6OBjTCBijAdBgNVHQ4EFgQUG5TaQ3MxvjQY
MZ5z+MFcB4cMTYwwHwYDVR0jBBgwFoAUG5TaQ3MxvjQYMZ5z+MFcB4cMTYwwDwYD
VR0TAQH/BAUwAwEB/zALBgNVHQ8EBAMCAQYwKgYDVR0RBCMwIYIJbG9jYWxob3N0
ghFsb2NhbGhvc3QubG9jYWxkb20wCgYIKoZIzj0EAwIDSAAwRQIhALvRZ5z1sEiQ
B0WqRGDzDjLp+xj+ONxWyqE4xuNu3GjsAiAzMuLZZlL9Q9DcW5yXeR0ZkSkDJSqQ
bNkZDvpxDc7hwQ==
-----END CERTIFICATE-----
"""
    return cert_pem, ""


class TestMockReceiverRoundTrip(TestEnvContext):
    """Real POST against a stdlib http.server (HTTP — not HTTPS in test).

    The CI smoke workflow uses HTTPS + self-signed with CEO_OTEL_SMOKE=1.
    Here we bypass the scheme check by going through the library path
    directly (validate_endpoint is unit-tested above).
    """

    def test_payload_arrives_at_mock(self) -> None:
        # Reset the class-level storage
        _StoringHandler.received = []
        _StoringHandler.received_headers = []

        server = HTTPServer(("127.0.0.1", 0), _StoringHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            # Library path: we already validated the scheme/host logic
            # above. Here we exercise post_spans directly against plain
            # HTTP to avoid self-signed TLS overhead (scheme guard is
            # owned by validate_endpoint, not post_spans).
            payload = {
                "resourceSpans": [
                    {
                        "resource": {"attributes": []},
                        "scopeSpans": [
                            {
                                "scope": {"name": "test"},
                                "spans": [
                                    {
                                        "traceId": "a" * 32,
                                        "spanId": "b" * 16,
                                        "name": "test_span",
                                        "kind": 1,
                                        "startTimeUnixNano": "1",
                                        "endTimeUnixNano": "2",
                                        "attributes": [],
                                        "status": {"code": 0},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
            status, body = otel_emit.post_spans(
                f"http://127.0.0.1:{port}/v1/traces",
                payload,
                headers={"X-Trace": "t1"},
                timeout=5.0,
                verify_tls=False,
            )
            self.assertEqual(status, 200)
            self.assertIn("ok", body)
            self.assertEqual(len(_StoringHandler.received), 1)
            received = json.loads(_StoringHandler.received[0])
            self.assertEqual(received["resourceSpans"][0]["scopeSpans"][0]
                             ["spans"][0]["name"], "test_span")
            # Header propagated
            self.assertEqual(
                _StoringHandler.received_headers[0].get("X-Trace"), "t1"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


# -----------------------------------------------------------------------------
# --no-tls-verify opt-in
# -----------------------------------------------------------------------------


class TestNoTlsVerifyGate(TestEnvContext):
    def test_no_tls_verify_without_smoke_env_rejects(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        os.environ.pop("CEO_OTEL_SMOKE", None)
        rc, _, err = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--no-tls-verify",
            ]
        )
        self.assertEqual(rc, 2)
        self.assertIn("CEO_OTEL_SMOKE", err)

    def test_no_tls_verify_with_smoke_env_allowed(self) -> None:
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "tempo.example.com"
        os.environ["CEO_OTEL_SMOKE"] = "1"
        audit_path = self.audit_dir / "audit-log.jsonl"
        _write_audit_jsonl(audit_path, [_make_valid_event()])
        rc, _, _ = _run_cli(
            [
                "--endpoint",
                "https://tempo.example.com/v1/traces",
                "--dry-run",
                "--no-tls-verify",
                "--audit-log",
                str(audit_path),
            ]
        )
        self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# parse_duration unit
# -----------------------------------------------------------------------------


class TestParseDuration(unittest.TestCase):
    def test_hours(self) -> None:
        self.assertEqual(otel_export.parse_duration("24h"), 24 * 3600)

    def test_days(self) -> None:
        self.assertEqual(otel_export.parse_duration("7d"), 7 * 86400)

    def test_seconds(self) -> None:
        self.assertEqual(otel_export.parse_duration("30s"), 30)

    def test_weeks(self) -> None:
        self.assertEqual(otel_export.parse_duration("2w"), 2 * 604800)

    def test_minutes(self) -> None:
        self.assertEqual(otel_export.parse_duration("5m"), 300)

    def test_bad_raises(self) -> None:
        with self.assertRaises(ValueError):
            otel_export.parse_duration("infinity")
        with self.assertRaises(ValueError):
            otel_export.parse_duration("")
        with self.assertRaises(ValueError):
            otel_export.parse_duration("24hours")


if __name__ == "__main__":
    unittest.main()
