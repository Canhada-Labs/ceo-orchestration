# SPEC v1 — scratchpad.schema

> **Normative source:** `.claude/hooks/_lib/scratchpad_lib.py` +
> `.claude/scripts/scratchpad.py` (reference driver)
> **Spec version:** 1.0.0-rc.1 (PLAN-011 Phase 7, 2026-04-14)
> **Related ADRs:** ADR-027 (unified state backend), ADR-034 (shared
> working memory).
> **Depends on:** `SPEC/v1/state-stores.schema.md` (store_name =
> `"scratchpad"`).

## Summary (normative)

The scratchpad surface is a plan-scoped key/value store used by
agents within the same `PLAN-NNN` to hand off structured notes (phase
completion flags, extracted facts, handoff payloads). It is a thin
surface on top of the unified state backend; no new storage schema,
no new filelock primitive, no new redaction pipeline. Everything
delegates to `state_store.py`.

## Envelope

Identical to `state-stores.schema.md` with `store_name="scratchpad"`:

```
${CEO_STATE_ROOT:-$HOME/.claude/projects/<project>/state}/
    scratchpad/
        <plan_id>.sqlite
        <plan_id>.sqlite.lock
```

## Plan-id derivation (normative)

A scratchpad call that does NOT pass `--plan PLAN-NNN` MUST derive
the effective plan id from the current session's audit-log linkage:

1. Read `CLAUDE_SESSION_ID` from the process env.
2. Scan `audit-log.jsonl` for `plan_transition` events where
   `session_id` equals the current session id.
3. Return the `plan_id` of the MOST RECENT matching event (linear
   file order; timestamps are not re-sorted).

If any step fails, implementations MUST raise a typed error and
propagate it to the caller. **Implementations MUST NOT fall back to
`CEO_CURRENT_PLAN` or any other env var** (consensus M2; env vars are
trivially spoofable by a misbehaving agent with subshell execution).

Reference: `_lib.scratchpad_lib.resolve_plan_id`,
`PlanIdDerivationError`.

## Cross-plan isolation (normative)

A CLI invocation with `--plan PLAN-X` MUST be blocked at the
`check_scratchpad_access.py` PreToolUse Bash hook when the current
session derives to a different plan. The block reason MUST include
both the requested and derived plan ids.

When the session plan cannot be derived (empty audit log, unset
session id), the hook fails open (no trust anchor to compute a
mismatch). The CLI itself still refuses `--plan`-less calls in that
state.

## Value semantics (normative)

Inherited from `state-stores.schema.md`:

- String values: `_lib.redact.redact_secrets(v, max_chars=0)` before
  write, UTF-8 encoded.
- Byte values: stored as-is (caller asserts known-safe).
- Per-key cap: default 64 KiB (`DEFAULT_VALUE_MAX_BYTES`); over-cap
  writes raise `StateStoreValueTooLarge`. **Not fail-open.**
- Other types (int, dict, list): `TypeError` at caller — the CLI
  accepts strings only; machine callers that need richer types
  serialize them (JSON string, etc.) before calling.

## TTL semantics

- `ttl_seconds=None` → never expires.
- `ttl_seconds > 0` → expires at `now + ttl_seconds`.
- `ttl_seconds <= 0` → `ValueError` at `set()` (CLI maps this to
  exit 2).

## Clear-on-rollback (normative)

When a plan transitions `executing → draft` (rollback), callers
invoke `scratchpad_lib.clear_on_rollback(plan_id, "executing",
"draft")`. This delegates to `SqliteStateStore.clear_plan()` which
issues `DELETE FROM kv` under the plan's filelock and emits a
`state_store_pruned` event.

Every other transition (including `executing → done`, `executing →
abandoned`, `reviewed → executing`, etc.) is a **no-op** and returns 0.
This is deliberate: completed and abandoned plans retain their
scratchpad for post-mortem.

The actual wiring into `plan_transition` events (i.e. a hook that
calls `clear_on_rollback` automatically) is out-of-scope for Phase 7;
this library exposes the primitive. The `check_plan_edit.py` hook
already emits `plan_transition` events; a future sprint registers a
PostToolUse hook that reads those and calls `clear_on_rollback`.

## CLI contract

Reference implementation: `scripts/scratchpad.py`. Sub-commands:

| Command | Args | Output | Exit |
|---|---|---|---|
| `set` | `KEY VALUE [--ttl N]` | human or JSON | 0/3/4 |
| `get` | `KEY` | value on stdout or not-found line | 0 |
| `list` | — | one key per line | 0 |
| `delete` | `KEY` | ok / no-op line | 0/3 |
| `clear` | `--confirm` | keys_cleared line | 0/2 |

All sub-commands accept:

- `--plan PLAN-NNN` — explicit plan override (gated by the hook).
- `--json` — single-line JSON payload on stdout.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | success (or kill-switch no-op) |
| 2 | usage error (missing flag, non-positive TTL, `clear` without `--confirm`) |
| 3 | plan derivation failed OR delete of missing key |
| 4 | value over 64 KiB cap |

### JSON output shape

```
{
  "kind": "set|get|list|delete|clear|disabled|error",
  "plan_id": "PLAN-NNN",
  "key": "<key or null>",
  "found": true|false,             // get only
  "value": "<utf-8 string>",       // get only, when found + decodable
  "value_b64": "<base64>",         // get only, when binary
  "bytes": <int>,                  // set/get
  "ttl_seconds": <int|null>,       // set
  "keys": [...],                   // list
  "count": <int>,                  // list
  "deleted": true|false,           // delete
  "keys_cleared": <int>,           // clear
  "message": "<human readable>",   // error|disabled
  "reason": "CEO_SOTA_DISABLE=1"   // disabled
}
```

## Kill switch

`CEO_SOTA_DISABLE=1` short-circuits every CLI sub-command to exit 0
with `{"kind":"disabled"}` (JSON mode) or `scratchpad: disabled
(CEO_SOTA_DISABLE=1)` (human mode). The sqlite file is never opened
in this mode.

## Audit events

Scratchpad operations produce the standard `state_store_*` events
defined in `state-stores.schema.md`. The `store_name` field is always
`"scratchpad"`. No new event types are introduced by this surface.

## Consumer contract

- Tolerate additive JSON fields in machine output.
- Do not depend on key ordering in `list` beyond "sqlite default"
  (current reference sorts alphabetically).
- Treat `plan_id` in event payloads as canonical `PLAN-NNN` strings.

## Version history

| SPEC version | Source | Notes |
|---|---|---|
| 1.0.0-rc.1 | Sprint 11 PLAN-011 Phase 7 | Initial scratchpad surface, plan-id derivation, cross-plan guard, clear-on-rollback primitive |
