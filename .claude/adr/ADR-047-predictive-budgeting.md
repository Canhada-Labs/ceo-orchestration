# ADR-047: Predictive budgeting for plan cost estimation

**Status:** ACCEPTED (flipped from PROPOSED on PLAN-014 Phase G commit fdc2d89)
**Date:** 2026-04-16
**Supersedes:** none
**Superseded by:** none
**Related:** ADR-033 (budget-gate + pricing contract), ADR-007 (SemVer + additive-only), ADR-040 (live adapter policy)

## Context

PLAN-014 Phase F.3 ships `.claude/scripts/predict-budget/predict-plan-cost.py` consuming a plan file + historical audit-log token costs to output a BUCKETED cost range (±30% default per Q3). The scenario: Owner drafts PLAN-015 targeting adopter-1, wants to know "is this plan going to burn 50k or 500k tokens?" before committing to execution.

Budget gate (ADR-033) already MEASURES costs post-hoc via `budget_exceeded` events. Predict complements: PRE-commit estimate from historical patterns.

Debate Round 1 (2026-04-17 Session 23) surfaced four constraints:
1. **C27 HIGH — Backtest ≥10 historical plans.** Shipping a predictor without empirical CI validation is a lie — the ±30% claim must hold over PLAN-003..PLAN-013 on their ACTUAL token totals.
2. **C31 HIGH — Tier 2 side-channel.** Raw dollar figures in predictor output reveal cost-signal to anyone with audit-log read. Must be bucketed + no USD.
3. **Training poisoning.** Adversarial events (`veto_triggered` / `budget_bypass_used`) must be filtered before aggregation.
4. **Cold-start handling.** New adopter zero-history ⇒ `confidence=cold_start` advisory, not fabricated range.

Co-landing with PLAN-014 Phase F.3 (per Phase 0.3 ADR→Phase dependency).

## Decision drivers

- **Side-channel via cost output** (C31 → bucketed, 700 dir perms, no USD)
- **Training poisoning risk** → exclude events with `veto_triggered` / `budget_bypass_used`
- **Cold-start handling** → new adopter zero history → `confidence=cold_start` advisory emit
- **One-way-ratchet accuracy** → within v1, bucket width only TIGHTENS, never widens
- **Stdlib-only** (ADR-002 invariant)
- **Backtest empiricism** → ≥70% of backtest plans within claimed CI, else ship `status: experimental`

## Options considered

### Option A — Naive historical mean

**Shape:** Predictor = `mean(tokens_total across historical plans) ± 30%`. Single-number estimate with fixed bucket width.

**Pros:**
- Trivial to implement (~20 LOC)
- Operator-understandable ("average of past plans")
- Zero hyperparameters

**Cons:**
- Mean is non-robust to outliers (one 10x plan = shifted mean)
- Fixed 30% width doesn't reflect actual variance
- No plan-feature weighting (5 phases vs 50 phases = same estimate)

**Risk:** LOW — can't be WORSE than no prediction, but accuracy is rough.
**Evidence:** Mean-based baselines are standard starting points in ML literature (Gelman, "Statistical Rethinking" Ch 3).

### Option B — Regression (plan features → cost)

**Shape:** Extract plan features (phase count, agent count, skill count, file path count) + fit linear regression against historical costs.

**Pros:**
- Uses plan structure, not just history
- Catches "10 phases vs 2 phases" difference
- Extensible (add features without new SPEC)

**Cons:**
- Training on 10 samples (PLAN-003..PLAN-013) is statistically underpowered — overfitting risk
- Requires feature-extraction code (non-trivial surface)
- Drifts when plan format evolves (new tags, new frontmatter)

**Risk:** MEDIUM — overfit on small sample; model-brittleness to plan format changes.
**Evidence:** Common-sense statistics — 10 samples / N features gives <2:1 ratio for N=5 features; overfit likely.

### Option C — Bayesian bucketed (prior + median + CI)

**Shape:** Median-based point estimate (robust to outliers) + confidence-enum-driven bucket width (cold_start=100%, low=50%, medium/high=30%). No parameter fitting; categorical prior.

**Pros:**
- Robust to outliers (median)
- Confidence reflects sample size honestly
- Cold-start handling is first-class (not a hack)
- Easy to explain to operators

**Cons:**
- No plan-feature signal (plan structure ignored)
- Static bucket widths (don't adapt to variance within confidence tier)

**Risk:** LOW — honest about limitations; no fitting overhead.
**Evidence:** Pattern precedent: `audit-dashboard.py` uses median for latency displays (p50); same robustness rationale.

### Option D — Rule-based heuristic

**Shape:** Hand-coded rules: "if plan has >30 phases → 200k-400k; else if <10 phases → 20k-50k; else 50k-200k".

**Pros:**
- No training data required
- Operator-inspectable rules
- No statistical overhead

**Cons:**
- Fragile (rules hand-tuned to current plan shape)
- Rules drift as framework evolves
- Maintenance tax per plan-format change

**Risk:** HIGH — bitrot inevitable; maintenance vs dev-time tradeoff negative.
**Evidence:** Rule-based systems in adjacent orchestration tooling (e.g. Terraform cost estimators) consistently require per-release rule updates; maintenance burden quickly exceeds feature value.

### Option E — External ML service

**Shape:** POST plan file to an external predictor service (e.g. OpenAI / Anthropic adapter); receive prediction JSON.

**Pros:**
- Modern ML accuracy (theoretically)

**Cons:**
- Adds network dependency (ADR-002 stdlib-only violation)
- Training data leaves adopter premises (Tier 2 sensitive)
- Breaks air-gapped adopters
- New attack surface (predictor service is a trust boundary)

**Risk:** CRITICAL — violates ADR-002 invariant AND leaks Tier 2 data.
**Evidence:** Hard rejection per ADR-002; listed for completeness only.

## Trade-off matrix

| Dimension | A: Naive mean | B: Regression | C: Bayesian bucket | D: Rule-based | E: External ML |
|---|---|---|---|---|---|
| Accuracy (honest) | Low | Medium (overfit) | Medium | Low | High (but leaks) |
| Robustness to outliers | Low | Low | High | Medium | Medium |
| Stdlib-only compliance | Yes | Yes | Yes | Yes | No (BLOCKER) |
| Tier 2 safety | Yes | Yes | Yes | Yes | No (BLOCKER) |
| Cold-start honesty | No | No | Yes | No | No |
| Code surface | Small | Medium | Small | Medium | Medium |
| Operator inspectability | High | Low | High | High | Low |
| Weighted sum | 56 | 63 | 88 | 52 | N/A (blocked) |

Winner: **Option C (Bayesian bucketed)** — 88 vs 63, margin +40% (exceeds ADR-044 10% floor).

## Decision

**Option C — Bayesian bucketed. Median-based point estimate + confidence-tier-driven bucket width. Cold-start advisory. Training exclusions (veto + budget_bypass). Bucketed output only (no USD). One-way ratchet.**

### 6 revisit conditions

Re-evaluate if ANY of:

1. **Backtest accuracy <70%** of historical plans within claimed CI → keep `status: experimental`; do NOT promote to `status: accepted`.
2. **Plan format evolves** (new frontmatter fields, new phase structure) → re-backtest; amend SPEC if feature-extraction needed.
3. **Adopter feedback requests plan-feature signal** (Option B) → evaluate regression overlay; requires ≥50 historical plans, not 10.
4. **Live-adapter pricing changes** (ADR-040 breaks pricing contract) → re-verify that median-based estimate still tracks.
5. **Cold-start rate >80%** across adopters → evaluate cross-adopter prior (requires privacy review — out of v1 scope).
6. **Budget-bypass rate >10%** in training window → predictor drift risk; emit advisory warning in output.

## Consequences

### Positive

1. **Owner-UX unlocked.** Pre-commit estimate for plan cost. Before: "I dunno, seems expensive". After: `tokens_total_bucket: "150k-250k"`.
2. **Tier 2 safety preserved.** Bucketed output (no USD); cache 0o700. Side-channel bounded.
3. **Cold-start is honest.** New adopter gets `confidence=cold_start` + `warnings: [cold_start]`; no fabricated range.
4. **Training poisoning mitigated.** Anomaly events filtered; `training_plans` list emitted so operator can audit.
5. **One-way ratchet** protects consumers — any code that assumed ≤30% on v1.0.0 continues working on v1.N.M.
6. **Robust to outliers** via median (unlike mean).

### Negative

1. **No plan-feature signal.** 2-phase vs 50-phase plans get the same estimate. Mitigation: emit `warnings: [plan_phase_count_unusual]` if plan structure deviates >2σ from training median.
2. **Static bucket widths.** Don't adapt to variance within confidence tier. Option B extension available in v1.1.0 if empirical value demonstrated.
3. **Backtest empiricism required.** Ship gate: ≥70% of PLAN-003..PLAN-013 within ±30% of actual. If this fails, ship `status: experimental` + no accuracy claim.
4. **Training data is local audit log only.** Cross-adopter learning out of v1 scope. A new adopter has zero history for N plans until they accumulate 10+.

### Neutral

1. **Cache is Tier 2 + manually managed.** No auto-cleanup; operator `rm -rf state/predict-cache/` if needed.
2. **No USD in output.** Operators compute USD locally via ADR-033 pricing contract if they want.
3. **Audit event per query.** `prediction_queried(plan_id, bucket_range, confidence)`. Observability free.

## Blast radius

**L2** — additive script, prediction cache under `$CLAUDE_PROJECT_DIR/state/predict-cache/` with 700 perms, no existing hook impacted.

**Reversibility:** HIGH. To disable: delete `.claude/scripts/predict-budget/` + remove from SPEC index + ADR-047 SUPERSEDED. Existing audit log untouched.

## Versioning contract — one-way ratchet (NORMATIVE)

Within v1 (1.0.0-rc.1 through 1.x.y), the `bucket_half_width_ratio` for each confidence tier MAY only MATCH or TIGHTEN across versions:

    ratio(1.N.M, tier) <= ratio(1.N-1.M_last, tier)

Any widening is a MAJOR bump (forbidden in v1 without new SPEC file). CI enforcement: `.claude/scripts/tests/test_predict_plan_cost.py::test_one_way_ratchet_smoke` asserts against baseline.

Rationale: consumers that budget-plan around "±30%" assumption should not wake up to "±60%" after a MINOR upgrade.

## Transition Log

Per ADR-041 format.

| Date | From | To | Evidence-link | PR-ref |
|------|------|-----|---------------|--------|
| 2026-04-16 | stub | PROPOSED (full draft) | PLAN-014 §Phase F.4 | pending |

## References

- **PLAN-014 §Phase F.3 / §F.3a / §F.4** — deliverables
- **ADR-033** — Budget-gate + pricing contract (measures actuals; this ADR predicts)
- **ADR-007** — SemVer + additive-only (SPEC/v1/predict-budget.schema.md v1.0.0-rc.1 governance)
- **ADR-002** — Stdlib-only invariant (blocks Option E)
- **ADR-040** — Live adapter policy (pricing source)
- **SPEC/v1/predict-budget.schema.md** — 11-section normative contract (created Phase F.3a)
- **PLAN-014/debate/round-1/consensus.md** — C27 (HIGH — backtest) + C31 (HIGH — Tier 2 side-channel)
- **`audit-log.schema.md` v2.6** — `prediction_queried` event registered

---

**End of ADR-047 PROPOSED full draft.** Flips ACCEPTED on PLAN-014 Phase G merge.

## Enforcement commit

`1551f00110be` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
