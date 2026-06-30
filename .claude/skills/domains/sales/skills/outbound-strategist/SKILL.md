---
name: outbound-strategist
description: >
  Governs signal-based outbound prospecting: ICP definition with falsifiable exclusion
  criteria, trigger-signal taxonomy ranked by intent strength and decay window, multi-channel
  sequence architecture matched to buyer persona, and personalization tiering that separates
  deeply researched effort from broadcast automation. Use when pipeline sourcing requires
  a new outbound motion, when reply rates fall below signal-based benchmarks, when an SDR
  team is measured on send volume rather than pipeline quality, when sequence design needs
  channel-persona alignment, or when ICP definitions are too broad to generate a targeted
  account list.
owner: Sasha Marlowe (Outbound Strategist, sales domain)
tier: domain:sales
scope_tags:
  - outbound-prospecting
  - signal-based
  - sequence-design
  - icp-definition
  - personalization
  - multi-channel
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-outbound-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/outbound/**"
  - "**/sequences/**"
  - "**/icp/**"
  - "**/prospecting/**"
---

# Outbound Strategist

## Cardinal Rule

An outbound message that does not cite a specific signal observed at THIS prospect THIS
quarter is spam wearing a name. The obligation before any sequence enrollment is to identify
one observable event at that account — a leadership change, a funding close, a hiring spike,
a technology shift, a competitor contract expiry — that creates a plausible reason the buyer
should care about this message now, not next quarter.

## Fail-Fast Rule

Stop and rebuild the motion when three conditions simultaneously hold: (1) reply rate
sustained below 5% across two full sequence cohorts on signal-enrolled accounts, (2) ICP
definition cannot exclude at least 40% of accounts in the target list on firmographic or
behavioral grounds, and (3) no documented signal source is feeding enrollment. Volume is
not a substitute for relevance. A broken motion run louder produces unsubscribe rates and
domain reputation damage, not pipeline.

## When to Apply

- Designing or auditing an outbound motion from first principles.
- Sequence reply rate drops below 12% on signal-enrolled accounts — diagnostic required.
- SDR team is reporting activity metrics (emails sent, dials made) rather than pipeline metrics.
- ICP definition review: if the account list exceeds a manageable research threshold without
  tier segmentation, the ICP is too broad.
- Channel-persona mismatch: a single channel used uniformly regardless of buyer seniority.
- Post-funding or post-launch: new signal sources and new buying personas require sequence reset.

## ICP Definition Discipline

A useful ICP is falsifiable. An ICP that does not exclude companies is a TAM slide. Required
dimensions for a working ICP definition:

**Firmographic**
- Industry verticals: 2-4 specific named categories, not broad descriptors.
- Revenue band or employee count range with explicit upper and lower bounds.
- Geography scope, if go-to-market is regionally constrained.
- Funding stage or ownership type, if relevant to budget authority or procurement process.

**Technographic**
- Prerequisite technologies that must already be present for the product to deliver value.
- Technologies that signal readiness for an adjacent solution or displacement of an incumbent.
- Stack indicators visible via job postings, vendor documentation, or public data sources.

**Behavioral**
- The business event that creates urgency in this quarter, not in general.
- The pain the product resolves that cannot be deferred without measurable cost.
- The internal stakeholder who owns the pain acutely enough to champion a purchase.
- The current workaround and its documented cost or failure rate.

**Signal-Density Threshold**
- Tier 1 sub-segment: accounts with two or more independent signals active simultaneously.
- Tier 2 sub-segment: accounts with one strong signal or two weak signals.
- Tier 3: ICP-fit accounts with no current signal — automation only, no manual research spend.
- Explicit disqualifiers: industries where win rate is documented below 15%; company stages
  where the product is architecturally premature or commercially overkill.

## Trigger Signals Taxonomy

Signal classification by intent strength, source, decay window, and actionability.

| Signal Class | Representative Sources | Decay Window | Actionability |
|---|---|---|---|
| Direct buyer intent | G2 / review site visits, pricing page views, competitor comparison search, RFP announcement | < 24 hours | Route to rep immediately; highest-priority sequence enrollment |
| Leadership change | LinkedIn, press releases, 10-K, board announcements | 30 days | New executive = new priorities; outreach before incumbent vendor relationship resets |
| Funding event | Crunchbase, PitchBook, press release | 14 days | Series B+ with stated growth goals signals budget and urgency; tie message to stated use of funds |
| Hiring spike | LinkedIn, Greenhouse, Lever, job aggregators | 21 days | Department headcount growth signals scaling pain; message to the team owner, not HR |
| Technology stack shift | BuiltWith, Wappalyzer, job posting language, vendor press release | 45 days | Stack change creates integration requirement or incumbent displacement window |
| M&A or restructure | SEC filing, press, industry news | 14 days | Integration pressure and tool consolidation create active evaluation cycles |
| Conference or content signal | Event speaker lists, webinar registrations, whitepaper downloads | 7 days | Recency matters; message must reference the specific content or event, not the category |
| Competitor contract renewal | Renewal date databases, G2 reviews, champion intelligence | 60 days | Longest decay window; requires champion-sourced timing data to act with precision |

Signal routing rule: signals must reach the assigned rep within 30 minutes of capture.
After 24 hours, the conversion rate on the signal drops significantly. After 72 hours,
a competitor has in most documented cases already initiated contact.

## Sequence Architecture

Sequence design is determined by account tier and buyer persona before any other variable.
Channel mix, cadence rhythm, and touch count derive from those inputs, not from platform
defaults.

**Channel-Persona Alignment**

| Persona Level | Primary Channel | Secondary | Tertiary |
|---|---|---|---|
| C-Suite | LinkedIn (InMail or connection with note) | Warm introduction / referral | Short direct email |
| VP-level | Email | LinkedIn | Phone with voicemail |
| Director | Email | Phone with voicemail | LinkedIn |
| Manager / Individual Contributor | Email | Short-form video (Loom) | LinkedIn |
| Technical buyer | Email (technical framing) | Community or Slack | LinkedIn |

**Cadence Rhythm (Standard 10-Touch, 28-Day Frame)**

```
Touch 1  — Day 1,  Email:      Signal-based opening + single value claim + low-friction CTA
Touch 2  — Day 3,  LinkedIn:   Connection request with personalized note; no pitch
Touch 3  — Day 5,  Email:      Relevant data point or industry insight tied to their situation
Touch 4  — Day 8,  Phone:      Call with voicemail referencing previous email by subject line
Touch 5  — Day 10, LinkedIn:   Engage with their published content or share relevant material
Touch 6  — Day 14, Email:      Peer case study from a comparable account and situation
Touch 7  — Day 17, Video:      60-second Loom referencing something specific to their account
Touch 8  — Day 21, Email:      Different angle — second pain point or adjacent stakeholder view
Touch 9  — Day 24, Phone:      Final call attempt
Touch 10 — Day 28, Email:      Breakup email — honest, brief, door left open without pressure
```

Each touch adds a new value angle. A repeated ask with different wording is not a new touch;
it is a noise event. Reply-then-pivot rule: any positive reply exits the automated sequence
immediately and transfers to human-directed follow-up within one business hour.

**Cold Email Anatomy**

```
SUBJECT LINE
- 3-5 words, sentence case, reads like an internal thread
- References signal or account-specific detail, not category or solution name
- Never all-caps, never punctuation-spam, never vague urgency

OPENING LINE
- Signal-specific, not a pleasantry or a self-introduction
- Correct: "Saw the Series B close last week — growth-stage
  scaling usually surfaces the tooling gaps the previous
  architecture was not designed for."
- Incorrect: "I hope this finds you well."
- Incorrect: "I'm reaching out because we help companies like yours..."

VALUE CLAIM
- One sentence connecting their current observable situation to a concrete outcome
- Buyer's vocabulary, not marketing copy
- Specificity over cleverness: numbers, timeframes, documented outcomes

SOCIAL PROOF (conditional)
- One line only; include if directly analogous to buyer's situation and verifiable
- Omit if not genuinely parallel — unearned social proof erodes credibility faster
  than no social proof

CTA
- Single, unambiguous, low friction
- Correct: "Worth 15 minutes to see if this applies to your team?"
- Incorrect: "I'd love to schedule a 30-minute demo to walk you through..."
```

## Personalization Tier Matrix

Personalization investment must match account tier and signal strength. Claiming Tier 1
effort on a Tier 3 message is the defining characteristic of fake personalization — buyers
recognize it immediately and it is worse than no personalization.

| Tier | Account Definition | Personalization Depth | Research Investment |
|---|---|---|---|
| Tier 1 — Deep | Top 50-100 accounts; two or more active signals | Account-specific: annual report language, earnings call themes, stated strategic initiatives, named stakeholder references | 45-90 minutes per account; dedicated rep ownership; multi-thread across 3-5 contacts |
| Tier 2 — Templated-with-variable | Next 200-500 accounts; one strong signal or ICP-fit with two weak signals | Industry-specific messaging + account-level opening line variable; persona-matched value claim | 10-15 minutes per account; signal-triggered enrollment; 2-3 contacts per account |
| Tier 3 — Broadcast | Remaining ICP-fit accounts; no current signal | Role and industry tokens only; no account-level research | Automated enrollment; no manual research spend; single primary contact; automated scoring surfaces for promotion |

Tier promotion criteria: a Tier 3 account that generates positive engagement (reply, content
engagement, website revisit) or acquires a new Tier 1 signal upgrades to Tier 2 automatically
within the next enrollment cycle. Quarterly review demotes accounts with no signal activity.

## Performance Diagnostics

Leading and lagging metrics are not interchangeable. Leading metrics diagnose the motion
in flight; lagging metrics confirm outcomes already in the system. Corrective action
requires leading-metric visibility.

| Metric | Type | What It Diagnoses | Reference Range |
|---|---|---|---|
| Signal-to-contact latency | Leading | Routing speed from signal capture to first touch | < 30 minutes |
| Reply rate (signal-enrolled) | Leading | Message relevance and opening-line quality | 12-25% |
| Positive reply rate | Leading | Actual interest generated; ICP fit quality | 5-10% |
| Meeting set rate (reply-to-meeting) | Leading | CTA clarity and objection handling in follow-up | 40-60% of positive replies |
| Meeting held rate | Lagging | Prospect commitment quality; confirmation and prep quality | 80%+ of meetings set |
| Stage 1 to Stage 2 conversion | Lagging | Discovery qualification depth; meeting quality | 50%+ |
| SQL conversion | Lagging | Full-funnel ICP accuracy and sequence targeting | Varies by ACV and market |
| Sequence completion rate | Process | Rep execution discipline | 80%+ sequences run to completion |
| Channel mix effectiveness | Process | Which channel produces reply per persona | Review monthly per persona |

Corrective action thresholds: reply rate below 5% on signal-enrolled cohorts triggers
sequence audit. Stage 1 to Stage 2 below 35% triggers ICP review or discovery coaching
escalation, not sequence volume increase.

## Anti-patterns

| Anti-pattern | Failure Mode |
|---|---|
| Spray-and-pray | Treats outreach as a numbers game; destroys domain reputation, triggers inbox filters, and produces pipeline that does not convert because ICP fit was never enforced |
| Fake personalization | Opening line inserts a company name or role title without account-specific observation; buyers recognize it; trust cost exceeds any engagement gain |
| Stale signal enrollment | Acting on a signal more than the published decay window after capture; competitor has already had the conversation; message has no urgency basis |
| Channel-persona mismatch | Running phone-primary sequences on C-Suite contacts or email-only on Director-and-below; channel preference is a persona property, not a platform default |
| Volume escalation as fix | Increasing send volume in response to low reply rate; amplifies the broken motion, accelerates domain damage, and produces false-positive meeting data |
| Automating Tier 1 outreach | Tier 1 accounts have sufficient deal value to justify manual research; automating them signals to the buyer that their account was not worth research investment |
| Single-variable optimization | Changing subject line, opening line, and CTA simultaneously in a test cohort; three variables changed produce no learnable signal; test one variable per cohort |
| Sequence abandonment before touch 6 | Most replies come after touch 4; reps who abandon sequences after 2-3 touches report artificially low reply rates and miss late-breaking signals |
| Vanity metric reporting | Reporting emails sent, dials made, or sequences enrolled without reply rate, positive reply rate, and meeting held rate; activity metrics do not predict pipeline |
| Ignoring opt-outs | Non-compliance with opt-out requests is a legal and reputational liability; unsubscribe handling must be immediate and complete with no re-enrollment path |

## Cross-References

- `domains/sales/skills/discovery-coach` — call structure and question sequencing for
  converting outbound-sourced meetings into qualified opportunities.
- `domains/sales/skills/account-strategist` — multi-stakeholder mapping and account planning
  for Tier 1 accounts requiring coordinated outbound across multiple contacts.
- `domains/sales/skills/pipeline-analyst` — pipeline quality analysis and stage-conversion
  diagnostics when outbound-sourced pipeline underperforms relative to inbound.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review): outbound sequence design exemplifies
  the two-pass discipline — pass one is ICP definition and signal research without drafting any
  copy; pass two is sequence construction using only what the research surfaced. Collapsing
  both passes into simultaneous research-and-write produces generic copy that does not reflect
  specific findings, the same failure mode as reviewers who generate and evaluate in a single
  motion.
