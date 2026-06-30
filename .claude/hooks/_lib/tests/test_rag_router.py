"""PLAN-097 Wave C tests — rag_router.py routing decisions.

Canonical destination at ceremony: .claude/hooks/_lib/tests/test_rag_router.py
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path

import pytest


def _short_socket_path(name: str = "s") -> Path:
    """Allocate a Unix socket path under /tmp to stay under macOS AF_UNIX
    104-char limit. pytest tmp_path on macOS lives under
    `/private/var/folders/...` which busts the limit."""
    d = tempfile.mkdtemp(prefix="rr-", dir="/tmp")
    return Path(d) / name

# Add hooks dir to sys.path for test imports.
_HOOKS = Path(__file__).resolve().parents[2]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import rag_router  # noqa: E402


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a tmp repo with a minimal `.claude/repo-profile.yaml`."""
    (tmp_path / ".claude").mkdir()
    return tmp_path


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Reset env vars that affect routing decisions."""
    for k in (
        "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED",
        "CEO_RAG_SIDECAR",
        "CEO_RAG_SIDECAR_SOCKET",
        "CEO_RAG_HEALTH_PROBE",
    ):
        monkeypatch.delenv(k, raising=False)


def _write_profile(tmp_repo: Path, size_class: str) -> None:
    text = (
        "---\n"
        'schema_version: "1"\n'
        'risk_class: "engine"\n'
        f'size_class: "{size_class}"\n'
        "loc_count: 250000\n"
        'detected_at: "2026-05-17T12:00:00Z"\n'
        'confidence: "high"\n'
        "manual_override: false\n"
        'created_at: "2026-05-17T12:00:00Z"\n'
        "signals: []\n"
    )
    (tmp_repo / ".claude" / "repo-profile.yaml").write_text(text, encoding="utf-8")


def test_kill_switch_class_wins(tmp_repo, monkeypatch):
    """ADR-062-AMEND-1 precedence rule 1 — class kill-switch wins."""
    monkeypatch.setenv("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", "0")
    _write_profile(tmp_repo, "LARGE")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.KILL_SWITCH
    assert "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED" in reason


def test_kill_switch_legacy_alias_wins(tmp_repo, monkeypatch):
    """ADR-062-AMEND-1 precedence rule 2 — legacy alias kill-switch wins."""
    monkeypatch.setenv("CEO_RAG_SIDECAR", "0")
    _write_profile(tmp_repo, "LARGE")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.KILL_SWITCH
    assert "CEO_RAG_SIDECAR" in reason


def test_kill_switch_class_precedes_legacy(tmp_repo, monkeypatch):
    """When BOTH kill-switches set, class kill-switch takes precedence."""
    monkeypatch.setenv("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", "0")
    monkeypatch.setenv("CEO_RAG_SIDECAR", "0")
    _write_profile(tmp_repo, "LARGE")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.KILL_SWITCH
    assert "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED" in reason


def test_profile_small_ineligible(tmp_repo):
    """SMALL profile never auto-wires routing."""
    _write_profile(tmp_repo, "SMALL")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.PROFILE_INELIGIBLE
    assert "profile=SMALL" in reason


def test_profile_medium_ineligible(tmp_repo):
    """MEDIUM profile never auto-wires routing."""
    _write_profile(tmp_repo, "MEDIUM")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.PROFILE_INELIGIBLE
    assert "profile=MEDIUM" in reason


def test_profile_absent_ineligible(tmp_repo):
    """Missing `size_class` field → PROFILE_INELIGIBLE."""
    text = (
        "---\n"
        'schema_version: "1"\n'
        'risk_class: "engine"\n'
        'detected_at: "2026-05-17T12:00:00Z"\n'
        'confidence: "high"\n'
        "manual_override: false\n"
        'created_at: "2026-05-17T12:00:00Z"\n'
        "signals: []\n"
    )
    (tmp_repo / ".claude" / "repo-profile.yaml").write_text(text, encoding="utf-8")
    decision, reason = rag_router.evaluate_predicate(tmp_repo)
    assert decision == rag_router.PROFILE_INELIGIBLE
    assert "profile=absent" in reason


def test_profile_large_sidecar_down(tmp_repo, monkeypatch):
    """LARGE profile + sidecar socket missing → SKIP_SIDECAR_DOWN."""
    missing = _short_socket_path("missing.sock")
    # Remove the file the helper would have allocated; we want missing socket.
    missing.unlink(missing_ok=True)
    monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(missing))
    _write_profile(tmp_repo, "LARGE")
    try:
        decision, reason = rag_router.evaluate_predicate(tmp_repo)
        assert decision == rag_router.SKIP_SIDECAR_DOWN
        assert "socket-missing" in reason
    finally:
        shutil.rmtree(missing.parent, ignore_errors=True)


def test_profile_large_socket_present_skip_health(tmp_repo, monkeypatch):
    """LARGE profile + socket present + skip-probe → AUTO_WIRE."""
    sock_path = _short_socket_path()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    try:
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        _write_profile(tmp_repo, "LARGE")
        decision, reason = rag_router.evaluate_predicate(tmp_repo, skip_health_probe=True)
        assert decision == rag_router.AUTO_WIRE
        assert "probe-skipped" in reason
    finally:
        server.close()
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_profile_large_socket_health_ok(tmp_repo, monkeypatch):
    """LARGE profile + socket alive + health probe success → AUTO_WIRE."""
    sock_path = _short_socket_path()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    try:
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        _write_profile(tmp_repo, "LARGE")
        decision, reason = rag_router.evaluate_predicate(tmp_repo)
        assert decision == rag_router.AUTO_WIRE
        assert reason == "predicate-true"
    finally:
        server.close()
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_kill_switch_class_overrides_large(tmp_repo, monkeypatch):
    """Kill-switch wins even when full predicate would AUTO_WIRE."""
    sock_path = _short_socket_path()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    try:
        monkeypatch.setenv("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", "0")
        monkeypatch.setenv("CEO_RAG_SIDECAR_SOCKET", str(sock_path))
        _write_profile(tmp_repo, "LARGE")
        decision, reason = rag_router.evaluate_predicate(tmp_repo)
        assert decision == rag_router.KILL_SWITCH
    finally:
        server.close()
        shutil.rmtree(sock_path.parent, ignore_errors=True)


def test_no_profile_yaml(tmp_path):
    """No `.claude/repo-profile.yaml` at all → PROFILE_INELIGIBLE."""
    decision, reason = rag_router.evaluate_predicate(tmp_path)
    assert decision == rag_router.PROFILE_INELIGIBLE
    assert "profile=absent" in reason


def test_route_query_signature(tmp_repo, monkeypatch):
    """route_query() returns (decision, reason) tuple per public API."""
    _write_profile(tmp_repo, "SMALL")
    result = rag_router.route_query(repo_root=tmp_repo, query_class="semantic")
    assert isinstance(result, tuple)
    assert len(result) == 2
    decision, reason = result
    assert decision == rag_router.PROFILE_INELIGIBLE
