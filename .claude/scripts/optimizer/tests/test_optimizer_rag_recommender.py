"""Tests for optimizer.rag_recommender — WS-2(d) RAG context hint.

Covers BOTH legs of the ``in_hook`` gate:

* ``in_hook=True`` (the default, the <100 ms hook hot-path) — always skips the
  synchronous sidecar IO and returns ``available=False`` BEFORE any router /
  probe / bridge call.
* ``in_hook=False`` (the out-of-hook production path) — actually runs the lever:
  kill-switch → ``route_query`` → health probe → ``rag_search`` over the unix
  socket, with the router + bridge MOCKED (no real socket, no chromadb /
  sentence_transformers / lightrag import — ADR-126 boundary respected: the core
  path only talks to the sidecar via ``rag_bridge``).

``recommend`` NEVER raises and ``available=False`` is the default posture.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from _lib import rag_bridge, rag_router  # type: ignore[import]

from optimizer import rag_recommender as R


# ---------------------------------------------------------------------------
# in_hook=True — the latency-critical hook hot-path always skips sidecar IO.
# ---------------------------------------------------------------------------


def test_in_hook_true_skips_sidecar_io(monkeypatch):
    """Default ``in_hook=True`` short-circuits to available=False BEFORE touching
    the router / probe / bridge (the <100 ms hook SLO)."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(rag_router, "route_query") as rq, \
            mock.patch.object(rag_bridge, "rag_search") as rs:
        h = R.recommend("semantic query about auth", Path("."))  # in_hook defaults True
        assert h.available is False
        assert h.router_decision == "in_hook_skip"
        assert h.context_block == ""
        assert h.chunks_returned == 0
        rq.assert_not_called()
        rs.assert_not_called()


def test_in_hook_true_skips_even_with_kill_switch_off(monkeypatch):
    """The hook-skip happens before the kill-switch read, so even with CEO_RAG=0
    the decision is the skip sentinel (the hook never reaches the switch)."""
    monkeypatch.setenv("CEO_RAG", "0")
    h = R.recommend("anything", Path("."), in_hook=True)
    assert h.available is False
    assert h.router_decision == "in_hook_skip"


# ---------------------------------------------------------------------------
# in_hook=False — the out-of-hook production lever.
# ---------------------------------------------------------------------------


def test_kill_switch_disables(monkeypatch):
    """CEO_RAG=0 disables the lever on the out-of-hook path."""
    monkeypatch.setenv("CEO_RAG", "0")
    h = R.recommend("anything", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == "kill_switch"
    assert h.chunks_returned == 0


def test_out_of_hook_healthy_returns_bounded_block(monkeypatch):
    """Out-of-hook with a MOCKED healthy router + bridge returns a bounded,
    available context block sourced from rag_search over the socket."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    chunks = [
        {"file": "auth/login.py", "line": 42, "text": "def authenticate(user): ..."},
        {"file": "auth/session.py", "line": 9, "snippet": "session = new_session()"},
    ]
    with mock.patch.object(rag_router, "route_query", return_value=(rag_router.AUTO_WIRE, "predicate-true")), \
            mock.patch.object(rag_bridge, "is_sidecar_healthy", return_value=True) as health, \
            mock.patch.object(rag_bridge, "rag_search", return_value=chunks) as search:
        h = R.recommend("how does auth work", Path("."), top_k=5, in_hook=False)
    assert h.available is True
    assert h.router_decision == rag_router.AUTO_WIRE
    assert h.chunks_returned == 2
    assert "auth/login.py:42" in h.context_block
    assert len(h.context_block) <= 2000
    health.assert_called_once()
    # rag_search was actually invoked over the (mocked) bridge.
    search.assert_called_once()


def test_out_of_hook_sidecar_down_unavailable(monkeypatch):
    """AUTO_WIRE but the health probe reports unhealthy → available=False, the
    bridge query is never issued."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(rag_router, "route_query", return_value=(rag_router.AUTO_WIRE, "predicate-true")), \
            mock.patch.object(rag_bridge, "is_sidecar_healthy", return_value=False), \
            mock.patch.object(rag_bridge, "rag_search") as search:
        h = R.recommend("auth", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == "sidecar_unhealthy"
    assert h.context_block == ""
    search.assert_not_called()


def test_out_of_hook_non_auto_wire_unavailable(monkeypatch):
    """A non-AUTO_WIRE routing decision (the default posture on this repo) →
    available=False carrying the router's decision; no bridge call."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(
        rag_router, "route_query",
        return_value=(rag_router.PROFILE_INELIGIBLE, "profile=absent"),
    ), mock.patch.object(rag_bridge, "rag_search") as search:
        h = R.recommend("auth", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == rag_router.PROFILE_INELIGIBLE
    search.assert_not_called()


def test_out_of_hook_empty_results_unavailable(monkeypatch):
    """Healthy AUTO_WIRE but the bridge returns no chunks → available=False."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(rag_router, "route_query", return_value=(rag_router.AUTO_WIRE, "predicate-true")), \
            mock.patch.object(rag_bridge, "is_sidecar_healthy", return_value=True), \
            mock.patch.object(rag_bridge, "rag_search", return_value=[]):
        h = R.recommend("auth", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == "no_results"


def test_out_of_hook_default_posture_unavailable(monkeypatch):
    """On THIS repo (no LARGE repo-profile, no sidecar socket) the REAL router
    returns PROFILE_INELIGIBLE / SKIP_SIDECAR_DOWN so the hint is unavailable —
    the honest default, exercised through the live _lib (not mocked)."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    monkeypatch.delenv("CEO_RAG_SIDECAR", raising=False)
    monkeypatch.delenv("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", raising=False)
    h = R.recommend("semantic query about auth", Path("."), in_hook=False)
    assert h.available is False
    assert isinstance(h.router_decision, str) and h.router_decision
    assert h.context_block == ""


def test_out_of_hook_route_error_never_raises(monkeypatch):
    """A router that raises is swallowed → available=False (never propagates)."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(rag_router, "route_query", side_effect=RuntimeError("boom")):
        h = R.recommend("auth", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == "route_error"


def test_out_of_hook_query_error_never_raises(monkeypatch):
    """A bridge that raises on rag_search is swallowed → available=False."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    with mock.patch.object(rag_router, "route_query", return_value=(rag_router.AUTO_WIRE, "predicate-true")), \
            mock.patch.object(rag_bridge, "is_sidecar_healthy", return_value=True), \
            mock.patch.object(rag_bridge, "rag_search", side_effect=RuntimeError("socket blew up")):
        h = R.recommend("auth", Path("."), in_hook=False)
    assert h.available is False
    assert h.router_decision == "query_error"


def test_never_raises_on_garbage(monkeypatch):
    """Empty query + nonexistent repo on either leg never raises."""
    monkeypatch.delenv("CEO_RAG", raising=False)
    assert R.recommend("", Path("/nonexistent")).available in (True, False)
    assert R.recommend("", Path("/nonexistent"), in_hook=False).available in (True, False)


# ---------------------------------------------------------------------------
# _render_block — defensive, bounded.
# ---------------------------------------------------------------------------


def test_render_block_defensive():
    block = R._render_block([
        {"file": "a.py", "line": 4, "text": "def foo(): pass"},
        {"path": "b.py", "snippet": "x = 1"},
        "not a dict",
        {"weird": "shape"},
    ])
    assert "a.py:4" in block
    assert len(block) <= 2000


def test_render_block_bounded():
    big = [{"file": "f%d.py" % i, "line": i, "text": "x" * 300} for i in range(100)]
    block = R._render_block(big)
    assert len(block) <= 2000
