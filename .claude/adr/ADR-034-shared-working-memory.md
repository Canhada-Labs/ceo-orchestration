# ADR-034: Shared Working Memory (Scratchpad)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 7)
**Related:** ADR-027 (unified agent state backend), ADR-005 (event
stream v2), ADR-010 (canonical-edit sentinel), ADR-018 (claim
grammar).

## Context

Agents within a single plan frequently need to hand off structured
notes to later-spawned agents in the same plan. Concrete Sprint-11
examples:

- **Phase 1 → Phase 7** — the adapter parity spike writes
  "canonical-envelope-v2" → true once the schema is frozen, so later
  spawns under the same plan skip re-validation.
- **Agent Architect spawns (Sprint 10 carryover)** — the first spawn
  drafts a squad manifest; a second spawn reads the draft path via a
  shared key instead of re-parsing arguments.
- **Long-running phases with interleaved reviews** — the executor
  leaves a `phase-<N>-status` key that the Owner's `/status` command
  picks up without re-scanning git commits.

Prior to this ADR the only options were:

1. Pass state via agent `prompt` text (brittle; loses on long chains).
2. Write to ad-hoc files inside `.claude/…` (no isolation, no TTL, no
   redaction).
3. Over-load the audit log with "agent-intent" events (audit log is
   an append-only observation stream, not a mailbox).

Debate round-1 §M2 (Security) flagged the single hardest gotcha: any
such shared store where plan-id comes from an env var is
**spoofable** by a misbehaving agent. The store must tie plan-id to
an attested source — the audit-log session linkage is that source.

## Decision drivers

- **Consumer of ADR-027**, not a parallel backend — every byte lives
  in the unified state store (scratchpad is just `store_name="scratchpad"`).
- **Plan-scoped by construction** — filesystem boundary; impossible
  to read PLAN-X from PLAN-Y even with a malicious flag.
- **Attested plan-id** — derived from `audit-log.jsonl`
  `plan_transition` events with matching `session_id`. No env-var
  fallback.
- **Redacted writes** — string values pass through `redact_secrets`
  (inherited from state_store).
- **Size-bounded** — 64 KiB per-key cap (inherited). Scratchpad is
  for notes, not blobs.
- **Rollback-clean** — `executing → draft` rollback drops every key
  for that plan; other transitions keep data for post-mortem.

## Options considered

### Option A — In-memory only (per-session dict)

Keep shared state in a module-level dict inside the Python hook
process. No disk, no audit, no durability.

**Pros:** Dead simple, zero IO cost.
**Cons:**
- Dies at session end — handoff across two spawns in different
  processes is impossible.
- No audit trail, defeating the "explain what each plan is doing" goal.
- Useless in 24-hour-spanning plans (the vast majority of Sprint-11
  work).

**Rejected** — does not solve the hand-off problem it is proposed for.

### Option B — Per-plan JSON/YAML file in `.claude/`

Write a file like `.claude/scratchpad/PLAN-011.yaml` and let agents
read/write it directly.

**Pros:** Human-readable, grepppable.
**Cons:**
- No filelock — concurrent writers corrupt. Reinventing filelock
  violates ADR-002.
- No redaction — secrets land in plaintext in the repo.
- Lives in `.claude/` so it would be committed to git (disaster).
- No TTL / pruning.
- Every surface invents its own schema.

**Rejected** — re-opens the "four bespoke backends" tarpit ADR-027
explicitly closed.

### Option C (CHOSEN) — Consume ADR-027 state_store; add derivation
layer

The scratchpad surface becomes a thin library (`scratchpad_lib.py`)
+ CLI (`scratchpad.py`) + PreToolUse Bash hook
(`check_scratchpad_access.py`) on top of `SqliteStateStore`.

- Reuses the Phase 0 filelock, redaction, TTL, audit machinery.
- Adds one responsibility: derive the plan_id from audit-log session
  linkage so callers cannot spoof via env vars.
- Adds one responsibility: cross-plan guard as a Bash hook so
  explicit `--plan` overrides at the CLI are gated by the session's
  attested plan.
- Adds one rollback primitive (`clear_on_rollback`); wiring into
  actual plan_transition events is deferred to a later sprint (we
  ship the library; a future PostToolUse hook calls it).

**Chosen.**

### Option D — External KV (sqlite shared with other surfaces, Redis, etc.)

**Rejected** — violates ADR-027's per-store isolation (sharing one
sqlite across scratchpad + skill_proposals + skill_index +
session_graph breaks the blast-radius argument that made C the
chosen option for Phase 0).

## Decision

### 1. Contract

- `store_name = "scratchpad"` (ADR-027 alphanumeric slug).
- `plan_id` is always a canonical `PLAN-NNN`.
- Plan-id derivation (normative): walk audit-log `plan_transition`
  events filtered by matching `session_id`; return the `plan_id` of
  the most recent match (linear file order). No env-var fallback.
- Cross-plan override is blocked at `check_scratchpad_access.py`.
  Fail-open when session plan is not derivable (no trust anchor).
- Rollback clear (normative): `clear_on_rollback(plan, "executing",
  "draft")` deletes every key; every other transition is a no-op.

### 2. Public API

    from _lib.scratchpad_lib import (
        PlanIdDerivationError,
        clear_on_rollback,
        open_scratchpad,
        resolve_plan_id,
    )

And the CLI surface:

    scratchpad.py set|get|list|delete|clear [--plan PLAN-NNN] [--json]

Slash command: `/memory scratchpad` (namespace per consensus M8).

### 3. Audit events

All writes/reads/clears emit the ADR-027 `state_store_*` events with
`store_name="scratchpad"`. No new event types.

### 4. Kill switch

`CEO_SOTA_DISABLE=1` (consensus S4) short-circuits the CLI to exit 0
with a "disabled" message. The sqlite file is never opened.

### 5. Non-goals

- **Not** a cross-plan mailbox. Sharing between `PLAN-010` and
  `PLAN-011` is impossible by design — if a workflow needs it, that
  coordination is a lesson or a fresh plan, not scratchpad.
- **Not** a cache for large blobs. 64 KiB cap holds; larger payloads
  belong in files with their own retention policy.
- **Not** an event queue. Consumers polling for changes should rely
  on audit-log events, not scratchpad reads.
- **Not** the plan_transition rollback wirer. This ADR ships the
  primitive; the PostToolUse plan_transition hook that calls into
  `clear_on_rollback` is a Sprint-11-or-later wiring task.

## Consequences

### Positive

- One backend, one filelock, one redaction pipeline, one audit
  vocabulary — inherited from ADR-027 for free.
- Plan-id derivation is attested, not declared. An agent that tries
  `export CEO_CURRENT_PLAN=PLAN-EVIL && scratchpad.py get secret-key`
  gets `PlanIdDerivationError` — env vars are ignored.
- Cross-plan `--plan PLAN-X` attempts are blocked at the Bash hook
  before the CLI even runs.
- 64 KiB cap bounds damage: a scratchpad-stored secret is at most
  64 KiB of redacted text.

### Negative

- **Dependency on audit-log freshness** — derivation requires a
  `plan_transition` event to exist for the session. Brand-new
  sessions (before any plan activity) get `PlanIdDerivationError`.
  Documented; CLI error message explains the fix.
- **No cross-plan workflow** — intentional, but agents crossing
  plans must serialize via file artifacts or fresh plans.
- **Rollback wiring not yet automatic** — callers must invoke
  `clear_on_rollback` explicitly. Sprint 11-or-later PostToolUse hook
  closes this gap; until then, Owner or `/memory scratchpad clear
  --confirm` is the manual path.

### Neutral

- Filesystem footprint: one sqlite + sibling lock per active plan.
  At steady state ≤100 plans × ~10 keys each = trivial.
- No new env var introduced (reuses `CEO_STATE_ROOT`,
  `CLAUDE_SESSION_ID`, `CEO_SOTA_DISABLE`).

## Blast radius

**L2** — one new `_lib` module (~200 LOC), one new CLI (~320 LOC), one
new PreToolUse Bash hook (~190 LOC), one new slash command, one SPEC
file, one ADR, +30 tests. Zero modifications to existing hooks.

**Reversibility:** HIGH. The CLI + hook + library are all additive;
disabling them is a settings.json edit + `rm -rf
$CEO_STATE_ROOT/scratchpad/`.

## Transition timeline

| Milestone | When | Source |
|---|---|---|
| Contract accepted | 2026-04-14 (this commit) | ADR-034 |
| Phase 0 consumed | Sprint 11 Phase 7 | `scratchpad_lib.py` |
| `/memory scratchpad` shipped | Sprint 11 Phase 7 | slash command |
| `check_scratchpad_access.py` registered | End of Group B (CEO) | `.claude/settings.json` |
| Rollback wiring automated | Sprint 11 closeout or Sprint 12 | follow-up PostToolUse hook |

## References

- PLAN-011 Phase 7 task card
- PLAN-011/debate/round-1/consensus.md §M2 + §M7 + §M8 + §S4 + §S5
- ADR-027 — Unified Agent State Backend (Phase 0 contract)
- ADR-005 — Event stream v2 (fail-open observability)
- ADR-010 — Canonical-edit sentinel (Owner-signed mutation pattern)
- `SPEC/v1/scratchpad.schema.md` — normative scratchpad spec
- `SPEC/v1/state-stores.schema.md` — backend envelope + events

## Enforcement commit

`731ca92694b6` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
