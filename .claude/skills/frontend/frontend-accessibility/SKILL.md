---
name: frontend-accessibility
description: Accessibility and internationalization for the {{PROJECT_NAME}} frontend. Covers
  WCAG 2.1 AA compliance for data-rich applications, ARIA patterns for data tables,
  charts, and interactive UIs, keyboard navigation patterns, focus
  management, screen reader compatibility, color contrast for data UX (red/green
  alternatives), i18n parity across locales, locale-aware number and
  currency formatting, and RTL readiness. Use when building or reviewing any interactive
  component, form, data visualization, or page-level navigation.
owner: Accessibility & i18n Lead (archetype)
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 5
risk_class: low
stack: [typescript, react]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 9}
  fintech: {active: true, priority: 7}
  trading-readonly: {active: true, priority: 9}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)a11y|i18n|locale|rtl|aria"}
---

# Frontend Accessibility & i18n

## Fail-Fast Rule

If a component is interactive and has no keyboard support, **it does not
ship**. If a financial value is displayed without locale-aware formatting,
**it does not ship**. Accessibility is not a follow-up task — it's a
requirement for every component.

## Current State (Audit 2026-03-23)

| Metric | Value | Target |
|--------|-------|--------|
| aria-* coverage | minimal across the codebase | 100% interactive components |
| role= usage | minimal across the codebase | All custom widgets |
| i18n locales | project-specific (e.g. en, pt-BR, es) | Parity across all |
| i18n namespaces | project-specific | Key parity verified |
| Keyboard navigation | Unknown | Full app navigable |
| Screen reader | Unknown | VoiceOver + NVDA tested |

## WCAG 2.1 AA Checklist for Financial Apps

### Perceivable
- [ ] Color is NEVER the only indicator (red/green for gain/loss needs icon/arrow too)
- [ ] Text contrast ratio >= 4.5:1 (normal text), >= 3:1 (large text)
- [ ] All images/icons have alt text or aria-label
- [ ] Charts have text alternatives (summary table, aria-description)
- [ ] Real-time updates announced via aria-live regions (polite for prices, assertive for alerts)
- [ ] Financial data tables have proper headers (th scope="col/row")

### Operable
- [ ] All interactive elements reachable via Tab key
- [ ] Focus order matches visual order
- [ ] Focus visible indicator on all interactive elements (not just browser default)
- [ ] No keyboard traps (can always Tab out of modals, dropdowns)
- [ ] Modals trap focus correctly (Tab cycles within modal)
- [ ] Escape closes modals, dropdowns, tooltips
- [ ] Skip-to-main-content link present
- [ ] No time limits without extension option

### Understandable
- [ ] Form inputs have visible labels (not just placeholder)
- [ ] Error messages identify the field and describe the fix
- [ ] Language attribute set on html element
- [ ] Consistent navigation across pages
- [ ] Financial terms have glossary links or tooltips

### Robust
- [ ] Valid HTML (no duplicate IDs, proper nesting)
- [ ] ARIA roles match element behavior
- [ ] Custom widgets follow WAI-ARIA design patterns
- [ ] Components work with screen readers (VoiceOver, NVDA)

## ARIA Patterns for Common Components

### Data Table with Row Groups
```tsx
<div role="table" aria-label="Activity log for Project Alpha">
  <div role="rowgroup" aria-label="Pending items">
    <div role="row">
      <div role="columnheader">Name</div>
      <div role="columnheader">Count</div>
      <div role="columnheader">Updated</div>
    </div>
    <div role="row" aria-label="Item 42 updated recently">
      <div role="cell">Item 42</div>
      <div role="cell">17</div>
      <div role="cell">2m ago</div>
    </div>
  </div>
</div>
```

### Real-Time Value Updates
```tsx
// Use aria-live for value changes the user is monitoring
<span aria-live="polite" aria-atomic="true">
  Current value: {formatValue(value)}
</span>

// Use aria-live="assertive" ONLY for alerts that demand immediate attention
<div role="alert" aria-live="assertive">
  Action required: your session is about to expire
</div>
```

### Trading Form (EXAMPLE: fintech domain)
```tsx
<form aria-label="Place order">
  <fieldset>
    <legend>Order Type</legend>
    <label><input type="radio" name="type" value="buy" /> Buy</label>
    <label><input type="radio" name="type" value="sell" /> Sell</label>
  </fieldset>
  <label htmlFor="price">Price (USDT)</label>
  <input id="price" type="text" inputMode="decimal"
    aria-describedby="price-help" aria-invalid={hasError} />
  <span id="price-help">Enter limit price or leave empty for market order</span>
</form>
```

### Charts (lightweight-charts / recharts)
- Canvas-based charts are NOT accessible by default
- Provide: aria-label on container, data table alternative, keyboard navigation for data points
- For lightweight-charts: overlay transparent button grid for keyboard access
- For recharts: use built-in a11y props (role, tabIndex on elements)

## Color Contrast for Financial UX (EXAMPLE: fintech domain)

### Problem: Red/Green Color Blindness
~8% of males have red-green color blindness. Financial apps that rely on
red=loss, green=gain exclude these users.

### Solution: Multi-channel indicators
```tsx
// BAD: color only
<span className={gain ? "text-green-500" : "text-red-500"}>
  {value}
</span>

// GOOD: color + icon + aria-label
<span
  className={gain ? "text-green-500" : "text-red-500"}
  aria-label={gain ? "Gain" : "Loss"}
>
  {gain ? "▲" : "▼"} {value}
</span>
```

## Keyboard Navigation Patterns

### Page-Level
- Tab: move between interactive elements
- Shift+Tab: move backward
- Enter/Space: activate buttons, links
- Arrow keys: navigate within composite widgets (tabs, menus, grids)
- Escape: close modals, dropdowns, tooltips
- Home/End: first/last item in lists

### Data Table Navigation
- Arrow keys move between cells
- Enter to sort column (on header)
- Page Up/Down for scrolling large tables

## i18n Parity Rules

### Key Parity
Every translation key must exist in ALL configured locales for the project.
Missing keys = English fallback = broken UX for non-English users.

### Number/Currency Formatting
```typescript
// ALWAYS use locale-aware formatting
// Example locale A: 1.234,56 (dot=thousand, comma=decimal)
// Example locale B: 1,234.56 (comma=thousand, dot=decimal)
// Never hardcode separators
```

### Date Formatting
```typescript
// Example locale A: 24/03/2026 (dd/mm/yyyy)
// Example locale B: 03/24/2026 (mm/dd/yyyy)
// Always use Intl.DateTimeFormat or date-fns with locale
```

### Pluralization
- English: "1 item" / "2 items"
- Portuguese: "1 item" / "2 itens"
- Spanish: "1 elemento" / "2 elementos"
- Use i18next pluralization, never manual if/else

## Testing Accessibility

### Manual Testing Checklist
1. Navigate entire page with Tab key only
2. Activate every button/link with Enter and Space
3. Open and close every modal/dropdown with keyboard
4. Test with VoiceOver (Mac) or NVDA (Windows)
5. Test with browser zoom at 200% and 400%
6. Test with high contrast mode (Windows)
7. Test with forced-colors media query

### Automated Testing
- eslint-plugin-jsx-a11y in CI
- axe-core integration tests
- Lighthouse accessibility score >= 90
