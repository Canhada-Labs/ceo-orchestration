"""Tests for otel-local-sink.py — PLAN-135 W5 UNIT o10.

Loopback fixture: binds the sink on an ephemeral 127.0.0.1 port in a
background thread, POSTs OTLP-shaped bodies via stdlib http.client, and
asserts the JSONL artifact. Zero egress, zero spend — the only socket is
a loopback connection to the sink itself.

All tests are hermetic:
- No real `$HOME` touched: --out points at a tmp_path file.
- No network beyond 127.0.0.1.
- No Anthropic / API / Admin / Analytics calls.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import threading
from http.server import HTTPServer
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the script as a module (it lives in .claude/scripts, not a package).
# ---------------------------------------------------------------------------
_SINK_PATH = Path(__file__).resolve().parents[1] / "otel-local-sink.py"
_spec = importlib.util.spec_from_file_location("otel_local_sink", _SINK_PATH)
assert _spec and _spec.loader
sink = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sink)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Loopback fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def loopback_sink(tmp_path):
    """Bind the sink on an ephemeral loopback port; yield (port, out_path).

    Uses the same handler the CLI builds, on port 0 (kernel-assigned),
    served from a daemon thread. Torn down after the test.
    """
    out_path = tmp_path / "otel-sink.jsonl"
    handler = sink.make_handler(out_path)
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, out_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _post(port: int, path: str, body: bytes, content_type: str) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request(
            "POST", path, body=body, headers={"Content-Type": content_type}
        )
        resp = conn.getresponse()
        resp.read()
        return resp.status
    finally:
        conn.close()


def _read_jsonl(out_path: Path):
    return [
        json.loads(ln)
        for ln in out_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


# ---------------------------------------------------------------------------
# Loopback round-trip
# ---------------------------------------------------------------------------
class TestLoopbackRoundTrip:
    def test_post_traces_json_writes_jsonl(self, loopback_sink):
        port, out_path = loopback_sink
        otlp = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "plan.id", "value": {"stringValue": "PLAN-135"}},
                        ]
                    },
                    "scopeSpans": [{"spans": [{"name": "cost.usage"}]}],
                }
            ]
        }
        status = _post(
            port, "/v1/traces", json.dumps(otlp).encode("utf-8"), "application/json"
        )
        assert status == 200
        records = _read_jsonl(out_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["signal"] == "traces"
        assert rec["path"] == "/v1/traces"
        assert rec["remote"].startswith("127.")
        assert rec["payload"] == otlp

    def test_post_logs_records_signal_logs(self, loopback_sink):
        port, out_path = loopback_sink
        # OTEL_LOGS_EXPORTER hook-execution event — the rail-tamper witness.
        body = {
            "resourceLogs": [
                {
                    "scopeLogs": [
                        {
                            "logRecords": [
                                {
                                    "body": {"stringValue": "hook_execution"},
                                    "attributes": [
                                        {
                                            "key": "hook.name",
                                            "value": {"stringValue": "check_canonical_edit"},
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        status = _post(
            port, "/v1/logs", json.dumps(body).encode("utf-8"), "application/json"
        )
        assert status == 200
        records = _read_jsonl(out_path)
        assert records[-1]["signal"] == "logs"

    def test_post_metrics_signal(self, loopback_sink):
        port, out_path = loopback_sink
        status = _post(port, "/v1/metrics", b'{"resourceMetrics":[]}', "application/json")
        assert status == 200
        assert _read_jsonl(out_path)[-1]["signal"] == "metrics"

    def test_multiple_posts_append(self, loopback_sink):
        port, out_path = loopback_sink
        for i in range(3):
            _post(port, "/v1/traces", json.dumps({"i": i}).encode(), "application/json")
        records = _read_jsonl(out_path)
        assert len(records) == 3
        assert [r["payload"]["i"] for r in records] == [0, 1, 2]

    def test_protobuf_body_stored_as_raw_b64_not_dropped(self, loopback_sink):
        port, out_path = loopback_sink
        status = _post(
            port, "/v1/traces", b"\x00\x01\x02\xff\xfe", "application/x-protobuf"
        )
        assert status == 200
        rec = _read_jsonl(out_path)[-1]
        assert "_raw_b64" in rec["payload"]  # never decoded, never dropped

    def test_get_health_does_not_write(self, loopback_sink):
        port, out_path = loopback_sink
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/")
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        assert resp.status == 200
        assert b"ok" in payload
        assert not out_path.exists()  # GET is a health probe, writes nothing


# ---------------------------------------------------------------------------
# Loopback guard — the no-egress / no-public-bind invariant
# ---------------------------------------------------------------------------
class TestLoopbackGuard:
    @pytest.mark.parametrize("bad", ["0.0.0.0", "192.168.1.10", "10.0.0.1", "::"])
    def test_non_loopback_host_refused(self, bad):
        with pytest.raises(ValueError):
            sink.assert_loopback(bad)

    @pytest.mark.parametrize("ok", ["127.0.0.1", "::1", "localhost"])
    def test_loopback_host_allowed(self, ok):
        sink.assert_loopback(ok)  # must not raise

    def test_cli_refuses_public_host_exit_2(self, capsys):
        rc = sink.main(["--host", "0.0.0.0", "--once"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "loopback-only" in err

    def test_no_egress_client_not_imported(self):
        # The sink must NOT import an outbound HTTP client. urllib.request
        # is the egress path the *exporter* uses; the sink must not pull it.
        # Check actual IMPORT statements (the prose mentions the name to
        # explain its absence), not the substring.
        import ast

        tree = ast.parse(_SINK_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module)
        # No outbound HTTP client imported anywhere.
        assert "urllib.request" not in imported
        assert "urllib" not in imported  # urllib.* family
        assert "requests" not in imported
        assert "httpx" not in imported
        assert "socket" not in imported  # raw socket egress
        # http.server (inbound receiver) IS expected.
        assert any(m.startswith("http.server") for m in imported)


# ---------------------------------------------------------------------------
# Parse helpers (pure, no socket)
# ---------------------------------------------------------------------------
class TestParseHelpers:
    def test_classify_signal(self):
        assert sink.classify_signal("/v1/traces") == "traces"
        assert sink.classify_signal("/v1/logs?x=1") == "logs"
        assert sink.classify_signal("/v1/metrics/") == "metrics"
        assert sink.classify_signal("/unknown") == "unknown"

    def test_ndjson_parse(self):
        out = sink.parse_body(b'{"a":1}\n{"b":2}\n', "application/x-ndjson")
        assert out == [{"a": 1}, {"b": 2}]

    def test_empty_body(self):
        assert sink.parse_body(b"", "application/json") == {}

    def test_bad_json_falls_back_to_raw(self):
        rec = sink.parse_body(b"\xff\xfe not json", "application/json")
        assert "_raw_b64" in rec

    def test_state_dir_honors_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
        assert sink._state_dir() == tmp_path
        assert sink._default_out_path() == tmp_path / "otel-sink.jsonl"

    def test_append_jsonl_mkdir_parents(self, tmp_path):
        out = tmp_path / "nested" / "deep" / "otel-sink.jsonl"
        sink.append_jsonl(out, {"recv_ts": "x", "signal": "traces"})
        assert out.exists()
        assert json.loads(out.read_text().strip())["signal"] == "traces"


# ---------------------------------------------------------------------------
# Self-test path
# ---------------------------------------------------------------------------
class TestSelfTest:
    def test_self_test_passes(self):
        assert sink._self_test() == 0

    def test_cli_self_test(self):
        assert sink.main(["--self-test"]) == 0
