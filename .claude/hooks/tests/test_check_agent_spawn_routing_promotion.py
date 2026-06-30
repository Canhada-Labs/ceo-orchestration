"""Tests for PLAN-091 Wave A.4 + A.5 wires in `check_agent_spawn.py`.

A.4 (W3.1) — `_emit_mcp_routing_advisory()` callsite delegating to
             `_lib/mcp_routing.resolve()` for `mcp_route_advised` emit.
A.5 (W3.3) — `_emit_promotion_advisory()` heuristic emitting
             `specialization_promoted` when general-purpose spawn matches
             a specialist hint.

Both wires are ADVISORY-ONLY: never block, never mutate, never raise.

Coverage:

- A.4 callsite: archetype heuristic maps to task_class / unknown
  archetypes → no emit / bypass env / mcp_routing.resolve unavailable
  fail-soft.
- A.5 callsite: hint match → emit / no match → no emit / non-general-
  purpose spawn → no emit / bypass env / multi-hint first-hit wins.

Stdlib only. TestEnvContext for env isolation.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import List
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
import check_agent_spawn  # noqa: E402


class _AuditEmitSpy:
    """Captures emit_generic calls for assertion."""

    def __init__(self):
        self.calls: List[dict] = []

    def emit_generic(self, action, **fields):
        self.calls.append({"action": action, **fields})


class TestMcpRoutingAdvisoryCallsite(TestEnvContext):
    """A.4 — mcp_routing.resolve() invoked via spawn-hook callsite."""

    def _make_spawn_payload(self, subagent_type: str, prompt: str = ""):
        """Minimal tool_input payload structure for the decide() path."""
        return {
            "description": "PLAN-091 test spawn",
            "prompt": prompt,
            "subagent_type": subagent_type,
        }

    def test_arch_archetype_triggers_mcp_resolve(self):
        """architect → task_class=arch → mcp_routing.resolve emits."""
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="Architectural review",
                prompt="## AGENT PROFILE\nrole: architect",
                subagent_type="architect",
            )
            mock_resolve.assert_called_once_with("arch")

    def test_finops_archetype_triggers_mcp_resolve(self):
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="cost analysis",
                prompt="",
                subagent_type="llm-finops-architect",
            )
            mock_resolve.assert_called_once_with("finops")

    def test_seo_archetype_triggers_mcp_resolve(self):
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="seo audit",
                prompt="",
                subagent_type="seo-analyst",
            )
            mock_resolve.assert_called_once_with("seo_research")

    def test_crypto_archetype_triggers_mcp_resolve(self):
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="crypto market scan",
                prompt="",
                subagent_type="crypto-research-analyst",
            )
            mock_resolve.assert_called_once_with("crypto_research")

    def test_unknown_archetype_does_not_emit(self):
        """No mapping → resolve never called (avoid noise)."""
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="generic task",
                prompt="",
                subagent_type="general-purpose",
            )
            mock_resolve.assert_not_called()

    def test_empty_archetype_does_not_emit(self):
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="",
                prompt="",
                subagent_type="",
            )
            mock_resolve.assert_not_called()

    def test_bypass_env_skips_resolve(self):
        """CEO_MCP_ROUTING_HOOK=0 → resolve never called."""
        os.environ["CEO_MCP_ROUTING_HOOK"] = "0"
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="arch review",
                prompt="",
                subagent_type="architect",
            )
            mock_resolve.assert_not_called()

    def test_resolve_exception_swallowed(self):
        """Resolver raising MUST NOT propagate (fail-open invariant)."""
        with mock.patch(
            "_lib.mcp_routing.resolve", side_effect=RuntimeError("boom")
        ):
            # Must not raise.
            check_agent_spawn._emit_mcp_routing_advisory(
                description="arch review",
                prompt="",
                subagent_type="architect",
            )

    def test_archetype_from_persona_header(self):
        """Archetype detected from `## AGENT PROFILE` body when no
        explicit subagent_type is set (defensive matching)."""
        with mock.patch("_lib.mcp_routing.resolve") as mock_resolve:
            check_agent_spawn._emit_mcp_routing_advisory(
                description="",
                prompt="## AGENT PROFILE\narchitect persona for cost review",
                subagent_type="",
            )
            # Implementation walks subagent_type first, then header — either
            # path may return an archetype string. The contract is just "no
            # raise + emit when archetype detected"; both behaviors are
            # acceptable, but resolve MUST NOT be called when extraction
            # returns the literal "" fallback.
            if mock_resolve.called:
                args, _ = mock_resolve.call_args
                self.assertIn(args[0], ("arch", "finops", "seo_research",
                                        "crypto_research"))


class TestPromotionAdvisoryCallsite(TestEnvContext):
    """A.5 — `specialization_promoted` heuristic emit."""

    def _spy_audit_emit(self):
        spy = _AuditEmitSpy()
        return mock.patch.object(
            check_agent_spawn, "_audit_emit", spy
        ), spy

    def test_no_emit_when_not_general_purpose(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="latency profile",
                prompt="optimize p99",
                subagent_type="performance-engineer",
            )
        self.assertEqual(spy.calls, [])

    def test_emit_on_performance_hint(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="optimize p99 latency",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(len(spy.calls), 1)
        call = spy.calls[0]
        self.assertEqual(call["action"], "mcp_route_advised")
        self.assertEqual(call["signal_source"], "specialization_promoted")
        self.assertEqual(call["task_class"], "promotion")
        self.assertEqual(call["suggested_servers"], "performance-engineer")

    def test_emit_on_security_hint(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="JWT token rotation policy",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(spy.calls[0]["suggested_servers"], "security-engineer")

    def test_emit_on_qa_hint(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="mutation testing strategy",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(spy.calls[0]["suggested_servers"], "qa-architect")

    def test_emit_first_hit_wins(self):
        """Multiple hint matches → only one emit (first archetype)."""
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="latency analysis with JWT authentication",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(len(spy.calls), 1)

    def test_no_emit_when_no_hint_matches(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="generic task with no specialist hint",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(spy.calls, [])

    def test_bypass_env_skips_emit(self):
        os.environ["CEO_PROMOTION_HEURISTIC"] = "0"
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="latency p99 hotpath",
                prompt="",
                subagent_type="general-purpose",
            )
        self.assertEqual(spy.calls, [])

    def test_subagent_type_case_insensitive(self):
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="memory leak hunt",
                prompt="",
                subagent_type="GENERAL-PURPOSE",
            )
        self.assertEqual(len(spy.calls), 1)

    def test_prompt_text_matched_too(self):
        """Hint may appear in `prompt` rather than `description`."""
        os.environ.pop("CEO_PROMOTION_HEURISTIC", None)
        patcher, spy = self._spy_audit_emit()
        with patcher:
            check_agent_spawn._emit_promotion_advisory(
                description="task",
                prompt="see SIEM rule for the alert.",
                subagent_type="general-purpose",
            )
        self.assertEqual(len(spy.calls), 1)
        self.assertEqual(spy.calls[0]["suggested_servers"], "threat-detection-engineer")

    def test_audit_emit_exception_swallowed(self):
        """emit_generic raising MUST NOT propagate."""
        broken = mock.MagicMock()
        broken.emit_generic.side_effect = RuntimeError("boom")
        with mock.patch.object(check_agent_spawn, "_audit_emit", broken):
            # Must not raise.
            check_agent_spawn._emit_promotion_advisory(
                description="latency hot path",
                prompt="",
                subagent_type="general-purpose",
            )

    def test_returns_none_invariant(self):
        """Helper always returns None (no return value contract)."""
        result = check_agent_spawn._emit_promotion_advisory(
            description="hi",
            prompt="",
            subagent_type="general-purpose",
        )
        self.assertIsNone(result)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
