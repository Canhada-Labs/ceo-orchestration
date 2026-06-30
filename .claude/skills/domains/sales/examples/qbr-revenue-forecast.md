---
plan_id: PLAN-EXAMPLE-SAL
title: "QBR Revenue Forecast Package — Q2 Close"
status: draft
owner: ceo
level: L3
squad: sales
profile: core,sales
created_at: 2026-05-10
---

# Example PLAN — QBR Revenue Forecast Package

> **This is an illustrative example**, not a real plan. It shows
> how the Sales squad coordinates on a quarter-end forecast package
> that touches all three VETO scopes (forecast methodology, deal
> structure integrity, and prospect PII compliance).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/sales/task-chains.yaml`

## 1. Problem

The revenue team needs to produce a locked, exec-ready QBR forecast
package two weeks before quarter-end. The package must include:

- A pipeline snapshot validated against the signed methodology document
- A rep-level attainment projection with commission liability estimate
- An ARR bridge (new + expansion - churn)
- A compliance sign-off confirming all enrichment tool DPAs are active
  for new accounts added this quarter

Sources:
- CRM opportunity records (stage, ARR, close date, probability)
- Comp plan document (quota, ramp, accelerator structure)
- Legal DPA tracker for enrichment and outreach vendors
- Signed Order Forms for Commit-category deals

## 2. Scope

**In:**
- Pipeline snapshot and forecast rollup for the current fiscal quarter
- Rep attainment calculation and commission liability estimate
- Deal-by-deal Commit vs. Upside validation (Order Form on file check)
- Compliance audit for new accounts added via enrichment tool this quarter
- ARR bridge (new + expansion + churn) for the quarter

**Out:**
- Revenue recognition accounting (use finance-accounting squad)
- Board-level financial reporting (CFO-owned process; receives the package as input)
- Customer success renewal pipeline (separate CS forecast process)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — CRM Snapshot + Methodology Validation | Valentina Osei | Pipeline snapshot with close-date and Order Form gap flags (SAL-002, SAL-005) |
| P2 — Attainment + Commission Liability | Valentina Osei | Rep-level attainment table + commission dry-run within 2% of manual check |
| P3 — Deal-by-Deal Commit Review | Marcus Thorne | Commit category validated: signed Order Forms on file, no verbal-only commitments (SAL-005, SAL-006) |
| P4 — Compliance Audit | Priya Srinath | DPA coverage confirmed for all enrichment vendor integrations on new accounts (SAL-009, SAL-010) |
| P5 — ARR Bridge | Valentina Osei | ARR bridge with multi-year credit consistent with comp plan (SAL-007) |
| P6 — Launch Review | CEO + all VETO holders | Forecast + compliance + legal sign-off recorded before package is distributed |

## 4. Risk axes and VETO holders

- **Valentina Osei (Revenue Operations):** Any forecast formula that deviates
  from the signed methodology document → BLOCK if probability weights or ARR
  field mappings have changed without a versioned methodology update (SAL-002).
- **Marcus Thorne (Account Executive Lead):** Any Commit deal without a
  countersigned Order Form on file → BLOCK stage advancement to Closed Won
  until paper is on file (SAL-005, SAL-006).
- **Priya Srinath (Sales Compliance):** Any new account added via enrichment
  tool without an active DPA → BLOCK the account from appearing in forecast
  until DPA is confirmed (SAL-009).

## 5. Task chains invoked

- `sales-qbr-revenue-forecast` — primary chain; runs the full QBR package
  generation workflow
- `sales-enterprise-deal-close` — invoked for each Commit deal above the
  enterprise ARR threshold still lacking a countersigned Order Form at P3

## 6. Acceptance

- CRM snapshot timestamp and methodology doc version are pinned in the package header (SAL-002)
- All Commit-category deals have countersigned Order Forms linked in the CRM (SAL-005)
- Commission dry-run is within 2% of the manual calculation; discrepancies documented with root cause
- No verbal-commitment side letters remain unresolved for any Commit deal (SAL-006)
- DPA coverage confirmed active for 100% of enrichment-sourced accounts added this quarter (SAL-009)
- ARR bridge reconciles to within $1k of the sum of individual opportunity ARR values

## 7. Metrics

- Number of Commit deals requiring Order Form escalation at P3
- Commission liability estimate vs. prior quarter (directional trend)
- **DPA coverage rate for enrichment-sourced accounts** (monitored post-close; target 100%)

## 8. Scenario walkthrough

**Scenario:** Valentina starts the QBR package 12 days before quarter-end.

1. **CRM Snapshot (P1):** Valentina pulls the snapshot and runs the pipeline
   report. She notices 3 deals in the Commit bucket with close dates this
   quarter but no countersigned Order Form attachment. She flags them immediately
   to Marcus Thorne and to the CEO — these deals cannot appear as Closed Won
   until paper is on file (SAL-005 triggered).

2. **Attainment Calculation (P2):** Valentina runs the attainment formula.
   Rep Sofia's attainment shows 112%, triggering an accelerator. Valentina
   cross-checks against the comp plan document. The formula references an ARR
   field that was renamed in a CRM migration two weeks ago (SAL-003 — field
   rename without dependency audit). The formula is silently returning null for
   Sofia's two largest deals. Valentina catches the bug before the package is
   sent; raises an urgent fix with the RevOps engineer.

3. **Commit Review (P3):** Marcus reviews the Commit deals one by one. Deal
   with Acme Corp has a verbal commitment to a custom SLA logged only in an email
   thread. Marcus escalates to Legal to get it captured in an addendum before
   the deal advances (SAL-006 triggered).

4. **Compliance Audit (P4):** Priya audits new accounts added via ZoomInfo
   enrichment this quarter. She finds one EU-based account added after ZoomInfo's
   sub-processor list was updated — she flags a pending DPA re-confirmation
   needed before the account can be counted in the forecast package (SAL-009
   triggered).

5. **ARR Bridge (P5):** Valentina confirms multi-year deals are credited in the
   quarter the ARR is booked (not amortized), consistent with the comp plan.
   One multi-year deal's expansion ARR was double-counted because both the AE
   and the CSM overlay had it as new ARR. Valentina corrects the bridge before
   distribution.

6. **Package sign-off (P6):** CEO, Valentina, Marcus, and Priya review and
   sign off. The three flagged Commit deals have now resolved their Order Form
   gaps. The ZoomInfo DPA re-confirmation is documented as in-progress with a
   48-hour deadline. Package is distributed to the exec team.

**Outcome:** The QBR forecast package is distributed on time, with all Commit
deals backed by signed paper, the commission dry-run within tolerance, and a
documented DPA exception with a resolution path. The compensation restatement
risk from the field-rename bug was caught before the package left RevOps.

**Caveats:**
- This example assumes a single-tier attainment model. Multi-tier accelerators
  (e.g., pay-at-rate from dollar one above 100%) require additional formula
  review in P2.
- The DPA re-confirmation path is advisory: Priya can block the account from
  appearing in forecast if Legal cannot confirm within the deadline.
- This chain does not cover churn-related comp clawback calculations, which are
  governed by a separate clawback policy outside this squad.

## 9. References

- `.claude/skills/domains/sales/task-chains.yaml` — `sales-qbr-revenue-forecast`
- `.claude/skills/domains/sales/task-chains.yaml` — `sales-enterprise-deal-close`
- `.claude/skills/domains/sales/pitfalls.yaml` — SAL-001 through SAL-012
- ADR-009 (squad-bundle completeness contract)
