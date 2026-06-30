---
name: discovery-coach
description: >
  Governs discovery methodology for sales conversations: question design using SPIN-style
  sequencing, current-state mapping co-built with the buyer, gap quantification expressed
  in the buyer's own currency, and call structure that surfaces real buying motivation before
  any pitch occurs. Use when an account executive needs a discovery call framework, when a
  seller is rushing to demo before mapping pain, when a pipeline review reveals shallow
  qualification, or when quantifying the cost of inaction is needed to create authentic urgency.
owner: Morgan Vale (Discovery Coach, sales methodology domain)
tier: domain:sales
scope_tags:
  - sales-discovery
  - question-design
  - current-state-mapping
  - gap-quantification
  - buying-motivation
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-discovery-coach.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/discovery/**"
  - "**/call-notes/**"
  - "**/qualification/**"
---

# Discovery Coach

## Cardinal Rule

Pain not quantified in the buyer's own currency is preference, not pain; preference does
not fund a deal. Until the buyer states — in their own words — the measurable cost of their
current state, discovery is incomplete. All call structure and question sequencing exists
to reach this moment.

## Fail-Fast Rule

Disqualify when three conditions are simultaneously absent after two full discovery calls:
(1) a root-cause problem the buyer acknowledges, (2) quantified business impact, and
(3) an identified economic buyer with authority and timeline. A pipeline entry without all
three is a forecast liability, not an opportunity.

## When to Apply

- Pre-call preparation for any first or second discovery conversation.
- Pipeline review: any opportunity lacking documented current-state map or gap dollar figure.
- Call debrief: seller pitched before minute 20 of a 30-minute call, or left without next-step
  contract.
- Onboarding: new account executives building question repertoire.
- Escalation: deal stalled at "interested but not urgent" — root-cause gap mapping required.

## Question Architecture

Question sequencing follows a four-stage discipline. Departing from the sequence before
completing a stage is the primary cause of shallow qualification.

**Situation (2-3 questions maximum)**
Establish factual context. Research eliminates most situation questions before the call.
Every situation question that could have been answered by LinkedIn, the company website,
or the CRM record signals to senior buyers that preparation was absent.
- Confirm current tools, team structure, or process ownership only when not researchable.

**Problem (surface dissatisfaction)**
Open the space of acknowledged friction. Stop here only briefly — most sellers
treat problem questions as the destination; they are the entry point.
- "Where does that process break down for the team?"
- "What happens when that scenario occurs mid-quarter?"

**Implication (expand cost — primary leverage point)**
Implication questions are where urgency is born. Buyers have rarely fully confronted the
downstream cost of their current state. These questions activate that reckoning.
- "When that breaks down, what is the downstream impact on the adjacent team or metric?"
- "How does that affect delivery against the goal stated earlier?"
- "If this continues another two to three quarters, what does that cost in concrete terms?"
- "Who else in the organization absorbs the effects of this problem?"
Never skip implication under time pressure. A shortened discovery without implication
produces a proposal the buyer will not prioritize.

**Need-Payoff (buyer articulates future value)**
Let the buyer describe the desired state in their own language. Those words become
the only language used in the written proposal.
- "If that root cause were resolved, what would that unlock for the team?"
- "What would change in the business if this were no longer a factor?"

Questions never lead with product capability, price, competitive comparison, or
timeline pressure. All four categories are late-stage inputs, not discovery inputs.

## Current-State Map

The current-state map is co-built with the buyer during the call. It is never
constructed from assumptions and presented as a lecture. Required fields:

| Field | Description |
|---|---|
| Workflow | The specific process or system where friction occurs |
| Volume | Scale or frequency: transactions per period, team size, data volume |
| Cost | Quantified in dollars, hours, or headcount — buyer-sourced figures only |
| Friction | Specific breakdown points; root cause distinguished from symptom |
| Consequence | Business impact: revenue, risk, capacity, or competitive exposure |

The map is complete only when the buyer has confirmed each field in their own words.
A map built from seller inference is not a current-state map — it is a hypothesis that
will fail at proposal review.

## Gap Quantification Frame

The sale is the gap between current state and desired state. Gap size determines urgency.
Gap precision determines whether the buyer chooses action over inaction.

```
Gap dollars = current-state cost - desired-state cost
Potential win value = gap dollars × buyer-assigned probability of resolution
```

Current-state cost components: direct spend (tools, headcount, rework), opportunity cost
(revenue blocked or delayed), and risk exposure (compliance, churn, competitive loss).

Desired-state figures are buyer-stated, not seller-projected. If the buyer cannot articulate
a desired state with any specificity, discovery is not complete.

The root-cause question is the highest-leverage question in the map: surface-level symptoms
("the tool is slow") do not create urgency. Root causes with timeline pressure
("legacy architecture cannot scale to the three enterprise onboards this quarter") do.

## Discovery Call Structure

60-minute frame. The 30-minute variant compresses opener and mutual close by four minutes each;
all other proportions hold.

**Opener — 4 minutes: Upfront Contract**
State agenda, time boundary, and three acceptable outcomes (fit → next step; no fit → say so
honestly; insufficient information → agree what is needed). Request buyer additions to agenda.
This eliminates ambiguity, signals preparation, and grants permission to ask hard questions.

**Discovery — 35 minutes: Current State and Pain**
Spend 60-70% of total call time here. The opening territory question:
- Inbound: "What prompted the decision to take this call today?"
- Outbound: "When the outreach referenced the signal observed, what was the context on
  your side?"

Follow the signal using SPIN sequencing. Before any transition to solution framing,
the seller must be able to state: the problem in the buyer's words, the root cause, the
quantified impact, the stakeholder map, the trigger for current prioritization, and the cost
of inaction.

**Targeted Response — 10 minutes: Mapped to Stated Pain Only**
Present two to three capabilities that directly address problems stated by the buyer.
Restate the buyer's problem framing before each capability description.
No product tour. No unprompted feature enumeration. Relevance is the only criterion.

**Mutual Close — 5 minutes: Next-Step Contract**
Define the next action with owner, deliverable, and date. Identify additional stakeholders
who must be present at the next stage. Agree on disqualification criteria so neither party
invests past a clear no.

**Internal: 6 minutes buffer** for note capture and CRM update before the next call.

## Multi-stakeholder Discovery

Enterprise deals involve multiple decision stakeholders with distinct pain profiles.
Single-threading — running all discovery through one contact — is the primary cause of
late-stage stalls and ghosting.

Required protocol:
- Map all stakeholder roles in the first discovery call: economic buyer, technical evaluator,
  champion, and end-user are the minimum four.
- Schedule separate discovery conversations per persona. Each persona has distinct pain,
  distinct success criteria, and distinct risk tolerance.
- Never relay one persona's concerns to another as shared organizational position without
  verification.
- Converge findings in a shared current-state map that the champion can validate before
  the group presentation. Discrepancies between personas are not noise — they are the
  deal risk.

## Silence as Instrument

After an implication or need-payoff question, wait. Do not fill the pause with a restatement,
a clarification, or an answer. The buyer's first response is the surface answer. The answer
after two to four seconds of silence is the real one — the cost figure, the personal stake, or
the admission that previous attempts to solve the problem failed.

Sellers who fear silence fill it with features. The pause is not a signal that the question
failed; it is a signal that the buyer is doing the cognitive work the question was designed to
trigger. Interrupting that work resets the buyer to the surface level.

The 60/40 rule enforces silence structurally: if the seller is talking more than 40% of the
call, the buyer is not doing the work. The ratio is measurable via call recording.

## Objection Handling

Objections during discovery are diagnostic, not adversarial. They reveal what the buyer is
actually thinking, which is more useful than silence. Three categories cover more than 95% of
discovery-stage objections:

| Category | Surface Statement | Underlying Signal |
|---|---|---|
| Value / Budget | "This is not in budget" | Gap not yet quantified in buyer's currency; ROI case not established |
| Timing | "Not the right time" | Competing priority or initiative; urgency not activated |
| Fit | "We already have a solution" | Incumbent switching cost not surfaced; differentiation not mapped to pain |

Resolution protocol for each: return to the gap quantification frame. A budget objection
resolves when the buyer states the cost of inaction in their own numbers. A timing objection
resolves when the trigger creating current-quarter urgency is identified. A fit objection
resolves when the specific failure mode of the incumbent is documented in the current-state map.

Never accept an objection at face value during discovery. Acceptance forecloses the
diagnostic process.

## Anti-patterns

| Anti-pattern | Why It Fails |
|---|---|
| Leading questions ("You're probably finding that X, right?") | Confirms seller hypothesis; produces false-positive qualification |
| Demo during discovery | Anchors conversation to product features before pain is mapped; buyer objections become feature objections, not business objections |
| Accepting "we want X" without quantified pain | Stated desire without underlying cost does not survive budget review; deal stalls at approval |
| Asking situation questions answerable by research | Signals lack of preparation; erodes credibility with senior buyers before discovery begins |
| Pitching before minute 20 of a 30-minute call | Discovery is incomplete; proposal will not map to actual priorities |
| Treating problem questions as destination | Problem-level discovery misses implication; buyer has not confronted cost of inaction; no urgency |
| Single-threaded stakeholder coverage | Champion cannot navigate internal review without multi-persona buy-in; deal stalls or reverses |
| Talking more than 40% of call time | Active listening drops; buyer signals are missed; call becomes a pitch monologue |
| Accepting "not the right time" without root cause | Timing objection conceals real objection; disqualification or re-engagement strategy cannot be formed |
| Accepting verbal confirmation without written next-step contract | Follow-up emails with "great to connect" do not constitute a next step; deal velocity collapses without explicit owner + date |

## Cross-References

- `domains/sales/skills/deal-strategist` — opportunity qualification scoring, multi-stakeholder
  map, competitive positioning after discovery is complete.
- `domains/sales/skills/sales-coach` — call debrief methodology, pipeline review cadence,
  rep performance coaching.
- `domains/sales/skills/sales-engineer` — technical discovery for complex product environments;
  handoff protocol from business discovery to technical validation.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review): discovery call structure exemplifies
  ADR-058 two-pass discipline — pass one maps current state without solution framing; pass two
  introduces tailored response only after map is confirmed. Sellers who collapse both passes
  into a single motion produce the same failure mode as reviewers who evaluate and generate
  simultaneously.
