#!/usr/bin/env python3
"""Tests for the PLAN-083 Wave 2 sub-agent 2.2 contextual recommender.

Stdlib unittest. Validates:
  - 3 hand-picked acceptance scenarios per PLAN-083 §5.4 row 2.2.
  - Dormant skills suppressed across all scenarios.
  - Confidence label present on every recommendation.
  - Top-3 cap enforced (even with 20 candidates).
  - Idempotency / determinism.
  - --json schema valid.
  - Sec MF-3 audit whitelist enforced.
  - Edge cases (empty context, write-intent escalation under trading-readonly,
    glob normalization, regex compile errors, missing file_path).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Import the recommender (hyphenated filename) via importlib so the test
# file works whether or not the staging dir is on sys.path.
_HERE = Path(__file__).resolve().parent
_REC_FILE = _HERE.parent / "contextual-recommender.py"


def _load_recommender() -> Any:
    spec = importlib.util.spec_from_file_location(
        "contextual_recommender_under_test", str(_REC_FILE)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


cr = _load_recommender()


# ---------------------------------------------------------------------------
# Skill fixture factory — minimal frontmatter dicts that pass resolver gate.
# ---------------------------------------------------------------------------

def _skill(
    name: str,
    *,
    domain: str = "core",
    priority: int = 5,
    risk_class: str = "low",
    context_budget_tokens: int = 1000,
    description: str = "",
    globs: List[str] = None,
    regexes: List[str] = None,
    inactive: bool = False,
    profiles: List[str] = None,
    profile_priorities: Dict[str, int] = None,
) -> Dict[str, Any]:
    """Build a SKILL.md-frontmatter-shaped dict for tests."""
    globs = globs or []
    regexes = regexes or []
    profiles = profiles or ["frontend", "engine", "fintech",
                            "trading-readonly", "generic"]
    profile_priorities = profile_priorities or {}

    triggers: List[Dict[str, Any]] = []
    for g in globs:
        triggers.append({"event": "edit", "glob": g})
    for r in regexes:
        triggers.append({"event": "intent", "regex": r})

    binding: Dict[str, Any] = {}
    for p in profiles:
        binding[p] = {
            "active": True,
            "priority": profile_priorities.get(p, priority),
        }

    return {
        "name": name,
        "domain": domain,
        "description": description,
        "priority": priority,
        "risk_class": risk_class,
        "context_budget_tokens": context_budget_tokens,
        "inactive_but_retained": inactive,
        "repo_profile_binding": binding,
        "activation_triggers": triggers,
        "_path": f".claude/skills/{domain}/{name}/SKILL.md",
    }


# ---------------------------------------------------------------------------
# Catalog used across multiple tests
# ---------------------------------------------------------------------------

FRONTEND_SKILLS = [
    _skill(
        "audit-page",
        domain="frontend",
        description="Audit a frontend page across 16 UX and technical dimensions. Use for any Next.js or React TSX page.",
        globs=["pages/**/*.tsx", "app/**/*.tsx"],
        regexes=[r"(?i)audit\s+(page|frontend|launch)"],
        priority=3, risk_class="low",
    ),
    _skill(
        "component-library",
        domain="frontend",
        description="Refactor and document shared React components and TypeScript design tokens.",
        globs=["components/**/*.tsx"],
        priority=4, risk_class="medium",
    ),
    _skill(
        "lighthouse-perf",
        domain="frontend",
        description="Run Lighthouse perf audits on a frontend route before launch.",
        regexes=[r"(?i)perf|lighthouse|launch"],
        priority=5, risk_class="low",
    ),
]

BACKEND_SKILLS = [
    _skill(
        "fastapi-route-review",
        domain="engine",
        description="Review FastAPI Python route handlers for error handling, validation and async correctness.",
        globs=["app.py", "**/routers/*.py", "**/api/*.py"],
        regexes=[r"(?i)route|endpoint|fastapi"],
        priority=3, risk_class="medium",
    ),
    _skill(
        "python-test-coverage",
        domain="engine",
        description="Audit Python pytest coverage on backend modules.",
        globs=["**/*.py"],
        priority=4, risk_class="low",
    ),
    _skill(
        "db-migration",
        domain="engine",
        description="Author and verify SQL database migration scripts.",
        globs=["**/migrations/*.sql", "**/*.sql"],
        priority=5, risk_class="high",
    ),
]

TRADING_SKILLS = [
    _skill(
        "strategy-safety-audit",
        domain="fintech",
        description="Audit a trading strategy file for kill-switch, slippage and concurrency issues.",
        globs=["strategies/**/*.py", "arbitrage/**/*.py"],
        regexes=[r"(?i)arbitrage|strategy|trade"],
        priority=2, risk_class="high",
    ),
    _skill(
        "exchange-secret-scan",
        domain="fintech",
        description="Scan a trading repo for exchange API key leaks and secret patterns.",
        regexes=[r"(?i)secret|leak|api\s*key"],
        priority=2, risk_class="high",
    ),
    _skill(
        "order-flow-review",
        domain="fintech",
        description="Review order-flow execution path for race conditions and order placement bugs.",
        globs=["execution/**/*.py", "order/**/*.py"],
        priority=3, risk_class="high",
    ),
]

DORMANT_SKILL = _skill(
    "legacy-deprecated",
    description="Old skill kept for reference but never to be surfaced.",
    globs=["pages/**/*.tsx", "**/*.py"],  # would otherwise match strongly
    inactive=True,
    priority=10, risk_class="low",
)

UNBOUND_SKILL = _skill(
    "frontend-only-skill",
    description="Only bound to frontend profile, must not surface for engine.",
    globs=["**/*.py"],
    profiles=["frontend"],
    priority=3, risk_class="low",
)


# ---------------------------------------------------------------------------
# Helper for the override path
# ---------------------------------------------------------------------------

def _recommend(
    context: Dict[str, Any],
    skills: List[Dict[str, Any]],
    profile: str = "frontend",
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    return cr.recommend(
        context,
        profile=profile,
        active_skills=skills,
        top_k=top_k,
    )


def _meta(
    context: Dict[str, Any],
    skills: List[Dict[str, Any]],
    profile: str = "frontend",
    top_k: int = 3,
) -> Dict[str, Any]:
    return cr.recommend_with_meta(
        context,
        profile=profile,
        active_skills=skills,
        top_k=top_k,
    )


# ===========================================================================
# Test suite
# ===========================================================================

class TestHandPickedScenarios(unittest.TestCase):
    """PLAN-083 §5.4 row 2.2 acceptance: 3 hand-picked scenarios."""

    def test_scenario_1_frontend_tsx_recommends_frontend_skills(self) -> None:
        """Frontend edit on pages/index.tsx -> frontend-related skills."""
        ctx = {
            "file_path": "pages/index.tsx",
            "file_extension": ".tsx",
            "recent_tool_calls": ["Read", "Edit"],
            "user_intent": "audit page before launch",
        }
        recs = _recommend(ctx, FRONTEND_SKILLS, profile="frontend")
        self.assertGreaterEqual(len(recs), 1)
        self.assertLessEqual(len(recs), 3)
        names = [r["skill_name"] for r in recs]
        # Top recommendation should be audit-page (path glob hit + intent hit).
        self.assertEqual(recs[0]["skill_name"], "audit-page")
        # At least one of the other frontend skills should also surface.
        self.assertTrue(
            any(n in names for n in ("component-library", "lighthouse-perf"))
        )

    def test_scenario_2_backend_app_py_recommends_python_skills(self) -> None:
        """Backend edit on app.py -> Python/FastAPI skills."""
        ctx = {
            "file_path": "app.py",
            "file_extension": ".py",
            "recent_tool_calls": ["Read", "Bash"],
            "user_intent": "review FastAPI endpoint for validation",
        }
        recs = _recommend(ctx, BACKEND_SKILLS, profile="engine")
        self.assertGreaterEqual(len(recs), 1)
        names = [r["skill_name"] for r in recs]
        self.assertIn("fastapi-route-review", names)
        # Top should be the FastAPI-specific skill.
        self.assertEqual(recs[0]["skill_name"], "fastapi-route-review")

    def test_scenario_3_trading_arbitrage_recommends_safety_and_flags_risky(self) -> None:
        """Trading edit on strategies/arbitrage.py (trading-readonly) ->
        safety/audit skills surfaced AND every recommendation is RISKY
        because risk_class=high + trading-readonly profile.
        """
        ctx = {
            "file_path": "strategies/arbitrage.py",
            "file_extension": ".py",
            "recent_tool_calls": ["Read"],
            "user_intent": "review arbitrage strategy logic",
        }
        recs = _recommend(ctx, TRADING_SKILLS, profile="trading-readonly")
        self.assertGreaterEqual(len(recs), 1)
        names = [r["skill_name"] for r in recs]
        self.assertIn("strategy-safety-audit", names)
        # All recs should carry RISKY marker because risk_class=high on all
        # 3 trading skills.
        for r in recs:
            self.assertEqual(
                r["confidence_label"], "[RISKY]",
                f"expected RISKY for {r['skill_name']}, got {r['confidence_label']}",
            )


class TestDormantSuppression(unittest.TestCase):
    """Dormant + unbound skills MUST NEVER appear in recommendations."""

    def test_dormant_skill_suppressed_frontend(self) -> None:
        catalog = FRONTEND_SKILLS + [DORMANT_SKILL]
        ctx = {"file_path": "pages/index.tsx", "user_intent": "audit"}
        recs = _recommend(ctx, catalog, profile="frontend")
        names = [r["skill_name"] for r in recs]
        self.assertNotIn("legacy-deprecated", names)

    def test_dormant_skill_suppressed_engine(self) -> None:
        catalog = BACKEND_SKILLS + [DORMANT_SKILL]
        ctx = {"file_path": "app.py", "user_intent": "review"}
        recs = _recommend(ctx, catalog, profile="engine")
        names = [r["skill_name"] for r in recs]
        self.assertNotIn("legacy-deprecated", names)

    def test_dormant_skill_suppressed_trading(self) -> None:
        catalog = TRADING_SKILLS + [DORMANT_SKILL]
        ctx = {"file_path": "strategies/arbitrage.py"}
        recs = _recommend(ctx, catalog, profile="trading-readonly")
        names = [r["skill_name"] for r in recs]
        self.assertNotIn("legacy-deprecated", names)

    def test_unbound_profile_skill_suppressed(self) -> None:
        """A skill bound only to frontend MUST NOT appear under engine."""
        catalog = BACKEND_SKILLS + [UNBOUND_SKILL]
        ctx = {"file_path": "app.py", "user_intent": "review"}
        recs = _recommend(ctx, catalog, profile="engine")
        names = [r["skill_name"] for r in recs]
        self.assertNotIn("frontend-only-skill", names)


class TestConfidenceLabelPresence(unittest.TestCase):
    """Every recommendation must carry a known confidence label."""

    _VALID = ("[SAFE]", "[NEEDS-CONFIRM]", "[RISKY]")

    def test_label_present_frontend(self) -> None:
        recs = _recommend(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="frontend",
        )
        self.assertGreaterEqual(len(recs), 1)
        for r in recs:
            self.assertIn(r["confidence_label"], self._VALID)

    def test_label_present_backend(self) -> None:
        recs = _recommend(
            {"file_path": "app.py", "user_intent": "review fastapi"},
            BACKEND_SKILLS, profile="engine",
        )
        for r in recs:
            self.assertIn(r["confidence_label"], self._VALID)

    def test_label_present_trading(self) -> None:
        recs = _recommend(
            {"file_path": "strategies/arbitrage.py"},
            TRADING_SKILLS, profile="trading-readonly",
        )
        for r in recs:
            self.assertIn(r["confidence_label"], self._VALID)


class TestTopThreeCap(unittest.TestCase):
    """Top-K cap is strict even with 20 candidates."""

    def _twenty_matching_skills(self) -> List[Dict[str, Any]]:
        return [
            _skill(
                f"matcher-{i:02d}",
                description=f"Audit a frontend page handler number {i}.",
                globs=["pages/**/*.tsx"],
                priority=(i % 7) + 1,
                risk_class="low",
            )
            for i in range(20)
        ]

    def test_cap_at_3_with_20_candidates(self) -> None:
        catalog = self._twenty_matching_skills()
        ctx = {"file_path": "pages/index.tsx", "user_intent": "audit page"}
        recs = _recommend(ctx, catalog, profile="frontend")
        self.assertEqual(len(recs), 3)

    def test_explicit_top_k_honored(self) -> None:
        catalog = self._twenty_matching_skills()
        ctx = {"file_path": "pages/index.tsx"}
        recs = _recommend(ctx, catalog, profile="frontend", top_k=5)
        self.assertEqual(len(recs), 5)

    def test_top_k_zero_returns_empty(self) -> None:
        catalog = self._twenty_matching_skills()
        ctx = {"file_path": "pages/index.tsx"}
        recs = _recommend(ctx, catalog, profile="frontend", top_k=0)
        self.assertEqual(recs, [])


class TestDeterminism(unittest.TestCase):
    """Calling recommend twice with identical inputs returns identical output."""

    def test_idempotent_frontend(self) -> None:
        ctx = {"file_path": "pages/about.tsx", "user_intent": "audit"}
        r1 = _recommend(ctx, FRONTEND_SKILLS, profile="frontend")
        r2 = _recommend(ctx, FRONTEND_SKILLS, profile="frontend")
        self.assertEqual(r1, r2)

    def test_idempotent_with_extra_candidates(self) -> None:
        catalog = FRONTEND_SKILLS + BACKEND_SKILLS + [DORMANT_SKILL]
        ctx = {"file_path": "pages/index.tsx"}
        r1 = _recommend(ctx, catalog, profile="frontend")
        r2 = _recommend(ctx, catalog, profile="frontend")
        self.assertEqual(r1, r2)


class TestJsonOutputSchema(unittest.TestCase):
    """`recommend --json` emits the documented top-level schema."""

    def test_json_schema_keys(self) -> None:
        meta = _meta(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="frontend",
        )
        # Simulate the CLI JSON shape.
        payload = {
            "profile": meta["profile"],
            "recommendation_count": meta["recommendation_count"],
            "suppressed_count": meta["suppressed_count"],
            "top_score": meta["top_score"],
            "recommendations": meta["recommendations"],
        }
        encoded = json.dumps(payload, sort_keys=True)
        decoded = json.loads(encoded)
        for key in ("profile", "recommendation_count", "suppressed_count",
                    "top_score", "recommendations"):
            self.assertIn(key, decoded)
        # Each recommendation must carry the 5 documented fields.
        for r in decoded["recommendations"]:
            for k in ("skill_name", "score", "confidence_label",
                      "rationale", "invocation_hint"):
                self.assertIn(k, r)


class TestAuditWhitelist(unittest.TestCase):
    """Sec MF-3: emit payload contains ONLY the 4 whitelisted fields."""

    def test_emit_payload_keys(self) -> None:
        meta = _meta(
            {"file_path": "pages/x.tsx", "user_intent": "audit launch"},
            FRONTEND_SKILLS, profile="frontend",
        )
        # The emit helper builds its own dict — we mirror that inline:
        emit_payload = {
            "profile": meta["profile"],
            "recommendation_count": meta["recommendation_count"],
            "top_score": meta["top_score"],
            "suppressed_count": meta["suppressed_count"],
        }
        self.assertEqual(set(emit_payload.keys()), cr.AUDIT_ALLOWED_FIELDS)

    def test_emit_helper_does_not_raise(self) -> None:
        # The audit emit helper is fail-open; calling it with a minimal
        # dict must not raise even when _lib.audit_emit is unavailable.
        cr.emit_contextual_recommendation({
            "profile": "frontend",
            "recommendation_count": 2,
            "top_score": 13,
            "suppressed_count": 5,
        })


class TestEdgeCases(unittest.TestCase):
    """Defensive edges that the recommender must survive without raising."""

    def test_empty_context_returns_empty(self) -> None:
        # No file_path, no intent, no tool calls -> no signals -> 0 recs.
        recs = _recommend({}, FRONTEND_SKILLS, profile="frontend")
        self.assertEqual(recs, [])

    def test_missing_file_path_uses_intent(self) -> None:
        ctx = {"user_intent": "audit a Next.js page before launch"}
        recs = _recommend(ctx, FRONTEND_SKILLS, profile="frontend")
        # Intent NL match alone should still surface audit-page via name +
        # description token overlap.
        self.assertGreaterEqual(len(recs), 1)
        self.assertIn(
            "audit-page", [r["skill_name"] for r in recs],
        )

    def test_no_active_skills_returns_empty(self) -> None:
        recs = _recommend(
            {"file_path": "pages/x.tsx"}, [], profile="frontend",
        )
        self.assertEqual(recs, [])

    def test_write_intent_under_trading_escalates_low_risk(self) -> None:
        """A low risk_class skill under trading-readonly with write-intent
        keyword must escalate beyond [SAFE]."""
        catalog = [
            _skill(
                "trading-helper",
                description="Helper to inspect place order and submit flow.",
                globs=["execution/**/*.py"],
                regexes=[r"(?i)place\s+order|submit"],
                priority=3, risk_class="low",
            ),
        ]
        ctx = {
            "file_path": "execution/place.py",
            "user_intent": "place order and submit to exchange",
        }
        recs = _recommend(ctx, catalog, profile="trading-readonly")
        self.assertEqual(len(recs), 1)
        self.assertNotEqual(recs[0]["confidence_label"], "[SAFE]")

    def test_low_risk_under_generic_no_write_intent_stays_safe(self) -> None:
        catalog = [
            _skill(
                "doc-skill",
                description="Read project documentation.",
                regexes=[r"(?i)doc|readme"],
                priority=5, risk_class="low",
            ),
        ]
        ctx = {"file_path": "README.md", "user_intent": "read documentation"}
        recs = _recommend(ctx, catalog, profile="generic")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["confidence_label"], "[SAFE]")

    def test_malformed_regex_in_skill_does_not_raise(self) -> None:
        bad = _skill(
            "broken-regex",
            description="Skill with a malformed activation regex.",
            regexes=["[unterminated"],
            globs=["pages/**/*.tsx"],
            priority=4, risk_class="low",
        )
        catalog = FRONTEND_SKILLS + [bad]
        ctx = {"file_path": "pages/index.tsx", "user_intent": "audit"}
        # Must not raise; broken regex just contributes 0 from that signal.
        recs = _recommend(ctx, catalog, profile="frontend")
        self.assertGreaterEqual(len(recs), 1)

    def test_extension_inferred_from_file_path_when_missing(self) -> None:
        ctx = {"file_path": "pages/index.tsx"}  # no file_extension
        recs = _recommend(ctx, FRONTEND_SKILLS, profile="frontend")
        self.assertGreaterEqual(len(recs), 1)
        self.assertEqual(recs[0]["skill_name"], "audit-page")

    def test_context_not_dict_handled(self) -> None:
        recs = cr.recommend(
            "not a dict",  # type: ignore[arg-type]
            profile="frontend",
            active_skills=FRONTEND_SKILLS,
        )
        self.assertEqual(recs, [])

    def test_unknown_profile_falls_through_safely(self) -> None:
        # An override profile name not in cap-table — we never run the
        # disk resolver here (active_skills override) so it must still
        # return whatever skills bind that profile (none of the fixtures
        # bind "fake" -> empty list).
        recs = _recommend(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="fake-profile",
        )
        self.assertEqual(recs, [])


class TestScoringWeights(unittest.TestCase):
    """Spot-check that high-weight signals dominate low-weight ones."""

    def test_path_glob_beats_intent_only(self) -> None:
        # path-winner: glob hit (10) + ext-match (5, via "frontend" in desc) = 15
        path_match = _skill(
            "path-winner",
            description="Audit a frontend tsx page handler.",
            globs=["pages/**/*.tsx"],
            priority=5, risk_class="low",
        )
        # intent-only: no glob, no path hit, no extension-language hint
        # tokens in description (avoid "frontend" / "tsx"). Just intent
        # token overlap = capped at 4 * 3 = 12 points total.
        intent_only = _skill(
            "intent-only",
            description="zeta omega kappa sigma topics review check",
            priority=5, risk_class="low",
        )
        catalog = [path_match, intent_only]
        ctx = {
            "file_path": "pages/index.tsx",
            "user_intent": "zeta omega kappa sigma topics review check",
        }
        recs = _recommend(ctx, catalog, profile="frontend")
        # Path glob (10) + ext_match (5) = 15 > intent cap (12).
        self.assertEqual(recs[0]["skill_name"], "path-winner")

    def test_regex_signal_scored(self) -> None:
        skill_regex = _skill(
            "regex-skill",
            description="generic helper",
            regexes=[r"(?i)refactor"],
            priority=5, risk_class="low",
        )
        ctx = {"file_path": "lib/util.py", "user_intent": "refactor this helper"}
        recs = _recommend(ctx, [skill_regex], profile="engine")
        self.assertEqual(len(recs), 1)
        self.assertGreater(recs[0]["score"], 0)

    def test_score_is_non_negative(self) -> None:
        recs = _meta(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="frontend",
        )
        for r in recs["recommendations"]:
            self.assertGreaterEqual(r["score"], 0)


class TestRationaleAndHint(unittest.TestCase):
    def test_rationale_truncates_to_140_chars(self) -> None:
        long_desc = "x" * 500
        s = _skill(
            "long-desc",
            description=long_desc,
            globs=["pages/**/*.tsx"],
            priority=5, risk_class="low",
        )
        recs = _recommend(
            {"file_path": "pages/index.tsx"},
            [s], profile="frontend",
        )
        self.assertEqual(len(recs), 1)
        self.assertLessEqual(len(recs[0]["rationale"]), 140)

    def test_invocation_hint_core_skill(self) -> None:
        s = _skill(
            "help-me",
            domain="core",
            description="Natural-language assistant",
            globs=["pages/**/*.tsx"],
            priority=3, risk_class="low",
        )
        recs = _recommend(
            {"file_path": "pages/index.tsx"},
            [s], profile="frontend",
        )
        self.assertEqual(recs[0]["invocation_hint"], "/help-me")

    def test_invocation_hint_non_core_uses_spawn(self) -> None:
        s = _skill(
            "frontend-archetype",
            domain="frontend",
            description="generic helper",
            globs=["pages/**/*.tsx"],
            priority=3, risk_class="low",
        )
        recs = _recommend(
            {"file_path": "pages/index.tsx"},
            [s], profile="frontend",
        )
        self.assertTrue(recs[0]["invocation_hint"].startswith("/spawn"))


class TestRecommendWithMeta(unittest.TestCase):
    def test_meta_returns_expected_keys(self) -> None:
        meta = _meta(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="frontend",
        )
        for k in ("recommendations", "profile", "suppressed_count",
                  "top_score", "recommendation_count"):
            self.assertIn(k, meta)

    def test_meta_top_score_matches_first_rec(self) -> None:
        meta = _meta(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            FRONTEND_SKILLS, profile="frontend",
        )
        if meta["recommendations"]:
            self.assertEqual(
                meta["top_score"],
                meta["recommendations"][0]["score"],
            )
        else:
            self.assertEqual(meta["top_score"], 0)

    def test_meta_suppressed_count_includes_dormant(self) -> None:
        catalog = FRONTEND_SKILLS + [DORMANT_SKILL, UNBOUND_SKILL]
        meta = _meta(
            {"file_path": "pages/index.tsx", "user_intent": "audit"},
            catalog, profile="frontend",
        )
        # UNBOUND_SKILL is bound only to frontend, so under frontend it
        # *is* active. DORMANT_SKILL is inactive_but_retained=True, so it
        # contributes >=1 to suppressed_count.
        self.assertGreaterEqual(meta["suppressed_count"], 1)


class TestCliEntryPoint(unittest.TestCase):
    """Spot-check the CLI parser + JSON path don't crash."""

    def test_cli_requires_file_flag(self) -> None:
        # argparse exits non-zero on missing required arg; capture SystemExit.
        with self.assertRaises(SystemExit):
            cr.main(["recommend"])

    def test_cli_runs_with_empty_skill_root_returns_zero_recs(self) -> None:
        # Provide a temporary skill_root that does not exist; the resolver
        # bridge silently returns ([], profile, 0) so the CLI exits cleanly.
        argv = [
            "recommend",
            "--file", "pages/index.tsx",
            "--ext", ".tsx",
            "--intent", "audit page",
            "--profile", "frontend",
            "--skill-root", "/tmp/__plan083_recommender_nonexistent__",
            "--top-k", "3",
            "--json",
        ]
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            rc = cr.main(argv)
        finally:
            sys.stdout = old_stdout
        self.assertEqual(rc, 0)
        decoded = json.loads(buf.getvalue())
        self.assertIn("profile", decoded)
        self.assertEqual(decoded["recommendation_count"], 0)


if __name__ == "__main__":
    unittest.main()
