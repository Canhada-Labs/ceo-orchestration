# Org Chart (Template)

> The organizational archetype for a project adopting ceo-orchestration. Concrete
> personas live in `.claude/team.md` and `.claude/frontend-team.md`. This template
> shows the **shape** of the organization; fill in the names and backgrounds when
> you adopt it.
>
> For a fully-worked example (a reference fintech roster with 29 personas and
> concrete VETO holders), see `.claude/skills/domains/fintech/ORG_CHART.md`.

---

## Backend (N ICs + 1-3 staff)

```
                         ┌──────────────────┐
                         │   {{OWNER_NAME}} │
                         │   Owner / Founder │
                         │   Final decision  │
                         └────────┬─────────┘
                                  │
                         ┌────────┴─────────┐
                         │   CLAUDE (CEO)    │
                         │   Orchestrator    │
                         │   Accountable     │
                         └────────┬─────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
 ┌──────┴───────┐          ┌──────┴───────┐          ┌──────┴───────┐
 │  ENGINEERING │          │   PRODUCT    │          │  OPERATIONS  │
 │  VP          │          │  VP          │          │  VP          │
 │  arch-decis. │          │  prod-conv.  │          │  obs-and-ops │
 └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
        │                         │                         │
   ICs (4-8)                 ICs (2-4)                  ICs (2-4)

 ╔══════════════════════════════════════╗
 ║  STAFF (report directly to CEO)      ║
 ║  Cross-cutting authority — VETO       ║
 ║                                       ║
 ║  Required:                            ║
 ║  ┌────────────────┐                   ║
 ║  │ Staff Code     │                   ║
 ║  │ Reviewer       │                   ║
 ║  │ VETO: merges   │                   ║
 ║  └────────────────┘                   ║
 ║                                       ║
 ║  Optional (domain-specific):          ║
 ║  ┌────────────────┐                   ║
 ║  │ Staff Domain   │                   ║
 ║  │ Expert         │                   ║
 ║  │ VETO: domain   │                   ║
 ║  └────────────────┘                   ║
 ╚══════════════════════════════════════╝
```

### Backend archetypes

| Archetype | Title | Reports to | Primary skill |
|-----------|-------|-----------|---------------|
| **VP Engineering** | Head of Engineering / Distinguished Architect | CEO | `architecture-decisions` |
| **VP Product** | Head of Product | CEO | `product-conversion-readiness` |
| **VP Operations** | Head of Operations / Staff SRE | CEO | `observability-and-ops` |
| **Principal Performance Engineer** | Perf, event loop, memory, GC | VP Engineering | `performance-engineering` |
| **Staff Backend Engineer** | API design, external integrations | VP Engineering | `public-api-design` |
| **Real-Time Systems Engineer** | WebSocket, IPC, workers, state machines | VP Engineering | `state-machines-and-invariants` |
| **Frontend Engineer** (if no separate frontend team) | React, UX | VP Engineering | `frontend-patterns` |
| **Principal Data Engineer** | Schemas, migrations, RLS | VP Engineering | `data-schema-design` |
| **Principal QA Architect** | Testing, regression, edge cases | VP Engineering | `testing-strategy` |
| **Growth Engineer** | Funnel, onboarding, conversion | VP Product | `growth-and-launch` |
| **Billing & Payments Engineer** | Stripe, subscriptions, metered | VP Product | `monetization-and-billing` |
| **Compliance Specialist** | LGPD/GDPR, privacy, legal | VP Product | `compliance-lgpd` |
| **Chaos & Resilience Engineer** | Failure testing, circuit breakers | VP Operations | `chaos-and-resilience` |
| **Principal Security Engineer** | Auth, encryption, threat modeling | VP Operations | `security-and-auth` |
| **DevOps & Platform Engineer** | CI/CD, Docker, deploy | VP Operations | `devops-ci-cd` |
| **Staff Code Reviewer** (STAFF, CEO) | Merge VETO holder | CEO (staff) | `code-review-checklist` |
| **Staff Domain Expert** (STAFF, CEO) | Optional — domain VETO holder (per project) | CEO (staff) | depends on domain |

The exact number of ICs is project-dependent. A small team may run with 4-6 ICs + 1 staff (code reviewer). A large team may have 15+ ICs and multiple domain-specific staff VETOes.

---

## Frontend (optional — if separate from backend)

```
                    ┌──────────────────┐
                    │   {{OWNER_NAME}} │
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
   ICs (2-4)            ICs (1-3)            ICs (1-3)
```

### Frontend archetypes

| Archetype | Title | Reports to | Primary skill |
|-----------|-------|-----------|---------------|
| **UI/UX Lead** | Design System Owner | CEO | `design-system-and-components` |
| **Component Architect** | Component reuse, composition | UI/UX Lead | `frontend-patterns` |
| **Frontend Perf Engineer** | Bundle, rendering, virtualization | UI/UX Lead | `frontend-performance-optimization` |
| **Accessibility & i18n Lead** | WCAG, ARIA, locale parity | UI/UX Lead | `accessibility-and-wcag` |
| **UX Engineer** | Journeys, onboarding | UI/UX Lead | `ux-and-user-journeys` |
| **Data Layer Lead** | API, state, real-time | CEO | `frontend-data-layer` |
| **Real-Time Data Engineer** | WebSocket, SSE, streaming | Data Layer Lead | `frontend-data-layer` |
| **Frontend Security Engineer** | XSS, auth, CSP, input validation | Quality Lead | `security-and-auth` |
| **Frontend QA Architect** | Tests, regression, CI | Quality Lead | `testing-strategy` |
| **Quality Lead** | Merge VETO, TypeScript strict mode | CEO | `code-review-checklist` |
| **TypeScript Quality Lead** | `:any` audit, strict mode | Quality Lead | `code-quality-and-typescript` |
| **Staff Domain Display Engineer** (optional) | Domain display VETO (per project) | CEO (staff) | depends on domain |

---

## Routing (who to call)

See the full ROUTING TABLE in `.claude/team.md`. The table maps work types to archetypes and skills:

| Type of work | Archetype | Skill |
|--------------|-----------|-------|
| API design, OpenAPI, SDK | Staff Backend Engineer + Code Reviewer | `public-api-design` + `code-review-checklist` |
| Security, auth, encryption | Security Engineer | `security-and-auth` |
| Performance, event loop, memory | Performance Engineer | `performance-engineering` |
| Database, schemas, migrations | Data Engineer | `data-schema-design` |
| Resilience, circuit breakers | Chaos Engineer | `chaos-and-resilience` |
| Tests, QA, edge cases | QA Architect | `testing-strategy` |
| Real-time, WebSocket, IPC | Real-Time Systems Engineer | `state-machines-and-invariants` |
| Billing, Stripe, subscriptions | Billing Engineer | `monetization-and-billing` |
| Compliance, privacy, LGPD | Compliance Specialist | `compliance-lgpd` |
| CI/CD, Docker, deploy | DevOps Engineer | `devops-ci-cd` |
| Growth, onboarding, conversion | Growth Engineer | `growth-and-launch` |
| Architecture (3+ modules) | VP Engineering | `architecture-decisions` |
| Code review (every change) | Code Reviewer | `code-review-checklist` |

Domain-specific work types are added when you install a domain profile. For example, installing the `fintech` profile adds routes for exchange adapters, financial math, trading execution, etc. See `.claude/skills/domains/fintech/team-personas.md` for the full fintech routing extension.
