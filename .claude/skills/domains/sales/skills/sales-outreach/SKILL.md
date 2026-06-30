---
name: sales-outreach
description: >
  Consultative B2B sales outreach — cold prospecting, lead follow-up,
  objection handling, proposal-stage messaging, and pipeline management for
  {{PROJECT_NAME}} sales teams. Combines data-driven targeting with
  relationship-first execution: research-before-write discipline, signal-cited
  openers, channel-specific message architecture, structured objection frames,
  and cadence rhythm calibrated by deal stage. Use when writing a cold
  sequence, handling an objection, drafting a proposal, managing a
  multi-stakeholder account, or deciding when to send a break-up message.
owner: Sales Outreach Specialist (domain persona)
tier: domain:sales
scope_tags: [sales-outreach, cold-prospecting, lead-follow-up, objection-handling, b2b-outreach, pipeline-management]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/sales-outreach.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/outreach/**"
  - "**/cold-email/**"
  - "**/cadences/**"
  - "**/objections/**"
---

# Sales Outreach

## Cardinal Rule

Outreach that respects the prospect's time is the long-game; the rep
who treats every send as transactional builds nothing. Every message
must earn the prospect's attention with a researched signal, a single
clear ask, and a word count the prospect can finish in under thirty
seconds.

## Fail-Fast Rule

Stop the sequence and escalate to ICP review when:

- Three consecutive sequences on a segment produce zero replies,
  including break-up messages.
- The opener references a trigger event that is more than ninety days
  old — the signal has expired and relevance cannot be recovered.
- The product's stated value proposition does not map to a pain point
  the prospect's role is accountable for — the account is out of ICP.
- A prospect has explicitly asked to not be contacted. No cadence
  management system overrides a stated opt-out.

## When to Apply

Apply this skill when:

- Building a cold sequence targeting a defined ICP segment.
- Writing or reviewing a follow-up message after an initial send.
- Drafting a response to an objection received via email or voicemail.
- Preparing proposal messaging after verbal alignment on value and budget.
- Deciding whether to continue, pause, or close a prospect in the pipeline.
- Designing outreach for a multi-stakeholder account with distinct
  persona tracks.

Do NOT apply to inbound lead response (handled by discovery-coach) or
to renewal and expansion messaging (handled by account-strategist).

## Cold Prospecting Discipline

Research precedes writing, always. A rep who writes before researching
signals that the message is about the sender, not the receiver.

Required research sequence before drafting touch 1:

1. Confirm the account is inside ICP on firmographic dimensions:
   industry vertical, company size, business model, geography.
2. Identify at least one trigger event with a timestamp — funding
   announcement, new executive hire, job posting that signals pain,
   product launch, or competitive displacement signal.
3. Confirm the contact's role owns the problem the product solves.
   A message sent to a title that does not own the pain is wasted.
4. Map the buying committee at the account: decision maker, champion
   candidate, and any known detractor or gatekeeper.

Signal citation is mandatory in touch 1. An opener that contains no
verifiable external signal — not a generic industry observation, not
"I noticed your company is growing" — does not meet the standard. The
prospect must be able to confirm the signal with a search.

Disqualify early rather than late. A bad-fit account closed is a churn
event. Disqualification at prospecting is free; disqualification at
proposal costs both parties time and erodes trust.

## Message Architecture

Every cold message contains five components in order. Any component
absent reduces reply rate and signals the prospect that the sender
did not prepare.

| Component | Function | Length ceiling |
|-----------|----------|---------------|
| Subject | Curiosity or relevance to the prospect's world | 7 words |
| Opener | Specific signal — trigger event or observed context | 1 sentence |
| Pain cite | One sentence connecting the signal to a known pain | 1 sentence |
| Proof | One social proof datum (customer outcome or metric) | 1 sentence |
| CTA | Single low-friction next step | 1 sentence |

Total word count ceiling for cold touch 1: 150 words. Messages over
150 words are not edited down — they are rewritten from the signal.

Subject line patterns that meet the standard:

- `Question about [Company]'s [specific initiative]`
- `[Trigger event] — quick thought`
- `[ICP peer company] used this to [specific outcome]`

Subject line patterns that do not meet the standard:

- `Following up` (no signal, no specificity)
- `Quick question` (prospect cannot evaluate relevance from the subject)
- Any subject line that could be sent to any prospect unchanged

## Channel-Specific Patterns

Different channels carry different norms. Applying email norms to
LinkedIn DM or phone to video produces friction that kills the reply.

**Email** — the primary cold channel. Personalized opener mandatory.
Plain text performs better than HTML on first touch. No attachments
on touch 1; the CTA is a call, not a document download. Follow up by
adding new value, not restating touch 1 in different words.

**LinkedIn DM** — connection request carries no pitch. The message
sends after the connection is accepted. Shorter than email: 75 words
maximum. The signal in the DM must differ from the email signal — do
not duplicate the email in a shorter format.

**Phone voicemail** — 30 seconds maximum. State: name, company,
the specific trigger that caused the call, one outcome statement,
callback number twice. Do not pitch the product in the voicemail.
The voicemail earns a callback; the callback is the pitch.

**Video (Loom or equivalent)** — 60–90 seconds. Open with the
prospect's name and a visible screen showing something specific to
their company or role. Generic opener videos are ignored. Video adds
face and tone; use it for mid-sequence re-engagement or for
high-value accounts where personalization ROI justifies the investment.

## Objection Handling Frame

Every objection is a request for clarification, not a rejection. The
rep who responds with a rebuttal has already lost the conversation.

Frame: Acknowledge → Clarify → Reframe → Validate → Move-forward.

**"No budget right now"**
Acknowledge: "That makes sense — budgets are tight in most organizations."
Clarify: "Is it that no budget exists, or that it has not been
allocated for this problem yet?"
Reframe: Surface the cost of inaction, not the cost of the product.
Validate: Confirm whether Q-planning timing or a different stakeholder
changes the picture.
Move-forward: Propose a no-commitment discovery call to understand
whether timing is the actual constraint.

**"Using a competitor"**
Acknowledge: "Good to know — that tells me you've already bought into
the category."
Clarify: "What made you choose them originally, and is there anything
you wish worked differently?"
Reframe: Let the prospect name the gap. Never cite a competitor's
weakness unprompted.
Move-forward: Request a 15-minute conversation to explore whether
the gap the prospect named is addressable.

**"Not a priority right now"**
Clarify: "What is the top priority for your team this quarter?"
Reframe: Map the product's value to the stated priority. If no
mapping exists, disqualify.
Move-forward: If a mapping exists, propose a brief call to show the
connection; set a re-engagement reminder for 60–90 days if no mapping.

**"Send information"**
Reframe: "I want to send something relevant, not a generic deck. Can
I ask two questions to make sure it addresses your situation?"
Move-forward: Qualify before sending anything. A document sent without
qualification is a delay tactic, not a sales motion.

**"Price is too high"**
Clarify: "Is the price outside your budget entirely, or is it a
question of whether the value justifies the investment?"
Reframe: Build the ROI calculation together. Show the cost of inaction
against the investment.
Move-forward: Offer a scoped engagement at a lower entry point only
if it genuinely addresses the objection — never discount without a
documented business reason.

## Follow-up Cadence

Cadence rhythm by stage:

| Stage | Cadence | Value-add requirement |
|-------|---------|----------------------|
| Cold (touch 1–3) | Day 1 / Day 3 / Day 5 | Each touch adds a different signal |
| Cold (touch 4–6) | Day 8 / Day 12 / Day 17 | Channel switch minimum once; new angle mandatory |
| Break-up | Day 21 | Honest, door-open; no new pitch |
| Post-reply pause | 24 hours to respond | No follow-up until next step is confirmed |
| Re-engagement | 90 days minimum | Treat as a new sequence; do not reference old cadence |

Reply-pause-resume rule: once a prospect replies, the cadence stops.
The rep responds within one hour during business hours. The next
scheduled touch does not fire until the conversation resolves or the
prospect goes silent for more than five business days.

Break-up message discipline: the break-up message signals honest
respect for the prospect's time and explicitly closes the sequence.
It mentions one of two possibilities — timing is wrong, or the
problem is not a current priority — and leaves the door open without
asking for a reply. Break-up messages frequently generate the highest
reply rates in a sequence because they remove pressure.

Break-up message structure:

```
Subject: Should I close your file?

[First name], I have reached out a few times without hearing back —
which usually means the timing is off or this is not a current
priority. Either is completely fine.

I will close out your file to stop cluttering your inbox. If
[specific pain] becomes a priority, I am easy to find.

[Name]
```

## Multi-stakeholder Outreach

Enterprise accounts involve three distinct tracks. Copy-pasting the
same message across tracks is detected immediately by buyers and
collapses trust across all three.

**Champion track** — the internal advocate who will sell on behalf of
the rep when the rep is not in the room. Messages to the champion
focus on: the business case in their language, the internal objections
they will face, and the proof points that will survive scrutiny from
the economic buyer. Equip the champion; do not pitch them.

**Economic buyer track** — the person with budget authority. Messages
to the economic buyer lead with business outcomes and cost of inaction.
They do not include product detail or feature lists. An economic buyer
who hears product detail before business impact closes the door.

**Detractor track** — a known blocker or skeptic in the buying
committee. Do not ignore detractors; they will surface in the decision
process regardless. The goal is not to convert the detractor but to
understand their objection and ensure it has a documented response
available to the champion.

Each track maintains its own message log. Merging tracks — for
example, copying the champion on an economic buyer message — removes
the rep's ability to calibrate each relationship independently.

## Personalization Authenticity

Templated personalization is identified instantly by experienced buyers.
Inserting `[First name]` and `[Company name]` into a generic template
is not personalization — it is mail merge. The buyer recognizes the
pattern and deletes without reply.

A researched signal in the opener is the minimum threshold. The signal
must be:

- Verifiable — the prospect can confirm it with a search.
- Specific — tied to this company or this person, not the industry.
- Recent — trigger events older than 90 days have expired.
- Connected — the opener bridges from the signal to the pain in one
  sentence, not two.

Signal half-life by type:

| Signal type | Effective window |
|-------------|-----------------|
| Funding announcement | 60 days |
| Executive hire | 45 days |
| Job posting (signals pain) | 30 days |
| Product launch / press mention | 30 days |
| Conference speaking appearance | 14 days |
| Earnings call comment | 14 days |

Signals outside their effective window may still be used to open a
re-engagement sequence (90+ days after initial touch) if framed as
context for renewed outreach, not as a current event.

## Anti-patterns

| Anti-pattern | Why it fails |
|-------------|-------------|
| "Just bumping this up" | Adds zero value; signals the rep has nothing new to say |
| "Circling back" | Identical problem; transparent filler with no forward motion |
| "Hope you're well" / "Hope this finds you well" | Generic opener that delays relevance; prospect skips to the next sentence |
| Fake intimacy ("As a fellow [title]...") | Manufactured connection the buyer did not earn is recognized and resented |
| Multiple CTAs in one message | Forces a decision the prospect was not asked to make; confusion produces silence |
| Attachment on touch 1 | Triggers spam filters and signals the rep wants to pitch before qualifying |
| Ghosting after a "no" reply | Leaving an explicit no without acknowledgment damages sender reputation for future outreach |
| Spray-and-pray volume without research | High volume with no signal produces low reply rates and trains the segment to ignore the sender |
| Badmouthing a competitor | Prospect reads it as insecurity; trust moves toward the competitor |
| Re-sending touch 1 verbatim as follow-up | The prospect already received it; re-sending signals either a broken process or disrespect for their time |
| "Just wanted to check in" | Vague; provides no reason for the prospect to reply |
| Discounting before the objection is understood | Trains the prospect to withhold commitment to extract price concessions |

## Cross-References

- `domains/sales/skills/outbound-strategist` — ICP definition, territory
  segmentation, and lead sourcing upstream of outreach execution.
- `domains/sales/skills/discovery-coach` — once a reply converts to a
  scheduled call, discovery-coach governs the conversation structure.
- `domains/sales/skills/sales-coach` — for rep-level coaching on outreach
  performance patterns, message quality review, and cadence discipline.

## ADR Anchors

- **ADR-058** — Creative-rewrite drop policy. All section content is
  original authorship. Upstream structural inspiration acknowledged in
  `inspired_by:` frontmatter; no prose copied verbatim from source.
