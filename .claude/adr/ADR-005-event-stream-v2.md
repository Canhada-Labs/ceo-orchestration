# ADR-005: Promote audit-log.jsonl to typed event stream v2

## Status: ACCEPTED (2026-04-12)

## Context

PLAN-004 Phase 1 consensus finding C5 (VP Ops R-OBS1 + AI R-AI2): the
audit log today emits a single `action: "agent_spawn"` type. We have no
machine-readable record of debate rounds, plan status transitions, veto
triggers, benchmark runs, or lesson writes. Every view of framework
activity must be reconstructed from git log + filesystem + prose.

A competing framework ships many small state files
(`patterns.md`, `gotchas.md`, `feedback.json`, `error-tracking.json`,
etc.). That approach fragments schema, locking, rotation, and consumer
code. VP Eng P2 argued: one typed event stream > many ad-hoc files.

Reflexion lessons.py, the upcoming dashboard (Phase 5), staleness
checker (Phase 6), and future per-spawn cost accounting all need a
canonical event stream to read from.

## Decision Drivers

- **Additivity.** The existing JSONL must keep working unchanged for
  v1 `agent_spawn` consumers. No v1 → v2 migration may be forced on
  adopters.
- **Discoverability.** An event type MUST be discriminator-addressable
  (`action` field) so consumers can filter without parsing prose.
- **Fail-open.** Emission failures write a breadcrumb and return
  silently — observability NEVER blocks the session.
- **Stdlib-only.** No new dependencies. fcntl.flock via existing
  `_lib/filelock.py`.
- **Concurrency.** All writers share the same lock file
  (`audit-log.lock`) as `audit_log.py`.
- **Future cost accounting.** AI specialist P5 wants per-event token
  counts. Reserving nullable fields now is free; adding them later
  forces consumer revalidation.

## Options Considered

### Option A: One canonical JSONL, typed `action` discriminator (chosen)

- **Pros:** single SoT, one locking primitive, one rotation policy,
  one consumer API (`iter_events`), additive (v1 readers still work),
  dashboard + lessons + staleness all derive from it.
- **Cons:** schema drift risk if event families explode; mitigated by
  freezing v2 at 6 families (ADR-required to add a 7th).

### Option B: One file per event family (`audit-log.jsonl`, `debate-events.jsonl`, …)

- **Pros:** no discriminator parsing; clean per-family schemas.
- **Cons:** N lock files, N rotation policies, N readers, harder to
  correlate across families. Exactly the competing-framework pattern we rejected.

### Option C: SQLite database

- **Pros:** typed columns, indexed queries, transactional.
- **Cons:** breaks stdlib-only ethos (sqlite3 is stdlib but file format
  isn't grep-friendly); loses append-only simplicity; tools like `jq`
  stop working.

## Decision

**Option A.** Promote `audit-log.jsonl` to a typed event stream with
the following 6 known actions (the `_KNOWN_ACTIONS` set in
`_lib/audit_emit.py`):

1. `agent_spawn` — **v1, unchanged.** Emitted by `audit_log.py` PostToolUse hook.
2. `debate_event` — emitted during `/debate` cycles (start / agent-done / consensus).
3. `plan_transition` — emitted by `check_plan_edit.py` when a legal status transition is observed.
4. `veto_triggered` — emitted by any governance hook on block path.
5. `benchmark_run` — emitted by `run-skill-benchmark.py` on completion.
6. `lesson_write` — emitted by `lessons.py` when corpus grows.

All v2 events include:
- `event_schema: "v2"` discriminator
- `action: <one of six literals>`
- `ts: ISO 8601 UTC Z`
- reserved nullable `tokens_in`, `tokens_out`, `tokens_total` fields

v1 `agent_spawn` events do NOT carry `event_schema` (their absence is the
v1 marker). Consumers treat missing `event_schema` as v1.

### Schema additivity rules

- **Adding a field to an existing event type** → additive, no bump.
- **Removing or renaming a field** → MAJOR bump of `event_schema` (forbidden within v2).
- **Adding a new event type** → requires a new ADR appending to this one.
- **Reserving nullable fields** → permitted at any time.

### Log rotation (consensus C5)

- Rotate at 10 MB OR 30 days, whichever first (env override
  `CEO_AUDIT_LOG_ROTATE_BYTES`, default 10 MB).
- Rotated archive: `audit-log-YYYY-MM.jsonl`, collision → `-1`, `-2`.
- Rotation happens UNDER the lock so no writer races past a rename.
- `audit-query.py --include-rotated` reads across live + archived.

### Lessons concurrency (consensus C5 + AI Unseen §2)

`lessons.py` writes share `audit-log.lock`. Future standalone lesson
files MUST use the same lock primitive to prevent corruption when two
sessions run concurrently.

## Consequences

### Positive

- One schema, one consumer API (`audit_emit.iter_events(action_filter=...)`).
- Dashboard (Phase 5), metrics (Phase 6), staleness (Phase 6) all derive
  from this single stream without adding state.
- Future per-spawn cost accounting requires zero schema revalidation.
- v1 consumers (existing `audit-query.py` queries) continue to work.

### Negative

- Event family count capped at 6 in v2; growth requires an ADR.
- Ad-hoc debugging via `grep` on one file still works but now needs
  `.action` discriminator filter to focus.
- Adding a producer to a hook = small risk of hot-path overhead (mitigated:
  all emitters are stdlib + <10 KB per event + non-blocking writes).

### Neutral

- Consumer code that reads the log must tolerate unknown `action` values
  (already a contract per AUDIT-LOG-SCHEMA.md §2 forward-compat).

## Blast Radius

**Modules affected:**
- `.claude/hooks/_lib/audit_emit.py` (NEW, ~300 LOC + 16 tests)
- `.claude/plans/AUDIT-LOG-SCHEMA.md` (§11 v2 addendum)
- `.claude/hooks/check_agent_spawn.py` (call `emit_veto_triggered` on block)
- `.claude/hooks/check_plan_edit.py` (call `emit_plan_transition` on legal transition)
- `.claude/scripts/audit-query.py` (add v2 sub-commands: debate, plans, vetoes, benchmarks, lessons)
- Future Phase 5/6/7 consumers

**Reversibility:** MEDIUM — the `audit_emit.py` module is additive
and fail-open; disabling the v2 writers leaves the log readable by v1
consumers. Removing v2 events that have been written = lossy (git revert
removes the module; log entries persist in the out-of-repo JSONL).

## References

- PLAN-004 §3 Phase 1
- PLAN-004/debate/round-1/consensus.md §C5
- AUDIT-LOG-SCHEMA.md (v1 schema, unchanged)
- ADR-001 (runtime state directory) — event stream lives there
- ADR-002 (hooks package layout) — `_lib/` placement rule

## Enforcement commit

`a8b46294e6a8` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
