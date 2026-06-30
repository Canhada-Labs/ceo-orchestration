# ADR-016: Spawn Token Tracking — Contract and Null Semantics

## Status: ACCEPTED (2026-04-13)

## Context

The v2 audit log schema already declared nullable `tokens_in` /
`tokens_out` / `tokens_total` fields on `agent_spawn` events (see
`SPEC/v1/audit-log.schema.md` §"v2"). But until Sprint 6, every
emitter wrote them as `null` — no code actually extracted token
counts from spawn responses.

PLAN-006 debate round 1 (R-SB4) flagged ambiguity: "null-allowed" in
JSON admits **three states** — field absent, field present as null,
field present with integer. Without a contract declaring which state
means what, each consumer reimplements the null check differently
(some treat absent as "pre-field-exists era", some as "adapter couldn't
report", etc.).

Plan also flagged (R-SB8) that the original Phase 5 wording implied
the fields were new; they already existed in the schema. The actual
work is writer-side: populate the fields from spawn response data.

## Decision Drivers

- **Adapter portability.** Claude uses `usage.input_tokens`; Gemini
  uses `usageMetadata.promptTokenCount`; OpenAI uses `usage.prompt_tokens`.
  The extractor must probe multiple shapes without guessing.
- **Consumer ergonomics.** `audit-query.py tokens` must be able to
  distinguish "we don't know if this emitter supported tokens" from
  "emitter supports tokens but couldn't extract on this record".
- **Fail-open.** Token extraction is observability; never blocks the
  user session. Any exception → (None, None).
- **No SPEC version bump.** Semantics amendment is additive to the v2
  schema documentation — consumers that don't read the amendment still
  work (they just can't distinguish absent-vs-null).

## Options Considered

### Option A: Required field (always integer), adapters estimate 0 when unknown

- **Pros:** simplest consumer logic.
- **Cons:** "0 tokens" is semantically wrong when we don't know;
  skews aggregates; indistinguishable from "spawn used zero tokens"
  (genuinely possible for cached responses).

### Option B: Optional nullable, absence == "older emitter" (chosen)

- **Pros:** 3-state distinction lets operators measure adapter
  coverage (what % of spawns have token data) separately from
  aggregate volume; forward-compatible with new adapters.
- **Cons:** consumers must handle 3 states; misread as "null means
  zero" is possible (mitigated by SPEC doc + `audit-query.py tokens`
  reference implementation).

### Option C: Always integer with sentinel (-1) for "unknown"

- **Pros:** avoids null in JSON.
- **Cons:** -1 is not semantically "unknown" — it's a negative count.
  Breaks tolerance matrix for consumers that validate `value >= 0`.

## Decision

**Option B.** Optional nullable, always-present-when-emitter-supports-it.

### Extractor: `_lib/tokens.py`

```python
from _lib import tokens

tin, tout = tokens.extract_tokens(event.tool_response)
# tin, tout are each Optional[int] — None when shape is unknown
```

### Probe order (fail-over down the list)

1. `tool_response.usage.input_tokens` + `output_tokens` (Claude, Anthropic SDK)
2. `tool_response.usage.promptTokenCount` + `candidatesTokenCount` (Gemini nested)
3. `tool_response.usage.prompt_tokens` + `completion_tokens` (OpenAI-ish)
4. `tool_response.usageMetadata.*` (Gemini top-level)
5. `tool_response.totalTokens` (legacy Claude — output-only)
6. None, None (unknown)

### Emitter contract

Emitters that call `extract_tokens` MUST always set the key in the
emitted record, even when the value is None:

```python
tin, tout = tokens.extract_tokens(event.tool_response)
entry = {
    ...,
    "tokens_in": tin,       # int or None — key ALWAYS present
    "tokens_out": tout,     # int or None — key ALWAYS present
    "tokens_total": tokens.total_tokens(event.tool_response),
}
```

Emitters that don't call `extract_tokens` (pre-ADR-016 code) leave
the keys absent — consumers interpret absence as "older emitter".

### Consumer contract

Per `SPEC/v1/audit-log.schema.md` §"tokens_* field semantics":

| State | Meaning |
|---|---|
| Key absent | Pre-ADR-016 emitter |
| Key present, null | Post-ADR-016 emitter, extraction failed |
| Key present, integer ≥ 0 | Extracted count |

Consumers MUST NOT sum null values; MUST NOT treat absent as 0 for
aggregation purposes.

### Reference implementation

`audit-query.py tokens` — groups by skill / subagent_type / day, reports:
- `totals.tokens_in` / `tokens_out` / `tokens_total`
- `totals.spawns_with_tokens` / `spawns_without_tokens`
- Per-group breakdowns

`spawns_without_tokens` combines both "absent" and "null" states —
Sprint 7 may split these into separate counts when Gemini adapter
reaches real parity.

## Consequences

### Positive

- Adapter coverage becomes measurable (`spawns_with_tokens /
  total_spawns`).
- Aggregates stay correct (null values never corrupt sums).
- Three-state semantics match how the audit log already handles
  `event_schema` (absent = v1, present = v2+).
- New adapters plug into `extract_tokens` by adding a probe without
  modifying the emitter wiring.

### Negative

- Consumers with 2-state (null-or-int) logic still work but can't
  distinguish adapter-upgrade-era from adapter-cant-extract. This is
  acceptable for most dashboards; the distinction matters only for
  adapter-quality measurement.
- Probe order is opinionated. A new adapter with a different shape
  (e.g. named fields) requires code change to `_lib/tokens.py`. This
  is the same trade-off as every adapter contract in the framework.

### Neutral

- No SPEC version bump. Amendment is documentation-only; the v2
  schema declared these fields nullable already.

## Blast Radius

- `.claude/hooks/_lib/tokens.py` (NEW, ~120 LOC)
- `.claude/hooks/tests/test_tokens_lib.py` (NEW, 23 tests)
- `.claude/scripts/audit-query.py` (+1 sub-command `tokens`, ~70 LOC)
- `.claude/scripts/tests/test_audit_query_tokens.py` (NEW, 6 tests)
- `SPEC/v1/audit-log.schema.md` (+§tokens_* field semantics)
- `.claude/hooks/audit_log.py` — wires `_lib/tokens.py` into emitted
  record (Phase 5b, separate commit — depends on Phase 1 migration)

**Reversibility:** HIGH. Extractor is additive; emitter-side wiring
is one line added to `build_entry` in `audit_log.py`; consumer-side
is a new sub-command. Revert = remove these paths, no data migration.

## References

- PLAN-006 §Phase 5a, §Phase 5b
- PLAN-006/debate/round-1/staff-backend-engineer.md §R-SB4, §R-SB8
- PLAN-006/debate/round-1/consensus.md §K4, §C8
- ADR-005 — Event stream v2 foundation
- ADR-011 — Event stream v2.1 (injection_flag — precedent for additive
  actions without schema version bump)
- `SPEC/v1/audit-log.schema.md` §"tokens_* field semantics"

## Enforcement commit

`e31edc1e5e4e` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
