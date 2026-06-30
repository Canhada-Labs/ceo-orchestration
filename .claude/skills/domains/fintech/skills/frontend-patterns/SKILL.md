---
name: fintech-frontend-patterns
description: Fintech-specific frontend patterns — financial data formatting (BRL/USD/USDT/
  multi-currency), trading terminal component architecture (order book virtualization,
  trading form), real-time price update patterns, PRO tier gating (Free/Pro/Trader/Quant
  ladder), accessibility rules specific to dense financial data, and fintech anti-patterns.
  Use when working on any trading, market data, orderbook, price display, tier gating, or
  financial-domain UI code in the {{PROJECT_NAME}} frontend. EXTENDS the universal skill at
  `frontend/frontend-patterns/SKILL.md` — read that first, then apply the rules here.
owner: Alex Rivera
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 5
risk_class: low
stack: [typescript, react]
context_budget_tokens: 1000
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 9}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)trading.?terminal|tier.?gating|pro.?tier|trading.?form"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/trading/**"
  - "**/terminal/**"
  - "**/tiers/**"
  - "**/orderbook/**"
---

# Fintech Frontend Patterns

> **This skill extends `frontend/frontend-patterns/SKILL.md`.** Read the
> universal skill first for architecture principles, composition patterns,
> error boundaries, lazy loading, WS/SSE lifecycle, state management,
> virtualization, memoization, responsive design, accessibility basics, and
> performance monitoring. This document layers fintech-specific rules on top.

## Fintech Overview

| Item | Value |
|------|-------|
| Primary users | Brazilian traders (default locale `pt-BR`) |
| Currencies | BRL, USD, USDT, MXN, ARS, EUR (more possible) |
| PRO tiers | Free, Pro, Trader, Quant |
| Real-time | WebSocket (market data) + SSE (book updates, alerts) |
| Dense-data pages | Trading terminal, order book, arbitrage, spreads, depth |

## Fintech-Specific Component Hierarchy

Above and beyond the universal `Pages` / `Shared` split, fintech apps usually
grow these page families and providers:

```
App
  ├── AuthProvider (JWT token, user tier)
  ├── Pages
  │     ├── Market data pages (exchanges, orderbooks, pairs)
  │     ├── Trading pages (terminal, orders, positions)
  │     ├── Analytics pages (arbitrage, spreads, depth)
  │     ├── Intelligence pages (AI, predictions, social)
  │     └── Settings pages (billing, API keys, profile)
  └── Shared
        ├── PRO widgets (gated by tier)
        └── Financial formatters (prices, volumes, timestamps)
```

### Extra Rules

1. **PRO widgets MUST check tier** before rendering content. Show upgrade CTA
   for insufficient tier.
2. **Every component that displays financial data MUST use the formatting
   utilities.** Never format prices/volumes inline.
3. **AuthProvider MUST expose the user tier** so PRO widgets can read it
   synchronously during render.

## Financial Data Formatting

### Price Formatting

```typescript
// CORRECT — locale-aware, precision-preserving
function formatPrice(
  value: string | number,
  options?: {
    currency?: string;        // "BRL", "USD", "USDT"
    significantDigits?: number;
    locale?: string;          // default "pt-BR"
  }
): string {
  const { currency = "USD", significantDigits = 8, locale = "pt-BR" } = options ?? {};

  // Use Intl.NumberFormat for locale-aware formatting
  const num = typeof value === "string" ? parseFloat(value) : value;

  // Dynamic precision based on magnitude
  const decimals = num >= 1000 ? 2
    : num >= 1 ? 4
    : num >= 0.01 ? 6
    : 8;

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: decimals,
    style: currency === "BRL" || currency === "USD" ? "currency" : "decimal",
    currency: currency === "BRL" ? "BRL" : currency === "USD" ? "USD" : undefined,
  }).format(num);
}

// WRONG — hardcoded formatting
function formatPrice(value: number): string {
  return `$${value.toFixed(2)}`; // Loses precision, wrong locale, wrong currency
}
```

### BRL Locale Specifics

- Decimal separator: `,` (comma)
- Thousands separator: `.` (period)
- Currency symbol: `R$` (prefix with space)
- Example: `R$ 1.234.567,89`
- Default locale for the platform: `pt-BR`

### Volume Formatting

```typescript
// Abbreviate large volumes
function formatVolume(value: number, locale = "pt-BR"): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value);
}
```

### Timestamp Formatting

```typescript
// Always show relative time for recent, absolute for old
function formatTimestamp(ms: number, locale = "pt-BR"): string {
  const age = Date.now() - ms;
  if (age < 60_000) return `${Math.floor(age / 1000)}s ago`;
  if (age < 3_600_000) return `${Math.floor(age / 60_000)}min ago`;
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(ms);
}
```

### Formatting Rules

1. **NEVER use `toFixed()` directly in JSX.** Always use a formatter function.
2. **Locale MUST default to `pt-BR`** (primary user base is Brazilian).
3. **Currency MUST come from the data, not hardcoded.** BRL, USD, USDT, MXN, ARS, EUR all possible.
4. **Negative values MUST be visually distinct** (red color, minus sign).
5. **Zero values MUST be shown as "0", not empty string or "-".**
6. **Loading states MUST show skeleton, not "0" or "N/A".**

## Trading Terminal Component Architecture

### Order Book Component

```
OrderBookWidget
  ├── OrderBookHeader (pair, spread, mid price)
  ├── AskSide (virtualized list, sorted ascending)
  │     └── PriceLevel (price, size, cumulative, depth bar)
  ├── MidPrice (current mid, trend arrow)
  ├── BidSide (virtualized list, sorted descending)
  │     └── PriceLevel (price, size, cumulative, depth bar)
  └── OrderBookFooter (depth summary, exchange source)
```

### Order Book Virtualization

Order books routinely show 500+ price levels per side. That makes virtualization
mandatory — rendering every level kills FPS during WS updates. Use
`react-window` or `@tanstack/react-virtual` exactly as described in the
universal skill, but pin row height and keep depth bars off the main layout
pass:

```typescript
import { useVirtualizer } from "@tanstack/react-virtual";

function OrderBookSide({ levels }: { levels: PriceLevel[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: levels.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 24,  // order-book rows are dense
    overscan: 8,
  });

  return (
    <div ref={parentRef} className="ob-side">
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
        {virtualizer.getVirtualItems().map((vRow) => (
          <PriceLevelRow
            key={levels[vRow.index].price}  // stable key = price string
            level={levels[vRow.index]}
            style={{
              position: "absolute",
              top: 0,
              transform: `translateY(${vRow.start}px)`,
              height: `${vRow.size}px`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
```

### Rules for Order Book UI

1. **Order book MUST be virtualized.** Rendering 500+ price levels kills FPS.
2. **Price levels MUST show depth bars** (visual representation of size at each level).
3. **Spread MUST be prominently displayed** between bid and ask sides.
4. **Color coding:** Green for bids, red for asks. NEVER use color alone (add +/- signs).
5. **Flash animation** on price level changes (brief highlight, 200ms).
6. **Stale indicator:** If book data is >15s old, show warning badge.
7. **Stable keys** from the price string, never array index — keys must survive
   delta updates.

### Trading Form Component

The order-entry form is the highest-stakes UI surface in the app. Treat it as a
single feature area with these contracts:

```
TradingForm
  ├── PairSelector
  ├── SideToggle (Buy / Sell)
  ├── OrderTypeTabs (Market / Limit / Stop)
  ├── PriceInput (disabled for Market)
  ├── QuantityInput (with slider for percent of balance)
  ├── QuoteEstimate (fees, slippage, total)
  └── SubmitButton (confirmation modal on click)
```

### Rules for Trading Form

1. **Optimistic validation runs on every keystroke.** Show inline errors, don't
   wait for submit.
2. **Quote estimate refreshes on input pause (300ms debounce)**, not on every
   keystroke.
3. **Tab order MUST be pair → side → type → price → quantity → submit.**
4. **Submit MUST require a confirmation modal** showing final price, quantity,
   fees, total, and a "this is irreversible" line.
5. **Disable submit while a previous submission is in-flight.** No double orders.
6. **Form state is ephemeral.** Use `useState` or a dedicated `trading-store`
   that is NOT persisted.
7. **Never prefill the quantity field from the previous order.** Each order is
   a fresh decision.

## Real-Time Price Update Patterns

Real-time price updates need more than the generic WS lifecycle from the
universal skill. Layer these fintech rules on top:

1. **rAF batching is mandatory.** Price streams fire faster than the refresh
   rate. Coalesce updates in a `requestAnimationFrame` tick (e.g. 30 books per
   frame max), carry excess to the next frame.
2. **Per-instrument throttle** (50ms per exchange:pair, max 20 updates/sec/book)
   for depth updates.
3. **Delta protocol applies to pending frame**, not committed state, so
   overlapping deltas collapse cleanly.
4. **Flash animation on change**: wrap the price cell with a brief 200ms
   highlight (green on up-tick, red on down-tick). Use CSS `@keyframes`, not JS
   interval.
5. **Stale badge after 15s of no update** on any visible price. Stale prices
   are worse than no prices.
6. **Components MUST NOT subscribe to the raw WS store.** Use typed selector
   hooks (`usePriceForPair`, `useSpread`, `useBookDepth`) that use `useShallow`
   so only the interested component re-renders.

## PRO Widget Gating

### Tier System

| Tier | Widgets | Data Refresh | API Calls |
|------|---------|-------------|-----------|
| Free | Basic (market overview, top pairs) | 30s polling | 100/day |
| Pro | +50 widgets (analytics, spreads) | 5s polling + SSE | 1K/day |
| Trader | +30 widgets (trading terminal) | Real-time WS | 5K/day |
| Quant | All widgets (AI, predictions) | Real-time WS | Unlimited |

### Gating Pattern

```typescript
function ProWidget({
  requiredTier,
  children,
}: {
  requiredTier: "pro" | "trader" | "quant";
  children: React.ReactNode;
}) {
  const { tier } = useAuth();
  const tierRank = { free: 0, pro: 1, trader: 2, quant: 3 };

  if (tierRank[tier] < tierRank[requiredTier]) {
    return (
      <UpgradeCTA
        currentTier={tier}
        requiredTier={requiredTier}
        featureDescription="Access advanced analytics"
      />
    );
  }

  return <>{children}</>;
}

// Usage
<ProWidget requiredTier="trader">
  <TradingTerminal />
</ProWidget>
```

### Rules

1. **Gating check MUST happen client-side AND server-side.** Client for UX,
   server for security.
2. **Upgrade CTA MUST be contextual** ("Upgrade to Trader to access trading
   terminal").
3. **Never hide PRO features entirely.** Show blurred/teaser version with
   upgrade prompt.
4. **Free tier MUST still be useful.** Market overview, top 10 pairs, basic
   charts.
5. **Currently 95% of backend endpoints lack tier gating** (audit finding).
   Frontend gating is the ONLY layer until backend is fixed.

## Responsive Density for Trading UIs

Density rules that override the universal responsive defaults for financial
data:

| Viewport | Order Book | Pair List | Charts |
|----------|-----------|-----------|--------|
| Mobile | Top 5 bids + asks | Card view, 10 visible | Simplified, no overlays |
| Tablet | Top 15 bids + asks | Compact table, 20 visible | Standard with tooltips |
| Desktop | Top 25 bids + asks | Full table, virtualized | Full with overlays |
| Wide | Top 50 + depth chart | Multi-column, virtualized | Multiple chart panels |

### Rules

1. **Desktop is primary** for the trading terminal. Mobile must still be
   functional for monitoring.
2. **Font size MUST NOT go below 12px** for financial data (readability).
3. **Charts MUST be touch-friendly** on tablet (larger touch targets).

## Accessibility for Financial Data

On top of the universal accessibility basics, financial UIs need:

1. **Price levels MUST have aria-labels** with full context:
   `aria-label="Bid: 50,123.45 BRL, size 0.5 BTC, cumulative 2.3 BTC"`.
2. **Status changes MUST use `aria-live="polite"`** for updates:
   book status, connection status, alert notifications.
3. **Charts MUST have text alternatives** (summary table or description).
4. **Order entry form: Tab order MUST follow logical sequence**
   (pair → side → type → price → quantity → submit).
5. **Arrow keys for navigating order book levels.**
6. **Financial data MUST be readable** without visual styling (plain text
   fallback when CSS fails to load).
7. **Provide a high-contrast mode** for the trading terminal.

## Fintech Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `toFixed(2)` in JSX | Wrong locale, wrong precision | `formatPrice()` utility |
| Hardcoded "R$" / "$" | Breaks for USD, USDT, MXN pairs | `Intl.NumberFormat` with currency |
| Rendering 500 price levels without virtualization | DOM thrashing on every WS tick | Virtualize order book sides |
| Updating the DOM on every WS message | Re-render storm | rAF batching + per-book throttle |
| Color-only bid/ask indicator | Accessibility violation | Color + `+`/`-` + arrow |
| Persisting trading form state | Stale orders on next session | Ephemeral `useState` or non-persisted store |
| Prefilling quantity from last order | Encourages unintended trades | Always start at zero |
| Client-only PRO gating | Bypassable by any user | Gate on server too |
| Showing "0" while price stream warms up | Misleading | Skeleton / "—" with explicit "loading" aria |
