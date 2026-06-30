"""Unit tests for handlers/server_capabilities.py — protocol discovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Bootstrap sys.path.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

from handlers import server_capabilities  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402
from handlers import audit_query as h_audit_query  # type: ignore[import-not-found]  # noqa: E402


# Expected handler names (logical modules, not per-sub-command expansions).
_EXPECTED_HANDLERS = [
    "list_skills",
    "get_skill",
    "list_agents",
    "list_pitfalls",
    "get_audit_log",
    "spawn_agent",
    "server.capabilities",
    # PLAN-096 Wave A/B/C/D additions
    "audit_query",
    "plan_status",
    "get_debate_state",
    "get_cost_budget",
]


class TestServerCapabilities(TestEnvContext):

    def test_returns_full_envelope(self):
        result = server_capabilities.handle(
            params={}, context={"registry_entry": {"handlers": ["list_skills"]}}
        )
        # Required keys.
        self.assertIn("protocol_version", result)
        self.assertIn("server_version", result)
        self.assertIn("handlers", result)
        self.assertIn("feature_flags", result)
        # All 11 handler modules present (7 original + 4 PLAN-096 additions).
        self.assertEqual(len(result["handlers"]), 11)
        for h in _EXPECTED_HANDLERS:
            self.assertIn(h, result["handlers"], f"handler '{h}' missing from inventory")
        # Feature flags fixed-shape.
        ff = result["feature_flags"]
        self.assertTrue(ff["audit_enabled"])
        self.assertFalse(ff["spawn_agent_enabled"])  # client lacks ACL
        self.assertEqual(ff["kill_switch_var"], "CEO_SOTA_DISABLE")

    def test_spawn_agent_enabled_reflects_acl(self):
        # Client whose registry_entry includes spawn_agent → True.
        result_with = server_capabilities.handle(
            params={},
            context={
                "registry_entry": {
                    "handlers": ["list_skills", "spawn_agent"],
                }
            },
        )
        self.assertTrue(result_with["feature_flags"]["spawn_agent_enabled"])
        # Client without it → False.
        result_without = server_capabilities.handle(
            params={},
            context={"registry_entry": {"handlers": ["list_skills"]}},
        )
        self.assertFalse(
            result_without["feature_flags"]["spawn_agent_enabled"]
        )

    def test_inventory_matches_dispatch(self):
        """HANDLERS_INVENTORY must cover every logical handler in dispatch.HANDLERS.

        This test prevents the two lists from drifting silently again
        (F-11.10 / F-5.9 — PLAN-113 WIRE-MCP).

        dispatch.HANDLERS may contain many method-name entries for a single
        logical module (e.g. audit_query has 27+ sub-command method names).
        We map method names back to their logical module name using the
        same grouping logic dispatch.py uses:

        - All method names from audit_query.HANDLERS map to "audit_query".
        - "list_plans" / "get_plan" / "get_plan_acs" /
          "get_plan_dependencies" all map to "plan_status".
        - Everything else maps to itself (method name == handler module).

        The invariant: every logical module name derived from dispatch.HANDLERS
        must appear in HANDLERS_INVENTORY.
        """
        # Derive logical module names from dispatch.HANDLERS keys.
        audit_query_methods = set(h_audit_query.HANDLERS.keys())
        plan_status_methods = {"list_plans", "get_plan", "get_plan_acs", "get_plan_dependencies"}

        logical_modules: set = set()
        for method_name in dispatch.HANDLERS:
            if method_name in audit_query_methods:
                logical_modules.add("audit_query")
            elif method_name in plan_status_methods:
                logical_modules.add("plan_status")
            else:
                logical_modules.add(method_name)

        inventory_set = set(server_capabilities.HANDLERS_INVENTORY)

        missing = logical_modules - inventory_set
        self.assertEqual(
            missing,
            set(),
            f"dispatch.HANDLERS has logical modules not in HANDLERS_INVENTORY: {sorted(missing)}. "
            f"Add them to server_capabilities.HANDLERS_INVENTORY."
        )


if __name__ == "__main__":
    unittest.main()
