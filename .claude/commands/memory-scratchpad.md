---
command: /memory-scratchpad
alias: /memory scratchpad
description: Read/write plan-scoped shared memory for inter-agent handoff
usage: |
  /memory scratchpad set <key> <value> [--ttl 86400]
  /memory scratchpad get <key>
  /memory scratchpad list
  /memory scratchpad delete <key>
  /memory scratchpad clear --confirm
idempotent: get|list
allowed-tools: Bash
---

# /memory scratchpad — Plan-scoped shared memory

Read/write a plan-scoped key/value store for inter-agent handoff
inside a single `PLAN-NNN`. Consumes the Phase 0 unified state backend
(ADR-027); this command is a thin front door over
`.claude/scripts/scratchpad.py`.

## Scope boundaries

- The **plan** is derived from your current session's audit-log
  (consensus M2). You cannot read or write another plan's scratchpad
  — the `check_scratchpad_access.py` hook blocks cross-plan
  `--plan PLAN-X` overrides.
- Per-key value cap is **64 KiB** (inherited from state_store).
- Secrets in string values are **redacted before write** (bytes are
  trusted). Audit-log records whether redaction mutated the value.

## Arguments

`/memory scratchpad $ARGUMENTS`

| Sub-command | Effect | Exit |
|---|---|---|
| `set KEY VALUE [--ttl SECONDS]` | Write key/value; optional TTL. | 0 ok, 3 plan-derivation fail, 4 over-cap |
| `get KEY` | Read value (empty stdout when missing). | 0 (found or not) |
| `list` | List non-expired keys, one per line. | 0 |
| `delete KEY` | Remove key. | 0 deleted, 3 missing-no-op |
| `clear --confirm` | Drop every key for the plan. | 0 ok, 2 missing `--confirm` |

Add `--json` anywhere for machine-readable output.

## Procedure

### Step 1 — Decide mode

Inspect `$ARGUMENTS`:

- first token = sub-command (`set|get|list|delete|clear`)
- remaining tokens = sub-command args
- `--json` passthrough

### Step 2 — Invoke backing CLI

```bash
python3 .claude/scripts/scratchpad.py $ARGUMENTS
```

Surface stdout verbatim and propagate the exit code.

### Step 3 — Interpret exit codes

- `0` — success (or no-op in kill-switch mode; stdout says `disabled`).
- `2` — usage error (e.g. `clear` without `--confirm`, negative `--ttl`).
- `3` — plan derivation failed OR delete of missing key. Print
  stdout; it already contains the reason.
- `4` — value > 64 KiB cap. Tell the user to chunk / use a file.

## Idempotency contract (consensus M7)

- `get KEY` and `list` are **read-only** — trivially idempotent.
- `set KEY VALUE` **overwrites** — calling twice leaves the second
  value (not appended).
- `delete KEY` is **idempotent with signaling**: exit 3 with a
  friendly "no-op" message the second time.
- `clear --confirm` is **destructive and requires confirmation**
  each call — never idempotent by design.

## Kill switch

`CEO_SOTA_DISABLE=1` makes every sub-command exit 0 with a
`disabled` message and never touches sqlite. Use this if you suspect
a regression in the state backend.

## Fail-open

If `scratchpad.py` is missing (old install), report the gap and stop
— do not silently succeed.

## Related

- `.claude/hooks/_lib/scratchpad_lib.py` — library (plan-id derivation,
  rollback clear).
- `.claude/hooks/_lib/state_store.py` — Phase 0 unified backend.
- `.claude/adr/ADR-027-unified-agent-state-backend.md` — backend contract.
- `.claude/adr/ADR-034-shared-working-memory.md` — scratchpad decision.
- `SPEC/v1/scratchpad.schema.md` — normative spec.
