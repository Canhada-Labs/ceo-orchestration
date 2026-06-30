# Measurement protocols — PLAN-012 flip metrics

> **Owner:** Principal QA Architect.
> **Purpose:** central reference for statistical methods per PLAN-012
> flip criterion. Each flip points here instead of redefining methods
> locally. Criteria are falsifiable only if the method is specified.
> "FPR ≤ 5%" without N or CI is theatre.

## 1. Why pin methods per flip

Sprint 11 shipped ten flip criteria of varying statistical rigour.
Round-1 debate (QA §CRITICAL/HIGH, consensus §C2/C3/C5) documented
several flips would produce confidently wrong decisions — e.g. Flip #2
"N≥30" gave Wilson 95% CI on p̂=5% of [0.9%, 16.5%], unable to
distinguish 5% from 15%. This doc is the fix: one pre-registered method
per flip. Changing mid-window requires `/debate` + ADR amendment.

## 2. Method catalogue

Four families. Wrong family → right-looking number for wrong question.

### 2.1 Binomial proportion — Wilson score interval

Use for FPR / FN / any proportion `p̂ = k/N`.

**Wilson (1927):**
```
          p̂ + z²/(2N) ± z·√(p̂(1−p̂)/N + z²/(4N²))
CI(p) =  ──────────────────────────────────────────
                      1 + z²/N
```
z = 1.96 for 95%. Preferred over normal approximation at moderate N.

**Sample size:** `N ≥ z² · p̂·(1−p̂) / h²` for half-width h. At p̂=5%,
h=2% → N ≈ 457; h=5% → N ≈ 73.

**Example — Flip #1 (output safety).** Target FPR ≤ 0.2% with 95%
upper-CI. At p̂ = 0.1%, N ≥ ~3000 (consensus §C2). Pair with FN rate
on `benchmarks/output-safety-redteam.yaml` (≥200 planted across 7
families + 30 Unicode evasions).

**Example — Flip #2 (budget).** N ≥ 100 over-cap events + Wilson upper
CI ≤ 5%. Floor; larger if traffic permits.

### 2.2 Inter-rater / intra-rater agreement — Cohen's κ + bootstrap CI

Use for nominal-label agreement (inter-rater) or test-retest (intra-rater).

**Cohen (1960):** κ = (p_o − p_e) / (1 − p_e). p_o = observed agreement
rate; p_e = chance-agreement from marginals.

**Asymptotic SE (sanity only):** `SE(κ) ≈ √((1−κ)/N)`. Fleiss-Cohen-
Everitt upper-bound. Not authoritative at moderate N.

**Authoritative CI: percentile bootstrap.** 10 000 paired resamples
(Efron & Tibshirani 1993 §13.3 floor). Takes 2.5th/97.5th percentile of
κ distribution. Paired bootstrap preserves rater-pair correlation.

**Sample size at κ=0.7:**

| N    | SE    | ±1.96·SE | κ̂ for LCI=0.7 |
|------|-------|----------|----------------|
| 30   | 0.100 | ±0.196   | ≈0.90 (unrealistic) |
| 50   | 0.077 | ±0.151   | ≈0.85          |
| 100  | 0.055 | ±0.107   | ≈0.81          |
| 200  | 0.039 | ±0.076   | ≈0.78          |

N=100 floor; N=200 comfortable.

**Landis-Koch (1977) bands:** poor ≤0.20; fair 0.21–0.40; moderate
0.41–0.60; substantial 0.61–0.80; almost-perfect 0.81–1.00.

**Example — Flip #D2 (judge calibration).** N ≥ 100, bootstrap 95%
CI_lower ≥ 0.7, intra-rater κ ≥ 0.8 on 10-item retest. SOP:
`docs/labelling-sop-judge-calibration.md`.

**Tool:** `.claude/scripts/k-calibration.py` — exits 0 iff CI_lower ≥
threshold.

### 2.3 Paired effect size — paired bootstrap / permutation

Use for **differences** between paired systems (Δrecall@5 between
embedding backends on same query set).

**Paired bootstrap.** 10 000 resamples of item-pair indices, compute
`score_A − score_B` per resampled set. 95% CI = 2.5th–97.5th percentile
of Δ distribution. Significant at α=0.05 iff CI excludes zero.

**Paired permutation.** H₀: A, B exchangeable. 10 000 permutations
swap A/B within each pair; p-value = fraction of |permuted| ≥ |observed|.

**Sample size:** N ≥ 200 paired items for 5-point Δrecall@5 at 95% CI
half-width ≤ 2 points.

**Example — Flip #10 (real embeddings).** N ≥ 200 stratified query-
pairs; paired bootstrap 95% CI on Δrecall@5 strictly excludes zero,
direction positive ≥ 5 points. PII-scrub pre-embed + opt-out header
per consensus §S1.

### 2.4 Distribution drift — Mann-Whitney U

Use when the metric is a distribution (p99 latency) across repeated
time buckets. Question: has the distribution drifted?

**Mann-Whitney U (1947):** non-parametric, no normality assumption.
Applied to first-3 vs last-3 weekly p99 measurements. p > 0.10 → no
drift evidence; flip permitted.

**Variance metric (define explicitly):**
`(max(p99) − min(p99)) / median(p99) ≤ 0.20` over N ≥ 6 weekly runs per
hook (consensus §MEDIUM-Flip-#7). "±20% variance" without formula is
unfalsifiable.

**Example — Flip #7 (perf-profile).** N ≥ 6 weekly p99 runs per hook.
Both: `(max − min) / median ≤ 0.20` AND Mann-Whitney U p > 0.10 on
first-3 vs last-3.

## 3. Per-flip method assignment (PLAN-012)

| Flip | Name | Family | N | Threshold | Tool |
|------|------|--------|---|-----------|------|
| #1 | Output safety FPR/FN | 2.1 + RT corpus | ≥3000 labelled (2-rater κ≥0.8) + ≥200 planted | FPR upper-CI ≤0.2%, FN≤target | `k-calibration.py`; manual Wilson |
| #2 | Budget 0→1 | 2.1 | ≥100 over-cap events | upper-CI ≤ 5% | manual Wilson |
| #3 | Confidence gate | 2.1 + 2nd blinded | ≥50, κ≥0.6 on 10% sample | Owner-labelled FPR upper-CI ≤5%, κ≥0.6 | `k-calibration.py` |
| #4 | OTEL export 0→1 | 2.1 + zero-baseline guard | ≥50 export attempts + rate stable ±20% | stable non-zero rate | manual |
| #5 | Chaos 0→1 | 2.1 per-mode | 120 runs (6 hooks × 5 modes × 4 wk) | per-mode upper-CI ≤5% | manual Wilson |
| #6 | Real embeddings 0→1 | 2.3 | ≥200 query-pairs | Δrecall@5 CI excludes zero; PII-scrubbed | `k-calibration.py` (CI only) |
| #7 | perf-profile 0→1 | 2.4 | ≥6 weekly runs | range/median ≤ 0.20 AND MWU p > 0.10 | manual |
| #8 | docs-freshness 1→2 | binary | 2 consecutive clean CI on main | binary | CI gate |
| #9 | Adopter confidence | 2.1 + stratified (deferred S16) | 2 adopters × 50 spawns | per-adopter upper-CI ≤5%, κ≥0.6 | `k-calibration.py` |
| #10 | Real-embeddings promotion | 2.3 | ≥200 stratified | Δrecall@5 LCI > 0; opt-out confirmed | `k-calibration.py` |
| D2 | Judge calibration | 2.2 | ≥100 inter + n=10 intra | CI_lower ≥ 0.7; κ_intra ≥ 0.8 | `k-calibration.py` |

Notes:
- Flips #1/#2/#4/#9 volume-bound; deferred to Sprint 15/16 per §C7
  (private-repo event rate can't produce required N in 30-day window).
- Flip #8 deterministic binary; CI math neither required nor
  appropriate.

## 4. SOPs

Every labelling flip needs a **pre-registered SOP**. SOP locks before
collection; changes require ADR amendment.

- `docs/labelling-sop-judge-calibration.md` — Flip #D2 (and a sibling
  SOP needed for Flip #1's N≥3000 labelling when that deferred
  window opens).

Covers: sample selection, rater eligibility, blinding, labelling UI,
consensus rule, timing, power analysis, recording format, retention,
ethics.

## 5. Why not alternative methods?

**Not "N=30 + point estimate":** Wilson 95% CI at N=30, p̂=5% is
[0.9%, 16.5%]. Flipping on that means shipping either 5% or 15% FPR
without knowing which. §C3 rejects.

**Not scipy/numpy:** ADR-002 stdlib-only. Bootstrap-over-loops is
sub-1s for N=100 × 10k iterations on 2020 hardware. Reproducibility
across Python minors > numpy minors. Rater hours, not μs, are the
bottleneck.

**Not parametric CI instead of bootstrap:** `SE ≈ √((1−κ)/N)` assumes
asymptotic normality that holds only at large N far from boundaries.
Our regime (N=100, κ̂ near 0.7–0.8) is exactly where the parametric
approximation fails. Bootstrap is distribution-free — textbook
preference.

**Not t-test for Flip #7:** t-test assumes normal p99 samples. p99 is
a right-skewed tail statistic. Mann-Whitney U is distribution-free and
conservative.

## 6. References

- Wilson (1927) JASA 22 209-212.
- Cohen (1960) EPM 20(1) 37-46.
- Mann & Whitney (1947) Ann. Math. Stat. 18(1) 50-60.
- Landis & Koch (1977) Biometrics 33(1) 159-174.
- Efron (1979) Ann. Stat. 7(1) 1-26.
- Efron & Tibshirani (1993) *An Introduction to the Bootstrap*.
- PLAN-012 stub (`.claude/plans/PLAN-012-sprint-12-stub.md`).
- PLAN-012 Round-1 debate consensus
  (`.claude/plans/PLAN-012/debate/round-1/consensus.md`).
- ADR-030 — LLM-as-judge methodology.
- `.claude/benchmarks/human-sample-calibration.md` — living κ protocol.
- `docs/labelling-sop-judge-calibration.md` — pre-registered SOP.
