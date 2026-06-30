# Human-sample calibration — κ protocol

> **Status:** ONGOING (Sprint 11 seed; N≥100 upgrade in PLAN-012 Phase 4 D2).
> **Related:** PLAN-011 Phase 3 §H5, PLAN-012 Phase 4 D2, ADR-030,
> `calibration-kappa.py` (ordinal/weighted), `k-calibration.py` (nominal
> + bootstrap CI), `docs/labelling-sop-judge-calibration.md`,
> `docs/measurement-protocols.md`.

## 0. What changed in Sprint 12

Sprint 11 seeded this at `N ≥ 50, κ ≥ 0.7`. Round-1 debate (QA §HIGH)
established that was under-powered: at N=50, κ=0.7, SE ≈ 0.077, 95% CI
≈ [0.55, 0.85] — straddles Landis-Koch moderate/substantial boundary,
which is the boundary the flip-gate is meant to resolve.

Sprint 12 promotes to:
- **N ≥ 100 paired grades** (up from 50)
- **Bootstrap 95% CI lower bound ≥ 0.7** (hard gate, not just point estimate)
- **Intra-rater κ ≥ 0.8** on 10 regraded items after ≥14d blind retest
- **Landis-Koch (1977) bands cited explicitly** (§4)
- **Blinded grading** — rater sees neither judge score nor hook State
- **Pre-registered SOP** at `docs/labelling-sop-judge-calibration.md`,
  locked before data collection (anti p-hacking)
- **Calibration set** — 30 known-positive + 30 known-negative labelled
  by Owner **before** main N=100 begins (detects grader drift early)

§1–§9 preserved from Sprint 11 seed; §0 and §10–§13 are additive.

## 1. Purpose

Before enforcing LLM-as-judge (Sprint 12+), measure inter-rater
agreement between judge and human gold-standard grader. PLAN-012
Phase 4 D2 pins the promoted bar at **κ ≥ 0.7 with bootstrap 95% CI
lower bound ≥ 0.7 on N ≥ 100 paired grades**, plus intra-rater
test-retest ≥ 0.8 on a blinded 10-item subset. Updated in-place as
calibration accumulates.

## 2. Sample size

**Target N = 100 paired grades.** Floor for flip-gate; smaller N values
report as "preliminary" but do NOT satisfy the Sprint 12 criterion.

**Power rationale.** Cohen's κ large-sample SE ≈ `√((1 − κ) / N)`
(Fleiss-Cohen-Everitt upper bound). At target κ = 0.7:

| N    | SE    | ±1.96·SE | κ̂ for LCI = 0.7 |
|------|-------|----------|------------------|
| 30   | 0.100 | ±0.196   | ≈ 0.90 (unrealistic) |
| 50   | 0.077 | ±0.151   | ≈ 0.85 (tight)   |
| 100  | 0.055 | ±0.107   | ≈ 0.81 (floor)   |
| 200  | 0.039 | ±0.076   | ≈ 0.78 (comfy)   |
| 385  | 0.028 | ±0.055   | 2% half-width on 5% FPR (debate §C2) |

Floor = N=100 with κ̂ ≥ ~0.81 for bootstrap LCI to clear 0.7. If capacity
permits N=200, use it — tighter CI is strictly better.

Each pair = (candidate response, human grade, judge forward grade,
optional judge reverse grade). Nominal path uses pass/fail labels;
ordinal path uses 0–10 integers.

## 3. Sampling strategy

- **Source:** `benchmark_run` audit events from last 30 days.
- **Mode:** stratified random, no replacement, across skill domains
  (backend / frontend / fintech / edtech / government / LGPD / trading-hft).
- **Exclude:** `refused=true` items → separate precision/recall signal (§6).
- **Calibration subset:** 30 positive + 30 negative Owner-curated items
  graded **before** main N=100 starts. Rater ≥90% accuracy → proceed.
  75–89% → retrain + fresh batch. <75% → debate opens on rubric clarity.
  Calibration items discarded (not reused in main N=100).

## 4. Landis-Koch (1977) bands

| κ range       | Band               |
|---------------|--------------------|
| κ < 0.00      | No agreement       |
| 0.00–0.20     | Poor               |
| 0.21–0.40     | Fair               |
| 0.41–0.60     | Moderate           |
| 0.61–0.80     | Substantial        |
| 0.81–1.00     | Almost perfect     |

Flip-gate at κ ≥ 0.7 sits inside "substantial". We do NOT accept
"moderate" — bootstrap CI_lower must land in "substantial" or above.

Citation: Landis, J. R. & Koch, G. G. (1977). *Biometrics* 33(1) 159–174.

## 5. κ formula

### Ordinal (weighted)

0–10 Likert → weighted κ with linear weights (standard ordinal
practice). Shipped at `.claude/scripts/calibration-kappa.py` (21 tests).
Linear weight: `w_ij = |i − j|/(k − 1)`; `κ_w = 1 − Σ(w·O) / Σ(w·E)`
where O = observed confusion, E = independence-expected from marginals.
Unweighted reported alongside as secondary.

### Nominal (unweighted) + bootstrap CI

Dichotomous/nominal labels → unweighted κ + **percentile bootstrap 95%
CI** at `.claude/scripts/k-calibration.py` (PLAN-012 D2). Parametric
SE `√((1−κ)/N)` reported as sanity only; bootstrap is authoritative
because the parametric assumption (asymptotic normality) breaks at
moderate N. 10 000 paired resamples per Efron & Tibshirani (1993) §13.3.

Citations: Cohen (1960); Efron (1979).

**Usage:**
```
# Sprint 11 ordinal (weighted κ on 0–10 grades)
python3 .claude/scripts/calibration-kappa.py [--grades <path>] [--json]

# Sprint 12 nominal (unweighted κ + bootstrap CI)
python3 .claude/scripts/k-calibration.py \
    --rater1 benchmarks/calibration-samples/grades/rater1.csv \
    --rater2 benchmarks/calibration-samples/grades/rater2.csv \
    --bootstrap-iterations 10000 --ci-level 0.95 --threshold 0.7
```

## 6. Refusal handling

Judge `refused=true` items report separately as precision/recall:
- Precision: of judge-refused, how many human-refused?
- Recall: of human-refused, how many judge-refused?
NOT merged into headline κ.

## 7. Current κ: **UNREPORTABLE** (N = 0, seed only)

Tooling shipped; no grades collected yet. Grades land in
`.claude/benchmarks/calibration-grades.jsonl` (ordinal path) or
`benchmarks/calibration-samples/grades/*.csv` (nominal path, one per rater).

**Ordinal row (JSONL):**
```json
{"id": "g-001", "date": "2026-04-14", "benchmark": "owasp-basics",
 "skill": "security-and-auth", "human": 8, "judge_fwd": 7,
 "judge_rev": 8, "refused_human": false, "refused_judge": false,
 "note": "short rationale"}
```

**Nominal row (CSV):**
```
item_id,rater_id,label,timestamp,duration_s
g-001,rater-A,pass,2026-05-01T10:32:00Z,42
```

### Flip-gate thresholds (Sprint 12 promoted)
- N < 20 → **UNREPORTABLE**
- 20 ≤ N < 100 → **PRELIMINARY** (report; do NOT flip)
- N ≥ 100 AND bootstrap 95% CI_lower ≥ 0.7 AND κ_intra ≥ 0.8 → **FLIP-READY**
- N ≥ 100 AND bootstrap 95% CI_lower < 0.7 → **FLIP-BLOCKED** (debate
  round per ADR-030 §9; do NOT recollect)

## 8. What this document is NOT

- Not a license to defer indefinitely. If after 6 months N still < 100,
  Owner convenes scope review: invest in faster collection OR drop
  enforcement (permanent fixture-only fallback).
- Not private. All rows auditable; no grader identity beyond initials.

## 9. References

- PLAN-011 Phase 3 §H5 (Sprint 11 seed).
- PLAN-012 Phase 4 D2 (Sprint 12 promoted criterion).
- ADR-030 (LLM-as-judge methodology).
- `SPEC/v1/judge-payload.schema.md`.
- `.claude/benchmarks/judge-rotation-schedule.md` (provider rotation).
- `docs/labelling-sop-judge-calibration.md` (pre-registered SOP).
- `docs/measurement-protocols.md` (cross-flip methods).
- Cohen (1960) EPM 20(1) 37-46; Landis & Koch (1977) Biometrics 33(1)
  159-174; Efron (1979) Ann. Stat. 7(1) 1-26; Efron & Tibshirani (1993)
  *Introduction to the Bootstrap*; Snow et al. (2008) EMNLP.

---

## 10. Blinding protocol (Sprint 12)

**Raters see:** input payload, LLM textual claim, LLM prose rationale.

**Raters do NOT see:** judge numeric confidence; hook State (0/1) at
generation time; prior rater's label (until §6 disagreement round on
disagreement subset only); LLM provider identity (Claude / Gemini /
OpenAI / local); `skill` / `benchmark` fields (stratum leakage).

**Enforcement.** Labelling tooling redacts before delivery
(`benchmarks/calibration-samples/labelling-ui.html` Sprint 13 SPA stub;
interim Sprint 12 uses pre-redacted JSON generated by second party via
deterministic key-filter — NOT an LLM). Raters have no file-system
access to raw audit logs.

## 11. Calibration set (pre-main-run)

Before main N=100 each rater: grades 60 calibration items (30 positive +
30 negative, Owner-curated). Reports classification accuracy.

- ≥ 90% → proceed to main sample.
- 75–89% → re-read rubric + `judge-rubric.yaml` → retry fresh 60-item
  batch from same pool.
- < 75% → does not proceed; debate opens on rubric clarity.

Calibration items **discarded** (not reused in main N=100) to prevent
training-measurement leakage.

## 12. Intra-rater test-retest (drift)

Random 10-item subset from rater A's N=100 held out; regraded by same
rater after **blind ≥14-day delay** (UI re-presents fresh; rater does
not see prior label).

```
python3 .claude/scripts/k-calibration.py \
    --first-pass benchmarks/calibration-samples/grades/rater-A-pass1.csv \
    --second-pass benchmarks/calibration-samples/grades/rater-A-retest.csv \
    --intra-threshold 0.8
```

Required: **κ_intra ≥ 0.8** (point estimate). If < 0.8, rater A's N=100
discarded; collection repeats with additional calibration or replacement
rater. κ_intra < 0.8 invalidates inter-rater measurement.

## 13. Transition Log (appended)

| Date       | Event                       | N   | κ̂   | CI_lower | CI_upper | Band           | Status          | Ref |
|------------|-----------------------------|-----|------|----------|----------|----------------|-----------------|-----|
| 2026-04-14 | Sprint 11 tooling seeded    |   0 |  —   |   —      |   —      | UNREPORTABLE   | seed            | PLAN-011 §H5 |
| 2026-04-14 | Sprint 12 protocol promoted |   0 |  —   |   —      |   —      | UNREPORTABLE   | N≥100 target    | PLAN-012 D2 |
| TBD        | First preliminary readout   | TBD | TBD  | TBD      | TBD      | TBD            | PRELIMINARY     | TBD |
| TBD        | N=100 flip readiness check  | TBD | TBD  | TBD      | TBD      | TBD            | FLIP-READY/BLOCKED | TBD |

Aggregated results published here (not in `grades/`, which is
gitignored until consensus reached — see
`benchmarks/calibration-samples/README.md`).
