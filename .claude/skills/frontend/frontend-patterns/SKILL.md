---
name: frontend-patterns
description: >
  Universal frontend development patterns for the {{PROJECT_NAME}} platform.
  Covers your build tool (e.g. Vite, Webpack) + your UI framework (e.g. React,
  Vue, Svelte) patterns, real-time data display (WebSocket client, SSE),
  virtualization for large lists, memoization strategies, composition patterns
  (compound components, render props, custom hooks), error boundaries, lazy
  loading and code splitting, responsive design, accessibility basics, and
  performance monitoring. Use when working on any frontend code, UI
  components, real-time updates, responsive layout, accessibility, or
  performance optimization. Domain-specific patterns (finance, e-commerce,
  healthcare, etc.) live under
  domains/<domain>/skills/frontend-patterns/SKILL.md and extend this universal
  baseline. Frontend repo: {{FRONTEND_REPO_PATH}}. NOTE: examples are
  prescriptive to React + Vite; adapt to your chosen stack.
owner: Frontend Engineer (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/design/design-whimsy-injector.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: topic_only
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 5
risk_class: low
stack: [typescript, react, vite]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 9}
  fintech: {active: true, priority: 7}
  trading-readonly: {active: true, priority: 9}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: file-edit, glob: "**/*.tsx"}
  - {event: help-me-invoked, regex: "(?i)react|vite|memo|hook|render.?prop"}
source: affaan-m/ecc@81af4076 skills/react-patterns/
license: MIT
---

# Frontend Patterns (Universal)

This skill captures project-agnostic frontend patterns. Anything specific to a
business domain (financial display, tier gating, domain-specific widgets, etc.)
is extracted to `domains/<domain>/skills/frontend-patterns/SKILL.md` and
composed on top of this baseline.

## Project Overview

| Item | Value |
|------|-------|
| Repo | `{{FRONTEND_REPO_PATH}}` |
| Stack | your build tool (e.g. Vite, Webpack) + your UI framework (e.g. React, Vue, Svelte) + TypeScript (example: React 19 + Vite 7 + TypeScript) |
| Deploy | Vercel (auto-deploy on push) |
| Real-time | WebSocket + SSE |
| Backend | `{{BACKEND_URL}}` |

## Architecture Principles

### Component Hierarchy

```
App
  ├── Layout (responsive shell, sidebar, header)
  │     ├── AuthProvider (session, user identity)
  │     ├── RealTimeProvider (WS + SSE connections)
  │     └── ThemeProvider (light/dark, density)
  ├── Pages (route-level components)
  └── Shared (widgets, formatters, hooks)
        ├── Data formatters (numbers, dates, locale)
        └── Hooks (useWebSocket, useSSE, data hooks)
```

### Rules

1. **Pages are thin.** They compose widgets, they do not contain business logic.
2. **Widgets are self-contained.** Each widget fetches its own data or receives
   it via props. No implicit global state dependencies.
3. **Every component that displays formatted data MUST use shared formatting
   utilities.** Never format numbers/dates/currencies inline.
4. **Providers wrap the whole app, not individual pages.** Connections and
   global state should be mounted once.

## Composition Patterns

### Compound Components

Use when a parent and its children share implicit state (tabs, accordions,
menus). The parent exposes context, children consume it.

```typescript
// Parent sets context, children consume it
const TabsContext = createContext<TabsState | null>(null);

function Tabs({ children, defaultValue }: TabsProps) {
  const [active, setActive] = useState(defaultValue);
  return (
    <TabsContext.Provider value={{ active, setActive }}>
      <div className="tabs-root">{children}</div>
    </TabsContext.Provider>
  );
}

Tabs.List = function TabsList({ children }: { children: ReactNode }) {
  return <div role="tablist">{children}</div>;
};

Tabs.Trigger = function TabsTrigger({ value, children }: TriggerProps) {
  const ctx = useContext(TabsContext)!;
  return (
    <button
      role="tab"
      aria-selected={ctx.active === value}
      onClick={() => ctx.setActive(value)}
    >
      {children}
    </button>
  );
};
```

### Render Props / Function as Children

Use when you want to expose state/logic without dictating the DOM.

```typescript
function Toggle({ children }: { children: (state: ToggleState) => ReactNode }) {
  const [on, setOn] = useState(false);
  return <>{children({ on, toggle: () => setOn(v => !v) })}</>;
}

// Usage
<Toggle>
  {({ on, toggle }) => (
    <button onClick={toggle}>{on ? "On" : "Off"}</button>
  )}
</Toggle>
```

### Custom Hooks

Encapsulate stateful logic so it can be reused across components. Rule of thumb:
if you'd copy-paste `useState + useEffect` between two components, extract a
hook.

```typescript
function useOnlineStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}
```

### Rules

1. **Prefer composition over props drilling.** If a prop is passed 3+ levels,
   use context or a store.
2. **Custom hooks start with `use`.** The name MUST reflect behavior, not
   implementation (`useAuth`, not `useJWTFromLocalStorage`).
3. **One hook = one concern.** Don't bundle unrelated state into a mega-hook.

## Error Boundaries

React renders errors inside a component tree crash the whole subtree unless
caught by an error boundary. Every route-level component should be wrapped in
one.

```typescript
class ErrorBoundary extends React.Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Report to your monitoring system (Sentry, Datadog, etc.)
    reportError(error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

// Usage
<ErrorBoundary fallback={<ErrorScreen />}>
  <Route path="/dashboard" element={<Dashboard />} />
</ErrorBoundary>
```

### Rules

1. **Wrap each route.** One crashed page should not kill the whole app.
2. **Wrap risky widgets.** Third-party embeds, chart libraries, anything that
   parses untrusted input.
3. **Fallback MUST be useful.** Show a retry button and a way to navigate away.
4. **Error boundaries do NOT catch async errors.** Wrap async calls in
   try/catch and push errors to state to trigger the boundary.

## Lazy Loading and Code Splitting

### Route-Level Splitting

```typescript
import { lazy, Suspense } from "react";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Settings = lazy(() => import("./pages/Settings"));

function AppRoutes() {
  return (
    <Suspense fallback={<RouteSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

### Component-Level Splitting

For heavy widgets (charts, editors, PDF viewers):

```typescript
const HeavyChart = lazy(() =>
  import("./charts/HeavyChart").then(m => ({ default: m.HeavyChart }))
);

<Suspense fallback={<ChartSkeleton />}>
  <HeavyChart data={data} />
</Suspense>
```

### Rules

1. **Split at route boundaries first.** That's the highest ROI.
2. **Split heavy libraries separately** (chart libs, rich text editors).
3. **Prefetch on hover** for critical routes:
   `onMouseEnter={() => import("./Dashboard")}`.
4. **Suspense fallback MUST match layout** to avoid cumulative layout shift.
5. **Measure bundle impact** with your bundler's analyzer before and after.

## Real-Time Data Display

### WebSocket Client

```typescript
// Hook pattern for WS connection
function useWebSocket(channels: string[]) {
  const wsRef = useRef<WebSocket | null>(null);
  const [data, setData] = useState<Map<string, unknown>>(new Map());

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      // Subscribe to channels
      ws.send(JSON.stringify({
        type: "subscribe",
        channels,
      }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setData(prev => {
        const next = new Map(prev);
        next.set(msg.key, msg.data);
        return next;
      });
    };

    // Reconnect on close
    ws.onclose = () => {
      setTimeout(() => reconnect(), 2000 + Math.random() * 1000);
    };

    return () => ws.close();
  }, [channels]);

  return data;
}
```

#### WS Rules

1. **Always reconnect on close** with jittered backoff (2-5s).
2. **Subscribe only to visible channels.** Unsubscribe when component unmounts.
3. **Batch state updates.** Use `unstable_batchedUpdates` or React 19 automatic
   batching to avoid re-render storms.
4. **Never parse WS messages on the main thread** if volume is high. Use a
   dedicated Web Worker for parsing + diffing.
5. **Connection count:** Max 1 WS connection per client. Multiplex channels.

### SSE (Server-Sent Events)

```typescript
// Hook pattern for SSE
function useSSE(endpoint: string) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const source = new EventSource(`${API_URL}${endpoint}`, {
      withCredentials: true,
    });

    source.onmessage = (event) => {
      setData(JSON.parse(event.data));
    };

    source.onerror = () => {
      // Browser auto-reconnects SSE
      // But track reconnect count for alerting
    };

    return () => source.close();
  }, [endpoint]);

  return data;
}
```

#### SSE Rules

1. **SSE auto-reconnects.** Do not implement manual reconnect logic.
2. **Use SSE for low-frequency push** (alerts, status changes, analytics).
3. **Use WS for high-frequency bidirectional data.**
4. **Never open multiple SSE connections to the same endpoint.**

## Deriving and Locating State

### Render is a pure function of props and state

Derive values during render. Storing a derived value in `useState` and
syncing it with `useEffect` adds an extra render cycle, can desync from
its source, and hides the data flow.

```typescript
// GOOD — derive during render
const total = items.reduce((sum, i) => sum + i.price * i.qty, 0);

// BAD — derived state kept in an effect
const [total, setTotal] = useState(0);
useEffect(() => {
  setTotal(items.reduce((sum, i) => sum + i.price * i.qty, 0));
}, [items]);
```

### Where should this state live?

Reach for the least powerful option that works; escalate only when the
current one hurts.

```
Used by one component?              → useState inside it
Parent + a few descendants?         → lift to nearest common ancestor
Distant branches, low-frequency
  reads (theme, auth, locale)?      → React Context
High-frequency updates, shared?     → external store (Zustand / Jotai / Redux)
Derived from the server?            → server-state library (see below)
```

Most pages need neither context nor a global store. Resist the
abstraction until duplicated lifting becomes painful — and when you do
reach for context, **split it by concern** (one context per axis) so a
theme change does not re-render auth consumers. For external stores,
subscribe through `useSyncExternalStore` (or the store's own hook, which
uses it) so reads stay safe under concurrent rendering.

### Which fetching tool?

| Need | Tool |
|------|------|
| Per-request data in a server-component router | server-side `await fetch()` |
| Client cache + mutations + invalidation | TanStack Query |
| Lightweight client cache + revalidation | SWR |
| Real-time subscriptions | SSE / WebSocket (see Real-Time Data Display) |
| One-off, fire-and-forget | `fetch()` in an event handler |

Avoid `useEffect` + `fetch` for application data: it races, has no cache,
no retry, and no Suspense integration. The existing anti-pattern
"Fetching on every render" is the same failure in a different shape.

## Server and Client Components (RSC)

Frameworks with a React Server Components model (for example the Next.js
App Router) split the tree into two runtimes. Getting the boundary right
is the difference between shipping a little JS and shipping a lot.

```typescript
// Server Component — the default. Async, runs on the server, ships no JS for itself.
export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id);
  if (!product) return notFound();
  return <ProductView product={product} />;   // pass serializable data down
}

// Client Component — opt in explicitly; needed for state, effects, event handlers.
"use client";
export function AddToCart({ id }: { id: string }) {
  const [pending, start] = useTransition();
  return (
    <button disabled={pending} onClick={() => start(() => addToCart(id))}>
      {pending ? "Adding…" : "Add to cart"}
    </button>
  );
}
```

Boundary rules:

1. **Server → Client:** pass serializable props or `children`. Functions,
   class instances, and Dates-with-methods do not cross.
2. **Client → Server:** invoke a server action from a `<form action={…}>`
   or an event handler — never `import` a server component into a client
   component file. Compose them via `children` instead.
3. **A server action is a public endpoint.** Authenticate and authorize
   inside it; the client's gating is not a security boundary.

## Forms (React 19 Actions and Optimistic UI)

For new code, prefer form *actions* over hand-wired `onSubmit` +
`useState`. `useActionState` gives you pending state and a return channel
for validation errors with no manual plumbing.

```typescript
"use client";
import { useActionState } from "react";

export function ProfileForm() {
  const [state, action, pending] = useActionState(updateProfile, { error: null });
  return (
    <form action={action}>
      <input name="name" required />
      <button type="submit" disabled={pending}>Save</button>
      {state.error && <p role="alert">{state.error}</p>}
    </form>
  );
}
```

- **Controlled inputs** only when the value drives other UI, formats on
  each keystroke, or needs live validation — otherwise let the form own
  the value (uncontrolled + form action).
- **Reach for a form library** (React Hook Form, TanStack Form) at the
  first sign of multi-step flows, dynamic field arrays, or cross-field
  validation. Rolling your own past trivial complexity is a maintenance
  trap.
- **Optimistic UI** with `useOptimistic`: render the intended end-state
  immediately, then reconcile when the server responds. The reduced
  perceived latency is worth the reconciliation code for send / like /
  toggle interactions.

```typescript
const [optimistic, addOptimistic] = useOptimistic(
  messages,
  (state, next: Message) => [...state, next],
);
```

## State Management Patterns

### Server State vs Client State

| Type | Examples | Tool |
|------|----------|------|
| Server state | Data fetched from APIs, cached and synchronized | TanStack Query, SWR, RTK Query |
| Client state | UI mode, form drafts, theme, open/closed panels | Zustand, Redux, Jotai, useState |

**Rule:** Data lives in exactly one place. If it comes from the server, it
belongs to your server-state library. If it's ephemeral UI state, it belongs to
a client store or component state. Never both.

### Zustand Store Pattern (Example)

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ThemeState {
  mode: "light" | "dark";
  toggle: () => void;
  set: (mode: "light" | "dark") => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: "light",
      toggle: () => set((s) => ({ mode: s.mode === "light" ? "dark" : "light" })),
      set: (mode) => set({ mode }),
    }),
    { name: "theme-store" }
  )
);
```

### Redux Slice Pattern (Example)

```typescript
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

const uiSlice = createSlice({
  name: "ui",
  initialState: { sidebarOpen: false, density: "comfortable" as "comfortable" | "compact" },
  reducers: {
    toggleSidebar: (state) => { state.sidebarOpen = !state.sidebarOpen; },
    setDensity: (state, action: PayloadAction<"comfortable" | "compact">) => {
      state.density = action.payload;
    },
  },
});

export const { toggleSidebar, setDensity } = uiSlice.actions;
export default uiSlice.reducer;
```

### Rules

1. **Start with `useState`.** Only reach for a store when state is shared across
   unrelated components.
2. **Persist deliberately.** Persist theme/preferences. Do NOT persist sensitive
   state or data that can drift from the server.
3. **Never store derived data.** Compute it with selectors or `useMemo`.
4. **Selectors MUST be stable.** Use `useShallow` (Zustand) or
   `createSelector` (Redux) for arrays and objects to avoid re-render churn.

## Virtualization for Large Lists

### When to Virtualize

Virtualize any list that can grow beyond a few hundred items or that renders
heavy row components. Rule of thumb: if more than ~100 DOM nodes would be
rendered for the list, virtualize it.

### Pattern (react-window or @tanstack/virtual)

```typescript
import { useVirtualizer } from "@tanstack/react-virtual";

function VirtualizedList<T>({ items, renderRow }: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,  // row height in px
    overscan: 10,            // render 10 extra rows outside viewport
  });

  return (
    <div ref={parentRef} style={{ height: "600px", overflow: "auto" }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.key}
            style={{
              position: "absolute",
              top: 0,
              transform: `translateY(${virtualRow.start}px)`,
              height: `${virtualRow.size}px`,
              width: "100%",
            }}
          >
            {renderRow(items[virtualRow.index])}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Rules

1. **Never render more than ~100 DOM nodes for a list.** Virtualize everything larger.
2. **estimateSize MUST be accurate.** Variable row heights cause scroll jank.
3. **overscan=5-10** for smooth scrolling without blank flashes.
4. **Stable keys from data**, never array index.

## Memoization Strategies

### When to Memoize

| Pattern | When to Use | When NOT to Use |
|---------|-------------|-----------------|
| `React.memo()` | Components receiving stable props that re-render due to parent | Components that always re-render anyway |
| `useMemo()` | Expensive computation (sorting, filtering, aggregation) | Simple value derivation |
| `useCallback()` | Callbacks passed to memoized children | Callbacks used only in the same component |
| `useRef()` | Values that change without triggering re-render | Values that SHOULD trigger re-render |

### Examples

```typescript
// CORRECT — memoize expensive sorting/filtering
const sortedItems = useMemo(
  () => items.slice().sort((a, b) => a.order - b.order),
  [items]  // Only re-sort when items change
);

// CORRECT — memoize a component receiving stable props
const Row = React.memo(function Row({ item }: { item: Item }) {
  return <div>{item.label}</div>;
});

// WRONG — memoizing trivial computation
const doubled = useMemo(() => value * 2, [value]); // Overhead > benefit
```

### Rules

1. **Profile before memoizing.** Use React DevTools Profiler to find slow components.
2. **Memoize at the right level.** Memoizing a parent component is often better
   than memoizing 50 children.
3. **Streaming data arrives as new object references every time.** Use
   structural comparison or normalized stores to prevent unnecessary re-renders.
4. **Never memoize JSX directly.** Memoize the data, let React handle rendering.

## Responsive Design

### Breakpoints

```typescript
const breakpoints = {
  mobile: 0,       // 0-639px: single column, essential content only
  tablet: 640,     // 640-1023px: 2 columns, condensed layout
  desktop: 1024,   // 1024-1439px: full layout
  wide: 1440,      // 1440+: extra columns, expanded content
};
```

### Rules

1. **Decide primary viewport up front.** Is this a mobile-first product or a
   desktop-first one? Don't fake one if you need the other.
2. **Data tables MUST be horizontally scrollable on mobile** (not wrapped).
3. **Touch targets MUST be at least 44x44px** on tablet and mobile.
4. **Minimum readable body font: 14px** (12px only for dense data views).
5. **Use CSS Grid for dashboard layouts, Flexbox for linear flows.**

## Accessibility Basics

1. **Never use color alone** to convey information (green/red for status).
   Always add text indicators, icons, or patterns.
2. **Contrast ratio >= 4.5:1** for body text, >= 3:1 for large text and UI
   components.
3. **All interactive elements MUST be keyboard accessible.** Tab order must
   follow a logical sequence.
4. **Escape MUST close modals and dropdowns.**
5. **Status changes MUST use `aria-live="polite"`** so screen readers announce
   them.
6. **Test with a screen reader** (VoiceOver on macOS, NVDA on Windows) before
   shipping critical flows.
7. **Run an automated accessibility audit** (Lighthouse or axe) in CI with a
   minimum score threshold.

## Performance Monitoring

### Key Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| FPS during realtime updates | >= 30 FPS | `requestAnimationFrame` loop counter |
| Time to Interactive (TTI) | < 3s | Lighthouse |
| Message processing | < 5ms/msg | `performance.mark` around handler |
| Re-render count per state change | <= 3 components | React DevTools Profiler |
| Bundle size (gzipped) | < 500KB initial | Bundler build output |
| Memory (heap) | stable after warm-up | `performance.memory` API |

### Monitoring Pattern

```typescript
// FPS monitor
function useFPSMonitor() {
  const [fps, setFps] = useState(60);

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();

    function tick() {
      frameCount++;
      const now = performance.now();
      if (now - lastTime >= 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = now;
      }
      requestAnimationFrame(tick);
    }

    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, []);

  return fps;
}
```

### Rules

1. **FPS below 30 during normal operation is a bug.**
2. **Memory growth without plateau after 30min is a leak.**
3. **Realtime message queue backlog means the client is too slow** — reduce
   subscription scope or move parsing to a Web Worker.
4. **Profile before optimizing.** React DevTools Profiler identifies the actual
   bottleneck.

## Animation and Motion Floors

This section does NOT encode brand voice, playfulness levels, or personality
choices — those are product and brand-team decisions that vary by domain. What
this section encodes are the **non-negotiable floors** that any animation,
regardless of intent, must satisfy: motion safety, performance budget, and
state-change legibility.

### Motion Safety (prefers-reduced-motion)

WCAG 2.1 §2.3.3 (AAA) requires a mechanism to suppress non-essential motion.
`prefers-reduced-motion: reduce` is that mechanism and it is set by real users
with vestibular disorders, epilepsy, or motion sensitivity.

```css
/* CORRECT — gate every non-trivial animation behind the media query */
@keyframes slide-in {
  from { transform: translateX(-16px); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}

.panel-enter {
  animation: slide-in 200ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .panel-enter {
    animation: none;
    /* Preserve the end-state so layout is correct */
    transform: translateX(0);
    opacity: 1;
  }
}
```

```typescript
// CORRECT — read the preference in JS for imperative animations.
// IMPORTANT: read fresh on EVERY call so an OS preference change while
// the page is open is honored on the next animation. For declarative
// React component code, prefer the usePrefersReducedMotion() hook
// from frontend/accessibility-and-wcag (it subscribes to the
// `change` event of the MediaQueryList).
function getReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function animateEntrance(el: HTMLElement) {
  if (getReducedMotion()) {
    // Apply end-state directly; skip the animation
    el.style.opacity = "1";
    el.style.transform = "none";
    return;
  }
  el.animate(
    [{ opacity: 0, transform: "translateX(-16px)" }, { opacity: 1, transform: "none" }],
    { duration: 200, easing: "ease-out", fill: "forward" }
  );
}

// WRONG — always animating regardless of user OS preference
el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 400 });
```

### Animation Budget During High-Frequency Updates

CSS animations running concurrently with high-frequency data updates (WS
tickers, live order books) compete for the same compositor budget. The cost
compounds: a 60 fps ticker that also triggers 3 simultaneous CSS transitions
per frame can drop perceived FPS to <30 on mid-range hardware even when each
transition is individually cheap.

| Condition | Animation budget |
|-----------|-----------------|
| Component receives WS updates > 5/s | ZERO running CSS transitions on that element |
| Component receives WS updates 1-5/s | At most 1 active transition, duration <= 150ms |
| Component receives WS updates < 1/s | Normal budget (multiple transitions, up to 300ms each) |

```typescript
// CORRECT — suppress transition while ticker is hot, re-enable on pause
function useSuppressedTransition(updateRate: number) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (updateRate > 5) {
      el.style.transition = "none";
    } else {
      el.style.transition = "";  // Restore stylesheet value
    }
  }, [updateRate]);

  return ref;
}

// WRONG — CSS transition left on a WS ticker cell
// .ticker-cell { transition: background-color 300ms; }  <- kills FPS at >5 msg/s
```

### State-Change Legibility

Animations on data updates (highlight flash, color change) MUST communicate a
direction, not just change. A price cell that flashes green and then reverts to
neutral tells the user "this went up." A cell that merely flashes an arbitrary
color communicates nothing actionable.

Rules:

1. **Highlight animations on data change MUST encode direction via icon AND
   text label, with color as a reinforcing cue only.** Use ▲ / ▼ glyphs (or
   equivalent shape) plus a `+` / `−` text prefix; layer green/red as a
   secondary signal. Color-only direction encoding fails WCAG 1.4.1 (Use of
   Color) and excludes deuteranopic / protanopic users. No other color mapping
   for numeric change indicators.
2. **Flash duration MUST be 200-400ms.** Below 200ms is imperceptible; above
   400ms interferes with the next update cycle at 2+ updates/s.
3. **NEVER animate a loading state and a data-update state simultaneously** on
   the same element. Pick one: either the element is loading (skeleton) or it
   is live (update flash). Overlapping the two produces visual noise with no
   information value.
4. **`prefers-reduced-motion` MUST suppress flash animations**, not just slow
   them. Reduced-motion users still need the direction signal — deliver it via
   text change or icon, not motion.

```typescript
// CORRECT — direction-encoded flash with reduced-motion fallback
type Direction = "up" | "down" | "neutral";

function usePriceFlash(value: number): Direction {
  const prev = useRef(value);
  const [dir, setDir] = useState<Direction>("neutral");

  useEffect(() => {
    if (value > prev.current) setDir("up");
    else if (value < prev.current) setDir("down");
    else setDir("neutral");
    prev.current = value;

    const t = setTimeout(() => setDir("neutral"), 350);
    return () => clearTimeout(t);
  }, [value]);

  return dir;
}

// In CSS (with reduced-motion override):
// .flash-up   { background-color: var(--color-positive-flash); }
// .flash-down { background-color: var(--color-negative-flash); }
// @media (prefers-reduced-motion: reduce) {
//   .flash-up, .flash-down { background-color: unset; }
// }
```

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Formatting numbers/dates inline in JSX | Inconsistent, wrong locale | Shared formatter utilities |
| New WS per component | Connection explosion | Single WS, multiplex channels |
| `useEffect` for data transform | Unnecessary re-render cycle | `useMemo` |
| Rendering 5000 list items | DOM thrashing, low FPS | Virtualization |
| Polling when WS/SSE available | Wasted bandwidth, stale data | Subscribe to the push channel |
| Color-only status | Accessibility violation | Color + text + icon |
| Inline styles for layout | Unmaintainable | CSS modules or utility framework |
| Fetching on every render | API hammering | Server-state library with stale-while-revalidate |
| Showing "0" or "N/A" during loading | Misleading | Skeleton loader |
| Props drilling 4+ levels | Unmaintainable | Context or store |
| Missing error boundary around route | Full app crashes | Route-level `ErrorBoundary` |
| CSS transition on high-frequency WS element | FPS drops on mid-range hardware | Suppress transition when update rate > 5/s |
| Flash animation without direction encoding | No actionable information; fails WCAG 1.4.1 if color-only | ▲/▼ icon + `+`/`−` text prefix; color (green/red) reinforces but does NOT solely communicate direction |
| Animation without prefers-reduced-motion gate | Vestibular/accessibility violation | Gate every non-essential motion |

## Changelog

- **1.1.0** (2026-07-07, PLAN-153 Wave G, SP-025): enrichment merge — added
  §Deriving and Locating State (derive-during-render, state-location and
  data-fetching decision trees), §Server and Client Components (RSC), and
  §Forms (React 19 Actions and Optimistic UI). Clean-room ADAPT of
  upstream React 18/19 pattern guidance; no pre-existing section changed.
  First tracked revision.
- **1.0.0** (framework v1.0.x): initial version shipped with the
  framework; this changelog was introduced retroactively at 1.1.0.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=835c8ab17461c1b1cfcffb2f62955184d0c4212fb2549789e09800c3d2360b45
