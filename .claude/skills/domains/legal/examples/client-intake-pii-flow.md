---
plan_id: PLAN-EXAMPLE-LEG
title: "AI-Assisted Client Intake — Conflict Check + Matter Opening with Privilege Controls"
status: draft
owner: ceo
level: L3
squad: legal
profile: core,legal
created_at: 2026-05-10
---

# Example PLAN — AI-Assisted Client Intake

> **This is an illustrative example**, not a real plan. It shows how the
> Legal squad coordinates on an AI-assisted client intake feature that
> touches all three VETO scopes (client data/privilege, records lifecycle,
> and billing/trust account initialization).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/legal/task-chains.yaml`

## 1. Problem

A mid-size law firm using the platform wants to accelerate client intake
by using an AI tool to pre-screen conflict check results, classify incoming
matter types, and draft the initial engagement letter. The intake process
currently takes 2-3 hours of paralegal time per new matter. The AI-assisted
workflow is projected to reduce this to 30 minutes.

The challenge: the AI tool must be integrated without exposing attorney-client
privileged content to a vendor without a qualifying DPA, and the conflict-check
result must never expose one client's matter details to another client's
intake context.

Sources:
- Intake form data (client name, matter description, adverse parties, jurisdiction)
- Existing matter database (for conflict screening — adverse party index only)
- AI tool API (for conflict pre-screening, matter classification, letter drafting)
- Trust account system (if retainer is collected at intake)

## 2. Scope

**In:**
- Conflict check (adverse party screening against closed and open matters)
- Client PII collection and data residency assessment (GDPR/LGPD)
- Matter record creation with append-only document store and privilege classification
- AI-assisted engagement letter drafting (with attorney review gate before delivery)
- Trust account initialization if retainer is collected at intake

**Out:**
- Full billing system configuration for the matter (separate matter-setup workflow)
- E-discovery and litigation hold (separate legal-litigation-hold chain)
- Any AI tool that receives the full matter file without DPA coverage (blocked by Ingrid VETO)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — AI Tool DPA Review | Ingrid Vasquez + Chloé Bernard | DPA signed and technically verified; privilege scope document drafted (LEG-001) |
| P2 — Conflict Check System | Amir Nakashima | CLEAR/CONFLICT-only result; no cross-matter exposure (LEG-002) |
| P3 — PII + Residency Assessment | Ingrid Vasquez | Data residency confirmed; SCCs executed for EU/BR intake (LEG-004) |
| P4 — Matter Record Creation | Amir Nakashima | Append-only matter record; privilege ACL; retention class assigned (LEG-005) |
| P5 — Trust Account Init | Elena Sorokina | Three-way reconciliation baseline; retainer ledger initialized (LEG-009) |
| P6 — Launch Review | CEO + all VETO holders | Privilege, records, billing sign-offs recorded before first live matter |

## 4. Risk axes and VETO holders

- **Ingrid Vasquez (Compliance Officer):** Any AI tool that ingests client matter
  text without a DPA covering privileged content → BLOCK until DPA is signed and
  technically verified (LEG-001). Cross-matter exposure in conflict check → BLOCK
  immediately (LEG-002).
- **Tobias Mensah (Records Manager):** Any matter record that does not have a
  retention class assigned at creation → BLOCK matter from moving to active status
  until retention class is confirmed (LEG-005).
- **Elena Sorokina (Legal Operations Lead):** Any trust account initialization that
  does not produce a three-way reconciliation baseline before funds are received →
  BLOCK trust account from accepting the retainer (LEG-009).

## 5. Task chains invoked

- `legal-client-intake-pii-flow` — primary chain; runs the full intake workflow
  from conflict check through matter opening and trust account initialization
- `legal-ai-tool-onboarding` — invoked at P1 for the AI engagement-letter
  drafting tool; runs before any client content is processed

## 6. Acceptance

- Conflict check returns CLEAR/CONFLICT only; underlying matter details are not
  accessible to the intaking attorney for the conflicting matter (LEG-002)
- DPA for the AI drafting tool explicitly covers attorney-client privileged material;
  zero-retention claim verified technically (LEG-001)
- EU/BR client intake confirms data residency; SCCs are executed before the first
  data transfer to the processing stack (LEG-004)
- Every matter record created via the intake flow has a retention class and expected
  destruction date assigned at creation (LEG-005)
- AI-generated engagement letter output is flagged as draft; attorney attestation
  is required before the letter is sent to the client (LEG-012)
- Trust account three-way reconciliation baseline is recorded before any retainer
  funds are accepted (LEG-009)

## 7. Scenario walkthrough

**Scenario:** Intake coordinator Selena uses the AI-assisted intake flow for a
new corporate client, Nexum Holdings, seeking representation on a commercial
dispute with Apex Corp.

1. **Conflict Check (P2):** The system runs the adverse party index against all
   open and closed matters. The result returns: CONFLICT DETECTED. Selena sees
   only "CONFLICT DETECTED — escalate to supervising attorney." She does NOT see
   which matter or which attorney represents the conflicting party (LEG-002).
   The supervising attorney reviews the matter-level detail in a privileged
   view and determines it is a non-disqualifying conflict (different matter type,
   screened attorney). Intake continues with a conflict waiver on file.

2. **PII + Residency (P3):** Nexum Holdings is incorporated in the UK (post-Brexit).
   Ingrid reviews the processing stack: the matter management system's primary
   data center is in São Paulo. Ingrid confirms UK adequacy regulations post-Brexit
   are in effect for this data flow and documents the assessment. If the client
   were in the EU, UK SCCs would be required; the adequacy decision covers this case.

3. **AI Tool DPA (P1):** The engagement letter drafting tool is a third-party LLM
   API. Chloé reviews the DPA. The vendor's DPA covers attorney-client privileged
   content but contains a vague clause about "model quality improvements." Chloé
   escalates to Ingrid. Ingrid requires the vendor to provide a written amendment
   confirming no training use of client matter content before the tool goes live
   (LEG-001 triggered). The amendment is received and appended to the DPA.

4. **Matter Record (P4):** Amir initializes the matter record with privilege
   classification "attorney-client privileged" as default for all documents.
   Tobias assigns the retention class: client file (7 years post-closure) and
   firm work product (10 years post-closure). The expected destruction date for
   the client file is computed from matter creation date + active period + 7 years
   and stored in the record.

5. **Trust Account (P5):** Nexum Holdings pays a $25,000 retainer. Elena initializes
   the trust account ledger. Before the retainer is processed, the system runs a
   three-way reconciliation baseline (matter ledger = $0, client ledger = $0, bank
   confirmation pending). The retainer is posted only after the bank confirms receipt.
   Elena reviews the reconciliation output — all three balances now show $25,000
   inbound correctly (LEG-009).

6. **Launch Review (P6):** CEO, Ingrid, Tobias, and Elena sign off. The AI tool
   generates a draft engagement letter. The supervising attorney reviews, corrects
   a clause that was subtly wrong (the AI had hallucinated a jurisdiction-specific
   fee-disclosure requirement that does not apply here — caught at human review,
   LEG-012), attests the letter, and sends it to Nexum Holdings.

**Outcome:** The matter is opened in 35 minutes (vs. the prior 2-3 hours).
The conflict waiver is documented, the AI tool is operating under a qualifying
DPA, the matter record is append-only with retention class, the trust account
is reconciled, and the engagement letter was sent only after attorney attestation.
The AI hallucination on the fee-disclosure clause was caught before it reached
the client.

**Caveats:**
- This example assumes the conflict waiver is straightforward. A disqualifying
  conflict blocks the entire intake flow and does not reach steps 3-6.
- The AI drafting tool operates only on the intake form data, not on the full
  matter file. As the matter develops, any AI access to matter documents requires
  re-running the legal-ai-tool-onboarding chain for the expanded scope.
- Trust account handling for multi-currency retainers requires additional FX
  reconciliation logic outside this squad's scope.

## 8. Metrics

- Intake time per new matter (target: < 45 minutes end-to-end)
- Conflict detection accuracy (CLEAR/CONFLICT vs. manual review comparison)
- **AI hallucination rate in engagement letters** (monitored post-launch; target < 2% requiring attorney correction)

## 9. References

- `.claude/skills/domains/legal/task-chains.yaml` — `legal-client-intake-pii-flow`
- `.claude/skills/domains/legal/task-chains.yaml` — `legal-ai-tool-onboarding`
- `.claude/skills/domains/legal/pitfalls.yaml` — LEG-001 through LEG-012
- ADR-009 (squad-bundle completeness contract)
- ADR-111 (PLAN-080 Phase 0a PII core promotion — inherited by legal domain)
