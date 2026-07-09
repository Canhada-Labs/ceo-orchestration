---
name: supply-chain-strategist
description: Supply chain strategy across sourcing, supplier qualification, demand
  planning, inventory optimisation, S&OP, lead-time management, freight and carrier
  strategy, customs and trade compliance, logistics exception and claims management,
  risk diversification, and ESG traceability compliance for {{PROJECT_NAME}}.
  Evaluates total-cost-of-ownership over unit price, applies statistical
  safety-stock and forecast-accuracy discipline, decomposes freight rates,
  classifies goods under the tariff GRI order, and enforces multi-tier supplier
  discipline. Use when designing sourcing strategy, qualifying a new supplier,
  running S&OP, setting safety-stock or forecast-method targets, building a carrier
  portfolio or freight RFP, classifying goods or evaluating FTA/duty savings,
  resolving a freight claim, building a risk-diversification plan, or meeting
  forced-labor and Scope 3 compliance obligations.
owner: Supply Chain Strategist (domain persona)
tier: domain:supply-chain
scope_tags: [supply-chain, sourcing, demand-planning, inventory-optimization, sop, esg-compliance, traceability, freight, carrier-management, customs, trade-compliance, tariff-classification, incoterms, duty-optimization, freight-claims, exception-management]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/supply-chain-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
  - source: affaan-m/ecc/skills/carrier-relationship-management/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/customs-trade-compliance/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/logistics-exception-management/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/inventory-demand-planning/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: supply-chain
priority: 8
risk_class: low
stack: []
context_budget_tokens: 1100
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
  - "**/supply-chain/**"
  - "**/sourcing/**"
  - "**/suppliers/**"
  - "**/inventory/**"
  - "**/freight/**"
  - "**/customs/**"
source: affaan-m/ecc@81af4076 skills/carrier-relationship-management/ + skills/customs-trade-compliance/ + skills/logistics-exception-management/ + skills/inventory-demand-planning/
license: MIT
---

# Supply Chain Strategist

## Cardinal Rule

Total-cost-of-ownership is the only valid decision basis.
Unit price is an input, not an output. Every sourcing decision,
supplier selection, and inventory parameter must be expressed in
TCO terms: purchase price, freight, duty, incoming inspection,
quality-loss cost, inventory carrying cost, expedite risk premium,
and supplier switching cost. Decisions made on unit price alone
create a predictable failure mode — lowest-bidder awards that
destroy margin through downstream quality and availability failures.

## Fail-Fast Rule

Stop and escalate when any of the following conditions are true:

- A single supplier accounts for more than 30% of spend in a
  critical category with no qualified alternative.
- A new supplier is being onboarded by skipping capability audit
  or pilot production to meet a delivery deadline.
- Safety-stock parameters have not been recalculated after a
  demand-pattern or lead-time change.
- An ESG or forced-labor compliance audit finding is being closed
  with a supplier's self-attestation rather than independent
  verification.
- The S&OP process is producing two sets of numbers — one for
  planning and one for finance.
- A carrier with revoked operating authority, lapsed insurance, or
  an Unsatisfactory safety rating is still receiving tenders.
- A restricted-party (denied-party or sanctions) screening hit is
  being cleared, or the transaction released, without a documented
  adjudication rationale.
- A freight claim is approaching its statutory filing window — nine
  months for US domestic surface under the Carmack Amendment — with
  no claim filed.
- Goods are being entered under a tariff classification derived from
  a product name or a supplier's assertion rather than a documented
  General Rules of Interpretation analysis.

Each condition represents a structural risk that coaching or
workarounds cannot resolve. Escalate before the next procurement
decision that depends on the deficient area.

## When to Apply

Apply this skill when:

- Designing or reviewing category-level sourcing strategy.
- Qualifying a new supplier (initial or re-qualification cycle).
- Setting or recalibrating safety-stock and reorder-point parameters.
- Running or restructuring the monthly S&OP cycle.
- Building a supply-chain risk map or risk-diversification plan.
- Responding to a supply disruption or shortage event.
- Assessing ESG posture, Scope 3 carbon data, or forced-labor
  compliance obligations (UK MSA, Lieferkettengesetz, US UFLPA).
- Evaluating nearshore vs offshore trade-offs for a category.
- Designing an alternative-BOM or dual-source activation trigger.
- Building or running a freight RFP, a carrier scorecard review, or
  a routing-guide refresh.
- Vetting a carrier's operating authority, insurance, and safety
  rating before its first tender.
- Classifying goods under HS/HTS, evaluating FTA or duty-optimization
  savings, or screening a counterparty against denied-party lists.
- Resolving a freight exception, a damage or shortage claim, or a
  carrier liability dispute.

## Sourcing Strategy

### Single vs Dual vs Multi-Source

Single-source is only acceptable when a commodity is non-critical,
fully substitutable, and the supplier has no spend concentration
above 10%. Strategic and bottleneck categories require a minimum of
two qualified suppliers; critical-path materials require three.
Volume allocation discipline: primary 60–70%, secondary 20–30%,
development pipeline 5–10%. Adjust quarterly based on performance
data, not relationship tenure.

### Total-Cost-of-Ownership

TCO components: unit purchase price, tooling and mold amortisation,
packaging, inbound freight and duty, incoming inspection cost,
quality-loss yield adjustment, inventory carrying cost at the
applicable rate, expedite premium modeled at historical frequency,
and supplier switching cost. Hidden costs — coordination overhead,
compliance audit burden, IP protection risk — are estimated and
included even when imprecise. A 5% higher unit price with a 0.1%
defect rate consistently outperforms a 5% lower price with a 1.5%
defect rate when carrying cost and quality-loss are modeled.

### Nearshore vs Offshore Trade-off

Offshore sourcing carries: longer lead times and higher lead-time
variability, larger minimum order quantities, higher safety-stock
requirements, greater geopolitical exposure, and Scope 3 freight
emissions. Nearshore or domestic sourcing carries: higher unit price,
lower total landed cost in many demand-volatility scenarios, shorter
cycle times, and reduced inventory burden. The decision must be
modeled per SKU or category using lead-time-adjusted TCO, not
blanket policy. Geopolitical risk discount is applied as a
probability-weighted cost of disruption per category.

## Supplier Qualification

Qualification is a gate process, not a formality. A supplier is
qualified when all five dimensions are verified:

1. **Capability audit** — production process, equipment state,
   quality system (ISO 9001 or sector equivalent), capacity
   headroom above 20% for surge absorption.
2. **Quality system** — documented IQC/IPQC/OQC procedures, AQL
   sampling plan per ISO 2859-1, closed-loop CAPA process,
   historical defect data for a minimum of six months.
3. **Financial health** — credit profile, payment behavior, revenue
   concentration risk. A supplier deriving more than 40% of revenue
   from one customer is a concentration risk regardless of their
   quality score.
4. **ESG posture** — labor practice compliance, environmental
   management system, conflict-minerals due diligence where
   applicable, Scope 1/2 emissions baseline.
5. **Capacity headroom** — confirmed available capacity above
   projected peak demand, with evidence, not assertion.

Qualification never completes on a single on-site visit. Pilot
production runs of at least one production batch are mandatory
before volume supply authorization.

## Demand Planning

### Statistical Forecasting

Forecast method selection follows demand pattern classification:
stationary demand uses simple exponential smoothing; trended demand
uses Holt's method; seasonal demand uses Holt-Winters. Forecast
accuracy is measured as Mean Absolute Percentage Error (MAPE)
per SKU family, reviewed monthly. Bias is tracked separately from
accuracy — a consistently low-biased forecast is structurally
different from a high-variance unbiased forecast and requires
different correction.

### Forecast Accuracy and Method Selection

Method follows the demand pattern, and the pattern is measured, not
assumed. Stable low-variability demand uses a short weighted moving
average or single exponential smoothing; trended demand uses Holt's
method; seasonal demand uses Holt-Winters. Intermittent demand —
more than roughly 30% zero-demand periods — breaks normal-distribution
methods entirely and requires Croston's method or the Syntetos-Boylan
approximation, with a bootstrapped demand distribution for its buffer
rather than an analytical formula. A new SKU with no history is
forecast from an analog profile — the three-to-five most similar
items at the same lifecycle stage — with a 20–30% buffer that tapers
as its own history accumulates.

Accuracy is read on three instruments, not one. MAPE inflates on
low-volume items because near-zero actuals sit in the denominator;
weighted MAPE (sum of absolute errors over sum of actuals) becomes
the headline number, because it is the dollar-weighted figure finance
recognises. Bias — the average signed error — is tracked apart from
accuracy: a persistent bias is a structural model defect, not noise,
once it exceeds about ±10% for several consecutive cycles, and it
drives overstock (positive bias) or stockout (negative bias)
predictably. A tracking signal — cumulative error over mean absolute
deviation — beyond ±4 is the trigger to re-parameterise or switch
methods; the model has drifted and will keep drifting silently until
it is re-selected.

### Promotional and Event Demand

Promotions distort the baseline and are modeled as a separate layer,
never blended into history. Strip promotional volume out before
fitting the baseline, then apply a multiplicative lift layer during
promo weeks. Lift magnitude scales with promo mechanics: a temporary
price reduction alone moves demand modestly; price reduction plus
display plus feature moves it far more; a loss-leader event moves it
several-fold. Three failure modes recur and each produces excess
inventory or stockout — ignoring cannibalization (a promoted SKU
draws 10–30% of a close substitute's volume), ignoring the forward
buy (customers stockpile during deep promotions on shelf-stable
goods), and ignoring the post-promo dip (below-baseline demand for
one to three weeks afterward, concentrated in the first week). A
promotional forecast that omits the dip creates markdowns as reliably
as a gut-feel forecast accumulates bias.

### Collaborative S&OP

S&OP is a monthly cross-functional process: demand review
(commercial input), supply review (capacity and procurement
constraint), pre-S&OP reconciliation, and executive S&OP sign-off.
Output is a single consensus number used by both planning and finance.
Parallel planning and finance numbers are a governance failure, not
a coordination problem.

### Safety-Stock Formula

Safety stock = Z × σ_dLT, where Z is the service-level z-score
(e.g., 1.645 for 95%), and σ_dLT is the standard deviation of
demand during lead time. When lead-time variability is significant,
σ_dLT is computed as:

    σ_dLT = sqrt(LT_avg × σ_d² + d_avg² × σ_LT²)

Parameters are recalculated when demand MAPE changes by more than
five percentage points or when lead time changes by more than 20%.
Setting safety stock by gut feel or by rounding to a round number
without formula backing is a root cause of both stockouts and
excess inventory simultaneously across different SKUs. Lead-time
variability deserves specific attention: a supplier whose lead time
has a coefficient of variation above roughly 0.3 can require safety
stock 40–60% higher than a demand-variability-only formula suggests,
because the variance term for lead time dominates.

## Inventory Optimisation

### ABC Analysis

Classify inventory by annual consumption value: A items (top 10%
of SKUs, ~70% of value), B items (next 20%, ~20% of value), C items
(remaining 70%, ~10% of value). Cycle count frequency, safety-stock
service levels, and supplier review cadence differ by class.
A items receive weekly cycle counts and 98%+ service levels; C items
receive monthly counts and 90% service levels unless criticality
overrides.

### XYZ Predictability and the Policy Matrix

ABC value classification answers "how much does this item matter";
it does not answer "how predictable is it," and inventory policy
needs both. Overlay an XYZ axis for demand predictability, measured
as the coefficient of variation on de-seasonalised, de-promoted
demand: X is highly predictable (CV below ~0.5), Y moderate
(0.5–1.0), Z erratic (above 1.0). The two axes produce a policy
matrix that drives cadence and review effort. AX items — high value,
predictable — run automated replenishment on tight safety stock.
AZ items — high value, erratic — get human review every cycle and
are backstopped by expediting capability rather than the
astronomically expensive safety stock a high service level would
demand. CX items run automated replenishment on generous review
periods. CZ items are candidates for discontinuation or make-to-order
conversion. Classifying on the value axis alone over-invests safety
stock in high-revenue low-margin erratic items — the exact SKUs where
a high service level is least affordable. Classify value on margin
contribution, not revenue, for the same reason.

### EOQ and Reorder Point

Economic Order Quantity: EOQ = sqrt(2DS/H), where D = annual demand,
S = order cost, H = unit holding cost. EOQ minimises the sum of
ordering and carrying cost. Reorder Point: ROP = d_avg × LT_avg +
safety stock. Days-of-supply discipline: track inventory position
against target days-of-supply per SKU family and flag deviations
weekly.

### Inventory Position and Order-Quantity Reconciliation

Reorder decisions run on inventory position, never on on-hand alone:
inventory position = on-hand + on-order − backorders − committed
(quantity already allocated to open orders). Reordering against
on-hand double-orders every SKU that has a purchase order in transit.
Two reconciliations then govern the order quantity itself. First, a
theoretically optimal EOQ is meaningless against the unit a vendor
actually ships — an EOQ of 847 rounds to the nearest case, layer, or
pallet tier, and a vendor minimum-order-quantity above the EOQ forces
an explicit choice between accepting weeks of excess or consolidating
other items from the same vendor to clear the minimum. Second,
phantom inventory — a system count that overstates the physical
count — silently corrupts every downstream reorder and forecast; the
signature is a stockout on an item the system said had cover, and the
response is a cycle count triggered by that signature, not by the
calendar.

### Cycle Stock vs Safety Stock vs Anticipation

Cycle stock is the working inventory consumed between replenishment
cycles. Safety stock is the buffer against demand and supply
variability. Anticipation inventory is pre-built stock for planned
demand spikes (seasonal ramp, promotional event, capacity shutdown).
Each type has a different cost driver and a different management
lever. Treating all excess inventory as a single category prevents
correct root-cause action.

## S&OP Discipline

The S&OP cycle runs on a fixed monthly cadence with four mandatory
gates: demand review, supply review, pre-S&OP financial
reconciliation, and executive S&OP. Each gate has a defined input
set, a decision authority, and an output document. The consensus
forecast produced at executive S&OP is the single operating number
for the following 13-week rolling horizon. Two sets of numbers —
planning forecast and finance forecast — indicate that the process
is advisory rather than authoritative and must be corrected before
the next cycle. S&OP that does not change a resource decision at
least once per quarter is not functioning as designed.

## Lead-Time Management

Total lead time is the sum of manufacturing lead time, transit
time, customs clearance, and dock-to-stock processing. Each leg
is tracked separately because variability sources differ: supplier
production scheduling (manufacturing), carrier capacity and routing
(transit), broker efficiency and compliance completeness (customs),
internal receiving throughput (dock-to-stock). Safety-stock
parameters absorb lead-time variability; reducing lead-time
variability reduces required safety stock independently of mean
lead time.

Expedite cost vs delay cost trade-off: expedite cost (premium
freight, overtime) is quantified per instance and benchmarked
against delay cost (line stoppage, lost sales, contractual
penalties). Chronic expediting signals a systemic lead-time or
safety-stock parameter error, not a logistics problem.

## Freight and Carrier Strategy

Transit is one of the four lead-time legs, and the carrier portfolio
that moves it is managed as a risk-diversified investment, not a
procurement line item. Concentration buys pricing leverage;
diversification buys capacity security — and when the freight market
tightens, a carrier's willingness to cover a shipper's freight is set
by how that shipper treated it when capacity was loose.

### Rate Decomposition

A freight rate is never negotiated as a single number, because
bundling hides where the spend leaks. Decompose it into base linehaul
(benchmarked lane by lane against a market index — a carrier
competitive on one lane can run well over market on another), the
fuel-surcharge table (its base-price trigger, its increment, and its
index lag, not just today's percentage — a low linehaul paired with
an aggressive surcharge table can cost more than a higher linehaul on
a standard index), accessorials (detention beyond free time is the
single largest source of invoice dispute; liftgate, residential,
inside-delivery, and limited-access each priced explicitly), and the
per-shipment minimum on short-haul lanes. Modeling total cost across
a range of diesel prices, not linehaul alone, exposes an artificially
low base rate carrying an inflated surcharge.

### Contract vs Spot Mix

A healthy freight book runs roughly 75–85% contract and 15–25% spot.
Contract rates buy predictability and committed capacity; spot rates
run higher in tight markets and lower in soft ones. Spot exceeding
about 30% of a lane's budget is a signal that the routing guide is
failing — the contract rate has fallen below market and carriers are
pricing the shipper into the spot market by rejecting tenders.

### Carrier Scorecard

Measure the few metrics that get acted on, not the twenty that get
ignored. On-time delivery, measured at pickup and delivery separately
because a gap between them localises a terminal or linehaul problem
rather than a capacity one. Tender-acceptance rate, where acceptance
falling below market signals the rate is below market, and chronic
late pickup after acceptance is a soft rejection — the carrier is
holding the load while shopping it. Claims ratio as a fraction of
spend, with frequency tracked apart from severity, since many small
claims signal a systemic handling defect that one large claim does
not. Invoice accuracy, where chronic small overbilling is either
rate-testing or a broken billing system and either way costs audit
labor. Award decisions weight service history and capacity commitment
alongside cost — the lowest bidder with poor on-time and low tender
acceptance is more expensive than a slightly higher bid that actually
delivers.

### Compliance Vetting as a Qualification Gate

Carrier qualification is a gate, parallel to supplier qualification:
verify active operating authority, insurance at or above the
shipper's own floor (regulatory minimums do not cover a serious
accident), and a safety rating that is not Unsatisfactory — verified
at the source of record, not from a certificate the carrier supplies,
which can be stale or forged. For brokered freight, verify the surety
bond is active and contingent cargo cover exists, and treat a truck
that does not match the carrier named on the bill of lading as
suspected double-brokering — a broken insurance chain — and stop the
load. Routing guides run at least three carriers deep on any lane
with meaningful volume, and no single carrier holds more than about
40% of a critical lane. A carrier exits the routing guide only after
documented corrective action has failed: sustained low on-time or
tender acceptance, a claims ratio that will not come down, an
authority or insurance lapse, or evidence of financial distress.

## Risk Diversification

Risk diversification operates across four dimensions:

- **Geographic**: No single country supplies more than 50% of spend
  in a strategic category. Track tariff and export-control exposure
  per origin country.
- **Supplier**: Dual-source trigger fires automatically when a
  supplier's rolling 90-day on-time delivery drops below 85% or
  their financial-risk score crosses the medium threshold.
- **Modal**: Single-mode dependency on ocean freight for critical
  materials is a risk. Air freight contingency cost is modeled and
  pre-authorized for a defined list of SKUs.
- **Inventory positioning**: Safety stock for critical-path items
  may be positioned at a second geographic location to decouple
  from a single distribution point.

Alternative-BOM preparation is mandatory for any component with a
single qualified supplier. The alternative does not need to be
production-qualified but must reach a pre-qualified state — audit
complete, sample approval done — so that full qualification can
complete within a defined time window (target: 90 days from
trigger).

## ESG + Traceability

### Scope 3 Emissions

Supply-chain emissions (Scope 3 Category 1: purchased goods and
services) are calculated using spend-based or activity-based methods
per GHG Protocol. Suppliers in the top 20% of Scope 3 contribution
are required to provide primary emissions data. Annual reduction
targets are set at category level, tracked in S&OP, and reported
externally where required.

### Forced-Labor Compliance

Three jurisdictions require active due diligence:

- **UK Modern Slavery Act (MSA)**: Annual transparency statement
  and supply-chain risk assessment.
- **Lieferkettengesetz (German LkSG)**: Documented risk analysis,
  preventive measures, and remediation process for direct and
  indirect suppliers.
- **US Uyghur Forced Labor Prevention Act (UFLPA)**: Rebuttable
  presumption — goods sourced from or transiting a covered region
  are assumed to involve forced labor unless clear and convincing
  evidence to the contrary is provided.

Self-attestation is not acceptable evidence under any of the three
regimes. Compliance requires independent audit or certified
chain-of-custody documentation.

### Chain of Custody

Raw material traceability requires: documented sourcing origin at
the input material level, audit trail from raw material to finished
goods, and retention of evidence sufficient to respond to a customs
or regulatory inquiry within 72 hours. Conflict-minerals due
diligence (3TG: tin, tantalum, tungsten, gold) follows the OECD
Due Diligence Guidance and uses CMRT submission from tier-1
suppliers with pass-through obligations to sub-tier.

## Customs and Trade Compliance

Cross-border movement is lawful and cost-optimised or it is neither.
Customs clearance is one of the four lead-time legs, and its
variability is driven by classification accuracy and documentation
completeness — the levers the shipper controls.

### Tariff Classification

Goods are classified under the Harmonized System by applying the
General Rules of Interpretation in strict order, never from a product
name and never by the most expensive component. GRI 1 — the terms of
the headings plus the section and chapter notes — resolves the large
majority of cases and is exhausted before any later rule is invoked;
chapter notes override heading text. GRI 2 handles incomplete
articles and material mixtures. GRI 3 handles goods classifiable
under two or more headings: the most specific heading first, then
essential character for composite goods and retail sets, then the
last heading in numerical order as the tiebreak. GRI 6 applies the
same logic at the subheading level. A classification is defensible
only when its GRI path, the headings considered and rejected, and the
determining factor are documented — that record is the audit defence.
Existing binding rulings on the same or analogous goods are
persuasive and are checked before a novel determination is made.

### Incoterms and Valuation

Incoterms allocate cost, risk, and clearance responsibility between
buyer and seller, but they do not transfer title and they do not by
themselves set the customs value. Two traps recur: an Ex Works term
makes the buyer the exporter of record in the seller's country,
importing an export-compliance obligation it may be unequipped to
carry; and using FOB for containerised ocean freight mis-states the
risk-transfer point, where FCA is the correct term. Customs value
follows the importing regime's own rules regardless of the commercial
term — a valuation that includes or excludes international freight and
insurance incorrectly changes the duty even when the Incoterm is
clear. The valuation methods apply in hierarchical order: transaction
value first (the price paid or payable, adjusted for assists,
royalties, commissions, and packing), falling through to identical
goods, similar goods, deductive value, computed value, and a reasoned
fallback only when each prior method genuinely cannot be applied.

### Duty Optimization

Duty is a managed cost, not a fixed one. Preferential trade agreements
each carry product-specific rules of origin — tariff shift, a
regional-value-content threshold, or both — and qualification is
proven by tracing every non-originating input through the bill of
materials, then, where a choice of RVC method exists, selecting the
one that yields the higher content (the net-cost method often wins on
thin margins by excluding promotion, royalty, and shipping costs from
the denominator). Foreign-trade zones defer duty until goods enter
commerce and can invert the tariff to the finished-good rate when it
is lower than the component rates. Duty drawback refunds the bulk of
duty paid on imported inputs that are later exported, within the
statutory claim window. Temporary-import bonds and ATA carnets move
samples and professional equipment duty-free, provided the goods are
actually re-exported before the bond or carnet guarantee is called.

### Restricted-Party Screening

Every party to a cross-border transaction — buyer, seller, consignee,
end user, forwarder, bank, and intermediate consignee — is screened
against the consolidated denied-party and sanctions lists before
shipment. A screening hit is neither auto-cleared nor auto-blocked:
it is adjudicated on match quality (name similarity, address
correlation, country nexus, alias and, for individuals, date-of-birth
analysis), and the adjudication rationale and disposition are
documented and retained, because the regulator will ask. True
positives and genuinely ambiguous cases stop the transaction and
escalate to counsel; a transaction never proceeds while a hit is
unresolved. The list matters as much as the match — some list hits
admit a licence pathway and others are absolute prohibitions.

### Penalty Posture

The penalty framework scales with culpability — negligence, gross
negligence, fraud — and the single most powerful mitigation is a
prior disclosure filed before the authority opens its own
investigation, which caps exposure toward interest on the unpaid duty
for the negligence tier. Record retention over the statutory window
(five years for US entry records) is not clerical hygiene: failure to
produce records during an audit lets the authority reconstruct value
and classification unfavourably. Self-clearing a duty or
classification error through disclosure is consistently cheaper than
being found to have carried it.

## Logistics Exception and Claims Management

Exceptions are inevitable at volume; whether they cost money is a
function of taxonomy, deadline discipline, and knowing when to fight.
Every exception is first classified — delay, visible damage, concealed
damage, temperature excursion, shortage, overage, refusal,
misdelivery, full or partial loss, contamination — because the class
sets the resolution workflow, the evidence required, and the filing
window.

### Liability Regimes and Filing Windows

Carrier liability and its deadlines differ by mode, and a missed
window time-bars a claim regardless of merit. US domestic surface
runs under the Carmack Amendment: the carrier is liable for actual
loss with narrow exceptions, the shipper must prove clean tender,
damaged or short arrival, and quantum, and the claim is filed within
nine months of delivery (the carrier then has 30 days to acknowledge
and 120 to pay or decline, with two years from a decline to sue).
Concealed damage — not noted on the delivery receipt — carries a much
shorter industry-standard notice window (about five days) and shifts
the burden onto the shipper, so packaging-integrity evidence is
preserved from the moment it is found. Ocean freight limits liability
per package unless a higher value is declared; air freight runs under
a strict short-notice regime measured in days, not months. The
operational discipline that protects all of these is refusing to sign
a clean proof of delivery before count and condition are verified at
the tailgate.

### Fight or Absorb

Not every claim is worth filing. Below the internal cost of
processing a claim, and with a strong carrier relationship, the
exception is absorbed and logged to the carrier scorecard rather than
filed — chasing it is negative-ROI. In the middle band the standard
claims process runs without aggressive escalation. Above a material
threshold the full process runs with independent inspection, tighter
settlement floors, and legal review of any denial. Cutting across the
dollar bands is the pattern rule: a third-or-later exception from the
same carrier or lane inside a short window is a carrier-performance
problem to be escalated as such, whatever the individual amounts. As
with chronic expediting, chronic exceptions are a symptom of a
structural lead-time or handling defect, not a nuisance to be worked
case by case.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Lowest-bidder award without TCO | Downstream quality and availability costs invert the saving within two quarters on average |
| Single-source on critical material | Any disruption — financial, quality, geopolitical — has no buffer; recovery time exceeds customer tolerance |
| Safety-stock set by round-number intuition | Produces simultaneous stockouts on volatile SKUs and excess on stable ones; error compounds at each replenishment cycle |
| Ignoring lead-time variability | Mean lead time drives ROP but variability drives safety stock; modeling only mean leaves service level below target even when average is met |
| Visit-only supplier qualification | On-site visits are a social event without data; qualification requires process evidence, quality records, and pilot production output |
| ESG washing | Compliance attestations from the supplier being audited are not evidence; independent audit or chain-of-custody certification is the minimum standard |
| Gut-feel demand forecast | Bias accumulates invisibly; statistical baseline with collaborative override is the minimum; gut-feel-only forecasts cannot be debugged or improved |
| Negotiating freight as one bundled rate | Bundling hides which component — linehaul, fuel surcharge, or accessorial — is over market; the leak cannot be closed until the rate is decomposed |
| Awarding freight on linehaul alone | An aggressive fuel-surcharge table on a low base rate inflates total cost above market; only total cost across a diesel-price range exposes it |
| Spot freight run above ~30% of a lane | Signals a failing routing guide and a below-market contract rate, not a market condition; carriers are pricing the shipper into spot by rejecting tenders |
| Classifying goods from a product name | Skips the GRI order and the section/chapter notes; produces indefensible entries and penalty exposure on value and classification |
| Auto-clearing or auto-blocking a screening hit | Both bypass adjudication; the regulator asks for the documented match-quality rationale, and its absence is itself the finding |
| Signing a clean POD before counting | Waives the strongest visible-damage and shortage evidence and forces a concealed-damage claim on a shorter window with the burden reversed |
| Blending promotional volume into the baseline | Contaminates the forecast baseline and hides the post-promo dip; strip promo to a separate multiplicative layer |
| Reordering against on-hand instead of inventory position | Double-orders every SKU with a PO in transit; reorder on on-hand + on-order − backorders − committed |

## Cross-References

- `domains/fintech/skills/` — financial exposure modeling for
  commodity price and FX hedging inputs to TCO, and the duty and
  landed-cost inputs to duty-optimization decisions
- `core/architecture-decisions` — decision-record format for
  make-or-buy and nearshore/offshore structural choices
- `core/compliance-lgpd` — data handling obligations when supply
  chain data includes personal information (supplier contacts,
  audit respondents)
- `domains/legal/skills/` — contractual liability terms (force
  majeure, Incoterms incorporation, carrier limitation-of-liability)
  that govern freight claims and cross-border commercial terms

## ADR Anchors

ADR-058 governs the tier boundary between `core` and `domains`.
Supply-chain domain skills live in `domains/supply-chain/` and
must not import or depend on domain-specific constants from other
domain buckets. Cross-domain references are documentation links,
not code imports.

## Changelog

- **2026-07-07 — PLAN-153 Wave G merge (SP-033, clean-room ADAPT).** Enriched
  with operational teaching adapted from four upstream supply-chain
  skills. Added three sections — `## Freight and Carrier Strategy`,
  `## Customs and Trade Compliance`, and `## Logistics Exception and
  Claims Management` — and extended Demand Planning (forecast-accuracy
  instruments, method-by-pattern, promotional/event demand), Inventory
  Optimisation (XYZ policy matrix, inventory-position and MOQ/EOQ
  reconciliation), the Safety-Stock Formula (lead-time CV note), the
  Fail-Fast Rule, When to Apply, and the Anti-patterns table.
  Provenance recorded in `inspired_by` (four MIT entries, relationship
  `pattern_reference`). No new skill file — framework skill count
  unchanged. Soak: parallel-shadow (PLAN-153 OQ3=c).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=058eb9ae26baf7868bf81c1440f847fd8497cde83c417393231c5bdc5bb733cb
