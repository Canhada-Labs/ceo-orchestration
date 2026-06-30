---
name: Fintech Frontend Data Layer & Real-Time
description: Fintech-specific frontend data-layer patterns — Financial Display Rules
  (safe-number helpers, locale-aware formatters, precision-per-pair), order-book-specific
  WS throttling/rAF batching (30 books/frame, 50ms per exchange:pair), price/volume caching
  concerns, project-specific endpoint audit findings (/stats, fear-greed, duplicate keys),
  and trading-domain data patterns. EXTENDS the universal skill at
  `frontend/frontend-data-layer/SKILL.md` — read that first, then apply the rules
  here. Use when working with market data queries, orderbook streams, price formatting,
  trading mutations, or any fintech-domain data code.
trigger: Any fintech-domain data-layer work — market data, orderbooks, price display, trading mutations.
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 4
risk_class: medium
stack: [typescript, react]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 6}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)orderbook|market.?data|ws.?throttl|raf|price.?stream"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/queries/**"
  - "**/orderbook/**"
  - "**/market-data/**"
  - "**/websocket/**"
  - "**/ws/**"
---

# Fintech Frontend Data Layer & Real-Time

> **This skill extends `frontend/frontend-data-layer/SKILL.md`.** Read
> the universal skill first for query layer organization, server vs client
> state boundaries, cache invalidation, optimistic updates, error retry, generic
> WS/SSE transports, and staleness UX. This document layers fintech-specific
> rules on top.

## Current State (2026-03-23 Audit)
- **Query Architecture: 7/10** — 504 keys, 0 inline violations, but 3 state overlaps
- **Real-Time: 9.2/10** — Exemplary WS lifecycle, rAF batching, staleness UX
- **Financial Display: 8/10** — Zero parseFloat, 95% typed safe-number helper coverage, 202 raw toFixed

## Audit Reference
Full findings: `FRONTEND_AUDIT_2026-03-23.md` — Queries (findings 38-42), Real-time (F3, F12-F15)

## Fintech Data Flow

On top of the universal data flow, the fintech app has these specific lanes:

```
Engine REST API → engineFetch() → TanStack Query (queries*.ts) → Components
Engine WS       → ws.ts singleton → ws-store.ts (Zustand + rAF) → Components
Engine SSE      → useSSE() hook → Component local state → Components
Supabase        → supabase client (anon_key + RLS) → Auth/User data
```

## Fintech-Specific Query Key Examples

```typescript
// Market data
['engine', 'book', exchange, pair]
['engine', 'arb', 'v2', lot, fees, limit]
['engine', 'ticker', exchange, pair]

// Admin / health
['admin', 'health']
```

### Fintech-Specific Rules

1. `staleTime` varies heavily — order books: 0 (use WS), tickers: 5s,
   arbitrage: 30s, health: 15s.
2. Persistence to IndexedDB MUST exclude `admin/*`, `partners/*`, and
   `user/*` keys — these contain privileged data.

## Known Query Issues (Audit Findings)

- **4 mutations missing invalidation:** circuit breaker trip/reset, quote
  engine pause/resume. Add `invalidateQueries` calls to these.
- **Duplicate query for `/stats`** — same endpoint registered under both the
  `status` and `health` namespaces. Pick one.
- **3 different fear-greed queries from 3 endpoints** — consolidate into a
  single source.

## State Overlap Issues (HIGH — 3 found)

1. **Exchange data**: `useExchangeRegistry` (30s setInterval) AND
   `healthQueries.exchanges()` (15s refetchInterval) — TWO sources of truth.
2. **Paper trading**: Client-side store AND server-side queries — which is
   truth?
3. **Subscription tier**: Zustand store fetches from Supabase directly,
   bypassing React Query.

**Fix:** Data lives in ONE place. If it comes from the server, use React
Query. If it's client-only UI state, use Zustand. NEVER both.

## Fintech Zustand Stores (13 total)

### In `src/stores/` (6):
| Store | Purpose | Persisted? |
|-------|---------|-----------|
| theme-store | Dark/light mode | localStorage |
| trading-store | Order form state | NO (ephemeral) |
| paper-trading-store | Paper trading sim | localStorage |
| notification-store | Alerts/notifications | localStorage (unreadCount) |
| subscription-store | Billing tier | localStorage (WARNING: spoofable) |
| ui-mode-store | Advanced/simple mode | localStorage |

### Across codebase (7 more):
`ws-store`, `exchange-registry`, `precision-service`, `engine-auth`,
`tour-store`, `font-store`, `workspace-store`.

### Rules specific to these stores

1. **`trading-store` MUST remain ephemeral.** Persisting order-form state
   causes stale orders on next session.
2. **`subscription-store` is spoofable** — never use it as the authoritative
   tier check on the backend. Gate server-side too.
3. **`precision-service` MUST be the only source of per-pair decimal
   precision** used by formatters.

## Order Book Real-Time Throttling

Order books are the hottest feed in the app. Layer these rules on top of the
universal WS/rAF pattern:

- **rAF batching cap: 30 books per frame.** Excess carries to the next frame.
- **Per-book throttle: 50ms per exchange:pair** (max 20 updates/sec/book).
- **Delta protocol** is applied to the pending (not-yet-flushed) book so
  overlapping deltas collapse before the component re-renders.
- **23 selector hooks with proper isolation** (`useShallow` for arrays).
  Components NEVER import `useWSStore` directly — they import typed hooks like
  `useBookForPair`, `useSpread`, `useDepth`.
- **Zero WS subscription leaks found in audit** — keep it that way. Every
  subscribe has a matching unsubscribe on unmount.

### Subscription Hooks (project-specific)

- `useWSChannels` — proper cleanup on unmount (setChannels([]))
- `useUWWSChannels` — proper cleanup on unmount
- `useWsFallbackInterval` — read-only, no cleanup needed

## SSE Consumers (fintech)

- `useSSEAlerts` — user-facing alert triggers
- `useSSEPredictions` — streaming predictions / AI outputs

**Known issue:** reconnect timers not cancelled on unmount (MEDIUM). Fix is to
clear the timers in the effect cleanup.

## Staleness UX (fintech thresholds)

On top of the universal staleness UX rules, the fintech app uses these
thresholds:

- **ConnectionStatus:** Green/Yellow/Red dot with hysteresis (3s grace).
- **EngineOfflineBanner:** Full-width red banner when WS disconnected > 5s.
- **useEffectiveExchanges:** Stale (15s), Degraded (60s), Offline (120s).
- **useWsFallbackInterval:** Falls back to 10s REST polling when WS is down.

## Financial Display Rules (Mei's Domain)

This is the heart of the fintech data layer. These rules are non-negotiable.

### NEVER:
- `parseFloat()` — use `safeNumber()` from the project's typed safe-number
  helpers (e.g. a `safe.ts` module).
- `Number()` on financial values — use `safeNumber()`.
- Raw `.toFixed()` for display — use `formatFixed()`, `fmtNum()`,
  `formatPrice()`.
- Hardcode decimal points — use `getUserLocale()` for locale-aware formatting.

### ALWAYS:
- Use `usePairPrecision()` for per-pair decimal precision.
- Use format functions from your project's shared formatter module (typically `lib/format` — 24 locale-aware formatters expected).
- Use `safeNumber / safeFixed / safePct / safeMul / safeAdd / safeDivide` from
  the project's typed safe-number helpers (e.g. a `safe.ts` module).
- Handle `null` / `undefined` / `NaN` with fallback values — a missing price
  is NOT zero.

### 202 raw `toFixed()` violations found — concentrated in:
- Predictions / Polymarket components (~80)
- Trading strategy components (~20)
- Shared widgets (~30)

**Fix plan:** Each violation is a small PR. Do a sweep per component tree,
not a single mega-commit.

## Fintech-Specific Data Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `parseFloat()` on a price string | Precision loss | `safeNumber()` |
| Raw `.toFixed()` in JSX | Wrong locale, wrong precision | `formatPrice()` / `formatFixed()` |
| Hardcoded decimal count | Ignores per-pair precision | `usePairPrecision()` |
| WS store imported directly in a component | Re-render storms | Typed selector hooks with `useShallow` |
| Trading form state in a persisted store | Stale orders on next session | Ephemeral `trading-store` |
| Subscription tier read only client-side | Spoofable | Gate on server, treat client as UX hint |
| Two sources of truth for exchange data | Races, inconsistent state | One source (pick React Query OR store) |
| Missing invalidation after quote-engine mutation | Stale quote display | Add `invalidateQueries` |
