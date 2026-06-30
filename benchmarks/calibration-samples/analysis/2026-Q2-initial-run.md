# 2026-Q2 — initial κ calibration run (PLAN-012 D2 seed)

> **Status:** PLANNED (no data collected yet).
> **Purpose:** Pre-registered seed file documenting the plan for the
> first N=100 inter-rater calibration run before any item is graded.
> SOP lock date: 2026-04-14.

## Plan (pre-registration)

- **Window:** 2026-Q2 (April–June 2026; exact start pending rater
  availability)
- **Target N:** 100 paired items (inter-rater, primary gate)
- **Target n:** 10 regraded items (intra-rater, drift test, ≥14-day blind)
- **Raters planned:** 2 primary + 1 adjudicator standby
- **Labels vocabulary:** `pass` / `fail` (dichotomous nominal)
- **Threshold:** bootstrap 95% CI lower bound ≥ 0.7 (per SOP §6)
- **Calibration set:** 30 known-positive + 30 known-negative items
  curated by Owner; raters gate at ≥90% accuracy before main N=100

## Protocol lock

This run follows `docs/labelling-sop-judge-calibration.md` as locked
on 2026-04-14. Any deviation between the lock date and the conclusion
of this run requires a `/debate round PLAN-012` and is logged in
§Deviations below.

## Results (TBD)

Will be populated post-collection:

| Field                        | Value |
|------------------------------|-------|
| Collection start             | TBD   |
| Collection end               | TBD   |
| N (primary)                  | TBD   |
| n (intra-rater retest)       | TBD   |
| κ̂ (point estimate)           | TBD   |
| Bootstrap 95% CI_lower       | TBD   |
| Bootstrap 95% CI_upper       | TBD   |
| Landis-Koch band             | TBD   |
| κ_intra (drift)              | TBD   |
| Disagreement count           | TBD   |
| Adjudicated disagreements    | TBD   |
| Raw grade hash (SHA-256)     | TBD   |
| **Flip-gate status**         | TBD (FLIP-READY / FLIP-BLOCKED / PRELIMINARY) |

## Deviations (if any)

None recorded. (Appended chronologically with timestamp and
ADR/debate reference.)

## References

- `docs/labelling-sop-judge-calibration.md` — locked SOP
- `.claude/benchmarks/human-sample-calibration.md` — living protocol
- `.claude/scripts/k-calibration.py` — computation tool
- PLAN-012 Phase 4 D2 — flip criterion
- ADR-030 — LLM-as-judge methodology
