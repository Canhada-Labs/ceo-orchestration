"""WS-2(d) — optional RAG context-trim recommendation.

Killable via ``CEO_RAG=0`` (NEW switch — no framework code reads bare ``CEO_RAG``
today; enforced solely inside this module). Read-only consumes ``_lib.rag_router``
+ ``_lib.rag_bridge`` exactly like ``skill-retrieve.py``. On THIS repo at HEAD
(no ``repo-profile.yaml`` of LARGE size, no sidecar socket) ``route_query``
returns ``PROFILE_INELIGIBLE`` so this honestly degrades to ``available=False`` —
that is the **default posture** and the tests cover it as such. It NEVER calls
``rag_search`` synchronously inside the latency-critical hook: ``recommend`` is
``in_hook=True`` by default and short-circuits to ``available=False`` before any
router / probe / bridge IO; only the out-of-hook production path
(``in_hook=False``) runs the lever, and even then with an aggressive
``CEO_RAG_QUERY_TIMEOUT_MS`` so it can never block on the bridge's 5 s default.
``recommend`` never raises.
"""

from __future__ import annotations

from pathlib import Path

from ._skeleton import env_int, kill_switch_off
from .types import RagHint

# Cap on the rendered context block so the additionalContext stays bounded.
_MAX_BLOCK_CHARS = 2000


def recommend(query: str, repo_root: Path, top_k: int = 5, in_hook: bool = True) -> RagHint:
    """Best-effort RAG context hint. Returns a :class:`RagHint`. Never raises.

    ``in_hook`` gates the synchronous sidecar IO. The latency-critical
    ``UserPromptSubmit`` hook (<100 ms p99 SLO) passes ``in_hook=True`` (the
    default) so this short-circuits to ``available=False`` BEFORE touching the
    router / health probe / bridge — none of which is bounded tightly enough for
    the hook hot-path. The out-of-hook production path (``in_hook=False``, the
    façade's in-turn call) actually runs the lever: kill-switch → ``route_query``
    → health probe → ``rag_search`` over the unix socket (ADR-126 boundary: this
    core path NEVER imports chromadb / sentence_transformers / lightrag — it only
    talks to the sidecar via ``rag_bridge``).

    Degrades cleanly to ``RagHint(available=False, ...)`` on: ``in_hook=True``
    (the SLO skip), kill-switch off, ``_lib`` import failure, a non-``AUTO_WIRE``
    routing decision (the default on this repo), an unhealthy/absent sidecar, or
    any exception. ``available=False`` is the default posture.
    """
    if in_hook:
        # Hook hot-path: never run synchronous sidecar IO under the <100 ms SLO.
        return RagHint(available=False, router_decision="in_hook_skip", context_block="", chunks_returned=0)

    if kill_switch_off("CEO_RAG"):
        return RagHint(available=False, router_decision="kill_switch", context_block="", chunks_returned=0)

    try:
        from _lib import rag_router  # type: ignore[import]
        from _lib import rag_bridge  # type: ignore[import]
    except Exception:
        return RagHint(available=False, router_decision="import_failed", context_block="", chunks_returned=0)

    try:
        decision, _reason = rag_router.route_query(repo_root=Path(repo_root), query_class="semantic")
    except Exception:
        return RagHint(available=False, router_decision="route_error", context_block="", chunks_returned=0)

    if decision != getattr(rag_router, "AUTO_WIRE", "auto_wire"):
        # On this repo this is PROFILE_INELIGIBLE — the honest default posture.
        return RagHint(available=False, router_decision=str(decision), context_block="", chunks_returned=0)

    # AUTO_WIRE — a sidecar is provisioned. Precheck health, then query with an
    # aggressive timeout so we never block on the 5 s bridge default.
    try:
        if hasattr(rag_bridge, "is_sidecar_healthy") and not rag_bridge.is_sidecar_healthy(timeout_ms=500):
            return RagHint(available=False, router_decision="sidecar_unhealthy", context_block="", chunks_returned=0)
        timeout_ms = env_int("CEO_RAG_QUERY_TIMEOUT_MS", 800, 100, 5000)
        chunks = rag_bridge.rag_search(query, top_k=max(1, int(top_k)), timeout_ms=timeout_ms)
    except Exception:
        return RagHint(available=False, router_decision="query_error", context_block="", chunks_returned=0)

    if not chunks:
        return RagHint(available=False, router_decision="no_results", context_block="", chunks_returned=0)

    block = _render_block(chunks)
    return RagHint(
        available=True,
        router_decision=str(decision),
        context_block=block,
        chunks_returned=len(chunks),
    )


def _render_block(chunks) -> str:
    """Render retrieved chunks (already injection-scrubbed by the bridge) into a
    bounded ``file:line — snippet`` context block. Defensive on chunk shape."""
    lines = []
    used = 0
    try:
        for ch in chunks:
            if not isinstance(ch, dict):
                continue
            path = str(ch.get("file") or ch.get("path") or ch.get("source") or "?")
            line_no = ch.get("line") or ch.get("line_no") or ""
            snippet = str(ch.get("text") or ch.get("snippet") or ch.get("content") or "").strip()
            snippet = " ".join(snippet.split())[:200]
            rendered = "- %s:%s — %s" % (path[:80], line_no, snippet)
            if used + len(rendered) + 1 > _MAX_BLOCK_CHARS:
                break
            lines.append(rendered)
            used += len(rendered) + 1
    except Exception:
        return ""
    return "\n".join(lines)
