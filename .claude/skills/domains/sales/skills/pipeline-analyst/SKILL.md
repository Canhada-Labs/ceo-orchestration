---
name: pipeline-analyst
description: >
  Revenue operations pipeline analysis discipline covering health diagnostics,
  deal velocity mathematics, forecast accuracy methodology, and data-driven
  sales coaching from CRM data. Applies structured qualification depth
  (MEDDPICC), stage-level conversion benchmarks, and engagement-signal
  adjustment to produce probability-weighted forecasts with explicit confidence
  intervals — not single-number guesses. Use when: reviewing pipeline coverage
  against quota, diagnosing stalled deals, constructing a Commit / Best Case /
  Upside forecast, identifying which stage is the primary conversion bottleneck,
  evaluating CRM data hygiene before a forecast call, or coaching a rep on
  deal-level qualification gaps.
owner: Marcus Oliveira (Pipeline Analyst, domain persona)
tier: domain:sales
scope_tags: [revenue-operations, pipeline-health, deal-velocity, forecast-accuracy, sales-analytics, crm-data]
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-pipeline-analyst.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/pipeline/**"
  - "**/forecasts/**"
  - "**/crm/**"
---

# Pipeline Analyst

## Cardinal Rule

A forecast not falsifiable against last-quarter prediction error is opinion;
opinion does not earn coverage targets. Every forecast output MUST carry an
explicit confidence band (Commit / Best Case / Upside) AND a stated accuracy
delta versus the prior period — "Q2 Commit was $4.1M, actual was $3.8M,
error −7.3%" — before any new number is presented for planning. A single
point estimate without a confidence interval and a retrospective error
anchors every downstream plan to false precision and trains the organization
to ignore the analyst.

---

## Fail-Fast Rule

Pipeline review sessions MUST NOT begin with stage-weighted CRM totals as
the headline number. Stage probability weights are assigned at deal creation,
not updated on deal behavior; a deal sitting at Stage 3 for 60 days carries
the same CRM weight as one that entered Stage 3 yesterday. Before any coverage
ratio is reported, the following gates MUST pass: (1) all deals with zero
activity in the past 30 days are flagged and excluded from the quality-adjusted
count; (2) coverage is computed against remaining quota — not full-year quota —
for the current period; (3) the Commit category contains only deals with a
defined close path and no open procurement blocker. If any gate fails, the
headline number is not ready to present.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Running a pipeline review — weekly, monthly, or quarterly — and producing
  a Commit / Best Case / Upside forecast output.
- Diagnosing why a quarter is tracking below or above plan before the
  quarter closes.
- Identifying the primary stage-level conversion bottleneck in a funnel.
- Evaluating whether current pipeline creation rate will sustain the quota
  target two to three quarters out.
- Scoring individual deal health using MEDDPICC depth and engagement signals.
- Auditing CRM data quality before a forecast call or board presentation.
- Coaching a rep or segment on qualification gaps correlated with deal loss.

Skip when: the engagement is pre-pipeline lead generation (use
discovery-coach instead); the task is a closed-won account expansion plan
(use account-strategist instead); or the request is a deal-specific
negotiation strategy (use deal-strategist instead).

---

## Pipeline Health Frame

Pipeline health is four distinct measurements that can diverge. Treat each
independently — a high-coverage, low-velocity pipeline is a different failure
mode than a low-coverage, high-velocity one.

### Coverage

The ratio of open weighted pipeline to remaining quota for the current period.

Targets by business context:

| Context | Minimum Coverage Ratio |
|---|---|
| Mature, predictable market | 3.0x |
| Growth-stage or new market | 4.0–5.0x |
| New rep ramping | 5.0x+ |

Coverage is always computed quality-adjusted: deals with no activity in 30+
days, missing close dates, or fewer than 5 of 8 MEDDPICC fields populated
are discounted or excluded from the quality-adjusted figure. Raw stage-weighted
pipeline is reported separately as a reference, never as the primary number.

### Velocity

How quickly revenue moves through the funnel per unit of time. See
`## Velocity Mathematics` for the formula and lever-pulling order.

### Quality

MEDDPICC population depth per deal, combined with engagement recency and
stakeholder breadth. A pipeline of 20 stale, underqualified deals is
worth less than 8 active, well-qualified opportunities at the same nominal
dollar value. Quality beats quantity in every coverage calculation.

### Movement

Stage progression rate versus benchmark. Deals that have not advanced in
more than 1.5× the median stage duration for their segment are classified
as stalled. Stalled deals MUST be flagged for intervention or removal —
not carried silently in the forecast.

---

## Coverage Discipline

Coverage analysis follows a fixed sequence; shortcuts produce misleading
conclusions.

1. Establish remaining quota for the period — not full-year quota.
2. Pull all open deals with stage, amount, close date, last activity date,
   and MEDDPICC field count.
3. Compute raw weighted pipeline (stage probability × amount).
4. Apply quality adjustment: exclude or discount deals failing the three
   hygiene gates (no activity 30+ days, missing close date, MEDDPICC < 5/8).
5. Calculate quality-adjusted coverage ratio = quality-adjusted pipeline /
   remaining quota.
6. Segment by deal size (e.g., SMB < $25K, Mid-Market $25K–$150K, Enterprise
   $150K+). Blended averages hide the signal.
7. Calculate pipeline creation rate (new qualified pipeline added per week)
   and project forward to determine whether coverage will be adequate when
   the period closes.

Gap diagnostics:

- Coverage below 2x with eight or fewer weeks remaining: pipeline creation
  alone cannot close the gap; deal-level intervention and forecast revision
  are both required.
- Coverage appears adequate but quality-adjusted ratio is below 2x: pipeline
  is volume-inflated; remove or reclassify stale deals before the next call.
- Coverage healthy but creation rate declining: no current-quarter risk, but
  the following quarter is at risk; signal must be escalated now.

---

## Velocity Mathematics

Pipeline velocity is the single compound metric that captures pipeline health
as a rate rather than a snapshot.

```
Pipeline Velocity = (Qualified Opportunities × Average Deal Size × Win Rate)
                    / Sales Cycle Days
```

Each variable is a diagnostic lever with a distinct intervention:

| Lever | Declining signal | Primary intervention |
|---|---|---|
| Qualified Opportunities | Top-of-funnel shortfall; shows in revenue 2–3 quarters later | Increase sourcing activity; segment by source |
| Average Deal Size | Discounting pressure or market shift | Segment; check if specific reps are systematically underpricing |
| Win Rate | Stage-level decay; check stage-by-stage to isolate where deals die | Process fix (systemic) or coaching (individual) depending on distribution |
| Sales Cycle Days | Lengthening = competitive pressure, larger buying committees, or qualification gaps | Qualify harder at entry; compress paper process |

Lever-pulling order: address the earliest-stage lever first. Declining
qualified opportunity volume is a 2–3 quarter leading indicator; declining
win rate at the Evaluation stage is a current-quarter indicator. Both matter,
but the order of intervention reflects urgency versus structural impact.

Win rate MUST be segmented before drawing conclusions. An aggregate win rate
improvement that is driven entirely by closing smaller, lower-competition
deals is not an improvement signal — it is a mix shift that will suppress
average deal size in subsequent periods.

---

## Forecast Accuracy Methodology

Forecast categories carry defined confidence thresholds, not subjective labels.

| Category | Confidence Threshold | Inclusion Criteria |
|---|---|---|
| Commit | > 90% | Verbal or written agreement; no open procurement blocker; close-date confirmed by buyer |
| Best Case | 60–90% | Commit + high-velocity qualified deals with active multi-threaded engagement |
| Upside | < 60% | Best Case + early-stage high-potential deals; explicitly speculative |

Forecast construction steps:

1. Start from historical base rates: what percentage of deals at each stage,
   in each segment, in the same calendar period one year ago actually closed?
   These are the base-rate priors. CRM stage probabilities are almost always
   higher than empirical base rates.
2. Apply velocity adjustment: deals progressing faster than segment benchmark
   receive a probability uplift; deals stalled beyond 1.5× median duration
   receive a discount.
3. Apply engagement adjustment: multi-threaded deals with buyer-initiated
   activity in the past 14 days close at materially higher rates than
   single-threaded, low-activity deals at the same stage.
4. Apply seasonal adjustment: quarter-end compression, budget cycle timing,
   and industry-specific patterns are predictable variance — account for them.
5. Report the delta between this model and the raw stage-weighted CRM total.
   A large positive delta (model > CRM) suggests deals progressing faster
   than CRM weights reflect. A large negative delta (model < CRM) is a risk
   flag requiring deal-by-deal review.

Accuracy tracking is mandatory. Every forecast call records the Commit
number. After the period closes, the actual versus Commit delta is logged.
Forecast accuracy cannot improve without this retrospective record.

---

## Stage Definition Discipline

Stage definitions MUST be expressed as buyer-observable entry criteria, not
as seller activities.

Falsifiable example: "Buyer has completed a live demo and provided written
evaluation criteria."

Non-falsifiable example: "Demo has been scheduled." — reject.

Criteria checklist for each stage definition:

- Can a third party verify the criterion from CRM data or a meeting record?
- Does the criterion reflect something the BUYER has done, not the seller?
- Is there a clear binary: the criterion is met or it is not?

Rotting thresholds: each stage has a maximum age. Deals exceeding 1.5× the
segment's median stage duration without documented advancement are flagged
as stalled. Stalled deals are reviewed at the next pipeline call and either
receive a documented intervention plan or are moved to a later stage in the
forecast with an appropriate probability discount.

---

## CRM Data Hygiene

Four fields are required for any deal to be included in forecast analysis
without a documented exception:

| Field | Staleness threshold | Consequence of staleness |
|---|---|---|
| Next step with date | 14 days | Deal excluded from Commit; flagged in Best Case |
| Close date | Must be current period or explicitly deferred | Excluded from period forecast |
| Amount | Must reflect current scope | Used as-is with a data-quality note |
| Competitor | Required for late-stage deals | Single-threaded risk flag |

Data hygiene is not an administrative exercise — it is a forecast accuracy
input. A forecast built on stale CRM data is not a forecast; it is a
spreadsheet-formatted guess. The analyst's job is to state data quality
assumptions explicitly before presenting numbers, never to silently
interpolate missing values.

Field weaponization risk: when CRM fields are used for rep performance
management rather than pipeline visibility, reps optimise field values for
manager approval rather than accuracy. Monitor for systematic patterns
(e.g., every deal shows close date on the last day of the quarter) as a
signal that fields have been weaponized and can no longer be trusted for
forecast purposes.

---

## Anti-patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| Hopium pipeline | Deals carried in forecast because the rep believes they will close "eventually," not because there is a close plan. | Apply rotting threshold; require documented close path for all Commit-category deals. |
| Vanity coverage | Reporting raw stage-weighted pipeline as the coverage ratio without quality adjustment. | Always compute quality-adjusted coverage; publish both numbers with explicit delta. |
| Retrofit forecast | Adjusting the forecast methodology after the quarter closes to explain the miss rather than to improve future accuracy. | Lock forecast methodology at the start of the quarter; post-period review modifies the next-period model only. |
| Single-stage chokepoint denial | Win rate is declining but the decline is attributed to individual rep performance rather than a systemic process failure at a specific stage. | Segment win-rate decline by stage, rep cohort, and deal size; a systemic drop affecting multiple reps at the same stage is a process failure. |
| Blended-average blindness | Reporting aggregate metrics across segments, deal sizes, or rep tenure cohorts, hiding the signal in noise. | Always segment before drawing conclusions; blended averages are presented only as a summary after segmented analysis. |
| Point-estimate anchoring | Presenting a single forecast number without a confidence range, training stakeholders to treat the number as precise. | Enforce Commit / Best Case / Upside at every forecast presentation; single numbers are not accepted outputs. |
| Last-quarter anchoring | Adjusting this quarter's forecast by incrementing from the prior-quarter actual rather than analyzing from current deal data. | Build forecast from deal-level data up each period; prior-period actual is an accuracy check, not a starting point. |

---

## Cross-References

- `domains/sales/skills/account-strategist` — post-sale expansion pipeline
  analysis and NRR / GRR tracking.
- `domains/sales/skills/deal-strategist` — deal-level negotiation and
  competitive positioning for individual opportunities.
- `domains/sales/skills/sales-coach` — rep-level performance diagnostics
  and skill-gap identification correlated with pipeline outcomes.

---

## ADR Anchors

- **ADR-058** — domain skill authoring standards: house-voice constraints,
  scope_tags schema, and inspired_by attribution requirements that govern
  this file.
