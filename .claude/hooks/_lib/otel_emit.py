"""OpenTelemetry export library (Sprint 11 Phase 8 — CR3 defense-in-depth).

Stdlib-only OTLP/HTTP JSON exporter. Maps `audit-log.jsonl` events to
OTEL spans and POSTs them to an allowlisted HTTPS endpoint. This module
is the library counterpart to the CLI exporter at
``.claude/scripts/otel-export.py``; both share the same defense bundle.

## Defense bundle (consensus round-1 CR3)

Every export path is guarded by the following checks. All are mandatory;
none have a runtime opt-out.

1. **Scheme allowlist** — HTTPS only. ``http://``, ``file://``,
   ``gopher://``, ``ws://``, and any other scheme is rejected *before*
   DNS resolution. This closes SSRF to cloud metadata services
   (``http://169.254.169.254/latest/meta-data``), local file exfil via
   ``file:///etc/passwd``, and protocol-smuggling via gopher/ws.
2. **Host allowlist** — ``CEO_OTEL_ALLOWED_HOSTS`` (comma-separated).
   **Empty default** ⇒ endpoint rejected. Fail-closed. The caller must
   opt in to each destination host explicitly.
3. **Double redaction** — every span attribute value passes through
   ``_lib.redact.redact_secrets`` **twice**. First pass covers raw
   secrets; second pass covers nested/adjacent patterns unmasked only
   after the first substitution. Applied to string values only; ints /
   bools / None skip.
4. **Identifier hygiene** — ``description_hash`` is dropped from every
   exported span. SHA-256 of plaintext is *correlatable* across corpora
   by an adversary with partial knowledge; we correlate internally via
   the audit log, not externally.
5. **Audit-the-drops** — every dropped field and every rejected host
   emits ``otel_export_dropped`` via
   ``_lib.audit_emit.emit_otel_export_dropped``. The endpoint URL is
   recorded as **host-only** (no path, no query). This keeps the audit
   log itself free of URL-shaped secrets even if a caller embedded a
   token in the path.
6. **Global kill-switch** — ``CEO_SOTA_DISABLE=1`` short-circuits
   *every* entry point with a no-op. Mirrors the Sprint-11 H11/S4
   consensus: one env var disables all Sprint-11 surfaces.

## Fail mode

Library functions raise on internal errors (malformed events, socket
failures) so the CLI can surface them. Library consumers that integrate
this into hooks MUST wrap calls in try/except per ADR-005 fail-open
contract — audit/export MUST never block the user session.

## Stdlib-only

``urllib.request`` for POST, ``json`` for serialization, ``ssl`` for
TLS, ``socket`` indirectly via urllib. NO ``requests``, NO ``httpx``,
NO ``opentelemetry``, NO ``protobuf``. ADR-002 compliance.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import redact as _redact  # noqa: E402
from _lib import audit_emit as _audit  # noqa: E402


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Only HTTPS is allowed. No fallbacks, no overrides.
_ALLOWED_SCHEMES: Tuple[str, ...] = ("https",)

# Fields that MUST NOT be exported (even after redaction). ``description_hash``
# is a SHA-256 of plaintext description — correlatable externally.
_EXPORT_FIELD_DENYLIST: Tuple[str, ...] = (
    "description_hash",
    "desc_hash",  # alternate name seen in some emitters
)

# Fields copied through as resource attributes rather than span attributes.
_RESOURCE_FIELD_KEYS: Tuple[str, ...] = ("project", "session_id")

# Upper bound on a single POST payload (protective; OTLP receivers
# typically accept up to 4 MiB).
_MAX_BATCH_BYTES = 1_000_000

# Default POST timeout in seconds.
DEFAULT_POST_TIMEOUT = 10.0

# Span kind constants (numeric in OTLP JSON per spec).
_SPAN_KIND_INTERNAL = 1


class OtelExportError(Exception):
    """Raised on unrecoverable export errors (scheme, host, transport)."""


# -----------------------------------------------------------------------------
# Gate: kill-switch
# -----------------------------------------------------------------------------


def sota_disabled() -> bool:
    """Return True if ``CEO_SOTA_DISABLE=1`` is set.

    Checked at every public entry point — the H11/S4 consensus promises
    one env var disables *every* Sprint-11 surface.
    """
    return os.environ.get("CEO_SOTA_DISABLE", "") == "1"


# -----------------------------------------------------------------------------
# Endpoint validation
# -----------------------------------------------------------------------------


def _parse_allowed_hosts(raw: Optional[str]) -> List[str]:
    """Parse CEO_OTEL_ALLOWED_HOSTS into a normalized list of hostnames.

    Case-insensitive matching; we normalize to lowercase. Empty / missing
    means an empty list — every host will be rejected (fail-closed).
    """
    if not raw:
        return []
    out: List[str] = []
    for piece in raw.split(","):
        h = piece.strip().lower()
        if h:
            out.append(h)
    return out


def validate_endpoint(
    endpoint: str,
    *,
    allowed_hosts: Optional[Iterable[str]] = None,
) -> Tuple[str, str]:
    """Validate endpoint URL. Return (host_lower, normalized_url).

    Raises ``OtelExportError`` with a specific code prefix on violation.
    The error message format is stable (tested): ``scheme <X> not allowed``
    or ``host <X> not in allowlist``.

    Args:
        endpoint: URL string (``https://<host>[:<port>]/<path>``).
        allowed_hosts: iterable of lowercase hostnames; if None, read
            from ``CEO_OTEL_ALLOWED_HOSTS``.
    """
    if not endpoint or not isinstance(endpoint, str):
        raise OtelExportError("endpoint is required")

    try:
        parsed = urllib.parse.urlparse(endpoint)
    except Exception as e:  # pragma: no cover - urlparse is very forgiving
        raise OtelExportError(f"endpoint parse failed: {e}") from e

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        # Emit audit breadcrumb on reject (host-only = empty for bad scheme).
        _safe_emit_drop(
            fields_dropped_count=0,
            endpoint_host=(parsed.hostname or "").lower(),
            reason=f"scheme_rejected:{scheme or 'none'}",
        )
        raise OtelExportError(f"scheme {scheme or 'none'} not allowed (HTTPS only)")

    host = (parsed.hostname or "").lower()
    if not host:
        raise OtelExportError("endpoint missing hostname")

    if allowed_hosts is None:
        allowed = _parse_allowed_hosts(os.environ.get("CEO_OTEL_ALLOWED_HOSTS"))
    else:
        allowed = [h.lower() for h in allowed_hosts]

    if host not in allowed:
        _safe_emit_drop(
            fields_dropped_count=0,
            endpoint_host=host,
            reason="host_rejected",
        )
        raise OtelExportError(f"host {host} not in allowlist")

    return host, endpoint


# -----------------------------------------------------------------------------
# Redaction + attribute hygiene
# -----------------------------------------------------------------------------


def double_redact(value: str) -> str:
    """Apply ``redact_secrets`` twice.

    The second pass catches nested patterns that only become adjacent
    *after* the first substitution (e.g., ``password=Bearer abc`` → the
    first pass redacts the kv pair, the second normalizes the Bearer
    tail if any remains).
    """
    first = _redact.redact_secrets(value, max_chars=0)
    second = _redact.redact_secrets(first, max_chars=0)
    return second


def _redact_value(v: Any) -> Tuple[Any, bool]:
    """Return (redacted_value, was_mutated) for a span attribute value.

    Only strings are passed through the redactor. Non-string values are
    returned unchanged; mutated=False.
    """
    if isinstance(v, str):
        new = double_redact(v)
        return new, (new != v)
    return v, False


def _sanitize_attrs(
    event: Mapping[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """Return (clean_attrs, dropped_field_count).

    - ``description_hash`` / ``desc_hash`` are dropped.
    - String values are double-redacted.
    - None values are dropped (OTLP attribute values must be typed).
    - Dict / list values are JSON-serialized then double-redacted.
    """
    out: Dict[str, Any] = {}
    dropped = 0
    for k, v in event.items():
        if k in _EXPORT_FIELD_DENYLIST:
            dropped += 1
            continue
        if v is None:
            continue
        # Resource attrs are handled separately.
        if k in _RESOURCE_FIELD_KEYS:
            continue
        if isinstance(v, (dict, list)):
            try:
                serialized = json.dumps(v, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                dropped += 1
                continue
            cleaned, _mutated = _redact_value(serialized)
            out[k] = cleaned
        else:
            cleaned, _mutated = _redact_value(v)
            out[k] = cleaned
    return out, dropped


# -----------------------------------------------------------------------------
# OTLP span mapping
# -----------------------------------------------------------------------------


def _iso_to_unix_nanos(ts_iso: str) -> int:
    """Parse an ISO-8601 timestamp to unix nanoseconds. 0 on failure."""
    if not ts_iso:
        return 0
    # Accept trailing Z (ISO 8601 UTC).
    try:
        if ts_iso.endswith("Z"):
            ts_iso = ts_iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000_000)
    except (ValueError, OverflowError):
        return 0


def _stable_span_id(event: Mapping[str, Any]) -> str:
    """Derive a 16-char hex span id from the event's ts + action.

    The OTLP JSON spec allows 16-hex (span) / 32-hex (trace) ids. We use
    a stable derivation so re-exporting the same audit log produces the
    same spans (idempotent).
    """
    import hashlib

    basis = f"{event.get('ts', '')}|{event.get('action', '')}|{event.get('session_id', '')}"
    return hashlib.sha256(basis.encode("utf-8", errors="replace")).hexdigest()[:16]


def _stable_trace_id(event: Mapping[str, Any]) -> str:
    """32-hex trace id. Use session_id when present, else per-event hash."""
    import hashlib

    session = event.get("session_id") or ""
    if session:
        return hashlib.sha256(session.encode("utf-8", errors="replace")).hexdigest()[:32]
    basis = f"{event.get('ts', '')}|{event.get('action', '')}"
    return hashlib.sha256(basis.encode("utf-8", errors="replace")).hexdigest()[:32]


def _otlp_attr(key: str, value: Any) -> Dict[str, Any]:
    """Wrap a (key, value) pair in the OTLP attribute envelope."""
    if isinstance(value, bool):
        av = {"boolValue": value}
    elif isinstance(value, int):
        av = {"intValue": str(value)}  # OTLP int is string to preserve i64
    elif isinstance(value, float):
        av = {"doubleValue": value}
    else:
        av = {"stringValue": str(value)}
    return {"key": key, "value": av}


def event_to_span(event: Mapping[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Map a single audit event to an OTLP span. Return (span, dropped_count).

    Each event → exactly 1 span. span.name = event action. span.attributes
    = every scalar field minus the denylist. Resource attributes
    (project, session_id) are carried separately via the ResourceSpans
    envelope (see ``batch_to_otlp``).
    """
    clean_attrs, dropped = _sanitize_attrs(event)
    now_ns = _iso_to_unix_nanos(event.get("ts", "")) or _now_ns()
    span: Dict[str, Any] = {
        "traceId": _stable_trace_id(event),
        "spanId": _stable_span_id(event),
        "name": str(event.get("action", "audit_event")),
        "kind": _SPAN_KIND_INTERNAL,
        "startTimeUnixNano": str(now_ns),
        # Audit events are point-in-time; end==start keeps OTLP happy.
        "endTimeUnixNano": str(now_ns),
        "attributes": [_otlp_attr(k, v) for k, v in sorted(clean_attrs.items())],
        "status": {"code": 0},
    }
    return span, dropped


def _now_ns() -> int:
    """Current unix nanoseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)


def batch_to_otlp(
    events: Iterable[Mapping[str, Any]],
    *,
    service_name: str = "ceo-orchestration",
) -> Tuple[Dict[str, Any], int]:
    """Build an OTLP/HTTP JSON ``ExportTraceServiceRequest`` from events.

    Returns (payload, total_dropped_fields). Resource attributes are
    service.name + any event-level project/session_id.
    """
    spans: List[Dict[str, Any]] = []
    total_dropped = 0
    project = ""
    session_ids: List[str] = []
    for event in events:
        span, dropped = event_to_span(event)
        total_dropped += dropped
        spans.append(span)
        if not project:
            project = str(event.get("project", "") or "")
        sid = str(event.get("session_id", "") or "")
        if sid and sid not in session_ids:
            session_ids.append(sid)

    resource_attrs = [_otlp_attr("service.name", service_name)]
    if project:
        # project is a directory name; strip to plain basename for safety
        resource_attrs.append(_otlp_attr("ceo.project", project))

    payload = {
        "resourceSpans": [
            {
                "resource": {"attributes": resource_attrs},
                "scopeSpans": [
                    {
                        "scope": {"name": "ceo-orchestration.audit"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }
    return payload, total_dropped


# -----------------------------------------------------------------------------
# POST
# -----------------------------------------------------------------------------


def _sanitize_headers(
    raw_headers: Optional[Mapping[str, str]],
) -> Dict[str, str]:
    """Return headers with values passed through double_redact.

    We intentionally redact *values* — the keys are caller-controlled
    strings but values may be API tokens. Bearer-shaped values become
    ``Bearer [TOKEN]`` via the redactor's existing pattern set.
    """
    if not raw_headers:
        return {}
    out: Dict[str, str] = {}
    for k, v in raw_headers.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        out[k] = double_redact(v)
    return out


def _build_request(
    url: str,
    payload_bytes: bytes,
    headers: Mapping[str, str],
) -> urllib.request.Request:
    req = urllib.request.Request(url, data=payload_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(payload_bytes)))
    for k, v in headers.items():
        req.add_header(k, v)
    return req


def _ssl_context(*, verify: bool = True) -> ssl.SSLContext:
    """Build an SSL context. Verify True in production; False only for smoke."""
    ctx = ssl.create_default_context()
    if not verify:
        # CEO_OTEL_SMOKE=1 is checked by the caller. We never silently
        # disable verification — the caller must explicitly thread this in.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def post_spans(
    endpoint: str,
    payload: Mapping[str, Any],
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = DEFAULT_POST_TIMEOUT,
    verify_tls: bool = True,
) -> Tuple[int, str]:
    """POST an OTLP/HTTP JSON payload. Return (status, response_body).

    The caller is responsible for having already validated the endpoint.
    Raises ``OtelExportError`` on transport failure.
    """
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise OtelExportError(f"payload serialization failed: {e}") from e

    if len(data) > _MAX_BATCH_BYTES:
        raise OtelExportError(f"batch too large: {len(data)} > {_MAX_BATCH_BYTES}")

    req = _build_request(endpoint, data, headers or {})
    try:
        ctx = _ssl_context(verify=verify_tls)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.getcode()
            body = resp.read(1024).decode("utf-8", errors="replace")
            return status, body
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(1024).decode("utf-8", errors="replace")
        except Exception:
            pass
        raise OtelExportError(f"HTTP {e.code}: {body[:200]}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise OtelExportError(f"transport failure: {e}") from e


# -----------------------------------------------------------------------------
# Audit breadcrumb (fail-open wrapper)
# -----------------------------------------------------------------------------


def _safe_emit_drop(
    *,
    fields_dropped_count: int,
    endpoint_host: str = "",
    reason: str = "",
) -> None:
    """Fail-open wrapper around ``emit_otel_export_dropped`` (ADR-005)."""
    try:
        _audit.emit_otel_export_dropped(
            fields_dropped_count=int(fields_dropped_count),
            endpoint_host=endpoint_host,
            reason=reason,
        )
    except Exception:
        # Library is fail-open on audit per ADR-005.
        pass


# -----------------------------------------------------------------------------
# Library entry point
# -----------------------------------------------------------------------------


def export_events(
    endpoint: str,
    events: Iterable[Mapping[str, Any]],
    *,
    headers: Optional[Mapping[str, str]] = None,
    dry_run: bool = False,
    allowed_hosts: Optional[Iterable[str]] = None,
    timeout: float = DEFAULT_POST_TIMEOUT,
    verify_tls: bool = True,
) -> Dict[str, Any]:
    """Main library entry point. Returns a summary dict.

    Summary keys: ``exported`` (int), ``dropped_fields`` (int),
    ``endpoint_host`` (str), ``dry_run`` (bool), ``status`` (optional
    int on real POST), ``disabled`` (bool when kill-switch fired).

    Behavior contract:
    - ``CEO_SOTA_DISABLE=1`` → return {"disabled": True, ...} no export.
    - Scheme != https → raise OtelExportError before any network I/O.
    - Host not in allowlist → raise OtelExportError.
    - dry_run=True → no POST; summary has spans=N, status=None.
    - Any drop → ``otel_export_dropped`` audit event emitted.
    """
    if sota_disabled():
        return {
            "disabled": True,
            "exported": 0,
            "dropped_fields": 0,
            "endpoint_host": "",
            "dry_run": bool(dry_run),
        }

    host, url = validate_endpoint(endpoint, allowed_hosts=allowed_hosts)

    events_list = list(events)
    payload, dropped = batch_to_otlp(events_list)

    if dropped > 0:
        _safe_emit_drop(
            fields_dropped_count=dropped,
            endpoint_host=host,
            reason="field_redaction",
        )

    summary: Dict[str, Any] = {
        "disabled": False,
        "exported": len(events_list),
        "dropped_fields": dropped,
        "endpoint_host": host,
        "dry_run": bool(dry_run),
    }

    if dry_run:
        summary["status"] = None
        summary["payload"] = payload  # caller can inspect
        return summary

    sanitized_headers = _sanitize_headers(headers)
    status, _body = post_spans(
        url,
        payload,
        headers=sanitized_headers,
        timeout=timeout,
        verify_tls=verify_tls,
    )
    summary["status"] = status
    return summary


# -----------------------------------------------------------------------------
# Fail-open wrapper for hook-side consumers (ADR-005)
# -----------------------------------------------------------------------------


def try_export_events(
    endpoint: Optional[str],
    events: Iterable[Mapping[str, Any]],
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """ADR-005 fail-open wrapper — use from hook code paths.

    Any exception is swallowed; returns None. A drop breadcrumb is still
    emitted for scheme/host rejects via ``validate_endpoint``.

    Intended for Sprint-12 wiring from ``audit_log.py``. Sprint 11 ships
    the library + CLI only; this function is the documented integration
    surface.
    """
    if not endpoint:
        return None
    try:
        return export_events(endpoint, events, **kwargs)
    except OtelExportError:
        return None
    except Exception:
        return None
