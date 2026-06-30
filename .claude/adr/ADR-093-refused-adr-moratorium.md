# ADR-093 — 60-day refused-ADR moratorium + per-plan refusal cap (§moratorium SUPERSEDED-BY-ADR-103; §per-plan-cap PRESERVED)

## Status

SUPERSEDED-BY-ADR-103 (2026-05-03) — original ACCEPTED Wave C ceremony 2026-04-27 — round-3 sentinel — Owner key 0000000000000000000000000000000000000000

> **Supersession scope (2026-05-03):** The §60-day-moratorium clause is
> SUPERSEDED by ADR-103 effective immediately. The §per-plan-refusal-cap
> clause (≤2 refusals before plan flag) is PRESERVED as structural
> anti-sandbagging signal independent of calendar.
>
> **Empirical justification for supersession:** zero refused ADRs
> authored between 2026-04-27 (this ADR ACCEPTED) and 2026-05-03
> (ADR-103 ACCEPTED). Moratorium was fighting a non-recurring pattern.
> See ADR-103 §Empirical evidence cited #4.
>
> **What remains in force from this ADR:**
> - §per-plan-refusal-cap (≤2) — structural, NOT calendar
> - All shipped refusal-class ADRs (083-091) remain valid historical record
> - ADR-091 retraction precedent (Part-3 reversibility) — preserved
>
> **What is dissolved:**
> - 60-day calendar-bound timer (was: 2026-04-27 → 2026-06-26)
> - "Pattern brake" rationale — replaced by per-PR Codex re-pass per ADR-095 §gate-#6 (mechanical, immediate)
>
> See ADR-103 for full rationale + memory feedback `feedback_calendar_gates_invented.md` for the always-on rule.

## Date

2026-04-27

## Enforcement commit

Documentation-only / no enforcement commit (60-day procedural moratorium ADR; enforced via `check_canonical_edit.py` ADR creation guard which is itself unchanged).

## Context

PLAN-044 audit-v2 (2026-04-27) Round 2 raised TWO new P0 findings
about the framework's tendency to over-use refusal as a closure
mechanism:

**R2-NEW-P0 #1:** PLAN-056 Framework Landscape Closeout shipped 3 of
its 5 phases as REFUSED via ADRs 086, 087, 088. PLAN-051 §3.1
established a cap of ≤2/5 refused phases per plan; PLAN-056 exceeded
this cap by one. The cap was not enforced; the closure proceeded
anyway. This is a precedent risk — future plans can refuse arbitrarily
many phases as long as ADRs are written.

**R2-NEW-P0 #2:** Sessions 60-67 introduced 9 refusal-class ADRs
(083-091, with 091 being a deferral) in a 4-day window. The pace of
refusal generation (~2.25/day at peak) signals a "refusal-is-easier-
than-doing-the-work" pattern that the audit-v2 verdict.md flagged as
a closure-honesty failure mode.

The framework needs both:
1. A **moratorium** on new refusal-class ADRs to break the pattern.
2. An **enforced cap** on refusal density per plan.

## Decision drivers

- **Refusals are reversible (ADR-091 retracted in same Wave C).** The
  framework can choose differently. But the tendency to refuse work
  rather than do it must be slowed structurally.
- **CI-enforceable cap > policy doc.** PLAN-051 §3.1's cap was never
  CI-enforced — it relied on Owner discipline. Refusals exceeded
  it (PLAN-056) without trigger. The cap needs `validate-governance.sh`
  enforcement.
- **60 days = 2 sprint cycles.** Long enough to break the pattern,
  short enough to not block legitimate refusals indefinitely. The
  moratorium expires on its own (2026-06-26).
- **Don't break legitimate refusals.** ADRs already shipped (083-091)
  remain valid; the moratorium applies only to NEW refusal ADRs
  authored 2026-04-27 onward.

## Options considered

### Option A — 30-day moratorium, no cap enforcement
Too short to break habit; doesn't address PLAN-056 §3.1 cap precedent.

### Option B — 60-day moratorium + CI-enforced cap of ≤2/5 refused per plan
Path chosen.

### Option C — 90-day moratorium, hard freeze on new ADRs entirely
Too restrictive; legitimate non-refusal ADRs (e.g. design decisions)
should not be blocked.

### Option D — Status quo
Rejected: audit-v2 verdict explicitly named this as a NEW-P0.

## Decision

**Option B.** Two-part rule:

### Part 1 — 60-day refusal moratorium

For 60 days starting 2026-04-27, the framework MUST NOT author new
ADRs whose primary purpose is to refuse work (status: ACCEPTED with
title containing "REFUSED" or "DEFERRED" or "RETIRED").

Moratorium expires: **2026-06-26**.

Authoring a new refusal ADR during the moratorium requires
explicit Owner override (out-of-band; signed sentinel).

### Part 2 — Per-plan refusal cap (≤2/5 refused per plan)

Effective immediately, `validate-governance.sh` will count the number
of phases refused per plan (via grep for `refused` keyword in plan
body or per-phase status fields) and FAIL CI when:

  - Any plan has > 40% of its phases marked refused (≤2/5 per
    PLAN-051 §3.1)
  - Author of an over-cap plan must either reduce refusals OR
    ship a sentinel-signed ADR amending PLAN-051 §3.1

PLAN-056 (which already exceeded the cap with 3/5 refused via ADRs
086/087/088) is grandfathered — the cap applies to plans CREATED
2026-04-27 or later.

### Part 3 — Refused ADR retract demonstrates reversibility

ADR-091 (PLAN-059 Phase 4 dogfood DEFERRED) is retracted in the
same Wave C ceremony — Status flipped from ACCEPTED to PROPOSED
with note documenting that audit-v2 found the deferral insufficient
and PLAN-059 is being re-opened to actively wire the FPR alarm.

This demonstrates that refusals are reversible and the framework
can change its mind.

## Consequences

**Positive (+):**
- Slows the refusal-as-closure pattern via structural cap.
- Forces honest engagement with deferred work (re-open via ADR-092
  rather than refuse via NEW ADR).
- The moratorium's 60-day window is publishable in
  `docs/READINESS-STATUS.md` as a calendar-soak item visible to
  external evaluators.
- CI-enforced cap removes "discipline-only" weakness of PLAN-051 §3.1.

**Negative (-):**
- Legitimate refusals during the moratorium need Owner override —
  small process overhead.
- The 40% cap may be too restrictive for some plans; emergency
  override path documented.

**Neutral (~):**
- Pre-existing 9 refusal ADRs (083-091) remain valid; this ADR does
  not retroactively retract them (except ADR-091 by separate decision).

## Blast radius

L3+. Touches:
- `.claude/scripts/validate-governance.sh` (new cap check)
- New ADR file (this one)
- ADR-091 status flip (separate edit, same ceremony)
- `docs/READINESS-STATUS.md` (new doc — moratorium tracking)

## Compliance checklist

| Item | Verification |
|---|---|
| Moratorium start date | 2026-04-27 |
| Moratorium end date | 2026-06-26 |
| New refused-ADR authored during moratorium | requires Owner sentinel override |
| Per-plan cap enforcement | `validate-governance.sh` (gate added Wave C) |
| Pre-existing refused ADRs grandfathered | ADRs 083-091 remain valid |
| ADR-091 retract demonstration | Status ACCEPTED → PROPOSED in Wave C |
| Tracking | `docs/READINESS-STATUS.md` §Calendar items |

## Related decisions

- ADR-092 — Plan closure honest-deferral framework (Wave C R2)
- ADR-091 — PLAN-059 Phase 4 dogfood validation DEFERRED (retracted in Wave C)
- ADR-084 — Multi-adapter REFUSED (pre-moratorium, grandfathered)
- ADR-085 — Claude-only thesis (pre-moratorium, grandfathered)
- ADR-086 — Phase checkpointing REFUSED (pre-moratorium, grandfathered)
- ADR-087 — OTel-emit REFUSED (pre-moratorium, grandfathered)
- ADR-088 — Guardrails-library REFUSED (pre-moratorium, grandfathered)
- PLAN-051 §3.1 — original ≤2/5 refused cap (now CI-enforced)
- audit-v2 verdict.md — primary motivation for this ADR
