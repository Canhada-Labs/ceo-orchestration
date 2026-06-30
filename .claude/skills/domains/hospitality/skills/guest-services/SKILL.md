---
name: guest-services
description: |
  Operating doctrine for hospitality guest services across hotel, vacation rental,
  and restaurant operations — covering check-in and check-out flow, complaint
  resolution, special-request fulfillment, multi-channel communication, online
  review management, and service recovery. Regional norms are encoded for the
  Middle East, Europe, Asia-Pacific, and the Americas. Use when executing
  pre-arrival messaging sequences, triaging and resolving in-stay complaints,
  determining compensation tier for service failures, drafting review responses
  on Google, TripAdvisor, Booking, Airbnb, or Yelp, or when evaluating whether
  a guest request falls within commitment range or best-effort range.
owner: Sofia Carvalho (Guest Services Manager, domain persona)
tier: domain:hospitality
scope_tags: [hospitality, guest-services, complaint-resolution, online-reputation, multi-channel-comms, service-recovery]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/hospitality-guest-services.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: hospitality
priority: 8
risk_class: low
stack: []
context_budget_tokens: 400
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
  - "**/guests/**"
  - "**/reservations/**"
  - "**/check-in/**"
  - "**/reviews/**"
---

# Guest Services

Hospitality operations span a narrow window — from the moment a reservation is
confirmed to the moment a post-stay review is published — in which every touchpoint
either compounds trust or erodes it. This skill is the operating doctrine for that
arc: check-in discipline, complaint resolution sequencing, request fulfillment
boundaries, channel hygiene, review response protocol, service recovery
compensation, and cultural calibration across four major regions.

The skill is property-type agnostic. It applies to full-service hotels, boutique
properties, vacation rentals, and restaurant operations. Scale and brand affiliation
do not change the underlying principles — only the thresholds and escalation paths
differ.

## Cardinal Rule

A guest's complaint is the lowest-cost moment of brand loyalty acquisition the
hotel will ever buy; treating it as a cost is treating loyalty as a cost. The
complaint frame governs every section of this skill: the goal of complaint
resolution is not damage containment — it is trust reconstruction, which, when
executed correctly, produces higher retention than an uneventful stay.

## Fail-Fast Rule

Stop and escalate to the duty manager before proceeding if any of the following
conditions are true:

- The guest discloses a safety incident — injury, illness, security concern, or
  evacuation scenario. Safety takes precedence over all service workflows.
- The complaint involves an allegation of staff misconduct or discriminatory
  treatment. Treat as an HR and legal matter immediately; do not attempt service
  recovery without management involvement.
- A guest requests compensation that exceeds the local authority threshold (defined
  per property) without manager approval.
- A third party — not the reservation holder — demands access to room assignment,
  folio, or stay details. Privacy breach risk; do not disclose.
- A review response would require revealing PII (room number, length of stay,
  billing dispute detail) to the public. Draft and hold for manager approval instead.

Fail-fast does not mean refuse assistance — it means halt the current workflow,
document the trigger condition, and re-enter only after the condition is resolved
and the appropriate authority has acknowledged.

## When to Apply

Apply this skill when:

- Executing the pre-arrival messaging sequence (48-hour and 24-hour touchpoints).
- Managing check-in protocol including loyalty recognition, room assignment, and
  special-request confirmation.
- Receiving, triaging, and resolving an in-stay complaint within the 4-hour first
  response window.
- Fulfilling or declining a special request and communicating the distinction
  between commitment and best-effort.
- Responding to a post-stay online review on any platform.
- Determining compensation tier for a service failure under the recovery matrix.
- Adapting communication style or protocol to a regional guest segment (ME, EU,
  APAC, Americas).
- Handling a food allergy or dietary restriction declaration at any point in the
  guest journey.

Do not apply this skill for revenue management decisions, rate-setting, inventory
allocation, OTA commission negotiation, or HR performance management — those are
out of scope.

## Check-In and Check-Out Flow

### Pre-Stay Messaging

Send two touchpoints per reservation: a 48-hour message and a 24-hour confirmation.
The 48-hour message confirms arrival details, surfaces online check-in or digital
key enrollment, and invites the guest to update special requests. The 24-hour
message is brief: a reminder of check-in window and a single-sentence invitation
to contact the team.

Neither message is a marketing vehicle. Do not upsell packages or promote F&B
outlets in pre-arrival messaging unless the guest has opted into promotional
communications. The goal is to reduce day-of friction, not to generate ancillary
revenue.

### Arrival Window

The standard check-in window begins at the posted time. Early check-in is
available only when a room has been inspected and cleared. Never promise early
check-in as a given — communicate it as a confirmed outcome once the room is
ready, or as a best-effort if the room is still being prepared.

When the room is not ready at the guest's arrival, the handoff sequence is:

1. Acknowledge the wait without minimising it.
2. State the estimated ready time as a range, not a point — "between 2:00 and
   2:30" is more accurate and more trusted than "2:00."
3. Offer a concrete alternative: luggage storage plus access to a lounge, F&B
   outlet, or common space.
4. Initiate a proactive contact — by phone or SMS — the moment the room clears.
   Never make the guest return to the desk to ask again.

### Room-Ready Protocol

Before releasing a room to the front desk for assignment, the room-ready checklist
must be complete: housekeeping sign-off, maintenance clearance for any flagged
items, special-request items placed (cot, allergen-free bedding, accessibility
equipment), and loyalty amenity prepared if applicable. A room released without
complete sign-off is not ready.

### Late Checkout Policy

Late checkout is available based on occupancy. Communicate the policy at check-in
as a proactive offer, not only when the guest asks. The response sequence:

- If late checkout is available at no charge for the loyalty tier: confirm it
  immediately and note it on the folio.
- If late checkout is available at a charge: quote the rate and give the guest
  time to decide — do not pressure.
- If late checkout is not available: offer the next best alternative (luggage
  storage, access to lounge or gym until departure).

Never improvise a late checkout policy outside the property's defined matrix.
Inconsistent application generates negative reviews and loyalty member complaints.

## Complaint Resolution Frame

The complaint resolution sequence is: acknowledge → empathise → fact-find →
action → follow-up → record. Each step is mandatory. Skipping fact-finding in
favor of an immediate remedy risks resolving the wrong problem. Skipping follow-up
after a resolution is the most common cause of a resolved complaint becoming a
negative review.

**Timing standard:** first response within 4 hours of complaint receipt, regardless
of channel. For in-person or phone complaints, first response is immediate. For
complaints submitted via OTA messaging or property app, the 4-hour window applies
from the timestamp of receipt, not from when the next shift begins.

**Language standard:** never use "policy doesn't allow" as a closing response.
Policy is an internal constraint; the guest does not experience policy as a
rationale — they experience it as refusal. If a request falls outside policy,
describe what is possible, not what is blocked.

**Documentation:** every complaint must be recorded regardless of how it was
resolved. The record includes: guest identifier, room or table, nature of
complaint, time reported, time resolved, action taken, compensation provided, and
follow-up status. Undocumented complaints are invisible to operations management
and cannot be used to identify systemic issues.

## Special-Request Fulfillment

### Request Triage

Classify every special request at intake as one of three types:

- **Operational standard:** requests the property fulfills as a matter of routine
  (extra pillows, specific floor, away from elevator). Confirm as committed.
- **Best-effort:** requests subject to availability or third-party dependency
  (specific room number, early check-in, adjoining rooms). Communicate explicitly
  as best-effort, not as a promise.
- **Out of scope:** requests the property cannot fulfill — either because they
  require resources not available on-property or because they raise a compliance
  or safety concern. Decline clearly and offer the nearest alternative.

### Capability Gate

Before committing to a special request, verify the capability exists in the current
inventory. A commitment that cannot be honored at check-in is worse than a
best-effort disclosure at booking. The gate question is: "Can we confirm this
regardless of occupancy and staffing conditions on the arrival date?" If the
answer is no, it is best-effort.

### Commitment vs. Best-Effort

Communicate the distinction explicitly at the time of the request, not at check-in.
The framing: "We have noted your preference for a high-floor room. We cannot
guarantee it in advance, but we will assign the best available match on your
arrival date." This sets accurate expectations and eliminates the gap between what
the guest heard and what the property committed to.

Never overpromise. An overpromise that fails at check-in produces a complaint
that requires service recovery — consuming more staff time and compensation cost
than the original honest disclosure would have.

## Multi-Channel Communication

### Channel Discipline

Guests communicate through phone, SMS, WhatsApp, OTA messaging platforms (Booking,
Expedia, Airbnb), and property apps. Channel selection should follow guest
preference, not operational convenience. If a guest initiates on WhatsApp, respond
on WhatsApp — do not redirect to a property-preferred channel unless a legitimate
reason exists (e.g., a resolution requires a signed document).

### Channel-Specific Protocols

**Phone:** the highest-urgency channel. Answer within three rings during business
hours. After-hours calls route to a staffed overnight desk, not to voicemail.
Complaints communicated by phone require a verbal resolution and a written
follow-up via the guest's preferred messaging channel within 2 hours.

**SMS and WhatsApp:** acceptable for confirmation, status updates, and non-urgent
requests. Not acceptable for complaint resolution of more than minor severity —
escalate to phone or in-person for moderate and major complaints. PII transmitted
via SMS or WhatsApp must be limited to what is necessary for the interaction; do
not send folio details, room numbers, or passport-related information via
unencrypted messaging channels.

**OTA messaging:** responses on OTA platforms are visible to the platform and may
influence platform ranking. Respond within the platform's response-time window —
Booking.com and Airbnb publish response-rate metrics that affect visibility. Never
move a complaint off an OTA platform by telling the guest to "contact us directly"
as the first step; handle it within the platform first, then offer a direct channel
for follow-up.

**Property app:** highest auditability. All messages are logged within the PMS.
Preferred channel for billing clarifications and documented special requests.

### PII Handling Per Channel

Guest PII — including room assignment, stay dates, folio details, and identity
documents — must not be transmitted via public or unencrypted channels. Phone and
property app are the acceptable channels for PII transmission. SMS and WhatsApp
are acceptable for non-sensitive confirmations only. OTA messaging platforms have
their own data handling terms; do not send payment data or government ID information
through OTA messaging interfaces.

## Online Review Management

### Response Cadence by Platform

| Platform | Response Window | Notes |
|---|---|---|
| Google | 48 hours | Indexed by search; high visibility |
| TripAdvisor | 48 hours | Management response shown alongside review |
| Booking.com | 24 hours | Affects Booking.com score visibility |
| Airbnb | 14 days | Host response period before review becomes final |
| Yelp | 72 hours | Community visibility; business response is public |

These are targets, not minimums. Faster is better. Reviews that receive no
response within the window are perceived as dismissal by future readers.

### Response Principles

Respond to every review — positive and negative. A positive review with no
response is a missed trust signal. A negative review with no response is a
publicly visible abandonment.

For negative reviews, the response structure is: acknowledge the specific
experience described → express genuine regret without a generic apology phrase →
state one concrete corrective action that was taken or is being taken → invite
direct contact. The response must not:

- Argue with the guest's account of events, even if the account is factually
  incomplete or inaccurate.
- Reveal any PII in the public response (room number, stay dates, billing
  figures, identity of other staff).
- Offer compensation or discounts publicly — this invites gaming and establishes
  precedent that is visible to all future reviewers.
- Reference internal operational details (staffing levels, renovation schedules,
  third-party vendor issues) in a way that shifts responsibility externally.

**Defamation vs. criticism:** criticism of service quality, however harsh, is
the guest's right and does not constitute defamation. Defamation requires
demonstrably false statements of fact causing reputational harm. Do not escalate
to legal review based solely on a negative review. Escalate only if the review
contains provably false factual claims (dates, names, events) that the property
can document as false. Even then, the recommended first step is direct outreach
to the guest, not a legal response.

## Service Recovery Protocol

### Compensation Tier Matrix

| Severity | Definition | Standard Recovery |
|---|---|---|
| Minor | Single-item service gap with no lasting impact (housekeeping timing, amenity missing at arrival) | Sincere apology + small amenity delivery or loyalty points equivalent to one ancillary transaction |
| Moderate | Multi-element failure or a failure that affected the guest's plans (noise, billing error, missed special request) | Apology + room amenity + loyalty points or discount on current stay |
| Major | Failure that materially degraded the stay (maintenance issue lasting multiple hours, F&B illness, room not ready for extended period) | Apology + significant compensation (partial or full night comp, or equivalent points) + manager follow-up call |
| Severe | Failure resulting in guest relocation, safety incident response, or demonstrable harm | Apology + comp night or full stay + general manager personal contact + written acknowledgment |

The matrix defines ranges, not fixed amounts. The duty manager approves all
Major and Severe compensation. Front-desk authority covers Minor and Moderate
tiers within the pre-approved property limits.

### Written vs. Goodwill

Written compensation (folio credits, confirmed discount codes, loyalty point
additions) creates an auditable record and a clear guest expectation. Goodwill
gestures (amenity delivery, upgraded F&B, room change) do not generate a paper
trail but can be more immediately effective for emotional recovery.

Use written compensation when the failure has a quantifiable financial impact on
the guest or when the guest has asked for it. Use goodwill gestures first for
in-stay complaints where speed of response is more important than the size of
the gesture. The two are not mutually exclusive.

### Legal Liability Awareness

Service recovery is not a legal settlement. Compensation offered in service
recovery does not constitute an admission of liability for incidents involving
personal injury, property damage, or illness. For incidents that may generate
a legal claim, notify the duty manager and the property's insurance contact
before offering compensation, and document the incident timeline precisely. Do
not offer written compensation for personal injury incidents without management
and legal clearance.

## Cultural Adaptation

### Regional Norms

**Middle East:** hospitality in the Gulf region carries strong social weight — a
guest's dignity and face are implicated in every interaction, particularly in
complaint handling. Complaints should be received with full attention and never
minimized. Direct refusal (e.g., "we cannot do that") is perceived as a higher
affront than in other regions; frame limitations as "what we can arrange" rather
than "what is not possible." Honorific usage (Sheikh, Dr., Eng.) matters for
business travelers; verify before first interaction when possible.

**Europe:** service distance norms vary significantly across the continent.
Northern European guests (Scandinavian, Germanic) tend to prefer efficient,
low-affect interactions; extended warmth can read as performative. Southern
European and Mediterranean guests generally respond well to more relational
communication. Privacy consciousness is high across the EU; be precise about
what data is collected and why. GDPR-adjacent practices (consent for marketing,
right to access folio data) should be handled correctly even when not legally
required in the property's jurisdiction.

**Asia-Pacific:** honorific layers are structurally significant in Japan, Korea,
and parts of China. Guest title and last name should be used unless the guest
explicitly signals informality. Group harmony considerations mean that some
guests will not complain directly even when dissatisfied; proactive mid-stay
check-in calls or written channels may surface dissatisfaction that in-person
inquiry would not. In markets with strong gifting norms (Japan, China), a
recovery gesture that can be carried home — rather than a discount — may carry
higher symbolic value.

**Americas:** communication norms are generally less formal, and first-name use
is more readily accepted. Guest expectations for proactive problem-solving are
high — stating a problem and waiting for the guest to follow up is perceived as
poor service. In North America, review culture is mature and review incentives
are legally restricted (FTC guidance in the US); never offer compensation in
exchange for a positive review. In Latin American markets, relationship-building
over multiple interactions is valued; a brief personal follow-up on day two of a
multi-night stay is expected at upper-tier properties.

Never assume regional norms apply to an individual guest. Calibrate based on
observed interaction cues, not on nationality alone.

## Anti-Patterns

| Anti-pattern | Why It Fails |
|---|---|
| Blaming the guest for the service failure | Converts a complaint into a confrontation; violates the cardinal rule and produces negative reviews at a higher rate than any other response |
| Scripted or generic apologies ("sorry for any inconvenience") | Signals that the complaint has not been read; guests perceive it as a template and escalate instead of accepting the resolution |
| Ignoring online reviews or responding only to positive ones | Creates a visible asymmetry that future guests read as defensiveness; platforms penalize non-response with lower ranking |
| Defending policy as the primary response to a request or complaint | Positions the property as an adversary rather than a partner; the guest experiences it as "you don't matter enough for us to try" |
| Promising a specific room, floor, or amenity without confirming availability | Generates a check-in complaint that requires service recovery; the cost exceeds the value of the original promise |
| Offering compensation publicly in a review response | Establishes a visible precedent that any guest can exploit; may constitute a consumer protection issue in some jurisdictions |
| Routing mid-stay complaints to the next shift without handoff | Allows a resolvable complaint to metastasize; the guest interprets it as organizational indifference |
| Transmitting folio or identity data via unencrypted messaging channels | PII exposure risk; non-compliant with GDPR in EU jurisdictions and with local data protection law in most markets |

## Cross-References

- `domains/retail/skills/customer-returns` — shared complaint framing principles;
  the acknowledge → empathise → fact-find → action → follow-up → record sequence
  applies in both domains with domain-specific thresholds.
- `core/compliance-lgpd` — PII handling discipline for guest data; applies to
  folio records, identity documents, dietary information, and loyalty profile data.
- `core/code-review-checklist` — two-pass review pattern; applies to review
  response drafts before publishing (ADR-058 adversarial review principle).

## ADR Anchors

- **ADR-058** (Brainstorm gate and two-pass adversarial review): review responses
  and complaint resolution scripts above the Moderate severity tier should go
  through a two-pass review before delivery — draft by the attending agent,
  reviewed by the duty manager — to avoid responses that are defensive, legally
  exposed, or PII-disclosing.
