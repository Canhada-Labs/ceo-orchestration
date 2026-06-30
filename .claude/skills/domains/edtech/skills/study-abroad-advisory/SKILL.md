---
name: study-abroad-advisory
description: |
  End-to-end advisory doctrine for international study pathways covering destination
  selection, profile assessment, school-list construction, essay coaching, application
  timeline management, standardized test strategy, visa preparation, and post-arrival
  adaptation. Multi-jurisdiction expertise spanning the US, UK, Canada, Australia,
  Continental Europe, Hong Kong, and Singapore at undergraduate, master's, and PhD
  levels. Handles PII-touching workflows — student transcripts, family financials,
  passport and visa data, and recommender contact details — under minimum-necessary
  discipline with LGPD/FERPA/GDPR awareness. Use when performing destination-country
  comparison, school-list tiering, essay structure review, visa document checklist,
  or any student profile intake that touches regulated personal data.
owner: Alexandra Ferreira (Study Abroad Advisor, domain persona)
secondary_owner: David Okonkwo (Visa & Compliance Specialist, domain persona)
tier: domain:edtech
scope_tags: [study-abroad, application-strategy, essay-coaching, visa-preparation, profile-assessment, multi-jurisdiction]
inherits: core/compliance-lgpd
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/specialized/study-abroad-advisor.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: edtech
priority: 8
risk_class: low
stack: []
context_budget_tokens: 600
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
  - "**/applications/**"
  - "**/admissions/**"
  - "**/visa/**"
  - "**/advising/**"
---

# Study Abroad Advisory

International study preparation spans two to three years of consequential decisions —
country selection, program fit, profile building, essay development, and visa compliance —
where a single structural error (wrong school-list tier ratio, missed visa timing, or
ghostwritten essay) compounds into outcomes that cannot be reversed after submission.
This skill is the operating doctrine for advising students and families through that
arc with accuracy, transparency, and no anxiety selling.

The skill is source-country agnostic. It does not presuppose any particular origin
country or educational system (gaokao, A-levels, IB, Abitur, ENEM, etc.) for the
applicant. Destination-country expertise is detailed and multi-jurisdiction. Profile
assessment criteria adapt to whatever credentialing system the student comes from.

## Cardinal Rule

Anxiety selling, ghostwritten essays, fabricated activities, or guaranteed-admission
claims are professional malpractice and grounds for immediate advisor dismissal — no
exceptions. Every recommendation issued under this skill must be reproducible from
publicly verifiable admission data, and every uncertainty must be disclosed as
uncertainty rather than masked as expertise.

## Fail-Fast Rule

Stop and escalate to the owning advisor before proceeding if any of the following
conditions are true at intake:

- Student requests that experiences be invented or embellished for application materials.
- Student or family presents documents that appear inconsistent (e.g., transcript dates
  that do not align with enrollment records, financial statements from institutions that
  cannot be verified).
- Any party requests an opinion on whether misrepresentation "will be detected."
- Visa counsel requests conflict with official embassy/consulate guidance in ways that
  cannot be reconciled through published policy.
- PII collection exceeds the minimum necessary for the current advisory phase (see
  PII Handling).

Fail-fast does not mean refuse all assistance — it means halt the current workflow,
document the condition, and re-enter only after the condition is resolved.

## When to Apply

Apply this skill when:

- Performing initial destination-country comparison for a student or family.
- Constructing or reviewing a tiered school list (reach/target/safety).
- Reviewing or coaching a personal statement, statement of purpose, Why-School essay,
  diversity essay, research proposal, or UCAS personal statement.
- Building or auditing a backward-planned application timeline.
- Advising on standardized test strategy (test selection, score floors, retake logic).
- Preparing or reviewing visa documentation checklists (F-1, Tier-4/Student Route,
  study permit, Subclass 500, or equivalent).
- Advising on post-arrival logistics (housing, banking, healthcare, academic culture).
- Handling any student data intake that involves transcripts, financial data, passport
  details, or health disclosures.

## PII Handling

This skill is designated `pii_handling: required`. The following data classes are
routinely collected during advisory workflows and must be handled under the disciplines
below.

### Intake Consent Gate (BLOCKING — runs before any PII is collected)

Per `domains/edtech/skills/student-data-privacy` (§Cardinal Rule), the
applicant's regulatory regime MUST be resolved before any student record
is written. The intake consent gate is mandatory:

| Gate check | Required resolution before PII collection |
|---|---|
| Applicant age vs source-country majority age | If minor, identify guardian(s); collect guardian-consent record covering each data class below |
| Applicant age vs COPPA (under-13, US-served institutions) | Verifiable Parental Consent (VPC) workflow before collection |
| Eligible-student transition under FERPA (turning 18 OR enrolling in post-secondary, whichever first) | Update consent record from guardian to eligible-student; archive prior guardian record per FERPA Sec. 99.5 |
| Data Sharing Agreement (DSA) status with destination-country institution | Confirm DSA exists or note its absence in advisory record before transmitting any record to that institution |
| LGPD Art. 14 (BR minors): legal basis selection (parental consent + best-interest assessment) | Document in intake per `domains/edtech/skills/student-data-privacy` §LGPD-educational — basis "usually legítimo interesse + parental consent for under-12 + RIPD when high-risk"; standalone legítimo interesse without parental consent is not lawful for under-12 |
| GDPR Art. 8 (digital consent age, member-state floor 13-16) | Verify member-state-specific digital consent floor before processing for EU-resident applicants |

A guardian-consent record MUST itemise every data class the guardian is
authorising; blanket consent is not lawful basis under LGPD or GDPR.
The advisor's intake form is the source of truth; subsequent collection
without an itemised consent entry is a governance violation.

### Data Classes

| Class | Examples | Regulatory Scope |
|---|---|---|
| Academic records | Transcripts, grade reports, class rank, research publications | FERPA (US institutions), LGPD, GDPR |
| Standardized test scores | GRE, GMAT, SAT, ACT, TOEFL, IELTS raw and superscore records | LGPD, GDPR |
| Family financial data | Bank statements, tax returns, sponsor letters, scholarship income | LGPD, GDPR; destination-country visa requirements |
| Identity documents | Passport copies, national ID, birth certificate | LGPD Art. 11; GDPR Art. 9; FERPA NA |
| Visa and immigration history | Prior visa applications, refusals, I-20s, CAS numbers | Destination-country immigration law |
| Recommender contact details | Name, institution, email, relationship to student | LGPD, GDPR |
| Medical/health disclosures | Vaccination records, disability disclosures when host country requires | LGPD Art. 11; GDPR Art. 9 (special category) |

### Minimum-Necessary Discipline

Collect only the data class required for the advisory phase currently active. Do not
request family financial data during destination-country comparison; do not retain
identity documents beyond visa-preparation phase. Each collection event must have an
identifiable advisory purpose.

### Retention and Deletion

- Academic records and test scores: retain for the duration of the active application
  cycle plus 12 months post-enrollment confirmation or cycle abandonment.
- Financial and identity documents: retain for visa-preparation phase only; delete
  within 30 days of visa issuance or cycle closure.
- Recommender contact details: retain for duration of active application cycle; delete
  on request at any time.
- On student request, all retained PII must be deleted within 15 days (LGPD Art. 18;
  GDPR Art. 17 right to erasure). Deletion confirmation must be logged.

### Cross-Border Data Flow

Student data routinely flows from the source country to destination-country institutions.
Advisors must disclose to students that application submissions transmit personal data
to foreign institutions operating under different regulatory frameworks (FERPA in the
US; the UK Data Protection Act / UK GDPR; Australia's Privacy Act; Singapore's PDPA).
Students must be informed that once data is submitted to a foreign institution, the
advisor cannot guarantee the data handling practices of that institution.

Cross-reference: `core/compliance-lgpd` for LGPD lawful-basis selection and data
subject rights workflows. Cross-reference: `domains/edtech/skills/student-data-privacy`
for institutional data retention contracts.

## Destination Country System Profiles

The table below covers the primary destination-country application systems. Program
durations are typical; variants exist by institution. Timeline is measured backward
from the start-of-program semester.

| Country | Degree Levels | Application Portal / System | Typical Timeline | Notable Constraints |
|---|---|---|---|---|
| United States | UG / Master's / PhD | CommonApp (UG), institution-direct portals (grad) | 12-18 months out | Holistic review; test-optional trend for UG; PhD funding competitive; STEM OPT extension eligibility relevant for work-intent students |
| United Kingdom | UG / Master's / PhD | UCAS (UG, 5-school cap); institution-direct (grad) | 12-15 months out (UG); 9-12 months (grad) | UCAS personal statement is one statement for all five schools; 1-year master's is common; Student Route visa replaces Tier 4; post-study work (Graduate Route) 2 years UG/master's, 3 years PhD |
| Canada | UG / Master's / PhD | Institution-direct (no national UG clearinghouse) | 10-14 months out | Province-specific post-graduation work permit (PGWP) duration; Quebec has distinct language and immigration requirements; study permit separate from visa for some nationalities |
| Australia | UG / Master's / PhD | Institution-direct; some states use QTAC/UAC/SATAC for UG | 9-12 months out | Subclass 500 student visa; genuine temporary entrant (GTE) requirement adds non-immigrant intent scrutiny; health and character requirements; Genuine Student requirement (2023 reform) |
| Continental Europe | UG / Master's / PhD | Varies by country (Uni-Assist DE; Campus France FR; NUFFIC NL) | 10-14 months out | Germany/Netherlands/Nordic countries: largely tuition-free or low-tuition public sector; language of instruction varies (many English-track master's); Schengen student visa; APS certificate required for some source countries for Germany |
| Hong Kong | UG / Master's / PhD | JUPAS (UG local track); institution-direct (non-local / grad) | 9-12 months out | 1-year master's common; IANG visa allows 1-year stay-and-work post-graduation; proximity to mainland China is a factor for some students; highly competitive for full-funding PhD |
| Singapore | Master's / PhD (primary for international) | Institution-direct (NUS, NTU, SMU, SUTD, SUSS) | 9-12 months out | NUS/NTU consistently top-ranked in Asia; scholarship competition significant (NUS Research Scholarship, A*STAR); Employment Pass pathway attractive post-graduation; limited undergraduate international intake |

Multi-country combinations require timeline coordination. Common working combinations:
US + UK (essay overlap limited — UCAS personal statement diverges sharply from SOP
style); US + HK + Singapore (rolling admission in HK/SG allows earlier decisions);
UK + Australia (similar 1-year master's structure; visa timelines diverge).

## Profile Assessment Discipline

Profile assessment must separate hard credentials (objective, verifiable) from soft
credentials (contextual, advisor-interpreted) and must benchmark each against the
published or empirically observed admission data of target programs — not against
generic rankings.

### Hard Credentials

- **GPA / academic results:** Convert to 4.0 scale equivalent when comparing across
  systems. Note the institutional context (research university vs. teaching-focused
  college; grading compression at elite institutions). Major GPA and final-year GPA
  are often more indicative than cumulative for graduate admissions.
- **Standardized tests:** Report scores with percentile for the relevant applicant
  pool, not raw score alone. Note superscore eligibility by institution.
- **Research outputs:** Peer-reviewed publications carry weight at PhD level. Conference
  proceedings, technical reports, and preprints carry weight only when venue quality
  is verified. Predatory journal publications actively harm applications and must be
  disclosed rather than featured.
- **Language proficiency:** TOEFL/IELTS overall band plus component sub-scores (writing
  and speaking are the most frequently sub-scored by programs). Duolingo acceptance is
  expanding but not universal — verify per institution.

### Soft Credentials

- **Internships and professional experience:** Relevance to target program, not total
  months. A six-month research internship at a relevant lab outweighs two years of
  unrelated commercial work for PhD applications.
- **Extracurricular and project work:** Depth over breadth. One substantive independent
  project with measurable outcome is more readable than a list of club memberships.
- **Recommendations:** Assess the recommender's knowledge of the student's work, not
  only the recommender's prestige. A specific, evidence-backed letter from a direct
  supervisor outperforms a generic letter from a famous name.
- **Cross-disciplinary profile:** Identify which programs explicitly welcome career
  switchers; identify prerequisite bridge courses required; assess gap risk honestly.

### Benchmarking Discipline

All profile benchmarks must cite a data source and vintage. Admission statistics from
three or more years prior are advisory only. Express probability as a range (e.g.,
"20-35% based on reported median GPA for this program") — never as a point estimate.
Clearly distinguish confirmed program data from advisor judgment.

## School-List Construction

A school list that skews toward reach schools is not ambitious — it is a risk management
failure. The three-tier structure below is the required framework.

### Three-Tier Framework

| Tier | Definition | Admission Probability | Recommended Count |
|---|---|---|---|
| Reach | Program where the student's hard credentials fall at or below the 25th percentile of reported admits, or where the program is highly selective without published data | 20-40% | 2-4 schools |
| Target | Program where the student's profile is within the reported median range and soft credentials are competitive | 40-70% | 4-6 schools |
| Safety | Program where the student's hard credentials exceed the reported 75th percentile, and admission is reasonably predictable | 70-90% | 2-3 schools |

Total list size: 8-13 programs for most students. Lists exceeding 15 programs
dilute essay quality without proportionate risk reduction.

### Over-Reach Failure Mode

A list composed of 80%+ reach schools is the single most common structural error in
study abroad advising. It produces an outcome distribution weighted toward admission
at no school. When a student presents a reach-heavy list, the advisor must:

1. Restate the probability math explicitly.
2. Identify the gap between the student's profile and the target programs' medians.
3. Propose concrete profile improvements that would reduce the gap before submission,
   or propose safer alternatives.

Safety-school aversion ("I only want to apply to top schools") is a stated preference
that advisors must acknowledge and then honestly reframe — it is not a basis for
removing the safety tier from the list.

### Single-Country Lock-In

Applying exclusively to one destination country concentrates visa-refusal risk, policy
change risk, and admission-cycle risk. Students should be informed of the
diversification rationale before committing to a single-country strategy.

## Application Timeline Backwards Planning

All timelines are expressed as months before program start (typically August/September
for fall-start programs; January/February for spring/winter-start).

### 18-14 Months Out: Foundation

- Profile assessment completed; preliminary country and degree-level decisions made.
- Standardized test plan established with target score dates.
- Profile enhancement priorities identified (research opportunities, internship gaps,
  publication targets, bridge coursework).
- Preliminary school list drafted (pre-essays version).

### 13-10 Months Out: Testing and Enhancement

- Language test completed with scores that meet all target-program thresholds.
- Academic standardized test (GRE/GMAT/SAT/ACT) completed or in final preparation.
- Summer research, internship, or project activity completed or ongoing.
- Recommenders identified and approached; talking points delivered to each recommender.

### 9-7 Months Out: Essay Development

- School list finalized after essay-material inventory.
- Core narrative arc established; first draft of primary statement (PS/SOP) completed.
- Why-School and supplemental essays drafted for early-deadline programs.
- UK UCAS personal statement drafted (single statement for all five schools).
- Research proposal drafted for PhD and UK master's programs that require it.

### 6-4 Months Out: First Submission Wave

- US early-action and early-decision applications submitted.
- UK UCAS main batch submitted (target: October 15 for Oxford/Cambridge and most
  Medicine/Veterinary/Dentistry; verify the current UCAS Equal Consideration
  deadline at intake — the date has shifted from late January in recent cycles
  and is updated annually on `ucas.com`).
- HK and Singapore main batch submitted (rolling admissions — earlier is better).
- All recommendation letters confirmed submitted.
- Interview preparation commenced for programs with interview rounds.

### 3-2 Months Out: Second Submission Wave

- US regular-decision and Round 2 graduate applications submitted.
- Canada institution-direct deadlines met.
- Australia flexible-semester applications submitted.
- Interview practice continued; behavioral frameworks rehearsed.

### 1 Month Out to Decision: Offer Management

- All offers compiled into comparison matrix (see Anti-patterns for ranking-obsession
  failure mode).
- Waitlist strategy activated for borderline programs.
- Enrollment deposit confirmed; financial aid and scholarship appeals filed.
- Visa preparation initiated immediately on enrollment confirmation — do not wait for
  all decisions before beginning visa documents.

## Essay Coaching Discipline

Essay coaching is the structured facilitation of the student's own narrative. It is
not authorship, not dictation, and not stylistic takeover. The distinction between
coaching and ghostwriting must be operationally clear.

### Coaching vs. Ghostwriting — The Line

**Coaching (permitted):** Structural feedback, narrative arc consultation, identification
of logical gaps, language-level editing for clarity and grammar, question-by-question
strategy guidance, brainstorming sessions where the student generates content and the
advisor shapes structure.

**Ghostwriting (prohibited):** Writing sentences or paragraphs that the student will
submit as their own voice; sourcing experiences or framing from advisor knowledge
rather than student disclosure; making strategic claims about the student's motivations
that the student has not themselves expressed.

If a student submits an essay that reads as advisor-authored, the advisor must flag it
and return it for student rewrite — submitting it regardless because the deadline
is approaching is not a permissible exception.

### Essay Types and Required Structural Elements

**Personal Statement / Statement of Purpose (PS/SOP)**
- Core narrative arc: who this person is, where they are going, why this program.
- Not a chronological resume in prose form — transitions must carry analytical weight.
- Opening must not be a generic statement of passion. It must place the reader inside
  a specific experience, problem, or turning point.
- Program-specific closing: demonstrate genuine knowledge of the program (faculty,
  curriculum, research group) — not surface-level website language.
- Typical length: 500-1,000 words (US graduate); 1-2 pages (varies by program).

**Why-School Essay**
- Requires demonstrated deep engagement with the program — specific courses, labs,
  faculty research, or program structures that are not universally available.
- Generic observations about ranking, location, or general reputation are disqualifying
  signals — remove them.

**Diversity Essay**
- Authentic experience and perspective; not fabricated persona.
- The essay must be grounded in experiences the student can speak to in an interview
  without inconsistency.

**Research Proposal (PhD / UK Master's)**
- Four required components: problem statement, literature review (brief), proposed
  methodology, feasibility and timeline.
- Must not overstate the student's current knowledge; feasibility honesty is valued
  by admissions committees.
- Advisor fit section: name the faculty member and explain the fit based on their
  published work — not their institutional rank.

**UCAS Personal Statement (UK Undergraduate)**
- Hard limit: 4,000 characters (including spaces).
- Academic motivation must occupy at least 70-80% of the statement.
- Extracurriculars should be framed through their contribution to academic development,
  not standalone.
- One statement is submitted for all five UCAS choices — it cannot be school-specific.

### Essay Diagnostic Framework

```markdown
## Core Narrative Check
- Is there a clear throughline identifiable in one sentence?
- Does the opening avoid "I have always been passionate about..."?
- Is the logical chain from experience to goal coherent, not just chronological?
- Is the "why this program" section specific and non-generic?

## Content Quality Check
- Are experiences described with concrete evidence (data, outcomes, context)?
- Does the essay avoid resume-style listing of activities?
- Does it demonstrate growth or insight, not just completion of tasks?
- Is the ending specific and forward-facing, not generically aspirational?

## Technical Quality Check
- Does length meet program requirements?
- Is grammar natural (non-native voice is acceptable; grammatical errors are not)?
- Are paragraph transitions functional, not decorative?
- Is each school-specific essay actually customized to that school?

## Integrity Check
- Could the student speak fluently to every claim in this essay in a live interview?
- Are all activities and experiences verifiable through the application record?
- Does the essay read as the student's voice, not the advisor's?
```

## Standardized Test Strategy

### Language Proficiency

| Test | Common Acceptance | Minimum Score Floors (Typical Tier-1 Program) | Notes |
|---|---|---|---|
| TOEFL iBT | Universally accepted | Overall 100; Speaking 22; Writing 22 | Section sub-scores matter; some programs require 25+ in each section |
| IELTS Academic | Universally accepted | Overall 7.0; no band below 6.5 | UK programs commonly require 7.0 overall; some 7.5 |
| Duolingo | Selective acceptance (expanding) | 120+ overall | Verify acceptance per institution before relying on Duolingo as primary score |

Score validity: TOEFL and IELTS scores are valid for two years from test date. Plan
test dates so scores are valid at the submission deadline of the latest-deadline
program on the school list.

Retake economics: marginal improvement on the third or subsequent attempt produces
diminishing returns. If a student has sat a test twice with minimal improvement,
redirect effort to other application components rather than a third test cycle.

### Academic Standardized Tests

| Test | Programs | Score Floors (Competitive Range) | Superscore Mechanics |
|---|---|---|---|
| GRE General | Most US master's and PhD programs (check waiver policies) | Verbal 160+; Quant 165+ for STEM; AW 4.0+ | Section-level superscore accepted by some programs; confirm per institution |
| GMAT | MBA and some finance master's programs | 700+ for top-20 MBA; 650+ for target-tier | Total score superscored across attempts by GMAC; confirm program acceptance |
| SAT | US undergraduate (test-optional trend ongoing) | 1450+ for top-40; 1350+ for target-tier | Section-level superscore widely accepted; check per institution |
| ACT | US undergraduate (test-optional trend ongoing) | 33+ for top-40; 30+ for target-tier | Composite superscore available; less universally accepted than SAT superscore |

Test-optional policies: verify current status per institution per cycle — policies
introduced during 2020-2022 are being revisited. Submitting a strong score under
a test-optional policy is always advantageous; submitting a weak score is not.

GRE waiver trend: many US programs introduced waivers during 2020-2023. Confirm
whether the waiver is still active and whether submitting a score (even optional)
differentiates the application positively for the current cycle.

## Visa Preparation Guardrails

Visa preparation errors after admission are one of the few ways a successful admission
can be undone. Begin visa document collection simultaneously with enrollment deposit,
not after all applications are decided.

### Primary Student Visa Types

| Destination | Visa Type | Key Document Requirements | Non-Immigrant Intent? | Common Rejection Patterns |
|---|---|---|---|---|
| United States | F-1 (academic); M-1 (vocational) | I-20 from SEVIS; financial documentation (1 year of tuition + living costs); SEVIS fee payment; DS-160 | Yes — must demonstrate ties to home country and intent to depart after studies | Insufficient financial documentation; prior visa overstays; administrative processing for certain STEM fields/source nationalities |
| United Kingdom | Student Route (replaced Tier 4) | CAS from institution; financial requirement (tuition + monthly maintenance × 9 months — verify current GOV.UK rates at intake; rates revised periodically); tuberculosis test for some nationalities | No genuine-intent test (replaced by continuous residency compliance) | Financial documents not meeting 28-consecutive-day bank statement requirement; English language not meeting UKVI-approved test requirement |
| Canada | Study Permit | Letter of Acceptance; proof of financial support (tuition + first-year living-cost minimum + additional dependent amount where applicable + return travel — verify current Canada.ca thresholds at intake; minimum was raised effective 2024 and updated again 2025); biometrics | No formal non-immigrant intent test, but low return-likelihood evidence cited in refusals | Insufficient financial documentation; ties to home country not demonstrated; purpose of study not credible |
| Australia | Subclass 500 | Confirmation of Enrolment (CoE); Genuine Student requirement assessment; OSHC (overseas student health cover); financial capacity (annual living-cost threshold + tuition + travel — verify current Department of Home Affairs amount at intake; threshold revised 2024 onward); character and health requirements | Genuine Student (GS) statement requirement assesses intent and study plan | GS statement failing to demonstrate genuine study intent; health or character clearance delays; financial documents not meeting AUD threshold |
| Continental Europe (Schengen) | National student visa (varies by country) | Varies by country; typically: enrollment letter, housing proof, financial means, health insurance | Non-immigrant intent assessed variably by country | Incomplete documentation; proof of accommodation not confirmed; health insurance not meeting host-country minimum |

### Financial Documentation Discipline

Financial documentation is the most common visa rejection cause. Apply these rules:

- Bank statements must reflect the required balance maintained continuously for a
  defined period (UK: 28 consecutive days ending no earlier than 31 days before
  application; US: no defined period but officer discretion applies — use 60+ days).
- Funds must be liquid and accessible — investment accounts, retirement accounts,
  or pledged assets typically do not qualify.
- Sponsor letters must be from an identifiable individual with a demonstrable
  relationship to the student; unexplained large deposits shortly before the statement
  period are a red flag for officers.
- Where program costs increase year over year, financial documentation must cover
  the stated academic year's costs, not the prior year's costs.

### Interview Preparation (US F-1)

The DS-160 and visa interview are the primary gate for F-1 issuance. Preparation:

- Consulate officers assess: genuine student intent, ability to fund study, intention
  to depart after program completion, and program credibility.
- The student must be able to articulate the program, why they chose it, and their
  post-study plan clearly and consistently.
- STEM fields subject to administrative processing (INA 221(g) security clearance):
  advise students that processing delays of 60-180+ days are possible. Do not book
  non-refundable travel before visa issuance.

## Post-Arrival Adaptation Plan

Pre-departure planning for the post-arrival phase reduces the administrative chaos
that distracts from academic engagement in the first weeks.

### Pre-Departure Checklist

```markdown
## Housing
- [ ] Confirm accommodation booking (on-campus or verified off-campus lease)
- [ ] Research local deposit and lease-signing requirements
- [ ] Identify temporary accommodation if permanent housing is not confirmed

## Banking
- [ ] Research whether source-country bank cards work in destination country
- [ ] Identify which local banks accept international student accounts without
      local credit history (Wise, Revolut, or destination-country student-specific
      accounts are common transitional tools)
- [ ] Confirm arrival timing against bank branch hours for account opening

## Healthcare
- [ ] Confirm health insurance enrollment status (F-1 students: institution
      health plan enrollment deadlines; UK: NHS surcharge paid via visa application;
      Australia: OSHC activation on arrival)
- [ ] Obtain 90-day supply of any prescription medications with verified customs
      declarations for controlled substances

## Academic Registration
- [ ] Confirm course registration deadlines; many programs require advisor sign-off
      before first-week registration
- [ ] Identify international student orientation attendance requirements
      (some are mandatory for visa compliance)

## Visa / Status Compliance
- [ ] Record SEVIS registration deadline (US: within 30 days of program start)
- [ ] Register with local immigration authority if required (verify
      destination-country obligations at intake — requirements change;
      e.g. UK police registration was abolished in August 2022 but
      some destinations retain analogous registration regimes)
- [ ] Note on-campus work authorization limits (F-1: 20 hours/week during term)
```

### Academic Culture Shift

Different destination countries operate under markedly different academic participation
norms. Prepare students for:

- **US:** Participation in seminar-style classes is graded; faculty office hours
  are expected to be used; grade inflation varies widely by institution.
- **UK:** Tutorial and supervision models require independent preparatory reading;
  exams carry high weight relative to coursework in many programs.
- **Australia:** Assessment is often continuous; group project norms involve strong
  peer accountability.
- **Singapore / HK:** Highly competitive student cohorts; grade curves are common;
  faculty accessibility varies significantly by department.

Advisors should explicitly set expectations about academic culture differences
before departure, not after the student's first graded assessment.

## Anti-patterns

| Anti-pattern | Description | Correct Practice |
|---|---|---|
| Anxiety selling | Framing risk in worst-case terms to push the student toward services, more applications, or premium tiers | State probability ranges factually; allow students to make informed decisions at their own risk tolerance |
| Ghostwritten essays | Writing application text that the student submits as their own | Coach structure and narrative; the student writes; the advisor edits |
| Fabricated or exaggerated activities | Adding research experience, leadership roles, or publications that did not occur | Profile reflects only verifiable experience; fabrication is grounds for admission rescission |
| Ranking obsession | Building school lists around a single ranking system without program-fit analysis | Multi-dimensional comparison: program fit, funding, career outcomes, visa pathway, cost, location |
| Single-country lock-in | Submitting exclusively to one destination country | Advise on diversification rationale; document student's informed choice if they decline |
| Outcome guarantees | "Guaranteed admission" or "95% success rate" claims | Express probability ranges with source citations; no admission outcome is guaranteeable |
| Stale data citation | Using admission statistics from 3+ years prior as current benchmarks | Cite vintage of all data; flag when current data is unavailable |
| Overfitting to source-country norms | Assuming destination-country institutions value the same signals as source-country systems | Calibrate recommendation framing to destination-country admission committee expectations |

## Cross-References

- `core/compliance-lgpd` — LGPD lawful-basis selection, data subject rights (deletion,
  portability, correction), data processing agreements, and cross-border transfer
  obligations. Required reading before any student data intake.
- `domains/edtech/skills/student-data-privacy` — Institutional data retention contracts,
  FERPA third-party disclosure rules, parental rights vs. student rights at majority,
  and COPPA applicability for under-13 platforms.
- `domains/edtech/skills/learning-analytics` — Behavioral and engagement data analytics
  pipelines; relevant when platforms generate predictive admission-likelihood scores
  from student interaction data (scope and consent boundaries apply).

## ADR Anchors

- **ADR-058** — Two-pass review for application packages: all application materials
  (school list + primary essay + at least one supplemental) must receive an independent
  second review before submission. A single-advisor single-pass workflow is insufficient
  for consequential, non-reversible submissions.
