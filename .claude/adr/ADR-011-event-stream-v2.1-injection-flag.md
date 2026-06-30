# ADR-011: Event stream v2.1 — `injection_flag` action

**Status:** ACCEPTED
**Date:** 2026-04-13
**Sprint:** 5 Phase 5
**Supersedes:** none
**Extends:** ADR-005 (event stream v2)

## Context

PLAN-005 Phase 5 (B.4) introduces an advisory prompt-injection scanner
(`scan-injection.py`) and an opt-in PreToolUse hook
(`check_read_injection.py`) that flags files likely crafted to subvert
an LLM's instructions when read.

For the scanner to be useful operationally, its findings must be
queryable: how often does Read content trigger the scanner, which
families dominate, which sources, etc. ADR-005 locked the v2 audit
event stream with 5 actions (`agent_spawn`, `debate_event`,
`plan_transition`, `veto_triggered`, `benchmark_run`, `lesson_write`).
We need a 7th.

## Decision drivers

- **Forward compat.** Adding a new `action` literal is the additive
  evolution path explicitly preserved by ADR-005 §1.
- **Advisory only.** This event documents observation, never
  enforcement. The scanner cannot block; the hook cannot block.
- **Aggregation-friendly.** Operators want family-level counts +
  per-source breakdowns. The schema bakes both in.

## Decision

Introduce a **v2.1** action: `injection_flag`. The version bump is
PATCH (consumers tolerating unknown actions are unaffected).

### Schema

```json
{
  "ts": "2026-04-13T12:34:56Z",
  "event_schema": "v2",
  "action": "injection_flag",
  "source": "<file path or '<stdin>'>",
  "family_counts": {
    "direct_override": 2,
    "role_injection": 1
  },
  "match_count": 3,
  "bytes_scanned": 4096,
  "truncated": false,
  "triggered_by_tool": "Read",
  "snippet_preview": "<redacted, ≤200 chars>",
  "session_id": "<optional>",
  "project": "<CLAUDE_PROJECT_DIR>",
  "tokens_in": null,
  "tokens_out": null,
  "tokens_total": null
}
```

### Field semantics

| Field | Type | Notes |
|---|---|---|
| `source` | string | File path scanned, or sentinel `<stdin>` for CLI use |
| `family_counts` | object | Map of pattern family → hit count |
| `match_count` | integer | Total matches across all families |
| `bytes_scanned` | integer | Bounded at 1 MiB by the scanner |
| `truncated` | boolean | True if input exceeded the scan cap |
| `triggered_by_tool` | string | Originating tool (`Read`, `Bash`, future) |
| `snippet_preview` | string | Redacted snippet of the highest-confidence hit |

### Pattern families (locked in v2.1)

The scanner ships with 6 families. New families MAY be added in future
PATCH versions; removals require a MINOR bump per SemVer policy
(ADR-007).

| Family | Examples |
|---|---|
| `direct_override` | "ignore previous instructions", "new system prompt:" |
| `role_injection` | "I am the CEO", "<system>", "from now on you are" |
| `instruction_disclosure` | "show your prompt", "what are your rules" |
| `action_override` | "execute the following", "curl ... \| bash" |
| `tool_smuggling` | `<tool_use>`, `"function_call":` |
| `encoded_payload` | base64-ish blob ≥120 chars, hex blob ≥120 chars |

### Producers

| Producer | When |
|---|---|
| `check_read_injection.py` (PreToolUse Read hook) | On every Read of a non-skipped file with at least one match |
| Future hooks may emit similarly | (e.g. WebFetch result scanning) |

### Consumers

`audit-query.py` `vetoes` and `metrics` sub-commands surface
`injection_flag` aggregate counts. A future `injections` sub-command
MAY ship in Sprint 6 if usage warrants per-source / per-family drill-down.

## Consequences

### Positive

- Operators have a single audit channel for both real vetoes
  (`veto_triggered`) and advisory observations (`injection_flag`),
  queried via the same tooling.
- Pattern family additions are PATCH-version events.
- The advisory contract is enforced at the schema: there is no
  `decision: block` field — the event records observation only.

### Negative

- `family_counts` is a free-form map, not enumerated. Consumers must
  tolerate new families gracefully (the v2 forward-compat clause
  already covers this).
- The hook + audit emission means a noisy file produces an audit row
  on every Read. Aggregation-friendly tooling absorbs this; raw-tail
  monitors must filter.

### Neutral

- The hook is opt-in. The default `settings.json` does NOT wire it.
  Adopters who care about prompt safety enable it explicitly.

## Blast radius

L1:
- `_lib/audit_emit.py` — adds `emit_injection_flag()` + `injection_flag`
  to `_KNOWN_ACTIONS`
- `.claude/hooks/check_read_injection.py` (NEW)
- `.claude/scripts/scan-injection.py` (NEW)
- `AUDIT-LOG-SCHEMA.md` + `SPEC/v1/audit-log.schema.md` — append the row
- Tests + fixtures (NEW)

**Reversibility:** HIGH — the action literal can be removed in a future
MAJOR; the hook is opt-in (deletion is invisible to non-adopters).

## References

- ADR-005 (event stream v2 contract)
- ADR-007 (SemVer + RC policy — drives the v2.1 PATCH bump)
- PLAN-005 §3 Phase 5
- `scan-injection.py` for the scanner contract
- `check_read_injection.py` for the hook wire-up instructions

## Enforcement commit

`d24cc8181058` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
