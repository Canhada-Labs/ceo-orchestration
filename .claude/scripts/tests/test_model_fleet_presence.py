"""PLAN-163 T1.5 presence oracle — Claude 5 fleet in cost/telemetry surfaces.

CF-2 / gap G3 (grok r1 F11 scope): the cost-rollup and ghost-token-waste
surfaces must RECOGNIZE the current fleet (claude-opus-4-8, claude-fable-5,
claude-opus-5 + its fast row, claude-sonnet-5) while NEVER dropping the
historical ids they already carry (audit-log replay, ADR-142).

Born-RED by design (red-first): at authoring time (2026-07-28, HEAD before
the T1.5 fix) `audit-telemetry.py` `_PRICING_PER_MTOK` lacked opus-4-8 AND
fable-5 entirely, the detectors lacked fable-5/opus-5, and
`ceo-cost.py`/`budget-summary.py` lacked fable-5/opus-5/sonnet-5. This file
is the standing regression that keeps the fleet presence honest.

Pricing pins asserted here (public rates, per MTok):
  - claude-opus-4-8       $5 / $25
  - claude-opus-4-8-fast  $10 / $50  (W2 P2b — live replacement id in
                                      model-deprecations.json; was $0/unknown)
  - claude-fable-5        $10 / $50  (rate the repo already carries in
                                      cost-table.yaml / rate-card fixtures)
  - claude-opus-5         $5 / $25   (drop-in at the 4.8 rate)
  - claude-opus-5-fast    $10 / $50  (fast-mode premium row)
  - claude-sonnet-5       $2 / $10   intro through 2026-08-31, then $3/$15 —
                          EVENT-DATE-AWARE on the replay/rollup surfaces
                          (W2 P2a: each event is priced by its OWN ts via the
                          _DATED_PRICING tables; the global row is never
                          mutated). cost-table.yaml deliberately keeps the
                          $3/$15 sticker per its ADR-157 comment (forward
                          estimator, intro not modeled) — NOT asserted here.

Reads only repo files — touches no env, no network. Stdlib-only unittest,
env-isolated via TestEnvContext (env-hygiene gate compliance).
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
for _p in (str(_HOOKS_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402

_COST_TABLE = _SCRIPTS_DIR / "cost-table.yaml"

#: Fleet ids that every rollup surface must recognize after PLAN-163 T1.5.
#: claude-opus-4-8-fast added by W2 P2b — it is the live replacement id in
#: model-deprecations.json (4-6-fast and 4-7-fast both point at it) and was
#: silently priced $0/unknown by every surface.
_NEW_FLEET = (
    "claude-opus-4-8",
    "claude-opus-4-8-fast",
    "claude-fable-5",
    "claude-opus-5",
    "claude-opus-5-fast",
    "claude-sonnet-5",
)

#: Historical ids that must NEVER be removed (audit-log replay, ADR-142).
_HISTORICAL_RETAINED = (
    "claude-opus-4-7",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
)


def _load_hyphenated(module_name: str, file_name: str):
    """Load a hyphenated-filename script as a module (scripts-tests pattern)."""
    spec = importlib.util.spec_from_file_location(
        module_name, str(_SCRIPTS_DIR / file_name)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestAuditTelemetryFleetPresence(TestEnvContext):
    """`_PRICING_PER_MTOK` (audit-telemetry.py) knows the current fleet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = _load_hyphenated("audit_telemetry_fleet", "audit-telemetry.py")

    def test_new_fleet_present(self) -> None:
        pricing = self.mod._PRICING_PER_MTOK
        for model in _NEW_FLEET:
            self.assertIn(
                model, pricing,
                "%s missing from audit-telemetry _PRICING_PER_MTOK "
                "(PLAN-163 T1.5a presence fix)" % model,
            )

    def test_new_fleet_rates(self) -> None:
        pricing = self.mod._PRICING_PER_MTOK
        expected = {
            "claude-opus-4-8": (5.00, 25.00),
            "claude-opus-4-8-fast": (10.00, 50.00),  # W2 P2b
            "claude-fable-5": (10.00, 50.00),
            "claude-opus-5": (5.00, 25.00),
            "claude-opus-5-fast": (10.00, 50.00),
            # Base-row intro rate; the 2026-08-31 flip is event-date-aware
            # via _DATED_PRICING_PER_MTOK (W2 P2a, asserted below).
            "claude-sonnet-5": (2.00, 10.00),
        }
        for model, (inp, out) in expected.items():
            row = pricing.get(model)
            self.assertIsNotNone(row, "%s missing" % model)
            self.assertAlmostEqual(row["input"], inp, msg="%s input" % model)
            self.assertAlmostEqual(row["output"], out, msg="%s output" % model)

    def test_historical_ids_retained(self) -> None:
        pricing = self.mod._PRICING_PER_MTOK
        for model in _HISTORICAL_RETAINED:
            self.assertIn(
                model, pricing,
                "%s dropped from audit-telemetry — historical ids must be "
                "RETAINED for audit-log replay (ADR-142)" % model,
            )
        # The 4-7 long-context row is a replay id too.
        self.assertIn("claude-opus-4-7[1m]", pricing)

    def test_cost_computed_for_opus5_event(self) -> None:
        """A synthetic opus-5 spawn event yields a non-zero cost."""
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-opus-5", "tokens_in": 1_000_000, "tokens_out": 0}
        )
        self.assertAlmostEqual(cost, 5.00)

    # -- W2 P2a: Sonnet 5 pricing is event-date-aware, never global-mutated --

    def test_sonnet5_intro_rate_before_cutoff(self) -> None:
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 0, "ts": "2026-08-01T00:00:00Z"}
        )
        self.assertAlmostEqual(cost, 2.00)

    def test_sonnet5_cutoff_day_is_inclusive(self) -> None:
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 0, "ts": "2026-08-31T23:59:59Z"}
        )
        self.assertAlmostEqual(cost, 2.00)

    def test_sonnet5_sticker_rate_after_cutoff(self) -> None:
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 1_000_000, "ts": "2026-09-01T00:00:00Z"}
        )
        self.assertAlmostEqual(cost, 18.00)  # $3 in + $15 out

    def test_sonnet5_missing_ts_falls_back_to_base_row(self) -> None:
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 0}
        )
        self.assertAlmostEqual(cost, 2.00)

    def test_dated_lookup_does_not_mutate_global_row(self) -> None:
        before = dict(self.mod._PRICING_PER_MTOK["claude-sonnet-5"])
        self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 0, "ts": "2026-09-01T00:00:00Z"}
        )
        self.assertEqual(
            self.mod._PRICING_PER_MTOK["claude-sonnet-5"], before,
            "dated pricing must never repaint the global row (P2a)",
        )


class TestDetectorFleetPresence(TestEnvContext):
    """PLAN-047 detectors treat Fable 5 / Opus 5 as large-model spawns."""

    def test_overpowered_large_models(self) -> None:
        from detectors import overpowered
        for model in ("claude-fable-5", "claude-opus-5"):
            self.assertIn(
                model, overpowered._LARGE_MODELS,
                "%s missing from overpowered._LARGE_MODELS" % model,
            )
        # Existing members retained (replay + current fleet).
        for model in ("claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6"):
            self.assertIn(model, overpowered._LARGE_MODELS)

    def test_wasteful_thinking_target_models(self) -> None:
        from detectors import wasteful_thinking
        for model in ("claude-fable-5", "claude-opus-5"):
            self.assertIn(
                model, wasteful_thinking._TARGET_MODELS,
                "%s missing from wasteful_thinking._TARGET_MODELS" % model,
            )
        # 4-8 current + 4-7 historical replay (ADR-142) retained.
        for model in ("claude-opus-4-8", "claude-opus-4-7"):
            self.assertIn(model, wasteful_thinking._TARGET_MODELS)


class TestCeoCostFleetPresence(TestEnvContext):
    """`_DEFAULT_PRICING` (ceo-cost.py) knows the current fleet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = _load_hyphenated("ceo_cost_fleet", "ceo-cost.py")

    def test_new_fleet_present(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in _NEW_FLEET:
            self.assertIn(
                model, pricing,
                "%s missing from ceo-cost _DEFAULT_PRICING "
                "(PLAN-163 T1.5b)" % model,
            )

    def test_historical_ids_retained(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        # opus-4-7 rows keep the RETAINED HISTORICAL $15/$75 replay rate.
        self.assertIn("claude-opus-4-7", pricing)
        self.assertIn("claude-opus-4-7[1m]", pricing)
        self.assertAlmostEqual(
            pricing["claude-opus-4-7"]["input_per_mtok"], 15.00
        )
        for model in _HISTORICAL_RETAINED:
            self.assertIn(model, pricing)

    def test_opus5_rate(self) -> None:
        row = self.mod._DEFAULT_PRICING["claude-opus-5"]
        self.assertAlmostEqual(row["input_per_mtok"], 5.00)
        self.assertAlmostEqual(row["output_per_mtok"], 25.00)

    # -- W2 P2a: cost_usd honours the event's own ts for dated rows --

    def test_sonnet5_dated_cost_usd(self) -> None:
        p = self.mod._DEFAULT_PRICING
        self.assertAlmostEqual(
            self.mod.cost_usd(p, "claude-sonnet-5", 1_000_000, 0,
                              ts="2026-08-31T12:00:00Z"), 2.00)
        self.assertAlmostEqual(
            self.mod.cost_usd(p, "claude-sonnet-5", 1_000_000, 0,
                              ts="2026-09-01T00:00:00Z"), 3.00)
        # No ts -> static row (pre-P2a behaviour preserved).
        self.assertAlmostEqual(
            self.mod.cost_usd(p, "claude-sonnet-5", 1_000_000, 0), 2.00)

    def test_sonnet5_custom_override_beats_dated_row(self) -> None:
        """CEO_COST_PRICING_JSON custom rows win over built-in dated rows."""
        custom = dict(self.mod._DEFAULT_PRICING)
        custom["claude-sonnet-5"] = {
            "input_per_mtok": 9.00, "output_per_mtok": 9.00
        }
        self.assertAlmostEqual(
            self.mod.cost_usd(custom, "claude-sonnet-5", 1_000_000, 0,
                              ts="2026-09-01T00:00:00Z"), 9.00)


class TestBudgetSummaryFleetPresence(TestEnvContext):
    """`_DEFAULT_PRICING` (budget-summary.py, per-1k rates) knows the fleet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = _load_hyphenated("budget_summary_fleet", "budget-summary.py")

    def test_new_fleet_present(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in _NEW_FLEET:
            self.assertIn(
                model, pricing,
                "%s missing from budget-summary _DEFAULT_PRICING "
                "(PLAN-163 T1.5b)" % model,
            )

    def test_per_1k_rates(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        expected = {
            "claude-opus-4-8-fast": (0.010, 0.050),  # W2 P2b
            "claude-opus-5": (0.005, 0.025),
            "claude-opus-5-fast": (0.010, 0.050),
            "claude-fable-5": (0.010, 0.050),
            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below
        }
        for model, (inp, out) in expected.items():
            row = pricing[model]
            self.assertAlmostEqual(row["in"], inp, msg="%s in" % model)
            self.assertAlmostEqual(row["out"], out, msg="%s out" % model)

    def test_sonnet5_dated_compute_cost(self) -> None:
        """W2 P2a: compute_cost_usd honours the event's own ts."""
        self.assertAlmostEqual(
            self.mod.compute_cost_usd("claude-sonnet-5", 1000, 0,
                                      ts="2026-08-31T12:00:00Z"), 0.002)
        self.assertAlmostEqual(
            self.mod.compute_cost_usd("claude-sonnet-5", 1000, 1000,
                                      ts="2026-09-01T00:00:00Z"), 0.018)
        # No ts -> static row (pre-P2a behaviour preserved).
        self.assertAlmostEqual(
            self.mod.compute_cost_usd("claude-sonnet-5", 1000, 0), 0.002)

    def test_historical_ids_retained(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in ("claude-opus-4-7", "claude-opus-4", "claude-sonnet-4",
                      "claude-haiku-4"):
            self.assertIn(
                model, pricing,
                "%s dropped — historical rows must be retained (ADR-142)"
                % model,
            )


class TestCostTableFleetPresence(TestEnvContext):
    """cost-table.yaml carries the NEW ids (opus-5 + fast row).

    fable-5 / opus-4-8 / sonnet-5 rows already existed there pre-PLAN-163
    (asserted by test_a4_pricing_doctrine.py); only the ids new to this
    plan are asserted here.
    """

    def setUp(self) -> None:
        super().setUp()
        self.cost_table = _COST_TABLE.read_text(encoding="utf-8")

    def _block(self, model: str) -> str:
        block = re.search(
            r"^  " + re.escape(model) + r":\n(?:    .*\n)+",
            self.cost_table,
            re.MULTILINE,
        )
        self.assertIsNotNone(
            block, "%s missing from cost-table.yaml models block" % model
        )
        return block.group(0)

    def test_opus5_row(self) -> None:
        text = self._block("claude-opus-5")
        self.assertIn("input_per_mtok: 5.00", text)
        self.assertIn("output_per_mtok: 25.00", text)

    def test_opus5_fast_row(self) -> None:
        text = self._block("claude-opus-5-fast")
        self.assertIn("input_per_mtok: 10.00", text)
        self.assertIn("output_per_mtok: 50.00", text)

    def test_opus48_fast_row(self) -> None:
        """W2 P2b: 4-8-fast is a live replacement id and must be priced."""
        text = self._block("claude-opus-4-8-fast")
        self.assertIn("input_per_mtok: 10.00", text)
        self.assertIn("output_per_mtok: 50.00", text)

    def test_historical_rows_retained(self) -> None:
        for model in ("claude-opus-4-7", "claude-opus-4-7-1m",
                      "claude-fable-5", "claude-opus-4-8",
                      "claude-sonnet-4-6", "claude-sonnet-5",
                      "claude-haiku-4-5"):
            self._block(model)


if __name__ == "__main__":
    unittest.main()
