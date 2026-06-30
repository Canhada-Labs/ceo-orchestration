---
name: tracking-specialist
description: >
  Ad-tracking and measurement engineering discipline covering pixel
  deployment, GA4 / Meta CAPI / TikTok Events API server-side tracking,
  consent-mode v2, cross-domain identity stitching, conversion-value
  modeling, and data-quality assurance. Produces tracking architectures
  grounded in event taxonomy, PII-safe signal collection, and dual-deploy
  redundancy rather than platform self-reporting assumptions. Use when:
  designing or auditing a pixel deployment plan, diagnosing conversion-count
  discrepancies between ad platforms and analytics, implementing server-side
  tagging on GA4 Measurement Protocol, Meta CAPI, or TikTok Events API,
  configuring consent-mode v2 with per-region defaults, building cross-domain
  linker or identity-graph stitching, modeling conversion value with LTV or
  margin weighting, or establishing event-volume alarms and dedup-audit cadences.
owner: Marlena Voss (Tracking Specialist, domain persona)
tier: domain:paid-media
scope_tags: [tracking, server-side-tagging, ga4, meta-capi, consent-mode, conversion-modeling, data-quality]
inspired_by:
  - source: msitarzewski/agency-agents/paid-media/paid-media-tracking-specialist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/tracking/**"
  - "**/pixels/**"
  - "**/gtm/**"
  - "**/capi/**"
---

# Tracking Specialist

## Cardinal Rule

An untested pixel is a guess; an unmonitored pixel is a guess that
decays into broken without notice. Every conversion signal feeding a
bidding algorithm MUST be verified at the event level — not at the
campaign summary level — before it is treated as authoritative. A 5%
mismatch between platform-reported conversions and CRM ground truth
does not round to acceptable; it compounds into miscalibrated bids,
distorted attribution models, and budget misallocation that accumulates
silently. Measurement is not a launch task; it is an ongoing operational
discipline with defined alarm thresholds, scheduled dedup audits, and a
documented escalation path when signal quality degrades.

---

## Fail-Fast Rule

A pixel deployment MUST NOT proceed to production if the following gates
have not passed: (1) the event taxonomy is fully specified before any
tag fires — parameter schema, dedup key assignment, and value-currency
pairs documented for every tracked event; (2) PII redaction has been
confirmed at the source — no hashed or unhashed personally identifiable
data may travel in URL parameters, `document.referrer`, or custom
dimensions without explicit redaction review; (3) a QA protocol has been
executed in a staging environment using the platform's native debug tool
(GA4 DebugView, Meta Events Manager test mode, TikTok Event Tester) AND
an independent network-request inspection; (4) deduplication logic via
`event_id` has been implemented and verified when both browser-side and
server-side paths fire the same event. If any gate fails, deployment is
blocked until the condition is remediated.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing a pixel deployment plan for a new site launch, redesign, or
  major campaign infrastructure build.
- Diagnosing conversion-count discrepancies between ad platforms (GA4,
  Google Ads, Meta Ads Manager, TikTok Ads) and CRM or backend records.
- Implementing or migrating to server-side tracking via GA4 Measurement
  Protocol, Meta Conversions API, or TikTok Events API.
- Configuring consent-mode v2 signals — `ad_user_data`,
  `ad_personalization` — with per-region defaults for LGPD, GDPR, CCPA,
  and DMA jurisdictions.
- Auditing an existing tag container for PII leakage, consent gaps,
  duplicate event fires, or missing dedup keys.
- Building cross-domain tracking via linker parameters or first-party
  cookie domain configuration.
- Modeling conversion value with revenue, margin, LTV-weighted, or
  offline-upload enrichment.
- Establishing event-volume monitoring, trend-anomaly alarms, and browser-
  versus-server comparison baselines.

---

## Pixel Deployment Discipline

Pixel deployment without a preceding taxonomy document produces
unmeasurable technical debt. The taxonomy MUST be established before
any tag fires.

**Event taxonomy before deployment:**

For every tracked event, the taxonomy document MUST specify: event name
(snake_case, platform-canonical where applicable); required and optional
parameters with data types; the dedup key field (`event_id` or platform
equivalent) and its generation method; currency and value fields with
units; the trigger condition and data layer source; and the responsible
tag-management container workspace.

Events not present in the taxonomy document MUST NOT be deployed.
Taxonomy additions require a documented change record referencing the
campaign or product requirement that motivated the addition.

**PII redaction at source:**

PII — email addresses, phone numbers, full names, government identifiers
— MUST NOT appear in plaintext in tag payloads, URL parameters,
`document.referrer`, or GTM variables. When enhanced-conversion or CAPI
matching requires hashed PII, hashing MUST occur server-side or in a
trusted container execution environment, never in client-side JavaScript
that exposes the pre-hash value to the network layer. SHA-256 with
normalization (lowercase, trimmed) is the platform-standard hash
function; do not substitute MD5 or SHA-1.

**Deduplication via event_id:**

When both browser-side and server-side paths fire the same event, the
same `event_id` value MUST be present in both payloads. The `event_id`
MUST be generated once — in the data layer push or server-side event
constructor — and passed through to both paths. Generating independent
random IDs per path produces double-counting that platform dedup logic
cannot resolve.

**No deployment without QA:**

QA is a blocking gate, not a post-deployment check. QA MUST cover:
(a) native platform debug tool confirmation of event receipt with correct
parameters; (b) network-request inspection to confirm no PII in
plaintext; (c) consent-off state test — with consent denied, no tracking
tags MUST fire; (d) cross-browser smoke test for at minimum Chrome and
Safari (ITP behavior diverges).

---

## Server-Side Tracking

Server-side tracking is mandatory — not advisory — in three conditions:
(1) the conversion event involves sensitive transaction data (financial,
health, regulated); (2) client-side signal loss due to browser
restrictions (Safari ITP, Firefox ETP) exceeds 15% of measured events
in a 30-day baseline; (3) a compliance review has flagged client-side
third-party cookies as non-compliant with the applicable privacy regime.

**GA4 Measurement Protocol:**

The Measurement Protocol sends events directly from a trusted server to
the GA4 collection endpoint using the API secret and measurement ID.
Use cases: purchase confirmation events where the authoritative source
is the backend transaction record; offline conversion imports; server-
to-server enrichment with CRM data unavailable client-side. Limitations:
Measurement Protocol events do not participate in session stitching
unless `client_id` and `session_id` are forwarded from the client-side
cookie; always forward both. Measurement Protocol events are not
real-time in DebugView; use the `debug_mode: true` parameter for QA.

**Meta Conversions API (CAPI):**

Meta CAPI sends events from server or cloud to the Meta Graph API
endpoint. CAPI is mandatory when: campaign objectives include
purchase or lead events and iOS 14.5+ signal loss has been confirmed
above 20% in Event Match Quality diagnostics; or when the account
operates under LGPD or GDPR and requires server-side consent signal
propagation. Event Match Quality (EMQ) score below 6.0 MUST trigger
a remediation review — common causes are missing `fbp`/`fbc` cookie
passthrough, missing hashed email, and incorrect event dedup timing.
Dual-deploy (browser Pixel + CAPI for the same event) is the
recommended redundancy model; dedup via matching `event_id` values
is required, not optional.

**TikTok Events API:**

TikTok Events API (server-side) is the mirror of the browser Pixel for
environments where ITP/ETP signal loss is material or where transaction
events require server authoritative data. The API requires: `pixel_code`,
`event_name` (TikTok canonical names), `timestamp` (ISO 8601 UTC),
`context.user` hashed identifiers (`sha256_email`, `sha256_phone`),
and `event_id` for dedup. Dual-deploy with browser Pixel and Events API
requires matching `event_id`; TikTok dedup is event-name scoped, not
account-scoped, so `event_id` uniqueness within event-name namespace is
sufficient. EMQ equivalent is TikTok's "Match Rate" in Events Manager.

**First-party versus third-party cookie context:**

Server-side tagging using a first-party subdomain (e.g.,
`collect.example.com`) sets cookies in a first-party context, bypassing
ITP lifetime caps on third-party cookies. This is the primary mechanism
for extending `_fbp`, `_ga`, and `ttclid` cookie persistence. The
server-side container must NOT set cookies for domains other than the
publisher's own registered domain; doing so reverts to third-party
context and negates the ITP mitigation.

**Signal redundancy via dual-deploy:**

Dual-deploy — parallel browser-side and server-side event firing —
provides redundancy against client-side signal loss without requiring
full migration. The browser path fires immediately on user action
(lower latency, participates in session stitching); the server path
fires on backend confirmation (authoritative value, unaffected by
ad-blockers). Both paths MUST carry the same `event_id`. Volume
reconciliation between browser and server counts must be part of the
weekly data-quality review.

---

## Consent Mode

Consent mode is the mechanism by which measurement and personalization
tags respect user consent decisions without requiring tag blocking.
Consent mode v2 introduced two additional signals that MUST be
implemented for compliance with DMA (Digital Markets Act) requirements
and are recommended for LGPD and GDPR.

**v2 schema:**

| Signal                 | Scope                                                      |
|------------------------|------------------------------------------------------------|
| `ad_storage`           | Cookie-based ad targeting and remarketing storage          |
| `analytics_storage`    | Cookie-based analytics measurement storage                 |
| `ad_user_data`         | Sending user data to Google for ad purposes                |
| `ad_personalization`   | Personalised advertising (remarketing audiences)           |
| `functionality_storage`| Cookies required for site functionality                    |
| `security_storage`     | Cookies required for security and fraud detection          |

**Granularity and v2 minimum requirements:**

`ad_user_data` and `ad_personalization` are the v2-new signals.
Implementations that set only `ad_storage` and `analytics_storage`
without propagating `ad_user_data` and `ad_personalization` are
non-compliant with DMA obligations for Google's designated services.
All four ad-related signals MUST be updated simultaneously when consent
state changes; partial updates produce undefined platform behavior.

**Consent flag propagation server-side:**

Server-side containers MUST receive and forward consent signals from
the client. The consent payload from the browser (typically from the
CMP dataLayer push) MUST be serialized and passed as a query parameter
or request header to the server container on each event call.
Server-side tags MUST NOT fire if the forwarded consent state denies
`ad_storage` for ad tags or `analytics_storage` for analytics tags.

**Per-region defaults:**

| Region             | Default state (pre-consent) | Notes                                            |
|--------------------|------------------------------|--------------------------------------------------|
| EEA / UK (GDPR)    | `denied` for all ad signals  | Explicit opt-in required before any signal fires |
| Brazil (LGPD)      | `denied` for ad signals      | Legitimate interest basis does not apply to behavioral targeting |
| United States      | `granted` default permitted  | CCPA opt-out model; flip to `denied` on GPC signal |
| DMA designated     | `denied`; v2 signals mandatory | `ad_user_data` + `ad_personalization` required  |
| Other jurisdictions| Consult legal; default `denied` is safest posture | —                        |

Default state must be set in the tag container initialization before
any user interaction; do not rely on CMP latency to block tags.

---

## Cross-Domain Stitching

Cross-domain tracking preserves session continuity and attribution when
a user journey spans two or more distinct registered domains (e.g.,
a marketing site and a checkout domain).

**Linker parameter handoff:**

GA4 cross-domain tracking appends a `_gl` parameter to outbound links
and form actions. The receiving domain extracts `client_id` and
`session_id` from the linker parameter, overriding any existing cookie
values to maintain session continuity. Configuration requires: listing
all destination domains in the GA4 tag's cross-domain settings; enabling
auto-linking for outbound links; verifying that the receiving page does
not strip query parameters before GA4 fires.

**Cookie-domain configuration:**

The `_ga` cookie MUST be scoped to the top-level registered domain
(`.example.com`), not to the hostname (`www.example.com`), to be
readable across subdomains. Misconfigured cookie domain produces
phantom new sessions for users navigating between subdomains on the
same property. Audit cookie-domain scope with browser DevTools before
any cross-domain or cross-subdomain measurement claim is accepted.

**Identity graph for logged-in users:**

For authenticated user journeys, the server-side identity graph provides
deterministic cross-domain stitching without reliance on linker
parameters or third-party cookies. Map the authenticated `user_id`
(a non-PII stable internal identifier) to `client_id` at login time;
propagate `user_id` in all server-side event payloads. This provides
consistent attribution across device switches and browser cookie resets.

**Never use email-as-key in URL:**

Email addresses MUST NOT appear in URL parameters used for cross-domain
identity handoff, even in hashed form. URL parameters are logged in
server access logs, browser history, and referrer headers propagated
to third-party resources. If deterministic cross-domain identity is
required before authentication, use a short-lived, server-issued opaque
token with a TTL of ≤10 minutes, invalidated after first use.

---

## Conversion Value Modeling

Conversion value modeling replaces nominal event counts with
economically meaningful signals that better calibrate automated bidding
toward business outcomes.

**Revenue, margin, and LTV-weighted value:**

Revenue-based value (transaction amount) is the baseline. Margin-based
value adjusts revenue by product-category gross margin to prevent
bidding algorithms from optimizing toward high-revenue but low-margin
SKUs. LTV-modeled value multiplies the transaction by a cohort-level
predicted lifetime value multiplier, directing spend toward customer
segments with demonstrated retention. All three value models MUST
be documented with their derivation formula and refresh cadence; stale
LTV multipliers (older than 90 days without recalibration) MUST be
flagged in the data-quality review.

**Offline conversion uploads:**

Offline conversions (CRM close-won, phone sale, in-store transaction)
MUST be uploaded via platform APIs — Google Ads Enhanced Conversions for
Leads API, Meta Offline Conversions API — with the original click
identifier (`gclid`, `fbclid`) preserved in the CRM record at lead-
capture time. Upload cadence MUST be within 24 hours of conversion event
to remain within the attribution window for the bidding algorithm.
GCLID matching rate below 80% requires investigation; common causes are
CRM identifier field truncation, URL-parameter stripping by landing page
redirects, and delayed first-page-load tag fire.

**SKAdNetwork conversion-value schema for iOS:**

For iOS app campaigns, SKAdNetwork limits post-install measurement to a
6-bit conversion value (0–63). The conversion-value schema MUST map
the 64 possible values to distinct user actions or revenue bands,
prioritizing the highest-value signals in the upper range. Schema design
MUST account for: first meaningful action within the measurement window
(typically 24–72 hours); revenue tiering aligned to LTV segments;
and fine/coarse value hierarchy introduced in SKAdNetwork 4.0 for
larger install cohorts. Schema changes require a full regression test
against historical install cohorts before deployment.

---

## Data Quality Assurance

Data quality is not a one-time launch check; it is a recurring
operational discipline with defined thresholds, alarm mechanisms,
and audit cadences.

**Event-volume alarms:**

For each tracked conversion event, establish a rolling 7-day baseline
volume. Alarm thresholds: WARNING at ±20% deviation from baseline;
CRITICAL at ±40% deviation or total event count of zero for any 4-hour
window during campaign-active hours. Alarms MUST route to a named
owner, not a shared inbox; unacknowledged CRITICAL alarms escalate to
campaign pause within 2 hours.

**Trend-anomaly detection:**

Week-over-week trend deviation above 30% in event volume or conversion
rate MUST trigger a root-cause investigation before the signal is used
in optimization decisions. Seasonal patterns MUST be documented and
annotated in the analytics view so that expected seasonal variation is
not misclassified as a tracking failure.

**Browser-versus-server comparison:**

For dual-deploy deployments, the ratio of browser-path events to
server-path events MUST be monitored continuously. The expected ratio
depends on the estimated client-side signal-loss rate; deviations of
more than 15 percentage points from baseline MUST be investigated.
A browser count significantly exceeding the server count suggests
server-path failures; a server count significantly exceeding the browser
count suggests dedup-logic failures producing double-count on the server.

**Dedup audit cadence:**

Deduplication effectiveness MUST be audited monthly. Audit method:
pull event-level logs for a 7-day window; count events with duplicate
`event_id` values across browser and server paths; dedup failure rate
above 2% requires immediate fix. For Meta CAPI, review the "Deduplicated
Events" metric in Events Manager diagnostics; a deduplicated rate above
5% indicates `event_id` generation or transmission failures.

**Success thresholds:**

| Metric                                  | Minimum acceptable | Strong signal |
|-----------------------------------------|--------------------|---------------|
| Platform-vs-analytics discrepancy       | <5%                | <3%           |
| Enhanced-conversion / CAPI match rate   | ≥65%               | ≥75%          |
| CAPI dedup failure rate                 | <5%                | <2%           |
| GCLID offline-upload match rate         | ≥80%               | ≥90%          |
| Consent-mode tag compliance             | 100%               | 100%          |
| Event-volume alarm acknowledgment       | ≤2 h for CRITICAL  | ≤30 min       |

---

## Anti-patterns

| Anti-pattern                          | Failure mode                                                                    | Correct behaviour                                                               |
|---------------------------------------|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| PII in pixel payload                  | Email, phone, or name in plaintext in tag parameters or URL; regulatory exposure | Hash server-side (SHA-256 normalized); never expose pre-hash value client-side  |
| No consent gating                     | Tags fire before consent decision; GDPR/LGPD/DMA violation                     | Default all ad signals to `denied`; fire only on explicit opt-in CMP signal    |
| Single-source measurement             | Platform self-reporting trusted without independent verification                | Cross-reference ad platform, analytics, and CRM on a defined weekly cadence    |
| No QA cadence                         | Tracking regression accumulates silently; discovered weeks later via budget waste | Monthly dedup audit + event-volume alarms + post-deploy regression checklist   |
| Duplicate `event_id` per path         | Dedup fails; double-counting corrupts conversion totals and bid calibration     | Generate `event_id` once in data layer; forward same value to all downstream paths |
| URL-parameter email for cross-domain  | PII exposed in server logs, referrer headers, and browser history               | Use short-lived server-issued opaque token; TTL ≤10 min, single-use            |
| Stale LTV multipliers                 | Bidding algorithm optimizes toward historical cohort value, not current         | Recalibrate LTV multipliers on a maximum 90-day cadence; flag stale values in QA |
| Missing `client_id` in Measurement Protocol | Server events create phantom new users; session metrics destroyed          | Forward `client_id` and `session_id` from client cookie on every MP event     |

---

## Cross-References

- `domains/paid-media/skills/ppc-strategist` — Google Ads conversion
  action hierarchy, enhanced conversions configuration, GCLID lifecycle
  management, and offline conversion import integration with paid search
  campaigns.
- `domains/paid-media/skills/paid-social-strategist` — Meta Pixel and
  CAPI event strategy, TikTok Events API for paid social campaigns,
  attribution-window policy for social conversion events.
- `core/compliance-lgpd` — LGPD Article 7 lawful bases for tracking,
  consent collection requirements, data-subject rights obligations
  relevant to pixel and identity-graph data, and DPA notification
  procedures for measurement incidents involving personal data.

---

## ADR Anchors

- **ADR-058** — Creative authorship and structural-inspiration licensing
  policy; governs `inspired_by` attribution requirements for domain skill
  files derived from upstream open-source agent corpora.
