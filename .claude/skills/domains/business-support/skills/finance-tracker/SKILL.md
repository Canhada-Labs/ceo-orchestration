---
name: finance-tracker
description: |
  SMB and startup finance tracking — cash-flow projection, runway
  calculation, burn-rate diagnostics, founder-finance literacy, monthly
  close-light cadence, and founder-friendly tooling (Brex / Mercury /
  Stripe Atlas / Conta Azul / Omie). Distinct from
  `domains/finance-accounting/skills/bookkeeper-controller` (full-stack
  accounting) and `domains/finance-accounting/skills/fpa-analyst`
  (enterprise planning cycles) — this skill addresses founder-side
  financial awareness at the pre-scale stage. Use when: a founder or
  small-team operator needs runway visibility within one business day;
  when cash-flow forecasting is absent or spreadsheet-only; when burn
  decomposition by category has not been performed; when preparing the
  first investor board pack; or when selecting between SMB-oriented
  finance tools.
owner: Carla Tesouraria (Finance Tracker, domain persona)
tier: domain:business-support
scope_tags: [finance-tracking, runway, burn-rate, cash-flow, founder-finance, smb-finance]
inspired_by:
  - source: msitarzewski/agency-agents/support/support-finance-tracker.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: business-support
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
  - "**/finance/**"
  - "**/cashflow/**"
  - "**/runway/**"
  - "**/budget/**"
---

# Finance Tracker

Founder-side financial awareness is not accounting. The scope is
narrower and the cadence faster: know runway at any moment, know burn
by category, know which tool produces which number. Without this
baseline, every strategic decision rests on an unknown cash position.

## Cardinal Rule

A founder who does not know runway within one business day at any
moment has lost the company's primary survival metric. Runway is not a
quarterly deliverable — it is a standing obligation. Any state in which
the answer to "how many months of runway remain?" takes more than one
business day to produce is a governance failure, regardless of company
stage, team size, or fundraising status.

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- Runway is being calculated using gross revenue instead of net cash
  inflow, which inflates the apparent position and obscures deferred
  payment obligations.
- Cash on hand is being treated as equivalent to committed but
  uncollected revenue or an unsigned term sheet.
- Burn rate is expressed as a single total without category
  decomposition; a total without attribution cannot be managed.
- The 13-week rolling cash-flow forecast has not been updated in the
  current week. A stale forecast is not a forecast.
- Deferred revenue has been counted as available cash. Deferred
  revenue is a liability until the service obligation is fulfilled.
- A spreadsheet is the sole system of record for a company that has
  crossed $500K in annual recurring revenue or has more than three
  funding sources.

## When to Apply

Apply for founder-side and early-stage tasks requiring rapid,
high-confidence cash-position awareness:

- Calculating or auditing a runway figure and confirming the
  cash/net-burn/gross-burn inputs used.
- Building or reviewing a 13-week rolling cash-flow forecast.
- Decomposing monthly burn into category-level attribution (payroll,
  cloud, vendor contracts, marketing, other).
- Preparing a monthly finance summary readable by a non-accountant
  founder or a seed-stage investor.
- Selecting or configuring a finance tool for an SMB or early-stage
  startup (Brex, Mercury, Stripe Atlas, Conta Azul, Omie, Pleo).
- Preparing the finance section of a fundraise board pack.

Do not apply for full-period close, statutory reporting, tax
provision, or enterprise planning cycles — use `bookkeeper-controller`
or `fpa-analyst` respectively.

## Cash-Flow Projection Discipline

Three forecast horizons operate in parallel; collapsing them into one
is a reliability failure.

**13-week rolling forecast (weekly granularity).** Updated every week
without exception. Inflows and outflows are recorded, the horizon
extends by one week at the far end, and any week with actual cash
flow deviating more than 15% from the prior forecast requires a
root-cause note before the next update proceeds.

**90-day forecast (weekly granularity).** The fundraising and
decision horizon. Used when evaluating whether a new commitment can
be absorbed without a cash crisis in the quarter. Updated weekly as
part of the 13-week refresh.

**12-month forecast (monthly granularity).** The strategic horizon
for scenario planning and investor communication. Updated monthly.
Forecasts beyond 90 days carry explicit confidence bands; presenting
them as point estimates is misleading.

All three horizons must reconcile back to actual bank balances within
one business day. Forecasts that cannot are structurally broken.

## Runway Calculation

Runway is a quotient, not a heuristic. The denominator determines
whether the figure is meaningful.

**Cash.** Total cash and cash-equivalent balances, net of restricted
cash. Committed-but-uncollected receivables do not count until
collected.

**Net burn.** Cash spent minus cash received in a period, from
operations only. Net burn is the correct denominator for
revenue-generating companies. A company with $2M cash and $150K
monthly net burn has approximately 13 months of runway.

**Gross burn.** Total operating cash outflows before revenue.
Gross burn is the correct denominator for pre-revenue companies and
for stress-testing under a zero-revenue scenario. Confusing the two
when communicating runway to investors is a credibility error.

**Three scenarios** (conservative, base, aggressive) must accompany any
runway figure presented to a board or investor. Conservative assumes
net burn increases by 10-15% from the trailing three-month average.
Base holds net burn constant at trailing three-month average. Aggressive
assumes a revenue acceleration that reduces net burn by 15-20%.
Presenting a single-point runway figure without scenario bands is
optimism encoded as fact.

## Burn-Rate Diagnostics

Burn cannot be managed at the total level. Category-level attribution
is the minimum required resolution.

Mandatory burn categories:

- **Payroll and contractor.** Split between full-time employees and
  contractors. Track headcount and fully-loaded cost per head. Payroll
  is typically the largest burn category; it must be reviewed monthly
  for accuracy against payroll-system actuals.
- **Cloud infrastructure.** Monthly commitment versus actual usage.
  Track by provider. A cloud bill that grows faster than revenue is
  an architecture signal, not only a finance signal.
- **Vendor contracts.** Recurring SaaS subscriptions, professional
  services retainers, and annual contracts amortised monthly. Maintain
  a vendor register with renewal dates and cancellation windows.
- **Marketing and paid acquisition.** Separated from vendor contracts
  because its burn-to-output ratio (CAC, pipeline contribution) must
  be evaluated independently.

Trend-flag threshold: any category that increases more than 20%
month-over-month without documented justification triggers a
burn-diagnostic review before the next payment cycle closes.
Declining output ratios are flagged for renegotiation or spend
suspension within 30 days.

## Founder Finance Literacy

Founders operating without basic GAAP awareness make decisions that
produce surprises at audit or fundraise. The minimum literacy set:

**Revenue recognition basics.** Revenue is recognised when the
performance obligation is fulfilled, not when cash is received. A
12-month SaaS contract signed in month 1 recognises 1/12 of contract
value per month; the remaining 11/12 is deferred revenue — a balance-
sheet liability, not available cash.

**Deferred revenue trap.** Annual prepayments improve cash position but
create a service obligation. If the company ceases to operate before
fulfilling that obligation, the prepayment must be refunded. Deferred
revenue is a future liability that happens to reside in the bank today.

**Basic GAAP awareness.** Accrual accounting recognises revenue and
expenses when earned or incurred, not when cash moves. Cash-basis
thinking produces a systematically distorted view of profitability.

**Venture-debt covenant tracking.** Debt agreements typically include
financial maintenance covenants (minimum cash balance, revenue growth
thresholds). Covenant breaches can trigger immediate repayment. Track
compliance monthly and flag approaching thresholds to legal counsel at
least 60 days before the measurement date.

## Monthly Close-Light Cadence

Not a full accounting close. Purpose: produce a founder-readable
finance summary within three business days of month end, and ensure
the books are audit-ready by month three of a fundraise.

**Day 1.** Reconcile all bank and payment accounts to actual balances.
Confirm payroll actuals match payroll system. Flag any unreconciled
items above $1K for same-day resolution.

**Day 2.** Update the 13-week rolling forecast with the closed month's
actuals. Perform burn variance review: actual versus prior-month
forecast per category. Document any variance exceeding 10%.

**Day 3.** Produce the founder-readable monthly summary: cash position,
runway (three scenarios), burn by category with month-over-month delta,
and a one-paragraph narrative on any change requiring action. This
summary is the input to investor reporting.

**Fundraise-ready target.** By month three of any fundraise, the books
must support due-diligence access: reconciled actuals for the trailing
24 months, a cap table matching the equity register, all vendor
contracts with renewal and cancellation terms, and payroll records
segregated by employee and contractor.

## Tool Selection

No single tool fits all stages. Selection criteria: company size,
banking relationship, geography, and accounting integration needs.

**Brex.** Corporate card and cash management for US-incorporated
startups. Best fit when spend controls and accounting-platform
integration are required. Not suitable as a primary bank for
Brazilian-entity structures without a US co-entity.

**Mercury.** US banking for startups — API-accessible, no monthly
fees at seed stage. Best fit for US-incorporated companies; available
to foreign founders via a US entity.

**Stripe Atlas.** US company formation and banking bundle. Best fit
when payment processing is primarily in USD and the founder is forming
a US entity from outside the United States.

**Conta Azul.** Brazilian SMB accounting platform. Best fit for Ltda
or S.A. entities needing Nota Fiscal issuance, DAS (Simples Nacional),
and Receita Federal integrations.

**Omie.** Brazilian ERP for SMBs. Best fit for integrated CRM,
billing, and accounting within the Brazilian fiscal framework. Higher
implementation complexity than Conta Azul; justified at R$500K+ ARR.

**Pleo.** European employee spend management. Best fit for companies
with European entities requiring multi-currency expense management and
VAT reclaim.

**Never use a spreadsheet as the sole system of record** beyond the
pre-product stage. No access controls, no audit trail, no bank
reconciliation enforcement. Post-seed, spreadsheet-only finance is a
fundraise liability.

## Reporting to Investors

Board and investor reporting is a credibility transaction. A single
instance of stretched or sandbagged numbers alters the trust baseline
for all subsequent communications.

**Board-pack discipline.** Required contents: cash position as of the
reporting date; runway under three scenarios; burn by category with
month-over-month delta; actual revenue versus forecast with variance
narrative; any covenant or compliance item requiring board awareness.
Distribute at least 48 hours before the meeting.

**Never sandbag and never stretch.** Both degrade investor
relationships when discovered. Report actuals and best-estimate
forecasts. Variance narratives replace the need for pre-emptive
optimism.

**Honest variance.** When actuals deviate from the prior forecast by
more than 10%, the explanation must name the root cause. "Revenue came
in below plan" is not a variance explanation; "Enterprise deal slipped
to Q1 — customer procurement cycle; $120K ARR expected February close"
is.

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Spreadsheet-only finance post-traction | No audit trail, no access controls, no bank reconciliation enforcement; due-diligence exposure at fundraise |
| Founder cannot state runway within one business day | Primary survival metric is unmanaged; creates reactive rather than strategic cash decisions |
| Deferred revenue counted as available cash | Deferred revenue is a service obligation; counting it as a buffer overstates runway and leads to over-hiring |
| Gross burn confused with net burn in investor communication | Overstates or understates runway depending on direction; destroys credibility when the investor recalculates |
| Total burn reported without category decomposition | Unmanageable; no visibility into which category is driving the trend or which vendor can be renegotiated |
| Single-point runway figure presented without scenarios | Encodes optimism as fact; base-case accuracy is not the relevant question under stress |
| Venture-debt covenants not tracked monthly | Covenant breach triggers immediate repayment; 60-day notice window missed due to monthly-only review |

## Cross-References

- `domains/finance-accounting/skills/bookkeeper-controller` — full-stack
  accounting, month-end close, journal entries, statutory reporting; use
  when the company has reached a stage requiring formal accounting close
- `domains/finance-accounting/skills/fpa-analyst` — annual operating plan,
  rolling forecast, driver-based modelling, and capital-expenditure
  governance; use when the company has a dedicated FP&A function
- `domains/business-support/skills/analytics-reporter` — business
  intelligence and KPI reporting; complements finance-tracker when
  operational metrics must be correlated with cash-flow trends

## ADR Anchors

- ADR-058 — Brainstorm gate pre-Plan and two-pass adversarial review.
  All finance projections and runway figures must pass the two-pass
  review gate before presentation to investors or board. The first pass
  checks arithmetic and source reconciliation; the second pass applies
  adversarial framing to surface optimism bias in revenue forecasts and
  understated expense assumptions.
