"""Unit tests for PLAN-096 Wave D cost-budget MCP handler (stub-mode pre-PLAN-102).

ACs exercised:
- AC5 (get_cost_budget exposed; stub returns plan_dep=PLAN-102)
- AC-C-3 (cross-tenant isolation — caller scope cannot read sibling client_id)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_SERVER = _REPO_ROOT / ".claude" / "scripts" / "mcp-server"
_HANDLERS = _MCP_SERVER / "handlers"

for _p in (_MCP_SERVER, _HANDLERS):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import get_cost_budget  # type: ignore[import-not-found]  # noqa: E402


_CALLER = "aaaaaaaaaaaaaaaa"
_OTHER = "bbbbbbbbbbbbbbbb"


def test_stub_returns_unwired_status():
    """AC5 — stub explicitly carries plan_dep=PLAN-102."""
    r = get_cost_budget.handle({"scope": "caller"}, {"client_id": _CALLER})
    assert r["status"] == "unwired"
    assert r["plan_dep"] == "PLAN-102"
    assert r["scope"] == "caller"
    assert r["daily_used_usd"] is None
    assert r["daily_remaining_usd"] is None


def test_aggregate_scope_strips_client_hash():
    """AC-C-3 — aggregate mode returns no per-client identifier."""
    r = get_cost_budget.handle({"scope": "aggregate"}, {"client_id": _CALLER})
    assert r["scope"] == "aggregate"
    assert r.get("client_id_hash") == ""


def test_caller_scope_includes_client_hash():
    r = get_cost_budget.handle({"scope": "caller"}, {"client_id": _CALLER})
    assert r.get("client_id_hash") != ""


def test_invalid_scope_returns_error():
    r = get_cost_budget.handle({"scope": "evil"}, {"client_id": _CALLER})
    assert "__error__" in r
    assert "invalid_scope" in r["__error__"]["message"]


def test_cross_tenant_probe_denied():
    """AC-C-3 — client X tries to read client Y's per-client cost."""
    r = get_cost_budget.handle(
        {"scope": "caller", "target_client_id": _OTHER},
        {"client_id": _CALLER},
    )
    assert "__error__" in r
    assert r["__error__"]["message"] == "cross_tenant"
    assert r["__error__"]["code"] == -32002


def test_self_target_is_allowed():
    """Caller asking about its own client_id is legitimate."""
    r = get_cost_budget.handle(
        {"scope": "caller", "target_client_id": _CALLER},
        {"client_id": _CALLER},
    )
    assert "__error__" not in r
    assert r["status"] == "unwired"


def test_aggregate_target_is_allowed():
    """In aggregate scope, target_client_id is ignored (rollup wins)."""
    r = get_cost_budget.handle(
        {"scope": "aggregate", "target_client_id": _OTHER},
        {"client_id": _CALLER},
    )
    assert "__error__" not in r
    assert r["scope"] == "aggregate"


def test_dispatch_registers_cost_budget_under_cost_budget_class():
    import dispatch, rate_limit  # type: ignore[import-not-found]
    assert "get_cost_budget" in dispatch.HANDLERS
    cls, _ = dispatch.HANDLERS["get_cost_budget"]
    assert cls == "cost_budget"
    assert rate_limit.handler_to_class("get_cost_budget") == "cost_budget"


def test_cost_budget_class_default_limits():
    import rate_limit  # type: ignore[import-not-found]
    rpm, burst = rate_limit.DEFAULT_LIMITS["cost_budget"]
    assert rpm == 30
    assert burst == 5
