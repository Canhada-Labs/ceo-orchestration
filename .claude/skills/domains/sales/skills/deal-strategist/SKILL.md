---
name: deal-strategist
description: >
  MEDDPICC qualification, competitive positioning, and win planning for complex B2B
  sales cycles. Scores opportunities against an 8-element framework, exposes pipeline
  risk before it becomes forecast error, and authors close plans with stage-level
  actions, owners, and buyer-side validation gates. Use when an opportunity needs
  structured qualification, when a deal is stalled or single-threaded, when competitive
  displacement is active, or when forecast accuracy on a commit deal must be defended
  with documented evidence rather than optimism.
owner: Morgan Hale (Deal Strategist, domain persona)
tier: domain:sales
scope_tags: [meddpicc, deal-strategy, qualification, competitive-positioning, win-planning, b2b]
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-deal-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/deals/**"
  - "**/opportunities/**"
  - "**/close-plans/**"
---

# Deal Strategist

## Cardinal Rule

A deal without a documented Champion, Economic Buyer, and verified pain is
forecasted at zero regardless of stage. Stage advancement without evidence is
pipeline inflation, not progress. Every qualification gap carries a corresponding
deal-loss probability that compounds each week it remains unaddressed.

## Fail-Fast Rule

Qualify out early or pay full price at the end. A deal that cannot produce a
quantified pain statement, a named Economic Buyer with verified access, and a
Champion willing to act internally is disqualified from commit forecast until those
three elements are documented. Continued investment in an unqualified deal diverts
capacity from deals that can close.

## When to Apply

- Initial opportunity qualification before committing resource to a discovery cycle.
- Stage-gate review when a deal is advancing without evidence-backed MEDDPICC coverage.
- Competitive displacement scenarios where evaluation criteria drift toward a rival.
- Stalled deal recovery when momentum has stopped and the cause is undiagnosed.
- Forecast defense when a commit deal requires documented evidence to survive inspection.
- Win plan authoring for deals above deal-size threshold entering the final third of
  the sales cycle.
- Pipeline hygiene reviews to cull deals older than 2× average sales cycle without
  a compelling event.

## MEDDPICC Discipline

All eight elements must carry documented evidence, not assumptions. A score without
evidence is a guess. Gaps are surfaced explicitly; no element is marked complete
until the evidence statement is verifiable in the deal record.

### Metrics

The quantifiable outcome the buyer must achieve. Evidence format: specific number,
current baseline, target state, and consequence of missing it. "Better reporting" is
a feature request, not a metric. Acceptable evidence: "Reduce new-hire onboarding
from 14 days to 3, saving $420K annually in lost productivity." If the buyer cannot
articulate the metric, the internal business case does not exist. Help them build it
or disqualify.

### Economic Buyer

The individual who controls budget allocation and can approve spend without escalation.
The EB is not necessarily the contract signer. Test: can this person reallocate budget
from another initiative to fund this deal? If the answer is uncertain, access has not
been earned. EB access is negotiated through the Champion; it is not granted by
title-matching org charts.

### Decision Criteria

The explicit technical, business, and commercial criteria the buying committee will
use to evaluate options. If criteria are undocumented, the competitor who co-authored
them is leading. Decision criteria must be captured before the formal evaluation stage.
Criteria not yet documented are treated as adverse until confirmed neutral or favorable.

### Decision Process

The sequential steps from shortlist to signed contract, including approval levels,
committee composition, timeline, and explicit dependencies between steps. Every
unmapped step is a place the deal can stall without visible cause. Required capture:
step name, owner (buyer side), gate condition, and estimated duration.

### Paper Process

Legal review, procurement intake, security questionnaire, vendor risk assessment,
DPA execution, and InfoSec review. Paper process is the operational gauntlet where
verbally-won deals die. Initiation timing: no later than stage 3 of a 5-stage cycle.
A 6-week procurement cycle discovered in week 11 destroys the quarter.

### Identify Pain

The specific, quantified business problem driving urgency. Pain has a cost—revenue,
risk, time, or reputational. Acceptable evidence: "Lost three enterprise deals last
quarter because implementation took 90 days; competitor does it in 30. Each loss
averaged $280K ACV." If the buyer cannot state the cost of inaction, urgency is
assumed, not real. Assumed urgency produces forecast slippage.

### Champion

An internal advocate with organizational power, access to the Economic Buyer and
decision process, and personal motivation for the initiative to succeed. Qualification
test: ask the Champion to do something difficult—internal meeting request, sharing
competitive intelligence, or advancing a next step. A contact who declines hard asks
is a coach, not a Champion. A Champion sells internally when the vendor is not present.

### Competition

Every deal has competition: direct rivals, adjacent products expanding scope,
internal build teams, and status quo (do nothing). The competitive map must capture:
where the deal is won (criteria aligned to vendor strengths), where it is contested
(both vendors credible), and where it is losing (criteria aligned to rival strengths).
Losing zones are addressed by repositioning criteria weight, not by attacking the
rival's capabilities.

## Opportunity Scoring Rubric

Each MEDDPICC element is scored 1–5. Aggregate score drives forecast tier.

| Element | 1 (No evidence) | 3 (Partial / unvalidated) | 5 (Documented / verified) | Weight |
|---|---|---|---|---|
| Metrics | No quantification | Buyer stated goal; no cost model | CFO-validated metric + ROI model | 1.5× |
| Economic Buyer | Unknown | Named; no direct access | Direct conversation; budget confirmed | 2.0× |
| Decision Criteria | Unknown | Draft list; not finalized | Signed-off criteria; mapped to differentiators | 1.0× |
| Decision Process | Unknown | Steps partial; owners unclear | Full map; each step owned + timed | 1.0× |
| Paper Process | Not raised | Raised; timeline unknown | Initiated; timeline confirmed | 1.5× |
| Identify Pain | Not articulated | Described; not quantified | Cost of inaction quantified; validated by ≥2 stakeholders | 2.0× |
| Champion | No advocate identified | Friendly contact; not tested | Tested; acts internally; coaches deal | 2.0× |
| Competition | Not mapped | Direct rival named; gaps unknown | Full zone map; battlecard active | 1.0× |

**Weighted aggregate threshold:**

| Tier | Weighted Score | Forecast Category | Action |
|---|---|---|---|
| Strong | ≥38 | Commit | Defend in forecast; activate close plan |
| Qualified | 28–37 | Best Case | Close gap plan required before next stage |
| Developing | 18–27 | Pipeline | Gap plan required; no commit forecast |
| Weak | <18 | At Risk | Disqualify or restart qualification |

A deal with any single element scored 1 on a 2.0× weight (Economic Buyer, Pain,
Champion) is capped at Best Case regardless of aggregate score until the gap closes.

## Competitive Positioning Frame

### Zone Classification

For each active competitor, classify every evaluation criterion as one of three zones:

- **Winning zone** — vendor's differentiation is clear and the buyer values it.
  Action: amplify weight; make these criteria central to evaluation scoring.
- **Contested zone** — both vendors are credible on this criterion.
  Action: shift the conversation to adjacent factors (implementation velocity, total
  cost of ownership, ecosystem integration) where separation can be created.
- **Losing zone** — competitor's capability is genuinely stronger on this criterion.
  Action: do not attack; reposition the criterion's weight. Talk track structure:
  "They are strong at X. Customers at your scale typically find Y matters more
  because [evidence]." Never fabricate capability claims to cover a losing zone.

### Battle-Card Structure

Each active competitor requires a documented battle card. Required fields:

| Field | Content |
|---|---|
| Competitor | Name |
| Encounter rate | % of pipeline where this rival appears |
| Their stated strength | Specific capability they lead with |
| Truthful counter | Factual repositioning—not a denial |
| Proof point | Reference customer, third-party validation, or measured outcome |
| Landmine questions | Discovery questions that surface requirements where the vendor leads |
| Trap handling | If buyer cites [competitor claim] → respond with [reframe] |

**Landmine question discipline:** questions asked during discovery that surface
requirements aligned to vendor strengths are legitimate business questions, not
manipulation. They must be defensible as genuine discovery. Example: if the vendor
handles multi-entity consolidation natively and the rival requires middleware, ask:
"How are you managing data consolidation across subsidiary entities today? What breaks
when you add a new legal entity?" The answer surfaces a real operational gap.

## Win Plan Authoring

A win plan is required for all deals above deal-size threshold entering the final
third of the sales cycle. The win plan is a stage-gated action plan, not a narrative.

### Win Plan Required Fields

| Field | Description |
|---|---|
| Deal name + ACV | Account name and annual contract value |
| Close date | Committed close date with basis |
| MEDDPICC score | Current weighted aggregate |
| Champion name | Named Champion with test evidence |
| Economic Buyer | Named EB; last contact date; access method |
| Compelling event | External or internal event driving the timeline |
| Competitive zone | Winning / Contested / At Risk + active rivals |
| Paper process status | Stage; estimated completion date |

### Stage-Action Table

Each stage of the close plan carries explicit buyer-side and seller-side actions,
a completion gate, and an assigned owner. Template:

| Stage | Seller action | Buyer validation | Owner | Target date | Exit gate |
|---|---|---|---|---|---|
| Technical validation | Deliver proof of concept | Technical stakeholder sign-off | AE + SE | [date] | Written summary from buyer |
| Economic justification | ROI model walkthrough | EB attends; approves model | AE | [date] | EB verbal commit on budget |
| Legal / paper | Redline MSA + DPA | Procurement initiates intake | AE + Legal | [date] | First markup returned |
| Final approval | Executive alignment call | EB + executive sponsor confirm | AE | [date] | Verbal go ahead |
| Contract execution | Order form delivered | Signature obtained | AE + RevOps | [date] | Signed document |

Stages without a buyer-side validation action are stalled stages wearing close
plan formatting. Every stage requires a buyer commitment, not just a seller task.

## Risk Surfacing Discipline

The following risk patterns require immediate escalation to the close plan with a
documented remediation step and deadline. An undocumented risk is an unmanaged risk.

| Risk pattern | Severity | Required action |
|---|---|---|
| Single-threaded to a contact who is not the EB | High | Champion must broker EB introduction within 10 business days |
| No compelling event or consequence of inaction | High | Qualify out of commit forecast; establish urgency before re-entry |
| Champion will not grant EB access | High | Re-evaluate Champion status; identify alternate path |
| Stale deal: no buyer-side activity in 30+ calendar days | High | Re-engagement conversation with explicit next step or disqualify |
| Decision criteria map cleanly to a rival's known strengths | High | Reposition criteria weight immediately; do not proceed to proposal |
| Paper process not initiated by stage 3 of 5 | Medium | Initiate procurement conversation regardless of deal status |
| Mute champion: no internal advocacy visible | Medium | Test Champion with a hard internal ask within 5 business days |
| Late-arriving competitor: new rival enters evaluation post-stage 2 | Medium | Update battle card; assess criteria impact; adjust competitive zone map |
| No quantified pain: buyer cannot state cost of inaction | Medium | Return to discovery; do not advance stage without pain quantification |
| Buyer-initiated contact with no stated business problem | Low | Discovery required before any solution conversation |

## Anti-patterns

Patterns that produce forecast error, extend cycle time, or cause late-stage losses.
Each carries a detection signal and a corrective action.

| Anti-pattern | Detection signal | Corrective action |
|---|---|---|
| Happy-ears qualification | Rep describes deal health with phrases such as "they loved the demo" or "we have great relationships" without documented evidence | Require MEDDPICC evidence entries; replace narrative with data |
| Missing Decision Process | Stage 3+ deal with no step-by-step map of buyer approval sequence | Block stage advancement until Decision Process is documented |
| Champion conflated with high-title contact | Named Champion has senior title but has never taken a hard internal action | Test Champion immediately; re-evaluate status if test is declined |
| Metrics-free pipeline | Pain described qualitatively; no cost of inaction stated | Return to discovery; no advance without quantified metric |
| Paper process deferred to close | Procurement timeline raised only after verbal agreement | Paper process must be initiated at stage 3 regardless of deal momentum |
| Artificial deadline | Buyer "needs it by Q-end" with no underlying compelling event | Identify the external driver; if none exists, the urgency is assumed |
| Evaluation criteria not documented | Rep assumes criteria favor the vendor based on relationship quality | Map all criteria explicitly; treat undocumented criteria as unknown |
| Competitor dismissed without zone analysis | Rep states "they're not a real threat" without evidence | Require battle-card completion for every named competitor |
| Single-threaded executive relationship | All access flows through one contact regardless of title | Identify two additional stakeholder contacts within 15 business days |
| Stage advancement on seller activity | Deal moves to next stage because seller completed a task; buyer made no commitment | Stage advance requires buyer-side validation gate, not seller task completion |
| Forecast optimism without close plan | Deal in commit forecast without a documented stage-action table | Block commit forecast entry until win plan is complete |
| Proposal sent before discovery complete | RFP or proposal delivered before pain, criteria, and process are documented | Return to discovery or accept the deal is not qualified |

## Cross-References

- `domains/sales/skills/pipeline-analyst` — pipeline-level risk aggregation,
  stage distribution analysis, and conversion rate modeling across the full book.
- `domains/sales/skills/account-strategist` — account-level relationship mapping,
  expansion planning, and multi-product opportunity development within existing accounts.
- `domains/sales/skills/proposal-strategist` — proposal structure, executive summary
  authoring, and commercial packaging for deals that have passed MEDDPICC qualification.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review) — every authored
  MEDDPICC capture, scorecard, and close plan under this skill is
  subject to two-pass adversarial review before Owner sign-off.
- **ADR-060 amendment §Bulk creative-authoring path** — governs
  domain-skill authoring discipline (tier assignment, scope_tags, the
  structural_inspiration relationship in `inspired_by`, and the
  ≤12-word verbatim / ≤4-word H2 constraints).
