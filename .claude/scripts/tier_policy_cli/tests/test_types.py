"""PLAN-043 Phase 1 — tier_policy.types unit tests.

Guards:
- MODEL_ID allowlist (VALID_MODEL_IDS tuple)
- ROLE_TO_TASK_TYPES mapping completeness (every canonical-5 role
  has >=1 task-type; every ADR-063 task-type maps to >=1 role)
- CANONICAL_5_AGENTS stability
- build_adr052_baseline() returns ADR-052 §Role-to-model exactly
- Dataclass defaults behave correctly
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli._types import (  # noqa: E402
    Assignment,
    AssignmentEvidence,
    CANONICAL_5_AGENTS,
    CURRENT_POLICY_SCHEMA_VERSION,
    Recommendation,
    ROLE_TO_TASK_TYPES,
    SigchainEntry,
    TOURNAMENT_TASK_TYPES,
    TierPolicyRecord,
    VALID_MODEL_IDS,
    build_adr052_baseline,
)


class TestValidModelIds(unittest.TestCase):
    def test_three_canonical_tiers(self):
        # ADR-149 (PLAN-134 W0): claude-fable-5 added — 4 legal IDs.
        self.assertEqual(len(VALID_MODEL_IDS), 4)

    def test_includes_all_three_tiers(self):
        self.assertIn("claude-fable-5", VALID_MODEL_IDS)
        self.assertIn("claude-opus-4-8", VALID_MODEL_IDS)
        self.assertIn("claude-sonnet-4-6", VALID_MODEL_IDS)
        self.assertIn("claude-haiku-4-5-20251001", VALID_MODEL_IDS)


class TestRoleToTaskTypes(unittest.TestCase):
    def test_every_canonical_5_role_has_at_least_one_task_type(self):
        for role in CANONICAL_5_AGENTS:
            self.assertIn(role, ROLE_TO_TASK_TYPES)
            self.assertGreaterEqual(len(ROLE_TO_TASK_TYPES[role]), 1)

    def test_every_tournament_task_type_maps_to_at_least_one_role(self):
        all_mapped_types = set()
        for task_types in ROLE_TO_TASK_TYPES.values():
            all_mapped_types.update(task_types)
        for task_type in TOURNAMENT_TASK_TYPES:
            self.assertIn(
                task_type,
                all_mapped_types,
                "Task type {t} not mapped to any role".format(t=task_type),
            )

    def test_veto_roles_include_security_review(self):
        # Defense-in-depth: VETO roles (code-reviewer, security-engineer)
        # MUST include security-review in their task-type mapping.
        self.assertIn("security-review", ROLE_TO_TASK_TYPES["code-reviewer"])
        self.assertIn(
            "security-review", ROLE_TO_TASK_TYPES["security-engineer"]
        )


class TestCanonical5Agents(unittest.TestCase):
    def test_five_agents(self):
        self.assertEqual(len(CANONICAL_5_AGENTS), 5)

    def test_includes_all_five(self):
        for expected in (
            "code-reviewer",
            "security-engineer",
            "qa-architect",
            "performance-engineer",
            "devops",
        ):
            self.assertIn(expected, CANONICAL_5_AGENTS)


class TestAdr052Baseline(unittest.TestCase):
    def test_matches_adr_052_role_to_model(self):
        # ADR-149 (W0 variant A): VETO roles on the running generation.
        baseline = build_adr052_baseline()
        self.assertEqual(baseline["code-reviewer"].tier, "claude-fable-5")
        self.assertEqual(
            baseline["security-engineer"].tier, "claude-fable-5"
        )
        self.assertEqual(baseline["qa-architect"].tier, "claude-sonnet-4-6")
        self.assertEqual(
            baseline["performance-engineer"].tier, "claude-sonnet-4-6"
        )
        self.assertEqual(
            baseline["devops"].tier, "claude-haiku-4-5-20251001"
        )

    def test_veto_roles_locked_by_veto_floor(self):
        baseline = build_adr052_baseline()
        self.assertEqual(baseline["code-reviewer"].locked_by, "VETO_FLOOR")
        self.assertEqual(
            baseline["security-engineer"].locked_by, "VETO_FLOOR"
        )

    def test_non_veto_roles_unlocked(self):
        baseline = build_adr052_baseline()
        self.assertIsNone(baseline["qa-architect"].locked_by)
        self.assertIsNone(baseline["performance-engineer"].locked_by)
        self.assertIsNone(baseline["devops"].locked_by)

    def test_evidence_all_none_on_baseline(self):
        baseline = build_adr052_baseline()
        for slug, assignment in baseline.items():
            self.assertIsNone(
                assignment.evidence,
                "Baseline for {s} has evidence; expected None".format(s=slug),
            )


class TestSchemaVersion(unittest.TestCase):
    def test_current_version_is_1_0(self):
        self.assertEqual(CURRENT_POLICY_SCHEMA_VERSION, "1.0")


class TestDataclassDefaults(unittest.TestCase):
    def test_assignment_evidence_defaults(self):
        ev = AssignmentEvidence(n=30, gap_pp=20.5, last_updated=None)
        self.assertEqual(ev.runs_considered, 0)
        self.assertEqual(ev.tournament_report_hmacs, [])

    def test_tier_policy_record_defaults(self):
        r = TierPolicyRecord(
            schema_version="1.0",
            generated_at="2026-04-19T00:00:00Z",
            baseline_from="ADR-052",
            assignments={},
            hmac_anchor="a" * 64,
        )
        self.assertEqual(r.sigchain_tip_length, 1)
        self.assertEqual(r.last_change_by_role, {})


if __name__ == "__main__":
    unittest.main()
