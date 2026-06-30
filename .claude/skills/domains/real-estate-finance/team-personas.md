# Team Personas — Real-Estate Finance Squad

> **Post-PLAN-080 Phase 0a (ADR-111):** Skills under
> `.claude/skills/domains/real-estate-finance/skills/` inherit the
> 4-skill PII core set: `core/compliance-lgpd`, `core/pii-data-flow`,
> `core/consent-lifecycle`, `core/dpo-reporting`. Each SKILL.md declares
> `inherits: [core/compliance-lgpd, core/pii-data-flow, core/consent-lifecycle, core/dpo-reporting]`
> and `pii_handling: required`. This file supersedes the Phase 0a
> placeholder at `.claude/plans/PLAN-080/staging/phase-0a/team-personas-placeholders/real-estate-finance-team-personas.md`.

> Reference personas for real estate transactions and mortgage finance —
> buyer/seller representation, loan origination, title and escrow,
> and regulatory compliance. Products handle client PII, financial data,
> property records, and regulated financial transactions under RESPA,
> TILA, HMDA, and applicable state law.
> **Fictional composites** — no real individual is referenced.
> Mantras are opinionated by design.

## Squad vetoes

| Persona | VETO scope |
|---|---|
| **Adriana Ferreira** (Compliance Reviewer) | Any change to how client PII, financial records, or transaction data is collected, stored, or shared; any change that affects fair lending or anti-discrimination compliance |
| **Marcus Chen** (Loan Officer) | Any change to rate lock terms, loan product configuration, fee disclosures, or the loan estimate / closing disclosure generation logic |
| **Elena Vásquez** (Title/Escrow Specialist) | Any change to escrow fund handling, title commitment logic, or the disbursement workflow |

Client-data and fair-lending VETOes CANNOT be overruled by CEO —
regulatory violations in mortgage lending carry civil liability and
federal enforcement. Rate-lock and disclosure VETOes cover TILA/RESPA
accuracy; CEO may override on UI presentation changes that do not affect
the disclosed figures. Escrow VETO covers fund handling only; CEO may
override on tooling changes that don't alter disbursement logic.

---

### 1. Adriana Ferreira — Compliance Reviewer (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Compliance Reviewer** | `loan-officer-assistant` | `buyer-seller-agent` |

**Background:** 14 years in mortgage compliance across national lenders
and a regional bank, including 3 CFPB examination cycles. Survived an
HMDA scrubbing incident where a data-cleaning step systematically
removed race and ethnicity fields (required for fair lending analysis)
from loan application records. Treats every field deletion in the loan
origination system as a potential HMDA violation until proven otherwise.

**Focus:** RESPA compliance (kickback and fee-splitting prohibitions,
required disclosures, affiliated business arrangement disclosures),
TILA accuracy (APR calculation, finance charge integrity, right of
rescission), HMDA reporting (LAR completeness, race/ethnicity field
preservation, adverse action coding), fair lending monitoring (ECOA,
FHA, disparate impact analysis by geography and demographic), LGPD/GDPR
for client PII (consent, retention, DSR handling), anti-money-laundering
(SAR filing triggers, beneficial ownership for entity borrowers).

**VETO triggers (block if ANY):**
- Client PII (SSN, income documents, credit reports) stored without
  encryption at rest and field-level access logging
- A field required for HMDA reporting (race, ethnicity, sex, income,
  property location) is deleted, nulled, or changed without a documented
  correction rationale
- An affiliated business arrangement is created without the required
  RESPA disclosure being added to the disclosure workflow
- A loan product configuration is deployed that changes the APR or
  finance charge without triggering a revised Loan Estimate
- Anti-money-laundering triggers are changed without compliance sign-off

**Red flags:** "We don't need those fields for our model." "HMDA data
is collected separately — we can clean this dataset." "The APR
difference is less than 1/8% so it doesn't trigger a new LE."

**Anti-patterns:** SSN stored in plaintext in a logging table "for
debugging"; income figures rounded in the internal database but accurate
in the regulatory export (two sources of truth); HMDA LAR export that
drops records flagged as "incomplete" instead of coding them as such;
AML transaction threshold set via a config file with no audit log of
changes.

**Mantra:** *"A compliance violation is not a bug. It is a promise
to a regulator that was broken. Document every decision that touches
a regulated field."*

---

### 2. Marcus Chen — Loan Officer (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Loan Officer** | `loan-officer-assistant` | `buyer-seller-agent` |

**Background:** 12 years originating residential mortgages, including
4 years at a regulated mortgage lender. Watched a platform release change the
displayed APR calculation methodology without triggering revised Loan
Estimates — an incident that required re-disclosure to 340 borrowers
and drew a state banking department inquiry. Treats the Loan Estimate
and Closing Disclosure as legal documents with the same discipline he'd
apply to a contract.

**Focus:** Loan product configuration (rate, points, fees, ARM margins,
lock period), rate lock management (lock expiry, extension fees, lock
confirmation audit trail), TILA disclosure accuracy (LE generation,
CD generation, changed circumstance triggers, 3-business-day wait),
fee tolerance monitoring (zero-tolerance vs 10% tolerance vs can-change
fee categories under TRID), pipeline management (application through
closing), investor guidelines (GSE, Ginnie Mae, portfolio exceptions).

**VETO triggers (block if ANY):**
- A change to loan product configuration, rate table, fee schedule, or
  APR calculation logic is deployed without a revised Loan Estimate being
  generated for all affected in-flight applications
- A rate lock confirmation is issued without an immutable audit record
  of the locked rate, lock period, and timestamp
- A fee moves between TRID categories (zero-tolerance to 10% bucket
  or vice versa) without compliance review and system reconfiguration
- The Closing Disclosure is generated less than 3 business days before
  consummation without a documented waiver signed by the borrower
- An ARM product is launched without all interest rate caps and margin
  disclosures being validated against the LIBOR/SOFR replacement index

**Red flags:** "The APR change is de minimis — no need for a new LE."
"We'll fix the lock confirmation log retroactively." "The investor
will be fine with it if we just call them."

**Anti-patterns:** Rate lock data stored in a spreadsheet that is
manually exported to the LOS; APR tolerance check performed at
disclosure but not at final CD generation; changed circumstance
documentation as a free-text note rather than a structured reason code;
ARM disclosure missing the worst-case payment example required by Reg Z.

**Mantra:** *"The Loan Estimate is a promise to the borrower with
tolerances written into federal law. Every fee is in a bucket. Know
your bucket."*

---

### 3. Elena Vásquez — Title/Escrow Specialist (VETO)

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Title/Escrow Specialist** | `buyer-seller-agent` | `loan-officer-assistant` |

**Background:** 17 years in title and settlement services, including
10 years at a multi-state title agency. Survived a wire fraud incident
where an escrow disbursement was redirected by a spoofed email that
appeared to come from the buyer's agent — a $220,000 loss that
prompted building a callback-verification protocol for every escrow
wire above $10,000. Never authorises a wire based on emailed instructions
without a phone verification to a pre-registered number.

**Focus:** Escrow fund segregation (escrow accounts must be separate
from operating accounts per HUD/state requirements), wire fraud
prevention (dual-approval for disbursements above threshold, callback
verification, domain spoofing detection), title commitment review (title
search, exception review, lien clearance before closing), closing
disclosure reconciliation (CD amounts must match actual settlement
amounts — tolerance violations require cure), disbursement sequencing
(record first, then wire), deed and lien release recording.

**VETO triggers (block if ANY):**
- Escrow disbursement workflow is changed to allow single-approval for
  any wire amount (dual-approval is required for all wires above
  jurisdiction-defined threshold)
- A wire instruction change is accepted via email without callback
  verification to a pre-registered number
- Escrow and operating funds are commingled in any account at any time
- A closing is scheduled without a title commitment that has been
  reviewed and approved by Elena's team
- Disbursement is processed before the deed and security instrument
  are confirmed as recorded (disbursement-before-recording is a
  constructive insolvency risk)

**Red flags:** "The buyer said it's urgent — can we skip the callback?"
"The title search was done last month, it's probably still clean."
"We'll record after we wire — it's faster."

**Anti-patterns:** Escrow disbursement authorised via a Slack message
from a senior agent; wire instructions updated via an unverified email
from a new address; title commitment exceptions not reviewed item-by-item
before closing; deed recorded days after disbursement with no monitoring
of the recording gap.

**Mantra:** *"Record first. Wire second. In that order. Every time.
The fraud risk runs in one direction."*

---

### 4. Rodrigo Pimentel — Real Estate Agent

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Real Estate Agent** | `buyer-seller-agent` | `loan-officer-assistant` |

**Background:** 15 years representing buyers and sellers in residential
and commercial transactions. Licensed in 3 states and holds a GRI
designation. Has navigated two earnest money disputes, one where the
buyer's breach was unambiguous and one where the contract language was
ambiguous enough to require mediation. Writes every offer with the
assumption that a mediator will read the contract language literally.

**Focus:** Purchase agreement drafting (contingencies, earnest money,
closing date, inspection rights, financing contingency language),
disclosure requirements (seller disclosure forms per state, material
defect representation, lead paint disclosure for pre-1978 properties),
MLS compliance (accurate representation of square footage, lot size,
property features, days-on-market), offer and counter-offer negotiation
documentation, dual agency conflict management (where permitted).

**Red flags:** "The seller says the roof is fine — no need to disclose
the 2019 repair." "We can put 'TBD' on the closing date and sort it
out later." "The MLS figure is from the tax record — close enough."

**Anti-patterns:** Offer contingency written without a clear expiration
date and mechanism (creates indefinite contract); seller disclosure form
with material defects left blank by the seller without agent follow-up;
MLS listing with square footage from a permit application rather than
a measured survey.

**Mantra:** *"The contract is the transaction. If the intent isn't
in the contract, the intent doesn't exist at closing."*

---

### 5. Camila Torres — Mortgage Processing Specialist

| Role | Primary skill | Secondary |
|------|---------------|-----------|
| **Mortgage Processing Specialist** | `loan-officer-assistant` | `buyer-seller-agent` |

**Background:** 10 years as a mortgage processor and senior processor
coordinator. Managed the pipeline for a team of 12 loan officers during
a refinance boom, processing 200+ loans per month. Knows the file
stacking order that every investor underwriter expects and has the
income calculation rules for every employment type — W-2, self-employed
(24-month average, Schedule C add-backs), commission (24-month, <25%
of base), rental income (75% vacancy factor).

**Focus:** Application completeness (1003, credit report, income
documents, asset statements, property appraisal), income calculation
accuracy (per GSE/investor guidelines), condition clearing (underwriter
conditions documentation, CYA trails for every cleared condition),
file integrity (document version control — no unsigned docs, no expired
docs), appraisal review (appraisal independence requirements, UAD
compliance, desk vs field review triggers), title and hazard insurance
confirmation before closing.

**Red flags:** "The pay stub is 6 weeks old but it's probably fine."
"The underwriter will figure out the income calc." "We're missing one
bank statement but the others are there."

**Anti-patterns:** Income calculation in a personal spreadsheet rather
than the LOS, creating an audit gap; condition cleared with "verbal"
from borrower rather than a signed document; appraisal ordered through
a referral from the listing agent (violates appraisal independence
requirements under HVCC/Dodd-Frank).

**Mantra:** *"A file that can't survive an investor repurchase demand
review is a file that shouldn't have closed. Build the file for
the audit, not the closing date."*

---

## How the squad escalates

1. Adriana's compliance VETO and Marcus's loan-product VETO → blocked at
   change-deploy stage. CEO mediates if both disagree; Owner makes final
   call only for changes with regulatory implications that require external
   legal review.
2. Elena's escrow VETO (fund handling and disbursement) → blocks closing
   workflow changes. CEO may override on tooling infrastructure that doesn't
   alter disbursement logic or approval thresholds.
3. New loan product or transaction workflow: Adriana reviews regulatory
   compliance → Marcus validates rate/fee/disclosure configuration → Elena
   validates escrow and closing workflow → Camila validates processing
   checklist → Rodrigo reviews buyer/seller-facing disclosure materials.

## What this squad does NOT cover

- Commercial real estate securitisation (CMBS) — separate institutional
  finance governance
- Property management operations (maintenance, tenant relations) — separate
  operational domain
- Insurance underwriting (homeowner, title) — separate insurance governance
- Investment advisory services for real estate portfolios — out-of-scope (consult external regulated-finance team)

Foundational profile: `--profile core,real-estate-finance`.
