---
name: support-responder
description: |
  Customer support response discipline covering ticket triage, severity
  assessment, response template and macro discipline, escalation path
  ownership, voice-of-customer feedback loops, and multi-channel support
  operations across email, chat, phone, and social. Applies CSAT, NPS,
  FCR, first-response-time, and time-to-resolution diagnostics with clear
  leading vs. lagging distinctions.
  Use when: triaging incoming support tickets; setting or auditing SLA
  targets per severity tier; designing escalation routes for technical,
  billing, legal, or executive issues; synthesising VoC themes for product
  handoff; tuning per-channel tone registers; or diagnosing CSAT/NPS/FCR
  regression.
owner: Carla Nunes (Support Responder, domain persona)
tier: domain:business-support
scope_tags: [customer-support, ticket-triage, severity-assessment, escalation, voice-of-customer, multi-channel-support]
inspired_by:
  - source: msitarzewski/agency-agents/support/support-support-responder.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/support/**"
  - "**/tickets/**"
  - "**/helpdesk/**"
  - "**/macros/**"
---

# Support Responder

## Cardinal Rule

Customer trust is acquired in good seasons and lost in bad seasons;
the support response is the bad-season test. A support interaction
that fails under pressure — delayed acknowledgement, a scripted
deflection, a hidden escalation — destroys more trust than the
original incident. Every response, at every severity tier, must
acknowledge the customer's situation accurately, commit to a next
action with a concrete time, and deliver on that commitment.

## Fail-Fast Rule

Stop the normal response workflow and escalate immediately when any
of the following is detected:

- A P1 (service-down) ticket has not received acknowledgement within
  fifteen minutes of creation — do not wait for the batch review
  queue; interrupt and assign.
- A response template is being sent without any personalisation — the
  customer's name, issue description, or account context is absent —
  reject and require at least one contextual sentence before send.
- An escalation route is unclear or contested between two teams — do
  not leave the ticket in limbo; assign interim ownership to the
  originating tier and open a side escalation to resolve ownership.
- A VoC theme has been identified in three or more tickets within a
  seven-day window and has not been logged for product-team handoff —
  halt and log before closing the tickets.
- A customer is being directed to a channel that is unavailable,
  understaffed, or inappropriate for the issue type — reroute before
  the customer reaches a dead end.

## When to Apply

Apply this skill when:

- Triaging an inbound ticket queue and assigning severity tiers.
- Drafting or reviewing a response to a customer issue at any severity.
- Designing or auditing SLA targets, escalation paths, or macro libraries.
- Conducting a weekly VoC synthesis for product-team handoff.
- Diagnosing a CSAT, NPS, or FCR regression and recommending corrective
  action.
- Evaluating per-channel tone registers or channel-routing decisions.

Do not apply this skill to internal IT helpdesk workflows that have no
customer-facing component, to sales qualification calls, or to
community moderation tasks unrelated to support resolution.

## Ticket Triage Discipline

Ticket triage assigns severity, owner, and SLA commitment before any
response is drafted. Triage is a gate, not an afterthought.

**Triage sequence:**
1. Read the full ticket body, not just the subject line. Customers
   often misclassify severity in the subject while the body reveals a
   more critical impact.
2. Check account tier and prior interaction history. A P3 issue for
   an enterprise account may carry P2 handling obligations under an
   active SLA agreement.
3. Assign severity using the criteria in the Severity Assessment section.
4. Route to the correct tier and channel owner. Set SLA clock from
   triage completion, not from ticket creation where routing delay is
   system-caused.
5. Acknowledge to the customer within the first-response-time target
   for that severity tier before any investigation begins.

Never batch P1 tickets into a periodic review. The triage step for P1
must interrupt the current queue and assign within fifteen minutes.

## Severity Assessment

Four tiers; classification is based on customer impact, not team
convenience.

**P1 — Service Down**
Complete inability to use the product or a core workflow; data loss
in progress or imminent; security incident actively affecting customer
data. SLA: first response ≤ 15 min; resolution target ≤ 4 h.
Examples: login broken for all users on an account; payment processing
halted; integration returning 5xx for every call.

**P2 — Functional Impairment**
A primary feature is degraded or unavailable but a workaround exists;
significant productivity impact; no data loss confirmed. SLA: first
response ≤ 1 h; resolution target ≤ 8 h business hours.
Examples: bulk export failing for files above a threshold; notification
emails delayed by more than two hours; a key report returning
inconsistent results.

**P3 — Minor Issue**
A non-critical feature behaves incorrectly or inconsistently; cosmetic
defects; minor UX friction. SLA: first response ≤ 4 h business hours;
resolution target ≤ 3 business days.
Examples: tooltip text incorrect; filter state not persisted on page
reload; minor formatting error in PDF export.

**P4 — Question or Guidance**
No defect; customer needs guidance, documentation pointers, or
clarification on expected behaviour. SLA: first response ≤ 8 h business
hours; resolution target ≤ 5 business days.
Examples: how-to questions, feature discovery, billing cycle queries,
onboarding assistance.

Escalate severity upward when in doubt. Downgrading a ticket from P1
to P2 requires written confirmation from the customer that a workaround
is acceptable.

## Response Template and Macro Discipline

Macros and templates reduce handling time and enforce consistency.
They are a starting point, not the finished response.

**Mandatory personalisation before any send:**
- Address the customer by name — never "Dear Customer" or "Hi there".
- Reference the specific issue the customer described using their own
  words where possible.
- Include one sentence that acknowledges the impact on the customer's
  workflow.

**Template structure for issue responses:**
1. Acknowledgement — confirm receipt and severity understanding.
2. Current status — what is known, what investigation is underway.
3. Next action — single concrete commitment with a time bound.
4. Contact path — how the customer reaches the assigned owner directly.

**Macro review cadence:** review the macro library monthly. Retire
macros that generate follow-up questions at a rate above fifteen percent;
those indicate the macro is not resolving the question. Add macros for
any issue type that recurs more than ten times in a calendar month.

Never send a macro without reading the full customer message first.
A macro applied to the wrong issue damages trust more than a slower
personalised response.

## Escalation Paths

Four escalation routes; each has a defined owner and an SLA for
escalation acknowledgement.

**Technical escalation**
Trigger: bug reproduction required; integration or API defect beyond
tier-1 or tier-2 capabilities; data inconsistency requiring database
access. Owner: engineering on-call or tier-3 technical specialist.
Acknowledgement SLA: 30 min for P1/P2; 4 h for P3.
Handoff artifact: ticket with reproduction steps, environment details,
account ID, and full error log attached.

**Billing escalation**
Trigger: disputed charge; refund request outside standard policy;
invoice discrepancy; subscription state inconsistency. Owner: billing
operations or finance team. Acknowledgement SLA: 2 h for any billing
escalation. Handoff artifact: ticket with charge history, contract
reference, and customer-stated amount.

**Legal escalation**
Trigger: customer references legal action, regulatory complaint, or
data-rights request (erasure, portability, access). Owner: legal or
compliance team. Acknowledgement SLA: 4 h. Handoff artifact: ticket
with full verbatim customer text and timestamp. Do not paraphrase legal
or regulatory language in the handoff.

**Executive escalation**
Trigger: customer explicitly requests CEO or C-level contact; a P1
incident has exceeded resolution SLA and the customer is a strategic
account; a situation carries reputational risk. Owner: customer success
or account management lead, who decides whether to involve executive
staff. Acknowledgement SLA: 1 h. Handoff artifact: ticket with full
interaction history, account value, and recommended response posture.

Never leave an escalation without a named owner. Escalation to "the
team" is not an escalation; it is a deferral.

## Voice-of-Customer Loop

Support volume is a structured source of product and operations
intelligence. The VoC loop extracts that intelligence systematically
rather than losing it in ticket closure.

**Weekly synthesis:**
- Identify the five most frequent issue categories from the prior
  seven days.
- Flag any category that has grown more than twenty percent week-over-
  week.
- For each top category, extract three to five representative verbatim
  customer quotes.
- Summarise root cause if known; label as "unknown root cause" if not.
- Deliver the synthesis document to the product team in the agreed
  channel before the end of the business week.

**Product handoff format:** issue category, frequency, representative
quotes, known root cause or open question, recommended product action
or documentation update, severity distribution for the category.

**Closing gate:** do not close a ticket that contains a novel complaint
or a feature request without tagging it for VoC capture. Tags must
be applied before closure, not retroactively.

The VoC loop fails when support volume is high and synthesis is skipped
"temporarily" — that is precisely when the signal is most valuable.

## Multi-Channel Support

Each channel has a distinct interaction contract. Match the issue type
to the appropriate channel; never force a customer into a channel that
does not fit the issue.

**Email**
Appropriate for: P3/P4 issues; billing enquiries; formal documentation
requests; any issue that benefits from asynchronous follow-up.
Tone register: professional, concise, full sentences. Avoid bullet
lists for emotional situations; prose acknowledges the customer more
directly. Include a case reference number in every email.

**Chat (live)**
Appropriate for: P2 initial triage; quick-resolution P3/P4; guided
walkthroughs. Tone register: conversational, present-tense, short
turns. Do not use chat for P1 as the primary resolution channel —
use it for acknowledgement while the engineering channel is engaged.
Never close a chat session with an open action; convert to email with
a written summary before closing.

**Phone**
Appropriate for: P1 incidents where email/chat latency is unacceptable;
executive escalations; emotionally charged interactions where text
amplifies friction. Tone register: calm, deliberate pacing; allow
silence; do not interrupt. Document the call summary in the ticket
within thirty minutes of the call ending.

**Social (public)**
Appropriate for: initial acknowledgement only. Move all substantive
resolution to a private channel within two public exchanges. Tone
register: brief, non-defensive, solution-forward. Never debate a
customer on a public social channel; never post account-specific
information publicly.

Per-channel tone must remain consistent across agents. Tone guidelines
belong in the macro library, not in individual agent discretion.

## Diagnostics and Metrics

**Leading indicators** (predict future satisfaction before it deteriorates):
- First-response time by severity tier — against SLA target, not average.
- First-contact resolution rate (FCR) — percentage of tickets resolved
  without a follow-up contact from the customer on the same issue.
- Escalation rate — percentage of tickets requiring escalation; a rising
  escalation rate signals either under-trained tier-1 or a systemic
  product issue.
- Reopen rate — percentage of closed tickets reopened within seven days;
  indicates resolution quality.

**Lagging indicators** (measure outcomes after the interaction is complete):
- CSAT (Customer Satisfaction Score) — post-interaction survey; 1–5
  scale; target ≥ 4.3 across all tiers.
- NPS (Net Promoter Score) — periodic relationship survey; detractor
  rate is more actionable than the headline score.
- Time-to-resolution by severity tier — measure against SLA; report
  median and 90th percentile, not mean (mean conceals outliers).

**Never optimise for speed at the expense of resolution quality.** A
ticket closed in thirty seconds that reopens in two days is a failed
interaction measured twice. FCR is a more reliable quality signal than
average handle time.

Review metrics weekly at the severity-tier level; review trends monthly
at the channel level. Present both leading and lagging indicators in the
same dashboard to avoid gaming a single metric.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Scripted-only responses | Customers detect templates; personalisation signals competence and care |
| Hidden escalation | Customer discovers escalation after the fact; destroys trust faster than the original delay |
| Vanity CSAT optimisation | Timing surveys to catch happy moments rather than measuring representative interactions; inflates scores while masking real issues |
| Ignored VoC | Tickets closed without synthesis; product team receives no signal; same issues recur without root-cause resolution |
| Channel mismatch | Directing a P1 incident to asynchronous email; directing billing disputes to live chat without specialist access |
| "Dear Customer" macros | Demonstrates the agent did not read the ticket; damages trust immediately |
| Closing without next-action commitment | Customer is left without a concrete expectation; increases reopen rate and escalation demand |
| Optimising for average handle time | Encourages premature closure and deflection; FCR and reopen rate will degrade as a consequence |

## Cross-References

- `domains/hospitality/skills/guest-services` — guest-facing service
  standards that parallel multi-channel support tone discipline.
- `domains/retail/skills/customer-returns` — returns and claims handling
  with severity-triage patterns applicable to billing escalations.
- `domains/business-support/skills/analytics-reporter` — metrics
  pipeline and dashboard discipline for CSAT/NPS/FCR reporting.

## ADR Anchors

- **ADR-058** — canonical skill authorship and creative-rewrite
  discipline; this skill is a structural adaptation of the upstream
  source, not a verbatim copy. All doctrine is independently authored.
