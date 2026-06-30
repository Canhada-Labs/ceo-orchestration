---
name: Frontend Data Layer & Real-Time (Universal)
description: Universal frontend data-layer patterns — server state library architecture (e.g.
  TanStack Query), client state store architecture (e.g. Zustand/Redux), WebSocket/SSE
  subscription lifecycle, cache strategy, query key conventions, mutation/invalidation
  patterns, optimistic updates, error retry/backoff, rAF batching for high-frequency
  streams, staleness UX, and state-overlap prevention for the {{PROJECT_NAME}} frontend.
  Use when working with queries, mutations, stores, WebSocket, SSE, data fetching, caching,
  or any real-time data display. Also use when the user mentions "queries", "cache",
  "stale", "refetch", "WebSocket", "SSE", "Zustand", "store", "subscription", "real-time",
  or when reviewing data flow architecture. Domain-specific data concerns (financial
  display, order-book throttling, etc.) live under
  `domains/<domain>/skills/frontend-data-layer/SKILL.md`.
trigger: Any work involving data fetching, state management, real-time data, or API integration.
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 4
risk_class: medium
stack: [typescript, react]
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 5}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: file-edit, glob: "**/queries/**"}
  - {event: file-edit, glob: "**/stores/**"}
  - {event: help-me-invoked, regex: "(?i)tanstack|zustand|redux|websocket|sse|cache|stale|refetch"}
---

# Frontend Data Layer & Real-Time — Universal

This skill captures project-agnostic data-layer patterns. Anything specific to
a business domain (financial display rules, order-book throttling, price
caching, etc.) is extracted to
`domains/<domain>/skills/frontend-data-layer/SKILL.md` and composed on
top of this baseline.

## Owners
- **Data Layer Lead** (archetype) — Query architecture, cache, stores.
- **Real-Time Engineer** (archetype) — WS, SSE, rAF batching, staleness.

> Replace with your concrete personas when adopting this skill. See
> `.claude/frontend-team.md` for the archetype → persona mapping.

## Architecture

### Data Flow
```
REST API  → fetch wrapper → server-state library (queries*.ts) → Components
WS        → ws.ts singleton → ws-store (client store + rAF) → Components
SSE       → useSSE() hook → Component local state → Components
Auth/User → auth client (RLS / session) → Auth store
```

### QueryClient Config (example — TanStack Query)
- staleTime: 30s (prevents refetch on page transitions)
- gcTime: 1h (enables IndexedDB restoration)
- retry: 1 (jittered exponential backoff, cap 5s)
- refetchOnWindowFocus: false
- Persistence: IndexedDB (maxAge 1h, excludes sensitive keys like admin/user/billing)

## Query Layer Organization

### Centralized queries.ts

All query definitions live in `src/<feature>/queries*.ts`. Components consume
them via typed hooks; they NEVER inline `useQuery` with a literal URL or key.

```typescript
// example: feature/queries.ts
export const featureQueries = {
  list: (filter: Filter) =>
    queryOptions({
      queryKey: ['feature', 'list', filter],
      queryFn: () => api.listFeatures(filter),
      staleTime: 30_000,
    }),

  detail: (id: string) =>
    queryOptions({
      queryKey: ['feature', 'detail', id],
      queryFn: () => api.getFeature(id),
      staleTime: 60_000,
    }),
};

// Component usage
const { data } = useQuery(featureQueries.detail(id));
```

### Query Key Conventions

#### Namespace Pattern
```typescript
// GOOD: Namespaced, all params in key
['feature', 'list', filter]
['feature', 'detail', id]
['admin', 'health']

// BAD: No namespace, missing params
['list']            // Missing namespace + filter
['detail', id]      // Missing namespace
```

### Rules

1. **ALL queries in `src/<feature>/queries*.ts`** — NEVER inline `useQuery` in
   components.
2. Use `queryOptions()` factories (NOT `useQuery()` wrappers).
3. **Include ALL parameters in the key** — missing params = cache collisions.
4. **Mutations MUST invalidate affected query keys.** Every mutation has a
   matching `onSuccess` that calls `queryClient.invalidateQueries({ queryKey })`.
5. **staleTime varies by data type** — tune it per query, don't globalize.

## Server State vs Client State Boundaries

| Type | Examples | Tool |
|------|----------|------|
| Server state | Any data fetched from an API, cached and synchronized | TanStack Query, SWR, RTK Query |
| Client state | UI mode, draft forms, theme, open/closed panels | Zustand, Redux, Jotai, useState |

**Rule:** Data should live in ONE place. If it comes from the server, use your
server-state library. If it's client-only UI state, use a store. NEVER both.

### State Overlap Smells

Watch for these anti-patterns — they're how data gets two sources of truth:

1. **Same data fetched by a store `setInterval` AND a server-state query.**
   Pick one. Kill the other.
2. **Client-side simulated data + server-side history of the same thing** with
   no clear "which is truth" rule. Write the rule down, enforce it in code.
3. **A store that fetches directly from the backend**, bypassing your
   server-state library. That store is now a second, invisible cache.

## Client Stores

### Store Taxonomy (example — Zustand)

| Store | Purpose | Persisted? |
|-------|---------|-----------|
| theme-store | Dark/light mode | localStorage |
| ui-mode-store | Advanced/simple mode | localStorage |
| notification-store | Alerts/notifications | localStorage (unreadCount) |
| draft-store | In-progress form drafts | NO (ephemeral) |
| workspace-store | Layout / panel arrangement | localStorage |

### Rules

1. **Stores hold client state only.** Never use a store as a secondary cache
   for server data.
2. **Persist deliberately.** Persist preferences and UI state. NEVER persist
   authenticated tier, role, permissions, or anything security-sensitive — it's
   spoofable.
3. **Expose typed selector hooks.** Components should not import the raw
   `useStore` hook; they should import `useTheme()`, `useDensity()`, etc.
4. **Use shallow comparison for array/object selectors** (e.g. Zustand's
   `useShallow`, Redux's `createSelector`) to prevent unnecessary re-renders.

## Cache Invalidation Patterns

### Rules

1. **Every mutation MUST invalidate the queries it affects.** If you edit a
   resource, invalidate its list query and its detail query.
2. **Invalidate by key prefix**, not by exact key, when a mutation affects an
   unknown subset: `invalidateQueries({ queryKey: ['feature'] })`.
3. **Use `setQueryData` for targeted updates** when you already have the new
   server value in the mutation response — skips a refetch.
4. **Never rely on `refetchOnWindowFocus` to sync state.** It's a safety net,
   not a strategy.

## Optimistic Updates

Use optimistic updates for mutations where the user needs instant feedback and
the failure mode is recoverable.

```typescript
const mutation = useMutation({
  mutationFn: updateItem,
  onMutate: async (next) => {
    await queryClient.cancelQueries({ queryKey: ['item', next.id] });
    const previous = queryClient.getQueryData(['item', next.id]);
    queryClient.setQueryData(['item', next.id], next);
    return { previous };
  },
  onError: (_err, next, ctx) => {
    // Roll back
    if (ctx?.previous) {
      queryClient.setQueryData(['item', next.id], ctx.previous);
    }
  },
  onSettled: (_data, _err, next) => {
    queryClient.invalidateQueries({ queryKey: ['item', next.id] });
  },
});
```

### Rules

1. **Cancel in-flight queries before mutating the cache** so a stale fetch
   can't clobber your optimistic value.
2. **Always snapshot the previous value** for rollback.
3. **Always `invalidateQueries` on settle** so the final state matches the
   server.
4. **Do NOT use optimistic updates for operations that cannot be safely rolled
   back** (payments, irreversible submissions). Show a pending state instead.

## Error Retry and Backoff

### Default Policy

- **retry: 1** — one automatic retry, then surface the error.
- **Jittered exponential backoff**, capped (e.g. 5s). Don't hammer a struggling
  backend.
- **Do NOT retry 4xx errors** — they won't change on retry. Retry only 5xx and
  network errors.

### Error Surfacing

1. **Show the error in the same surface the data would have rendered in.**
   Don't toast a silent query failure — the user will stare at a blank chart.
2. **Provide a retry button** so users aren't stuck waiting for the automatic
   retry.
3. **Log errors to your monitoring system** with the query key and params so
   they're searchable in Sentry/Datadog.

## WebSocket Architecture (Generic Transport)

### Connection Lifecycle

- **Singleton connection:** `export const ws = new AppWebSocket()`. Never
  construct `new WebSocket()` per component.
- **Lazy connect:** The WS opens on the first subscribe/setChannels call.
- **Ready protocol:** Wait for a server `ready` message before reporting
  connected. That gives the server time to load subscriptions.
- **Reconnect:** Exponential backoff (1s → 30s) + jitter (±25%). Honour
  backoff codes (e.g. rate-limit code 4008 = 10s minimum).
- **Heartbeat:** Ping every 25s, staleness check every 30s. Force reconnect
  after 90s of no message.

### WS Store (rAF Batching Pattern)

High-frequency streams can fire faster than the browser's refresh rate. Coalesce
updates inside `requestAnimationFrame`:

- **rAF batching:** Cap N messages per frame (e.g. 30). Carry excess to the
  next frame.
- **Per-key throttle:** Optional millisecond cap per message key to prevent one
  noisy topic from starving the others.
- **Delta protocol:** Apply deltas to the pending (not-yet-flushed) frame so
  overlapping deltas collapse before React sees them.
- **23 typed selector hooks** isolate components from the raw store. Components
  NEVER import `useWSStore` directly — they import `useChannelState(id)` etc.,
  which uses `useShallow` for array/object selectors.

### Subscription Hooks

Wrap subscription management in tiny hooks with explicit cleanup:

- `useWSChannels(channels)` — subscribes on mount, sets channels to `[]` on
  unmount.
- Read-only listener hooks don't subscribe themselves; they just read state and
  need no cleanup.
- **Every hook MUST clean up on unmount.** A subscription leak is usually
  invisible until a user opens/closes 50 panels and the WS is throttled.

## SSE Architecture (Generic Transport)

- **Generic factory:** `useSSE(endpoint)` with reconnect, circuit breaker, and
  cleanup in one place. Per-consumer hooks (`useSSEAlerts`,
  `useSSENotifications`, etc.) sit on top of the factory.
- **Let the browser reconnect.** Do not wrap `EventSource` in a manual
  reconnect loop — it already retries. Track the reconnect count for alerting
  instead.
- **Close on unmount.** `source.close()` in the effect cleanup is mandatory.
- **Cancel any manual reconnect/backoff timers on unmount** — dangling timers
  are the most common SSE leak.

## Staleness UX

When real-time transports drop, the UI MUST communicate it — silent stale data
is worse than no data.

- **ConnectionStatus dot** — Green / Yellow / Red with hysteresis (e.g. 3s
  grace) so it doesn't flicker.
- **Offline banner** — Full-width warning when WS is disconnected for more
  than a few seconds.
- **Per-feature staleness tiers** — Fresh (<15s), Stale (15-60s),
  Degraded (60-120s), Offline (>120s). Label which tier each data feed is in.
- **REST fallback polling** — When the WS is down, critical feeds fall back to
  REST polling at a low rate (e.g. every 10s).

## Generic Data-Fetching Rules

1. **Queries are declarative.** The query key is the identity of the data. Two
   identical keys MUST return the same data.
2. **Mutations are verbs.** Every mutation is named for the action it performs
   and has a matching invalidation.
3. **Loading states MUST be skeletons**, not spinners, for structured data.
   Skeletons preserve layout.
4. **Error states MUST be recoverable.** Always give the user a way forward.
5. **Real-time and query data MUST NOT both feed the same component from
   independent paths.** Pick one source of truth per feature.
6. **Persist only what you can safely rehydrate.** If the persisted data could
   be wrong on next load (tier, permissions, session), don't persist it.
