# ADR-017: Lesson Pruning Policy — Advisory Sprint 6, Bounded Execute Sprint 8

## Status: SUPERSEDED by ADR-020 (2026-04-14)

> **Current policy lives in [ADR-020](./ADR-020-lesson-pruning-policy-v2.md).**
> This ADR is retained as historical record. See ADR-020 §ADR-017
> supersede for the migration rationale (PLAN-009 Phase 2 C8/A5).

### Historical status

- ACCEPTED 2026-04-13 (Sprint 6, v1)
- AMENDED 2026-04-13 (Sprint 8, bounded execute)
- SUPERSEDED 2026-04-14 (Sprint 9, ADR-020)

## Sprint 8 Amendment (bounded execute)

PLAN-008 Phase 4 enabled `--execute` with **three safeguards** instead
of the "post-FPR-measurement" gate the original version required. The
debate round 1 consensus on PLAN-008 (VP Engineering R-VP1 HIGH) was
explicit that enabling execute without a measured FPR baseline would
be a governance violation. The chosen response:

1. **Env-gate:** `--execute` refuses with exit 10 unless
   `CEO_PRUNE_EXECUTE=1` is set. Opt-in per invocation prevents
   accidental pruning from automated runs.
2. **Per-invocation cap:** `--max-archive N` (default 3) limits the
   blast radius of any single run. Even if the threshold is wrong,
   damage is bounded.
3. **Restore companion:** `.claude/scripts/lesson-restore.py` ships
   in the same sprint, reversing the archive move. `lesson_restored`
   event emitted per restore.

**Honest framing:** Sprint 8 does NOT claim FPR has been measured.
Sprint 8 enables execute *as the mechanism for collecting FPR
baseline data* — archival events + their later restoration (true
positive or false positive per operator review) are the data
source. The original "post-FPR-measurement" gate is now worded as:
post-FPR-measurement, Sprint 9 decides whether to lift the cap or
remove the env-gate. If measured FPR > 5%, this ADR re-opens and
execute is rolled back.

The preview path (`--execute --plan-only`) and per-batch receipt
file (`prune-receipt-<ISO>.json`) were added per debate consensus
C9 (Staff Backend) so repeated operator runs are auditable even
across wall-clock-dependent record_outcome() drift.

Sprint 8 implementation details in `.claude/scripts/prune-lessons.py`.

---

## Context (original, Sprint 6)

## Context

PLAN-006 original Phase 4 bundled Reflexion outcome tracking AND
auto-pruning into a single ADR. PLAN-006 debate round 1 (R-VP3) split
them: outcome tracking (counters) is additive + reversible; auto-
pruning is **irreversible** data operation on accumulated context. If
the outcome signal is noisy (R-VP3 + Q3 open question), auto-pruning
silently deletes lessons that took dozens of spawns to accrue.

VP Engineering cited the skill's rule: irreversible + high-blast →
ADR first + advisory-then-blocking pattern (same as confidence gate,
coverage gate).

This ADR documents the pruning policy. Sprint 6 ships it **dry-run
only**; Sprint 7 measures false-positive rate (FPR), then decides
whether to enable enforcing mode.

## Decision Drivers

- **Irreversibility.** Deleted lessons can't be recovered except from
  git history. A noisy signal that flags 30% of lessons as "losers"
  would evaporate the corpus.
- **Signal maturity.** Sprint 6 is the FIRST sprint with outcome
  data. No empirical basis for threshold selection yet.
- **Consistency.** Mirrors confidence gate (Sprint 6 advisory, Sprint
  7 decide-to-block) and coverage gate (Sprint 5 measure-only,
  Sprint 6 enforce).

## Options Considered

### Option A: Auto-prune in Sprint 6 when hit_rate < 0.3 at n≥5

- **Pros:** keeps corpus curated; acts on signal immediately.
- **Cons:** no FPR evidence; a confirmed-miss lesson might be correct
  advice that consistently arrives in wrong contexts (scope issue,
  not content issue); deletion bypasses review.

### Option B: Archive-not-delete, advisory-only Sprint 6 (chosen)

- **Pros:** reversible (archived lessons can be restored); builds
  FPR evidence; aligns with confidence-gate + coverage-gate cadence;
  operator reviews candidates before Sprint 7 decision.
- **Cons:** delays actual corpus curation by one sprint; requires
  separate `--execute` gate in Sprint 7.

### Option C: Delete immediately at much stricter threshold (n≥20, hit_rate<0.1)

- **Pros:** very conservative; low FPR.
- **Cons:** at N<5000 lessons in practice, threshold rarely triggers;
  effectively does nothing; doesn't solve the "curate corpus" goal.

## Decision

**Option B.** Advisory-only `--dry-run` in Sprint 6. No code path
deletes or archives lessons. CLI flag `--execute` raises
`NotImplementedError` (exit code 10).

### Prune criteria (Sprint 6 dry-run)

A lesson is a **candidate** when:
- `hit_count + miss_count >= 5` (minimum sample size)
- `hit_rate < 0.3` (heavy miss bias)

Sprint 6's `prune-lessons.py --dry-run` identifies candidates +
emits to stdout (human or JSON) + exits 0. No files modified.

### Archive-not-delete (Sprint 7 plan)

When Sprint 7 enables `--execute`, the behavior is:
1. Copy lesson JSON to `$CEO_LESSONS_DIR/archive/<lesson_id>.json`
2. Emit audit event `lesson_archived` (new v2 action)
3. Remove from active `lessons/` directory
4. Restore path documented: copy back from archive + rebuild index

**Never delete** — archive only. Git history is a secondary recovery
layer; the primary restore path is `archive/`.

### FPR measurement (Sprint 7)

Before enabling enforcement, Sprint 7 operator reviews a sample of
candidate lessons and classifies each:
- True positive: lesson was genuinely wrong / stale
- False positive: lesson was correct but misapplied to wrong context

FPR threshold to enable enforcement: `FPR ≤ 15%`. If higher, the
threshold (sample size or hit_rate cutoff) tightens, or enforcement
stays deferred.

### Minimum sample size rationale

`n >= 5` chosen because:
- Binary outcomes with n<5 have very wide confidence intervals
- At n=5, 1/5 = 0.2 is below 0.3 threshold (catches clear losers)
- At n=5, 2/5 = 0.4 is above 0.3 (avoids flipping on a single outcome
  swing)

## Consequences

### Positive

- No corpus destruction in Sprint 6.
- Operator sees candidates and can override / investigate before
  enforcement.
- Mirrors the advisory-then-blocking pattern already proven in the
  framework (coverage gate, confidence gate).
- `prune-lessons.py --json` output feeds dashboards without side-effects.

### Negative

- Sprint 6 ships the CLI but does not curate the corpus. If the
  corpus grows noisy before Sprint 7 ships enforcement, ranking in
  `get_top_k` already down-weights losers (via ADR-015 hit_weight
  formula), so user-facing injection is minimally affected.
- `--execute` flag is a visible "not implemented" surface — must be
  maintained until Sprint 7 implements it properly.

### Neutral

- `find_candidates()` function is reusable by dashboards (future
  audit-dashboard panel, optional).

## Blast Radius (Sprint 6 scope)

- `.claude/scripts/prune-lessons.py` (NEW ~120 LOC, dry-run only)
- `.claude/scripts/tests/test_prune_lessons.py` (NEW, ~10 tests)

**Reversibility:** ABSOLUTE. Sprint 6 does not mutate any lesson. If
Sprint 7 enforcement is never built, Sprint 6 shipped a useful
advisory tool that ages gracefully.

## References

- PLAN-006 §Phase 4
- PLAN-006/debate/round-1/vp-engineering.md §R-VP3
- PLAN-006/debate/round-1/consensus.md §K1
- ADR-015 — Reflexion v2 outcome loop (companion)
- Sprint 7 plan (TBD) — FPR measurement + enforcement decision

## Enforcement commit

`043de3bfa120` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
