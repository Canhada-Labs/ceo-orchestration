---
name: Accessibility & WCAG Compliance
description: WCAG 2.1 AA compliance, ARIA patterns, keyboard navigation, focus management, screen reader support, color contrast, and accessible data visualization for the {{PROJECT_NAME}} frontend. Use when reviewing or writing any interactive component, form, modal, chart, table, or page-level navigation. Also use when the user mentions "accessibility", "a11y", "ARIA", "screen reader", "keyboard", "focus trap", "contrast", "skip navigation", or when reviewing any component that displays data to ensure it's accessible to all users.
trigger: Any work touching interactive components, forms, modals, charts, navigation, or visual design.
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
