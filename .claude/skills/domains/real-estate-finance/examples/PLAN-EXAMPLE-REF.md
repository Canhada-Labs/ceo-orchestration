---
plan_id: PLAN-EXAMPLE-REF
title: "Launch ARM loan product with SOFR index and TRID fee reconfiguration"
status: draft
owner: ceo
level: L3
squad: real-estate-finance
profile: core,real-estate-finance
created_at: 2026-05-10
---

# Example PLAN — ARM Product Launch with SOFR Transition

> **This is an illustrative example**, not a real plan. It shows
> how the real-estate-finance squad coordinates on a loan product
> launch that touches all three VETO scopes: regulatory and client-data
> compliance (Adriana), loan disclosure accuracy (Marcus), and escrow/
> closing workflow (Elena).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`

## 1. Problem

The lender is launching a 5/1 ARM product indexed to SOFR (replacing
a legacy LIBOR-indexed product retired in 2023). The new product requires:
(a) SOFR margin and cap disclosure in the Loan Estimate per updated Reg Z
requirements, (b) reconfiguration of two fees that were previously in the
10% tolerance bucket but must move to zero-tolerance under the new product
structure, and (c) ARM disclosure addendum updates. Additionally, 12
in-flight applications from a pilot cohort need revised LEs issued within
3 business days of the new configuration going live.

Sources:
- Reg Z 12 CFR §1026.18 and §1026.35 — ARM disclosure requirements
- SOFR-indexed ARM: FHFA guidance + Fannie Mae SEL 2022-07
- 12 in-flight pilot applications at various pipeline stages

## 2. Scope

**In:**
- New 5/1 SOFR ARM product configuration in LOS (rate, margin, caps,
  index)
- Updated TRID fee-category mapping: 2 fees moving from 10% bucket to
  zero-tolerance (REF-006)
- ARM disclosure addendum update (worst-case payment example, index source,
  cap structure)
- Revised LEs for 12 in-flight pilot applications (REF-005)
- HMDA product classification for new ARM type (REF-002)
- Processing checklist update for SOFR ARM-specific documentation

**Out:**
- LIBOR-indexed product sunset (separate operational change)
- Secondary market investor notification (separate capital markets workflow)
- Commercial ARM products (different regulatory scope)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Regulatory pre-check | Adriana Ferreira | QM status, SOFR disclosure compliance, HMDA classification (REF-002) |
| P2 — Fee categorisation | Marcus Chen | TRID fee-category mapping for all fees; 2-fee reclassification documented (REF-006) |
| P3 — LE dry run | Marcus Chen | Sample LE APR verified; ARM disclosure addendum populated correctly (REF-005) |
| P4 — In-flight audit | Marcus Chen + Camila Torres | 12 revised LEs identified and issued within 3 business days (REF-005) |
| P5 — Processing checklist | Camila Torres | SOFR ARM-specific income and appraisal documentation requirements |
| P6 — Closing workflow review | Elena Vásquez | Confirm ARM CD generation, rate lock configuration with escrow impact |
| P7 — Post-launch monitoring | Adriana Ferreira | 30-day 10% sample of LEs/CDs for tolerance compliance |
| P8 — Launch review | CEO + all VETO holders | Adriana + Marcus + Elena sign-off |

## 4. Risk axes and VETO holders

- **Adriana Ferreira (Compliance Reviewer):** SOFR ARM disclosure
  requirements differ from LIBOR ARM — specifically the index source
  documentation and margin transparency requirements → BLOCK if any
  SOFR disclosure is generated without Reg Z §1026.18(f) ARM disclosure
  addendum populated (REF-005). HMDA LAR must classify the new product
  correctly → BLOCK if HMDA product code mapping is missing or defaults
  to a prior LIBOR ARM code (REF-002).
- **Marcus Chen (Loan Officer):** The 2 fees reclassified to zero-tolerance
  create cure liability if they exceed the disclosed amount at closing →
  BLOCK if fee-category mapping is deployed without written documentation
  of each fee's TRID category and rationale (REF-006). BLOCK if any
  in-flight application does not receive a revised LE within 3 business
  days of the new product going live (REF-005).
- **Elena Vásquez (Title/Escrow Specialist):** ARM products have a variable
  payment that affects CD accuracy at closing → BLOCK if the CD generation
  logic does not correctly calculate the ARM interest rate and payment at
  the time of closing disclosure (not at origination) (REF-008).

## 5. Task chains invoked

- `real-estate-finance-loan-product-launch` — primary chain for product
  configuration, fee mapping, and in-flight LE issuance
- `real-estate-finance-closing-workflow` — updated to reflect ARM-specific
  CD generation requirements
- `real-estate-finance-client-data-dsrhandling` — skipped (no client data
  deletion or DSR scope in this launch)

## 6. Acceptance

- SOFR ARM product configuration live with all Reg Z ARM disclosures
  populating correctly in sample LE (REF-005)
- All 12 in-flight pilot application revised LEs issued within 3 business
  days of product go-live (REF-005)
- 2 fee reclassifications documented with TRID rationale; zero-tolerance
  bucket confirmed in system configuration (REF-006)
- HMDA product classification confirmed for SOFR ARM type (LAR export
  verified with test record) (REF-002)
- ARM disclosure addendum includes worst-case payment example, SOFR
  index source, and all cap disclosures per Reg Z (REF-005)
- Post-launch 30-day monitoring plan in place: 10% LE/CD sample for
  tolerance compliance

## 7. Metrics

- Revised LE issuance SLA: 100% of in-flight applications receive revised
  LE within 3 business days (zero tolerance — this is a regulatory deadline)
- TRID tolerance compliance: zero cure payments triggered in first 60 days
- **HMDA LAR accuracy rate** (monitored quarterly — percent of ARMs
  correctly classified in LAR export)

## 8. References

- `.claude/skills/domains/real-estate-finance/skills/loan-officer-assistant/SKILL.md`
- `.claude/skills/domains/real-estate-finance/skills/buyer-seller-agent/SKILL.md`
- `.claude/skills/domains/real-estate-finance/task-chains.yaml` — `real-estate-finance-loan-product-launch`
- `.claude/skills/domains/real-estate-finance/task-chains.yaml` — `real-estate-finance-closing-workflow`
- Reg Z 12 CFR §1026.18(f) — ARM disclosure requirements
- Fannie Mae SEL 2022-07 — SOFR ARM guidelines
