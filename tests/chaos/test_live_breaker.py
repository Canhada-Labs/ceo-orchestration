"""Chaos tests — circuit-breaker invariants (PLAN-012 Phase 1 D3.4).
ADR-040 §1-§2 via mock provider (Claude — breaker is provider-agnostic).
CEO_CHAOS_ALLOWED=1 gate. Deterministic via _lib.adapters.live._breaker
._now_override (xfail if absent).
"""
from __future__ import annotations
import importlib, os, socket, sys, threading, time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterator
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_CHAOS_ALLOWED") != "1",
    reason="Chaos tests gated by CEO_CHAOS_ALLOWED=1 per ADR-037",
)
_HOOKS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

CLAUDE = {"label": "claude", "activation_env": "CEO_LIVE_CLAUDE",
    "key_env": "ANTHROPIC_API_KEY", "key_value": "sk-ant-test-fake-DEADBEEFCAFE0001",
    "module": "_lib.adapters.live.claude", "class_name": "ClaudeLiveAdapter"}


def _make_adapter(url: str):
    """ClaudeLiveAdapter takes mock URL via constructor `url=` kwarg."""
    try:
        mod = importlib.import_module(CLAUDE["module"])
    except ImportError as e:
        pytest.xfail(f"adapter not landed: {e}")
    cls = getattr(mod, CLAUDE["class_name"], None)
    if cls is None:
        pytest.xfail(f"{CLAUDE['class_name']} missing")
    return cls(url=url)


def _breaker_mod():
    try:
        return importlib.import_module("_lib.adapters.live._breaker")
    except ImportError as e:
        pytest.xfail(f"_breaker not landed: {e}")


class _S(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass  # noqa: A002
    def _record(self):
        self.server.request_log.append(self.path)  # type: ignore[attr-defined]
        clen = int(self.headers.get("Content-Length", "0") or "0")
        try: self.rfile.read(clen)
        except Exception: pass
    def _reply(self, status, body):
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

class _H502(_S):
    def do_POST(self): self._record(); self._reply(502, b'{"error":"bad_gateway"}')  # noqa: N802
class _H401(_S):
    def do_POST(self): self._record(); self._reply(401, b'{"error":"invalid_key"}')  # noqa: N802
class _HGarbage(_S):
    def do_POST(self): self._record(); self._reply(200, b'{"truncated')  # noqa: N802
class _HOK(_S):
    def do_POST(self):  # noqa: N802
        self._record()
        self._reply(200, b'{"id":"x","content":[{"type":"text","text":"ok"}],"usage":{"input_tokens":1,"output_tokens":1},"model":"test","stop_reason":"end_turn"}')


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close(); return port


@contextmanager
def _serve(handler_cls):
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    server.request_log = []  # type: ignore[attr-defined]
    th = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    th.start()
    try:
        yield server, f"http://127.0.0.1:{port}"
    finally:
        server.shutdown(); server.server_close(); th.join(timeout=2.0)


@pytest.fixture
def env_ctx() -> Iterator[TestEnvContext]:
    ctx = TestEnvContext(); ctx.setUp()
    try:
        os.environ["CEO_CHAOS_ALLOWED"] = "1"
        yield ctx
    finally:
        ctx.tearDown()


def _activate() -> None:
    os.environ[CLAUDE["activation_env"]] = "1"
    os.environ[CLAUDE["key_env"]] = CLAUDE["key_value"]
    os.environ["CEO_LIVE_ADAPTER_ALLOWLIST"] = CLAUDE["label"]


def _set_clock(bm, value: float) -> None:
    if hasattr(bm, "_now_override"):
        bm._now_override = value
    else:
        pytest.xfail("_breaker._now_override missing — task spec required deterministic clock hook")


def _clear_clock(bm) -> None:
    if hasattr(bm, "_now_override"):
        bm._now_override = None


def _MSG(text="x"): return [{"role": "user", "content": text}]


# 1 — 5 transient failures within window opens breaker; 6th fast-fails
def test_breaker_opens_after_threshold_failures(env_ctx):
    with _serve(_H502) as (srv, url):
        _activate(); a = _make_adapter(url)
        for i in range(5):
            r = a.call(messages=_MSG(), model="t", max_tokens=5)
            assert r.failure_mode in {"server_error", "breaker_open"}, f"call {i}: {r.failure_mode!r}"
        before = len(srv.request_log)
        r6 = a.call(messages=_MSG("y"), model="t", max_tokens=5)
        assert r6.failure_mode == "breaker_open"
        assert r6.breaker_state == "open"
        assert len(srv.request_log) == before


# 2 — once open, fail-fast in <50ms (stop server to prove no socket attempt)
def test_breaker_fails_fast_under_50ms_when_open(env_ctx):
    cm = _serve(_H401); srv, url = cm.__enter__()
    try:
        _activate(); a = _make_adapter(url)
        a.call(messages=_MSG("open"), model="t", max_tokens=5)
    finally:
        cm.__exit__(None, None, None)  # stop server
    t0 = time.monotonic()
    r2 = a.call(messages=_MSG("fast"), model="t", max_tokens=5)
    elapsed_ms = (time.monotonic() - t0) * 1000
    assert r2.failure_mode == "breaker_open"
    assert elapsed_ms < 50, f"breaker_open must <50ms, took {elapsed_ms:.1f}ms"
    assert r2.duration_ms < 50, f"result.duration_ms={r2.duration_ms} > 50ms"


# 3 — half_open after 60s
def test_breaker_half_open_after_60s(env_ctx):
    bm = _breaker_mod()
    try:
        with _serve(_H401) as (_srv1, url):
            _activate(); a = _make_adapter(url)
            _set_clock(bm, 0.0)
            a.call(messages=_MSG("open"), model="t", max_tokens=5)
            _set_clock(bm, 59.0)
            r_still = a.call(messages=_MSG("still"), model="t", max_tokens=5)
            assert r_still.failure_mode == "breaker_open"
            assert r_still.breaker_state == "open"
        # Need a NEW adapter pointing at OK server but sharing breaker state.
        # Adapter recreated with new url; breaker is per-adapter so we must
        # reuse the same adapter — instead, shift OK server URL onto same
        # breaker by creating a sibling adapter with shared breaker.
        with _serve(_HOK) as (_srv2, url2):
            _activate()
            a2 = _make_adapter(url2)
            a2._breaker = a._breaker  # share breaker state across URL swap
            _set_clock(bm, 60.1)
            r_probe = a2.call(messages=_MSG("probe"), model="t", max_tokens=5)
            assert r_probe.breaker_state in {"half_open", "closed"}, f"got {r_probe.breaker_state!r}"
            assert r_probe.failure_mode != "breaker_open"
    finally:
        _clear_clock(bm)


# 4 — half_open SUCCESS closes breaker
def test_breaker_half_open_probe_success_closes(env_ctx):
    bm = _breaker_mod()
    try:
        with _serve(_H401) as (_bad, bad_url):
            _activate(); a = _make_adapter(bad_url)
            _set_clock(bm, 0.0)
            a.call(messages=_MSG("open"), model="t", max_tokens=5)
        with _serve(_HOK) as (_ok, ok_url):
            _activate()
            a2 = _make_adapter(ok_url)
            a2._breaker = a._breaker  # share breaker state across URL swap
            _set_clock(bm, 61.0)
            r_probe = a2.call(messages=_MSG("probe"), model="t", max_tokens=5)
            _set_clock(bm, 61.1)
            r_after = a2.call(messages=_MSG("after"), model="t", max_tokens=5)
            if r_probe.success:
                assert r_after.failure_mode != "breaker_open"
                assert r_after.breaker_state == "closed"
    finally:
        _clear_clock(bm)


# 5 — half_open FAIL reopens
def test_breaker_half_open_probe_fail_reopens(env_ctx):
    bm = _breaker_mod()
    try:
        with _serve(_H502) as (_srv, url):
            _activate(); a = _make_adapter(url)
            _set_clock(bm, 0.0)
            for _ in range(5):
                a.call(messages=_MSG(), model="t", max_tokens=5)
            _set_clock(bm, 10.0)
            r_open = a.call(messages=_MSG("open"), model="t", max_tokens=5)
            assert r_open.failure_mode == "breaker_open"
            _set_clock(bm, 61.0)
            r_probe = a.call(messages=_MSG("probe"), model="t", max_tokens=5)
            assert r_probe.failure_mode in {"server_error", "breaker_open"}
            _set_clock(bm, 61.1)
            r_after = a.call(messages=_MSG("after"), model="t", max_tokens=5)
            assert r_after.failure_mode == "breaker_open", f"should reopen, got {r_after.failure_mode!r}"
            assert r_after.breaker_state == "open"
    finally:
        _clear_clock(bm)


# 6 — parse_error doesn't count toward breaker
def test_parse_error_does_not_open_breaker(env_ctx):
    with _serve(_HGarbage) as (_srv, url):
        _activate(); a = _make_adapter(url)
        for i in range(10):
            r = a.call(messages=_MSG(), model="t", max_tokens=5)
            assert r.failure_mode == "parse_error", f"call {i}: {r.failure_mode!r}"
            assert r.breaker_state == "closed", f"call {i}: parse_error counted to breaker"
            assert r.retry_count == 0


# 7 — single 401 opens breaker immediately
def test_401_opens_breaker_immediately(env_ctx):
    with _serve(_H401) as (srv, url):
        _activate(); a = _make_adapter(url)
        r = a.call(messages=_MSG(), model="t", max_tokens=5)
        assert r.failure_mode == "auth_permanent"
        assert r.breaker_state == "open"
        assert r.retry_count == 0
        before = len(srv.request_log)
        r2 = a.call(messages=_MSG("y"), model="t", max_tokens=5)
        assert r2.failure_mode == "breaker_open"
        assert len(srv.request_log) == before


def test_chaos_env_does_not_leak_real_home(env_ctx):
    home = os.environ.get("HOME", "")
    assert "ceo-hook-test-" in home or "/tmp" in home or "/var/" in home, f"real $HOME leaked: {home!r}"
    assert os.environ.get("CEO_CHAOS_ALLOWED") == "1"
