---
name: app-store-optimizer
description: >
  App Store Optimization discipline covering keyword targeting across the
  relevance × volume × difficulty matrix, conversion-optimised metadata and
  visual assets for Apple App Store and Google Play, systematic A/B test
  cadence, platform-algorithm awareness for both crawler models, review-rating
  economy management, and post-install retention loop diagnostics. Distinct
  from paid-media acquisition (UA campaigns, bid management) — this skill
  governs organic discoverability, store-listing conversion, and the install
  quality signals that feed algorithmic ranking. Use when: selecting or
  auditing keyword sets against platform-specific crawlers; optimising title,
  subtitle, promotional text, or description within per-store character limits;
  sequencing screenshot and preview-video assets for conversion; designing an
  A/B test with correct isolation and sample-sizing; diagnosing rating-score
  decline or review-volume gaps; or attributing D1/D7/D30 retention breaks
  back to install-source quality.
owner: Laila Nasser (App Store Optimizer, domain persona)
tier: domain:marketing-global
scope_tags: [aso, app-store-optimization, keyword-targeting, conversion-rate-optimization, app-store-algorithm, review-rating]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-app-store-optimizer.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/fastlane/metadata/**"
  - "**/store-listing/**"
  - "**/app-store/**"
  - "**/play-store/**"
---

# App Store Optimizer

## Cardinal Rule

Every keyword, metadata field, visual asset, and test variant MUST be
justified by a measurable organic signal — search impression volume,
category-browse impression rate, or conversion rate from listing page visit
to install. Decisions made from aesthetic preference, competitor imitation
without data verification, or keyword tool estimates that are not
cross-validated against platform-native analytics (App Store Connect Search
Popularity, Google Play Console Keyword Planner) are opinion, not ASO work.
Optimisation without a pre-specified primary metric and a baseline value
recorded before the change is not optimisation — it is undocumented
experimentation with no learning accumulation.

---

## Fail-Fast Rule

No more than one variable is changed per A/B test cycle. Testing a new icon
variant simultaneously with a new screenshot sequence makes it impossible to
attribute a conversion-rate change to either variable. Each test runs until
the pre-specified minimum sample size is reached and the minimum duration
(at minimum 7 days, to capture a full weekly traffic cycle) has elapsed.
Stopping a test because the partial result looks favourable is p-hacking.
Extending a test beyond its pre-specified endpoint because the result is
unfavourable is a different form of the same bias. Both invalidate the
result. When a test produces a null result, that null result is recorded as
a learning entry — it constrains the hypothesis space for subsequent tests
and has equal value to a positive result.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Selecting or auditing keyword sets: primary, secondary, and long-tail tiers
  across brand, category, feature, and competitor-gap dimensions for either
  Apple App Store or Google Play.
- Drafting or revising metadata fields (title, subtitle, promotional text,
  keyword field, description) within platform-enforced character limits.
- Sequencing screenshot or preview-video assets for conversion-rate impact:
  frame order, caption placement, locale variants.
- Designing an isolated A/B test for a single visual or textual variable with
  correct sample-size calculation and duration specification.
- Diagnosing a rating-score decline, review-volume gap, or flagged review
  pattern that may affect ranking algorithms.
- Attributing install-source quality breakdowns to D1/D7/D30 retention
  differences between organic search, browse, and referral traffic.
- Scoping a localisation matrix for a set of priority markets.

Skip when: the work is paid-channel user acquisition campaign execution or
bid management (use ppc-strategist instead); the task is brand-voice content
creation for social media (use social-media-strategist or content-creator);
or the engagement is general mobile product growth loop architecture without
a store-listing component (use growth-hacker instead).

---

## Keyword Strategy

ASO keyword selection operates on a three-axis evaluation matrix. All three
axes must be scored before a keyword enters the active set.

### Relevance × Volume × Difficulty Matrix

| Axis | Definition | Measurement Approach |
|---|---|---|
| Relevance | The degree to which users who search this term intend to install an app that the product genuinely satisfies. | Manual evaluation + install-quality proxy: conversion rate and D7 retention of users who arrive via this keyword versus category average. |
| Volume | The number of searches per period that include this term on the target platform. | App Store Connect Search Popularity score (0–100 relative scale); Google Play Console search volume estimate. Both are relative, not absolute — use for ranking within a platform, not cross-platform comparison. |
| Difficulty | The strength of existing apps ranking for this term, measured by their rating count, download velocity, and metadata alignment. | Category leader rating volume as a proxy; estimated gap to page-one placement given the product's current rating count and growth velocity. |

Viable candidates score High relevance, and at least one of: Medium-to-High
volume with Medium difficulty, or Medium volume with Low difficulty. High
volume + High difficulty keywords are tracked as aspirational targets with a
minimum 12-month horizon unless the product's installed base and rating count
have already reached category-leader proximity.

### Apple Search vs Google Play Crawler Differences

The two platform crawlers index different metadata fields and weight them
differently.

**Apple App Store:**
- Title (30 chars): highest algorithmic weight. Primary keyword must appear here.
- Subtitle (30 chars): second-highest weight. Secondary keyword or a qualifying
  phrase that completes the title's intent signal.
- Keyword field (100 chars, comma-separated, not visible to users): supplementary
  index. No spaces around commas (each space wastes a character). Do not repeat
  terms already in Title or Subtitle — Apple indexes them already and repetition
  wastes keyword-field budget.
- Developer name and in-app purchase names are also crawled.
- Description is NOT indexed for search ranking on iOS; it serves conversion
  only.

**Google Play:**
- Title (30 chars): high weight.
- Short description (80 chars): indexed and user-visible below the title in
  search results. Must front-load the primary keyword and communicate value in
  the first clause — it is the primary conversion line in browse view.
- Long description (4000 chars): fully indexed. Keyword density matters; 3–5
  natural repetitions of priority terms across the full description body is the
  documented guidance range. Keyword stuffing (mechanical repetition above
  meaningful density) triggers spam filters and harms ranking.
- Developer name is indexed.

### Brand vs Category vs Feature Keyword Tiering

Three tiers govern how keyword budget is allocated across the available field
characters:

**Tier 1 — Brand**: the product's own name and direct brand misspellings. These
are low-difficulty by definition (no competitor should outrank a brand's own
app for its brand name) and must be protected in the title.

**Tier 2 — Category**: terms that describe the app's primary use case class.
Highest volume, highest difficulty. Occupy the remaining title and subtitle
characters after brand is placed. Long-horizon investment — ranking improvement
is measured in quarters, not weeks.

**Tier 3 — Feature**: specific capability or problem-solution terms with lower
volume but higher intent and lower difficulty. Keyword field and description
carry these. Feature keywords are the primary driver of near-term ranking gains
because the competition is structurally lower.

---

## Metadata Discipline

Metadata optimisation is constrained by hard platform character limits that
are enforced at submission. Every field draft must be character-counted before
submission — overruns cause rejection and delay.

### Character Limits Per Store

| Field | Apple App Store | Google Play |
|---|---|---|
| Title | 30 | 30 |
| Subtitle / Short Description | 30 | 80 |
| Promotional Text (iOS only) | 170 | — |
| Keyword Field (iOS only) | 100 | — |
| Description | 4000 | 4000 |

### First-Line Eyeball Test

The first line visible in a truncated listing view (search result card before
the user taps to expand) is the only line guaranteed to be read. On iOS this
is the title + subtitle combination. On Google Play it is the title + short
description combination. Both combinations must communicate the product's
primary value proposition in full without requiring expansion. Metadata that
requires the user to tap "more" to understand what the app does has failed the
first-line test.

### Localisation Matrix

Localisation is not translation. Metadata for each locale requires:

1. Native-language keyword research conducted with a native speaker or native
   search tool — direct translation of English keywords does not match local
   search behaviour.
2. Cultural relevance review: value propositions, imagery references in
   description copy, and social proof framing may need reorientation, not
   just translation.
3. Character limit compliance re-verified per locale — the same semantic
   content occupies different character counts in different scripts.

Priority localisation order: the top-10 markets by target-category download
volume on the target platform, not the markets where the product already has
users. Existing users require support localisation, not acquisition localisation
— these are different work streams.

---

## Visual Asset Architecture

Visual assets (icon, screenshots, preview video) are the primary conversion
surface for users who reach the listing page. Metadata drives arrival; visuals
drive install.

### Conversion-Optimised Asset Order

**Icon**: must be recognisable at 16px (small search result tile) and at 512px
(feature placement). The icon is the highest-leverage single asset — it appears
in every browse, search, and chart context before any other element. Test one
variable at a time: colour scheme, symbol choice, or complexity level. Never
test two icon variables simultaneously.

**Screenshot sequence**: the first screenshot must communicate the product's
primary value proposition without caption support — assume the image is viewed
in 300ms without reading. Subsequent screenshots address secondary features,
social proof, and use-case diversity. Common evidence-based ordering:
- Screenshot 1: hero value proposition.
- Screenshots 2–3: core use cases in action.
- Screenshots 4–5: differentiation features or social proof.
- Screenshots 6+: secondary features, platform-specific content, or awards.

**Preview video** (optional): the first 3 seconds are the only seconds
guaranteed to be watched. Lead with the highest-impact feature demonstration,
not a brand introduction. 15–30 seconds on iOS; up to 30 seconds on Google
Play. Auto-plays muted in most browse contexts — captions are required for
the muted-play context to carry message.

### Per-Locale Visual Variants

Screenshots containing UI text, user-facing copy, or locale-sensitive
imagery require locale-specific variants, not overlaid translations on
English-language screenshots. Overlaid translations fail the cultural
relevance standard and are frequently flagged by platform review teams in
major non-English markets.

### A/B Test Impact on Visual Assets

App Store Connect Product Page Optimization and Google Play Store Listing
Experiments both support visual asset A/B testing natively. Test one asset
category at a time. Do not run an icon test and a screenshot test
simultaneously — results will be unattributable.

---

## A/B Test Cadence

### One Variable at a Time

Each test cycle isolates one variable: icon, first screenshot, screenshot
sequence order, short description, or preview video. Testing multiple
variables simultaneously produces unattributable results. All previous active
tests on the same listing must reach their endpoint (sample complete + minimum
duration elapsed) before a new test begins on any variable on that listing.

### Minimum Sample Size

Sample size is calculated from the baseline conversion rate (listing visits
to installs), the minimum detectable effect (MDE — the smallest conversion
improvement that would justify the change in production), desired power (0.80
standard; 0.90 for high-stakes changes), and alpha (0.05). MDE is specified
before the test launches, not after looking at partial data. For store listings
with fewer than 2,000 weekly listing visits, most visual-asset tests will
require 4–8 weeks to reach a statistically valid sample — this is a constraint
that cannot be accelerated by shortening the test.

### Duration vs Traffic

Minimum duration is 7 days regardless of traffic volume, to capture a full
weekly seasonality cycle. For products with strong monthly seasonality (e.g.
products tied to recurring events or billing cycles), minimum duration extends
to 28 days. Listings with very high weekly traffic (100,000+ visits/week) may
reach sample size before minimum duration — the minimum duration still applies.

### Never Run Parallel Tests on Same Screen

Two simultaneous tests on the same listing screen contaminate each other's
traffic assignment. Platform-native tools enforce this for their own test
slots; manually tracked tests on the same screen must be serialised.

---

## Review-Rating Economy

App store ranking algorithms incorporate rating score and review volume as
ranking signals. The floor below which ranking suppression is documented
varies by category but a 4.0 threshold is the conservatively cited floor
across Apple and Google internal documentation. The 4.5+ range is necessary
to compete for feature placement.

### Rating Threshold for Ranking

Maintain a rolling 30-day rating score above 4.2 as a minimum operating floor.
Scores below 4.0 require an immediate diagnostic: release note analysis (recent
update causing regressions), review text categorisation (systemic bug reports
versus isolated complaints), and a triage path for the root cause. Suppressing
negative reviews through other tactics without addressing the underlying cause
delays the ranking damage rather than preventing it.

### Review-Prompt Timing

The optimal prompt timing is immediately after a value-delivery moment, not
after an error, and not at app launch. Prompts served after a user successfully
completes a task the app is designed for produce response rates and rating scores
measurably above prompts served at session start. Both Apple and Google enforce
limits on review-prompt frequency (Apple: three times per year maximum via the
native API; Google: no specified cap but aggressive prompting triggers spam
classifier).

Use only platform-native review prompt APIs (`SKStoreReviewRequest` on iOS;
`ReviewManager` on Android). Custom review dialogs that intercept users before
they reach the platform's native flow violate both stores' policies and
constitute a dark pattern.

### Response Cadence

Responding to negative reviews publicly is a ranking signal and a conversion
signal — users reading negative reviews also read the developer response. Target
a 24-hour response window for reviews at 1–2 stars. Responses must acknowledge
the specific issue reported, provide a resolution path or timeline, and avoid
defensive framing. Do not request that users update their rating in the public
response — this is prohibited by both stores.

### Never Incentivise Reviews

Offering any reward — in-app currency, extended trial, discounts, or any other
benefit — in exchange for a review or rating violates both stores' policies and
constitutes a fraudulent review practice. Detection results in rating removal,
app suspension, or developer account termination. The restriction applies to
direct incentives and to conditional incentives ("rate us to unlock this
feature").

---

## Post-Install Retention Loop

Install quality is a ranking signal on both platforms. An app that drives high
install volume but low post-install engagement is penalised algorithmically
over time. The retention loop connects ASO work to product health.

### D1/D7/D30 Cohort Monitoring

Segment retention cohorts by install source: organic search, category browse,
search ads (if running), editorial feature, and referral. Retention differences
across sources are the primary diagnostic signal for install quality. High
organic search retention paired with low paid-install retention indicates the
paid targeting is reaching a different user intent segment than the organic
keywords. The correct response is to adjust paid targeting to match the
organic keyword intent, not to improve the store listing for paid traffic.

Reference orientation benchmarks (consumer apps):

| Interval | Low floor | Healthy range |
|---|---|---|
| D1 | < 20% (investigate) | 25–40% |
| D7 | < 8% (investigate) | 12–22% |
| D30 | < 3% (investigate) | 5–12% |

Values below the low floor warrant a diagnostic before any further ASO
investment — a listing change that increases installs from users who do not
retain compounds the install-quality penalty.

### Install-Source Attribution

Attribution requires a Mobile Measurement Partner (MMP) or platform-native
attribution (SKAdNetwork on iOS 14.5+; Google Play Install Referrer on
Android). Without attribution, retention cohorts cannot be segmented by source
and the link between keyword changes and install quality is unverifiable. ASO
work undertaken without attribution infrastructure in place produces unverifiable
outcome claims.

### Uninstall Reason Diagnostics

When D1 or D7 retention falls below floor, uninstall reasons should be
investigated via:
- In-app survey at the beginning of the third session (users who did not uninstall
  at D1 but are at uninstall risk).
- Exit survey surfaced on Android uninstall confirmation (Play Store allows
  opt-in collection).
- App review text categorisation for recurring complaint patterns.

Uninstall reasons feed keyword strategy: if recurring complaints indicate a
mismatch between what the listing promises and what the product delivers,
the listing is over-promising on that dimension. Correcting the metadata to
match the actual product experience reduces the install quality penalty
regardless of the volume impact.

---

## Localisation Strategy

### Top-10 Markets First

Localisation priority is set by target-category download volume in each
market on the target platform — not by existing user geography, not by
language similarity to the primary locale. Allocating localisation budget
to markets where the product already has users is retention localisation,
not acquisition localisation; both have value but are different work streams
with different asset requirements.

### Native Review Over Translation

Metadata copy for a priority locale must be reviewed by a native speaker who
also has familiarity with the app category's search vocabulary in that market.
Machine translation and bilingual-reviewer translation without search-vocabulary
context produce grammatically correct text that does not match how users in
that market search. The search vocabulary gap is the primary cause of poor
keyword performance in localised markets.

### Cultural Relevance Over Literal Translation

Screenshot copy, feature naming, and social proof framing in visual assets
should be adapted for cultural resonance, not translated literally. A social
proof claim that resonates in a high-individualism market (e.g. "used by
X people like you") may require reframing for high-collectivism markets.
Feature ordering in screenshots may need adjustment if a feature that is
primary for one market is secondary for another.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Practice |
|---|---|---|
| **Keyword stuffing in description** | Repetitive or unnatural keyword insertion above a meaningful density threshold triggers spam classifiers on both platforms, suppressing ranking rather than improving it. | Integrate priority keywords naturally at 3–5 occurrences across the full description. If natural integration cannot be achieved above 3 repetitions, the keyword is not a good match for the description content. |
| **Running A/B tests on multiple variables simultaneously** | Conversion-rate change cannot be attributed to either variable when both are changed at once. The test produces no actionable learning and consumes the traffic required for a valid single-variable test. | Serialise all tests. One variable active at a time. Collect result, record learning, then initiate the next test. |
| **Fake reviews or review rings** | Both platforms have automated and human-review detection for inauthentic review patterns. Detection results in rating removal, app suspension, or developer account termination. The short-term rating improvement is reversed with penalties that take months to recover from. | Drive review volume exclusively through platform-native prompts served at value-delivery moments. |
| **Dark-pattern install prompts** | Intercepting users before the platform-native review flow, using custom dialogs, or filtering users to show the native prompt only to those who indicate a positive sentiment violates both stores' review policies and developer agreements. | Use only `SKStoreReviewRequest` (iOS) and `ReviewManager` (Android). Serve the prompt after a value-delivery moment without pre-screening. |
| **Ignoring store-specific crawler differences** | Applying iOS metadata strategy to Google Play (e.g. relying on keyword field, not investing in short description) leaves the highest-weight indexable field under-optimised on Android. The two crawlers weight fields differently and must be treated as distinct systems. | Maintain separate metadata strategies per platform. iOS: title + subtitle + keyword field as the index. Google Play: title + short description + long description as the index. |
| **Localising only text, not visual assets** | Screenshots containing English-language UI captions or culturally specific imagery serve as effective assets only in the primary locale. In other markets they signal low localisation effort and reduce conversion. | Produce locale-specific screenshot variants with captions in the target language and culturally appropriate imagery for all priority markets in the localisation matrix. |
| **Treating rating score as a vanity metric without source analysis** | A 4.3 average that is the result of a bimodal distribution (many 5-star + many 1-star) carries less ranking and conversion weight than a 4.3 composed of genuine mid-to-high ratings. The distribution signals a user segmentation problem that the aggregate score hides. | Monitor rating distribution, not only aggregate score. A bimodal distribution requires user segmentation analysis: who are the 1-star reviewers and are they the target user? If not, the acquisition source needs adjustment. |

---

## Cross-References

- `.claude/skills/domains/marketing-global/skills/seo-specialist` — Organic
  search strategy for web properties. Keyword research methodology and
  relevance × volume × difficulty evaluation are structurally parallel between
  web SEO and ASO; the seo-specialist skill governs web-crawler contexts while
  this skill governs store-crawler contexts. Localisation matrix approaches
  overlap.

- `.claude/skills/domains/marketing-global/skills/growth-hacker` — Experiment
  design, funnel diagnostics, and retention analysis. The growth-hacker skill
  governs the experimental methodology layer (hypothesis formation, MDE,
  sample sizing, stopping rules) that is applied within this skill to A/B test
  cadence and install-quality cohort analysis. When a retention loop diagnostic
  exceeds store-surface scope and requires product or onboarding changes, hand
  off to growth-hacker.

- `.claude/skills/domains/paid-media/skills/ppc-strategist` — Paid user
  acquisition campaign execution, Apple Search Ads and Google App Campaigns bid
  management. This skill governs organic ASO; ppc-strategist governs paid
  channel execution. Attribution infrastructure requirements (MMP, SKAdNetwork,
  Install Referrer) are shared between the two disciplines and must be jointly
  confirmed before either work stream begins.

---

## ADR Anchors

- **ADR-058** (`ADR-058-brainstorm-gate-and-two-pass-review.md`) — Two-pass
  review mandate for high-stakes authored artifacts. ASO keyword strategy
  documents, metadata revision proposals that span multiple platform-field
  changes, and localisation matrix decisions are in scope. First pass:
  completeness — all fields character-counted, all keyword candidates scored
  on relevance × volume × difficulty, all A/B test plans include primary
  metric and MDE. Second pass: adversarial pressure-testing — does the keyword
  set over-promise relative to actual product capability (install quality risk)?
  Are any metadata changes applied to both iOS and Android without verifying
  crawler-difference implications?
