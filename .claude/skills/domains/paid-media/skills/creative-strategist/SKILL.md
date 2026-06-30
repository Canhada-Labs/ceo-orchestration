---
name: creative-strategist
description: >
  Performance ad creative discipline covering concept framework selection
  (Problem/Agitate/Solve, AIDA, PAS, Hook-Turn-Payoff, Founder-Story,
  Testimonial, Comparison), creative brief architecture, format-specific
  iteration cadence, fatigue diagnostics, UGC and creator strategy, and
  performance creative testing. Distinct from brand creative direction — this
  skill governs paid ad creative as a performance lever, not a brand expression
  instrument. Applies post-iOS-14.5 logic where creative is the primary
  controllable variable in automated-bidding environments. Use when: building
  or reviewing a creative brief for a paid campaign; designing a concept-to-asset
  pipeline; diagnosing creative fatigue from CTR decay or CPM rise; planning a
  UGC creator program; structuring a creative A/B or multivariate test; or
  evaluating format mix against production cost and iteration speed constraints.
owner: Rafael Andrade (Performance Creative Strategist, domain persona)
tier: domain:paid-media
scope_tags: [creative-strategy, performance-creative, ad-concept-frameworks, creative-briefs, fatigue-diagnostics, ugc-mix]
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-creative-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: paid-media
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
  - "**/creatives/**"
  - "**/ad-creative/**"
  - "**/briefs/**"
  - "**/ugc/**"
---

# Creative Strategist

## Cardinal Rule

In automated-bidding environments the algorithm controls bids, budget, and
targeting. Creative is what remains under direct control. Every headline,
image asset, video hook, and description line is a testable hypothesis about
audience psychology — not a brand expression preference. Creative decisions
that are not grounded in a falsifiable brief and measurable KPI are guesses
dressed as strategy. The discipline of this skill is to replace guesswork with
a repeatable authoring and testing loop: research the audience's language,
construct the concept brief from that language, produce minimum-viable variants,
measure against a predefined signal, and iterate on evidence.

---

## Fail-Fast Rule

A creative production cycle MUST NOT start without three confirmed inputs:
a concept framework matched to funnel stage and audience awareness level, a
falsifiable brief with a named success metric, and a defined minimum-variant
count per format. The following conditions MUST hold before any asset enters
production:

1. The concept framework is selected against the target audience's awareness
   level (see Concept Framework Selection below) — not selected by convention
   or personal preference.
2. The creative brief contains a named problem-to-solve, a target audience
   definition distinct from the campaign targeting spec, a single primary
   message, mandatory inclusions, format constraints, and a measurable KPI.
   If the KPI cannot be stated as a number with a direction (e.g., CTR ≥ 1.8%,
   CPA ≤ $42), it is not a KPI — it is an aspiration.
3. Minimum-variant requirements per format are documented before production
   starts. Producing one variant of any format is not a creative test — it is
   a single creative hypothesis with no comparative signal.

If any condition is unresolved, production is blocked until it is closed.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Building a creative brief for a new campaign or a creative refresh cycle.
- Selecting a concept framework for a specific funnel stage or audience cohort.
- Designing the variant set for a creative A/B test or multivariate test.
- Diagnosing underperformance through fatigue signals (CTR decay, CPM rise,
  frequency spike, conversion rate drop with stable targeting).
- Planning a UGC or creator program, including creator brief design, rights
  management, and FTC or ANPD-LGPD disclosure requirements.
- Evaluating format mix decisions (static vs. motion vs. UGC vs. live-action
  vs. animation) against production cost and iteration speed tradeoffs.
- Structuring a concept-to-asset pipeline with defined review gates per stage.

Skip when: the task is media buying, bid strategy, or audience targeting —
route to `domains/paid-media/skills/paid-social-strategist` or
`domains/paid-media/skills/ppc-strategist`; the task is brand identity or
visual design systems — route to brand creative direction; the task is
organic content authorship without a paid distribution objective — route to
`domains/marketing-global/skills/content-creator`.

---

## Concept Framework Selection

Framework selection is driven by audience awareness level and funnel stage, not
by creative preference. Applying a Comparison framework to a cold audience that
has no category awareness produces confusion; applying a Problem/Agitate/Solve
frame to a retargeting cohort already aware of the problem wastes impression
budget on persuasion that already occurred.

### Awareness-to-Framework Mapping

| Audience awareness level | Funnel stage | Recommended framework | Rationale |
|---|---|---|---|
| Unaware (problem not recognized) | Upper funnel / cold | Problem/Agitate/Solve (PAS) | Names the problem before proposing the solution |
| Problem-aware (knows the pain, not the category) | Upper-to-mid | Hook-Turn-Payoff | Interrupts the scroll with the problem, reframes it, delivers the solution |
| Solution-aware (knows solutions exist, not the brand) | Mid funnel | AIDA (Attention-Interest-Desire-Action) | Sequential persuasion through the decision arc |
| Product-aware (knows the brand, not converted) | Mid-to-lower | Comparison or Testimonial | Objection handling and social proof at the decision point |
| Most-aware (previous purchaser or high-intent retarget) | Lower funnel | Testimonial or Founder-Story | Trust reinforcement and identity alignment |

### Framework Descriptions

**Problem/Agitate/Solve (PAS):** Opens with the named problem (not a generic
pain category — a specific symptom), intensifies the cost of inaction (agitate),
then presents the solution as the logical resolution. The agitate step is
where most executions fail — it is not hyperbole; it is specificity about
downstream consequences the audience already fears.

**AIDA (Attention-Interest-Desire-Action):** Sequential arc: interrupt attention
(hook), hold interest with a relevant claim or story beat, create desire by
connecting the product to the audience's aspiration, close with a single action.
Strongest in mid-funnel where the audience is in deliberation mode. Requires
the interest step to be genuinely informative — not a second hook.

**PAS (as distinct from Problem/Agitate/Solve variant):** A compressed version
used in short-format static and copy-only placements. Problem named in one
line, solution in the next, social proof or CTA in the third. Useful for
placements with low dwell time and audiences already in the consideration phase.

**Hook-Turn-Payoff:** Borrowed from video storytelling. Hook: a pattern
interrupt in the first 3 seconds (visual or auditory) that creates a question
in the viewer's mind. Turn: an unexpected pivot that reframes the problem or
introduces tension. Payoff: the resolution that delivers the value and the
CTA. Strongest for short-form video in cold audiences. Fails when the hook
is clickbait that the payoff cannot satisfy.

**Founder-Story:** Narrative of the product origin told through the founder's
lived problem. Strongest in most-aware retargeting cohorts and in verticals
where trust is the primary purchase barrier. Weakest in high-competition
categories where audiences have heard multiple founder stories and treat them
as genre, not signal.

**Testimonial:** A real customer voice narrating a specific transformation —
before state, obstacle encountered, after state, measurable outcome. The
specificity of the outcome (not "my life changed" but "reduced churn from 14%
to 6% in 90 days") is the load-bearing element. Generic testimonials provide
social proof noise, not persuasion signal.

**Comparison:** Explicit contrast between the product and an alternative (a
competitor, the status quo, or the DIY approach). Strongest at the decision
point for a product-aware cohort. Requires legal review in regulated verticals.
The comparison must be on a dimension the audience already values — not a
dimension the brand prefers.

---

## Creative Brief Architecture

A creative brief is a production contract between strategy and execution. A
brief that cannot be falsified — meaning a brief where no possible asset could
be declared "wrong" — is not a brief. It is a mood board with a deadline.

### Required Brief Fields

| Field | Definition | Failure mode if missing |
|---|---|---|
| Problem-to-solve | The specific friction the target audience is experiencing — stated in the audience's language, not the brand's | Brief produces assets that solve the brand's communication problem, not the audience's decision problem |
| Target audience | Named segment with awareness level, funnel stage, and one primary pain — distinct from the campaign targeting parameters | Assets default to generic appeal; framework selection has no anchor |
| Primary message | One claim the audience must leave the ad believing — not a list of benefits | Assets try to communicate everything; communicate nothing |
| Mandatory inclusions | Brand or legal requirements that cannot be modified: logo placement, disclaimer copy, regulated-industry disclosures | Assets fail compliance review after production; re-shoot cost incurred |
| Format constraints | Platform, placement, aspect ratio, duration (video), character limits (copy), file size | Assets are produced in wrong specifications; re-export delays launch |
| KPI | A single measurable signal with a numeric threshold and a direction: CTR ≥ N%, CPA ≤ $N, ROAS ≥ N× | No decision rule for winner/loser; creative rotation driven by feelings |

### Brief Falsifiability Test

Before approving a brief for production, apply this test: given this brief,
could an execution team produce an asset that the brief would classify as
wrong? If the answer is no — if any asset would be "fine" — the brief lacks
either a defined audience, a defined message, or a defined KPI. Revise until
the answer is yes.

---

## Format-Specific Iteration

Format selection balances production cost against iteration speed. High-
production-cost formats (live-action video, animation) require larger minimum
budgets to reach statistical significance before the test is economically
viable. Low-production-cost formats (static, UGC) allow faster iteration at
lower cost per variant but carry lower upper-bound engagement ceiling in some
placements.

### Format Cost vs Iteration Speed Matrix

| Format | Relative production cost | Minimum viable variants | Primary signal | Notes |
|---|---|---|---|---|
| Static image (single) | Low | 3 per concept | CTR, conversion rate | Fastest to iterate; hook is visual + headline; test one variable at a time |
| Carousel | Medium | 2 per concept | CTR, swipe-through rate, link click | Frame 1 is the hook; later frames do not display if Frame 1 fails the hook test |
| Short-form video (≤60s) | Medium-high | 2 per concept | Hook rate (3s view %), completion, CTR | First 3 seconds determine 90% of performance; test hooks separately before full production |
| Long-form video (60-120s) | High | 1-2 per concept | Completion rate, conversion | Reserve for most-aware cohorts where narrative depth is required |
| UGC (creator-produced) | Low-medium (creator fee) | 3-5 per creator | CTR, conversion, ad relevance | Higher variance than studio; scale winners not the entire set |
| Animation / motion graphics | High | 1-2 per concept | Completion, CTR | High production cost justifies only when static variants have validated the concept |

### Per-Format Hook Discipline

For every format, the hook is the highest-leverage variable and must be tested
before the full asset is produced at scale. For static, the hook is the
primary visual combined with the headline. For video, the hook is the first
3 seconds of audio and visual. A concept that tests multiple hooks against
the same body asset will surface the hook winner at lower cost than a concept
that tests complete finished assets.

---

## Fatigue Diagnostics

Creative fatigue is the degradation of ad performance caused by audience
overexposure to the same creative execution. Fatigue is not the same as
market saturation — it is a per-ad-set signal caused by frequency exceeding
the audience's tolerance threshold for a specific execution. Fatigue is
recoverable by creative refresh; saturation requires market or category
strategy revision.

### Fatigue Signal Hierarchy

| Signal | Threshold (advisory) | Action |
|---|---|---|
| CTR decay | 15%+ decline week-over-week for 2+ consecutive weeks | Flag for refresh review |
| CPM rise (same audience, same bid) | 20%+ rise without seasonal or auction explanation | Audit frequency; consider audience expansion |
| Frequency cap breach | ≥ 3 impressions per user per 7-day window (cold) or ≥ 5 per 7-day (retarget) | Pause highest-frequency ads; rotate in challenger variants |
| Conversion rate drop with stable targeting | 10%+ CvR drop without landing page change | Isolate to creative variable; test new hooks |
| Ad relevance diagnostic decline | Drop from above-average to average or below (Meta) | Treat as corroborating signal — not standalone; check in combination with CTR |

### Refresh Cadence by Audience Cohort

| Cohort type | Maximum creative lifespan before scheduled refresh review | Notes |
|---|---|---|
| Cold (prospecting) | 4-6 weeks | Higher impression volume means faster fatigue onset |
| Warm (engagement retargeting) | 6-10 weeks | Lower volume slows fatigue; but stale concepts do damage |
| Hot (cart abandon / high-intent) | 2-4 weeks | Smallest audience; highest frequency per user; shortest cycle |

Refresh-by-feeling — rotating creative because a team member is "bored of
seeing it" without a fatigue signal present — is waste. Rotate on evidence,
not familiarity.

---

## UGC and Creator Strategy

User-generated content in a paid context means content produced by real
customers or paid creators that reads as authentic peer communication rather
than brand-produced advertising. The performance advantage of UGC is its
trust signal and its resistance to the "ad blindness" that affects polished
studio production. That advantage degrades in direct proportion to how much
the brand controls the script.

### Creator Brief vs. Script-Tight Execution

**Creator brief model:** The brand provides the problem-to-solve, the one
primary message, the mandatory inclusions, and the format constraints. The
creator produces the execution in their own voice. Output variance is higher;
trust signal is higher; production cost is lower. Scale the winners.

**Script-tight model:** The brand provides the hook verbatim, the body
structure, and the CTA copy. The creator provides their face and voice. Output
variance is lower; brand control is higher; trust signal is lower. Appropriate
when mandatory disclosures or regulated-industry compliance requirements
constrain the message.

The hybrid model — a brief that provides the concept hook and mandatory
inclusions but leaves body and delivery to the creator — captures most of the
trust signal advantage while maintaining compliance. Use the hybrid model as
the default.

### Performance UGC vs Brand UGC

Performance UGC is optimized for direct response: the brief requires a clear
problem statement, a transformation arc, a specific outcome claim, and a CTA.
Brand UGC is optimized for affinity: softer narrative, no explicit CTA,
identity alignment over transformation. Do not run brand UGC in performance
placements — it will underperform on conversion metrics and inflate CPM
without delivering conversion signal.

### Rights Management

Creator agreements MUST specify:

- Usage rights: paid placement, duration, platforms, geographic scope.
- Exclusivity window: period during which the creator may not produce
  comparable content for a direct competitor.
- Revision rights: number of revision rounds included before additional fees
  apply.
- Takedown conditions: brand's right to remove content that becomes
  associated with negative brand events after publication.

Rights management failures that surface post-launch require emergency takedown
and re-shoot. The cost is 5-10× the cost of front-loading the rights clause.

### FTC and ANPD-LGPD Disclosure Compliance

All paid creator content distributed in Brazilian territory or to Brazilian-
resident audiences is subject to ANPD-LGPD data collection requirements at
the landing destination and to CONAR advertising transparency norms. For
any campaign with an international audience including Brazil: the disclosure
"#publi" or the equivalent platform-native disclosure mechanism is required
in creator-produced paid content. ANPD-LGPD applies to data collected from
the click destination (landing page, lead form), not to the ad creative
itself — but the creative team is responsible for confirming that the landing
destination's data collection is compliant before launch.

For FTC-regulated audiences (US-resident), the disclosure must be prominent
(not buried), unambiguous (not "collab" or "partner" — "Paid advertisement"
or "#ad"), and platform-appropriate. Do not use creator-brief templates that
omit the disclosure requirement — every brief that involves a paid creator
relationship MUST include the disclosure requirement as a mandatory inclusion.

---

## Performance Creative Testing

Post-iOS-14.5, pixel-based audience targeting precision declined across Meta
and programmatic platforms. Creative is the primary remaining lever for
conversion lift in automated-bidding environments. This shifts the testing
investment from audience experimentation to creative experimentation.

### Statistical Significance at Low Base Rates

Conversion events at the bottom of the funnel (purchases, leads, high-value
actions) occur at base rates of 1-5% of ad impressions. This requires larger
sample sizes to reach statistical significance than CTR-based testing. The
practical implication: do not declare a creative winner on conversion signal
alone unless each variant has received ≥ 500 impressions at the conversion-
intent audience level and the difference exceeds the minimum detectable effect
at 80% power.

For high-cost-per-conversion products (LTV > $200), the sample size requirement
may be unachievable within a reasonable budget window. In these cases, use CTR
as the primary signal and conversion as a corroborating secondary signal, with
explicit documentation that the test is CTR-gated.

### A/B vs Multivariate

| Test type | Use case | Minimum duration | Risk |
|---|---|---|---|
| A/B (two variants) | Hook test, single-variable creative element | 7-14 days | Low — cleanest signal |
| A/B (3-4 variants) | Hook set test before full production decision | 10-21 days | Medium — requires sufficient budget per variant |
| Multivariate | Simultaneous test of hook × copy body × CTA | 21-35 days; high budget required | High — interaction effects obscure individual variable attribution |

Default to A/B testing. Multivariate testing is only warranted when budget
is sufficient to reach significance across all cells simultaneously and when
the interaction between variables (e.g., hook style × CTA tone) is the
specific hypothesis under test.

### Winner and Loser Criteria

Before the test launches, document the decision rule:

- Winner: variant that meets or exceeds the KPI threshold with ≥ 95%
  statistical confidence (or the alternative significance threshold documented
  in the brief).
- Inconclusive: no variant meets the threshold within the test window. Document
  the result; do not promote the "best performer" as the winner.
- Loser: variant that underperforms the control by more than the minimum
  detectable effect. Archive; do not re-test the same execution without a
  documented hypothesis for why the next execution would differ.

Promoting an inconclusive result as a winner because the budget is spent is
a testing failure. It produces a winner-rotation dynamic based on random noise,
not signal.

---

## Concept-to-Asset Pipeline

The production pipeline is the governance layer between concept brief and
launched asset. Each stage has a defined output and a defined gate. A stage
does not advance until its gate output exists and has been reviewed.

### Stage Map

| Stage | Owner | Output artifact | Gate to advance |
|---|---|---|---|
| Concept brief | Creative strategist | Written brief with all required fields (see Creative Brief Architecture) | Brief falsifiability test passes |
| Script or copy deck | Copywriter or creator | Platform-formatted copy; video script with scene annotations | Message accuracy review: does the copy deliver the primary message without introducing off-brief claims? |
| Storyboard or mock | Art director or creator | Static storyboard (video) or static mock (image/carousel) | Format compliance check: dimensions, duration, mandatory inclusions |
| Production | Creator or studio | Raw footage or final static | Delivery spec confirmation: file type, size, aspect ratio |
| Review | Creative strategist | Annotated review against brief | Brief compliance: all mandatory inclusions present; KPI hypothesis confirmed |
| Launch | Media team | Live ad with UTM parameters and tracking | Tracking confirmation: conversion event fires on test click |

### Gate Failure Handling

If a review gate surfaces a brief compliance failure (missing mandatory
inclusion, wrong format spec, off-brief message), the asset returns to the
stage that introduced the failure. It does not advance. Gate failures that
are caught post-launch require pause-and-fix — the cost is always higher
than catching the failure at the gate stage.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| Creative-without-research | Producing creative from brand positioning documents rather than audience language research; brief uses brand vocabulary the audience does not use | Conduct T1-T3 audience research (interviews, support transcripts, community language) before brief authorship; extract vocabulary from audience sources, not brand copy |
| Single-format fetish | Running all campaigns in one format (e.g., only static) because the team is most comfortable with it, not because the format fits the placement and audience | Audit format mix against placement data; require at least two formats per campaign to maintain baseline coverage across feed and story placements |
| Refresh-by-feeling | Rotating creative because the team is fatigued by seeing the same ad, without a fatigue signal present in the data | Define and track the fatigue signal hierarchy; pause or rotate only when a signal threshold is breached |
| Ignoring fatigue signals | Continuing to run ads showing CTR decay and CPM rise because the budget cycle has not completed | Monitor fatigue signals on a weekly cadence; treat threshold breaches as blocking events, not advisory notes |
| Copy-paste UGC | Taking creator-produced organic content and repurposing it as a paid ad without adapting the hook, mandatory inclusions, or disclosure language | All UGC used in paid placement must go through the creator brief pipeline; organic content is a concept source, not a production shortcut |
| Inconclusive-promoted-as-winner | Declaring a creative winner because the test window closed, not because the significance threshold was met | Pre-document the winner/loser decision rule in the brief; if neither variant reaches significance, log as inconclusive and design a higher-powered follow-on test |

---

## Cross-References

- `domains/paid-media/skills/paid-social-strategist` — campaign structure,
  audience targeting, bid strategy, platform-specific campaign architecture.
  Route when the task is media buying mechanics, not creative production.
- `domains/paid-media/skills/ppc-strategist` — search ad creative (RSA
  headline architecture, Quality Score optimization, ad extension strategy).
  Route when the creative brief is for search placements rather than social
  or display.
- `domains/marketing-global/skills/content-creator` — organic content
  authorship, narrative architecture, repurposing matrix. Route when the
  content objective is earned distribution without a paid placement brief.

---

## ADR Anchors

- **ADR-058** (Brainstorm gate pre-Plan + two-pass adversarial review): the
  brainstorm gate discipline maps directly to this skill's brief falsifiability
  test. Before a creative concept enters production, the brief must pass the
  falsifiability gate — the creative equivalent of ADR-058's spec artifact
  requirement. The two-pass adversarial review pattern applies to creative
  review: the first pass checks brief compliance (are all required fields
  present, is the KPI numeric and directional?); the second pass applies the
  audience's perspective (would this claim land with the named audience at the
  documented awareness level, or does it assume knowledge the audience does not
  have?).
