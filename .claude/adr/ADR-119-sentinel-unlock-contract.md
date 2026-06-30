# ADR-119 — Sentinel-Unlock Contract Tightening

**Status:** ACCEPTED

**Enforcement commit:** `d5099b15` (PLAN-086 closeout v1.20.0 — sentinel-unlock enforcement in check_canonical_edit.py Wave I)
**Date:** 2026-05-12
**Plan:** PLAN-086 Wave I
**Supersedes:** none
**Amends:** ADR-010 (canonical-edit policy — augmentation only)
**Depends-on:** ADR-010, ADR-040-AMEND-2 (credential blocking parallel)
**Veto-floor:** D (governance bypass) + B (auth/crypto)

## Context

`CEO_SENTINEL_UNLOCK` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` env-override
mechanism (ADR-010 amendment, PLAN-045 Wave 1 P0-01) provides dual-auth
bypass of the detached GPG signature check on Owner-signed sentinels.
The mechanism preserves the sentinel scope + plaintext Approved-By
gates but removes the .asc verification — useful during ceremony
authoring where the .asc is being signed in parallel.

PLAN-084 audit identified two weaknesses in the current contract:

1. **Unlock-reason regex too permissive** (F-C2-005). At v1.19.0 the
   regex `^[A-Za-z0-9._-]{1,120}$` accepts arbitrary slugs including
   names that bear no semantic relationship to ADR/PLAN identifiers.
   A sub-agent with env-injection capability (e.g. via prompt
   compromise) could set `CEO_SENTINEL_UNLOCK=arbitrary-junk` and pass
   the dual-auth gate even though the slug is not traceable to an
   accepted governance artifact.

2. **No scope-glob enforcement against edit target**. The current
   contract grants unlock based solely on (a) reason regex match,
   (b) ACK token, (c) sentinel Scope: block containing the target
   path. The reason slug does NOT cross-reference the edit target;
   a stale-reason unlock can grant edits to unrelated canonical paths
   if the sentinel's Scope: block happens to cover them.

PLAN-086 Wave I closes both gaps via this ADR.

## Decision

Tighten `CEO_SENTINEL_UNLOCK` contract per the following invariants:

### Invariant 1 — Reason regex tightening

The unlock reason regex changes from
```
^[A-Za-z0-9._-]{1,120}$
```
to
```
^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$
```

Valid examples:
- `ADR-119-sentinel-unlock-contract`
- `PLAN-086-wave-i-rollout`
- `PLAN-086-kernel-extension`

Invalid examples (reject with dual-auth failure):
- `something-arbitrary` (no ADR/PLAN prefix)
- `PLAN-86-foo` (zero-padding required, 3 digits)
- `ADR-001` (no descriptor suffix)

### Invariant 2 — SCOPE-glob match against edit target

New env var `CEO_SENTINEL_UNLOCK_SCOPE` REQUIRED in addition to
`CEO_SENTINEL_UNLOCK` + `CEO_SENTINEL_UNLOCK_ACK`. The SCOPE glob MUST
fnmatch-match the actual edit-target path. Mismatch → DENY (dual-auth
contract violated).

Example:
```bash
CEO_SENTINEL_UNLOCK=PLAN-086-wave-i-rollout
CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT
CEO_SENTINEL_UNLOCK_SCOPE=.claude/hooks/check_canonical_edit.py
```

Bare regex pass WITHOUT SCOPE-glob match denies (per test
`TestUnlockReasonMatchesEditTarget`).

### Invariant 3 — Per-session budget cap

`sentinel_unlock_used` audit-emit budget cap = **10 per session**.
11th attempt blocks. Mirrors `CEO_BUDGET_BYPASS` discipline per H13.

### Invariant 4 — GPG verify still enforced for signature path

The env-override only relaxes the **signer-allowlist** gate (the
`.claude/sentinel-signers.txt` fingerprint check). It does NOT skip
GPG verify entirely — if a `.asc` file is present, it is verified
against allowlist with the SAME timeout + strict-args discipline. The
override path is "missing-.asc-allowed" not "any-junk-.asc-accepted".

## Consequences

- ADR-119 is STANDALONE — does NOT amend ADR-010 bytes. The runtime
  enforcement ships in `check_canonical_edit.py` per Wave I implementation.
- `check_canonical_edit.py` is in `_KERNEL_PATHS` HARD-DENY; the edit
  requires Owner kernel ceremony.
- Sentinel `.claude/sentinel-signers.txt` gets added to `_KERNEL_PATHS`
  in this same wave (currently NOT kernel — F-C2-007 gap).
- Tests:
  - `test_sentinel_unlock_contract.py` (5 cases for I.1-I.4)
  - `test_sentinel_signers_kernel_protection.py` (verify sentinel-signers
    edit blocked without kernel-override)

## Rollout

1. **Phase 1 (this ADR)**: PROPOSED. PLAN-086 Wave I implementation
   prepared as staging. Tests pre-flight green.
2. **Phase 2 (Wave I ceremony)**: Owner runs kernel ceremony with
   `CEO_KERNEL_OVERRIDE=PLAN-086-wave-i-rollout` +
   `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` + `CEO_SENTINEL_UNLOCK_SCOPE=*`.
   Apply check_canonical_edit.py + check_arbitration_kernel.py edits.
3. **Phase 3 (closeout)**: ADR flips PROPOSED → ACCEPTED. Verify
   `test_sentinel_unlock_contract.py` green. Tag v1.20.0.

## Cross-references

- ADR-010 (canonical-edit policy)
- ADR-040-AMEND-2 (credential blocking — parallel pattern)
- PLAN-086 Wave I (this ADR's runtime owner)
- F-C2-005 (CEO_SENTINEL_UNLOCK contract weakness)
- F-C2-007 (sentinel-signers.txt SPOF)

---

**Note**: this ADR is PROPOSED at PLAN-086 Wave I dispatch and flips
to ACCEPTED on Wave I closeout per AC14. The kernel-edits are gated
on Owner ceremony — this ADR file is non-kernel and lands first
(documentation-only).
