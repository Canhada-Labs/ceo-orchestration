# Org Chart

> 29 named agents organized into Engineering / Product / Operations + 2 staff with
> cross-cutting veto power. Detailed personas in `.claude/team.md` and
> `.claude/frontend-team.md`.

---

## Backend (18 + 2 staff)

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
 │  VP: Sofia   │          │  VP: Isabela │          │  VP: Nadia   │
 │  arch-decis. │          │  prod-conv.  │          │  obs-and-ops │
 └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
        │                         │                         │
 ┌──────┼──────────┐       ┌──────┼──────┐          ┌──────┼──────────┐
 │      │          │       │      │      │          │      │          │
┌┴───┐ ┌┴───┐    ┌┴────┐ ┌┴───┐ ┌┴───┐ ┌┴────┐    ┌┴───┐ ┌┴───┐    ┌┴───┐
│Kai │ │Luna│    │Tomás│ │Hugo│ │Liam│ │Priya│    │Mara│ │Dant│    │Omar│
│perf│ │API/│    │real │ │grow│ │bill│ │compl│    │chao│ │secu│    │dev │
│-eng│ │trad│    │-time│ │th  │ │ing │ │iance│    │s   │ │rity│    │ops │
└────┘ │/pre│    │/IPC │ └────┘ └────┘ └─────┘    └────┘ └────┘    └────┘
       │dict│    └─────┘
       └────┘
 ┌──────┬─────────┬──────────┐
┌┴───┐ ┌┴────┐  ┌┴───┐    ┌┴────┐
│Alex│ │River│  │Marc│    │Yuki │
│fron│ │data │  │us  │    │test │
│tend│ │/SQL │  │exch│    │ing  │
└────┘ └─────┘  │ang.│    └─────┘
                └────┘

 ╔══════════════════════════════════════╗
 ║  STAFF (report directly to CEO)      ║
 ║  Cross-cutting authority — VETO       ║
 ║                                       ║
 ║  ┌──────────┐    ┌──────────┐         ║
 ║  │ Viktor   │    │  Chen    │         ║
 ║  │ financial│    │ code-    │         ║
 ║  │ math     │    │ review   │         ║
 ║  │ VETO: $  │    │ VETO:    │         ║
 ║  │          │    │ merge    │         ║
 ║  └──────────┘    └──────────┘         ║
 ╚══════════════════════════════════════╝
```

### Backend roster (alphabetical)

| Name | Title | Reports to | Primary skill |
|------|-------|-----------|---------------|
| Alex Rivera | Staff Frontend Engineer | Sofia | `frontend-patterns` |
| Chen Wei | Distinguished Engineer & Reviewer | CEO (staff) | `code-review-checklist` (VETO merge) |
| Dante Rossi | Principal Security Engineer | Nadia | `security-and-auth` |
| Hugo Ferreira | Growth Engineer | Isabela | `growth-and-launch` |
| Isabela Santos | VP Product / Head of Product | CEO | `product-conversion-readiness` |
| Kai Zhang | Principal Performance Engineer | Sofia | `performance-engineering` |
| Liam O'Brien | Billing & Payments Engineer | Isabela | `monetization-and-billing` |
| Luna Park | Staff Backend Engineer | Sofia | `public-api-design` |
| Mara Okonkwo | Chaos & Resilience Engineer | Nadia | `chaos-and-resilience` |
| Marcus Alencar | Exchange Integration Architect | Sofia | `exchange-api-integration` |
| Nadia Volkov | VP Operations / Staff SRE | CEO | `observability-and-ops` |
| Omar Hassan | DevOps & Platform Engineer | Nadia | `devops-ci-cd` |
| Priya Sharma | Compliance & Legal Specialist | Isabela | `compliance-lgpd` |
| River Kim | Principal Data Engineer | Sofia | `data-schema-design` |
| Sofia Nakamura | VP Engineering / Distinguished Architect | CEO | `architecture-decisions` |
| Tomás Herrera | Real-Time Systems Engineer | Sofia | `real-time-market-systems` |
| Viktor Petrov | Staff Quant | CEO (staff) | `financial-correctness-and-math` (VETO $) |
| Yuki Tanaka | Principal QA Architect | Sofia | `testing-strategy` |

---

## Frontend (10 + 1 consultant)

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
 │  Lead: Amara │    │  Lead: Soren │    │  Lead: Keiko │
 │  front-patt. │    │  front-data. │    │  code-review │
 └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
        │                    │                    │
 ┌──────┼──────┐      ┌─────┼─────┐       ┌─────┼──────┐
 │      │      │      │     │     │       │     │      │
┌┴───┐ ┌┴───┐ ┌┴───┐ ┌┴───┐ ┌┴───┐ ┌─┴───┐ ┌─┴────┐
│Rafa│ │Ines│ │Zara│ │Kofi│ │Mei │ │Anil │ │Yara  │
│comp│ │perf│ │a11y│ │ws/ │ │$   │ │auth │ │QA    │
│ents│ │    │ │/i18│ │sse │ │disp│ │veto │ │      │
└────┘ └────┘ └────┘ └────┘ └────┘ └─────┘ └──────┘
```

### Frontend roster (alphabetical)

| Name | Title | Reports to | Primary skill |
|------|-------|-----------|---------------|
| Amara Osei | UI/UX Lead & Design System Owner | CEO | `frontend-patterns` |
| Anil Kapoor | Frontend Security Engineer | Keiko | `security-and-auth` (VETO auth) |
| Hugo Ferreira (consultant) | Growth Engineer (backend) | n/a — consultant | `growth-and-launch` |
| Ines Moreau | Principal Performance Engineer | Amara | `frontend-patterns` + `performance-engineering` |
| Keiko Hayashi | Quality Lead & TypeScript Czar | CEO | `code-review-checklist` |
| Kofi Asante | Real-Time Frontend Systems Engineer | Soren | `real-time-market-systems` + `frontend-data-layer` |
| Mei Chen | Financial Display Engineer | Soren | `financial-display` (VETO display) |
| Rafael Mendez | Senior Component Architect | Amara | `frontend-patterns` |
| Soren Lindqvist | Data Layer Architect | CEO | `frontend-data-layer` |
| Yara Oliveira | Frontend QA Architect | Keiko | `testing-strategy` |
| Zara Ahmadi | Accessibility & i18n Lead | Amara | `frontend-accessibility` (VETO interactive) |

---

## Routing table (who to call)

| Type of work | Agent(s) | Skill |
|--------------|----------|-------|
| OpenAPI, public APIs, SDK | Luna + Chen review | `public-api-design` + `code-review-checklist` |
| Security, auth, encryption | Dante | `security-and-auth` |
| Performance, event loop, memory | Kai | `performance-engineering` |
| Financial math, VWAP, arb | Viktor (VETO) | `financial-correctness-and-math` |
| Supabase, SQL, schemas | River | `data-schema-design` |
| Exchange adapters, WS/REST | Marcus | `exchange-api-integration` |
| Resilience, circuit breakers | Mara | `chaos-and-resilience` |
| Tests, QA, edge cases | Yuki | `testing-strategy` |
| Frontend (React, UX) | Alex + frontend team | `frontend-patterns` |
| WebSocket, IPC, workers | Tomás | `real-time-market-systems` |
| Billing, Stripe, tiers | Liam | `monetization-and-billing` |
| LGPD, compliance, privacy | Priya | `compliance-lgpd` |
| CI/CD, Docker, deploy | Omar | `devops-ci-cd` |
| Growth, onboarding, conversion | Hugo | `growth-and-launch` |
| Architecture (>3 modules) | Sofia | `architecture-decisions` |
| Trading, SOR, market-making | Luna + Viktor VETO | `trading-execution` + `financial-correctness-and-math` |
| AI council, LLM prompts, AI safety | Dante + Luna | `ai-llm-orchestration` + `security-and-auth` |
| Prediction markets, Polymarket, Kalshi | Luna + Viktor VETO | `prediction-markets` + `financial-correctness-and-math` |
| Code review (every change) | Chen | `code-review-checklist` |
| Visual / design system | Amara | `frontend-patterns` (FE) |
| Frontend security | Anil | `security-and-auth` (FE) |
| Frontend perf | Ines | `frontend-patterns` + `performance-engineering` (FE) |
| Frontend a11y / i18n | Zara | `frontend-accessibility` (FE) |
| Frontend financial display | Mei | `financial-display` (FE) |
| Frontend WS/SSE/realtime | Kofi | `real-time-market-systems` (FE) |
| Frontend data/state/queries | Soren | `frontend-data-layer` (FE) |
| Frontend QA | Yara | `testing-strategy` (FE) |
| Frontend code quality / TS | Keiko | `code-review-checklist` + `code-quality-and-typescript` (FE) |
