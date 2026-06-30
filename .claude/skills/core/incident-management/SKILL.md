---
name: core-incident-management
description: Live-incident operational doctrine for the {{PROJECT_NAME}} —
  severity classification, role assignment under load, escalation discipline,
  blame-free post-incident review, communication cadence, and rollback-first
  bias. Use when an alert fires, when a user-reported outage is being triaged,
  when designing on-call rotations, when authoring or reviewing an incident
  runbook, when facilitating a post-incident review, or when reviewing any
  change that affects detection, paging, or recovery surface area. The
  authority on declaring severity, assigning the commander role, and ending
  an incident is a VETO-floor responsibility paired with the framework's
  release-gate and security disciplines.
owner: Incident Commander (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-incident-response-commander.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/strategy/runbooks/scenario-incident-response.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: severity_scale
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 3
risk_class: high
stack: []
context_budget_tokens: 800
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)incident|outage|postmortem|sev"}
---

# Incident Management

## Fail-Fast Rule

When an alert is real, **declare and assign before you investigate**. Never
defer severity classification while you "look around for two minutes" — the
two minutes become twenty, and nobody is in charge while it happens. Never
silence a page without a written reason in the incident channel. Never end
an incident on the basis of "metrics look better" alone; recovery is
confirmed by user-facing verification AND a sustained observation window
AND no fresh alerts in that window. If any of those three are missing, the
incident is still open.

## What This Skill Is (and isn't)

This is operational doctrine for handling production incidents — declaring,
running, ending, and learning from them. It pairs with `core/observability-and-ops`
(which tells you how to *see* the system) and `core/chaos-and-resilience`
(which tells you how to *design for* failure). When an alert fires, this
skill answers: who is in charge, what gets said, what gets done first, and
how the post-incident loop closes.

This skill is NOT a runbook. Per-service runbooks live next to the service
they cover — this skill governs the meta-process that all runbooks share.
When in doubt about whether a given page is operational doctrine or a
service-specific procedure, consult `docs/MECHANISM-SELECTION.md` §Quick
flowchart: if the content is reusable across services, it is doctrine
(this skill); if it is `kubectl` / `psql` / cloud-CLI invocations specific
to one service, it is a per-service runbook stored next to that service.

## Severity Schema

The framework uses a four-band schema. Bands are mutually exclusive — a
single incident has exactly one severity at any moment, and changes to
severity are logged events with a timestamp and reason.

| Band  | Trigger conditions                                                                              | Initial response | Update cadence | Auto-escalation                |
|-------|------------------------------------------------------------------------------------------------|-----------------|----------------|---------------------------------|
| SEV1  | Total outage of a tier-1 service; suspected data loss; suspected breach; pay-flow halted        | Page primary; declare within 5 min | Every 15 min, even with no change | Doubling impact → already SEV1 |
| SEV2  | Partial outage affecting >25% of a tier-1 surface; degraded SLO; one paying tenant down hard    | Page primary; declare within 15 min | Every 30 min | Cross 50% impact → upgrade SEV1 |
| SEV3  | Single feature broken with workaround; non-paying tenant impact; fast-recoverable degradation   | Acknowledge in 1 hour | Every 2 hours during waking hours | Workaround fails → upgrade SEV2 |
| SEV4  | Cosmetic / docs / known-issue with no user-visible impact; signal worth tracking but not paging | Next business day | At triage only | n/a — escalation means re-classify |

Three rules govern severity:

1. **Severity is set by impact, not by guesswork about cause.** "We don't
   know yet" maps to "use the worst plausible band consistent with what
   you do see." A 5xx spike that *might* be a deploy regression is at least
   SEV2 until proven otherwise.
2. **Customer-paying-account impact is a hard floor of SEV2.** Non-paying
   accounts can sit at SEV3 by default.
3. **Severity downgrades happen only after mitigation is confirmed and a
   verification window has elapsed.** Never downgrade because "we think
   we know what's going on now."

## Roles During an Active Incident

These four roles are non-overlapping. One person holds each at a time.
Role transitions are announced in the incident channel and timestamped.

### Incident Commander (IC)

Owns the incident. Decides what gets tried, what gets stopped, when to
escalate, when to call it resolved. Does NOT type commands into a terminal
during an active SEV1/SEV2 — that is the Technical Lead's job. The IC is
the single decision-maker; everything else is advisory.

### Communications Lead

Owns external + internal updates. Drafts the status-page entry. Posts
cadence updates. Briefs leadership when the severity warrants. Knows the
audience for each channel: customers want impact + ETA, leadership wants
business consequence, engineers want technical state.

### Technical Lead

Owns the keyboard. Runs diagnostic queries, executes mitigation steps,
proposes hypotheses to the IC. Does NOT broadcast updates directly to
users; routes them through the Communications Lead so cadence and tone
stay consistent.

### Scribe

Owns the timeline. Logs every command, every observation, every decision,
with timestamps. The post-incident review depends on this. Without a
scribe, the timeline is reconstructed from memory three days later, which
is when the systemic causes get rationalized away.

For SEV3+ a single engineer may hold IC + Tech Lead + Scribe simultaneously
provided the timeline is logged in real time. SEV1/SEV2 require role
separation.

## CORRECT vs WRONG — declaring an incident

```
# CORRECT
[14:02] alert: api-error-rate > 5% for 90s
[14:03] declare: SEV2, IC=alex, comms=jordan, tech=mei, scribe=sam
[14:03] impact: ~25% of /checkout requests failing in EU-west-1
[14:03] hypothesis: TBD; investigation starting; first update at 14:18
[14:04] @comms: post initial status-page entry now

# WRONG
[14:02] alert fires
[14:04] "let me see what's going on real quick"
[14:11] "wait, also the dashboard is loading slow"
[14:18] "should we maybe declare this?"
```

The wrong pattern wastes the first 16 minutes before the response structure
exists. The correct pattern spends the first 90 seconds installing the
structure, then investigates *inside* it.

## Communication Cadence

Cadence is contractual, not aspirational. Stakeholders learn to trust the
update interval and stop interrupting the response when they can predict
the next message.

### Internal (incident channel)

- SEV1: every 15 min, no exceptions, "no change" is a valid update
- SEV2: every 30 min
- SEV3: every 2 hours

A skipped update is itself an incident-process defect logged in the
post-incident review.

### External (status page + customer comms)

- SEV1: initial post within 10 min of declaration; cadence matches internal
- SEV2: initial post within 30 min
- SEV3: post only if customer-visible AND duration >1 hour

### Leadership

- SEV1: brief at declaration + at every cadence beat
- SEV2: brief at declaration + at resolution
- SEV3/SEV4: include in weekly digest

### Update template

```
# [SEV<N> UPDATE — <service>] <one-line status>
- State: <investigating | identified | mitigating | recovering | resolved>
- Impact: <what users see, scope, geography>
- Working theory: <best current hypothesis or "still narrowing">
- Action in flight: <what we're doing right now>
- Next update: <timestamp>
```

The five fields are mandatory. Filling "working theory" with "investigating"
twice in a row is a signal that the hypothesis loop is stuck and the IC
should consider widening the response team.

## Mitigation Bias: Stop the Bleeding First

The IC's first question is not "what is the cause?" but "what is the
fastest action that ends user impact?" That action is usually one of:

| Mitigation         | When it's right                                                                              | Risk                                    |
|---------------------|----------------------------------------------------------------------------------------------|------------------------------------------|
| Rollback           | Onset within minutes of a deploy / config-push                                               | None if last-known-good is verified clean |
| Feature-flag off   | A specific feature is implicated and the flag exists                                         | Blast radius depends on flag granularity  |
| Failover / shed    | A specific dependency is implicated and a fallback exists                                    | Fallback path must be tested in advance   |
| Scale up           | Saturation symptoms (CPU, queue depth, connection pool) without underlying logic regression  | Masks a real bug; pair with an action item |
| Restart            | State corruption suspected; service is otherwise healthy in code                             | Restart cycles can cascade; cap retries   |

Investigation of root cause is a *parallel* track to mitigation, not a
prerequisite. A SEV1 mitigated by rollback at minute 8 with root cause
identified at minute 45 is a successful response. A SEV1 still in
investigation at minute 30 with no mitigation attempted is a process
failure regardless of how interesting the root cause turns out to be.

### Hypothesis time-boxing

A diagnostic hypothesis gets a budget. Default is 15 minutes. When the
budget elapses without confirmation, the hypothesis is set aside (logged,
not erased) and the next one starts. The IC enforces this — engineers
naturally over-invest in their first guess.

## Ending an Incident

Recovery is a state, not a vibe. Three conditions, all required:

1. **Symptoms gone in observed metrics.** Error rates, latency p99, queue
   depth, whatever the page paged on, back inside SLO with a margin.
2. **User-facing verification.** Someone (Tech Lead, on-call, or the
   Communications Lead via a customer ping) confirms the broken surface
   actually works again. Not "the dashboard says 200 OK" — actually
   exercise the endpoint or the flow.
3. **Sustained observation window.** SEV1 = 30 min watching; SEV2 = 15 min;
   SEV3 = 5 min. No fresh alerts in that window. If anything pops, the
   window restarts.

When all three pass, the IC declares "resolved" in the channel with the
final timeline and the link to the (yet-to-be-written) post-incident
review.

## Post-Incident Review (blame-free)

The review happens within 48 hours of resolution while context is still
recoverable. Attendance is the response team plus anyone whose system was
implicated. Format is a structured document, not a freeform retro.

### Required sections

```markdown
# Post-Incident Review: <service> — <YYYY-MM-DD>

- **Severity:** SEV<N>
- **Duration:** <start UTC> → <end UTC> (<minutes>)
- **Detection latency:** alert-to-declaration
- **Mitigation latency:** declaration-to-symptoms-clear
- **Customer impact:** <quantified — accounts affected, requests failed, $ if known>
- **SLO budget consumed:** <% of monthly>

## Timeline (UTC)
<table from scribe — every state change, decision, and observation>

## What broke (system, not people)
<the failure chain in technical terms; no individual names except in
"who was in IC role" sense>

## Why the safeguards we had didn't catch it earlier
<this is the point of the review>

## Action items
| ID | Action | Type    | Owner | Priority | Due date | State |
|----|--------|---------|-------|----------|----------|-------|
| 1  | …      | detect  | …     | P1       | …        | open  |
| 2  | …      | prevent | …     | P1       | …        | open  |
| 3  | …      | recover | …     | P2       | …        | open  |

## What we got right
<the response patterns to keep>
```

### Action-item discipline

Action items are tagged by type — `detect` (we'd see it sooner), `prevent`
(it can't happen again), `recover` (we'd recover faster) — and tracked to
completion outside the review document. A repeat incident whose action
item from the previous review is still `open` is itself a finding in the
new review. This is how the review loop becomes load-bearing rather than
ceremonial.

### Blame-free framing

Blame-free means findings are framed in terms of system gaps. "Engineer X
typo'd a config" is the wrong framing. "There is no integration test for
config validation; the manual review process is the only safeguard, and
manual review missed a one-character typo" is the right framing. The
people involved are not absent from the document — they wrote the timeline
and they own action items — but their decisions are not characterized as
the cause. The system that *allowed* their decision to reach production
is the cause.

## Anti-Patterns to Reject

| Anti-Pattern | Why it's wrong | Correct approach |
|---|---|---|
| Declaring severity after the response is over | Loses the trigger for cadence + escalation; updates never get written | Declare in the first 5 min; downgrade later if warranted |
| Single person doing IC + tech + comms during SEV1 | Decision-maker is also typing; nobody is reading the metrics | Force role split at SEV1 even if it slows the first 5 min |
| "Let's not page leadership at 3am, it's not that bad" | Severity is set by impact, not by hour; under-paging trains leadership to ignore the channel | If the band says page, page; calibrate the band, not the page |
| Closing an incident on "metrics look better" | The mitigation may be cosmetic; users may still be broken | Three-condition close (metrics + user-facing + sustained window) |
| Skipping the post-incident review for "small" SEV3 | Patterns are learned across small incidents; only writing reviews for SEV1 misses the systemic signal | Every SEV1/SEV2 + every repeat SEV3 gets a review |
| Action items without owners or due dates | The list grows, nothing closes | Owner + due date are mandatory fields; missing fields fail review |
| Same finding in three consecutive reviews | Action item discipline has broken; the system is teaching you nothing | Halt feature work for the affected component until the action item lands |
| Status-page silence during a confirmed customer-visible SEV1 | Users learn from each other on social media first; trust collapses | Initial post within 10 min even if the only content is "investigating" |
| Treating an alert as the trigger to investigate the alert quality | Real alert is happening; tune the alert AFTER, in a follow-up | Action item: "tune `<alert-name>` threshold" — handled in the review, not during |
| Letting the tech lead push code mid-incident without review | Mid-incident hot-fixes are how the recovery becomes its own incident | Rollback first; new code goes through normal review even if expedited |

## On-Call Hygiene

On-call rotations are the input to this whole process — a degraded rotation
produces degraded incidents. The framework's stance:

- **Minimum rotation size of four engineers.** Three rotates engineers
  through primary every third week, which corrodes sleep and judgment.
- **Two-week cap on consecutive primary weeks.** Hand off, rest, return.
- **Shadow before primary.** A new engineer rides along for at least one
  full rotation cycle before holding the pager alone.
- **Pages-per-shift health metric.** Above five pages per engineer per
  week is a signal that alerts are noisy or the system is degraded;
  either way it's a remediation target, not a steady state.
- **Handoff during business hours.** Rotation transitions at 10:00 local,
  not midnight. Engineers should hand context across to a refreshed
  successor, not wake one up to receive it.
- **Pager compensation is non-optional.** This is a stance, not a HR
  policy — when carrying the pager is unpaid, recruitment and retention
  for the senior end of the rotation deteriorate within two quarters.

These items are not enforced by a hook in this framework. They are review
checklist items the Incident Commander archetype consults when reviewing
on-call program proposals.

## Cross-Validation with Other Disciplines

### Release-gate intersection

A live SEV1 freezes new releases of the affected surface until the
post-incident action items are at least scoped (not necessarily landed).
This ties directly to the framework's release discipline (ADR-103
calendar-gate-final-purge — release.yml RC-hold mechanics). Mitigation
deploys are exempt; feature deploys are not.

### Security-and-auth intersection

A suspected breach at any band auto-elevates to SEV1. The Incident
Commander coordinates with whichever archetype holds the security VETO
floor for the framework (ADR-052 multi-model dispatch by role). The IC
does not unilaterally decide a breach is over; the security archetype
signs that off.

### Chaos-and-resilience intersection

`core/chaos-and-resilience` lists known failure scenarios and their
recovery posture. During investigation, the Tech Lead consults that
catalog as the first hypothesis source — many incidents are re-runs of
already-mapped scenarios. After resolution, the post-incident review
updates the catalog with anything new.

### Brainstorm-gate intersection

The post-incident review is a Pass-2 adversarial-framing exercise per
ADR-058 (brainstorm-gate-and-two-pass-review). The reviewer's job is to
disagree with the timeline's framing — to look for the systemic cause
the responders rationalized around. A review that produces zero pushback
on the responders' explanation is a review that hasn't done its job.

## Operating-Mode Selector

| Situation                          | Mechanism the framework expects |
|-------------------------------------|----------------------------------|
| Active SEV1/SEV2 happening now      | This skill loaded into the responding archetype's context |
| Authoring a per-service runbook     | This skill loaded into a Senior Engineer archetype as the meta-doctrine reference; the runbook lives next to the service |
| On-call program review              | This skill + `core/observability-and-ops` loaded into the operations archetype |
| Post-incident review facilitation   | This skill + `code-review-checklist` loaded into the facilitator; ADR-058 Pass-2 framing applied |
| Incident-readiness audit / game day | This skill + `core/chaos-and-resilience` loaded into the auditor; outputs feed the chaos-scenario catalog |

The matrix above is the basis for the Operating-Mode rationale recorded
in `mechanism-selection-rationale.md` alongside this skill — the work is
*persistent doctrine plus role-bearing pattern reference*, which the
mechanism-selection guide maps to a SKILL with a thin task-chain
companion, not a slash-command and not a runbook.

## Success Signals

A working incident-management practice produces:

- Detection-to-declaration latency under 5 min for tier-1 services
- Sustained reduction in median time-to-mitigate quarter over quarter
- Zero repeat incidents whose previous review's action items shipped
- Pages-per-engineer-per-week trending down or stable, not up
- Post-incident review action-item completion >85% within stated due date
- A culture where engineers escalate freely and re-classify upward without
  asking permission

The metrics are lagging indicators. The leading indicator is whether the
roles, cadence, and three-condition close are *actually used* during real
incidents — that is what the SKILL.md exists to govern.

## References

- `core/observability-and-ops` — health-check + metrics design, the input
  to detection
- `core/chaos-and-resilience` — failure-scenario catalog, the input to
  hypothesis generation
- `core/security-and-auth` — auth + breach handling intersection
- `core/code-review-checklist` — adversarial-framing methodology applied
  to the post-incident review
- `ADR-052` — multi-model dispatch by role (VETO-floor invariants this
  doctrine plugs into)
- `ADR-058` — brainstorm gate + two-pass review (Pass-2 framing for
  post-incident review)
- `ADR-103` — calendar-gate-final-purge (release.yml RC-hold mechanics
  intersected by SEV1 freezes)
- `docs/MECHANISM-SELECTION.md` — the flowchart this skill resolves to a
  skill (not a runbook, not a slash-command)
