---
plan: PLAN-EXAMPLE-GOV
status: draft
owner: CEO (example)
created_at: 2026-04-14
---

# PLAN-EXAMPLE-GOV: Citizen benefits portal — license renewal workflow

> Example plan exercising the government squad's three VETO holders
> in a realistic cross-cutting feature. Intended as reference only;
> not an actual shipping plan.

## §1. Problem

State Department of Motor Vehicles wants to launch an online
driver's-license renewal workflow. Current surface: in-person only.
Target surface: citizen-facing web portal + mobile-responsive,
handling eligibility check, document upload (proof of residency),
payment (credit card), photo update (uploaded or captured), and
issuance tracking.

Regulatory surface: Section 508 (citizen-facing = state ADA Title II
exposure post-2024 DOJ rule), state public-records law (renewal
applications are public records with (b)(6) personal-privacy
redaction), state procurement code (if a vendor provides the
photo-capture or ID-verification component).

## §2. Goals

1. Renewal can be completed end-to-end online by a citizen using
   assistive technology, without in-person visit.
2. Application records meet the state records-retention schedule
   with tombstoning on lifecycle events.
3. Any third-party integration (ID verification SaaS) is procured
   with the integrity-preserving process (bid confidentiality,
   debarment vetting, COI).

## §3. Non-goals

- Replacing the DMV's internal adjudication system (out of scope).
- Handling CDL or commercial-vehicle renewals (separate regime).
- Real-ID upgrades (separate federal compliance workflow).

## §4. Plan

### Phase 0: Procurement of ID verification vendor (if needed)

Owner: **Senator Rafael Hoelzle** (Procurement Integrity Officer, VETO)

- Publish RFP via `gov-publish-rfp` task chain
- COI vetting of requirements authors (GOV-016)
- Bid encryption until scheduled opening (GOV-014); no pre-opening
  amount emission (GOV-013)
- SAM.gov + state debarment check at award (GOV-015)
- Award memo with trade-off rationale (GOV-017)

**Gate:** No ID-verification integration ships without a clean
award trail.

### Phase 1: Records schema + retention mapping

Owner: **Yewande Crossland** (FOIA Compliance Officer, VETO)

- Renewal application = record; retention class per state schedule
  (typically 7 years post-renewal)
- Retention clock anchored to issuance (not submission) (GOV-011)
- Tombstone on lifecycle (withdrawal, denial, issuance) — never
  hard delete (GOV-007)
- FOIA exemption mapping: (b)(6) on SSN/DOB/photo/address; (b)(4)
  on vendor trade-secret if any vendor data co-mingles
- Redaction pipeline at data layer (GOV-008) with exemption +
  legal basis logging (GOV-009)

**Gate:** Schema review with FOIA Officer; no `DELETE` in
migrations.

### Phase 2: Citizen-facing UI

Owner: **Linh Abernathy** (Government A11y Engineer, VETO)
Support: Darius Okonkwo (Public Records Engineer)

- Keyboard-only flow end-to-end (GOV-006)
- Screen-reader pass on NVDA + VoiceOver for full renewal path
- Form labels + ARIA + required-field text indicator (GOV-001)
- Photo-capture step: keyboard/button alternative to camera auto-
  capture; assistive-tech allowlist
- Session timeout warning with extend option (GOV-004)
- Zoom to 200% without reflow breakage
- Color-independent status indicators (application submitted /
  under review / approved / issued / denied)
- VPAT authored at release (GOV-005); refreshed annually

**Gate:** Section 508 checklist green; automated axe-core + manual
screen-reader smoke; VPAT on file.

### Phase 3: Payment + document upload

Owner: Darius Okonkwo
Support: Linh (a11y), Yewande (records), Senator Rafael
(if third-party processor)

- Payment: accessible checkout (WCAG 2.1 AA); PCI scope isolated;
  receipt also retained as record
- Document upload: accept tagged PDFs OR require re-entry in HTML
  form (GOV-020); never accept scanned untagged PDFs for storage
- If a third-party payment processor is integrated, Phase 0
  procurement gate applies

### Phase 4: FOIA responsiveness infrastructure

Owner: Yewande Crossland

- Responsive-records search includes renewal application table,
  supporting docs, audit log, and any vendor-side records (subject
  to contract right-to-audit)
- Requester-identity confidentiality: a citizen cannot request
  records ABOUT another citizen's renewal (privacy) AND the requester
  of their own record (Privacy Act) is not a record-subject risk
- SLA clock machinery per state sunshine law
- Redaction tooling operational before launch (not "we'll add it
  if someone asks")

### Phase 5: Launch + post-launch

- Annual VPAT refresh
- Quarterly FOIA-hold list reconciliation with purge pipeline
- Continuous: COI attestations refreshed for anyone touching
  procurement decisions going forward

## §5. Risks

| Risk | Mitigation |
|---|---|
| Citizen with disability cannot complete renewal | Section 508 VETO gate; real-user testing with disabled users pre-launch |
| Vendor-provided component fails 508 | VPAT required as bid artifact; agency cannot accept "partial supports" without remediation plan |
| SSN/DOB appears in logs | Data-layer redaction at write time; log schema review |
| Records hard-deleted on user "cancel" | Tombstone-only path; admin tool cannot bypass |
| Procurement protest on vendor award | Bid confidentiality + COI + rationale discipline; source-selection memo complete |

## §6. Success criteria

- End-to-end renewal completed with keyboard + NVDA only
- VPAT delivered with "Supports" on all Level A+AA with at most
  documented "Partially Supports" remediation items
- Renewal application retention clock fires at correct event for
  100% of sampled records (migration audit)
- Sample FOIA request completed within state statutory SLA with
  full audit trail reconstructable

## §7. References

- `.claude/skills/domains/government/skills/accessibility-section-508/SKILL.md`
- `.claude/skills/domains/government/skills/foia-and-records/SKILL.md`
- `.claude/skills/domains/government/skills/public-procurement/SKILL.md`
- `.claude/skills/domains/government/task-chains.yaml` (gov-publish-rfp, gov-foia-respond)
- State records retention schedule (agency-specific)
- State sunshine law (agency-specific)
