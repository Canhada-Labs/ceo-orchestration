---
plan_id: PLAN-EXAMPLE-HRR
title: "Launch attrition prediction model for voluntary turnover early warning"
status: draft
owner: ceo
level: L3
squad: hr
profile: core,hr
created_at: 2026-05-10
---

# Example PLAN — Launch attrition prediction model for voluntary turnover early warning

> **This is an illustrative example**, not a real plan. It shows how the
> HR squad coordinates on launching a people-analytics model that touches
> protected-class fairness, employee PII, and manager-facing prediction output.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/hr/task-chains.yaml`

## 1. Problem

A 1,200-person technology company has experienced 24% voluntary attrition
in the trailing year, significantly above its industry peer benchmark of
16%. The People Analytics team has built a gradient-boosted model on 3
years of HRIS data (tenure, performance ratings, compensation bands, team
size, manager tenure, promotion lag, engagement survey scores) that
predicts 90-day voluntary departure risk. The model has 78% accuracy on
held-out data. Leadership wants to surface risk scores to HRBPs and
direct managers so they can initiate retention conversations.

Sources:
- HRIS export: 3 years of employment data across 1,200 current + 850
  former employees
- Engagement survey: quarterly scores from 2023-2025 (72% response rate)
- Performance reviews: 3 cycles, annual, manager-rated 1-5 scale

## 2. Scope

**In:**
- Fairness evaluation per protected class (gender, race where legally
  collectable, age bracket) before any manager-facing output
- HRBP-facing dashboard showing team-level risk distribution (individual
  scores NOT exposed to managers directly — only HRBPs)
- Opt-out mechanism: employees can opt out of having their data used in
  the model (LGPD consent-lifecycle requirement)
- Re-evaluation schedule: quarterly retrain with fairness re-audit

**Out:**
- Automated manager notifications triggered by risk score (manual HRBP
  outreach only — no algorithm-driven push to manager without human review)
- Use of model output in compensation or performance decisions (prohibited)
- Collecting new PII fields not already in HRIS for model improvement

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Data audit | Daniel Kwon | Training data minimum-necessary review + opt-out exclusion confirmed |
| P2 — Fairness evaluation | Daniel Kwon | Per-class disparate-impact analysis, confusion matrices, FPR/FNR tables |
| P3 — Access-control design | Isabel Meireles | HRBP-only access, manager exclusion confirmed, compensation data redacted |
| P4 — Opt-out mechanism | Isabel Meireles + Daniel Kwon | LGPD-compliant opt-out, propagation to training data pipeline |
| P5 — HRBP dashboard | Daniel Kwon | Team-level aggregation only, N<5 suppression, no individual score display to managers |
| P6 — Launch review | CEO + all VETO holders | Fairness sign-off + Operations sign-off before HRBP rollout |

## 4. Risk axes and VETO holders

- **Daniel Kwon (People Analytics Lead):** The model is trained on
  historical performance ratings which may encode manager bias. Disparate-
  impact analysis per gender and race is required before launch → BLOCK if
  FPR for any protected class exceeds 2x the majority rate, or if any
  subgroup cell in the dashboard has N<5 (HRR-009, HRR-010).
- **Isabel Meireles (HR Operations Lead):** Compensation data included in
  training features must not be individually visible on the HRBP dashboard.
  Risk scores must never be used as justification for performance or
  compensation decisions → BLOCK if compensation fields are exposed in
  dashboard output or if any policy document implies risk scores influence
  pay decisions (HRR-002).
- **Larissa Andrade (Recruitment Compliance Specialist):** Not directly
  applicable to this plan's core scope, but Larissa will review if the
  model output is ever extended to recruitment (predicting new-hire
  attrition from hiring-stage signals) — that extension requires a
  separate plan with disparate-impact analysis on protected classes at
  hiring stage.

## 5. Task chains invoked

- `hr-hire-to-onboard` — skipped for this plan (no new hire involved);
  will be invoked if HRBP rollout requires onboarding new HRBP users to
  the dashboard.
- `hr-structured-recruitment` — skipped for this plan.
- Custom analytics launch sequence: data-audit → fairness-evaluation →
  access-control-design → opt-out-mechanism → dashboard-build → launch-review.
  This sequence mirrors the edtech `edtech-launch-prediction-model` chain
  adapted to the HR domain and LGPD employment context.

## 6. Acceptance

- Training data opt-out exclusion: employees who exercised LGPD opt-out
  are excluded from both training and inference (HRR-009 minimum standard)
- Fairness evaluation: per-class confusion matrices, FPR/FNR tables
  archived before any HRBP sees a score (HRR-009)
- No subgroup cell with N<5 displayed in HRBP dashboard (HRR-010)
- HRBP-only access: direct managers cannot query individual employee risk
  scores; they receive only HRBP-mediated retention conversation prompts
- Compensation data: not exposed in dashboard output, redacted from any
  model explanations shown to HRBPs (HRR-002)
- Quarterly retrain schedule committed with fairness re-evaluation gate (HRR-011)
- Opt-out mechanism live before model is exposed to any user (consent-lifecycle)

## 7. Metrics

- Voluntary attrition rate 90-day post-intervention cohort vs. control
  (HRBPs who used model vs. who did not)
- Model precision and recall at the 0.6 risk-score threshold (HRBP action
  threshold)
- **Per-class FPR stability across quarterly retrains** (monitored post-launch;
  any retrain where FPR for any protected class exceeds 2x majority rate
  triggers HRR-011 remediation review)

## 8. References

- `.claude/skills/domains/hr/skills/hr-onboarding/SKILL.md`
- `.claude/skills/domains/hr/skills/recruitment-specialist/SKILL.md`
- `.claude/skills/domains/hr/task-chains.yaml` — `hr-hire-to-onboard`
- `.claude/skills/domains/hr/pitfalls.yaml` — HRR-002, HRR-009, HRR-010, HRR-011
- ADR-009 — squad-bundle completeness contract
