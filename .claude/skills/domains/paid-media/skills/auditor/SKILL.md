---
name: auditor
description: >
  Paid-media account audit discipline: systematic evaluation of account structure,
  spend-waste detection, attribution-integrity verification, conversion-tracking
  validation, and agency-vs-internal performance benchmarking across Google Ads,
  Microsoft Ads, and Meta. Produces findings ranked by severity with quantified
  waste estimates and a 90-day remediation roadmap. Use when assessing an inherited
  account, suspecting agency mismanagement, diagnosing a performance drop, or
  evaluating pre-scaling readiness. Use when conversion tracking integrity is unknown
  before any budget increase commitment, or when attribution data diverges across
  platforms by more than 15%.
owner: Marlene Voss (Paid-Media Auditor, paid-media domain persona)
tier: domain:paid-media
scope_tags:
  - paid-media-audit
  - account-review
  - spend-waste-detection
  - attribution-integrity
  - fiduciary-diligence
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-auditor.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/ads/**"
  - "**/ad-accounts/**"
  - "**/campaigns/**"
---

# Paid-Media Auditor

## Cardinal Rule

An account that cannot answer "where did every dollar go and what did it produce?"
is not auditable — it is a liability. Attribution ambiguity, fragmented conversion
signals, and opaque agency fee structures collectively produce the appearance of
performance while concealing structural waste. The audit function exists to replace
appearance with evidence. Every finding must carry: platform, severity tier
(CRITICAL / HIGH / MEDIUM / LOW), a quantified or banded waste estimate, and a
specific remediation action. Findings without a remediation action are observations,
not audit findings, and have no place in a professional report.

## Fail-Fast Rule

Halt and escalate before completing the audit if any of the following is true:

1. Conversion tracking is broken or unmeasured on the primary conversion action —
   audit conclusions on efficiency are invalid without reliable conversion data.
2. Platform-reported conversions exceed GA4-reported sessions on the same path by
   more than 3× — strong signal of conversion duplication or pixel misfiring that
   invalidates ROAS calculations throughout.
3. Account access is view-only and change history is inaccessible — structural audit
   can proceed; spend-waste diagnosis cannot be confirmed without change-correlation.
4. The audit lookback window is under 30 days and seasonality is uncharacterized —
   expand to minimum 90 days or flag conclusions as provisional.

## When to Apply

Apply this skill when any of the following conditions is present:

- Account ownership transferred from a previous agency or internal team (full
  onboarding audit required before any budget change).
- Spend efficiency has declined for two or more consecutive 30-day periods without
  a structural cause identified in change history.
- A budget increase of 50% or more is under consideration (pre-scaling readiness
  assessment).
- An attribution methodology change is planned (baseline audit required for before/
  after comparison validity).
- Quarterly scheduled health check on a managed account (scope-limited variant
  acceptable; use full scope if last full audit exceeded 180 days).
- Agency contract is under renewal or competitive review (fiduciary diligence scope).
- A compliance review is required for a regulated vertical (healthcare, finance,
  legal — policy audit layer added to standard scope).

Do not apply this skill for campaign build tasks, ad copy production, or ongoing
optimization cycles. Those are distinct operational workflows.

## Audit Scope Definition

Audit scope is not optional and not client-negotiable on the following four axes:

**Lookback window:** Minimum 90 days. Extending to 12 months is required when
seasonality is a primary driver. Audits covering fewer than 90 days produce findings
that cannot be distinguished from short-term variance and must be labelled
provisional.

**Per-platform isolation:** Each platform (Google Ads, Microsoft Ads, Meta, TikTok,
Pinterest, LinkedIn) receives a separate audit pass. Cross-platform aggregation
occurs only at the attribution and reporting layers, never earlier. Blending
platform-native data before per-platform findings are complete conceals
platform-specific structural failures.

**Spend-tier-driven depth:** Accounts spending under $10k/month receive a
lightweight structural pass (account organization, conversion tracking, top-10
keyword quality). Accounts spending $10k–$100k/month receive the full 200-checkpoint
framework. Accounts above $100k/month add a competitive positioning layer,
impression-share forensics, and an agency-fee efficiency calculation.

**No partial audit:** A scope that excludes one or more audit dimensions (e.g.,
"just look at keywords, skip tracking") produces findings that are structurally
dependent on excluded data. If time constraints prevent full scope, document the
excluded dimensions explicitly as out-of-scope in the report cover and flag that
conclusions in dependent dimensions are provisional.

## Account Structure Review

Account structure drives Quality Score inheritance, budget allocation efficiency,
and reporting clarity. Structural deficiencies compound over time.

**Hierarchy inspection:** Review campaign → ad-set/ad-group → ad → keyword/audience
hierarchy for each platform. Flag any hierarchy that collapses two logical levels
into one (e.g., one campaign per product category containing mixed match types
alongside mixed audience targets — this merges bid logic and creative logic into a
single control unit that cannot be optimized independently).

**Nomenclature consistency:** Every campaign, ad group, and ad must follow a
documented naming schema. Absent schema: flag as MEDIUM. Naming schema present but
inconsistently applied: flag by violation count (≥20% non-compliant = HIGH).
Inconsistent nomenclature prevents reliable programmatic reporting and makes change
history correlation manual.

**Fragmentation indicators:** Flag any of the following:

- More than one active campaign targeting the same geo + audience + match-type
  combination — self-auction competition (CRITICAL).
- Ad groups containing fewer than 3 active ads per platform rotation policy —
  insufficient creative coverage for statistical learning (MEDIUM).
- Single-keyword ad groups (SKAGs) at scale on broad or phrase match — typically
  a legacy structure that inflates management overhead without corresponding
  precision benefit at current platform algorithm maturity (MEDIUM).

**Consolidation opportunities:** Identify campaigns that can be merged without
changing audience logic or bid strategy type. Calculate projected Quality Score
improvement from consolidation where data supports it. Consolidation
recommendations must include a migration sequence — consolidation executed without
a transition plan causes learning period restarts.

**Label and shared library hygiene:** Audit label usage for consistency. Audit
shared negative keyword lists for staleness — lists not updated in 90+ days are
presumed stale. Audit bid adjustments at device, geo, and daypart level for logic
consistency with campaign objectives.

## Spend Waste Detection

Spend waste is defined as budget consumed by impressions, clicks, or conversions
that carry no plausible path to the stated business objective. Waste categories:

**Impression-share lost to budget:** A campaign constrained by daily budget with
Impression Share Lost to Budget above 30% is structurally undersized for its
targeting universe. Either the budget is insufficient for the targeting scope
(increase budget or narrow targeting) or targeting is oversized for the budget
(tighten geo, match type, or audience). Flag as HIGH with a bid/budget rebalancing
recommendation.

**Bid strategy mismatch:** A manual CPC bid strategy on a conversion-objective
campaign with fewer than 30 conversions in the prior 30 days is operating below
the statistical floor required for automated bidding. Switching to Target CPA or
Target ROAS before the conversion floor is met produces erratic spend. Document
current conversion volume and flag as HIGH if auto-bidding is active below the
threshold.

**Broad-match runaway:** Pull the Search Terms Report for the trailing 90 days.
Flag any search term that (a) generated more than 5% of total spend in that period,
(b) does not contain a keyword root present in the account, and (c) has a
conversion rate below the campaign average. These are broad-match expansion terms
consuming budget without coverage intent. Quantify spend on flagged terms as the
waste estimate for this finding.

**Competitor-name spend leakage:** If the account bids on competitor brand terms,
audit conversion rate and ROAS for those terms versus non-brand. If competitor
terms have a ROAS below 1.0 and no strategic defense rationale is documented,
flag as HIGH. If competitor terms have never been reviewed for ROAS, flag the gap.

**Low-CTR ads still funded:** Any active ad with an impression count above 1,000
and a CTR below the platform/placement benchmark by more than 50% is consuming
budget on a unit with demonstrated audience signal failure. Flag by ad count with
a creative refresh recommendation.

**Dayparting and device inefficiency:** Calculate conversion rate and CPA by hour
of day and device type for the trailing 90 days. If any 4-hour block or device
type has a CPA more than 2× the campaign average and bid adjustments have not
been applied, calculate the spend attributable to the overpriced inventory as the
waste estimate.

## Attribution Integrity

Attribution integrity is the precondition for all efficiency conclusions. An account
with broken or manipulated attribution produces performance metrics that are
internally consistent but empirically false.

**Platform-vs-GA4 divergence:** For each conversion action, compare platform-
reported conversions against GA4 goal completions or GA4 events on the same date
range. Divergence below 15% is acceptable (view-through, same-session discrepancy).
Divergence of 15–40% is MEDIUM and requires investigation. Divergence above 40% is
HIGH and invalidates efficiency conclusions until resolved.

**Conversion duplication:** Identify conversion actions that fire on the same user
event via multiple tags (e.g., Google Ads tag + Google Analytics import from the
same goal, both active). Document all active conversion actions per platform and
trace each to its source event. Duplicate conversion counting inflates reported
ROAS and creates false bidding signals for automated strategies.

**Attribution window manipulation:** Compare the account's current attribution
window against industry defaults for the vertical. A 90-day click window on a
product with a 3-day purchase cycle inflates assisted conversion counts without
improving decision quality. Flag window settings that are materially longer than
the empirical purchase cycle as MEDIUM. Attribution window changes mid-period
invalidate time-series comparisons — flag any window changes in the lookback period.

**Fraudulent traffic and SIVT scrubbing:** Review Placement Reports (Display/YouTube)
for domains or apps with high impression volume and zero or near-zero conversion
rates. Flag any placement consuming more than 1% of display budget with a
conversion rate of 0 over 90 days as a potential invalid traffic sink. Calculate
spend on flagged placements. Review IP exclusion lists — an empty exclusion list
on a high-volume account is a process gap (MEDIUM).

## Conversion Tracking Validation

Conversion tracking validation is a distinct audit pass from attribution integrity
review. Attribution review examines whether reported numbers are accurate. Tracking
validation examines whether the measurement infrastructure is correctly instrumented.

**Event firing test:** For each primary conversion action, execute a live test
conversion in a controlled session and confirm that: (a) the platform tag fires
exactly once, (b) the event reaches the platform debugger without errors, and (c)
the GA4 event fires in the same session. Document pass/fail per conversion action.

**Deduplication audit:** Confirm deduplication logic is implemented for any
conversion action that can be triggered by both client-side tag and server-side
Conversions API (CAPI) / Enhanced Conversions. Absent deduplication with both
signals active = CRITICAL double-counting.

**Consent-flag propagation:** Confirm that consent mode signals (granted/denied/
pending) are propagated from the CMP to all platform tags. On Google Ads, confirm
`ad_storage` and `analytics_storage` consent states are passed. Missing consent
propagation is a compliance risk in GDPR jurisdictions and a data quality risk
everywhere — flag as HIGH.

**Offline conversion match rate:** If offline conversions are imported, review the
match rate for the trailing 90 days. A match rate below 40% indicates CRM identifier
alignment failure (phone number format, email normalization, or GCLID capture gap).
Document match rate and flag the gap tier: 40–60% = MEDIUM, below 40% = HIGH.

## Agency-vs-Internal Benchmark

The agency-vs-internal benchmark applies when the account is managed by a third-
party agency and the audit is commissioned by the account owner. The purpose is
fiduciary diligence, not adversarial critique.

**Cost-of-management vs uplift calculation:** Obtain the total agency fee (monthly
retainer + performance fees + tech-stack markups) for the trailing 12 months.
Compare against the measurable performance improvement attributable to the agency
relationship versus a documented baseline. If no baseline exists, document the
absence as a diligence gap that prevents quantified ROI assessment.

**Fee transparency audit:** Review the contract for: (a) media markup clauses
(agency purchasing media at one rate and billing at a higher rate), (b) tech-stack
fees (DSP seats, attribution tools, creative platforms) bundled into the retainer
without line-item disclosure, and (c) performance-fee structure alignment with
client-side business objectives (revenue, profit margin) rather than proxy metrics
(impressions, clicks, MQLs without downstream conversion data). Flag any markup
clause without explicit client acknowledgment as HIGH.

**Performance-fee alignment:** A performance fee tied to a metric that the agency
controls (e.g., agency-reported ROAS using the agency's attribution model) creates
a structural conflict of interest. Performance fees should be tied to metrics
verifiable by a third party (GA4, CRM revenue, or independent attribution vendor).
Document the fee structure and flag the conflict-of-interest risk if present.

**Client-side data ownership:** Confirm that the advertiser owns: (a) the Google
Ads account (not a sub-account under agency MCC without transfer rights), (b) all
conversion tags and the GTM container, (c) all audience lists, and (d) all creative
assets uploaded to the account. An agency-owned account or agency-owned audience
lists mean the client cannot leave without losing data continuity. Flag as CRITICAL
if data ownership is not fully client-side.

## Audit Report Structure

All audit outputs must conform to the following structure. Deviation requires
explicit justification in the report cover.

**Executive Summary (max 1 page):** Business-language synthesis of the audit.
States: (a) total identified waste (banded estimate, 90-day basis), (b) top-3
findings by business impact, (c) recommended 30-day priority actions, (d) overall
account health assessment (HEALTHY / AT-RISK / CRITICAL). No technical jargon
in this section.

**Findings by Severity:** All findings listed under CRITICAL / HIGH / MEDIUM / LOW
headers. Each finding includes: platform, dimension (structure / spend / attribution /
tracking / agency), description, evidence (metric, date range, specific data point),
waste estimate (quantified or banded), and recommended remediation action with
implementation effort (hours or story points).

**Quantified Waste Summary:** A single table aggregating waste estimates by dimension
and platform. Banded estimates acceptable where precise quantification requires data
not available in the audit window; document the banding rationale.

**Recommendations:** Ordered by ROI (waste elimination per implementation hour).
Each recommendation includes: owner (client-side or agency-side), dependencies,
and expected time-to-impact.

**Quick Wins:** Recommendations that can be implemented in under 2 hours with no
dependency on third-party approvals or infrastructure changes. List separately for
immediate action.

**90-Day Roadmap:** Sequenced implementation plan with week-of-month targets.
Accounts for platform learning periods — bid strategy changes require 2–4 weeks
of learning before performance conclusions are valid; sequence non-conflicting
changes in parallel where learning periods do not overlap.

## Anti-Patterns

| Anti-Pattern | Why Harmful | Correct Practice |
|---|---|---|
| Cherry-picked lookback window | Selecting a 7- or 14-day window excludes cyclical variation and inflates or deflates efficiency conclusions depending on the selected period | Use minimum 90-day window; document any deviation |
| No statistical significance test | Declaring a finding based on 50 impressions or 3 conversions produces noise as signal | Apply minimum volume thresholds (1,000 impressions for CTR findings; 30 conversions for CPA/ROAS findings) |
| Vague recommendations | "Optimize your keywords" or "review your bids" without specific action, owner, or timeline is not a recommendation | Every recommendation specifies: exact setting, platform path, expected outcome, and effort estimate |
| Ignoring tracking integrity before drawing efficiency conclusions | Reporting ROAS of 4.2× when conversion duplication is unresolved produces false confidence | Always complete tracking validation before interpreting efficiency metrics |
| Consolidating findings across platforms | Blending Google Ads and Meta data into a single ROAS figure obscures platform-specific structural failures | Maintain per-platform analysis throughout; aggregate only in the executive summary |
| Benchmarking against industry averages without vertical adjustment | "Your CTR is below average" without specifying vertical, match type, and placement type is uninformative and misleading | All benchmarks must be qualified by vertical, network, match type, and device type |
| Recommending automation before conversion floor is met | Enabling Target CPA with 8 conversions in 30 days produces erratic spend during a learning period that harms performance | Document conversion volume against platform thresholds before recommending any automated bid strategy |
| Omitting agency data ownership verification | An account where the agency owns audience lists and conversion tags cannot be transitioned cleanly to a new partner | Data ownership verification is mandatory scope on every agency-managed account audit |

## Cross-References

- `domains/paid-media/skills/ppc-strategist` — operational campaign management
  and bid strategy execution; the auditor identifies structural failures, the
  ppc-strategist executes the remediation.
- `domains/paid-media/skills/tracking-specialist` — conversion tracking
  instrumentation and GTM/GA4 implementation; for CRITICAL tracking findings,
  escalate to the tracking-specialist for remediation.
- `domains/paid-media/skills/paid-social-strategist` — Meta, TikTok, LinkedIn,
  and Pinterest channel strategy; paid-social-specific structural findings are
  best remediated in coordination with the paid-social-strategist.

## ADR Anchors

**ADR-058 (Brainstorm gate + two-pass adversarial review):** The two-pass review
discipline applies to this skill. Pass 1: collect and categorize all findings
without scoring. Pass 2: apply severity scoring and waste quantification
independently, then reconcile. Single-pass audits where findings are scored during
collection introduce confirmation bias — the first high-severity finding anchors
subsequent severity assessments upward. Two-pass separation is mandatory for
CRITICAL and HIGH findings on accounts above $10k/month spend.
