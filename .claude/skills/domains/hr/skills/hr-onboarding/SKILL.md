---
name: hr-onboarding
description: |
  Employee onboarding doctrine covering pre-boarding paperwork and document
  collection, day-one orientation, first-30 / first-60 / first-90 plans,
  role and mission induction, team and culture integration, system and access
  provisioning under least-privilege discipline, benefits enrolment with
  window enforcement, compliance training completion tracking, and manager
  check-in cadence. Operates at the employment threshold where regulatory
  obligations intersect with retention risk: SSN, CPF, banking coordinates,
  dependent data, medical disclosures, and immigration documents are collected
  under minimum-necessary discipline with encryption-at-rest, in-transit
  controls, and jurisdiction-aware retention schedules. Use when designing or
  executing onboarding workflows, auditing onboarding records for compliance
  readiness, coaching managers on new-hire integration cadence, or handling
  any intake that touches regulated employment PII.
owner: Valentina Souza (HR Onboarding Specialist, domain persona)
tier: domain:hr
scope_tags: [hr-onboarding, employee-experience, role-induction, access-provisioning, benefits-enrolment, compliance-training]
inherits: [core/compliance-lgpd, core/pii-data-flow, core/consent-lifecycle, core/dpo-reporting]
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/specialized/hr-onboarding.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: hr
priority: 8
risk_class: low
stack: []
context_budget_tokens: 500
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/onboarding/**"
  - "**/employees/**"
  - "**/benefits/**"
  - "**/provisioning/**"
---

# HR Onboarding

Onboarding is the interval between offer acceptance and full productivity where
the employment contract is either confirmed as genuine or revealed as aspirational.
Every broken promise — missing access, absent manager, generic 30-60-90 plan,
compliance paperwork treated as a formality — compounds into turnover that
no retention programme can reverse.

This skill is the operating doctrine for designing, executing, and auditing
onboarding workflows from pre-boarding through day-ninety closeout. It does not
presuppose a single jurisdiction, headcount band, or work modality. All
compliance references include their multi-jurisdiction variants; PII handling
requirements apply regardless of company size or onboarding toolchain.

## Cardinal Rule

Onboarding is the single moment where the employer's promises meet evidence;
broken promises here cost more than every retention programme combined. No
onboarding artefact — offer letter, 30-60-90 plan, access provisioning ticket,
or manager guide — may assert a commitment the organisation cannot honour on the
stated date. If delivery is uncertain, the artefact must state that uncertainty
explicitly rather than default to the aspirational.

## Fail-Fast Rule

Stop and escalate to the HR lead before proceeding if any of the following is
true at intake:

- Personal data collection is requested before a documented lawful basis exists
  under the governing jurisdiction (LGPD Art. 7/11, GDPR Art. 6/9, CCPA, or
  equivalent employment-data statute).
- A hiring manager requests that onboarding documentation be backdated or that
  a compliance deadline be waived without documented executive authorisation.
- A new hire discloses a disability, religious observance need, or immigration
  status that triggers accommodation obligations — these require immediate
  escalation, not deferred queue handling.
- System access provisioning requests include permissions beyond the role's
  documented minimum at start date; least-privilege must be enforced before
  Day One, not after the fact.
- I-9 / Form E-Verify (US), CTPS / eSocial (BR), or right-to-work verification
  (UK) cannot be completed within the legal window; failure to timely complete
  creates employer liability that cannot be cured retroactively.

Fail-fast does not mean refuse onboarding. It means halt the current workflow,
document the condition with a timestamped record, and re-enter only after the
condition is resolved and the resolution is logged.

## When to Apply

Apply this skill when:

- Designing or auditing a pre-boarding checklist from offer acceptance to Day One.
- Building or reviewing a day-one orientation schedule covering compliance,
  access, and culture induction.
- Constructing or evaluating a 30-60-90 day plan for a new hire or manager.
- Conducting a compliance audit of I-9, CTPS/eSocial, or right-to-work
  documentation for a new hire cohort.
- Reviewing benefits enrolment communications for deadline accuracy and
  default-election completeness.
- Designing manager check-in cadences and structured agenda templates.
- Handling any intake that collects SSN, CPF, bank coordinates, dependent
  data, medical disclosures, or immigration documents.

## PII Handling

This skill is designated `pii_handling: required`. The following data classes
are collected across onboarding phases under the disciplines below.

### Intake Consent Gate (BLOCKING — runs before any employment PII is collected)

The applicable regulatory regime must be resolved before any employment record
is written. The intake consent gate is mandatory:

| Gate check | Required resolution before PII collection |
|---|---|
| Jurisdiction of employment | Identify governing statute: LGPD (BR), GDPR (EU/EEA), CCPA (CA), PIPEDA (CA-federal), or equivalent; note any multi-jurisdiction overlay |
| Lawful basis for employment-data processing | LGPD Art. 7 I (contract performance) or Art. 11 (sensitive data with explicit consent or legal obligation); GDPR Art. 6(1)(b) (contract) + Art. 9(2)(b) (employment law); document basis per class |
| Sensitive data classes present (SSN, CPF, health, biometric, immigration) | Art. 11 LGPD / Art. 9 GDPR — explicit consent or statutory employment exemption required; blanket consent insufficient |
| Cross-border data flow (multi-country hires or global HRIS) | Data transfer mechanism documented (SCCs, adequacy decision, BCRs); employee notified |
| Third-party processors (HRIS, payroll, benefits broker, background-check vendor) | Data processing agreements (DPAs) in place; processor registry updated |

A consent or lawful-basis record must itemise every data class and its basis;
blanket authorisation is not valid under LGPD Art. 11 or GDPR Art. 9.

### Employment Data Classes

| Class | Examples | Regulatory Scope |
|---|---|---|
| Government identity | SSN (US), CPF (BR), NIN (UK), SIN (CA), passport copy | LGPD Art. 11; GDPR Art. 9; employment law exemptions apply |
| Banking and payroll | Bank routing/account, direct-deposit authorisation, payroll tax elections (W-4, IR330) | LGPD Art. 7; GDPR Art. 6(1)(b) |
| Dependent data | Dependent names, SSN/CPF, beneficiary designations for benefits | LGPD Art. 11; GDPR Art. 9 if health-related |
| Medical and accommodation | Disability disclosures, accommodation requests, vaccination records (where legally mandated) | LGPD Art. 11; GDPR Art. 9; ADA (US); equality law (UK/EU) |
| Immigration and work authorisation | I-9 documents (US), CTPS (BR), Biometric Residence Permit (UK), work-permit copies | Jurisdiction-specific employment law; strict retention limits |
| Background check results | Criminal record checks, credit checks (where role-justified), reference verification | Proportionality required; retain only pass/fail outcome unless law mandates full record |
| Compensation and equity | Offer letter terms, salary, equity grant details | Confidentiality obligations; access restricted to HR + manager + finance |

### Minimum-Necessary Discipline by Onboarding Phase

| Phase | Data collected | Data NOT yet collected |
|---|---|---|
| Pre-boarding (offer → Day −7) | Emergency contact, work-authorisation eligibility confirmation, IT setup preferences | SSN/CPF, banking details, dependent data, medical disclosures |
| Day One compliance window | Government identity (I-9/CTPS/RTW), tax withholding elections, direct-deposit authorisation | Dependent data (collected at benefits enrolment); medical (collected only if accommodation disclosed) |
| Benefits enrolment window (Days 1–30) | Dependent names and eligibility data, beneficiary designations, HSA/FSA elections | Medical details beyond coverage elections (not required for plan selection) |
| Accommodation intake (triggered by disclosure) | Minimum functional limitation description; no diagnosis required; interactive process notes | Detailed medical records; collect only if employee voluntarily provides and role-justifies |

### Encryption and Security Controls

- Government identity documents (SSN, CPF, passport): encrypted at rest (AES-256
  minimum) and in transit (TLS 1.2+); access-controlled to HR personnel with
  documented need; no transmission via unencrypted email.
- Banking details: encrypted at rest; transmitted only via payroll system
  integration or secure portal; never stored in HRIS free-text fields.
- Background check results: stored in vendor system; only the pass/fail outcome
  synced to HRIS unless role-specific law mandates the full record.
- Medical and accommodation records: stored separately from the general personnel
  file per ADA, GDPR Art. 9, and LGPD Art. 11 requirements; access restricted to
  HR and the accommodation-decision chain.

### Retention Schedule

| Data class | Retention period | Deletion trigger |
|---|---|---|
| I-9 / work-authorisation documents (US) | 3 years from hire OR 1 year after termination, whichever is later | Automatic at schedule expiry; DOL audit readiness required throughout |
| CTPS / eSocial records (BR) | Duration of employment + 5 years post-termination | LGPD Art. 15 legitimate interest ends at schedule expiry |
| Government identity (non-I-9) | Duration of employment; delete within 30 days of termination | Employee data-erasure request under LGPD Art. 18 honoured within 15 days |
| Banking / payroll elections | Duration of employment + applicable tax audit window (5 years BR; 7 years US) | Superseded elections deleted on update after current tax year closes |
| Background check outcomes | Pass/fail: 1 year post-hire; full record per vendor contract unless law mandates longer | Vendor contract governs; DPA must reflect this schedule |
| Medical / accommodation records | Duration of employment + 10 years (litigation hold default); jurisdiction-specific floor applies | HR lead approval required before deletion |

Cross-reference: `core/compliance-lgpd` for LGPD lawful-basis selection, data
subject rights workflows (access, rectification, deletion, portability), and
RIPD/DPIA triggers. Cross-reference: `core/security-and-auth` for encryption
standard selection and access-control implementation.

## Pre-Boarding Discipline

Pre-boarding is the interval from signed offer letter to Day One. Failures here
arrive on Day One with the new hire.

### Document Collection

Collect only the minimum necessary for administrative setup — emergency contact,
work-authorisation eligibility confirmation, and IT provisioning preferences.
Government identity, banking details, and benefits data are NOT pre-boarding
collections; they are Day-One compliance or benefits-window collections.

### System Pre-Provisioning

Submit access requests at minimum ten business days before start date. The
provisioning manifest must enumerate each system, the role-level permission set,
and the approver. Requests must not include elevated permissions not documented
in the role definition; least-privilege is enforced at the provisioning stage,
not reviewed post-hire.

### Equipment Delivery

Confirm equipment delivery or on-site readiness by Day −2. Test all credentials
before the new hire is present. An employee who arrives to a non-functional
laptop on Day One absorbs an onboarding quality signal before any HR
representative speaks.

### Multi-Jurisdiction Work-Authorisation Preparation

| Jurisdiction | Instrument | Completion window |
|---|---|---|
| US | Form I-9 Section 1 (employee) before / on Day 1; Section 2 (employer) within 3 business days | Strict — non-completion triggers DOL liability |
| US (federal contractors) | E-Verify case within 3 business days of hire | Required by FAR 22.1802 |
| BR | CTPS registration and eSocial event S-2200 before or on Day 1 | CLT Art. 29; eSocial table 1.2 |
| UK | Right-to-work check (original documents or Home Office online service) before Day 1 | Illegal Working Act 2006; BRP or share code check for non-EEA nationals |

## Day-One and 30-60-90 Plans

Day One sets the quality floor for all subsequent onboarding interactions.
Rushing compliance steps, defaulting to slide presentations, or leaving the new
hire to navigate access independently signals disorganisation at the moment of
maximum impressionability.

### Day-One Sequence

1. Personal welcome from the hiring manager before any administrative activity.
2. I-9 / CTPS / right-to-work verification — completed before end of Day One.
3. Tax-withholding elections and direct-deposit authorisation — completed before
   end of Day One.
4. Policy acknowledgements (code of conduct, data-privacy notice, acceptable-use)
   — completed before end of Day One.
5. Access and credential verification — the new hire tests each required system
   before IT departs; a non-functional system is a Day-One blocker, not a
   post-onboarding ticket.
6. Team introduction — informal, no work agenda; manager attends.
7. Buddy introduction — separate from team introduction; buddy role is informal
   Q&A and cultural navigation, not workflow training.
8. Day-One close — HR check-in: first impressions, open questions, benefits
   enrolment window confirmed and understood.

### 30-60-90 Mutual-Success Criteria

The 30-60-90 plan must be co-built by the manager and the new hire before Day
Five; a plan delivered unilaterally by the manager is a performance document
masquerading as an onboarding plan. Each phase has a mutual-success criterion
agreed and written before the phase begins.

| Phase | Focus | Manager obligation | New hire obligation | Mutual-success criterion |
|---|---|---|---|---|
| Days 1–30 | Learn | Weekly 1:1 (min 30 min); clear written expectations; stakeholder introductions | Complete all compliance and benefits enrolment; shadow role workflows; build team map | "Both parties can state what success looks like in the role and agree the statement is accurate" |
| Days 31–60 | Contribute | Bi-weekly 1:1; first formal feedback given and received | Take ownership of one defined responsibility; identify one improvement opportunity | "New hire is contributing independently on at least one defined scope" |
| Days 61–90 | Accelerate | Bi-weekly 1:1; 90-day formal review; development goals set | Deliver measurable result; propose one initiative from fresh-perspective position | "New hire and manager co-sign the 90-day review and agree on the 6-month development path" |

HR check-ins are independent of manager 1:1s: end of week two, end of month one,
mid-point of day sixty, and a formal 90-day HR close with retention-risk
assessment and onboarding-experience survey.

## Role, Mission, Team, Culture Induction

Culture transmitted implicitly through behaviour is the only culture that
survives past the first-year cohort; slide decks are not culture induction.

### Role Expectations

Role expectations must be written before the new hire's start date and shared
no later than Day One. Expectations cover: scope of decisions the new hire
makes independently; scope that requires manager approval; success metrics for
the first 90 days; and who the new hire escalates to for what.

### Team Norms

Team norms must be made explicit, not discovered by infraction. The onboarding
record must include: meeting cadence and expected preparation; communication
channel conventions (async vs synchronous; response-time expectations by channel);
how decisions are made and documented; how disagreement is raised.

### Company Values and Decision-Making Norms

Values stated in marketing materials are not the same as the values applied when
decisions are costly. The onboarding conversation on values must include at least
one concrete historical example where a company decision favoured the stated value
at material cost; otherwise values induction is marketing, not culture.

## System and Access Provisioning

### Least-Privilege at Start

Every access request is provisioned at the minimum permission level required
for the new hire's Day-One responsibilities. Elevated permissions are not
pre-provisioned on the expectation the new hire will need them later; they are
provisioned just-in-time when the business need is documented.

### Just-in-Time Elevation

Elevated access follows a documented request → approval → grant → expiry cycle.
The provisioning record must include: requestor, approver, business justification,
permission level granted, and expiry date. Permanent elevation from the
just-in-time level requires a formal access-review event.

### Access Review Cadence

Access rights are reviewed at Day 30 (confirm provisioned set matches actual
role), Day 90 (audit for scope creep), and at role change. The review record
is retained for audit purposes.

### Offboarding-Ready Provisioning

Every access grant is tagged to the employee record in the provisioning system.
Offboarding triggers automatic deprovisioning of all grants; no manual checklist
is the single source of truth. The onboarding provisioning manifest doubles as
the offboarding deprovisioning manifest.

## Benefits Enrolment

Benefits enrolment windows are hard deadlines; missing the window in most
jurisdictions means waiting until open enrolment — potentially twelve months
without elected coverage.

### Window Discipline

The enrolment window (typically 30 days from start date) must be communicated
in the Day-One orientation, confirmed in the end-of-week-one HR check-in, and
visible as a countdown in any HRIS self-service portal the new hire uses. A new
hire who misses the window because the window was communicated once is an HR
process failure, not a new hire failure.

### Default Elections Audit

Where the HRIS assigns default elections (e.g., defaulting to the lowest plan
tier if no election is made), the default must be disclosed explicitly before
the window opens. The new hire must affirmatively acknowledge the default or
make an alternative election; silent default is not an informed election.

### Dependent Verification

Dependent data is collected only during the benefits-enrolment phase and only
for the dependents being enrolled. Dependent eligibility documentation (birth
certificate, marriage certificate) is collected, verified, and retained per the
retention schedule above; copies are not retained beyond the verification event
without explicit legal basis.

### Multi-Jurisdiction Benefit Coverage

| Jurisdiction | Retirement | Medical | Parental leave |
|---|---|---|---|
| BR | INSS mandatory contribution; private PGBL/VGBL optional; eSocial S-1020 plan registration | Vale-Saúde / Plano de Saúde — CLT Art. 458 if contractually committed; ANVISA-registered plan required | CLT: 120 days statutory; Programa Empresa Cidadã extends to 180 days if enrolled |
| US | 401(k) — IRS contribution limits; ERISA fiduciary duty; vesting schedule disclosure required | ACA compliance — minimum essential coverage, affordability threshold; COBRA notice within 14 days of qualifying event | FMLA: 12 weeks unpaid (50-employee threshold); state law may exceed |
| UK | Auto-enrolment pension (NEST or qualifying scheme) — minimum contribution rates set by Pensions Act 2008 | NHS primary care; employer private medical supplement common; notify new hire of any employer contribution | Statutory Maternity/Paternity/Shared Parental Pay — eligibility and rate schedule disclosed at offer stage |

## Compliance Training

Compliance training completion is an audit event, not a welfare event. Each
training completion must generate a dated, employee-attributed record stored
in the HRIS against the employee record.

### Required Training Matrix

| Training | Target population | Completion window | Evidence record |
|---|---|---|---|
| Anti-harassment and discrimination | All employees | Day 30 | Completion certificate + date in HRIS |
| Data privacy and information security | All employees | Day 30 | Completion certificate; note training version and applicable law |
| Code of conduct acknowledgement | All employees | Day One | Signed acknowledgement in HRIS |
| Safety training (OSHA US / NR BR / Health and Safety at Work UK) | All employees; role-specific modules for physical environments | Day 30 | Completion certificate; OSHA injury log entry for role-specific training |
| Industry-specific compliance | Role-determined (HIPAA, PCI-DSS, SOC 2, CVM BR, FCA UK, etc.) | As defined by role profile, not later than Day 60 | Certification or vendor-issued completion record |
| Manager training (new people managers only) | All new managers | Day 60 | HR-facilitated session record; not self-paced only |

### Evidence Per Training Event

Each training event record must capture: employee ID, training title, version
or curriculum revision, completion date, pass/fail outcome, and the expiry date
if the training has a recertification cycle. Records must be retrievable within
two business days for audit.

## Manager Check-In Cadence

The manager relationship is the single highest-leverage variable in 90-day
retention. The onboarding protocol does not treat manager check-ins as optional.

### Cadence Structure

- Week one: Daily informal check-in (5–10 min) — surface friction before it
  compounds.
- Weeks two through four: Weekly 1:1 (30 min minimum) — structured agenda:
  what is going well, what is unclear, what blockers exist, one specific action
  the manager will take before next 1:1.
- Months two through three: Bi-weekly 1:1 (30 min minimum) — same agenda
  structure; add feedback given and feedback requested.
- Day 90: Formal review — co-signed written summary covering 30-60-90 outcomes,
  development goals, and mutual-success retrospective.

### Written Summary Requirement

Every 1:1 that is part of the onboarding cadence must have a written summary.
The summary is owned by the manager, shared with the new hire within 24 hours,
and retained in the HRIS onboarding record. Verbal-only check-ins are not
compliant with this cadence; if a commitment is not written, it did not happen
for onboarding-record purposes.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Paperwork-only Day One | Signals the organisation treats compliance as the purpose of onboarding rather than the floor; new hire's first memory is forms |
| Access provisioned after start date | New hire cannot do their job; first-week productivity is zero; onboarding quality signal is irreversible |
| Generic 30-60-90 plan delivered unilaterally | New hire has no ownership stake in the plan; manager has no accountability to co-signed criteria |
| Surface-only culture pitch (values without examples) | Values transmitted without costly historical examples are perceived as marketing; new hires calibrate to observed behaviour, not stated values |
| No structured manager check-in cadence | New hire concerns surface at 90-day review or at resignation; neither point allows remediation |
| Benefits window communicated once | Single communication is insufficient for a decision with 12-month consequence; results in uninsured employees and HR liability |
| PII collected in bulk at intake regardless of phase | Over-collection relative to current phase is an LGPD / GDPR violation; minimum-necessary discipline applies per phase |
| Verbal-only 1:1 summaries | Commitments without written record disappear; disputes at 90-day review have no audit trail |

## Cross-References

- `core/compliance-lgpd` — LGPD lawful-basis selection (Art. 7 / Art. 11),
  data subject rights (Art. 18 access, rectification, deletion, portability),
  RIPD/DPIA triggers for high-risk onboarding processing (biometric access,
  health data, immigration data).
- `domains/hr/skills/recruitment-specialist` — handoff protocol from offer
  acceptance to onboarding; candidate-PII transfer between ATS and HRIS must
  follow minimum-necessary and DPA disciplines established at recruitment stage.
- `core/security-and-auth` — encryption standard selection (AES-256 at rest,
  TLS 1.2+ in transit), access-control implementation for HRIS and provisioning
  systems, just-in-time elevation audit trail requirements.

## ADR Anchors

- ADR-058 (Brainstorm gate + two-pass adversarial review): onboarding plan
  artefacts that assert compliance claims (I-9 timelines, LGPD lawful bases,
  benefits window deadlines) must pass a two-pass verification against the
  governing statute before the claim is published to the new hire. A reviewers'
  pass that accepts a compliance claim on implementer self-report without
  independent statutory verification is non-compliant with ADR-058 §two-pass.
