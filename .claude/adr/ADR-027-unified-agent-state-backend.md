# ADR-027: Unified Agent State Backend

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 0)
**Related:** ADR-001 (runtime state directory), ADR-002 (hooks package layout), ADR-005 (event stream v2), ADR-010 (canonical-edit sentinel), ADR-015 (Reflexion v2 outcome loop)

## Context

Sprint 11 introduces four distinct surfaces that need to persist small
amounts of state scoped to a specific plan:

1. **Phase 7 — shared scratchpad** — agents within the same plan
   exchange structured notes (phase-complete flags, extracted facts,
   handoff payloads). M2 in consensus: plan-id must be derived from
   audit-log session linkage, filelock-safe, 64 KiB per-key cap,
   cleared on `executing → draft` rollback.
2. **Phase 4 — skill-patch proposals** — pending `SP-NNN` records
   awaiting Owner GPG signature. Needs queryable list of proposals per
   plan, TTL expiry for stale proposals, audit trail.
3. **Phase 2 — skill-retrieval index metadata** — which skill mtimes
   were seen at index-build time, checksum of the index, stale flag.
   Ephemeral but plan-scoped for per-session retrieval.
4. **Phase 11 — session graph snapshots** — derived view of the plan's
   session history. Must be *strictly derived* from audit-log (M3:
   no new source of truth), encrypted at rest, 30-day default retention.

Absent a shared backend, each surface would otherwise invent its own
file format, locking strategy, redaction pipeline, TTL mechanism, and
audit-log event vocabulary. That produces four inconsistent invariants
and four sets of tests — and would ship with subtle fail-open divergence
between them.

The debate round-1 consensus (§H1, VPE + Security + Backend all HIGH)
demanded that Phase 0 land **before** Phases 2/4/7/11 execute so they
can build on a single contract. ADR-027 documents that contract.

## Decision drivers

- **Consistency** — one redaction path, one filelock primitive, one
  audit-log vocabulary across four consumers.
- **Plan-scoping** — writes to `PLAN-010` must never leak into
  `PLAN-011`. File-system boundary (separate sqlite per plan) is the
  strongest achievable isolation with stdlib.
- **Auditability** — every write and read must be traceable in
  `audit-log.jsonl` so `audit-query.py` can surface per-plan activity.
- **Redaction-by-default** — string values pass through
  `redact_secrets` before landing on disk. No opt-out (bytes values
  bypass because the caller is asserting "I already know what this is").
- **Stdlib-only** — sqlite3 + fcntl + hashlib. Zero new dependencies
  (ADR-002 constraint).
- **Fail mode** — state correctness > observability. Mutations raise;
  audit inside state_store is fail-open.

## Options considered

### Option A — Plain JSONL files per surface

Each surface picks its own `<plan>.jsonl` layout and appends events.

**Pros:** zero schema; human-readable.
**Cons:**
- No indexed lookup — `get(key)` scans the whole file.
- Concurrent writer safety requires reinventing filelock each time.
- TTL requires compaction logic per surface.
- Ambiguous failure semantics (partial writes?).
- Four redaction pipelines to audit.

**Rejected** — duplicates too much machinery.

### Option B — Single shared sqlite file per project

One file, one WAL, schema distinguishes store by a `store_name` column.

**Pros:** single connection per process; easy to query cross-store.
**Cons:**
- **Plan isolation is a query convention**, not a filesystem boundary —
  a bug in a caller's WHERE clause leaks across plans.
- Single WAL means all surfaces block on each other's write bursts.
- File grows unbounded — no "drop this plan's data" natural operation.
- Harder to encrypt per-plan (Phase 11 requirement).

**Rejected** — violates the plan-scoping invariant.

### Option C (CHOSEN) — Per-store, per-plan sqlite file

```
<state_root>/<store_name>/<plan_id>.sqlite
```

One sqlite file per (store, plan) pair. Generic `kv` schema inside.

**Pros:**
- Plan isolation is a filesystem boundary — impossible to query
  accidentally across plans.
- Rolling back a plan = `rm <plan>.sqlite*`.
- Per-plan file permissions and encryption (Phase 11) natural.
- WAL contention is bounded to one store × one plan at a time.
- sqlite schema is generic; callers serialize their own value shapes.

**Cons:**
- Cross-store / cross-plan analytics require union queries (acceptable
  — we audit per-write via `state_store_*` events; analytics ride on
  the audit log, not the sqlite files).
- sqlite WAL produces two sibling files (`-wal`, `-shm`). Must be
  documented so `rm <plan>.sqlite` isn't the whole cleanup story.

**Chosen** — strongest isolation boundary with stdlib.

### Option D — External KV (Redis / embedded LMDB)

**Rejected** — violates ADR-002 stdlib-only constraint. Redis adds a
deployment dependency the framework is designed to avoid.

## Decision

### 1. Contract

- `store_name` (1–32 chars, `[A-Za-z0-9_-]`): short slug identifying
  the store (`scratchpad`, `skill_proposals`, `skill_index`, `session_graph`).
- `plan_id` (1–64 chars, `[A-Za-z0-9_.-]`, no leading `.`, no `..`):
  canonical `PLAN-NNN` string.
- Path: `${CEO_STATE_ROOT:-$HOME/.claude/projects/<project>/state}/<store>/<plan>.sqlite`
- Schema: single `kv` table with `(key TEXT PK, value BLOB, expires_at
  INTEGER NULL, created_at INTEGER, redacted INTEGER)`.
- Mandatory redaction: string values pass through
  `_lib.redact.redact_secrets` before write. `redacted=1` if the
  regex mutated the value. Bytes values are trusted (not redacted).
- Value cap: 64 KiB per-key default; override per-store via ctor arg.
- TTL: opt-in; stored per-row; expired rows are excluded from reads but
  require `prune_expired()` for physical deletion.
- Filelock: sibling `<plan>.sqlite.lock` via `_lib.filelock.FileLock`
  (ADR-002). Timeout 5.0s.

### 2. Audit events

Three new actions in `_KNOWN_ACTIONS` (additive, event_schema stays `v2`):

- `state_store_write` — `store_name`, `plan_id_hash`, `key_hash`,
  `value_bytes`, `ttl_seconds` (nullable), `redaction_applied` (bool).
- `state_store_read` — `store_name`, `plan_id_hash`, `key_hash`,
  `found` (bool).
- `state_store_pruned` — `store_name`, `plan_id_hash`, `keys_pruned_count`.

`plan_id_hash` and `key_hash` are SHA-256 prefixes (16 chars). Plaintext
ids/keys are NEVER in audit.

### 3. Fail mode

- Mutations (`set` / `delete` / `prune_expired` / `clear_plan`):
  exceptions propagate. Filelock timeout, sqlite corruption, quota
  violations all raise.
- `get` raises on sqlite errors but returns `None` on missing/expired
  (side-effect-free read path).
- Audit emission is fail-open (wrapped in try/except), matching ADR-005.

### 4. Rollback

On plan `executing → draft` rollback, callers invoke
`store.clear_plan()` which `DELETE FROM kv` and emits
`state_store_pruned`. A follow-up sprint will wire this into the
plan-transition hook automatically.

### 5. Where this is consumed

- **Phase 7 (scratchpad)** — `scratchpad.py` wraps
  `SqliteStateStore("scratchpad", plan_id)` with a CLI.
- **Phase 4 (skill proposals)** — `skill-patch-propose.py` uses
  `SqliteStateStore("skill_proposals", plan_id)` for pending records
  (files under `.claude/proposals/` remain the canonical artifact;
  sqlite stores just the index).
- **Phase 2 (skill index)** — `skill-index-build.py` uses
  `SqliteStateStore("skill_index", "shared")` for metadata (plan_id
  special-cased to `"shared"` because the index is global).
- **Phase 11 (session graph)** — strictly derived from audit-log; the
  state store holds only the snapshot checksum + ttl for the current
  session's working copy.

### 6. Explicit non-goals

- **Not** a general-purpose cache. Surfaces with throughput > 100 ops/s
  should use in-process data structures and flush snapshots periodically.
- **Not** a message queue. No publish/subscribe semantics. Surfaces
  needing event delivery should audit-emit.
- **Not** cross-process synchronization beyond filelock mutual
  exclusion. If surface X needs "wait until surface Y writes key K",
  that's a separate coordination problem.
- **Not** encrypted at this layer. Phase 11 adds per-file encryption
  for `session_graph` store via a separate wrapper; other stores stay
  plaintext (values are already redacted).

## Consequences

### Positive

- One implementation surface, one set of filelock semantics, one
  redaction pipeline, one audit vocabulary.
- Plan isolation is a filesystem boundary — Sprint-12+ surfaces inherit
  it for free.
- sqlite WAL gives concurrent-reader / single-writer semantics with
  zero additional code.
- 64 KiB per-key cap prevents accidental blob storage misuse.
- TTL + prune mechanics are implemented once and shared.
- Adding a new store in Sprint 12+ = one line in the caller + zero
  new ADR / tests for plumbing.

### Negative

- **Per-plan file count grows linearly** with plans × stores. At
  steady state we expect ≤5 stores × ≤100 active plans = 500 sqlite
  files + lock siblings. `ls state/scratchpad/` stays readable.
- **WAL sibling files** (`.sqlite-wal`, `.sqlite-shm`) mean naive
  cleanup scripts that do `rm *.sqlite` leak space. Documented in
  schema; `clear_plan()` is the supported operation, not `rm`.
- **Redaction is silent from the caller's perspective.** If a caller
  passes `"Bearer abc123..."`, the stored value is
  `"Bearer [TOKEN]"`. Audit `redaction_applied=true` is the only
  signal. Documented in state_store.py and SPEC.
- **sqlite3 connection is not thread-safe** — callers opening a store
  in one thread and using it in another will get
  `sqlite3.ProgrammingError`. Documented; if thread-sharing becomes
  necessary Sprint 12+ adds a connection pool.

### Neutral

- No new env vars beyond `CEO_STATE_ROOT` (optional override) and
  `CEO_PROJECT_NAME` (optional override; defaults to
  `"ceo-orchestration"`). Both additive.
- No impact on existing hooks — Phase 0 is library-only.

## Blast radius

**L2** — one new `_lib` module (~350 LOC), three new audit-event
emitters, one new SPEC file, one ADR. Plus ~25 new tests. No existing
hook modified.

**Reversibility:** HIGH. If the design turns out wrong in Sprint 12,
callers are already isolated from the driver via
`SqliteStateStore` — swapping to a different backend means changing
one class, not four surfaces.

## Transition timeline

| Milestone | When | Source |
|---|---|---|
| Contract accepted | 2026-04-14 (this commit) | ADR-027 |
| Wired by Phase 7 (scratchpad) | Group B | PLAN-011 Phase 7 |
| Wired by Phase 4 (skill proposals) | Group B | PLAN-011 Phase 4 |
| Wired by Phase 2 (skill index) | Group B | PLAN-011 Phase 2 |
| Wired by Phase 11 (session graph) | Group A | PLAN-011 Phase 11 |

## References

- PLAN-011 §Phase 0 (new phase added post-debate)
- PLAN-011/debate/round-1/consensus.md §H1 + §M2
- ADR-001 — runtime state directory convention (`$HOME/.claude/projects/<project>/state`)
- ADR-002 — hooks package layout (stdlib-only, Python ≥3.9)
- ADR-005 — event stream v2 (fail-open on audit, additive semantics)
- ADR-010 — canonical-edit sentinel (precedent for signed-state-change gating)
- `SPEC/v1/state-stores.schema.md` — normative spec
- `.claude/hooks/_lib/state_store.py` — reference driver
- `.claude/hooks/_lib/audit_emit.py` — `emit_state_store_{write,read,pruned}`

## Enforcement commit

`29724af9cb4e` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
