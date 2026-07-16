---
id: PLAN-EXAMPLE-data-ml
title: Replace the churn model v3 with v4 behind a shadow-then-canary rollout
status: draft
created: 2026-07-13
owner: CEO
sprint: example
tags: [data-ml, model-promotion, example]
---

# PLAN-EXAMPLE — Replace churn model v3 with v4

> Example plan demonstrating how the data-ml squad routes a model
> promotion through its two-VETO process. Not for execution. Used by
> adopters as a reference template when proposing a real model
> replacement.

## 0. Thesis

Replace the production churn-prediction model (v3, gradient-boosted
trees on tabular features) with v4 (a PyTorch tabular network adding
30-day behavioral sequence features). Offline experiments suggest a
meaningful PR-AUC lift, but v4 introduces two new risks this plan must
retire: a temporal feature window (leakage surface) and a GPU serving
path (memory + rollback surface). v3 stays pinned warm as the rollback
target for the entire rollout window.

This plan exists to demonstrate the squad's promotion process
end-to-end (`data-ml-promote-model-to-production` chain).

## 1. Phases + owners

| Phase | Owner | Approver | Output |
|---|---|---|---|
| 1. Candidate training | Rafael Siqueira (Training Systems) | Priya Raghunathan | Reproducible run manifest + checkpoint |
| 2. Evaluation gate | Ingrid Solheim (Evaluation Lead) | self (VETO) | Seeded eval report + leakage checklist |
| 3. Export + serving safety | Kwame Mensah (Inference Platform) | self (VETO) | Export/parity/memory report + pinned rollback |
| 4. Monitoring wire-up | Mei-Lin Chou (ML Reliability) | Kwame Mensah | Monitors live + thresholds documented |
| 5. Staged rollout | Kwame Mensah + Mei-Lin Chou | Priya Raghunathan (go/no-go) | Shadow → canary → full |
| 6. 30-day review | All five | Priya Raghunathan | Post-deployment review |

## 2. Phase 1 — Candidate training

**Owner:** Rafael Siqueira (skill: `pytorch-patterns`)

- Implement `models/churn_v4.py` with device-agnostic placement and
  full seed control (torch CPU+CUDA, NumPy, random).
- Training run records the (code SHA, data snapshot ID, seed) triple
  in the run manifest; checkpoint carries model + optimizer +
  scheduler + epoch + RNG state.
- Sequence features are built by `features/behavior_window.py` — the
  same module the serving path will import in Phase 3 (parity by
  construction).
- Three seeds trained for the Phase 2 significance comparison.

**Acceptance:** Re-running from the manifest triple reproduces
checkpoint metrics; three seeded checkpoints delivered to evaluation.

## 3. Phase 2 — Evaluation gate

**Owner:** Ingrid Solheim (skill: `ml-evaluation-patterns`)

- Split review: churn labels are temporal — verify the split is a
  temporal holdout (train ≤ month M, validation M+1, test M+2), not a
  random shuffle. Grouped by customer ID so no customer spans splits.
- Leakage checklist: feature scalers and the behavior-window
  vocabulary fit on train only; the 30-day window for any example
  must end before its label date; test set untouched by early
  stopping or model selection.
- Metric fixed before the sweep: PR-AUC primary (churn is ~4%
  positive), recall@precision=0.8 secondary. Accuracy is not
  reported.
- Baseline table: majority class, logistic regression on v3 features,
  and production v3 itself — all three seeds of v4, mean and spread.

**Acceptance:** Seeded evaluation report shows v4 beats v3 across all
three seeds on the fixed metric; leakage checklist signed; VETO
released.

## 4. Phase 3 — Export + serving safety

**Owner:** Kwame Mensah (skill: `ml-serving-patterns`)

- Export the winning seed as safetensors; the loader path enforces
  `weights_only=True` for any torch-format fallback.
- Serving imports `features/behavior_window.py` directly; a
  golden-batch parity test (500 rows, training pipeline vs. serving
  pipeline, max abs diff < 1e-6) runs in CI.
- GPU memory measured at max batch size × max sequence length;
  documented headroom vs. the serving card's capacity.
- v3 pinned in the model registry as the rollback target, kept warm,
  load-tested at expected traffic.

**Acceptance:** Export + parity + memory report attached; rollback
drill (flip to v3 and back in staging) completes within the
documented SLA; VETO released.

## 5. Phase 4 — Monitoring wire-up

**Owner:** Mei-Lin Chou

- Input drift monitors on the top-10 features + the sequence-length
  distribution; prediction-distribution monitor on the score
  histogram.
- Delayed-label quality: weekly PR-AUC on matured labels, segmented
  by customer tenure and acquisition channel (aggregate-only
  dashboards rejected).
- NaN/data-quality alerts wired upstream of the model, so a pipeline
  break is distinguishable from drift during triage.
- Synthetic-drift injection in staging verifies each alert fires.

**Acceptance:** All monitors fire on synthetic drift; thresholds and
the retraining trigger documented in the runbook.

## 6. Phase 5 — Staged rollout

**Owner:** Kwame Mensah + Mei-Lin Chou; go/no-go by Priya Raghunathan

- Shadow window (7 days): v4 scores logged, not served; shadow-vs-v3
  score correlation and shadow-vs-offline PR-AUC delta reviewed.
- Canary at 10% of traffic: promote to full only if canary metrics
  match offline evaluation within the documented tolerance and no
  monitor fires.
- Abort criteria (any → pinned rollback to v3): quality delta beyond
  tolerance, GPU memory alarm, parity-test regression, NaN spike.

**Acceptance:** Full traffic on v4 with all monitors green; rollback
path re-verified post-promotion.

## 7. Phase 6 — 30-day review

**Owner:** All five (rotating dashboard duty)

- Weekly: delayed-label PR-AUC vs. offline expectation, per segment.
- 30-day formal review: retire v3's warm pin only if v4's matured
  metrics hold; otherwise extend the pin window.

**Acceptance:** 30-day review filed; v3 retirement decision logged.

## 8. Open questions

1. Retraining cadence: fixed monthly retrain vs. drift-triggered —
   who owns the decision when both fire in the same week?
2. Feedback loop: retention offers driven by v4's scores will alter
   future churn labels — the Phase 4 runbook flags this; the first
   drift-triggered retrain requires Ingrid's feedback-loop audit.
3. Sequence-feature backfill cost for cold-start customers: serve a
   v3-style fallback or accept degraded v4 scores?

## 9. Rollback

- The pinned warm v3 in the registry is the rollback. Any abort
  criterion flips serving to v3 within the drilled SLA; audit trail
  captured. No code rollback required.
- If drift or regression appears after full traffic, the
  `data-ml-drift-incident-triage` chain owns the response; rollback
  is step 2 of that chain.
