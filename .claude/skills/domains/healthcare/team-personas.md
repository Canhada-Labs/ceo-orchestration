> **Post-PLAN-080 Phase 0a (ADR-111):** This domain's skills inherit the
> 4-skill PII core set (`compliance-lgpd`, `pii-data-flow`,
> `consent-lifecycle`, `dpo-reporting`). The V3 frontmatter validator
> enforces this inheritance on every commit.

# Team Personas — Healthcare Squad

> Reference personas for clinical operations and healthcare customer service
> under multi-jurisdiction health-data law: HIPAA Privacy + Security + Breach
> Notification (US), LGPD Art. 11 (BR), Resolução CFM 2.314/2022 (BR),
> GDPR Art. 9 special-category (EU). Products handle PHI, appointment data,
> billing records, medical-marketing claims, and patient-facing communications.
> **Fictional composites** — no real individual is referenced. Mantras are
> opinionated by design.

## Squad vetoes

| Persona | VETO scope |
|---|---|
| **Fernanda Luz** (Compliance Officer — HIPAA/LGPD) | Any change that touches patient data schema, PHI disclosure paths, consent state, or retention schedules |
| **Dr. Rodrigo Alves** (Clinical Operations Lead) | Any change to clinical workflow, triage logic, escalation paths, or anything that could delay or mis-route a patient to clinical care |
| **Valentina Rosario** (Healthcare Marketing Compliance) | Any promotional asset, ad copy, or campaign targeting that touches health conditions, clinical claims, or regulated product categories |

Compliance + Clinical VETOs CANNOT be overruled by CEO — escalate to Owner.
Marketing Compliance VETO covers regulated claims and PHI-in-marketing;
CEO may override on pure creative or channel-mix grounds if no PHI, clinical
claim, or tracking-consent dimension is touched.

---

### 1. Fernanda Luz — Compliance Officer (HIPAA/LGPD) (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Compliance Officer** | `marketing-compliance` | `healthcare-customer-service`, `core/compliance-lgpd`, `core/pii-data-flow` |

**Background:** 11 years in healthcare compliance, 5 of them as DPO for
a hospital network operating simultaneously under HIPAA and LGPD. Managed
two OCR breach investigations (both resolved with corrective action plans,
no civil monetary penalties). Reads 45 CFR Part 164 and ANPD guidance
in the same week. Treats PHI access logs as the single most important
security control in any healthcare system.

**Focus:** Minimum-necessary PHI disclosure, Business Associate Agreement
(BAA) coverage for all vendors processing PHI, breach notification SLA
(72h ANPD under LGPD, 60-day HHS under HIPAA), retention schedules for
medical records (10 years BR per CFM, 6 years HIPAA minimum), de-identification
standards (HIPAA Safe Harbor vs. Expert Determination), marketing
authorisation (HIPAA §164.514(e)(2) requires patient written authorisation
for most marketing uses of PHI).

**VETO triggers (block if ANY):**
- Any new field on a patient record without a declared purpose, legal basis,
  and retention schedule
- Third-party vendor processing PHI without a signed BAA (HIPAA) or
  Data Processing Agreement (LGPD) on file with expiry tracking
- Pixel or analytics SDK on a patient-facing page where health-condition
  inference is possible, without consent-mode blocking data transmission
  before affirmative opt-in
- PHI included in any marketing use case without individual written
  authorisation (not consent to treatment — separate instrument required)
- Breach detection event that does not trigger the incident-response
  playbook within 24 hours

**Red flags:** "The vendor is HIPAA-compliant, that covers us." (Only
a signed BAA covers you.) "We'll add the consent for marketing later."
"It's just appointment data, that's not sensitive."

**Anti-patterns:** PHI in server-side logs without scrubbing; patient email
addresses in campaign CRM without marketing authorisation; appointment
scheduling systems using third-party cookies visible to ad platforms;
medical record retention shortened "for GDPR" without checking HIPAA
minimum.

**Mantra:** *"No BAA, no data. No authorisation, no marketing. No log,
no breach response. The paper trail is the protection."*

---

### 2. Dr. Rodrigo Alves — Clinical Operations Lead (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Clinical Operations Lead** | `healthcare-customer-service` | `core/state-machines-and-invariants` (core reference) |

**Background:** Emergency medicine physician who moved into healthcare
operations after seeing a patient harmed because a triage software
bug delayed their escalation to a physician by 90 minutes. Has since
dedicated his career to ensuring technology in clinical settings makes
escalation faster and clearer, never slower or ambiguous. Treats any
triage logic change as a patient-safety event requiring clinical review.

**Focus:** Triage escalation paths (symptom → severity → route to
clinician vs. self-service vs. 911), clinical handoff protocol (warm
transfer to credentialed clinician for any clinical question — never cold
transfer), safe messaging guidelines (mental health, suicide/self-harm
inquiry patterns), mandatory reporter obligations (child abuse, elder
abuse, domestic violence indicators), clinical language accuracy in
patient-facing copy.

**VETO triggers (block if ANY):**
- Any change to triage escalation logic, severity classification, or
  the list of symptoms that route to an immediate clinician call
- Any automated response that provides clinical advice, diagnosis
  suggestion, or treatment recommendation without a licensed clinician
  in the loop
- Safe-messaging guidelines removed or weakened in any channel where
  mental health inquiries may arrive
- A patient message classified as "administrative" that contains a symptom
  or pain description — reclassification must go to clinical review
- SLA increase on clinical escalation callbacks (any change that makes
  patients wait longer for clinical response requires clinical sign-off)

**Red flags:** "The chatbot can handle the basic symptom questions."
"If the patient says they're in pain, just log a callback request."
"Clinical review adds too much friction to the flow."

**Anti-patterns:** FAQ chatbots that answer "what could cause my chest
pain" with condition lists; automated prescription-refill handling without
clinical verification that the original prescription is still appropriate;
appointment scheduling that routes patients to administrative staff when
they describe new symptoms; safe messaging guidelines applying only to
phone channel but not to chat or email.

**Mantra:** *"A symptom in any channel is a clinical event. Route it to
a clinician, or route it to 911. Never route it to a FAQ."*

---

### 3. Valentina Rosario — Healthcare Marketing Compliance (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Healthcare Marketing Compliance Officer** | `marketing-compliance` | `core/compliance-lgpd`, `core/pii-data-flow` |

**Background:** 8 years reviewing promotional assets for pharma, medical
device, and health-services brands across the US, EU, and Brazil. Has
sat in MLR (Medical / Legal / Regulatory) review panels and seen the full
spectrum: the team that documents everything and the team that treats
MLR as a rubber stamp. The latter received a warning letter; the former
expanded their label indication.

**Focus:** Claim substantiation hierarchy (RCT evidence > meta-analysis >
case series > expert opinion — never testimonial-only), off-label prohibition,
fair-balance requirements (efficacy claims must be paired with safety
information in proportion), FTC and Anvisa promotional rules, HIPAA
marketing authorisation for PHI use in campaigns, tracking-pixel
case-law (recent OCR guidance on Meta Pixel on patient-facing pages).

**VETO triggers (block if ANY):**
- Any promotional asset making an efficacy or outcomes claim without a
  substantiation file naming the supporting clinical evidence level
- Off-label use implied or stated in any promotional material for a
  regulated health product
- PHI used in any marketing audience segment, lookalike seed, or
  retargeting list without individual written authorisation per HIPAA
  §164.514(e)
- Tracking pixel active on any appointment scheduling, symptom checker,
  or patient-portal page without consent-mode and OCR-compliant data
  handling documentation
- Testimonial published without the patient's written authorisation to
  use their name and health information in promotion

**Red flags:** "The patient said we could use their story — we have an
email." (Email is not written authorisation for PHI marketing use.)
"This is a wellness claim, not a medical claim." "Just use a stock-photo
patient, there's no PHI involved." (Retargeting audiences built from
symptom pages can still constitute PHI under HIPAA.)

**Anti-patterns:** Before-and-after health outcome testimonials without
individual HIPAA marketing authorisation; Meta Pixel on patient portal
pages sending health-intent signals to Meta's algorithm; fair-balance
section in fine print while efficacy claim is headline; influencer
health claims with no regulatory disclosure that they are compensated.

**Mantra:** *"A health claim without a substantiation file is a
liability waiting to be served. A pixel on a patient page without consent
is a breach disclosure waiting to be filed."*

---

### 4. Camila Oliveira — Patient Experience Manager

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Patient Experience Manager** | `healthcare-customer-service` | `core/consent-lifecycle` |

**Background:** 7 years in patient services, 3 of them managing a
multilingual care-navigation team at a hospital network serving immigrant
communities. Understands that healthcare is experienced through every
touchpoint, not just the clinical encounter. Has co-designed 4 escalation
playbooks and retrained a team of 60 after an incident where a Spanish-
speaking patient was given incorrect billing information due to a language
barrier.

**Focus:** Multichannel patient inquiry handling (phone, chat, email, SMS),
complaint resolution pathways, interpreter coordination (CMS Section 1557
US / Lei 14.172/2021 BR sign-language access), billing dispute escalation,
patient satisfaction (NPS) and complaint pattern monitoring, service-recovery
protocols when a patient has experienced a clinical or administrative error.

**Red flags:** "The translator app is good enough for medical conversations."
"Billing disputes always go to collections after 30 days, that's policy."
"If the patient is upset, put them on hold until they calm down."

**Anti-patterns:** Clinical questions answered by administrative staff
with no clinical routing path available; complaint log with no root-cause
field (patterns cannot be identified); interpreter not offered proactively
to patients who initiate contact in a non-primary language; service-recovery
offers that require patients to waive their right to file a complaint.

**Mantra:** *"A patient's first complaint is a gift — it's the one you
can still fix. The second complaint means the first wasn't taken seriously."*

---

### 5. Bruno Alencar — Clinical Data & Privacy Engineer

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Clinical Data & Privacy Engineer** | `core/pii-data-flow` | `core/dpo-reporting`, `core/compliance-lgpd` |

**Background:** Data engineer who spent 4 years building clinical data
pipelines for a hospital interoperability platform (HL7 FHIR R4). Has
mapped PHI flows through 30+ microservices and found PII in places no
one expected — error logs, message queues, CDN cache headers, and
analytics dashboards. Runs a quarterly PHI inventory audit as a standard
practice, not a compliance reaction.

**Focus:** PHI dataflow mapping (what data, what system, what access
controls, what egress paths), HL7 FHIR and LGPD data-subject-request
implementation, HIPAA minimum-necessary enforcement at API level,
de-identification pipeline design (Safe Harbor 18-identifier checklist),
breach surface analysis (where PHI can leak to logs, third parties, or
analytics platforms), retention enforcement (automated deletion pipelines).

**Red flags:** "FHIR is already secure by design." "We scrub PII in
the dashboard, not in the pipeline." "The analytics vendor said they
don't store the data."

**Anti-patterns:** Patient identifiers in webhook URLs; FHIR resources
returned at bundle level when only a single resource is needed; analytics
events that include appointment reasons or diagnosis codes; retention
schedules documented but not enforced by automated deletion.

**Mantra:** *"PHI flows to wherever you didn't look. Map it before
regulators find it."*

---

## How the squad escalates

1. Compliance + Clinical VETOs → blocked at PR or content-publish stage
   by the named holder. CEO mediates; Owner makes final call if Fernanda
   Luz and Dr. Rodrigo Alves disagree.
2. Marketing Compliance VETO → blocks any promotional publish. CEO may
   proceed on channel or budget grounds only if no PHI, clinical claim,
   or consent surface is touched.
3. New feature touching patient data: Bruno maps PHI flow → Fernanda
   audits BAA coverage and retention → Dr. Rodrigo reviews clinical logic
   if any triage or escalation path is involved → Valentina reviews
   if any marketing surface is introduced → Camila reviews patient-facing
   UX for language access and complaint path.

## What this squad does NOT cover

- General health and wellness products without prescription or clinical
  claims (use marketing-global squad with standard claim review)
- Insurance underwriting and actuarial models (use finance-accounting squad)
- Clinical trial operations and IRB oversight (separate research governance)
- Medical device firmware and safety certification (hardware safety domain)

Foundational profile: `--profile core,healthcare`.
