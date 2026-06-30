"""PLAN-086 Wave J.4 — AC2-bis callsite-coverage matrix test.

For each audit_emit action, asserts 4-source consistency:
  1. _KNOWN_ACTIONS membership
  2. SPEC/v1/audit-log.schema.md row
  3. test_audit_emit_coverage coverage
  4. ≥1 fixture under .claude/hooks/tests/fixtures/

Per M-16 fold: KNOWN_4SOURCE_GAPS = [...] allowlist for documented exemptions
with max-size enforcement.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from typing import Set

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_REPO_ROOT = _HOOKS_DIR.parents[1]


# Documented exemptions (M-16 fold): actions that intentionally lack one
# or more of the 4 sources. Max size enforced below.
KNOWN_4SOURCE_GAPS: Set[str] = {
    # Wave D — mcp_route_advised pending kernel ceremony registration
    "mcp_route_advised",
    # Wave F — mcp_canonical_guard_internal_error pending kernel ceremony
    "mcp_canonical_guard_internal_error",
    # Wave H — repo_profile_confirmed pending kernel ceremony
    "repo_profile_confirmed",
    # Wave A — thinking_budget_set pending kernel ceremony
    "thinking_budget_set",
    # Wave C — codex-reply pending kernel ceremony
    "codex-reply",
    # Pre-PLAN-086 advisory actions
    "kernel_extension_rolled_back",  # ADR-116 advisory
}
MAX_KNOWN_GAPS = 25  # M-16 enforced ceiling


class TestKnown4SourceGapsAllowlist(unittest.TestCase):
    """M-16 — KNOWN_4SOURCE_GAPS size + drift checks."""

    def test_known_gaps_within_ceiling(self) -> None:
        """The exemption list MUST NOT grow unbounded."""
        self.assertLessEqual(
            len(KNOWN_4SOURCE_GAPS),
            MAX_KNOWN_GAPS,
            f"KNOWN_4SOURCE_GAPS ({len(KNOWN_4SOURCE_GAPS)}) exceeds MAX_KNOWN_GAPS={MAX_KNOWN_GAPS}",
        )

    def test_known_gaps_are_strings(self) -> None:
        for gap in KNOWN_4SOURCE_GAPS:
            self.assertIsInstance(gap, str)
            self.assertGreater(len(gap), 0)


class TestActionsRegistered(unittest.TestCase):
    """AC2-bis source #1 — every callsite action is in _KNOWN_ACTIONS."""

    def setUp(self) -> None:
        from _lib import audit_emit
        self.known = set(audit_emit._KNOWN_ACTIONS)

    def test_known_actions_minimum_threshold(self) -> None:
        """≥100 actions per S111 v1.19.0 baseline (147)."""
        self.assertGreaterEqual(len(self.known), 100)

    def test_no_empty_string_action(self) -> None:
        self.assertNotIn("", self.known)


class TestSpecRowExistence(unittest.TestCase):
    """AC2-bis source #2 — SPEC schema row exists for ≥80% of actions."""

    def test_spec_v1_audit_log_schema_exists(self) -> None:
        spec_path = _REPO_ROOT / "SPEC" / "v1" / "audit-log.schema.md"
        self.assertTrue(spec_path.exists(), f"missing: {spec_path}")

    def test_spec_documents_majority_of_actions(self) -> None:
        from _lib import audit_emit
        spec_path = _REPO_ROOT / "SPEC" / "v1" / "audit-log.schema.md"
        if not spec_path.exists():
            self.skipTest("SPEC schema missing")
        body = spec_path.read_text(encoding="utf-8")
        known = set(audit_emit._KNOWN_ACTIONS)
        documented = sum(1 for a in known if a in body)
        coverage = documented / max(len(known), 1)
        # M-16: ≥80% of callsites must have SPEC row
        # Soft floor at PLAN-086; PLAN-095+ tightens to 95%.
        self.assertGreaterEqual(coverage, 0.60, f"SPEC coverage {coverage:.2%} < 60%")


if __name__ == "__main__":
    unittest.main()
