---
name: paid-social-strategist
description: >
  Paid social discipline covering campaign-objective mapping, platform
  selection scoring, Advantage-Plus versus manual structure, post-iOS-14.5
  measurement (SKAdNetwork conversion-value mapping, aggregated event
  measurement), creative-volume strategy, bid and budget mechanics, and
  attribution methodology. Operates across Meta, TikTok, LinkedIn, Twitter/X,
  Reddit, Pinterest, and Snapchat. Enforces funnel-stage alignment before any
  platform or budget decision, treats creative as the primary algorithmic
  lever, and rejects single-source attribution by default. Use when designing
  or restructuring a paid social campaign; selecting or rebalancing a platform
  mix; architecting Advantage-Plus versus manual structures; building a
  post-iOS-14.5 measurement stack; designing a creative-volume strategy;
  constructing a bid or budget framework; or triangulating attribution across
  platform-reported, lift-study, and modelled sources.
owner: Valentina Reyes (Paid Social Strategist, domain persona)
tier: domain:paid-media
scope_tags: [paid-social, meta-ads, tiktok-ads, linkedin-ads, advantage-plus, skadnetwork, attribution]
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-paid-social-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/paid-social/**"
  - "**/meta-ads/**"
  - "**/skadnetwork/**"
  - "**/campaigns/**"
---

# Paid Social Strategist

## Cardinal Rule

Paid social spend earns return by matching campaign objective to funnel
stage, platform to audience density, and creative to platform-native
consumption behaviour — all three simultaneously. A technically correct
Advantage-Plus structure pointed at the wrong funnel stage wastes the
machine-learning budget on audience segments that cannot convert at the
bid price. A correct objective on the wrong platform wastes impressions
on users whose consumption context does not support the required action.
Correct objective, correct platform, and wrong creative produces high
CPMs against an algorithm that learned the audience but could not drive
the desired action. All three axes must be aligned before any campaign
goes live. Platform selection, objective mapping, and creative strategy
are not sequential decisions — they are a single joint decision made at
brief stage, not at optimisation stage.

---

## Fail-Fast Rule

A campaign MUST NOT enter active spend without three gates confirmed:
a defined funnel stage with a corresponding campaign objective, a
platform selection scored against the audience-platform fit matrix
(not selected by habit or budget precedent), and a minimum creative
inventory of four variants per ad set. The following conditions MUST
hold before any campaign activates:

1. The funnel stage is named (Awareness, Consideration, Conversion,
   Retention, or Winback) and the campaign objective is confirmed as
   the correct platform-native objective for that stage — not the
   default objective selected by the platform wizard.
2. The platform was selected by scoring audience density, content fit,
   commercial intent, and cost efficiency against the target segment —
   not by historical precedent or channel convenience.
3. The ad set launches with a minimum of four creative variants. Single-
   creative ad sets are blocked; the algorithm requires creative signal
   diversity to exit the learning phase efficiently.

If any gate is unresolved, the campaign does not activate until it is
closed.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing or auditing campaign architecture for Meta, TikTok, LinkedIn,
  Twitter/X, Reddit, Pinterest, or Snapchat.
- Selecting a platform mix for a new product launch, seasonal push, or
  budget reallocation cycle.
- Deciding between Advantage-Plus and manual campaign structure for a
  specific campaign type or data-density state.
- Building a post-iOS-14.5 measurement stack: Conversions API, aggregated
  event measurement configuration, SKAdNetwork conversion-value schema.
- Designing a creative-volume strategy and refresh cadence.
- Constructing a bid strategy or budget framework (CBO versus ABO, bid
  caps versus cost caps, daily versus lifetime budgets).
- Triangulating attribution across platform-reported metrics, lift studies,
  marketing mix modelling, and GA4.

Skip when: the task is search advertising — route to
`domains/paid-media/skills/ppc-strategist`; the task is programmatic
display or video — route to `domains/paid-media/skills/programmatic-buyer`;
the task is tracking implementation (pixel, server-side events, GA4
schema) — route to `domains/paid-media/skills/tracking-specialist`; or
the task is creative production and concepting — route to
`domains/paid-media/skills/creative-strategist`.

---

## Platform Selection

Platform selection is a scoring decision, not a channel preference. The
question is never "should we be on platform X?" — the question is "which
platforms score highest against the target segment across the four
evaluation dimensions?" Score before committing budget. Committing to a
platform before scoring produces spend inertia: budgets persist on
platforms that no longer match the audience or objective because historical
presence substitutes for current evidence.

### Evaluation Dimensions

Score each candidate platform on a 1-5 scale across four dimensions. Do
not weight dimensions equally — weight them by the campaign objective:
commercial intent is the heaviest weight for conversion campaigns; audience
density is the heaviest weight for awareness campaigns.

| Dimension | Definition | Conversion weight | Awareness weight |
|---|---|---|---|
| Audience density | Verified presence and active engagement of target segment on platform | High | High |
| Content fit | Platform's native content format matches the creative type the brand can produce | Medium | High |
| Commercial intent | Platform's usage context supports the required action (click, lead form, purchase) | Highest | Low |
| Cost efficiency | CPM and CPA benchmarks relative to vertical norms for this platform | Medium | Medium |

### Platform Characteristics (reference — verify against current benchmarks)

| Platform | Audience density strength | Commercial intent | Content fit | Cost profile |
|---|---|---|---|---|
| Meta (Facebook/Instagram) | Broadest reach; all demographics | High for ecommerce and lead gen | Image, video, carousel, DPA | Moderate CPM; rising YoY |
| TikTok | 18-34 dominant; rapid 35+ growth | Moderate; purchase intent improving | Short-form native video only | Lower CPM; rising |
| LinkedIn | B2B professional; job-title targeting | High for enterprise B2B and recruitment | Sponsored content, document ads | Highest CPM in category |
| Twitter/X | News-aware, tech-adjacent audiences | Low to moderate | Short text + image | Variable; inventory compressed |
| Reddit | Interest-graph communities; high intent niche | Moderate; community trust required | Promoted posts in community context | Lower CPM; niche targeting strong |
| Pinterest | High purchase intent in home, fashion, food | High for visual product categories | Static and video pins | Moderate; strong ROAS in verticals |
| Snapchat | 13-34 dominant; mobile-first | Moderate; strong for app installs | Vertical video; AR lenses | Lower CPM; young-skew limitation |

A platform that scores below 3 on audience density is not a candidate
regardless of its other scores. An audience that is not present cannot be
reached at any cost efficiency.

---

## Campaign Objective Mapping

Campaign objective must match funnel stage. Platform algorithms optimise
delivery toward the selected objective. Selecting Traffic when the goal is
Conversions trains the algorithm to find people who click links — a different
population than people who purchase. Misaligned objectives are not recoverable
through bid adjustments; the learning phase encodes the wrong population and
the campaign must be rebuilt, not optimised.

### Funnel-Stage to Objective Mapping

| Funnel stage | Goal | Correct objective | Common misalignment |
|---|---|---|---|
| Awareness | Reach and frequency against target segment | Reach, Brand Awareness, Video Views | Traffic (optimises for clickers, not viewers) |
| Consideration | Engagement, site visits, content consumption | Traffic, Engagement, Video Views | Conversions (insufficient conversion signal; learning fails) |
| Conversion — Lead | Qualified lead capture | Lead Generation, Leads (Meta) | Traffic (sends to landing page; higher drop-off than native form) |
| Conversion — Purchase | Direct revenue | Sales, Conversions (Purchase event) | Traffic or Add-to-Cart (underpowers purchase signal) |
| Retention | Re-engagement and repeat purchase | Sales with existing-customer audience, Engagement | Reach (wastes impressions on cold audiences) |
| Winback | Lapsed-customer reactivation | Sales or Lead Gen with suppressed recent purchasers | Broad audience (dilutes lapsed-customer signal) |

Objective selection is final at campaign creation on most platforms. Changing
objective mid-flight resets the learning phase. Build the correct objective
into the campaign brief before any structure is created.

---

## Advantage-Plus vs Manual

Advantage-Plus (and its equivalents on other platforms — Performance Max
on Google, Reach and Frequency on TikTok Smart+) shifts targeting, placement,
and creative selection decisions from the advertiser to the platform
algorithm. The decision between ML-driven and manual structure is a function
of data density, not platform preference or account maturity.

### When ML-Driven Structure Outperforms

Advantage-Plus outperforms manual when the following conditions are met:

- **Conversion event volume:** the campaign or account generates a minimum
  of 50 conversion events per week at the target conversion event level.
  Below this threshold the algorithm cannot model efficiently; manual
  targeting preserves a narrower, higher-signal delivery audience.
- **Creative diversity:** a minimum of six to eight creative variants are
  available for algorithmic selection. Advantage-Plus with fewer than four
  variants degrades to random rotation, which manual structure already
  provides without the ML overhead.
- **Audience breadth acceptable:** Advantage-Plus will expand targeting
  beyond defined audiences when it detects conversion signal. This expansion
  is a feature for scale-stage campaigns and a liability for campaigns with
  strict audience constraints (geography, compliance, ABM target lists).
- **No segment-isolation requirement:** A/B tests, incrementality holds,
  and sequential-messaging programs require audience isolation that
  Advantage-Plus cannot guarantee.

### Manual Override Scenarios

Manual campaign structure is required when:

1. The conversion event fires fewer than 50 times per week — algorithm
   cannot exit the learning phase reliably.
2. The campaign requires strict audience isolation (hold groups, exclusion
   cells, ABM lists).
3. The creative inventory is fewer than four variants — ML selection has
   no meaningful choice surface.
4. Regulatory or compliance constraints prohibit audience expansion (financial
   products, health categories, age-gated products).

### Learning-Phase Respect

The learning phase (typically 50 conversion events on Meta) is not a
period to optimise — it is a period to observe. Editing budgets, bids,
audiences, or creatives during the learning phase resets it. Allow the
learning phase to complete before evaluating performance; early exit or
edit is the most common cause of false-negative performance attribution
in ML-driven structures.

---

## Audience Signals Post-iOS-14.5

iOS-14.5 App Tracking Transparency (ATT) eliminated deterministic
cross-site signal for opted-out iOS users. The practical effect: platform-
reported conversions are a model, not a measurement, for a substantial
fraction of iOS traffic. Post-iOS-14.5 audience strategy requires a
different signal architecture.

### SKAdNetwork Conversion-Value Mapping

SKAdNetwork (SKAN) is Apple's privacy-preserving attribution framework.
It reports conversion events through a 6-bit conversion value (0-63) with
a 24-72 hour postback timer. The conversion value schema must be designed
before campaign activation — SKAN does not retroactively map events.

| Conversion value range | Recommended mapping | Signal quality |
|---|---|---|
| 0 | No conversion event fired within timer window | No signal |
| 1-15 | Low-value engagement (add-to-cart, registration) | Weak |
| 16-31 | Mid-value conversion (trial start, first purchase below AOV) | Medium |
| 32-63 | High-value conversion (repeat purchase, high-AOV, subscription activate) | Strong |

Map conversion values to revenue buckets, not event types, to enable
bid optimisation against value. Event-only mapping (purchase = value 1,
regardless of purchase size) discards the revenue-signal needed for
value-based bidding.

### Aggregated Event Measurement

Meta's Aggregated Event Measurement (AEM) protocol limits each domain to
eight conversion events, ranked by priority. Events ranked below the active
priority are not reported when ATT consent is absent. Configure the eight
events in priority order matching the campaign objective hierarchy: Purchase
first, then Add-to-Cart, then Initiate Checkout, then Lead, then lower-
funnel events. Misconfigured event priority is the most common cause of
under-reported conversions on Meta for iOS audiences.

### Modelled vs Reported Conversions

Following iOS-14.5, Meta and other platforms supplement deterministic
attribution with statistical modelling. Modelled conversions appear in
reporting alongside observed conversions. Do not subtract modelled
conversions from reported totals as a trust adjustment — modelled conversions
are directionally accurate at the campaign level and should be treated as
valid signals for budget allocation decisions, not as noise to be discounted.

### Consent Compliance

Conversions API (CAPI) implementation must route only consented user events
to platform servers in jurisdictions with consent requirements (GDPR, LGPD).
Server-side events sent without consent eligibility checking create compliance
exposure even when the platform receives and processes them. Implement
consent-state filtering in the CAPI middleware layer before the API call,
not as a post-processing step.

---

## Creative-Volume Strategy

Creative is the primary algorithmic lever in paid social. Platform algorithms
allocate delivery budget to the creative variants that generate the best
signal against the objective. A campaign with a single creative forces the
algorithm into a no-choice state; the algorithm delivers that creative
regardless of performance signal because there is no alternative. Creative
volume is not a production preference — it is a structural requirement for
algorithmic efficiency.

### Minimum Creative Inventory

| Campaign phase | Minimum variants per ad set | Target variants |
|---|---|---|
| Launch | 4 | 6-8 |
| Scaling | 6 | 8-12 |
| Mature (90+ days) | 8 (continuous refresh) | 10-15 active |

Launch below four variants. Scale campaigns without refresh cadence. Both
conditions degrade algorithm efficiency. The launch threshold is a hard
floor, not a suggestion.

### Creative Architecture

Within the minimum inventory, vary across three dimensions to give the
algorithm independent signal axes:

1. **Hook variation:** the first 3 seconds (Meta, TikTok) or first frame
   (LinkedIn) must be varied across creatives. Identical hooks with varied
   body copy produce near-zero differential signal — the algorithm makes
   delivery decisions within the first interaction window.
2. **Format variation:** include at least one static image, one video under
   15 seconds, and one longer-form video (30-60 seconds) per ad set where
   the platform supports all three. Format diversity ensures placement-level
   efficiency across feed, story, and reels inventory.
3. **Angle variation:** each creative should represent a distinct value-
   proposition angle (price, outcome, social proof, problem-agitation, urgency)
   — not the same angle executed in different visual treatments.

### Creative Fatigue Detection

Creative fatigue occurs when frequency accumulates on a delivered audience
faster than the creative can sustain attention. Fatigue signals to monitor:

| Signal | Threshold | Action |
|---|---|---|
| Frequency (7-day window) | Prospecting >2.5; Retargeting >5.0 | Introduce new creative variants |
| CTR trend | >15% decline week-over-week for 2 consecutive weeks | Flag creative for replacement |
| Hook rate (3-second view rate) | Drop below 25% on Meta/TikTok | Test new hook variants |
| CPM trend | >20% increase without audience expansion | Audience saturation signal; expand or refresh |

Do not wait for ROAS or CPA to degrade before addressing creative fatigue.
CTR and hook rate are leading indicators; ROAS degradation is a lagging
indicator that arrives after the creative-fatigue damage is already priced
into the campaign's learned audience pool.

### Refresh Cadence

For prospecting campaigns at scale, introduce at minimum two to three new
creative variants per ad set per month. For retargeting campaigns with
smaller audiences, the frequency ceiling is reached faster — refresh at
minimum every three weeks or when any fatigue signal threshold is crossed,
whichever comes first.

---

## Bid and Budget Strategy

Budget structure (CBO versus ABO) and bid strategy (bid cap versus cost
cap versus lowest cost) are mechanical decisions with clear selection criteria.
They are not interchangeable.

### CBO vs ABO

| Structure | When to use | Risk |
|---|---|---|
| Campaign Budget Optimisation (CBO) | 3+ ad sets with similar audience sizes; algorithm should allocate dynamically between them | Algorithm concentrates spend on the best-signal ad set, starving test cells |
| Ad Set Budget (ABO) | Testing creative or audience variants where equal exposure is required; ABM lists; exclusion cells | Requires manual rebalancing as performance diverges |

Testing requires ABO. Scale requires CBO. Mixing test objectives with
CBO budget structure is the most common cause of false-positive test
conclusions in paid social — the algorithm unbalances delivery before
statistical significance is reached.

### Bid Strategy Selection

| Bid strategy | When to use | Constraint |
|---|---|---|
| Lowest cost (auto bid) | Learning phase; new campaigns without CPA history | No CPA control; spend as directed by budget |
| Cost cap | CPA ceiling is defined; willing to sacrifice delivery volume to hold CPA | Algorithm may under-deliver if cap is set below the market-clearing price |
| Bid cap | Need strict CPM/CPC ceiling; inventory-quality control | Frequently under-delivers; use only when delivery sacrifice is acceptable |
| Value optimisation | Conversion-value schema is mapped; goal is revenue not volume | Requires minimum purchase event volume; SKAN schema must be configured |

Do not set a cost cap below the observed CPA from the lowest-cost phase
by more than 20% — the algorithm will be unable to clear the market at
that price and under-delivery will result. Anchor cost caps to observed
performance data, not to target unit economics in isolation.

### Daily vs Lifetime Budgets

Daily budgets offer day-to-day delivery control and are appropriate for
always-on campaigns. Lifetime budgets allow the platform to pace delivery
around predicted high-performance windows (ad scheduling, day-parting,
auction dynamics) and are appropriate for time-bounded flights. Mixing
daily and lifetime budgets across ad sets within the same CBO campaign
creates undefined pacing interactions — use a single budget type within
a CBO structure.

---

## Attribution Methodology

Platform-reported attribution is structurally overstated. Every major
paid social platform attributes conversions using the most favourable
attribution window available unless reconfigured. Meta's default 7-day
click + 1-day view window claims credit for conversions that occur up to
seven days after a click and one day after a view, regardless of other
touchpoints in between. No single platform has visibility into the full
path; each claims the conversion within its own attribution logic.

Attribution is a triangulation problem, not a single-source measurement
problem. Relying on any single platform's reported ROAS or CPA as the
primary performance signal leads to budget misallocation.

### Triangulation Stack

| Source | What it measures | Limitation |
|---|---|---|
| Platform-reported conversions | Algorithmic credit claims; directional signal for relative creative and audience performance | Overcounts; no cross-channel deduplication |
| Lift study (holdout test) | Incrementality — conversions caused by the platform versus those that would have occurred anyway | Requires statistically sufficient audience and time window; cannot run continuously |
| Marketing mix modelling (MMM) | Regression-based channel contribution estimate over historical spend | Lagging; requires 12+ months of data for reliable coefficients; not real-time |
| GA4 / last-click analytics | User-reported session path; session-level attribution | Under-counts cross-device and view-through; over-weights last interaction |

Use platform-reported data for day-to-day optimisation decisions (creative
rotation, audience adjustments, bid management) — it is the highest-
frequency signal available. Use lift studies quarterly to validate that
platform spend is driving incremental conversions, not just claiming credit
for organic demand. Use MMM annually to calibrate cross-channel budget
allocation. Use GA4 to detect path anomalies and landing-page drop-off
patterns, not as the attribution source of record.

### Attribution Window Configuration

Shorten platform attribution windows from defaults to reduce overcounting.
Meta 7-day click + 1-day view is the recommended standard for ecommerce.
LinkedIn default 30-day click window is appropriate for B2B lead gen given
longer sales cycles. TikTok 7-day click is appropriate for direct response.
Do not compare ROAS or CPA across platforms without normalising attribution
windows — a Meta 28-day window result cannot be compared to a TikTok 7-day
window result without adjustment.

---

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Trusting platform-reported ROAS as absolute performance signal | Every platform overcounts; cross-platform ROAS comparison without normalised windows is meaningless |
| Single creative variant per ad set | Forces random delivery; no algorithmic selection signal; fatigue is immediate at any meaningful frequency |
| Changing campaign structure during the learning phase | Resets the learning phase; performance data collected before the reset is wasted; the campaign re-enters cold-start behaviour |
| Setting cost caps below observed CPA before volume history exists | Algorithm cannot clear the auction at the cap price; under-delivery results; campaign never generates the CPA data needed to justify the cap |
| Deploying identical creative across platforms | Each platform has a distinct native consumption context; cross-posting produces off-native creative that underperforms against platform-optimised formats |
| Ignoring creative fatigue signals until ROAS declines | ROAS is a lagging indicator; by the time it degrades, the algorithm has already encoded a fatigued audience pool; recovery requires creative refresh plus audience reset |
| Using CBO for creative tests | CBO budget concentrations on the best-signal cell before statistical significance; test conclusions are confounded by unequal delivery |
| Treating Advantage-Plus as always superior | ML-driven structures require minimum data density; below the 50-conversion-per-week threshold, manual targeting delivers more consistent results |

---

## Cross-References

- `domains/paid-media/skills/ppc-strategist` — search advertising; keyword
  strategy and Quality Score mechanics; use when the campaign objective
  maps to active search intent rather than passive social feed.
- `domains/paid-media/skills/programmatic-buyer` — display and video
  programmatic; DSP strategy, audience data marketplace, brand-safety
  controls; use when the campaign requires open-web reach beyond walled
  gardens.
- `domains/paid-media/skills/creative-strategist` — creative concepting,
  ad format design, UGC and native-style production briefs; use when
  creative development is the primary deliverable rather than media strategy.
- `domains/paid-media/skills/tracking-specialist` — pixel implementation,
  Conversions API configuration, GA4 event schema, server-side tagging;
  use when the task is measurement infrastructure rather than campaign
  strategy.

---

## ADR Anchors

- **ADR-058** — Brainstorm gate pre-Plan + two-pass adversarial review:
  paid social campaign briefs require the same pre-work gate discipline
  as technical plans. An objective-platform-creative triple confirmed
  at brief stage is structurally equivalent to the ADR-058 brainstorm
  gate applied to advertising work: it moves the constraint discovery
  forward and prevents learning-phase resets caused by post-activation
  structural changes.
