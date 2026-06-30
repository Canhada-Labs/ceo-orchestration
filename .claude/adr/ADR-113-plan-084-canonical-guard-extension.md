---
id: ADR-113
title: PLAN-084 canonical guard extension — `.claude/plans/PLAN-084/canonical/*`
status: ACCEPTED
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-084 Wave 0.5)
related_plans: [PLAN-084]
related_adrs: [ADR-080, ADR-081, ADR-095, ADR-096, ADR-097, ADR-111, ADR-112]
supersedes: []
authorization: CEO_KERNEL_OVERRIDE=PLAN-084-WAVE-0-CANONICAL-GUARD-EXTENSION + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT
---

# ADR-113 — PLAN-084 canonical guard extension

## Context

PLAN-084 (SOTA-finalization audit) produces 3 canonical artifacts at
Phase E:

1. `.claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl`
2. `.claude/plans/PLAN-084/canonical/PLAN-084-capability-gap-report.md`
3. `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md`

These are the FINAL outputs that define framework's post-SOTA maintenance
posture. They must be tamper-evident at the mechanical floor.

## Decision

Extend `_CANONICAL_GUARDS` in `.claude/hooks/check_canonical_edit.py`
with glob `.claude/plans/PLAN-084/canonical/*`. Edits to canonical/* require:

1. Sentinel approved.md with Scope listing the specific path
2. Detached `.asc` GPG signature per `feedback_sentinel_signing_discipline.md`
3. Single atomic commit signing sentinel + 3 detached `.asc` per AC7

## Consequences

- Phase E.2 canonical artifact emission requires Owner-acordado ceremony
- AC7 mechanical enforcement at hook layer (NOT just policy)
- Post-PLAN-084, the 3 canonical artifacts become byte-stable (any
  mutation requires new sentinel + GPG; observable at git diff time)

## Authorization

KERNEL HARD-DENY extension. `check_canonical_edit.py` itself is in
`_KERNEL_PATHS` per `check_arbitration_kernel.py`. Extension requires:

  CEO_KERNEL_OVERRIDE=PLAN-084-WAVE-0-CANONICAL-GUARD-EXTENSION
  CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT

Override emits `veto_triggered(reason_code=kernel_override_used)` audit
event for forensic trail.

## Related work

- ADR-080 — Pair-Rail dispatcher canonical surface (precedent for
  kernel HARD-DENY extensions)
- ADR-081 — PLAN-082 batch canonical-guard extension precedent
- ADR-111 — locked-corpus governance (similar atomicity discipline)
