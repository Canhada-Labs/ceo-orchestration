# ADR-022: Reserved Slot (ACCEPTED-as-RESERVED)

**Status:** ACCEPTED-as-RESERVED
**Date:** 2026-04-17 (formalized during PLAN-019 Phase 3 VP-F5)
**Deciders:** CEO, VP Engineering
**Replaces purpose:** See ADR-020 (lesson pruning policy v2) which subsumed the original topic this slot was reserved for.

## Context

During Sprint 2 schema reservation, ADR slot 022 was set aside for a planned
"Lesson pruning policy" ADR. By Sprint 7 the topic was merged into
[ADR-017](./ADR-017-lesson-pruning-policy.md) (initial) and later
[ADR-020](./ADR-020-lesson-pruning-policy-v2.md) (v2 replacement). Slot 022
remained empty on disk, creating a governance gap (check-adr-chain.py
flagged it; the audit trail showed "ADR-022" referenced in tests but never
written).

## Decision

Formally close ADR-022 as **ACCEPTED-as-RESERVED** — a first-class status
meaning "this slot was deliberately reserved, its topic resolved elsewhere,
and the reservation record is preserved for historical continuity."
Replacement ADR chain: `ADR-017 → ADR-020` (lesson pruning lifecycle).

## Consequences

**Positive:**
- `check-adr-chain.py` stops warning about the empty slot.
- Historical continuity preserved (anyone grep'ing for ADR-022 finds this
  record pointing at the real decision).
- Establishes ACCEPTED-as-RESERVED as a reusable status for similar slots.

**Neutral:**
- No code change. Documentation-only ADR.

## Revisit condition

If the original topic (a new lesson-related policy) ever warrants a fresh
ADR, create a new slot (ADR-050+) rather than re-using 022. The
"ACCEPTED-as-RESERVED" status is a terminal state for this slot.

## References

- [ADR-017](./ADR-017-lesson-pruning-policy.md) — initial lesson pruning policy
- [ADR-020](./ADR-020-lesson-pruning-policy-v2.md) — v2 replacement
- `.claude/scripts/check-adr-chain.py` §inline-retirement-note rule
- PLAN-018 audit finding VP-F5 (2026-04-17)
- PLAN-019 Phase 3 Wave 3C+D (DYN-W3C-CANONICAL-BATCH)

## Enforcement commit

`4542fdb47745` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
