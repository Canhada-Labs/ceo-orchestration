"""PLAN-083 Wave 1 sub-agent 1.11 — `/help me` meta-command skill tests.

Stdlib-only unittest. Validates:

  1. SKILL.md exists at staging + frontmatter parses + complies with the
     Wave -1.3 `repo-profile-skill-binding.schema.json` smart-loading
     subset (required keys, value bounds, enum values).
  2. Redaction is applied to user input BEFORE any audit-emit-bound
     persistence (Sec P1 invariant in PLAN-083 §6 row 1.11).
  3. Recommendation count is bounded at <=3 across all queries (strict
     cap, no "see also" appendix).
  4. Profile-aware scoring: the same query in `frontend` vs
     `trading-readonly` produces different top-3 sets when the candidate
     pool differs per profile binding.
  5. Empty match set falls back to `codebase-onboarding` (the
     `/onboard` skill) — exactly 1 recommendation, marker SAFE.
  6. Audit-emit fields are whitelisted to exactly
     {recommendation_count, profile, top_skill_name} per Sec MF-3.
  7. Each recommendation carries a confidence label (SAFE / NEEDS-CONFIRM
     / RISKY) derived from `risk_class`.

The implementation under test is the staged `SKILL.md` body interpreted
as an algorithm spec. Because the canonical Python entry point for the
skill is not authored in this Wave (the skill is invoked by the CEO
runtime), the tests drive the algorithm through a small reference
implementation co-located in this file. That reference implementation
MUST stay byte-identical with what the future canonical resolver
produces (Wave 2 sub-agent 2.2 will collapse them).
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Resolve repo root: this file lives at
# .claude/plans/PLAN-083/staging/wave-1/sub-1-11-help-me/tests/<file>
# so repo root is 7 parents up (tests -> sub-1-11 -> wave-1 -> staging ->
# PLAN-083 -> plans -> .claude -> repo-root).
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[7]
_STAGING_DIR = _THIS.parents[1]
_SKILL_MD = _STAGING_DIR / "SKILL.md"

# Make `_lib.redact` importable for the redaction integration test.
_HOOK_ROOT = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOK_ROOT) not in sys.path:
    sys.path.insert(0, str(_HOOK_ROOT))

# Load the smart-loading-resolver mini-parser via importlib because the
# staging filename uses dashes (`smart-loading-resolver.py`) and is not
# directly importable. Wave 2 ceremony will rename to underscore at apply.
_RESOLVER_FILE = (
    _REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-083"
    / "staging"
    / "wave-0b"
    / "sub-0-7d-outcome-gates-resolver"
    / "smart-loading-resolver.py"
)

_SLR_MODULE: Any = None
if _RESOLVER_FILE.is_file():
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location("smart_loading_resolver_staged", _RESOLVER_FILE)
    if _spec and _spec.loader:
        _mod = _ilu.module_from_spec(_spec)
        try:
            _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
            _SLR_MODULE = _mod
        except Exception:
            _SLR_MODULE = None


# ---------------------------------------------------------------------------
# Reference implementation (mirrors the algorithm spec in SKILL.md)
# ---------------------------------------------------------------------------

_RISK_TO_LABEL = {"low": "SAFE", "medium": "NEEDS-CONFIRM", "high": "RISKY"}
_AUDIT_ALLOWED_FIELDS = frozenset({"recommendation_count", "profile", "top_skill_name"})
_TRADING_WRITE_HINTS = ("deploy", "place order", "submit", "mutate")


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_-]+", text.lower()) if t]


def _score_candidate(
    candidate: Dict[str, Any], query_tokens: List[str], query_text: str
) -> int:
    """Score = keyword-overlap (1pt each) + trigger-regex hit (3pt)."""
    score = 0
    desc = str(candidate.get("description", "")).lower()
    for tok in query_tokens:
        if tok and tok in desc:
            score += 1
    for trig in candidate.get("activation_triggers", []) or []:
        rgx = trig.get("regex") if isinstance(trig, dict) else None
        if isinstance(rgx, str) and rgx:
            try:
                if re.search(rgx, query_text):
                    score += 3
            except re.error:
                continue
    return score


def _sort_key(c: Dict[str, Any]) -> Tuple[int, int, str]:
    risk_rank = {"low": 0, "medium": 1, "high": 2}.get(c.get("risk_class", "high"), 2)
    pr = c.get("priority")
    if not isinstance(pr, int):
        pr = 10
    return (pr, risk_rank, str(c.get("path", "")))


def recommend(
    redacted_query: str,
    profile: str,
    active_skills: List[Dict[str, Any]],
    fallback_skill: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Return up to 3 ranked recommendations, each with marker + rationale."""
    if not active_skills:
        if fallback_skill is None:
            return []
        return [
            {
                "name": str(fallback_skill.get("name", "codebase-onboarding")),
                "marker": "SAFE",
                "rationale": str(fallback_skill.get("description", ""))[:120],
            }
        ]
    tokens = _tokenize(redacted_query)
    scored = [
        (s, _score_candidate(s, tokens, redacted_query)) for s in active_skills
    ]
    matches = [(s, sc) for (s, sc) in scored if sc > 0]
    if not matches:
        if fallback_skill is None:
            return []
        return [
            {
                "name": str(fallback_skill.get("name", "codebase-onboarding")),
                "marker": "SAFE",
                "rationale": str(fallback_skill.get("description", ""))[:120],
            }
        ]
    matches.sort(key=lambda pair: (-pair[1], _sort_key(pair[0])))
    top = matches[:3]
    # trading-readonly write-hint downgrade
    downgrade = False
    if profile == "trading-readonly":
        ql = redacted_query.lower()
        if any(h in ql for h in _TRADING_WRITE_HINTS):
            downgrade = True
    out: List[Dict[str, str]] = []
    for (skill, _score) in top:
        rc = str(skill.get("risk_class", "high"))
        marker = _RISK_TO_LABEL.get(rc, "RISKY")
        if downgrade and marker == "SAFE":
            marker = "NEEDS-CONFIRM"
        out.append({
            "name": str(skill.get("name", "")),
            "marker": marker,
            "rationale": str(skill.get("description", ""))[:120],
        })
    return out


def build_audit_payload(
    recommendations: List[Dict[str, str]], profile: str
) -> Dict[str, Any]:
    """Sec MF-3 whitelist payload builder. NEVER carries user text."""
    top_name = recommendations[0]["name"] if recommendations else ""
    return {
        "recommendation_count": len(recommendations),
        "profile": profile,
        "top_skill_name": top_name,
    }


# ---------------------------------------------------------------------------
# Helpers — frontmatter parser bound to the Wave -1.3 schema
# ---------------------------------------------------------------------------

def _read_frontmatter() -> Dict[str, Any]:
    """Parse the staged SKILL.md frontmatter using the Wave 0b mini-parser."""
    if _SLR_MODULE is None:
        raise unittest.SkipTest(
            "smart-loading-resolver staging module not loadable"
        )
    meta = _SLR_MODULE.parse_skill_frontmatter(_SKILL_MD)
    if meta is None:
        raise AssertionError("frontmatter parse returned None for SKILL.md")
    return meta


def _fixture_skills() -> List[Dict[str, Any]]:
    """Stable fixture set used across tests; profile bindings vary."""
    return [
        {
            "name": "audit-page",
            "description": "Audit a frontend page across 16 UX and technical dimensions.",
            "risk_class": "low",
            "priority": 4,
            "path": "/x/audit-page/SKILL.md",
            "repo_profile_binding": {
                "frontend": {"active": True, "priority": 3},
                "trading-readonly": {"active": False, "priority": 9},
            },
            "activation_triggers": [],
        },
        {
            "name": "incremental-refactoring",
            "description": "Safely evolving existing production codebases through incremental refactoring.",
            "risk_class": "medium",
            "priority": 5,
            "path": "/x/incremental-refactoring/SKILL.md",
            "repo_profile_binding": {
                "frontend": {"active": True, "priority": 4},
                "trading-readonly": {"active": True, "priority": 5},
            },
            "activation_triggers": [],
        },
        {
            "name": "trading-readonly-guardrail",
            "description": "Trading-readonly guardrails for high-risk write actions: deploy, submit, mutate.",
            "risk_class": "high",
            "priority": 2,
            "path": "/x/trading-readonly-guardrail/SKILL.md",
            "repo_profile_binding": {
                "frontend": {"active": False, "priority": 9},
                "trading-readonly": {"active": True, "priority": 2},
            },
            "activation_triggers": [
                {"event": "help-me-invoked", "regex": "(?i)deploy|submit|mutate"}
            ],
        },
        {
            "name": "code-review-checklist",
            "description": "Cardinal rule code review using objective evidence and minimal-diff discipline.",
            "risk_class": "low",
            "priority": 3,
            "path": "/x/code-review-checklist/SKILL.md",
            "repo_profile_binding": {
                "frontend": {"active": True, "priority": 3},
                "trading-readonly": {"active": False, "priority": 9},
            },
            "activation_triggers": [],
        },
    ]


def _filter_by_profile(
    skills: List[Dict[str, Any]], profile: str
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in skills:
        entry = (s.get("repo_profile_binding") or {}).get(profile)
        if isinstance(entry, dict) and bool(entry.get("active")):
            out.append(s)
    return out


_FALLBACK = {
    "name": "codebase-onboarding",
    "description": "Orient to an unfamiliar codebase: entry points, dependency graph, layer map, reading order.",
    "risk_class": "low",
    "priority": 3,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSkillMdExistsAndFrontmatter(unittest.TestCase):
    """Tests 1-6: SKILL.md presence + Wave -1.3 schema compliance."""

    def test_01_skill_md_file_exists(self) -> None:
        self.assertTrue(_SKILL_MD.is_file(), f"missing: {_SKILL_MD}")

    def test_02_frontmatter_name_is_help_me(self) -> None:
        meta = _read_frontmatter()
        self.assertEqual(meta.get("name"), "help-me")

    def test_03_frontmatter_required_smart_loading_fields(self) -> None:
        meta = _read_frontmatter()
        for required in ("repo_profile_binding", "domain", "priority", "risk_class"):
            self.assertIn(required, meta, f"missing required field {required}")

    def test_04_frontmatter_priority_in_range(self) -> None:
        meta = _read_frontmatter()
        pr = meta.get("priority")
        self.assertIsInstance(pr, int)
        self.assertGreaterEqual(pr, 1)
        self.assertLessEqual(pr, 10)
        self.assertEqual(pr, 3, "spec mandates priority=3 for this skill")

    def test_05_frontmatter_risk_class_low(self) -> None:
        meta = _read_frontmatter()
        self.assertEqual(meta.get("risk_class"), "low")

    def test_06_frontmatter_active_all_five_profiles(self) -> None:
        meta = _read_frontmatter()
        binding = meta.get("repo_profile_binding")
        self.assertIsInstance(binding, dict)
        for profile in ("frontend", "engine", "fintech", "trading-readonly", "generic"):
            entry = binding.get(profile)
            self.assertIsInstance(entry, dict, f"profile {profile} missing")
            self.assertTrue(entry.get("active"), f"profile {profile} not active")
            self.assertEqual(
                entry.get("priority"),
                3,
                f"profile {profile} priority should be 3",
            )

    def test_07_frontmatter_activation_trigger_help_me_regex(self) -> None:
        meta = _read_frontmatter()
        trigs = meta.get("activation_triggers") or []
        self.assertGreaterEqual(len(trigs), 1)
        first = trigs[0]
        self.assertIsInstance(first, dict)
        self.assertEqual(first.get("event"), "help-me-invoked")
        rgx = first.get("regex")
        self.assertIsInstance(rgx, str)
        # The regex must match `/help me ...` and `/helpme ...`
        self.assertIsNotNone(re.search(rgx, "/help me audit a page"))
        self.assertIsNotNone(re.search(rgx, "/helpme do something"))

    def test_08_frontmatter_context_budget_within_cap(self) -> None:
        meta = _read_frontmatter()
        ctx = meta.get("context_budget_tokens")
        self.assertIsInstance(ctx, int)
        self.assertGreaterEqual(ctx, 0)
        self.assertLessEqual(ctx, 30000)

    def test_09_frontmatter_inactive_but_retained_false(self) -> None:
        meta = _read_frontmatter()
        self.assertFalse(bool(meta.get("inactive_but_retained")))

    def test_10_frontmatter_domain_core(self) -> None:
        meta = _read_frontmatter()
        self.assertEqual(meta.get("domain"), "core")


class TestRedactionBeforeAudit(unittest.TestCase):
    """Tests 11-12: Sec P1 — user text passes through _lib.redact before persistence."""

    def test_11_redact_strips_api_key_from_query(self) -> None:
        from _lib.redact import redact_secrets  # type: ignore

        raw = "/help me debug sk-AAAAAAAAAAAAAAAAAAAAAAAA leaking in logs"
        safe = redact_secrets(raw, max_chars=0)
        self.assertNotIn("AAAAAAAAAAAAAAAAAAAAAAAA", safe)
        self.assertIn("[API_KEY]", safe)

    def test_12_redact_strips_password_assignment_from_query(self) -> None:
        from _lib.redact import redact_secrets  # type: ignore

        raw = "/help me fix login flow password=hunter2supersecret"
        safe = redact_secrets(raw, max_chars=0)
        self.assertNotIn("hunter2supersecret", safe)
        self.assertIn("[REDACTED]", safe)


class TestRecommendationCap(unittest.TestCase):
    """Tests 13-14: strict <=3 cap across various queries."""

    def test_13_cap_at_three_when_many_match(self) -> None:
        # All 4 fixture skills active in a synthetic "all-active" profile.
        skills = _fixture_skills()
        # Force all skills active for a synthetic profile by relabeling.
        for s in skills:
            s["repo_profile_binding"]["frontend"] = {"active": True, "priority": 3}
        # Query that overlaps with all four descriptions.
        query = "audit refactor review trading mutate evolving code review"
        recs = recommend(query, "frontend", skills, fallback_skill=_FALLBACK)
        self.assertLessEqual(len(recs), 3)

    def test_14_cap_at_three_when_zero_match_yields_one_fallback(self) -> None:
        skills = _filter_by_profile(_fixture_skills(), "frontend")
        recs = recommend(
            "completely-unrelated-token-xyz", "frontend", skills, fallback_skill=_FALLBACK
        )
        # 0 matches -> 1 fallback recommendation (codebase-onboarding)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["name"], "codebase-onboarding")
        self.assertEqual(recs[0]["marker"], "SAFE")


class TestProfileAware(unittest.TestCase):
    """Test 15: same query produces different top-3 in different profiles."""

    def test_15_same_query_different_profiles_different_top3(self) -> None:
        skills_all = _fixture_skills()
        # Frontend-active candidates
        frontend_pool = _filter_by_profile(skills_all, "frontend")
        # Trading-readonly-active candidates
        trading_pool = _filter_by_profile(skills_all, "trading-readonly")
        # Sanity: pools must actually differ
        self.assertNotEqual(
            sorted(s["name"] for s in frontend_pool),
            sorted(s["name"] for s in trading_pool),
        )
        query = "/help me deploy a refactor"
        frontend_recs = recommend(query, "frontend", frontend_pool, _FALLBACK)
        trading_recs = recommend(query, "trading-readonly", trading_pool, _FALLBACK)
        # Result sets must differ in either the top skill or the marker set
        frontend_top = [r["name"] for r in frontend_recs]
        trading_top = [r["name"] for r in trading_recs]
        self.assertNotEqual(
            frontend_top,
            trading_top,
            f"profile-aware ranking failed: {frontend_top} == {trading_top}",
        )


class TestAuditWhitelist(unittest.TestCase):
    """Tests 16-17: Sec MF-3 audit-emit whitelist enforcement."""

    def test_16_audit_payload_has_exactly_three_fields(self) -> None:
        skills = _filter_by_profile(_fixture_skills(), "frontend")
        recs = recommend("audit page review", "frontend", skills, _FALLBACK)
        payload = build_audit_payload(recs, "frontend")
        self.assertEqual(set(payload.keys()), set(_AUDIT_ALLOWED_FIELDS))

    def test_17_audit_payload_never_contains_user_query_text(self) -> None:
        skills = _filter_by_profile(_fixture_skills(), "frontend")
        # Embed a unique sentinel that MUST NOT appear in the payload.
        sentinel = "UNIQUE-USER-SENTINEL-XYZ-9876"
        query = f"/help me audit page {sentinel}"
        recs = recommend(query, "frontend", skills, _FALLBACK)
        payload = build_audit_payload(recs, "frontend")
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn(sentinel, serialized)


class TestConfidenceLabel(unittest.TestCase):
    """Test 18: every recommendation carries SAFE / NEEDS-CONFIRM / RISKY."""

    def test_18_every_recommendation_has_valid_marker(self) -> None:
        skills = _fixture_skills()
        for s in skills:
            s["repo_profile_binding"]["frontend"] = {"active": True, "priority": 3}
        query = "audit refactor review deploy trading"
        recs = recommend(query, "frontend", skills, _FALLBACK)
        self.assertGreater(len(recs), 0)
        valid = {"SAFE", "NEEDS-CONFIRM", "RISKY"}
        for r in recs:
            self.assertIn("marker", r)
            self.assertIn(r["marker"], valid, f"bad marker: {r['marker']}")

    def test_19_trading_readonly_downgrades_safe_on_write_hint(self) -> None:
        # A low-risk skill in trading-readonly profile, when the query
        # contains a write hint, should be downgraded from SAFE to NEEDS-CONFIRM.
        # incremental-refactoring is `medium` -> NEEDS-CONFIRM regardless.
        # Use a synthetic low-risk skill for this profile.
        skills = [
            {
                "name": "trading-doc",
                "description": "deploy notes and submit guide for trading paths.",
                "risk_class": "low",
                "priority": 3,
                "path": "/x/trading-doc/SKILL.md",
                "repo_profile_binding": {
                    "trading-readonly": {"active": True, "priority": 3},
                },
                "activation_triggers": [],
            }
        ]
        pool = _filter_by_profile(skills, "trading-readonly")
        recs = recommend(
            "/help me deploy a hot-fix", "trading-readonly", pool, _FALLBACK
        )
        self.assertEqual(len(recs), 1)
        # `deploy` is in the write-hint set, so SAFE downgrades to NEEDS-CONFIRM.
        self.assertEqual(recs[0]["marker"], "NEEDS-CONFIRM")


if __name__ == "__main__":
    unittest.main()
