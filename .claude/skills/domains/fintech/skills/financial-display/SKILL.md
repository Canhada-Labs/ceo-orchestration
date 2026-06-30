---
name: financial-display
description: Financial data display correctness for a crypto trading platform frontend. Covers
  precision rules by asset type (crypto 8 decimals, fiat 2, stablecoin 4), locale-aware
  number formatting (BRL comma vs USD dot), safeNumber/safeFixed/safePct usage patterns,
  parseFloat prohibition, _pct field handling (already 0-100 vs 0-1), chart axis
  formatting, color coding accuracy for gains/losses, null/undefined/NaN/Infinity
  guards, and display consistency across 233 shared components. Use when building or
  reviewing any component that shows prices, volumes, percentages, spreads, depth,
  PnL, or any numeric financial value. Zero tolerance for display errors.
owner: Mei Chen
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 3
risk_class: medium
stack: [typescript, react]
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 8}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: file-edit, glob: "**/components/**"}
  - {event: help-me-invoked, regex: "(?i)safenumber|safefixed|parsefloat|brl|usd|usdt|precision.?display"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/components/**"
  - "**/formatters/**"
  - "**/charts/**"
---

# Financial Display

## Fail-Fast Rule

If a financial value cannot be safely converted to a display string, **show
a dash (—) or placeholder**, never show 0, NaN, undefined, or a wrong number.
A wrong price displayed confidently causes more damage than no price at all.

## Cardinal Rule

**NEVER use parseFloat() on financial values.** Use safe.ts functions.

```typescript
// FORBIDDEN — will lose precision
const price = parseFloat(data.price)     // BAD
const vol = Number(data.volume)          // BAD for display
const pct = parseFloat(data.spread_pct)  // BAD

// CORRECT — use safe.ts
import { safeNumber, safeFixed, safePct } from '@/lib/safe'
const price = safeFixed(data.price, precision)  // "50,123.45"
const vol = safeNumber(data.volume)              // handles null/NaN
const pct = safePct(data.spread_pct)             // "0.15%"
```

## Precision Rules by Asset Type

| Asset Type | Price Decimals | Volume Decimals | Example |
|-----------|---------------|----------------|---------|
| BTC | 2 | 8 | 50,123.45 / 0.00123456 |
| ETH | 2 | 6 | 3,456.78 / 0.123456 |
| Major altcoins (SOL, ADA) | 4 | 4 | 123.4567 / 12.3456 |
| Small altcoins | 6-8 | 2 | 0.00001234 / 100.00 |
| Stablecoins (USDT, USDC) | 4 | 2 | 1.0001 / 1,000.00 |
| Fiat (BRL, USD) | 2 | 2 | 5.4321 → 5.43 |
| Percentage | 2 | — | 0.15% |

### Dynamic Precision
Use `usePairPrecision` hook — it queries the engine for per-pair precision:
```typescript
const { pricePrecision, volumePrecision } = usePairPrecision(pairId)
// Returns backend-configured precision per pair
// Falls back to asset-type defaults if unavailable
```

## Locale Formatting

### BRL (pt-BR)
```
Number: 1.234,56 (dot=thousand, comma=decimal)
Currency: R$ 1.234,56
Negative: -R$ 1.234,56 (prefix minus)
Percentage: 1,23%
Date: 24/03/2026
```

### USD (en-US)
```
Number: 1,234.56 (comma=thousand, dot=decimal)
Currency: $1,234.56
Negative: -$1,234.56
Percentage: 1.23%
Date: 03/24/2026
```

### Rules
1. ALWAYS use `Intl.NumberFormat` or format.ts functions — never manual formatting
2. NEVER hardcode separators ("." or ",")
3. Currency symbol position varies by locale — use Intl
4. Compact notation for large numbers: "1.2M" not "1,200,000" (but full precision on hover/tooltip)

## _pct Field Handling

Backend sends percentage fields in TWO formats depending on the field:

| Pattern | Backend sends | Display as | Example |
|---------|--------------|-----------|---------|
| `spread_pct` | 0.0015 (ratio) | × 100 → "0.15%" | spread |
| `change_pct` | -2.5 (already %) | As-is → "-2.50%" | price change |
| `quality_score` | 85 (0-100) | As-is → "85" | quality |
| `imbalance` | 0.65 (ratio) | × 100 → "65%" | bid/ask imbalance |

**Rule**: Check the API type definition to know which format. When in doubt,
check the backend source. NEVER assume.

## Null/Undefined/NaN/Infinity Guards

Every financial display must handle these cases:

```typescript
// PATTERN: Guard → Format → Display
function displayPrice(value: unknown, precision: number): string {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  if (num === 0) return '0'  // zero IS a valid price (e.g., expired options)
  return safeFixed(num, precision)
}
```

### Special Cases
- **Negative spread**: Valid in crossed books. Display in red with warning icon.
- **Zero volume**: Valid. Display "0" not "—".
- **Very small prices**: 0.00000001 — use scientific notation or auto-precision
- **Very large prices**: 1,234,567,890 — use compact notation with full on hover

## Chart Formatting

### Price Axis (lightweight-charts)
```typescript
// GOOD: locale-aware, correct precision
priceFormat: {
  type: 'custom',
  formatter: (price) => safeFixed(price, pricePrecision),
}

// BAD: fixed precision, no locale
priceFormat: {
  type: 'price',
  precision: 2,  // wrong for crypto
}
```

### Tooltip Values
- Show full precision in tooltips (not abbreviated)
- Include timestamp with locale-aware formatting
- Show both base and quote values where applicable

### Volume Bars
- Use abbreviated format: "1.2M" not "1,200,000"
- Color: independent of price (volume is neutral)

## Color Coding Rules

| Value | Color | Alt Indicator | Meaning |
|-------|-------|--------------|---------|
| Positive change | Green | ▲ arrow | Gain |
| Negative change | Red | ▼ arrow | Loss |
| Zero change | Neutral/gray | — dash | Unchanged |
| Bid (buy) | Green | "BID" label | Buyer side |
| Ask (sell) | Red | "ASK" label | Seller side |
| Stale data | Yellow/amber | ⚠ icon | Data > 15s old |
| Invalid data | Gray | — dash | Cannot display |

**Critical**: Always pair color with a non-color indicator (arrow, icon, label)
for color-blind users (8% of males).

## Component Review Checklist

For any component displaying financial data:
- [ ] Uses safe.ts functions? (no parseFloat, no toFixed)
- [ ] Uses usePairPrecision hook? (not hardcoded precision)
- [ ] Handles null/undefined/NaN? (shows "—" not "NaN")
- [ ] Locale-aware formatting? (respects BRL/USD conventions)
- [ ] _pct fields handled correctly? (ratio vs already-percent)
- [ ] Color + non-color indicator? (accessible to color-blind)
- [ ] Staleness indicator? (when data > 15s old)
- [ ] Compact notation for large numbers? (with full on hover)
- [ ] Chart axes properly formatted? (correct precision and locale)
