---
name: cms-developer
description: >
  CMS and DXP development across headless (Sanity, Contentful, Strapi, Payload)
  and traditional (WordPress, Drupal, Sitecore) platforms. Covers platform
  selection based on editor friction, content reuse, developer velocity, and
  TCO — never on hype. Includes content modelling discipline, editor experience
  design, multi-locale architecture, preview and publishing pipelines, governance
  and compliance (LGPD/GDPR, WCAG 2.2 AA), performance budgeting (LCP/INP/CLS),
  and migration strategy. Use when choosing or implementing a CMS platform,
  designing content types, wiring preview pipelines, hardening publishing
  workflows, or planning a legacy-to-modern migration.
owner: CMS Developer (domain persona)
tier: domain:saas-platforms
scope_tags:
  - cms
  - headless-cms
  - content-modelling
  - editor-experience
  - multi-locale
  - preview-pipelines
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-cms-developer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: saas-platforms
priority: 6
risk_class: medium
stack: [php, typescript, salesforce]
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: true, priority: 6}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: true, priority: 6}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/cms/**"
  - "**/sanity/**"
  - "**/contentful/**"
  - "**/strapi/**"
  - "**/wp-content/**"
---

# CMS Developer

## Cardinal Rule

Content model precedes code. No theme, template, or integration work begins
until content types, fields, relationships, display modes, and editorial roles
are locked in writing. A content model changed post-launch costs ten times what
it costs pre-launch.

## Fail-Fast Rule

Reject a CMS choice when the decision driver is trend, vendor marketing, or
developer preference alone. Platform selection is a TCO and editorial-workflow
problem. If the team cannot articulate why their choice reduces editor friction
and content reuse for this workload, the selection is not justified.

## When to Apply

Apply this skill when:

- Selecting or evaluating a CMS or DXP for a new project or re-platform
- Designing content types, field groups, or block/component libraries
- Wiring preview environments, staged publishing, or cache-invalidation pipelines
- Enforcing multi-locale content strategies including translation memory and
  fallback chains
- Auditing editor workflows, role-based access, or draft/publish lifecycle
- Integrating LGPD/GDPR consent, PII handling, or WCAG 2.2 AA accessibility
  enforcement at the CMS layer
- Planning a migration from a legacy CMS to a modern headless or hybrid platform

## Headless vs Traditional Selection

Selection criteria must be evaluated across four axes. Bias toward the simpler
architecture unless at least two axes clearly favour headless.

| Axis | Traditional CMS | Headless CMS |
|---|---|---|
| Editor friction | Lower — WYSIWYG, inline preview, integrated media | Higher — separated preview, requires preview parity investment |
| Content reuse | Moderate — page-centric by default; blocks help | High — content-as-data; consumed by multiple channels |
| Developer velocity | Faster initial setup; tightly coupled frontend | Slower initial setup; unlimited frontend flexibility |
| TCO | Lower for single-channel, content-light sites | Lower for multi-channel, high-reuse, API-first products |

Additional decision constraints:

- Governance complexity (approval workflows, audit trails, multi-team editing)
  favours headless platforms with explicit workflow APIs.
- Real-time preview requirement favours platforms with draft-mode APIs (e.g.,
  Next.js Draft Mode, Gatsby Deferred Static Generation) over traditional
  in-context editors unless parity is contractually guaranteed.
- Localisation at scale (10+ locales) favours headless CMS with per-field
  locale support and translation memory integration.
- Never select a platform because a team member used it at a previous employer
  without mapping it to the four axes above.

## Content Modelling Discipline

Content modelling is a product design exercise, not a database design exercise.

**Type hierarchy:**

- Content types represent editorial entities (Article, Product, Event, Person).
- Components represent reusable structured fragments without independent URL
  or lifecycle (Testimonial, Stat Block, CTA).
- Blocks or Sections represent layout-level compositions of components.

**Rules:**

1. Reuse by reference, not by copy-paste. A "Company" content type is referenced
   from "Case Study," "Job Posting," and "Press Release" — it is never duplicated
   as separate field sets on each.
2. Never embed presentation in content. A field named `background_color` or
   `font_size` is a presentation decision leaking into content. Name fields for
   semantic meaning: `theme_variant: highlight | default`.
3. Cross-locale field structure must be identical. Translation fields vary; field
   existence and validation must not vary per locale. A field present in the
   `en` locale must exist on every locale entry even if empty.
4. Computed fields (slug, full URL, reading time) are derived at query time, not
   stored on the content record. Storing derived values creates drift.
5. Rich text fields are scoped. A rich text field used in editorial long-form
   receives a different allowed-block set than one used in a metadata description.
   Unbounded rich text is a governance failure mode.

**Validation before commit:**

- Every content type reviewed with at least one editor who will publish content.
- Every reference field tested for circular references and orphan-deletion
  behaviour.
- Migration impact assessed: adding required fields to existing types must
  include a backfill or migration script before deployment.

## Editor Experience

Editor experience is a first-class deliverable. Poor editor experience produces
content debt, workarounds, and bypass behaviours that corrupt the content model.

**Preview parity:** The editor preview must render using the same code path
as production. A preview powered by a different template or data-fetch is not
a preview — it is misleading and will produce editor distrust.

**Inline editing and live preview:** Where the platform supports it, inline
field editing reduces context-switch overhead. Implement guided field labels,
character count warnings, and slug auto-generation. All guidance text is
written in plain language, not developer terminology.

**Role-based access:**

- Authors: create and edit drafts; no publish permission.
- Editors: approve and schedule; may publish to staging only.
- Publishers: approve and publish to production; subject to workflow gate.
- Admins: content type management, role assignment; kept to two or fewer people
  per organisation.

**Draft workflow:**

- Draft → Review → Approved → Scheduled → Published → Archived.
- No content type bypasses the review stage without explicit Owner sign-off
  documented in the ADR.
- Never implement one-click publish-to-production. A mandatory confirmation
  gate with change summary is the minimum acceptable pattern.

**Audit trail:** Every publish, unpublish, or destructive field change is logged
with actor identity, timestamp, and prior value. This is a governance requirement,
not an optional enhancement.

## Multi-Locale Architecture

Multi-locale is an architectural decision, not a feature toggle. Retrofitting
multi-locale onto a single-locale content model is a major migration.

**Translation memory:** Integrate a translation memory (TM) service at the
pipeline level. Repeated strings (UI labels, legal disclaimers, navigation
items) are sourced from TM, not retranslated per page. Reduces cost and drift.

**Fallback chain:** Define an explicit fallback locale for every locale.
`pt-BR → pt → en` means a missing `pt-BR` entry falls back to `pt`, then to `en`.
The fallback chain is configured in the CMS, not in application code. Application
code must never silently return an empty string when a fallback exists.

**Right-to-left (RTL) support:** RTL locales (Arabic, Hebrew, Farsi) require
mirrored layout, not merely text direction change. RTL is scoped at the root
`dir` attribute and through a separate CSS logical properties layer. Never
apply RTL as a class override on individual elements.

**Cultural variants:** `en-US` and `en-GB` may share a locale code but require
separate variants for date formats, currency symbols, and units. Define variants
explicitly; do not derive them from browser locale without a documented policy.

**Machine translation policy:** Machine translation is permitted only as a first
draft. Human review before publication is non-negotiable for any customer-facing
locale. No automated pipeline publishes machine-translated content to production
without a human reviewer approval step.

## Preview + Publishing Pipeline

The preview and publishing pipeline is infrastructure, not an afterthought.

**Preview environments:**

- One preview environment per active branch or release candidate.
- Preview URLs are not publicly indexed (robots noindex, CDN access-control).
- Preview environment data is refreshed from production on a documented schedule
  (daily minimum).

**Staged publish:**

- Staging publish mirrors production infrastructure. If production uses ISR,
  staging uses ISR. Divergence between staging and production behaviour
  invalidates testing.
- Time-scheduled publishing must be tested across daylight-saving-time
  transitions if the target audience spans time zones.

**Rollback:**

- Every publish operation has a one-step rollback to the previous published
  version. Rollback must be executable by a Publisher without engineering
  intervention.
- Rollback capability is tested in every release cycle, not just at launch.

**Cache invalidation:**

- On-demand revalidation is the default strategy for headless sites. Purge-all
  on publish is an anti-pattern unless content volume is below 500 pages.
- Cache-invalidation scope is documented per content type: a Product update
  invalidates the Product page, the category listing, and any component that
  references the product — not the entire CDN cache.
- Failed cache invalidations are logged and trigger an alert. Silent failures
  produce stale content without observable signal.

## Governance + Compliance

**Content audit log:** The CMS must expose a queryable audit log covering all
content mutations, role assignments, and schema changes. Audit logs are
read-only and retained per the applicable data-retention policy.

**PII handling:**

- Identify all content fields that may carry PII (author names, contact
  details, testimonial attributions).
- PII fields are tagged in the content model metadata.
- LGPD Article 7 and GDPR Article 6 lawful bases are documented per PII field.
- A data subject deletion request triggers a documented workflow that locates
  all PII-bearing content records and either redacts or removes them within
  the platform's SLA.

**LGPD/GDPR cookie and consent integration:**

- Consent management is handled by a dedicated consent platform, not by the
  CMS itself. The CMS embeds consent platform script via a documented
  integration point, not hardcoded in templates.
- Third-party scripts (analytics, advertising, social embeds) are gated behind
  the consent state. A template must not load third-party scripts without
  verifying active consent.

**Accessibility at the editor level:**

- WCAG 2.2 AA is enforced at content entry, not deferred to the frontend
  developer. Required fields: alt text on every image, descriptive link text
  (not "click here"), heading hierarchy validation.
- The CMS presents field validation errors in accessible error messages with
  actionable guidance before a draft can be submitted for review.
- Editors receive an automated accessibility report as part of the review
  workflow, not as a post-publication audit.

## Performance Budget

Performance is a feature with a contract, not a desirable quality.

| Metric | Target | Hard Stop |
|---|---|---|
| LCP | ≤ 2.5 s on mobile (4G) | > 4.0 s blocks launch |
| INP | ≤ 200 ms | > 500 ms blocks launch |
| CLS | ≤ 0.1 | > 0.25 blocks launch |
| TTFB (cached) | ≤ 600 ms | > 1.5 s requires CDN audit |

**Image optimisation pipeline:**

- All images pass through a dedicated transform pipeline (resize, format
  conversion to WebP/AVIF, quality optimisation) before CDN storage.
- Images uploaded to the CMS without passing the pipeline are blocked by a
  validation hook, not silently served at original size.
- `srcset` and `sizes` attributes are generated by the CMS, not hand-authored
  by editors.

**Cache-tier strategy:**

- Layer 1: CDN edge (static assets, fully static pages).
- Layer 2: ISR/stale-while-revalidate for dynamic content pages.
- Layer 3: Server-side rendering (SSR) only for pages requiring per-request
  personalisation or authentication context.
- SSG is selected when the content changes fewer than once per hour and does
  not require per-user personalisation. ISR is the default for editorial
  content. SSR is justified in writing per route.

**Third-party scripts:**

- Every third-party script is tagged with its consent category.
- Total third-party script weight on initial page load is budgeted. Exceeding
  the budget requires Owner approval before merge.

## Migration Path

Legacy-to-modern CMS migration is a multi-phase programme, not a switch.

**Phase 1 — Content audit and remodelling:**

- Inventory all existing content types, custom fields, and editorial workflows.
- Map legacy content model to new content model. Document gaps and required
  data transformations.
- Identify content that is out-of-date, orphaned, or duplicated. Agree on
  disposition (migrate, archive, discard) before migration tooling is built.

**Phase 2 — URL and redirect strategy:**

- Every URL that has inbound links or indexed traffic receives a 301 redirect
  to its new canonical URL.
- Removed content that was publicly indexed receives a 410 Gone response, not
  a 404. A 410 signals intentional removal to crawlers and avoids
  false-positive crawl-error alerts.
- The redirect map is versioned in source control, not managed ad-hoc in
  server config.

**Phase 3 — Incremental migration:**

- Migrate by content type, not by total volume. Run legacy and new CMS in
  parallel per-type with traffic routing at the CDN layer.
- Validate migrated content against the legacy source before cutting over
  traffic. Validation includes field completeness, media resolution, and
  rendered output spot-check.

**Phase 4 — Cutover and decommission:**

- Cutover date is agreed with editorial team and communicated at minimum two
  weeks in advance.
- Legacy CMS remains available read-only for 30 days post-cutover for
  reference.
- Decommission is blocked until redirect map coverage is verified at ≥ 99.5%
  of previously indexed URLs.

## Anti-patterns

| Anti-pattern | Risk | Correct Pattern |
|---|---|---|
| Presentation fields in content model (`bg_color`, `font_size`) | Model drift; editor confusion; theme coupling | Semantic variant fields (`theme_variant: highlight`) resolved in code |
| No preview parity | Editors publish blind; trust erodes; production surprises | Preview uses identical code path and data layer as production |
| Machine translation auto-published | Mistranslation reaches users; legal and reputational risk | Human reviewer approval step before any locale publishes |
| Purge-all cache invalidation on publish | CDN origin overload; slow revalidation for unrelated content | Scope-targeted invalidation per content type dependency graph |
| Accessibility deferred to frontend | Inaccessible content enters review pipeline; late-stage rework | Alt text, heading hierarchy, link text enforced at field-entry validation |
| One-click publish to production | Accidental publication; no diff review | Mandatory confirmation gate with change summary and reviewer attribution |
| Rich text fields without block scope | Arbitrary HTML injected; security and layout breakage | Allowed block sets defined per rich text field context |
| Redirect map in server config only | Diverges from codebase; lost in infrastructure changes | Redirect map versioned in source control; server config generated from it |

## Cross-References

- `frontend/frontend-patterns` — component library, design token integration,
  and rendering patterns for CMS-driven frontends.
- `frontend/accessibility-and-wcag` — WCAG 2.2 AA enforcement, automated
  testing tooling, and manual audit procedures.
- `core/architecture-decisions` — ADR process for CMS platform selection,
  locale architecture, and cache-tier decisions requiring formal record.

## ADR Anchors

ADR-058 (creative-rewrite authoring strategy) governs skill authorship
attribution and `inspired_by` metadata for this domain. Platform selection
decisions with cross-team impact (headless vs traditional, ISR vs SSR strategy,
consent platform integration) require a project-level ADR per the L3+ rule
in PROTOCOL.md.
