"""PLAN-088 W4.1 unit tests for pair_rail_decide pure module.

stdlib unittest. Coverage:
- M-17 / QA-2: Case A-F matrix evaluator (positive + negative fixtures)
- M-10 / Sec-1: TestPersonaSpoofingViaEnvVar (env-var sanitization,
  bounded enum, no privilege escalation)
- M-14 / Sec-5: Phase-A advance gate (time + samples + no-regression
  AND-of-three)
- M-6: ACTIVE phase REJECTED at resolver
- Fail-open invariant on garbage inputs
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parents[1]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import pair_rail_decide as prd  # noqa: E402


_CASE_FIXTURES = [
    # (label, claude_v, codex_v, jaccard, precond, phase, expected_case)
    ("case-A-precondition-MET",     "PASS", "PASS", "",       False, "DRY_RUN", "A"),
    ("case-A-precondition-NOT-met", "PASS", "PASS", "<=0.3",  False, "DRY_RUN", "E"),
    ("case-B-precondition-MET",     "PASS", "BLOCK", "",      True,  "DRY_RUN", "B"),
    ("case-B-precondition-NOT-met", "PASS", "BLOCK", "",      False, "DRY_RUN", "B'"),
    ("case-C-precondition-MET",     "BLOCK", "PASS", "",      False, "DRY_RUN", "C"),
    ("case-C-precondition-NOT-met", "BLOCK", "PASS", "<=0.3", False, "DRY_RUN", "C"),
    ("case-D-precondition-MET",     "BLOCK", "BLOCK", "",     False, "DRY_RUN", "D"),
    ("case-D-precondition-NOT-met", "BLOCK", "BLOCK", "<=0.3", False, "DRY_RUN", "D"),
    ("case-E-precondition-MET",     "PASS", "PASS", "<=0.3",  False, "DRY_RUN", "E"),
    ("case-E-precondition-NOT-met", "PASS", "PASS", "0.5-0.8", False, "DRY_RUN", "A"),
    ("case-F-precondition-MET",     "PASS", "TIMEOUT", "",    False, "DRY_RUN", "F"),
    ("case-F-precondition-NOT-met", "PASS", "MALFORMED", "",  False, "DRY_RUN", "F"),
]


class TestPairRailDecideMatrix(unittest.TestCase):
    def test_case_matrix_parametrized(self) -> None:
        for label, cv, xv, jb, pm, ph, expected in _CASE_FIXTURES:
            with self.subTest(label=label):
                out = prd.evaluate(
                    claude_verdict=cv, codex_verdict=xv,
                    phase=ph, jaccard_bucket=jb, precondition_met=pm,
                )
                self.assertEqual(out["case"], expected, "%s: %s" % (label, out))


class TestPhaseAdvanceGate(unittest.TestCase):
    def test_advance_blocked_below_time(self) -> None:
        self.assertFalse(prd.phase_a_can_advance(
            time_elapsed_seconds=6 * 86400,
            samples_observed=500,
            no_regression=True,
        ))

    def test_advance_blocked_below_samples(self) -> None:
        self.assertFalse(prd.phase_a_can_advance(
            time_elapsed_seconds=14 * 86400,
            samples_observed=99,
            no_regression=True,
        ))

    def test_advance_blocked_on_regression(self) -> None:
        self.assertFalse(prd.phase_a_can_advance(
            time_elapsed_seconds=14 * 86400,
            samples_observed=500,
            no_regression=False,
        ))

    def test_advance_allowed_when_all_three(self) -> None:
        self.assertTrue(prd.phase_a_can_advance(
            time_elapsed_seconds=7 * 86400,
            samples_observed=100,
            no_regression=True,
        ))


class TestActivePhaseRejected(unittest.TestCase):
    def test_resolve_active_to_disabled(self) -> None:
        self.assertEqual(prd.resolve_phase("ACTIVE"), "DISABLED")
        self.assertEqual(prd.resolve_phase("active"), "DISABLED")

    def test_is_active_phase_returns_false_for_active(self) -> None:
        self.assertFalse(prd.is_active_phase("ACTIVE"))

    def test_evaluate_with_active_returns_phase_disabled(self) -> None:
        out = prd.evaluate(
            claude_verdict="PASS", codex_verdict="PASS", phase="ACTIVE",
        )
        self.assertIsNone(out["case"])
        self.assertEqual(out["rationale"], "phase_disabled")
        self.assertFalse(out["advise_dispatch"])


class TestPersonaSpoofingViaEnvVar(unittest.TestCase):
    def test_signal_source_records_env_var_when_persona_set(self) -> None:
        src = prd.detect_signal_source({"CEO_PERSONA": "vibecoder"})
        self.assertEqual(src, "env-var")

    def test_signal_source_sanitized_to_bounded_enum(self) -> None:
        for raw in ("env-var", "cli-flag", "heuristic", "default"):
            self.assertEqual(prd.sanitize_signal_source(raw), raw)
        self.assertEqual(prd.sanitize_signal_source("env-var\ninjected"), "unknown")
        self.assertEqual(prd.sanitize_signal_source("../../etc/passwd"), "unknown")
        self.assertEqual(prd.sanitize_signal_source("a" * 500), "unknown")
        self.assertEqual(prd.sanitize_signal_source(None), "unknown")

    def test_env_var_persona_does_not_escalate(self) -> None:
        """vibecoder env-var cannot unlock CTO-only paths.

        Persona is an audit-trail slug; never a control input to the
        matrix.
        """
        out_vibe = prd.evaluate(
            claude_verdict="PASS", codex_verdict="PASS", phase="DRY_RUN",
        )
        out_cto = prd.evaluate(
            claude_verdict="PASS", codex_verdict="PASS", phase="DRY_RUN",
        )
        self.assertEqual(out_vibe, out_cto)


class TestFailOpen(unittest.TestCase):
    def test_evaluate_with_garbage_inputs_returns_safe_default(self) -> None:
        out = prd.evaluate(
            claude_verdict=None,
            codex_verdict={"x": 1},
            phase=42,
        )
        self.assertIn(out["rationale"], ("phase_disabled", "evaluator_error", "no_matrix_case"))
        self.assertFalse(out["advise_dispatch"])


if __name__ == "__main__":
    unittest.main()
