---
name: studio-operations
description: >
  Creative studio and agency operations discipline covering utilisation tracking,
  billable-rate enforcement, capacity planning, project profitability per client,
  retainer-vs-project revenue mix, freelance-network management, and studio-margin
  economics. Provides the operational scaffolding that converts creative output into
  sustainable business performance. Use when a studio lacks visibility into team
  utilisation or billable rates, when project margins are unmeasured, when a single
  client dominates revenue exposure, when freelancers are engaged without paper trail
  or IP assignment, or when capacity decisions are made without 90-day forward data.
owner: Morgan Calloway (Studio Operations Manager, domain persona)
tier: domain:project-management
scope_tags: [studio-operations, utilisation-tracking, capacity-planning, project-profitability, retainer-mix, freelance-network]
inspired_by:
  - source: msitarzewski/agency-agents/project-management/project-management-studio-operations.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: project-management
priority: 8
risk_class: low
stack: []
context_budget_tokens: 600
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
  - "**/studio-ops/**"
  - "**/capacity/**"
  - "**/utilization/**"
---

# Studio Operations

## Cardinal Rule

Studio economics are determined by the spread between billable rate realised and
fully-loaded cost per hour — every operational decision either protects that spread
or erodes it. Utilisation and margin are measurements, not targets; they are symptoms
of how well scope, staffing, and rate discipline are maintained across every
engagement. A studio that does not measure these continuously cannot manage them.

## Fail-Fast Rule

If project margin cannot be calculated before a project enters execution, the project
does not enter execution. Scope accepted without a budget model produces margin
surprises that cannot be recovered downstream. If a client engagement requires scope
reduction to preserve margin, that conversation happens before the first deliverable
is committed, not after the invoice is disputed.

## When to Apply

- A studio or agency team needs baseline utilisation visibility by role or discipline.
- Billable rates are applied inconsistently or discounted without scope reduction.
- Capacity decisions for the next quarter are made without forward-demand data.
- Per-project profitability has never been tracked or is tracked only at invoice time.
- Retainer-vs-project revenue mix is unmanaged and creates cash-flow volatility.
- Freelancers are engaged on verbal agreements or without IP assignment documentation.
- A single client represents more than 25 percent of total studio revenue.
- Gross margin has drifted below 50 percent without a documented causal analysis.

## Utilisation Tracking

Utilisation is the proportion of available hours that are applied to billable work.
It is not a proxy for productivity, output quality, or team health; confusing
utilisation with productivity is the root cause of the most common studio burnout
pattern.

### Target Rate by Role

Target utilisation differs by role because the work mix differs:

| Role tier | Target billable utilisation | Rationale |
|---|---|---|
| Senior practitioner | 65–70% | Client-facing strategic work; remaining capacity held for internal IP, mentoring, and BD support |
| Mid practitioner | 70–75% | Primary delivery capacity; bench time covers ramp and skill development |
| Junior practitioner | 75–80% | High-execution workload; buffer for review cycles and structured learning |
| Studio operations / PM | 20–35% directly billable | Primarily overhead function; partial project management may bill at client-project rate |

### Billable vs PD vs Admin Split

Every worked hour is classified weekly into three categories: billable (client
project), professional development (internal skill-building, tooling, portfolio),
or admin (internal meetings, studio management, non-billable coordination). The
split is recorded, not estimated at quarter-end. Retroactive reclassification is
a reporting failure, not a correction.

### Weekly Reporting Cadence

Utilisation data is collected and visible to studio leadership on a weekly basis.
Monthly or quarterly utilisation reports operate on data too stale to inform
resourcing decisions. A studio that discovers an underbilling pattern at month-end
has already lost the revenue.

### Utilisation Ceiling

Sustained billable utilisation above 80 percent for any role is a risk signal, not
a performance signal. Capacity above 80 percent leaves no buffer for scope-creep
absorption, quality review cycles, sick leave, or unexpected client escalations.
A studio running above 80 percent sustained is borrowing against team health.

## Billable-Rate Discipline

Rate cards are the studio's pricing architecture. They encode the value delivered
per role relative to market rate and studio cost structure. Rates that drift through
informal discounting destroy margin without a corresponding scope signal.

### Per-Role Rate Card

Each billable role carries a published rate. The rate card is reviewed at minimum
annually against market benchmarks and studio cost structure. A role whose market
rate has moved more than 15 percent since the last review is repriced on new
engagements; existing retainers are renegotiated at renewal.

### Blended-Rate Discipline

Blended rates (a single rate applied across a project regardless of role mix) are
used only when the scope requires it contractually. When a blended rate is applied,
the underlying role-mix assumption is documented and tracked. If the actual role
mix diverges from the assumption by more than 10 percent of total hours, the blended
rate is reviewed mid-project.

### Rate-Discount Rule

A discount to the published rate is approved only when accompanied by a documented
scope reduction, a volume commitment that justifies the rate, or a strategic account
classification ratified by studio leadership. An informal discount granted to avoid
scope negotiation is a scope-creep subsidy paid from margin. No rate discount is
applied without a written record of the justification.

## Capacity Planning

Capacity planning is the discipline of matching available studio capacity to forward
demand before demand arrives, not after. Reactive staffing — hiring when overwhelmed
or cutting when idle — destroys both talent retention and margin predictability.

### 90-Day Forward Staffing

Capacity is modelled 90 days forward by role and discipline. Inputs are confirmed
retainers, pipeline-stage-weighted project starts, and historical demand seasonality.
The model is refreshed monthly. A capacity gap identified at 60 days is manageable;
a gap identified at 10 days is a crisis.

### Bench Economics

Bench capacity — time held by salaried staff not allocated to billable or PD work —
has a direct cost. Bench is acceptable in limited quantities as a buffer and ramp
resource; bench that persists beyond 4–6 weeks for a given role is either a hiring
error or a demand forecasting failure. Both are corrected, not carried.

### Per-Skill-Set Demand Forecasting

Capacity planning tracks demand by skill set, not only by headcount. A studio that
is at full headcount but short on a specific specialisation (motion, data
visualisation, content strategy) has a capacity gap invisible to headcount-only
models. Skill-set demand is tracked in the capacity model as a distinct dimension.

### Bench Decay Prevention

An unallocated staff member whose bench time exceeds 3 weeks without an assigned PD
plan or a confirmed upcoming project is escalating. Bench time without a plan is
attrition risk and skill stagnation; it is addressed within the weekly resource
review, not deferred to the next 1:1 cycle.

## Project Profitability

Per-project profitability is measured during execution, not at invoice. A project
whose margin is discovered post-delivery cannot be corrected. Margin tracking during
execution enables scope-creep intervention before the damage is absorbed.

### Per-Project Margin Model

Every project carries a budget model that converts scope to hours by role, applies
the role rate card, and derives an expected gross margin. The model is live — actual
hours logged are compared to the budget weekly. A project that has consumed 60
percent of the hour budget at 40 percent of scope completion triggers a scope review.

### Scope-Creep Detection

Scope creep is detected by tracking hours per deliverable against the scoped estimate,
not by tracking total project hours against a lump-sum budget. Lump-sum tracking
masks where creep is occurring. Per-deliverable tracking identifies the work item
driving overrun and supports a change-order conversation grounded in evidence.

### Change-Order Discipline

When scope expands beyond the contracted definition, a change order is raised before
the additional work is executed. A change order documents the scope addition, the
incremental hour and cost estimate, and the revised margin impact. Work executed
without a change order in place is margin written off. The change-order threshold
is set by studio policy, not by individual project lead discretion.

### Scope-Creep Absorption Rule

Scope creep is never absorbed silently. A client relationship that depends on
uncompensated scope expansion is a loss-leader relationship that is explicitly
classified and reviewed against strategic account criteria. Silent absorption as a
client satisfaction strategy is not a strategy — it is deferred recognition of a
margin problem.

## Retainer-vs-Project Mix

Retainer revenue provides monthly cash-flow predictability and reduces pipeline
pressure on new project starts. Project revenue provides upside and margin optionality.
Both are necessary; managing the ratio is a studio-level strategic decision.

### Revenue Mix Targets

Studios with fewer than twenty full-time equivalents benefit from retainer coverage
of 40–60 percent of monthly revenue. Below 40 percent, cash-flow variance makes
staffing decisions reactive. Above 70 percent, retainer rate compression risk and
scope-drift risk accumulate across the portfolio.

### Retainer Scope Management

A retainer that has accrued informal scope additions over two or more renewal cycles
has become an underpriced project. Retainer scope is audited at every renewal against
the original statement of work. Additions are formalised, priced, and included in the
renewed rate.

### Single-Client Revenue Concentration

No single client represents more than 25 percent of total studio revenue. A client
above this threshold is a concentration risk: a pause, budget cut, or relationship
change at that client creates a studio-level cash-flow event. Concentration above
25 percent is a documented risk requiring an active diversification plan, not a
revenue achievement to be celebrated.

### Minimum Viable Retainer Size

Retainers below a minimum viable size (typically four to eight hours per month per
discipline) create administrative overhead disproportionate to revenue. Below-threshold
retainers are declined or converted to project engagements.

## Freelance-Network Management

A freelance network extends studio capacity without fixed overhead. It also extends
studio liability if not managed with the same rigour applied to permanent staff.

### Vetted Bench Requirement

Freelancers engaged for client work must be on the studio's vetted bench before being
introduced into a client-facing workflow. Vetting covers quality portfolio review,
one or more paid internal test assignments, reference verification, and documentation
completion. An unvetted freelancer introduced directly to client work is a quality
and relationship risk with no prior evidence baseline.

### Required Paper Trail

Every freelance engagement carries a written agreement covering: scope, deliverable
definition, rate, payment terms, confidentiality, IP assignment, and data-handling
obligations. A verbal agreement or email thread is not a freelance contract. Absence
of IP assignment is a downstream IP ownership dispute.

### IP Assignment

All work product created by a freelancer for a client engagement is assigned to the
studio (or directly to the client per the client contract) in writing before work
begins. A freelancer who has not signed an IP assignment agreement does not begin
client-facing work.

### Data-Handling Obligations

Freelancers who access client data, brand assets, or confidential materials sign a
data-handling addendum specifying access scope, retention limits, and deletion
obligations at engagement end. This applies to all client work regardless of
project sensitivity. Data-handling obligations are not optional for low-sensitivity
engagements.

## Studio-Margin Economics

Gross margin is the primary financial health indicator for a service studio. It
measures the spread between revenue and the direct cost of delivery before studio
overhead. A studio that does not track gross margin by client is managing revenue
without managing the business.

### Gross Margin Target

Target gross margin for a healthy creative studio is above 50 percent. Margin below
40 percent on a sustained basis indicates rate compression, scope-creep absorption,
or delivery inefficiency that cannot be sustained without structural intervention.
Margin above 65 percent indicates either exceptional rate positioning or under-investment
in delivery quality — both warrant examination.

### Per-Client Margin Variance

Gross margin is tracked per client, not only at portfolio level. A portfolio-average
margin of 52 percent can mask individual client relationships at 20 percent that are
subsidised by relationships at 70 percent. Per-client visibility enables renegotiation
or relationship reclassification decisions grounded in data rather than perception.

### Loss-Leader Risk

A client relationship classified as a loss-leader — accepted below target margin
for strategic, referral, or portfolio reasons — is a documented decision with explicit
exit criteria: a timeline by which the relationship either reprices to target margin
or is wound down. An undocumented loss-leader is a permanent subsidy.

## Anti-patterns

| Anti-pattern | Detection signal | Corrective action |
|---|---|---|
| Utilisation above 80% treated as success | Senior staff booking 85%+ for three or more consecutive weeks with no PD or buffer time | Redistribute load; initiate capacity planning conversation before burnout manifests |
| Scope-creep absorbed silently | Project hours overrun budget by 15%+ without a change order raised | Audit per-deliverable hours; raise change order retroactively or reclassify as loss-leader with documented exit criteria |
| Single client above 25% revenue | Monthly client revenue concentration review shows one client exceeding threshold | Initiate active diversification plan; set 18-month reduction target; document risk |
| Freelance engagement without paper trail | Freelancer starts client work before agreement and IP assignment are countersigned | Halt client-facing work; complete documentation; apply vetted-bench requirement retroactively to all active freelancers |
| Bench allowed to rot | Staff member unallocated beyond 3 weeks without PD plan or upcoming project | Assign to structured internal project or PD track within 5 business days; escalate if pipeline cannot absorb within 30 days |
| Project margin not tracked during execution | Margin is first calculated at invoice stage; no per-deliverable hour tracking in progress | Implement per-project budget model with weekly actuals; enforce tracking at PM level, not finance level |
| Rate discounted without scope reduction | Client rate below card with no documented volume commitment, scope reduction, or strategic account rationale | Require written justification for all below-card rates; enforce change-order discipline on scope additions post-discount |

## Cross-References

- `domains/business-support/skills/finance-tracker` — studio-level P&L, cash-flow
  forecasting, and cost structure modelling that sits above per-project margin tracking.
- `domains/project-management/skills/project-shepherd` — individual project execution
  discipline including scope management, milestone tracking, and stakeholder communication.
- `domains/sales/skills/proposal-strategist` — pricing narrative and profitability
  assumptions that feed directly into the per-project margin model at proposal stage.

## ADR Anchors

- **ADR-058** — Domain skill authoring standards; governs tier assignment, scope_tags
  format, frontmatter required fields, and the structural_inspiration relationship
  classification used in `inspired_by` entries for this file.
