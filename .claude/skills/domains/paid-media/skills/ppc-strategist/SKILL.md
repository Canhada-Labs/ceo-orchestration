---
name: ppc-strategist
description: >
  Pay-per-click strategy across Google Ads, Microsoft Ads, and Meta: campaign structure
  design at account/campaign/ad-group/keyword hierarchy, intent-based keyword research
  with negative-keyword discipline, bid strategy selection matched to data-maturity level,
  responsive search ad testing with statistical-significance thresholds, landing page
  message-match and conversion-element validation, budget pacing diagnostics via
  impression-share signals, and attribution model selection beyond last-click. Use when
  an account structure lacks tiered isolation between brand, non-brand, competitor, and
  informational intent; when Smart Bidding is active but conversion-volume prerequisites
  are unmet; when ad copy tests run without significance thresholds; when budget pacing
  is managed by gut feel rather than impression-share diagnostics; or when conversion
  attribution defaults have never been audited against actual customer paths.
owner: Marcus Holt (PPC Strategist, paid-media domain)
tier: domain:paid-media
scope_tags:
  - ppc
  - google-ads
  - search-ads
  - bid-strategy
  - ad-copy-testing
  - attribution
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-ppc-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/ppc/**"
  - "**/google-ads/**"
  - "**/keywords/**"
  - "**/search-ads/**"
---

# PPC Strategist

## Cardinal Rule

Account structure is strategy. The architecture of campaigns, ad groups, keyword
assignments, and bid-strategy containers determines which signals the algorithm
receives, how budgets flow, and what the advertiser can measure independently. A flat
account — one campaign, broad match, Smart Bidding, no negatives — is not a simplified
strategy; it is a strategy that delegates all decisions to the platform without the
data prerequisites to make those decisions well. Structural choices compound over time:
a structurally sound account accumulates clean conversion signal, controlled vocabulary,
and diagnostic clarity; a structurally unsound account accumulates noise that no
optimisation lever can remove.

## Fail-Fast Rule

Stop and rebuild the account structure when three conditions hold simultaneously:
(1) Smart Bidding is active on a campaign with fewer than 30 conversions in the last
30 days at campaign level, (2) there are no campaign-level or account-level negative
keyword lists, and (3) Search Query Reports contain more than 15% of spend on queries
that do not map to any intentional keyword theme. Operating bid automation without
conversion-volume prerequisites accelerates spend on statistically insufficient signals.
Adding bid optimisation to an account without negatives and without intent segmentation
does not fix the structural problem — it optimises a broken input faster.

## When to Apply

- A new account buildout requires structural design before any campaign is created.
- An existing account is being restructured due to efficiency decline, impression-share
  loss, or uncontrolled CPC growth.
- Bid strategy is being transitioned from manual CPC to automated bidding and the data
  prerequisites need verification.
- Conversion volume has grown sufficiently to reconsider which bid strategy tier is now
  appropriate.
- Ad copy tests are running without documented hypotheses, control/variant isolation, or
  significance thresholds.
- Budget pacing is uneven, campaigns are hitting daily limits inconsistently, or
  impression-share lost due to budget exceeds 10%.
- Attribution defaults have never been reviewed and the account is making budget
  allocation decisions from last-click data alone.
- A new platform (Microsoft Ads, Meta) is being added and structural conventions need
  to be applied consistently.

## Campaign Structure Discipline

Account structure is hierarchical: account → campaign → ad group → keyword/audience.
Each level serves a distinct governance purpose. Decisions made at the wrong level
produce either over-segmentation (hundreds of campaigns, each too small for bidding
signal) or under-segmentation (one campaign absorbing contradictory intent signals that
no single bid strategy can serve).

**Account-Level Governance**

- Account contains shared negative keyword lists, audience lists, conversion actions,
  and bidding signals that flow to all campaigns.
- Conversion action hierarchy is defined at account level: primary conversion actions
  (those Smart Bidding optimises toward) are separated from secondary conversion actions
  (those reported but not bid-optimised).
- Budget ceilings are enforced at campaign level; account-level shared budgets are
  used only when dynamic budget reallocation across thematically identical campaigns
  is intentional.

**Campaign-Level Segmentation**

Campaigns are segmented by intent tier, not by keyword theme:

| Campaign Tier | Intent Definition | Bid Strategy Starting Point |
|---|---|---|
| Brand | Queries containing the advertiser's own brand terms | Target Impression Share or Manual CPC |
| Non-Brand | Queries for the product/service category without brand terms | Target CPA or Target ROAS when conversion-volume prerequisites met |
| Competitor | Queries containing competitor brand terms | Manual CPC or conservative Target CPA; separate budget |
| Informational | Queries with research or comparison intent, no direct purchase signal | Separate campaign or excluded via negative list depending on LTV model |

Isolating tiers into separate campaigns enables independent budget control, separate
performance benchmarks, and clean bid-strategy configuration. A single campaign
combining brand and non-brand queries produces ROAS metrics that are inflated by
brand-query efficiency and are not meaningful for non-brand spend decisions.

**Ad-Group Structure: SKAG vs STAG vs Broad-Match-Machine-Learning**

Three structural models exist. Each is a deliberate choice, not an arbitrary default:

- **SKAG (Single Keyword Ad Group):** one keyword per ad group; maximum message
  match between keyword and ad copy; maximum diagnostic isolation. Appropriate when
  conversion volume per keyword is sufficient for independent tracking and the account
  operates below the conversion-volume threshold for Smart Bidding at ad-group level.
  Drawback: maintenance overhead scales linearly with keyword count.
- **STAG (Single Theme Ad Group):** tightly themed keyword clusters per ad group;
  shared ad copy reflects the theme rather than the exact keyword; reduces maintenance
  overhead while preserving thematic relevance. Appropriate for mid-scale accounts
  where per-keyword isolation is impractical but theme separation is maintained.
- **Broad-Match with Smart Bidding consolidation:** broad-match keywords feed the
  algorithm maximum query volume; the algorithm uses audience signals, device context,
  and conversion history to bid selectively. Requires sufficient conversion volume
  (minimum 50 conversions per month at campaign level per Google's stated prerequisite),
  a well-structured negative-keyword list to exclude irrelevant query expansion, and
  active Search Query Report monitoring. Not appropriate for accounts below the
  conversion-volume threshold.

**Campaign Type Selection by Intent**

| Campaign Type | When Appropriate | When Not Appropriate |
|---|---|---|
| Search | Direct-response; user expresses explicit query intent | Brand awareness without conversion intent; visual-product categories |
| Shopping / PMax Shopping | E-commerce with product feed; comparison intent | Service businesses; no structured feed |
| Performance Max | Supplementary reach across Google inventory after Search and Shopping are optimised; sufficient conversion history | Primary campaign type before Search is optimised; insufficient conversion volume |
| Display | Remarketing to past site visitors; awareness objectives with defined audience | Cold prospecting without remarketing exclusions applied |
| Demand Gen (Meta / Google) | Upper-funnel creative-driven campaigns with lookalike or interest targeting | Direct-response campaigns where click intent is the primary signal |

## Keyword Research

Keyword research is an intent-classification exercise before it is a volume exercise.
A keyword with 10,000 monthly searches and mixed intent — some users researching,
some comparing, some ready to purchase — requires segmentation before it can be bid
on efficiently. A keyword with 200 monthly searches and unambiguous purchase intent
may warrant higher bids than the high-volume mixed-intent term.

**Intent Classification**

Every keyword is assigned to one of four intent categories before being added to any
campaign:

| Intent Class | Signal | Campaign Destination |
|---|---|---|
| Brand | Contains the advertiser's trademarked or colloquial brand terms | Brand campaign |
| Non-Brand Commercial | Describes the product or service without brand reference; user likely in evaluation or purchase phase | Non-brand campaign |
| Competitor | Contains a competitor's brand or product name | Competitor campaign |
| Informational | Research or comparison query; no direct purchase signal | Informational campaign if LTV model supports it; otherwise negative list |

**Match-Type Strategy**

Match types control which queries trigger a keyword. Match-type selection is a
structural decision with bid and attribution consequences:

- Exact match: maximum query control; minimum reach. Use for highest-value, highest-confidence keywords where query-keyword alignment is non-negotiable.
- Phrase match: moderate control; captures close variants. Use when query expansion around a core phrase is acceptable and monitored.
- Broad match: maximum reach; minimum control. Use only when Smart Bidding is active, conversion-volume prerequisites are met, and a comprehensive negative-keyword list is in place.

Mixed match types within the same ad group for the same keyword intent produce
auction cannibalism — exact and phrase variants compete against each other and
produce ambiguous Quality Score signals.

**Negative-Keyword Discipline**

Negative keywords are not optional hygiene; they are structural controls that define
the account's query scope. An account without negative keywords is bidding on the
full query space the platform chooses to match, which includes irrelevant, low-intent,
and competitive queries that consume budget without conversion signal.

- Campaign-level negatives: intent-class exclusions. The non-brand campaign excludes
  all brand terms; the brand campaign excludes all non-brand commercial terms.
- Ad-group-level negatives: theme exclusions within a campaign. An ad group for
  "project management software" excludes "free" if the product has no free tier.
- Account-level shared negative lists: universal exclusions (competitor names in
  non-competitor campaigns, irrelevant industry terms, navigational queries) applied
  across all campaigns.
- Search Query Report review cadence: weekly for active accounts; negatives added
  within 7 days of identifying an irrelevant spend pattern.

## Bid Strategy Selection

Bid strategy is matched to data maturity. The correct bid strategy for an account
with 10 conversions per month is not the same as the correct strategy for an account
with 500 conversions per month. Applying Smart Bidding before the data prerequisites
are met does not accelerate learning; it produces auction decisions based on
statistically insufficient conversion signals.

**Bid Strategy Matrix by Data Maturity**

| Strategy | Conversion-Volume Prerequisite | When to Select | Risk Profile |
|---|---|---|---|
| Manual CPC | None — appropriate below any automated threshold | New accounts; brand campaigns requiring impression-share control; accounts where conversion tracking is not yet verified | Full manual exposure to auction volatility; requires active daily management |
| Enhanced CPC (eCPC) | Minimum 20–30 conversions per month | Transition layer from manual to automation; retains manual bid floor with algorithmic micro-adjustments | Low automation risk; limited upside vs Target CPA |
| Maximise Conversions | Minimum 30 conversions per month at campaign level; no CPA target | Budget-constrained campaigns where spend efficiency is secondary to volume growth; time-limited promotions | Budget exhaustion risk without CPA guardrail |
| Target CPA | Minimum 30–50 conversions per month at campaign level | Established campaigns with stable conversion rate; known acceptable cost-per-acquisition | CPA target set too low starves the campaign of impression share; target set too high produces budget waste |
| Target ROAS | Minimum 50 conversions per month at campaign level; revenue values attached to conversions | E-commerce accounts with heterogeneous product values; portfolio bid strategies across multiple campaigns | Revenue-value accuracy dependency; incorrect values produce incorrect bidding |
| Maximise Conversion Value | Same as Target ROAS without explicit ROAS target | Revenue maximisation when a specific ROAS target cannot yet be set | Same revenue-value accuracy dependency as Target ROAS |

**Bid Strategy Transition Protocol**

Transitions between bid strategies require a transition window. Abrupt strategy
changes reset the algorithm's learning period and can produce 2–4 weeks of
performance instability:

1. Verify conversion-volume prerequisites are met for the target strategy.
2. Set a conservative initial target (CPA target 20% above current actual CPA; ROAS
   target 20% below current actual ROAS) to allow the algorithm to maintain impression
   share during the learning period.
3. Do not change budgets, add/remove keywords, or modify audiences during the first
   14 days of a new bid strategy.
4. Evaluate performance at day 14 and day 30 before adjusting targets.

## Ad Copy Testing

Ad copy testing is a structured experiment, not a continuous rotation. An account
running three headline variants in a Responsive Search Ad (RSA) without a documented
hypothesis, a control definition, and a significance threshold is not running a test;
it is running an uncontrolled exposure that produces inconclusive data.

**Responsive Search Ad Configuration**

RSAs allow up to 15 headlines and 4 descriptions. Google's algorithm tests
combinations and reports an "Ad Strength" score. Ad Strength is a proxy metric — it
measures variation coverage, not conversion performance.

- Pin headlines 1 and 2 for brand-consistency and message-match elements that must
  always appear. Pinning reduces the algorithm's combination freedom; use pinning
  only for elements where variant exposure is unacceptable.
- Leave headline positions 3–15 and all description positions unpinned for
  algorithmic combination testing.
- Include at least one headline variant that directly reflects the most common
  query intent for the ad group. Message match between query and headline is a
  Quality Score input.

**Structured A/B Testing Protocol (RSA vs RSA)**

When testing fundamentally different value propositions — not headline variants within
the same RSA — use ad variation experiments or separate ad group A/B tests:

1. Define one hypothesis: "Replacing a feature-benefit headline with a social-proof
   headline will increase conversion rate by X%."
2. Define the control (current top-performing RSA) and the variant (one substantive
   change from the control).
3. Run both ads simultaneously at 50/50 rotation.
4. Determine the minimum sample size required for statistical significance at 95%
   confidence before the test starts. A test declared complete before reaching
   minimum sample size produces a false conclusion.
5. Do not modify campaign settings, budgets, or bid strategies during the test.
6. Declare a winner only after reaching significance. If significance is not reached
   within 60 days, the test is inconclusive — do not declare the variant a winner
   based on directional trends.

**Headline and Description Rotation Rules**

- Rotate by conversions (not clicks) when conversion volume is sufficient (≥30
  per variant per month).
- Rotate evenly when conversion volume is insufficient to declare conversion-rate
  significance; use click-through rate as a directional signal only.
- Document each active test with hypothesis, start date, sample size target, and
  current status. Undocumented tests are invisible to account transitions.

## Landing Page Conformance

The click is not the outcome. A campaign with a 5% click-through rate and a 0.5%
conversion rate is not a campaign with a good CTR — it is a campaign with a broken
post-click path. Landing page conformance is a prerequisite audit, not a post-launch
optimisation.

**Message Match**

Message match is the alignment between the query, the ad headline, and the landing
page headline. A user searching for "enterprise invoicing software" who clicks an ad
headlined "Enterprise Invoicing Software" must arrive at a page headlined around the
same concept. Each break in the message-match chain is a conversion-rate friction point.

- Verify message match for every ad group by tracing: primary keyword → ad headline
  → landing page headline → primary CTA. Gaps at any link require correction before
  campaign launch.

**Above-the-Fold Conversion Elements**

A landing page that requires scrolling to find the primary conversion element (form,
CTA button, phone number, product add-to-cart) is consuming the attention threshold
that the ad spend purchased. Required above-the-fold elements:

- Primary headline aligned to ad message.
- One clear CTA with unambiguous action language.
- At minimum one trust signal (social proof, security badge, or guarantee statement).

**Load-Time Budget**

A landing page that loads in more than 3 seconds on a mobile connection loses a
disproportionate share of mobile-click conversions. Mobile-first is not an optimisation
preference; it is a budget-protection measure on accounts where more than 40% of
clicks originate from mobile devices.

- Verify Core Web Vitals (LCP, INP, CLS) for every landing page before campaign
  launch and after any page modification.
- A campaign driving paid traffic to a page with LCP above 4 seconds is paying for
  clicks that the page design is discarding.

## Budget Pacing

Budget pacing is not synonymous with budget spending. A campaign that spends 100%
of its daily budget at noon has not paced correctly — it has exhausted its reach
window for the remainder of the day. Pacing discipline matches spend velocity to the
audience's conversion-probability distribution across hours and days.

**Even Pacing vs Front-Load Pacing**

| Pacing Model | When to Apply | Risk |
|---|---|---|
| Even pacing (default) | Conversion probability is relatively uniform across hours; no strong intraday conversion-rate pattern | Under-serves peak-conversion hours if the distribution is not actually uniform |
| Front-load pacing | Conversion rate is materially higher in the first half of the day; time-sensitive offers; auction competition is lower in morning hours | Exhausts budget before peak-search-volume periods if analysis is incorrect |

**Impression Share Lost Diagnostics**

Impression Share (IS) reports distinguish between two loss types: IS lost due to
budget and IS lost due to rank. These have different corrective actions:

- IS lost to budget: the campaign is eligible to show but has no remaining budget.
  Corrective actions: increase daily budget, or improve Quality Score to reduce CPC
  and extend budget reach.
- IS lost to rank: the campaign is losing auctions to competitors with higher Ad Rank.
  Corrective actions: improve Quality Score (expected CTR, ad relevance, landing page
  experience) or increase bids. Increasing budget does not correct IS lost to rank.

Diagnosing IS loss incorrectly and applying the wrong corrective action (increasing
budget for IS lost to rank, or increasing bids for IS lost to budget) is a structural
mismanagement pattern.

**Spend-Velocity Alerts**

- Set daily spend alerts at 80% of daily budget by noon local time. Consistent
  early exhaustion is a structural signal requiring pacing model review.
- Set underpacing alerts at 30% of daily budget remaining by 5 PM local time.
  Consistent underpacing indicates Quality Score, bid, or targeting constraints that
  are restricting impression eligibility below budget capacity.

## Attribution Discipline

Default attribution models misrepresent the contribution of campaigns to conversions.
A paid search account relying exclusively on last-click attribution systematically
under-values non-brand campaigns (which are often first-touch or assist-touch), and
systematically over-values brand campaigns (which are often last-touch on traffic
initiated by non-brand discovery). Attribution model selection is a budget allocation
decision disguised as a measurement setting.

**Attribution Model Comparison**

| Model | What It Measures | Best Use |
|---|---|---|
| Last click | Final click before conversion | Simple baseline; directional only; systematically biases toward brand and retargeting |
| First click | First paid click in the path | Upper-funnel contribution measurement; not a complete picture |
| Linear | Equal credit across all clicks in path | Multi-touch awareness; no differential weighting |
| Time decay | More credit to clicks closer to conversion | Appropriate when recency is a genuine purchase driver |
| Data-driven (DDA) | Algorithmic credit assignment based on observed path patterns | Preferred for accounts with sufficient conversion volume (≥300 conversions per month); most accurate for bidding alignment |

**Conversion Window Selection**

Conversion windows define the period after a click during which a subsequent
conversion is attributed to that click. Default windows (30 days for purchases, 90
days for lead forms in Google Ads) do not always match the actual purchase cycle:

- B2C impulse products: conversion window 1–7 days.
- B2C considered purchases: conversion window 14–30 days.
- B2B lead-to-close cycles: conversion window 30–90 days; view-through attribution
  requires separate justification and is not included in primary bid-optimisation
  conversion actions.

Setting a 30-day conversion window for a product with a 2-day average purchase
cycle inflates attributed conversions and overstates campaign contribution.

**Lift Studies and Incrementality**

Attribution models measure credit allocation; they do not measure incrementality.
A campaign that receives credit for 500 conversions in a last-click model does not
prove that those 500 conversions would not have occurred without the campaign. Lift
studies (geo-holdout, matched-market, or platform-native incrementality tests) are
the correct tool for measuring whether a campaign is generating incremental demand
or capturing demand that would have converted through another path.

Accounts making budget-scaling decisions from attribution data alone, without an
incrementality frame, risk scaling campaigns that are capturing existing intent rather
than generating new demand.

## Anti-patterns

| Anti-pattern | Failure Mode |
|---|---|
| Spray-and-pray match types | All keywords set to broad match without negative-keyword lists or conversion-volume prerequisites for Smart Bidding; the account bids on the full query space the platform chooses to match, including irrelevant, competitor-adjacent, and informational queries that consume budget without commercial-intent signal |
| No negatives | An account operating with no campaign-level or account-level negative keywords has an undefined query scope; every broad or phrase-match keyword is bidding on a superset of intended queries; Quality Score, conversion rate, and average CPC all degrade from irrelevant traffic contamination |
| Vanity-CTR optimisation | Optimising for click-through rate as a primary KPI produces high-CTR, low-intent traffic; CTR is a Quality Score input and a relevance signal, not a conversion predictor; accounts managed to CTR targets routinely achieve high impressions and low conversion volume |
| Ignoring Search Query Report | The Search Query Report (SQR) is the account's ground truth for what queries are actually triggering ads; an account that does not review the SQR weekly has no visibility into the query-to-keyword gap; negatives are not added; irrelevant spend accumulates silently |
| No landing-page test | Campaign optimisation without landing page experimentation treats the post-click path as a constant; in most accounts, landing page conversion rate variance across variants exceeds bid strategy efficiency gains; optimising the ad without testing the destination is optimising the top of the conversion path while ignoring the bottom |
| Smart Bidding below prerequisite threshold | Deploying Target CPA or Target ROAS on campaigns with fewer than 30 conversions per month per the stated minimum; the algorithm lacks sufficient signal to bid selectively; the result is either aggressive spend on low-signal queries or excessive bid suppression from premature learning-phase signals |
| Conflating attribution credit with incrementality | Treating high attributed conversion volume as evidence that a campaign is generating demand; attribution models redistribute credit, they do not measure whether the credited conversions are incremental; scaling a campaign that captures existing intent rather than generating new demand inflates spend without proportional revenue lift |

## Cross-References

- `domains/paid-media/skills/search-query-analyst` — Search Query Report analysis,
  query-to-keyword gap identification, and negative-keyword expansion protocols.
- `domains/paid-media/skills/auditor` — Full paid-media account audit framework
  covering structural health, bid strategy compliance, conversion tracking verification,
  and attribution model review.
- `domains/paid-media/skills/tracking-specialist` — Conversion tracking implementation,
  tag audit, Google Tag Manager configuration, and conversion-action hierarchy setup.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review): PPC strategy authorship follows
  the two-pass discipline — pass one is structural analysis and diagnostic (account
  audit, intent classification, bid-strategy data-maturity check, attribution model
  review) without drafting any campaign changes; pass two is campaign design and
  optimisation recommendations using only what the diagnostic surfaced. A campaign
  restructure authored before the structural audit is complete produces a structure
  optimised for the strategist's preferences rather than the account's actual conversion
  signal, the paid-media equivalent of a reviewer who generates and evaluates in a
  single motion.
