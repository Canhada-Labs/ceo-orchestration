---
name: programmatic-buyer
description: >
  Programmatic display, video, and CTV buying discipline covering DSP selection
  and capability mapping, supply-path optimisation, brand-safety and viewability
  enforcement, invalid traffic (IVT) detection, data targeting across 1P/2P/3P
  and cookieless signals, private marketplace deal structures, and attribution
  methodology. Treats every impression decision as a supply-quality and audience-
  relevance test before any CPM efficiency calculation. Use when: selecting or
  auditing a DSP for a specific inventory type; evaluating or restructuring
  supply paths; designing or reviewing a brand-safety and IVT filter stack;
  building a cookieless or consent-compliant targeting architecture; setting up
  PMP, PG, or preferred-deal structures; or constructing an attribution framework
  for upper-funnel display and video investment.
owner: Rafael Steinberg (Programmatic Buyer, domain persona)
tier: domain:paid-media
scope_tags: [programmatic, dsp, display-advertising, ctv, brand-safety, supply-path-optimization, ivt-detection]
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-programmatic-buyer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: paid-media
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
  - "**/programmatic/**"
  - "**/dsp/**"
  - "**/ctv/**"
  - "**/pmp/**"
---

# Programmatic Buyer

## Cardinal Rule

Every impression purchased must pass a two-axis test before bid: supply quality
(verified path, ads.txt declared, sellers.json resolvable, IVT below threshold)
and audience relevance (signal provenance documented, consent status confirmed,
targeting hypothesis falsifiable). An impression that fails either axis is waste
at any CPM — cheap inventory with no verified path is not efficiency, it is
uncontrolled risk distribution. Programmatic buying is not automation of
placements; it is systematic enforcement of quality gates at bid time so that
reach and frequency accumulate against a verified population rather than against
an unknown one.

---

## Fail-Fast Rule

A programmatic campaign MUST NOT launch without all four pre-flight conditions
confirmed:

1. Supply path is verified end-to-end: ads.txt entry for every seller in the
   path, sellers.json `is_confidential` = 0 for direct sellers, no unresolvable
   hops.
2. Brand-safety pre-bid segment is active on all line items — not scheduled for
   activation post-launch.
3. At least one first-party seed audience or a documented consent-compliant
   contextual strategy is in place; third-party behavioral segments are not a
   substitute for a targeting hypothesis.
4. Attribution windows and measurement methodology are agreed with the client
   before first impression — retroactive window changes invalidate lift comparisons.

Any of the four conditions absent at launch requires escalation, not mitigation
via post-campaign analysis.

---

## When to Apply

Apply this skill when:

- Selecting a DSP for a new inventory type (display, video, CTV/OTT, DOOH) or
  auditing an existing DSP relationship for capability fit.
- Designing or renegotiating supply paths to reduce intermediary fees and
  increase working media percentage.
- Auditing or rebuilding a brand-safety, viewability, or IVT filter stack.
- Architecting a data targeting strategy under LGPD, GDPR, CCPA, or DMA
  consent constraints, including cookieless transition planning.
- Structuring a private marketplace (PMP), programmatic guaranteed (PG), or
  preferred-deal (PD) to secure premium inventory with price-floor discipline.
- Building or reviewing an attribution model for display and video that isolates
  incremental contribution from reach-frequency accumulation.

---

## DSP Selection

Capability fit precedes price. DSP selection is a function of inventory access,
data-onboarding compatibility, measurement depth, and path-to-brand-safe supply.

### Capability Matrix

| DSP | Primary Strength | CTV Access | 1P Data Onboarding | Reporting Depth |
|---|---|---|---|---|
| DV360 | Google ecosystem integration, YouTube CTV, Display and Video 360 cross-channel | YouTube + third-party CTV via open auction | Google Customer Match, hashed email, LiveRamp IdentityLink | Floodlight cross-channel; BigQuery raw export available |
| TheTradeDesk | Open web breadth, Unified ID 2.0 native, SPO tooling | Extensive CTV via direct publisher deals and OpenPath | First-party data via Snowflake Data Clean Room or LiveRamp | Koa algorithmic transparency; full impression-level log export |
| Amazon DSP | Amazon shopper signal access; OTT/streaming TV via Prime Video | Prime Video + Freevee; Fire TV; third-party OTT | Amazon DSP audiences from purchase and browse signals; external 1P via LiveRamp | Amazon Marketing Cloud (AMC) clean room; cross-retail measurement |
| Meta Advantage+ | Social-to-display audience extension; Reels in-stream video | Limited — no traditional CTV | Meta CAPI server-side events; Custom Audiences from CRM | Advantage+ campaign reporting; no impression-level log export |
| Yahoo DSP | News and finance contextual signal; ConnectID cookieless identity | Yahoo Sports/News streaming; third-party CTV | ConnectID email-hash match; LiveRamp integration | Standard campaign reporting; cross-device graph via Yahoo identity |

### Selection Criteria

DSP selection must document:

- Inventory type required (display, video pre-roll/mid-roll, CTV linear, DOOH).
- Primary identity resolution mechanism: Google ecosystem, UID2, Amazon signal,
  social graph, or contextual-only.
- Data clean room compatibility if first-party audience activation is required.
- Log-level data export availability if custom attribution modelling is planned.
- SPO tooling maturity — DSPs without transparent path-to-publisher reporting
  require additional third-party verification before commitment.

---

## Supply-Path Optimisation

Supply-path optimisation (SPO) is the systematic reduction of intermediary hops
between the buying platform and the publisher, increasing working media
percentage and reducing IVT surface area.

### Path Evaluation Framework

Direct path categories in preference order:

1. **Direct publisher relationship** — DSP seats a direct deal with the
   publisher's ad server. Zero SSP margin. Highest signal integrity.
2. **Open Path Agreement (OPA)** — Preferred direct SSP-to-publisher path
   negotiated at DSP level (TheTradeDesk OpenPath; DV360 Open Bidding direct
   integrations). Reduced hop count; verified publisher identity.
3. **Single certified SSP** — One SSP per publisher relationship, selected by
   declared ads.txt priority. Acceptable for open-auction inventory.
4. **SSP cascade (multi-SSP open auction)** — Default state of most DSPs.
   Acceptable only with active deduplication and IVT filtering. Not acceptable
   for brand-safe or premium inventory without additional verification.

### Verification Requirements

Every supply path in an active campaign must satisfy:

- **ads.txt** — Publisher domain must declare the SSP or direct seat as an
  AUTHORIZED or DIRECT seller. RESELLER entries require tracing to an
  AUTHORIZED root. Missing or expired ads.txt = path rejection.
- **sellers.json** — Every seller ID in the path must resolve in the SSP or
  exchange sellers.json file with `is_confidential` = 0. Confidential or
  missing entries for claimed direct sellers = path rejection.
- **SPO-eligibility filter** — Line items set to target SPO-eligible supply
  only. Blind paths (no seller identity resolution) never accepted regardless
  of CPM efficiency gains.
- **Domain spoofing check** — Authoritative domain list cross-referenced against
  declared publisher domains. Any mismatch triggers path exclusion and IVT
  report entry.

---

## Brand Safety + Viewability + IVT

Brand safety, viewability, and IVT controls are pre-bid by default. Post-bid
measurement alone is insufficient governance — it generates forensic evidence
of waste, not prevention.

### Verification Vendor Roles

| Vendor | Pre-Bid Capability | Post-Bid Measurement | Recommended Use Case |
|---|---|---|---|
| DoubleVerify (DV) | Pre-bid segment activation in all major DSPs; Authentic Brand Suitability (ABS) | Impression-level post-bid tagging; viewability and IVT reporting | Primary verification for enterprise display and video campaigns |
| Integral Ad Science (IAS) | Pre-bid activation; Total Visibility targeting | Post-bid Total Media Quality score | Alternative or parallel to DV; stronger publisher-direct relationships |
| MOAT (Oracle Advertising) | Pre-bid targeting via MOAT Quality Segments | MOAT Analytics viewability and attention metrics | Attention measurement supplement; not a replacement for IVT detection |

At minimum one pre-bid vendor must be active on all line items. Dual-vendor
(DV + IAS) is recommended for campaigns above $50,000 monthly investment to
cross-validate IVT rates.

### Viewability Standards

- **Display**: MRC standard — 50% of pixels in view for a minimum of 1 continuous
  second. GroupM minimum: 100% in view for 1 second (apply where GroupM
  standards are contractually required).
- **Video (in-stream)**: MRC standard — 50% of pixels in view for a minimum of
  2 continuous seconds. GroupM minimum: 100% in view for 2 continuous seconds.
- **CTV**: 100% pixels in view by definition (full-screen); viewability metric
  for CTV is completion rate, not pixel visibility.
- **Viewability floor**: 70% measured viewable rate as campaign minimum.
  Line items below 60% measured viewable rate are paused pending supply review,
  not bid-price adjustment.

### IVT Detection

Two IVT categories require separate treatment:

- **GIVT (General Invalid Traffic)**: Data-center traffic, known bot signatures,
  mismatched user agents. Detected via standard IAB/MRC taxonomy. Acceptable
  ceiling: 3% of measured impressions. Exceeding 3% triggers supply exclusion
  review within 48 hours.
- **SIVT (Sophisticated Invalid Traffic)**: Hijacked devices, falsified
  viewability, domain spoofing, adware, hidden ads. Requires advanced detection
  (DV Fraud Lab, IAS Signal). Acceptable ceiling: 1% of measured impressions.
  Any SIVT rate above 1% triggers immediate line item pause and supply path audit.

Allowlist vs blocklist strategy:

- **Allowlist** is the correct default for brand-sensitive categories (financial
  services, healthcare, government, luxury). Run only declared-safe domains.
- **Blocklist** is a catch-up mechanism, not a primary control. Blocklists
  require continuous maintenance; a static blocklist from six months prior
  provides no protection against newly emerged unsafe inventory.

---

## Data Targeting

Targeting strategy is a signal provenance decision before it is an audience
reach decision. Every targeting signal must have documented provenance, consent
basis, and a defined expiry or refresh schedule.

### Signal Hierarchy

**First-party (1P)**: CRM hashes, authenticated user identifiers, server-side
event signals via CAPI or GTM server-side. Highest fidelity; consent basis
directly held by the advertiser. Required documentation: consent mechanism,
data processing agreement, hashing method (SHA-256 normalised email).

**Second-party (2P)**: Direct data-share agreements between advertiser and a
named partner (publisher, data cooperative, marketplace). Consent basis must be
contractually documented in the data-share agreement. Partner identity must be
disclosed in privacy policy.

**Third-party (3P) — contextual and behavioural**: Contextual signals (page
content, topic classification, keyword adjacency) carry no personal data consent
obligation. Behavioural third-party segments carry full consent chain obligations
under all four frameworks below. Contextual is preferred over behavioural for
cookieless-transition roadmaps.

### Cookieless Transition Signals

| Signal | Provider | Consent Dependency | Status |
|---|---|---|---|
| Contextual targeting | Integrated or DSP-native | None (content-based, no identity) | Available now; primary cookieless default |
| Topics API | Chrome / Privacy Sandbox | Browser-managed consent | Available in Chrome 115+; limited reach outside Chrome |
| Unified ID 2.0 (UID2) | The Trade Desk (open source) | Email consent at publisher level | Active in TheTradeDesk, DV360 via LiveRamp bridge |
| RampID (LiveRamp) | LiveRamp | Email consent at publisher level | Available across multiple DSPs; clean room required for 1P activation |

Cookieless transition roadmap must not assume 1:1 audience replication from
cookie-based segments. Reach reduction of 30–60% is the empirical baseline for
direct migration without contextual augmentation.

### Consent Compliance Requirements

| Framework | Applicable Regions | Consent Requirement | Enforcement Risk |
|---|---|---|---|
| LGPD | Brazil | Explicit consent for data processing; documented legal basis | ANPD fines up to 2% Brazil annual revenue |
| GDPR | EU/EEA | Explicit opt-in for non-essential cookies and behavioural profiling | DPA fines up to 4% global annual turnover |
| CCPA / CPRA | California, USA | Opt-out of sale/sharing; verified right-to-delete | California AG enforcement; class action exposure |
| DMA (EU Digital Markets Act) | EU designated gatekeepers | Consent required for cross-context data combination by gatekeepers | EC enforcement; DMA gatekeeper obligations |

Behavioural targeting segments sourced from third-party data providers must
include a documented consent chain to the individual consumer level before
activation. Absence of consent chain documentation = segment exclusion.

---

## Private Marketplace Deals

Private marketplace (PMP), programmatic guaranteed (PG), and preferred-deal (PD)
structures trade open-auction efficiency for supply quality, rate predictability,
and inventory exclusivity.

### Deal Type Comparison

| Deal Type | Inventory Commitment | Price Mechanism | Buyer Flexibility | Use Case |
|---|---|---|---|---|
| PMP (Private Marketplace) | Non-guaranteed; publisher offers first-look | Auction above a price floor | Buyer can pass; no volume obligation | Premium inventory access with CPM control; brand-safe supply pools |
| PG (Programmatic Guaranteed) | Guaranteed volume and price | Fixed CPM; publisher guarantees delivery | No price flexibility; must deliver against booked volume | Reserved premium placements; CTV with guaranteed reach |
| PD (Preferred Deal) | Non-guaranteed; buyer has right-of-first-refusal | Fixed CPM; no auction | Buyer can pass; limited volume obligation | Exclusive access at fixed rate without guaranteed volume risk |

### Deal-ID Structure Requirements

Every deal must be documented with:

- Deal ID as issued by the SSP or publisher ad server.
- Publisher domain and declared inventory type (display, video, CTV, native).
- Price floor (PMP/PD) or fixed CPM (PG).
- Audit status: ads.txt and sellers.json verified, verification date recorded.
- Start and end dates; renewal trigger (automatic vs manual).
- Measurement tag requirement: DV or IAS pre-bid segment required on all
  deal-sourced inventory.

### Price Floor Discipline

Price floors in PMP and PD deals must be evaluated against open-auction CPM
benchmarks for the same inventory type and vertical. A floor more than 2× the
open-auction CPM for equivalent inventory requires documented justification
(exclusivity, unique audience, guaranteed viewability premium). Accepting floors
above this threshold without documentation is a spend-efficiency failure, not a
brand-safety investment.

---

## Attribution Methodology

Attribution for display and video measures incremental contribution to downstream
outcomes — not last-touch credit assignment, which systematically undervalues
upper-funnel reach investment.

### View-Through Window Discipline

View-through attribution windows must be set before campaign launch and held
constant for the duration of the measurement period. Standard reference windows:

- **Display**: 1-day view-through for lower-funnel retargeting; 7-day view-through
  for prospecting.
- **Video (in-stream and pre-roll)**: 7-day view-through for completion-above-50%;
  1-day for below-50% completion.
- **CTV**: 14-day view-through; CTV operates at longer consideration cycles and
  has no click-through signal.

View-through windows longer than 30 days are not acceptable without documented
incrementality evidence. Long windows inflate attributed conversions from
organic and search-driven demand.

### Lift Studies

Lift studies are the minimum acceptable measurement standard for prospecting and
brand campaigns. Geo-matched holdout or user-level holdout (where consent and
volume permit) must be run for any campaign above $20,000 monthly investment.
Last-click CPA as primary KPI for display is a methodology failure — it measures
the existence of a cookie, not the contribution of an impression.

### Incrementality Testing Protocol

1. Define the hypothesis: the treated population will convert at a higher rate
   than the holdout, with statistical significance at alpha = 0.05.
2. Randomise holdout at the geo or user-hash level before campaign launch.
   Post-hoc holdout construction invalidates the test.
3. Run for minimum 14 days or until 1,000 conversions in the treated group,
   whichever is longer.
4. Report incremental ROAS (iROAS), not total ROAS. Total ROAS credits all
   conversions in the treated population; iROAS credits only conversions above
   the holdout baseline.
5. Archive test parameters, population sizes, and holdout methodology alongside
   campaign post-analysis. Reproducibility is a requirement.

---

## Anti-Patterns

| Anti-Pattern | Category | Consequence |
|---|---|---|
| Accepting blind supply path — no ads.txt declaration, no sellers.json resolution | Supply quality | IVT exposure; domain spoofing; brand-safety void; no recourse for post-campaign fraud claims |
| Activating brand-safety segment post-launch "once scale is confirmed" | Brand safety | Brand-unsafe impressions served during the activation gap; post-launch activation does not retroactively clean reported data |
| Using only GIVT filter with no SIVT detection | IVT detection | SIVT (sophisticated bots, hidden ads, adware) passes undetected; inflated reach metrics; no accurate performance baseline |
| Using a static six-month-old blocklist as primary brand-safety control | Brand safety | New unsafe inventory not in the blocklist runs unchecked; blocklist is a lagging indicator, not a prevention mechanism |
| Claiming audience reach from third-party behavioral segments without consent chain documentation | Data compliance | LGPD/GDPR/CCPA violation exposure; segment may be deactivated mid-campaign by DSP compliance enforcement |
| Changing view-through attribution windows mid-flight to improve reported ROAS | Attribution | Invalidates lift comparison; produces non-comparable pre/post data; misleads optimisation decisions |
| Accepting PMP price floors more than 2× open-auction CPM without documented justification | Deal economics | Overpaying for inventory with no verified exclusivity or quality premium; spend efficiency erosion |
| Reporting total ROAS for display campaigns as the primary success metric | Measurement | Attributes organic and search-assisted conversions to display; overestimates display contribution; under-reports true CPL |
| Launching cookieless migration by direct substitution of cookie segments with UID2 or Topics without reach-reduction modelling | Cookieless planning | 30–60% reach gap appears mid-campaign; budget pacing fails; false "cookieless parity" claim to stakeholders |

---

## Cross-References

- `domains/paid-media/skills/ppc-strategist` — paid search buying discipline;
  cross-channel attribution reconciliation between search and display requires
  shared attribution framework and agreed view-through/click-through windows.
- `domains/paid-media/skills/paid-social-strategist` — social inventory buying
  via Meta Advantage+ and LinkedIn Campaign Manager; audience overlap and
  frequency cap coordination across social and programmatic display.
- `domains/paid-media/skills/tracking-specialist` — tag management, server-side
  event collection, and consent platform integration; cookieless signal pipelines
  (UID2, RampID, CAPI) depend on tracking infrastructure defined in this skill.

---

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review) — programmatic
  campaign authoring (DSP setup, audience seeds, creative-brand-safety
  rules) is subject to two-pass adversarial review before launch.
- **ADR-060 amendment §Bulk creative-authoring path** — anchors this
  skill's tier assignment, scope_tags, and `inspired_by` relationship
  conventions.
