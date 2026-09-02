# DESIGN — pack `sonnet5-pricing-fu` (PLAN-169 follow-up, S338, 2026-09-01)

**Lands AFTER `wave-fable51`.** Every anchor in `apply-sonnet5-pricing-fu.py`
matches the POST-fable51 content (the fable51 patch touches the same files).
Base used for the final derivation and battery: HEAD `f0e98de` +
`apply-fable51-edits.py` (sha256 `c1bb9206…f228f4`, 55 edits / 30 paths).
HEAD moved twice while this pack was built (`dc72bf1` -> `6160578` ->
`f0e98de`, orchestrator/Owner commits); none of those commits touches any of
this pack's 10 paths or any fable51 path, so the derived diff is byte-identical
on all three bases. If a later fable51 iteration moves one of these anchors,
the script REFUSES by name and nothing is written — re-derive then.

## The fact (source, fetch date)

Official pricing page, `https://platform.claude.com/docs/en/about-claude/pricing`,
fetched 2026-09-01: *"The $2/$10 per million input/output token pricing for
Claude Sonnet 5, announced at launch as introductory pricing through
August 31, 2026, is now the standard price. The previously scheduled increase
to $3/$15 per million input/output tokens on September 1, 2026 will not
occur."* Cache multipliers for Sonnet 5 unchanged (0.1x read; 1.25x / 2x
write).

## Why a pack at all

The repo modelled the flip that did not happen. From 2026-09-01 every
surface below OVERSTATES Sonnet 5 by 50 % (3.00/15.00 vs 2.00/10.00) —
rollups of today's spend, the forward estimator, the reconcile tier table,
and two docs. ADR-149 Amendment 2 (fable51) names this exact follow-up in
§A2.3 and keeps it out of the ceremony by scope discipline; this is that
follow-up.

## Decisions

1. **Remove the Sonnet 5 dated ROW, keep the dated MECHANISM.** With the
   cancelled increase, the "after" leg equals the base row on all three
   tables (`_DATED_PRICING_PER_MTOK` / `_DATED_PRICING` x2) — the row was
   dead data, and a "both legs equal" row invites the next reader to trust a
   flip date that no longer means anything. The tables become `{}` with a
   comment recording why (fact + fetch date); the ts-aware code paths
   (`_rates_for_event`, the `ts` branch of `cost_usd`, the `ts` branch of
   `compute_cost_usd`) are UNTOUCHED — infrastructure for the next real rate
   change. No test asserted the mechanism except through the Sonnet 5 row, so
   each table gains a **synthetic-row mechanism test** (`mock.patch.dict` on
   the module dicts: cutoff inclusive, after-leg, no-ts fallback, no global
   mutation; for `ceo-cost.py` also the custom-override precedence; for
   `budget-summary.py` the lower-cased key). The dicts are restored on exit
   and the tests assert it.
2. **Base rows are exact on both sides of 2026-09-01 — asserted.** The
   rewritten tests price 1M in + 1M out at $12.00 (per-MTok tables) / 0.012
   (per-1k) for ts in {2026-08-01, 2026-08-31T23:59:59Z, 2026-09-01T00:00:00Z,
   2026-12-31}, and no-ts at the base row; plus
   `assertNotIn("claude-sonnet-5", <dated table>)` so a re-added flip row
   turns the suite red.
3. **`cost-table.yaml` sticker 3.00/15.00 -> 2.00/10.00**, `source_url` moved
   to the page actually fetched, comment rewritten to cite the fact and to
   name the ADR-157 sticker note as superseded (ADR-157 itself is a dated
   record and is NOT edited). Verified before editing: the calibrator
   fixtures (`rate-card-fixtures.json`) and `test_a4_pricing_doctrine.py`
   `_EXPECTED_RATES` carry NO sonnet-5 row, so both stay green without any
   fixture change; a new `test_sonnet5_row_standard_rate` in
   `TestCostTableFleetPresence` binds the new sticker. `last_verified_at` /
   `cost_table_valid_until` are whole-table claims (every row re-verified)
   and are left alone (the table goes stale on 2026-09-13 by its own cadence
   — separate refresh).
4. **Comments/docs say what changed and cite the source.** `ceo-cost.py`,
   `budget-summary.py`, `audit-telemetry.py` header comments; the
   `value-dashboard.py` NOTE (which predicted an UNDERSTATEMENT after
   2026-08-31 — now impossible) is kept as history and marked superseded;
   `docs/cost-of-operation.md` row text + one provenance sentence under the
   table; `docs/CEO-MODEL-ROUTING.md` advisory-tier cell.
5. **Additive / minimal / replay-safe.** No historical replay row touched
   (ADR-142: opus-4-7 $15/$75, sonnet-4-6 $3/$15 stay); no model id added or
   removed; no mechanism removed; every number sourced in-comment.
6. **Reconcile tier table (codex rail r2 P2 #1).** `build-canonical-models.py`
   `_MM_TIERS` resolved `claude-sonnet-5` through the generic `sonnet-[3-9]`
   tier at $3/$15 (+ cache columns), i.e. a second pricing mirror that would
   disagree with the cured cost-table the day an Owner models.dev refresh adds
   the row (five false divergences). A Sonnet-5-specific tier
   `(r"sonnet-5(?:\D|$)", (2.0, 2.50, 4.00, 0.20, 10.0))` is inserted BEFORE
   the generic tier; Sonnet 4.6 keeps $3/$15. The "mirror" the comment cites
   (`PLAN-128/wave1/measure_multiplier.py`) does not exist in-tree, so the
   cure is local. Two tests in `TestReconcile`; both RED on the uncured base.
7. **The dated adoption record is NOT edited (codex rail r2 P2 #2).**
   `docs/substrate-adopt-2026-08.md:37` still states the pre-cancellation
   flip; the brief forbids editing it (dated historical record, same class as
   ADR-157). The pointer to it in `docs/CEO-MODEL-ROUTING.md` (about the
   §Tokenizer note, still true) now says in-cell that the target is a DATED
   record whose G2 pricing clause is superseded by this row. A one-line
   supersession INSIDE the record is an Owner call outside this file
   assignment.

## Sites table

| # | Path | Before | After |
|---|------|--------|-------|
| 1 | `.claude/scripts/audit-telemetry.py` | base-row comment says intro-through-08-31 + dated row 2/10 -> 3/15 | comment cites the fact; `_DATED_PRICING_PER_MTOK = {}` with rationale |
| 2 | `.claude/scripts/ceo-cost.py` | header comment "bump the row when the intro window lapses"; dated row 2/10 -> 3/15 | header cites the fact ("no bump is due"); `_DATED_PRICING = {}` |
| 3 | `.claude/scripts/budget-summary.py` | header comment "bump when the window lapses"; dated row 0.002/0.010 -> 0.003/0.015 | header cites the fact; `_DATED_PRICING = {}` |
| 4 | `.claude/scripts/value-dashboard.py` | comment + NOTE predicting understatement after 2026-08-31 | comment rewritten; NOTE marked superseded, row exact both sides |
| 5 | `.claude/scripts/cost-table.yaml` | `claude-sonnet-5` 3.00 / 15.00, ADR-157 sticker comment | 2.00 / 10.00, platform.claude.com source, fact in comment |
| 6 | `.claude/scripts/build-canonical-models.py` | `_MM_TIERS`: sonnet-5 resolved by generic `sonnet-[3-9]` at (3.0, 3.75, 6.00, 0.30, 15.0) | `sonnet-5(?:\D\|$)` tier (2.0, 2.50, 4.00, 0.20, 10.0) inserted before the generic tier |
| 7 | `docs/cost-of-operation.md` | row "(intro $2/$10 until 2026-08-31, sticker $3/$15)" | row "($2/$10 is the standard rate …)"; +1 provenance sentence |
| 8 | `docs/CEO-MODEL-ROUTING.md` | "intro pricing $2/$10 through 2026-08-31 (then $3/$15)" | "$2/$10 per MTok is the STANDARD price … will not occur (fetched 2026-09-01)"; pointer target flagged as a DATED record |
| 9 | `.claude/scripts/tests/test_model_fleet_presence.py` | 8 dated-flip tests asserting $3/$15 after 2026-09-01 (18.00 / 3.00 / 0.018) | docstring; `from unittest import mock`; 5 cure tests + 4 synthetic mechanism tests (32 -> 34 tests on the FINAL fable51 base; the build measured 30 -> 32 on the pre-r3 base — P3 do refutador, S338) |
| 10 | `.claude/scripts/tests/test_build_canonical_models.py` | no sonnet-5 coverage | 2 tests in `TestReconcile` (tier resolution incl. suffixes + zero-finding reconcile of a $2/$10 canonical row) |

Numbers in the tests: per-MTok tables 1M+1M = **12.00** (was 18.00 after the
cutoff); `ceo-cost.cost_usd` 1M in = **2.00** on every ts (was 3.00 after);
`budget-summary.compute_cost_usd` 1k+1k = **0.012** (was 0.018 after);
`_mm_tier_for("claude-sonnet-5")` = **(2.0, 2.5, 4.0, 0.2, 10.0)**.

## Canonicality

All ten touched paths and the script itself: `check_canonical_edit.py
--is-canonical` -> `0` (FREE). No SIGN/LAND material is needed for the paths;
the pack still lands through the orchestrator's commit AFTER fable51 (anchor
dependency, not governance dependency).

## What stays OUT (and why)

- `docs/substrate-adopt-2026-08.md:37` — dated adoption record (brief: do NOT
  edit); see decision 7 for how the pointer to it was handled.
- `.claude/adr/ADR-157-*.md` — dated ADR recording the $3/$15 sticker at the
  time; named as superseded in the yaml comment; ADRs are not rewritten by a
  free-surface pack.
- `.claude/adr/ADR-149-model-id-allowlist.md` §A2.3 — already names this
  follow-up; canonical/ceremony surface of the fable51 pack.
- `docs/provider-pricing.md` — has NO `claude-sonnet-5` row at all (primary or
  provenance). The brief conditions a row on the calibrator or
  `test_a4_pricing_doctrine` requiring it; neither does (fixtures and
  `_EXPECTED_RATES` lack sonnet-5, both stay green). Measured observation for
  a follow-up: `_lib/adapters/live/_cost.py` parses that primary table as its
  pricing source (docstring `:14`, path `:69`), so a Sonnet 5 live-adapter
  event has no rate there today — a PRESENCE gap of the T1.5 class,
  pre-existing and independent of the cancelled flip.
  `ceo-info.py --verify-models` (static) reports only `claude-opus-5` as the
  rate-card gap before and after this pack (unchanged).
- `cost-table.yaml` `last_verified_at` / `cost_table_valid_until` (2026-09-13)
  — whole-table refresh cadence, not a one-row edit.
- `rate-card-fixtures.json` — the ratified fixture set has no sonnet-5 row;
  adding one is a ratification act (Owner), not a follow-up cure.
- `build-canonical-models.py --reconcile` pre-existing divergences for
  `claude-opus-4-6-fast` (canonical 6x fast-mode rates vs the base opus tier)
  — unrelated to Sonnet 5, observed while running the CLI, left as found.
- The `_MM_TIERS` comment's reference to a non-existent
  `PLAN-128/wave1/measure_multiplier.py` mirror — stale comment, left as
  found (not a pricing surface).
