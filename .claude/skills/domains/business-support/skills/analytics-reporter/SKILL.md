---
name: analytics-reporter
description: |
  Business intelligence reporting discipline covering data-source-of-truth
  selection, dashboard design, narrative reporting, statistical literacy,
  visualisation discipline, and audience-tailored output. Governs how
  business metrics are surfaced to executives, operations teams, and
  analysts: canonical source per metric, one decision per page, insight
  over data, and chart type matched to question. Distinct from
  `core/observability-and-ops` (technical telemetry and system health) —
  this skill concerns business-domain reporting on revenue, customers,
  pipelines, and operations. Use when designing or auditing a KPI
  dashboard, writing a narrative report for leadership, choosing a
  visualisation type, or evaluating a reporting cadence proposal.
owner: Camila Reyes (Analytics Reporter, domain persona)
tier: domain:business-support
scope_tags: [business-intelligence, dashboard-design, narrative-reporting, statistical-literacy, audience-tailoring]
inspired_by:
  - source: msitarzewski/agency-agents/support/support-analytics-reporter.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/dashboards/**"
  - "**/reports/**"
  - "**/kpi/**"
---

# Analytics Reporter

## Cardinal Rule

Data without a decision it enables is inventory, not reporting. Every
report, dashboard, or data artefact produced under this skill must map
to a specific decision or action its audience can take. If no decision
or action is identified, the output is deferred until one is named. All
outputs are subject to the two-pass review gate (ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- The canonical data source for a metric is undefined, disputed, or
  differs from the source used in the current analysis.
- A metric is derived from screenshots, exports from an unversioned
  spreadsheet, or any source with no documented lineage.
- Sample size is below the minimum required for the statistical claim
  being made, and the audience is not informed of this constraint.
- Axes, time windows, or currency differ between charts that will be
  read together.
- A rate or index is about to be averaged without denominators.

## When to Apply

Apply when any of the following is true:

- Designing or reviewing a business KPI dashboard for any audience tier.
- Writing a narrative report for leadership, operations, or investors.
- Selecting a chart type or visualisation encoding for a business metric.
- Evaluating or proposing a reporting cadence (daily / weekly / monthly
  / quarterly).
- Auditing an existing report for statistical or framing errors.
- Presenting trend, composition, comparison, or distribution data.

Do not apply to system health telemetry, error-rate monitoring, or
infrastructure observability — see `core/observability-and-ops`.

## Data Source-of-Truth Selection

Every metric in a report has exactly one canonical source. That source
is documented before the report is authored.

| Requirement | Rule |
|---|---|
| One source per metric | If two systems report different revenue figures, stop. Resolve the discrepancy with data owners before publishing. |
| Lineage documented | State the source table/query/pipeline and the snapshot time in a footnote or appendix on every report. |
| No screenshots | Screenshots from dashboards, spreadsheets, or BI tools are not admissible as source data. They are decorative only. |
| Transformation chain | Any transformation between source and metric is documented as a formula or query, not described in prose. |
| Refresh cadence | State when the data was last refreshed. Stale data displayed as current is a reporting defect. |

### Common lineage anti-pattern

Metric shown in a deck sourced from "someone's export" that was
processed in an unnamed spreadsheet is untraceable. The fix is not to
add a footnote saying "source: finance team" — it is to trace back to
the raw source table and re-derive.

## Dashboard Design

Dashboards are decision support surfaces, not data museums.

### Signal density

Each page of a dashboard answers one question. If a dashboard page has
more than one question it is answering, split the page. Dense dashboards
with 20+ metrics per screen cause decision paralysis and suppress use.

### Visual hierarchy

Top-left carries the primary signal. Supporting context goes lower and
right. Annotations explaining anomalies appear inline, not in a separate
legend.

### One decision per page

State the decision the page enables at the top of the page, visible
without scrolling:

> "Is this week's pipeline coverage sufficient to hit monthly quota?"

Dashboards without this framing are exploration tools, not decision
tools. Exploration tools are not shipped to leadership.

### Never decorate

Every visual element either encodes data or aids interpretation. Drop-
shadows, 3D effects, gradient fills, and decorative iconography are
removed. They consume attention without adding signal.

## Narrative Reporting

Narrative reports accompany dashboards; they are not transcripts of
charts.

### Insight over data

The lead sentence of any section names the insight, not the metric:

- Correct: "Activation dropped sharply in the mid-tier cohort, driven
  by a single onboarding step with a 43% abandonment rate."
- Incorrect: "The activation rate for mid-tier customers was 57% in
  Q2, down from 71% in Q1."

The data supports the insight. It does not replace it.

### One headline per report

Each report has one headline finding. Multiple co-equal headlines signal
that the report has not been synthesised — the author has exported the
analysis, not interpreted it.

### Bury caveats no longer

Caveats appear in the section they qualify, not in an appendix the
audience will not read. If a caveat changes the interpretation of a
finding, it belongs in the same paragraph as the finding, stated plainly.

### Report length discipline

| Audience tier | Target length |
|---|---|
| Executive (C-suite, board) | 1 page / 5-minute read |
| Operations (team leads, managers) | 2–4 pages / 10-minute read |
| Analyst (data team, technical deep-dive) | Unlimited, with executive summary on page 1 |

## Statistical Literacy

Analytics outputs are only as reliable as the statistical reasoning
behind them. The following rules are non-negotiable.

### Correlation and causation

Observed co-movement between two metrics is reported as correlation
unless a controlled experiment or a clear causal mechanism is documented.
Causal language (drove, caused, led to) is reserved for experiments
with appropriate controls.

### Sample-size awareness

Every claim derived from a sample states:

1. The sample size (n).
2. Whether the sample is representative of the population being
   generalised to.
3. The confidence interval or margin of error on the metric.

Claims from samples below 30 are labelled directional; they are not
presented as conclusions.

### Outlier handling

Outliers are documented, not silently removed. If an outlier is excluded
from a chart or aggregate, a note states: the excluded value, the reason
for exclusion, and what the metric looks like with and without it.

### Never average ratios

Averages of rates or ratios (conversion rate, churn rate, margin
percentage) are always weighted by the denominator. Unweighted averages
of rates produce numerically incorrect results and are prohibited.

```
# WRONG
avg_conversion = mean([rate_cohort_a, rate_cohort_b, rate_cohort_c])

# CORRECT
avg_conversion = (
    sum(conversions) / sum(sessions)
)
```

### Never average percentiles

p95 across groups is not the average of each group's p95. Report
percentiles only from the full population, or state explicitly that you
are reporting representative-sample percentiles.

### Percent-of-percent confusion

Absolute change and relative change are labelled explicitly. "Revenue
grew 5 percentage points" and "revenue grew 5 percent" are different
claims. Never conflate them.

## Audience-Tailoring

The same underlying data surfaces in different forms for different
audiences. Format follows audience; the data does not change.

| Audience | Primary need | Format signal |
|---|---|---|
| Executive | Decision clarity | One headline, two supporting facts, one recommended action |
| Operations | Diagnostic depth | Trend + comparison + top-driver breakdown |
| Analyst | Reproducibility | Full methodology, source queries, sensitivity notes |

Never produce a single report intended for all three tiers simultaneously.
A combined report optimises for no one.

### Vocabulary calibration

Analyst-tier vocabulary (p-value, confidence interval, regression
coefficient) does not appear in executive-tier reports without a one-sentence
translation. Untranslated technical vocabulary signals the author has not
synthesised — the audience bears the cost.

## Reporting Cadence

Cadence matches the decision tempo of the audience, not the availability
of data.

| Cadence | Suitable for |
|---|---|
| Daily | Operational metrics with same-day intervention (support queue, activation blockers, SLA breach) |
| Weekly | Tactical performance tracking (pipeline, retention cohort, campaign performance) |
| Monthly | Strategic KPI review (revenue vs budget, CAC/LTV, product adoption curves) |
| Quarterly | Architectural decisions (market position, segment mix, long-range forecast accuracy) |

Cadence more frequent than the decision tempo creates noise; the audience
trains itself to ignore the reports. Cadence inflation is a reporting defect.

## Visualisation Discipline

Chart type is a function of the question being answered.

| Question type | Preferred chart | Prohibited |
|---|---|---|
| Trend over time | Line chart | Bar chart with many time periods |
| Part-of-whole composition | Bar chart (stacked or 100%) | Pie chart (>3 slices), donut chart |
| Comparison across categories | Bar chart (horizontal if label-heavy) | Radar / spider chart |
| Distribution | Histogram, box-plot | Stacked line |
| Correlation between two variables | Scatter plot | Dual-axis line chart |
| Geographic distribution | Choropleth map | 3D map |

### Never 3D anything

3D bar charts, 3D pie charts, and 3D surface charts introduce visual
distortion that changes perceived magnitude. They are unconditionally
prohibited.

### Colorblind-safe palette

All charts use a palette that is distinguishable under the three most
common colour-vision deficiencies (deuteranopia, protanopia,
tritanopia). Red/green encoding without a secondary differentiator
(pattern, label, shape) is prohibited.

### Consistent axes

Two charts that will appear on the same page, or in the same section of
a report, use the same y-axis scale and the same time window unless the
difference is intentional and labelled. Axis misalignment is a common
source of false impressions about relative magnitude.

### Dual-axis prohibition

Dual-axis charts (two y-axes on one chart) are prohibited except when both
series are labelled in the title and the relationship is the primary question.
Even then, prefer two separate charts aligned vertically.

## Anti-patterns

The following patterns are treated as reporting defects and trigger a
revision request:

1. **Vanity metrics** — metrics that move in one direction by design
   (total registered users, total emails sent) with no denominators
   or quality signal. Replace with rate or engagement metrics.
2. **Data without insight** — chart or table with no annotation, no
   headline, and no framing sentence. The audience is left to form
   their own conclusion from raw data.
3. **Decorative chartjunk** — gradients, drop-shadows, 3D effects,
   clip-art, or decorative icons on any analytical visualisation.
4. **Mismatched cadence** — daily data presented in a quarterly review
   without aggregation; or quarterly targets tracked in a daily ops
   dashboard without a daily proxy metric.
5. **3D charts** — unconditionally prohibited (see Visualisation
   Discipline above).
6. **Percent-of-percent confusion** — relative change presented as
   absolute change, or vice versa, without explicit labelling.

## Cross-References

- `core/observability-and-ops` — system telemetry and infrastructure
  health monitoring (distinct from business-domain reporting)
- `domains/business-support/skills/finance-tracker` — bookkeeping and
  period-close accuracy (upstream source of financial actuals)
- `domains/business-support/skills/executive-summary` — concise
  leadership communication and synthesis discipline

## ADR Anchors

- ADR-058 (two-pass adversarial review gate) — all analytical outputs
  undergo a second pass before delivery; the second reviewer reads
  independently, not from the author's framing.
