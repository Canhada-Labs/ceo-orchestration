---
name: digital-presales
description: >
  Presales engineering for government and public-sector digital transformation
  engagements. Covers the full lifecycle from policy signal interpretation and
  opportunity qualification through solution architecture, bid documentation,
  proof-of-concept validation, and post-award handoff. Operates across
  multiple procurement jurisdictions — FedRAMP / GovRAMP / FISMA (US), eIDAS 2
  / GDPR / NIS2 (EU), LGPD / Lei das Estatais 13.303 / Lei 14.133 (Nova Lei de
  Licitações) + ICT procurement instructions (Brazil), and 等保2.0 / 国密 / 数据本地化
  (China/APAC) — applying the same structural discipline to each. Includes
  compliance matrix authorship, sovereign-cloud architecture tradeoffs, and
  data-residency mandate mapping. Use when designing a presales workflow for a
  public-sector engagement; reviewing a draft bid document for compliance
  coverage; shaping a POC acceptance-criteria set; advising on
  multi-jurisdiction data-residency architecture; or assessing go/no-go for a
  government opportunity.
owner: Augustina Ferreira (Government Digital Presales Lead, domain persona)
secondary_owner: Tomasz Wierzbicki (Public Sector Compliance Architect, domain persona)
tier: domain:government
scope_tags: [presales, public-sector, bid-documentation, fedramp, eidas, lgpd, compliance-architecture]
pii_handling: optional
inspired_by:
  - source: msitarzewski/agency-agents/specialized/government-digital-presales-consultant.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: government
priority: 8
risk_class: medium
stack: []
context_budget_tokens: 700
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
  - "**/bids/**"
  - "**/rfp/**"
  - "**/proposals/**"
  - "**/compliance-matrix/**"
  - "**/poc/**"
---

# Government Digital Presales

## Cardinal Rule

A bid commitment the implementation team cannot deliver under audit-grade
scrutiny is a contract that must be lost, not won. Every technical claim in
a bid document — architecture scope, performance metrics, compliance
posture, staffing levels, timelines — must be traceable to evidence the
delivery team can reproduce under protest or contract dispute. Over-promising
to win creates a liability larger than the contract value.

## Fail-Fast Rule

If a mandatory compliance control (FedRAMP authorization boundary, LGPD
data-minimization requirement, 等保2.0 Level 3 security domain, eIDAS
trust-service qualification) cannot be mapped to a concrete product or design
decision already in the solution architecture, **stop bid preparation and
escalate**. A compliance matrix row that says "TBD" or "planned for Phase 2"
for a mandatory control is a disqualification risk in every jurisdiction.
Do not submit.

## When to Apply

- Qualifying a government or public-sector opportunity (go/no-go assessment).
- Authoring or reviewing a technical proposal, compliance matrix, or SOW.
- Designing a POC scope and acceptance-criteria set.
- Advising on sovereign-cloud, on-prem, or hybrid architecture for a
  government agency.
- Mapping data-residency and cryptography requirements across jurisdictions.
- Preparing a bid-document review for public-records exposure risk (FOIA /
  sunshine laws).
- Conducting a presales-to-delivery handoff.

## Public-Sector Engagement Lifecycle

```
Pre-RFP intel
    |
    v
RFI response (optional — shapes the RFP)
    |
    v
Solution shaping (architecture + compliance mapping + partner alignment)
    |
    v
RFP response (technical proposal + compliance matrix + past performance +
              pricing + risk register)
    |
    v
POC / technical evaluation (if required by the procuring agency)
    |
    v
BAFO — Best and Final Offer (if multi-round procurement)
    |
    v
Award / contract execution
    |
    v
Presales-to-delivery handoff (commitments transfer + knowledge transfer)
```

Each gate has a hard exit condition:

| Gate | Hard exit |
|------|-----------|
| Pre-RFP intel | Budget not confirmed, no clear timeline → monitor only |
| Solution shaping | Mandatory compliance control unresolvable → no-bid |
| RFP response | Disqualification risk in qualifications section → no-bid |
| POC | Acceptance criteria not agreed in writing before start → defer start |
| BAFO | Price below cost floor → withdraw or accept loss on record |
| Handoff | Delivery team cannot confirm they own all presales commitments → escalate before contract signing |

## Multi-Jurisdiction Compliance Frame

Every government engagement must identify the applicable compliance frame
before solution architecture begins. The table below covers the four primary
lanes. A single engagement may span multiple lanes (e.g., a multinational
agency deployment).

| Jurisdiction | Key Frameworks | Typical Bid Touchpoints |
|---|---|---|
| **US federal / state** | FedRAMP (cloud authorization), GovRAMP (formerly StateRAMP, rebrand announced February 2025), FISMA (agency ISMS), NIST SP 800-53 Rev. 5, CMMC 2.0 (defense supply chain) | FedRAMP authorization impact level (Low/Moderate/High) cited in §Technical Approach; FISMA system categorization drives security controls count; CMMC level for any DoD-adjacent work; state procurement code compliance |
| **EU / EEA** | eIDAS 2 (electronic identity and trust services, including European Digital Identity Wallet provisions), GDPR (personal data), NIS2 (network and information security), EU Cloud Code of Conduct, EUCS (EU Cloud Services scheme, evolving) | Trust-service qualification level for identity components; GDPR Article 28 data-processor clauses; NIS2 incident-reporting SLAs (early-warning within 24h, full notification within 72h); EU-based data processing for public authorities |
| **Brazil** | LGPD (Lei 13.709 — personal data protection), Lei das Estatais 13.303 (state-owned enterprise procurement rules), Lei 14.133 (Nova Lei de Licitações e Contratos — replaces 8.666 over the 2024-2026 transition), current ICT procurement instruction (verify the operative IN at intake — instructions are revised periodically; previous IN-04/SLTI superseded by subsequent instructions under SGD/ME), ABNT NBR ISO/IEC 27001 | LGPD lawful-basis for data processing; Lei 13.303 competitive-bidding thresholds; current ICT instruction technical qualification requirements; TCU audit readiness |
| **China / APAC** | 等保2.0 (Cybersecurity Classified Protection Level 2/3/4), 国密 / Guomi algorithms (SM2/SM3/SM4), 数据本地化 (data localization), PIPL (Personal Information Protection Law) | 等保 level classification and remediation plan; Guomi algorithm coverage for identity, transmission, storage; data localization boundary for government-grade deployments; PIPL cross-border transfer controls |

Jurisdiction-neutral minimum bar (applies to all four lanes):
- Data classification scheme documented before solution design is finalized.
- Encryption-at-rest and encryption-in-transit with named algorithm + key management plan.
- Identity and access management design with named authentication assurance level.
- Audit log retention period and tamper-evidence mechanism specified.
- Incident response SLA named in the bid.

## Policy Interpretation Discipline

### Reading a policy document for technical implication

1. **Identify the enforcement class.** Distinguish "shall" (mandatory),
   "should" (recommended), and "may" (permitted) language. Only "shall"
   clauses are hard controls in the compliance matrix.
2. **Extract the technical operand.** For each mandatory clause, identify
   what system component, data type, or process is being constrained.
   Map each clause to a named architecture element before writing bid prose.
3. **Trace to an accepted standard.** Cite the specific version of the
   policy document (publication date, section number, clause number).
   Paraphrase for readability, but the verbatim clause reference must appear
   in footnotes or the compliance matrix. Evaluators cross-check.
4. **Identify the verification artifact.** Each mandatory control must have
   a named verification artifact: a penetration test report, a third-party
   assessment letter, a certification document, or a test result. "We comply"
   without a named artifact is not compliance.
5. **Date-stamp the policy version.** Regulations are amended. A bid
   submitted against a superseded policy version is a liability. Record the
   specific document version cited in every compliance matrix row.

### What bid responses MUST cite verbatim vs. paraphrase

| Item | Treatment |
|---|---|
| Mandatory control clause | Verbatim quote in compliance matrix; source, section, and clause number in footnote |
| Authorization level or categorization | Verbatim label (e.g., "FedRAMP Moderate", "等保 Level 3") — never paraphrase |
| Applicable law citation | Full statutory reference (e.g., "5 USC §552a" not "the Privacy Act") |
| Certification or qualification name | Exact name and issuing body; never abbreviate without defining |
| Performance SLA in contract template | Verbatim from the procuring agency's template — no substitutions without written approval |

## Solution Architecture for Government

### Deployment model selection

| Model | Applicable when | Key constraints |
|---|---|---|
| Sovereign / government cloud | Agency policy requires FedRAMP-authorized or equivalently certified IaaS; data must not leave jurisdiction | Named CSP authorization status must be confirmed before architecture is locked; key management must be agency-controlled (BYOK or HYOK) |
| On-premises government data center | Agency prohibits cloud hosting; classified system boundary required; air-gap mandate | Vendor access to production environment is restricted; deployment procedures must be agency-executable; hardware refresh cycle owned by agency |
| Hybrid (agency DC + authorized cloud) | Sensitive workloads on-prem; analytics / citizen-facing layers in authorized cloud | Data-residency boundary between tiers must be documented; latency SLA for cross-tier calls must be bid-committed |
| Commercial cloud (non-sovereign) | Low-sensitivity public-facing services only; no PII at rest; jurisdiction explicitly permits | Confirm agency authority to use non-authorized cloud; document out-of-scope data types; include data-egress controls |

### Cryptography mandates by jurisdiction

| Jurisdiction | Algorithm requirement | Certificate / CA requirement |
|---|---|---|
| US federal | FIPS 140-2/3 validated modules; NIST-approved algorithms (AES-256, SHA-2, RSA-2048+, P-256+) | PIV/CAC or FICAM-approved credential for identity |
| EU | ENISA-recommended; eIDAS qualified certificates for trust services; GDPR-compliant key management | Qualified Trust Service Provider (QTSP) certificate for legal electronic signatures |
| Brazil | ABNT NBR ISO/IEC 27001; ICP-Brasil certificate chain for legal signatures (MP 2.200-2) | ICP-Brasil Autoridade Certificadora for qualified signatures |
| China / APAC | SM2 (asymmetric), SM3 (hash), SM4 (symmetric) for government-grade; domestic CA certificate | Approved commercial CA using Guomi certificate profile |

### Data-residency matrix

For each data category in the solution, document:
- **Storage jurisdiction**: the physical or logical boundary where data at
  rest resides.
- **Processing jurisdiction**: where compute operations occur (including
  analytics, AI inference, log aggregation).
- **Transit path**: whether data crosses jurisdictional boundaries in transit
  and under what encryption and legal basis.
- **Backup / DR jurisdiction**: disaster-recovery replicas may trigger
  secondary data-residency obligations; confirm these separately.

## Bid Document Structure

A government bid response must contain the following sections in the
order the RFP evaluation criteria demand. Where the RFP specifies a
different structure, follow the RFP exactly — evaluators are often
required to score section-by-section and will penalize out-of-order
content.

| Section | Required fields | Hard rules |
|---|---|---|
| **Executive Summary** | Value proposition; compliance posture summary; key differentiators; management approach overview | ≤ the page limit specified in the RFP; no pricing in this section unless RFP requires it |
| **Technical Approach** | Architecture overview; deployment model; security architecture; integration plan; Xinchuang / FedRAMP / eIDAS qualification level as applicable; staffing plan; implementation schedule with milestones | Every claim must be traceable to a named product, certified service, or peer-reviewed method |
| **Compliance Matrix** | One row per RFP requirement (identified by section and clause number); response: "Compliant", "Partially Compliant" (with gap plan), or "Not Compliant" (with rationale); evidence reference | Must be line-by-line traceable to RFP requirements; "Compliant" without an evidence column is insufficient |
| **Past Performance** | Client name (or anonymized placeholder if confidentiality required); contract value range; scope description; period of performance; client POC name and contact (or attestation it is available upon request); relevance statement | No fabricated references; references must be reachable and willing; relevance must match the scope of the current bid |
| **Pricing** | Line-item cost breakdown; total evaluated price; payment schedule tied to milestones; warranty / maintenance costs | Pricing must be consistent with Bill of Materials in Technical Approach; no shadow pricing reserved for negotiation |
| **Risk Register** | Risk description; probability; impact; mitigation; residual risk; owner | At least 5 risks; risks that emerge during delivery and were foreseeable but absent from the bid register are a contractual liability |

### Compliance matrix authorship rule

The compliance matrix is the single most audited section of a government
bid. Every row must state:
1. The RFP requirement identifier (section + clause number).
2. The verbatim or condensed requirement text.
3. The response disposition: Compliant / Partially Compliant / Not Compliant.
4. The named evidence artifact: product certification, test report, policy
   document, or architecture diagram section.
5. The responsible party (prime contractor or named subcontractor).

A compliance matrix that copies the prior bid's rows without re-verifying
against the current RFP is a disqualification risk. RFPs change between
editions. Verify every row against the current document version.

## POC Validation Discipline

### Before POC start

The following must be agreed in writing before any POC environment is
stood up:

1. **Acceptance criteria**: specific, measurable, falsifiable pass/fail
   criteria for each POC scenario. "System works well" is not a criterion.
   "OCR extraction accuracy ≥ 95% on the provided 200-document test set,
   measured by the agency evaluator" is a criterion.
2. **Scope boundary**: the POC validates named capabilities, not a full
   system. Any agency request to add scope during POC requires written
   change authorization. Undocumented scope expansion is a free project.
3. **Data protocol**: test data must be agency-provided or
   agency-approved synthetic data. Vendor-sourced demo data that "looks
   like" agency data does not satisfy evaluation requirements.
4. **Evaluation method**: who measures, what tool, what sample size, what
   time window. If the agency retains the right to re-run tests, define
   the re-run protocol.
5. **Sign-off authority**: the individual with authority to sign the POC
   acceptance report must be identified before the POC starts. Evaluator
   turnover mid-POC without sign-off transfer is a risk to manage.

### Falsifiability requirement

Every acceptance criterion must have a binary outcome. If the evaluator
cannot state "this criterion passed" or "this criterion failed" without
judgment, the criterion is not falsifiable and must be rewritten. Vague
criteria favor the agency in disputes.

### Sign-off protocol

A POC without a signed acceptance report is an incomplete POC regardless
of informal feedback. Obtain written sign-off before demobilizing the POC
environment. Retain the signed report as contract evidence.

## Public Records / Transparency Considerations

Bid documents submitted to government agencies are generally subject to
public-records disclosure (FOIA in the US, equivalents in other
jurisdictions) after award. This is not optional and not negotiable. The
bid document is a semi-public artifact.

### What must NEVER appear in a bid document

- Unpublished proprietary pricing models or margin structures beyond the
  line-item prices required by the RFP.
- Non-public client names when a reference is provided under NDA — use
  "a large municipal agency" and provide the POC contact through a separate
  confidential channel.
- Internal personnel salary data; use labor-category rates.
- Trade-secret technical details beyond what is needed to demonstrate
  compliance; mark the minimum necessary set as trade secret under the
  applicable exemption (e.g., FOIA (b)(4)) and confirm the agency will
  honor the request.
- Any language implying coordination with another bidder on pricing or
  technical approach.

Cross-link: `domains/government/skills/foia-and-records` covers the
exemption framework and redaction mechanics that govern post-award
disclosure of bid documents.

## Pricing Disclosure Hard-Rules

- **No shadow pricing.** The price submitted is the price to be executed.
  Reserving a lower price "for negotiation after selection" is an integrity
  violation in most government procurement frameworks.
- **No price changes after technical lock.** In multi-envelope procurement
  (technical envelope scored before commercial envelope opened), modifying
  the commercial envelope after technical submission is prohibited and may
  constitute bid fraud.
- **Cost floor discipline.** A below-cost price that relies on anticipated
  change orders to recover margin is not a compliant bid; it is a loss-leader
  that creates delivery and legal risk. Document the cost floor before
  pricing is finalized.
- **Consistency between technical and commercial.** The Bill of Materials
  in the technical proposal and the line-item pricing must reference the
  same products, quantities, and service levels. Evaluators check for
  inconsistencies as a signal of poor planning or intentional misdirection.
- **Warranty and maintenance costs.** Total evaluated price in most
  government RFPs includes lifecycle costs. Omitting or underestimating
  O&M costs to win on initial price creates a performance baseline that
  cannot be sustained.

## Anti-patterns

| Anti-pattern | Description | Consequence |
|---|---|---|
| **Over-promising on compliance** | Marking controls "Compliant" in the compliance matrix without confirmed evidence, assuming the gap will be closed during delivery | Audit finding, cure-notice, contract termination; in regulated jurisdictions may constitute a false claim |
| **"We've done this before" without a case study** | Asserting past performance relevance without a specific, verifiable reference that matches scope, scale, and jurisdiction | Evaluator cannot award performance points; if reference is later found unverifiable, bid may be disqualified retroactively |
| **Single-jurisdiction generalization** | Applying one jurisdiction's compliance frame (e.g., FedRAMP) as if it satisfies another (e.g., 等保2.0 or LGPD) | Compliance matrix gaps discovered during evaluation or post-award audit; redesign cost falls on contractor |
| **Copy-paste compliance matrix** | Reusing compliance matrix rows from a prior bid without re-verifying against the current RFP version | Requirements that changed between RFP editions appear incorrectly answered; evaluators flag as inattentive or non-compliant |
| **Ghosted past-performance citations** | Listing a project reference whose client POC no longer works at the agency or has refused to be listed | Past-performance verification fails; points are zeroed; if the reference was known unavailable, it may be treated as misrepresentation |
| **POC scope creep acceptance** | Agreeing verbally to add POC scenarios during evaluation without written change authorization | POC exceeds budget; acceptance criteria become ambiguous; agency gains leverage to claim the original criteria were not met |
| **Loss-leader pricing with change-order recovery intent** | Pricing below cost under the assumption that change orders will make the contract profitable | Government contracting officers are trained to detect this; protests from competitors; unsustainable delivery; reputational damage |
| **Bid document as sales brochure** | Filling bid narrative with marketing language and vendor-capability descriptions not directly responsive to RFP requirements | Evaluators score for responsiveness; non-responsive sections earn zero points regardless of quality |

## Cross-References

- `domains/government/skills/foia-and-records` — FOIA exemption framework,
  redaction mechanics, and post-award bid-document disclosure obligations.
- `domains/government/skills/public-procurement` — Bid-confidentiality
  invariants, debarment-list vetting, COI declarations, and protest-survivability
  requirements for the procurement lifecycle.
- `domains/government/skills/accessibility-section-508` — Section 508 / WCAG
  compliance requirements for digital government deliverables; a mandatory
  compliance matrix row in US federal and many state bids.
- `core/compliance-lgpd` — LGPD data-processing rules, lawful-basis mapping,
  and data-subject rights mechanics for Brazilian public-sector engagements.

## ADR Anchors

- **ADR-058** — Two-pass review discipline for high-stakes authored artifacts.
  Bid documents are explicitly in scope: a technical proposal and its compliance
  matrix must pass a two-pass review (first pass: technical accuracy and
  completeness; second pass: compliance matrix row-by-row verification against
  the RFP) before submission. A single-pass review is insufficient for
  government bid documents.
