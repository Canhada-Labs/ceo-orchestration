# Judge-provider rotation schedule

> **Status:** ACTIVE (PLAN-011 Phase 3 §H5).
> **Related:** ADR-030, `benchmark-judge.py` cross-provider guard.

## 1. Principle

Per debate round-1 §H5: the LLM judge MUST differ from the judged
model. Beyond that baseline, rotating the judge across providers
guards against **systematic bias in a single provider's evaluation
instincts**. A judge whose grading drift correlates with the judged
model is not a judge — it is a co-author.

We rotate weekly and run a fixed-seed replay to detect drift.

## 2. Rotation table

| Week | Judge adapter | Role | Notes |
|------|---------------|------|-------|
| W1 (current) | `gemini` | primary | Initial calibration; collect 10+ κ rows. |
| W2 | `openai` | primary | Same benchmarks, different provider. Compare grade distributions vs W1. |
| W3 | `local` | offline control | Fully local inference (Ollama or equivalent). Primarily serves as fallback receiver for `CEO_SOTA_DISABLE=1` sessions. |
| W4 | `gemini` (fixed-seed replay W1) | drift detection | Re-run W1 benchmarks with pinned seed / temperature=0. If the grade distribution differs by more than delta of 0.3 on a per-benchmark basis, alert the QA lead. |

Week boundaries align to the first Monday UTC of each rotation cycle.
The Owner may compress / extend any individual week when a benchmark
cohort is unusually small or unusually large; rotations shorter than
2 days or longer than 4 weeks MUST be recorded in the changelog
below.

## 3. Selection enforcement

The benchmark runner reads `CEO_HOOK_ADAPTER` to determine the main
("judged") adapter. `benchmark-judge.py --judge-adapter=<x>` rejects
any `<x>` equal to that main adapter with exit code 3 and reason
code `cross-provider-collision`.

The rotation schedule is enforced **operationally** (by scripting the
weekly `--judge-adapter` value), NOT at code-review time.

## 4. Drift detection (W4 replay)

- Pin the benchmark corpus from W1 (store the sampled audit events in
  `.claude/benchmarks/.drift-snapshots/<yyyy-mm-dd>.jsonl`).
- Re-run with the same adapter (`gemini`), temperature=0, same prompt
  text (golden hash asserted — see ADR-030).
- Expected outcome: grade distribution is stable within ±10% per
  benchmark.
- If distribution shifts more than ±10%, file a finding — this is a
  signal the underlying model updated or the prompt has been silently
  mutated.

## 5. Changelog

- 2026-04-14 (PLAN-011 Phase 3) — initial rotation schedule.

## 6. References

- ADR-030 LLM-as-judge methodology
- `.claude/benchmarks/human-sample-calibration.md`
- Debate round-1 consensus §H5
