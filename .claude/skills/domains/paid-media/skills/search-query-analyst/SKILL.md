---
name: search-query-analyst
description: >
  Search query analysis discipline for paid search accounts: STR and SQR mining at
  configurable frequency cadence, intent classification across informational / commercial /
  transactional / navigational axes, negative-keyword harvest at account / campaign /
  ad-group scope, query-to-keyword matching diagnostics across match types, automated
  bidding signal interpretation against data-sufficiency thresholds, and irrelevant-traffic
  detection via geo / device / language / parameter-stuffing vectors. Use when a paid
  search account shows CPA degradation without a bid or budget change, when broad-match
  or Performance Max campaigns have not been reviewed against SQR data in the past 30 days,
  when negative keyword coverage is unknown or undocumented, or when match-type performance
  has never been segmented and compared.
owner: Nadia Sørensen (Search Query Analyst, paid-media domain)
tier: domain:paid-media
scope_tags:
  - search-query-analysis
  - str-sqr-mining
  - negative-keywords
  - intent-classification
  - query-keyword-matching
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-search-query-analyst.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/search-queries/**"
  - "**/sqr/**"
  - "**/negative-keywords/**"
---

# Search Query Analyst

## Cardinal Rule

Every impression on an irrelevant query is a direct transfer of budget from converting
traffic to noise. The search query layer sits between bidding strategy and actual user
intent — no algorithmic smart-bidding system compensates for a structurally uncleaned
query funnel. Query analysis is not an audit task performed once at account setup; it is
a continuous control system with defined cadence, thresholds, and escalation paths. An
account that has not reviewed its SQR in 30 days has no reliable signal on whether its
negative keyword architecture is intact, whether match-type bleed has increased waste,
or whether new irrelevant modifiers have entered the query stream through broad-match
expansion or Performance Max category drift.

## Fail-Fast Rule

Stop and escalate before continuing any query optimization when: (1) the SQR pull is
older than 14 days and automated bidding is active — stale data produces negative keyword
decisions calibrated to a query distribution that no longer exists; (2) the account has
fewer than 500 impressions per match-type segment in the analysis window — statistical
conclusions on match-type performance at this volume have confidence intervals that render
them operationally useless; (3) a proposed account-level negative would conflict with any
exact-match keyword in any active campaign — negative keyword conflicts silently suppress
converting queries and are unrecoverable without a full audit cycle.

## When to Apply

- CPA has increased by more than 15% week-over-week without a corresponding bid, budget,
  or auction-landscape change — query drift is the primary alternative hypothesis.
- Broad-match keywords or Performance Max campaigns are active and SQR has not been
  reviewed in the past 30 days.
- Negative keyword lists exist at account level only, with no campaign-level or
  ad-group-level segmentation.
- A new campaign was launched without seeding negative keywords from historical SQR data
  of related campaigns.
- Match-type distribution has never been reported as a standalone performance dimension.
- An account was inherited, merged, or scaled rapidly and the query layer has not been
  audited against the new traffic volume.

## STR / SQR Mining Discipline

Search Term Report (STR) and Search Query Report (SQR) mining follow a tiered cadence
calibrated to account spend and match-type aggressiveness.

**Frequency cadence:**
- Accounts above $10,000 USD/month with broad-match or broad-match-modifier active:
  weekly tactical review covering the prior 7-day window.
- Accounts between $2,000 and $10,000 USD/month with phrase or exact match dominant:
  bi-weekly review covering the prior 14-day window.
- Accounts below $2,000 USD/month: monthly review covering the prior 28-day window.
- Performance Max campaigns require an independent SQR pull from the Search Category
  Insights panel; do not fold PMax query data into standard SQR without labeling the
  source — PMax query visibility is partial and conflation distorts impression share
  calculations.

**Minimum-impression threshold per query:**
- A query with fewer than 10 impressions in the analysis window produces no statistically
  stable intent signal. Log it for cohort grouping but do not make individual keyword or
  negative decisions based on it.
- A query with 10–49 impressions and zero conversions in a 30-day window qualifies for
  review-and-flag status but not automatic negative addition — low-volume queries can
  carry conversion events outside the 30-day attribution window.
- A query with 50 or more impressions and zero conversions in a 30-day window, where
  CPA target would require at minimum 2 conversions by volume-to-CPA ratio, qualifies
  for negative keyword addition subject to intent classification review.

**Cohort-based filter to surface signal:**
- Group queries by n-gram prefix (1-gram, 2-gram, 3-gram) before individual query
  review. A modifier appearing in 40 or more distinct queries with a collective
  zero-conversion rate is a candidate for account-level negative regardless of
  individual query impression counts.
- Segment query cohorts by device, geography, and hour-of-day before drawing waste
  conclusions — a query that converts on desktop may be genuinely irrelevant on mobile
  due to landing page form-factor mismatch, not query-level irrelevance.

## Intent Classification

Intent classification maps each query to one of four canonical intent categories.
Platform taxonomy variance means the same query can resolve to different intent buckets
depending on the platform and the campaign type; never assume intent is platform-invariant.

**Canonical intent taxonomy:**

| Intent | Definition | Typical conversion rate relative to account mean |
|---|---|---|
| Transactional | Query contains explicit purchase, booking, or download signal | 2–5x above mean |
| Commercial | Query signals active comparison, review-seeking, or vendor evaluation | 0.8–2x mean |
| Informational | Query seeks explanatory content without vendor evaluation signal | 0.05–0.3x mean |
| Navigational | Query targets a specific brand or URL | Highly variable; depends on brand ownership |

**Per-platform taxonomy variance:**
- Google Search: transactional and commercial intent queries typically contain verbs
  (buy, compare, hire, get, download) or modifier-noun patterns (best, top, cheapest,
  near me). Informational queries are disproportionately long-tail question forms.
- Microsoft Advertising: demographic skew toward older, professional audiences shifts
  commercial intent queries toward higher specificity; the same 2-word query often has
  higher commercial intent on Bing than on Google.
- Performance Max: intent classification from Search Category Insights is aggregate, not
  per-query. Treat PMax intent signals as directional rather than individually actionable.

**Intent-to-campaign mapping discipline:**
- Transactional queries must route to campaigns with transactional ad copy and
  conversion-optimized landing pages. Routing transactional queries to informational
  landing pages is a structural CPA inflator that no bid adjustment can correct.
- Informational queries are legitimate targets only in awareness-stage campaigns with
  CPM or tCPM bidding; never add broad-match informational keywords to tCPA campaigns.

## Negative-Keyword Harvest

Negative keyword architecture operates across three scope levels. The scope level for
a negative determines blast radius — a negative placed too high suppresses queries across
all campaigns; placed too low, it requires duplication across dozens of ad groups and
degrades over time as structure evolves.

**Scope selection rules:**
- Account-level negatives: only for queries that are universally irrelevant regardless
  of campaign, product, or audience segment. Examples: competitor brand names that the
  account will never target, content categories legally prohibited from the account (e.g.
  certain financial product queries under regulatory restriction), and n-gram modifiers
  with zero historical conversion at account level over 90+ days and 1,000+ impressions.
- Campaign-level negatives: for queries irrelevant to a specific campaign's product
  scope but potentially relevant elsewhere in the account. A campaign targeting enterprise
  software should carry "free" and "student" as campaign-level negatives if the account
  also runs a separate SMB campaign where those modifiers convert.
- Ad-group-level negatives: for query-sculpting within campaigns — directing queries to
  the intended ad group by negating adjacent keywords at the ad-group level. This is the
  primary mechanism for preventing internal query cannibalization.

**Match type for negatives:**
- Exact-match negatives provide precision suppression with no blast-radius risk.
  Use for specific navigational queries and brand terms.
- Phrase-match negatives suppress queries containing the negative phrase in sequence.
  Use for modifier-noun patterns with clear irrelevance signals (e.g. [free trial] as a
  phrase negative on a revenue-only campaign).
- Broad-match negatives are never appropriate as the default. Broad-match negatives
  suppress any query containing the negative keyword in any form, including close
  variants — the blast radius is unpredictable and routinely suppresses converting queries.
  Use only when an n-gram cohort analysis at 90-day + 10,000-impression scale confirms
  universal irrelevance at that modifier level across all match variants.

**Never-too-broad rule:**
Before adding any negative at account or campaign level, run a conflict check: pull all
exact-match keywords in all active campaigns and verify the proposed negative does not
suppress any of them. A negative keyword conflict suppresses exact-match keywords silently
— Google Ads surfaces this only in the Negative Keyword Conflicts diagnostic, which is
not checked automatically. Conflict rate target: zero.

## Query-Keyword Matching Diagnostics

Match-type performance varies structurally by account vertical, competition level, and
query specificity. Reporting match-type performance as a single blended metric conceals
the most actionable optimization signal in the account.

**Broad match performance analysis:**
- Pull SQR segmented by match type. For broad-match keywords, calculate the percentage
  of impressions served on queries containing none of the keyword's constituent words
  (semantic expansion events). An expansion rate above 40% indicates Google's semantic
  model is expanding beyond the intended query space.
- Calculate waste rate (spend on non-converting queries / total spend) per keyword per
  match type over a 30-day window. Broad-match waste rates above 35% trigger a match-type
  demotion review unless smart-bidding conversion volume falls below the 50-conversions/
  30-day data-sufficiency floor.

**Phrase match and exact match boundary testing:**
- Phrase-match in post-2021 environments includes close variants that can materially
  change query coverage. Compare phrase-match impression share against exact-match
  impression share for the same keyword root; a phrase-match/exact-match impression ratio
  above 3:1 indicates close-variant expansion is active and requires review.
- Exact-match close variant audits: pull exact-match SQR and identify queries that differ
  from the exact keyword by more than spelling or grammatical inflection — these are
  close-variant expansions and should be evaluated individually for intent alignment.

**Match-type bleed detection:**
Match-type bleed occurs when a broader match type captures queries intended for a more
specific match type within the same account, causing internal auction competition and
inflating CPC. Detection: pull impression data per query string, identify queries appearing
under multiple match types for the same keyword, and calculate the CPC delta. A broad-match
query with identical CPC to its exact-match counterpart suggests Smart Bidding is
managing the auction correctly; a broad-match query with CPC 30% above the exact-match
counterpart indicates unresolved bleed.

## Automated Bidding Signal Interpretation

Smart bidding systems require sufficient conversion data to operate within calibrated
error bounds. Interpreting automated bidding query-level signals without verifying data
sufficiency produces false-positive waste conclusions.

**Data sufficiency thresholds:**
- tCPA campaigns: minimum 30 conversions in the past 30 days at campaign level for
  Smart Bidding to operate within its stated error range. Below 30 conversions, the
  algorithm is in exploration mode and query distribution is intentionally broad —
  penalizing "irrelevant" queries during exploration undermines learning.
- tROAS campaigns: minimum 50 conversions in the past 30 days. ROAS targets below the
  statistically achievable floor (visible in the tROAS simulator) force exploration mode
  indefinitely.
- Performance Max: conversion volume thresholds apply per asset group, not per campaign.
  An asset group with fewer than 20 conversions in 30 days is in exploration and its
  query categories are unreliable for negative keyword decisions.

**Smart bidding query insights interpretation:**
- The Smart Bidding Insights panel surfaces query-level performance aggregated into
  categories, not individual query strings. Category-level waste conclusions cannot be
  used to justify individual query negatives without a corroborating SQR pull.
- Signal pollution detection: if a conversion action was misconfigured (e.g., a
  micro-conversion was used as the primary conversion action during a period where
  macro-conversion data was unavailable), historical smart-bidding signals for that
  period are polluted. Flag the pollution window and exclude it from trend analysis.

## Irrelevant Traffic Detection

Irrelevant traffic reaches the account when targeting parameters fail to constrain query
delivery to the intended audience. Query-level analysis alone does not expose targeting
mismatches — a separate detection pass against targeting dimensions is required.

**Detection vectors:**

- **Geo-mismatch:** Pull impressions by location targeting vs. location of physical
  presence. Impressions from locations outside the target radius that exceed 5% of total
  impressions indicate a geo-targeting misconfiguration (presence vs. interest vs.
  regular-location setting), not a query relevance issue. Fix at targeting level, not
  via negative keywords.

- **Device-mismatch:** Segment conversion rate by device. A conversion rate on mobile
  that is less than 30% of desktop conversion rate on the same query, with mobile traffic
  representing more than 25% of total spend, indicates a landing page or checkout
  form-factor failure, not query irrelevance. Negative keywords do not resolve device
  mismatch — device bid adjustments or device exclusions are the correct mechanism.

- **Language-mismatch:** Queries in a language not matching the campaign language target
  that nonetheless trigger ads indicate a language targeting misconfiguration. This is
  common in multilingual markets where the campaign language is set to "All languages."
  Negative keywords in the non-target language provide a partial workaround but do not
  substitute for language targeting correction.

- **Parameter-stuffing:** Queries containing URL parameters, tracking codes, or injected
  strings (e.g., `{keyword}`, `utm_`, encoded characters) appearing in search term data
  indicate a click injection or bot traffic pattern. Flag immediately for the
  tracking-specialist; do not attempt negative keyword resolution — parameter-stuffed
  queries are a traffic quality issue requiring fraud investigation, not query sculpting.

## Reporting Cadence

**Weekly tactical report (aligned to STR mining cycle):**
Scope: SQR review output — new negatives added, queries promoted to keyword candidates,
match-type bleed events, conflict-check results. Audience: campaign manager. Format:
tabular delta (new negatives / new keywords / bleed events) + waste rate trend line.
Statistical change threshold for action: waste rate increase of more than 3 percentage
points versus the prior 4-week average, or a single new n-gram cohort with 100+
impressions and zero conversions.

**Monthly strategic report:**
Scope: intent distribution shift over 30-day rolling window, match-type performance
comparison, negative keyword list health (coverage rate, conflict audit results,
list-size growth trend), query-keyword alignment score (percentage of spend on queries
with correct intent classification). Audience: account strategist / paid-media auditor.
Statistically significant change threshold: a 5-percentage-point shift in intent
distribution that persists across two consecutive weekly windows constitutes a structural
change requiring campaign architecture review, not a weekly tactical response.

## Anti-Patterns

| Anti-pattern | Consequence | Correct practice |
|---|---|---|
| Ignoring SQR for more than 30 days on broad-match campaigns | Budget bleeds to irrelevant queries without detection; n-gram modifier proliferation compounds monthly | Weekly cadence with automated report delivery |
| Adding broad-match negatives as default negative type | Suppresses converting close-variant queries; blast radius extends to exact-match keywords silently | Phrase-match for modifier patterns; exact-match for specific terms; broad-match only after 90-day n-gram cohort confirmation |
| Evaluating match-type performance on blended account metrics | Hides per-match-type waste rates; broad-match waste subsidizes exact-match performance optics | Segment every performance dimension by match type before drawing conclusions |
| Building account-level negative lists without conflict checks | Exact-match keyword suppression — silent, not visible in performance reports | Run conflict check against all exact-match keywords before every account-level negative addition |
| Applying conversion-rate conclusions from informational queries to CPA campaigns | Informational queries structurally underperform CPA targets; penalizing them inflates the perceived waste rate | Separate informational query analysis from CPA campaign optimization entirely |
| Using smart bidding query insights as a substitute for SQR | Category-level signals mask individual query waste; exploration-mode traffic is penalized incorrectly | Always corroborate smart bidding insights with a direct SQR pull for the same window |
| Promoting a converting search term to keyword without intent verification | A query converting on one device or geo context may carry no conversion signal in a different context | Verify conversion pattern across device, geo, and time-of-day before keyword promotion |
| Treating device-mismatch traffic as query irrelevance | Negative keywords do not resolve device-level landing page failures; adds negative volume without fixing root cause | Isolate device performance, then apply device bid adjustment or exclusion |

## Cross-References

- `domains/paid-media/skills/ppc-strategist` — bidding strategy, campaign architecture,
  budget allocation; this skill operates at the query sub-layer of the campaign structure
  ppc-strategist designs.
- `domains/paid-media/skills/auditor` — full-account paid media audit; invokes this skill
  for the query layer dimension of an account audit engagement.
- `domains/paid-media/skills/tracking-specialist` — parameter-stuffing events and
  conversion action misconfiguration detected during query analysis route to
  tracking-specialist for root-cause investigation.

## ADR Anchors

- **ADR-058** — domain skill tier boundary policy. This skill is `tier: domain:paid-media`
  and MUST NOT reference core or frontend skill internals directly. Cross-domain calls
  route through the CEO orchestration layer.
