---
title: Sentinel-Signers Rotation Policy — DRAFT
status: DRAFT
plan: PLAN-086
wave: F.4
next_plan: PLAN-089
related_adrs:
  - ADR-119-sentinel-unlock-contract
  - ADR-010-canonical-edit-policy
  - ADR-040-AMEND-2-credential-blocking
related_findings:
  - F-A-IDA-T-0004 (sentinel-signers SPOF)
veto_case: B
---

# Sentinel-Signers Rotation Policy — DRAFT

> **STATUS: DRAFT.** Enumerates the four mandatory fields of the
> sentinel-signers rotation policy as TBD-placeholders per PLAN-086
> Wave F M-10 fold. Authoritative spec ships in **PLAN-089**.
>
> No production code reads this document yet.

## Scope

The sentinel-signers list at `.claude/sentinel-signers.txt` currently
contains a single Owner-physical GPG key — a documented single-point-
of-failure (finding **F-A-IDA-T-0004**). This DRAFT enumerates the
four fields the rotation policy MUST specify.

## ADR-119 binding

Bound to **ADR-119 (sentinel-unlock-contract)**, parent ADR governing
sentinel-signers semantics. ADR-119 PROPOSED at PLAN-086 Wave I; on
acceptance this DRAFT promotes to non-DRAFT spec via PLAN-089 ceremony.

## The four mandatory fields (M-10 fold, all TBD)

### Field 1 — Cold-key recovery procedure (TBD)

**Purpose:** Defines how a NEW signer key is added to
`sentinel-signers.txt` when primary key is lost/compromised/unavailable.

**TBD specifics PLAN-089 must resolve:**

- Cold-key storage location (air-gapped hardware token recommended).
- Cold-key activation ceremony (who, where, with witnesses).
- Cold-key signing scope (signs a NEW `sentinel-signers.txt` only).
- Cold-key rotation cadence (≤ 365 days recommended).
- Recovery test cadence (≥ once per release-train cycle).

**Anti-pattern guard:** cold-key MUST NOT share physical medium with
the primary key.

### Field 2 — Quorum M-of-N ≥ 2 (TBD)

**Purpose:** Replace single-signer authority with M-of-N quorum for
high-severity ceremonies (canonical-path edits, ADR amendments to
security kernel, branch-protection bypass).

**TBD specifics PLAN-089 must resolve:**

- N (total signers) — recommend 3.
- M (required) — recommend 2 (any two of N).
- Per-ceremony override (some ceremonies may require M=N).
- Aging policy (each signer in N has own `expires_at` per Field 4).
- Quorum-loss recovery (N < 2 active → refuse new ceremonies).

**Anti-pattern guard:** M ≥ 2 non-negotiable.

### Field 3 — `revoked_signers` block schema (TBD)

**Purpose:** Append-only revocation ledger for compromised/retired
signer keys that remain in historical sentinel-signers.txt chain.

**TBD specifics PLAN-089 must resolve:**

- File location (`.github/revoked-signers.txt` recommended).
- Schema per row:
  - `signer_id` (canonical fingerprint).
  - `revoked_at` (RFC 3339).
  - `revoked_by` (signer_id, MUST be in quorum).
  - `reason` (compromise/retirement/inactive/unknown).
  - `signature` (detached signature of row by revoker).
- Verification cadence (every sentinel-acceptance consults this file).
- Quorum requirement for revocation (recommend M=N).

**Anti-pattern guard:** revocations are append-only.

### Field 4 — `expires_at` per entry (TBD)

**Purpose:** Cap each signer's authority lifetime.

**TBD specifics PLAN-089 must resolve:**

- Format (RFC 3339).
- Default lifetime (365 days from issuance).
- Renewal ceremony (M-of-N excluding renewee; no self-renewal).
- Grace period (warn-only for N days after expires_at; recommend 14).
- Audit-emit field `signer_id` + `signer_expires_at` on `sentinel_signer_used` event (M-10).

**Anti-pattern guard:** `expires_at` mandatory per row; missing →
validator reject.

## Implementation surface (deferred to PLAN-089)

- `.claude/scripts/check_sentinel_signers.py` — extend for quorum + `expires_at` + `revoked_signers`.
- `audit_emit.py` — register `sentinel_signer_used` action (kernel touch).
- `.github/workflows/validate.yml` — extend governance gate.
- `docs/incident-runbook.md` — "lost primary signer" runbook branch.

## Cross-references

- ADR-119-sentinel-unlock-contract (PROPOSED, PLAN-086 Wave I)
- ADR-010-canonical-edit-policy
- ADR-040-AMEND-2-credential-blocking (75-day prior art)
- Finding F-A-IDA-T-0004 (acknowledged; closed by PLAN-089)
