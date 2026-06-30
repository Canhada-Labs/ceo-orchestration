"""Fuzzer-driven byte-identity — PLAN-014 Phase A.5.

Generates ≥500 synthetic inputs per hook via the deterministic fuzzers
and runs them through BOTH the legacy Python hook and the new policy
engine, asserting the 6-tuple matches modulo the 3 allow-listed
message-text deviations documented by Phase A.4.

Drift MUST be zero. If any input causes an un-allow-listed divergence,
the test fails and surfaces the offending input.

Stdlib-only. No time.sleep. Deterministic (seed=42).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

_HOOKS_DIR = Path(__file__).resolve().parent.parent

_TESTS_DIR = Path(__file__).resolve().parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy as _policy  # noqa: E402
from _lib import policy_preprocessors as _pp  # noqa: E402

# Shared infrastructure — reuse the harness's 6-tuple machinery.
from test_byte_identity_harness import (  # noqa: E402
    _BASH_POLICY_PATH,
    _PLAN_POLICY_PATH,
    _run_policy_path,
    _run_py_bash_path,
    _run_py_plan_path,
    compare_six_tuple,
    _ALLOWLISTED_MESSAGE_DEVIATIONS,
)

# Fuzzers live under fixtures/byte_identity/
from fixtures.byte_identity import (  # noqa: E402
    bash_safety_fuzzer,
    plan_edit_fuzzer,
)


# ---------------------------------------------------------------------------
# Bash fuzzer suite
# ---------------------------------------------------------------------------


class TestBashFuzzerByteIdentity(TestEnvContext):
    """≥500 synthetic bash commands through both paths; zero drift."""

    _N = 500
    _SEED = 42

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = _policy.load(_BASH_POLICY_PATH)
        cls.inputs = bash_safety_fuzzer.generate(n=cls._N, seed=cls._SEED)

    def test_fuzzer_input_count_meets_floor(self) -> None:
        """≥500 inputs acceptance criterion."""
        self.assertGreaterEqual(len(self.inputs), 500)

    def test_fuzzer_is_deterministic(self) -> None:
        """Re-generating with same seed yields identical inputs."""
        a = bash_safety_fuzzer.generate(n=50, seed=self._SEED)
        b = bash_safety_fuzzer.generate(n=50, seed=self._SEED)
        self.assertEqual(a, b)

    def test_fuzzer_different_seed_differs(self) -> None:
        a = bash_safety_fuzzer.generate(n=50, seed=42)
        b = bash_safety_fuzzer.generate(n=50, seed=7)
        self.assertNotEqual(a, b)

    def test_zero_drift_across_500_inputs(self) -> None:
        """Every fuzzer input → 6-tuple match modulo allow-list."""
        drifts: List[str] = []
        checked = 0
        for i, raw_event in enumerate(self.inputs):
            # Enrich through the preprocessor so both paths see the same
            # derived state.
            event = _pp.bash_safety_preprocess(raw_event)
            yaml_res = _run_policy_path(self.policy, event)
            py_res = _run_py_bash_path(event)
            # Determine expected reason_key from yaml path (source of truth
            # for policy semantics).
            reason_key = yaml_res["reason_key"] if yaml_res["decision"] == "block" else ""
            diffs = compare_six_tuple(py_res, yaml_res, reason_key)
            if diffs:
                drifts.append(
                    f"[{i}] cmd={raw_event['tool_input']['command']!r} "
                    f"decision_yaml={yaml_res['decision']} "
                    f"decision_py={py_res['decision']} diffs={diffs}")
            checked += 1
        self.assertEqual([], drifts,
                         f"bash fuzzer drift: {len(drifts)}/{checked}")
        self.assertGreaterEqual(checked, 500)


# ---------------------------------------------------------------------------
# Plan fuzzer suite
# ---------------------------------------------------------------------------


class TestPlanFuzzerByteIdentity(TestEnvContext):
    """≥500 synthetic Edit events through both paths; zero drift."""

    _N = 500
    _SEED = 42

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = _policy.load(_PLAN_POLICY_PATH)
        cls.inputs = plan_edit_fuzzer.generate(n=cls._N, seed=cls._SEED)

    def test_fuzzer_input_count_meets_floor(self) -> None:
        self.assertGreaterEqual(len(self.inputs), 500)

    def test_fuzzer_is_deterministic(self) -> None:
        a = plan_edit_fuzzer.generate(n=50, seed=self._SEED)
        b = plan_edit_fuzzer.generate(n=50, seed=self._SEED)
        self.assertEqual(a, b)

    def test_fuzzer_different_seed_differs(self) -> None:
        a = plan_edit_fuzzer.generate(n=50, seed=42)
        b = plan_edit_fuzzer.generate(n=50, seed=7)
        self.assertNotEqual(a, b)

    def test_zero_drift_across_500_inputs(self) -> None:
        drifts: List[str] = []
        checked = 0
        for i, event in enumerate(self.inputs):
            yaml_res = _run_policy_path(self.policy, event)
            py_res = _run_py_plan_path(event)
            reason_key = yaml_res["reason_key"] if yaml_res["decision"] == "block" else ""
            diffs = compare_six_tuple(py_res, yaml_res, reason_key)
            # Additional check: decision must match
            if py_res["decision"] != yaml_res["decision"]:
                drifts.append(
                    f"[{i}] path={event['tool_input']['file_path']!r} "
                    f"decision_yaml={yaml_res['decision']} "
                    f"decision_py={py_res['decision']}")
                continue
            if diffs:
                drifts.append(
                    f"[{i}] path={event['tool_input']['file_path']!r} diffs={diffs}")
            checked += 1
        self.assertEqual([], drifts,
                         f"plan fuzzer drift: {len(drifts)}/{checked}")
        self.assertGreaterEqual(checked, 500)


# ---------------------------------------------------------------------------
# Aggregate report
# ---------------------------------------------------------------------------


class TestTotalFuzzerAssertionCount(TestEnvContext):
    """Meta-assertion: ≥1000 total fuzzer-driven checks (500 × 2 hooks)."""

    def test_total_is_at_least_1000(self) -> None:
        bash_count = len(bash_safety_fuzzer.generate(n=500, seed=42))
        plan_count = len(plan_edit_fuzzer.generate(n=500, seed=42))
        total = bash_count + plan_count
        self.assertGreaterEqual(total, 1000,
                                f"total fuzzer inputs {total} < 1000 floor")


# ---------------------------------------------------------------------------
# Allow-list regression guard
# ---------------------------------------------------------------------------


class TestAllowListIsFixed(TestEnvContext):
    """Exactly 3 deviations — adding more requires explicit plan action."""

    def test_exactly_three_allowlisted(self) -> None:
        self.assertEqual(len(_ALLOWLISTED_MESSAGE_DEVIATIONS), 3)


if __name__ == "__main__":
    unittest.main()
