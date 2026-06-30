"""Typed RAG audit-log emitters (PLAN-041 Phase 5 / ADR-062).

Wraps `_lib.audit_emit.emit_generic` with type-safe signatures for the
5 RAG action types. Bridge code calls these directly (via
`rag_bridge.py::_emit_event`) but callers with richer type information
can import these wrappers for compile-time field validation.

## Action types (snake_case per Round 1 consensus A2)

- `rag_query_issued` — before bridge opens MCP request
- `rag_query_returned` — on successful round-trip
- `rag_query_fallback` — on any failure (sidecar down, timeout, error)
- `rag_query_redacted` — on chunk drop by `_scan_chunks`
- `rag_index_redacted` — indexer drops chunk pre-embed (LLM06)

## Registration dependency

These action types MUST be registered in `_lib.audit_emit._KNOWN_ACTIONS`.
Until the arbitration-kernel batch lands (Owner physical shell), this
module's emit calls silently drop (emit_generic breadcrumbs "unknown
action"). Bridge behavior is unaffected; only the audit trail is
temporarily missing.

Registration command (Owner physical shell):

    cd "$CLAUDE_PROJECT_DIR"
    CEO_KERNEL_OVERRIDE=PLAN-041-AUDIT-ACTIONS \
    CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT \
    python3 -c "
    import os
    from pathlib import Path
    p = Path('.claude/hooks/_lib/audit_emit.py')
    src = p.read_text()
    if '\"rag_query_issued\"' in src:
        print('idempotent, no change')
        raise SystemExit(0)
    anchor = '    \"output_scan_finding\",  # check_output_secrets hook emit on hit\\n'
    insert = (
        '    # PLAN-041 Wave A+ (ADR-062)\\n'
        '    \"rag_query_issued\",\\n'
        '    \"rag_query_returned\",\\n'
        '    \"rag_query_fallback\",\\n'
        '    \"rag_query_redacted\",\\n'
        '    \"rag_index_redacted\",\\n'
    )
    p.write_text(src.replace(anchor, anchor + insert, 1))
    print('applied')
    "

## Fail-open contract

Every emitter catches every exception and returns None. Framework MUST
NOT block on observability.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _project() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or ""


def _emit(action: str, **fields: Any) -> None:
    """Best-effort emit via emit_generic. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is None:
            return
        emitter(action=action, project=_project(), **fields)
    except Exception:
        return


def emit_rag_query_issued(
    *,
    method: str,
    timeout_ms: int,
    session_id: str = "",
    bridge_version: str = "1.0.0",
) -> None:
    """Fires before the bridge opens the MCP socket for a new query."""
    _emit(
        "rag_query_issued",
        method=str(method),
        timeout_ms=int(timeout_ms),
        session_id=str(session_id),
        bridge_version=str(bridge_version),
    )


def emit_rag_query_returned(
    *,
    method: str,
    chunks_returned: int = 0,
    chunks_dropped: int = 0,
    session_id: str = "",
    bridge_version: str = "1.0.0",
) -> None:
    """Fires on successful MCP round-trip (post-scan, pre-caller-return)."""
    _emit(
        "rag_query_returned",
        method=str(method),
        chunks_returned=int(chunks_returned),
        chunks_dropped=int(chunks_dropped),
        session_id=str(session_id),
        bridge_version=str(bridge_version),
    )


def emit_rag_query_fallback(
    *,
    method: str,
    reason: str,
    session_id: str = "",
    bridge_version: str = "1.0.0",
    rpc_error_code: Optional[int] = None,
) -> None:
    """Fires on any failure path: sidecar missing / timeout / parse error / RPC error."""
    fields: Dict[str, Any] = {
        "method": str(method),
        "reason": str(reason),
        "session_id": str(session_id),
        "bridge_version": str(bridge_version),
    }
    if rpc_error_code is not None:
        fields["rpc_error_code"] = int(rpc_error_code)
    _emit("rag_query_fallback", **fields)


def emit_rag_query_redacted(
    *,
    chunk_keys: list,
    family_counts: Dict[str, int],
    session_id: str = "",
    bridge_version: str = "1.0.0",
) -> None:
    """Fires when the bridge drops a retrieved chunk due to LLM01/02/10
    + tag_character / homoglyph injection defense."""
    _emit(
        "rag_query_redacted",
        chunk_keys=list(chunk_keys),
        family_counts={k: int(v) for k, v in (family_counts or {}).items()},
        session_id=str(session_id),
        bridge_version=str(bridge_version),
    )


def emit_rag_index_redacted(
    *,
    file_path: str,
    reason: str,
    family_counts: Optional[Dict[str, int]] = None,
    indexer_version: str = "1.0.0",
) -> None:
    """Fires when the indexer drops a chunk pre-embed due to LLM06 secret shape."""
    _emit(
        "rag_index_redacted",
        file_path=str(file_path),
        reason=str(reason),
        family_counts={k: int(v) for k, v in (family_counts or {}).items()},
        indexer_version=str(indexer_version),
    )
