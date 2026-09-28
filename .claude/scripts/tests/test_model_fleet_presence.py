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
  - claude-opus-5-5       $4 / $20   (ADR-149 Amendment 3, S357 — the session
                                      pin; cache reads 0.05x base, asserted
                                      below together with the class cure that
                                      reads the fleet FROM ADR-149)
  - claude-sonnet-5       $2 / $10   STANDARD rate on BOTH sides of 2026-09-01
                          (PLAN-169 S338 follow-up): the launch intro price
                          became permanent — the official pricing page
                          (fetched 2026-09-01) states the scheduled 2026-09-01
                          increase to $3/$15 "will not occur". The dated
                          $3/$15 flip row was retired from the three
                          _DATED_PRICING tables (both legs equalled the base
                          row = dead data); the event-date MECHANISM (W2 P2a:
                          each event priced by its OWN ts, the global row
                          never mutated) stays and is asserted below through
                          a SYNTHETIC dated row. cost-table.yaml now carries
                          $2/$10 too (the ADR-157 sticker note is superseded)
                          — asserted below.

Reads only repo files — touches no env, no network. Stdlib-only unittest,
env-isolated via TestEnvContext (env-hygiene gate compliance).
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
for _p in (str(_HOOKS_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402

_COST_TABLE = _SCRIPTS_DIR / "cost-table.yaml"
_ADR_149 = _REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"

#: Fleet ids that every rollup surface must recognize after PLAN-163 T1.5.
#: claude-opus-4-8-fast added by W2 P2b — it is the live replacement id in
#: model-deprecations.json (4-6-fast and 4-7-fast both point at it) and was
#: silently priced $0/unknown by every surface.
#: claude-fable-5-1 added by ADR-149 Amendment 2 (S338) — Fable 5.1 at the
#: Fable 5 rate; the same silent-$0 class this file exists to keep honest.
#: claude-opus-5-5 added by ADR-149 Amendment 3 (S357) — Opus 5.5 at $4/$20.
#: Since S357 this hand list is NOT the only guard: the working-set class
#: cure below reads the fleet from ADR-149 itself.
_NEW_FLEET = (
    "claude-opus-4-8",
    "claude-opus-4-8-fast",
    "claude-fable-5",
    "claude-fable-5-1",
    "claude-opus-5",
    "claude-opus-5-fast",
    "claude-opus-5-5",
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


def _load_registered(module_name: str, file_name: str):
    """Like ``_load_hyphenated`` but registers the module in ``sys.modules``
    BEFORE executing it: ceo-cost-transcripts.py declares dataclasses, which
    resolve their module through ``sys.modules`` at class-definition time.
    """
    spec = importlib.util.spec_from_file_location(
        module_name, str(_SCRIPTS_DIR / file_name)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
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
            "claude-fable-5-1": (10.00, 50.00),  # ADR-149 A2 (S338)
            "claude-opus-5": (5.00, 25.00),
            "claude-opus-5-fast": (10.00, 50.00),
            "claude-opus-5-5": (4.00, 20.00),  # ADR-149 A3 (S357)
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

    # -- PLAN-169 S338 follow-up: Sonnet 5 is $2/$10 on BOTH sides of
    #    2026-09-01 (the intro price became the standard price; the dated
    #    $3/$15 flip row was retired). The W2 P2a event-date MECHANISM is
    #    kept alive below through a SYNTHETIC dated row. --

    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:
        for ts in ("2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z",
                   "2026-09-01T00:00:00Z", "2026-12-31T23:59:59Z"):
            cost = self.mod._compute_event_cost_usd(
                {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
                 "tokens_out": 1_000_000, "ts": ts}
            )
            # $2 in + $10 out — never $3 + $15.
            self.assertAlmostEqual(cost, 12.00, msg="ts=%s" % ts)

    def test_sonnet5_missing_ts_uses_base_row(self) -> None:
        cost = self.mod._compute_event_cost_usd(
            {"model": "claude-sonnet-5", "tokens_in": 1_000_000,
             "tokens_out": 0}
        )
        self.assertAlmostEqual(cost, 2.00)

    def test_sonnet5_has_no_dated_row(self) -> None:
        """The $3/$15 flip row is dead data since 2026-09-01 — retired."""
        self.assertNotIn("claude-sonnet-5", self.mod._DATED_PRICING_PER_MTOK)

    def test_dated_pricing_mechanism_synthetic_row(self) -> None:
        """W2 P2a mechanism survives the row retirement: a synthetic dated
        row prices by the event's OWN ts (cutoff inclusive), a missing ts
        falls back to the base row, and the global row is never mutated."""
        model = "synthetic-dated-model"
        base = {"input": 2.00, "output": 10.00}
        dated = ("2026-08-31", {"input": 2.00, "output": 10.00},
                 {"input": 3.00, "output": 15.00})
        with mock.patch.dict(self.mod._PRICING_PER_MTOK, {model: base}), \
                mock.patch.dict(self.mod._DATED_PRICING_PER_MTOK, {model: dated}):
            ev = {"model": model, "tokens_in": 1_000_000, "tokens_out": 1_000_000}
            self.assertAlmostEqual(
                self.mod._compute_event_cost_usd(dict(ev, ts="2026-08-31T23:59:59Z")),
                12.00)
            self.assertAlmostEqual(
                self.mod._compute_event_cost_usd(dict(ev, ts="2026-09-01T00:00:00Z")),
                18.00)
            self.assertAlmostEqual(self.mod._compute_event_cost_usd(ev), 12.00)
            self.assertEqual(
                self.mod._PRICING_PER_MTOK[model], base,
                "dated pricing must never repaint the global row (P2a)",
            )
        self.assertNotIn(model, self.mod._PRICING_PER_MTOK)
        self.assertNotIn(model, self.mod._DATED_PRICING_PER_MTOK)


class TestDetectorFleetPresence(TestEnvContext):
    """PLAN-047 detectors treat Fable 5 / Opus 5 as large-model spawns."""

    def test_overpowered_large_models(self) -> None:
        from detectors import overpowered
        for model in ("claude-fable-5", "claude-fable-5-1", "claude-opus-5",
                      "claude-opus-5-5"):
            self.assertIn(
                model, overpowered._LARGE_MODELS,
                "%s missing from overpowered._LARGE_MODELS" % model,
            )
        # Existing members retained (replay + current fleet).
        for model in ("claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6"):
            self.assertIn(model, overpowered._LARGE_MODELS)

    def test_wasteful_thinking_target_models(self) -> None:
        from detectors import wasteful_thinking
        for model in ("claude-fable-5", "claude-fable-5-1", "claude-opus-5",
                      "claude-opus-5-5"):
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

    # -- PLAN-169 S338 follow-up: Sonnet 5 is $2/$10 on BOTH sides of
    #    2026-09-01; the W2 P2a ts branch of cost_usd is kept alive through
    #    a SYNTHETIC dated row. --

    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:
        p = self.mod._DEFAULT_PRICING
        for ts in ("2026-08-31T12:00:00Z", "2026-09-01T00:00:00Z",
                   "2026-12-31T23:59:59Z"):
            # $2 in + $10 out — never $3 + $15.
            self.assertAlmostEqual(
                self.mod.cost_usd(p, "claude-sonnet-5", 1_000_000, 1_000_000,
                                  ts=ts), 12.00, msg="ts=%s" % ts)
        # No ts -> static row.
        self.assertAlmostEqual(
            self.mod.cost_usd(p, "claude-sonnet-5", 1_000_000, 0), 2.00)
        self.assertNotIn("claude-sonnet-5", self.mod._DATED_PRICING)

    def test_dated_cost_usd_mechanism_synthetic_row(self) -> None:
        """W2 P2a mechanism (ts-aware row selection, cutoff inclusive, no
        mutation) survives the Sonnet 5 row retirement."""
        model = "synthetic-dated-model"
        base = {"input_per_mtok": 2.00, "output_per_mtok": 10.00}
        dated = ("2026-08-31", dict(base),
                 {"input_per_mtok": 3.00, "output_per_mtok": 15.00})
        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \
                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):
            p = self.mod._DEFAULT_PRICING
            self.assertAlmostEqual(
                self.mod.cost_usd(p, model, 1_000_000, 0,
                                  ts="2026-08-31T12:00:00Z"), 2.00)
            self.assertAlmostEqual(
                self.mod.cost_usd(p, model, 1_000_000, 0,
                                  ts="2026-09-01T00:00:00Z"), 3.00)
            self.assertAlmostEqual(self.mod.cost_usd(p, model, 1_000_000, 0), 2.00)
            self.assertEqual(p[model], base,
                             "dated pricing must never repaint the global row")
        self.assertNotIn(model, self.mod._DEFAULT_PRICING)
        self.assertNotIn(model, self.mod._DATED_PRICING)

    def test_custom_override_beats_dated_row_synthetic(self) -> None:
        """CEO_COST_PRICING_JSON custom rows win over built-in dated rows."""
        model = "synthetic-dated-model"
        base = {"input_per_mtok": 2.00, "output_per_mtok": 10.00}
        dated = ("2026-08-31", dict(base),
                 {"input_per_mtok": 3.00, "output_per_mtok": 15.00})
        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \
                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):
            custom = dict(self.mod._DEFAULT_PRICING)
            custom[model] = {"input_per_mtok": 9.00, "output_per_mtok": 9.00}
            self.assertAlmostEqual(
                self.mod.cost_usd(custom, model, 1_000_000, 0,
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
            "claude-fable-5-1": (0.010, 0.050),  # ADR-149 A2 (S338)
            "claude-opus-5-5": (0.004, 0.020),  # ADR-149 A3 (S357)
            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below
        }
        for model, (inp, out) in expected.items():
            row = pricing[model]
            self.assertAlmostEqual(row["in"], inp, msg="%s in" % model)
            self.assertAlmostEqual(row["out"], out, msg="%s out" % model)

    def test_fable51_cache_read_multiplier(self) -> None:
        """ADR-149 A2 (S338): Fable 5.1 cache hits are 0.025x base input
        (pricing page 2026-09-01); every other fleet id keeps 0.10x."""
        self.assertAlmostEqual(
            self.mod._cache_read_multiplier("claude-fable-5-1"), 0.025)
        for model in ("claude-fable-5", "claude-opus-5", "claude-sonnet-5",
                      "some-unknown-model"):
            self.assertAlmostEqual(self.mod._cache_read_multiplier(model), 0.10)

    def test_opus55_cache_read_multiplier(self) -> None:
        """ADR-149 A3 (S357): Opus 5.5 cache hits are 0.05x base input
        ($0.20 on the $4 base — pricing page 2026-09-22), NOT the standard
        0.10x; claude-opus-5 keeps 0.10x (a distinct minor)."""
        self.assertAlmostEqual(
            self.mod._cache_read_multiplier("claude-opus-5-5"), 0.05)
        self.assertAlmostEqual(
            self.mod._cache_read_multiplier("claude-opus-5"), 0.10)
        text = self.mod._cache_read_exceptions_text()
        self.assertIn("0.05x on claude-opus-5-5", text)
        self.assertIn("0.025x on claude-fable-5-1", text)

    def test_native_spawn_opus55_one_m_tag_priced_with_its_cache_rate(self) -> None:
        """ADR-149 A3 (S357): a session that selected the 1M variant
        reports the id WITH the ``[1m]`` tag (``claude-opus-5-5[1m]``,
        observed S357 on Claude Code 2.1.280); a bare
        ``opus`` meta alias is ambiguous, so the transcript model decides —
        and the spawn is priced at $4 input + 0.05x cache reads."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            tr = Path(td) / "agent-y.jsonl"
            tr.write_text(
                '{"timestamp": "2026-09-22T00:00:00Z", "message": '
                '{"model": "claude-opus-5-5[1m]", "usage": {"input_tokens": 1000000, '
                '"output_tokens": 0, "cache_read_input_tokens": 1000000}}}\n',
                encoding="utf-8",
            )
            (Path(td) / "agent-y.meta.json").write_text(
                '{"agentType": "t", "spawnDepth": 1, "model": "opus"}',
                encoding="utf-8",
            )
            rec = self.mod._read_native_spawn(tr, "native", "sess")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["model_id"], "claude-opus-5-5")
        self.assertFalse(rec["cost_tbd"])
        # 1M fresh input at $4 + 1M cache reads at 0.05x ($0.20) == $4.20
        self.assertAlmostEqual(rec["cost_usd"], 4.20, places=6)

    def test_bare_fable_alias_is_ambiguous_and_versioned_alias_resolves(self) -> None:
        """ADR-149 A2 (S338, codex r2 P2): with two Fable ids in the
        registry the bare family alias resolves to NOTHING (never guess a
        version); the versioned aliases and exact ids still resolve."""
        self.assertIsNone(self.mod._normalize_model_id("fable"))
        self.assertEqual(self.mod._normalize_model_id("fable-5-1"), "claude-fable-5-1")
        self.assertEqual(self.mod._normalize_model_id("fable-5"), "claude-fable-5")
        self.assertEqual(self.mod._normalize_model_id("claude-fable-5-1[1m]"),
                         "claude-fable-5-1")

    def test_native_spawn_ambiguous_meta_alias_falls_back_to_transcript(self) -> None:
        """ADR-149 A2 (S338, codex r2 P2): meta.model="fable" (measured in
        native metas) must not turn the spawn into cost TBD when the
        transcript names the exact model."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            tr = Path(td) / "agent-x.jsonl"
            tr.write_text(
                '{"timestamp": "2026-09-01T00:00:00Z", "message": '
                '{"model": "claude-fable-5-1", "usage": {"input_tokens": 1000000, '
                '"output_tokens": 0, "cache_read_input_tokens": 1000000}}}\n',
                encoding="utf-8",
            )
            (Path(td) / "agent-x.meta.json").write_text(
                '{"agentType": "t", "spawnDepth": 1, "model": "fable"}',
                encoding="utf-8",
            )
            rec = self.mod._read_native_spawn(tr, "native", "sess")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["model_id"], "claude-fable-5-1")
        self.assertFalse(rec["cost_tbd"])
        # 1M fresh input at $10 + 1M cache reads at 0.025x ($0.25) == $10.25
        self.assertAlmostEqual(rec["cost_usd"], 10.25, places=6)

    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:
        """PLAN-169 S338 follow-up: $2/$10 per MTok (0.002/0.010 per 1k) on
        both sides of 2026-09-01 — the intro price became the standard price
        and the dated $3/$15 flip row was retired."""
        for ts in ("2026-08-31T12:00:00Z", "2026-09-01T00:00:00Z",
                   "2026-12-31T23:59:59Z"):
            # 1k in + 1k out = 0.002 + 0.010 — never 0.003 + 0.015.
            self.assertAlmostEqual(
                self.mod.compute_cost_usd("claude-sonnet-5", 1000, 1000, ts=ts),
                0.012, msg="ts=%s" % ts)
        # No ts -> static row.
        self.assertAlmostEqual(
            self.mod.compute_cost_usd("claude-sonnet-5", 1000, 0), 0.002)
        self.assertNotIn("claude-sonnet-5", self.mod._DATED_PRICING)

    def test_dated_compute_cost_mechanism_synthetic_row(self) -> None:
        """W2 P2a mechanism (ts-aware row selection, cutoff inclusive, no
        mutation, lower-cased key) survives the Sonnet 5 row retirement."""
        model = "synthetic-dated-model"
        base = {"in": 0.002, "out": 0.010}
        dated = ("2026-08-31", dict(base), {"in": 0.003, "out": 0.015})
        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \
                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):
            self.assertAlmostEqual(
                self.mod.compute_cost_usd(model, 1000, 0,
                                          ts="2026-08-31T12:00:00Z"), 0.002)
            self.assertAlmostEqual(
                self.mod.compute_cost_usd(model.upper(), 1000, 1000,
                                          ts="2026-09-01T00:00:00Z"), 0.018)
            self.assertAlmostEqual(self.mod.compute_cost_usd(model, 1000, 0), 0.002)
            self.assertEqual(self.mod._DEFAULT_PRICING[model], base,
                             "dated pricing must never repaint the global row")
        self.assertNotIn(model, self.mod._DEFAULT_PRICING)
        self.assertNotIn(model, self.mod._DATED_PRICING)

    def test_historical_ids_retained(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in ("claude-opus-4-7", "claude-opus-4", "claude-sonnet-4",
                      "claude-haiku-4"):
            self.assertIn(
                model, pricing,
                "%s dropped — historical rows must be retained (ADR-142)"
                % model,
            )


class TestSuccessReceiptFleetPresence(TestEnvContext):
    """`_DEFAULT_PRICING` (success-receipt.py) knows the current fleet.

    ADR-149 Amendment 2 (S338, codex rail r3 P1): this mirror had no gen-5
    row at all, so a MIXED session (one known model + fable-5-1 events)
    emitted a numeric `default-pricing-table` total that silently dropped
    every Fable 5.1 token. The presence guard binds it to the fleet.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = _load_hyphenated("success_receipt_fleet", "success-receipt.py")

    def test_new_fleet_present(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in _NEW_FLEET:
            self.assertIn(
                model, pricing,
                "%s missing from success-receipt _DEFAULT_PRICING "
                "(ADR-149 A2 / rail r3 P1 presence fix)" % model,
            )

    def test_per_1k_rates_mirror_budget_summary(self) -> None:
        bs = _load_hyphenated("budget_summary_for_receipt", "budget-summary.py")
        for model in _NEW_FLEET:
            row = self.mod._DEFAULT_PRICING[model]
            ref = bs._DEFAULT_PRICING[model]
            self.assertAlmostEqual(row["in"], ref["in"], msg="%s in" % model)
            self.assertAlmostEqual(row["out"], ref["out"], msg="%s out" % model)

    def test_historical_rows_retained(self) -> None:
        pricing = self.mod._DEFAULT_PRICING
        for model in ("claude-opus-4-7", "claude-opus-4", "claude-sonnet-4-5",
                      "claude-sonnet-4", "claude-haiku-4"):
            self.assertIn(model, pricing, "%s dropped (ADR-142 replay)" % model)

    def test_mixed_session_receipt_counts_fable51_spend(self) -> None:
        """The r3 finding, as a receipt: 1M Fable 5.1 input == $10.00 must be
        IN the total, not silently dropped behind a known sonnet event."""
        events = [
            {"action": "agent_spawn", "model": "claude-sonnet-4-5",
             "tokens_in": 1000, "tokens_out": 0},
            {"action": "agent_spawn", "model": "claude-fable-5-1",
             "tokens_in": 1_000_000, "tokens_out": 0},
        ]
        section = self.mod.build_value_created(events)
        self.assertEqual(section["cost_source"], "default-pricing-table")
        # sonnet-4-5 1k in @0.003 + fable-5-1 1M in @0.010/1k == 0.003 + 10.0
        self.assertAlmostEqual(section["cost_usd"], 10.003, places=4)


class TestWorkingSetPricedOnEverySurface(TestEnvContext):
    """ADR-149 Amendment 3 (S357) — the CLASS cure for "a new model id
    prices at $0 / TBD on some rollup surface".

    A recurring class (PLAN-163 T1.5, PLAN-169 W2.10 F3, the Fable 5.1
    codex rail r3 P1), and Opus 5.5 needed the same hand edits again: the
    hand-kept ``_NEW_FLEET`` tuple only guards the ids someone remembered
    to add. Here the fleet is READ from the signed
    authority — ADR-149 ``AVAILABLE_MODELS_WORKING_SET``, through the same
    parser the model-currency gate uses — so the NEXT working-set append
    fails this test until every rollup surface prices it at the
    cost-table.yaml rate.
    """

    #: (script, table attribute, input key, output key, factor to per-MTok)
    _SURFACES = (
        ("audit-telemetry.py", "_PRICING_PER_MTOK", "input", "output", 1.0),
        ("ceo-cost.py", "_DEFAULT_PRICING", "input_per_mtok", "output_per_mtok", 1.0),
        ("budget-summary.py", "_DEFAULT_PRICING", "in", "out", 1000.0),
        ("success-receipt.py", "_DEFAULT_PRICING", "in", "out", 1000.0),
        ("value-dashboard.py", "_DEFAULT_PRICING", "in", "out", 1000.0),
        ("ceo-cost-transcripts.py", "_EMBEDDED_PRICING", "input_per_mtok",
         "output_per_mtok", 1.0),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        currency = _load_registered(
            "fleet_ws_currency", "check-model-currency.py")
        cls.working_set = list(
            currency.read_adr_blocks(_ADR_149)["AVAILABLE_MODELS_WORKING_SET"])
        cls.cct = _load_registered(
            "fleet_ws_transcripts", "ceo-cost-transcripts.py")
        cls.cost_table = cls.cct._parse_cost_table_yaml(
            _COST_TABLE.read_text(encoding="utf-8"))
        cls.tables = {}
        for idx, (script, attr, k_in, k_out, factor) in enumerate(cls._SURFACES):
            if script == "ceo-cost-transcripts.py":
                mod = cls.cct
            else:
                mod = _load_registered("fleet_ws_surface_%d" % idx, script)
            cls.tables[script] = (getattr(mod, attr), k_in, k_out, factor)

    def test_working_set_read_from_the_adr(self) -> None:
        """Non-vacuity: the fleet came from the ADR, and this pack's id is
        in it (the ADR append and these price rows land together)."""
        self.assertGreaterEqual(len(self.working_set), 8)
        self.assertIn("claude-opus-5-5", self.working_set)

    def test_every_working_set_id_priced_on_every_surface(self) -> None:
        for model in self.working_set:
            ref = self.cost_table.get(model)
            self.assertIsNotNone(ref, "%s has no cost-table.yaml row" % model)
            for script, (table, k_in, k_out, factor) in self.tables.items():
                with self.subTest(model=model, surface=script):
                    row = table.get(model)
                    self.assertIsNotNone(
                        row, "%s missing from %s — prices at $0/TBD" % (model, script))
                    self.assertAlmostEqual(
                        row[k_in] * factor, ref["input_per_mtok"], places=6,
                        msg="%s input rate on %s" % (model, script))
                    self.assertAlmostEqual(
                        row[k_out] * factor, ref["output_per_mtok"], places=6,
                        msg="%s output rate on %s" % (model, script))


class TestCacheReadMultiplierMirror(TestEnvContext):
    """ADR-149 Amendment 3 (S357): the per-model cache-read rate is now a
    CLASS (Fable 5.1 0.025x, then Opus 5.5 0.05x) that lives in TWO scripts.
    ceo-cost-transcripts.py declares it "mirrors budget-summary.py's
    _CACHE_READ_MULTIPLIER_OVERRIDES exactly" — this makes that mechanical.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bs = _load_hyphenated("budget_summary_cache_mirror", "budget-summary.py")
        cls.cct = _load_registered(
            "transcripts_cache_mirror", "ceo-cost-transcripts.py")

    def test_transcripts_mirror_budget_summary_exactly(self) -> None:
        self.assertEqual(self.cct._CACHE_READ_MULTIPLIER_OVERRIDES,
                         self.bs._CACHE_READ_MULTIPLIER_OVERRIDES)
        self.assertEqual(self.cct._CACHE_READ_MULTIPLIER_DEFAULT,
                         self.bs._CACHE_READ_MULTIPLIER_DEFAULT)

    def test_opus55_is_005_on_both(self) -> None:
        for mod in (self.bs, self.cct):
            self.assertAlmostEqual(mod._cache_read_multiplier("claude-opus-5-5"), 0.05)
            self.assertAlmostEqual(mod._cache_read_multiplier("claude-opus-5"), 0.10)

    def test_every_override_is_a_priced_id(self) -> None:
        for model in self.bs._CACHE_READ_MULTIPLIER_OVERRIDES:
            self.assertIn(model, self.bs._DEFAULT_PRICING)
            self.assertIn(model, self.cct._EMBEDDED_PRICING)


class TestCostTableFleetPresence(TestEnvContext):
    """cost-table.yaml carries the NEW ids (opus-5 + fast row).

    fable-5 / opus-4-8 / sonnet-5 rows already existed there pre-PLAN-163
    (fable-5 / opus-4-8 rates asserted by test_a4_pricing_doctrine.py); the
    ids new to this plan are asserted here, plus the sonnet-5 RATE since the
    PLAN-169 S338 follow-up (the $3/$15 sticker became $2/$10).
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

    def test_fable51_row(self) -> None:
        """ADR-149 Amendment 2 (S338): Fable 5.1 priced at the Fable 5 rate."""
        text = self._block("claude-fable-5-1")
        self.assertIn("input_per_mtok: 10.00", text)
        self.assertIn("output_per_mtok: 50.00", text)

    def test_opus55_row(self) -> None:
        """ADR-149 Amendment 3 (S357): Opus 5.5 at $4/$20 — and NO fast
        row: ``claude-opus-5-5-fast`` is outside the signed working set, so
        check-model-currency.py would report it as a new red."""
        text = self._block("claude-opus-5-5")
        self.assertIn("input_per_mtok: 4.00", text)
        self.assertIn("output_per_mtok: 20.00", text)
        self.assertIsNone(
            re.search(r"^  claude-opus-5-5-fast:", self.cost_table, re.MULTILINE))

    def test_opus48_fast_row(self) -> None:
        """W2 P2b: 4-8-fast is a live replacement id and must be priced."""
        text = self._block("claude-opus-4-8-fast")
        self.assertIn("input_per_mtok: 10.00", text)
        self.assertIn("output_per_mtok: 50.00", text)

    def test_sonnet5_row_standard_rate(self) -> None:
        """PLAN-169 S338 follow-up: the estimator sticker is $2/$10 — the
        launch intro price became the standard price (pricing page fetched
        2026-09-01; the 2026-09-01 increase to $3/$15 will not occur). The
        ADR-157 'sticker $3/$15' note is superseded."""
        text = self._block("claude-sonnet-5")
        self.assertIn("input_per_mtok: 2.00", text)
        self.assertIn("output_per_mtok: 10.00", text)
        self.assertNotIn("input_per_mtok: 3.00", text)
        self.assertNotIn("output_per_mtok: 15.00", text)

    def test_historical_rows_retained(self) -> None:
        for model in ("claude-opus-4-7", "claude-opus-4-7-1m",
                      "claude-fable-5", "claude-opus-4-8",
                      "claude-sonnet-4-6", "claude-sonnet-5",
                      "claude-haiku-4-5"):
            self._block(model)


if __name__ == "__main__":
    unittest.main()
