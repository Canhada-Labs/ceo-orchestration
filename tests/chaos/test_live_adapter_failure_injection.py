"""Chaos tests — live LLM adapter failure injection (PLAN-012 Phase 1 D3.4).
ADR-040 §1-§7 vs local mocks. 5 modes x 3 providers (15 base) + meta
redaction. CEO_CHAOS_ALLOWED=1 gate. URL injection via constructor
kwarg (Wave 2 chose ctor-arg not env): Claude `url=`, Gemini `base_url=`,
OpenAI `chat_url=`. provider_name slugs: anthropic/google/openai.
"""
from __future__ import annotations
import importlib, json, os, socket, sys, threading, time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Iterator, List
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_CHAOS_ALLOWED") != "1",
    reason="Chaos tests gated by CEO_CHAOS_ALLOWED=1 per ADR-037",
)
_HOOKS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

PROVIDERS: List[Dict[str, str]] = [
    {"label": "claude", "provider_name": "anthropic", "activation_env": "CEO_LIVE_CLAUDE",
     "key_env": "ANTHROPIC_API_KEY", "key_value": "sk-ant-test-fake-DEADBEEFCAFE0001",
     "url_kwarg": "url", "module": "_lib.adapters.live.claude", "class_name": "ClaudeLiveAdapter"},
    {"label": "gemini", "provider_name": "google", "activation_env": "CEO_LIVE_GEMINI",
     "key_env": "GOOGLE_API_KEY", "key_value": "AIzaTestFakeKey0123456789ABCDEFGHIJ012345",
     "url_kwarg": "base_url", "module": "_lib.adapters.live.gemini", "class_name": "GeminiLiveAdapter"},
    {"label": "openai", "provider_name": "openai", "activation_env": "CEO_LIVE_OPENAI",
     "key_env": "OPENAI_API_KEY", "key_value": "sk-proj-test-fake-DEADBEEFCAFE000200030004",
     "url_kwarg": "chat_url", "module": "_lib.adapters.live.openai", "class_name": "OpenAILiveAdapter"},
]
PIDS = [p["label"] for p in PROVIDERS]


def _make_adapter(p: Dict[str, str], url: str):
    """xfail (not skip) if Wave 2 not landed — visible at review.
    Wave 2 chose constructor injection over env override; pass the
    mock URL via the provider's URL kwarg.
    """
    try:
        mod = importlib.import_module(p["module"])
    except ImportError as e:
        pytest.xfail(f"{p['module']} not importable: {e}")
    cls = getattr(mod, p["class_name"], None)
    if cls is None:
        pytest.xfail(f"{p['class_name']} not present yet")
    # Gemini's _BASE_URL is a template with {model}; preserve that.
    if p["url_kwarg"] == "base_url":
        return cls(base_url=url + "/v1beta/models/{model}:generateContent")
    return cls(**{p["url_kwarg"]: url})


class _S(BaseHTTPRequestHandler):
    """Silent base; records on server.request_log."""
    def log_message(self, format, *args): pass  # noqa: A002
    def _record(self):
        clen = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(clen) if clen else b""
        self.server.request_log.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})  # type: ignore[attr-defined]
    def _reply(self, status: int, body: bytes, extra=None):
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)


class _H502(_S):
    def do_POST(self): self._record(); self._reply(502, b'{"error":"bad_gateway"}')  # noqa: N802

class _HSlow(_S):
    def do_POST(self):  # noqa: N802
        self._record()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.flush()
        time.sleep(15)  # > 8s read timeout (ADR-040 §1)
        self.wfile.write(b'{"late":"body"}')

class _HGarbage(_S):
    def do_POST(self): self._record(); self._reply(200, b'{"invalid": truncated')  # noqa: N802

class _H401(_S):
    def do_POST(self): self._record(); self._reply(401, b'{"error":"invalid_key"}')  # noqa: N802

class _H429(_S):
    def do_POST(self): self._record(); self._reply(429, b'{"error":"rate_limit"}', {"Retry-After": "0"})  # noqa: N802

class _HEcho(_S):
    """Echoes request headers — credential leak attempt."""
    def do_POST(self):  # noqa: N802
        self._record()
        self._reply(200, json.dumps({"echoed_headers": dict(self.headers.items())}).encode("utf-8"))


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close(); return port


@contextmanager
def _serve(handler_cls):
    """Start mock server; auto-stop on context exit (no try/finally per test)."""
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


def _activate(p: Dict[str, str]) -> None:
    """Set activation + credential env. URL injection is via constructor."""
    os.environ[p["activation_env"]] = "1"
    os.environ[p["key_env"]] = p["key_value"]
    os.environ["CEO_LIVE_ADAPTER_ALLOWLIST"] = p["label"]


def _audit_text(env_ctx: TestEnvContext) -> str:
    p = env_ctx.audit_dir / "audit-log.jsonl"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _MSG(text="hi"): return [{"role": "user", "content": text}]


# Mode 1 — 502 → server_error + retry; 6th of 5 opens breaker
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_mode_502_server_error_with_retry(env_ctx, p):
    with _serve(_H502) as (srv, url):
        _activate(p); a = _make_adapter(p, url)
        r = a.call(messages=_MSG(), model="test", max_tokens=10)
        assert r.success is False
        assert r.failure_mode == "server_error", f"{p['label']}: got {r.failure_mode!r}"
        assert r.retry_count == 1
        assert r.http_status == 502
        assert r.provider == p["provider_name"]
        assert len(srv.request_log) >= 2  # original + retry


def test_mode_502_breaker_opens_on_threshold(env_ctx):
    p = PROVIDERS[0]
    with _serve(_H502) as (srv, url):
        _activate(p); a = _make_adapter(p, url)
        for i in range(5):
            r = a.call(messages=_MSG("x"), model="test", max_tokens=5)
            assert r.failure_mode in {"server_error", "breaker_open"}, f"call {i}: {r.failure_mode!r}"
        before = len(srv.request_log)
        r6 = a.call(messages=_MSG("y"), model="test", max_tokens=5)
        assert r6.failure_mode == "breaker_open"
        assert r6.breaker_state == "open"
        assert len(srv.request_log) == before, "breaker_open MUST NOT touch network"


# Mode 2 — slow body → read_timeout/timeout, duration ≈ 8s
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_mode_slow_body_read_timeout(env_ctx, p):
    with _serve(_HSlow) as (_srv, url):
        _activate(p); a = _make_adapter(p, url)
        t0 = time.monotonic()
        r = a.call(messages=_MSG(), model="test", max_tokens=10)
        wall_ms = (time.monotonic() - t0) * 1000
        assert r.success is False
        # SPEC §3 says "read_timeout"; task says "timeout" — accept either.
        assert r.failure_mode in {"read_timeout", "timeout"}, f"{p['label']}: got {r.failure_mode!r}"
        assert r.duration_ms >= 7000, f"duration_ms={r.duration_ms}"
        assert wall_ms < 30_000, f"runaway test: {wall_ms:.0f}ms"  # 8s rd + retry + jitter


# Mode 3 — garbage JSON → parse_error, no retry, breaker stays closed
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_mode_garbage_json_no_retry_no_breaker(env_ctx, p):
    with _serve(_HGarbage) as (_srv, url):
        _activate(p); a = _make_adapter(p, url)
        r = a.call(messages=_MSG(), model="test", max_tokens=10)
        assert r.success is False
        assert r.failure_mode == "parse_error", f"{p['label']}: got {r.failure_mode!r}"
        assert r.retry_count == 0, "parse errors must NOT retry"
        assert r.breaker_state == "closed", "parse errors must NOT count toward breaker"


# Mode 4 — 401 → auth_permanent, breaker open immediately, no retry
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_mode_401_auth_permanent_immediate_open(env_ctx, p):
    with _serve(_H401) as (srv, url):
        _activate(p); a = _make_adapter(p, url)
        r = a.call(messages=_MSG(), model="test", max_tokens=10)
        assert r.success is False
        assert r.failure_mode == "auth_permanent", f"{p['label']}: got {r.failure_mode!r}"
        assert r.retry_count == 0
        assert r.breaker_state == "open"
        before = len(srv.request_log)
        r2 = a.call(messages=_MSG("x"), model="test", max_tokens=5)
        assert r2.failure_mode == "breaker_open"
        assert len(srv.request_log) == before, "post-401 leaked to network"


# Mode 5 — 429 → rate_limited, retry once, counts toward breaker
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_mode_429_rate_limited_with_retry(env_ctx, p):
    with _serve(_H429) as (srv, url):
        _activate(p); a = _make_adapter(p, url)
        r = a.call(messages=_MSG(), model="test", max_tokens=10)
        assert r.success is False
        assert r.failure_mode in {"rate_limit", "rate_limited"}, f"{p['label']}: got {r.failure_mode!r}"
        assert r.retry_count == 1
        assert r.http_status == 429
        assert len(srv.request_log) >= 2


# Meta — credential MUST NOT appear in audit log
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_redaction_key_not_in_audit_log(env_ctx, p):
    with _serve(_H502) as (_srv, url):
        _activate(p); a = _make_adapter(p, url)
        a.call(messages=_MSG(), model="test", max_tokens=5)
        log = _audit_text(env_ctx)
        assert p["key_value"] not in log, f"{p['label']}: credential leaked to audit"


# Meta — server echoes headers; credential MUST NOT reach result.text or audit
@pytest.mark.parametrize("p", PROVIDERS, ids=PIDS)
def test_no_credential_in_response_echo(env_ctx, p):
    with _serve(_HEcho) as (_srv, url):
        _activate(p); a = _make_adapter(p, url)
        r = a.call(messages=_MSG(), model="test", max_tokens=5)
        if r.text is not None:
            assert p["key_value"] not in r.text, f"{p['label']}: credential in result.text"
        log = _audit_text(env_ctx)
        assert p["key_value"] not in log, f"{p['label']}: credential leaked via echo→audit"


def test_chaos_env_does_not_leak_real_home(env_ctx):
    home = os.environ.get("HOME", "")
    assert "ceo-hook-test-" in home or "/tmp" in home or "/var/" in home, f"real $HOME leaked: {home!r}"
    assert os.environ.get("CEO_CHAOS_ALLOWED") == "1"
