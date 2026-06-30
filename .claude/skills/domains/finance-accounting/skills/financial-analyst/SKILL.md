---
name: financial-analyst
description: |
  Corporate FP&A and financial analyst discipline covering variance
  analysis, KPI dashboard architecture, business-unit P&L review,
  scenario modelling, capital-allocation evaluation, and board-pack
  preparation. Applies price / volume / mix decomposition, hurdle-rate
  discipline, and SOX-aligned reporting integrity to all analytical
  outputs. Distinct from `domains/fintech/skills/equity-research`
  (sell-side / public-markets focus). Use when: investigating actuals-
  vs-budget shortfalls and decomposing root causes; designing or auditing
  a financial KPI dashboard; reviewing business-unit P&L for allocation
  transparency; building multi-scenario financial models; evaluating
  capital projects with NPV / IRR / ROIC; or preparing board-ready
  financial packs with executive-summary clarity.
owner: Morgan Faria (Financial Analyst, domain persona)
tier: domain:finance-accounting
scope_tags: [fpa, financial-analysis, variance-analysis, scenario-modelling, capital-allocation, board-reporting]
inherits: [core/compliance-lgpd, core/pii-data-flow, core/consent-lifecycle, core/dpo-reporting]
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/finance/finance-financial-analyst.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: finance-accounting
priority: 5
risk_class: medium
stack: []
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/fpa/**"
  - "**/variance/**"
  - "**/kpi/**"
  - "**/scenarios/**"
---

# Financial Analyst

## Cardinal Rule

Assumptions precede conclusions; conclusions without assumptions are
assertions. Every analytical output produced under this skill must state
its input assumptions — data source, period, currency, consolidation
scope, and key driver values — before presenting any conclusion. Where
assumptions are uncertain or contested, the sensitivity of the conclusion
to each assumption is quantified. Precision without accuracy is noise:
four-decimal outputs on rough estimates misrepresent analytical confidence
and are prohibited. All outputs are subject to the two-pass review gate
(ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- The consolidation scope, reporting period, or base currency is
  undefined or ambiguous across entities.
- No single reconciled source of truth for actuals exists; multiple
  unreconciled versions of the same figure are present in scope.
- A forecast or model presents a single-point output with no scenario
  envelope and no sensitivity analysis.
- Variance analysis is requested but neither a budget line nor a prior
  comparable period is available as the reference point.
- Capital-project evaluation lacks either a stated hurdle rate or a
  documented basis for the discount rate applied.
- A board-pack draft contains figures that have not been reconciled to
  a signed-off close package or audited statement.

Never proceed on unreconciled inputs. "Latest management estimate" is not
a reconciled source; "ERP trial balance DD/MM/YYYY, signed off by
Controller, version final" is.

## When to Apply

Apply when: decomposing a budget-vs-actual shortfall by price / volume
/ mix; designing or auditing a financial KPI dashboard; reviewing
business-unit P&L for allocation transparency; building a multi-scenario
financial model; evaluating a capital project with NPV / IRR / ROIC; or
preparing a board pack.

Do not apply to sell-side equity research, public-market valuation, or
trading execution; route those to `domains/fintech/skills/equity-research`
or `domains/trading-hft/skills/order-routing`.

## Variance Analysis Discipline

Variance analysis produces explanations, not flags. A line item labelled
"unfavourable variance: $420k" with no further content is not analysis.

**Decomposition hierarchy:**

1. **Price variance** — the portion attributable to rate or price change
   holding volume constant at actual.
2. **Volume variance** — the portion attributable to quantity change
   holding price constant at budget.
3. **Mix variance** — the portion attributable to shifts in the
   composition of the volume (product, channel, geography, customer
   segment) relative to the budget mix assumption.
4. **Calendar / timing variance** — the portion attributable to
   recognised period shift with a documented reversal entry. This
   category is accepted only when a specific journal entry, invoice, or
   accrual is identified as the timing item. "Timing" without a specific
   entry is rejected as an explanation and reclassified as unexplained
   residual.

**Reference period discipline:**

- Every variance line is stated against a minimum of two reference
  points: budget/forecast AND prior-year equivalent period.
- Where the two references diverge materially, both are explained.
- Forecast-vs-actual comparisons use the most recent locked forecast,
  not the original budget, unless both are explicitly labelled.

**Flux explanation standard:**

- Flux explanation is required for any variance exceeding the lower of:
  (a) the materiality threshold defined in the reporting protocol, or
  (b) 5% of the relevant total.
- Flux explanation must identify the specific operational driver (unit
  sold, headcount change, rate change, one-time item) and the
  responsible business unit or cost centre.
- Explanations composed entirely of accounting movements (reclassification,
  accrual release) without identifying the underlying operational event
  are incomplete; the operational root cause must be appended.

## KPI Dashboard Architecture

A KPI dashboard is a decision-support instrument, not a data display.
Every KPI must be linked to a specific management decision it informs.

**Selection principles:**

- Per function or business unit, the dashboard contains 5–7 KPIs.
  More dilutes attention; fewer risks missing a material signal category.
- Each KPI is classified as **leading** (predictive) or **lagging**
  (confirmatory). A dashboard with only lagging KPIs is a rear-view
  mirror; at least two leading indicators are required per business unit.
- Each KPI has one designated source of truth — one system, one query,
  one extract schedule. Competing sources must be resolved before launch.

**Presentation discipline:**

- Every KPI is presented with a reference value, the current value, a
  directional indicator, and a context note for the most recent
  significant movement. A KPI without a reference value is incomplete.
- Trend sparklines accompany each KPI; a single data point with no
  trend is misleading for operating decisions.
- Refresh cadence is stated explicitly: daily, weekly, monthly, or
  ad-hoc — with the last-refreshed timestamp always visible.

## Business-Unit P&L Review

Business-unit P&L integrity requires transparency at three margin levels.

**Margin hierarchy:**

| Level | Definition | Minimum Disclosure |
|-------|------------|-------------------|
| Gross margin | Revenue minus direct COGS, before any allocation | Always |
| Contribution margin | Gross margin minus direct variable opex (sales commissions, variable fulfilment) | Required when business unit has material variable opex |
| Segment EBITDA | Contribution margin minus directly attributable fixed costs, before shared-service allocation | Required when business unit carries allocated overheads |

**Allocation methodology disclosure:**

- The allocation basis for every shared-service or overhead line must be
  stated in the P&L footnotes: headcount-based, revenue-based, usage-
  based, or negotiated fixed. Undisclosed allocations are treated as
  opaque and flagged for resolution.
- Year-over-year changes to allocation methodology are disclosed as a
  separate line or footnote. Silent methodology changes produce
  non-comparable period results and constitute a reporting-integrity
  violation (see §Reporting Integrity).
- Cross-unit subsidy detection: where a business unit's segment EBITDA
  is positive only because of a favourable allocation or inter-company
  transfer price, the pre-allocation result is disclosed alongside the
  post-allocation result.

## Scenario Modelling

A model with a single output is a point estimate, not a model. Scenario
discipline is mandatory for all forward-looking financial work.

**Required scenario set:**

| Scenario | Definition |
|----------|-----------|
| Base | Most likely outcome given current trajectory and management plan; assumptions documented as the probability-weighted central case |
| Upside | Outcome if identified positive drivers materialise at the optimistic end of their documented range; not a best-case fantasy |
| Downside | Outcome if identified risk factors materialise at the adverse end of their documented range; not a catastrophe scenario unless the business is genuinely stressed |
| Break-case | The minimum revenue or margin level at which the business unit or project remains viable given its fixed-cost structure and financing constraints |

**Assumption documentation standard:**

- Each scenario has its own independent assumption set, recorded in a
  dedicated input section of the model, not derived by applying a
  blanket percentage adjustment to the base.
- Key drivers are defined as those where a 10% change in the driver
  value produces a greater-than-5% change in the output metric. Key
  drivers are identified by sensitivity analysis before scenarios are
  finalised.
- Model documentation states: driver name, base-case value, upside
  value, downside value, source, and the last date the assumption was
  reviewed against actuals or market data.

**Sensitivity analysis:**

- A two-way sensitivity table is required for the two most impactful
  key drivers.
- Tornado charts are produced for models with more than four key drivers,
  ranking drivers by their absolute impact on the primary output metric.
- Conclusions that change sign (positive to negative, viable to non-
  viable) within the documented driver range are flagged explicitly as
  threshold-sensitive and require management sign-off before presentation.

## Capital Allocation Evaluation

Capital allocation decisions require a full return profile, not a single
preferred metric.

**Required metrics:**

| Metric | Application |
|--------|-------------|
| NPV | Primary viability test; the project creates value if and only if NPV > 0 at the stated hurdle rate |
| IRR | Efficiency metric; compared to hurdle rate and to alternative uses of capital |
| Payback period | Liquidity-risk indicator; stated as both simple and discounted payback |
| ROIC | Strategic-fit indicator; compared to the entity's weighted average cost of capital (WACC) and to the return earned by the existing portfolio |

**Hurdle-rate discipline:**

- The hurdle rate is stated explicitly and sourced: WACC, sector
  benchmark, board-approved threshold, or financing cost plus itemised
  risk premium.
- A project with IRR above hurdle but NPV near zero in the downside is
  flagged as fragile and requires a break-even covenant.
- Hurdle-rate sensitivity table is required at base, +200 bps, and
  +400 bps. Negative-NPV within 200 bps is classified as rate-sensitive.

**Opportunity-cost framing:**

- Every recommendation states the next-best use of the same capital and
  quantifies the opportunity cost of the chosen allocation over that
  alternative. "Do nothing" is always a valid alternative; its NPV
  (typically zero or the value of optionality preserved) is stated.

## Board-Pack Preparation

Board packs are decision instruments, not performance reports. Clarity of
message is the primary design constraint; data density is secondary.

**Structure:** (1) one-page executive summary — key message, three to
five data points, and one-sentence forward outlook per scenario; must
stand alone. (2) flux narrative — actuals vs budget vs prior year with
root-cause explanations (per §Variance Analysis Discipline). (3) KPI
scorecard with reference values and context notes (per §KPI Dashboard
Architecture). (4) scenario outlook bridge to period end (per §Scenario
Modelling).

**Presentation rules:**

- Adverse information is presented in the executive summary, not deferred
  to appendices; opening with positive highlights while burying bad news
  later is an anti-pattern (see §Anti-patterns).
- Every chart title states the conclusion, not the subject: "Gross
  margin declined 3pp YoY due to raw-material cost increase" not "Gross
  Margin Trend".
- Tables foot and cross-foot. A table that does not foot is a reporting
  error corrected before distribution.
- Footnotes state the basis of preparation (GAAP / IFRS / management
  accounts), non-GAAP bridges, and material period-on-period differences.

## Compliance and Materiality

Financial reporting controls are non-negotiable regardless of entity type.

- **SOX / J-SOX:** changes to models or close processes affecting a
  SOX-scoped account require a documented change-management record and
  control-owner sign-off before deployment.
- **Brazilian Lei 13.303/2016:** internal reporting for in-scope state-
  owned entities must be reconcilable to the public Formulário de
  Referência / CVM Instruction 480 disclosure.
- **Materiality threshold:** documented at the start of each reporting
  cycle. Variances above threshold trigger a restatement assessment;
  those below are recorded as audit-difference items and disclosed at the
  closing conference.
- **Auditor coordination:** board-pack figures differing from audit
  workpapers are flagged before distribution. No pack is issued with
  figures under active auditor dispute without an explicit disclosure note.

## Reporting Integrity

Four rules apply to all deliverables without exception:

1. **No plugs.** A forced balancing entry that makes a model foot without
   identifying the source is prohibited. Any unexplained residual is
   labelled as such and investigated before circulation.
2. **No last-minute force.** Adjusting an undocumented assumption in the
   final step to reach a pre-determined number is prohibited. The
   documented assumption set explains every variance; silent correction
   is not permitted.
3. **Comment trail.** Every judgement call or assumption override is
   documented at the point of application. A model with applied
   judgement and no comment trail fails the audit-readiness standard.
4. **Reconciliation chain.** Every model output feeding a management
   report or board pack is traceable, step by step, to the source-of-
   truth system. Breaks in the chain are reported as open items with a
   resolution date.

## Anti-patterns

| Anti-pattern | Description | Correct Approach |
|--------------|-------------|-----------------|
| Plug-to-target | Forcing a balancing entry or assumption to reach a pre-determined number | Label the residual as unexplained; investigate the source discrepancy |
| Hidden assumption | Using a driver value that is not documented in the assumption register | Add the assumption to the register with source and review date |
| Single-scenario forecast | Presenting one output number without scenario envelope or sensitivity range | Build base / upside / downside / break-case per §Scenario Modelling |
| Post-hoc rationalisation | Writing the variance explanation after the fact to fit a narrative rather than deriving it from operational data | Derive explanations from system data and operational owner confirmation before drafting |
| Board-deck drama inversion | Opening the executive summary with positive highlights while deferring adverse news to later sections | Present the most material item — positive or negative — in the first paragraph of the executive summary |
| Silent methodology change | Changing allocation basis, consolidation scope, or account mapping without disclosing the change in the comparative period footnote | Disclose methodology changes explicitly; provide a like-for-like bridge |
| False precision | Presenting forecasts to four decimal places on inputs with ±20% uncertainty | Match precision of output to precision of inputs; use ranges for uncertain drivers |

## Cross-References

- `domains/finance-accounting/skills/bookkeeper-controller` — chart-of-
  accounts governance and trial-balance sign-off; source of truth for
  all inputs consumed by this skill
- `domains/finance-accounting/skills/fpa-analyst` — budget calendar and
  rolling-forecast architecture; defines reference points for variance
  analysis
- `domains/business-support/skills/finance-tracker` — lightweight
  expense and project-budget tracking; escalates here when variance
  investigation or board reporting is required

## ADR Anchors

- **ADR-058** — two-pass review gate: all financial models, variance
  analyses, scenario outputs, and board-pack drafts are subject to the
  two-pass adversarial review before being treated as final.
