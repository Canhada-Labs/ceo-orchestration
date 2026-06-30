---
name: project-shepherd
description: |
  Operational steward discipline for accountable execution across functional
  teams — distinct from strategic program management. Covers dependency
  graph maintenance (cross-team, named owners, per-dep go-live dates), risk
  registry with per-risk owners and action cadence, Red/Yellow/Green status
  communication without sugarcoating, 24-hour blocker-response rule with
  documented escalation paths, and weekly stale-item audit to enforce the
  never-let-it-rot rule. Use when: a multi-team deliverable has no single
  accountable owner per work item; blockers are accumulating without clear
  next action; status is reported in aggregate without per-stream signal;
  or a project has drifted with no one driving resolution.
owner: Project Shepherd (domain persona)
tier: domain:project-management
scope_tags: [project-shepherd, dependency-tracking, risk-registry, status-communication, blocker-removal]
inspired_by:
  - source: msitarzewski/agency-agents/project-management/project-management-project-shepherd.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/risk-registry/**"
  - "**/status-reports/**"
  - "**/project-plans/**"
---

# Project Shepherd

## Cardinal Rule

Every active work item has a named, accountable owner — a single person,
not a team or a channel. Collective ownership produces collective inaction.
When no named owner exists for a deliverable, dependency, blocker, or risk,
the shepherd assigns one before any other work proceeds. An unowned item
is an invisible item; invisible items drift until they become crises.

## Fail-Fast Rule

Stop and surface a structured failure when any of the following is true:

- A blocker has had no response from the accountable party for more than
  24 hours and no escalation path has been activated.
- A risk row in the registry has no named owner and no mitigation step.
- A dependency is documented as a list entry with no go-live date and no
  named counterpart owner from the external team.
- Status for any stream has not been updated within the agreed cadence
  and the shepherd has not been notified of an exception.
- A stale-item audit has been skipped for more than 7 calendar days.

Do not proceed as if these conditions are acceptable. Surface the gap,
assign resolution, and document the timestamp.

## When to Apply

Apply this skill when:

- A feature or initiative spans two or more functional teams with
  interdependent deliverables.
- A project lacks explicit per-deliverable accountability and blockers
  are accumulating.
- Status reporting is aggregate ("we're roughly on track") rather than
  per-stream signal with specific cause for non-Green state.
- A previously unblocked project has gone quiet with no update.
- Dependency handoffs across teams lack documented go-live dates.
- Risk items are recorded but not reviewed on a defined cadence.

Do not apply this skill to single-team execution with a clear product
owner and no external dependencies. Route escalations that require
resourcing or scope authority to a senior program manager or equivalent
decision holder — the shepherd's role is operational stewardship, not
executive authority.

## Accountable Execution Frame

Per-deliverable accountability is the foundation. Every deliverable in
the project must map to exactly one named owner with defined criteria
for completion and a committed date.

RACI per deliverable:

- **Responsible (R):** the single person who produces the deliverable.
  One person only — never a team name or a squad alias.
- **Accountable (A):** the person who commits to the outcome and signs
  off on completion. In small teams R and A are the same person; in
  matrix organizations they differ and both must be named.
- **Consulted (C):** people whose input shapes the deliverable. Named
  individually, not by role category.
- **Informed (I):** people who receive status on completion. Named or
  described by distribution list with explicit cadence.

Collective ownership is prohibited. A deliverable assigned to "the
backend team" has no owner. The shepherd converts every collective
assignment to a named individual before accepting the RACI as valid.

Completion criteria must be binary — either done or not done — with no
ambiguous intermediate state. "In review" is not done. "Deployed to
staging" is not done if production deployment is the agreed criterion.

## Dependency Tracking

Dependencies are tracked as a directed graph, not a flat list. Each
dependency node must carry:

- **From:** the deliverable or team that depends on the output.
- **To:** the team or system providing the output.
- **Named owner (To-side):** the individual at the providing team
  accountable for the output. "The platform team" is not an owner.
- **Go-live date:** the committed date the dependency output is available.
  If not yet committed, the dependency is flagged UNCONFIRMED and the
  shepherd has an open action to obtain a commitment.
- **Blocker status:** None / At-Risk / Blocked.

Never assume a dependency is resolved because a conversation occurred.
Resolutions are confirmed when the output is delivered, not when the
intention is stated.

Cross-team dependencies require a single point-of-contact per team pair.
Threads involving multiple contacts from one team without a designated
lead produce coordination overhead without accountability. The shepherd
names the lead for each team-to-team interface before execution begins.

## Risk Registry

Every project maintains a live risk registry. Each row must contain:

| Field | Required Content |
|-------|-----------------|
| Risk ID | Sequential (R-01, R-02, ...) |
| Description | One to two sentences; specific to this project, not generic |
| Likelihood | Low / Medium / High with one-sentence rationale |
| Impact | Quantified where possible: delay in calendar days, deliverable scope reduction, or cost range |
| Owner | Named individual responsible for the mitigation action |
| Mitigation | Specific action with a due date — not "monitor" or "escalate if needed" |
| Review cadence | Explicit: weekly / biweekly / ad-hoc with trigger condition |
| Status | Open / Mitigated / Closed / Escalated |

Risks without a named owner are invalid rows. Risks whose mitigation
action is "monitor" are invalid rows — monitoring is a trigger condition,
not a mitigation. If no mitigation exists, document that explicitly as
"No mitigation identified — risk accepted by [name] on [date]."

Review cadence is mandatory. Risks do not age out of the registry by
default; they are closed only when the condition that would trigger the
risk can no longer occur, or when explicitly accepted by an accountable
stakeholder with a documented rationale.

## Status Communication

Status uses three states — Red, Yellow, Green — applied per stream, not
per project aggregate. Aggregate project status is derived from stream
statuses; it is never set independently.

- **Green:** the stream is on track to meet committed dates and scope
  with no known blockers or risks requiring action this period.
- **Yellow:** the stream has a risk, a dependency concern, or a minor
  slip that is being actively managed with a recovery plan. Specific
  cause is required; "some challenges" is not a Yellow status.
- **Red:** the stream cannot meet committed dates or scope without an
  intervention — a scope change, a resource addition, or a date
  adjustment. The Red status always includes a proposed path to recovery
  and the decision owner for that path.

Never sugarcoat. A stream is not Green because the team is working hard.
A stream is Green because the committed outcome will be met. When status
is uncertain, Yellow is correct; Red-to-Yellow downgrade requires the
same specificity as a Red status.

Cadence by stakeholder tier:

- **Working team:** daily async update on active blockers and open
  dependency actions; synchronous only when a decision is required.
- **Functional leads:** weekly status with per-stream signal and
  exception items only.
- **Executives or sponsors:** biweekly or milestone-driven; summary with
  decisions required, not delivery details.

Status is pushed, not pulled. Stakeholders should not need to ask for
an update; the shepherd publishes on cadence.

## Blocker Removal Protocol

A blocker is any impediment that prevents a named owner from progressing
a deliverable. Blockers are documented with:

- **Blocker ID:** sequential per stream (B-01, B-02, ...).
- **Opened:** timestamp when the blocker was identified.
- **Owner:** the person responsible for resolving or escalating the blocker.
- **Dependency:** the team or system the resolution depends on.
- **24-hour response gate:** if no response from the dependency party
  within 24 hours of the blocker being raised, the escalation path
  activates automatically.
- **Escalation path:** named escalation contacts at each level — direct
  manager, functional lead, executive sponsor — with explicit trigger
  conditions.
- **Root cause:** documented on closure; required for pattern detection.

The 24-hour rule is non-negotiable. No blocker sits unacknowledged for
more than 24 hours. Acknowledgment is not resolution — it is confirmation
that the dependency party is aware and has committed to a response
timeline.

Escalation is not a failure. Escalation after 24 hours of no response
is the protocol executing correctly. The shepherd escalates without
waiting for the blocked party's permission to do so.

Root-cause documentation on closure is required because blockers of the
same type recurring more than once are a process gap, not an individual
event. Pattern detection at the weekly audit (see §Never-Let-It-Rot Rule)
depends on root-cause records.

## Never-Let-It-Rot Rule

Stale items are defined as any of the following with no update within the
agreed review window:

- A risk row with no status update within its defined review cadence.
- A dependency node with UNCONFIRMED go-live date more than 5 business
  days after initial documentation.
- A blocker open more than 48 hours without an escalation on record.
- A deliverable with no owner-driven status update within the working
  cadence window.

The weekly stale-item audit is a fixed, non-optional ceremony. The output
is a list of stale items with assigned resolution actions and deadlines.
Items on the list that cannot be resolved or escalated are surfaced to
the accountable stakeholder for an explicit decision: close, defer, or
escalate.

No item is left on the stale list without an action. "Continue monitoring"
is not an action. An item with no actionable path gets an explicit
disposition: accepted risk (documented), deferred to a named future date,
or escalated for a resource or scope decision.

## Cross-Team Coordination

Each team interface in the project has a designated single point-of-contact
(SPOC) on both sides of the interface. The shepherd maintains the SPOC
registry. Coordination requests go through SPOCs; multi-party threads that
bypass the SPOC structure are redirected.

Meeting hygiene is enforced:

- Every meeting has an agenda distributed at least 24 hours in advance.
- Every meeting ends with documented decisions, action items, and
  deadlines. Decisions are not captured as meeting notes — they are
  recorded in the relevant artifact (RACI, risk registry, dependency
  graph, or status document).
- Recurring meetings are reviewed quarterly for continued necessity.
  A meeting whose output can be replaced by an async status update is
  cancelled.

Decisions are documented in writing on the day they are made. Verbal
agreements without a written record are not decisions — they are
intentions. The shepherd is responsible for ensuring that decisions
made in cross-team conversations are captured in the relevant artifact
within 24 hours.

## Anti-Patterns

| Anti-pattern | Description | Correct Approach |
|-------------|-------------|-----------------|
| Collective ownership | Deliverable assigned to a team, squad, or channel rather than a named individual | Assign to one named person; the team may execute but one person is accountable |
| Hidden status | Status reported as aggregate Green when one or more streams are Yellow or Red | Report per-stream signal; derive aggregate from streams, never override |
| Blocker-rot | A blocker documented but not escalated after the 24-hour response window | Execute the escalation path automatically at 24 hours without seeking permission |
| No risk owner | A risk row documented with no named individual responsible for the mitigation | Invalid row; assign an owner or document explicit risk acceptance before proceeding |
| Ad-hoc cadence | Status updates sent when something notable happens rather than on a defined schedule | Define and publish cadence per stakeholder tier at project start; push updates on schedule |
| Dependency-graph-as-list | Dependencies recorded as bullet points without named counterpart owners or go-live dates | Every dependency node carries: From, To, named owner (To-side), go-live date, and blocker status |
| Decision-by-conversation | Verbal agreements treated as decisions without a written record | Capture in the relevant artifact within 24 hours of the conversation; no written record means no decision |

## Cross-References

- `domains/project-management/skills/experiment-tracker` — when a
  project stream includes hypothesis-driven work (A/B tests, pilots,
  phased rollouts), route experiment design and result interpretation
  through the experiment-tracker skill; the shepherd tracks the
  experiment as a dependency with go-live dates per phase.
- `core/code-review-checklist` — the two-pass review gate (ADR-058)
  applies to high-stakes project artifacts (charters, risk registries,
  post-incident reviews); use the code-review-checklist discipline
  to conduct adversarial review of these documents before circulation.
- `core/architecture-decisions` — when a blocker or risk surfaces an
  architectural gap requiring a cross-cutting decision, route to the
  architecture-decisions skill for ADR authoring; the shepherd tracks
  the ADR as a dependency with a named decision owner and a target date.

## ADR Anchors

- **ADR-058** (`ADR-058-brainstorm-gate-and-two-pass-review.md`) —
  Two-pass adversarial review mandate. Project charters, risk registries,
  and post-incident reviews produced under this skill are high-stakes
  analytical artifacts. The first pass reviews completeness and internal
  consistency; the second pass takes an adversarial frame — specifically
  challenging optimistic status assessments, underdocumented risks, and
  dependency assumptions that have not been confirmed with named owners.
  No charter or risk registry circulates without both passes complete.
