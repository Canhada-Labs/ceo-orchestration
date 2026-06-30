---
plan_id: PLAN-EXAMPLE-EDTECH
title: "Launch at-risk early-warning dashboard for advisors"
status: draft
owner: ceo
level: L3
squad: edtech
profile: core,frontend,edtech
created_at: 2026-04-14
---

# Example PLAN — At-Risk Early-Warning Dashboard

> **This is an illustrative example**, not a real plan. It shows
> how the edtech squad coordinates on a feature that touches all
> three VETO scopes (privacy, integrity, fairness).

## 1. Problem

Higher-ed advising teams want a dashboard that surfaces undergraduate
students who are trending toward course failure or dropout in the
current term, early enough to intervene.

Sources:
- Grade events (from the assessment-integrity pipeline)
- Engagement telemetry (LMS time-on-task, resource access)
- Attendance (SIS roster × classroom check-ins)

## 2. Scope

**In:**
- Advisor-facing dashboard with per-student risk score
- Fairness evaluation per retrain
- Opt-out propagation to training data
- Aggregate roll-up per advisor caseload (suppressed when N<5)

**Out:**
- Student-facing surface (advisor-only for v1)
- Automated outreach (human-in-the-loop only)
- K-12 use case (higher-ed only for v1; K-12 requires parental
  consent surface that's out of scope)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Data sourcing | Priya Narayanan | PII inventory entry; confirm no URL-bound identifiers (EDTECH-001) |
| P2 — Opt-out pipeline | Marcus Olatunde + Dr. Léa Mbeki | Opt-out propagates to training data snapshots (EDTECH-016) |
| P3 — Model + fairness eval | Dr. Léa Mbeki | Per-subgroup FPR/FNR report, calibration plot (EDTECH-015, EDTECH-018) |
| P4 — Dashboard UI | Jin-Soo Ramirez + frontend team | Calibration interval shown, feature attributions (EDTECH-017), color-blind-safe |
| P5 — Aggregation floor | Dr. Léa Mbeki | N≥5 cell suppression + cross-tab check (EDTECH-014) |
| P6 — Access control | Konstantin Ferreira + security | Advisor-only; audit-log every view |
| P7 — Launch review | CEO + all VETO holders | Privacy + fairness sign-off |

## 4. Risk axes & VETO holders

- **Priya Narayanan (Privacy):** PII in telemetry → BLOCK if any
  student identifier leaks to analytics/SDK.
- **Konstantin Ferreira (Integrity):** Grade source must be
  append-only feed, not mutable snapshot.
- **Dr. Léa Mbeki (Analytics Fairness):** Per-subgroup FPR > 2x
  majority → BLOCK launch.

## 5. Task chains invoked

- `edtech-launch-prediction-model` — runs per model retrain
- `edtech-deploy-assessment-feature` — skipped (no assessment surface)

## 6. Acceptance

- Fairness report archived, versioned
- Opt-out respected in training + inference
- Calibration interval visible on every risk card
- Cross-tab suppression validated via synthetic test dataset
- Cross-district leakage test: advisor at School A cannot see
  School B's students

## 7. Metrics

- Number of students flagged per advisor per week
- Intervention conversion rate (flagged → advising session)
- **Disparate intervention rate per subgroup** (monitored post-launch)

## 8. References

- `.claude/skills/domains/edtech/skills/learning-analytics/SKILL.md`
- `.claude/skills/domains/edtech/skills/student-data-privacy/SKILL.md`
- `.claude/skills/domains/edtech/task-chains.yaml` — `edtech-launch-prediction-model`
- ADR-025 (edtech squad dogfood)
