#!/usr/bin/env python3
"""otel-local-sink.py — loopback-only OTLP/HTTP receiver → local JSONL (no egress).

PLAN-135 W5 UNIT o10 ("OTEL opt-in profile / who watches the hooks").

This is the **receive** counterpart to the existing `otel-export.py`
(ADR-035, which *sends* audit-log spans OUT to an allowlisted HTTPS
backend). This script *receives* OTLP/HTTP payloads that Claude Code
itself emits when the Owner opts in via
`templates/settings/settings.stack.otel.json`
(`CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_*` exporter knobs), and writes
each batch to a local JSONL file. It NEVER forwards anything onward.

## Positioning (ADR-087-AMEND-1)

> audit-log.jsonl = tamper-evident truth; OTel = dashboard.

The audit log (HMAC-chained, fail-closed on security checks) remains the
canonical governance record. This sink is the **dashboard / panel** side:
a convenient, queryable mirror of Claude-Code-native telemetry
(`cost.usage` / `token.usage` with `agent.name` / `skill.name`
attribution, and `OTEL_LOGS_EXPORTER` `hook_execution`-class log events
that act as the **independent rail-tamper witness** — "who watches the
hooks"). The two streams are independent: a hook that is silently
disarmed (exec-bit stripped, S228; settings-merge skip, S217) still emits
NO audit-log event, but Claude Code's OTel `hook_execution` log records
the absence — caught by an external diff against the registered-hook set.

## Trust + no-egress invariants (the load-bearing security contract)

1. **Loopback bind ONLY.** The server binds `127.0.0.1` (or `::1`) and
   REFUSES any non-loopback bind host. There is NO flag to bind a public
   interface. A misconfigured `--host 0.0.0.0` exits 2 before any socket
   is opened.
2. **No egress.** This process opens NO outbound socket. It is a pure
   receiver: read request body → append JSONL → 200 OK. It imports no
   client (`urllib.request` is NOT imported); there is no forward path.
3. **Read-only-to-governance.** The JSONL it writes is a *dashboard*
   artifact, NOT an audit-chain input. It is never read by a governance
   hook as a decision input (same trust tier as other local dashboard
   state; cf. PLAN-135 §W5 sidecar residual). If a future consumer ever
   gates a decision on it, that is a new ADR.
4. **Line-protocol-tolerant.** Real OTLP/HTTP posts JSON (`Content-Type:
   application/json`) to `/v1/traces`, `/v1/logs`, `/v1/metrics`. We also
   tolerate `application/x-protobuf` (recorded as an opaque base64 blob —
   we do NOT decode protobuf; stdlib-only, ADR-002) and newline-delimited
   bodies, so a partial/odd exporter never crashes the sink. Anything we
   cannot parse as JSON is stored as `{"_raw_b64": "..."}` so no bytes
   are silently dropped.
5. **Stdlib-only.** `http.server`, `json`, `base64`, `socketserver`.
   NO `opentelemetry`, NO `protobuf`, NO `requests`. ADR-002 compliant.

## Where it writes

Default: `<state-dir>/otel-sink.jsonl`, where `<state-dir>` mirrors the
audit-log resolution (`CEO_AUDIT_LOG_DIR` env → else
`$HOME/.claude/projects/ceo-orchestration`). Override with
`--out PATH`. Each line is one received signal:

    {"recv_ts": "...Z", "signal": "traces|logs|metrics|unknown",
     "path": "/v1/traces", "content_type": "application/json",
     "remote": "127.0.0.1", "payload": {...} | {"_raw_b64": "..."}}

## Usage

    python3 .claude/scripts/otel-local-sink.py            # bind 127.0.0.1:4318
    python3 .claude/scripts/otel-local-sink.py --port 4319
    python3 .claude/scripts/otel-local-sink.py --out /tmp/sink.jsonl
    python3 .claude/scripts/otel-local-sink.py --once      # serve ONE request then exit (CI/tests)

Then point the opt-in stack at it:

    export CLAUDE_CODE_ENABLE_TELEMETRY=1
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
    export OTEL_EXPORTER_OTLP_PROTOCOL=http/json

(See settings.stack.otel.json for the full opt-in env profile.)

## Exit codes

    0  clean shutdown (Ctrl-C, or --once completed, or --self-test pass)
    2  refused / usage error (non-loopback host, bad args, self-test fail)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# The ONLY hosts this sink will ever bind. No public-interface bind path.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# OTLP/HTTP default port (the value Claude Code's OTEL exporter targets
# by convention). Overridable via --port.
_DEFAULT_PORT = 4318

# Max request body we will buffer (defensive cap; OTLP batches are small).
# 16 MiB is generous; oversize → 413 + breadcrumb, never OOM.
_MAX_BODY_BYTES = 16 * 1024 * 1024

# Path → signal classification (OTLP/HTTP standard sub-paths).
_SIGNAL_BY_SUFFIX = {
    "/v1/traces": "traces",
    "/v1/logs": "logs",
    "/v1/metrics": "metrics",
}


# -----------------------------------------------------------------------------
# State-dir resolution (mirrors _lib.audit_emit._audit_dir, dependency-free)
# -----------------------------------------------------------------------------

def _state_dir() -> Path:
    """Return the project state dir (env-overridable; matches audit_emit)."""
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _default_out_path() -> Path:
    return _state_dir() / "otel-sink.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# -----------------------------------------------------------------------------
# Payload parsing (line-protocol-tolerant, never raises)
# -----------------------------------------------------------------------------

def classify_signal(path: str) -> str:
    """Map an OTLP/HTTP request path to a signal name."""
    # Strip query string defensively.
    clean = path.split("?", 1)[0].rstrip("/") or "/"
    for suffix, signal in _SIGNAL_BY_SUFFIX.items():
        if clean == suffix or clean.endswith(suffix):
            return signal
    return "unknown"


def parse_body(body: bytes, content_type: str) -> Any:
    """Parse a request body into a JSON-serializable record.

    Tolerant by design (no exception escapes):
    - ``application/json`` → ``json.loads`` (object/array/scalar).
    - newline-delimited JSON → list of parsed lines (best-effort; a line
      that is not JSON is kept as a raw string element).
    - anything else / unparseable (e.g. ``application/x-protobuf``) →
      ``{"_raw_b64": "<base64>"}`` so no bytes are dropped and we never
      try to decode protobuf (stdlib-only).
    """
    if not body:
        return {}
    ct = (content_type or "").lower()
    if "json" in ct:
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            pass  # fall through to NDJSON / raw
    # Try newline-delimited JSON (some exporters stream).
    text: Optional[str]
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None and "\n" in text:
        parts = [ln for ln in text.split("\n") if ln.strip()]
        if len(parts) > 1:
            out = []
            any_json = False
            for ln in parts:
                try:
                    out.append(json.loads(ln))
                    any_json = True
                except ValueError:
                    out.append(ln)
            if any_json:
                return out
    # Single-line JSON (json content-type missing but body is JSON).
    if text is not None:
        try:
            return json.loads(text)
        except ValueError:
            pass
    # Opaque (protobuf or binary): keep as base64 — never decode, never drop.
    return {"_raw_b64": base64.b64encode(body).decode("ascii")}


def build_record(
    *,
    path: str,
    content_type: str,
    remote: str,
    body: bytes,
) -> Dict[str, Any]:
    """Assemble one JSONL record for a received OTLP signal."""
    return {
        "recv_ts": _utc_now_iso(),
        "signal": classify_signal(path),
        "path": path.split("?", 1)[0],
        "content_type": content_type or "",
        "remote": remote,
        "byte_len": len(body),
        "payload": parse_body(body, content_type),
    }


def append_jsonl(out_path: Path, record: Dict[str, Any]) -> None:
    """Append one record as a JSON line. Best-effort, fail-soft.

    Mkdir-parents on first write. A write failure is swallowed and a
    breadcrumb is written to ``<out>.errors`` — this is a dashboard
    artifact, not a governance input, so a failed append MUST NOT crash
    the receiver (loopback service-loop liveness).
    """
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as err:  # pragma: no cover - exercised via fault injection
        try:
            err_path = out_path.with_suffix(out_path.suffix + ".errors")
            with err_path.open("a", encoding="utf-8") as efh:
                efh.write(f"{_utc_now_iso()} sink-write-failed: {err}\n")
        except OSError:
            pass  # truly nothing we can do; never raise in the service loop


# -----------------------------------------------------------------------------
# Loopback guard
# -----------------------------------------------------------------------------

def assert_loopback(host: str) -> None:
    """Refuse any non-loopback bind host. Raises ValueError on violation."""
    if host not in _LOOPBACK_HOSTS:
        raise ValueError(
            f"refusing to bind non-loopback host {host!r}: "
            f"otel-local-sink is loopback-only (no egress, no public bind). "
            f"Allowed: {sorted(_LOOPBACK_HOSTS)}"
        )


# -----------------------------------------------------------------------------
# HTTP handler
# -----------------------------------------------------------------------------

def make_handler(out_path: Path) -> type:
    """Build a BaseHTTPRequestHandler bound to ``out_path``."""

    class _OtelSinkHandler(BaseHTTPRequestHandler):
        # Quiet: do not spam stderr per request (this is a long-lived loop).
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _read_body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                length = 0
            if length <= 0:
                return b""
            if length > _MAX_BODY_BYTES:
                # Drain + refuse oversize without buffering it all.
                return b""
            return self.rfile.read(length)

        def _refuse_oversize(self) -> bool:
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                return False
            if length > _MAX_BODY_BYTES:
                self.send_response(413)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"payload too large"}')
                return True
            return False

        def do_POST(self) -> None:  # noqa: N802 (http.server convention)
            # Loopback is already enforced at bind time; the handler only
            # ever sees connections to the loopback socket. Belt-and-braces:
            # a non-loopback client_address is dropped without writing.
            remote = (self.client_address[0] if self.client_address else "")
            if remote not in _LOOPBACK_HOSTS and not remote.startswith("127."):
                self.send_response(403)
                self.end_headers()
                return
            if self._refuse_oversize():
                return
            body = self._read_body()
            content_type = self.headers.get("Content-Type", "")
            record = build_record(
                path=self.path,
                content_type=content_type,
                remote=remote,
                body=body,
            )
            append_jsonl(out_path, record)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            # OTLP/HTTP success response is an empty/partial-success JSON.
            self.wfile.write(b"{}")

        def do_GET(self) -> None:  # noqa: N802
            # Health probe: GET / → 200, no body write to JSONL.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","sink":"otel-local-sink"}')

    return _OtelSinkHandler


# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------

def serve(
    host: str,
    port: int,
    out_path: Path,
    *,
    once: bool = False,
) -> Tuple[str, int]:
    """Bind a loopback HTTP server and serve. Returns the bound (host, port).

    ``once=True`` serves exactly one request then returns (CI/test mode).
    Otherwise serves until KeyboardInterrupt.
    """
    assert_loopback(host)
    server = HTTPServer((host, port), make_handler(out_path))
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    try:
        if once:
            server.handle_request()
        else:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return bound_host, int(bound_port)


# -----------------------------------------------------------------------------
# Self-test (hermetic, no network bind needed for the parse/guard paths)
# -----------------------------------------------------------------------------

def _self_test() -> int:
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        if not cond:
            ok = False
            sys.stderr.write(f"SELFTEST FAIL: {label}\n")

    # Loopback guard
    try:
        assert_loopback("0.0.0.0")
        check(False, "0.0.0.0 should be refused")
    except ValueError:
        check(True, "0.0.0.0 refused")
    assert_loopback("127.0.0.1")  # must not raise
    assert_loopback("::1")  # must not raise

    # Signal classification
    check(classify_signal("/v1/traces") == "traces", "traces classify")
    check(classify_signal("/v1/logs?x=1") == "logs", "logs classify w/ query")
    check(classify_signal("/v1/metrics") == "metrics", "metrics classify")
    check(classify_signal("/nope") == "unknown", "unknown classify")

    # JSON parse
    check(parse_body(b'{"a":1}', "application/json") == {"a": 1}, "json parse")
    # NDJSON parse
    nd = parse_body(b'{"a":1}\n{"b":2}\n', "application/x-ndjson")
    check(nd == [{"a": 1}, {"b": 2}], "ndjson parse")
    # Opaque protobuf → base64, never raises, never empty
    rec = parse_body(b"\x00\x01\x02\xff", "application/x-protobuf")
    check(isinstance(rec, dict) and "_raw_b64" in rec, "protobuf → raw_b64")
    check(parse_body(b"", "application/json") == {}, "empty body → {}")

    # Record shape
    r = build_record(path="/v1/traces", content_type="application/json",
                     remote="127.0.0.1", body=b'{"k":"v"}')
    check(r["signal"] == "traces", "record signal")
    check(r["payload"] == {"k": "v"}, "record payload")
    check(r["remote"] == "127.0.0.1", "record remote")

    sys.stderr.write("SELFTEST PASS\n" if ok else "SELFTEST FAIL\n")
    return 0 if ok else 2


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="otel-local-sink.py",
        description=(
            "Loopback-only OTLP/HTTP receiver → local JSONL (no egress). "
            "PLAN-135 W5 O10. audit-log = truth; OTel sink = dashboard."
        ),
    )
    p.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host. LOOPBACK ONLY (127.0.0.1 / ::1 / localhost). "
        "Any other value is refused (exit 2).",
    )
    p.add_argument("--port", type=int, default=_DEFAULT_PORT,
                   help=f"Bind port (default {_DEFAULT_PORT}; 0 = ephemeral).")
    p.add_argument("--out", default=None,
                   help="Output JSONL path (default: <state-dir>/otel-sink.jsonl).")
    p.add_argument("--once", action="store_true",
                   help="Serve exactly ONE request then exit (CI/tests).")
    p.add_argument("--self-test", action="store_true",
                   help="Run hermetic self-test (no socket bind) and exit.")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        assert_loopback(args.host)
    except ValueError as err:
        sys.stderr.write(f"ERROR: {err}\n")
        return 2

    out_path = Path(args.out) if args.out else _default_out_path()

    sys.stderr.write(
        f"otel-local-sink: binding {args.host}:{args.port} "
        f"(loopback-only, no egress) → {out_path}\n"
    )
    try:
        bound_host, bound_port = serve(
            args.host, args.port, out_path, once=args.once
        )
    except OSError as err:
        sys.stderr.write(f"ERROR: bind/serve failed: {err}\n")
        return 2
    sys.stderr.write(f"otel-local-sink: stopped ({bound_host}:{bound_port})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
