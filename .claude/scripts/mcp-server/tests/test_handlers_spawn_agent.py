"""Unit tests for handlers/spawn_agent.py — CRITICAL byte-identity governance.

PLAN-013 §C2 / ADR-042 §Decision: the MCP spawn_agent handler MUST
re-enter the EXACT same governance decision function that a Claude
PreToolUse Agent hook hits, and the ``block_reason`` returned MUST be
byte-identical to what ``check_agent_spawn.decide()`` returns.

Without this parity, an external MCP client could bypass governance.
The byte-identity assertion is the single most important test in this
suite — a paraphrase / redact / reformat would silently divert
production behavior away from the in-session contract.

Other coverage:
- Budget per_spawn deny → SUCCESSFUL RPC with allowed=False
- Budget per_plan_5min deny → SUCCESSFUL RPC with allowed=False
- Allow path returns spawn_queued
- Malformed params → __error__ sentinel (-32602)
"""

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

import check_agent_spawn  # noqa: E402  (loaded from .claude/hooks/)
from _lib import team as _team  # noqa: E402
from _lib.adapters.live._cost import (  # noqa: E402
    PlanCostTracker,
    SpawnCostTracker,
)
from handlers import spawn_agent  # type: ignore[import-not-found]  # noqa: E402


_TEAM_MD_FIXTURE = """\
# Team

## ICs

| Archetype | Reports to | Focus | Primary skill | Secondary |
|-----------|-----------|-------|---------------|-----------|
| **Staff Backend Engineer** | VP Engineering | APIs | `public-api-design` | — |
| **Principal QA Architect** | VP Engineering | Tests | `testing-strategy` | — |
| **Principal Security Engineer** | VP Operations | Auth | `security-and-auth` | — |

## Leadership

| Role | Reports to | Area | Primary skill |
|------|-----------|------|---------------|
| **VP Engineering** | CEO | Architecture | `architecture-decisions` |
"""


# Three governance-trigger scenarios — different persona shapes, all
# missing the ## SKILL CONTENT marker → MUST be blocked identically.
SCENARIOS = [
    {
        "agent_name": "Staff Backend Engineer",
        "description": "Staff Backend Engineer for public-api-design task",
        "prompt": "PERSONA: Staff Backend Engineer\n\nDesign endpoint X.",
    },
    {
        "agent_name": "Principal QA Architect",
        "description": "spawn an agent",
        "prompt": "## AGENT PROFILE\n\nPersona: QA Architect.\n\nTask: write tests for module Y.",
    },
    {
        "agent_name": "Principal Security Engineer",
        "description": "Principal Security Engineer for security-and-auth review",
        "prompt": "## PERSONA\n\nPrincipal Security Engineer.\n\nReview the auth flow.",
    },
]


class TestSpawnAgentByteIdentity(TestEnvContext):
    """The CRITICAL parity test — block_reason MUST be byte-identical."""

    def setUp(self) -> None:
        super().setUp()
        # Reset module-level trackers.
        spawn_agent._default_spawn_tracker = None
        spawn_agent._default_plan_tracker = None
        # Seed team.md so the names_regex matches our fixture archetypes.
        team = self.project_dir / ".claude" / "team.md"
        team.parent.mkdir(parents=True, exist_ok=True)
        team.write_text(_TEAM_MD_FIXTURE, encoding="utf-8")

    def test_byte_identity_governance_block_reason(self):
        """For each scenario, MCP block_reason == decide() reason byte-for-byte."""
        names_regex = _team.load_names(self.project_dir)
        for i, scenario in enumerate(SCENARIOS):
            with self.subTest(scenario_index=i, agent=scenario["agent_name"]):
                # 1. Hook-side: call decide() directly.
                decision = check_agent_spawn.decide(
                    description=scenario["description"],
                    prompt=scenario["prompt"],
                    names_regex=names_regex,
                )
                self.assertFalse(
                    decision.allow,
                    f"scenario {i} should block (no SKILL CONTENT)",
                )
                self.assertIsNotNone(decision.reason)

                # 2. MCP-side: call handle() with same inputs.
                result = spawn_agent.handle(
                    params={
                        "agent_name": scenario["agent_name"],
                        "description": scenario["description"],
                        "prompt": scenario["prompt"],
                    },
                    context={"project_dir": self.project_dir},
                )
                self.assertFalse(result["allowed"])
                # 3. BYTE-IDENTITY assertion — no paraphrase, no reformat.
                self.assertEqual(
                    result["block_reason"],
                    decision.reason,
                    f"BYTE-IDENTITY violation in scenario {i}: "
                    f"MCP returned {result['block_reason']!r} but "
                    f"decide() returned {decision.reason!r}. "
                    "Per ADR-042 §Decision + PLAN-013 §C2 these MUST match.",
                )


class TestSpawnAgentAllowPath(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        spawn_agent._default_spawn_tracker = None
        spawn_agent._default_plan_tracker = None

    def test_compliant_spawn_returns_queued(self):
        # Generic prompt with no persona header → not a "named spawn"
        # → allowed by decide(). The test demonstrates the allow path
        # passes both governance + budget when ample ceilings.
        spawn = SpawnCostTracker(ceiling_usd=100.0)
        plan = PlanCostTracker(ceiling_usd=200.0)
        result = spawn_agent.handle(
            params={
                "agent_name": "generic-research",
                "description": "do some general research",
                "prompt": "Research best practices for X.",
            },
            context={
                "project_dir": self.project_dir,
                "trackers": {"spawn": spawn, "plan": plan},
            },
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["result"], "spawn_queued")
        self.assertIsNone(result["block_reason"])

    def test_named_spawn_with_skill_content_allowed(self):
        # Named spawn (PERSONA: header) WITH ## SKILL CONTENT → allow.
        # P1-SEC-B (Session 42 Wave A): SKILL CONTENT must be ≥256 non-ws
        # bytes to prevent trivial-bypass via empty section header.
        spawn = SpawnCostTracker(ceiling_usd=100.0)
        plan = PlanCostTracker(ceiling_usd=200.0)
        result = spawn_agent.handle(
            params={
                "agent_name": "Staff Backend Engineer",
                "description": "Staff Backend Engineer for API design",
                "prompt": (
                    "PERSONA: Staff Backend Engineer\n\n"
                    "## SKILL CONTENT\n\n"
                    "# public-api-design\n\n"
                    "Design and implement public-facing APIs with versioning, "
                    "self-service API key management, per-tier rate limiting, "
                    "consumer-facing documentation, developer onboarding, and "
                    "SDK patterns. Contract-first: every endpoint documented "
                    "before code lands. Versioning via URL path (/v1/, /v2/) "
                    "with deprecation windows of 6 months minimum.\n"
                ),
            },
            context={
                "project_dir": self.project_dir,
                "trackers": {"spawn": spawn, "plan": plan},
            },
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["result"], "spawn_queued")


class TestSpawnAgentBudgetDeny(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        spawn_agent._default_spawn_tracker = None
        spawn_agent._default_plan_tracker = None

    def test_per_spawn_ceiling_blocks(self):
        # Tiny per-spawn ceiling — the conservative estimator will overshoot.
        spawn = SpawnCostTracker(ceiling_usd=0.0001)
        plan = PlanCostTracker(ceiling_usd=200.0)
        result = spawn_agent.handle(
            params={
                "agent_name": "generic",
                "description": "do general research",
                "prompt": "x" * 10000,  # large prompt → over the tiny ceiling
            },
            context={
                "project_dir": self.project_dir,
                "trackers": {"spawn": spawn, "plan": plan},
            },
        )
        self.assertFalse(result["allowed"])
        self.assertIn("BUDGET:", result["block_reason"])
        self.assertIn("budget_hard_stop_per_spawn", result["block_reason"])
        # The _budget_reason private field is what dispatch.py reads
        # to set the audit reason; verify it's present and clean.
        self.assertEqual(
            result["_budget_reason"], "budget_hard_stop_per_spawn"
        )

    def test_per_plan_5min_ceiling_blocks(self):
        # Per-spawn ceiling generous; plan ceiling small + pre-loaded.
        spawn = SpawnCostTracker(ceiling_usd=100.0)
        plan = PlanCostTracker(ceiling_usd=0.10)
        plan.add(0.09)  # leaves 0.01 headroom; estimator will overshoot.
        result = spawn_agent.handle(
            params={
                "agent_name": "generic",
                "description": "do general research",
                "prompt": "x" * 5000,
            },
            context={
                "project_dir": self.project_dir,
                "trackers": {"spawn": spawn, "plan": plan},
            },
        )
        self.assertFalse(result["allowed"])
        self.assertIn(
            "budget_hard_stop_per_plan_5min", result["block_reason"]
        )


class TestSpawnAgentMalformedParams(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        spawn_agent._default_spawn_tracker = None
        spawn_agent._default_plan_tracker = None

    def test_missing_description_returns_invalid_params(self):
        result = spawn_agent.handle(
            params={"prompt": "x", "agent_name": "X"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["code"], -32602)

    def test_missing_prompt_returns_invalid_params(self):
        result = spawn_agent.handle(
            params={"description": "x", "agent_name": "X"},
            context={"project_dir": self.project_dir},
        )
        self.assertIn("__error__", result)
        self.assertEqual(result["__error__"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
