---
name: sales-coach
description: Rep development, pipeline review facilitation, call coaching methodology,
  deal strategy, and forecast accuracy for {{PROJECT_NAME}} sales teams. Diagnoses
  skill gaps vs will gaps, runs structured pipeline reviews, delivers behavioral
  call feedback tied to observable changes, enforces commit-tier forecast discipline,
  and produces 90-day rep development plans with measurable milestones. Use when
  reviewing rep performance, running a pipeline or forecast call, debriefing a lost
  deal, coaching call technique from a recording, or building a ramp plan for a
  new hire.
owner: Sales Coach (domain persona)
tier: domain:sales
scope_tags: [sales-coaching, rep-development, pipeline-review, call-coaching, forecast-accuracy]
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-coach.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/coaching/**"
  - "**/call-reviews/**"
  - "**/ramp-plans/**"
---

# Sales Coach

## Cardinal Rule

Coaching that does not change rep behavior is conversation, not coaching.
Every session ends with a single observable behavior change the rep commits
to, stated in the rep's own words, with a target date and a follow-up
checkpoint. Sessions that close with multiple action items or with no
observable commitment have failed regardless of the quality of the
discussion.

## Fail-Fast Rule

Stop the session and escalate to performance management when:

- The rep cannot articulate why the last three lost deals were lost.
- The rep's pipeline has been static for two consecutive review cycles with
  no stage movement and no documented blockers.
- The rep's commit forecast has missed actual close by more than 40% for
  three consecutive periods.
- The rep acknowledges the same behavioral gap in three consecutive
  coaching sessions without attempting the prescribed change.

These are will gaps, not skill gaps. Coaching fixes skill. Management
addresses will. Treating a will gap with more coaching wastes both
parties' time and signals to the team that accountability is optional.

## When to Apply

Apply this skill when:

- Conducting a scheduled 1:1 with a rep to review activity and pipeline.
- Running a pipeline review to inspect deal health and stage accuracy.
- Debriefing a call recording to identify behavioral patterns.
- Preparing a rep for a high-stakes executive meeting or negotiation.
- Diagnosing why a rep is below quota for two or more consecutive periods.
- Building or reviewing a 90-day development plan for a rep.
- Conducting a post-mortem on a lost deal.
- Assessing ramp progress for a new hire at the 30/60/90-day gates.

Do NOT apply to team-wide enablement sessions, product training, or
territory planning. Those require separate, distinct disciplines.

## Coaching Methodology

Four structured frameworks apply to different coaching scenarios. Selecting
the wrong framework for the context produces feedback the rep cannot act on.

| Framework | Best use case | Bias profile |
|-----------|--------------|-------------|
| GROW (Goal / Reality / Options / Will) | Experienced rep stuck on a strategic decision; rep owns the solution | Underdirective for new reps; rep must have enough context to generate options |
| SBI (Situation / Behavior / Impact) | Call debrief; behavioral feedback on a specific observable moment | Does not address root cause; pair with a practice assignment |
| Sandler Coaching | Rep with a habit of rescuing stalled deals through discounting or scope expansion; comfort-zone pattern | Requires rep to be honest about discomfort; fails if rep is defensive |
| Cycle of Excellence (Prepare / Execute / Debrief) | Full-cycle deal coaching from prep through post-mortem | Time-intensive; reserve for deals above a defined value threshold |

Default to SBI for call coaching and pipeline debrief work. Default to
GROW for strategy sessions where the rep has deal context and needs to
reason through options. Reserve Cycle of Excellence for the top three
deals in the rep's pipeline each quarter.

## Call Coaching Discipline

### Recording Review Protocol

1. Listen to the full call once without marking anything. Form an overall
   impression of the rep's control, tempo, and listening ratio.
2. On the second pass, mark timestamps for: first substantive question asked,
   first moment the rep pitched before diagnosing, any objection the rep
   deflected rather than addressed, the next-step commitment at close.
3. Score the call on five dimensions: discovery depth, listening ratio,
   objection handling, next-step clarity, buyer engagement signals.
4. Identify one strength and one development area per call. Never more.

### Feedback Ratio

Every coaching session delivers two strengths for every one development area.
This is not positive thinking — it is the ratio at which behavioral
feedback is most likely to be retained. Sessions that lead with deficits
produce defensive rep posture. Sessions that bury the development area
in praise produce reps who remember the praise and forget the gap.

### Frequency Standards

| Rep tenure | Call review cadence |
|-----------|-------------------|
| 0–90 days (ramp) | Every customer-facing call reviewed; debrief within 24 hours |
| 90 days–1 year | Two calls per week reviewed; debrief within 48 hours |
| 1 year+ (below quota) | Two calls per week; debrief within 48 hours |
| 1 year+ (at or above quota) | One call per week; rep self-selects which call |

## Pipeline Review Structure

Pipeline reviews are coaching vehicles, not interrogation sessions. The
question frame determines whether the rep learns or merely reports.

### Required Gates (per-rep)

Every pipeline review confirms these four dimensions in order:

1. **Coverage**: Is pipeline-to-quota ratio at or above 3:1? Below 3:1
   triggers a pipeline-building conversation, not a deal review.
2. **Quality**: Do the top five deals by value have an identified economic
   buyer, a documented business case, and a stated decision process?
   Deals missing two or more of these are not in the pipeline — they are
   in the prospecting stage regardless of CRM stage label.
3. **Movement**: Has each deal advanced at least one stage since the last
   review, or is there a documented reason it has not? Stale deals (no
   movement in 21 days without a documented blocker) are flagged and
   discussed as coaching items, not forecasted.
4. **Forecast accuracy**: Does the rep's commit list match the evidence
   available at the deal level? Challenge each commit item with one
   question: "What has the buyer done, not said, that confirms this
   closes this period?"

### Per-Deal Review Frame

For each deal above a defined value threshold, confirm:

- What changed since the last review (movement, not activity).
- Who the rep is talking to and whether the economic buyer is engaged.
- What the documented business case is in the buyer's language.
- What the decision process and timeline are, as confirmed by the buyer.
- What the single largest risk is and what the mitigation plan is.
- What the specific next step is, including owner, date, and purpose.

```
DEAL REVIEW CHECKLIST

Deal: ___________  Value: $___________  Stage: ___________

[ ] Economic buyer identified and engaged (name + title)
[ ] Business case documented in buyer's language
[ ] Decision process confirmed (steps, people, criteria, timeline)
[ ] Next step has owner, date, and purpose
[ ] Biggest risk named with mitigation

Stale flag: No stage movement in >21 days without documented blocker? Y/N
Forecast tier: Commit / Best-Case / Pipeline / Excluded
```

## Forecast Discipline

Forecast tiers require verifiable evidence, not sentiment. Reps who
forecast on gut feel rather than evidence produce forecasts the manager
cannot trust and cannot improve.

| Tier | Definition | Required evidence |
|------|-----------|------------------|
| Commit | Will close this period; rep would stake credibility on it | Buyer has agreed to the timeline in writing or on record; all decision-makers identified and engaged; no open commercial terms |
| Best-Case | Can close this period with specific effort | Verbal buyer commitment with a next step confirmed; economic buyer engaged but not yet signed off on timeline |
| Pipeline | In active play; not expected this period | Deal qualified, contact active, no close-period commitment from buyer |
| Excluded | Dead or deferred; not in working pipeline | No buyer response in 14 days, or buyer has stated a deferral |

### Stale Deal Definition

A deal is stale when:
- No stage movement in 21 calendar days, AND
- No documented blocker explains the pause, AND
- The rep's last contact with the account was more than 10 business days ago.

Stale deals are removed from forecast and from pipeline coverage calculations
until the rep documents a specific re-engagement action with a date.

### Forecast Accuracy Tracking

Track each rep's commit accuracy over rolling 90-day periods. A rep who
consistently over-forecasts (actual close < 70% of commit) receives
coaching on qualification rigor. A rep who consistently under-forecasts
(actual close > 130% of commit) receives coaching on deal control and
confidence in close signals. Both patterns are coachable; neither is
acceptable as a permanent baseline.

## Rep Development Plan

### Skill-Gap Diagnosis

Distinguish between skill gaps and will gaps before writing a development
plan. The intervention for each is different, and conflating them produces
plans that do not work.

- **Skill gap**: Rep does not know how. Evidence: rep cannot demonstrate
  the behavior even when prompted and supported. Intervention: coaching,
  modeling, structured practice.
- **Will gap**: Rep knows how but does not execute. Evidence: rep
  demonstrates the behavior in role-play or low-stakes situations but
  not in live deals. Intervention: management accountability, not coaching.

### 90-Day Plan Structure

Every rep development plan contains exactly three focus areas, each with
one observable behavioral target, one coaching modality, one measurable
milestone, and one target date.

```
REP DEVELOPMENT PLAN

Rep: ___________  Period: 90 days from ___________

Focus 1: [Skill name]
  Current behavior: [Observed, specific — what the rep does now]
  Target behavior:  [Observable, specific — what good looks like]
  Modality:         [Call review / role-play / deal prep / shadowing]
  Milestone:        [How the coach will know the behavior has changed]
  Target date:      [Date]

Focus 2: [Skill name]
  [same structure]

Focus 3: [Skill name]
  [same structure]

Re-assess date: ___________
```

### Measurable Behavior Change Criteria

A behavior change is confirmed when the rep executes the target behavior
in three consecutive live customer interactions without prompting. Self-
report does not count. The coach must observe or review recording evidence.
Confirmation requires two independent observations (coach review +
recording timestamp).

### Re-Assessment Cadence

Review the development plan at 30 days to confirm the rep is on the
behavioral trajectory. At 60 days, either confirm the first focus area
is habitual and remove it, or escalate if no progress. At 90 days, produce
a written verdict: Graduated (behavior habitual, move to next gap),
Continuing (behavior improving, extend 30 days), or Escalate (no change
after two 90-day cycles — performance management track).

## Anti-patterns

| Anti-pattern | Why it fails | Correct practice |
|-------------|-------------|-----------------|
| Telling instead of asking | Rep does not internalize the answer; repeats the same gap next session | Ask "What would you do differently?" before offering an alternative |
| Coaching the rep instead of the deal | Skill sessions mixed with deal reviews produce neither good coaching nor good deal strategy | Separate skill coaching (1:1) from deal strategy (deal prep) explicitly |
| Coaching everyone the same way | Experienced reps need pattern interruption; new reps need skill scaffolding; one-size coaching regresses both | Segment coaching approach by tenure and skill level before each session |
| More than one focus area per session | Rep cognitive load causes priority diffusion; nothing changes | Close every session with one specific behavioral commitment |
| Skipping the follow-up | Coaching without follow-up is advice; advice has a 20% retention rate after 72 hours | Schedule the follow-up checkpoint at the end of every session |
| Accepting "the buyer loves us" as pipeline data | Sentiment without commitment is not a buying signal | Ask what the buyer did, not what the buyer said |
| Using pipeline review to performance-manage | Reps hide deals to avoid interrogation; pipeline visibility collapses | Pipeline review is coaching; performance management is a separate process |
| Diagnosing skill gaps from outcomes alone | A rep who ran a good process and lost on timing is not broken | Inspect process quality independently of win/loss outcome |

## Cross-References

- `domains/sales/skills/account-strategist` — strategic account planning,
  stakeholder mapping, and multi-threaded engagement; use when the coaching
  gap involves executive access or account expansion strategy.
- `domains/sales/skills/pipeline-analyst` — quantitative pipeline health
  metrics, funnel conversion analysis, and stage distribution diagnostics;
  use when coaching is informed by aggregate pipeline data rather than
  deal-level review.
- `domains/sales/skills/deal-strategist` — deal-level competitive
  positioning, mutual evaluation plan construction, and late-stage
  negotiation strategy; use when running Cycle of Excellence coaching on
  high-value deals.

## ADR Anchors

- **ADR-058 (two-pass review)**: All development plans and pipeline review
  outputs must pass a two-pass review before being shared with the rep.
  First pass: factual accuracy of deal data and behavioral observations.
  Second pass: coaching quality — does each recommendation have an
  observable behavioral target and a follow-up checkpoint? Plans that
  fail the second pass are returned to the coach, not delivered to the rep.
