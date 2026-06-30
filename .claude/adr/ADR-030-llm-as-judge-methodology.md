# ADR-030: LLM-as-Judge Methodology (hybrid with deterministic fallback)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 3)
**Blast radius:** L2 — two new scripts, one schema file, two documentation
artifacts, amendments to `run-skill-benchmark.py` and
`SPEC/v1/benchmarks.schema.md`. No existing hook is modified.
**Related:** ADR-015 (Reflexion v2 outcome loop), ADR-027 (unified state
backend — audit redaction precedent), ADR-035 (OTEL export — advisory →
gate lifecycle precedent), SPEC/v1/judge-payload.schema.md,
SPEC/v1/benchmarks.schema.md.
**Supersedes:** none.

## Context

Benchmarks in Sprints 1–10 scored skills via **fixture-based** scoring:
pattern-match against `must_flag_tags` and `must_suggest_keywords`
defined in the scenario YAML. This produces determinism (temperature=0,
same inputs ⇒ same output) and local reproducibility, but captures
only what the authoring team thought to enumerate. Nuances like
"correct diagnosis but wrong suggestion vocabulary" or "correct
suggestion but overstated severity" slip through.

PLAN-011 Phase 3 introduces an **LLM-as-judge** mode so that skill
evaluations can measure response quality the way a skilled reviewer
would — against the intent of the rubric, not only its keyword
shadow. Debate round-1 raised three HIGH-severity findings that shape
the decision:

- **§H5 (AI + QA, HIGH):** "Phase 3 judge methodology under-spec."
  Require a committed prompt, two-pass (position bias), κ ≥ 0.7 on
  N ≥ 50 calibration samples, provider rotation, and a golden-prompt
  test.
- **§H6 (Security, HIGH):** "Phase 3 judge sees everything."
  Default-deny payload: rubric + redacted response + minimal task
  context. Nothing else.
- **§H7 (VPE, HIGH):** "Phase 3 judge provider SPOF." Ship a
  deterministic fallback scorer; block closeout only when BOTH fail.

Acting on these without discipline produces a judge that is worse than
fixture-only: a single-provider oracle that silently drifts with model
updates and sees Owner source whenever the response is echoed.

## Decision Drivers

- **Separation of rater and ratee.** A judge run by the same provider
  as the judged model is a coauthor in disguise. Cross-provider is a
  methodological invariant, not folklore.
- **Payload minimisation.** Every extra field in the judge payload is
  an exfil channel. Default-deny > default-allow.
- **Deterministic fallback availability.** The judge MUST NOT be on
  the critical path; an unreachable judge must degrade to a
  deterministic grade that keeps CI green.
- **Advisory now, gate later.** Same lifecycle precedent as ADR-023,
  ADR-024, ADR-035: ship the machinery, measure, flip after evidence.
- **Stdlib-only.** ADR-002 constraint. JSON-twin rubrics instead of
  YAML parsing.

## Options Considered

### Option A — Fixture-only forever

Keep the existing keyword-pattern scoring. Never introduce an LLM
judge.

**Pros:** zero new surface; fully deterministic.
**Cons:** Ignores the core Phase 3 brief ("model-graded evaluation").
Evaluations remain as good as the YAML authoring; blind to semantic
quality.

**Rejected.**

### Option B — LLM-only (no fallback)

Ship the judge and make it the sole grading path for `--judge-mode=llm`.

**Pros:** simplest code path once the adapter is wired.
**Cons:** any provider outage or rate-limit hits blocks CI. Single
point of failure (§H7). No deterministic reproduction path.

**Rejected.**

### Option C — Hybrid with deterministic fallback (CHOSEN)

Ship three modes behind `--judge-mode`:

1. `fixture` (default; current behaviour preserved)
2. `llm` (LLM judge with cross-provider guard; unreachable → None)
3. `both` (fixture AND judge; disagreement emits veto)
4. `fallback` (deterministic keyword-match baseline)

When `mode=llm` and the adapter is unreachable, the RUNNER degrades
silently — the fixture score still lands in the audit log with
`judge_mode="llm"` and no judge fields. Operators who want the
deterministic number use `--judge-mode=fallback` explicitly OR
`--judge-mode=both` (which captures both).

**Pros:** every decision path has a deterministic answer; cross-
provider is enforced; disagreement becomes a queryable audit event;
ADR-030 can flip to enforcement once κ ≥ 0.7.
**Cons:** 3 new files + schema surface. Acceptable.

**Chosen.**

## Decision

### 1. Committed prompt + golden hash

The judge prompt lives at `.claude/benchmarks/_schemas/judge-prompt.md`.
Its SHA-256 is:

```
297eabeffb4f0eec8c1ab5bc67f18627c563c72003151931317ce41a5ef0b1a1
```

This is the **golden prompt hash**. The test
`test_benchmark_judge.TestGoldenPromptHash.test_committed_hash_matches`
asserts the current file hashes to this value. Any intentional change
REQUIRES:

1. Updating the prompt file.
2. Updating `GOLDEN_PROMPT_SHA256` in the test.
3. Updating this hash line in the ADR.
4. A commit message explaining the semantic change, not just the hash.

Drift without all four is a regression.

### 2. Default-deny payload

The judge sees ONLY three top-level keys:

```json
{
  "task_context": "<redacted, <=4000 chars>",
  "rubric":       {<JSON rubric>},
  "response":     "<redacted via redact_secrets, <=8000 chars>"
}
```

Any fourth key raises `ValueError` at `validate_payload` time. See
`SPEC/v1/judge-payload.schema.md` for the full contract. Six unit
tests lock this down (`TestPayloadDefaultDeny.*`).

### 3. Two-pass position-bias control

Every judge invocation runs two passes:

- **Forward:** task → rubric → response.
- **Reverse:** task → response → rubric. The prompt is rendered with
  the two sections swapped; the three-key payload is unchanged (the
  reverse-pass bit is carried as a `[REVERSE-PASS] ` prefix inside
  `task_context`, NOT a new key).

Both scores are reported; `|forward - reverse| > 0.5` sets
`recommend_human_review=true` in the output.

### 4. Cross-provider guard

`benchmark-judge.py --judge-adapter=<x>` rejects `<x>` equal to
`CEO_HOOK_ADAPTER` (the main adapter). Exit code 3, reason code
`cross-provider-collision`. Empty main adapter is allowed (stand-
alone judge invocation).

### 5. Deterministic fallback (§H7)

`benchmark-fallback-scorer.py` is a keyword-match scorer with the
same JSON output shape as `benchmark-judge.py`. For each rubric item,
it tokenises the description (minus stopwords), counts matches in the
response, and scores as `(matched / total_keywords) * weight`.

Used:
- Explicitly via `--judge-mode=fallback`.
- Implicitly when `--judge-mode=llm|both` + judge unreachable
  (silent degradation, audit shows `judge_mode` but no judge scores).

Closeout is blocked ONLY when BOTH fixture AND fallback fail.

### 6. Provider rotation

`.claude/benchmarks/judge-rotation-schedule.md` documents the weekly
rotation:

| Week | Judge | Role |
|---|---|---|
| W1 | gemini | primary |
| W2 | openai | primary |
| W3 | local | offline control |
| W4 | gemini (fixed-seed replay W1) | drift detection |

Enforced operationally (by the weekly `--judge-adapter` value), NOT
at code-review time. Cross-provider collision is enforced at runtime.

### 7. κ calibration

`.claude/benchmarks/human-sample-calibration.md` is the living
protocol. Sample N = 50 paired grades across domains; compute Cohen's
linear-weighted κ. Current state: **TBD (no grades yet)**. The file
is append-only; corrections are new rows.

### 8. Three-state lifecycle

```
    Sprint 11               Sprint 12+                Sprint 13+
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  State 0       │───▶│  State 1       │───▶│  State 2       │
│  advisory      │    │  gated         │    │  enforced      │
│  both-score    │    │  disagreement  │    │  |delta|>0.2   │
│  audit event   │    │  veto blocks   │    │  fails         │
│  (no block)    │    │  PR until      │    │  benchmark run │
│                │    │  resolved      │    │                │
│ κ = TBD        │    │ κ ≥ 0.7        │    │ κ ≥ 0.8        │
│                │    │ (N=50 sample)  │    │ (N=100+)       │
└────────────────┘    └────────────────┘    └────────────────┘
```

Sprint 11 ships **State 0**. No existing benchmark is blocked by
judge score.

### 9. Flip criteria

| From | To | Criterion | Window | Owner |
|---|---|---|---|---|
| State 0 | State 1 | `κ ≥ 0.7 on N ≥ 50 paired grades` AND `disagreement rate ≤ 15% over 30 days` | 14d avg | QA lead |
| State 1 | State 2 | `κ ≥ 0.8 on N ≥ 100 paired grades` AND `judge unreachable events ≤ 1/week` | 30d avg | QA + VPE |

A PR that proposes the flip MUST include an `audit-query.py
benchmark-disagreements --since 30d` report and the κ calculation
output (with 95% bootstrap CI when N allows). Without that data the
flip PR is not approved.

### 10. Non-goals

- **Active learning of the rubric.** The rubric is a human-authored
  artefact. The judge does not propose rubric edits; that would
  collapse the rater/ratee separation.
- **Aggregating judges (ensemble).** A single judge per invocation.
  Ensembling is tempting but introduces another layer of bias that
  the rotation schedule already mitigates.
- **Real-time judging in hook context.** The judge is a batch /
  benchmark tool; it does NOT run inside a PreToolUse or PostToolUse
  hook. Those paths stay fixture-only.
- **OPENAI / LOCAL real-wire invocation.** Phase 3 ships the
  adapter-invocation seam (`invoke_adapter()`) with a mock path; the
  real provider-wire implementation is provisional pending per-
  provider SDK + credential handling. Unreachable mode is tested;
  reachable is mock-only.

### 11. Environment variables

| Var | Default | Effect |
|---|---|---|
| `CEO_HOOK_ADAPTER` | `claude` | Main adapter; judge MUST differ. |
| `CEO_SOTA_DISABLE` | unset | When `1`, judge mode becomes a no-op (WARNING on stderr, `fixture` is used). Mirrors the ADR-035 escape hatch. |

## Consequences

### Positive

- Evaluations capture semantic quality, not just keyword coverage.
- Payload default-deny is enforced at the code level; reviewers
  cannot casually "sneak in" a source-code field.
- Cross-provider guard prevents silent coauthor regressions.
- Every judge result lands in the audit log with a parseable
  envelope (`judge_mode`, `judge_score_forward`, `judge_delta`).
- Disagreement vetoes become a first-class audit signal usable by
  Sprint 12 calibration work.

### Negative

- Two new scripts to maintain (`benchmark-judge.py`,
  `benchmark-fallback-scorer.py`) plus the one-schema expansion.
- Human calibration is an ongoing obligation; if the team never
  reaches N = 50 grades, the gate never flips — sunsetting is
  explicit in §7 of `human-sample-calibration.md`.
- Mock judge is deterministic by hash, which is enough for unit
  tests but NOT enough to simulate realistic drift. Live provider
  runs are required for W1–W4 rotation evidence.

### Neutral

- `run-skill-benchmark.py` grows a handful of flags (`--judge-mode`,
  `--judge-adapter`, `--judge-mock`, `--judge-rubric-file`). Default
  `--judge-mode=fixture` keeps current CI contracts unchanged.
- Rubric public doc is YAML; code reads the JSON twin. Both are
  committed; drift check is left to human review (a rubric-drift
  test may be added in Sprint 12 if churn warrants).

## Blast Radius

**L2** — Cross-module contract change affecting:

- `.claude/scripts/run-skill-benchmark.py` (AMEND — 4 new flags,
  judge dispatcher, extended audit-emit path)
- `.claude/scripts/benchmark-judge.py` (NEW)
- `.claude/scripts/benchmark-fallback-scorer.py` (NEW)
- `.claude/scripts/tests/test_benchmark_judge.py` (NEW)
- `.claude/scripts/tests/test_benchmark_fallback_scorer.py` (NEW)
- `.claude/scripts/tests/test_run_skill_benchmark_judge_mode.py` (NEW)
- `.claude/benchmarks/_schemas/judge-prompt.md` (NEW)
- `.claude/benchmarks/_schemas/judge-rubric.yaml` (NEW — public doc)
- `.claude/benchmarks/_schemas/judge-rubric-example.json` (NEW — JSON
  twin consumed by code)
- `.claude/benchmarks/human-sample-calibration.md` (NEW — living doc)
- `.claude/benchmarks/judge-rotation-schedule.md` (NEW)
- `SPEC/v1/judge-payload.schema.md` (NEW)
- `SPEC/v1/benchmarks.schema.md` (AMEND — additive judge-mode fields)

**Reversibility:** HIGH. Rolling back to pre-Phase 3:

1. Revert the `run-skill-benchmark.py` diff (flag/handler removal).
2. Delete the two new scripts + their tests.
3. Delete the two new schema files + two benchmark docs + two schema
   artifacts.
4. Revert `SPEC/v1/benchmarks.schema.md` to 1.0.0-rc.1.

No migration path touches existing benchmarks (fixture-mode is the
default and stable).

## References

- PLAN-011 Phase 3 — this commit
- PLAN-011/debate/round-1/consensus.md §H5, §H6, §H7
- `SPEC/v1/judge-payload.schema.md`
- `SPEC/v1/benchmarks.schema.md` (judge-mode fields section)
- `.claude/benchmarks/_schemas/judge-prompt.md` (golden prompt)
- `.claude/benchmarks/human-sample-calibration.md` (κ protocol)
- `.claude/benchmarks/judge-rotation-schedule.md` (provider rotation)
- ADR-015 (Reflexion v2 outcome loop)
- ADR-023 (docs-freshness lifecycle precedent)
- ADR-024 (perf-baseline lifecycle precedent)
- ADR-035 (OTEL advisory → gate lifecycle precedent)

## Enforcement commit

`61c1f2876fe1` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
