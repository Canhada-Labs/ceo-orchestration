"""Thin OTEL gateway for hook-side callers — PLAN-113 Phase C WIRE-OTEL.

Hooks import this single function and call it in one line. Default-OFF:
when ``CEO_OTEL_ENDPOINT`` is absent the call is a strict no-op (False
returned immediately, no singleton created, no thread started).

Usage from any hook::

    from _lib.otel.hook_bridge import maybe_enqueue
    maybe_enqueue({"action": "agent_spawn", "ts": ts, ...})

The call is fire-and-forget. Fail-open per ADR-005: any exception is
swallowed. The audit primary path (audit-log.jsonl) is never affected.

Activation::

    CEO_OTEL_ENDPOINT=https://<host>/v1/traces
    CEO_OTEL_ALLOWED_HOSTS=<host>

Both env vars must be set for spans to actually be exported. The host
allowlist enforces the SSRF defense bundle from otel_emit.py (CR3).

## Stdlib-only

No third-party imports. ADR-126 sidecar boundary is NOT crossed.
Downstream ``otel_emit`` uses ``urllib.request`` (stdlib). ``opentelemetry``
SDK is explicitly NOT imported (documented in otel_emit.py header).
"""

from __future__ import annotations

import os
from typing import Any, Mapping

# Type alias matching BoundedExporter.Span
_Span = Mapping[str, Any]


def maybe_enqueue(span: _Span) -> bool:
    """Enqueue ``span`` for async OTEL export only when endpoint is configured.

    Returns True if span was accepted by the queue; False otherwise
    (including the default-OFF no-endpoint case).

    Never raises — fail-open per ADR-005.
    """
    if not os.environ.get("CEO_OTEL_ENDPOINT", ""):
        return False  # strict no-op — no singleton, no thread, no import side-effect
    try:
        from _lib.otel.bounded_exporter import maybe_enqueue_span
        return maybe_enqueue_span(span)
    except Exception:
        return False
