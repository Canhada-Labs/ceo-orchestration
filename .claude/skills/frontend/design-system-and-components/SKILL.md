---
name: Design System & Component Architecture
description: Design token governance, component architecture patterns, shared component organization, empty/loading/error state standards, component library integration (e.g. shadcn/ui, Material-UI, Chakra), responsive design, and visual consistency for the {{PROJECT_NAME}} frontend. Use when creating or reviewing components, organizing shared/, working with design tokens, implementing responsive layouts, or ensuring visual consistency across pages. Also use when the user mentions "design system", "components", "shared/", "god component", "empty state", "skeleton", "design tokens", "dark mode", "responsive", or any visual/structural component work.
trigger: Any work involving components, design system, visual consistency, or shared/ directory.
version: 1.1.0
inspired_by:
  - source: affaan-m/ecc/skills/motion-foundations@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 5
risk_class: low
stack: [typescript, react, tailwind]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 9}
  fintech: {active: true, priority: 7}
  trading-readonly: {active: true, priority: 10}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: file-edit, glob: "**/components/**"}
  - {event: file-edit, glob: "**/shared/**"}
  - {event: help-me-invoked, regex: "(?i)design.?system|component|shadcn|tailwind|token"}
source: affaan-m/ecc@81af4076 skills/motion-foundations/
license: MIT
---

# Design System & Component Architecture — {{PROJECT_NAME}} Frontend

## Current State (2026-03-23 Audit)
- **Component Architecture: 6/10** — shared components in FLAT directory, god components (>300 lines)
- **Design System: 6.5/10** — Tokens well-designed (8/10) but adoption weak (5/10)
- **Empty States: 2/10** — Only 14% of components handle no-data
- **Loading States: 8/10** — 81% of components
- **Error States: 7/10** — 66% of components
- **Responsive: 4/10** — Only 40% of components use breakpoints
- **PRO Widgets: 9/10** — 79% thin wrappers (<=15 lines)

## Audit Reference
Produce your own audit file (e.g. `FRONTEND_AUDIT_<date>.md`) with findings
numbered so this skill can reference them.

## Owners
- **UI/UX Lead** (archetype) — design system governance, visual consistency
- **Component Architect** (archetype) — composition, deduplication, tier-gated widget variants

## Design Token System

### Architecture (3 layers)
1. The project's design token source of truth (e.g. a design-tokens.ts file) — 47 tokens per theme (94 total), injected as CSS vars on `<html>`
2. `src/styles/globals.css` `@theme` block — bridges CSS vars to Tailwind utilities
3. Components use Tailwind utilities: `text-tx-1`, `bg-bg-1`, `border-ds-border`

### Token Categories
| Category | Tokens | Examples |
|----------|--------|---------|
| Background | 5 | bg0-bg3, bgOverlay, widgetBg |
| Text | 4 | text1-text3, textMuted |
| Border | 3 | border, borderHover, borderFocus |
| Accent | 4 | accent, accentBright, accentDim |
| CTA | 4 | cta, ctaHover, ctaDim, ctaText |
| Semantic | 12 | positive/negative/trust/warning + Dim |
| Density | 3 modes | editorial, dense, maximum |
| Motion | 7 | micro through pulse |

### Rules
- **NEVER** hardcode hex colors in .tsx files — use tokens via Tailwind classes
- **NEVER** use `dark:` prefix — theme works via CSS variable swapping
- **ALWAYS** use density tokens for spacing (gap, padding, row height, font size)
- 33 files currently violate with hardcoded colors (mostly chart/canvas components)

## Motion Tokens & Motion Governance

Motion is a token category, not a per-component decision. The token table
above already lists Motion (7 tokens) alongside color and density; this
section gives that category the same governance the color tokens get — a
single source of truth, no hardcoded values, and accessibility baked into
the tokens rather than bolted onto each animation.

### Tokenize every motion value

Durations, easings, spring configs, and interaction scales all live in
the token layer. A component that references `motionTokens.duration.normal`
is correct by construction; a component with `transition: 300ms` inline is
a drift you cannot audit.

| Tier | What it holds | Example steps |
|------|---------------|---------------|
| Duration | How long a motion runs | instant / fast / normal / slow / crawl |
| Easing | The acceleration curve | smooth / sharp / bounce / linear |
| Spring | Named physics presets | snappy / gentle / bouncy / instant / release |
| Scale | Interaction transforms | subtle / press / pop |

Rule (parallel to "NEVER hardcode hex colors"): **NEVER hardcode a
duration, easing, or spring config in a component — reference a token.**
Inline motion values are the same class of violation as inline hex.

### Accessibility is a property of the token layer

Reduced motion is not a per-component opt-in — it is a priority order the
token/gate layer enforces for *every* animation:

1. **`prefers-reduced-motion: reduce` wins over everything.** It disables
   transforms; the only permitted fallback is an opacity fade ≤ 0.2s.
2. **Low-end device** (e.g. low `hardwareConcurrency`) drops non-essential
   animation and shortens the rest.
3. **Design preference** applies only after the two gates above pass.

A single `shouldAnimate()` gate that reads those two signals is what every
animated component calls before it animates — so the accessibility
contract cannot be forgotten one component at a time. The runtime *budget*
rules (zero transitions on high-frequency-update elements, direction-
encoded state flashes) live in `frontend-patterns` → "Animation and Motion
Floors"; this section governs the *tokens and the gate*, that one governs
*what motion is allowed to run*.

### Two hard constraints

- **Animate `transform` and `opacity` only.** `width`, `height`, `top`,
  `left`, `margin`, and `padding` trigger layout/paint and drop frames —
  use a `scale` / `translate` transform instead. (This is why the Scale
  tier exists as a token.)
- **`initial` must match server output.** An entrance that starts at
  `opacity: 0` while the server rendered `opacity: 1` is a hydration
  mismatch. Defer the animated initial state to a client mount flag, or
  drive enter/exit through a presence wrapper. Never read `window` or
  `navigator` at module scope — guard with `typeof window !== "undefined"`.

### Should this motion exist at all?

Before adding an animation, require it to do at least one job: **guide
attention**, **communicate a state change**, or **preserve spatial
continuity**. Decorative motion with none of these is removed.
Responsiveness outranks smoothness — an animation that adds input latency
is worse than no animation.

See `reference/motion-tokens.md` for the concrete token object, the spring
preset map, the `shouldAnimate()` gate, and an SSR-safe animated component.

## Component Standards

### Every shared component MUST have:
1. `React.memo()` wrapper (all shared components currently do — maintain this)
2. `useTranslation()` for all user-visible text
3. **Loading state** — Skeleton or LoadingSkeleton component
4. **Empty state** — EmptyState component from core/ (CRITICAL: only 14% have this)
5. **Error state** — ErrorSection component from core/
6. Props interface exported and documented

### Component Size Limits
| Size | Action |
|------|--------|
| <300 lines | OK |
| 300-500 lines | Review — could it be split? |
| >500 lines | MUST be split. CEO approval required to keep. |

### Current God Components (>300 lines)
Track your top-N largest components and their line counts. A component
that crosses 500 lines MUST be split; 300-500 is a review trigger.

## Shared/ Directory Organization

### Current: FLAT (all shared files in one directory) — CRITICAL issue

### Proposed subdirectories:
```
src/components/shared/
├── analytics/    # analytics-domain components
├── charts/       # chart wrappers
├── dashboards/   # dashboard / overview components
├── tables/       # table components (with shared DataTable primitive)
├── notifications/# alert & notification components
├── forms/        # form-related components
├── settings/     # Settings tab components
└── (remaining)   # General-purpose shared components
```

(Adapt the subdirectory list to match your product's actual domain clusters.)

## Missing Primitives

Only 5 of ~30 standard component library primitives (e.g. shadcn/ui, Material-UI, Chakra) present. Need:
- **Button** — standardized variants (primary, secondary, ghost, destructive)
- **Dialog/Modal** — with focus trap, aria attributes (replaces 10+ hand-rolled modals)
- **Sheet/Drawer** — mobile-friendly side panel
- **Tooltip** — accessible, delay-based
- **Dropdown** — keyboard navigable, ARIA compliant
- **Select** (exists but heavily customized)
- **Tabs** (exists but customized)

## Duplication Patterns to Extract

| Pattern | Components | Extraction |
|---------|-----------|------------|
| DataTable | 13 table components | `<DataTable>` with sort/filter/pagination/virtualization |
| BaseChart | 18 chart wrappers | `<BaseChart>` with loading/error/empty + a11y wrapper |
| BasePanel | 43 panel/card components | `<BasePanel>` with header/body/footer structure |

## PRO Widget Pattern
- Thin wrapper (~15 lines): imports shared component, wraps in WidgetShell
- NEVER put business logic in widgets
- Target: >90% of widgets at <=15 lines
- Track outliers and refactor the ones that exceed the threshold
## Adopter Note — Current-State Snapshot is Originating-Project (PLAN-044 P0-12)

The §Current State (2026-03-23 Audit) subsection contains
concrete `X/10` scores (Component Architecture 6/10, Design
System 6.5/10, Empty States 2/10, Loading 8/10, Error 7/10,
Responsive 4/10, PRO Widgets 9/10) and a `47 tokens per theme
(94 total)` metric. These figures come from the originating
`ceo-orchestration` dogfood frontend audit of a specific
fintech-console React + Tailwind codebase and should **not**
be read as your adopter baseline.

Likewise, the §Design Token System references `design-tokens.ts`
and `src/styles/globals.css` — those paths are illustrative of
the pattern ("single source of truth → CSS vars → Tailwind
bridge"), not prescriptions for your file layout.

For your adopter project:

- Run your own design-system audit; override the 7 scores in
  §Current State with your numbers before component work.
- Replace the file paths in §Design Token System with your own
  equivalents (or keep the pattern if they happen to match).
- The §Empty / Loading / Error States contract below the
  current-state block is universal and applies as-is.

## Changelog

- **1.1.0** (2026-07-07, PLAN-153 Wave G): enrichment merge — added
  §Motion Tokens & Motion Governance (motion as a governed token category:
  tokenize every value, reduced-motion priority order, transform/opacity-
  only, SSR-safe initial state) plus `reference/motion-tokens.md`. Clean-
  room ADAPT of upstream motion-foundations guidance; no pre-existing
  section changed. First tracked revision.
- **1.0.0** (framework v1.0.x): initial version shipped with the
  framework; this changelog was introduced retroactively at 1.1.0.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=76e69cd5e2175c53eb36b1da9a8e8fd56e8afa80026356faa489da59c4661013
