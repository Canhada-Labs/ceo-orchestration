"""MCP Server entry point — CEO_SOTA_DISABLE gate, transport selection, audit.

Framework's first inbound public-boundary surface per ADR-042. This
module is intentionally thin: it orchestrates the kill-switch gate,
emits startup audit events, and hands off to either
:mod:`http_transport` or :mod:`stdio_transport` for the actual
request loop.

## Entry flow

1. **Kill-switch check** FIRST (before binding port / opening stdio):
   ``CEO_SOTA_DISABLE=1`` → emit
   ``mcp_server_disabled_by_kill_switch`` + exit 0. Mirrors ADR-040
   §6 activation gate.
2. **Project dir resolution** from ``CLAUDE_PROJECT_DIR`` env or
   script location.
3. **Transport selection** from ``CEO_MCP_TRANSPORT`` (default
   ``http``).
4. **Startup emit** — ``mcp_server_started`` event with transport,
   host, port, version, handlers_count.
5. **Dispatch** to transport-specific run loop.

## Env vars

| Var | Default | Effect |
|---|---|---|
| ``CEO_SOTA_DISABLE`` | unset | ``=1`` disables the server |
| ``CEO_MCP_TRANSPORT`` | ``http`` | ``http`` or ``stdio`` |
| ``CEO_MCP_HOST`` | ``127.0.0.1`` | HTTP bind host (never 0.0.0.0 by default) |
| ``CEO_MCP_PORT`` | ``9000`` | HTTP port |
| ``CEO_MCP_ALLOW_PUBLIC`` | unset | ``=1`` allows 0.0.0.0 bind (dangerous) |
| ``CLAUDE_PROJECT_DIR`` | script location | Project root for settings + state |
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Tuple

# Bootstrap sys.path BEFORE internal imports.
_SERVER_DIR = Path(__file__).resolve().parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
_PROJECT_DIR = _CLAUDE_DIR.parent

for _p in (_SERVER_DIR, _SERVER_DIR / "handlers", _HOOKS_DIR):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib import audit_emit  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402
import http_transport  # type: ignore[import-not-found]  # noqa: E402
import stdio_transport  # type: ignore[import-not-found]  # noqa: E402


SERVER_VERSION = "1.0.0-rc.1"
KILL_SWITCH_ENV = "CEO_SOTA_DISABLE"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000


def _kill_switch_active(env: Optional[dict] = None) -> bool:
    """Return True iff ``CEO_SOTA_DISABLE=1`` in env."""
    src = env if env is not None else os.environ
    return (src.get(KILL_SWITCH_ENV) or "").strip() == "1"


def _resolve_project_dir() -> Path:
    """Return the project_dir, preferring ``CLAUDE_PROJECT_DIR`` env."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return _PROJECT_DIR


def _resolve_transport() -> str:
    """Read CEO_MCP_TRANSPORT env var. Defaults to ``http``."""
    t = os.environ.get("CEO_MCP_TRANSPORT", "http").strip().lower()
    return t if t in ("http", "stdio") else "http"


def _resolve_host_port() -> Tuple[str, int]:
    """Read CEO_MCP_HOST + CEO_MCP_PORT env vars.

    Default 127.0.0.1:9000. ``0.0.0.0`` is rejected unless
    ``CEO_MCP_ALLOW_PUBLIC=1`` is explicitly set. Malformed port →
    default.
    """
    host = os.environ.get("CEO_MCP_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port_raw = os.environ.get("CEO_MCP_PORT", str(DEFAULT_PORT)).strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = DEFAULT_PORT
    if port <= 0 or port > 65535:
        port = DEFAULT_PORT
    if host == "0.0.0.0":
        if os.environ.get("CEO_MCP_ALLOW_PUBLIC", "").strip() != "1":
            host = DEFAULT_HOST
    return host, port


def run(project_dir: Optional[Path] = None) -> int:
    """Main entry point.

    1. Kill-switch check FIRST (before binding port / opening stdio).
    2. Emit startup event.
    3. Dispatch to transport.

    Returns process exit code.
    """
    if _kill_switch_active():
        try:
            audit_emit.emit_mcp_server_disabled_by_kill_switch(
                reason=f"{KILL_SWITCH_ENV}=1",
                project=str(project_dir or _resolve_project_dir()),
            )
        except Exception:
            pass
        sys.stderr.write(
            f"[mcp-server] {KILL_SWITCH_ENV}=1 — server disabled. Exiting 0.\n"
        )
        return 0

    project = project_dir or _resolve_project_dir()
    transport = _resolve_transport()

    if transport == "stdio":
        try:
            audit_emit.emit_mcp_server_started(
                transport="stdio",
                host="",
                port=0,
                version=SERVER_VERSION,
                handlers_count=len(dispatch.HANDLERS),
                project=str(project),
            )
        except Exception:
            pass
        stdio_transport.run(project)
        return 0

    host, port = _resolve_host_port()
    try:
        audit_emit.emit_mcp_server_started(
            transport="http",
            host=host,
            port=port,
            version=SERVER_VERSION,
            handlers_count=len(dispatch.HANDLERS),
            project=str(project),
        )
    except Exception:
        pass

    try:
        server = http_transport.make_server(host, port, project)
    except http_transport.TransportSecurityError as e:
        # P2-SEC-K: refuse to start with an invalid transport posture.
        sys.stderr.write(
            f"[mcp-server] TRANSPORT SECURITY: {e}\n"
            f"[mcp-server] refusing to start. See P2-SEC-K.\n"
        )
        return 2
    # Use scheme that matches actual transport.
    scheme = "https" if os.environ.get("CEO_MCP_TLS_CERT") else "http"
    sys.stderr.write(
        f"[mcp-server] listening on {scheme}://{host}:{port}/rpc (version={SERVER_VERSION})\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[mcp-server] interrupted; shutting down.\n")
        server.shutdown()
    finally:
        try:
            server.server_close()
        except Exception:
            pass
    return 0


# Re-export for backward-compat with tests that imported from server.
HANDLERS = dispatch.HANDLERS
_McpHTTPHandler = http_transport.McpHTTPHandler  # backwards-compat alias


def _run_stdio(
    project_dir: Path,
    *,
    stdin=None,
    stdout=None,
) -> None:
    """Backward-compat shim — forwards to :func:`stdio_transport.run`."""
    stdio_transport.run(project_dir, stdin=stdin, stdout=stdout)


def main() -> int:
    """CLI entry. Exits with the return value of :func:`run`."""
    try:
        return run()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
