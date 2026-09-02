#!/usr/bin/env python3
"""apply-sonnet5-pricing-fu.py — derivation of the `sonnet5-pricing-fu` pack (PLAN-169, S338).

FACT (official pricing page, platform.claude.com/docs/en/about-claude/pricing,
fetched 2026-09-01): "The $2/$10 per million input/output token pricing for
Claude Sonnet 5, announced at launch as introductory pricing through
August 31, 2026, is now the standard price. The previously scheduled increase
to $3/$15 per million input/output tokens on September 1, 2026 will not
occur." Cache multipliers for Sonnet 5 are unchanged (0.1x read, 1.25x/2x
write).

The repo modelled the (now cancelled) 2026-09-01 flip to $3/$15 on FREE
surfaces: three `_DATED_PRICING*` tables (audit-telemetry.py, ceo-cost.py,
budget-summary.py), the cost-table.yaml sticker (3.00/15.00), a comment block
in value-dashboard.py, one table row in docs/cost-of-operation.md, one table
row in docs/CEO-MODEL-ROUTING.md, the dated-flip tests in
test_model_fleet_presence.py, and (codex rail r2 P2) the `_MM_TIERS` reconcile
tier table in build-canonical-models.py, whose generic sonnet tier resolved
`claude-sonnet-5` at $3/$15. From 2026-09-01 every one of them OVERSTATES
Sonnet 5 by 50 %. This script applies the cure over a tree at
HEAD + wave-fable51 (the fable51 patch touches the same files; every anchor
below matches the POST-fable51 content), with an EXACT anchor per edit and a
declared occurrence count — a missing, ambiguous or already-applied anchor is
a NAMED refusal before anything is written, never a best effort.

Design (see DESIGN-SONNET5-FU-S338.md):
  * the dated-pricing MECHANISM stays (``_rates_for_event`` / ``cost_usd`` /
    ``compute_cost_usd`` ts branches are infrastructure); only the Sonnet 5
    ROW is removed — with both legs equal to the base row it was dead data;
    the mechanism is kept under test through a SYNTHETIC dated row;
  * additive/minimal: every number is sourced in-comment (pricing page +
    fetch date); historical replay rows are untouched (ADR-142); dated
    records (docs/substrate-adopt-2026-08.md, ADR-157) are NOT rewritten.

Usage:
    python3 apply-sonnet5-pricing-fu.py --root <tree at HEAD+fable51>
    python3 apply-sonnet5-pricing-fu.py --root <tree> --check-only   (anchors only)
    python3 apply-sonnet5-pricing-fu.py --root <tree> --list-paths
    python3 apply-sonnet5-pricing-fu.py --root <tree> --only <rel-path> [--only ...]
        (positive control: apply only the edits of the named path(s) — e.g. the
        rewritten tests against the UNCURED sources must be RED)

Exit codes: 0 = applied (or applicable with --check-only); 1 = named refusal;
2 = usage error. Stdlib-only, Python >= 3.9, no runtime PEP 604.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

#: Every replacement carries this marker; its presence in ANY touched path
#: means the tree is already patched (double application would be refused by
#: the anchor counts anyway — this names the cause).
MARKER = "PLAN-169 S338 follow-up"

AUDIT = ".claude/scripts/audit-telemetry.py"
CEO_COST = ".claude/scripts/ceo-cost.py"
BUDGET = ".claude/scripts/budget-summary.py"
VALUE = ".claude/scripts/value-dashboard.py"
COST_TABLE = ".claude/scripts/cost-table.yaml"
COST_DOC = "docs/cost-of-operation.md"
ROUTING_DOC = "docs/CEO-MODEL-ROUTING.md"
FLEET_TEST = ".claude/scripts/tests/test_model_fleet_presence.py"
# codex rail r2 P2 (REAL, latent): the reconcile tier table still resolved
# sonnet-5 through the generic $3/$15 sonnet tier.
BUILD_CM = ".claude/scripts/build-canonical-models.py"
BUILD_CM_TEST = ".claude/scripts/tests/test_build_canonical_models.py"

# --------------------------------------------------------------------------
# (path, EXACT anchor, replacement, expected occurrences)
# Order is application order; every anchor is counted BEFORE any write.
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ---------------- audit-telemetry.py ----------------
    (
        AUDIT,
        "    # Sonnet 5: INTRO pricing through 2026-08-31 — the dated row in\n"
        "    # _DATED_PRICING_PER_MTOK carries the post-intro sticker; this base row\n"
        "    # is the fallback for events with no parseable ts (W2 P2a).\n"
        "    \"claude-sonnet-5\": {\"input\": 2.00, \"output\": 10.00},\n",
        "    # Sonnet 5: $2/$10 is the STANDARD rate. The launch-time intro price\n"
        "    # became permanent — the official pricing page (fetched 2026-09-01,\n"
        "    # platform.claude.com/docs/en/about-claude/pricing) states the scheduled\n"
        "    # 2026-09-01 increase to $3/$15 \"will not occur\". The dated flip row this\n"
        "    # comment used to point at was retired (PLAN-169 S338 follow-up).\n"
        "    \"claude-sonnet-5\": {\"input\": 2.00, \"output\": 10.00},\n",
        1,
    ),
    (
        AUDIT,
        "#: PLAN-163 W2 P2a — event-date-aware rows: models whose public rate changes\n"
        "#: on a date boundary. An event is priced by its OWN ``ts`` (never by\n"
        "#: \"today\", and never by mutating the global row — mutation would repaint\n"
        "#: history on replay). Shape: model -> (cutoff_iso_date,\n"
        "#: rates_through_cutoff_inclusive, rates_after). Sonnet 5: $2/$10 intro\n"
        "#: through 2026-08-31, $3/$15 sticker after.\n"
        "_DATED_PRICING_PER_MTOK: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {\n"
        "    \"claude-sonnet-5\": (\n"
        "        \"2026-08-31\",\n"
        "        {\"input\": 2.00, \"output\": 10.00},\n"
        "        {\"input\": 3.00, \"output\": 15.00},\n"
        "    ),\n"
        "}\n",
        "#: PLAN-163 W2 P2a — event-date-aware rows: models whose public rate changes\n"
        "#: on a date boundary. An event is priced by its OWN ``ts`` (never by\n"
        "#: \"today\", and never by mutating the global row — mutation would repaint\n"
        "#: history on replay). Shape: model -> (cutoff_iso_date,\n"
        "#: rates_through_cutoff_inclusive, rates_after).\n"
        "#: EMPTY since the PLAN-169 S338 follow-up: the only row ever carried here\n"
        "#: (Sonnet 5 — $2/$10 intro through 2026-08-31, then $3/$15) was retired\n"
        "#: when the official pricing page (fetched 2026-09-01) made $2/$10 the\n"
        "#: standard price and cancelled the 2026-09-01 increase — both legs equal\n"
        "#: the base row, so the row was dead data. The MECHANISM\n"
        "#: (``_rates_for_event``) stays and is exercised through a synthetic row in\n"
        "#: test_model_fleet_presence.py.\n"
        "_DATED_PRICING_PER_MTOK: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {}\n",
        1,
    ),
    # ---------------- ceo-cost.py ----------------
    (
        CEO_COST,
        "# premium row; sonnet-5 at the $2/$10 INTRO rate through 2026-08-31 (post-intro\n"
        "# sticker $3/$15 — bump the row when the intro window lapses; this table prices\n"
        "# actual logged spend, unlike the forward-looking cost-table.yaml sticker).\n",
        "# premium row; sonnet-5 $2/$10 — the launch intro price became the STANDARD\n"
        "# price (official pricing page fetched 2026-09-01: the scheduled 2026-09-01\n"
        "# increase to $3/$15 \"will not occur\"; PLAN-169 S338 follow-up), so no bump\n"
        "# is due and cost-table.yaml now carries the same $2/$10.\n",
        1,
    ),
    (
        CEO_COST,
        "#: PLAN-163 W2 P2a — event-date-aware rows (see audit-telemetry.py twin):\n"
        "#: an event is priced by its OWN ``ts``, never by \"today\" and never by\n"
        "#: mutating the global row. Sonnet 5: $2/$10 intro through 2026-08-31\n"
        "#: (inclusive), $3/$15 sticker after.\n"
        "_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {\n"
        "    \"claude-sonnet-5\": (\n"
        "        \"2026-08-31\",\n"
        "        {\"input_per_mtok\": 2.00, \"output_per_mtok\": 10.00},\n"
        "        {\"input_per_mtok\": 3.00, \"output_per_mtok\": 15.00},\n"
        "    ),\n"
        "}\n",
        "#: PLAN-163 W2 P2a — event-date-aware rows (see audit-telemetry.py twin):\n"
        "#: an event is priced by its OWN ``ts``, never by \"today\" and never by\n"
        "#: mutating the global row. Shape: model -> (cutoff_iso_date,\n"
        "#: row_through_cutoff_inclusive, row_after).\n"
        "#: EMPTY since the PLAN-169 S338 follow-up: the Sonnet 5 row ($2/$10 intro\n"
        "#: through 2026-08-31, then $3/$15) was retired when the official pricing\n"
        "#: page (fetched 2026-09-01) made $2/$10 the standard price and cancelled\n"
        "#: the 2026-09-01 increase — both legs equal the base row. The MECHANISM\n"
        "#: (the ``ts`` branch of ``cost_usd``) stays; test_model_fleet_presence.py\n"
        "#: exercises it through a synthetic row.\n"
        "_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {}\n",
        1,
    ),
    # ---------------- budget-summary.py ----------------
    (
        BUDGET,
        "#: opus-5-fast $10/$50 premium row; sonnet-5 $2/$10 INTRO rate through\n"
        "#: 2026-08-31 (post-intro sticker $3/$15 — bump when the window lapses).\n",
        "#: opus-5-fast $10/$50 premium row; sonnet-5 $2/$10 — the launch intro price\n"
        "#: became the STANDARD price (official pricing page fetched 2026-09-01: the\n"
        "#: scheduled 2026-09-01 increase to $3/$15 \"will not occur\"; PLAN-169 S338\n"
        "#: follow-up).\n",
        1,
    ),
    (
        BUDGET,
        "#: PLAN-163 W2 P2a — event-date-aware rows (per-1k twin of the tables in\n"
        "#: audit-telemetry.py / ceo-cost.py): an event is priced by its OWN ``ts``,\n"
        "#: never by \"today\" and never by mutating the global row. Sonnet 5: $2/$10\n"
        "#: per MTok intro through 2026-08-31 (inclusive), $3/$15 sticker after.\n"
        "_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {\n"
        "    \"claude-sonnet-5\": (\n"
        "        \"2026-08-31\",\n"
        "        {\"in\": 0.002, \"out\": 0.010},\n"
        "        {\"in\": 0.003, \"out\": 0.015},\n"
        "    ),\n"
        "}\n",
        "#: PLAN-163 W2 P2a — event-date-aware rows (per-1k twin of the tables in\n"
        "#: audit-telemetry.py / ceo-cost.py): an event is priced by its OWN ``ts``,\n"
        "#: never by \"today\" and never by mutating the global row. Shape: model ->\n"
        "#: (cutoff_iso_date, row_through_cutoff_inclusive, row_after).\n"
        "#: EMPTY since the PLAN-169 S338 follow-up: the Sonnet 5 row ($2/$10 per\n"
        "#: MTok intro through 2026-08-31, then $3/$15) was retired when the official\n"
        "#: pricing page (fetched 2026-09-01) made $2/$10 the standard price and\n"
        "#: cancelled the 2026-09-01 increase — both legs equal the base row. The\n"
        "#: MECHANISM (the ``ts`` branch of ``compute_cost_usd``) stays;\n"
        "#: test_model_fleet_presence.py exercises it through a synthetic row.\n"
        "_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {}\n",
        1,
    ),
    # ---------------- value-dashboard.py ----------------
    (
        VALUE,
        "    # ceo-cost.py (per-MTok) converted to per-1k. Sonnet 5 uses the intro\n"
        "    # rate ($2/$10 until 2026-08-31; sticker $3/$15) — same as the mirror.\n",
        "    # ceo-cost.py (per-MTok) converted to per-1k. Sonnet 5 at $2/$10 — the\n"
        "    # standard rate since the intro price became permanent (NOTE below).\n",
        1,
    ),
    (
        VALUE,
        "    # NOTE (repass-r2 part-c P2): this is the INTRO rate, valid until\n"
        "    # 2026-08-31 (sticker $3/$15). compute_cost_usd has no event-date\n"
        "    # selection, so after that date this row UNDERSTATES sonnet-5 cost\n"
        "    # until swept — same semantics as the ceo-cost.py mirror; sweep both.\n"
        "    \"claude-sonnet-5\":             {\"in\": 0.002, \"out\": 0.010},\n",
        "    # NOTE (repass-r2 part-c P2, superseded by the PLAN-169 S338 follow-up):\n"
        "    # $2/$10 was the INTRO rate through 2026-08-31 with a $3/$15 sticker\n"
        "    # after; the official pricing page (fetched 2026-09-01) made $2/$10 the\n"
        "    # STANDARD price — the scheduled 2026-09-01 increase \"will not occur\".\n"
        "    # No event-date selection is needed here any more: this row is exact on\n"
        "    # both sides of 2026-09-01, same as the ceo-cost.py mirror.\n"
        "    \"claude-sonnet-5\":             {\"in\": 0.002, \"out\": 0.010},\n",
        1,
    ),
    # ---------------- cost-table.yaml ----------------
    (
        COST_TABLE,
        "  claude-sonnet-5:\n"
        "    input_per_mtok: 3.00\n"
        "    output_per_mtok: 15.00\n"
        "    tier: sonnet\n"
        "    source_url: \"https://docs.anthropic.com/en/docs/about-claude/pricing\"  # ADR-157: sticker rate; intro $2/$10 through 2026-08-31 not modeled (estimator uses standard); tokenizer +30% tokens vs 4.6\n",
        "  claude-sonnet-5:\n"
        "    input_per_mtok: 2.00\n"
        "    output_per_mtok: 10.00\n"
        "    tier: sonnet\n"
        "    source_url: \"https://platform.claude.com/docs/en/about-claude/pricing\"  # PLAN-169 S338 follow-up (fetched 2026-09-01): the $2/$10 launch intro price is now the STANDARD price — the scheduled 2026-09-01 increase to $3/$15 will not occur; supersedes the ADR-157 sticker note ($3/$15 sticker, intro not modeled); tokenizer +30% tokens vs 4.6\n",
        1,
    ),
    # ---------------- docs/cost-of-operation.md ----------------
    (
        COST_DOC,
        "| `claude-sonnet-5` (current; intro $2/$10 until 2026-08-31, sticker $3/$15) | $2.00 | $10.00 | 0.4× |\n",
        "| `claude-sonnet-5` (current; $2/$10 is the standard rate — the launch intro price became permanent, pricing page fetched 2026-09-01) | $2.00 | $10.00 | 0.4× |\n",
        1,
    ),
    (
        COST_DOC,
        "Gen-5 rows added 2026-08-09 (PLAN-169 W2.10 D7, mirroring `ceo-cost.py`).\n",
        "Gen-5 rows added 2026-08-09 (PLAN-169 W2.10 D7, mirroring `ceo-cost.py`).\n"
        "Sonnet 5 row re-verified 2026-09-01 (PLAN-169 S338 follow-up): the official pricing page (https://platform.claude.com/docs/en/about-claude/pricing) states the $2/$10 launch intro price is now the standard price and the previously scheduled 2026-09-01 increase to $3/$15 will not occur — the dated $3/$15 flip was retired from every rollup surface (`audit-telemetry.py`, `ceo-cost.py`, `budget-summary.py`) and from the `cost-table.yaml` sticker.\n",
        1,
    ),
    # ---------------- docs/CEO-MODEL-ROUTING.md ----------------
    (
        ROUTING_DOC,
        "| Advisory tier (qa / perf / non-VETO staff, `code_gen`/`finops`) | `claude-sonnet-5` | OQ2 = migrate now; intro pricing $2/$10 through 2026-08-31 (then $3/$15); tokenizer ~+30% tokens",
        "| Advisory tier (qa / perf / non-VETO staff, `code_gen`/`finops`) | `claude-sonnet-5` | OQ2 = migrate now; $2/$10 per MTok is the STANDARD price — the launch intro rate became permanent and the scheduled 2026-09-01 increase to $3/$15 will not occur (pricing page fetched 2026-09-01, PLAN-169 S338 follow-up; `docs/substrate-adopt-2026-08.md` is a DATED adoption record — its G2 row still shows the pre-cancellation $3/$15 flip and is superseded by this row); tokenizer ~+30% tokens",
        1,
    ),
    # ---------------- test_model_fleet_presence.py ----------------
    (
        FLEET_TEST,
        "  - claude-sonnet-5       $2 / $10   intro through 2026-08-31, then $3/$15 —\n"
        "                          EVENT-DATE-AWARE on the replay/rollup surfaces\n"
        "                          (W2 P2a: each event is priced by its OWN ts via the\n"
        "                          _DATED_PRICING tables; the global row is never\n"
        "                          mutated). cost-table.yaml deliberately keeps the\n"
        "                          $3/$15 sticker per its ADR-157 comment (forward\n"
        "                          estimator, intro not modeled) — NOT asserted here.\n",
        "  - claude-sonnet-5       $2 / $10   STANDARD rate on BOTH sides of 2026-09-01\n"
        "                          (PLAN-169 S338 follow-up): the launch intro price\n"
        "                          became permanent — the official pricing page\n"
        "                          (fetched 2026-09-01) states the scheduled 2026-09-01\n"
        "                          increase to $3/$15 \"will not occur\". The dated\n"
        "                          $3/$15 flip row was retired from the three\n"
        "                          _DATED_PRICING tables (both legs equalled the base\n"
        "                          row = dead data); the event-date MECHANISM (W2 P2a:\n"
        "                          each event priced by its OWN ts, the global row\n"
        "                          never mutated) stays and is asserted below through\n"
        "                          a SYNTHETIC dated row. cost-table.yaml now carries\n"
        "                          $2/$10 too (the ADR-157 sticker note is superseded)\n"
        "                          — asserted below.\n",
        1,
    ),
    (
        FLEET_TEST,
        "import unittest\n"
        "from pathlib import Path\n",
        "import unittest\n"
        "from pathlib import Path\n"
        "from unittest import mock\n",
        1,
    ),
    (
        FLEET_TEST,
        "    # -- W2 P2a: Sonnet 5 pricing is event-date-aware, never global-mutated --\n"
        "\n"
        "    def test_sonnet5_intro_rate_before_cutoff(self) -> None:\n"
        "        cost = self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 0, \"ts\": \"2026-08-01T00:00:00Z\"}\n"
        "        )\n"
        "        self.assertAlmostEqual(cost, 2.00)\n"
        "\n"
        "    def test_sonnet5_cutoff_day_is_inclusive(self) -> None:\n"
        "        cost = self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 0, \"ts\": \"2026-08-31T23:59:59Z\"}\n"
        "        )\n"
        "        self.assertAlmostEqual(cost, 2.00)\n"
        "\n"
        "    def test_sonnet5_sticker_rate_after_cutoff(self) -> None:\n"
        "        cost = self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 1_000_000, \"ts\": \"2026-09-01T00:00:00Z\"}\n"
        "        )\n"
        "        self.assertAlmostEqual(cost, 18.00)  # $3 in + $15 out\n"
        "\n"
        "    def test_sonnet5_missing_ts_falls_back_to_base_row(self) -> None:\n"
        "        cost = self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 0}\n"
        "        )\n"
        "        self.assertAlmostEqual(cost, 2.00)\n"
        "\n"
        "    def test_dated_lookup_does_not_mutate_global_row(self) -> None:\n"
        "        before = dict(self.mod._PRICING_PER_MTOK[\"claude-sonnet-5\"])\n"
        "        self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 0, \"ts\": \"2026-09-01T00:00:00Z\"}\n"
        "        )\n"
        "        self.assertEqual(\n"
        "            self.mod._PRICING_PER_MTOK[\"claude-sonnet-5\"], before,\n"
        "            \"dated pricing must never repaint the global row (P2a)\",\n"
        "        )\n",
        "    # -- PLAN-169 S338 follow-up: Sonnet 5 is $2/$10 on BOTH sides of\n"
        "    #    2026-09-01 (the intro price became the standard price; the dated\n"
        "    #    $3/$15 flip row was retired). The W2 P2a event-date MECHANISM is\n"
        "    #    kept alive below through a SYNTHETIC dated row. --\n"
        "\n"
        "    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:\n"
        "        for ts in (\"2026-08-01T00:00:00Z\", \"2026-08-31T23:59:59Z\",\n"
        "                   \"2026-09-01T00:00:00Z\", \"2026-12-31T23:59:59Z\"):\n"
        "            cost = self.mod._compute_event_cost_usd(\n"
        "                {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "                 \"tokens_out\": 1_000_000, \"ts\": ts}\n"
        "            )\n"
        "            # $2 in + $10 out — never $3 + $15.\n"
        "            self.assertAlmostEqual(cost, 12.00, msg=\"ts=%s\" % ts)\n"
        "\n"
        "    def test_sonnet5_missing_ts_uses_base_row(self) -> None:\n"
        "        cost = self.mod._compute_event_cost_usd(\n"
        "            {\"model\": \"claude-sonnet-5\", \"tokens_in\": 1_000_000,\n"
        "             \"tokens_out\": 0}\n"
        "        )\n"
        "        self.assertAlmostEqual(cost, 2.00)\n"
        "\n"
        "    def test_sonnet5_has_no_dated_row(self) -> None:\n"
        "        \"\"\"The $3/$15 flip row is dead data since 2026-09-01 — retired.\"\"\"\n"
        "        self.assertNotIn(\"claude-sonnet-5\", self.mod._DATED_PRICING_PER_MTOK)\n"
        "\n"
        "    def test_dated_pricing_mechanism_synthetic_row(self) -> None:\n"
        "        \"\"\"W2 P2a mechanism survives the row retirement: a synthetic dated\n"
        "        row prices by the event's OWN ts (cutoff inclusive), a missing ts\n"
        "        falls back to the base row, and the global row is never mutated.\"\"\"\n"
        "        model = \"synthetic-dated-model\"\n"
        "        base = {\"input\": 2.00, \"output\": 10.00}\n"
        "        dated = (\"2026-08-31\", {\"input\": 2.00, \"output\": 10.00},\n"
        "                 {\"input\": 3.00, \"output\": 15.00})\n"
        "        with mock.patch.dict(self.mod._PRICING_PER_MTOK, {model: base}), \\\n"
        "                mock.patch.dict(self.mod._DATED_PRICING_PER_MTOK, {model: dated}):\n"
        "            ev = {\"model\": model, \"tokens_in\": 1_000_000, \"tokens_out\": 1_000_000}\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod._compute_event_cost_usd(dict(ev, ts=\"2026-08-31T23:59:59Z\")),\n"
        "                12.00)\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod._compute_event_cost_usd(dict(ev, ts=\"2026-09-01T00:00:00Z\")),\n"
        "                18.00)\n"
        "            self.assertAlmostEqual(self.mod._compute_event_cost_usd(ev), 12.00)\n"
        "            self.assertEqual(\n"
        "                self.mod._PRICING_PER_MTOK[model], base,\n"
        "                \"dated pricing must never repaint the global row (P2a)\",\n"
        "            )\n"
        "        self.assertNotIn(model, self.mod._PRICING_PER_MTOK)\n"
        "        self.assertNotIn(model, self.mod._DATED_PRICING_PER_MTOK)\n",
        1,
    ),
    (
        FLEET_TEST,
        "    # -- W2 P2a: cost_usd honours the event's own ts for dated rows --\n"
        "\n"
        "    def test_sonnet5_dated_cost_usd(self) -> None:\n"
        "        p = self.mod._DEFAULT_PRICING\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.cost_usd(p, \"claude-sonnet-5\", 1_000_000, 0,\n"
        "                              ts=\"2026-08-31T12:00:00Z\"), 2.00)\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.cost_usd(p, \"claude-sonnet-5\", 1_000_000, 0,\n"
        "                              ts=\"2026-09-01T00:00:00Z\"), 3.00)\n"
        "        # No ts -> static row (pre-P2a behaviour preserved).\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.cost_usd(p, \"claude-sonnet-5\", 1_000_000, 0), 2.00)\n"
        "\n"
        "    def test_sonnet5_custom_override_beats_dated_row(self) -> None:\n"
        "        \"\"\"CEO_COST_PRICING_JSON custom rows win over built-in dated rows.\"\"\"\n"
        "        custom = dict(self.mod._DEFAULT_PRICING)\n"
        "        custom[\"claude-sonnet-5\"] = {\n"
        "            \"input_per_mtok\": 9.00, \"output_per_mtok\": 9.00\n"
        "        }\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.cost_usd(custom, \"claude-sonnet-5\", 1_000_000, 0,\n"
        "                              ts=\"2026-09-01T00:00:00Z\"), 9.00)\n",
        "    # -- PLAN-169 S338 follow-up: Sonnet 5 is $2/$10 on BOTH sides of\n"
        "    #    2026-09-01; the W2 P2a ts branch of cost_usd is kept alive through\n"
        "    #    a SYNTHETIC dated row. --\n"
        "\n"
        "    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:\n"
        "        p = self.mod._DEFAULT_PRICING\n"
        "        for ts in (\"2026-08-31T12:00:00Z\", \"2026-09-01T00:00:00Z\",\n"
        "                   \"2026-12-31T23:59:59Z\"):\n"
        "            # $2 in + $10 out — never $3 + $15.\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.cost_usd(p, \"claude-sonnet-5\", 1_000_000, 1_000_000,\n"
        "                                  ts=ts), 12.00, msg=\"ts=%s\" % ts)\n"
        "        # No ts -> static row.\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.cost_usd(p, \"claude-sonnet-5\", 1_000_000, 0), 2.00)\n"
        "        self.assertNotIn(\"claude-sonnet-5\", self.mod._DATED_PRICING)\n"
        "\n"
        "    def test_dated_cost_usd_mechanism_synthetic_row(self) -> None:\n"
        "        \"\"\"W2 P2a mechanism (ts-aware row selection, cutoff inclusive, no\n"
        "        mutation) survives the Sonnet 5 row retirement.\"\"\"\n"
        "        model = \"synthetic-dated-model\"\n"
        "        base = {\"input_per_mtok\": 2.00, \"output_per_mtok\": 10.00}\n"
        "        dated = (\"2026-08-31\", dict(base),\n"
        "                 {\"input_per_mtok\": 3.00, \"output_per_mtok\": 15.00})\n"
        "        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \\\n"
        "                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):\n"
        "            p = self.mod._DEFAULT_PRICING\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.cost_usd(p, model, 1_000_000, 0,\n"
        "                                  ts=\"2026-08-31T12:00:00Z\"), 2.00)\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.cost_usd(p, model, 1_000_000, 0,\n"
        "                                  ts=\"2026-09-01T00:00:00Z\"), 3.00)\n"
        "            self.assertAlmostEqual(self.mod.cost_usd(p, model, 1_000_000, 0), 2.00)\n"
        "            self.assertEqual(p[model], base,\n"
        "                             \"dated pricing must never repaint the global row\")\n"
        "        self.assertNotIn(model, self.mod._DEFAULT_PRICING)\n"
        "        self.assertNotIn(model, self.mod._DATED_PRICING)\n"
        "\n"
        "    def test_custom_override_beats_dated_row_synthetic(self) -> None:\n"
        "        \"\"\"CEO_COST_PRICING_JSON custom rows win over built-in dated rows.\"\"\"\n"
        "        model = \"synthetic-dated-model\"\n"
        "        base = {\"input_per_mtok\": 2.00, \"output_per_mtok\": 10.00}\n"
        "        dated = (\"2026-08-31\", dict(base),\n"
        "                 {\"input_per_mtok\": 3.00, \"output_per_mtok\": 15.00})\n"
        "        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \\\n"
        "                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):\n"
        "            custom = dict(self.mod._DEFAULT_PRICING)\n"
        "            custom[model] = {\"input_per_mtok\": 9.00, \"output_per_mtok\": 9.00}\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.cost_usd(custom, model, 1_000_000, 0,\n"
        "                                  ts=\"2026-09-01T00:00:00Z\"), 9.00)\n",
        1,
    ),
    (
        FLEET_TEST,
        "    def test_sonnet5_dated_compute_cost(self) -> None:\n"
        "        \"\"\"W2 P2a: compute_cost_usd honours the event's own ts.\"\"\"\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.compute_cost_usd(\"claude-sonnet-5\", 1000, 0,\n"
        "                                      ts=\"2026-08-31T12:00:00Z\"), 0.002)\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.compute_cost_usd(\"claude-sonnet-5\", 1000, 1000,\n"
        "                                      ts=\"2026-09-01T00:00:00Z\"), 0.018)\n"
        "        # No ts -> static row (pre-P2a behaviour preserved).\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.compute_cost_usd(\"claude-sonnet-5\", 1000, 0), 0.002)\n",
        "    def test_sonnet5_standard_rate_on_both_sides_of_2026_09_01(self) -> None:\n"
        "        \"\"\"PLAN-169 S338 follow-up: $2/$10 per MTok (0.002/0.010 per 1k) on\n"
        "        both sides of 2026-09-01 — the intro price became the standard price\n"
        "        and the dated $3/$15 flip row was retired.\"\"\"\n"
        "        for ts in (\"2026-08-31T12:00:00Z\", \"2026-09-01T00:00:00Z\",\n"
        "                   \"2026-12-31T23:59:59Z\"):\n"
        "            # 1k in + 1k out = 0.002 + 0.010 — never 0.003 + 0.015.\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.compute_cost_usd(\"claude-sonnet-5\", 1000, 1000, ts=ts),\n"
        "                0.012, msg=\"ts=%s\" % ts)\n"
        "        # No ts -> static row.\n"
        "        self.assertAlmostEqual(\n"
        "            self.mod.compute_cost_usd(\"claude-sonnet-5\", 1000, 0), 0.002)\n"
        "        self.assertNotIn(\"claude-sonnet-5\", self.mod._DATED_PRICING)\n"
        "\n"
        "    def test_dated_compute_cost_mechanism_synthetic_row(self) -> None:\n"
        "        \"\"\"W2 P2a mechanism (ts-aware row selection, cutoff inclusive, no\n"
        "        mutation, lower-cased key) survives the Sonnet 5 row retirement.\"\"\"\n"
        "        model = \"synthetic-dated-model\"\n"
        "        base = {\"in\": 0.002, \"out\": 0.010}\n"
        "        dated = (\"2026-08-31\", dict(base), {\"in\": 0.003, \"out\": 0.015})\n"
        "        with mock.patch.dict(self.mod._DEFAULT_PRICING, {model: base}), \\\n"
        "                mock.patch.dict(self.mod._DATED_PRICING, {model: dated}):\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.compute_cost_usd(model, 1000, 0,\n"
        "                                          ts=\"2026-08-31T12:00:00Z\"), 0.002)\n"
        "            self.assertAlmostEqual(\n"
        "                self.mod.compute_cost_usd(model.upper(), 1000, 1000,\n"
        "                                          ts=\"2026-09-01T00:00:00Z\"), 0.018)\n"
        "            self.assertAlmostEqual(self.mod.compute_cost_usd(model, 1000, 0), 0.002)\n"
        "            self.assertEqual(self.mod._DEFAULT_PRICING[model], base,\n"
        "                             \"dated pricing must never repaint the global row\")\n"
        "        self.assertNotIn(model, self.mod._DEFAULT_PRICING)\n"
        "        self.assertNotIn(model, self.mod._DATED_PRICING)\n",
        1,
    ),
    (
        FLEET_TEST,
        "    fable-5 / opus-4-8 / sonnet-5 rows already existed there pre-PLAN-163\n"
        "    (asserted by test_a4_pricing_doctrine.py); only the ids new to this\n"
        "    plan are asserted here.\n",
        "    fable-5 / opus-4-8 / sonnet-5 rows already existed there pre-PLAN-163\n"
        "    (fable-5 / opus-4-8 rates asserted by test_a4_pricing_doctrine.py); the\n"
        "    ids new to this plan are asserted here, plus the sonnet-5 RATE since the\n"
        "    PLAN-169 S338 follow-up (the $3/$15 sticker became $2/$10).\n",
        1,
    ),
    (
        FLEET_TEST,
        "    def test_opus48_fast_row(self) -> None:\n"
        "        \"\"\"W2 P2b: 4-8-fast is a live replacement id and must be priced.\"\"\"\n"
        "        text = self._block(\"claude-opus-4-8-fast\")\n"
        "        self.assertIn(\"input_per_mtok: 10.00\", text)\n"
        "        self.assertIn(\"output_per_mtok: 50.00\", text)\n",
        "    def test_opus48_fast_row(self) -> None:\n"
        "        \"\"\"W2 P2b: 4-8-fast is a live replacement id and must be priced.\"\"\"\n"
        "        text = self._block(\"claude-opus-4-8-fast\")\n"
        "        self.assertIn(\"input_per_mtok: 10.00\", text)\n"
        "        self.assertIn(\"output_per_mtok: 50.00\", text)\n"
        "\n"
        "    def test_sonnet5_row_standard_rate(self) -> None:\n"
        "        \"\"\"PLAN-169 S338 follow-up: the estimator sticker is $2/$10 — the\n"
        "        launch intro price became the standard price (pricing page fetched\n"
        "        2026-09-01; the 2026-09-01 increase to $3/$15 will not occur). The\n"
        "        ADR-157 'sticker $3/$15' note is superseded.\"\"\"\n"
        "        text = self._block(\"claude-sonnet-5\")\n"
        "        self.assertIn(\"input_per_mtok: 2.00\", text)\n"
        "        self.assertIn(\"output_per_mtok: 10.00\", text)\n"
        "        self.assertNotIn(\"input_per_mtok: 3.00\", text)\n"
        "        self.assertNotIn(\"output_per_mtok: 15.00\", text)\n",
        1,
    ),
    # ---------------- build-canonical-models.py (codex rail r2 P2) ----------------
    # `reconcile()` diffs every canonical row against the `_MM_TIERS` regex tier
    # its id resolves to; `claude-sonnet-5` resolved through the GENERIC sonnet
    # tier at $3/$15 (+ its cache columns). Latent today (canonical_models.json
    # carries no sonnet-5 row — Owner-run models.dev refresh only), but the day
    # that refresh lands the $2/$10 row would raise five FALSE divergences. A
    # Sonnet-5-specific tier goes BEFORE the generic one (first match wins).
    (
        BUILD_CM,
        "    (r\"opus-(?:[5-9]|\\d\\d)\", (5.0, 6.25, 10.0, 0.50, 25.0)),\n"
        "    (r\"sonnet-[3-9]\", (3.0, 3.75, 6.00, 0.30, 15.0)),\n",
        "    (r\"opus-(?:[5-9]|\\d\\d)\", (5.0, 6.25, 10.0, 0.50, 25.0)),\n"
        "    # PLAN-169 S338 follow-up: Sonnet 5 is $2/$10 — the launch intro price\n"
        "    # became the STANDARD price (official pricing page fetched 2026-09-01; the\n"
        "    # scheduled 2026-09-01 increase to $3/$15 will not occur); cache\n"
        "    # multipliers unchanged (1.25x / 2x write, 0.1x read). MUST precede the\n"
        "    # generic sonnet tier, which would otherwise match it at $3/$15 and raise\n"
        "    # five false divergences the day an Owner refresh adds the row.\n"
        "    (r\"sonnet-5(?:\\D|$)\", (2.0, 2.50, 4.00, 0.20, 10.0)),\n"
        "    (r\"sonnet-[3-9]\", (3.0, 3.75, 6.00, 0.30, 15.0)),\n",
        1,
    ),
    (
        BUILD_CM_TEST,
        "        data = _sample_data(models=models)\n"
        "        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)\n"
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_divergence_is_flagged_not_overwritten(self):\n",
        "        data = _sample_data(models=models)\n"
        "        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)\n"
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_mm_tier_sonnet5_is_standard_2_10_and_generic_sonnet_kept(self):\n"
        "        \"\"\"PLAN-169 S338 follow-up: Sonnet 5 resolves to its own $2/$10 tier\n"
        "        (cache 1.25x/2x write, 0.1x read); Sonnet 4.6 keeps the generic\n"
        "        $3/$15 tier. Dated suffixes resolve like the bare id.\"\"\"\n"
        "        sonnet5 = (2.0, 2.50, 4.00, 0.20, 10.0)\n"
        "        for mid in (\"claude-sonnet-5\", \"claude-sonnet-5-20260630\",\n"
        "                    \"claude-sonnet-5[1m]\"):\n"
        "            self.assertEqual(bcm._mm_tier_for(mid), sonnet5, mid)\n"
        "        self.assertEqual(bcm._mm_tier_for(\"claude-sonnet-4-6\"),\n"
        "                         (3.0, 3.75, 6.00, 0.30, 15.0))\n"
        "\n"
        "    def test_reconcile_sonnet5_row_at_standard_rate_is_clean(self):\n"
        "        \"\"\"A canonical Sonnet 5 row at the standard $2/$10 (+ standard cache\n"
        "        multipliers) reconciles with ZERO findings against BOTH the\n"
        "        cost-table.yaml sticker and the tier table — the day an Owner\n"
        "        models.dev refresh adds the row, it must not raise false drift.\"\"\"\n"
        "        models = {\"claude-sonnet-5\": {\n"
        "            \"input_per_mtok\": 2.0, \"cache_write_5m_per_mtok\": 2.5,\n"
        "            \"cache_write_1h_per_mtok\": 4.0, \"cache_read_per_mtok\": 0.2,\n"
        "            \"output_per_mtok\": 10.0}}\n"
        "        data = _sample_data(models=models)\n"
        "        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)\n"
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_divergence_is_flagged_not_overwritten(self):\n",
        1,
    ),
]

TOUCHED_BY_EDITS = sorted({e[0] for e in EDITS})


class Refuse(Exception):
    pass


def _selected(only: List[str]) -> List[Tuple[str, str, str, int]]:
    if not only:
        return list(EDITS)
    unknown = sorted(set(only) - set(TOUCHED_BY_EDITS))
    if unknown:
        raise Refuse("\n".join("  - --only %s: not a path this script touches" % u
                               for u in unknown))
    return [e for e in EDITS if e[0] in set(only)]


def _plan(root: Path, edits: List[Tuple[str, str, str, int]]) -> None:
    """Step 1 — count EVERY anchor and refuse before any write."""
    problems = []
    for rel, old, _new, count in edits:
        p = root / rel
        if not p.is_file():
            problems.append("%s: file missing" % rel)
            continue
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != count:
            problems.append("%s: anchor found %dx, expected %d — %r"
                            % (rel, n, count, old[:70]))
    # Already applied? The marker must be absent from every touched path.
    for rel in sorted({e[0] for e in edits}):
        p = root / rel
        if p.is_file() and MARKER in p.read_text(encoding="utf-8"):
            problems.append("%s: already contains %r — tree already patched?" % (rel, MARKER))
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))


def _apply(root: Path, edits: List[Tuple[str, str, str, int]]) -> List[str]:
    written: List[str] = []
    for rel, old, new, count in edits:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        assert text.count(old) == count  # _plan already guaranteed
        p.write_text(text.replace(old, new), encoding="utf-8")
        if rel not in written:
            written.append(rel)
    return sorted(set(written))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="tree at HEAD + wave-fable51 to patch (optional with --list-paths)")
    ap.add_argument("--check-only", action="store_true",
                    help="only verify the anchors; write nothing")
    ap.add_argument("--list-paths", action="store_true",
                    help="print the touched paths (one per line) and exit")
    ap.add_argument("--only", action="append", default=[], metavar="REL_PATH",
                    help="apply only the edits of this path (repeatable; positive control)")
    args = ap.parse_args(argv)
    if args.list_paths:
        for rel in TOUCHED_BY_EDITS:
            print(rel)
        return 0
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir():
        sys.stderr.write("apply-sonnet5-pricing-fu: --root does not look like a checkout: %s\n"
                         % root)
        return 2
    try:
        edits = _selected(args.only)
        _plan(root, edits)
        if args.check_only:
            print("apply-sonnet5-pricing-fu: %d edit(s) applicable in %d path(s); nothing written"
                  % (len(edits), len({e[0] for e in edits})))
            return 0
        written = _apply(root, edits)
    except Refuse as exc:
        sys.stderr.write("apply-sonnet5-pricing-fu: REFUSED\n%s\n" % exc)
        return 1
    print("apply-sonnet5-pricing-fu: %d edit(s) applied in %d path(s):"
          % (len(edits), len(written)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
