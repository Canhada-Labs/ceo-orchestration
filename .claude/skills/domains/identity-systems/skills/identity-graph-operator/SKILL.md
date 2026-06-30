---
name: identity-graph-operator
description: |
  Customer identity graph operations for marketing and customer-data
  platforms. Covers deterministic match (hashed email, hashed phone,
  known-customer-id), probabilistic match (device-graph, IP-cluster,
  behavioural-similarity), household graph construction, cookieless
  identity resolution (UID2 / RampID / ID5 / Topics API), CDP
  integration, consent propagation across LGPD / GDPR / CCPA / DMA,
  fraud-signal detection, and data clean room collaboration. Distinct
  from `core/identity-and-trust-architecture`, which covers
  cryptographic agent identity and token signing. PII-touching: all
  operations require a valid consent record. Use when building or
  auditing a customer identity layer, designing a CDP integration,
  modelling household graphs, selecting a cookieless identity
  protocol, or authoring a data clean room agreement.
owner: Valentina Osei (Identity Graph Operator, domain persona)
tier: domain:identity-systems
scope_tags:
  - identity-graph
  - deterministic-match
  - probabilistic-match
  - household-graph
  - cookieless-identity
  - cdp
  - data-clean-room
inherits: core/compliance-lgpd
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/specialized/identity-graph-operator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: identity-systems
priority: 3
risk_class: high
stack: [typescript, node]
context_budget_tokens: 800
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 5}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)identity|sso|oidc|saml"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/identity/**"
  - "**/identity-graph/**"
  - "**/cdp/**"
  - "**/consent/**"
---

# Identity Graph Operator

## Cardinal Rule

Every identity resolution decision that reaches a PII-adjacent
surface — ad targeting, personalisation, data clean room query,
household attribution — must be traceable to a consent record that
was valid at the time the decision was made. A match that cannot be
paired with a valid consent record must be treated as no match for
disclosure purposes, regardless of confidence score.

## Fail-Fast Rule

If a consent record for the target identity cannot be confirmed at
the time of resolution, **stop and return an error before writing
any link to the identity graph**. Never infer consent from
engagement history, login recency, or downstream business logic.
Consent absence is not the same as consent revocation, but neither
state authorises processing.

## When to Apply

- Designing or auditing a customer identity resolution pipeline.
- Selecting a deterministic vs. probabilistic match strategy for a
  given use case and regulatory regime.
- Modelling a household graph or sub-household identity layer.
- Choosing a cookieless identity protocol (UID2, RampID, ID5,
  Topics API, first-party authenticated traffic).
- Integrating a Customer Data Platform (CDP) with an existing
  identity spine.
- Authoring or reviewing a consent propagation workflow across
  LGPD, GDPR, CCPA, or DMA jurisdictions.
- Designing a data clean room for multi-party collaboration
  without raw-data exchange.
- Investigating synthetic-identity fraud or bot-traffic exclusion.

## PII Handling

All fields processed by this skill are treated as PII until
explicitly classified otherwise by a data-quality gate.

**Canonical PII inputs:**

| Field | Canonical form at ingest | Retention rule |
|---|---|---|
| Email address | SHA-256 hash (hex, lowercase, trimmed) | Raw email discarded immediately after hashing |
| Phone number | E.164 normalised, then SHA-256 hash | Raw phone discarded immediately after hashing |
| Device fingerprint | Opaque token; never reverse-mapped to a named user without consent | Session-scoped or consent-bounded TTL |
| Cookie ID / device ID | Pseudonymous; store only the graph-edge, not the raw cookie | Per-consent-revocation TTL |

Minimum-necessary principle applies at every stage: do not request,
store, or propagate fields not required for the specific resolution
operation in flight.

**LGPD Art. 14 — minor handling:** Any identity record associated
with a user whose age cannot be verified must default to the minor
data-handling regime. Do not merge or link minor records into
household graphs without explicit guardian consent. Cross-link to
`core/compliance-lgpd` §Minor Data Handling and
`domains/edtech/skills/student-data-privacy` §Age Verification Gate
for enforcement details.

**Consent propagation primary:** every write to the identity graph
must carry the consent-string or consent-event-id that authorises
the operation. Downstream consumers of the graph inherit the
consent scope; they do not re-derive it.

## Deterministic Match

Deterministic match assigns confidence = 1.0 when two or more
stable, verified signals agree.

**Accepted deterministic signals:**

- Hashed email (SHA-256, normalised before hashing)
- Hashed phone number (E.164, SHA-256)
- Authenticated login state (first-party session token validated
  server-side)
- Known-customer-id (CRM canonical key with authoritative source
  of record declared in the data processing registry)

**Rules:**

- Confidence = 1.0 is only valid when at least one deterministic
  signal resolves without ambiguity. Never assign 1.0 to a
  probabilistic signal regardless of score.
- Never infer a deterministic link from co-occurrence, timing, or
  shared device without an authenticated signal confirming the link.
- Field normalisation must precede hashing; normalisation logic
  must be version-pinned and auditable.
- Contradictory deterministic signals (two confirmed emails that
  hash to different values on the same canonical entity) trigger a
  mandatory split review, not a silent merge.

## Probabilistic Match

Probabilistic match produces a per-match confidence score in
[0.0, 1.0). The score is evidence, not a decision; the decision
threshold is a tunable policy parameter.

**Accepted probabilistic signals:**

- Device graph (shared device-fingerprint or cookie-id cluster)
- IP cluster (shared IP prefix, recency-weighted)
- Behavioural similarity (session-pattern vectors, frequency
  distribution)
- Cross-device co-occurrence (temporal proximity on authenticated
  sessions)

**Rules:**

- Every probabilistic match record must carry: signal sources,
  per-signal weight, composite score, and the threshold policy in
  effect at decision time.
- Threshold tuning is use-case-specific. Suggested baseline
  thresholds:

  | Use case | Min threshold | Notes |
  |---|---|---|
  | Ad frequency capping | 0.70 | False merges cause under-exposure, not privacy harm |
  | Household attribution | 0.80 | False merges affect billing accuracy |
  | Consent-derived action | Do not use | Use deterministic signals only |
  | PII disclosure | Do not use | Prohibited — deterministic only |

- Probabilistic matches must never be used for PII-disclosure
  decisions, consent derivation, fraud prosecution, or any
  operation that requires identity certainty.
- Re-score probabilistic links on a rolling basis; stale scores
  (score > configured staleness TTL without refresh) must be
  demoted to "needs-review" status.

## Household Graph

A household graph clusters identities that share a physical
dwelling for attribution and measurement purposes.

- Membership derived from deterministic or high-confidence
  probabilistic links to shared signals (device, IP, postal address).
- Sub-household individuals must remain distinct records; never
  collapse them into a single entity for any PII regulatory operation.
- A shared device is a device node with edges to each member, not a
  merged person node.
- Household is a measurement unit, not a legal entity; never use
  household aggregates for per-individual compliance decisions
  (credit, insurance, employment).
- LGPD / GDPR consent is individual: household-level consent does
  not extend to members unless each has independently consented.

## Cookieless Identity

Third-party cookie deprecation requires an explicit protocol
selection matched to the consent posture and use case.

**Protocol fit matrix:**

| Protocol | Consent requirement | Primary use case | Limitations |
|---|---|---|---|
| UID2 (Unified ID 2.0) | Explicit opt-in; hashed email as seed | Programmatic advertising, CTV | Requires publisher + DSP support; email mandatory |
| RampID (LiveRamp) | Consent via CMP or direct opt-in | Cross-publisher identity spine | Proprietary graph; data-residency scope varies by region |
| ID5 | Publisher-controlled consent signal | Open web frequency capping | Lower coverage outside premium publishers |
| Topics API | Browser-enforced; no PII transmitted | Contextual targeting | Coarse signal; Chrome-only as of v1.14 |
| First-party authenticated traffic | First-party consent (login) | Own-property personalisation | Requires login wall or registration incentive |

**Consent flag pass-through:** when a UID2 / RampID / ID5 token is
passed to a downstream activation platform, the consent-string that
authorised the token generation must travel with the token. Platforms
that cannot accept or enforce a consent-string are not eligible
activation targets.

## CDP Integration

A Customer Data Platform is an input source and activation rail,
not an identity source of record.

**Input source taxonomy:**

| Source tier | Examples | Trust level | Consent verification |
|---|---|---|---|
| First-party authenticated | Login events, purchase history, support tickets | High | Verify consent at record ingest |
| First-party anonymous | Page-view events, session analytics | Medium | Verify cookie-consent signal before linking to profile |
| Second-party partner | Data-share agreements, co-registration | Medium | Confirm contract scope; map to identity graph only within agreed fields |
| Third-party enrichment | Data brokers, modelled attributes | Low | Reject unless explicit LGPD Art. 7 legal basis documented |

**Data-quality gates at write:** completeness (hashed email or phone
required before node creation); consent-flag enforcement (no
resolvable consent event-id → quarantine partition, not live graph);
deduplication (run deterministic match before creating a new node;
duplicate tolerance target ≤ 0.1%).

**Latency targets:** real-time lookup p99 ≤ 150 ms. Batch
reconciliation must complete within the consent-revocation SLA
window so revoked identities do not appear in the next activation
cycle.

## Consent Propagation

Consent is the authorisation record; identity is the resolution
key. They must travel together.

**Jurisdiction defaults:**

| Regulation | Default posture | Legal basis for identity processing |
|---|---|---|
| LGPD (Brazil) | Opt-in for marketing; legitimate interest allowed for fraud detection | Art. 7 I (consent) or Art. 7 IX (legitimate interest) |
| GDPR (EU/EEA) | Opt-in; ePrivacy Directive for cookies | Art. 6(1)(a) consent or Art. 6(1)(f) legitimate interest |
| CCPA / CPRA (California) | Opt-out model; "Do Not Sell / Share" signal | California privacy rights; GPC signal must be honoured |
| DMA (EU) | Gatekeeper-specific obligations; no cross-context tracking without consent | Art. 5(2) — explicit consent required for combining personal data across core platform services |

**Consent-string format:** TCF v2.2 (GDPR) / LGPD Consent Framework
strings stored alongside the identity graph edge they authorise.
Consent strings are immutable; revocation creates a new event,
it does not mutate the original string.

**Revoke-propagation SLA:** graph edge suppressed within 24 h of
revocation event; downstream activation platforms updated within
72 h or platform SLA, whichever is shorter. Audit record of
revocation and propagation confirmation retained for 5 years
(LGPD Art. 37 / GDPR Art. 30).

## Fraud Detection

Identity graph anomaly detection is a defensive signal, not a
prosecution tool.

**Accepted fraud signals:** synthetic-identity (zero deterministic
signals + high-velocity creation), bot-traffic (inhuman session
patterns — exclude from merges, not from logs), cross-account-graph
anomaly (single device/IP cluster linked to abnormally many distinct
nodes in a short window).

**Rules:**

- Fraud flags are advisory labels, not deletions; deletion requires
  a data-subject erasure request or legal hold decision.
- A node labelled as fraud candidate must be reviewable before any
  consequential action (account suspension, payment block).
- Fraud model outputs are probabilistic; apply the same threshold
  discipline as Probabilistic Match; never use for identity certainty.

## Data Clean Room

A data clean room enables multi-party data collaboration without
exchanging raw personal data.

Each party contributes pseudonymised or hashed match keys; only
aggregated outputs cross the clean room boundary. Minimum
aggregation threshold: k ≥ 5 (k ≥ 10 for sensitive categories);
exact k documented in the DPA. If the operator supports
differential privacy (LiveRamp Habu, AWS Clean Rooms, Snowflake DP
mode), document epsilon value and per-query budget in the DPA.

**Platform selection criteria:**

| Platform | Hosted / self-managed | DP support | LGPD residency |
|---|---|---|---|
| LiveRamp Habu | Hosted (multi-cloud) | Configurable | Requires data-residency contract addendum |
| AWS Clean Rooms | Hosted (AWS VPC isolation) | Limited (analysis rules) | São Paulo region (sa-east-1) available |
| Snowflake Clean Rooms | Hosted (Snowflake account) | Preview (DP mode) | Brazil region available; verify account tier |
| Self-managed (open-source) | Self-managed | Custom | Full control; higher operational burden |

**DPA requirements:** enumerate permitted query types (ad hoc
expansion requires amendment); log all queries with participant
attribution; define data-deletion timeline and propagation
confirmation at agreement termination.

## Anti-Patterns

| Anti-pattern | Risk | Correct approach |
|---|---|---|
| Using probabilistic match for PII disclosure | Discloses personal data to wrong identity; LGPD / GDPR violation | Use deterministic signals only for any PII-adjacent disclosure |
| Missing consent propagation to activation platforms | Activates suppressed identities; enforcement action risk | Carry consent-string with every activation payload |
| Storing raw email after hashing | Unnecessary PII retention; breach surface expansion | Discard raw email at ingest boundary; retain hash only |
| Collapsing household individuals into a single node | Attributes actions to wrong person; incorrect consent association | Model each individual as a distinct node; household is an edge |
| No revoke-propagation SLA | Revoked consent continues to drive activation | Define and enforce 24h graph + 72h downstream SLA |
| Linking minor records into household graph without guardian consent | LGPD Art. 14 violation | Default to minor regime; require verified guardian consent before any household link |
| Third-party enrichment without documented legal basis | Unlawful processing (LGPD Art. 7) | Reject third-party data unless Art. 7 legal basis is on file |

## Cross-References

- `core/compliance-lgpd` — LGPD Art. 7 legal bases, data subject
  rights, consent management, and breach notification procedures.
- `core/identity-and-trust-architecture` — cryptographic agent
  identity, JWT signing, token rotation, and VETO-floor agent
  governance. Distinct domain: that skill governs who the agent
  is; this skill governs who the customer is.
- `domains/paid-media/skills/tracking-specialist` — upstream
  signals that feed the identity graph (pixel events, UTM
  attribution, cookie consent signals).
- `domains/edtech/skills/student-data-privacy` — minor data
  handling and age-verification gate; cross-apply when any
  identity graph operation may touch records of users under 18.

## ADR Anchors

- ADR-058 — clean room minimum aggregation threshold and DP budget
  documentation requirements.
