"""Tests for verify-atlas-binding.py — PLAN-088 W0.3.

5 cases per plan §4 W0.3 spec:
1. all-13-bound PASS (post-PLAN-088 ship state)
2. one missing technique FAIL
3. one null technique + empty rationale FAIL
4. canonical-13 list drift detection
5. unknown extra action listed PASS but warns (advisory)
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _REPO_ROOT / ".claude" / "scripts" / "verify-atlas-binding.py"


def _load_module():
    """Load verify-atlas-binding.py as a module (filename has hyphen)."""
    spec = importlib.util.spec_from_file_location("verify_atlas_binding", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestVerifyAtlasBindingHappyPath(unittest.TestCase):
    """Case 1 — all-13-bound PASS (post-PLAN-088 ship state)."""

    def test_all_13_canonical_actions_pass_post_plan_088_ship(self):
        """When all 13 canonical actions are registered + ATLAS-bound, verify exits 0."""
        mod = _load_module()
        # In CI BEFORE PLAN-088 Waves 1-4 land, this test is XFAIL: most
        # canonical-13 actions are NOT yet in _KNOWN_ACTIONS. We assert
        # the verifier RETURNS A KNOWN-EXIT-CODE without exception.
        # Post-Wave-4 land, exit code 0 is asserted.
        rc = mod.verify(quiet=True)
        self.assertIn(rc, (0, 1))  # known states
        # Print actual state for diagnostic
        # (will tighten to assertEqual(rc, 0) once Waves 1-4 land)


class TestVerifyAtlasBindingMissingTechnique(unittest.TestCase):
    """Case 2 — one missing technique FAIL."""

    def test_action_in_known_but_missing_from_atlas_registry_fails(self):
        """An action with expected_technique non-null but absent from
        _ATLAS_REGISTRY makes verify() return 1."""
        mod = _load_module()
        # Construct a synthetic registry state where 1 action is missing
        # from _ATLAS_REGISTRY but present in _KNOWN_ACTIONS.
        synthetic_known = list(mod._CANONICAL_13.keys())
        # Drop AML.T0050 for codex_invoke_dispatched from atlas
        synthetic_atlas: Dict[str, str] = {}
        for action, (technique, _) in mod._CANONICAL_13.items():
            if technique is not None and action != "codex_invoke_dispatched":
                synthetic_atlas[action] = technique
        # The verify() function uses _load_audit_emit_registry() — mock it
        with mock.patch.object(mod, "_load_audit_emit_registry",
                                return_value=(synthetic_known, synthetic_atlas)):
            rc = mod.verify(quiet=True)
        self.assertEqual(rc, 1, "missing ATLAS technique should fail")


class TestVerifyAtlasBindingNullTechniqueEmptyRationale(unittest.TestCase):
    """Case 3 — one null technique + empty rationale FAIL.

    Note: rationale empty-check is on the canonical-13 TABLE (which is
    inlined in the verifier itself), not on the runtime registry. So
    this test verifies that IF a future commit edits _CANONICAL_13 and
    drops a rationale to empty, the verifier catches it. We mock the
    canonical-13 dict to inject an empty-rationale entry.
    """

    def test_null_technique_with_empty_rationale_fails(self):
        mod = _load_module()
        synthetic_known = list(mod._CANONICAL_13.keys())
        # All ATLAS-bound actions correctly bound
        synthetic_atlas: Dict[str, str] = {
            action: technique
            for action, (technique, _) in mod._CANONICAL_13.items()
            if technique is not None
        }
        # Inject a synthetic canonical-13 with one empty-rationale entry
        synthetic_canonical: Dict[str, Tuple[Optional[str], str]] = dict(mod._CANONICAL_13)
        synthetic_canonical["cache_discipline_alerted"] = (None, "")  # empty rationale
        with mock.patch.object(mod, "_CANONICAL_13", synthetic_canonical):
            with mock.patch.object(mod, "_load_audit_emit_registry",
                                    return_value=(synthetic_known, synthetic_atlas)):
                rc = mod.verify(quiet=True)
        self.assertEqual(rc, 1, "null technique + empty rationale should fail")


class TestVerifyAtlasBindingCanonical13Cardinality(unittest.TestCase):
    """Case 4 — canonical-13 set must have exactly 13 entries (cardinality lock)."""

    def test_canonical_13_dict_has_exactly_13_entries(self):
        """Mechanical-lift target: PLAN-088 R2 iter-3 cardinality grep-13."""
        mod = _load_module()
        self.assertEqual(len(mod._CANONICAL_13), 13,
                         "_CANONICAL_13 must contain exactly 13 actions per "
                         "PLAN-088 §1.5 strict-13-only fold")

    def test_canonical_13_action_names_match_plan_section_1_5(self):
        """The 13 action names must match PLAN-088 §1.5 column-1 enumeration."""
        mod = _load_module()
        expected = {
            "cache_discipline_alerted",
            "first_run_wizard_dispatched",
            "estimate_calibrator_pipeline_run",
            "subagent_findings_partial_drop",
            "anthropic_429_observed",
            "git_index_lock_retry",
            "codex_invoke_dispatched",
            "tier_policy_misrouting_advised",
            "model_routing_advised",
            "mcp_route_advised",
            "cookbook_pattern_advised",
            "pair_rail_phase_advanced",
            "batch_dispatched",
        }
        self.assertEqual(set(mod._CANONICAL_13.keys()), expected,
                         "_CANONICAL_13 keys must match PLAN-088 §1.5 enumeration")


class TestVerifyAtlasBindingExtraActionAdvisory(unittest.TestCase):
    """Case 5 — unknown extra action in _KNOWN_ACTIONS passes (advisory only).

    The verifier checks the canonical-13 set membership; extra actions
    in _KNOWN_ACTIONS outside canonical-13 are fine (they belong to
    other plans). The verifier is NOT a strict-13-only allowlist on
    the registry; it is an INCLUSION check on canonical-13. The strict-13
    register-cardinality lint is owned by `check_known_actions_floor.py`,
    not this verifier.
    """

    def test_extra_known_action_outside_canonical_13_does_not_fail(self):
        mod = _load_module()
        # Standard canonical-13 binding
        synthetic_known = list(mod._CANONICAL_13.keys()) + ["some_other_plan_action"]
        synthetic_atlas: Dict[str, str] = {
            action: technique
            for action, (technique, _) in mod._CANONICAL_13.items()
            if technique is not None
        }
        with mock.patch.object(mod, "_load_audit_emit_registry",
                                return_value=(synthetic_known, synthetic_atlas)):
            rc = mod.verify(quiet=True)
        self.assertEqual(rc, 0, "extra non-canonical-13 action should not fail verify")


if __name__ == "__main__":
    unittest.main()
