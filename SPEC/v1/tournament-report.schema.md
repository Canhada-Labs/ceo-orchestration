---
spec_id: tournament-report
version: 1.0
related_adrs: [ADR-063, ADR-052, ADR-055]
status: published
date: 2026-04-19
---

# SPEC/v1/tournament-report.schema — Tournament report JSONL schema

> **Normative source:** SELF (self-authoritative — see ADR-007
> §Self-authoritative pattern). Paired-ADR: ADR-063 (agent-eval
> empirical dispatch validation).
>
> Strict contract for `benchmarks/tournament-<run_id>.jsonl` emitted by
> `.claude/scripts/tournament/reporter.py`. Part of PLAN-032 Wave B
> empirical ADR-052 validation. Committed reports are forgery-resistant
> via HMAC anchor (`<report>.jsonl.hmac` — see ADR-055 pattern).

## Design invariants

- **Hashes-only, no raw content** (Round 1 C-P0-3): raw fixture prompt,
  raw model output, raw judge rationale MUST NEVER appear in committed
  reports. Only SHA-256 digests + lengths.
- **Default-deny extra keys**: unknown keys MUST NOT be present. Parser
  may either reject or warn; framework defaults to warn + strip.
- **String value cap**: no string field exceeds **256 bytes**. Beyond
  that, the emitter truncates.
- **Numeric types**: all integers are non-negative; floats are rounded
  to at most 6 decimal places for cost, 3 for confidence, 4 for win-rate.
- **Verdict enum**: `pass` | `fail` | `errored` exclusively.
- **Stability**: schema changes bump this spec's `version` field (major
  for breaking, minor for additive with default-deny compatibility).

## Record types

Each line in the JSONL is one of two types: `task` or `aggregate`. Task
records come first; the aggregate record is the final line.

### Task record

One record per (fixture × model) dispatch.

| Field | Type | Required | Bounds / notes |
|---|---|---|---|
| `type` | string | yes | literal `"task"` |
| `fixture_id` | string | yes | ≤256 bytes; fixture stable identifier |
| `fixture_sha256` | string | yes | 64 hex chars; SHA-256 of raw fixture prompt (integrity) |
| `task_type` | string | yes | one of the 5 task-types (security-review, code-review, performance-triage, test-design, docs-writing); ≤64 bytes |
| `model` | string | yes | Anthropic model id per ADR-052 (claude-opus-4-8 \| claude-sonnet-4-6 \| claude-haiku-4-5-20251001); ≤64 bytes |
| `verdict` | string | yes | enum: `pass` \| `fail` \| `errored` |
| `output_sha256` | string | yes | 64 hex chars; SHA-256 of raw model output. Prevents verbatim output leak via report channel. |
| `tokens_in` | integer | yes | non-negative |
| `tokens_out` | integer | yes | non-negative |
| `cost_usd` | float | yes | non-negative, rounded to 6 decimals; uses ADR-052 pricing |
| `wall_clock_ms` | integer | yes | non-negative |
| `rationale_sha256` | string | no | present only for llm-judge mode; 64 hex chars |
| `rationale_length` | integer | no | character count of raw rationale before hashing |
| `confidence` | float | no | `[0.0, 1.0]` rounded to 3 decimals; llm-judge output |
| `error_reason` | string | no | present only when `verdict="errored"`; ≤256 bytes |

**Forbidden keys on task record:**
- `prompt` / `prompt_echo` / any raw fixture prompt content
- `output` / `output_text` / `content` / any raw model output
- `rationale` (the string itself; only `rationale_sha256` + `rationale_length` permitted)
- Any PII / credential fields

### Aggregate record

Exactly one record per report, emitted last.

| Field | Type | Required | Bounds / notes |
|---|---|---|---|
| `type` | string | yes | literal `"aggregate"` |
| `run_id` | string | yes | GH Actions run_id in CI, sha256 prefix locally; ≤128 bytes |
| `fixtures_count` | integer | yes | total fixtures dispatched |
| `models_count` | integer | yes | count of distinct models |
| `judge_runs` | integer | yes | multi-run median count (default 3) |
| `win_rate` | object | yes | nested `{task_type: {model: float∈[0,1]}}` |
| `total_cost_usd` | float | yes | sum of per-task `cost_usd` |
| `projected_cost_usd` | float | yes | pre-run projection per ADR-063 §Invariants |
| `budget_cap_usd` | float | yes | the `CEO_TOURNAMENT_BUDGET_USD` in effect |
| `errored_count` | integer | yes | count of tasks with `verdict="errored"` |
| `tasks_completed` | integer | yes | count of all task records |
| `partial` | boolean | yes | true if tournament aborted mid-run (cumulative > 1.5× projection) |
| `abort_reason` | string | no | present only when `partial=true`; ≤256 bytes |
| `adr052_validation` | object | yes | `{task_type: signal_string}` per validate_adr052() |

### ADR-052 validation signals

`adr052_validation` values are one of the enumerated signals below.
Downstream tooling (CI regression issue creator, Owner review) consumes
these strings.

| Signal | Meaning | Task-types it applies to |
|---|---|---|
| `opus_confirmed` | Opus > Sonnet by ≥15pp (significant at n=10) | security-review, code-review |
| `opus_marginal` | Opus > Sonnet by 5-15pp (directional) | security-review, code-review |
| `opus_mid_surprise` | Opus - Sonnet < 5pp (sampling noise; Owner review) | security-review, code-review |
| `parity_confirmed` | Opus ≈ Sonnet (gap ≤ 15pp) | performance-triage |
| `sonnet_underperforms` | Opus - Sonnet > 15pp on mid-tier task | performance-triage |
| `haiku_sufficient` | Haiku pass-rate ≥ 0.7 on low-risk task | docs-writing |
| `haiku_insufficient` | Haiku pass-rate < 0.7 on low-risk task | docs-writing |
| `no_prior_claim` | No ADR-052 claim for this task-type | test-design |
| `no_data` | Zero task records for this type | any |
| `incomplete_data` | At least one expected model missing | any |

**Non-auto-amendment clause:** signals are advisory. ADR-052 amendment
MUST require Owner signature (not tournament output alone). The VETO
floor invariant (code-reviewer + security-engineer = Opus in debate
spawns) is hard-coded in the tier-policy dispatcher and does not
auto-update from win-rate data.

## Statistical-power caveat

Default 10 fixtures × 3 judge runs per task-type × model cell yields
SE ≈ 0.16 at p=0.5. Signals where the raw win-rate delta is < 15pp
should be treated as **directional only**, not definitive.

Scaling the fixture corpus to ≥30 per task-type reduces SE to ~0.09
and makes 15pp deltas significant at α=0.05. Adopters with high
confidence-needs should expand the corpus accordingly.

## HMAC anchor (companion file)

Each report is accompanied by `<report_path>.hmac` containing the hex
digest of the audit-log HMAC chain walk over every JSONL line. The
chain uses `_lib/audit_hmac.compute_entry_hmac()` (ADR-055 precedent),
seeded from the framework audit key at
`~/.ceo-orchestration/state/audit-hmac.key`.

Verification via `.claude/scripts/audit-verify-chain.py --tournament
<report_path>` recomputes the chain and compares; any mismatch implies
post-emission forgery.

## Byte-identity reproducibility

For **strict-mode scorer** (no LLM-judge call), the report JSONL is
byte-identical across two runs with the same seed + same fixture corpus
+ same mock-Anthropic dispatcher. Regression anchor:
`tests/golden/strict_report_seed42.jsonl` (committed; verified via
SHA-256 compare in `test_reporter_golden_aggregate()`).

For **llm-judge mode**, byte-identity does NOT hold (judge variance
modulo model weight drift). Stability claim downgrades to "same ranking"
via multi-run median — test compares ranking not raw bytes.

## Failure-example artifact (NOT in this schema)

Raw failure examples for debugging live in
`benchmarks/tournament-<run_id>.failures.jsonl` which is `.gitignore`d
and never committed. Schema of that artifact is local-only + free-form.

## Version history

- 1.0 (2026-04-19) — initial publication, Round 1 hardened scope.
