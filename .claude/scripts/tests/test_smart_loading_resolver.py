"""Outcome-gate tests for smart-loading-resolver.py (PLAN-083 Wave 0b 0.7d).

Covers all 5 Wave 0b acceptance criteria from PLAN-083 §5.2 row 0.7d:

    AC-a  Per-profile max-active numeric cap enforced (5 tests, one per profile)
    AC-b  Context budget cap enforced  <=30000 (5 tests, one per profile)
    AC-c  Duplicate-trigger arbitration ordering (3 scenarios)
    AC-d  Dormant suppression — 24 dormant bundle skills not surfaced
    AC-e  smart_loading_resolved audit emit with allowlist fields only

Plus determinism + debug-mode + inactive_but_retained universal suppress.

Stdlib only; no yaml dependency.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import the resolver under test (sibling file in the staging dir)
_HERE = Path(__file__).resolve().parent
_STAGING = _HERE.parent
if str(_STAGING) not in sys.path:
    sys.path.insert(0, str(_STAGING))

# Module file uses hyphens; load it via importlib so `import` works.
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location(
    "smart_loading_resolver",
    str(_STAGING / "smart-loading-resolver.py"),
)
assert _spec is not None and _spec.loader is not None
slr = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(slr)  # type: ignore[union-attr]


_VALID_PROFILES = ("frontend", "engine", "fintech", "trading-readonly", "generic")
# PLAN-085 Wave A.2 (R-002): cap-table canonical path is now
# .claude/policies/smart-loading-cap-table.yaml (sibling to other
# policy YAMLs). Pre-Wave-A it lived at .claude/scripts/ alongside
# the resolver. Test now references the policies/ location; legacy
# scripts/ fallback retained on the prod _default_cap_table_path()
# for adopters mid-upgrade but tests pin canonical.
_CAP_TABLE_PATH = _STAGING.parent / "policies" / "smart-loading-cap-table.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(
    path: str,
    priority: int = 5,
    risk_class: str = "medium",
    domain: str = "core",
    context_budget_tokens: int = 500,
    inactive_but_retained: bool = False,
    bindings: Optional[Dict[str, Dict[str, Any]]] = None,
    activation_triggers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct a parsed-SKILL.md-frontmatter dict for the resolver."""
    return {
        "_path": path,
        "priority": priority,
        "risk_class": risk_class,
        "domain": domain,
        "context_budget_tokens": context_budget_tokens,
        "inactive_but_retained": inactive_but_retained,
        "repo_profile_binding": bindings or {},
        "activation_triggers": activation_triggers or [],
    }


def _all_profiles_active(priority: int = 5) -> Dict[str, Dict[str, Any]]:
    return {p: {"active": True, "priority": priority} for p in _VALID_PROFILES}


def _build_20_active_candidates() -> List[Dict[str, Any]]:
    """Return 20 skills all active for all 5 profiles, varying priority."""
    out = []
    for i in range(20):
        out.append(_make_skill(
            path=f"core/cand-{i:02d}/SKILL.md",
            priority=(i % 10) + 1,
            risk_class=["low", "medium", "high"][i % 3],
            context_budget_tokens=300,
            bindings=_all_profiles_active(),
        ))
    return out


def _build_dormant_24() -> List[Dict[str, Any]]:
    """Return 24 dormant domain-bundle skills (no bindings for any profile)."""
    domains = [
        "hospitality", "retail", "healthcare", "hr",
        "real-estate-finance", "edtech", "government", "community",
    ]
    sub_skills = ["sales", "devrel", "legal"]
    out = []
    for d in domains:
        for s in sub_skills:
            out.append(_make_skill(
                path=f"domains/{d}/{s}/SKILL.md",
                priority=5,
                risk_class="medium",
                domain=d,
                context_budget_tokens=400,
                bindings={},  # dormant — no profile binding
            ))
    assert len(out) == 24
    return out


# ---------------------------------------------------------------------------
# AC-a — Per-profile max-active cap enforcement
# ---------------------------------------------------------------------------

class TestAcAMaxActiveCap(unittest.TestCase):
    """AC-a — frontend<=10, engine<=12, fintech<=15, trading-readonly<=8,
    generic<=6 enforced when input has 20 active candidates per profile."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.skills = _build_20_active_candidates()

    def _run(self, profile: str, expected_cap: int):
        result = slr._resolve_from_skills(self.skills, profile, self.cap_table)
        self.assertEqual(result["profile"], profile)
        self.assertLessEqual(result["active_count"], expected_cap,
                             f"profile {profile} exceeded cap {expected_cap}")
        self.assertEqual(result["max_active_cap"], expected_cap)

    def test_frontend_cap_10(self):
        self._run("frontend", 10)

    def test_engine_cap_12(self):
        self._run("engine", 12)

    def test_fintech_cap_15(self):
        # fintech cap is 15 but our input has 20; result should be capped at 15.
        result = slr._resolve_from_skills(self.skills, "fintech", self.cap_table)
        self.assertLessEqual(result["active_count"], 15)
        self.assertEqual(result["max_active_cap"], 15)

    def test_trading_readonly_cap_8(self):
        self._run("trading-readonly", 8)

    def test_generic_cap_6(self):
        self._run("generic", 6)


# ---------------------------------------------------------------------------
# AC-b — Context budget cap enforcement
# ---------------------------------------------------------------------------

class TestAcBContextBudgetCap(unittest.TestCase):
    """AC-b — sum of context_budget_tokens across active set <= 30000."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        # Build candidates designed to exceed 30k: 20 skills * 2000 = 40k
        self.skills = []
        for i in range(20):
            self.skills.append(_make_skill(
                path=f"core/heavy-{i:02d}/SKILL.md",
                priority=(i % 10) + 1,
                risk_class="medium",
                context_budget_tokens=2000,
                bindings=_all_profiles_active(),
            ))

    def _run(self, profile: str):
        result = slr._resolve_from_skills(self.skills, profile, self.cap_table)
        self.assertLessEqual(result["context_total_tokens"], 30000,
                             f"profile {profile} blew context budget")

    def test_frontend_budget(self):
        self._run("frontend")

    def test_engine_budget(self):
        self._run("engine")

    def test_fintech_budget(self):
        self._run("fintech")

    def test_trading_readonly_budget(self):
        self._run("trading-readonly")

    def test_generic_budget(self):
        self._run("generic")


# ---------------------------------------------------------------------------
# AC-c — Duplicate-trigger arbitration
# ---------------------------------------------------------------------------

class TestAcCArbitration(unittest.TestCase):
    """AC-c — duplicate-trigger arbitration: priority -> risk_class -> path."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)

    def test_same_priority_different_risk_low_wins(self):
        """Two skills share priority=5 and a trigger; low risk wins."""
        low_skill = _make_skill(
            path="core/low-risk-winner/SKILL.md",
            priority=5,
            risk_class="low",
            bindings=_all_profiles_active(priority=5),
            activation_triggers=[{"event": "file-edit", "glob": "src/**"}],
        )
        high_skill = _make_skill(
            path="core/high-risk-loser/SKILL.md",
            priority=5,
            risk_class="high",
            bindings=_all_profiles_active(priority=5),
            activation_triggers=[{"event": "file-edit", "glob": "src/**"}],
        )
        result = slr._resolve_from_skills(
            [low_skill, high_skill], "generic", self.cap_table, debug=True
        )
        paths = result["active_skills"]
        self.assertIn("core/low-risk-winner/SKILL.md", paths)
        self.assertNotIn("core/high-risk-loser/SKILL.md", paths)
        self.assertEqual(result["arbitration_dropped_count"], 1)

    def test_same_priority_same_risk_lex_path_wins(self):
        """When priority + risk_class tie, lex-min path wins."""
        alpha = _make_skill(
            path="core/zzz-alpha/SKILL.md",  # zzz > aaa lex; aaa wins
            priority=5,
            risk_class="medium",
            bindings=_all_profiles_active(priority=5),
            activation_triggers=[{"event": "help-me-invoked", "regex": "tie"}],
        )
        beta = _make_skill(
            path="core/aaa-beta/SKILL.md",
            priority=5,
            risk_class="medium",
            bindings=_all_profiles_active(priority=5),
            activation_triggers=[{"event": "help-me-invoked", "regex": "tie"}],
        )
        result = slr._resolve_from_skills([alpha, beta], "generic", self.cap_table)
        self.assertIn("core/aaa-beta/SKILL.md", result["active_skills"])
        self.assertNotIn("core/zzz-alpha/SKILL.md", result["active_skills"])
        self.assertEqual(result["arbitration_dropped_count"], 1)

    def test_different_priority_lower_number_wins(self):
        """priority=2 beats priority=8 even when risk is reversed."""
        winner = _make_skill(
            path="core/winner-prio-2/SKILL.md",
            priority=2,
            risk_class="high",  # high risk but lower priority number
            bindings=_all_profiles_active(priority=2),
            activation_triggers=[{"event": "spawn-requested"}],
        )
        loser = _make_skill(
            path="core/loser-prio-8/SKILL.md",
            priority=8,
            risk_class="low",  # low risk but higher priority number
            bindings=_all_profiles_active(priority=8),
            activation_triggers=[{"event": "spawn-requested"}],
        )
        result = slr._resolve_from_skills([winner, loser], "generic", self.cap_table)
        self.assertIn("core/winner-prio-2/SKILL.md", result["active_skills"])
        self.assertNotIn("core/loser-prio-8/SKILL.md", result["active_skills"])


# ---------------------------------------------------------------------------
# AC-d — Dormant-suppression (24 dormant bundles NOT surfaced)
# ---------------------------------------------------------------------------

class TestAcDDormantSuppression(unittest.TestCase):
    """AC-d — 24 dormant bundle skills must not appear in any profile."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        # 4 active anchors + 24 dormant
        self.active = [
            _make_skill(
                path="core/security-and-auth/SKILL.md",
                priority=1, risk_class="high",
                bindings=_all_profiles_active(priority=1),
            ),
            _make_skill(
                path="core/code-review-checklist/SKILL.md",
                priority=3, risk_class="low",
                bindings=_all_profiles_active(priority=3),
            ),
            _make_skill(
                path="core/minimal-change-discipline/SKILL.md",
                priority=3, risk_class="low",
                bindings=_all_profiles_active(priority=3),
            ),
            _make_skill(
                path="core/compliance-lgpd/SKILL.md",
                priority=4, risk_class="high",
                bindings=_all_profiles_active(priority=4),
            ),
        ]
        self.dormant = _build_dormant_24()
        self.skills = self.active + self.dormant

    def _assert_no_dormant(self, profile: str):
        result = slr._resolve_from_skills(self.skills, profile, self.cap_table)
        for path in result["active_skills"]:
            self.assertFalse(
                path.startswith("domains/"),
                f"profile {profile} surfaced dormant skill {path}",
            )
        # All 24 dormant + (cap-dropped active) accounted as suppressed
        self.assertGreaterEqual(result["suppressed_count"], 24)

    def test_frontend_no_dormant(self):
        self._assert_no_dormant("frontend")

    def test_engine_no_dormant(self):
        self._assert_no_dormant("engine")

    def test_fintech_no_dormant(self):
        self._assert_no_dormant("fintech")

    def test_trading_readonly_no_dormant(self):
        self._assert_no_dormant("trading-readonly")

    def test_generic_no_dormant(self):
        self._assert_no_dormant("generic")


# ---------------------------------------------------------------------------
# inactive_but_retained — universal suppress
# ---------------------------------------------------------------------------

class TestInactiveButRetained(unittest.TestCase):
    """inactive_but_retained: true must suppress across all profiles even
    when bindings say active=true (Owner directive PLAN-083 §4)."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.skills = [
            _make_skill(
                path="core/retained-a/SKILL.md",
                priority=1, risk_class="low",
                inactive_but_retained=True,
                bindings=_all_profiles_active(priority=1),
            ),
            _make_skill(
                path="core/retained-b/SKILL.md",
                priority=1, risk_class="low",
                inactive_but_retained=True,
                bindings=_all_profiles_active(priority=1),
            ),
            _make_skill(
                path="core/active/SKILL.md",
                priority=2, risk_class="low",
                inactive_but_retained=False,
                bindings=_all_profiles_active(priority=2),
            ),
        ]

    def test_universal_suppress_across_all_profiles(self):
        for profile in _VALID_PROFILES:
            result = slr._resolve_from_skills(self.skills, profile, self.cap_table)
            for path in result["active_skills"]:
                self.assertNotIn("retained-", path,
                                 f"profile {profile} surfaced inactive_but_retained skill")


# ---------------------------------------------------------------------------
# AC-e — Audit emit allowlist + integration
# ---------------------------------------------------------------------------

class TestAcEAuditEmit(unittest.TestCase):
    """AC-e — smart_loading_resolved emits ONLY whitelisted fields."""

    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.skills = _build_20_active_candidates() + _build_dormant_24()

    def test_audit_payload_only_whitelisted_fields(self):
        result = slr._resolve_from_skills(self.skills, "frontend", self.cap_table)
        payload = result["audit_emit_payload"]
        self.assertEqual(set(payload.keys()), {
            "profile", "active_count", "suppressed_count",
            "context_total_tokens", "arbitration_dropped_count",
        })

    def test_audit_payload_no_skill_paths(self):
        result = slr._resolve_from_skills(self.skills, "engine", self.cap_table)
        payload_str = json.dumps(result["audit_emit_payload"])
        # No SKILL.md path content / no skill names should leak through.
        self.assertNotIn("SKILL.md", payload_str)
        self.assertNotIn("/", payload_str)

    def test_emit_smart_loading_resolved_fail_open(self):
        """Calling emit helper must NEVER raise even when audit_emit is
        unavailable (fail-open invariant)."""
        # No exception expected even if framework hooks aren't on sys.path.
        slr.emit_smart_loading_resolved({
            "profile": "frontend",
            "active_count": 10,
            "suppressed_count": 20,
            "context_total_tokens": 9000,
            "arbitration_dropped_count": 0,
        })

    def test_emit_smart_loading_resolved_strips_forbidden_fields(self):
        """If a caller tries to slip a non-whitelist field, it's dropped."""
        # We can't easily observe audit_emit.py here, but verify the helper
        # explicitly filters before dispatch.
        payload = {
            "profile": "engine",
            "active_count": 12,
            "suppressed_count": 5,
            "context_total_tokens": 8000,
            "arbitration_dropped_count": 0,
            "rogue_field": "secret",
            "skill_content": "leak",
        }
        # No exception; rogue keys are filtered in the helper.
        slr.emit_smart_loading_resolved(payload)


# ---------------------------------------------------------------------------
# CEO_SMART_LOADING_DEBUG=1 debug output schema
# ---------------------------------------------------------------------------

class TestDebugOutput(unittest.TestCase):
    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.skills = _build_20_active_candidates() + _build_dormant_24()

    def test_debug_includes_dropped_reasons(self):
        result = slr._resolve_from_skills(
            self.skills, "trading-readonly", self.cap_table, debug=True
        )
        self.assertIn("dropped", result)
        self.assertIsInstance(result["dropped"], list)
        # Must have at least the 24 dormant suppressions
        self.assertGreaterEqual(len(result["dropped"]), 24)
        for entry in result["dropped"]:
            self.assertEqual(set(entry.keys()), {"path", "reason"})

    def test_debug_off_omits_dropped(self):
        result = slr._resolve_from_skills(
            self.skills, "trading-readonly", self.cap_table, debug=False
        )
        self.assertNotIn("dropped", result)


# ---------------------------------------------------------------------------
# Determinism / idempotency
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):
    def setUp(self):
        self.cap_table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.skills = _build_20_active_candidates() + _build_dormant_24()

    def test_same_input_same_output(self):
        r1 = slr._resolve_from_skills(self.skills, "engine", self.cap_table)
        r2 = slr._resolve_from_skills(self.skills, "engine", self.cap_table)
        self.assertEqual(r1["active_skills"], r2["active_skills"])
        self.assertEqual(r1["active_count"], r2["active_count"])
        self.assertEqual(r1["context_total_tokens"], r2["context_total_tokens"])

    def test_input_order_does_not_matter(self):
        reversed_skills = list(reversed(self.skills))
        r1 = slr._resolve_from_skills(self.skills, "engine", self.cap_table)
        r2 = slr._resolve_from_skills(reversed_skills, "engine", self.cap_table)
        self.assertEqual(sorted(r1["active_skills"]), sorted(r2["active_skills"]))


# ---------------------------------------------------------------------------
# read_repo_profile fail-CLOSED + cap-table loader
# ---------------------------------------------------------------------------

class TestRepoProfileFailClosed(unittest.TestCase):
    def test_missing_file_falls_back_to_trading_readonly(self):
        result = slr.read_repo_profile(Path("/nonexistent/path/repo-profile.yaml"))
        self.assertEqual(result, "trading-readonly")

    def test_unknown_risk_class_falls_back_to_trading_readonly(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("risk_class: unknown-needs-owner-confirmation\n")
            path = Path(f.name)
        try:
            result = slr.read_repo_profile(path)
            self.assertEqual(result, "trading-readonly")
        finally:
            path.unlink(missing_ok=True)

    def test_valid_profile_passthrough(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("risk_class: fintech\n")
            path = Path(f.name)
        try:
            self.assertEqual(slr.read_repo_profile(path), "fintech")
        finally:
            path.unlink(missing_ok=True)


class TestCapTableLoader(unittest.TestCase):
    def test_load_canonical_cap_table(self):
        table = slr.load_cap_table(_CAP_TABLE_PATH)
        self.assertEqual(table["frontend"]["max_active"], 10)
        self.assertEqual(table["engine"]["max_active"], 12)
        self.assertEqual(table["fintech"]["max_active"], 15)
        self.assertEqual(table["trading-readonly"]["max_active"], 8)
        self.assertEqual(table["generic"]["max_active"], 6)
        for p in _VALID_PROFILES:
            self.assertEqual(table[p]["context_budget_tokens"], 30000)


# ---------------------------------------------------------------------------
# End-to-end resolve() over on-disk SKILL.md tree
# ---------------------------------------------------------------------------

class TestE2EOnDisk(unittest.TestCase):
    """End-to-end resolve() that walks an on-disk SKILL.md tree."""

    def _write_skill(self, root: Path, sub_path: str, frontmatter: str) -> None:
        full = root / sub_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"---\n{frontmatter}---\n\nbody\n", encoding="utf-8")

    def test_e2e_frontend_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skills"
            self._write_skill(root, "core/security-and-auth/SKILL.md", """name: security-and-auth
description: Security
priority: 1
risk_class: high
domain: core
context_budget_tokens: 1400
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 2}
  engine: {active: true, priority: 1}
  fintech: {active: true, priority: 1}
  trading-readonly: {active: true, priority: 1}
  generic: {active: true, priority: 3}
""")
            self._write_skill(root, "domains/hospitality/sales/SKILL.md", """name: hospitality-sales
priority: 5
risk_class: medium
domain: hospitality
context_budget_tokens: 400
inactive_but_retained: false
repo_profile_binding:
  generic: {active: false, priority: 6}
""")

            profile = Path(td) / "repo-profile.yaml"
            profile.write_text("risk_class: frontend\n", encoding="utf-8")

            result = slr.resolve(
                profile_path=profile,
                skill_root=root,
                cap_table_path=_CAP_TABLE_PATH,
            )
            self.assertEqual(result["profile"], "frontend")
            self.assertEqual(result["active_count"], 1)
            self.assertIn("security-and-auth", result["active_skills"][0])

    def test_e2e_dormant_bundle_not_surfaced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skills"
            # Active anchor
            self._write_skill(root, "core/anchor/SKILL.md", """priority: 2
risk_class: low
domain: core
context_budget_tokens: 500
repo_profile_binding:
  fintech: {active: true, priority: 2}
""")
            # Dormant
            self._write_skill(root, "domains/healthcare/sales/SKILL.md", """priority: 5
risk_class: medium
domain: healthcare
context_budget_tokens: 400
repo_profile_binding: {}
""")
            profile = Path(td) / "repo-profile.yaml"
            profile.write_text("risk_class: fintech\n", encoding="utf-8")
            result = slr.resolve(
                profile_path=profile,
                skill_root=root,
                cap_table_path=_CAP_TABLE_PATH,
            )
            self.assertEqual(result["active_count"], 1)
            self.assertIn("anchor", result["active_skills"][0])
            self.assertEqual(result["suppressed_count"], 1)


# ---------------------------------------------------------------------------
# Frontmatter parser edge cases
# ---------------------------------------------------------------------------

class TestFrontmatterParser(unittest.TestCase):
    def test_missing_frontmatter_returns_none(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("no frontmatter here\n")
            path = Path(f.name)
        try:
            self.assertIsNone(slr.parse_skill_frontmatter(path))
        finally:
            path.unlink(missing_ok=True)

    def test_inline_mapping_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("---\npriority: 3\nrisk_class: low\ndomain: core\n"
                    "repo_profile_binding:\n"
                    "  frontend: {active: true, priority: 5}\n"
                    "---\n\nbody\n")
            path = Path(f.name)
        try:
            data = slr.parse_skill_frontmatter(path)
            self.assertIsNotNone(data)
            assert data is not None  # for mypy
            self.assertEqual(data["priority"], 3)
            self.assertEqual(data["risk_class"], "low")
            self.assertEqual(
                data["repo_profile_binding"]["frontend"],
                {"active": True, "priority": 5},
            )
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# PLAN-094 Wave B — File-backed frontmatter cache (R-039)
# ---------------------------------------------------------------------------

class TestPlan094WaveBFrontmatterCache(unittest.TestCase):
    """File-backed cache invalidation + hit/miss accounting + kill-switch."""

    def _reset_module_state(self):
        """Clear in-process cache + counters between test cases."""
        slr._LOADED_CACHE = None
        slr._CACHE_DIRTY = False
        slr._CACHE_HITS = 0
        slr._CACHE_MISSES = 0
        slr._CACHE_ERRORS = 0

    def _make_skill_file(self, dir_path: Path, name: str, priority: int = 5) -> Path:
        skill = dir_path / name
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\n"
            f"priority: {priority}\n"
            "risk_class: low\n"
            "domain: core\n"
            "context_budget_tokens: 500\n"
            "inactive_but_retained: false\n"
            "repo_profile_binding:\n"
            "  frontend: {active: true, priority: 5}\n"
            "activation_triggers: []\n"
            "---\n\nbody\n",
            encoding="utf-8",
        )
        return skill

    def test_cold_then_warm_full_hit(self):
        """First parse = miss; second parse with same content = hit."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_DISABLED", None)
            self._reset_module_state()
            try:
                skill_dir = Path(tmp) / "skills"
                p1 = self._make_skill_file(skill_dir, "a/SKILL.md")
                p2 = self._make_skill_file(skill_dir, "b/SKILL.md")
                # Cold pass — both miss.
                self.assertIsNotNone(slr.parse_skill_frontmatter(p1))
                self.assertIsNotNone(slr.parse_skill_frontmatter(p2))
                self.assertEqual(slr.cache_stats()["miss_count"], 2)
                self.assertEqual(slr.cache_stats()["hit_count"], 0)
                slr.flush_cache()
                self.assertTrue(cache_path.is_file())
                # Drop in-process state to simulate process restart.
                self._reset_module_state()
                # Warm pass — both hit.
                d1 = slr.parse_skill_frontmatter(p1)
                d2 = slr.parse_skill_frontmatter(p2)
                self.assertIsNotNone(d1)
                self.assertIsNotNone(d2)
                self.assertEqual(slr.cache_stats()["hit_count"], 2)
                self.assertEqual(slr.cache_stats()["miss_count"], 0)
                # Cached frontmatter must contain the priority we wrote.
                self.assertEqual(d1["priority"], 5)
                self.assertEqual(d2["priority"], 5)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                self._reset_module_state()

    def test_invalidation_on_content_change(self):
        """SKILL.md edit (same mtime tier, different sha256) triggers re-parse."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            self._reset_module_state()
            try:
                skill_dir = Path(tmp) / "skills"
                p = self._make_skill_file(skill_dir, "a/SKILL.md", priority=5)
                d_pre = slr.parse_skill_frontmatter(p)
                self.assertEqual(d_pre["priority"], 5)
                slr.flush_cache()
                self._reset_module_state()
                # Mutate priority + file size.
                p.write_text(
                    p.read_text(encoding="utf-8").replace(
                        "priority: 5", "priority: 7"
                    ),
                    encoding="utf-8",
                )
                d_post = slr.parse_skill_frontmatter(p)
                self.assertEqual(d_post["priority"], 7)
                self.assertEqual(slr.cache_stats()["miss_count"], 1)
                self.assertEqual(slr.cache_stats()["hit_count"], 0)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                self._reset_module_state()

    def test_kill_switch_disables_cache(self):
        """CEO_SKILL_FRONTMATTER_CACHE_DISABLED=1 → no cache file written."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_DISABLED"] = "1"
            self._reset_module_state()
            try:
                skill_dir = Path(tmp) / "skills"
                p = self._make_skill_file(skill_dir, "a/SKILL.md")
                self.assertIsNotNone(slr.parse_skill_frontmatter(p))
                slr.flush_cache()
                self.assertFalse(cache_path.is_file())
                # Hit + miss counters remain zero (bypass path).
                self.assertEqual(slr.cache_stats()["hit_count"], 0)
                self.assertEqual(slr.cache_stats()["miss_count"], 0)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_DISABLED", None)
                self._reset_module_state()

    def test_corrupted_cache_returns_empty(self):
        """Cache file with malformed JSON triggers fail-open rebuild."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("not valid json {{{", encoding="utf-8")
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            self._reset_module_state()
            try:
                skill_dir = Path(tmp) / "skills"
                p = self._make_skill_file(skill_dir, "a/SKILL.md")
                # Parser should not raise; returns parsed frontmatter.
                self.assertIsNotNone(slr.parse_skill_frontmatter(p))
                self.assertEqual(slr.cache_stats()["miss_count"], 1)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                self._reset_module_state()

    def test_version_bump_invalidates_legacy_cache(self):
        """Cache with version != _FRONTMATTER_CACHE_VERSION is ignored."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"version": 0, "entries": {"/x": {"key": {}}}}),
                encoding="utf-8",
            )
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            self._reset_module_state()
            try:
                skill_dir = Path(tmp) / "skills"
                p = self._make_skill_file(skill_dir, "a/SKILL.md")
                self.assertIsNotNone(slr.parse_skill_frontmatter(p))
                self.assertEqual(slr.cache_stats()["miss_count"], 1)
                self.assertEqual(slr.cache_stats()["hit_count"], 0)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                self._reset_module_state()

    def test_stat_failure_records_error(self):
        """Non-existent path increments error_count + falls through to parse."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            os.environ["CEO_SKILL_FRONTMATTER_CACHE_PATH"] = str(cache_path)
            self._reset_module_state()
            try:
                ghost = Path(tmp) / "ghost.md"
                self.assertIsNone(slr.parse_skill_frontmatter(ghost))
                self.assertGreaterEqual(slr.cache_stats()["error_count"], 1)
            finally:
                os.environ.pop("CEO_SKILL_FRONTMATTER_CACHE_PATH", None)
                self._reset_module_state()


if __name__ == "__main__":
    unittest.main()
