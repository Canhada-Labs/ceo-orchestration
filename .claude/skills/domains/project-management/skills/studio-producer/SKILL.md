---
name: studio-producer
description: |
  Creative-project producer discipline — scope definition, creative-brief
  authoring, talent and vendor selection, schedule and budget management,
  delivery cadence, client expectations management, and post-mortem.
  Use when: initiating a creative engagement that requires a signed scope
  document before any production work begins; authoring a creative brief
  that must be falsifiable against KPIs; selecting talent or vendors for
  a time-boxed production sprint; running a weekly burn-down against a
  phased production schedule; managing a client relationship where verbal
  scope changes are accumulating; or closing a project with a structured
  retrospective that feeds the skills library.
owner: Renata Voss (Studio Producer, domain persona)
tier: domain:project-management
scope_tags: [studio-producer, creative-brief, schedule-management, budget-management, vendor-selection, client-expectations]
inspired_by:
  - source: msitarzewski/agency-agents/project-management/project-management-studio-producer.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/creative-briefs/**"
  - "**/production/**"
  - "**/post-mortems/**"
---

# Studio Producer

## Cardinal Rule

Scope undefined is scope unbounded; the producer who cannot say "no" on
day one will say "we need more time" on day thirty. Every creative
engagement begins with a written, signed scope document. No brief is
authored, no talent is engaged, no schedule is built, and no budget is
allocated until that document exists and carries explicit client sign-off.
All outputs from this skill are subject to the two-pass review gate
(ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- A creative brief is being authored without a defined problem statement,
  target audience, and at least one falsifiable KPI; a brief that cannot
  be evaluated against objective criteria is an opinion document, not a
  production instrument.
- A production milestone is being scheduled without contingency reserve
  of at least 15 percent; schedules without contingency are commitments
  made on behalf of luck.
- A talent or vendor is being engaged under deadline pressure without a
  portfolio review and at least one reference call; deadline pressure does
  not reduce the probability of a quality miss — it amplifies it.
- A verbal scope change from a client is being absorbed into production
  without written confirmation; verbal changes are not scope changes until
  documented.
- A project is being closed without a post-mortem scheduled; institutional
  learning that is not captured is lost permanently.

Never allow delivery pressure to compress the scope-definition or
brief-authoring phase; compression at the front of a production cycle
produces re-work at the back at a rate that consistently exceeds the
time saved.

## When to Apply

Apply this skill when:

- A creative project is being initiated and scope boundaries, deliverable
  formats, revision counts, and out-of-scope exclusions have not been
  formally documented and signed.
- A creative brief must be authored for an internal or external creative
  team and the brief must be treated as a falsifiable production contract
  rather than a mood board.
- Talent or vendors must be selected for a production sprint and the
  selection must be defensible against portfolio evidence, reference
  feedback, and rate fit.
- A production schedule is being built and per-stage milestones,
  contingency allocation, and burn-down cadence must be established before
  creative work begins.
- Client communications are accumulating scope requests and a protocol for
  written confirmation, change-order issuance, and schedule impact
  assessment is needed.
- A project has concluded and a structured retrospective must be captured
  in the skills library before the team disperses.

Do not apply this skill to product-roadmap management or engineering
sprint planning; route those contexts to
`domains/project-management/skills/project-shepherd` or
`core/engineering-practices`.

## Scope Definition Discipline

Scope is defined before any other production activity. A scope document
that is missing any of the four components below is incomplete and cannot
serve as the basis for scheduling, budgeting, or talent engagement.

**Required scope components:**

| Component | Definition | Failure signal |
|-----------|-----------|----------------|
| Deliverable list | Enumerated outputs with format, resolution, and file-type specification | "Assets as needed" or open-ended output descriptions |
| Format specification | Per-deliverable technical requirements (dimensions, codec, file format, platform destination) | Missing technical spec for any deliverable |
| Revisions allowed | Numeric limit per deliverable per production phase | No revision cap or "unlimited revisions" language |
| Out-of-scope explicit | Written list of what the engagement does NOT produce | Absence of exclusions; exclusions are not implied by inclusions |

**Scope sign-off protocol:**

The scope document is presented in writing, reviewed with the client in
a synchronous session, and signed before the project enters the brief-
authoring phase. Partial sign-off (client approves some scope components
verbally) does not constitute sign-off. A project that enters production
without a signed scope document is operating outside this skill's
governance and any resulting schedule or budget deviation is attributable
to that gap.

## Creative Brief Authoring

A creative brief is a falsifiable production contract. A brief that
cannot be evaluated against objective criteria at delivery is a
preferences document and cannot govern revision disputes.

**Required brief components:**

| Component | Content | Falsifiability requirement |
|-----------|---------|---------------------------|
| Problem to solve | Business or communication problem the creative must resolve | Must be testable at delivery (e.g., "increase email open rate by 15 pp") |
| Target audience | Demographic, psychographic, and behavioral specification | Must be specific enough to exclude; "everyone" is not a target |
| Core message | Single claim the audience must retain after exposure | Must be evaluable via recall or comprehension test |
| Mandatory elements | Brand marks, legal copy, required assets, platform specs | Enumerated; no "per brand guidelines" pass-throughs |
| Constraints | Budget ceiling, timeline, technology, and rights restrictions | Numeric and specific; "reasonable budget" is not a constraint |
| KPI | Quantified success metric tied to the problem statement | Numeric and time-bounded; "improve awareness" is not a KPI |

**Brief revision protocol:**

Revisions to the brief after creative production has begun are scope
changes. Each post-production-start brief revision triggers a change-
order request, a schedule impact assessment, and a budget impact
assessment before work on the revised direction begins. Brief revisions
that are absorbed without a change order are scope creep with a polite
name.

## Talent and Vendor Selection

Talent and vendor selection is a deliberate process governed by
portfolio evidence, reference feedback, and rate fit evaluated
against the production scope. The selection decision is documented
before any engagement begins.

**Per-discipline evaluation criteria:**

- **Portfolio review:** Minimum three comparable projects in the
  discipline; comparable means matching deliverable type, format
  complexity, and production scale — not matching aesthetic preference.
- **Reference call:** At least one client reference for a project of
  comparable scope; the reference call is structured around three
  questions: quality of final deliverable, adherence to schedule, and
  communication under pressure.
- **Rate fit:** Rate is evaluated against the project budget after
  portfolio and reference criteria are satisfied; rate is never the
  primary filter because it selects for unavailability.

**Prohibitions:**

- Blind engagement under deadline pressure: deadline urgency increases
  the operational risk of a quality miss and does not constitute
  justification for skipping portfolio or reference review.
- Single-source engagement: any discipline that has only one evaluated
  candidate carries unmitigated delivery risk; bench depth of at least
  two qualified candidates per discipline is required before production
  begins.
- Retroactive rate negotiation: rates are agreed in writing before work
  begins; retroactive rate changes after delivery are relationship-
  damaging and operationally unjustifiable.

## Schedule and Budget Management

Schedules and budgets are built per production phase, with contingency
allocated before the first deliverable is due. A schedule without
contingency is a plan to be late.

**Per-phase milestone structure:**

Each production phase requires: a defined input (what must be true to
begin), a defined output (what constitutes completion), a duration in
working days, a contingency allocation expressed as a percentage of
phase duration, and an assigned owner. Phases without defined inputs or
outputs cannot be tracked to completion.

**Contingency allocation rules:**

- Minimum 15 percent contingency on any single-phase duration.
- Minimum 20 percent contingency on total project schedule for projects
  with three or more external dependencies (client approvals, third-party
  assets, platform submissions).
- Contingency is a planning instrument, not a slack buffer; contingency
  consumed by avoidable delays is a signal of scope-definition or
  brief-authoring failure, not schedule conservatism.

**Weekly burn-down discipline:**

- Weekly burn-down review is mandatory from project kickoff to delivery.
- Burn-down report includes: budget consumed to date, budget remaining,
  schedule days consumed, schedule days remaining, and a risk flag for
  any phase that has consumed more than 110 percent of its planned
  duration.
- A late flag is issued the moment a phase exceeds its planned duration
  plus contingency, not after the phase is complete. Late flags are
  communicated to the client proactively before the client asks.

## Delivery Cadence

Delivery is governed by review checkpoints and per-phase sign-off.
No subsequent phase begins without sign-off on the preceding phase.

**Review checkpoint requirements:**

- Internal QA review before any deliverable is presented to the client;
  deliverables that have not passed internal QA are not client-ready
  regardless of deadline pressure.
- Per-phase client review session: synchronous, agenda-prepared, with
  feedback captured in writing during the session and confirmed by the
  client within 24 hours.
- Per-phase sign-off document: written client confirmation that the phase
  output meets the brief before the next phase begins.

**Sign-off protocol:**

Sign-off is written and specific. "Looks good" in a chat channel is not
sign-off. Sign-off documents the deliverable version, the date, and the
client name. Signed-off phases are frozen; changes to a signed-off phase
are change orders, not revisions.

## Client Expectations Management

Proactive communication is the primary expectation-management tool.
Bad news delivered early is a problem to solve; bad news delivered late
is a trust breach.

**Communication discipline:**

- Weekly status update regardless of whether the client has asked;
  clients who must ask for status are clients who are beginning to worry.
- Schedule or budget impact is communicated to the client before the
  impact materializes, not after; retroactive disclosure of a miss is
  a credibility event.
- Never overpromise on scope, schedule, or quality to resolve a client
  concern; an overpromise deferred is a miss compounded.
- Verbal change requests from the client are acknowledged, documented,
  and responded to with a written change-order assessment before any
  production work on the change begins.

**Written confirmation of verbal changes:**

All scope, schedule, or deliverable changes discussed verbally are
confirmed in writing within 24 hours of the conversation. The written
confirmation includes: the change described in deliverable terms, the
schedule impact, the budget impact, and a request for written client
approval before work proceeds.

## Post-Mortem Discipline

Every project concludes with a structured post-mortem. Projects that
are closed without a post-mortem forfeit the institutional learning
that justifies the project's cost to the organization.

**Post-mortem structure:**

| Section | Content | Output |
|---------|---------|--------|
| What worked | Processes, decisions, or team configurations that produced better-than-expected outcomes | Retained practice entry for skills library |
| What did not work | Processes, decisions, or gaps that produced rework, missed milestones, or client friction | Anti-pattern entry for pitfalls catalog |
| Change for next | Specific, actionable changes to scope definition, brief authoring, vendor selection, scheduling, or delivery process | Process update or ADR amendment if structural |
| Library entry | Post-mortem summary filed in the project archive | Mandatory; post-mortem not filed = post-mortem not done |

**Post-mortem gate:**

The project is not marked complete until the post-mortem library entry
is filed. Post-mortem is never skipped on the grounds that the project
went well; projects that went well contain the highest-value retained
practices.

## Anti-patterns

| Anti-pattern | Consequence | Correct Approach |
|--------------|-------------|-----------------|
| Undefined deliverable scope at project start | Unlimited revision exposure; client and producer operate on different mental models of completion | Author and sign a four-component scope document before any other production activity |
| No falsifiable KPI in the creative brief | Revision disputes are subjective; delivery is never demonstrably complete | Each brief must contain at least one numeric, time-bounded KPI tied to the problem statement |
| Ad-hoc review scheduling | Review preparation is inadequate; feedback is incomplete; phases slip | Establish per-phase review checkpoints at project kickoff; no phase ends without a scheduled review |
| Absorbing verbal scope changes into production | Budget and schedule overruns attributed to "client requests"; no audit trail for contractual disputes | All scope changes receive a written change-order assessment and written client approval before work begins |
| Blind talent hire under deadline pressure | Quality miss or missed deadline; downstream phases cascade | Deadline pressure does not waive portfolio review and reference call requirements |
| Hidden budget burn | Client discovers overrun at delivery; trust breach and potential contract dispute | Weekly burn-down report issued regardless of burn rate; overrun flags are proactive, not retrospective |
| Missed review checkpoint | Phase output locked in wrong direction; rework cost exceeds the checkpoint time saved | No phase advances without written sign-off on the preceding phase; checkpoints are mandatory, not advisory |
| No post-mortem | Institutional learning lost; same failure modes repeat across projects | Every project concludes with a post-mortem filed in the project archive before the project is marked complete |

## Cross-References

- `domains/project-management/skills/studio-operations` — operational
  infrastructure for a running studio: capacity planning, toolchain
  governance, and rate-card management
- `domains/sales/skills/proposal-strategist` — commercial framing of
  creative engagements: proposal structure, pricing strategy, and
  closing mechanics
- `domains/marketing-global/skills/content-creator` — content production
  execution within a scoped creative brief; downstream of this skill in
  the production chain

## ADR Anchors

- **ADR-058** — two-pass review gate: all scope documents, creative
  briefs, talent-selection records, and post-mortem library entries
  produced under this skill are subject to adversarial second-pass
  review before being treated as final outputs.
