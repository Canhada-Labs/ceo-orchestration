"""PLAN-152 sonnet5-tier (ADR-157) — routing-pin regression tests.

Debate/Critic-A requirement: adding the ``SONNET5`` member to the closed
``MODEL_ID`` enum must NOT silently repoint any routing default. The
routing flip to Sonnet 5 is explicitly OUT of v1.0.1 (OQ1 resolution) —
it needs its own plan with soak + documented revert. These tests pin the
CURRENT M-tier routing so any future flip must consciously edit them.

stdlib-only; read-only against the live tree.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TESTS_DIR.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.tier_policy import _constants as C  # noqa: E402
from _lib.tier_policy import _types as T  # noqa: E402


class TestSonnet5RoutingPin(TestEnvContext):
    """The enum grew; the routing did not move."""

    def test_frozen_baseline_default_model_unchanged(self):
        self.assertEqual(
            C.FROZEN_BASELINE["default_model"], "claude-opus-4-8",
            "FROZEN_BASELINE default_model moved — the OQ1 resolution pins "
            "the M-tier default to OPUS47 until a dedicated routing plan "
            "flips it with soak + revert.",
        )

    def test_frozen_baseline_default_mode_unchanged(self):
        self.assertEqual(C.FROZEN_BASELINE["default_mode"], "M")

    def test_sonnet5_is_recognized_but_not_default(self):
        # Additive: the new member is a KNOWN model...
        self.assertTrue(T.is_known_model("claude-sonnet-5"))
        # ...but it is not the default anywhere in the frozen baseline.
        self.assertNotEqual(
            C.FROZEN_BASELINE["default_model"], T.MODEL_ID.SONNET5.value
        )

    def test_cost_table_default_model_unchanged(self):
        # The sub-agent dispatch default (token-estimator surface) also
        # stays put — the Sonnet-5 row is pricing-only in v1.0.1.
        cost_table = (
            _REPO_ROOT / ".claude" / "scripts" / "cost-table.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("default_model: claude-sonnet-4-6", cost_table)
        self.assertIn("claude-sonnet-5:", cost_table,
                      "pricing row for the new member must exist")

    def test_legacy_and_unknown_slugs_still_rejected(self):
        # Closed-enum property preserved by the addition.
        with self.assertRaises(ValueError):
            T.MODEL_ID("claude-opus-4-1")
        with self.assertRaises(ValueError):
            T.MODEL_ID("claude-sonnet-5-20260601")  # no date-suffix variants


if __name__ == "__main__":
    unittest.main()
