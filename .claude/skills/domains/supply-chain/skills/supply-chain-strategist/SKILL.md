---
name: supply-chain-strategist
description: Supply chain strategy across sourcing, supplier qualification, demand
  planning, inventory optimisation, S&OP, lead-time management, risk diversification,
  and ESG traceability compliance for {{PROJECT_NAME}}. Evaluates total-cost-of-ownership
  over unit price, applies statistical safety-stock formulas, and enforces multi-tier
  supplier discipline. Use when designing sourcing strategy, qualifying a new supplier,
  running S&OP, setting safety-stock targets, building a risk-diversification plan,
  or meeting forced-labor and Scope 3 compliance obligations.
owner: Supply Chain Strategist (domain persona)
tier: domain:supply-chain
scope_tags: [supply-chain, sourcing, demand-planning, inventory-optimization, sop, esg-compliance, traceability]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/supply-chain-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: supply-chain
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
  - "**/supply-chain/**"
  - "**/sourcing/**"
  - "**/suppliers/**"
  - "**/inventory/**"
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
excess inventory simultaneously across different SKUs.

## Inventory Optimisation

### ABC Analysis

Classify inventory by annual consumption value: A items (top 10%
of SKUs, ~70% of value), B items (next 20%, ~20% of value), C items
(remaining 70%, ~10% of value). Cycle count frequency, safety-stock
service levels, and supplier review cadence differ by class.
A items receive weekly cycle counts and 98%+ service levels; C items
receive monthly counts and 90% service levels unless criticality
overrides.

### EOQ and Reorder Point

Economic Order Quantity: EOQ = sqrt(2DS/H), where D = annual demand,
S = order cost, H = unit holding cost. EOQ minimises the sum of
ordering and carrying cost. Reorder Point: ROP = d_avg × LT_avg +
safety stock. Days-of-supply discipline: track inventory position
against target days-of-supply per SKU family and flag deviations
weekly.

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

## Cross-References

- `domains/fintech/skills/` — financial exposure modeling for
  commodity price and FX hedging inputs to TCO
- `core/architecture-decisions` — decision-record format for
  make-or-buy and nearshore/offshore structural choices
- `core/compliance-lgpd` — data handling obligations when supply
  chain data includes personal information (supplier contacts,
  audit respondents)

## ADR Anchors

ADR-058 governs the tier boundary between `core` and `domains`.
Supply-chain domain skills live in `domains/supply-chain/` and
must not import or depend on domain-specific constants from other
domain buckets. Cross-domain references are documentation links,
not code imports.
