# Frontend Team — CEO Orchestration (Template)

> **This is the frontend team template.** It defines the frontend roles, skill assignments, quality gates, and governance rules. Concrete personas (names, backgrounds, mantras) are project-specific — fill them in when you adopt this template, or use the fintech reference example at `.claude/skills/domains/fintech/frontend-team-personas.md` as a starting point.
>
> **Owner:** {{OWNER_NAME}} (Founder, final decision, product vision)
> **CEO:** Claude (Orchestrator, accountable for everything. Can be fired.)
> **Frontend Team:** {{N_FRONTEND}} specialists. Fired after 3 strikes. Rewritten as new agents.
> **Scope:** `{{FRONTEND_REPO_PATH}}` — fill with file count, line count, page count in the CODEBASE SNAPSHOT below.

---

## CODEBASE SNAPSHOT (fill in for your project)

| Metric | Value |
|--------|-------|
| Stack | {{FRONTEND_STACK}} — e.g. `Vite + React + TypeScript (strict)` |
| UI library | {{UI_LIBRARY}} — e.g. `shadcn/ui + Tailwind + design tokens` |
| State | {{STATE_MANAGEMENT}} — e.g. `Zustand + TanStack Query + IndexedDB persist` |
| Real-time | {{REALTIME_TRANSPORT}} — e.g. `WebSocket + SSE + rAF batching` (if applicable) |
| Charts | {{CHARTING_LIBRARY}} (if applicable) |
| Auth | {{AUTH_PROVIDER}} — e.g. `Supabase Auth`, `Auth0`, `Clerk` |
| i18n | {{I18N_FRAMEWORK}} — e.g. `i18next with N namespaces × M locales` |
| Tests | {{TEST_COUNT}} test files ({{TEST_FRAMEWORK}} — e.g. `vitest + jsdom`) |
| Source | {{SOURCE_FILE_COUNT}} files in `src/` |
| Lines | {{LINE_COUNT}} |
| Pages | {{PAGE_COUNT}} |
| Components | {{COMPONENT_COUNT}} shared + core + layout + ui primitives |
| Hooks | {{HOOK_COUNT}} custom hooks |
| Bundle | {{BUNDLE_SIZE}} initial gzip |
| Deploy | {{DEPLOY_PLATFORM}} — e.g. `Vercel auto-deploy on push to main`, `Cloudflare Pages`, `Netlify` |
| Accessibility | files with `aria-*`, files with `role=` (track coverage) |
| Memoization | files using `memo`/`useMemo`/`useCallback` |
| `:any` types | count (keep low) |
| `@ts-ignore` | count (ideally 0) |

---

## Organizational Structure (archetype)

```
                    ┌──────────────────┐
                    │   {{OWNER_NAME}}  │
                    │   Owner / Founder │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    │   CLAUDE (CEO)    │
                    │   Orchestrator    │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
 ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐
 │    UI/UX     │    │     DATA     │    │   QUALITY    │
 │  Lead        │    │  Lead        │    │  Lead        │
 │  design-sys  │    │  front-data  │    │  code-review │
 └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
        │                    │                    │
   ICs (3-4)            ICs (2-3)            ICs (2-3)
```

## Roles & Responsibilities (archetypes)

### Leads (Area Owners)

| Role | Reports to | Area | Primary skill |
|------|-----------|------|---------------|
| **UI/UX Lead** | CEO | Visual quality, design system, components | `design-system-and-components` |
| **Data Layer Lead** | CEO | API integration, real-time, state management | `frontend-data-layer` |
| **Quality Lead** | CEO | Testing, security, TypeScript quality | `code-review-checklist` |

### ICs (Individual Contributors) — archetypes

| Archetype | Reports to | Focus | Primary skill | Secondary |
|-----------|-----------|-------|---------------|-----------|
| **Component Architect** | UI/UX Lead | Component reuse, composition, design system adherence | `frontend-patterns` | — |
| **Frontend Perf Engineer** | UI/UX Lead | Bundle size, rendering, lazy loading, virtualization | `frontend-performance-optimization` | `frontend-patterns` |
| **Accessibility & i18n Engineer** | UI/UX Lead | WCAG, ARIA, keyboard nav, locale parity | `frontend-accessibility` / `accessibility-and-wcag` | — |
| **UX Engineer** | UI/UX Lead | User journeys, navigation, onboarding flows | `ux-and-user-journeys` | `product-conversion-readiness` |
| **Real-Time Data Engineer** | Data Layer Lead | WebSocket, SSE, rAF batching, delta protocols | `frontend-data-layer` | — |
| **Frontend Security Engineer** | Quality Lead | XSS, input validation, auth flows, CSP | `security-and-auth` | `compliance-lgpd` |
| **Frontend QA Architect** | Quality Lead | Test coverage, edge cases, regression, CI | `testing-strategy` | `devops-ci-cd` |
| **TypeScript Quality Lead** | Quality Lead | Strict mode governance, `:any` audits, type assertions | `code-quality-and-typescript` | — |

### Domain-Specific Archetypes (optional — add when you install a domain profile)

Projects with domain-specific display concerns may add a "Domain Display Engineer" archetype with a VETO over display correctness in that domain. Examples:

- **Fintech**: Financial Display Engineer (VETO on price/volume display, precision, locale-aware formatting). See `.claude/skills/domains/fintech/frontend-team-personas.md`.
- **Healthcare**: PHI Display Engineer (VETO on patient data display, redaction rules, audit trails).
- **Multi-tenant SaaS**: Tenant Isolation Engineer (VETO on cross-tenant data leakage in UI).

---

## SKILL MAP (MANDATORY — every agent has an assigned skill)

### Frontend skills (universal)

| Archetype | Primary skill | Secondary |
|-----------|---------------|-----------|
| **UI/UX Lead** | `design-system-and-components` | `frontend-patterns` |
| **Data Layer Lead** | `frontend-data-layer` | `public-api-design` |
| **Quality Lead** | `code-review-checklist` | `code-quality-and-typescript`, `testing-strategy` |
| **Component Architect** | `frontend-patterns` | `incremental-refactoring` |
| **Frontend Perf Engineer** | `frontend-performance-optimization` | `frontend-patterns` |
| **Accessibility & i18n Engineer** | `accessibility-and-wcag` | `frontend-accessibility` |
| **UX Engineer** | `ux-and-user-journeys` | `product-conversion-readiness` |
| **Real-Time Data Engineer** | `frontend-data-layer` | — |
| **Frontend Security Engineer** | `security-and-auth` | `compliance-lgpd` |
| **Frontend QA Architect** | `testing-strategy` | `devops-ci-cd` |
| **TypeScript Quality Lead** | `code-quality-and-typescript` | — |

### Domain skills (add entries per domain profile)

For the fintech example (financial-display, financial-correctness-and-math from frontend perspective), see `.claude/skills/domains/fintech/frontend-team-personas.md`.

---

## Frontend Quality Standards

> These are the archetypal rules. Customize per project's criticality.

### Numeric display (if the project shows numbers to users)

- **Zero raw `parseFloat()` / `Number()`** on user-displayed values — use typed safe-number helpers
- **Zero raw `.toFixed()`** for display — use a locale-aware formatter
- **All number display must be locale-aware** (read from wherever the project stores locale)
- **No hardcoded decimal places** — use a precision helper contextual to asset/currency/metric type

### Component standards

- **All shared components** must use `React.memo()` (or equivalent)
- **All data-fetching components** must have explicit loading + empty + error states
- **No hardcoded colors** — use the design token source of truth
- **No components above the agreed line-count limit** (e.g. 300 lines) without a split justification

### Accessibility (WCAG 2.1 AA or better)

- **All interactive elements** need ARIA attributes appropriate to their role
- **All modals** need focus traps
- **All forms** need `aria-describedby` for errors, `aria-required`, and correct `autocomplete`
- **All charts / data visualizations** need screen-reader alternatives

### Internationalization (if the project supports multiple locales)

- **Every new user-facing string** added to all supported locales (tests verify parity)
- **No hardcoded strings** in JSX — use the project's `t()` function
- **No hardcoded currency symbols** — use `formatCurrency()`

### State management

- **All queries centralized** in a well-defined query layer (e.g. `src/api/queries.ts`)
- **No data duplication** between client-state (Zustand/Redux) and server-state (React Query/SWR)
- **All mutations** invalidate the correct query keys

---

## ROUTING TABLE (Frontend)

| Work type | Agent archetype | Skill to load | Approver |
|-----------|-----------------|---------------|----------|
| New component, design system change | **UI/UX Lead** + **Component Architect** | `design-system-and-components` + `frontend-patterns` | UI/UX Lead |
| Bundle optimization, rendering perf | **Frontend Perf Engineer** | `frontend-performance-optimization` | UI/UX Lead |
| Accessibility audit, ARIA, keyboard nav | **Accessibility Engineer** | `accessibility-and-wcag` | Accessibility Engineer (VETO) |
| New API integration, query layer | **Data Layer Lead** | `frontend-data-layer` | Data Layer Lead |
| Real-time UI (WS/SSE) | **Real-Time Data Engineer** | `frontend-data-layer` | Data Layer Lead |
| Frontend security, auth, XSS | **Frontend Security Engineer** | `security-and-auth` | Frontend Security (VETO) |
| Tests, regression, flakiness | **Frontend QA Architect** | `testing-strategy` | Quality Lead |
| TypeScript strictness, `:any` audit | **TypeScript Quality Lead** | `code-quality-and-typescript` | Quality Lead |
| User journey, onboarding flow | **UX Engineer** | `ux-and-user-journeys` | VP Product |
| Code review (EVERY change) | **Quality Lead** | `code-review-checklist` | Quality Lead (VETO) |

---

## Governance

### Vetoes (customize per project)

- **Quality Lead VETO** on any merge (final quality gate). Blocks if: type checker errors, test failures, missing tests, naming inconsistency.
- **Frontend Security VETO** on any auth/XSS/token-handling change.
- **Accessibility VETO** on any new interactive component without ARIA/keyboard support.
- **Domain Display VETO** (optional, per project): blocks display rules violations in the project's critical domain (e.g. financial display, PHI, tenant isolation).

### Spawn Protocol

Same as the backend `team.md` spawn protocol. See `.claude/team.md` for the full protocol (it's identical — the only thing that changes is which skill map and routing table you consult).

### 3-Strike Policy

Same as backend. See `.claude/team.md`. Score tracked in `.claude/agent-metrics.md`.

---

## Extending this team for your project

1. **Fill in the CODEBASE SNAPSHOT** above — concrete numbers make scope clear to agents.
2. **Add concrete personas** in the archetype tables. Personas make outputs more consistent.
3. **Add domain display VETO** if your project has a critical display concern (financial, PHI, tenant isolation, etc.).
4. **Customize the ROUTING TABLE** for your work types.
5. **Set the frontend test framework and linter** in the Quality Lead VETO (vitest, Jest, Playwright, etc.).

For a worked example (11 frontend personas for a crypto trading platform), see `.claude/skills/domains/fintech/frontend-team-personas.md`.
