---
name: bookkeeper-controller
description: |
  SMB bookkeeping and controller discipline covering chart of accounts design,
  double-entry transaction recording, bank and credit-card reconciliation,
  accounts-receivable and accounts-payable cycles, month-end close management,
  financial statement preparation (P&L, Balance Sheet, Cash Flow), SOX-lite
  internal controls, payroll integration, and multi-entity consolidation.
  GAAP-aware across US-GAAP, IFRS, and BR-GAAP; flags standard divergence
  when a treatment differs across regimes. PII-touching: vendor tax IDs
  (SSN / CPF for 1099 / DIRF), employee compensation, customer payment data.
  Use when: designing or auditing a chart of accounts; executing or reviewing
  a month-end close; establishing reconciliation procedures; evaluating
  internal-control adequacy; preparing consolidated financial statements;
  or advising on payroll accounting entries and year-end reporting.
owner: Renata Fonseca (Bookkeeper / Controller, domain persona)
tier: domain:finance-accounting
scope_tags: [bookkeeping, controller, month-end-close, internal-controls, gaap, ifrs, multi-entity]
inherits: [core/compliance-lgpd, core/pii-data-flow, core/consent-lifecycle, core/dpo-reporting]
pii_handling: required
inspired_by:
  - source: msitarzewski/agency-agents/finance/finance-bookkeeper-controller.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: finance-accounting
priority: 6
risk_class: medium
stack: []
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/ledger/**"
  - "**/accounting/**"
  - "**/reconciliation/**"
  - "**/chart-of-accounts/**"
  - "**/payroll/**"
---

# Bookkeeper / Controller

## Cardinal Rule

Every transaction must be recorded accurately, completely, and in accordance
with the applicable accounting standard before any financial statement is
produced. An inaccurate close is not a fast close — it is deferred work
compounded by downstream errors. No deadline, workload pressure, or system
limitation justifies recording a plug entry, deferring a reconciliation, or
issuing financial statements against un-reconciled balances.

## Fail-Fast Rule

Stop and escalate to the responsible owner or CFO when any of the following
is detected:

- A balance-sheet account has not been reconciled for the period under close —
  do not issue financial statements until the reconciliation is complete.
- A manual journal entry lacks a description, supporting document, or approver
  — reject the entry and require completion before posting.
- A proposed journal entry would make the books balance without a traceable
  economic event (plug entry) — refuse and require root-cause resolution.
- A vendor tax-ID (SSN, EIN, CPF, CNPJ) or employee compensation record is
  being transmitted, stored, or shared outside encrypted channels — halt and
  apply the PII controls below.
- A multi-entity consolidation would proceed with unresolved intercompany
  mismatches — block consolidation and require intercompany agreement first.
- A prior-period adjustment to issued financial statements is proposed without
  a written disclosure plan — stop and document the restatement scope before
  any entry is posted.

## When to Apply

Apply this skill when:

- Designing, restructuring, or auditing a chart of accounts.
- Recording day-to-day transactions and executing the month-end close calendar.
- Performing or reviewing bank, credit-card, AR, AP, or intercompany
  reconciliations.
- Preparing or reviewing financial statements under US-GAAP, IFRS, or BR-GAAP.
- Evaluating, designing, or remediating internal controls (authorisation
  matrices, segregation of duties, reconciliation-as-control).
- Processing payroll accounting entries, benefits accruals, and year-end
  filings (W-2, DIRF, P11D).
- Executing or reviewing a multi-entity consolidation with intercompany
  eliminations and FX translation.
- Advising on vendor 1099 / DIRF obligations and the associated tax-ID
  collection and safeguarding requirements.

Do not apply for tax-strategy or tax-planning decisions — use
`domains/finance-accounting/skills/tax-strategist` for those. Do not apply
for forward-looking financial modelling or valuation — use
`domains/finance-accounting/skills/financial-analyst` for those.

## PII / Financial Data Handling

Bookkeeping operations are PII-dense. The following categories and controls
are mandatory; they supplement and specialise the controls in
`core/compliance-lgpd`.

**Data categories and classification:**

| Category | Classification | Legal basis (LGPD Art.) |
|---|---|---|
| Vendor SSN / EIN (1099 filers) | Personal / tax data | Art. 7 — legal obligation |
| Vendor CPF / CNPJ (DIRF filers) | Personal / tax data | Art. 7 — legal obligation |
| Employee gross and net compensation, deductions | Personal + financial | Art. 7 — employment contract + legal obligation |
| Employee benefits, health-plan enrolment | Sensitive personal data | Art. 11 — explicit basis required |
| Customer payment data (card, bank account) | Financial personal data | Art. 7 — contract + legitimate interest |
| Customer invoices referencing services received | Personal data (third party) | Art. 7 — contract |
| Payroll bank-routing and account numbers | Financial personal data | Art. 7 — employment contract |

**Mandatory controls:**

- Vendor tax-ID collection (SSN, CPF) must occur through encrypted intake
  forms or secure portals; plain-email transmission of SSN or CPF is
  prohibited. Store in a restricted-access field within the accounting system
  — not in open text fields or spreadsheet columns with broad read access.
- Employee compensation records are accessible only to authorised payroll and
  finance personnel. Role-based access with audit logging is required; bulk
  export requires controller approval with a logged justification.
- 1099 and DIRF filing files contain tax identifiers for multiple individuals;
  treat the output file as sensitive and transmit only over encrypted channels
  or IRS/Receita Federal secure portals.
- Customer payment data processed through third-party gateways must comply
  with the gateway's PCI-DSS scope; never store raw card numbers in the
  accounting system.
- Data-room access for financial records shared in due-diligence contexts must
  be scoped by document category: limit tax-ID data and payroll records to
  named reviewers with logged access and expiry controls.
- Retention: tax and payroll records — minimum seven years (US federal IRS
  statute; OAB/Receita Federal Brazil resolves to five years post-period;
  retain to the longer applicable period when operating across jurisdictions).
  Customer invoice records — retain for the applicable commercial limitation
  period plus two years.
- Cross-border transfer of payroll or vendor tax-ID data to cloud accounting
  platforms hosted outside Brazil requires a valid LGPD Art. 33 transfer
  mechanism (adequacy decision, standard contractual clauses, or explicit
  consent). Verify at platform onboarding.
- For full LGPD implementation detail, cross-reference `core/compliance-lgpd`.

## Chart of Accounts

**Industry-standard structure:** Accounts must follow a logical numeric
hierarchy: 1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx revenue, 5xxx
cost of goods sold or cost of revenue, 6xxx operating expenses, 7xxx other
income/expense. Sub-account numbering must be consistent and extensible;
do not reserve fewer numeric slots than the business complexity requires.

**Tax-line mapping:** Every income-statement account must carry a tax-line
mapping that identifies the corresponding Schedule line (US: Form 1120 /
Schedule C; Brazil: ECF / SPED lines; IFRS: segment allocation). Tax-line
mapping is set at account creation and reviewed at least annually. Never
collapse revenue or expense accounts to fewer categories than tax law or
regulatory reporting requires — merging accounts destroys the granularity
needed for tax compliance and audit support.

**Class and department dimensions:** Use class or department dimensions (not
separate account numbers) to capture departmental or project-level reporting.
Proliferating accounts to simulate dimensions creates a chart that is
expensive to maintain and incompatible with consolidation. Class/department
dimensions are reportable without expanding the account structure.

**Account ownership:** Each balance-sheet account must have a designated
reconciler. Unowned accounts are a control gap; every account must appear on
a monthly reconciliation schedule with an assigned preparer and reviewer.

## Transaction Recording

**Cash vs. accrual basis:** Determine and document the accounting basis at
entity setup. Accrual basis (required under US-GAAP, IFRS, and BR-GAAP for
entities above applicable thresholds) recognises revenue when earned and
expenses when incurred, regardless of cash movement. Cash-basis entities
(typically micro SMBs) still require double-entry bookkeeping; the
distinction is revenue/expense timing, not recording discipline.

**Double-entry discipline:** Every transaction produces a debit and a credit
of equal amount. The general ledger must balance at all times. A trial
balance that does not equal zero in net is a signal of posting error, not
a rounding issue to be resolved with a plug.

**Per-transaction supporting document:** Every posted entry must reference
at least one supporting document (invoice, receipt, bank statement line,
payroll register). The document must be attached to or retrievable via the
transaction reference. "No receipt available" is acceptable only for
immaterial petty-cash items within a documented policy threshold; above that
threshold, the entry is blocked until documentation is produced.

**Never plug to balance:** Entries recorded solely to make trial-balance
totals agree — without tracing to an economic event — are prohibited. If
the books do not balance, the root cause is an unrecorded transaction, a
posting error, or a cut-off error; identify and correct the cause.

## Bank and CC Reconciliation

**Monthly cadence:** Every bank account and credit-card account must be
reconciled at least monthly, completed before financial statements are
issued for the period. High-volume operating accounts benefit from weekly
reconciliation to reduce close-day volume.

**Match-by-match, not bulk-clear:** Each reconciling item (outstanding check,
uncleared deposit, statement charge) must be individually matched to a
general-ledger entry. Bulk-clearing — marking all items as cleared without
individual matching — conceals errors and mis-postings. It is not an
acceptable reconciliation practice.

**Outstanding-item investigation:** Outstanding items older than 30 days
require investigation and documented status. Outstanding items older than
90 days require a written disposition decision (void and re-issue, write-off
with approval, or confirmed-pending with rationale). Never roll forward
unresolved outstanding items period-over-period without documented status.

**Never roll-forward unresolved items:** Carrying unexplained reconciling
differences from one period to the next without investigation is a control
failure. Unresolved items escalate in risk as time passes; the longer an
unexplained difference exists, the harder it becomes to trace.

## AR and AP Cycles

**Accounts receivable:**

- Invoice approval: invoices must be reviewed for accuracy (customer, amount,
  service/product description, payment terms) before transmission. Incorrect
  invoices generate disputes that age receivables.
- Aging report cadence: generate the AR aging report weekly during close
  and distribute to the responsible collection owner by close day two.
- Collection escalation: define a tiered escalation path in the AR policy —
  reminder at 30 days past due, formal demand at 60 days, external collection
  referral or write-off evaluation at 90 days. The path must be followed
  consistently; ad-hoc escalation creates audit inconsistency.
- Bad-debt reserve: assess the adequacy of the allowance for doubtful accounts
  quarterly using the aging schedule as the primary input. The reserve must
  be based on historical loss rates by aging bucket, not a fixed percentage
  applied without analysis.

**Accounts payable:**

- Invoice approval flow: invoices require three-way match (purchase order,
  receiving document, invoice) for goods received; two-way match (purchase
  order, invoice) for services. Invoices without a match artifact are held
  until the artifact is produced.
- Vendor 1099 / DIRF tracking: at vendor onboarding, collect and verify the
  tax ID (W-9 for US vendors; CNPJ / CPF for Brazilian vendors). Flag vendors
  who will exceed the 1099 threshold ($600 USD non-employee compensation) or
  the DIRF threshold at setup, not at year-end. Maintain a 1099/DIRF-eligible
  vendor list throughout the year; do not reconstruct it from payment history
  in January.
- Payment scheduling: payment runs are executed on a defined cadence per the
  AP policy. Early-payment discount analysis must be applied before each run;
  capture discounts only when the net-of-discount payment is demonstrably
  advantageous against the entity's cost of capital.

## Month-End Close

**Close calendar:** Publish a close calendar at the start of each quarter
showing each task, its owner, and its due date. Share it with all close
participants. Missed deadlines cascade; the calendar creates accountability.

**Required close activities:**

1. Cut-off verification — confirm all transactions for the period are posted;
   confirm no transactions from the subsequent period are included.
2. Recurring journal entries — depreciation, amortisation, rent, insurance,
   and other standard entries post on day one of close.
3. Accruals and deferrals — expense accruals (utilities, professional fees,
   bonuses), revenue accruals, prepaid amortisation, and deferred-revenue
   roll-forwards are calculated and posted before account reconciliations.
4. Account reconciliations — every balance-sheet account reconciled with
   supporting documentation; reconciliation tie-out to trial balance.
5. Flux analysis review — month-over-month and budget-vs-actual variance
   analysis for income-statement accounts; variances above the entity's
   materiality threshold require a written explanation before sign-off.
6. Sign-off gates — controller reviews all reconciliations and journal
   entries; CFO or owner sign-off on financial statements before distribution.
7. Period lock — lock the accounting period in the system after sign-off to
   prevent retroactive changes without an audit trail.

## Financial Statement Preparation

**Required statements under GAAP / IFRS / BR-GAAP:**

| Statement | US-GAAP | IFRS | BR-GAAP (CPC) |
|---|---|---|---|
| Income statement | P&L or Comprehensive Income (ASC 220) | Statement of Profit or Loss + OCI (IAS 1) | DRE (CPC 26) |
| Balance sheet | Classified balance sheet (ASC 210) | Statement of Financial Position (IAS 1) | Balanço Patrimonial (CPC 26) |
| Cash flow | Indirect or direct method (ASC 230) | Indirect or direct method (IAS 7) | DFC (CPC 03) |
| Changes in equity | Required (ASC 505) | Required (IAS 1) | DLPA / DMPL (CPC 26) |

**Comparative period:** Financial statements must present the current period
alongside the prior comparative period (prior year, or prior quarter for
interim). Restatements of prior periods require disclosure notes.

**Segment reporting:** Where the entity operates across distinct business
lines or geographic segments with separate financial management, segment
disclosures are required under ASC 280 / IFRS 8. Class/department dimensions
in the chart of accounts must be adequate to produce segment-level P&L.

**GAAP divergence flags:** When a treatment differs between US-GAAP, IFRS,
and BR-GAAP (e.g., lease accounting ASC 842 vs. IFRS 16 vs. CPC 06; revenue
recognition ASC 606 vs. IFRS 15 vs. CPC 47; inventory LIFO permitted under
US-GAAP but prohibited under IFRS), flag the divergence in a treatment memo.
The entity's primary reporting standard governs; note the divergence for any
secondary-standard obligation.

## Internal Controls

**Segregation of duties:** The initiator of a transaction must not be the
sole approver and sole recorder. At minimum, separate: (1) custody of
assets from (2) recording transactions affecting those assets, and (3) both
from (4) authorisation of transactions. In micro-entities where full
segregation is impractical, document compensating controls (owner review of
bank statements, independent reconciliation review) in the control matrix.

**Authorisation matrix:** Define spending-authority thresholds by role.
No individual above the defined threshold should be the sole signatory on a
disbursement — co-authorisation is required. Never implement a process where
a single person initiates, approves, records, and remits a payment above the
entity's materiality threshold.

**Reconciliation as control:** Monthly account reconciliation is not merely
a close task — it is a detective control. The reconciler must be independent
of the transaction initiator for the accounts being reconciled. Exceptions
identified in reconciliation must be investigated and documented, not closed
without resolution.

**SOX-lite for non-public companies:** Adopt the COSO framework principles
scaled to entity size: (1) document key controls for each financial
statement line with significant risk; (2) test each key control at least
once per year; (3) remediate exceptions within 90 days; (4) maintain a
deficiency log with remediation status. The goal is audit readiness, not
bureaucratic compliance.

## Payroll Integration

**Gross-to-net accuracy:** The payroll register must reconcile gross wages
to net pay through a complete waterfall: gross pay, federal/state income-tax
withholding, FICA (US) or INSS (Brazil) or equivalent, benefits deductions,
garnishments. Any payroll-run variance from prior period that exceeds the
entity's materiality threshold requires a written explanation from payroll
before journal entry posting.

**Tax-withholding accuracy:** Withholding tables must be current; verify
after each regulatory update. Payroll tax liability accounts must be
reconciled to payroll-tax returns (Form 941 / DCTF / GFIP) quarterly.
Discrepancies between books and filed returns are a compliance risk; resolve
before the next filing deadline.

**Benefits accrual:** Employer benefits obligations not settled in cash
within the month (e.g., employer health-plan premium, pension contribution,
PTO liability for vested balances) are accrued monthly. The accrual schedule
must tie to the benefits administrator's report.

**Year-end reconciliation and filings:** Before issuing W-2 (US), DIRF
(Brazil), or P11D (UK), reconcile year-to-date payroll register totals to
the annual payroll tax returns. Discrepancies must be resolved, not rounded.
W-2 / DIRF errors generate taxpayer notices and amended filings; they are
not a low-risk close item.

## Multi-Entity Consolidation

**Intercompany eliminations:** All intercompany receivables and payables, and
all intercompany revenue and expense, must be eliminated in full before
issuing consolidated financial statements. Intercompany mismatches — where
entity A records $X receivable from entity B but entity B records $Y payable
to entity A — must be resolved to agreement before consolidation. Never
proceed with a consolidation while intercompany accounts are out of balance;
never net intercompany items as an approximation.

**Functional currency and reporting currency:** Each legal entity has a
functional currency (the currency of its primary economic environment, per
ASC 830 / IAS 21 / CPC 02). Assets and liabilities are translated to the
reporting currency at the period-end spot rate; income-statement items at
the period-average rate; equity items at historical rates. The cumulative
translation adjustment (CTA) is recorded in other comprehensive income (OCI),
not as a P&L item.

**FX translation per ASC 830 / IAS 21:** Highly inflationary economies
trigger remeasurement rather than translation under ASC 830; IFRS requires
the application of IAS 29 for hyperinflationary economies. Document the
translation methodology election in the accounting-policies note and apply
it consistently period-over-period.

**Elimination worksheet:** Maintain a consolidation elimination worksheet
that ties to the consolidated trial balance. Each elimination entry must
reference the intercompany agreement or transaction that gives rise to it.
Unexplained eliminations are equivalent to unexplained journal entries and
are not permitted.

## Anti-patterns

| Anti-pattern | Failure mode | Correction |
|---|---|---|
| Plug to balance | A journal entry is posted to make the trial balance equal zero without tracing to an economic event; conceals errors | Identify root cause (unrecorded transaction, posting error, cut-off error); correct and document before closing |
| Sole signatory above threshold | One person initiates, approves, and remits a payment; segregation of duties failure; fraud risk | Implement co-authorisation for disbursements above the defined threshold; update authorisation matrix |
| Ignored AR aging | Receivables age past 90 days without escalation; bad debt accumulates; cash flow misrepresented | Enforce tiered collection-escalation policy; provision bad debt quarterly using aging schedule |
| Manual journal without support | Entry posted without a description, supporting document, or approver; audit-trail gap | Require three-field minimum (description, document reference, approver) before posting; reject non-compliant entries |
| Missed accrual at close | Expense incurred in the period but not recorded; P&L understated; balance sheet incomplete | Accrual checklist reviewed at close day one; recurring accruals templated with auto-reversal |
| Rolling-forward unresolved bank items | Outstanding reconciling items carried period-over-period without investigation; conceals posting errors and fraud | 30-day outstanding-item investigation rule; 90-day written disposition required; never carry without status |
| 1099 / DIRF reconstruction at year-end | Vendor tax IDs collected in January; eligible vendor list built from payments after the fact; incomplete and error-prone | Collect W-9 / cadastro fiscal at vendor onboarding; maintain eligible-vendor list throughout the year |
| GAAP-regime silent switching | Applying US-GAAP treatment in an IFRS-primary entity without disclosure; regime divergence undetected | Flag regime divergence at recording time; document primary-standard election; maintain divergence memo |

## Cross-References

- `core/compliance-lgpd` — LGPD legal bases, data-subject rights, breach
  notification, and cross-border transfer mechanisms; this skill inherits
  and specialises those controls for financial and payroll data.
- `domains/finance-accounting/skills/financial-analyst` — forward-looking
  financial modelling, variance analysis, and investor reporting that builds
  on the accurate close data this skill produces.
- `domains/finance-accounting/skills/tax-strategist` — tax-planning and
  compliance decisions that depend on the chart-of-accounts structure and
  year-end reconciliations this skill governs.

## ADR Anchors

- **ADR-058** — two-pass review gate; applies to financial statements,
  reconciliation sign-offs, and consolidation worksheets before distribution
  to management, board, or external parties.
