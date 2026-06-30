---
name: account-strategist
description: >
  Post-sale account strategy discipline covering land-and-expand execution,
  stakeholder mapping across multi-threaded relationships, QBR facilitation
  as forward-looking planning sessions, and retention math anchored to
  Net Revenue Retention (NRR) and Gross Revenue Retention (GRR) targets.
  Applies MEDDPICC qualification hygiene to expansion opportunities, the
  Bow Tie model (Land → Expand → Retain) as the structural growth frame,
  and health-score banding to route each account to the correct play
  (expansion, stabilization, or save). Use when: designing or reviewing an
  account expansion plan, preparing a QBR agenda, diagnosing single-threaded
  coverage risk, scoring renewal readiness, classifying a churn-risk signal,
  or building a post-sale risk register.
owner: Valentina Cruz (Account Strategist, domain persona)
tier: domain:sales
scope_tags: [account-strategy, land-and-expand, stakeholder-mapping, qbr, nrr, grr, post-sale]
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-account-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: sales
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
  - "**/accounts/**"
  - "**/qbr/**"
  - "**/renewals/**"
  - "**/expansion/**"
---

# Account Strategist

## Cardinal Rule

Account expansion happens because the customer's outcomes improve, not because
the account strategist has a quota to fill. If the customer cannot articulate
a concrete outcome delivered in the previous quarter — time saved, cost avoided,
revenue enabled, or risk reduced — there is no expansion claim. Framing the
ask as vendor benefit before establishing delivered value is the fastest way to
lose trust and forfeit renewal. Establish the outcome record first; every
expansion motion begins there.

---

## Fail-Fast Rule

Expansion plays MUST NOT be launched on any account classified red in the
current health-score band. Running an upsell motion into an account that has
not yet achieved success with existing products accelerates churn, not growth.
Before any expansion conversation is initiated, the following three gates MUST
pass: (1) the customer can name a measurable outcome the product delivered in
the prior 90 days; (2) the account health score is green or yellow-with-plan;
(3) at least one active relationship thread exists independent of the primary
champion. If any gate fails, the required play is stabilization or save — not
expansion.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing or reviewing a Land-Expand-Retain playbook for an account or a
  portfolio segment.
- Preparing a QBR agenda, evidence package, or mutual action plan.
- Diagnosing single-threaded coverage risk or performing a stakeholder-map
  audit.
- Scoring renewal readiness or computing NRR / GRR trajectory.
- Classifying an early-warning signal as churn-risk, contraction-risk, or
  expansion-ready.
- Building or reviewing a commercial, technical, or political risk register
  entry for an account.
- Coordinating a cross-functional expansion play (account team + CS + product).

Skip when: the account is pre-close (use deal-strategist instead); the task
is pipeline generation into net-new logos (use pipeline-analyst instead); or
the engagement is a procurement-only renewal with no upsell vector.

---

## Account Health Frame

Account health is a composite diagnostic, not a single metric. Four dimensions
must be tracked independently because they can diverge — high adoption with
low executive sentiment is a different failure mode than low adoption with a
highly engaged sponsor.

### Adoption

What it measures: the depth and breadth of product use relative to licensed
capacity and the customer's stated intended use cases.

Leading indicators (signal before the problem compounds):
- Feature activation rate for capabilities included in the signed scope.
- Department-level usage asymmetry (one team at 95% capacity, adjacent teams
  at 10% — signals blocked rollout, not healthy expansion).
- License utilization trending toward 80%+ threshold (expansion readiness
  signal) or trending toward 30% and falling (churn precursor).

Lagging indicators (measure what already happened):
- Monthly active user count versus provisioned seats.
- Tier-upgrade conversion rate (where consumption-based pricing applies).

### Outcomes

What it measures: the customer's ability to articulate a before/after delta
attributable to the product — time, cost, revenue, risk.

Leading indicators:
- Customer-side success metrics tracked in a joint success plan.
- Frequency of ROI references in customer communications without prompting.

Lagging indicators:
- Quantified ROI documented in QBR evidence package.
- Case study or reference participation willingness.

### Risk

What it measures: commercial, technical, political, and external threats to
the renewal or expansion trajectory.

Leading indicators:
- Executive sponsor posting externally about a new role or being recruited.
- Support ticket volume spike or sentiment decline over a rolling 30-day window.
- Detractor identified but not engaged.
- Contract milestone approaching without a renewal conversation opened.

Lagging indicators:
- Formal escalation opened.
- Legal or commercial dispute on record.
- Champion confirmed departed without a successor relationship active.

### Sentiment

What it measures: the subjective quality of the relationship with key
stakeholders — trust level, candor, willingness to share internal context.

Leading indicators:
- Informal communication frequency (outside of scheduled touchpoints).
- Stakeholder willingness to make internal introductions.
- Champion proactively scheduling executive alignment without being asked.

Lagging indicators:
- NPS or CSAT score trend.
- Executive sponsor attendance rate at QBRs.

---

## Stakeholder Mapping Discipline

A stakeholder map is a live document, not a pre-sale artifact. It MUST be
reviewed at minimum monthly and updated immediately when a role change,
departure, or budget shift is detected. A stale map is a structural risk —
the account team loses awareness of the actual influence topology before
a critical moment (renewal, expansion ask, escalation response).

### Roles and Motivations

**Champion**: internal advocate with organizational credibility who benefits
personally and professionally from the product succeeding. Motivation: outcome
delivery, personal brand, career leverage. Develop through: ROI evidence kits,
internal business-case templates, peer case studies for internal circulation.

**Decision Maker (Economic Buyer)**: controls the budget or signs the renewal.
May not be the most engaged user. Motivation: cost justification, risk
reduction, strategic alignment with organizational objectives. Develop through:
executive summary framing, board-level metrics, and C-suite QBR sessions for
strategic accounts.

**Influencer**: shapes the decision-maker's opinion without owning budget.
Common in technical evaluations, procurement reviews, and compliance
assessments. Motivation: vendor reliability, technical fit, risk profile.
Develop through: technical deep dives, documented integration success, security
and compliance evidence.

**Detractor**: actively or passively opposes the product or the vendor
relationship. MUST be identified and tracked with the same rigor as champions.
A detractor surfaced at renewal negotiation is a managed risk; a detractor
discovered two weeks before contract close is a crisis. Develop through:
direct engagement, problem resolution, and where possible, converting the
concern into a documented fix or roadmap commitment.

**Coach**: provides insider intelligence about organizational dynamics, informal
decision processes, and the true decision timeline. Often not the formal
champion. Motivation: relationship reciprocity, trust. Develop through:
consistent value exchange and demonstrated discretion.

### Coverage Standards

Every account in the portfolio MUST maintain:
- Minimum three independent relationship threads across the organizational
  map (not three contacts at the same level reporting to the same manager).
- At least one thread at the decision-maker or budget-holder level.
- At least one thread that would survive the champion's departure.
- Detractor list reviewed quarterly; no unengaged detractor with medium or
  higher influence allowed to persist beyond one review cycle.

---

## QBR Structure

A QBR is a forward-looking strategic planning session. Its purpose is to
align the customer's evolving business objectives with the product roadmap,
validate the expansion thesis, and produce a mutual action plan with committed
owners and dates. A QBR that is primarily a status report of past activity
fails its purpose regardless of delivery quality.

### Required Sections and Evidence Standards

| Section | Time (60-min frame) | Owner | Required Evidence |
|---|---|---|---|
| Value Delivered | 15 min | Account Strategist | Quantified outcomes: time saved, cost avoided, revenue enabled, risk reduced — specific numbers, not estimates. Source: usage data, customer-reported metrics, support resolution data. |
| Customer Roadmap | 20 min | Customer lead | Customer states top 3 business priorities for next two quarters. Account team listens; asks clarifying questions. No product pitch in this section. |
| Product Alignment | 15 min | Account Strategist + Product | Map product capabilities and roadmap items to customer priorities named in previous section. Only capabilities directly relevant to stated priorities are presented. |
| Mutual Action Plan | 10 min | Account Strategist | Named actions, named owners (both sides), specific dates. Decisions deferred without a date and owner are not decisions. |

### Pre-QBR Preparation Gate

The following MUST be completed before the QBR is scheduled:

- Usage and adoption metrics pulled and formatted for the delivery period.
- Support ticket summary: volume trend, CSAT trend, open escalations resolved
  or acknowledged with a resolution date.
- Stakeholder map validated: confirm attendees, identify any missing stakeholders
  who should be present, prepare a plan for any new faces to introduce.
- Expansion thesis reviewed internally: is the account health-score green? Are
  the expansion signals paired with context, timing, and stakeholder alignment?
  If the account is yellow, the QBR's primary goal is stabilization, not pitch.
- ROI data confirmed with specific figures, not verbal customer assertions.
  Vague positive sentiment is not evidence; a number is evidence.

### QBR Failure Modes to Avoid

- Opening with a product roadmap before presenting delivered value.
- Presenting expansion options before the customer has confirmed they are
  receiving value from existing scope.
- Filling the customer roadmap section with vendor talking points instead of
  listening to the customer's stated priorities.
- Ending without a mutual action plan that has named owners and dates on both
  sides.

---

## Renewal and Expansion Math

### Core Formulas

**Gross Revenue Retention (GRR)**: measures retention excluding expansion.
Denominator is starting ARR; numerator is ending ARR minus churn minus
contraction. GRR ≤ 100% by definition. A declining GRR signals churn or
contraction accelerating faster than expansion can compensate — the underlying
retention problem is masked by expansion.

```
GRR = (Starting ARR - Churned ARR - Contracted ARR) / Starting ARR × 100
```

Target floor by segment: enterprise ≥ 90%; mid-market ≥ 85%; SMB ≥ 80%.

**Net Revenue Retention (NRR)**: measures retention including expansion.
NRR > 100% means the cohort is growing even after accounting for churn and
contraction. NRR is the primary portfolio-level health metric.

```
NRR = (Starting ARR - Churned ARR - Contracted ARR + Expansion ARR)
      / Starting ARR × 100
```

Target by segment: enterprise ≥ 120%; mid-market ≥ 110%; SMB ≥ 105%.

### Renewal MUST be Earned, Not Forecast

A renewal that appears in forecast without an active renewal conversation,
documented value delivery, and confirmed stakeholder engagement is a wishful
entry, not a pipeline entry. The renewal is earned by the following conditions
— all three MUST be present:

1. The customer can state a quantified outcome the product delivered in the
   prior contract period.
2. A renewal conversation has been opened with the economic buyer at minimum
   90 days before contract end.
3. No unresolved detractor or unmanaged risk-register item is blocking the
   renewal path.

Forecasting a renewal without these three conditions is misrepresenting
pipeline health to the organization.

### Expansion Qualification Gate (MEDDPICC Applied Post-Sale)

Before any expansion opportunity is entered as qualified pipeline, apply
the following checks drawn from MEDDPICC qualification discipline:

- **Metrics**: the customer can state a specific metric the expansion will
  improve, with a before-state and a target state.
- **Economic Buyer**: the budget holder for the expansion has been identified
  and has confirmed interest or at minimum has not declined.
- **Decision criteria**: the customer has stated what success looks like for
  the expansion scope.
- **Decision process**: the internal approval process for this expansion
  amount has been mapped — who signs, in what sequence, at what threshold.
- **Champion**: an internal advocate is actively supporting the expansion
  case with their peers and manager.

An expansion opportunity missing any of these five items is a signal, not an
opportunity. Do not promote to qualified pipeline until all five are confirmed.

---

## Risk Register Format

Every account at yellow or red health status MUST maintain a written risk
register. Each risk entry requires the following fields:

| Field | Required Content |
|---|---|
| Risk ID | Sequential identifier within the account (R-01, R-02, etc.) |
| Category | One of: commercial / technical / political / sponsor-change / consolidation |
| Description | One sentence describing the specific risk condition |
| Probability | High / Medium / Low with brief rationale |
| Impact | Revenue at risk ($ range) and renewal/expansion effect |
| Leading signal | Observable indicator that predicts this risk materializing (not the risk itself) |
| Mitigation | Named action, named owner, due date |
| Status | Open / In Progress / Mitigated / Accepted |

### Risk Category Definitions

**Commercial**: pricing dispute, budget freeze, procurement consolidation
exercise, CFO-driven vendor reduction initiative, or competitor pricing pressure
during renewal window.

**Technical**: product failure to meet a contractually committed performance
SLA, integration instability, or a roadmap promise that cannot be delivered in
the committed timeframe.

**Political**: internal reorganization that eliminates the champion's role or
transfers budget authority; merger or acquisition that introduces a competing
incumbent; change in executive sponsor priorities.

**Sponsor change**: champion departure, economic buyer replacement, or primary
user team restructuring that severs the relationship threads built during the
land phase.

**Consolidation**: customer platform rationalization initiative that evaluates
whether the product's function can be absorbed by an existing enterprise
license or a competing solution already owned elsewhere in the organization.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Practice |
|---|---|---|
| **Feature-pitching during the renewal window** | Presenting new capabilities before confirming the customer has realized value from current scope signals the vendor's priority is upsell revenue, not customer outcomes. Trust erodes; economic buyers become skeptical of every claim. | Establish the value delivered from existing scope with specific evidence before introducing any expansion option. The expansion ask must be framed as the logical next step from confirmed outcomes, not a sales motion. |
| **Ignoring identified detractors** | A detractor left unengaged does not stay neutral. They surface at the decision moment — renewal sign-off, executive review, procurement approval — with concentrated opposition. The later the engagement, the less time to resolve it. | Map detractors with the same rigor as champions. Engage directly, acknowledge the concern specifically, and document the resolution plan. Convert where possible; contain and neutralize where conversion is unlikely. |
| **Single-threaded account coverage** | Accounts with one active relationship thread lose their entire relationship when that contact changes roles, leaves the company, or shifts priorities. The account team arrives at renewal with no internal context and no warm path to the economic buyer. | Maintain at minimum three independent relationship threads at different organizational levels and reporting lines. Threads MUST include at least one path to the budget holder that does not route through the primary champion. |
| **Stale stakeholder map** | An outdated map leads the team to act on a power topology that no longer exists. Outreach goes to departed contacts; expansion conversations are brought to people who no longer control the budget; detractors who gained influence are unknown. | Review the stakeholder map monthly at minimum. Update immediately when a title change, departure, or budget shift is detected. Treat an unreviewed map as an unreliable map. |
| **Forecasting renewals without the three earned-renewal conditions** | A renewal in forecast without confirmed value delivery, an active conversation with the economic buyer, and no unresolved blockers misrepresents pipeline health. Leadership makes resource and investment decisions based on this data. | Apply the three earned-renewal conditions as a qualification gate before entering any renewal as committed or likely. Document which condition is missing and the plan to achieve it. |
| **Conflating expansion readiness with expansion intent** | A usage signal at 90% capacity means the customer could benefit from expansion; it does not mean the customer is ready to buy more. Acting on readiness signals without confirming intent generates rejected proposals and relationship friction. | Validate every expansion signal across three axes before treating it as an opportunity: the underlying cause (what drove this signal?), the timing fit (is there an internal trigger that makes now the right moment?), and stakeholder buy-in (who has a vested interest and can internally sponsor the case?). All three axes MUST confirm before promotion to pipeline. |
| **Running a QBR as a status report** | A backward-looking QBR produces a passive audience. The customer hears about what already happened; there is no forward agenda to engage with. The session ends without alignment on the customer's next priorities and without a mutual action plan. | Structure every QBR with the majority of time allocated to the customer's forward roadmap and joint next steps. Value delivered is the opening context — not the entire session. Always close with a documented mutual action plan with named owners and specific dates. |
| **Bringing an expansion ask to a red-health account** | Pitching into an unhealthy account signals that the vendor's quota is more important than the customer's outcome. It accelerates distrust and can convert a recoverable save situation into a confirmed churn. | Gate every expansion motion on the health-score band. Red accounts receive only a save play. Yellow accounts with a documented stabilization plan may receive a limited, customer-requested scoping conversation, not a pitch. |

---

## Cross-References

- `.claude/skills/core/code-review-checklist/SKILL.md` — Two-pass review
  protocol applicable to QBR preparation and risk-register review: first pass
  for completeness of evidence and stakeholder coverage; second pass for
  adversarial pressure-testing of the expansion thesis and renewal forecast
  assumptions.

- `.claude/skills/domains/sales/skills/deal-strategist` — Qualification
  discipline (MEDDPICC, SCOTSMAN) and competitive displacement framing applied
  at the pre-close stage. The account-strategist post-sale expansion gate
  borrows MEDDPICC qualification mechanics for post-sale expansion pipeline
  qualification.

- `.claude/skills/domains/sales/skills/pipeline-analyst` — Portfolio-level
  NRR / GRR trending, cohort analysis, and renewal-forecast accuracy modeling.
  The account-strategist skill operates at the individual account level; the
  pipeline-analyst skill aggregates and surfaces portfolio-level signals.

---

## ADR Anchors

- **ADR-058** (`ADR-058-brainstorm-gate-and-two-pass-review.md`) — Two-pass
  review mandate for high-stakes authored artifacts. QBR preparation, renewal
  forecasts, and expansion proposals are explicitly in scope for this discipline.
  First pass: completeness of evidence and stakeholder coverage. Second pass:
  adversarial review of expansion thesis assumptions, detractor coverage, and
  risk-register gaps. A single-pass QBR preparation is insufficient for accounts
  above a materiality threshold defined by the account team's risk policy.
