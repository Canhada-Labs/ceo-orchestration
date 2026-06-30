---
plan_id: PLAN-EXAMPLE-HCR
title: "Add symptom-checker flow to patient portal with clinical routing"
status: draft
owner: ceo
level: L3
squad: healthcare
profile: core,healthcare
created_at: 2026-05-10
---

# Example PLAN — Add symptom-checker flow to patient portal with clinical routing

> **This is an illustrative example**, not a real plan. It shows how the
> healthcare squad coordinates on a feature that touches PHI, clinical
> escalation logic, and marketing analytics on patient-facing pages.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/healthcare/task-chains.yaml`

## 1. Problem

A healthcare network wants to reduce unnecessary emergency department
visits by adding a symptom checker to the patient portal. The checker
will ask guided questions about symptoms, recommend urgency level
(self-care / schedule appointment / urgent care / call 911), and offer
an immediate telehealth connection for moderate-urgency cases. The
current portal has a Meta Pixel active on all pages for marketing
attribution purposes.

Sources:
- Clinical leadership: 22% of ED visits assessed as primary-care
  appropriate in the trailing year
- Patient services: top complaint is inability to self-triage without
  calling the nurse line
- Digital team: Meta Pixel currently fires on all pages including the
  appointment scheduling and patient login pages

## 2. Scope

**In:**
- Symptom intake form with urgency classification logic (self-care /
  appointment / urgent care / 911 escalation)
- Telehealth connection path for moderate-urgency cases
- Safe-messaging overlay for mental health or self-harm symptom keywords
- Meta Pixel consent-mode reconfiguration for patient-portal pages
- PHI dataflow mapping for symptom data stored or transmitted

**Out:**
- Clinical decision support algorithm (requires separate clinical
  validation and regulatory pathway — not in this plan)
- Insurance verification or billing during triage (separate workflow)
- Changes to the nurse line IVR routing (separate operations scope)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — PHI mapping | Bruno Alencar | PHI inventory updated for symptom data fields + egress paths |
| P2 — BAA coverage | Fernanda Luz | Vendor BAA audit for symptom data pipeline, telehealth vendor, analytics |
| P3 — Clinical routing design | Dr. Rodrigo Alves | Urgency classification logic + safe-messaging overlay design |
| P4 — Pixel consent-mode | Valentina Rosario | Consent-mode configured to block Meta Pixel on portal pages pre-consent |
| P5 — Patient UX | Camila Oliveira | Complaint path, interpreter access, and clinical routing UX review |
| P6 — Launch review | CEO + all VETO holders | Compliance + Clinical + Marketing sign-off |

## 4. Risk axes and VETO holders

- **Fernanda Luz (Compliance Officer):** Symptom data is PHI under HIPAA
  and sensitive health data under LGPD. The telehealth vendor and any
  analytics vendor receiving symptom data must have a signed BAA/DPA →
  BLOCK if any vendor processes symptom data without a signed agreement on
  file (HCR-002). Meta Pixel must be blocked on all patient-portal pages
  before affirmative consent (HCR-003).
- **Dr. Rodrigo Alves (Clinical Operations Lead):** The urgency
  classification algorithm must route any ambiguous or moderate-severity
  symptom to a licensed clinician, not to a FAQ or static content →
  BLOCK if the escalation logic allows any symptom pattern associated with
  cardiac, stroke, or psychiatric emergency to reach a non-clinical
  response (HCR-005, HCR-006, HCR-007).
- **Valentina Rosario (Healthcare Marketing Compliance):** The Meta Pixel
  currently active on all portal pages is sending health-intent signals to
  Meta's algorithm. This must be resolved before the symptom checker
  launches — consent-mode must block pixel fire before opt-in on all
  portal pages (HCR-003, HCR-004).

## 5. Task chains invoked

- `healthcare-launch-patient-facing-feature` — primary chain governing
  PHI mapping → BAA coverage → retention schedule → clinical safety review
  → analytics consent-mode → patient UX → launch VETO.
- `healthcare-marketing-campaign-review` — skipped (no promotional asset
  in this plan); will be invoked separately if the symptom checker is
  promoted in marketing campaigns that reference patient outcomes.

## 6. Acceptance

- PHI inventory updated to include symptom response data, urgency
  classification output, and telehealth session metadata (HCR-001)
- BAA confirmed: telehealth vendor, any NLP/symptom-parsing vendor, and
  any analytics tool receiving symptom page data (HCR-002)
- Symptom retention schedule assigned: clinical interaction records 10
  years per CFM requirement (HCR-012)
- Clinical escalation tested: "chest pain", "shortness of breath",
  "thoughts of self-harm" all route to immediate clinician path, not FAQ
  (HCR-005, HCR-006)
- Safe-messaging overlay confirmed for mental health symptom keywords
  across phone, chat, and portal channels (HCR-006)
- Meta Pixel consent-mode: verified as blocked on all portal pages before
  affirmative opt-in; verified as not transmitting symptom-page engagement
  data to Meta audience network (HCR-003)
- Interpreter access path reachable from symptom checker for non-English
  speakers (Camila Oliveira sign-off)

## 7. Metrics

- Emergency department visit rate for portal-registered patients (measured
  at 90 days post-launch vs. prior 90-day cohort)
- Urgency classification accuracy: rate of "self-care" classifications
  later upgraded to urgent care within 24 hours (clinical safety signal)
- **Pixel consent-mode compliance rate** (monitored post-launch; any day
  where pixel fires on portal page before consent triggers HCR-003 incident
  review)

## 8. References

- `.claude/skills/domains/healthcare/skills/healthcare-customer-service/SKILL.md`
- `.claude/skills/domains/healthcare/skills/marketing-compliance/SKILL.md`
- `.claude/skills/domains/healthcare/task-chains.yaml` — `healthcare-launch-patient-facing-feature`
- `.claude/skills/domains/healthcare/pitfalls.yaml` — HCR-001, HCR-002, HCR-003, HCR-005, HCR-006, HCR-012
