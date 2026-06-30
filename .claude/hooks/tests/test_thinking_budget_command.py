"""PLAN-086 Wave A.1+A.2+A.7 — `/effort` slash command + kwarg pass-through.

Tests for the `/effort` slash command spec at .claude/commands/effort.md and
the ClaudeLiveAdapter `thinking` kwarg wiring per Anthropic Messages API.

PLAN-134 W0 E6-F2: the contract is now model-aware. On the adaptive-only
generation (Opus 4.6+/Sonnet 4.6/Opus 4.7/4.8/Fable 5) a level maps to
``output_config.effort`` alongside ``thinking={"type": "adaptive"}``; the
``budget_tokens`` shape survives ONLY for legacy (pre-4.6) model ids. The
local parsers below mirror the doc's form table; the canonical value tables
are ``_SLASH_EFFORT_TABLE`` / ``_SLASH_BUDGET_TABLE`` in
``_lib/model_routing.py`` and are cross-checked here.

Per AC A.7 (Perf-2): task-class guard table + CEO_THINKING_AUTO_DISABLE
kill-switch.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Optional

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import model_routing  # noqa: E402


# Local parsers for the `/effort` command spec (.claude/commands/effort.md).
# The env-var transport is CEO_EFFORT_OVERRIDE (no state file); the adapter
# translation lives in ClaudeLiveAdapter.call() via _resolve_effort_config.
def parse_effort_level(arg: str) -> int:
    """Returns the LEGACY budget_tokens for a level keyword OR raw integer.

    Legacy-model-only surface (pre-4.6 ids). `--budget-tokens` is marked
    legacy-only in the doc and is ignored on adaptive-only models.
    """
    if arg == "--no-thinking" or arg == "off":
        return 0
    if arg.startswith("--budget-tokens="):
        n = int(arg.split("=", 1)[1])
        return max(1024, min(n, 32768))
    budget = model_routing._SLASH_BUDGET_TABLE.get(arg)
    if isinstance(budget, int) and budget > 0:
        return budget
    raise ValueError(f"unknown effort arg: {arg!r}")


def parse_effort_string(arg: str) -> Optional[str]:
    """Returns the ADAPTIVE output_config.effort value for a level keyword.

    None means OMIT the thinking param entirely (never {"type": "disabled"}
    — that returns HTTP 400 on Fable 5).
    """
    if arg == "--no-thinking" or arg == "off":
        return None
    level = model_routing._SLASH_EFFORT_TABLE.get(arg)
    if isinstance(level, str) and level:
        return level
    raise ValueError(f"unknown effort arg: {arg!r}")


# Task-class guard table per Perf-2 fold.
_FORCED_OFF_CLASSES = frozenset({"file_read", "line_audit", "digest"})


def thinking_allowed_for_class(task_class: str) -> bool:
    """Returns False for task classes that force-disable thinking kwarg."""
    if task_class in _FORCED_OFF_CLASSES:
        return False
    return True


class TestEffortLevelParserLegacy(unittest.TestCase):
    """Legacy (pre-4.6) budget surface — values from _SLASH_BUDGET_TABLE."""

    def test_low_1024(self) -> None:
        self.assertEqual(parse_effort_level("low"), 1024)

    def test_med_4096(self) -> None:
        self.assertEqual(parse_effort_level("med"), 4096)

    def test_high_16384(self) -> None:
        self.assertEqual(parse_effort_level("high"), 16384)

    def test_max_32768(self) -> None:
        self.assertEqual(parse_effort_level("max"), 32768)

    def test_no_thinking_zero(self) -> None:
        self.assertEqual(parse_effort_level("--no-thinking"), 0)

    def test_off_zero(self) -> None:
        self.assertEqual(parse_effort_level("off"), 0)

    def test_explicit_budget(self) -> None:
        self.assertEqual(parse_effort_level("--budget-tokens=5000"), 5000)

    def test_budget_clamped_low(self) -> None:
        self.assertEqual(parse_effort_level("--budget-tokens=500"), 1024)

    def test_budget_clamped_high(self) -> None:
        self.assertEqual(parse_effort_level("--budget-tokens=99999"), 32768)

    def test_unknown_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_effort_level("absurd-level")

    def test_medium_keyword_is_not_accepted(self) -> None:
        # The accepted keyword is `med` (canonical tables); `medium` is the
        # API-side output_config value, not a slash-command level.
        with self.assertRaises(ValueError):
            parse_effort_level("medium")


class TestEffortLevelParserAdaptive(unittest.TestCase):
    """Adaptive surface — output_config.effort values from _SLASH_EFFORT_TABLE."""

    def test_low_maps_low(self) -> None:
        self.assertEqual(parse_effort_string("low"), "low")

    def test_med_maps_medium(self) -> None:
        self.assertEqual(parse_effort_string("med"), "medium")

    def test_high_maps_high(self) -> None:
        self.assertEqual(parse_effort_string("high"), "high")

    def test_max_maps_max(self) -> None:
        self.assertEqual(parse_effort_string("max"), "max")

    def test_off_omits_thinking(self) -> None:
        # None = OMIT the thinking param (never emit {"type": "disabled"}).
        self.assertIsNone(parse_effort_string("off"))
        self.assertIsNone(parse_effort_string("--no-thinking"))

    def test_unknown_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_effort_string("absurd-level")

    def test_canonical_tables_share_keywords(self) -> None:
        # Both tables must accept exactly the same slash-command keywords.
        self.assertEqual(
            set(model_routing._SLASH_EFFORT_TABLE.keys()),
            set(model_routing._SLASH_BUDGET_TABLE.keys()),
        )

    def test_effort_table_never_contains_disabled(self) -> None:
        # E6-F2: no level may resolve to a "disabled" thinking type.
        self.assertNotIn("disabled", model_routing._SLASH_EFFORT_TABLE.values())


class TestTaskClassGuardTable(unittest.TestCase):
    """AC A.7 Perf-2: task-class guard table."""

    def test_file_read_forces_off(self) -> None:
        self.assertFalse(thinking_allowed_for_class("file_read"))

    def test_line_audit_forces_off(self) -> None:
        self.assertFalse(thinking_allowed_for_class("line_audit"))

    def test_digest_forces_off(self) -> None:
        self.assertFalse(thinking_allowed_for_class("digest"))

    def test_arch_allowed(self) -> None:
        self.assertTrue(thinking_allowed_for_class("arch"))

    def test_code_gen_allowed(self) -> None:
        self.assertTrue(thinking_allowed_for_class("code_gen"))

    def test_debate_allowed(self) -> None:
        self.assertTrue(thinking_allowed_for_class("debate"))

    def test_finops_allowed(self) -> None:
        self.assertTrue(thinking_allowed_for_class("finops"))

    def test_no_thinking_kwarg_for_excluded_classes(self) -> None:
        """Cost-delta smoke: forced-off classes must NOT receive thinking."""
        for tc in ("file_read", "line_audit", "digest"):
            self.assertFalse(
                thinking_allowed_for_class(tc),
                f"task_class={tc} should NEVER trigger thinking kwarg",
            )


class TestThinkingKillSwitch(TestEnvContext):
    """AC A.7 — CEO_THINKING_AUTO_DISABLE global kill-switch.

    Converted from manual env-snapshot to TestEnvContext (PLAN-113 F-2-2.7).
    """

    def setUp(self) -> None:
        super().setUp()  # snapshots + strips CEO_* vars (incl. CEO_THINKING_AUTO_DISABLE)

    def test_kill_switch_set_to_1(self) -> None:
        """Adapter call must drop `thinking` kwarg from body when env=1.

        Verifies the integration point by inspecting the adapter source
        (the actual run-call to Anthropic is not exercised; we read the
        source string to ensure the kill-switch is wired).
        """
        adapter_src = (_HOOKS_DIR / "_lib" / "adapters" / "live" / "claude.py").read_text()
        self.assertIn("CEO_THINKING_AUTO_DISABLE", adapter_src)
        self.assertIn('body["thinking"] = thinking', adapter_src)

    def test_effort_resolver_is_model_aware(self) -> None:
        """E6-F2: the resolver consults CEO_EFFORT_OVERRIDE and the model."""
        adapter_src = (_HOOKS_DIR / "_lib" / "adapters" / "live" / "claude.py").read_text()
        self.assertIn("CEO_EFFORT_OVERRIDE", adapter_src)
        self.assertIn("_resolve_effort_config", adapter_src)
        self.assertIn("_SLASH_EFFORT_TABLE", adapter_src)


class TestClaudeAdapterThinkingKwarg(unittest.TestCase):
    """AC A.2 — ClaudeLiveAdapter.call() accepts thinking kwarg."""

    def test_signature_has_thinking_kwarg(self) -> None:
        import inspect
        from _lib.adapters.live.claude import ClaudeLiveAdapter
        sig = inspect.signature(ClaudeLiveAdapter.call)
        params = sig.parameters
        self.assertIn("thinking", params, "thinking kwarg missing from call() signature")


if __name__ == "__main__":
    unittest.main()
