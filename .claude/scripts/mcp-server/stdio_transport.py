"""stdio transport for the MCP server (ADR-042 §Transport).

Reads newline-delimited JSON-RPC 2.0 envelopes from stdin, writes
newline-delimited responses to stdout. Auth fields live in
``params.authorization`` + ``params.timestamp_ms`` + optional
``params.session_id`` — stdio has no transport-level headers.

Auth fields are STRIPPED from ``params`` before the handler sees
them (ADR-042 §Auth.6 hygiene).

Single-threaded by construction — one request, one response. This
matches the MCP spec's stdio contract: each message is a complete
JSON value on its own line.

## PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — remote_addr sentinel

The stdio transport has NO network remote address (it is a local
pipe). The replay store's loopback gate would DENY a missing/empty
address, so this transport passes the ``"stdio-local"`` sentinel
(``dispatch.bearer_replay.STDIO_LOCAL_ADDR``) into
``authenticate(remote_addr=...)``; the store whitelists that sentinel
as loopback-equivalent trust (§3a).
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, TextIO

_SERVER_DIR = Path(__file__).resolve().parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

import auth  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402


def _extract_auth(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Remove auth-only fields from envelope.params so handlers see clean params.

    Returns a new envelope dict with clean params; the original is
    not mutated. This prevents any downstream handler from seeing the
    bearer token or timestamp (ADR-042 §Auth.6 hygiene).
    """
    params = envelope.get("params") or {}
    if not isinstance(params, dict):
        return envelope
    clean = {
        k: v for k, v in params.items()
        if k not in ("authorization", "timestamp_ms", "session_id")
    }
    return {**envelope, "params": clean}


def run(
    project_dir: Path,
    *,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> None:
    """stdio transport main loop.

    Test callers inject ``stdin`` / ``stdout`` streams; production
    uses ``sys.stdin`` / ``sys.stdout``. Loop exits when stdin is
    closed (EOF) or exhausted.
    """
    in_stream = stdin or sys.stdin
    out_stream = stdout or sys.stdout
    project = str(project_dir)

    for raw_line in in_stream:
        line = raw_line.strip()
        if not line:
            continue
        envelope, err_resp = dispatch.parse_envelope(line)
        if err_resp is not None:
            out_stream.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            out_stream.flush()
            continue
        assert envelope is not None

        params = envelope.get("params") or {}
        if not isinstance(params, dict):
            out_stream.write(
                json.dumps(
                    dispatch.rpc_error(
                        envelope.get("id"), dispatch.ERR_INVALID_PARAMS, "Invalid params"
                    ),
                    ensure_ascii=False,
                )
                + "\n"
            )
            out_stream.flush()
            continue

        raw_token = params.get("authorization")
        if not isinstance(raw_token, str):
            raw_token = None
        timestamp_ms = params.get("timestamp_ms", "")
        session_id_raw = params.get("session_id")
        session_id = session_id_raw if isinstance(session_id_raw, str) and session_id_raw else str(uuid.uuid4())

        clean_env = _extract_auth(envelope)

        ctx, deny_reason, _retry_ms = dispatch.authenticate(
            raw_token=raw_token,
            timestamp_ms=timestamp_ms,
            method=envelope["method"],
            origin=None,
            transport="stdio",
            session_id=session_id,
            project_dir=project_dir,
            remote_addr=dispatch.bearer_replay.STDIO_LOCAL_ADDR,
        )

        if deny_reason is not None:
            client_id_for_audit = ""
            if raw_token:
                parsed = auth.parse_token(raw_token)
                if parsed is not None:
                    client_id_for_audit = parsed["client_id"]
            dispatch.emit_deny(
                handler=envelope["method"],
                client_id=client_id_for_audit,
                transport="stdio",
                reason=deny_reason,
                session_id=session_id,
                project=project,
            )
            code = dispatch.DENY_CODE_MAP.get(deny_reason, dispatch.ERR_APP_AUTH)
            out_stream.write(
                json.dumps(
                    dispatch.rpc_error(envelope.get("id"), code, deny_reason),
                    ensure_ascii=False,
                )
                + "\n"
            )
            out_stream.flush()
            continue

        assert ctx is not None
        response = dispatch.dispatch(clean_env, ctx, project)
        out_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
        out_stream.flush()


__all__ = ["run"]
