"""Tests for PLAN-091 Wave A.6 docstring + status promotion.

PLAN-091 A.6 lands a MINIMAL wire per the R1 escalation clause:

1. Docstring top-of-file mentions PRODUCTION + PLAN-091 A.6.
2. Module-level `_PRODUCTION_PROMOTED_BY_PLAN_091: bool = True`.
3. The SHADOW-invariant behavior strip (removing the line ~630
   block return + line ~1149 matrix-overlay) is DEFERRED to PLAN-092
   per `.claude/plans/PLAN-091/wave-a-pair-rail-defer.md`.

These tests verify the MINIMAL wire mechanically — NOT the SHADOW
invariant (which is PLAN-092 scope).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import check_pair_rail  # noqa: E402


class TestProductionPromotionConstant(unittest.TestCase):
    """Module-level status constant exposed by A.6."""

    def test_constant_present(self):
        self.assertTrue(
            hasattr(check_pair_rail, "_PRODUCTION_PROMOTED_BY_PLAN_091"),
            "PLAN-091 A.6 must expose _PRODUCTION_PROMOTED_BY_PLAN_091",
        )

    def test_constant_is_true(self):
        self.assertIs(check_pair_rail._PRODUCTION_PROMOTED_BY_PLAN_091, True)

    def test_constant_is_bool(self):
        self.assertIsInstance(
            check_pair_rail._PRODUCTION_PROMOTED_BY_PLAN_091, bool
        )


class TestDocstringPromotion(unittest.TestCase):
    """Top-of-file docstring carries the PRODUCTION marker per R1 fold."""

    def setUp(self):
        self._source = (
            _HOOKS_DIR / "check_pair_rail.py"
        ).read_text(encoding="utf-8")

    def test_first_line_mentions_production(self):
        # Docstring begins on the second non-shebang line.
        lines = self._source.splitlines()
        docstring_line = lines[1] if len(lines) > 1 else ""
        self.assertIn("PRODUCTION", docstring_line)

    def test_first_line_cites_plan_091(self):
        lines = self._source.splitlines()
        docstring_line = lines[1] if len(lines) > 1 else ""
        self.assertIn("PLAN-091", docstring_line)


class TestDeferralDocumented(unittest.TestCase):
    """The SHADOW-strip deferral document exists."""

    def test_deferral_md_present(self):
        path = (
            _REPO_ROOT
            / "tests" / "fixtures" / "pair_rail_deferral"
            / "wave-a-pair-rail-defer.md"
        )
        self.assertTrue(path.is_file(), f"deferral doc missing: {path}")

    def test_deferral_md_references_plan_092(self):
        path = (
            _REPO_ROOT
            / "tests" / "fixtures" / "pair_rail_deferral"
            / "wave-a-pair-rail-defer.md"
        )
        body = path.read_text(encoding="utf-8")
        self.assertIn("PLAN-092", body)
        self.assertIn("SHADOW", body)


class TestPureKernelImportable(unittest.TestCase):
    """`_lib.pair_rail_decide` PURE kernel module is importable.

    PLAN-088 W4.1 shipped the kernel; A.6 promotion makes it the
    authoritative decision module. This test asserts the import path
    is stable post-A.6.
    """

    def test_pair_rail_decide_module_importable(self):
        import importlib
        mod = importlib.import_module("_lib.pair_rail_decide")
        # Spot-check 2 public symbols defined in the module.
        self.assertTrue(hasattr(mod, "resolve_phase"))
        self.assertTrue(hasattr(mod, "is_active_phase"))

    def test_active_phase_rejects_ACTIVE_str(self):
        from _lib.pair_rail_decide import is_active_phase
        # M-6 invariant: ACTIVE must be rejected as not-active.
        self.assertFalse(is_active_phase("ACTIVE"))

    def test_resolve_phase_disabled_fallback(self):
        from _lib.pair_rail_decide import resolve_phase
        self.assertEqual(resolve_phase(""), "DISABLED")
        self.assertEqual(resolve_phase(None), "DISABLED")
        self.assertEqual(resolve_phase("ACTIVE"), "DISABLED")  # M-6
        self.assertEqual(resolve_phase("SHADOW"), "SHADOW")
        self.assertEqual(resolve_phase("DRY_RUN"), "DRY_RUN")
        self.assertEqual(resolve_phase("garbage"), "DISABLED")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
