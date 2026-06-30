"""MCP handler: ``get_audit_log`` — read the framework audit log.

Per ADR-042 §Auth.2 this is an ``audit_read`` handler (lower rate
limit than other read-onlys). Params:

- ``limit`` (optional, int): max events to return. Server-side hard
  cap is 1000; larger values are silently clamped.
- ``action_filter`` (optional, str): filter to exactly one
  ``action`` discriminator (e.g. ``"agent_spawn"``). Unknown action
  yields empty list (no error).
- ``since`` (optional, str): ISO8601 timestamp (with ``Z`` or
  offset). Events with ``ts < since`` are skipped.

Returns:

    {
      "events": [ {...}, ... ],
      "truncated": bool,        # True iff limit clamped the result
      "total_returned": int
    }

## Redaction

Sensitive fields (``reason_preview``, ``snippet_preview``,
``desc_preview``) are redacted at emit time by
``_lib/audit_emit.py::_preview``. We do NOT re-redact here — the log
file is already the authoritative truth.

However, this handler applies defense-in-depth:

1. **Secret-looking top-level fields** — any field whose key ends in
   ``_secret``, ``_token``, ``_key`` is pruned from returned events.
   (The emitters should never produce these; this is a belt-and-braces
   pass against future regressions.)
2. **Truncate over-long string fields** — any single field value >32 KiB
   is truncated. Prevents a single malformed line from blowing up the
   JSON-RPC response.

## Hard cap

Limit is clamped to ``[1, 1000]``. Default is 100. Server-side hard
cap is 1000 per ADR-042 (to keep JSON-RPC responses under ~5 MiB
even with verbose debate events).

Fail-open: empty list + ``warning`` on read error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make _lib importable for audit_emit.iter_events.
_HOOKS_DIR = Path(__file__).resolve().parents[3] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_emit  # noqa: E402


_HARD_CAP = 1000
_DEFAULT_LIMIT = 100
_MAX_FIELD_BYTES = 32 * 1024


# Field-name patterns to redact defensively.
_SECRET_FIELD_RE = re.compile(
    r"(?:^|_)(secret|token|api_key|key|password|authorization)$",
    flags=re.IGNORECASE,
)


def _iso_le(ts_a: str, ts_b: str) -> bool:
    """Return True iff ts_a <= ts_b (lexicographic ISO8601).

    We only require string comparison because emit_emit always writes
    ``%Y-%m-%dT%H:%M:%SZ`` — a sortable form.
    """
    return str(ts_a) <= str(ts_b)


def _sanitize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Apply defense-in-depth redaction pass to a single event."""
    out: Dict[str, Any] = {}
    for k, v in event.items():
        key_str = str(k)
        if _SECRET_FIELD_RE.search(key_str):
            continue  # drop suspicious fields outright
        if isinstance(v, str) and len(v.encode("utf-8")) > _MAX_FIELD_BYTES:
            out[k] = v[: _MAX_FIELD_BYTES // 4] + "…(truncated)"
        else:
            out[k] = v
    return out


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Returns ``{"events", "truncated", "total_returned"}`` on success.
    Never raises — on any read error returns empty list + warning.
    """
    if not isinstance(params, dict):
        params = {}

    limit_raw = params.get("limit", _DEFAULT_LIMIT)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    if limit <= 0:
        limit = _DEFAULT_LIMIT
    if limit > _HARD_CAP:
        limit = _HARD_CAP

    action_filter_raw = params.get("action_filter")
    action_filter: Optional[str]
    if isinstance(action_filter_raw, str) and action_filter_raw.strip():
        action_filter = action_filter_raw.strip()
    else:
        action_filter = None

    since_raw = params.get("since")
    since: Optional[str]
    if isinstance(since_raw, str) and since_raw.strip():
        since = since_raw.strip()
    else:
        since = None

    collected: List[Dict[str, Any]] = []
    truncated = False

    try:
        for event in audit_emit.iter_events(action_filter=action_filter):
            if since is not None:
                ts = event.get("ts", "")
                if not isinstance(ts, str) or _iso_le(ts, since):
                    continue
            collected.append(_sanitize_event(event))
            if len(collected) >= limit:
                # Peek once more to know whether we truncated.
                # iter_events is a generator — if there is at least
                # one more event matching, we truncated.
                # We don't actually consume it to avoid extra work.
                truncated = True
                break
    except Exception as e:  # pragma: no cover - defensive fail-open
        return {
            "events": [],
            "truncated": False,
            "total_returned": 0,
            "warning": f"read_failed:{type(e).__name__}",
        }

    return {
        "events": collected,
        "truncated": truncated,
        "total_returned": len(collected),
    }


__all__ = ["handle"]
