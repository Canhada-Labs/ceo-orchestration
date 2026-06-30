"""Tests for PLAN-088 W2.2 model_routing.resolve_full()."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_HOOKS = Path(__file__).resolve().parents[1]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import model_routing  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestResolveFull(TestEnvContext):
    """Wave 2.2 dict-returning resolver.

    Uses TestEnvContext so that CEO_* env writes in individual test methods
    are automatically snapshotted in setUp and restored in tearDown —
    preventing cross-test env leakage (PLAN-113 F-2-2.7).
    """

    def setUp(self) -> None:
        super().setUp()  # snapshots + strips CEO_* vars

    def test_architect_default_budget_4096(self) -> None:
        result = model_routing.resolve_full(task_class="arch")
        # arch maps to opus-4-7 in stub routing
        self.assertEqual(result["model"], "claude-opus-4-8")
        # arch task_class lookup is via "arch" key in stub, but the
        # cap_table key is "architect"; for arch task_class, the
        # general budget (0) applies — verify pricing class lookup.
        # (architect cap_table entry is keyed by "architect" task_class
        # name not the stub "arch" alias)
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])

    def test_architect_task_class_explicit_4096(self) -> None:
        # When task_class == "architect" (the cap-table key), default 4096
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["thinking_budget_tokens"], 4096)
        self.assertTrue(result["thinking"])
        self.assertEqual(result["rationale"], "task_class_default")

    def test_opt_out_multi_model_manual(self) -> None:
        os.environ["CEO_MULTI_MODEL_MANUAL"] = "1"
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["model"], "")
        self.assertFalse(result["thinking"])
        self.assertEqual(result["rationale"], "opted_out_multi_model_manual")

    def test_thinking_auto_disable_forces_budget_zero(self) -> None:
        os.environ["CEO_THINKING_AUTO_DISABLE"] = "1"
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])
        self.assertEqual(result["rationale"], "opted_out_thinking_auto_disable")

    def test_slash_override_high(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "high"
        result = model_routing.resolve_full(task_class="general")
        # general default is 0, but override to high = 16384
        self.assertEqual(result["thinking_budget_tokens"], 16384)
        self.assertTrue(result["thinking"])
        self.assertEqual(result["rationale"], "effort_override")

    def test_slash_override_off(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "off"
        result = model_routing.resolve_full(task_class="architect")
        # architect default is 4096, but slash off = 0
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])

    def test_invalid_slash_override_falls_through(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "unknown-value"
        result = model_routing.resolve_full(task_class="architect")
        # Falls through to task_class default
        self.assertEqual(result["thinking_budget_tokens"], 4096)

    def test_backward_compat_resolve_still_returns_str(self) -> None:
        # PLAN-086 callers expect resolve() to return Optional[str]
        result = model_routing.resolve("debate")
        self.assertEqual(result, "claude-opus-4-8")
        self.assertIsInstance(result, str)


class TestResolveFullExpansion(TestEnvContext):
    """PLAN-091 Wave A.2 — broader resolve_full coverage.

    R1 security-engineer P0 fold: persona enum match against
    `_ADR_052_ROLE_TO_MODEL`. Current implementation does not raise on
    unknown task_class (returns model="" instead) — that fail-SAFE
    posture is preserved per anti-churn discipline (ADR-115). These
    tests document the current contract + lock its return shape so
    PLAN-093 can extend safely without regressing v1.22.1 callers.

    Uses TestEnvContext for env isolation (PLAN-113 F-2-2.7).
    """

    def setUp(self) -> None:
        super().setUp()  # snapshots + strips CEO_* vars

    # Return-shape invariants ------------------------------------------------

    def test_return_keys_exact_set(self) -> None:
        result = model_routing.resolve_full(task_class="file_read")
        self.assertEqual(
            set(result.keys()),
            {"model", "thinking", "thinking_budget_tokens", "rationale"},
        )

    def test_thinking_field_is_bool(self) -> None:
        for tc in ("file_read", "architect", "code_gen", "unknown_xyz"):
            with self.subTest(task_class=tc):
                self.assertIsInstance(
                    model_routing.resolve_full(task_class=tc)["thinking"],
                    bool,
                )

    def test_budget_tokens_is_int(self) -> None:
        for tc in ("file_read", "architect", "code_gen", "unknown_xyz"):
            with self.subTest(task_class=tc):
                self.assertIsInstance(
                    model_routing.resolve_full(task_class=tc)["thinking_budget_tokens"],
                    int,
                )

    def test_model_field_is_str(self) -> None:
        for tc in ("file_read", "architect", "code_gen", "unknown_xyz"):
            with self.subTest(task_class=tc):
                self.assertIsInstance(
                    model_routing.resolve_full(task_class=tc)["model"],
                    str,
                )

    def test_rationale_field_is_str(self) -> None:
        for tc in ("file_read", "architect", "unknown_xyz"):
            with self.subTest(task_class=tc):
                self.assertIsInstance(
                    model_routing.resolve_full(task_class=tc)["rationale"],
                    str,
                )

    # task_class branch coverage ---------------------------------------------

    def test_file_read_maps_to_haiku(self) -> None:
        result = model_routing.resolve_full(task_class="file_read")
        self.assertEqual(result["model"], "claude-haiku-4-5")

    def test_line_audit_maps_to_haiku(self) -> None:
        result = model_routing.resolve_full(task_class="line_audit")
        self.assertEqual(result["model"], "claude-haiku-4-5")

    def test_debate_maps_to_opus(self) -> None:
        result = model_routing.resolve_full(task_class="debate")
        self.assertEqual(result["model"], "claude-opus-4-8")

    def test_code_gen_maps_to_sonnet(self) -> None:
        result = model_routing.resolve_full(task_class="code_gen")
        self.assertEqual(result["model"], "claude-sonnet-4-6")

    def test_finops_maps_to_sonnet(self) -> None:
        result = model_routing.resolve_full(task_class="finops")
        self.assertEqual(result["model"], "claude-sonnet-4-6")

    def test_digest_maps_to_haiku(self) -> None:
        result = model_routing.resolve_full(task_class="digest")
        self.assertEqual(result["model"], "claude-haiku-4-5")

    def test_unknown_task_class_model_empty(self) -> None:
        """Fail-SAFE: unknown task_class returns model='' (no raise).

        Anti-churn — PLAN-091 preserves the current fail-SAFE contract.
        Fail-CLOSED via raise is a behavior change deferred to PLAN-093.
        """
        result = model_routing.resolve_full(task_class="bogus_xyz")
        self.assertEqual(result["model"], "")

    def test_empty_task_class_model_empty(self) -> None:
        result = model_routing.resolve_full(task_class="")
        self.assertEqual(result["model"], "")

    # Cap-table coverage -----------------------------------------------------

    def test_architect_default_4096(self) -> None:
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["thinking_budget_tokens"], 4096)
        self.assertTrue(result["thinking"])

    def test_debate_r2_synthesis_default_8192(self) -> None:
        result = model_routing.resolve_full(task_class="debate-R2-synthesis")
        self.assertEqual(result["thinking_budget_tokens"], 8192)
        self.assertTrue(result["thinking"])

    def test_audit_class_default_8192(self) -> None:
        result = model_routing.resolve_full(task_class="audit-class")
        self.assertEqual(result["thinking_budget_tokens"], 8192)
        self.assertTrue(result["thinking"])

    def test_general_default_zero(self) -> None:
        result = model_routing.resolve_full(task_class="general")
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])

    # Slash-effort override matrix -------------------------------------------

    def test_slash_low_1024(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "low"
        self.assertEqual(
            model_routing.resolve_full(task_class="general")["thinking_budget_tokens"],
            1024,
        )

    def test_slash_med_4096(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "med"
        self.assertEqual(
            model_routing.resolve_full(task_class="general")["thinking_budget_tokens"],
            4096,
        )

    def test_slash_xhigh_24576(self) -> None:
        # PLAN-135 W1 K8b: xhigh legacy budget = high↔max interpolation.
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        self.assertEqual(
            model_routing.resolve_full(task_class="general")["thinking_budget_tokens"],
            24576,
        )

    def test_slash_max_32768(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "max"
        self.assertEqual(
            model_routing.resolve_full(task_class="general")["thinking_budget_tokens"],
            32768,
        )

    def test_slash_overrides_architect_default(self) -> None:
        """Slash override beats cap-table default (any direction)."""
        os.environ["CEO_EFFORT_OVERRIDE"] = "low"
        result = model_routing.resolve_full(task_class="architect")
        # cap-table architect default = 4096, slash low = 1024.
        self.assertEqual(result["thinking_budget_tokens"], 1024)
        self.assertEqual(result["rationale"], "effort_override")

    # Kill-switch interactions ------------------------------------------------

    def test_thinking_kill_switch_wins_over_slash(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "max"
        os.environ["CEO_THINKING_AUTO_DISABLE"] = "1"
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])
        self.assertEqual(result["rationale"], "opted_out_thinking_auto_disable")

    def test_manual_kill_switch_takes_precedence(self) -> None:
        os.environ["CEO_MULTI_MODEL_MANUAL"] = "1"
        os.environ["CEO_EFFORT_OVERRIDE"] = "max"
        result = model_routing.resolve_full(task_class="architect")
        self.assertEqual(result["model"], "")
        self.assertEqual(result["rationale"], "opted_out_multi_model_manual")

    # archetype + context_size parameters (currently unused) -----------------

    def test_archetype_param_ignored(self) -> None:
        a = model_routing.resolve_full(task_class="architect", archetype="x")
        b = model_routing.resolve_full(task_class="architect", archetype="")
        self.assertEqual(a, b)

    def test_context_size_param_ignored(self) -> None:
        a = model_routing.resolve_full(task_class="architect", context_size=0)
        b = model_routing.resolve_full(task_class="architect", context_size=10000)
        self.assertEqual(a, b)

    # Resolve() backward-compatibility sanity --------------------------------

    def test_resolve_non_string_returns_none(self) -> None:
        for v in (None, 42, 3.14, [], {}):
            with self.subTest(value=v):
                self.assertIsNone(model_routing.resolve(v))  # type: ignore[arg-type]

    def test_resolve_empty_returns_none(self) -> None:
        self.assertIsNone(model_routing.resolve(""))

    def test_resolve_unknown_returns_none(self) -> None:
        self.assertIsNone(model_routing.resolve("definitely-not-real"))

    def test_route_alias_matches_resolve(self) -> None:
        self.assertEqual(model_routing.route("debate"), model_routing.resolve("debate"))

    # TASK_CLASSES enum invariants -------------------------------------------

    def test_task_classes_tuple_immutable(self) -> None:
        self.assertIsInstance(model_routing.TASK_CLASSES, tuple)

    def test_task_classes_canonical_seven(self) -> None:
        expected = {"file_read", "line_audit", "debate", "arch",
                    "code_gen", "finops", "digest"}
        self.assertEqual(set(model_routing.TASK_CLASSES), expected)

    def test_slash_table_canonical_six(self) -> None:
        # PLAN-135 W1 K8b added xhigh (5 active levels + off).
        self.assertEqual(
            set(model_routing._SLASH_BUDGET_TABLE.keys()),
            {"off", "low", "med", "high", "xhigh", "max"},
        )

    def test_thinking_cap_table_canonical_four(self) -> None:
        self.assertEqual(
            set(model_routing._THINKING_BUDGET_CAP_TABLE.keys()),
            {"architect", "debate-R2-synthesis", "audit-class", "general"},
        )


if __name__ == "__main__":
    unittest.main()
