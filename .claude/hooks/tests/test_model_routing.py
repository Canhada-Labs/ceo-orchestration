"""PLAN-135 W1 K8b — `/effort` xhigh fix on the canonical routing tables.

W1 Check target: ``python3 -m pytest .claude/hooks/tests/test_model_routing.py
-q -k effort`` — every test method name carries ``effort`` so the ``-k``
filter selects the whole file.

Covers the K8b unit (cherry-picked from W3, debate R1):

- ``_SLASH_EFFORT_TABLE`` gains ``"xhigh" -> "xhigh"`` — the API
  ``output_config.effort`` tier between ``high`` and ``max`` introduced
  with Opus 4.7 (supported on Opus 4.7/4.8 + Fable 5; Claude Code default
  for coding/agentic work). 5-active-level ladder parity (K8 harvest).
- ``_SLASH_BUDGET_TABLE`` gains ``"xhigh" -> 24576`` — the legacy-surface
  high↔max interpolation, keeping the cross-table shared-keyword
  invariant (test_thinking_budget_command.py::
  test_canonical_tables_share_keywords) and the ``CEO_EFFORT_OVERRIDE``
  transport (resolve_full) working for the new keyword.
- Adapter pass-through: ``_resolve_effort_config`` emits
  ``({"type": "adaptive"}, {"effort": "xhigh"})`` on adaptive-only ids
  and ``({"type": "enabled", "budget_tokens": 24576}, None)`` on legacy
  ids.

STAGED with the staged ``_lib/model_routing.py`` (coupling rule: this
file asserts xhigh, which only exists post-ceremony).

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import model_routing  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestSlashEffortTableXhigh(unittest.TestCase):
    """Adaptive surface — _SLASH_EFFORT_TABLE carries the xhigh tier."""

    def test_effort_table_has_xhigh_keyword(self) -> None:
        self.assertIn("xhigh", model_routing._SLASH_EFFORT_TABLE)

    def test_effort_xhigh_maps_to_api_xhigh(self) -> None:
        # API value is the literal effort tier string, same shape as "high".
        self.assertEqual(model_routing._SLASH_EFFORT_TABLE["xhigh"], "xhigh")

    def test_effort_xhigh_value_format_matches_high_entry(self) -> None:
        # K8b spec: match the exact value format of the existing high entry
        # (plain non-empty str — the output_config.effort wire value).
        high = model_routing._SLASH_EFFORT_TABLE["high"]
        xhigh = model_routing._SLASH_EFFORT_TABLE["xhigh"]
        self.assertIsInstance(high, str)
        self.assertIsInstance(xhigh, str)
        self.assertTrue(high)
        self.assertTrue(xhigh)

    def test_effort_table_canonical_six_keywords(self) -> None:
        self.assertEqual(
            set(model_routing._SLASH_EFFORT_TABLE.keys()),
            {"off", "low", "med", "high", "xhigh", "max"},
        )

    def test_effort_table_full_ladder_mapping(self) -> None:
        # off omits thinking entirely; the 5 active levels mirror the API
        # enum low < medium < high < xhigh < max.
        self.assertEqual(
            model_routing._SLASH_EFFORT_TABLE,
            {
                "off":   None,
                "low":   "low",
                "med":   "medium",
                "high":  "high",
                "xhigh": "xhigh",
                "max":   "max",
            },
        )

    def test_effort_table_never_contains_disabled(self) -> None:
        # E6-F2 invariant preserved: no level may resolve to a "disabled"
        # thinking type ({"type": "disabled"} is HTTP 400 on Fable 5).
        self.assertNotIn("disabled", model_routing._SLASH_EFFORT_TABLE.values())


class TestSlashEffortBudgetParity(unittest.TestCase):
    """Cross-table invariants — budget table tracks the same keywords."""

    def test_effort_budget_tables_share_keywords(self) -> None:
        # The same invariant test_thinking_budget_command pins; asserted
        # here too so the K8b check file is self-contained.
        self.assertEqual(
            set(model_routing._SLASH_EFFORT_TABLE.keys()),
            set(model_routing._SLASH_BUDGET_TABLE.keys()),
        )

    def test_effort_xhigh_legacy_budget_24576(self) -> None:
        self.assertEqual(model_routing._SLASH_BUDGET_TABLE["xhigh"], 24576)

    def test_effort_xhigh_legacy_budget_between_high_and_max(self) -> None:
        # Legacy ids have no native xhigh tier — the budget is the
        # high↔max interpolation, inside the --budget-tokens clamp range.
        table = model_routing._SLASH_BUDGET_TABLE
        self.assertGreater(table["xhigh"], table["high"])
        self.assertLess(table["xhigh"], table["max"])

    def test_effort_budget_ladder_monotonic(self) -> None:
        table = model_routing._SLASH_BUDGET_TABLE
        ladder = [table[k] for k in ("off", "low", "med", "high", "xhigh", "max")]
        self.assertEqual(ladder, sorted(ladder))
        self.assertEqual(len(ladder), len(set(ladder)))


class TestEffortOverrideTransportXhigh(TestEnvContext):
    """CEO_EFFORT_OVERRIDE=xhigh flows through resolve_full (legacy field).

    Uses TestEnvContext so CEO_* env writes are snapshotted/restored
    (PLAN-113 F-2-2.7).
    """

    def setUp(self) -> None:
        super().setUp()  # snapshots + strips CEO_* vars

    def test_effort_override_xhigh_resolve_full(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        result = model_routing.resolve_full(task_class="general")
        self.assertEqual(result["thinking_budget_tokens"], 24576)
        self.assertTrue(result["thinking"])
        self.assertEqual(result["rationale"], "effort_override")

    def test_effort_override_xhigh_beats_task_class_default(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        result = model_routing.resolve_full(task_class="architect")
        # cap-table architect default = 4096, slash xhigh = 24576.
        self.assertEqual(result["thinking_budget_tokens"], 24576)
        self.assertEqual(result["rationale"], "effort_override")

    def test_effort_override_xhigh_killed_by_thinking_auto_disable(self) -> None:
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        os.environ["CEO_THINKING_AUTO_DISABLE"] = "1"
        result = model_routing.resolve_full(task_class="general")
        self.assertEqual(result["thinking_budget_tokens"], 0)
        self.assertFalse(result["thinking"])
        self.assertEqual(result["rationale"], "opted_out_thinking_auto_disable")


class TestEffortAdapterPassThroughXhigh(TestEnvContext):
    """_resolve_effort_config translates xhigh per model generation."""

    def setUp(self) -> None:
        super().setUp()  # snapshots + strips CEO_* vars

    def test_effort_xhigh_adaptive_model_emits_output_config(self) -> None:
        from _lib.adapters.live.claude import _resolve_effort_config
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        thinking, output_config = _resolve_effort_config("claude-fable-5")
        self.assertEqual(thinking, {"type": "adaptive"})
        self.assertEqual(output_config, {"effort": "xhigh"})

    def test_effort_xhigh_legacy_model_emits_budget(self) -> None:
        from _lib.adapters.live.claude import _resolve_effort_config
        os.environ["CEO_EFFORT_OVERRIDE"] = "xhigh"
        # claude-opus-4-5 is outside _ADAPTIVE_ONLY_MODELS → legacy shape.
        thinking, output_config = _resolve_effort_config("claude-opus-4-5")
        self.assertEqual(thinking, {"type": "enabled", "budget_tokens": 24576})
        self.assertIsNone(output_config)


if __name__ == "__main__":
    unittest.main()
