"""Dispatch pipeline: envelope parse, authenticate, handler dispatch.

This module isolates the transport-agnostic request flow so both the
HTTP transport (``http_transport.py``) and stdio transport
(``stdio_transport.py``) share a single implementation.

Per ADR-042 §Auth the request pipeline is:

1. Parse JSON-RPC 2.0 envelope.
2. Extract bearer token (transport-specific — provided by caller).
3. Parse token format.
4. Load client registry from settings.json.
5. Load per-client secret.
6. Verify HMAC-SHA256 (constant-time).
7. Verify timestamp skew (±60s).
7b. Replay defense — BearerReplayStore.check_request (POST-HMAC).
8. Check ACL.
9. CORS (HTTP only).
10. Rate limit.
11. Dispatch to handler.
12. Emit audit event (invoked/denied).

Module exposes three entry points:

- :func:`parse_envelope` — envelope validation.
- :func:`authenticate` — steps 3-10 (auth + replay + ACL + rate limit).
- :func:`dispatch` — step 11-12 (handler + audit).

Both transports compose these in order. The dispatch module holds no
module-level mutable state except the handler registry and the
per-process bearer replay store; bucket state lives in ``rate_limit.py``.

## PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — replay + friction wire-up

- Replay defense (``_lib.mcp.bearer_replay.BearerReplayStore``) is
  invoked POST-HMAC (after ``verify_hmac`` + ``verify_timestamp_skew``)
  so an unauthenticated request can never poison/grow the nonce store
  (CWE-770 DoS — security P0). The token's wall-clock ``timestamp_ms``
  is converted to ns (``iat_ns = ts_int * 1_000_000``) so it shares the
  store's wall-clock domain (clock reconcile — identity-trust P1). The
  ``remote_addr`` is threaded in from the transport: HTTP passes
  ``client_address[0]``; stdio passes the ``"stdio-local"`` sentinel
  (whitelisted in the store).
- Friction telemetry (``_lib.mcp_bearer_friction.observe_auth_failure``)
  is recorded on EVERY auth-failure branch + the replay DENYs. It is
  NON-BLOCKING (bounded deque + retry-window dedup); the buffer is
  drained ONCE at the end of ``authenticate`` (mandatory per-request
  drain, atexit is backup) so the emit cost is off the per-branch path
  while still firing from the request path.
- Audit routing: replay/stale DENYs → ``mcp_bearer_replay_rejected``;
  ``DENY_NON_LOOPBACK`` → existing ``mcp_non_loopback_rejected``.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# Bootstrap sys.path so internal modules load regardless of caller.
_SERVER_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _SERVER_DIR.parent.parent / "hooks"
for _p in (_SERVER_DIR, _SERVER_DIR / "handlers", _HOOKS_DIR):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

import auth  # type: ignore[import-not-found]  # noqa: E402
import rate_limit  # type: ignore[import-not-found]  # noqa: E402
from handlers import list_skills as h_list_skills  # type: ignore[import-not-found]  # noqa: E402
from handlers import get_skill as h_get_skill  # type: ignore[import-not-found]  # noqa: E402
from handlers import list_agents as h_list_agents  # type: ignore[import-not-found]  # noqa: E402
from handlers import list_pitfalls as h_list_pitfalls  # type: ignore[import-not-found]  # noqa: E402
from handlers import get_audit_log as h_get_audit_log  # type: ignore[import-not-found]  # noqa: E402
from handlers import spawn_agent as h_spawn_agent  # type: ignore[import-not-found]  # noqa: E402
from handlers import server_capabilities as h_server_capabilities  # type: ignore[import-not-found]  # noqa: E402
# PLAN-096 Wave A/B/C/D — read-only MCP expansion (ADR-042-AMEND-1).
from handlers import audit_query as h_audit_query  # type: ignore[import-not-found]  # noqa: E402
from handlers import plan_status as h_plan_status  # type: ignore[import-not-found]  # noqa: E402
from handlers import get_debate_state as h_get_debate_state  # type: ignore[import-not-found]  # noqa: E402
from handlers import get_cost_budget as h_get_cost_budget  # type: ignore[import-not-found]  # noqa: E402
from _lib import audit_emit  # noqa: E402
# PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — replay defense + friction.
from _lib.mcp import bearer_replay  # noqa: E402
from _lib import mcp_bearer_friction  # noqa: E402


# JSON-RPC 2.0 error codes.
ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603
ERR_APP_AUTH = -32001
ERR_APP_ACL = -32002
ERR_APP_RATE_LIMIT = -32003
ERR_APP_CORS = -32004
ERR_APP_TIMESTAMP = -32005
ERR_APP_BUDGET = -32006


# Handler registry — method name → (handler_class, handle_fn).
HANDLERS: Dict[str, Tuple[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]]] = {
    "list_skills": ("readonly", h_list_skills.handle),
    "get_skill": ("readonly", h_get_skill.handle),
    "list_agents": ("readonly", h_list_agents.handle),
    "list_pitfalls": ("readonly", h_list_pitfalls.handle),
    "get_audit_log": ("audit_read", h_get_audit_log.handle),
    "spawn_agent": ("spawn", h_spawn_agent.handle),
    "server.capabilities": ("readonly", h_server_capabilities.handle),
    # PLAN-096 Wave B — plan-status MCP methods (ADR-042-AMEND-1).
    "list_plans": ("readonly", h_plan_status.handle_list_plans),
    "get_plan": ("readonly", h_plan_status.handle_get_plan),
    "get_plan_acs": ("readonly", h_plan_status.handle_get_plan_acs),
    "get_plan_dependencies": ("readonly", h_plan_status.handle_get_plan_dependencies),
    # PLAN-096 Wave C — debate-status (snapshot-only post-sentinel; AC4).
    "get_debate_state": ("debate_read", h_get_debate_state.handle),
    # PLAN-096 Wave D — cost-budget stub-mode pre-PLAN-102 (AC5 + AC-C-3).
    "get_cost_budget": ("cost_budget", h_get_cost_budget.handle),
}

# PLAN-096 Wave A — register one handler per audit-query sub-command
# (27 read-only commands; `label` excluded per wave-a-mcp-subset.md §3).
for _method_name, _handle_fn in h_audit_query.HANDLERS.items():
    HANDLERS[_method_name] = ("audit_read", _handle_fn)


# ---------------------------------------------------------------------------
# PLAN-112-FOLLOWUP — per-process bearer replay store (singleton).
#
# Loopback-only, single-process protection per ADR-040-MCP-Auth. The
# store uses a WALL-CLOCK ns source so the wall-clock token timestamp
# reconciles (clock-domain fix); its skew window is derived from
# ``auth._SKEW_MS`` at import (single freshness window). Lazily built so
# tests can swap it via ``set_replay_store_for_test``.
# ---------------------------------------------------------------------------

_REPLAY_STORE: Optional["bearer_replay.BearerReplayStore"] = None


def _get_replay_store() -> "bearer_replay.BearerReplayStore":
    """Return the per-process replay store, building it on first use."""
    global _REPLAY_STORE
    if _REPLAY_STORE is None:
        _REPLAY_STORE = bearer_replay.BearerReplayStore()
    return _REPLAY_STORE


def set_replay_store_for_test(store: Optional["bearer_replay.BearerReplayStore"]) -> None:
    """Swap (or reset) the module replay store — TEST AID ONLY.

    Passing ``None`` forces a fresh default store on next use.
    """
    global _REPLAY_STORE
    _REPLAY_STORE = store


# Replay-store DENY reasons that map to mcp_bearer_replay_rejected
# (replay/stale taxonomy). DENY_NON_LOOPBACK routes elsewhere.
_REPLAY_REJECT_REASONS = frozenset({
    bearer_replay.DENY_STALE_IAT,
    bearer_replay.DENY_NONCE_REUSED,
    bearer_replay.DENY_STALE_AND_REUSED,
})


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 helpers
# ---------------------------------------------------------------------------


def rpc_error(
    request_id: Any,
    code: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    err: Dict[str, Any] = {"code": int(code), "message": str(message)}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


def rpc_result(request_id: Any, result: Any) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def parse_envelope(
    body: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Parse + validate a JSON-RPC 2.0 envelope.

    Returns ``(envelope, error_response)``. On parse success
    ``error_response`` is None and ``envelope`` is the validated dict.
    On failure ``envelope`` is None and ``error_response`` is a
    ready-to-emit JSON-RPC error dict.
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, rpc_error(None, ERR_PARSE, "Parse error")
    if not isinstance(data, dict):
        return None, rpc_error(None, ERR_INVALID_REQUEST, "Invalid Request")
    if data.get("jsonrpc") != "2.0":
        rid = data.get("id") if isinstance(data.get("id"), (str, int)) else None
        return None, rpc_error(rid, ERR_INVALID_REQUEST, "Invalid Request")
    method = data.get("method")
    if not isinstance(method, str) or not method:
        rid = data.get("id") if isinstance(data.get("id"), (str, int)) else None
        return None, rpc_error(rid, ERR_INVALID_REQUEST, "Invalid Request")
    rid = data.get("id")
    if rid is not None and not isinstance(rid, (str, int)):
        return None, rpc_error(None, ERR_INVALID_REQUEST, "Invalid Request")
    params = data.get("params", {})
    if not isinstance(params, (dict, list)):
        return None, rpc_error(rid, ERR_INVALID_PARAMS, "Invalid params")
    return data, None


# ---------------------------------------------------------------------------
# Context + audit helpers
# ---------------------------------------------------------------------------


class AuthContext:
    """Per-request authenticated context, passed to handlers."""

    __slots__ = ("client_id", "registry_entry", "transport", "session_id", "project_dir")

    def __init__(
        self,
        client_id: str,
        registry_entry: Dict[str, Any],
        transport: str,
        session_id: str,
        project_dir: Path,
    ) -> None:
        self.client_id = client_id
        self.registry_entry = registry_entry
        self.transport = transport
        self.session_id = session_id
        self.project_dir = project_dir

    def to_handler_context(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "registry_entry": self.registry_entry,
            "transport": self.transport,
            "session_id": self.session_id,
            "project_dir": self.project_dir,
        }


def _now_ms() -> int:
    return int(time.time() * 1000)


def _settings_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "settings.json"


def _load_overrides(settings_path: Path) -> Dict[str, Any]:
    """Load ``mcp_rate_limits`` from settings.json. Empty on any error."""
    try:
        if not settings_path.is_file():
            return {}
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        mr = data.get("mcp_rate_limits")
        return mr if isinstance(mr, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def emit_deny(
    *,
    handler: str,
    client_id: str,
    transport: str,
    reason: str,
    session_id: str,
    project: str,
    target_client_id: str = "",
) -> None:
    """Emit ``mcp_handler_denied`` — never raises.

    When ``reason == 'cross_tenant'`` and the audit_emit module exposes
    ``emit_mcp_cross_tenant_denied`` (added by the PLAN-096 ceremony),
    also emit the dedicated cross-tenant event for AC-C-3 reporting.
    The dedicated emit is hasattr-guarded so pre-ceremony installs
    degrade to a no-op (the canonical ``mcp_handler_denied`` event
    still fires).
    """
    hashed_client = auth.hash_client_id(client_id) if client_id else ""
    try:
        audit_emit.emit_mcp_handler_denied(
            handler=handler,
            client_id=hashed_client,
            transport=transport,
            reason=reason,
            session_id=session_id,
            project=project,
        )
    except Exception:
        pass
    if reason == "cross_tenant":
        emit_fn = getattr(audit_emit, "emit_mcp_cross_tenant_denied", None)
        if callable(emit_fn):
            try:
                emit_fn(
                    handler=handler,
                    caller_client_id_hash=hashed_client,
                    target_client_id_hash=(
                        auth.hash_client_id(target_client_id)
                        if target_client_id
                        else ""
                    ),
                    transport=transport,
                    session_id=session_id,
                    project=project,
                )
            except Exception:
                pass


def emit_invoke(
    *,
    handler: str,
    client_id: str,
    transport: str,
    duration_ms: int,
    session_id: str,
    project: str,
) -> None:
    """Emit ``mcp_handler_invoked`` — never raises."""
    try:
        audit_emit.emit_mcp_handler_invoked(
            handler=handler,
            client_id=auth.hash_client_id(client_id) if client_id else "",
            transport=transport,
            duration_ms=int(duration_ms),
            session_id=session_id,
            project=project,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PLAN-112-FOLLOWUP — friction + replay emit helpers (never raise).
# ---------------------------------------------------------------------------


def _observe_friction(
    *,
    transport: str,
    failure_reason: str,
    replay_suspected: bool = False,
    client_id: Optional[str] = None,
    nonce: Optional[str] = None,
    raw_token: Optional[str] = None,
) -> None:
    """Buffer one friction observation — never raises.

    ``transport`` is used as the ``mcp_server`` slug (the deployed MCP
    server is single-tenant; the transport name is the most stable
    server discriminator available at this layer). The dedup key uses
    client_id/nonce (or token-hash sentinel for pre-parse branches).
    """
    try:
        mcp_bearer_friction.observe_auth_failure(
            mcp_server=transport or "mcp",
            failure_reason=failure_reason,
            replay_suspected=replay_suspected,
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
    except Exception:
        pass


def _drain_friction() -> None:
    """Mandatory end-of-authenticate drain — never raises."""
    try:
        mcp_bearer_friction.drain_observations()
    except Exception:
        pass


def _emit_replay_rejected(
    *,
    reason: str,
    nonce: str,
    session_id: str,
    project: str,
) -> None:
    """Emit mcp_bearer_replay_rejected (replay/stale DENYs) — never raises."""
    try:
        audit_emit.emit_mcp_bearer_replay_rejected(
            reason=reason,
            nonce_prefix=nonce or "",
            session_id=session_id,
            project=project,
        )
    except Exception:
        pass


def _emit_non_loopback_rejected(
    *,
    remote_addr: str,
    session_id: str,
    project: str,
) -> None:
    """Emit mcp_non_loopback_rejected (existing action) — never raises.

    Only the address FAMILY is recorded (ipv4 / ipv6 / other) — never
    the raw address — per the SPEC MF-3 allowlist for this action.
    """
    family = "other"
    addr = remote_addr or ""
    if addr.count(".") == 3 and ":" not in addr:
        family = "ipv4"
    elif ":" in addr:
        family = "ipv6"
    try:
        audit_emit.emit_mcp_non_loopback_rejected(
            remote_addr_family=family,
            session_id=session_id,
            project=project,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Authenticate + dispatch
# ---------------------------------------------------------------------------


def authenticate(
    *,
    raw_token: Optional[str],
    timestamp_ms: Any,
    method: str,
    origin: Optional[str],
    transport: str,
    session_id: str,
    project_dir: Path,
    remote_addr: str = bearer_replay.STDIO_LOCAL_ADDR,
) -> Tuple[Optional[AuthContext], Optional[str], int]:
    """Run the full auth pipeline.

    Returns ``(ctx, deny_reason, retry_after_ms)``. On success ``ctx``
    is populated; on denial ``ctx`` is None and ``deny_reason`` is one
    of the closed-enum strings in SPEC §4.3.

    ``remote_addr`` (PLAN-112-FOLLOWUP §3a): the network remote address
    for the replay-store loopback gate. HTTP transports pass
    ``client_address[0]``; the stdio transport passes the
    ``"stdio-local"`` sentinel (default). Defaulted so existing direct
    callers / tests that do not thread an address behave as loopback.

    Friction telemetry is buffered (non-blocking) on every deny branch
    and drained ONCE before returning (mandatory per-request drain).
    """
    try:
        return _authenticate_inner(
            raw_token=raw_token,
            timestamp_ms=timestamp_ms,
            method=method,
            origin=origin,
            transport=transport,
            session_id=session_id,
            project_dir=project_dir,
            remote_addr=remote_addr,
        )
    finally:
        # Mandatory per-request drain — moves the emit cost off the
        # per-branch path but guarantees friction fires from the request
        # path (NOT only at process exit). atexit is a backup only.
        _drain_friction()


def _authenticate_inner(
    *,
    raw_token: Optional[str],
    timestamp_ms: Any,
    method: str,
    origin: Optional[str],
    transport: str,
    session_id: str,
    project_dir: Path,
    remote_addr: str,
) -> Tuple[Optional[AuthContext], Optional[str], int]:
    project = str(project_dir)

    # Branch 1+2 (pre-parse): no token / malformed token. Dedup key uses
    # the raw-token hash sentinel (no client_id/nonce available yet).
    if not raw_token:
        _observe_friction(
            transport=transport,
            failure_reason="auth_token_malformed",
            raw_token=None,
        )
        return None, "auth_token_malformed", 0

    parsed = auth.parse_token(raw_token)
    if parsed is None:
        _observe_friction(
            transport=transport,
            failure_reason="auth_token_malformed",
            raw_token=raw_token,
        )
        return None, "auth_token_malformed", 0

    client_id = parsed["client_id"]
    nonce = parsed["nonce"]

    # Branch 3: unknown client.
    registry = auth.load_client_registry(_settings_path(project_dir))
    entry = registry.get(client_id)
    if not isinstance(entry, dict):
        _observe_friction(
            transport=transport,
            failure_reason="auth_hmac_invalid",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "auth_hmac_invalid", 0

    # Branch 4: missing/unreadable secret.
    secret = auth.load_secret(project_dir, client_id)
    if secret is None:
        _observe_friction(
            transport=transport,
            failure_reason="auth_hmac_invalid",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "auth_hmac_invalid", 0

    # Branch 5: non-integer timestamp.
    try:
        ts_int = int(timestamp_ms)
    except (TypeError, ValueError):
        _observe_friction(
            transport=transport,
            failure_reason="auth_token_malformed",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "auth_token_malformed", 0

    # Branch 6: HMAC mismatch.
    if not auth.verify_hmac(
        client_id=client_id,
        nonce=nonce,
        timestamp_ms=ts_int,
        secret=secret,
        candidate_hmac=parsed["hmac"],
    ):
        _observe_friction(
            transport=transport,
            failure_reason="auth_hmac_invalid",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "auth_hmac_invalid", 0

    # Branch 7: timestamp skew.
    if not auth.verify_timestamp_skew(ts_int, _now_ms()):
        _observe_friction(
            transport=transport,
            failure_reason="timestamp_skew",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "timestamp_skew", 0

    # ---- Branch 7b (NEW): replay defense — POST-HMAC + POST-SKEW. ----
    # Only HMAC-valid, freshness-valid tokens reach the nonce store, so
    # an unauthenticated request can never poison/grow it (CWE-770).
    # Clock reconcile: token ts is wall-clock ms → ns; store is wall-clock.
    iat_ns = ts_int * 1_000_000
    # Codex pair-rail P1 #2 — the replay-store consult MUST be
    # exception-contained. A replay-store / clock / state bug must NOT
    # propagate out of authenticate() (HTTP would turn it into a 500 and
    # stdio could terminate the loop). Fail CLOSED with a generic auth
    # deny + observe friction; the mandatory drain still runs in the
    # ``authenticate()`` ``finally`` even on this path.
    try:
        decision, reason = _get_replay_store().check_request(
            remote_addr=remote_addr,
            nonce=nonce,
            iat_ns=iat_ns,
        )
    except Exception:
        _observe_friction(
            transport=transport,
            failure_reason="replay_store_error",
            replay_suspected=True,
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        # Generic auth deny — no oracle about why (fail-CLOSED).
        return None, "auth_hmac_invalid", 0
    if decision != bearer_replay.ACCEPT:
        if decision == bearer_replay.DENY_NON_LOOPBACK:
            # Non-loopback uses the EXISTING dedicated action; this is
            # NOT a replay event, so do not flag replay_suspected.
            _emit_non_loopback_rejected(
                remote_addr=remote_addr,
                session_id=session_id,
                project=project,
            )
            _observe_friction(
                transport=transport,
                failure_reason="non_loopback",
                client_id=client_id,
                nonce=nonce,
                raw_token=raw_token,
            )
            return None, "auth_hmac_invalid", 0
        # Codex pair-rail P2 #4 — emit the replay-specific audit ONLY for
        # the known replay/stale taxonomy. ``_REPLAY_REJECT_REASONS`` is
        # now load-bearing: any other non-ACCEPT, non-DENY_NON_LOOPBACK
        # value (an unknown/future store decision) MUST fail closed
        # WITHOUT a (potentially-mislabeled) mcp_bearer_replay_rejected
        # emit — generic friction + a generic auth deny instead.
        if decision in _REPLAY_REJECT_REASONS:
            # Replay / stale DENYs → mcp_bearer_replay_rejected + replay flag.
            replay_reason = reason or decision
            _emit_replay_rejected(
                reason=replay_reason,
                nonce=nonce,
                session_id=session_id,
                project=project,
            )
            _observe_friction(
                transport=transport,
                failure_reason=replay_reason,
                replay_suspected=True,
                client_id=client_id,
                nonce=nonce,
                raw_token=raw_token,
            )
            # Surface to the transport as a timestamp/auth-level deny
            # without leaking which nonce was reused (no oracle). stale_iat
            # maps to the timestamp deny enum; nonce reuse maps to auth.
            if decision == bearer_replay.DENY_STALE_IAT:
                return None, "timestamp_skew", 0
            return None, "auth_hmac_invalid", 0
        # Unknown/future store decision — fail CLOSED, no replay-specific
        # audit. Observe generic friction so the anomaly is still visible.
        _observe_friction(
            transport=transport,
            failure_reason="replay_store_unknown_decision",
            replay_suspected=True,
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "auth_hmac_invalid", 0

    # Branch 8: ACL.
    if not auth.check_acl(entry, method):
        _observe_friction(
            transport=transport,
            failure_reason="acl_missing_handler",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "acl_missing_handler", 0

    # Branch 9: CORS (HTTP only).
    if transport == "http":
        if not auth.check_cors(entry, origin):
            _observe_friction(
                transport=transport,
                failure_reason="cors_default_deny",
                client_id=client_id,
                nonce=nonce,
                raw_token=raw_token,
            )
            return None, "cors_default_deny", 0

    # Branch 10: rate limit.
    overrides = _load_overrides(_settings_path(project_dir))
    handler_class = rate_limit.handler_to_class(method)
    bucket = rate_limit.get_bucket(client_id, handler_class, overrides=overrides)
    allowed, retry_ms = bucket.try_consume(cost=1)
    if not allowed:
        _observe_friction(
            transport=transport,
            failure_reason="rate_limit",
            client_id=client_id,
            nonce=nonce,
            raw_token=raw_token,
        )
        return None, "rate_limit", retry_ms

    ctx = AuthContext(
        client_id=client_id,
        registry_entry=entry,
        transport=transport,
        session_id=session_id,
        project_dir=project_dir,
    )
    return ctx, None, 0


def dispatch(
    envelope: Dict[str, Any],
    ctx: AuthContext,
    project: str,
) -> Dict[str, Any]:
    """Run the handler for an authenticated envelope.

    Returns a JSON-RPC response dict. Budget-denied spawn_agent calls
    return a successful JSON-RPC result with ``allowed=False`` —
    per ADR-042, governance + budget denies are SUCCESSFUL RPC calls
    whose application-level outcome happens to be deny.

    Emits ``mcp_handler_invoked`` on success; ``mcp_handler_denied``
    (with reason=governance_block / budget_hard_stop_* / internal_error)
    on failure paths.
    """
    method = envelope["method"]
    params = envelope.get("params", {})
    if isinstance(params, list):
        return rpc_error(envelope.get("id"), ERR_INVALID_PARAMS, "Invalid params")

    info = HANDLERS.get(method)
    if info is None:
        return rpc_error(envelope.get("id"), ERR_METHOD_NOT_FOUND, "Method not found")
    _, fn = info

    start = time.perf_counter()
    try:
        result = fn(params if isinstance(params, dict) else {}, ctx.to_handler_context())
    except Exception as e:
        emit_deny(
            handler=method,
            client_id=ctx.client_id,
            transport=ctx.transport,
            reason="internal_error",
            session_id=ctx.session_id,
            project=project,
        )
        _ = type(e).__name__  # recorded in audit via reason; never leaked
        return rpc_error(envelope.get("id"), ERR_INTERNAL, "internal_error")

    duration_ms = int((time.perf_counter() - start) * 1000.0)

    if isinstance(result, dict) and "__error__" in result:
        err = result["__error__"]
        code = int(err.get("code", ERR_INTERNAL))
        msg = str(err.get("message", "internal_error"))
        emit_deny(
            handler=method,
            client_id=ctx.client_id,
            transport=ctx.transport,
            reason=msg,
            session_id=ctx.session_id,
            project=project,
        )
        return rpc_error(envelope.get("id"), code, msg)

    # spawn_agent: governance or budget deny is a successful RPC.
    if method == "spawn_agent" and isinstance(result, dict):
        if result.get("allowed") is False and result.get("_budget_reason"):
            emit_deny(
                handler=method,
                client_id=ctx.client_id,
                transport=ctx.transport,
                reason=str(result["_budget_reason"]),
                session_id=ctx.session_id,
                project=project,
            )
            clean = {k: v for k, v in result.items() if not k.startswith("_")}
            return rpc_result(envelope.get("id"), clean)
        if result.get("allowed") is False:
            emit_deny(
                handler=method,
                client_id=ctx.client_id,
                transport=ctx.transport,
                reason="governance_block",
                session_id=ctx.session_id,
                project=project,
            )
            clean = {k: v for k, v in result.items() if not k.startswith("_")}
            return rpc_result(envelope.get("id"), clean)

    emit_invoke(
        handler=method,
        client_id=ctx.client_id,
        transport=ctx.transport,
        duration_ms=duration_ms,
        session_id=ctx.session_id,
        project=project,
    )
    return rpc_result(envelope.get("id"), result)


# Map deny reason to JSON-RPC application code.
DENY_CODE_MAP: Dict[str, int] = {
    "auth_token_malformed": ERR_APP_AUTH,
    "auth_hmac_invalid": ERR_APP_AUTH,
    "timestamp_skew": ERR_APP_TIMESTAMP,
    "acl_missing_handler": ERR_APP_ACL,
    "cors_default_deny": ERR_APP_CORS,
    "rate_limit": ERR_APP_RATE_LIMIT,
}


__all__ = [
    "HANDLERS",
    "AuthContext",
    "parse_envelope",
    "authenticate",
    "dispatch",
    "rpc_error",
    "rpc_result",
    "emit_deny",
    "emit_invoke",
    "set_replay_store_for_test",
    "DENY_CODE_MAP",
    "ERR_PARSE",
    "ERR_INVALID_REQUEST",
    "ERR_METHOD_NOT_FOUND",
    "ERR_INVALID_PARAMS",
    "ERR_INTERNAL",
    "ERR_APP_AUTH",
    "ERR_APP_ACL",
    "ERR_APP_RATE_LIMIT",
    "ERR_APP_CORS",
    "ERR_APP_TIMESTAMP",
    "ERR_APP_BUDGET",
]
