# SPEC v1 — state-stores.schema

> **Normative source:** `.claude/hooks/_lib/state_store.py` (reference driver)
> **Spec version:** 1.0.0-rc.1 (PLAN-011 Phase 0, 2026-04-14)
> **Related ADR:** ADR-027 — Unified Agent State Backend

## Summary (normative)

Plan-scoped, redaction-enforced key/value stores used by Sprint-11
surfaces (scratchpad, skill proposals, skill index, session graph) and
any future surface that needs persistent state tied to a `PLAN-NNN`.

### Envelope

```
${CEO_STATE_ROOT:-$HOME/.claude/projects/ceo-orchestration/state}/
    <store_name>/
        <plan_id>.sqlite         # kv storage
        <plan_id>.sqlite.lock    # sibling filelock (fcntl, ADR-002)
        <plan_id>.sqlite-wal     # WAL journal (sqlite-managed)
        <plan_id>.sqlite-shm     # WAL shared memory (sqlite-managed)
```

### Identifiers

| Field | Type | Rules |
|---|---|---|
| `store_name` | string | 1–32 chars, `[A-Za-z0-9_-]` only; no slashes/dots |
| `plan_id`    | string | 1–64 chars, `[A-Za-z0-9_.-]`; MUST NOT start with `.`; MUST NOT contain `..` |
| `key`        | string | free-form; length governed by sqlite TEXT PK (1 GB theoretical) |

Names violating these rules are rejected at `SqliteStateStore.__init__`
with `StateStoreInvalidName`. Validation is **per-argument** — both
`store_name` and `plan_id` are checked.

### Schema (per-plan sqlite file)

```sql
CREATE TABLE kv (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL,
    expires_at INTEGER,           -- epoch seconds, NULL = no expiry
    created_at INTEGER NOT NULL,  -- epoch seconds
    redacted INTEGER NOT NULL     -- 1 if redact_secrets changed the original
);
CREATE INDEX idx_kv_expires ON kv(expires_at);

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
```

Schema additions are MINOR bumps. Column removal / rename is MAJOR
(forbidden within v1). New surfaces SHOULD NOT invent their own
schemas — use the generic `kv` table with structured values (JSON
strings, pickle, etc.) serialized by the caller.

### Value semantics

| Input | Pre-write path | Audit field |
|---|---|---|
| `str` | `_lib.redact.redact_secrets(v, max_chars=0)` → UTF-8 bytes | `redaction_applied = (out != in)` |
| `bytes` | trusted; stored as-is | `redaction_applied = false` |
| other | `TypeError` at caller | — |

Values exceeding `value_max_bytes` (default 64 KiB, per-store-override
allowed) raise `StateStoreValueTooLarge`. **This is NOT fail-open.** A
caller asking for a cap violation means the cap is wrong for that
surface — raise in code, not at audit.

### TTL semantics

- `ttl_seconds=None` → never expires
- `ttl_seconds>0` → expires at `now() + ttl_seconds`
- `ttl_seconds<=0` → `ValueError` at `set()`
- Reads on expired keys return `None` and emit `state_store_read` with
  `found=false`. The row is NOT deleted by `get()` — callers must run
  `prune_expired()` on a schedule (typically after session close or
  via an admin tool).

### Plan rollback semantics

When a plan transitions `executing → draft` (rollback), callers SHOULD
invoke `store.clear_plan()` to zero out the per-plan state. This emits
a `state_store_pruned` event. There is no automatic rollback hook at
this layer — the plan-transition hook will call into state_store in a
follow-up sprint.

### Filelock

Every mutating method and every read path acquires the sibling filelock
(`<plan_id>.sqlite.lock`) via `_lib.filelock.FileLock`. Timeout default
5.0s — longer than audit_emit (2.5s) because sqlite contention is
expected on bursty scratchpad writes.

### Audit events

All three events use `event_schema: "v2"` (additive per ADR-005) and
share the mandatory fields `action`, `store_name`, `plan_id_hash`,
`session_id`, `project`, `ts`, `event_schema`. Nullable `tokens_*`
fields are reserved per the audit-log.schema.md pattern.

| action | per-action required |
|---|---|
| `state_store_write` | `key_hash`, `value_bytes`, `ttl_seconds` (nullable int), `redaction_applied` (bool) |
| `state_store_read` | `key_hash`, `found` (bool) |
| `state_store_pruned` | `keys_pruned_count` (int) |

`plan_id_hash` is `sha256(plan_id)[:16]`. `key_hash` is
`sha256(key)[:16]`. Plaintext `plan_id` / `key` is NEVER audited.

### Fail mode

- **State-mutating paths (set/delete/clear_plan/prune_expired):**
  exceptions propagate. Filelock timeout → `FileLockTimeout`; sqlite
  corruption → `sqlite3.DatabaseError`. State correctness > observability.
- **Audit emission inside state_store:** fail-open (tries/excepts the
  call). Consistent with ADR-005 (framework never blocks on audit).

### Permissions

- `state_root` and per-store dirs: `0o700` (owner-only).
- sqlite files: `0o600` (owner-only). `os.chmod` is best-effort after
  the first `connect()`.

### Back-compat within v1

- Fields added to `state_store_*` events → MINOR bump of SPEC.
- Removing / renaming fields → MAJOR bump (forbidden within v1).
- Adding new action literals scoped to state stores → MINOR bump + new
  ADR.

### Consumer contract

Consumers MAY build derived views (per-plan size, write rate,
redaction-hit rate) by scanning audit-log for `state_store_*` events.
They MUST:
- Tolerate unknown fields (forward-compat).
- Treat `plan_id_hash` as opaque; do not attempt to reverse.
- Handle `ttl_seconds: null` (no expiry).

### Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | Sprint 11 PLAN-011 Phase 0 | Initial envelope + three `state_store_*` events |
