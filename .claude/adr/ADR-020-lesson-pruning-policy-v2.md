# ADR-020: Lesson pruning policy v2

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 9 (PLAN-009 Phase 2)
**Supersedes:** ADR-017 (lesson pruning policy v1 — Sprint 6, amended Sprint 8)
**Related:** ADR-015 (Reflexion v2 outcome loop), ADR-018 v1.1 (claim grammar)

## Context

ADR-017 (v1) shipped in Sprint 6 with a single hardcoded rule:

> Prune when `n >= 5 AND hit_rate < 0.3`.

Sprint 8 amended it to document `--execute` enablement (env gate +
max-archive cap + receipt + lesson-restore companion). The amendment
left three problems unaddressed:

1. **Thresholds hidden.** The 0.3 hit-rate and 5-sample minimum are
   policy decisions, not implementation details. They should be
   flag-controllable so operators can measure trade-offs.
2. **No age-based filtering.** A new lesson with 1 hit + 4 miss has
   the same "miss_ratio=0.8" as a 6-month-old lesson with 20 hit +
   80 miss — but the first is noise, the second is evidence. ADR-017
   can't distinguish them.
3. **Three amendments to one Decision section.** ADR-017 was already
   amended once in Sprint 8. A second amendment would turn the doc
   into a changelog, not a decision record.

PLAN-009 debate round 1 (C8/A5) agreed: fresh ADR, ADR-017 →
SUPERSEDED.

## Decision drivers

- **Operators need knobs.** Defaults should preserve current behavior
  (zero behavior diff for existing callers), but all thresholds must
  be flag-controllable.
- **Safety over flexibility.** A flag that lets you prune 95% of your
  lessons in one invocation is a foot-gun. Guard against it.
- **AND semantics.** Multiple filters should compose as conjunction,
  not disjunction — otherwise the stricter filter is always redundant.
- **Preserve Sprint 8 safeguards.** Env gate (`CEO_PRUNE_EXECUTE=1`),
  cap (`--max-archive`), plan-only preview, receipt, audit event,
  lesson-restore companion all stay.

## Decision

### 1. Threshold flags

`prune-lessons.py` exposes three new filter flags in addition to the
existing `--max-archive`:

| Flag                         | Default | Maps to behavior |
|------------------------------|---------|------------------|
| `--min-miss-ratio FLOAT`     | 0.7     | Previous `hit_rate < 0.3` (≡ miss_ratio >= 0.7) |
| `--min-age-days INT`         | 0       | Previous: no age filter. 0 = disabled |
| `--min-archive-age-days INT` | 0       | Previous: no last-outcome filter. 0 = disabled |

Defaults match the v1 (ADR-017) behavior exactly. Existing invocations
are unaffected.

### 2. Filter composition — AND semantics

A lesson becomes a prune candidate iff **all** of the following hold:

```
n := hit_count + miss_count >= 5                   (hardcoded min-sample)
AND miss_count/n >= --min-miss-ratio
AND (--min-age-days == 0 OR age(created_at) >= --min-age-days)
AND (--min-archive-age-days == 0 OR age(last_outcome_at) >= --min-archive-age-days)
```

When the age fields are unparseable (malformed timestamps), the filter
votes **no** (fail-safe: don't prune what we can't date).

### 3. Safety guard — `--force-dangerous-threshold`

`--min-miss-ratio < 0.1` is rejected by the CLI unless
`--force-dangerous-threshold` is also set. Exit code 11.

**Rationale.** A miss ratio of 0.1 means "prune anything with at least
10% failures". That includes lessons with 9 hits + 1 miss —
almost-perfect lessons. The guard makes the operator confirm they
mean it.

The threshold value (0.1) is a deliberate order-of-magnitude cliff
from the 0.7 default. Operators experimenting with 0.5 or 0.3 don't
need the override; operators going below 0.1 probably typed wrong.

### 4. Safeguards preserved from ADR-017 (Sprint 8 amendment)

Not changed by this ADR:

- `--execute` requires `CEO_PRUNE_EXECUTE=1` env var. Exit 10 otherwise.
- `--max-archive N` (default 3) caps archivals per invocation.
- `--execute --plan-only` preview mode.
- Archive path: `lessons/archive/<YYYY-MM-DD>/<id>.json`.
- Per-batch receipt file: `prune-receipt-<ISO>.json`.
- `lesson_archived` audit event per archive.
- `lesson-restore.py` companion reverses the move.

### 5. Sprint 10 criteria (forward-looking)

PLAN-009 Phase 2 P2.4 defines when the defaults should be revisited:

- **If restore-ratio > 5%** (lessons archived then restored via
  `lesson-restore.py`): operators are frequently reversing the CLI.
  That means either the thresholds are too loose OR the archive
  process is wrong. Rollback `--execute` gating (require a fresh ADR
  to re-enable).
- **If restore-ratio < 5% over 100+ prune events**: thresholds are
  trustworthy. Consider relaxing `--max-archive` cap (separate ADR
  for that decision).
- **No action until data**: do not modify defaults based on intuition.

Measurement: `audit-query prune-restore-ratio` (PLAN-009 P2.2).

### 6. ADR-017 supersede

- Status: ACCEPTED (v1 Sprint 6) → AMENDED (Sprint 8) → SUPERSEDED
  (Sprint 9, this ADR).
- ADR-017 Decision section stands as historical record. New rules
  live in ADR-020 only.
- Callers that reference "ADR-017 threshold" should migrate to
  "ADR-020 default min-miss-ratio + min-age-days".

## Consequences

### Positive

- Thresholds are now *configurable* and *measurable* (audit events +
  restore-ratio metric).
- Age-based filtering catches "new noise" vs "old evidence" that v1
  couldn't distinguish.
- AND semantics are legible + testable (one table, one conjunction).
- Safety guard prevents the most obvious foot-gun without blocking
  legitimate experimentation.
- Reading ADR-020 alone gives the full current policy. ADR-017 is
  historical.

### Negative

- Three new flags to remember. `--help` text shows defaults verbatim.
- `--min-age-days` requires parseable timestamps. Corrupt
  `created_at` → lesson is fail-safe *kept* (not pruned), which is
  technically a behavior change from v1 (v1 would have pruned
  regardless of timestamps). Acceptable because corrupt timestamps
  are themselves a bug signal.

### Neutral

- Defaults preserve v1 behavior exactly. Zero behavior diff until an
  operator chooses non-default flags.

## Blast radius

**L2** — one new ADR, one CLI refactor (~50 LOC), ADR-017 status
update, +5 tests. Reversibility: HIGH. Callers unchanged. Flags
additive.

## References

- ADR-017 — lesson pruning policy v1 (SUPERSEDED)
- ADR-015 — Reflexion v2 outcome loop (provides `last_outcome_at`)
- ADR-018 v1.1 — claim grammar (unrelated but same sprint)
- PLAN-009 §Phase 2 P2.1/P2.4
- PLAN-009/debate/round-1/consensus.md §C8/A5

## Enforcement commit

`ce85197c8522` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
