# Labelling SOP — judge calibration (PLAN-012 D2)

> **Status:** PRE-REGISTERED — locked before any data collection.
> **Owner:** Principal QA Architect.
> **Locked:** 2026-04-14 (Sprint 12 Phase 4 D2).
> **Change policy:** modification between lock date and first N=100
> collection requires a `/debate` round and ADR amendment. Anti-p-hacking:
> rules do not move after numbers are in.

Pre-registered Standard Operating Procedure for collecting N ≥ 100
inter-rater grades that gate the Sprint 12 flip of LLM-as-judge
enforcement (Flip #D2 in PLAN-012). P-hacking is real: if the protocol
is not fixed before data is collected, any ambiguity can be retcon'd to
land a borderline κ on the favourable side. A locked SOP removes that.

## 1. Scope

Pairs of **(input payload, LLM-claimed label)** from the judge two-pass
output. Rater assigns their own nominal label blind to the judge score.
One CSV row per pair, keyed by `item_id`.

Out of scope: 0–10 ordinal grading (Sprint 11 ordinal branch uses
`calibration-kappa.py` weighted κ — see
`.claude/benchmarks/human-sample-calibration.md` §5).

## 2. Sample selection

**Frame:** `benchmark_run` audit events from the last 30 days.
**Sample:** stratified random N ≥ 100, no replacement.
**Stratification:** skill domain (backend / frontend / fintech / edtech
/ government / LGPD / trading-hft) × benchmark family (owasp-basics /
public-api-design / state-machines / other).
**Exclude:** `refused=true` items — tracked separately via precision/
recall (see `human-sample-calibration.md` §6).

**N=100 rationale.** See `human-sample-calibration.md` §2 power table.
SE(κ) ≈ √((1−κ)/N). At κ=0.7: N=50 gives ±0.151 half-width (straddles
moderate/substantial); N=100 gives ±0.107 (requires κ̂≈0.81 for LCI=0.7).

**Stopping rule:** exactly N=100. Optional continuation to N=200
permitted iff decided and logged in
`benchmarks/calibration-samples/analysis/<run>.md` before the first
item is graded. No peek-and-stop.

## 3. Rater selection

- **Count:** 2 primary + 1 adjudicator standby (§6).
- **Exclusion (hard):** anyone who authored LLM judge prompts, rubric
  YAML, or judge payload schema. Cohen (1960) premise: rater and ratee
  separable.
- **Eligibility:** Owner-approved.
- **Training gate:** 60-item calibration subset (30 known-positive +
  30 known-negative, Owner-curated). ≥90% accuracy → proceed.
  75–89% → retrain + retry a fresh 60-item batch. <75% → rubric
  debate opens, rater does not proceed. Calibration items NEVER reused
  in the main N=100.

## 4. Blinding

**Raters see:** input payload, LLM textual claim, LLM prose rationale.
**Raters do NOT see:** judge numeric confidence score; hook State
(0 advisory / 1 blocking) at generation time; prior grader's label
(until §6 adjudication on disagreement subset only); LLM provider
identity (Claude / Gemini / OpenAI / local); `skill` / `benchmark`
fields of source audit row (stratum leakage).

**Enforcement:** redaction step in labelling tooling (§5). Raters have
no file-system access to raw audit logs.

## 5. Labelling UI

**Sprint 12 interim:** raters grade from pre-redacted JSON payloads
exported by a deterministic key-selection redact script (NOT an LLM).
Second party (not the rater) runs the redact on a secured workstation.
Rater records labels into CSV per §9.

**Sprint 13 planned:** offline SPA at `benchmarks/calibration-samples/
labelling-ui.html`:
1. Load pre-redacted batch.
2. One item per screen (no scrollback).
3. 15s minimum dwell time (anti-rush).
4. Records `item_id, rater_id, label, timestamp, duration_s`.
5. CSV export matching §9.
6. No network (file:// only; air-gapped grading OK).
7. Ships redact pipeline source for auditability.

## 6. Consensus rule (disagreement resolution)

1. **Primary.** Both raters complete N=100 independently. Compute
   inter-rater Cohen's κ + bootstrap 95% CI via `k-calibration.py`.
2. **κ̂ ≥ 0.7 AND CI_lower ≥ 0.7:** FLIP-READY. No adjudication.
3. **κ̂ ∈ [0.5, 0.7) OR CI_lower < 0.7:** third-rater adjudication.
   Third rater (blinded per §4; not shown prior labels) regrades
   disagreement subset only. Majority label (2 of 3) adopted; recompute κ.
4. **Post-adjudication κ_LCI < 0.7:** FLIP-BLOCKED. **Do NOT recollect.**
   Open `/debate round PLAN-012` on rubric clarity (ADR-030 §9).
   Outcomes: (a) refined rubric → fresh N=100 from step 0; (b) abandon
   enforcement (judge stays State 0 advisory); (c) alternative metric
   (e.g. per-domain κ).

**Why not recollect on the same rubric?** p-hacking. Repeated draws
converge to the same point estimate; only the CI narrows. If κ̂ < 0.7
the estimator is the problem, not sample noise.

## 7. Timing

- Per-item: 30–120 s. UI enforces 15 s floor.
- Session: ≤ 30 min (~30 items) or until rater reports fatigue.
- Per-day: ≤ 3 sessions per rater.
- N=100 × 2 raters ≈ 200 items ≈ 7 sessions — 1–2 week calendar window.
- Raters work in parallel; neither sees the other's work pre-§6.

## 8. Power analysis

**N=100 floor.** Per `SE(κ) ≈ √((1−κ)/N)` at κ=0.7:

| N    | SE    | ±1.96·SE | κ̂ for LCI=0.7 |
|------|-------|----------|----------------|
| 50   | 0.077 | ±0.151   | ≈0.85 (tight)  |
| 100  | 0.055 | ±0.107   | ≈0.81 (floor)  |
| 200  | 0.039 | ±0.076   | ≈0.78 (comfy)  |

**Bootstrap (not parametric CI)** because the SE formula assumes
asymptotic normality that fails at moderate N near boundaries. Paired
percentile bootstrap (Efron 1979; Efron & Tibshirani 1993 §13.3 floor
of 10k resamples) is distribution-free. Paired resampling preserves
rater-pair correlation structure.

## 9. Recording format

One CSV per rater:

```
item_id,rater_id,label,timestamp,duration_s
g-001,rater-A,pass,2026-05-01T10:32:00Z,42
g-002,rater-A,fail,2026-05-01T10:33:15Z,58
```

- `item_id`: opaque stable identifier
- `rater_id`: anonymous short code (e.g. `rater-A`); real-name mapping
  kept off-repo
- `label`: agreed vocabulary (e.g. `pass` / `fail`, `safe` / `unsafe`)
- `timestamp`: ISO 8601 UTC
- `duration_s`: fatigue-analysis signal

Files live at `benchmarks/calibration-samples/grades/<rater_id>.csv`;
**gitignored** until §6 concludes.

## 10. Retention

- **Raw grades (CSV):** off-repo local, 7 years per `docs/rotation-log.md`
  human-subject labelling policy.
- **Aggregated outputs** (κ, CI, band, transition log): public in
  `.claude/benchmarks/human-sample-calibration.md` §13 and
  `benchmarks/calibration-samples/analysis/<year-quarter>-run.md`.
  No rater PII, no audit payloads — only anonymised `rater_id` and
  computed stats.
- **Deletion:** raw grades deleted at 7-year boundary via standard
  backup-audit rotation. Aggregated outputs permanent.

## 11. Ethics

Raters informed of purpose (judge calibration for ceo-orchestration).
Compensation at Owner's standard contractor rate if paid; volunteers
sign waiver. Free to withdraw at any time (partial session regraded by
replacement). Anonymised in all public outputs.

## 12. References

- Cohen (1960) EPM 20(1) 37-46; Landis & Koch (1977) Biometrics 33(1)
  159-174; Efron (1979) Ann. Stat. 7(1) 1-26; Efron & Tibshirani (1993)
  *An Introduction to the Bootstrap*; Snow et al. (2008) EMNLP.
- ADR-030 (LLM-as-judge methodology).
- PLAN-011 Phase 3 §H5; PLAN-012 Phase 4 D2.
- `.claude/benchmarks/human-sample-calibration.md` — living κ protocol.
- `docs/measurement-protocols.md` — cross-flip statistical methods.
