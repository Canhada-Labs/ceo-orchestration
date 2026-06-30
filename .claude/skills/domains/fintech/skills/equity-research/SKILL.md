---
name: equity-research
description: |
  Fundamental and quantitative equity research discipline for public markets.
  Covers the full research lifecycle: universe screening, industry framing,
  company deep-dive, intrinsic valuation, risk registration, and investment
  memo production. Applies multi-method valuation (DCF, comparable multiples,
  sum-of-parts, asset-based, EVA), quality-of-earnings forensics, and factor
  screens (Value, Quality, Momentum, Low-Volatility). Enforces MNPI firewall
  and Reg FD / CVM Resolution 44 compliance throughout. Use when: producing
  a sell-side or internal investment memo; stress-testing an existing thesis;
  screening a sector for new ideas; conducting due diligence on a listed issuer;
  building or validating a valuation model; or reviewing research for compliance
  and analytical rigor.
owner: Equity Research Analyst (domain persona)
tier: domain:fintech
scope_tags: [equity-research, fundamental-analysis, valuation, portfolio-analysis, due-diligence, sell-side]
inspired_by:
  - source: msitarzewski/agency-agents/finance/finance-investment-researcher.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 6
risk_class: low
stack: []
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 10}
  engine: {active: true, priority: 8}
  fintech: {active: true, priority: 5}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 8}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)equity|valuation|dcf|investment.?memo|sell.?side"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/equity-research/**"
  - "**/valuation/**"
  - "**/investment-memos/**"
---

# Equity Research

## Cardinal Rule

No investment memo may contain a buy, hold, or sell recommendation without
both a formally documented intrinsic-value model AND an explicit falsifiability
check — a written set of conditions whose occurrence would invalidate the thesis.
Memos that express price direction without both elements are rejected at the
two-pass review gate (ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- Material non-public information (MNPI) has been received or is suspected —
  do not proceed; escalate to compliance immediately.
- The most recent audited financial statements are unavailable or unverified.
- The issuer's primary filing language is unknown and no certified translation
  is available.
- Valuation model inputs contain floating-point arithmetic on monetary values
  (see `domains/fintech/skills/financial-correctness-and-math` §Cardinal Rule).
- The investment horizon has not been explicitly stated.

Never approximate, estimate from memory, or "rough" a model. Incomplete inputs
produce rejected outputs, not approximated outputs.

## When to Apply

Apply this skill when:

- Initiating coverage on a listed equity issuer.
- Producing or reviewing an investment memo or research note.
- Performing factor screens to populate or trim a watchlist.
- Stress-testing a thesis in response to a material development (earnings
  miss, regulatory action, management change, M&A announcement).
- Conducting due diligence on a listed issuer ahead of a significant position.
- Reviewing a third-party research report for analytical soundness.
- Designing or auditing a portfolio analytics system (route to
  `core/architecture-decisions` for system-level decisions).

Do not apply this skill to unlisted securities, private credit, or derivative
instruments without an accompanying listed-equity anchor. Crypto assets are
explicitly out of scope.

## Research Process — Six Stages

Each stage produces a named, persisted output. No stage may be skipped;
outputs are referenced by the memo at the final stage.

### Stage 1 — Universe Screen

Purpose: reduce the investable universe to a tractable candidate list.

Process:
- Apply quantitative factor screens (see §Quantitative Screens & Factors).
- Filter by liquidity floor: minimum 30-day average daily trading volume
  sufficient for the intended position size with <15% market-impact estimate.
- Filter by disclosure quality: issuers with qualified audit opinions,
  restatements in the past 24 months, or late filings are flagged and
  require explicit override with documented rationale.

Output: `screen-results.csv` — ranked candidate list with factor scores,
liquidity flag, and disclosure-quality flag per issuer.

### Stage 2 — Industry Frame

Purpose: establish the competitive structure and macro drivers before
touching company-specific data.

Process:
- Map Porter's Five Forces for the relevant sub-industry. Each force receives
  a Weak / Moderate / Strong rating with a one-sentence justification.
- Identify the top three secular tailwinds and top two structural headwinds.
- Document the regulatory regime: primary regulator(s), recent enforcement
  actions, pending rule-changes material to the industry.
- Establish peer group: minimum four publicly traded comparables with
  comparable revenue scale (within 3× of target), similar business model,
  and same primary geography.

Output: `industry-frame.md` — Porter map, secular drivers table, regulatory
summary, peer group definition with inclusion/exclusion rationale.

### Stage 3 — Company Deep-Dive

Purpose: build a complete picture of the issuer's business, financials,
and governance.

Process:
- Read the last three annual reports (10-K or equivalent) and the last
  four quarterly filings (10-Q or equivalent) in filing order, oldest first.
- Read the most recent proxy statement in full (see §Due-Diligence Workflow
  for reading-order discipline).
- Conduct quality-of-earnings review (see §Quality of Earnings Discipline).
- Assess management capital-allocation track record: ROIC trend vs. WACC,
  acquisition history with outcome, buyback timing relative to intrinsic value.
- Map insider ownership, director independence, and any related-party
  transactions.

Output: `company-deep-dive.md` — business description, financial summary
table (five-year), QoE findings, management assessment, governance flags.

### Stage 4 — Valuation

Purpose: produce a defensible intrinsic-value range.

Process:
- Select valuation method(s) per §Valuation Methods Selection.
- Build a three-scenario model (bull / base / bear) for each primary method.
- Document every key assumption explicitly: revenue CAGR, margin trajectory,
  terminal growth rate, discount rate derivation, multiple selection rationale.
- Triangulate across methods; document any material divergence between methods.
- The intrinsic-value range is the output — not a point estimate.

Output: `valuation-model.[xlsx|csv|py]` + `valuation-summary.md` documenting
assumptions, scenario weights, and resulting intrinsic-value range.

### Stage 5 — Risk Register

Purpose: enumerate and quantify risks in a standard format.

Process: populate the risk register per §Risk Register Format.
Minimum five rows covering at least three distinct risk categories.
Each risk must have a quantified impact estimate (not "material" — a
percentage or dollar range).

Output: `risk-register.md` — structured table per §Risk Register Format.

### Stage 6 — Memo

Purpose: produce the deliverable consumed by the investment decision-maker.

Process: write the investment memo per §Research Memo Output.
The memo synthesizes Stages 1-5. It must cite `valuation-summary.md`
and `risk-register.md` by filename. The memo is the input to the
two-pass review gate (ADR-058).

Output: `investment-memo.md` — structured document per §Research Memo Output.

## Valuation Methods Selection

| Method | Use When | Primary Bias |
|--------|----------|--------------|
| DCF (Discounted Cash Flow) | Issuer has stable, forecastable free cash flow; long investment horizon (3+ years) | Terminal-value sensitivity; WACC subjectivity; over-precision illusion |
| Comparable Multiples | Liquid, active peer group with comparable growth profiles; shorter-horizon trade | Circular (market may be wrong on peers); multiple compression/expansion timing |
| Sum-of-Parts | Issuer operates multiple distinct, separable business units | Segment EBIT allocation subjectivity; conglomerate discount omission |
| Asset-Based (NAV) | Asset-heavy issuer (real estate, natural resources, holding company); distressed or liquidation scenario | Mark-to-market assumptions; off-balance-sheet items; going-concern vs. liquidation gap |
| EVA (Economic Value Added) | Capital-intensive issuer where ROIC vs. WACC spread is the core thesis driver | WACC estimation sensitivity; accounting-to-economic capital bridge complexity |

Rule: primary method must be stated and justified. A second independent method
is required for any memo recommending a position above the portfolio concentration
limit defined in the investment policy statement.

### DCF Assumption Block — Required Fields

Every DCF model must document these fields in `valuation-summary.md`:

```
DCF Assumptions — Issuer A (base case)
───────────────────────────────────────────────────────
revenue_cagr_years_1_5:       X.X%    # source: internal model
revenue_cagr_terminal:        X.X%    # must be <= long-run nominal GDP
ebitda_margin_terminal:       X.X%    # industry median anchor: cite source
capex_pct_revenue_terminal:   X.X%    # maintenance + growth split documented
tax_rate:                     X.X%    # effective rate, jurisdiction-specific
wacc:                         X.X%    # CAPM derivation in footnote
terminal_growth_rate:         X.X%    # must be <= wacc
exit_multiple_sanity_check:   X.Xx EV/EBITDA (peer median: X.Xx) — convergence check
───────────────────────────────────────────────────────
intrinsic_value_range: $XX - $XX (bear: $XX, base: $XX, bull: $XX)
```

Omitting any field is a blocker finding at the two-pass review gate.

## Quality of Earnings Discipline

Revenue recognition red flags — any of the following requires an explicit
QoE finding in `company-deep-dive.md`:

- Revenue recognized before delivery obligations are substantially complete
  (channel stuffing, bill-and-hold).
- Disproportionate growth in deferred revenue or unbilled receivables relative
  to recognized revenue.
- Revenue concentration: top-three customers representing >40% of revenue
  without multi-year contracted visibility.
- Material change in revenue recognition policy between periods without
  a clear business rationale in the filing.

Working-capital manipulation flags:

- Days Sales Outstanding (DSO) trend diverging from revenue growth trend by
  more than 15 percentage points over two consecutive quarters.
- Days Payable Outstanding (DPO) extending aggressively into year-end reporting
  periods (suggests timing of cash flow, not operational improvement).
- Inventory build at a rate inconsistent with forward-revenue guidance.

Non-GAAP gymnastics flags:

- Stock-based compensation excluded from "adjusted" EBITDA without a
  unit-economics justification (SBC is a real cost).
- Recurring "one-time" items appearing in three or more consecutive periods.
- Non-GAAP gross margin exceeding GAAP gross margin by more than 500 basis
  points without documented amortization rationale.
- Adjusted metrics used in management compensation targets but not in
  external guidance.

Procedure: for each flag triggered, document in QoE findings with the
specific line item, period, magnitude, and management's stated explanation.
A finding is not a disqualifier — undisclosed or unexplained findings are.

## Quantitative Screens & Factors

Factor definitions are pinned to standard academic and practitioner sources.
Use these definitions consistently; do not substitute proprietary variants
without documenting the deviation.

| Factor | Definition | Signal Direction |
|--------|-----------|-----------------|
| Value — Price/Book | Market cap divided by tangible book value (intangibles and goodwill excluded) | Low P/B = value signal (Fama-French 1992) |
| Value — EV/EBITDA | Enterprise value divided by trailing twelve-month EBITDA | Low EV/EBITDA relative to peer group = value signal |
| Value — Free Cash Flow Yield | Trailing twelve-month free cash flow divided by market cap | High FCF yield = value signal |
| Quality — ROIC | NOPAT divided by invested capital (Greenwald / Koller definition) | High and stable ROIC above WACC = quality signal |
| Quality — Gross Margin Stability | Standard deviation of gross margin over five years | Low std dev = stable competitive position |
| Quality — Accruals Ratio | (Net operating assets[t] - Net operating assets[t-1]) / avg total assets | Low or negative = earnings more cash-backed (Sloan 1996) |
| Momentum — Price Momentum | Total return 12 months minus 1 month (Jegadeesh-Titman 1993 formation period) | Top quartile = momentum signal |
| Momentum — Earnings Revision | Net analyst earnings-estimate revisions over 90 days as a fraction of total estimates | Net positive revisions = momentum signal |
| Low-Volatility — Beta | 60-month rolling OLS beta to primary market index | Low beta = low-volatility signal (Black 1972; Frazzini-Pedersen 2014) |
| Low-Volatility — Idiosyncratic Vol | Standard deviation of daily excess returns over 12 months after removing market beta | Low idiosyncratic vol = quality-of-earnings stability proxy |

Multi-factor composite: when running a composite screen, document factor
weights and the rebalance frequency. Equal-weighting is the default absent
a documented empirical rationale for alternative weights.

## Due-Diligence Workflow

### Filing Reading Order

1. Annual report (10-K or equivalent) — most recent, then two prior years.
   Read: Business description, Risk Factors, MD&A, financial statements
   (income statement → balance sheet → cash flow statement → notes), and
   auditor's report including any critical audit matters.
2. Quarterly filings (10-Q or equivalent) — four most recent in reverse
   chronological order. Focus: sequential changes in revenue, margins,
   working capital, and any new risk disclosures.
3. Proxy statement (DEF 14A or equivalent) — read in full for: director
   biographies and independence determinations, executive compensation
   structure and pay-for-performance alignment, related-party transactions,
   and shareholder proposal outcomes.
4. Material event filings (8-K or equivalent) — screen all filings since
   the most recent 10-K. Flag: earnings releases, M&A announcements,
   management changes, material contract terminations, and regulatory
   correspondence.
5. Institutional ownership filings (13F, 13D/G where applicable) — note
   any significant new entrants, exits, or activist disclosures.

### Management Call Discipline

- Prepare written questions before the call. Questions must be derived
  from filing analysis, not from sell-side consensus summaries.
- Record or note verbatim any quantitative guidance or forward-looking
  statement management provides.
- After the call, document: what management confirmed, what management
  avoided, and what the avoidance pattern implies.
- Do not update the valuation model based on management guidance alone;
  triangulate against independent data sources.

### Channel Checks

Channel checks (customer interviews, supplier interviews, competitor
intelligence) are primary research. Document:
- Interview date, interviewee role (no names — initials or role only),
  and method (call, email, in-person).
- Specific questions asked and verbatim or paraphrased responses.
- Reliability assessment: is the interviewee in a position to know what
  they claim to know?

Channel check outputs feed the company deep-dive; they do not independently
drive valuation changes without corroboration from filings.

### Regulatory Filings

Beyond standard SEC/CVM filings: review any industry-specific regulatory
database (e.g., FCC, FDA, ANVISA, BACEN depending on issuer sector) for
enforcement actions, license status, or pending proceedings material to the
investment thesis.

## Risk Register Format

Each row in `risk-register.md` must contain:

| Field | Required Content |
|-------|-----------------|
| Risk ID | Sequential (R-01, R-02, ...) |
| Category | One of: Operational / Financial / Regulatory / Macro / Governance |
| Description | One to two sentences; specific to the issuer, not generic |
| Probability | Low / Medium / High with a one-sentence qualitative rationale |
| Impact (Bear Scenario) | Quantified estimate: percentage drawdown on intrinsic value or EPS impact |
| Thesis Breaker | Yes / No — if Yes, specify the observable trigger event |
| Mitigation | Specific monitoring action or hedge, or "None identified" |

Governance risks include: board capture, founder control without sunset,
related-party transaction history, auditor changes without disclosed rationale,
and material restatements.

Macro risks must specify the transmission mechanism to the issuer (e.g., "a
200 bps rise in long-term rates compresses the terminal multiple by ~1.5× at
current leverage, reducing intrinsic value by approximately 12% in the base case").

## Research Memo Output

The investment memo is the primary deliverable. Required sections and
length targets:

| Section | Required Content | Length Target |
|---------|-----------------|--------------|
| Cover | Issuer placeholder (e.g., "Issuer A"), sector, market cap range, memo date, investment horizon, analyst | 1 table row |
| Investment Thesis | Three to five bulleted core arguments, each supported by a specific data point from the deep-dive | 200-400 words |
| Catalysts | Table: catalyst description, expected timing (quarter or range), estimated price impact, probability assessment | 3-6 rows |
| Bear Case | Three specific scenarios that invalidate or significantly impair the thesis; each with a quantified downside | 200-350 words |
| Valuation Range | Bull / base / bear intrinsic-value range with method citation; explicit statement of key assumptions | 150-300 words |
| Risk Register Reference | Reference to `risk-register.md`; flag any Thesis Breaker risks; state monitoring cadence | 50-100 words |
| Position Sizing Rationale | Conviction level (High / Medium / Low) with evidence quality assessment; position size relative to portfolio concentration policy | 100-200 words |

The memo must state explicitly: "This memo does not constitute a trading
recommendation and has not been reviewed for MNPI compliance by [compliance
function]" — or, if compliance review has been completed, the reviewer name
and date.

## Compliance Guardrails

### MNPI Firewall (Hard Line)

The research process must not use material non-public information.
This is a hard line — not a soft guideline.

MNPI includes: non-public earnings guidance, undisclosed M&A negotiations,
regulatory outcomes not yet public, and any information received under NDA
from the issuer that has not been publicly disclosed.

If MNPI is received at any stage: stop research; do not update any model or
memo; escalate immediately to compliance. No exception for "I won't trade on
it" — possession is sufficient for regulatory exposure.

### Selective Disclosure — Reg FD (US Jurisdiction)

Regulation FD (17 CFR Part 243, effective 2000) prohibits issuers from
selectively disclosing material non-public information to securities market
professionals without simultaneous public disclosure.

Implication for the research process: information obtained in one-on-one
management calls that has not been publicly disclosed must be treated as
potentially MNPI until confirmed otherwise. Any guidance received in a
non-public setting that differs materially from public guidance triggers
a Reg FD review obligation on the issuer's side and an MNPI flag on the
analyst's side.

### CVM Resolution 44 / Lei 6.385 (Brazilian Jurisdiction)

For issuers listed on B3 (Brasil, Bolsa, Balcão) or subject to CVM
jurisdiction: CVM Resolution 44 (2021, superseding CVM Instruction 358)
establishes equivalent selective-disclosure prohibitions and insider-trading
controls. Lei 6.385/1976 (as amended) provides the underlying statutory
framework.

Brazilian-listed issuers additionally file material-fact notices (fatos
relevantes) with CVM via the Sistema Empresas.NET disclosure portal.
These filings carry the same information-barrier obligations as 8-K filings
under US rules.

Jurisdiction note: a single research process covering an issuer with ADR
listings and B3 listings is subject to both Reg FD and CVM Resolution 44
simultaneously.

### Insider-Trading Information Barriers

Research derived from public filings, channel checks with non-issuer
parties, and published industry data is permissible. Research that relies
on information obtained from the issuer in a non-public context requires
compliance sign-off before the memo is circulated.

## Anti-patterns

| Anti-pattern | Description | Correct Approach |
|-------------|-------------|-----------------|
| Confirmation bias | Seeking data that supports a pre-formed view; dismissing contradictory evidence | State the thesis as a falsifiable hypothesis before beginning Stage 3; document disconfirming evidence in the bear case section |
| Consensus chasing | Building a thesis that matches sell-side consensus without identifying a variant perception | Explicitly document where the thesis diverges from consensus and why the divergence is warranted |
| Target-price reverse-engineering | Starting from a desired price target and adjusting assumptions to reach it | Derive the intrinsic-value range from documented assumptions; never work backwards from a target |
| DCF "growing into the multiple" | Assuming terminal multiple expansion is justified by the thesis without independent support | Terminal multiple must be anchored to a peer group median or long-run sector average; expansion vs. contraction must be explicitly argued |
| Anchoring to cost basis | Holding or adding to a position because of entry price rather than current intrinsic value | The current intrinsic-value range is the only relevant reference; cost basis is irrelevant to the thesis |
| Thesis drift | Silently expanding the thesis scope when original catalysts fail to materialize | When a catalyst passes without triggering the expected outcome, explicitly address whether the thesis is intact or impaired |
| Precision over-claim | Reporting DCF output as "$47.32 per share" rather than a range | All intrinsic-value outputs are ranges, not point estimates; report as "$42-$53 per share (base case)" |

## Cross-References

- `core/code-review-checklist` — apply the two-pass review gate (ADR-058)
  to the investment memo before circulation; the memo is a high-stakes
  analytical artifact with the same review obligations as production code.
- `domains/fintech/skills/financial-correctness-and-math` — all monetary
  arithmetic in valuation models must satisfy the decimal-precision and
  invariant-validation requirements defined in that skill.
- `core/architecture-decisions` — when the research output feeds into a
  portfolio management system or quantitative screening platform, route
  system-level design decisions through the architecture-decisions skill;
  do not embed system architecture choices inside the research memo.

## ADR Anchors

- **ADR-058 (Brainstorm gate + two-pass adversarial review):** the
  investment memo produced at Stage 6 is a primary artifact requiring
  the two-pass review defined in ADR-058 §BORROW-2. The first pass
  reviews analytical completeness and internal consistency; the second
  pass reviews from an adversarial frame — specifically challenging the
  bull-case assumptions and verifying that the bear case is equally
  rigorous. The memo must not be circulated until both passes are complete
  and any blocker findings are resolved.
