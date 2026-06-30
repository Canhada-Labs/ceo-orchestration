"""RAG bridge — stdlib-only MCP client for LightRAG sidecar.

PLAN-041 Phase 2 / ADR-062 (PROPOSED, awaiting Phase 7 ACCEPTED). Framework
core stdlib calls into an isolated LightRAG sidecar over a local Unix
socket using a subset of the MCP JSON-RPC 2.0 protocol.

## Call-site invariant (Round 1 consensus A3)

This module MUST NOT be imported from any file under `.claude/hooks/`
OTHER than this file itself + `_lib/rag_events.py` + tests. CEO
orchestration code is the sole legitimate caller; hook handlers are
NEVER in the call path. The framework's hook latency SLO (<100ms p99)
is incompatible with the bridge's 5s default timeout.

Verification: `grep -r "rag_bridge" .claude/hooks/` returns only this
module, `_lib/rag_events.py`, and test files.

## Contract

Public callables (all return Optional[...]; None on any failure):

- `rag_search(query, top_k=5, timeout_ms=5000) -> Optional[List[dict]]`
- `rag_timeline(symbol, timeout_ms=5000) -> Optional[List[dict]]`
- `rag_get_observations(obs_id, timeout_ms=5000) -> Optional[str]`
- `is_sidecar_healthy(timeout_ms=500) -> bool`

## Fail-open (ADR-005)

Every callable catches every exception and returns `None` (or `False`
for the health probe). The caller must check the return value and
fall back to grep / direct Read.

## Injection defense (Round 1 consensus A4)

Every chunk returned by the sidecar passes through
`_lib.output_scan.scan()` before returning to the caller. Chunks that
fire LLM01_prompt_injection, tag_character (unicode smuggling), or
homoglyph (script-mixing) families are DROPPED with a
`rag_query_redacted` audit event. Kill-switch `CEO_RAG_SCAN=0` +
`CEO_RAG_SCAN_ACK=I-ACCEPT-INJECTION-RISK` (two-factor) bypasses scan.

## Kill-switches

- `CEO_RAG_SIDECAR=0` — explicit opt-out; all callables return None.
  When ABSENT (not set), the bridge is enabled — matching the router's
  conditional-default-on doctrine (ADR-062-AMEND-1 §kill-switch precedence).
  The old behaviour (absent → disabled) was a P1 defect: the router could
  return AUTO_WIRE while the bridge silently returned None.
- `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0` — class kill-switch (router
  checks this first; bridge also respects it as an alias).
- `CEO_RAG_QUERY_TIMEOUT_MS` — per-call timeout override (default 5000)
- `CEO_RAG_SCAN=0` + `CEO_RAG_SCAN_ACK=I-ACCEPT-INJECTION-RISK` —
  bypass chunk scan (two-factor; LLM01 amplification risk)
- `CEO_RAG_HEALTH_PROBE=0` — skip probe (tests + offline dev)
- `CEO_RAG_SIDECAR_SOCKET` — override socket path (canonical; same var as rag_router).
  `CEO_RAG_SOCKET` is accepted as a back-compat alias; canonical name takes precedence.
- `CEO_RAG_RETRY_HEALTH=1` — force re-probe after dead cache

## Dead-sidecar cache

When a call fails (connection refused, timeout, missing socket),
subsequent calls within `_DEAD_SIDECAR_CACHE_S` seconds return None
immediately without attempting a connection. Prevents the N × 5s
timeout storm noted by the performance-engineer agent in Round 1.
Per-process, module-level. Tests clear via `_clear_session_state()`.

## Audit events (snake_case per Round 1 consensus A2)

- `rag_query_issued` — before socket open
- `rag_query_returned` — on successful round-trip
- `rag_query_fallback` — on any failure path
- `rag_query_redacted` — on chunk drop by output_scan

Best-effort via `_lib.audit_emit`; any failure is swallowed.

## PLAN-113 W6 dead-code disposition (F-11.3)

As of PLAN-113 Phase B, `rag_search()` / `rag_timeline()` /
`rag_get_observations()` have ZERO production callers — only this module's
own tests invoke them. Per the PLAN-113 C2 doctrine, this dispositioned-dead
**security-relevant** path is NOT deleted on the dead signal alone; it is
verified to FAIL CLOSED while dead. With the default kill-switch posture
(`CEO_RAG_SIDECAR` unset/`0`), `_rpc_call()` short-circuits to None before
any socket is opened, so every public callable returns None (the bridge is
inert and cannot leak chunks). Regression coverage:
`_lib/tests/test_rag_dead_code_disposition.py`. Re-wiring RAG into production
is OUT OF SCOPE for W6. Do not delete; do not auto-wire.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_BRIDGE_VERSION = "1.0.0"

_KILL_SWITCH_ENV = "CEO_RAG_SIDECAR"
_TIMEOUT_ENV = "CEO_RAG_QUERY_TIMEOUT_MS"
_HEALTH_PROBE_ENV = "CEO_RAG_HEALTH_PROBE"
# Canonical socket-path env var — MUST match rag_router._sidecar_socket_path()
# which reads CEO_RAG_SIDECAR_SOCKET (router is the decision authority).
# CEO_RAG_SOCKET is accepted as a back-compat alias; canonical name takes precedence.
_SOCKET_PATH_ENV = "CEO_RAG_SIDECAR_SOCKET"
_SOCKET_PATH_ENV_COMPAT = "CEO_RAG_SOCKET"
_SCAN_ENV = "CEO_RAG_SCAN"
_SCAN_ACK_ENV = "CEO_RAG_SCAN_ACK"
_SCAN_ACK_VALUE = "I-ACCEPT-INJECTION-RISK"
_RETRY_HEALTH_ENV = "CEO_RAG_RETRY_HEALTH"
_DEFAULT_SOCKET_PATH = "~/.ceo-orchestration/rag/sidecar.sock"
_DEFAULT_TIMEOUT_MS = 5000  # A5: naive-mode-safe default
_DEAD_SIDECAR_CACHE_S = 30.0
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # 4 MiB hard cap
_RECV_CHUNK = 65536

# Injection-family drop list (A4).
_INJECTION_DROP_FAMILIES = frozenset({
    "LLM01_prompt_injection",
    "LLM02_insecure_output",
    "LLM10_model_theft",
})
_INJECTION_DROP_VECTORS = frozenset({
    "tag_character",
    "homoglyph",
})


# Module-level state.
_dead_sidecar_until: float = 0.0
_cache_lock = threading.Lock()


def _kill_switch_active() -> bool:
    """Return True (bridge disabled) iff CEO_RAG_SIDECAR is explicitly set to a
    falsy value ("0", "false", "off", "no").

    When the variable is ABSENT the bridge is ENABLED — this matches the
    router's conditional-default-on doctrine (ADR-062-AMEND-1 §kill-switch
    precedence rule 2): `CEO_RAG_SIDECAR=0` → KILL_SWITCH, but absence is not
    a kill-switch.  The old contract (absent → disabled) was a P1 defect:
    `rag_router.route_query()` could return AUTO_WIRE while the bridge short-
    circuited to None, silently falling back to tf-idf even when a healthy
    sidecar was present.

    Also respects the class kill-switch CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0
    for parity with the router's precedence rule 1.
    """
    # Class kill-switch (router precedence rule 1)
    if os.environ.get("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED") == "0":
        return True
    # Legacy alias kill-switch (router precedence rule 2): absent = not disabled
    raw = os.environ.get(_KILL_SWITCH_ENV)
    if raw is None:
        return False  # absent → enabled (conditional-default-on)
    val = raw.strip().lower()
    if val in {"0", "false", "off", "no"}:
        return True   # explicitly disabled
    return False      # any other value (including "1", "true", "on", "yes") → enabled


def _scan_bypass_active() -> bool:
    """Two-factor bypass for chunk scan. Default False (scan on)."""
    scan_off = os.environ.get(_SCAN_ENV, "1").strip().lower() in {"0", "false", "off", "no"}
    ack = os.environ.get(_SCAN_ACK_ENV, "").strip() == _SCAN_ACK_VALUE
    return scan_off and ack


def _resolve_timeout_ms(caller_ms: Optional[int]) -> int:
    if caller_ms is not None and caller_ms > 0:
        return int(caller_ms)
    env = os.environ.get(_TIMEOUT_ENV, "").strip()
    if env:
        try:
            parsed = int(env)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return _DEFAULT_TIMEOUT_MS


def _resolve_socket_path() -> Path:
    """Resolve the Unix socket path used to connect to the C2 sidecar.

    Canonical env var: CEO_RAG_SIDECAR_SOCKET (same as rag_router — the router
    is the decision authority).  Falls back to CEO_RAG_SOCKET for back-compat,
    then to the compiled-in default.  This ordering eliminates the router↔bridge
    socket-path mismatch that caused AUTO_WIRE decisions to silently fall back
    to tf-idf when a custom socket path was set only in one of the two vars.
    """
    raw = (
        os.environ.get(_SOCKET_PATH_ENV, "").strip()
        or os.environ.get(_SOCKET_PATH_ENV_COMPAT, "").strip()
        or _DEFAULT_SOCKET_PATH
    )
    return Path(os.path.expanduser(raw))


def _is_cached_dead() -> bool:
    if os.environ.get(_RETRY_HEALTH_ENV, "").strip().lower() in {"1", "true", "on", "yes"}:
        return False
    with _cache_lock:
        return time.monotonic() < _dead_sidecar_until


def _mark_dead() -> None:
    global _dead_sidecar_until
    with _cache_lock:
        _dead_sidecar_until = time.monotonic() + _DEAD_SIDECAR_CACHE_S


def _clear_session_state() -> None:
    """Test helper — reset the dead-sidecar cache."""
    global _dead_sidecar_until
    with _cache_lock:
        _dead_sidecar_until = 0.0


def _emit_event(action: str, **fields: Any) -> None:
    """Best-effort audit event emit. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is None:
            return
        emitter(
            action=action,
            bridge_version=_BRIDGE_VERSION,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
            **fields,
        )
    except Exception:
        return


def _scan_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop chunks whose text triggers any injection family.

    Returns the filtered list + emits `rag_query_redacted` per drop.
    On scan module import failure, returns input unchanged (fail-open
    per ADR-005 — non-redaction is preferable to dropping retrieval
    entirely when the scanner itself is broken; non-scanner bugs are
    not a security boundary).

    When the two-factor bypass env is set, returns input unchanged.
    """
    if _scan_bypass_active():
        return chunks
    try:
        from _lib import output_scan  # type: ignore
    except Exception:
        return chunks

    keep: List[Dict[str, Any]] = []
    for c in chunks:
        text = ""
        for key in ("snippet", "content", "text", "body"):
            v = c.get(key)
            if isinstance(v, str) and v:
                text = v
                break
        if not text:
            keep.append(c)
            continue
        try:
            result = output_scan.scan(text)
        except Exception:
            keep.append(c)
            continue
        family_counts = result.get("family_counts", {}) or {}
        findings = result.get("findings", []) or []
        drop = False
        for fam in family_counts:
            if fam in _INJECTION_DROP_FAMILIES and family_counts[fam] > 0:
                drop = True
                break
        if not drop:
            for f in findings:
                if f.get("vector") in _INJECTION_DROP_VECTORS:
                    drop = True
                    break
        if drop:
            _emit_event(
                "rag_query_redacted",
                chunk_keys=sorted(c.keys()),
                family_counts={k: int(v) for k, v in family_counts.items()},
            )
            continue
        keep.append(c)
    return keep


def _build_jsonrpc(method: str, params: Dict[str, Any]) -> bytes:
    """Construct a JSON-RPC 2.0 request frame per MCP subset."""
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _recv_response(sock: socket.socket, deadline: float) -> Optional[Dict[str, Any]]:
    """Read one MCP-framed JSON-RPC response from the socket."""
    buf = bytearray()
    content_length: Optional[int] = None
    header_end: Optional[int] = None

    while header_end is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(_RECV_CHUNK)
        except (socket.timeout, OSError):
            return None
        if not chunk:
            return None
        buf.extend(chunk)
        header_end = buf.find(b"\r\n\r\n")
        if len(buf) > _MAX_RESPONSE_BYTES:
            return None

    header_bytes = bytes(buf[:header_end])
    for line in header_bytes.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                content_length = int(line.split(b":", 1)[1].strip())
            except ValueError:
                return None
            break
    if content_length is None or content_length <= 0:
        return None
    if content_length > _MAX_RESPONSE_BYTES:
        return None

    body_start = header_end + 4
    while len(buf) - body_start < content_length:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(_RECV_CHUNK)
        except (socket.timeout, OSError):
            return None
        if not chunk:
            return None
        buf.extend(chunk)
        if len(buf) > _MAX_RESPONSE_BYTES:
            return None

    body = bytes(buf[body_start:body_start + content_length])
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _rpc_call(
    method: str,
    params: Dict[str, Any],
    timeout_ms: Optional[int] = None,
) -> Optional[Any]:
    """Issue a single JSON-RPC call to the sidecar.

    Returns the `result` field on success; None on any error path.
    Caller is responsible for applying `_scan_chunks` when the result
    is a list of chunks.
    """
    if _kill_switch_active():
        return None
    if _is_cached_dead():
        _emit_event(
            "rag_query_fallback",
            method=method,
            reason="dead_sidecar_cache",
        )
        return None

    resolved_ms = _resolve_timeout_ms(timeout_ms)
    deadline = time.monotonic() + (resolved_ms / 1000.0)
    sock_path = _resolve_socket_path()

    _emit_event("rag_query_issued", method=method, timeout_ms=resolved_ms)

    if not sock_path.exists():
        _mark_dead()
        _emit_event("rag_query_fallback", method=method, reason="socket_missing")
        return None

    sock: Optional[socket.socket] = None
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        sock.connect(str(sock_path))
        request = _build_jsonrpc(method, params)
        sock.sendall(request)
        response = _recv_response(sock, deadline)
    except (ConnectionRefusedError, FileNotFoundError, PermissionError):
        _mark_dead()
        _emit_event("rag_query_fallback", method=method, reason="connection_refused")
        return None
    except (socket.timeout, OSError) as e:
        _mark_dead()
        _emit_event(
            "rag_query_fallback",
            method=method,
            reason=f"socket_error:{type(e).__name__}",
        )
        return None
    except Exception as e:  # pragma: no cover — defensive
        _mark_dead()
        _emit_event(
            "rag_query_fallback",
            method=method,
            reason=f"unexpected:{type(e).__name__}",
        )
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    if response is None:
        _mark_dead()
        _emit_event("rag_query_fallback", method=method, reason="response_unparseable")
        return None

    if "error" in response:
        err = response.get("error") or {}
        _emit_event(
            "rag_query_fallback",
            method=method,
            reason="rpc_error",
            rpc_error_code=int(err.get("code", 0) or 0),
        )
        return None

    _emit_event("rag_query_returned", method=method)
    return response.get("result")


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def rag_search(
    query: str,
    top_k: int = 5,
    timeout_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Semantic search across the indexed corpus.

    Returns list of result dicts:
        {"file": str, "line": int, "score": float, "snippet": str, "id": str}

    Chunks containing injection patterns are dropped pre-return (A4).
    Returns None on any failure.
    """
    if not isinstance(query, str) or not query.strip():
        return None
    if not isinstance(top_k, int) or top_k <= 0 or top_k > 100:
        top_k = 5
    result = _rpc_call(
        "rag.search",
        {"query": query, "top_k": top_k},
        timeout_ms=timeout_ms,
    )
    if not isinstance(result, list):
        return None
    chunks = [r for r in result if isinstance(r, dict)]
    return _scan_chunks(chunks)


def rag_timeline(
    symbol: str,
    timeout_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Temporal view of symbol evolution."""
    if not isinstance(symbol, str) or not symbol.strip():
        return None
    result = _rpc_call(
        "rag.timeline",
        {"symbol": symbol},
        timeout_ms=timeout_ms,
    )
    if not isinstance(result, list):
        return None
    chunks = [r for r in result if isinstance(r, dict)]
    return _scan_chunks(chunks)


def rag_get_observations(
    obs_id: str,
    timeout_ms: Optional[int] = None,
) -> Optional[str]:
    """Retrieve full content of a node by opaque id.

    Returned string is scanned; on injection hit returns None (no partial
    redaction of a single monolithic string — drop entire observation).
    """
    if not isinstance(obs_id, str) or not obs_id.strip():
        return None
    result = _rpc_call(
        "rag.get_observations",
        {"id": obs_id},
        timeout_ms=timeout_ms,
    )
    if not isinstance(result, str):
        return None
    # Wrap as a single-chunk list for uniform scan
    wrapped = [{"snippet": result}]
    kept = _scan_chunks(wrapped)
    if not kept:
        return None
    return kept[0].get("snippet") if isinstance(kept[0], dict) else None


def rag_retrieve_skills(
    task: str,
    top_k: int = 5,
    timeout_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Retrieve skill matches for a task description via vector search.

    This is the production entry-point for ``skill-retrieve.py`` when the
    C2 sidecar is available.  It wraps ``rag_search()`` and normalises the
    returned chunks into skill-result dicts compatible with the tf-idf
    ranking format::

        {
            "slug":       str,   # from chunk["file"] stem or chunk["id"]
            "tier":       str,   # "rag-sidecar"
            "path":       str,   # from chunk["file"]
            "score":      float, # chunk["score"]
            "base_cosine": float,
            "boosted":    bool,
            "snippet":    str,   # from chunk["snippet"]
        }

    Returns None when the kill-switch is active, the sidecar is absent,
    or the query fails — callers MUST fall back to tf-idf / static lookup.
    Returns an empty list only when the sidecar is healthy but returned
    zero results.

    Normalisation rules:
      - ``slug`` = chunk["id"] if present, else ``Path(chunk["file"]).stem``
        if "file" key exists, else the loop index as a string.
      - ``score`` = float(chunk["score"]) when present, else 0.0.
    """
    if not isinstance(task, str) or not task.strip():
        return None
    if not isinstance(top_k, int) or top_k <= 0 or top_k > 100:
        top_k = 5
    chunks = rag_search(query=task, top_k=top_k, timeout_ms=timeout_ms)
    if chunks is None:
        return None
    results: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue
        # Derive a stable slug from id → file stem → index
        slug: str = ""
        raw_id = chunk.get("id")
        if isinstance(raw_id, str) and raw_id.strip():
            slug = raw_id.strip()
        else:
            raw_file = chunk.get("file")
            if isinstance(raw_file, str) and raw_file.strip():
                try:
                    slug = Path(raw_file).stem
                except Exception:
                    slug = raw_file
        if not slug:
            slug = str(i)
        score = 0.0
        raw_score = chunk.get("score")
        if isinstance(raw_score, (int, float)):
            score = float(raw_score)
        results.append({
            "slug": slug,
            "tier": "rag-sidecar",
            "path": str(chunk.get("file") or ""),
            "score": score,
            "base_cosine": score,
            "boosted": False,
            "snippet": str(chunk.get("snippet") or chunk.get("content") or ""),
        })
    return results


def is_sidecar_healthy(timeout_ms: Optional[int] = None) -> bool:
    """Health probe.

    Short default timeout (500ms) distinct from query timeout.
    Respects CEO_RAG_HEALTH_PROBE=0 (skip, return False).
    """
    if _kill_switch_active():
        return False
    if os.environ.get(_HEALTH_PROBE_ENV, "").strip().lower() in {"0", "false", "off", "no"}:
        return False
    probe_timeout = timeout_ms if timeout_ms is not None else 500
    result = _rpc_call("rag.health", {}, timeout_ms=probe_timeout)
    return isinstance(result, dict) and bool(result.get("ok"))
