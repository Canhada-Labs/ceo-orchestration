# ADR-019-AMEND-2-CLASS-SHA_EXISTS: Promote `sha_exists` claim class to HIGH_CONFIDENCE_BLOCK

**Status:** ACCEPTED
**Accepted:** 2026-05-18
**Date:** 2026-05-18
**Plan:** PLAN-100 v1.34.0
**Amends:** ADR-019-AMEND-1 §4 (initial v1.34.0 tier assignment) + §7 (per-class promotion ceremony)
**Related:** ADR-019, ADR-018, ADR-095, ADR-124, ADR-125

## Context

ADR-019-AMEND-1 §7 specifies the per-class promotion ceremony pattern.
This ADR is the FIRST application — it documents the decision to promote
`sha_exists` to HIGH_CONFIDENCE_BLOCK (already in v1.34.0 tier-config JSON)
under ACCEPTED status and establishes the canonical template for future
per-class promotions (e.g. a subsequent ADR-019-AMEND-N-CLASS-PATH_EXISTS).

## Decision

Promote claim class `sha_exists` to HIGH_CONFIDENCE_BLOCK in
`.claude/data/confidence-gate-class-tiers.json`. (Already shipped in
v1.34.0; this ADR is the doctrine-level ACCEPTED record.)

### Evidence

| Criterion | Threshold | Measured (PLAN-090 Wave A.10 baseline 2026-05-18) |
|---|---|---|
| Sample size N | >= 200 | 200 |
| Severity | critical | critical (forensic gap if wrong) |
| Verifier determinism | deterministic | `git cat-file -e <sha>` — pure git lookup, no env dependency |
| Empirical FPR on well-formed corpus | < 1% | 0% (5% intentional fakes only — true positives, not FPs) |
| ADR-095 data-volume gate | satisfied | Substantive criterion replaces calendar wait per ADR-095 |

### Drift detector

`.claude/scripts/check-confidence-gate-drift.py` scans 7-day rolling FPR
for `sha_exists`. If FPR > 2% threshold → emits
`confidence_gate_fp_drift_detected` audit event with an `auto_demote_at`
timestamp (24h cooling per ADR-019-AMEND-1 §6). The tier-config JSON
demotion is performed by a downstream operator/runner when the detector
is wired to ceo-boot Tier-S (future micro-plan); v1.34.0 keeps the
detector advisory + manual-invocation only.

### Reversal

Byte-identical reversal: remove `"sha_exists": "HIGH_CONFIDENCE_BLOCK"` from
`.claude/data/confidence-gate-class-tiers.json` (or change to
`MED_CONFIDENCE_ADVISORY`). Drift-detector emit + Owner GPG sentinel at
`.claude/data/confidence-gate-drift-override-sha_exists.asc` for override.

## Consequences

`sha_exists` claim failures now block spawn under `CEO_CONFIDENCE_ENFORCE=1`.
Per-class kill-switch `CEO_CONFIDENCE_BLOCK_SHA_EXISTS=0` for emergency
unblock. Pattern established: future per-class promotions follow this
template (a subsequent ADR-019-AMEND-N-CLASS-<CLASS>.md + tier-config JSON edit + Owner
GPG sentinel).

## Authority

- ADR-019-AMEND-1 §4 (initial tier assignment v1.34.0)
- ADR-019-AMEND-1 §7 (per-class promotion ceremony pattern)
- ADR-095 (calendar-gate retraction — data-volume substantive criterion)
- ADR-124 §Part 2 (amendments to existing ADRs)
- ADR-125 §B (conditional default-ON Tier-B)
- PLAN-090 Wave A.10 baseline report (`.claude/plans/PLAN-090/wave-a10-confidence-baseline.md`)
- PLAN-100 v1.34.0 ship — commit `71e99e54a33da7c61393facd00c160d657662681` + tag `v1.34.0` (2026-05-18)
