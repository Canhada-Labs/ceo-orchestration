---
name: buyer-seller-agent
description: |
  Residential real estate transaction discipline for buyer and seller
  representation. Covers agency law (single-agent, dual-agent, transaction-
  broker), fiduciary duties, listing strategy and CMA-based pricing, offer
  and counter-offer negotiation, disclosure compliance (material defects,
  lead-paint, flood-zone, Megan's Law), inspection and appraisal management,
  closing coordination, and fair-housing compliance across US federal law,
  EU equality directives, and BR Lei 12.288. PII-touching: pre-approval
  letters, SSN/CPF, financial qualification data, negotiation strategy, and
  property-condition history. Use when: representing a buyer or seller through
  transaction lifecycle; preparing or reviewing a CMA; structuring offer
  strategy; advising on seller-disclosure obligations; applying fair-housing
  controls to marketing or steering situations; or coordinating title, escrow,
  and lender parties through closing.
owner: Camila Ortiz (Real Estate Agent, domain persona)
tier: domain:real-estate-finance
scope_tags: [real-estate, buyer-representation, seller-representation, fair-housing, disclosure, closing-coordination, multi-jurisdiction-agency]
inherits: [core/compliance-lgpd, core/pii-data-flow, core/consent-lifecycle, core/dpo-reporting]
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/specialized/real-estate-buyer-seller.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: real-estate-finance
priority: 8
risk_class: medium
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
  - "**/listings/**"
  - "**/offers/**"
  - "**/disclosures/**"
  - "**/closings/**"
  - "**/cma/**"
---

# Buyer-Seller Agent

## Cardinal Rule

Every representation decision must exclusively advance the interests of the
represented party. A buyer's agent owes undivided loyalty to the buyer; a
seller's agent owes undivided loyalty to the seller. No pressure to close,
no commission timeline, and no relationship with the opposing agent excuses
compromising a client's negotiating position, concealing material information
from the client, or disclosing the client's confidential strategy to the other
side. All agreements — offers, counter-offers, amendments, repair agreements,
and possession arrangements — must be in writing and signed by all parties
before being acted upon.

## Fail-Fast Rule

Stop and obtain written client authorisation or escalate to a supervising
broker before proceeding when any of the following is detected:

- A dual-agency situation is forming (same brokerage represents both buyer
  and seller) without signed informed-consent disclosures from both parties —
  agency disclosure must precede any substantive discussion.
- A seller is directing the agent to omit a known material defect from
  disclosure — refuse, document the instruction, and advise the seller in
  writing that non-disclosure exposes both seller and agent to fraud liability.
- A buyer's confidential ceiling price, financial distress, or deadline is
  at risk of disclosure to the listing agent — halt communication and consult
  the client before any further negotiation.
- A marketing decision or showing-routing choice could constitute steering
  under the Fair Housing Act or applicable local statute — stop, document,
  and apply the Fair Housing controls below.
- A closing-wire instruction arrives by email with changed banking details —
  freeze and require verbal confirmation directly with the title company using
  a pre-verified phone number before any funds move.

## When to Apply

Apply this skill when:

- Onboarding a buyer client: needs assessment, pre-approval confirmation, MLS
  search setup, and buyer-agency agreement execution.
- Listing a seller property: CMA preparation, pricing strategy, listing
  agreement execution, staging and photography coordination, MLS input.
- Preparing or analysing an offer: price, terms, contingencies, escalation
  clauses, and earnest-money structuring.
- Negotiating inspection resolution, appraisal gaps, or seller concessions.
- Tracking and clearing contingency deadlines and coordinating title, lender,
  and escrow parties through closing.
- Advising on agency type (single-agent, dual-agent, transaction-broker) and
  the fiduciary obligations each carries.
- Evaluating fair-housing compliance in advertising copy, showing selection,
  or neighbourhood steering situations.

Do not apply for commercial lease negotiation, property-management operations,
or investment-portfolio analysis — those require domain-specific skills with
different regulatory frameworks.

## PII Handling

Real estate transactions generate dense PII including financial qualification
data, government identifiers, and confidential negotiation strategy. The
following controls are mandatory.

**Data categories and classification:**

| Category | Classification | Legal basis required |
|---|---|---|
| Buyer name, SSN/CPF, government ID | Personal data; financial identifier | LGPD Art. 7 / contract |
| Pre-approval letter, credit score, loan conditions | Financial personal data; highly sensitive | LGPD Art. 7 / contract; strict access control |
| Buyer ceiling price, motivation, deadline | Confidential negotiation strategy | Fiduciary duty + LGPD Art. 7; never disclose to opposing side |
| Seller property-condition disclosures | Personal data + legal obligation | LGPD Art. 7 / legal obligation |
| Property address and transaction terms | Personal data (transaction record) | LGPD Art. 7 / contract |
| Earnest-money account details, wire instructions | Financial personal data | LGPD Art. 7 / contract; wire-fraud risk class |

**Mandatory controls:**

- Pre-approval letters and financial qualification documents must be
  transmitted only through encrypted portals or TLS-in-transit channels.
  Never attach to unencrypted email.
- Buyer ceiling price, approval amount, and negotiation strategy must not be
  shared with the listing agent, seller, or any third party without explicit
  written client consent. This applies even when the same brokerage represents
  both sides.
- Seller disclosure forms, property-condition reports, and inspection findings
  are personal data tied to the property record. Retain for the applicable
  statute-of-limitations period for real estate fraud claims in the
  transaction jurisdiction (minimum five years; confirm per jurisdiction).
- Wire instructions must never be communicated solely by email. The closing-
  wire protocol requires a verbal confirmation step (see Closing Coordination
  below). Wire-fraud risk class data must be documented in the transaction file.
- LGPD Art. 7 legal-basis documentation is required for every data category
  processed. For cross-border cloud-platform storage of Brazilian client data,
  verify transfer mechanism under LGPD Art. 33 (adequacy decision or standard
  contractual clauses) at platform onboarding.
- Access to transaction files must be role-scoped: only the representing agent,
  supervising broker, and directly engaged transaction coordinator may access
  client financial or strategy data. Audit log required for bulk exports.
- For full LGPD implementation detail, cross-reference `core/compliance-lgpd`.

## Agency Law

The agency relationship defines the fiduciary obligations owed to each party.
Confirm the agency type in writing before substantive representation begins.

**Agency types:**

| Type | Who is represented | Fiduciary duties owed |
|---|---|---|
| Single-agent buyer | Buyer exclusively | Full fiduciary duties to buyer; no duties beyond honest dealing to seller |
| Single-agent seller | Seller exclusively | Full fiduciary duties to seller; no duties beyond honest dealing to buyer |
| Dual agent | Both buyer and seller | Reduced duties to both; requires written informed consent from both parties before formation |
| Transaction broker | Neither party (facilitating role) | No fiduciary duties; duties of honesty, accounting, and skill apply; jurisdiction-specific rules govern formation |

**Fiduciary duties in single-agency (applies to buyer agent or seller agent):**

- **Loyalty** — place the client's interest above all others, including the
  agent's own commission interests.
- **Obedience** — follow lawful client instructions; refuse instructions that
  require illegal, fraudulent, or unethical acts.
- **Disclosure** — proactively disclose all facts material to the
  representation including conflicts of interest, relationship to other
  parties, and known defects or risks.
- **Confidentiality** — protect client information acquired during
  representation; the obligation survives transaction close.
- **Accounting** — account for all client funds and documents entrusted to
  the agent; earnest money and trust deposits must be tracked to the cent.
- **Reasonable care** — apply the skill and diligence of a competent licensed
  practitioner for the transaction type and jurisdiction.

**Dual-agency restrictions:** Dual agency is prohibited in some jurisdictions
and permitted with conditions in others. Where permitted, dual agency without
written informed consent from both parties is a licence violation in every
US state. Never represent both sides without (a) confirming dual agency is
lawful in the transaction jurisdiction, (b) obtaining written informed consent,
and (c) restricting the agent's confidential access to each party's strategy.

## Fair Housing Compliance

Fair housing obligations are absolute and apply to every stage of the
transaction including advertising, showing selection, offer advice, and
neighbourhood commentary.

**Governing law:**

| Jurisdiction | Operative standard | Protected classes |
|---|---|---|
| US federal | Fair Housing Act (42 U.S.C. § 3604) | Race, colour, religion, national origin, sex, familial status, disability |
| US state additions | Vary by state — most add sexual orientation, gender identity, source of income, marital status | State-specific; verify per transaction state |
| EU | Equal Treatment Directives (2000/43/EC, 2004/113/EC) + national transposition | Race, ethnic origin, sex, religion, belief, disability, age, sexual orientation |
| Brazil | Lei 12.288/2010 (Estatuto da Igualdade Racial) + CF/88 Art. 3 | Race, colour, ethnicity; broader constitutional non-discrimination principle |

**Prohibited conduct:**

- Steering a buyer toward or away from any neighbourhood based on the racial,
  ethnic, or religious composition of that neighbourhood — this is illegal
  regardless of whether the buyer expressed a preference.
- Refusing to show a property to a qualified buyer based on any protected
  class characteristic.
- Advertising language that signals preference for or against any protected
  class — review all listing descriptions and social content for implicit
  exclusionary signals before publication.
- Providing materially different information about available properties,
  financing terms, or transaction services to similarly situated buyers based
  on a protected characteristic.

**Documentation requirement:** Any showing-selection decision that narrows
the property set shown to a buyer must be documented as derived solely from
the buyer's stated criteria. If the set narrows for any reason other than
client-stated criteria, escalate to supervising broker before proceeding.

## Listing Strategy

**Comparative market analysis (CMA) discipline:**

A listing price recommendation must be based on a current CMA anchored to
sold comparables within 90 days and within the applicable market radius.
Active-competition listings inform supply context but are not evidence of
value — buyers buy sold prices. Pending sales are the strongest forward
signal; weight them above active listings where available.

CMA components required before a price recommendation is issued:
(1) minimum three sold comparables adjusted for bedroom count, bath count,
square footage, garage, condition, and location; (2) active competition
count and average DOM; (3) current months-of-inventory and list-to-sale
ratio; (4) any price trend indicator from the prior 60-day period.

**Overpricing prohibition:** Accepting an inflated listing price to win
the listing (buying the listing) produces extended DOM, price reductions,
and a stigmatised property. Recommend only a price range supportable by
the CMA. If the seller insists on a price materially above the CMA range,
document the written disagreement in the listing file before signing.

**Marketing execution checklist:**

- Professional photography is required before MLS activation; drone and
  virtual-tour media where market standard supports it.
- MLS input must be verified for accuracy within 24 hours of activation;
  syndication to major portals confirmed.
- Listing description must not contain fair-housing-restricted language
  and must be reviewed before publication.
- Days-on-market discipline: trigger a pricing-strategy review with the seller
  at the DOM threshold that is 1.5× the current market-average DOM for the
  price band.

## Offer and Counter-Offer Negotiation

**Buyer offer strategy:** Base the price recommendation on the CMA-adjusted
value, current days-on-market, and confirmed competing-offer context. Never
advise a buyer to offer above the appraised value without a documented
appraisal-gap clause covering the difference. Escalation clauses must specify
a verified-offer trigger and a hard cap; never advise an unlimited escalation.

**Multiple-offer fairness (seller side):** Every offer received must be
presented to the seller on the day it is received. The seller — not the agent
— decides which offers to accept, counter, or reject. Never disclose the
specific terms of one offer to a competing buyer without the seller's written
authorisation.

**Competing-offer confidentiality:** In a multiple-offer situation, disclose
only the existence of competing offers to each buyer, not the price or terms
of any other offer. Disclosing competing-offer terms to incentivise escalation
is a breach of fiduciary duty to the sellers and violates agency law in most
jurisdictions.

**Contingency structuring:**

| Contingency | Standard function | Waiver risk |
|---|---|---|
| Inspection | Buyer right to inspect and negotiate or withdraw within agreed period | Waiving exposes buyer to undisclosed defects; only advise waiver on AS-IS verified properties |
| Financing | Protects buyer's earnest money if loan is not approved | Waiving without cash-offer verification risks earnest-money loss |
| Appraisal | Allows renegotiation or withdrawal if appraisal comes in below contract price | Appraisal-gap clause must specify the buyer's covered shortfall amount |
| Home sale | Protects buyer contingent on sale of current property | Advise seller of kick-out clause option to preserve marketability |

## Disclosure Compliance

Disclosure obligations run to both the seller (duty to deliver accurate
disclosures) and the agent (duty to disclose known material facts).

**Material defect categories requiring disclosure in all jurisdictions:**

- Structural defects: foundation cracks, roof condition, load-bearing
  alterations without permit.
- Water intrusion: documented or observed moisture, flood damage, drainage
  issues, sump-pump history.
- Systems condition: HVAC age and service history, electrical panel age and
  known deficiencies, plumbing material type (polybutylene, galvanised).
- Environmental hazards: lead-based paint (federal requirement for pre-1978
  properties), mold presence or prior mold remediation, asbestos-containing
  materials, radon test results.
- Legal and title matters: known encroachments, easements material to use,
  pending litigation affecting title, HOA special assessments.

**Jurisdiction-specific disclosures:** Flood-zone classification and FEMA
flood-map status; homicide or violent crime on the property where required by
state law; registered sex-offender proximity where state statute requires
(Megan's Law disclosure states); underground storage tanks; methamphetamine
laboratory decontamination history where required.

**Latent vs. patent defect distinction:** Patent defects are visible on
reasonable inspection and do not trigger seller disclosure where the buyer
had equal opportunity to observe. Latent defects are hidden and must be
disclosed by the seller even if not observable. When in doubt, disclose —
non-disclosure of a known latent defect is fraud, not discretion.

**Seller instruction to omit:** If a seller instructs the agent to omit a
known defect, refuse, document the refusal in writing, and advise the seller
that the agent may be required to independently disclose known material facts
regardless of seller instruction.

## Inspection and Appraisal

**Inspection protocol:**

- Schedule the inspection within five business days of accepted offer to
  preserve adequate time for resolution within the inspection contingency window.
- Attend the inspection; do not coach the inspector on what to flag or not flag.
- Buyer receives the full inspection report. The agent must not filter or
  summarise selectively.
- Inspection findings triggering negotiation are categorised as: safety
  hazards (repair or credit required), material defects (repair, credit, or
  price adjustment), and informational items (no contract action required).
- If the seller rejects a reasonable repair request, advise the buyer on the
  as-is value implication before electing to waive or withdraw.

**Appraisal management:**

- Financing contingency deadline must provide sufficient time for the lender
  to order, complete, and transmit the appraisal.
- If the appraisal comes in below the contract price: (a) request a
  reconsideration of value with documentation of overlooked comparables before
  accepting the low value; (b) if the value is confirmed, renegotiate price to
  appraised value, execute an appraisal-gap clause if the buyer elects to cover
  the shortfall, or invoke the financing contingency.
- For FHA and VA transactions, the appraisal is tied to the property for the
  appraisal validity period; the seller cannot demand a new appraisal for a
  new buyer within the validity window.

## Closing Coordination

**Parties and responsibilities:**

| Party | Primary responsibility |
|---|---|
| Title / escrow company | Title search, title insurance, escrow management, closing disclosure, deed recording |
| Lender | Loan approval, closing disclosure, wire of loan proceeds |
| Real estate attorney | Document review, title opinion, closing representation where attorney-state law applies |
| Buyer and seller agents | Contingency tracking, final walkthrough coordination, client communication |

**Closing checklist:**

- Confirm all contingencies are cleared in writing before scheduling closing.
- Closing Disclosure review: buyer must receive the CD at least three business
  days before closing; review with the buyer line by line before signing.
- Final walkthrough: schedule within 24 hours of closing; verify that agreed
  repairs were completed, the property is in the contracted condition, and all
  included personal property is present.
- Wire-fraud protocol: send written wire-fraud warning to the buyer at least
  five business days before closing. Before the buyer wires funds, require a
  verbal confirmation call to the title company using a phone number obtained
  independently from a pre-verified source — never a number supplied in a
  closing email.
- Verify that keys, garage openers, access codes, HOA documents, and appliance
  manuals are available for transfer at or before closing.

**No-close gate:** Never proceed to close if any of the following is
unresolved: title exception not insured over, unresolved lien or encumbrance
material to the buyer's use, uncleared financing contingency, or final-
walkthrough finding that materially alters property condition from contract.

## Anti-patterns

| Anti-pattern | Failure mode | Correction |
|---|---|---|
| Dual agency without written consent | Fiduciary breach; licence violation; transaction may be voidable | Obtain signed dual-agency disclosure from both parties before any representation of both sides |
| Steering toward or away from neighbourhoods | Fair Housing Act violation; civil liability; licence sanction | Route showing selection solely from client-stated criteria; document basis; escalate any ambiguous situation to broker |
| Undisclosed material defect | Fraud; seller and agent liability; transaction rescission risk | Disclose all known material defects regardless of seller instruction; document refusal in writing if seller objects |
| Overpriced listing accepted to win business | Extended DOM; price-stigma; seller trust erosion | Present CMA range; document disagreement in writing; hold the recommended range |
| Disclosing competing-offer terms | Fiduciary breach to seller; undermines seller's negotiating position | Disclose existence of competing offers only; never disclose price or terms without seller written authorisation |
| Wire instruction via email only | Wire-fraud vector; buyer financial loss; professional liability | Enforce verbal-confirmation protocol with pre-verified title-company phone number before any wire |
| Coaching the inspector | Concealment of defect; professional misconduct; disclosure obligation triggered anyway | Never instruct or influence what the inspector notes; attend as observer only |
| Proceeding to close with unresolved title issue | Title defect passes to buyer; lender may not fund; rescission after recording | Halt close until title company confirms issue is insured over or cleared |

## Cross-References

- `core/compliance-lgpd` — LGPD legal bases, data-subject rights, breach
  notification, and cross-border transfer mechanisms for all PII processed
  during the transaction lifecycle; this skill inherits and specialises those
  controls.
- `domains/real-estate-finance/skills/loan-officer-assistant` — mortgage
  qualification standards, loan-product comparison, and financing-contingency
  structuring; coordinate for buyer pre-approval and appraisal-gap analysis.
- `domains/legal/skills/document-review` — contract interpretation, title
  opinion review, and closing-document audit for attorney-state transactions
  or complex easement and encumbrance situations.

## ADR Anchors

- **ADR-058** — two-pass review gate; applies to all transaction deliverables
  (CMA reports, offer strategy memos, disclosure review checklists, closing
  coordination packets) before client transmission or matter-file lodgement.
