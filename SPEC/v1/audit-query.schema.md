# SPEC v1 — audit-query CLI envelope

**Version:** 1 (initial; introduced PLAN-009 Phase 2 C5/A6)
**Status:** STABLE for pre-existing sub-commands; EXPERIMENTAL for Sprint 9 additions
**Related:** ADR-005 (event stream), ADR-020 (prune policy), PLAN-009 Phase 2

## Purpose

`audit-query.py` is the primary consumer-facing tool for reading the
audit log. Sprint 5 grew it from 9 to 18 sub-commands. Sprint 8
added `claims`. Sprint 9 adds `prune-restore-ratio`,
`architect-outcomes` (Phase 3), and `lessons-effectiveness` (Phase 5).

Without a stable envelope, each sub-command is free to invent its
output shape. Downstream consumers (dashboards, scripts, CI checks)
then couple to implementation details and break on any refactor.

This SPEC declares the JSON-mode envelope that all **experimental** +
future sub-commands MUST follow, and documents the *stability tier*
of every existing sub-command so consumers know which ones are safe
to script against.

## JSON envelope (normative for new sub-commands)

All Sprint 9+ sub-commands MUST emit this top-level shape when
invoked with `--json`:

```json
{
  "query": "<sub-command-name>",
  "version": "1",
  "data": { /* sub-command specific */ }
}
```

Rules:

- `query` — the sub-command name, literal string matching the
  argparse entry
- `version` — string `"1"` for v1 SPEC. MINOR schema additions keep
  this string. MAJOR reshape → `"2"` + new SPEC doc.
- `data` — sub-command-specific payload. MAY be `null`, `object`,
  or `array`. Contents are defined per sub-command below.
- No other top-level keys. Consumers MUST tolerate unknown keys
  inside `data` (additive-within-v1 rule).

Human-readable (default, non-`--json`) output is free-form text and
NOT covered by this SPEC.

## Additive-within-v1 rule

Within SPEC v1:

- Adding a new field inside `data.*` → **allowed**, no bump.
- Adding a new sub-command → **allowed**, lists at the bottom.
- Removing a field → **forbidden** (breaks downstream).
- Renaming a field → **forbidden** (breaks downstream).
- Changing a field's type → **forbidden** (breaks downstream).
- Changing the envelope `{query, version, data}` shape → MAJOR,
  routes to v2 with a fresh SPEC file.

A breaking change to any "stable" sub-command is a SemVer MAJOR
event. A breaking change to an "experimental" sub-command is
permitted within Sprint 9 only (after Sprint 9 close, it promotes
to "stable" and the additive rule applies).

## Stability tiers

| Tier          | Rules                                                    |
|---------------|----------------------------------------------------------|
| **stable**    | Additive-only within v1. Existed pre-Sprint 9.           |
| **experimental** | Added in Sprint 9. May reshape up to Sprint 9 close. |

Post-Sprint 9: experimental → stable. New additions default to
experimental for 1 sprint.

## Sub-command inventory (as of Sprint 9)

### Stable (pre-existing, additive-only)

| Sub-command  | Data shape (high-level)                          |
|--------------|--------------------------------------------------|
| `summary`    | `{count, range, top_skills, compliance}` object |
| `by-skill`   | array of `{skill, count, ...}`                  |
| `compliance` | `{compliant, non_compliant, rate}` object       |
| `by-day`     | array of `{date, count}`                        |
| `search`     | array of matching entries                       |
| `since`      | array of entries on/after a date                |
| `stats`      | `{prompt_len_dist, response_kind_dist, latency}` object |
| `errors`     | array of breadcrumb lines                       |
| `export`     | csv / tsv / json dump (varies by --format)      |
| `debate`     | array of `{plan_id, round, agents, ...}`        |
| `plans`      | array of `{plan_id, transitions}`               |
| `vetoes`     | array of `{hook, reason_code, count}`           |
| `benchmarks` | array of `{skill, runs, pass_rate}`             |
| `lessons`    | array of `{archetype, trigger, count}`          |
| `metrics`    | cross-cutting `{veto_rate, debate_completion, ...}` |
| `health`     | `{verdict, signals}` object                     |
| `tokens`     | token aggregates (PLAN-006 Phase 5a)            |
| `claims`     | `{agents, kinds, pass_fail}` (Sprint 8)         |

These 18 sub-commands predate the envelope SPEC. Their current
output shapes are GRANDFATHERED as "v1 stable" — consumers may rely
on them, and we add fields only.

### Experimental (Sprint 9 additions)

| Sub-command              | Phase | Data shape |
|--------------------------|-------|------------|
| `prune-restore-ratio`    | P2.2  | `{archived_count, restored_count, unique_restored_lesson_ids, restore_ratio (null\|float), since, until, multi_restore_warnings}` |
| `architect-outcomes`     | P3.4  | `{lesson_id: {hit, miss, inference_mode_breakdown}}` |
| `lessons-effectiveness`  | P5.1  | array of `{lesson_id, effectiveness (null\|float), days_since_last_outcome, injection_count, inference_mode_breakdown}` |

These three follow the envelope explicitly. Each sub-command MAY
add fields within `data.*` in Sprint 10+ patches without a SPEC bump.

## Trust boundary note (D1)

`audit-query.py` operates on the local `audit-log.jsonl` written by
`audit_log.py`. In Sprint 9, the framework is a **single-user, local
tool**: there is no HMAC, no hash chain, and no tamper-evident
append. An attacker with write access to `audit-log.jsonl` can
fabricate any event. The audit log is a *behavioral record*, not a
*security audit trail*.

Downstream consumers that need tamper-evidence must import entries
into an append-only store (S3 object lock, cloud logging service,
etc.) at ingest time.

Hash-chain / HMAC options are deferred to Sprint 11+ backlog.

## Breaking-change protocol

If you need to reshape an existing field:

1. Propose a v2 SPEC doc at `SPEC/v2/audit-query.schema.md` with the
   full new shape.
2. Bump `VERSION` to `2.0.0-rc.1`.
3. Keep `audit-query.py v1` entry point working for 1 major version.
4. Emit a `DeprecationWarning` from v1 consumers for 1 major version.
5. Remove `audit-query.py v1` behavior in `3.0.0`.

Within Sprint 9: experimental sub-commands may reshape freely.

## References

- PLAN-009 §Phase 2 P2.2/P2.3, P3.4, P5.1
- PLAN-009/debate/round-1/consensus.md §C5/A6 (D1 audit-log trust)
- ADR-005 (event stream)
- ADR-020 (prune policy)
- SPEC/v1/audit-log.schema.md (the event shapes these commands read)
- SPEC/v1/benchmarks.schema.md (parallel SPEC for benchmark YAML)
