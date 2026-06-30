---
name: Frontend Performance Optimization
description: Bundle analysis, code splitting, lazy loading strategy, rendering optimization, virtualization patterns, Core Web Vitals targets, memoization correctness, network performance, image optimization, and build tool tuning (e.g. Vite) for the {{PROJECT_NAME}} frontend. Use when analyzing bundle size, optimizing rendering, adding virtualization to large lists, reviewing memoization patterns, tuning build config, or improving Core Web Vitals scores.
owner: Frontend Performance Engineer (archetype)
---

# Frontend Performance Optimization — {{PROJECT_NAME}} Frontend

> **Owner:** Frontend Performance Engineer (archetype)
> **Scope:** `{{FRONTEND_REPO_PATH}}/` — the codebase
> **Lighthouse CI:** `lighthouserc.js` — performance > 0.7, LCP < 4s, CLS < 0.1

## Performance Lead Profile

**Background archetype:** Senior web-performance specialist. Expert in bundle analysis, rendering profiling, Core Web Vitals measurement, and runtime optimization. Profiles before breakfast. Measures everything.

**Superpower:** Looks at a component tree and spots the unnecessary re-render chain that causes 200ms jank.

**Mantra:** *"If the list has more than 50 items and no virtualization, the user with a 2018 phone will hate you."*

## Current Metrics (V2 Audit 2026-03-24)

| Metric | Value | Target |
|--------|-------|--------|
| Initial gzip | ~218KB | < 250KB |
| Main chunk (raw) | 793KB | < 500KB |
| Largest chunk | vendor-pdf 1.5MB (lazy) | Lazy = OK |
| Lazy-loaded routes | 38/38 (100%) | 100% |
| `memo()` adoption | 445 files | > 90% of components |
| `useMemo` usage | 877 occurrences | Used where needed |
| `useCallback` usage | 374 in 119 files | Needs improvement |
| Virtualized lists | e.g. 4 (main data tables, search results, event feeds) | All lists > 50 items |
| Inline `style={{}}` | ~1,297 | Reduce in hot paths |

## Bundle Strategy

### Manual Chunks (vite.config.ts)
```
vendor-charts    → recharts + lightweight-charts (174KB gzip)
vendor-supabase  → @supabase/supabase-js (44KB gzip)
vendor-pdf       → @react-pdf/renderer (406KB brotli, LAZY)
vendor-grid      → react-grid-layout
vendor-query     → @tanstack/react-query
vendor-router    → react-router-dom
vendor-i18n      → i18next + react-i18next
vendor-zustand   → zustand
vendor-sonner    → sonner (toasts)
vendor-radix     → @radix-ui/*
vendor-helmet    → react-helmet-async
```

### Rules
1. **Never import heavy libs at top level** — always `React.lazy()` or dynamic `import()`
2. **react-pdf** only used in 2 components — MUST stay lazy
3. **zxcvbn** (454KB) is lazy-loaded for password strength — acceptable
4. **lucide-react** (44MB in node_modules) tree-shakes to ~20KB — use named imports only

## Rendering Performance

### Memoization Rules

| Pattern | When to use | When NOT to use |
|---------|------------|-----------------|
| `memo()` | Every component that receives props | Components that always re-render (root providers) |
| `useMemo` | Expensive computations, derived state, array/object creation | Simple primitives, single-line operations |
| `useCallback` | Functions passed as props to memo'd children, event handlers in `.map()` | Functions only used in the same component |

### Anti-Patterns to Detect

```tsx
// BAD: New object every render, defeats child memo()
<ChildComponent style={{ color: 'red' }} />

// GOOD: Stable reference
const style = useMemo(() => ({ color: 'red' }), []);
<ChildComponent style={style} />

// BAD: New function every render in .map()
{items.map(item => (
  <Row onClick={() => handleClick(item.id)} />
))}

// GOOD: Stable callback
const handleClick = useCallback((id: string) => { ... }, []);
{items.map(item => (
  <Row onClick={handleClick} itemId={item.id} />
))}

// BAD: Component created during render
function Parent() {
  const Badge = ({ label }: { label: string }) => <span>{label}</span>;
  return <Badge label="hi" />;
}

// GOOD: Extract outside
const Badge = memo(({ label }: { label: string }) => <span>{label}</span>);
```

### React Compiler (react-hooks/purity)

The React Compiler enforces render purity. Common violations:

| Violation | Fix |
|-----------|-----|
| `Date.now()` in render | Use `useRef(Date.now())` or state with interval |
| `ref.current` in render | Move to useEffect or event handler |
| `Math.random()` in render | Move to useState initializer |
| `new Date()` in render | Same as Date.now() |

## Virtualization

### When to Virtualize
- Any list/table with **>50 items** that updates frequently
- Any list/table with **>200 items** regardless of update frequency
- High-frequency feeds (e.g. data that updates every 50ms)
- Large data tables (thousands of rows)

### Implementation Pattern (react-window)
```tsx
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={containerHeight}
  itemCount={data.length}
  itemSize={ROW_HEIGHT}
  width="100%"
  overscanCount={8}
>
  {({ index, style }) => (
    <div style={style}>
      <Row data={data[index]!} />
    </div>
  )}
</FixedSizeList>
```

### Currently Virtualized (examples)
- `DataTable.tsx` — thousands of rows (react-window)
- `EntitySelector.tsx` — search results (react-window)
- `EventsFeed.tsx` — event stream (react-window)
- `ActivityFeed.tsx` — activity log (manual virtual scroll)

### Should Virtualize (backlog examples)
- `DetailTable.tsx` — detail rows
- `SignalsPanel.tsx` — signals / anomaly list
- `RankingTable.tsx` — ranking rows
- `ScheduleView.tsx` — event list
- `LeaderboardTable.tsx` — leaderboard list

## Network Performance

### Patterns
1. **Batch queries:** Use `/api/page/{name}` endpoints — 1 request instead of 5-10
2. **Cache seeding:** After batch, seed individual query caches with `queryClient.setQueryData`
3. **Prefetch on hover:** `usePrefetchRoute` prefetches route data on hover/focus/touchstart
4. **WS-first:** `wsData ?? httpData` — prefer WebSocket, REST as fallback
5. **Relaxed polling:** When WS active, increase REST `refetchInterval` (15s → 60s)
6. **staleTime tiers:** real-time 5-15s, live 30-60s, semi-static 2-5min, static 15min

### Image Rules
1. All `<img>` must have `loading="lazy"` (except above-fold hero)
2. Small icons (e.g. 20×20 logos) generally need no further optimization
3. OG image should be WebP (future: image optimization pipeline)

## Core Web Vitals Targets

| Metric | Target | Current |
|--------|--------|---------|
| LCP | < 2.5s | < 4s (Lighthouse CI) |
| CLS | < 0.1 | < 0.1 (Lighthouse CI) |
| INP | < 200ms | Not measured |
| FCP | < 1.8s | Not measured |
| TTFB | < 800ms | Vercel edge ~50ms |

## Performance Review Checklist (Ines)

Before approving performance-sensitive changes:
- [ ] No new top-level imports of heavy libraries
- [ ] Lists > 50 items use virtualization
- [ ] Components receiving props use `memo()`
- [ ] Expensive computations wrapped in `useMemo`
- [ ] Event handlers in `.map()` use `useCallback`
- [ ] No inline `style={{}}` in hot-path components
- [ ] Images have `loading="lazy"`
- [ ] Queries have appropriate `staleTime`
- [ ] No `Date.now()` or `Math.random()` in render path
## Adopter Note — Metrics Snapshot is Originating-Project (PLAN-044 P0-12)

The §Current Metrics (V2 Audit 2026-03-24) table and the
§Bundle Strategy / §Manual Chunks block contain values tied
to the originating `ceo-orchestration` dogfood frontend — a
React + Vite + Tailwind fintech console on a specific
dependency set. Concrete numbers include:

- `Initial gzip ~218KB`, `Main chunk (raw) 793KB`,
  `vendor-pdf 1.5MB (lazy)`, `Lazy-loaded routes 38/38`,
  `memo() 445 files`, `useMemo 877`, `useCallback 374 in 119`,
  `Virtualized lists ~4`, `Inline style={{}} ~1,297`.
- Named vendor chunks `vendor-charts` / `vendor-supabase` /
  `vendor-pdf` / `vendor-grid` / `vendor-query` / `vendor-router`
  / `vendor-i18n` / `vendor-zustand` / `vendor-sonner` /
  `vendor-radix` / `vendor-helmet` with specific gzip / brotli
  sizes.
- The §Lighthouse CI banner (`performance > 0.7, LCP < 4s, CLS
  < 0.1`) and its targets.

For your adopter project, run your own bundle audit (e.g.
`vite build --mode=analyse`, `webpack-bundle-analyzer`, or the
equivalent for your toolchain) and replace the current-metrics
table with your numbers before optimisation work. The rules
and patterns (never import heavy libs at top level, lazy-load
routes, memoise correctly, virtualise lists > 50 items) are
universal; the numbers and vendor-chunk names are not.
