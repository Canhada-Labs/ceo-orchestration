"""MCP handler: ``server.capabilities`` — protocol capability discovery.

Per ADR-042 §Auth.2 this is a ``readonly`` handler. The 7th handler
was added per PLAN-013 consensus §S4 to prevent client-side probing
fragility — clients ask the server what it supports rather than
guessing from a 404 / error pattern. PLAN-096 Wave A/B/C/D added 4
more handlers (audit_query expansion, plan_status, get_debate_state,
get_cost_budget) bringing the total to 11 discrete handler names.

NOTE: ``audit_query.*`` sub-commands are registered as individual
methods in ``dispatch.HANDLERS`` (one per sub-command) but they all
resolve through ``audit_query.HANDLERS``; this inventory lists the
logical handler modules, not every method name.

Returns:

    {
      "protocol_version": "2024-11-05",
      "server_version": "1.0.0-rc.1",
      "handlers": ["list_skills", "get_skill", ...],
      "feature_flags": {
        "audit_enabled": true,
        "spawn_agent_enabled": bool,  # per-client ACL
        "rate_limit_config_public": false,
        "kill_switch_var": "CEO_SOTA_DISABLE"
      }
    }

## Per-client customization

``spawn_agent_enabled`` reflects THIS client's ACL. The server passes
the client's registry entry in ``context["registry_entry"]`` — the
handler checks whether ``spawn_agent`` is in ``handlers`` allowlist.

Other flags are server-global. ``rate_limit_config_public=false``
means clients cannot query their own rate limits via this handler
(security hardening — limits are a potential bypass hint).

## Versioning

``protocol_version`` is the MCP spec release date this server
implements. It is a PINNED CONSTANT — not auto-discovered or bumped
automatically. Rationale for current pin (2024-11-05):

  - The MCP specification has not published a breaking-change release
    since 2024-11-05 that this server has been validated against.
  - Bumping this value requires a full review of the MCP changelog for
    breaking wire-format or auth changes and corresponding test
    coverage. Do NOT bump blindly.
  - If clients need a newer protocol feature, open a PLAN to review the
    spec diff, validate the wire format, and bump under test.

``server_version`` tracks OUR semver. Both are visible to clients for
compat gating.
"""

from __future__ import annotations

from typing import Any, Dict, List


# MCP spec release this server has been validated against.
# PINNED — see versioning rationale in the module docstring above.
# Do NOT bump without reviewing the MCP spec changelog for breaking
# wire-format or auth changes (see §Versioning above).
PROTOCOL_VERSION = "2024-11-05"

# Server software version (ADR-042 contract v1).
SERVER_VERSION = "1.0.0-rc.1"

# Canonical handler inventory — MUST match dispatch.py HANDLERS keys
# (module-level handlers, not the per-sub-command audit_query expansions).
# PLAN-096 added audit_query, plan_status, get_debate_state, get_cost_budget
# bringing the count from 7 to 11. Keep this list in sync with dispatch.py.
# A test (test_handlers_server_capabilities.py::test_inventory_matches_dispatch)
# asserts this list equals the set of handler module names reachable from
# dispatch.HANDLERS so it cannot silently drift again.
HANDLERS_INVENTORY: List[str] = [
    "list_skills",
    "get_skill",
    "list_agents",
    "list_pitfalls",
    "get_audit_log",
    "spawn_agent",
    "server.capabilities",
    # PLAN-096 Wave A — audit-query expansion (routed as audit_query.*)
    "audit_query",
    # PLAN-096 Wave B — plan-status methods
    "plan_status",
    # PLAN-096 Wave C — debate-state snapshot
    "get_debate_state",
    # PLAN-096 Wave D — cost-budget stub
    "get_cost_budget",
]


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Args:
        params: ignored (handler takes no args).
        context: runtime context. Uses ``registry_entry`` dict to
            derive ``spawn_agent_enabled``.

    Returns a flat dict conforming to the contract above.
    """
    registry_entry = context.get("registry_entry") or {}
    spawn_enabled = False
    if isinstance(registry_entry, dict):
        handlers = registry_entry.get("handlers", [])
        if isinstance(handlers, list):
            spawn_enabled = "spawn_agent" in handlers

    return {
        "protocol_version": PROTOCOL_VERSION,
        "server_version": SERVER_VERSION,
        "handlers": list(HANDLERS_INVENTORY),
        "feature_flags": {
            "audit_enabled": True,
            "spawn_agent_enabled": bool(spawn_enabled),
            "rate_limit_config_public": False,
            "kill_switch_var": "CEO_SOTA_DISABLE",
        },
    }


__all__ = ["handle", "PROTOCOL_VERSION", "SERVER_VERSION", "HANDLERS_INVENTORY"]
