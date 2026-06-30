---
name: Code Quality & TypeScript
description: TypeScript strict mode governance, ESLint rule strategy, type assertion audit, dead code detection, circular dependency prevention, `:any` evaluation criteria, naming conventions, and code review quality gates for the {{PROJECT_NAME}} frontend. Use when reviewing TypeScript health, configuring ESLint rules, auditing type assertions, cleaning dead code, enforcing naming conventions, or when any code needs quality review before merge.
owner: Frontend Quality Lead (archetype) + Staff Code Reviewer (archetype)
veto: Frontend Quality Lead VETO — any merge (quality gate final)
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: frontend
priority: 4
risk_class: medium
stack: [typescript, eslint]
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 2}
  engine: {active: true, priority: 6}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 7}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: file-edit, glob: "**/*.ts"}
  - {event: file-edit, glob: "**/*.tsx"}
  - {event: file-edit, glob: "**/tsconfig.json"}
  - {event: file-edit, glob: "**/.eslintrc*"}
  - {event: help-me-invoked, regex: "(?i)typescript|eslint|any.?type|lint|tsconfig"}
---

# Code Quality & TypeScript — {{PROJECT_NAME}} Frontend

> **Owners:** Frontend Quality Lead (archetype) + Staff Code Reviewer (archetype)
> **Scope:** `{{FRONTEND_REPO_PATH}}/src/` — the codebase
> **VETO:** Frontend Quality Lead vetoes any merge that fails quality gates

## Quality Lead Profile

**Background:** 13 years in type systems and code quality. At Google, led the TypeScript migration of 2M+ lines from Closure Compiler. At Airbnb, built the eslint-config-airbnb used by 500K+ repos. Believes type safety is not overhead — it's documentation that the compiler verifies.

**Superpower:** Reads a type assertion and knows if it's hiding a bug or working around a library gap. Distinguishes "necessary cast" from "lazy cast" in 2 seconds.

**Mantra:** *"Every `:any` is a hole in your safety net. Every `as` is a promise the compiler can't verify."*

## Quality Gates (MUST pass before merge)

1. `npx tsc --noEmit` — 0 errors
2. `npx vitest run` — 0 failures
3. `npx eslint src/` — 0 errors (warnings tracked, reduced over time)
4. No new `:any` types without justification comment
5. No new `as unknown as` double-casts
6. No new `@ts-ignore` or `@ts-expect-error`

## TypeScript Strictness

### Current Config (tsconfig.json)
```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true,
  "noUncheckedIndexedAccess": true
}
```
All flags enabled. This is above-average strictness. **Never relax these.**

### `:any` Evaluation Criteria

| Verdict | When to use |
|---------|------------|
| **REJECT** | Lazy typing — developer didn't bother to type the data |
| **REJECT** | API response without interface — create the interface |
| **ACCEPT** | Recharts/chart library formatter callbacks (library types are incomplete) |
| **ACCEPT** | i18next `t` function edge cases (TFunction generics are complex) |
| **DOCUMENT** | Any accepted `:any` MUST have inline comment explaining why |

### Type Assertion Tiers

| Pattern | Severity | Action |
|---------|----------|--------|
| `as SomeType` (single cast) | LOW | Acceptable when TypeScript can't infer (JSON.parse, API responses) |
| `as unknown as SomeType` (double-cast) | HIGH | Almost always wrong. Fix the upstream type instead |
| `x!` (non-null assertion) | MEDIUM | Acceptable in test files. In production, prefer optional chaining |
| `as const` | NONE | Always fine — narrows types |
| `as any` | CRITICAL | Same as `:any` — evaluate per criteria above |

### Current Metrics (V2 Audit 2026-03-24)
- `:any` types: **6** in 5 files (target: 0 new)
- `as unknown as`: **0** (was 13, all eliminated)
- `as Type` assertions: **384** (high but many are API response typing)
- `@ts-ignore`: **0**
- `@ts-expect-error`: **0**

## ESLint Strategy

### Rule Promotion Path
```
OFF → warn (discovery) → error (enforcement)
```

### Current Rule Levels
| Rule | Level | Target |
|------|-------|--------|
| `@typescript-eslint/no-explicit-any` | `error` | Stay `error` |
| `@typescript-eslint/consistent-type-assertions` | `warn` | Promote to `error` after cleanup |
| `@typescript-eslint/no-unnecessary-type-assertion` | `warn` | Promote to `error` after 77 fixes |
| `no-console` | `error` (allow warn/error) | Stay `error` |
| `react-hooks/exhaustive-deps` | `warn` | Promote to `error` after cleanup |
| `react-hooks/purity` | `error` (React Compiler) | Fix all Date.now/ref violations |

### ESLint Issue Categories

| Category | Pattern | Fix Strategy |
|----------|---------|-------------|
| **Impure render** | `Date.now()` in render/useMemo | Move to useRef or state with interval |
| **Ref in render** | `ref.current` access during render | Move to useEffect or event handler |
| **Component in render** | Arrow function component inside render | Extract to module-level const |
| **setState in effect** | Cascading renders | Convert to useMemo or restructure |
| **Exhaustive deps** | Missing hook dependencies | Add dep or document exclusion |
| **Preserve memoization** | useCallback/useMemo dep mismatch | Align deps with actual usage |

## Dead Code Detection

### Patterns to Check
1. **Unused exports:** grep for export, then grep for import of that name
2. **Unreachable routes:** Routes in App.tsx that redirect or are never navigated to
3. **Unused components:** Components in shared/ imported by zero files
4. **Phantom type assertions:** `as SomeType` where SomeType is the same as the inferred type

### Current Dead Code
- 5 redirect-only pages (FX, Macro, News, TechnicalAnalysis, Truf) — routes exist but just redirect

## Circular Dependency Prevention

### Rules
1. **No circular imports** between modules (use `madge` to verify)
2. **Dependency direction:** pages → components → hooks → lib → types
3. **Engine isolation:** `src/engine/` should not import from `src/components/`
4. **Store isolation:** Zustand stores should not import from components

### Current State
- 1 known circular dependency (documented in V1 audit)

## Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Components | PascalCase | `MarketPulse.tsx` |
| Hooks | camelCase with `use` prefix | `useWSChannels.ts` |
| Stores | camelCase with `use` prefix + `Store` suffix | `useTradingStore.ts` |
| Query keys | Array with namespace prefix | `['engine', 'markets']` |
| Types/Interfaces | PascalCase | `BookState`, `MarketData` |
| Utils/lib | camelCase | `safeNumber`, `formatMarketPrice` |
| Constants | UPPER_SNAKE_CASE | `BOOK_STALE_THRESHOLD_MS` |
| CSS tokens | kebab-case | `var(--positive-dim)` |
| i18n keys | dot.separated.lowercase | `billing.creditBalance` |

## Code Review Checklist (Quality Lead + Staff Code Reviewer)

Before approving any merge:
- [ ] `tsc --noEmit` passes
- [ ] `vitest run` passes
- [ ] No new `:any` without justification
- [ ] No new double-casts
- [ ] No hardcoded English strings (use i18n)
- [ ] No hardcoded colors (use DS tokens)
- [ ] No `parseFloat` on financial data
- [ ] No inline `style={{}}` on hot-path components
- [ ] Error/loading/empty states handled
- [ ] Accessibility: interactive elements have labels
