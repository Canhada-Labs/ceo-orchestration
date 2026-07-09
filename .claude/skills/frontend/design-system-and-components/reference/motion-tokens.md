# Motion tokens — reference shapes

Deep reference for the "Motion Tokens & Motion Governance" section of the
Design System skill. These are illustrative shapes to adapt to your token
source of truth. The governance rules — tokenize every value, enforce the
reduced-motion priority order, animate `transform`/`opacity` only, keep
`initial` matching server output — are the load-bearing part; the exact
numbers are yours to tune.

## The token object

```ts
// motion-tokens.ts — single source of truth for motion values
export const motionTokens = {
  duration: {           // seconds
    instant: 0.08,      // tooltip / focus ring / badge update
    fast:    0.18,      // button feedback, icon swap
    normal:  0.35,      // modal open, card expand, element enter
    slow:    0.6,       // hero entrance, full-page transition
    crawl:   1.0,       // deliberate storytelling; use sparingly
  },
  easing: {             // cubic-bezier control points
    smooth: [0.22, 1, 0.36, 1],
    sharp:  [0.4, 0, 0.2, 1],
    bounce: [0.34, 1.56, 0.64, 1],
    linear: [0, 0, 1, 1],
  },
  distance: { xs: 4, sm: 8, md: 16, lg: 24, xl: 48 }, // px offsets for enters
  scale:    { subtle: 0.98, press: 0.95, pop: 1.04 }, // interaction transforms
} as const;

// Spring presets — reference by name; never inline stiffness/damping.
export const springs = {
  snappy:  { type: "spring", stiffness: 300, damping: 30 },  // default UI
  gentle:  { type: "spring", stiffness: 120, damping: 14 },  // cards, panels
  bouncy:  { type: "spring", stiffness: 400, damping: 10 },  // playful moments
  instant: { type: "spring", stiffness: 600, damping: 35 },  // tooltips, popovers
  release: { type: "spring", stiffness: 200, damping: 20, restDelta: 0.001 }, // drag release
} as const;
```

## The animation gate

Every animated component consults one gate before it animates, so the
accessibility and device contracts are enforced in exactly one place
instead of being re-checked (and eventually forgotten) per component.

```ts
// motion-config.ts
export const motionConfig = {
  isLowEnd() {
    return typeof navigator !== "undefined" && navigator.hardwareConcurrency <= 4;
  },
  prefersReduced() {
    return typeof window !== "undefined"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  },
  // Essential motion (e.g. a loading indicator) survives the low-end gate;
  // reduced-motion still overrides everything.
  shouldAnimate({ essential = false } = {}) {
    if (this.prefersReduced()) return false;
    if (!essential && this.isLowEnd()) return false;
    return true;
  },
};
```

## Reduced-motion-aware enter/exit

```tsx
"use client";
import { useReducedMotion } from "<your-motion-library>"; // e.g. motion/react

// Returns transform+opacity states that collapse to opacity-only when the
// user prefers reduced motion: the transform distance goes to 0, the fade
// stays — capped at 0.2s per the loader's reduced-motion floor.
export function useSafeMotion(offsetY = 16) {
  const reduce = useReducedMotion();
  return {
    initial: { opacity: 0, y: reduce ? 0 : offsetY },
    animate: { opacity: 1, y: 0 },
    exit:    { opacity: 0, y: reduce ? 0 : -offsetY },
    transition: reduce ? { duration: 0.2 } : undefined,
  };
}
```

## SSR-safe animated component (no hydration mismatch)

```tsx
"use client";
import { useState, useEffect } from "react";
import { motion } from "<your-motion-library>";
import { motionTokens, springs } from "./motion-tokens";
import { useSafeMotion } from "./use-safe-motion";
import { motionConfig } from "./motion-config";

export function FadeInCard({ children }: { children: React.ReactNode }) {
  // The server renders the resting state (opacity: 1). Only after mount do we
  // allow the animated initial state — otherwise `initial` !== server output.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const safe = useSafeMotion(motionTokens.distance.md);
  if (!mounted || !motionConfig.shouldAnimate()) return <div>{children}</div>;

  return (
    <motion.div
      initial={safe.initial}
      animate={safe.animate}
      exit={safe.exit}
      transition={springs.gentle}
      whileHover={{ scale: motionTokens.scale.pop }}
      whileTap={{ scale: motionTokens.scale.press }}
    >
      {children}
    </motion.div>
  );
}
```

## Anti-patterns

| Anti-pattern | Why it's wrong | Fix |
|---|---|---|
| `transition: { duration: 0.4 }` inline | Untokenized drift | `motionTokens.duration.*` |
| `{ stiffness: 300, damping: 30 }` inline | Untokenized drift | `springs.snappy` |
| `animate={{ width: "100%" }}` | Layout/paint, drops frames | Animate `scaleX` |
| `initial={{ opacity: 0 }}` on an SSR component | Hydration mismatch | Mount-guard the initial state |
| `navigator.hardwareConcurrency` at module scope | Crashes SSR | Guard with `typeof navigator` |
| Skipping the reduced-motion check | Accessibility violation | Route through `shouldAnimate()` / `useSafeMotion` |

---

Motion-library note: the examples reference `<your-motion-library>` (for
example `motion/react`) rather than mandating a specific package. The
governance — tokens, the gate, reduced-motion priority, transform/opacity
only, SSR-safe initial — holds for any React animation library or for
hand-rolled CSS transitions driven by the same tokens.
