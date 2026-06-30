"""WIRE-RAG tests for skill-retrieve.py + rag_bridge + rag_router wiring.

PLAN-113 Phase C / F-5.6-5.6-f7d44719 / F-11.3-rag-zero-production-callers

Covers three scenarios per the task spec:

(a) Sidecar absent (default/kill-switched) → regex / tf-idf fallback,
    identical to pre-wiring behaviour (zero regression).
(b) Sidecar present (FakeSidecar mock) → rag path taken, merged results
    returned, events emitted.
(c) Cascade demotion decision points fire rag_false_large_demoted /
    rag_hit_rate_degraded via rag_router.emit_cascade_quality().
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import sqlite3
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch, MagicMock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Lazy-load modules under test
from _lib import rag_router  # noqa: E402
from _lib import rag_bridge  # noqa: E402


def _load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, str(_SCRIPTS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


retrieve_mod = _load_script("skill_retrieve", "skill-retrieve.py")
build_mod = _load_script("skill_index_build", "skill-index-build.py")


# ---------------------------------------------------------------------------
# Minimal synthetic skill fixtures (same as test_skill_retrieval.py)
# ---------------------------------------------------------------------------

_MINIMAL_SKILLS = {
    "core/security-and-auth": {
        "name": "security-and-auth",
        "description": (
            "Security, authentication, JWT token handling, authorization."
        ),
        "body": "# Security and Auth\n\nHTTPS, TLS, CSRF, JWT.",
    },
    "core/testing-strategy": {
        "name": "testing-strategy",
        "description": (
            "Testing patterns, unit tests, coverage, mutation testing."
        ),
        "body": "# Testing\n\nUse pytest, coverage.",
    },
}


def _write_skills(repo_root: Path) -> None:
    for rel_path, spec in _MINIMAL_SKILLS.items():
        skill_dir = repo_root / ".claude" / "skills" / rel_path
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent(f"""\
            ---
            name: {spec['name']}
            description: {spec['description']}
            owner: test
            ---

            {spec['body']}
            """)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def _restore_canonical_audit_emit() -> None:
    """Force-restore the canonical ``_lib.audit_emit`` (sys.modules entry + the
    ``_lib`` package attribute) before patching it.

    A test in a COMBINED hooks+scripts pytest session (the ``validate.yml``
    matrix step ``Run hook + script tests``) may shadow ``_lib.audit_emit`` with
    the PLAN-078 staged module and leave the ``_lib`` package attribute missing
    while a stale ``sys.modules`` entry lingers. Python's
    ``from _lib import audit_emit`` then binds from the sys.modules cache WITHOUT
    re-setting the package attribute, so ``patch("_lib.audit_emit.emit_*")``
    raises ``AttributeError: module '_lib' has no attribute 'audit_emit'``.
    Dropping the cached entry + re-importing canonical (the staged path is not on
    ``sys.path``) + re-binding the attribute makes the patch targets resolvable
    regardless of upstream test ordering. Fail-open (never blocks setUp)."""
    try:
        import _lib as _lib_pkg
        sys.modules.pop("_lib.audit_emit", None)
        _lib_pkg.audit_emit = importlib.import_module("_lib.audit_emit")
    except Exception:
        pass


class _TempRepoBase(unittest.TestCase):
    def setUp(self) -> None:
        self._env_snap = {
            k: os.environ.get(k)
            for k in (
                "CEO_SKILL_INDEX_PATH", "CEO_SOTA_DISABLE", "CEO_REAL_EMBEDDINGS",
                "CEO_RAG_SIDECAR", "CEO_RAG_SOCKET", "CEO_RAG_HEALTH_PROBE",
                "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", "CEO_RAG_SIDECAR_SOCKET",
                "HOME",
            )
        }
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ceo-rag-wire-"))
        self.repo_root = self.tmpdir / "repo"
        self.home_dir = self.tmpdir / "home"
        self.repo_root.mkdir()
        self.home_dir.mkdir()
        os.environ["HOME"] = str(self.home_dir)
        # Strip all RAG env vars — default posture is sidecar-OFF
        for k in (
            "CEO_RAG_SIDECAR", "CEO_RAG_SOCKET", "CEO_RAG_HEALTH_PROBE",
            "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED", "CEO_RAG_SIDECAR_SOCKET",
        ):
            os.environ.pop(k, None)
        # Reset rag_bridge dead-sidecar cache
        rag_bridge._clear_session_state()
        # Force-restore the canonical _lib.audit_emit so the patch("_lib.
        # audit_emit.emit_*") targets resolve regardless of upstream test
        # ordering (combined hooks+scripts session). See the helper docstring.
        _restore_canonical_audit_emit()
        self.index_path = self.tmpdir / "skill-index.sqlite"
        _write_skills(self.repo_root)
        build_mod.build_index(self.repo_root, self.index_path)

    def tearDown(self) -> None:
        for k, v in self._env_snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        rag_bridge._clear_session_state()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Minimal FakeSidecar (inline, for the tests below)
# ---------------------------------------------------------------------------

class _FakeSidecar:
    """Minimal Unix-socket sidecar stub that returns fixed search results."""

    def __init__(
        self,
        sock_path: Path,
        results: List[Dict[str, Any]],
    ) -> None:
        self.sock_path = sock_path
        self.results = results
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def __enter__(self) -> "_FakeSidecar":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    def start(self) -> None:
        if self.sock_path.exists():
            self.sock_path.unlink()
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.settimeout(0.5)
        srv.bind(str(self.sock_path))
        srv.listen(5)
        os.chmod(self.sock_path, 0o600)
        self._server = srv
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

    def _serve_loop(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except (socket.timeout, OSError):
                continue
            try:
                self._handle(conn)
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _handle(self, conn: socket.socket) -> None:
        conn.settimeout(5.0)
        buf = bytearray()
        try:
            while b"\r\n\r\n" not in buf:
                c = conn.recv(65536)
                if not c:
                    return
                buf.extend(c)
        except (socket.timeout, OSError):
            return
        header_end = buf.find(b"\r\n\r\n")
        header = bytes(buf[:header_end])
        clen = 0
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                clen = int(line.split(b":", 1)[1].strip())
        body_start = header_end + 4
        while len(buf) - body_start < clen:
            try:
                c = conn.recv(65536)
                if not c:
                    return
                buf.extend(c)
            except (socket.timeout, OSError):
                return
        try:
            req = json.loads(bytes(buf[body_start:body_start + clen]).decode("utf-8"))
        except Exception:
            return
        rpc_id = req.get("id", "")
        envelope: Dict[str, Any]
        method = req.get("method", "")
        if method == "rag.health":
            envelope = {"jsonrpc": "2.0", "id": rpc_id, "result": {"ok": True}}
        elif method == "rag.search":
            envelope = {"jsonrpc": "2.0", "id": rpc_id, "result": self.results}
        else:
            envelope = {"jsonrpc": "2.0", "id": rpc_id, "result": []}
        body = json.dumps(envelope).encode("utf-8")
        hdr = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        try:
            conn.sendall(hdr + body)
        except OSError:
            pass

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._server is not None:
                self._server.close()
        finally:
            if self.sock_path.exists():
                try:
                    self.sock_path.unlink()
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# (a) Sidecar absent → tf-idf fallback (zero regression)
# ---------------------------------------------------------------------------

class TestSidecarAbsentFallback(_TempRepoBase):
    """When the RAG sidecar is absent, skill-retrieve must behave exactly
    as before the wiring — tf-idf path, no crash, valid results."""

    def _run_cli_capture(self, task: str, extra_args: Optional[List[str]] = None) -> List[Dict]:
        import io
        out = io.StringIO()
        args_list = [
            "--task", task,
            "--top-k", "3",
            "--repo-root", str(self.repo_root),
            "--index-path", str(self.index_path),
            "--json",
        ] + (extra_args or [])
        with patch("sys.stdout", out):
            rc = retrieve_mod._cli(args_list)
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        return payload["results"]

    def test_sidecar_absent_returns_tfidf_results(self) -> None:
        """No sidecar socket present → results come from tf-idf path."""
        results = self._run_cli_capture("security authentication JWT")
        self.assertGreater(len(results), 0)
        slugs = {r["slug"] for r in results}
        self.assertIn("security-and-auth", slugs)

    def test_sidecar_absent_mode_is_tfidf(self) -> None:
        """With sidecar absent, CLI reports mode=tfidf (not rag+tfidf)."""
        import io
        out = io.StringIO()
        with patch("sys.stdout", out):
            retrieve_mod._cli([
                "--task", "security jwt",
                "--repo-root", str(self.repo_root),
                "--index-path", str(self.index_path),
                "--json",
            ])
        payload = json.loads(out.getvalue())
        self.assertEqual(payload.get("mode"), "tfidf")

    def test_kill_switch_active_returns_tfidf(self) -> None:
        """Explicit kill-switch → still returns valid tf-idf results."""
        import io
        out = io.StringIO()
        with patch.dict(os.environ, {"CEO_RAG_SIDECAR": "0"}):
            rag_bridge._clear_session_state()
            with patch("sys.stdout", out):
                rc = retrieve_mod._cli([
                    "--task", "test coverage",
                    "--repo-root", str(self.repo_root),
                    "--index-path", str(self.index_path),
                    "--json",
                ])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertGreater(len(payload["results"]), 0)

    def test_rag_retrieve_private_returns_none_when_sidecar_absent(self) -> None:
        """`_rag_retrieve` helper returns None when no sidecar socket."""
        result = retrieve_mod._rag_retrieve("any task", self.repo_root, top_k=5)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# (b) Sidecar present (stub) → rag path taken, events emitted
# ---------------------------------------------------------------------------

class TestSidecarPresentRagPath(_TempRepoBase):
    """When the C2 sidecar is present and healthy, skill-retrieve wires
    through rag_bridge and merges RAG results with tf-idf."""

    def _sock_path(self) -> Path:
        # Keep socket path short to stay under macOS AF_UNIX 104-char limit
        p = Path(tempfile.mkdtemp(prefix="rw-", dir="/tmp")) / "s.sock"
        return p

    def _write_large_profile(self) -> None:
        """Write .claude/repo-profile.yaml with size_class=LARGE so
        rag_router.evaluate_predicate returns AUTO_WIRE."""
        claude_dir = self.repo_root / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / "repo-profile.yaml").write_text(
            '---\nschema_version: "1"\nrisk_class: "engine"\nsize_class: "LARGE"\n'
            'loc_count: 300000\ndetected_at: "2026-05-25T00:00:00Z"\n'
            'confidence: "high"\nmanual_override: false\ncreated_at: "2026-05-25T00:00:00Z"\n'
            'signals: []\n',
            encoding="utf-8",
        )

    def test_rag_path_taken_when_sidecar_present(self) -> None:
        """AUTO_WIRE posture → _rag_retrieve returns non-None list."""
        sock_path = self._sock_path()
        self._write_large_profile()
        fake_results = [
            {"file": "core/security-and-auth/SKILL.md", "score": 0.92,
             "snippet": "auth def", "id": "security-and-auth"},
        ]
        with _FakeSidecar(sock_path, fake_results):
            with patch.dict(os.environ, {
                "CEO_RAG_SIDECAR": "1",
                "CEO_RAG_SOCKET": str(sock_path),
                "CEO_RAG_HEALTH_PROBE": "0",  # skip health probe in bridge
                "CEO_RAG_SIDECAR_SOCKET": str(sock_path),  # router uses this
            }):
                rag_bridge._clear_session_state()
                result = retrieve_mod._rag_retrieve(
                    "jwt authentication security", self.repo_root, top_k=5
                )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreater(len(result), 0)
        slugs = {r["slug"] for r in result}
        self.assertIn("security-and-auth", slugs)

    def test_merged_results_returned_in_rag_plus_tfidf_mode(self) -> None:
        """CLI mode is 'rag+tfidf' when sidecar returns results."""
        import io
        sock_path = self._sock_path()
        self._write_large_profile()
        fake_results = [
            {"file": "core/security-and-auth/SKILL.md", "score": 0.95,
             "snippet": "security auth", "id": "security-and-auth"},
        ]
        with _FakeSidecar(sock_path, fake_results):
            with patch.dict(os.environ, {
                "CEO_RAG_SIDECAR": "1",
                "CEO_RAG_SOCKET": str(sock_path),
                "CEO_RAG_HEALTH_PROBE": "0",
                "CEO_RAG_SIDECAR_SOCKET": str(sock_path),
            }):
                rag_bridge._clear_session_state()
                out = io.StringIO()
                with patch("sys.stdout", out):
                    rc = retrieve_mod._cli([
                        "--task", "security authentication",
                        "--repo-root", str(self.repo_root),
                        "--index-path", str(self.index_path),
                        "--json",
                    ])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload.get("mode"), "rag+tfidf")
        slugs = {r["slug"] for r in payload["results"]}
        self.assertIn("security-and-auth", slugs)

    def test_rag_retrieve_skills_normalises_chunks(self) -> None:
        """rag_bridge.rag_retrieve_skills normalises sidecar chunks."""
        sock_path = self._sock_path()
        fake_chunks = [
            {"file": "core/testing-strategy/SKILL.md", "score": 0.88,
             "snippet": "pytest coverage", "id": "testing-strategy"},
            {"file": "core/security-and-auth/SKILL.md", "score": 0.77,
             "snippet": "jwt auth", "id": "security-and-auth"},
        ]
        with _FakeSidecar(sock_path, fake_chunks):
            with patch.dict(os.environ, {
                "CEO_RAG_SIDECAR": "1",
                "CEO_RAG_SOCKET": str(sock_path),
                "CEO_RAG_HEALTH_PROBE": "0",
            }):
                rag_bridge._clear_session_state()
                results = rag_bridge.rag_retrieve_skills("test coverage", top_k=5, timeout_ms=3000)
        self.assertIsNotNone(results)
        assert results is not None
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn("slug", r)
            self.assertIn("tier", r)
            self.assertIn("score", r)
            self.assertEqual(r["tier"], "rag-sidecar")
        slugs = {r["slug"] for r in results}
        self.assertIn("testing-strategy", slugs)
        self.assertIn("security-and-auth", slugs)

    def test_rag_retrieve_skills_absent_sidecar_returns_none(self) -> None:
        """rag_bridge.rag_retrieve_skills returns None when sidecar is absent."""
        with patch.dict(os.environ, {"CEO_RAG_SIDECAR": "1", "CEO_RAG_SOCKET": "/tmp/no-such-path.sock"}):
            rag_bridge._clear_session_state()
            result = rag_bridge.rag_retrieve_skills("any task", top_k=3)
        self.assertIsNone(result)

    def test_rag_retrieve_skills_kill_switch_returns_none(self) -> None:
        """rag_bridge.rag_retrieve_skills returns None when kill-switch active."""
        with patch.dict(os.environ, {"CEO_RAG_SIDECAR": "0"}):
            rag_bridge._clear_session_state()
            result = rag_bridge.rag_retrieve_skills("any task", top_k=3)
        self.assertIsNone(result)

    def test_large_profile_socket_healthy_absent_env_engages_rag(self) -> None:
        """Regression: profile=LARGE + socket healthy + CEO_RAG_SIDECAR ABSENT
        → router returns AUTO_WIRE AND bridge now agrees → mode='rag+tfidf'.

        This is the exact P1 defect scenario: before the fix, router returned
        AUTO_WIRE but bridge._kill_switch_active() treated absent CEO_RAG_SIDECAR
        as disabled, causing rag_retrieve_skills() to return None and silently
        falling back to tf-idf.  After the fix, both agree and RAG is engaged.
        """
        import io
        import shutil
        sock_path = self._sock_path()
        self._write_large_profile()
        fake_results = [
            {"file": "core/security-and-auth/SKILL.md", "score": 0.93,
             "snippet": "auth jwt", "id": "security-and-auth"},
        ]
        try:
            with _FakeSidecar(sock_path, fake_results):
                # Explicitly absent CEO_RAG_SIDECAR (not set at all)
                # Router's CEO_RAG_SIDECAR_SOCKET needs to match the bridge's CEO_RAG_SOCKET
                env_without_rag = {
                    k: v for k, v in os.environ.items()
                    if k not in (
                        "CEO_RAG_SIDECAR",
                        "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED",
                        "CEO_RAG_SOCKET",
                        "CEO_RAG_SIDECAR_SOCKET",
                        "CEO_RAG_HEALTH_PROBE",
                    )
                }
                env_without_rag["CEO_RAG_SOCKET"] = str(sock_path)
                env_without_rag["CEO_RAG_SIDECAR_SOCKET"] = str(sock_path)
                env_without_rag["CEO_RAG_HEALTH_PROBE"] = "0"
                # CEO_RAG_SIDECAR is intentionally NOT set — verifying absent→enabled
                with patch.dict(os.environ, env_without_rag, clear=True):
                    rag_bridge._clear_session_state()
                    out = io.StringIO()
                    with patch("sys.stdout", out):
                        rc = retrieve_mod._cli([
                            "--task", "security authentication jwt",
                            "--repo-root", str(self.repo_root),
                            "--index-path", str(self.index_path),
                            "--json",
                        ])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            # Router+bridge now agree: mode must be 'rag+tfidf', not 'tfidf'
            self.assertEqual(
                payload.get("mode"), "rag+tfidf",
                f"Expected rag+tfidf mode but got '{payload.get('mode')}' — "
                "router and bridge may still disagree on absent CEO_RAG_SIDECAR",
            )
            slugs = {r["slug"] for r in payload["results"]}
            self.assertIn("security-and-auth", slugs)
        finally:
            shutil.rmtree(sock_path.parent, ignore_errors=True)

    def test_rag_events_emitted_on_rag_path(self) -> None:
        """rag_query_issued and rag_query_returned are emitted on the happy path."""
        sock_path = self._sock_path()
        self._write_large_profile()
        fake_results = [
            {"file": "core/testing-strategy/SKILL.md", "score": 0.85,
             "snippet": "pytest", "id": "testing-strategy"},
        ]
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        with _FakeSidecar(sock_path, fake_results):
            with patch.dict(os.environ, {
                "CEO_RAG_SIDECAR": "1",
                "CEO_RAG_SOCKET": str(sock_path),
                "CEO_RAG_HEALTH_PROBE": "0",
                "CEO_RAG_SIDECAR_SOCKET": str(sock_path),
            }):
                rag_bridge._clear_session_state()
                with patch("_lib.audit_emit.emit_generic", capture):
                    retrieve_mod._rag_retrieve("test coverage", self.repo_root, top_k=3)

        actions = [e.get("action") for e in emitted]
        self.assertIn("rag_query_issued", actions)
        # rag_query_routed emitted by router, rag_query_returned by bridge
        returned_or_routed = any(
            a in ("rag_query_returned", "rag_query_routed") for a in actions
        )
        self.assertTrue(returned_or_routed, f"Expected query_returned or routed in {actions}")


# ---------------------------------------------------------------------------
# (c) Cascade demotion events fire at the real decision points
# ---------------------------------------------------------------------------

class TestCascadeQualityEvents(unittest.TestCase):
    """rag_router.emit_cascade_quality() fires AC10/AC11 demotion events."""

    def setUp(self) -> None:
        rag_bridge._clear_session_state()
        # Force-restore the canonical _lib.audit_emit so the patch("_lib.
        # audit_emit.emit_*") targets resolve regardless of upstream test
        # ordering (combined hooks+scripts session). See the helper docstring.
        _restore_canonical_audit_emit()

    def test_false_large_demoted_fires_on_zero_results_for_large_profile(self) -> None:
        """AC10: profile=LARGE + zero chunks returned → rag_false_large_demoted."""
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        with patch("_lib.audit_emit.emit_rag_false_large_demoted", capture):
            rag_router.emit_cascade_quality(
                chunks_requested=5,
                chunks_returned=0,
                repo_profile_size="LARGE",
                window_days=7,
            )

        self.assertEqual(len(emitted), 1)
        call = emitted[0]
        self.assertEqual(call.get("false_large_rate_x100"), 100)
        self.assertEqual(call.get("window_days"), 7)

    def test_false_large_demoted_does_not_fire_for_non_large_profile(self) -> None:
        """AC10 gate: SMALL/MEDIUM profile → no demotion event even on zero results."""
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        for size in ("SMALL", "MEDIUM"):
            emitted.clear()
            with patch("_lib.audit_emit.emit_rag_false_large_demoted", capture):
                rag_router.emit_cascade_quality(
                    chunks_requested=5,
                    chunks_returned=0,
                    repo_profile_size=size,
                    window_days=7,
                )
            self.assertEqual(emitted, [], f"Should not fire for size={size}")

    def test_hit_rate_degraded_fires_when_below_floor(self) -> None:
        """AC11: hit_rate < 60% → rag_hit_rate_degraded emitted."""
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        # 2 of 5 returned → 40% hit rate (< 60% floor)
        with patch("_lib.audit_emit.emit_rag_hit_rate_degraded", capture):
            rag_router.emit_cascade_quality(
                chunks_requested=5,
                chunks_returned=2,
                repo_profile_size="LARGE",
                window_days=7,
            )

        self.assertEqual(len(emitted), 1)
        call = emitted[0]
        # 2/5 * 10000 = 4000
        self.assertEqual(call.get("hit_rate_x100"), 4000)
        self.assertEqual(call.get("window_days"), 7)

    def test_hit_rate_degraded_does_not_fire_when_above_floor(self) -> None:
        """AC11 gate: hit_rate ≥ 60% → no rag_hit_rate_degraded."""
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        # 5 of 5 returned → 100% hit rate
        with patch("_lib.audit_emit.emit_rag_hit_rate_degraded", capture):
            rag_router.emit_cascade_quality(
                chunks_requested=5,
                chunks_returned=5,
                repo_profile_size="LARGE",
                window_days=7,
            )

        self.assertEqual(emitted, [])

    def test_both_events_can_fire_simultaneously(self) -> None:
        """AC10 fires (0 chunks, LARGE) AND AC11 fires (0/5 = 0% < 60%) together."""
        false_large_calls: List[Dict] = []
        hit_rate_calls: List[Dict] = []

        def cap_fl(**kwargs: Any) -> None:
            false_large_calls.append(dict(kwargs))

        def cap_hr(**kwargs: Any) -> None:
            hit_rate_calls.append(dict(kwargs))

        with patch("_lib.audit_emit.emit_rag_false_large_demoted", cap_fl), \
             patch("_lib.audit_emit.emit_rag_hit_rate_degraded", cap_hr):
            rag_router.emit_cascade_quality(
                chunks_requested=5,
                chunks_returned=0,
                repo_profile_size="LARGE",
                window_days=7,
            )

        self.assertEqual(len(false_large_calls), 1)
        self.assertEqual(len(hit_rate_calls), 1)

    def test_emit_cascade_quality_fail_open_on_import_error(self) -> None:
        """emit_cascade_quality never raises even when audit_emit import fails."""
        # Temporarily mask the module
        original = sys.modules.get("_lib")
        try:
            sys.modules["_lib"] = None  # type: ignore[assignment]
            # Must not raise
            rag_router.emit_cascade_quality(
                chunks_requested=5,
                chunks_returned=0,
                repo_profile_size="LARGE",
            )
        finally:
            if original is None:
                sys.modules.pop("_lib", None)
            else:
                sys.modules["_lib"] = original

    def test_emit_cascade_quality_zero_requested_no_event(self) -> None:
        """No events when chunks_requested=0 (division by zero guard)."""
        emitted: List[Dict] = []

        def capture(**kwargs: Any) -> None:
            emitted.append(dict(kwargs))

        with patch("_lib.audit_emit.emit_rag_false_large_demoted", capture), \
             patch("_lib.audit_emit.emit_rag_hit_rate_degraded", capture):
            rag_router.emit_cascade_quality(
                chunks_requested=0,
                chunks_returned=0,
                repo_profile_size="LARGE",
            )

        self.assertEqual(emitted, [])


# ---------------------------------------------------------------------------
# rag_bridge.rag_retrieve_skills — input validation
# ---------------------------------------------------------------------------

class TestRagRetrieveSkillsInputValidation(unittest.TestCase):
    def setUp(self) -> None:
        rag_bridge._clear_session_state()

    def test_empty_task_returns_none(self) -> None:
        self.assertIsNone(rag_bridge.rag_retrieve_skills(""))
        self.assertIsNone(rag_bridge.rag_retrieve_skills("   "))

    def test_non_str_task_returns_none(self) -> None:
        self.assertIsNone(rag_bridge.rag_retrieve_skills(None))  # type: ignore[arg-type]
        self.assertIsNone(rag_bridge.rag_retrieve_skills(42))    # type: ignore[arg-type]

    def test_absent_sidecar_env_no_socket_returns_none(self) -> None:
        """Absent CEO_RAG_SIDECAR (bridge enabled) + no socket → None (fail-open).

        Under the unified contract, absent CEO_RAG_SIDECAR enables the bridge
        (conditional-default-on, ADR-062-AMEND-1).  The result is None because
        no sidecar socket exists — not because of a kill-switch.  This confirms
        the zero-regression fallback path is intact.
        """
        clean_env = {k: v for k, v in os.environ.items() if k not in (
            "CEO_RAG_SIDECAR", "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED",
        )}
        with patch.dict(os.environ, clean_env, clear=True):
            rag_bridge._clear_session_state()
            result = rag_bridge.rag_retrieve_skills("some task", top_k=3)
        self.assertIsNone(result)

    def test_invalid_top_k_normalised(self) -> None:
        """top_k=0 or negative is normalised to 5 — no crash."""
        with patch.dict(os.environ, {"CEO_RAG_SIDECAR": "1", "CEO_RAG_SOCKET": "/tmp/no.sock"}):
            rag_bridge._clear_session_state()
            # Should return None (socket missing) but not raise
            result = rag_bridge.rag_retrieve_skills("task", top_k=0)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
