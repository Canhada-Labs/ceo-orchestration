"""Forward/regression test for PLAN-137 A4 — 1M-window pricing doctrine.

Pins the A4 gate evidence (PLAN-137 S236 design-review, gate verdict GREEN):
the 1M context window prices at a FLAT standard per-token rate (NO long-context
premium) for the current CEO-tier models, and the three non-classic spend
multipliers — Haiku 4.5 caps at 200K (not 1M), fast-mode is an Opus-only
premium ($30/$150 for 4.6/4.7, $10/$50 for 4.8), and ``inference_geo:"us"``
data residency is 1.1x — are documented at their exact values.

If a future edit assumes a >200K context premium, reverts Opus 4.6 to its
retired $15/$75 rate, drops the Haiku-200K cap, or softens a multiplier, this
test fails. It is the standing regression that keeps the "raise the per-plan
token band to 1M" doctrine honest against the flat-rate assumption it rests on.

Reads only repo docs/config — touches no env, no network. Stdlib-only unittest,
env-isolated via TestEnvContext (env-hygiene gate compliance).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_COST_TABLE = _REPO_ROOT / ".claude" / "scripts" / "cost-table.yaml"
_PRICING = _REPO_ROOT / "docs" / "provider-pricing.md"
_CAP_MATRIX = _REPO_ROOT / "docs" / "provider_capability_matrix.md"

# Flat standard per-MTok rates the A4 gate confirmed carry NO long-context
# premium at the full 1M window (input, output). A drift here means either the
# rate card moved (re-verify the gate) or someone introduced a tiered rate.
# These are the cost-table.yaml models (Opus 4.6 lives only in the
# provider-pricing primary table — asserted separately below).
_EXPECTED_RATES = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


class TestA4PricingDoctrine(TestEnvContext):
    """Standing regression for the PLAN-137 A4 flat-1M-pricing assumption."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self.cost_table = _COST_TABLE.read_text(encoding="utf-8")
        self.pricing = _PRICING.read_text(encoding="utf-8")
        self.cap_matrix = _CAP_MATRIX.read_text(encoding="utf-8")

    def test_cost_table_has_ceo_tier_models_at_flat_rates(self) -> None:
        """Every CEO-tier model in cost-table.yaml is at its flat standard rate."""
        for model, (inp, out) in _EXPECTED_RATES.items():
            block = re.search(
                r"^  " + re.escape(model) + r":\n(?:    .*\n)+",
                self.cost_table,
                re.MULTILINE,
            )
            self.assertIsNotNone(
                block, "%s missing from cost-table.yaml models block" % model
            )
            text = block.group(0)
            self.assertIn(
                "input_per_mtok: %.2f" % inp, text, "%s input rate drift" % model
            )
            self.assertIn(
                "output_per_mtok: %.2f" % out, text, "%s output rate drift" % model
            )

    def test_provider_pricing_opus_4_6_rebased_to_5_25(self) -> None:
        """Opus 4.6 in the provider-pricing primary table is $5/$25, not the
        retired $15/$75 — the stale-rate drift the A4 pass closed."""
        # Primary table row (per-1k): claude-opus-4-6 | 0.005 | 0.025
        row = re.search(
            r"\|\s*Anthropic\s*\|\s*claude-opus-4-6\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
            self.pricing,
        )
        self.assertIsNotNone(row, "claude-opus-4-6 row missing from primary table")
        self.assertEqual(row.group(1), "0.005", "opus-4-6 input must be 0.005/1k")
        self.assertEqual(row.group(2), "0.025", "opus-4-6 output must be 0.025/1k")
        # The retired rate must not reappear anywhere on an opus-4-6 line.
        for line in self.pricing.splitlines():
            if "claude-opus-4-6" in line:
                self.assertNotIn("0.075", line, "opus-4-6 still carries retired 0.075")
                self.assertNotIn("75.00", line, "opus-4-6 still carries retired 75.00")

    def test_long_context_gate_evidence_present_and_green(self) -> None:
        """The dated/sourced 1M-premium confirmation artifact exists and is GREEN."""
        self.assertIn("Long-context (1M window) pricing", self.pricing)
        self.assertRegex(self.pricing, r"Gate verdict:\s*GREEN")
        self.assertIn("no long-context premium", self.pricing.lower())
        self.assertIn("2026-06-15", self.pricing)  # verified date stamped

    def test_three_spend_multipliers_documented_at_exact_values(self) -> None:
        """All three non-classic 1M-scale spend multipliers are pinned exactly."""
        low = self.pricing.lower()
        # (1) Haiku 4.5 window caps at 200K, NOT 1M — assert the cap row says N.
        self.assertRegex(
            self.pricing,
            r"claude-haiku-4-5\s*\|\s*\*\*N[ —-].*200[Kk]",
            "Haiku-200K-not-1M cap row missing/changed",
        )
        # (2) Fast mode (Opus-only premium) at exact rates.
        self.assertIn("$30 / $150", self.pricing)  # Opus 4.6/4.7 fast
        self.assertIn("$10 / $50", self.pricing)   # Opus 4.8 fast
        self.assertIn("fast mode", low)
        # (3) us-residency = 1.1x.
        self.assertIn("1.1", self.pricing)
        self.assertRegex(low, r"inference_geo|residency")

    def test_capability_matrix_no_stale_200k_only_opus(self) -> None:
        """The stale 'claude = 200k (Opus)' max_context claim is gone; 1M present."""
        self.assertNotIn("200k (Opus)", self.cap_matrix)
        self.assertIn("1M", self.cap_matrix)


if __name__ == "__main__":
    unittest.main()
