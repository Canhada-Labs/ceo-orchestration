---
name: Accessibility & WCAG Compliance
description: WCAG 2.1 AA compliance, ARIA patterns, keyboard navigation, focus management, screen reader support, color contrast, and accessible data visualization for the {{PROJECT_NAME}} frontend. Use when reviewing or writing any interactive component, form, modal, chart, table, or page-level navigation. Also use when the user mentions "accessibility", "a11y", "ARIA", "screen reader", "keyboard", "focus trap", "contrast", "skip navigation", or when reviewing any component that displays data to ensure it's accessible to all users.
trigger: Any work touching interactive components, forms, modals, charts, navigation, or visual design.
inspired_by:
  - source: msitarzewski/agency-agents/design/design-inclusive-visuals-specialist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 4
risk_class: low
stack: [typescript, react]
context_budget_tokens: 1000
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 8}
  fintech: {active: true, priority: 7}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: file-edit, glob: "**/*.tsx"}
  - {event: file-edit, glob: "**/*.jsx"}
  - {event: help-me-invoked, regex: "(?i)a11y|accessibility|aria|wcag|screen.?reader"}
---

# Accessibility & WCAG Compliance — {{PROJECT_NAME}} Frontend

## Current State (2026-03-23 Audit)
- **WCAG 2.1 AA Score: ~15-20%** (CRITICAL)
- ARIA coverage: minimal across the codebase
- Keyboard handlers: minimal across the codebase
- Focus traps in modals: ZERO
- Charts with screen reader alternatives: ZERO (71 charts invisible)
- Skip navigation: NONE
- sr-only utility class: NEVER used
- Forms with aria-describedby: ZERO
- Color contrast failures: text3 in both themes, accent + positive in light theme

## Audit Reference
Produce your own accessibility audit file (e.g. `FRONTEND_AUDIT_<date>.md`)
with findings numbered `A11Y-1`, `A11Y-2`, etc. so this skill can reference them.

## Owner
**Accessibility & i18n Lead** (archetype). Has VETO on any interactive component without accessibility.

## WCAG 2.1 AA Requirements (minimum)

### 1. Perceivable
- **1.1.1 Non-text content:** All images need alt text. All icon-only buttons need aria-label.
- **1.3.1 Info and relationships:** Use semantic HTML (headings, lists, tables, landmarks). Forms need proper label association.
- **1.4.3 Contrast minimum:** 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold).
- **1.4.11 Non-text contrast:** UI components and graphics need 3:1 contrast.

### 2. Operable
- **2.1.1 Keyboard:** All functionality available via keyboard. Tab order must be logical.
- **2.1.2 No keyboard trap:** Users must be able to leave any component via keyboard (except modals with focus trap that have an explicit close mechanism).
- **2.4.1 Bypass blocks:** "Skip to main content" link on every page.
- **2.4.3 Focus order:** Tab order follows visual layout.
- **2.4.7 Focus visible:** Focus indicator must be visible on all interactive elements.

### 3. Understandable
- **3.1.1 Language:** html lang attribute set to current locale.
- **3.3.1 Error identification:** Form errors identified and described in text.
- **3.3.2 Labels:** All form inputs have visible labels (not just placeholders).

### 4. Robust
- **4.1.2 Name, role, value:** All custom widgets have appropriate ARIA roles, states, and properties.

## Patterns for {{PROJECT_NAME}}

### Modals/Dialogs
```tsx
// REQUIRED: Focus trap + aria attributes + close on Escape
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <FocusTrap>
    <h2 id="dialog-title">{title}</h2>
    {/* content */}
    <button onClick={onClose} aria-label={t('close')}>X</button>
  </FocusTrap>
</div>
// On open: move focus INTO dialog
// On close: return focus to trigger element
```

### Charts (Recharts/lightweight-charts)
```tsx
// Charts MUST have screen reader alternative
<div role="img" aria-label={t('chart.description', { pair, timeframe })}>
  <RechartsChart {...props} />
  {/* Hidden data table for screen readers */}
  <table className="sr-only">
    <caption>{t('chart.data')}</caption>
    {/* data rows */}
  </table>
</div>
```

### Forms
```tsx
<label htmlFor="email">{t('email')}</label>
<input
  id="email"
  type="email"
  aria-required="true"
  aria-describedby={error ? 'email-error' : undefined}
  autoComplete="email"
/>
{error && <p id="email-error" role="alert">{error}</p>}
```

### Icon-Only Buttons
```tsx
// NEVER: <button onClick={onClose}>✕</button>
// ALWAYS:
<button onClick={onClose} aria-label={t('close')} type="button">
  <XIcon aria-hidden="true" />
</button>
```

### Financial Data Tables (EXAMPLE: fintech domain)
```tsx
<table role="table" aria-label={t('markets.table')}>
  <thead>
    <tr>
      <th scope="col" aria-sort={sortDir}>{t('pair')}</th>
      <th scope="col">{t('price')}</th>
    </tr>
  </thead>
  <tbody>
    {rows.map(row => (
      <tr key={row.id}>
        <td>{row.pair}</td>
        <td aria-label={`${row.pair} price ${formatPrice(row.price)}`}>
          {formatPrice(row.price)}
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

### Skip Navigation
```tsx
// In AppShell, FIRST element:
<a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-bg-0 focus:text-tx-1">
  {t('skip-to-content')}
</a>
// ... later:
<main id="main-content" tabIndex={-1}>
```

## Color Contrast Fixes Needed

| Token | Dark | Light | Issue |
|-------|------|-------|-------|
| text3 | #56657d on #0b1121 = 3.18:1 | #8494a7 on #f8f9fc = 2.94:1 | FAIL AA normal text |
| accent | OK in dark | #009b78 on #f8f9fc = 3.35:1 | FAIL AA normal text (light) |
| positive | OK in dark | #16a34a on #f8f9fc = 3.13:1 | FAIL AA normal text (light) |

## Testing Accessibility
```bash
# Lighthouse a11y audit
npx lighthouse https://{{DOMAIN}} --only-categories=accessibility --output=json

# axe-core in tests
import { axe } from 'vitest-axe'
const results = await axe(container)
expect(results).toHaveNoViolations()
```

## Priority Fix Order
1. Add focus traps to ALL modals (10+ implementations)
2. Add aria-label to ALL icon-only buttons (~75)
3. Add skip navigation to AppShell
4. Add screen reader alternatives to ALL charts (71)
5. Fix color contrast for text3, accent (light), positive (light)
6. Add aria-describedby + aria-required to ALL forms
7. Add keyboard handlers to ALL custom interactive components
## Adopter Note — Current-State Snapshot is Originating-Project (PLAN-044 P0-12)

The §Current State (2026-03-23 Audit) subsection and the
§Immediate Actions list carry concrete numbers and named tokens
(`text3`, `accent (light)`, `positive (light)`, `71 charts`,
`WCAG 2.1 AA Score: ~15-20%`) that come from the originating
`ceo-orchestration` dogfood frontend audit — a specific
fintech-console React + Tailwind codebase snapshotted on
2026-03-23. Those numbers do **not** describe your adopter
codebase.

When this skill loads in a fresh adopter project, treat the
current-state block and the action list as a **worked example**
of what a first-pass accessibility audit output looks like, not
as a diagnosis of your product.

Your own accessibility audit should produce
`FRONTEND_AUDIT_<date>.md` (as the §Audit Reference subsection
already suggests) and override the current-state figures before
any component work proceeds. The §Patterns / §WCAG 2.1 AA
Requirements sections above the current-state snapshot are
universal and apply as-is.

## Representation Integrity in Marketing and Hero Imagery

Every image shown to users communicates who belongs in the product's world. Failures here
are not aesthetic — they are functional: users who do not see themselves in product imagery
disengage, and alt text that misrepresents the depicted subject creates a false accessibility
record. This section governs image selection and generation for hero shots, onboarding flows,
marketing pages, and any UI surface where human subjects appear.

### Source classification and mandatory review gate

Three sourcing modes exist. Each carries distinct review obligations.

| Source mode | When to use | Mandatory review steps |
|---|---|---|
| Custom photography | Preferred for brand-critical surfaces (home hero, onboarding) | Art director + accessibility lead sign-off before shoot; post-shoot: verify alt text accuracy against actual depicted subjects |
| Licensed stock | Acceptable for secondary pages when budget prohibits custom | Representation audit checklist below; NEVER auto-accept first search result |
| AI-generated | Only for decorative/abstract use; NEVER for human subjects in production | Prohibited on human-subject surfaces until generation tooling is verified for the checks below |

The rule on AI-generated imagery for human subjects is a hard prohibition, not a guideline.
AI image generators produce clone faces in diverse groups, incorrect cultural text and symbols,
and lighting calibrated for lighter skin tones as a model-default. These outputs require
expert correction that costs more than sourcing stock or commissioning photography. Until your
team has a verified review protocol for generation artifacts, do not ship AI-generated images
of people.

### Stock imagery audit checklist

Run this checklist on every candidate image before committing it to the asset library.

```
REPRESENTATION AUDIT — stock image candidate
Image ID / filename: _______________
Surface: hero | onboarding | marketing-secondary | other: ___

[ ] Age: does the image default only to subjects aged 20-35?
    Flag if yes — seek at least one candidate with subjects 45+ or under 18 where product-appropriate.

[ ] Ability: are mobility aids, hearing aids, adaptive technology absent from all shortlisted images?
    Flag if yes — at least one surface in the onboarding/marketing set must include subjects
    with visible disability representation if the product serves a general population.

[ ] Body type: does the shortlist default exclusively to a single body-type range?
    Flag if yes — seek candidates with visible variance.

[ ] Cultural specificity: if the image depicts a cultural setting (clothing, architecture, signage),
    is the depiction accurate for the subject's evident cultural context?
    Flag if ambiguous — do not use ambiguous "cosmopolitan" framing as a substitute for accuracy.

[ ] Tokenism check: is the only subject from a marginalized group isolated,
    visually subordinated, or posed in a service role relative to other subjects?
    Flag if yes — reject and resource.

[ ] Alt text accuracy: write the alt text before finalizing the image.
    Does the alt text match what is actually depicted (age, role, setting)?
    Inaccurate alt text is a WCAG 1.1.1 failure regardless of image quality.
```

An image that triggers any flag is not automatically rejected — it is escalated to
the Accessibility & i18n Lead for a judgment call. An image that triggers three or
more flags is rejected without escalation; re-source.

### Alt text accuracy rule

Alt text is the only accessibility interface screen-reader users have to an image.
Writing alt text that softens, generalizes, or omits depicted characteristics is not
neutral — it produces an inaccurate record of the product's visual language.

```
# CORRECT
alt="Two engineers, one using a power wheelchair, reviewing code on a shared screen"

# WRONG
alt="Team collaboration"
# Reason: erases both the wheelchair user and the task context.
# A screen reader user has no information about who is in the image or what they are doing.
```

Decorative images that carry no informational content use `alt=""` (empty string, not absent).
Never use `alt="image"`, `alt="photo"`, or `alt="icon"` — these are not descriptions.

## Perceptual Variant Parity

Users invoke OS-level or browser-level accessibility preferences that re-render the product
at the system level. If the product's CSS and component logic do not respond to those
preferences, the rendered output can violate WCAG even when the default theme passes.
This section defines the minimum parity obligations for each preference signal.

### Mandatory preference signals

| Signal | CSS / JS hook | Minimum obligation |
|---|---|---|
| `prefers-color-scheme: dark` | CSS media query | All contrast ratios verified in dark variant; NEVER assume light-variant token values transfer |
| `prefers-reduced-motion` | CSS media query + JS `matchMedia` | All animations and transitions suppressed or replaced with instant state change; no exception for "subtle" animations |
| `forced-colors` (Windows High Contrast) | CSS media query | Layout must not collapse; interactive states must use `ButtonText` / `Highlight` system colors; no image-only affordances |

### Contrast verification across variants

Token contrast values verified in one theme do not transfer to the other.
Run the contrast audit independently for each deployed theme.

```
# For each token used on text or interactive UI:
# 1. Resolve the CSS custom property value in dark theme.
# 2. Resolve the background it appears on.
# 3. Compute the contrast ratio (WCAG formula or tooling output).
# 4. Repeat for light theme.
# NEVER shortcut: "accent passes in dark, should be fine in light" is the reasoning
# that produced the accent + positive failures in this project's 2026-03-23 audit.
```

### Reduced-motion implementation

```tsx
// WRONG — only checks a product preference toggle and (worse) reads
//         window.matchMedia at module scope, which crashes under SSR.
import { useProductSetting } from '@/hooks/useProductSetting'

const prefersReducedAtModuleScope =
  window.matchMedia('(prefers-reduced-motion: reduce)').matches // BUG: SSR crash

function MotionPanel() {
  const prefersReduced = useProductSetting('reducedMotion') // BUG: ignores OS signal
  // ...
}
```

```tsx
// CORRECT — module-scope custom hook reads the OS signal via an SSR-safe
//           effect; the component composes that with an optional product
//           toggle. Hook subscribes to change events so users who toggle
//           reduced-motion at runtime get the new value without reload.
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useProductSetting } from '@/hooks/useProductSetting'

function usePrefersReducedMotion(): boolean {
  // Default TRUE on the server (no motion until the client confirms
  // otherwise) and read matchMedia SYNCHRONOUSLY in the lazy initializer
  // on the client. This prevents an unwanted entry animation flashing
  // before useEffect runs — the "OS signal is authoritative" rule means
  // we never run motion the user has not opted into.
  const [systemReduced, setSystemReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })
  useEffect(() => {
    if (typeof window === 'undefined') return
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)')
    setSystemReduced(mql.matches)
    const handler = (e: MediaQueryListEvent) => setSystemReduced(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])
  const productOverride = useProductSetting('reducedMotion')
  return systemReduced || productOverride
}

function MotionPanel({ children }: { children: React.ReactNode }) {
  const prefersReduced = usePrefersReducedMotion()
  return (
    <motion.div
      animate={prefersReduced ? {} : { opacity: [0, 1], y: [8, 0] }}
      transition={{ duration: prefersReduced ? 0 : 0.2 }}
    >
      {children}
    </motion.div>
  )
}
```

The OS signal is the authoritative source. Product-level toggles may extend coverage
but NEVER override it. A user who has set `prefers-reduced-motion` at the OS level has
done so because animations cause vestibular harm — overriding that setting with a
product default is a functional accessibility failure.

### Forced-colors (High Contrast mode) validation

Test in Windows with High Contrast Aqua and High Contrast Black modes. Both must pass.

```
Checklist — forced-colors:
[ ] Focus indicators are visible: rely on outline (browser-default) rather than box-shadow only
    (box-shadow is suppressed in forced-colors mode).
[ ] Icon-only affordances have text alternatives: icon color may be flattened to a system color;
    the icon shape must remain distinguishable or a text label must be present.
[ ] Status communicated by color alone is duplicated with shape or text:
    e.g., error state signaled ONLY by red border fails in forced-colors.
[ ] Background images used to communicate meaning: prohibited in forced-colors context;
    any image-as-affordance must have a visible text or ARIA fallback.
```
