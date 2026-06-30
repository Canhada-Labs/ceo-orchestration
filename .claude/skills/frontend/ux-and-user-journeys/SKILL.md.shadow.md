---
name: UX & User Journeys
description: User experience design, journey mapping, information architecture, navigation patterns, responsive/mobile strategy, onboarding flows, empty state messaging, progressive disclosure, micro-interactions, and conversion-oriented UX for the {{PROJECT_NAME}} frontend. Use when designing new pages, reviewing user flows, optimizing onboarding, improving navigation, making the product more intuitive, or when the user mentions "UX", "user journey", "flow", "onboarding", "navigation", "mobile", "responsive", "friction", "intuitive", "confusing", or any user-experience concern.
trigger: Any work involving page design, user flows, navigation, onboarding, or user-facing product decisions.
---

# UX & User Journeys — {{PROJECT_NAME}} Frontend

## Owner
- **UI/UX Lead** (archetype) — Visual quality, design system, component architecture, and user experience.
- **Growth Engineer** (archetype, optional backend consultant) — Product lens, conversion, activation.

## Current State
- The codebase has pages, shared components, and any tier-gated feature variants (fill in from your project)
- Zero UX research conducted (no user interviews, no usability testing, no heatmaps)
- Phase 4 (page-by-page product audit) NOT YET DONE — pending engine online
- Onboarding: 6 files in src/onboarding/ (17-step guided tour)
- Empty states: Only 14% of components handle "no data" (CRITICAL UX gap)
- Mobile: 40% of shared components have responsive breakpoints

## UX Principles for Financial Data Platforms

### 1. Progressive Disclosure
- Show summary first, detail on demand
- Don't overwhelm with 50 columns — show 5, let user customize
- Use collapsible sections for advanced settings
- Hide PRO features behind contextual upgrade prompts (not hard paywalls)

### 2. Data Density vs Readability
- **Dense mode** for power users: small fonts, tight spacing, maximum data
- **Editorial mode** for new users: larger fonts, more whitespace, explanations
- Use DENSITY tokens from the project's design token source of truth (e.g. a design-tokens.ts file) (currently only used in 5 files!)
- Let user choose density mode in Settings

### 3. First-Time Experience
- Empty states MUST guide the user toward value (not just "No data")
- Every page needs a "what is this?" tooltip or intro card
- Onboarding tour (17 steps) should be contextual, not linear
- First login → Dashboard with curated data, not empty panels

### 4. Navigation Architecture
```
Landing → Login → Home (dashboard) (EXAMPLE: fintech domain)
                   ├── Markets (browse pairs)
                   │   └── PairDetail (deep dive)
                   ├── Exchanges (compare exchanges)
                   ├── Arbitrage (find opportunities)
                   ├── OrderBook (consolidated depth)
                   ├── Analytics (charts & analysis)
                   ├── Trading (execute trades)
                   ├── Portfolio (track positions)
                   ├── PRO Terminal (power users)
                   └── Settings (account, billing, API keys)
```

### 5. Real-Time UX
- Stale data MUST be visually indicated (never show stale data as current)
- Use staleness thresholds: 15s (warning), 60s (degraded), 120s (offline)
- Reconnection: show progress, not just "disconnected"
- Value changes: brief color flash (green up, red down) then return to normal

### 6. Numeric Data UX
- Numbers: locale-aware formatting (comma vs dot decimals, thousand separators)
- Precision: adaptive — pick decimal count based on magnitude of value
- Colors: green = positive, red = negative (configurable for colorblind users?)
- Large numbers: compact format (e.g. `1.2M`, `500K`)

### 7. Mobile Strategy
- Aim for 100% of routes responsive (not just 40%)
- Dense tables on mobile: horizontal scroll or card layout
- Charts: simplified on small screens (fewer labels, larger touch targets)
- Bottom navigation for core flows
- Touch-friendly: minimum 44px touch targets

### 8. Error Recovery
- Network errors: auto-retry with visual countdown ("Retrying in 3s...")
- Auth errors: redirect to login with return URL
- Data errors: show last known good data with "outdated" indicator
- Form errors: inline validation, don't clear form on error

### 9. Empty States (CRITICAL GAP)
For each data-fetching component, define 4 states:
1. **Loading**: Skeleton matching final layout shape
2. **Empty (first visit)**: Explain what this section shows + CTA to get started
3. **Empty (no results)**: "No matches" + suggest broader filters
4. **Error**: ErrorSection with retry button + fallback suggestion

### 10. Conversion Triggers
- Blurred data for free users with "Upgrade to PRO" overlay
- Feature discovery: tooltips on first encounter of PRO features
- Usage limits: show remaining quota + "Get more with PRO"
- Social proof: concrete numbers — "N entities tracked" / "K integrations" / "M events/day"

## Page-by-Page UX Checklist (for Phase 4 audit)

For EACH page, answer:
1. **Who is this for?** (new user, power user, analyst, admin)
2. **What's the #1 action?** (e.g. view a metric, find an opportunity, trigger a workflow)
3. **Can a new user understand it in 5 seconds?** (without domain knowledge)
4. **What's the empty state?** (first visit, no data, error)
5. **Is it usable on mobile?** (responsive, touch-friendly)
6. **Where's the upgrade trigger?** (if feature is PRO-gated)
7. **What's the loading experience?** (skeletons, not spinners)

## Information Architecture Audit Needed
- Are the number of pages too many? Which can be merged?
- Is the sidebar navigation intuitive for non-power-users?
- EXAMPLE (fintech domain): Should Traditional/FX/Macro/News be separate pages or tabs?
- EXAMPLE (fintech domain): Should Derivatives be a standalone page or part of a Markets super-page?
- EXAMPLE (fintech domain): Is the PRO Terminal discoverable enough?
## Adopter Note — Fintech Framing is Example-Only (PLAN-044 P0-12)

This skill is **universal UX** despite heavy fintech illustration.
Concrete elements drawn from the originating `ceo-orchestration`
dogfood project include:

- §Current State ("17-step guided tour", "6 files in
  src/onboarding/", "Phase 4 page-by-page product audit") —
  project-specific numbers, not prescriptive.
- §UX Principles for Financial Data Platforms section heading —
  the principles (progressive disclosure, data density, first-
  time experience) are universal; the `Financial Data Platforms`
  qualifier is example-only.
- §Navigation Architecture tree (`Markets / Exchanges / Arbitrage
  / OrderBook / Analytics / Trading / Portfolio / PRO Terminal`)
  is the dogfood fintech-console's IA — already labelled
  `EXAMPLE: fintech domain`.
- §Key UX Questions section (the final block above) — all
  labelled `EXAMPLE (fintech domain)`, kept for worked-example
  value.

Adopter-side mapping: replace "Markets / PRO Terminal /
Portfolio" with your own domain's IA, replace "17-step tour /
6 files in src/onboarding" with your own onboarding numbers,
and drop the "Financial Data Platforms" qualifier from the
UX Principles heading when spawning a non-fintech archetype.
The section structure (Current State → Principles → IA →
Real-Time UX → Key Questions) transfers as a template.
