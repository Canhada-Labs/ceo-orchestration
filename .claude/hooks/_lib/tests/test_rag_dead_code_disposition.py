"""PLAN-113 W6 (F-11.3) — RAG dead-code FAIL-CLOSED-WHILE-DEAD disposition.

The RAG retrieval path (`rag_router.route_query` + `rag_bridge.rag_search`
and siblings) has ZERO production callers as of PLAN-113 Phase B. Per the
PLAN-113 C2 doctrine, a dispositioned-dead *security-relevant* path is NOT
deleted on the dead signal alone — it must be verified to FAIL CLOSED while
dead. These tests assert that, with no production wiring and the default
opt-out posture, the entrypoints:

  * do NOT crash (return cleanly),
  * do NOT auto-dispatch to the sidecar (never AUTO_WIRE),
  * do NOT leak chunks / observations (always None when disabled).

This is the regression backstop for keeping the module present-but-inert.
Re-wiring RAG into production is OUT OF SCOPE for W6.
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path

import pytest

# Add hooks dir to sys.path for `from _lib import ...`.
_HOOKS = Path(__file__).resolve().parents[2]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import rag_bridge  # noqa: E402
from _lib import rag_router  # noqa: E402


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Strip every env var that could opt the dead path back in, so the
    test exercises the true default (disabled) posture regardless of the
    invoking shell."""
    for k in (
        "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED",
        "CEO_RAG_SIDECAR",
        "CEO_RAG_SIDECAR_SOCKET",
        "CEO_RAG_SOCKET",
        "CEO_RAG_HEALTH_PROBE",
        "CEO_RAG_SCAN",
        "CEO_RAG_SCAN_ACK",
        "CEO_RAG_RETRY_HEALTH",
    ):
        monkeypatch.delenv(k, raising=False)
    # Clear the per-process dead-sidecar cache so each test starts clean.
    rag_bridge._clear_session_state()


# ---------------------------------------------------------------------------
# rag_router.route_query — never AUTO_WIRE when unwired / default posture
# ---------------------------------------------------------------------------


def test_route_query_default_posture_does_not_auto_wire(tmp_path):
    """No repo-profile.yaml + default env → routing stays inert (not AUTO_WIRE)."""
    (tmp_path / ".claude").mkdir()
    decision, reason = rag_router.route_query(repo_root=tmp_path)
    assert decision != rag_router.AUTO_WIRE
    assert decision == rag_router.PROFILE_INELIGIBLE
    assert reason  # non-empty audit reason


def test_route_query_kill_switch_fails_closed(tmp_path):
    """Explicit kill-switch wins → KILL_SWITCH, never AUTO_WIRE."""
    (tmp_path / ".claude").mkdir()
    os.environ["CEO_RAG_SIDECAR"] = "0"
    try:
        decision, _ = rag_router.route_query(repo_root=tmp_path)
    finally:
        os.environ.pop("CEO_RAG_SIDECAR", None)
    assert decision == rag_router.KILL_SWITCH
    assert decision != rag_router.AUTO_WIRE


def test_route_query_returns_clean_tuple_no_crash(tmp_path):
    """Entrypoint returns a (decision, reason) tuple and does not raise."""
    result = rag_router.route_query(repo_root=tmp_path)
    assert isinstance(result, tuple) and len(result) == 2
    decision, reason = result
    assert isinstance(decision, str) and isinstance(reason, str)


# ---------------------------------------------------------------------------
# rag_bridge.* — fail closed (return None) when the feature is disabled
# ---------------------------------------------------------------------------


def test_rag_search_no_socket_returns_none_no_leak():
    """No sidecar socket (default env) → rag_search returns None (no chunk leak).

    Under the unified ADR-062-AMEND-1 contract, absent CEO_RAG_SIDECAR enables
    the bridge (conditional-default-on).  None is returned because there is no
    sidecar socket at the default path — not because of a kill-switch.  This
    ensures the dead path degrades safely: never raises, never leaks chunks.
    """
    assert rag_bridge.rag_search("any query", top_k=5) is None


def test_rag_timeline_no_socket_returns_none():
    """No sidecar socket → rag_timeline returns None (fail-open)."""
    assert rag_bridge.rag_timeline("Foo.bar") is None


def test_rag_get_observations_no_socket_returns_none():
    """No sidecar socket → rag_get_observations returns None (fail-open)."""
    assert rag_bridge.rag_get_observations("obs-123") is None


def test_is_sidecar_healthy_no_socket_returns_false():
    """Health probe is False when no sidecar socket is present."""
    assert rag_bridge.is_sidecar_healthy() is False


def test_rag_search_no_socket_even_if_enabled_fails_closed(monkeypatch, tmp_path):
    """Opt-in env set but NO sidecar socket present → still None (fail closed).

    Proves the path cannot accidentally dispatch when wired-on but the
    sidecar is absent — the dead path degrades to None, never raises and
    never returns unscanned content.
    """
    monkeypatch.setenv("CEO_RAG_SIDECAR", "1")
    missing = tmp_path / "no-such.sock"
    monkeypatch.setenv("CEO_RAG_SOCKET", str(missing))
    rag_bridge._clear_session_state()
    assert rag_bridge.rag_search("query") is None


def test_rag_search_rejects_bad_input_without_crash():
    """Defensive input validation: empty/non-str query → None, no exception."""
    assert rag_bridge.rag_search("") is None
    assert rag_bridge.rag_search("   ") is None


# ---------------------------------------------------------------------------
# Socket-path unification: CEO_RAG_SIDECAR_SOCKET (canonical) must be read
# by BOTH rag_router AND rag_bridge — P2 fix for the router↔bridge mismatch
# that caused AUTO_WIRE to silently fall back to tf-idf on a custom socket.
# ---------------------------------------------------------------------------


def _tmp_socket_path(name: str = "s") -> Path:
    """Allocate a short Unix socket path under /tmp (macOS AF_UNIX 104-char limit)."""
    d = tempfile.mkdtemp(prefix="rag-unify-", dir="/tmp")
    return Path(d) / name


def _write_large_profile(repo_root: Path) -> None:
    text = (
        "---\n"
        'schema_version: "1"\n'
        'risk_class: "engine"\n'
        'size_class: "LARGE"\n'
        "loc_count: 250000\n"
        'detected_at: "2026-05-17T12:00:00Z"\n'
        'confidence: "high"\n'
        "manual_override: false\n"
        'created_at: "2026-05-17T12:00:00Z"\n'
        "signals: []\n"
    )
    (repo_root / ".claude").mkdir(parents=True, exist_ok=True)
    (repo_root / ".claude" / "repo-profile.yaml").write_text(text, encoding="utf-8")


def test_canonical_socket_env_router_routes_auto_wire(monkeypatch, tmp_path):
    """CEO_RAG_SIDECAR_SOCKET set → router reaches AUTO_WIRE via that socket.

    Verifies the router's _sidecar_socket_path() reads the canonical var.
    """
    sock_path = _tmp_socket_path("router.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    try:
        _write_large_profile(tmp_path)
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        decision, reason = rag_router.evaluate_predicate(tmp_path, skip_health_probe=True)
        assert decision == rag_router.AUTO_WIRE, (
            f"Expected AUTO_WIRE, got {decision!r} ({reason!r})"
        )
    finally:
        server.close()
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_canonical_socket_env_bridge_resolves_same_path(monkeypatch, tmp_path):
    """CEO_RAG_SIDECAR_SOCKET set → bridge's _resolve_socket_path() returns same path.

    Proves there is no router↔bridge socket mismatch: both modules resolve
    the same Path object when the canonical env var is set, so an AUTO_WIRE
    decision by the router will not silently fall back to tf-idf in the bridge.
    """
    sock_path = _tmp_socket_path("bridge.sock")
    try:
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        resolved = rag_bridge._resolve_socket_path()
        assert resolved == sock_path.resolve() or resolved == sock_path, (
            f"Bridge resolved {resolved!r}, expected {sock_path!r}"
        )
    finally:
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_canonical_socket_env_bridge_missing_socket_fallback(monkeypatch, tmp_path):
    """CEO_RAG_SIDECAR_SOCKET set to absent path → bridge returns None (tf-idf fallback).

    Verifies the bridge reads the canonical var and correctly degrades to None
    (no crash, no silent mismatch) when that socket does not exist.
    """
    sock_path = _tmp_socket_path("absent.sock")
    # Do NOT create the socket — we want the "socket missing → fallback" path.
    try:
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        rag_bridge._clear_session_state()
        result = rag_bridge.rag_search("query")
        assert result is None, (
            "Expected None (tf-idf fallback) when socket is absent via canonical env var"
        )
    finally:
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_compat_alias_socket_env_still_works(monkeypatch, tmp_path):
    """CEO_RAG_SOCKET (back-compat alias) → bridge still resolves the path.

    Verifies the compat alias is not silently broken after the unification fix.
    CEO_RAG_SIDECAR_SOCKET is absent; CEO_RAG_SOCKET is set; bridge must use
    the alias value.
    """
    sock_path = _tmp_socket_path("compat.sock")
    try:
        monkeypatch.delenv("CEO_RAG_SIDECAR_SOCKET", raising=False)
        monkeypatch.setenv("CEO_RAG_SOCKET", str(sock_path))
        resolved = rag_bridge._resolve_socket_path()
        assert resolved == sock_path.resolve() or resolved == sock_path, (
            f"Back-compat alias: bridge resolved {resolved!r}, expected {sock_path!r}"
        )
    finally:
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_canonical_socket_env_takes_precedence_over_compat(monkeypatch):
    """CEO_RAG_SIDECAR_SOCKET takes precedence over CEO_RAG_SOCKET when both set."""
    canonical_path = "/tmp/canonical.sock"
    compat_path = "/tmp/compat.sock"
    monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", canonical_path)
    monkeypatch.setenv("CEO_RAG_SOCKET", compat_path)
    resolved = rag_bridge._resolve_socket_path()
    assert str(resolved) == canonical_path, (
        f"Canonical should win: got {resolved!r}, expected {canonical_path!r}"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
