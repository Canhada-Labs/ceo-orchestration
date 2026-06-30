---
name: customer-returns
description: >
  Governs retail and e-commerce returns operations: RMA workflow design, return reason
  taxonomy with root-cause analytics, restocking disposition decisions, refund / credit /
  exchange policy across payment channels, fraud detection covering wardrobing and
  serial-returner patterns using cross-account graph signals, and reverse logistics
  cost optimisation. Multi-jurisdiction consumer-rights awareness — US state-level, EU
  14-day withdrawal, UK Consumer Rights Act, BR Art. 49 CDC 7-day remoto — with
  verification-at-policy-time discipline. Use when designing or auditing a return
  programme, investigating an elevated return rate by SKU, structuring RMA authorisation
  rules, or responding to a consumer-rights dispute.
owner: Avery Strand (Customer Returns Coach, domain persona)
tier: domain:retail
scope_tags:
  - retail-returns
  - rma
  - reverse-logistics
  - fraud-detection
  - consumer-rights
  - restocking
inspired_by:
  - source: msitarzewski/agency-agents/specialized/retail-customer-returns.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: retail
priority: 8
risk_class: low
stack: []
context_budget_tokens: 400
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
  - "**/returns/**"
  - "**/rma/**"
  - "**/refunds/**"
  - "**/reverse-logistics/**"
---

# Customer Returns

## Cardinal Rule

A refund denied on a legitimate return is a one-time saving and a permanent
customer-acquisition cost. Return policy enforcement must be designed for the 95%
of honest customers, not calibrated primarily around the 5% who abuse it. Friction
that protects against marginal fraud at the cost of alienating compliant customers
destroys lifetime value at scale.

## Fail-Fast Rule

Do not design or operate a return programme without: (1) accurate reason-code capture
on every transaction, (2) a per-SKU return-rate threshold that triggers a product
review, and (3) written disposition rules for each merchandise grade. Absence of any
one of the three means return data cannot drive improvement and recovered value
systematically leaks to untracked shrink.

## When to Apply

- Designing or auditing RMA workflows for retail or e-commerce operations.
- Investigating a SKU or category with a return rate above category benchmark.
- Structuring fraud detection rules for wardrobing-prone segments (occasion apparel,
  high-value electronics).
- Responding to a consumer-rights dispute or regulatory enquiry under CDC, DCFR,
  or equivalent statute.
- Evaluating reverse logistics cost against return volume to determine carrier or
  aggregation model.
- Onboarding a new fulfilment channel where return routing has not been defined.

## RMA Workflow

**Initiation channel**
A return begins at exactly one authorisation point regardless of the sales channel
through which the original purchase occurred. For e-commerce, a self-serve portal
generating an RMA number with a pre-paid label is the minimum; phone and chat
initiation remain channels but must produce the same RMA record. For in-store,
the POS transaction creates the return record directly. Cross-channel parity — buy
online, return in store (BORIS) — requires the system to accept an order reference
lookup that does not depend on a printed receipt.

**Authorisation protocol**
Issue an RMA number before the customer ships anything. The number encodes: return
window eligibility (calculated from order date), declared reason code, and item
condition class (sealed / opened / defective / unknown). RMA numbers that expire
after 14 days reduce open-loop authorisations that never arrive.

**Return-window enforcement**
The advertised window (commonly 30, 60, or 90 days) is a contract with the customer.
Honour it consistently. Outside-window requests require a documented manager-level
exception with reason and approving identity recorded in the system — not discretionary
associate judgment. Seasonal extensions (e.g., holiday purchases returnable through
January) must be codified in policy and applied uniformly.

**Inspection criteria**
Every returned item is physically inspected before a refund is released. Inspection
confirms: item identity (SKU, serial number where applicable), completeness (original
accessories, packaging, documentation), condition grade (see Restocking Decision Tree),
and absence of fraud indicators. Uninspected returns processed on customer assertion
alone create uncontrolled shrink.

**Disposition decision**
Disposition follows inspection output. The decision is mechanical, not associate-level
judgment — a written disposition matrix by product category and condition grade
eliminates inconsistency. See Restocking Decision Tree.

## Return Reason Taxonomy

Reason codes are the primary data asset produced by the return programme. Inaccurate
or generic codes render analytics unusable. Each transaction carries exactly one
primary reason code selected from a controlled taxonomy; a free-text supplemental
field may expand context but does not substitute for the code.

**Defective / not working (P01)**
Item failed to perform its stated function within normal use conditions. Vendor
responsibility for defect claims; RMA to vendor separate from customer refund.
Defect codes subdivided by failure mode if volume warrants it.

**Wrong item sent (P02)**
Fulfilment or picking error. Carrier and warehouse accountability metrics draw
from this code; conflation with customer-ordered-wrong suppresses operational
visibility.

**Size or fit mismatch (P03)**
Dominant reason in apparel and footwear. High rates for a specific SKU indicate a
sizing label error or product-page description deficiency, not customer error.

**Changed mind (P04)**
No product or fulfilment deficiency. Decision-reversal returns carry no vendor
recovery path and represent the category most eligible for returnless-refund
analysis where item value is below return-shipping cost.

**Arrived late / missed occasion (P05)**
Logistics or carrier failure. Carrier SLA performance is measured against this code;
root cause is distinct from a product issue.

**Never received (P06)**
Carrier loss or theft-in-transit. Carrier claim process, not return disposition.
Conflation with returns understates carrier loss rates and inflates return-rate
metrics.

**Product-level return-rate flag**
Any SKU exceeding a category-specific threshold (examples: apparel 25%, electronics
12%, home goods 15%) triggers a product review. The review identifies whether the
root cause is a description defect, a quality defect, a sizing or specification
error, or a fulfilment error. A return rate is a symptom; the review identifies
the cause.

## Restocking Decision Tree

Disposition converts returned merchandise into one of five outcomes. The decision
uses condition grade as the primary input and category policy as the secondary input.

**Resaleable as new**
Condition: sealed original packaging, no evidence of use, all components present.
Action: return to primary stock at full price. Applicable to categories where customer
expectation permits it; excluded by policy for personal-care and hygiene categories
regardless of apparent condition.

**B-stock / open box**
Condition: opened packaging, item functional and complete, no physical damage. Action:
sell at B-stock price point with disclosed condition label. Electronics and appliances
are the primary category. B-stock price recovery is typically 60-80% of new retail
depending on category and brand.

**Refurbish**
Condition: minor cosmetic damage or missing non-essential accessories; item requires
cleaning, repackaging, or minor repair. Action: route to refurbishment queue. Cost of
refurbishment must be tested against B-stock price vs. liquidation price quarterly.

**Liquidate**
Condition: functional but unresaleable in current channel (damaged packaging,
incomplete, out-of-season). Action: bulk lot to secondary market or liquidator.
Recovery is typically 5-20% of cost; recording liquidation value is required for
accurate loss accounting.

**Scrap**
Condition: non-functional, safety risk, or hygiene category returned opened. Action:
destroy with documented chain of custody. Hazardous materials (batteries, chemicals)
require regulated disposal; the disposal method and cost are recorded separately
from merchandise value.

**Per-category protocol**
High-fraud-risk categories (electronics, jewellery, high-value apparel) have a hold
step before disposition: items are held pending loss-prevention review for a defined
period (24-48 hours) when fraud indicators are present.

## Refund / Credit / Exchange Policy

**Per-channel original-payment-method default**
Refunds return to the original payment method as the default. Credit card refunds
post in 3-5 business days; the customer must be informed of this timeline at the
point of processing. A cancelled or expired card requires a store-credit or check
alternative with manager approval. Cash purchases refunded in cash up to a defined
threshold; above that threshold, manager approval and ID documentation are required.
Gift card purchases refund to a new gift card; cash substitution for gift card
refunds is prohibited without documented exception.

**Store-credit incentive math**
Store credit is the appropriate primary instrument when: the return is outside
the standard window but within an exception window, the customer has no receipt,
or the item is a gift return without gift receipt. Many retailers offer a modest
incentive (5-10% uplift on refund value) to convert return refunds to store credit,
capturing revenue that would otherwise leave the business. The uplift must exceed
the average margin impact of the retained sale to be economically rational.

**Exchange friction reduction**
An exchange processed as a return plus a new purchase at the point of return is
the operationally correct model. It prevents phantom inventory, ensures accurate
reason-code capture, and creates a full transaction record. Simplifying the
exchange experience for the customer is a service layer goal, not a reason to
collapse the two distinct transactions in the system.

## Fraud Detection

**Wardrobing — buy-wear-return**
The defining indicators are: item returned after a weekend or event window, visible
wear, laundering smell, price tags reattached (verify tag attachment method vs.
original), and return timing clustered around occasions. Highest-risk categories:
formal and occasion apparel, outerwear, high-value footwear.
Detection: return timing pattern (purchase date → event date → return date), item
condition inspection, and return-frequency threshold by customer and SKU.

**Empty-box scam**
Item never in the box, or a lower-value substitute placed inside. Detection: weight
verification at receiving against declared product weight, box seal integrity
inspection, and photo documentation before opening high-value returns.

**Serial-returner pattern**
A customer whose return rate across transactions exceeds a defined threshold (e.g.,
40% of purchases returned within 90 days, or more than five returns per rolling
90-day window) is a policy-abuse signal. Cross-account graph analytics detect
customers operating multiple accounts to reset per-account thresholds.

**Cross-account graph analytics**
Shared address, shared payment instrument, or shared device fingerprint across
accounts with independent high-return rates is a structural fraud indicator.
Graph-based identity resolution is required to detect this pattern; single-account
return thresholds do not.

**Never accuse without evidence**
A fraud indicator is an internal escalation trigger, not a customer communication.
Suspected fraud routes to loss prevention via manager. The associate does not
communicate suspicion, deny the return on fraud grounds without manager direction,
or confront the customer. Associate-level fraud enforcement without loss-prevention
involvement creates legal exposure and customer harm.

## Reverse Logistics

**Return-shipping cost mapping**
Return shipping cost is a direct charge against the margin of the returned transaction.
For high-volume e-commerce programmes, carrier rate benchmarking, pre-negotiated
return labels, and customer-drop aggregation points (retail partner, parcel locker
network) each reduce per-unit cost. The decision between pre-paid label (cost absorbed
by retailer) and customer-paid label is a policy decision with direct impact on return
rate; frictionless returns demonstrably increase return volume.

**Aggregation point vs. direct return**
Items with low unit value relative to return shipping cost are candidates for
returnless refunds — issue refund without requiring physical return. The economic
threshold is: return shipping + handling + inspection cost > expected recovered value.
The economic threshold for a returnless-refund decision:

```
returnless_eligible = (return_shipping + handling + inspection_cost) > expected_recovered_value

expected_recovered_value = unit_cost × disposition_recovery_rate
  # resaleable-as-new: 1.00 × unit_cost
  # b-stock:           0.65 × unit_cost  (category-specific; recalibrate quarterly)
  # liquidate:         0.10 × unit_cost
  # scrap:             0.00
```

Returnless refund decisions are recorded with rationale for inventory accuracy.

High-value and high-fraud-risk items route directly back to a primary distribution
or inspection centre, not to store stock, to ensure condition verification by trained
personnel.

**Environmental and cost optimisation**
Consolidating return shipments at regional aggregation points before forwarding to
processing reduces carrier cost and carbon intensity per unit. Packaging re-use
programmes for B-stock processing reduce secondary packaging cost. Both are
measurable and should be included in returns programme reporting.

## Consumer-Rights Compliance

Consumer-rights statutes set a floor that return policy cannot undercut. Verify
the applicable statute at policy design time; the entries below are orientation
points, not legal advice.

**US (state-level)**
No uniform federal consumer-returns statute. California, New York, and other states
mandate disclosure of a no-return or all-sales-final policy at the point of sale;
failure to disclose creates an implied right of return. Specific categories (defective
goods) carry implied warranty protections under UCC Article 2 regardless of posted policy.

**EU — DCFR / Consumer Rights Directive**
Directive 2011/83/EU establishes a 14-day right of withdrawal for distance contracts
(online and phone purchases) with no reason required. Seller bears return shipping cost
if the seller did not clearly disclose that the consumer bears it. Defective goods rights
are governed by Directive 2019/771 (2-year minimum conformity guarantee). Verify per
Member State for implementing legislation.

**UK — Consumer Rights Act 2015**
30-day right to reject for goods that are faulty, not as described, or unfit for purpose.
Digital content and services have separate provisions under the same Act. Post-Brexit,
DCFR withdrawal rights no longer apply; UK-specific right of withdrawal applies under
Consumer Contracts Regulations 2013 (14 days for distance contracts).

**BR — Art. 49 CDC (Lei 8.078/1990)**
Consumercontracted remotely (phone, internet) carries a 7-day right of withdrawal from
delivery, no reason required, with full refund including original shipping cost. Defective
products carry a separate repair / replacement / refund escalation path under Art. 26
and Art. 18 CDC. PROCON enforcement is significant for repeated violations.

**Verify per-jurisdiction at policy time**
Statutes change; the entries above reflect the framework as of the authored date.
Obtain legal review before publishing a return policy for any jurisdiction where
the business has material consumer exposure.

## Anti-patterns

| Anti-pattern | Why It Fails |
|---|---|
| Blanket-deny policy for opened items without inspection | Closes legitimate defect returns; violates statutory warranty floors in most jurisdictions |
| Hostile RMA flow (multiple forms, manual approval queues, no status visibility) | Increases customer effort; converts policy-compliant returners into detractors and complaint escalations |
| Charging restocking fee on defective items | Customer bears cost of merchant or vendor error; legally prohibited under most consumer-rights frameworks for defective goods |
| Fraud-flag without documented evidence | Exposes business to discrimination and defamation claims; destroys customer relationship without recoverable upside |
| Opaque refund timing ("credit will appear eventually") | Creates CSAT failure and payment-dispute chargebacks; state the specific business-day window at every refund issuance |
| Reason-code accuracy not enforced | Analytics become unusable; product quality and fulfilment defects remain invisible until they compound |
| Returnless-refund decisions unrecorded | Inventory system overstates on-hand; downstream replenishment over-orders; cost is invisible to category P&L |
| Single per-account fraud threshold with no cross-account graph | Serial returners operating multiple accounts evade detection until losses are significant |

## Cross-References

- `domains/hospitality/skills/guest-services` — service recovery and escalation principles
  applicable to in-store return disputes and manager escalation protocol.
- `core/compliance-lgpd` — data handling requirements for customer return history and
  cross-account identity resolution under LGPD and GDPR; applicable when return fraud
  detection stores customer behavioural data.
- `core/code-review-checklist` — ADR-058 two-pass discipline (inspect before deciding)
  mirrors the returns workflow: physical inspection is pass one; disposition decision is
  pass two. Collapsing both into a single associate motion is the primary source of
  incorrect dispositions.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review): the mandatory inspection-before-refund
  rule is the operational form of two-pass discipline applied to physical goods. The inspection
  step is pass one (observe without deciding); the disposition step is pass two (decide with
  full information). Associates who skip inspection and process on customer assertion collapse
  both passes, producing the same class of error as reviewers who evaluate and generate
  simultaneously.
