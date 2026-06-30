# ADR-015: Reflexion v2 — Outcome Loop + Top-K Cap + Index

## Status: ACCEPTED (2026-04-13)

## Context

Reflexion v1 (PLAN-003 Item A, Sprint 3) shipped lessons CRUD +
ranking + benchmark-driven writes. It had no feedback loop: lessons
accumulated but the framework never learned which ones helped. PLAN-006
debate round 1 (R-VP4) flagged that v1 fails the 10× scale rule — at
10k lessons, per-spawn cross-archetype scoring becomes O(n) file walk
with regex parsing.

PLAN-006 Phase 4 (ADR-015 + ADR-017) closes this gap **partially** —
outcome tracking + top-K cap + index in Sprint 6; pruning is advisory
only (see ADR-017).

## Decision Drivers

- **10× scale**: spawns at 10k lessons must not spend O(n) on every
  prompt build. Must cap work and use an index.
- **Signal, not sampling**: hit_count/miss_count are integer counters
  written on each benchmark application — no stats estimation needed.
- **Reversibility**: outcome tracking is additive (new fields on
  Lesson), does not delete existing lessons, does not break v1 format.
- **Observability**: every outcome emits an audit event
  (`lesson_outcome`) so `audit-query.py lessons` can surface health
  over time.

## Options Considered

### Option A: Statistical prior (Bayesian beta) — per-lesson posterior

- **Pros:** proper handling of sample size; principled down-weighting
  of low-signal lessons.
- **Cons:** complexity; requires tracking prior; fails PLAN-006's
  stdlib-only constraint without dependencies.

### Option B: Integer counters + threshold rule (chosen)

- **Pros:** simple; stdlib-only; n<3 → use neutral weight 1.0; n≥3 →
  weight = 0.5 + hit_rate (range [0.5, 1.5]); confirmed winners
  outrank untested, confirmed losers down-rank below untested.
- **Cons:** coarse; no confidence interval.

### Option C: No outcome loop (status quo)

- **Pros:** zero cost.
- **Cons:** Reflexion can't learn from outcomes; lessons grow unbounded
  in utility-weighted influence.

## Decision

**Option B.** Integer counters + piecewise hit-rate weighting + hard
top-K cap + `lessons/index.json`.

### Schema extension

`Lesson` dataclass adds:
- `hit_count: int = 0` — successes attributed to this lesson
- `miss_count: int = 0` — failures attributed to this lesson
- `last_outcome_at: str = ""` — ISO 8601 of most recent hit/miss

`Lesson.hit_rate()` returns `None` when `n < 3` (low-signal guard)
and `hits / n` otherwise.

### Ranking formula (PLAN-006 Phase 4)

```
score = archetype_match × scope_overlap × recency_decay × hit_weight

hit_weight:
  - 1.0 if hit_rate() is None (untested, n<3)
  - max(0.1, 0.5 + hit_rate()) otherwise
```

Piecewise weighting:
- Untested (n<3): hw = 1.0
- Proven winner (hr=1.0): hw = 1.5 → **outranks untested**
- Neutral (hr=0.5): hw = 1.0
- Confirmed loser (hr=0.0): hw = 0.5 → **down-weighted below untested**

Floor at 0.1 prevents total suppression — ADR-017 handles deletion.

### Top-K cap

```python
def get_top_k(archetype, keywords, k=50, base_dir=None) -> List[Lesson]:
    # Hard ceiling: K ≤ 50 regardless of caller request
```

`rank_lessons` (v1 API) delegates to `get_top_k(..., k=3)` — preserves
injection-path budget. `get_top_k` with K=50 is used by future callers
(Sprint 7 confidence gate, dashboards).

### Scaling envelope

This design is valid up to **N=5000 lessons**. Beyond that:
- Full directory scan cost dominates even with top-K cap
- Index lookup needs to be keyed (current index is flat list)
- Revisit with new ADR

### Audit emission

`_lib/audit_emit.emit_lesson_outcome()` — action `lesson_outcome`.
Per SPEC/v1/audit-log.schema.md §Additivity, adding a new action
literal bumps MINOR but keeps `event_schema` value `"v2"` (matches
ADR-011 pattern).

### Index file

`lessons/index.json` regenerated on every `write_lesson` /
`record_outcome` call, under existing filelock. Structure:

```json
{
  "generated_at": "2026-04-13T...",
  "lesson_count": N,
  "lessons": [
    {"id": "...", "archetype": "...", "scope_tags": [...],
     "hit_count": X, "miss_count": Y, "created_at": "..."}
  ]
}
```

Sprint 6 consumers: `prune-lessons.py` (walks index for candidates).
Sprint 7 consumers: faster `get_top_k` without full file reads.

## Consequences

### Positive

- Lessons can be **ranked by evidence**, not just recency + scope.
- Proven winners rank above untested; confirmed losers rank below.
- Top-K cap bounds per-spawn work regardless of corpus size.
- Index file pre-aggregates for dashboards + pruning.
- `lesson_outcome` events give time-series view of lesson health.

### Negative

- Benchmark runs must decide `hit | miss` classification — ambiguous
  outcomes (partial pass) currently bucket as hit. Sprint 7 may add
  `partial` class.
- Two files written per outcome (lesson JSON + index.json) doubles
  filelock traffic. Measured: negligible at N<1000.
- Tests rely on `hit_rate()` low-signal guard (n<3). If the threshold
  changes, tests update.

### Neutral

- Schema is forward-compat: old readers ignore `hit_count` / `miss_count`;
  new readers tolerate missing fields (default to 0).

## Blast Radius

- `.claude/scripts/lessons.py` (EXTENDED: Lesson dataclass +3 fields;
  new `record_outcome`, `get_top_k`, `build_index` functions; ranking
  weighted by hit_rate)
- `.claude/hooks/_lib/audit_emit.py` (+1 function `emit_lesson_outcome`)
- `.claude/scripts/tests/test_lessons_v2.py` (NEW, 15 tests)
- Index file: `$CEO_LESSONS_DIR/index.json` (NEW artifact, regenerated
  on write/outcome)

**Reversibility:** HIGH. All additive. Revert = remove new functions +
ignore the extra Lesson fields (old Lesson() calls still work).

## Amendment 2026-04-14 — Sprint 9 Phase 3 (Architect path closure)

Sprint 8 Phase 3 wired the Agent Architect to INJECT top-K lessons into
new squad drafts, but no consumer existed to record whether those
lessons helped. Sprint 9 Phase 3 closes the loop with session_id
correlation + undo CLI + back-compat for pre-Sprint-9 events.

### Session-correlated inference rule

The Architect-execute window attribution is tightened from "10-minute
window only" to **"10-minute window AND session_id equality"**.
Without session_id match, the outcome is NOT recorded — this
prevents attribution attacks via unrelated vetos that happen to fire
in the same 10 minutes.

```
def infer_outcome(session_id, spawn_end, events):
    # Returns "hit" or "miss"
    for e in events:
        if e.session_id != session_id: continue       # MUST match
        if not (spawn_end <= e.ts <= spawn_end + 10min): continue
        if e.action == "veto_triggered": return "miss"
        if e.action == "confidence_gate" and e.fail_count > 0:
            return "miss"
    return "hit"
```

Implementation: `.claude/hooks/emit_architect_outcome.py` (separate
file — cleaner than widening `check_agent_spawn.py`).

### New fields on `lesson_outcome` events

Per PLAN-009 P3.5:

- `consumer: "architect" | "benchmark"` — closed enum, see
  `lessons.VALID_CONSUMERS`. New values require SPEC amendment.
- `inference_mode: "window-only" | "session-correlated" | ""` —
  Sprint 9+ Architect paths emit "session-correlated"; older
  benchmark paths emit `""` (pre-Sprint-9 legacy).
- `window_duration_seconds: int` — attribution window (0 = n/a).
- `session_end_reason: "timeout" | "explicit" | "unknown" | ""`.

### Back-compat for pre-Sprint-9 events (A23)

Events emitted before Sprint 9 lack the `consumer` field. Consumers
of the audit log MUST parse missing `consumer` as `"benchmark"`
(single-consumer era default). This is documented in
`SPEC/v1/audit-log.schema.md` v2.2.2.

### Undo CLI (P3.3)

`lessons.undo_outcome(lesson_id, consumer)` ships as an admin-facing
escape hatch for reversing a bad attribution. Decrements the larger
of (hit_count, miss_count) by 1; emits `lesson_outcome_undone` event
(schema v2.3, `_KNOWN_ACTIONS` amended).

### Known bypass — window-only records under session ambiguity

Pre-Sprint-9 `lesson_outcome` events have `inference_mode=""` or
missing. Under session ambiguity (multiple overlapping sessions in
the same 10-min window), window-only records can be attributed
wrongly. Sprint 9 marks these as dirty signal and EXCLUDES them by
default from `audit-query architect-outcomes` — use
`--include-window-only` to opt in.

## References

- PLAN-006 §Phase 4
- PLAN-006/debate/round-1/vp-engineering.md §R-VP4 (10× scale)
- PLAN-006/debate/round-1/consensus.md §K2
- PLAN-009 §Phase 3 P3.1-P3.6 + debate consensus.md §C4/A7/A23
- ADR-011 — Event stream v2.1 additive-action pattern
- ADR-017 — SUPERSEDED by ADR-020 (Sprint 9)
- ADR-020 — Lesson pruning policy v2
- ADR-018 v1.1 — Claim grammar
- ADR-019 — Confidence gate enforcement lifecycle
- Shinn et al. 2023 — Reflexion: Language Agents with Verbal
  Reinforcement Learning

## Enforcement commit

`043de3bfa120` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
