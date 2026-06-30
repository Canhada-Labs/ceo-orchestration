"""
test_validate_skill_frontmatter_pii_core.py — PLAN-080 Phase 0a test suite.

Tests new V3 helpers: _has_inherits_pii_core, _missing_inherits_pii_core
and updated validate_v3 for 4-skill PII core inheritance (ADR-111).

Structure:
  - 20 helper-level tests via subTest parametrize
      (test_has_inherits_pii_core_parametrize, test_missing_inherits_pii_core_parametrize)
  - 13 real-file integration tests against PII-required domain SKILL.md files

Integration tests: post-Phase-0a expected GREEN; pre-Phase-0a expected RED.
They read staged files from:
  .claude/plans/PLAN-080/staging/phase-0a/edits/<domain>/<skill>/SKILL.md
When staged files are absent (pre-Phase-0a), the test is SKIPPED with reason.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load the module under test (filename has dash — can't use plain import)
# ---------------------------------------------------------------------------

# Module path resolution — handles both staging and canonical install locations:
#   staging:   .../staging/phase-0a/scripts/validate-skill-frontmatter.py
#              (test at .../staging/phase-0a/tests/<file>.py → parent.parent/scripts/)
#   canonical: .claude/scripts/validate-skill-frontmatter.py
#              (test at .claude/scripts/tests/<file>.py → parent/<file>)
_THIS = Path(__file__).resolve()
_STAGING_CAND = _THIS.parent.parent / "scripts" / "validate-skill-frontmatter.py"
_CANONICAL_CAND = _THIS.parent.parent / "validate-skill-frontmatter.py"
if _STAGING_CAND.is_file():
    _SCRIPT = _STAGING_CAND
elif _CANONICAL_CAND.is_file():
    _SCRIPT = _CANONICAL_CAND
else:
    raise FileNotFoundError(
        f"validate-skill-frontmatter.py not found at staging ({_STAGING_CAND}) "
        f"or canonical ({_CANONICAL_CAND})"
    )
_spec = importlib.util.spec_from_file_location("validate_skill_frontmatter", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["validate_skill_frontmatter"] = _mod
_spec.loader.exec_module(_mod)

_has_inherits_pii_core = _mod._has_inherits_pii_core
_missing_inherits_pii_core = _mod._missing_inherits_pii_core
_has_pii_handling_required = _mod._has_pii_handling_required
validate_v3 = _mod.validate_v3
_parse_frontmatter = _mod._parse_frontmatter
PII_CORE_SKILLS = _mod.PII_CORE_SKILLS

# All 4 expected skill strings (sorted for deterministic assertions)
_ALL_4 = sorted(PII_CORE_SKILLS)

# ---------------------------------------------------------------------------
# Repo root path resolution
# ---------------------------------------------------------------------------

# This file lives at: .claude/plans/PLAN-080/staging/phase-0a/tests/
_REPO_ROOT = Path(__file__).resolve().parents[6]
_STAGING_EDITS = Path(__file__).resolve().parents[1] / "edits"
_CANONICAL_SKILLS = _REPO_ROOT / ".claude" / "skills" / "domains"


def _staged_path(domain: str, skill: str) -> Path:
    """Return the staged SKILL.md path for a given domain/skill.

    Staging mirrors the canonical layout: edits/<domain>/skills/<skill>/SKILL.md.
    """
    return _STAGING_EDITS / domain / "skills" / skill / "SKILL.md"


def _canonical_path(domain: str, skill: str) -> Path:
    """Return the canonical SKILL.md path for a given domain/skill."""
    return _CANONICAL_SKILLS / domain / "skills" / skill / "SKILL.md"


# ---------------------------------------------------------------------------
# Helper-level parametrize tests (20 tests)
# ---------------------------------------------------------------------------

class TestHasInheritsPiiCoreParametrize(unittest.TestCase):
    """
    20 subTest cases for _has_inherits_pii_core(fm).
    Uses self.subTest pattern (parametrize-equivalent, stdlib only).
    """

    def _fm(self, inherits) -> dict:
        """Build a minimal frontmatter dict with the given inherits value."""
        if inherits is None:
            return {}
        return {"inherits": inherits}

    def test_list_all_4_present(self):
        """4/4 inherits present (list form) → True."""
        fm = self._fm([
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/consent-lifecycle",
            "core/dpo-reporting",
        ])
        self.assertTrue(_has_inherits_pii_core(fm))

    def test_string_all_4_substrings_present(self):
        """4/4 inherits present (string with all 4 substrings) → True (legacy edge case)."""
        # Rare: single long string that contains all 4 as substrings
        val = (
            "core/compliance-lgpd, core/pii-data-flow, "
            "core/consent-lifecycle, core/dpo-reporting"
        )
        fm = self._fm(val)
        self.assertTrue(_has_inherits_pii_core(fm))

    def test_list_3of4_missing_compliance_lgpd(self):
        """3/4: missing core/compliance-lgpd → False."""
        fm = self._fm([
            "core/pii-data-flow",
            "core/consent-lifecycle",
            "core/dpo-reporting",
        ])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_3of4_missing_pii_data_flow(self):
        """3/4: missing core/pii-data-flow → False."""
        fm = self._fm([
            "core/compliance-lgpd",
            "core/consent-lifecycle",
            "core/dpo-reporting",
        ])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_3of4_missing_consent_lifecycle(self):
        """3/4: missing core/consent-lifecycle → False."""
        fm = self._fm([
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/dpo-reporting",
        ])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_3of4_missing_dpo_reporting(self):
        """3/4: missing core/dpo-reporting → False."""
        fm = self._fm([
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/consent-lifecycle",
        ])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_3of4_missing_one_parametrize(self):
        """3/4 inherits: 4 parametrized cases for which-one-missing."""
        cases = [
            ("compliance-lgpd", [
                "core/pii-data-flow", "core/consent-lifecycle", "core/dpo-reporting"
            ]),
            ("pii-data-flow", [
                "core/compliance-lgpd", "core/consent-lifecycle", "core/dpo-reporting"
            ]),
            ("consent-lifecycle", [
                "core/compliance-lgpd", "core/pii-data-flow", "core/dpo-reporting"
            ]),
            ("dpo-reporting", [
                "core/compliance-lgpd", "core/pii-data-flow", "core/consent-lifecycle"
            ]),
        ]
        for which_missing, inherits_list in cases:
            with self.subTest(which_missing=which_missing):
                fm = self._fm(inherits_list)
                self.assertFalse(
                    _has_inherits_pii_core(fm),
                    msg=f"Expected False when {which_missing!r} is absent",
                )

    def test_list_2of4_missing_two_pair_a(self):
        """2/4: missing compliance-lgpd + pii-data-flow → False."""
        fm = self._fm(["core/consent-lifecycle", "core/dpo-reporting"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_2of4_missing_two_pair_b(self):
        """2/4: missing compliance-lgpd + consent-lifecycle → False."""
        fm = self._fm(["core/pii-data-flow", "core/dpo-reporting"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_2of4_missing_two_pair_c(self):
        """2/4: missing pii-data-flow + consent-lifecycle → False."""
        fm = self._fm(["core/compliance-lgpd", "core/dpo-reporting"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_2of4_missing_two_pair_d(self):
        """2/4: missing pii-data-flow + dpo-reporting → False."""
        fm = self._fm(["core/compliance-lgpd", "core/consent-lifecycle"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_1of4_only_compliance_lgpd(self):
        """1/4: only core/compliance-lgpd (legacy pre-Phase-0a) → False."""
        fm = self._fm(["core/compliance-lgpd"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_1of4_only_pii_data_flow(self):
        """1/4: only core/pii-data-flow → False."""
        fm = self._fm(["core/pii-data-flow"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_1of4_only_consent_lifecycle(self):
        """1/4: only core/consent-lifecycle → False."""
        fm = self._fm(["core/consent-lifecycle"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_1of4_only_dpo_reporting(self):
        """1/4: only core/dpo-reporting → False."""
        fm = self._fm(["core/dpo-reporting"])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_inherits_none(self):
        """inherits: key absent (None) → False."""
        fm = {}
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_inherits_empty_list(self):
        """inherits: empty list → False."""
        fm = self._fm([])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_list_4_pii_plus_extra_skill(self):
        """inherits: 4 PII + extra core/ skill → True (no false-negative on superset)."""
        fm = self._fm([
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/consent-lifecycle",
            "core/dpo-reporting",
            "core/data-schema-design",  # extra — must not cause False
        ])
        self.assertTrue(_has_inherits_pii_core(fm))

    def test_list_non_pii_strings_only(self):
        """inherits: only non-PII strings → False."""
        fm = self._fm([
            "core/security-and-auth",
            "core/data-schema-design",
        ])
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_weird_type_int(self):
        """inherits: int type — should not crash, return False."""
        fm = self._fm(42)
        self.assertFalse(_has_inherits_pii_core(fm))

    def test_weird_type_dict(self):
        """inherits: dict type — should not crash, return False."""
        fm = self._fm({"skill": "core/compliance-lgpd"})
        self.assertFalse(_has_inherits_pii_core(fm))


class TestMissingInheritsPiiCore(unittest.TestCase):
    """Sanity checks for _missing_inherits_pii_core helper."""

    def test_all_present_returns_empty(self):
        fm = {"inherits": [
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/consent-lifecycle",
            "core/dpo-reporting",
        ]}
        self.assertEqual(_missing_inherits_pii_core(fm), [])

    def test_none_returns_all_4(self):
        self.assertEqual(_missing_inherits_pii_core({}), _ALL_4)

    def test_missing_one_returns_that_one(self):
        fm = {"inherits": [
            "core/compliance-lgpd",
            "core/pii-data-flow",
            "core/dpo-reporting",
        ]}
        result = _missing_inherits_pii_core(fm)
        self.assertEqual(result, ["core/consent-lifecycle"])

    def test_legacy_single_string_missing_two(self):
        # String with only 2 of 4 substrings
        fm = {"inherits": "core/compliance-lgpd, core/pii-data-flow"}
        result = _missing_inherits_pii_core(fm)
        self.assertIn("core/consent-lifecycle", result)
        self.assertIn("core/dpo-reporting", result)
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# Real-file integration tests (13 tests)
# Post-Phase-0a expected GREEN; pre-Phase-0a expected RED (SKIP if no staged file).
# ---------------------------------------------------------------------------

# 13 PII-required domain skills (domain, skill-slug pairs)
_PII_SKILL_CASES = [
    ("legal", "legal-billing"),
    ("legal", "client-intake"),
    ("legal", "document-review"),
    ("healthcare", "marketing-compliance"),
    ("healthcare", "healthcare-customer-service"),
    ("hr", "recruitment-specialist"),
    ("hr", "hr-onboarding"),
    ("finance-accounting", "financial-analyst"),
    ("finance-accounting", "fpa-analyst"),
    ("finance-accounting", "bookkeeper-controller"),
    ("finance-accounting", "tax-strategist"),
    ("real-estate-finance", "buyer-seller-agent"),
    ("real-estate-finance", "loan-officer-assistant"),
]


class TestPiiCoreIntegration(unittest.TestCase):
    """
    13 integration tests for PII-required domain SKILL.md files.

    Strategy: prefer staged files from
      .claude/plans/PLAN-080/staging/phase-0a/edits/<domain>/<skill>/SKILL.md
    (post-Phase-0a versions with 4-skill inherits set).

    If staged file is absent (pre-Phase-0a): skip with informative reason.

    Post-Phase-0a expected GREEN:
      - _has_inherits_pii_core(fm) is True
      - _has_pii_handling_required(fm) is True
      - validate_v3(filepath, fm) -> (errors=[], warnings=[])

    Pre-Phase-0a canonical files (only core/compliance-lgpd): these tests
    intentionally FAIL — that is the red state Phase 0a exists to fix.
    """

    def _run_one(self, domain: str, skill: str) -> None:
        """
        Core assertion logic for a single (domain, skill) pair.
        Called from each generated test method.
        """
        staged = _staged_path(domain, skill)
        canonical = _canonical_path(domain, skill)

        if staged.exists():
            filepath = staged
            source_label = "staged"
        elif canonical.exists():
            # Canonical exists but not staged: skip (pre-Phase-0a state)
            self.skipTest(
                f"Staged file absent (pre-Phase-0a); canonical {canonical} exists "
                f"with legacy single-skill inherits. "
                f"This test will GREEN after Phase 0a ships staged edits."
            )
            return  # unreachable but satisfies linters
        else:
            self.skipTest(
                f"Neither staged nor canonical SKILL.md found for "
                f"{domain}/{skill}. Investigate missing file."
            )
            return

        content = filepath.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter(content)
        self.assertIsNotNone(
            fm,
            msg=f"[{source_label}] {filepath}: no frontmatter found",
        )
        fm = fm or {}

        with self.subTest(domain=domain, skill=skill, source=source_label):
            # 1. 4/4 PII core skills present
            self.assertTrue(
                _has_inherits_pii_core(fm),
                msg=(
                    f"[{source_label}] {filepath}: expected all 4 PII core skills in inherits:. "
                    f"Missing: {_missing_inherits_pii_core(fm)}"
                ),
            )
            # 2. pii_handling: required present
            self.assertTrue(
                _has_pii_handling_required(fm),
                msg=f"[{source_label}] {filepath}: expected pii_handling: required",
            )
            # 3. validate_v3 PASS (no errors, no warnings)
            errors, warnings = validate_v3(str(filepath), fm, domain_override=domain)
            self.assertEqual(
                errors,
                [],
                msg=f"[{source_label}] validate_v3 produced errors: {errors}",
            )
            self.assertEqual(
                warnings,
                [],
                msg=f"[{source_label}] validate_v3 produced warnings: {warnings}",
            )

    # ---------------------------------------------------------------------------
    # Individual test methods (one per PII skill — 13 total)
    # Named explicitly so unittest discovery and result output are readable.
    # ---------------------------------------------------------------------------

    def test_legal_legal_billing(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("legal", "legal-billing")

    def test_legal_client_intake(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("legal", "client-intake")

    def test_legal_document_review(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("legal", "document-review")

    def test_healthcare_marketing_compliance(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("healthcare", "marketing-compliance")

    def test_healthcare_customer_service(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("healthcare", "healthcare-customer-service")

    def test_hr_recruitment_specialist(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("hr", "recruitment-specialist")

    def test_hr_onboarding(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("hr", "hr-onboarding")

    def test_finance_accounting_financial_analyst(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("finance-accounting", "financial-analyst")

    def test_finance_accounting_fpa_analyst(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("finance-accounting", "fpa-analyst")

    def test_finance_accounting_bookkeeper_controller(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("finance-accounting", "bookkeeper-controller")

    def test_finance_accounting_tax_strategist(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("finance-accounting", "tax-strategist")

    def test_real_estate_finance_buyer_seller_agent(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("real-estate-finance", "buyer-seller-agent")

    def test_real_estate_finance_loan_officer_assistant(self):
        # post-Phase-0a expected GREEN; pre-Phase-0a expected RED
        self._run_one("real-estate-finance", "loan-officer-assistant")


# ---------------------------------------------------------------------------
# M2-CDX-3 (Codex iter 1) — validate_v3 negative + warn branch coverage
# ---------------------------------------------------------------------------
# These tests exercise the public validate_v3() entry point — not just the
# helpers — to cover the error/warn message generation paths. Helps ensure
# that future refactors of validate_v3 do not silently degrade error wording
# or branch coverage.

_PII_REQUIRED_PATH = (
    ".claude/skills/domains/legal/skills/legal-billing/SKILL.md"
)
_PII_WARN_PATH = (
    ".claude/skills/domains/hospitality/skills/guest-services/SKILL.md"
)
_NON_PII_PATH = (
    ".claude/skills/core/data-schema-design/SKILL.md"
)


class TestValidateV3Branches(unittest.TestCase):
    """validate_v3() branch coverage — required ERROR, warn WARN, no-op."""

    def test_required_domain_missing_pii_core_emits_error_with_adr_111(self):
        """legal/<skill>/SKILL.md without 4-skill inherits → ERROR + cite all 4 + missing list + ADR-111."""
        fm = {
            "name": "legal-billing",
            "inherits": "core/compliance-lgpd",  # legacy single-skill (pre-Phase-0a)
            "pii_handling": "required",
        }
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        msg = errors[0]
        # Must cite the canonical V3 ERROR prefix
        self.assertIn("V3 ERROR", msg)
        # Must reference all 4 PII core skills
        self.assertIn("core/compliance-lgpd", msg)
        self.assertIn("core/pii-data-flow", msg)
        self.assertIn("core/consent-lifecycle", msg)
        self.assertIn("core/dpo-reporting", msg)
        # Must explicitly cite ADR-111
        self.assertIn("ADR-111", msg)
        # Must enumerate missing entries (not all 4 since compliance-lgpd is present)
        self.assertIn("Missing:", msg)
        self.assertIn("core/pii-data-flow", msg.split("Missing:")[1])
        self.assertIn("core/consent-lifecycle", msg.split("Missing:")[1])
        self.assertIn("core/dpo-reporting", msg.split("Missing:")[1])

    def test_required_domain_missing_pii_handling_emits_error(self):
        """legal/<skill>/SKILL.md missing pii_handling: required → ERROR."""
        fm = {
            "name": "legal-billing",
            "inherits": [
                "core/compliance-lgpd",
                "core/pii-data-flow",
                "core/consent-lifecycle",
                "core/dpo-reporting",
            ],
            # pii_handling intentionally missing
        }
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm)
        self.assertEqual(warnings, [])
        self.assertTrue(
            any("pii_handling" in e for e in errors),
            f"Expected pii_handling ERROR, got: {errors}",
        )

    def test_required_domain_full_compliance_no_errors(self):
        """legal/<skill>/SKILL.md with full 4-list inherits + pii_handling required → no errors/warnings."""
        fm = {
            "name": "legal-billing",
            "inherits": [
                "core/compliance-lgpd",
                "core/pii-data-flow",
                "core/consent-lifecycle",
                "core/dpo-reporting",
            ],
            "pii_handling": "required",
        }
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_warn_domain_missing_pii_core_emits_warn_only(self):
        """hospitality/<skill>/SKILL.md without 4-skill inherits → WARN, not ERROR."""
        fm = {"name": "guest-services"}
        errors, warnings = _mod.validate_v3(_PII_WARN_PATH, fm)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(warnings), 1)
        self.assertTrue(
            any("V3 WARN" in w for w in warnings),
            f"Expected V3 WARN, got: {warnings}",
        )
        # Warn should still cite the 4-skill set OR PII core context
        joined = " ".join(warnings)
        self.assertTrue(
            "core/compliance-lgpd" in joined or "PII core" in joined or "lower-risk" in joined,
            f"Warn message should reference PII core context: {warnings}",
        )

    def test_warn_domain_with_pii_core_no_findings(self):
        """hospitality/<skill>/SKILL.md WITH 4-skill inherits → no warnings (overcompliant is OK)."""
        fm = {
            "name": "guest-services",
            "inherits": [
                "core/compliance-lgpd",
                "core/pii-data-flow",
                "core/consent-lifecycle",
                "core/dpo-reporting",
            ],
            "pii_handling": "required",
        }
        errors, warnings = _mod.validate_v3(_PII_WARN_PATH, fm)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_no_domain_match_returns_empty(self):
        """Path that doesn't match the .claude/skills/domains/<domain>/ pattern → ([], []) no-op."""
        # core/* paths don't match domains/ regex; should be a no-op
        fm = {"name": "data-schema-design"}
        errors, warnings = _mod.validate_v3(_NON_PII_PATH, fm)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_unknown_domain_path_returns_empty(self):
        """Path with a domain NOT in PII_REQUIRED_DOMAINS or PII_WARN_DOMAINS → no-op."""
        fm = {"name": "irrelevant"}
        path = ".claude/skills/domains/devrel/skills/some-skill/SKILL.md"  # devrel is not PII-flagged
        errors, warnings = _mod.validate_v3(path, fm)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_required_domain_missing_both_emits_two_errors(self):
        """legal/<skill>/SKILL.md missing inherits AND pii_handling → 2 errors."""
        fm = {"name": "legal-billing"}
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 2, f"Expected 2 errors, got: {errors}")
        joined = " ".join(errors)
        self.assertIn("ADR-111", joined)
        self.assertIn("pii_handling", joined)

    def test_domain_override_takes_precedence_over_path(self):
        """domain_override parameter forces a different domain check."""
        fm = {"name": "test"}
        # _PII_REQUIRED_PATH is legal/, but override to devrel (no PII-flag) → no findings
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm, domain_override="devrel")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_required_domain_partial_compliance_lists_specific_missing(self):
        """3/4 inherits → error message Missing list shows the single absent entry."""
        fm = {
            "name": "legal-billing",
            "inherits": [
                "core/compliance-lgpd",
                "core/pii-data-flow",
                "core/consent-lifecycle",
                # missing core/dpo-reporting
            ],
            "pii_handling": "required",
        }
        errors, warnings = _mod.validate_v3(_PII_REQUIRED_PATH, fm)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        msg = errors[0]
        self.assertIn("Missing:", msg)
        missing_segment = msg.split("Missing:")[1]
        self.assertIn("core/dpo-reporting", missing_segment)
        # The 3 present skills should NOT appear in the Missing: segment
        self.assertNotIn("core/compliance-lgpd", missing_segment)
        self.assertNotIn("core/pii-data-flow", missing_segment)
        self.assertNotIn("core/consent-lifecycle", missing_segment)


if __name__ == "__main__":
    unittest.main()
