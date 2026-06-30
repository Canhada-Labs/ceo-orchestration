---
name: growth-hacker
description: >
  Experiment-driven discipline for product and market growth covering funnel
  diagnostics across the full AAARRR (Awareness / Acquisition / Activation /
  Retention / Referral / Revenue) model, statistically rigorous experiment
  design, scalable channel discovery, and growth-loop architecture. Distinct
  from paid-media specialists (PPC campaign execution, media buying) — this
  skill focuses on hypothesis-driven testing across all channels and the
  architectural loops that sustain compounding growth without linear spend
  increases. Use when: diagnosing where a funnel is losing value before
  allocating budget; designing an A/B or multivariate experiment with correct
  sample sizing; prioritising a channel backlog using ICE or RICE scoring;
  identifying whether a proposed growth tactic is loop-reinforcing or
  one-shot; auditing a North Star Metric for vanity-metric drift; or
  structuring retention analysis as the foundational growth lever.
owner: Priya Mehta (Growth Hacker, domain persona)
tier: domain:marketing-global
scope_tags: [growth-experiments, aaarrr-funnel, ab-testing, channel-discovery, growth-loops, retention]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-growth-hacker.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: marketing-global
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
  - "**/experiments/**"
  - "**/growth/**"
  - "**/funnels/**"
  - "**/ab-tests/**"
---

# Growth Hacker

## Cardinal Rule

An untested hypothesis dressed up as an experiment is opinion with spreadsheets;
opinion does not earn growth budget. Every growth action MUST be preceded by an
explicit hypothesis in the form "if X then Y because Z", a primary metric with a
pre-specified minimum detectable effect, and a sample size calculation completed
before a single impression is served or a single user is enrolled. The "because Z"
clause is not optional — it forces a causal mechanism to be stated and later
falsified or confirmed. Growth work that skips the mechanism claim does not
accumulate learning; it accumulates noise dressed as institutional knowledge.

---

## Fail-Fast Rule

Growth experiments MUST be stopped early only when a pre-registered stopping rule
fires, not when the current result looks good enough to call. Peeking at partial
results and stopping on a favorable signal is p-hacking regardless of the intent.
Conversely, an experiment that has crossed its pre-specified sample size and shows
no signal MUST be called as null and the resource reallocated — extending the run
to wait for a positive result that has not appeared is a different form of the same
bias. The stopping discipline protects both the team's statistical credibility and
the budget from being consumed by inconclusive runs.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Diagnosing which AAARRR stage is the primary constraint before committing spend
  to acquisition or activation improvements.
- Designing a growth experiment: hypothesis formation, metric selection, MDE
  specification, sample size calculation, and guardrail metric registration.
- Prioritising a backlog of growth tactics or channel candidates using a scored
  framework (ICE, RICE, or equivalent).
- Architecting or auditing a growth loop to identify whether the reinforcement
  mechanism is viral-coefficient dependent, content-compounding, network-effect
  dependent, or product-led.
- Selecting or validating a North Star Metric for a product or growth programme.
- Running cohort analysis to diagnose D1/D7/D30 retention breaks.
- Evaluating whether a channel is in cold-start, scale-up, or saturation phase.

Skip when: the work is paid-media campaign execution or bid management (use
ppc-strategist instead); the task is content calendar production or brand voice
(use content-creator instead); or the engagement is a market-sizing exercise
with no experimental component.

---

## Funnel Diagnostics

The AAARRR model is a diagnostic sequence, not a prioritisation order. The correct
practice is to measure conversion at each stage first, identify where the largest
absolute loss of value occurs, and allocate experiment budget to that stage.
Spending on top-of-funnel acquisition while a broken activation stage discards
80% of arriving users is budget waste, not growth work.

### Stage Definitions and Primary Signals

| Stage | Definition | Primary Loss Signal |
|---|---|---|
| Awareness | Potential users encounter the product or its content in a context where they form an initial impression. | Share of relevant search queries not captured; branded search volume flat against category growth. |
| Acquisition | A potential user takes a first attributable action — signup, trial start, waitlist entry, install. | Signup-to-install conversion rate; cost per acquisition trending against LTV ceiling. |
| Activation | The user reaches a moment where the product delivers its core value for the first time. | Time-to-first-value metric; percentage of new users who complete the activation milestone within a defined window (commonly 24 hours or 7 days). |
| Retention | The user returns to extract value in a subsequent session or period after the initial activation event. | D1/D7/D30 cohort retention curves; rolling 30-day active rate for the installed or signed-up base. |
| Referral | Existing users bring new users through deliberate or organic sharing behaviour. | Viral coefficient K; referral-attributed acquisition as percentage of total new users. |
| Revenue | The product captures economic value from the user relationship — subscription, transaction, advertising, or expansion. | Conversion rate from active to paying; ARPU trajectory; expansion revenue as percentage of net new ARR. |

### Choke-Point Identification Protocol

Before designing any experiment:

1. Pull stage-to-stage conversion rates for the most recent 30-day cohort.
2. Compute the absolute user count lost at each transition.
3. Rank stages by absolute loss — not percentage drop, because a 50% drop on
   100 users is less impactful than a 15% drop on 100,000 users.
4. Apply a leverage multiplier: recovering 10 percentage points at Activation
   propagates through Retention and Revenue; recovering 10 points at Referral
   benefits only the incoming cohort. Upstream fixes compound; downstream fixes
   are additive.
5. Confirm the hypothesis that the choke-point stage is addressable — if
   Retention is broken because the product has no repeat-use value, no
   growth experiment fixes that; a product decision is required first.

Spend is allocated only after this protocol is complete. Intuition-first channel
allocation before a funnel diagnostic is an anti-pattern.

---

## Experiment Design

Every experiment registered on the team's experiment backlog MUST contain all
six required elements before it is eligible for execution.

### Six Required Elements

**1. Hypothesis statement**: "If [treatment] then [primary metric] will [direction]
by at least [MDE] because [causal mechanism]."

No element may be missing. The MDE must be stated as an absolute or relative
change, not as "an improvement." The causal mechanism must be falsifiable — it
must be possible for the experiment result to disprove it.

**2. Primary metric**: one metric that, if it moves in the stated direction by at
least the MDE, constitutes a win for this experiment. Multiple primary metrics
cause p-hacking incentive; there is exactly one.

**3. Guardrail metrics**: two to four metrics that MUST NOT be materially harmed
by the treatment. Common guardrails: retention rate for an activation experiment;
support ticket rate for an onboarding experiment; revenue per user for a
conversion-rate experiment. A result where the primary metric wins but a guardrail
metric is materially harmed is not a clean win — it is a tradeoff requiring an
explicit Owner decision before rollout.

**4. Minimum detectable effect (MDE)**: the smallest change that would justify
acting on this experiment result and that the business outcome would require. MDE
is determined by business impact threshold, not by what looks achievable. Setting
MDE after peeking at data is not permissible.

**5. Sample size and duration**: calculated from baseline conversion rate, MDE,
desired power (≥0.80 standard; ≥0.90 for irreversible decisions), and alpha
(0.05 standard; Bonferroni-corrected for multiple comparisons). Duration must
account for at least one full business-cycle period (typically 7 days minimum for
products with weekly seasonality).

**6. Randomisation unit**: user, session, device, or account — specified before
launch. Switching the randomisation unit after launch invalidates the experiment.

### Pre-Launch Checklist

- Sample size calculation recorded and signed off.
- Baseline metric value from the most recent comparable period on record.
- Guardrail metrics instrumented and confirmed firing in the analysis environment.
- Stopping rule registered: minimum sample reached AND minimum duration elapsed.
  Early stopping only permitted if a pre-registered harm threshold on a guardrail
  metric is crossed.
- No other experiment running on the same population segment that could interact
  with this treatment.

---

## Statistical Rigor

### Alpha, Power, and Multiple Comparisons

Standard threshold: α = 0.05, power = 0.80. Power below 0.80 produces experiments
that fail to detect real effects at an unacceptable rate; underpowered experiments
that return null results are not informative — they are inconclusive.

For experiments testing more than one variant simultaneously, Bonferroni correction
is the minimum adjustment: divide alpha by the number of comparisons. For k variants
versus control, α_adjusted = 0.05 / k. More conservative corrections (Holm-Bonferroni,
Benjamini-Hochberg for discovery contexts) are preferred when the number of variants
exceeds four.

### CUPED

CUPED (Controlled-experiment Using Pre-Experiment Data) reduces variance in the
outcome metric by regressing out pre-experiment variance in a correlated covariate.
The effect is equivalent to increasing sample size without adding users. CUPED
is applicable whenever a pre-experiment observation of the primary metric (or a
correlated metric) is available for the same users. When variance reduction via
CUPED is available, it MUST be applied before concluding that a larger sample is
required — the sample size increase from CUPED is free; a longer experiment run
is not.

### Novelty and Primacy Effects

Experiments run on existing users are subject to novelty effects (initial
over-engagement with the treatment) and primacy effects (initial under-engagement
due to unfamiliarity). Both resolve over time. The minimum duration rule (one
full business cycle) addresses this partially. For products with strong weekly or
monthly seasonality, the minimum duration is two full cycles.

### Reporting Requirements

Every experiment result report MUST include:

- Sample size achieved versus planned.
- Observed effect with 95% confidence interval (not just a point estimate and
  p-value).
- Whether guardrail metrics were materially affected and in what direction.
- Statistical significance status at the pre-registered alpha.
- Recommendation: ship / iterate / kill — with explicit reasoning.

Reporting only p < 0.05 without confidence intervals, without guardrail status,
or without a recommendation is incomplete and MUST be rejected at review.

---

## Channel Discovery

### ICE and RICE Scoring

Prioritisation frameworks exist to make the backlog ordering explicit and auditable,
not to automate judgment. Two frameworks are supported:

**ICE** (Impact × Confidence × Ease): suitable for early-stage or resource-
constrained teams where speed of iteration is the primary constraint. Score
each dimension 1–10; multiply. High-ICE items enter the sprint queue; low-ICE
items are archived with the scores recorded for retrospective calibration.

**RICE** (Reach × Impact × Confidence / Effort): suitable for teams with
sufficient historical data to estimate reach and effort quantitatively. Reach
is the number of users affected in a defined period; Effort is the person-weeks
to execute. RICE is more precise and harder to game than ICE, but requires
reliable historical estimation data.

Regardless of framework, every score MUST be recorded with the date and the
scorer's assumptions made explicit. Scores without assumptions are not auditable.

### Cold-Start versus Scale-Up versus Saturation

Every channel occupies one of three phases:

| Phase | Signal | Correct Action |
|---|---|---|
| Cold-start | No reliable conversion data; cost-per-result estimate is a range wider than 2× | Run a structured test to establish baseline metrics. Do not optimise; do not scale. Budget: minimum viable to generate statistical signal. |
| Scale-up | Conversion rate stable; CAC within acceptable LTV ratio; efficiency holding with incremental budget increases | Increase investment while monitoring CAC:LTV ratio weekly. Stop scaling when CAC crosses the LTV/3 ceiling for that channel. |
| Saturation | CAC increasing on incremental budget additions; conversion rate declining; audience overlap rising | Cap spend. Begin testing adjacent audiences or adjacent channels. Do not attempt to solve saturation with creative rotation alone — audience exhaustion is structural, not creative. |

### Channel Half-Life

Channels degrade. A tactic that generates strong returns in quarter one is
frequently saturated or imitated by quarter three. Channel half-life estimates
(the period over which a new channel retains its initial efficiency advantage
before regression toward market average) by type:

- Viral or referral mechanics based on a novel incentive: 6–18 months before
  market saturation or regulatory friction.
- Organic content (SEO, long-form): 18–36 months for evergreen content; shorter
  for trend-dependent content.
- Paid performance channels: efficiency advantage from targeting innovation
  degrades in 3–9 months as competitors adopt the same signals.
- Product-led growth loops: longest half-life when the loop is embedded in core
  product value; shorter when dependent on a single feature.

Channel discovery work is ongoing, not a one-time exercise. A team that stops
discovering channels when current channels are performing is already 12 months
behind on the next working channel.

---

## Growth Loop Architecture

A growth loop is a self-reinforcing system where the output of one user action
becomes the input that acquires or activates the next user. Loops are
structurally different from funnels: funnels describe a single user's journey;
loops describe how user actions create the conditions for additional user
acquisition or retention without proportional spend increase.

### Loop Structure

Every loop has four required components:

```
Input → Action → Output → Reinforcement
```

- **Input**: the trigger that begins the cycle — a new user, a new piece of
  content, a new transaction, or a new referral.
- **Action**: what the user does with the product that generates an output.
- **Output**: a by-product of the action that has value outside the user's
  own session — shared content, a referral, a data signal, a network connection.
- **Reinforcement**: the mechanism by which the output reduces the cost or
  increases the probability of the next Input occurring.

Loops without a quantified reinforcement mechanism are hypotheses, not
architectures. The reinforcement must be measurable.

### Viral Coefficient Discipline

Viral coefficient K = (invitations sent per active user) × (conversion rate
of invitation to new active user).

K > 1.0: each cohort of users generates a larger following cohort. Growth
accelerates without proportional acquisition spend.
K = 1.0: growth is flat (each user replaces themselves exactly).
K < 1.0: viral mechanics contribute to growth but do not sustain it; other
channels are required to maintain net-positive growth.

K is a product of invite rate and invite conversion rate. These must be
measured and optimised separately — a high invite rate with low conversion
suggests the incentive structure or the landing experience is broken. A low
invite rate with high conversion suggests the sharing trigger is insufficient
or poorly placed.

### Loop Fatigue Detection

Loops degrade when:

- The addressable audience for the output has been saturated (all reachable
  users have already been exposed).
- The value proposition of the output degrades with repetition (first share
  is novel; tenth share is spam).
- External factors reduce conversion rate (platform policy changes, user
  behaviour shifts, competitive alternatives).

Loop fatigue is detected by tracking the reinforcement metric on a 30-day
rolling basis. A declining reinforcement metric while the action metric is
stable indicates fatigue in the output-to-reinforcement conversion step. Act
on the reinforcement conversion, not on the action step.

---

## Retention as Foundation

Retention is the mathematical foundation of all other growth work. The
relationship is direct: a product with low retention requires continuous
acquisition spend just to maintain user base size. A product with high
retention operates from a growing installed base, which amplifies the return
on every acquisition dollar and every referral loop.

### Cohort Analysis Protocol

Cohort analysis MUST be structured as follows:

1. Define the cohort entry event precisely: first install, first activation
   milestone, first payment, first meaningful action — whichever best
   represents the start of the user relationship. Do not use signup date if
   the product has a multi-step onboarding that delays value delivery.
2. Track the cohort at D1, D7, D14, D30, D60, and D90 retention rates.
3. Compare cohort retention curves across acquisition channels, onboarding
   variants, and product versions. Flat or improving curves across periods
   indicate a structural improvement; single-period anomalies are noise.
4. Identify the "retention cliff" — the interval where the largest single
   drop in the retention curve occurs — and focus activation and re-engagement
   work at that interval.

### D1/D7/D30 Reference Benchmarks

Benchmarks vary by product category and engagement model. These ranges serve
as rough orientation for diagnosis, not as targets:

| Retention Interval | Consumer (high frequency) | SaaS (core workflow) |
|---|---|---|
| D1 | 25–40% | 40–60% |
| D7 | 10–20% | 25–45% |
| D30 | 5–10% | 15–35% |

A product at the low end of all three intervals simultaneously has a
structural retention problem that no acquisition experiment can compensate.
The correct action before any growth spend is to identify and address the
activation or product value gap causing the retention break.

### Retention Before Acquisition

The sequencing rule: when the D30 retention rate is below the floor for the
product category and the root cause is in activation or core value delivery,
growth budget allocation MUST prioritise retention improvement over acquisition
scaling. Scaling acquisition into a broken retention curve multiplies the
cost of the retention problem without improving it. This sequencing discipline
is enforced at the experiment backlog review, not at the individual experiment
level.

---

## North Star Metric

The North Star Metric (NSM) is the single metric that best represents the value
the product delivers to users and that is most predictive of long-term revenue
sustainability. It is not the metric that is easiest to improve; it is the metric
whose improvement most reliably predicts that the product is creating genuine
value for users.

### NSM Selection Criteria

A valid NSM must satisfy all four:

1. **Product-value correlation**: the metric increases when users are getting
   more value from the product, not merely when the product is being used more
   superficially. Daily active users is frequently not an NSM — it is a vanity
   proxy unless the product's value is inherently session-frequency dependent.
2. **Revenue predictiveness**: improvements in the NSM must be historically
   correlated with improvements in long-term revenue, not just short-term
   conversion spikes.
3. **Actionability**: the growth team must be able to design experiments that
   move the NSM. An NSM that is determined entirely by external market conditions
   is an outcome, not a lever.
4. **Shared ownership**: the NSM must be meaningful to both the growth team and
   the product team. If the NSM is only interpretable by the growth team, it is
   a growth metric, not a north star.

### Vanity Metric Trap Detection

A metric is a vanity metric if it can increase while the product delivers less
value to users. Common vanity metrics misrepresented as NSMs:

- Total registered users (includes dormant accounts, bots, churned users).
- Page views or sessions (increases with re-engagement campaigns targeting users
  who are not getting value).
- App installs (includes users who install and never activate).
- Total revenue in a single period (can increase through price increases that
  harm retention without adding value).

When an NSM candidate is proposed, the test is: "Can this metric increase while
the product is delivering less value to active users?" If yes, it is not a valid
NSM. Replace it with a metric that requires genuine value delivery to increase.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Practice |
|---|---|---|
| **HIPPO decisions on channel allocation** | Highest Paid Person's Opinion on which channel to invest in, when not backed by scored experiment data, allocates budget based on authority rather than evidence. Past channel success in a different company, market, or period is not portable. | Score every channel candidate against a consistent framework (ICE or RICE) with explicit assumptions recorded. Budget allocation follows the score, not the hierarchy. Deviations from the scored order require a written rationale. |
| **P-hacking via premature stopping** | Peeking at experiment results before the pre-registered sample size is reached and stopping when the result looks favourable inflates the false-positive rate above the stated alpha. Reported significance is not actual significance. | Register stopping rules before launch. Stop only when the pre-registered sample size and minimum duration are both satisfied. Early stopping is permitted only when a pre-registered harm threshold on a guardrail metric fires. |
| **Vanity-metric retrofit** | Selecting the metric to report after seeing the experiment results, choosing the metric that shows the best outcome, is a post-hoc rationalisation, not an experiment result. It produces a confident-looking report with no statistical validity. | Register the primary metric and guardrail metrics before the experiment launches. The pre-registered metrics are reported regardless of whether they show a favourable outcome. |
| **Copy-cat tactic deployment** | Adopting a growth tactic because a competitor or industry publication reports success with it, without testing whether it applies to the current product's audience, stage, and market context. Most tactical results are not portable across market segments. | Treat externally reported tactics as hypothesis inputs, not execution plans. Run a minimum viable test with a pre-specified MDE before scaling. The hypothesis must include a mechanism claim specific to the product's context. |
| **Premature scaling before retention is stable** | Scaling acquisition spend before the D30 retention rate is above the product-category floor compounds the cost of a broken retention problem. Each scaled cohort churns at the same rate as prior cohorts, consuming budget without improving the installed base. | Apply the retention-before-acquisition sequencing rule. Retention floor must be confirmed stable — not improving, but stable — before acquisition spend is increased materially. |
| **Single-period revenue optimisation at the expense of retention** | Optimising for short-term conversion rate or average order value in ways that harm long-term retention (aggressive discounting, feature gating, dark patterns) can improve a single-period revenue metric while destroying LTV. Revenue optimisation experiments MUST include retention-rate guardrails. | Every revenue experiment must register D30 retention rate as a guardrail metric. A revenue win that causes a statistically significant retention decline is not a net win — it is a tradeoff requiring explicit Owner decision before rollout. |
| **Treating the viral coefficient as a target rather than an outcome** | Setting K > 1.0 as a goal and designing referral mechanics to hit it without understanding the value exchange that would motivate genuine sharing produces incentive-gamed referrals — users who share for the incentive, not for the product. Incentive-gamed K-factors collapse when the incentive changes or when the invited users discover the product does not match the sharing pitch. | Design referral mechanics around the value the referring user genuinely wants to share, not around hitting a coefficient target. Measure conversion quality (activation rate of referred users versus other channels) alongside volume. A referral programme with K = 0.5 and high-quality referred-user activation is more valuable than K = 1.2 with low activation. |

---

## Cross-References

- `.claude/skills/domains/marketing-global/skills/content-creator` — Content
  production, editorial calendar, and brand voice discipline. Content-creator
  governs organic content channel execution; growth-hacker governs the experiment
  layer that determines which content formats and distribution strategies to
  invest in based on measurable funnel impact.

- `.claude/skills/domains/paid-media/skills/ppc-strategist` — Paid acquisition
  channel execution, bid management, and media buying. The growth-hacker skill
  covers the ICE/RICE prioritisation and hypothesis design layer upstream of
  paid-channel execution; ppc-strategist governs the execution mechanics.

- `.claude/skills/core/code-review-checklist/SKILL.md` — Two-pass review
  protocol applicable to experiment design review: first pass for completeness
  of all six required experiment elements and pre-launch checklist; second pass
  for adversarial pressure-testing of the hypothesis mechanism claim,
  guardrail metric selection, and sample size calculation assumptions.

---

## ADR Anchors

- **ADR-058** (`ADR-058-brainstorm-gate-and-two-pass-review.md`) — Two-pass
  review mandate for high-stakes authored artifacts. Growth experiment design
  documents, NSM selection rationales, and channel investment proposals are in
  scope for this discipline. First pass: completeness of all required experiment
  elements and scoring-framework assumptions. Second pass: adversarial review of
  the hypothesis mechanism claim, guardrail metric coverage, and the
  retention-before-acquisition sequencing decision when applicable.
