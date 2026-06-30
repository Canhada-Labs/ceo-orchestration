---
plan_id: PLAN-EXAMPLE-FIN
title: "Launch usage-based pricing tier with professional services bundle"
status: draft
owner: ceo
level: L3
squad: finance-accounting
profile: core,finance-accounting
created_at: 2026-05-10
---

# Example PLAN — Launch usage-based pricing tier with professional services bundle

> **This is an illustrative example**, not a real plan. It shows how the
> finance-accounting squad coordinates on a new revenue stream that introduces
> multiple performance obligations, a variable-consideration element, and
> cross-border tax implications.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/finance-accounting/task-chains.yaml`

## 1. Problem

A B2B SaaS company currently sells only annual subscriptions at fixed per-seat
pricing. The growth team is launching a new "Enterprise Plus" tier that bundles:
(1) a platform subscription at a fixed monthly fee, (2) usage-based API calls
billed in arrears at $0.002/call, and (3) a 40-hour professional services
onboarding block, with unused hours expiring at end of month 3. The product
team wants to go live in 6 weeks. No recognition policy exists for usage-based
revenue or bundled professional services. The company operates entities in
Brazil and the UK; some Enterprise Plus customers will be in both jurisdictions.

Sources:
- Product spec: Enterprise Plus tier pricing v2.3 (internal doc)
- Legal: draft Master Subscription Agreement for Enterprise Plus
- Finance: current revenue recognition policy covers only annual fixed-fee
  subscriptions (last updated 2024-01-15)

## 2. Scope

**In:**
- ASC 606 / CPC 47 performance-obligation analysis for the three-component bundle
- Variable-consideration estimation methodology for API call revenue
- Professional services accounting treatment (distinct obligation vs. bundled)
- Transfer pricing documentation for intercompany service charges between
  Brazil holding and UK entity on shared platform infrastructure
- UK VAT registration threshold assessment for cross-border digital services
- GL account configuration for usage-based revenue and deferred professional
  services obligation

**Out:**
- Go-live pricing optimisation and competitive analysis (product/marketing)
- Customer contract negotiations above standard terms (legal)
- Sales commission plan design for Enterprise Plus (HR/finance-accounting
  shared scope — handled in a separate plan)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — POB analysis | Renata Fonseca | Written recognition policy memo for Enterprise Plus bundle |
| P2 — Tax structure | Valentina Fiscal | TP memo for intercompany charges, UK VAT threshold, BR PIS/COFINS treatment |
| P3 — FP&A model | Marcelo Santos | Usage-based revenue driver model, deferred PS obligation projection |
| P4 — GL configuration | Cintia Barros | New GL accounts, close checklist items, booking entries documented |
| P5 — Control design | Eduardo Marques | SOD confirmed for usage metering, billing reconciliation, revenue posting |
| P6 — Launch review | CEO + all VETO holders | Controller + Tax + Audit sign-off before first invoice |

## 4. Risk axes and VETO holders

- **Renata Fonseca (Financial Controller):** The three-component bundle
  creates at minimum three performance obligations under ASC 606 / CPC 47.
  Professional services must be evaluated as distinct (likely yes — customer
  can use the platform without the onboarding). Usage-based API calls must
  use a usage-has-occurred recognition point, not a commitment-based point →
  BLOCK if any revenue is recognised before performance obligation satisfied;
  BLOCK if first invoice issues without signed recognition policy memo (FIN-001, FIN-002).
- **Valentina Fiscal (Tax Practitioner):** Intercompany platform infrastructure
  charges from BR to UK entity are a transfer pricing event under OECD
  Guidelines and RFB IN 1.312. The UK entity's customer revenue also triggers
  UK VAT registration threshold analysis for cross-border digital services →
  BLOCK if first intercompany invoice is raised without a TP documentation
  memo; BLOCK if UK entity exceeds VAT threshold without registration (FIN-005, FIN-006).
- **Eduardo Marques (Audit Specialist):** Usage metering (the system that
  counts API calls) must be independent of the billing system that converts
  counts to invoices — same person should not control both. BLOCK if access
  provisioning allows a single person to modify usage meters AND approve
  billing runs (FIN-009).

## 5. Task chains invoked

- `finance-accounting-new-revenue-stream` — primary chain: performance-
  obligation analysis → recognition policy memo → tax treatment → FP&A
  model → GL configuration → control design → launch VETO.
- `finance-accounting-period-end-close` — extended with new checklist items
  for usage accrual (billable API calls in the period not yet invoiced),
  deferred PS obligation drawdown, and intercompany transfer pricing
  reconciliation. These are added before the first close cycle that includes
  Enterprise Plus customers.

## 6. Acceptance

- Recognition policy memo: three performance obligations identified, SSPs
  allocated, variable-consideration methodology for API calls documented,
  PS expiration treatment documented — signed by Renata Fonseca before
  first invoice (FIN-002)
- TP documentation memo: functional analysis of BR vs. UK entity roles,
  arm's-length methodology for infrastructure charge, signed by Valentina
  Fiscal before first intercompany invoice (FIN-005)
- UK VAT: threshold assessment documented; registration initiated if
  any Enterprise Plus customer is in the UK before go-live
- GL: usage-based revenue account, deferred PS obligation account, and
  usage accrual account created with Controller approval
- SOD: usage metering access list confirmed separate from billing approval
  access list (FIN-009)
- Close checklist: Enterprise Plus-specific items added before first
  period-end close containing Enterprise Plus revenue (FIN-012)

## 7. Metrics

- Usage-based revenue vs. ARR as a percentage of total revenue (mix shift
  monitoring for recognition pattern validity)
- Deferred PS obligation balance vs. earned — variance flag if earned rate
  deviates more than 10% from 40-hour-over-90-day ratable assumption
- **Transfer pricing reconciliation variance** (monitored quarterly; any
  intercompany charge deviation from TP memo arm's-length range triggers
  FIN-005 remediation review with Valentina Fiscal)

## 8. References

- `.claude/skills/domains/finance-accounting/skills/bookkeeper-controller/SKILL.md`
- `.claude/skills/domains/finance-accounting/skills/tax-strategist/SKILL.md`
- `.claude/skills/domains/finance-accounting/skills/fpa-analyst/SKILL.md`
- `.claude/skills/domains/finance-accounting/task-chains.yaml` — `finance-accounting-new-revenue-stream`
- `.claude/skills/domains/finance-accounting/pitfalls.yaml` — FIN-001, FIN-002, FIN-005, FIN-006, FIN-009, FIN-012
