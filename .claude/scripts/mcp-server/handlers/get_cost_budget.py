"""MCP handler: ``get_cost_budget`` (PLAN-096 Wave D).

Per ADR-042-AMEND-1 §Auth.2 this is a ``cost_budget`` class handler
(new rate-bucket — Read-only ≤30/min/client per ADR-042-AMEND-1).

## Stub mode (pre-PLAN-102)

PLAN-102 is the upstream that ships the live cost-envelope hook. Until
PLAN-102 lands, this handler is a stub that returns:

    {
      "status": "unwired",
      "plan_dep": "PLAN-102",
      "scope": "<caller_scope>",
      "client_id_hash": "<hashed>",
      "daily_used_usd": null,
      "daily_remaining_usd": null,
      "breakdown": {}
    }

The dispatch.py wire-up + ACL + rate-limit + audit-emit are LIVE in
v1.29.0; only the data payload is stubbed. This is the contract
referenced by AC5: "method exposed (stub-mode pre-PLAN-102)".

## Cross-tenant isolation (AC-C-3)

When PLAN-102 wires the live data path, this handler MUST scope to the
caller's ``client_id``. Aggregate-only mode (``scope=aggregate``) is
permitted and returns a redacted rollup with per-client fields
stripped. The stub currently honors these scope rules so the dispatch
contract is fully testable today; the actual data substitution happens
in PLAN-102 follow-up edits.

## Audit emit

The dispatcher emits ``mcp_handler_invoked`` per call (the existing
ADR-042 pattern). Cross-tenant attempts raise
``mcp_cross_tenant_denied`` from the dispatcher path, but the stub
also surfaces the rejection inline via ``__error__`` so the caller
sees a JSON-RPC error code instead of a successful empty stub.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


_VALID_SCOPES = ("caller", "aggregate")


def _resolve_client_hash(context: Dict[str, Any]) -> str:
    """Return a short hash of the caller's client_id (for audit trace).

    Re-uses ``auth.hash_client_id`` if available; otherwise returns
    empty string. Never raises.
    """
    try:
        import sys
        from pathlib import Path as _P
        server_dir = _P(__file__).resolve().parent.parent
        if str(server_dir) not in sys.path:
            sys.path.insert(0, str(server_dir))
        import auth  # type: ignore[import-not-found]
        cid = context.get("client_id") or ""
        return auth.hash_client_id(cid) if cid else ""
    except Exception:
        return ""


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """``get_cost_budget(scope='caller'|'aggregate', target_client_id=None)``.

    Stub-mode contract pre-PLAN-102.
    """
    scope_raw = "caller"
    target_client_id_raw: Optional[Any] = None
    if isinstance(params, dict):
        scope_raw = params.get("scope", "caller")
        target_client_id_raw = params.get("target_client_id")

    if not isinstance(scope_raw, str) or scope_raw not in _VALID_SCOPES:
        return {
            "status": "unwired",
            "plan_dep": "PLAN-102",
            "scope": "invalid",
            "__error__": {
                "code": -32602,
                "message": f"invalid_scope:{scope_raw!r}",
            },
        }
    scope = scope_raw

    # Cross-tenant probe: ``target_client_id`` is only valid in
    # ``aggregate`` scope. If a caller in scope=caller specifies a
    # target_client_id different from their own, deny with
    # cross_tenant violation.
    caller_id = context.get("client_id") or ""
    if (
        target_client_id_raw is not None
        and isinstance(target_client_id_raw, str)
        and target_client_id_raw != caller_id
        and scope == "caller"
    ):
        return {
            "status": "unwired",
            "plan_dep": "PLAN-102",
            "scope": scope,
            "__error__": {
                "code": -32002,  # ERR_APP_ACL — cross-tenant fault
                "message": "cross_tenant",
            },
        }

    client_hash = _resolve_client_hash(context) if scope == "caller" else ""

    return {
        "status": "unwired",
        "plan_dep": "PLAN-102",
        "scope": scope,
        "client_id_hash": client_hash,
        "daily_used_usd": None,
        "daily_remaining_usd": None,
        "breakdown": {},
    }


HANDLERS: Dict[str, Any] = {"get_cost_budget": handle}


__all__ = ["HANDLERS", "handle"]
