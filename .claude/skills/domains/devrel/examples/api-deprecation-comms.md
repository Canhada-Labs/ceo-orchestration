---
plan_id: PLAN-EXAMPLE-DEV
title: "v1 Payments API Deprecation — 9-Month Sunset with Migration Campaign"
status: draft
owner: ceo
level: L3
squad: devrel
profile: core,devrel
created_at: 2026-05-10
---

# Example PLAN — v1 Payments API Deprecation

> **This is an illustrative example**, not a real plan. It shows how the
> DevRel squad coordinates a major API deprecation that touches all three
> VETO scopes (documentation contract integrity, breaking-change communication
> strategy, and DX quality of the migration path).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/devrel/task-chains.yaml`

## 1. Problem

The platform is deprecating its v1 Payments API in favor of a redesigned
v2 API that has better idempotency key design, structured error responses,
and a simplified authentication flow. The v1 API has approximately 8,200
active integrations (measured by unique API keys with requests in the last
30 days) across 4 official SDKs (Python, Node.js, Go, Ruby).

The risk: a poorly-executed deprecation will generate a developer trust crisis,
a flood of support tickets, and potentially a churn spike from enterprise
integrations that cannot migrate on a short timeline. A well-executed deprecation
is a product quality signal.

Sources:
- v1 API usage telemetry (endpoint-level, SDK-level, integration-level)
- v2 API implementation (complete and in production)
- Migration path analysis (parameter mapping, authentication differences, response schema changes)
- Community feedback from the beta program (v2 was in preview for 3 months)

## 2. Scope

**In:**
- 9-month advance deprecation notice (6 months minimum required; 9 months for
  8,200 integrations)
- Migration guide for all v1 endpoints → v2 equivalents (30+ endpoints)
- In-code SDK deprecation warnings in all 4 official SDKs
- Community announcement campaign (forum, email to affected API keys, developer newsletter)
- Telemetry-gated sunset date announcement (announced only when < 5% of tracked
  integrations remain on v1)
- Migration tooling (automated parameter migration script for the 5 most-used endpoints)

**Out:**
- v2 API feature work (complete and out of scope for this deprecation plan)
- Enterprise migration support for very large integrations (handled by the account team
  separately with custom SLAs)
- Security-driven deprecations on the same timeline (separate emergency process)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Impact Telemetry | Felix Acharya | Per-integration usage breakdown; SDK-level active count; top-50 most-active integrations identified (DEV-006) |
| P2 — Migration Guide | Sola Adewale | Full migration guide for all 30+ v1 endpoints; published simultaneously with notice (DEV-004) |
| P3 — SDK Deprecation Warnings | Felix Acharya | In-code warnings in Python, Node.js, Go, Ruby SDKs; minor version bumps shipped (DEV-009) |
| P4 — Community Announcement | Remy Dubois + Jodie Okonkwo | Forum post + direct email to 8,200 affected API keys + developer newsletter; office hours scheduled (DEV-007) |
| P5 — Migration Tooling | Felix Acharya + Priscilla Tan | Auto-migration script for top 5 endpoints; DX quality gate (DEV-010) |
| P6 — Sunset Date Announcement | Remy Dubois | Announced only when telemetry shows < 5% still on v1 (DEV-006) |
| P7 — Launch Review | CEO + all VETO holders | Sola (docs), Remy (communication), Priscilla (DX) sign-off before notice goes live |

## 4. Risk axes and VETO holders

- **Sola Adewale (Technical Writer):** Migration guide must be published
  simultaneously with the deprecation notice — BLOCK notice if guide is not
  complete (DEV-004). Changelog must name every deprecated endpoint specifically
  — BLOCK if "various improvements" style entries are used (DEV-002).
- **Remy Dubois (Developer Advocate):** 9-month advance notice must be confirmed
  before notice is drafted — BLOCK if the proposed date is < 6 months away
  (DEV-005). Sunset date cannot be announced until telemetry shows < 5% on v1
  — BLOCK premature sunset announcement (DEV-006).
- **Priscilla Tan (DX Engineer):** Migration tooling must pass the DX quality
  gate (time to complete migration for a sample integration ≤ 2 hours) —
  BLOCK migration tooling launch if DX gate fails (DEV-010).

## 5. Task chains invoked

- `devrel-api-deprecation-comms` — primary chain; runs the full deprecation
  communication and sunset workflow
- `devrel-sdk-release` — invoked at P3 for the SDK minor-version releases
  that ship the in-code deprecation warnings

## 6. Acceptance

- Sunset date is 9 months from the deprecation notice date; no earlier (DEV-005)
- Migration guide covers all 30+ v1 endpoints; published on the same day as the notice (DEV-004)
- In-code deprecation warnings shipped in all 4 official SDKs before the notice goes live (DEV-009)
- Changelog entry names every deprecated v1 endpoint with a link to the migration guide (DEV-002)
- Direct notification sent to all 8,200 affected API keys within 24 hours of the notice (DEV-007)
- Sunset date announcement made only when telemetry shows < 5% of tracked integrations still on v1 (DEV-006)
- v1 API continues serving traffic through the full 9-month period regardless of v2 adoption rate (DEV-008)

## 7. Scenario walkthrough

**Scenario:** The team has shipped v2 to GA and is ready to begin the deprecation campaign.

1. **Impact Telemetry (P1):** Felix pulls the 30-day telemetry. Result: 8,200 unique
   API keys with active v1 requests. The top 50 integrations by request volume account
   for 61% of total v1 traffic. Felix flags the top 50 for priority direct outreach by
   Remy's team. He also notes that 400 integrations have not made a v1 request in
   90 days — these are likely already migrated or dormant. Sunset date is gated on
   < 5% of the 7,800 active integrations (i.e., < 390 integrations still on v1).

2. **Migration Guide (P2):** Sola and the engineering team map all 30+ v1 endpoints
   to their v2 equivalents. Two v1 endpoints have no direct v2 equivalent — they were
   intentionally sunset without replacement (a feature that was removed). Sola documents
   this explicitly: "This endpoint is not available in v2. If you use this feature, contact
   support before migrating." Remy reviews the two removed-without-replacement endpoints
   and confirms they have < 200 active users combined — acceptable for this migration scope.

3. **SDK Deprecation Warnings (P3):** Felix ships minor version bumps to all 4 SDKs.
   Python: 2.8.0 → 2.9.0 with deprecation warnings on all v1-wrapper methods. Node.js:
   5.3.1 → 5.4.0. Go: 1.12.0 → 1.13.0. Ruby: 3.5.2 → 3.6.0. Each SDK warning includes
   the sunset date and migration guide URL at runtime. The SDK releases ship 48 hours
   before the public notice goes live.

4. **Community Announcement (P4):** On Day 0 (deprecation notice day):
   - Forum post published by Remy: "v1 Payments API Deprecation Notice — Migration Guide + 9-Month Sunset"
   - Email sent to all 8,200 affected API key owners via the platform's notification system
   - Developer newsletter published with migration guide summary
   - Office hours scheduled: weekly for the first 8 weeks, bi-weekly thereafter
   Jodie pins the forum post and sets up keyword alerts for "v1 deprecation" and "v2 migration".
   Response SLA for migration questions: 4 hours for the first week.

5. **Migration Tooling (P5):** Priscilla and Felix build an automated migration script
   for the 5 most-used v1 endpoints (accounting for 73% of v1 traffic). The script
   takes a developer's v1 integration code and outputs a v2 equivalent with comments
   on manual review points. Priscilla runs the DX gate: a sample integration (mid-complexity)
   completes in 47 minutes with the migration script — well under the 2-hour gate.

6. **Week 8 Check-in:** Telemetry at 8 weeks shows 4,100 of 7,800 active integrations
   (53%) have migrated to v2. Remy reviews: good progress but not < 5% yet — sunset date
   announcement is blocked (DEV-006). Remy extends office hours frequency and adds a
   "migration sprint" campaign with a 30-day migration badge incentive.

7. **Month 7 Telemetry:** 7,600 of 7,800 integrations have migrated (97.4%). Only 200
   remain on v1 (2.6% < 5% threshold). Remy now proceeds with the sunset date announcement:
   "v1 API will cease serving traffic on [Month 9 date]." The remaining 200 integrations
   receive a direct email from Remy's team with an offer of white-glove migration support.

8. **Sunset Day (Month 9):** v1 API stops serving traffic. Felix confirms the infrastructure
   decommission. No integrations are surprised: every active integration received at least
   3 direct notifications and saw in-code warnings for 9 months.

**Outcome:** Of the 8,200 original integrations, 7,992 migrated to v2 before sunset.
208 integrations were dormant (never responded; presumed abandoned). Zero community crises.
The deprecation is cited in the developer community as a model for how to handle an API sunset.

**Caveats:**
- The 9-month timeline assumed no major competing API changes during the migration window.
  If a second breaking change is required during this period, Remy's VETO applies to ensure
  the combined migration burden is assessed.
- The telemetry-gated sunset date announcement (DEV-006) means the sunset date could be
  announced earlier than Month 7 if migration proceeds faster — or later if adoption stalls.
  The sunset date is fixed (Month 9 from notice); only the announcement timing floats.
- Enterprise integrations in the top 50 by volume received separate account-team outreach
  not covered by this plan's chain. The squad chain covers the long-tail of 8,150 integrations.

## 8. Metrics

- Migration rate at 3 months, 6 months, 9 months (target: >95% before sunset)
- Support ticket volume related to the migration (monitored weekly; spike triggers office-hours frequency increase)
- **Developer trust score** (community sentiment survey at Month 3 and Month 6; target: neutral or positive on the deprecation handling)

## 9. References

- `.claude/skills/domains/devrel/task-chains.yaml` — `devrel-api-deprecation-comms`
- `.claude/skills/domains/devrel/task-chains.yaml` — `devrel-sdk-release`
- `.claude/skills/domains/devrel/pitfalls.yaml` — DEV-001 through DEV-012
- ADR-009 (squad-bundle completeness contract)
