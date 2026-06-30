---
id: ADR-148
title: Canonical model-pricing source — models.dev-provenanced table, Owner-fetched, checksum-fail-CLOSED, advisory reconcile
status: ACCEPTED
enforcement_commit: 94694d5f
accepted_at: 2026-06-17
accepting_session: S242
decision_date: 2026-06-09
proposing_session: S223
authorization: "PLAN-133 (Goose-harvest SOTA evolution) Wave B finops — item B1 [P0]. 7-archetype Wave-A debate 0-VETO + Codex pair-rail."
owner: llm-finops-architect
plan: PLAN-133-goose-harvest-sota-evolution
amends: none
related: [ADR-052, ADR-064, ADR-081, ADR-142, ADR-144]
---

# ADR-148 — Canonical model-pricing source

**Status:** ACCEPTED (S242, 2026-06-17 — B1 landed: the data file + generator +
`canonical_models_ref` pointer are in the tree and green, 29 tests). This ADR
codifies WHY a single provenanced pricing table is the source of truth and how it
reconciles with `cost-table.yaml` + `measure_multiplier`. Promotion gate: debate
0-VETO + Codex pair-rail (PLAN-133 B1) + Codex R-sweep ACCEPT (thread `019ed788`).
**Enforcement commit:** `94694d5f` — the artifacts are
`.claude/data/canonical_models.json` + `.claude/scripts/build-canonical-models.py`
+ the `canonical_models_ref` pointer in `.claude/scripts/cost-table.yaml` (all
three NON-canonical). B3 — wiring `measure_multiplier`'s price source behind
`CEO_CANONICAL_MODELS=1` + publishing the reconcile delta — remains the SEPARATE
default-on gate.
**Blast radius:** L3 (a single pricing source-of-truth that the cost calculator +
`measure_multiplier` tiering will consume)
**Cites:** PLAN-133 item B1 [P0].

## Context

Model pricing currently lives in three places that can drift: `cost-table.yaml`
(the calculator), the `MODEL_PRICING` tier regexes in `measure_multiplier.py`, and
historical ADR-142 figures. B1's reconcile tool already caught a genuine
divergence: the `measure_multiplier` tier regex `opus-4-(?:[2-9]|1\d)` routes
`claude-opus-4-7` to the cheap `opus_new` tier ($5/$25), but `opus-4-7` is the
legacy expensive tier ($15/$75) per `cost-table.yaml` + the ADR-142 record. That
is a live pricing bug — flagged, not silently overwritten.

Goose sources canonical model pricing/limits from models.dev. PLAN-133 B1 harvests
that idea — a provenanced, checksummed pricing table — re-implemented from scratch
in stdlib with **no network import anywhere** in the generator (enforced by an AST
test). The sole sanctioned models.dev egress is Owner-executed, out-of-band; the
script only consumes an Owner-downloaded JSON blob.

## Decision drivers

- A single pricing source-of-truth eliminates the three-way drift class.
- Provenance (`source_url` + `fetched_at` + `sha256`) makes "where did this number
  come from / how stale is it" answerable.
- The generator must never reach the network (supply-chain + agent-egress hygiene);
  the fetch is an explicit Owner action.
- S220 doctrine: an unknown model resolves to an all-zero fallback (flag, don't
  guess); quota is the cost metric, USD is advisory.

## Options considered

### Option A: Keep the three drifting sources
Status quo; the `opus-4-7` mispricing is exactly the failure mode. Rejected.

### Option B: models.dev-provenanced canonical table, Owner-fetched, advisory reconcile (chosen)
`.claude/data/canonical_models.json` carries provenance + staleness + an all-zero
unknown fallback + cache multipliers + the model rows. `build-canonical-models.py`
is a stdlib, no-network CLI: `--verify` (checksum, fail-CLOSED), `--check-staleness`
(advisory), `--reconcile` (FLAGS divergence, never writes), `--fetch SRC`
(Owner-only transform of a downloaded blob). The table AUGMENTS `cost-table.yaml`
(a `canonical_models_ref` pointer), it does not replace it.

### Option C: Live-fetch in CI
Network egress on a runner + a moving source under the framework's feet. Rejected.

## Decision

Adopt **Option B**:

1. **`.claude/data/canonical_models.json` is the single pricing source-of-truth**,
   carrying `provenance{source_url, fetched_at, fetched_by, sha256}`,
   `staleness{valid_until, refresh_cadence_days, advisory_only}`, an all-zero
   `unknown_model_fallback`, `cache_multipliers` (5m=1.25× / 1h=2.0× / read=0.1×),
   and the Claude-only model rows.
2. **Checksum is fail-CLOSED** on a real mismatch; the `PENDING_OWNER_FETCH`
   sentinel returns pending (a fresh checkout must not hard-block before the Owner
   fetch — S220 "flag, don't guess").
3. **No network import in the generator** — enforced by
   `test_no_urllib_or_requests_in_source` (AST inspection). The sole models.dev
   egress is Owner-executed, out-of-band (`curl ... -o /tmp/models-dev.json` then
   `--fetch`); agents/hooks must NOT perform it.
4. **Reconcile FLAGS, never writes** — `--reconcile` reports divergence against
   `cost-table.yaml` + `measure_multiplier`; `cost-table.yaml` is byte-identical
   before/after (tested). The `opus-4-7` legacy-vs-new finding is recorded for B3
   to resolve by rewiring `measure_multiplier`'s price source to this table.
5. **Default-OFF consumer flag** — `CEO_CANONICAL_MODELS=1` gates the B3 consumer
   (measure-first per ADR-125); B1 itself stays advisory-only and touches no
   canonical file.
6. **Unknown model → all-zero fallback, `is_known=False`** (S220).
7. **Claude-only by design** — `build_from_models_dev` drops every non-`claude-*`
   row and fail-CLOSES if zero claude rows result (refuses an empty table).

## Consequences

- (+) Eliminates the three-way pricing drift; provenance + staleness make figures
  auditable; the `opus-4-7` mispricing has a clean resolution path (B3).
- (+) No agent/hook network egress; the fetch is an explicit, auditable Owner step.
- (−) The table goes stale between Owner fetches; mitigated by the staleness
  advisory + the `valid_until` window + the `/ceo-boot` advisory wiring (deferred).
- (~) B1 is entirely non-canonical (data + script + a `cost-table.yaml` augment);
  no GPG ceremony. The consuming rewire (B3) is the change that retires the
  `measure_multiplier` regex tiering in favor of this table.

## Promotion criteria (measure-first)

B3 wires the consumer behind `CEO_CANONICAL_MODELS=1` and publishes the reconcile
delta (canonical vs `measure_multiplier`) before flipping the price source on by
default.

## Blast radius

L3 — a single pricing source-of-truth consumed by the cost calculator +
`measure_multiplier`; B1 lands non-canonically, B3 rewires the consumer.
