#!/usr/bin/env python3
"""otel-export.py — OTLP/HTTP JSON exporter for the audit log.

PLAN-011 Phase 8 (CRITICAL CR3 bundle). Reads
``~/.claude/projects/<project>/audit-log.jsonl`` via
``_lib.audit_emit.iter_events``, maps each event to a single OTEL span,
and POSTs an ``ExportTraceServiceRequest`` (OTLP/HTTP JSON) to a
user-supplied HTTPS endpoint.

## SSRF + secret-exfil defense bundle (CR3)

All checks are mandatory and have no runtime override:

1. **HTTPS-only** — the scheme allowlist rejects ``http://``, ``file://``,
   ``gopher://``, ``ws://``, etc. before DNS resolution.
2. **Host allowlist** — ``CEO_OTEL_ALLOWED_HOSTS`` (comma-separated).
   Empty default ⇒ every endpoint rejected (fail-closed).
3. **Double redaction** — every span attribute value passes through
   ``_lib.redact.redact_secrets`` twice.
4. **Drop ``description_hash``** — never exported (SHA-256 of plaintext
   is externally correlatable).
5. **Audit the drops** — ``otel_export_dropped`` audit event on every
   redaction drop and every host/scheme rejection. Endpoint is recorded
   as host-only (no path, no query).
6. **Global kill-switch** — ``CEO_SOTA_DISABLE=1`` short-circuits to a
   zero-span no-op. Prints "disabled" to stdout, exits 0.

## Exit codes

- 0 — success (or dry-run, or disabled)
- 2 — validation failure (scheme / host / --since / malformed flag)
- 3 — transport failure (POST error)

## Stdlib-only

``urllib.request`` for POST, ``http.server`` in tests for the smoke
receiver. NO ``requests``/``httpx``/``opentelemetry``/``protobuf``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

# Ensure _lib import works whether invoked from repo root or anywhere.
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib import audit_emit as _audit  # noqa: E402
from _lib import otel_emit  # noqa: E402


DEFAULT_SERVICE_NAME = "ceo-orchestration"


# -----------------------------------------------------------------------------
# --since parsing
# -----------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d|w)$", re.IGNORECASE)
_DURATION_UNITS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def parse_duration(raw: str) -> int:
    """Parse a duration string (e.g. ``24h``, ``7d``) to seconds.

    Raises ``ValueError`` on bad input. Used by --since.
    """
    if not raw:
        raise ValueError("empty duration")
    m = _DURATION_RE.match(raw.strip())
    if not m:
        raise ValueError(
            f"bad duration {raw!r} (expected <int><s|m|h|d|w>)"
        )
    amount = int(m.group(1))
    unit = m.group(2).lower()
    return amount * _DURATION_UNITS[unit]


def _event_ts_epoch(event: Mapping[str, Any]) -> Optional[float]:
    ts = event.get("ts")
    if not isinstance(ts, str) or not ts:
        return None
    try:
        iso = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, OverflowError):
        return None


# -----------------------------------------------------------------------------
# Headers parsing (--headers "K: V" repeatable)
# -----------------------------------------------------------------------------


def parse_header(raw: str) -> Tuple[str, str]:
    """Parse ``Key: Value`` into (key, value). Raises ValueError on malformed input."""
    if ":" not in raw:
        raise ValueError(f"bad header {raw!r} (expected 'Key: Value')")
    key, _, value = raw.partition(":")
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValueError(f"bad header {raw!r} (empty key)")
    return key, value


# -----------------------------------------------------------------------------
# Event source
# -----------------------------------------------------------------------------


def _iter_filtered_events(
    source_path: Optional[Path],
    *,
    since_seconds: Optional[int],
) -> Iterable[Dict[str, Any]]:
    """Yield events from the audit log, filtered by --since.

    Malformed lines are skipped silently (iter_events emits breadcrumb).
    """
    cutoff: Optional[float] = None
    if since_seconds is not None and since_seconds > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - since_seconds

    for event in _audit.iter_events(path=source_path):
        if cutoff is not None:
            ts = _event_ts_epoch(event)
            if ts is None or ts < cutoff:
                continue
        yield event


# -----------------------------------------------------------------------------
# CLI wiring
# -----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="otel-export",
        description=(
            "Export audit-log events as OTLP/HTTP JSON traces. "
            "HTTPS-only; CEO_OTEL_ALLOWED_HOSTS enforces allowlist."
        ),
    )
    p.add_argument(
        "--endpoint",
        required=True,
        help=(
            "OTLP/HTTP endpoint (e.g. https://tempo.example.com/v1/traces). "
            "Must be HTTPS; host must appear in CEO_OTEL_ALLOWED_HOSTS."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not POST. Write the OTLP payload JSON to stdout.",
    )
    p.add_argument(
        "--since",
        default=None,
        help="Only export events newer than this duration (e.g. 24h, 7d).",
    )
    p.add_argument(
        "--headers",
        action="append",
        default=[],
        help=(
            "Header to include in POST (repeatable). "
            "Format: --headers 'Authorization: Bearer <token>'. "
            "Values are double-redacted before emission to the request."
        ),
    )
    p.add_argument(
        "--audit-log",
        default=None,
        help="Path to audit-log.jsonl (default: $CEO_AUDIT_LOG_PATH or HOME).",
    )
    p.add_argument(
        "--service-name",
        default=DEFAULT_SERVICE_NAME,
        help=f"OTEL service.name attribute. Default: {DEFAULT_SERVICE_NAME}",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=otel_emit.DEFAULT_POST_TIMEOUT,
        help=f"POST timeout (seconds). Default: {otel_emit.DEFAULT_POST_TIMEOUT}",
    )
    p.add_argument(
        "--no-tls-verify",
        action="store_true",
        help=(
            "Disable TLS verification. ONLY honored when CEO_OTEL_SMOKE=1. "
            "Intended for CI smoke testing against a loopback receiver."
        ),
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — stream audit-log entries to an OTLP collector."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse calls sys.exit(2) on bad args — propagate as "usage".
        code = exc.code if isinstance(exc.code, int) else 2
        return code if code != 0 else 0

    # Global kill-switch first — before any validation I/O.
    if otel_emit.sota_disabled():
        sys.stdout.write("otel-export: disabled (CEO_SOTA_DISABLE=1); 0 spans exported\n")
        return 0

    # --since
    since_seconds: Optional[int] = None
    if args.since is not None:
        try:
            since_seconds = parse_duration(args.since)
        except ValueError as e:
            sys.stderr.write(f"error: {e}\n")
            return 2

    # Parse --headers. Malformed entries abort.
    headers: Dict[str, str] = {}
    for raw in args.headers or []:
        try:
            k, v = parse_header(raw)
        except ValueError as e:
            sys.stderr.write(f"error: {e}\n")
            return 2
        headers[k] = v

    # TLS verify gate.
    verify_tls = True
    if args.no_tls_verify:
        if os.environ.get("CEO_OTEL_SMOKE", "") != "1":
            sys.stderr.write(
                "error: --no-tls-verify requires CEO_OTEL_SMOKE=1 "
                "(smoke-test opt-in only)\n"
            )
            return 2
        verify_tls = False

    # Audit log source
    source_path: Optional[Path] = None
    if args.audit_log:
        source_path = Path(args.audit_log).expanduser()

    events = _iter_filtered_events(source_path, since_seconds=since_seconds)

    # Validate endpoint BEFORE touching the audit log payload. This way
    # a bad endpoint fails fast and never emits spans.
    try:
        otel_emit.validate_endpoint(args.endpoint)
    except otel_emit.OtelExportError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2

    # Run the export.
    try:
        summary = otel_emit.export_events(
            args.endpoint,
            events,
            headers=headers,
            dry_run=bool(args.dry_run),
            timeout=float(args.timeout),
            verify_tls=verify_tls,
        )
    except otel_emit.OtelExportError as e:
        # Validation errors already return early above; this path is
        # reserved for transport failures.
        msg = str(e)
        if msg.startswith("scheme ") or msg.startswith("host "):
            sys.stderr.write(f"error: {msg}\n")
            return 2
        sys.stderr.write(f"error: {msg}\n")
        return 3

    # dry-run writes full OTLP payload to stdout as JSON; real export
    # writes a concise summary line.
    if args.dry_run:
        sys.stdout.write(
            json.dumps(
                {
                    "dry_run": True,
                    "exported": summary.get("exported", 0),
                    "dropped_fields": summary.get("dropped_fields", 0),
                    "endpoint_host": summary.get("endpoint_host", ""),
                    "payload": summary.get("payload", {}),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            "otel-export: "
            f"exported={summary.get('exported', 0)} "
            f"dropped_fields={summary.get('dropped_fields', 0)} "
            f"host={summary.get('endpoint_host', '')} "
            f"status={summary.get('status')}\n"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
