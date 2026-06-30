# ADR-092: Plan closure honest-deferral framework

**Status:** ACCEPTED
**Date:** 2026-04-27
**Enforcement commit:** 7b44042 (Wave C ceremony / v1.11.1 tag SHA)
**Decision drivers:**
  - Audit-v2 (2026-04-27) found Session 67 closed 5/6 plans as `done`
    while substantial work was either workflow-doc-only or partially
    complete — closure-honesty ratio measured at 1/6.
  - The framework's plan FSM lacked a way to express "deferred with
    explicit reopen-trigger", forcing the binary choice `done` vs.
    `abandoned`. Sandbagging filled the gap.
  - PLAN-057 (multi-adapter expansion) was filed under
    `status: abandoned` with an `abandoned_via:` workaround field
    that did not exist in PLAN-SCHEMA — a second symptom of the same
    expressivity gap.

## Context

Session 67 (2026-04-27) closed all 6 open plans in a single mega-
ceremony under Owner directive "close all code/audit/optimization
by 2026-05-01". The closure narrative was published in CLAUDE.md §6
and CHANGELOG `[1.11.0]`. Audit-v2 (run later the same day) found:

| Plan | Status claim | Audit-v2 finding |
|---|---|---|
| PLAN-015 | `done` (42-ledger preflight closed) | Phase 1-4 (actual install in adopter-1) NEVER ran |
| PLAN-052 | `done` (MCP scanner shipped) | 24/50 adversarial fixtures shipped; 26 missing; orphan emit closed in Wave B |
| PLAN-056 | `done` (Framework Landscape Closeout) | 3/5 phases REFUSED via ADRs 086/087/088 — exceeds PLAN-051 §3.1 cap of ≤2/5 refused |
| PLAN-057 | `abandoned` (with non-schema field `abandoned_via: ADR-084`) | Multi-adapter REFUSED per ADR-084 — but `abandoned` is operational not principled |
| PLAN-058 | `done` (post-v1.10.0 audit) | C-P0 cluster (esp. C-P0-01 G4) only partially addressed |
| PLAN-059 | `done` (Activation+Dogfood) | Phase 4 dogfood REFUSED via ADR-091 (sandbagged); 4/6 default flips workflow-doc-only |

The closure honesty ratio (genuinely-done / claimed-done) was
**1/6** (only PLAN-061 honest). The remaining 5 sandbagged the
audit because there was no schema-supported way to say "we shipped
much, but Phase X is genuinely deferred until external signal Y."

## Decision drivers

- **Honesty over completeness.** A `done` plan that hides deferred
  work corrupts the framework's own audit trail (the framework
  audit-v2 found this corruption recursive — the closure-honesty
  problem was the primary blocker to a TRIAL verdict).
- **Distinguish principled refusal from operational abandonment.**
  ADR-084 refusing multi-adapter is principled (Claude-only thesis).
  Forcing it into `abandoned` (operational premise-was-wrong) drops
  load-bearing context for future maintainers.
- **External signals are real triggers.** "Re-open after first adopter-1
  adopter signal" is a concrete reopen condition; the framework should
  represent it directly.
- **Avoid status-name proliferation.** Adding two new statuses
  (`refused` + `deferred`) is clearer than overloading `abandoned` or
  inventing parallel `caveat:` fields.

## Options considered

### Option A — Two new statuses: `refused` (terminal) + `deferred` (re-openable)
Cleanest semantically but doubles new-status surface area + schema
complexity.

### Option B — One new status (`refused`) + re-open transition (`done → executing`)
Single new status. Re-open expressed as `done → executing` transition
gated on `reopen_via:` ADR reference + `reopen_trigger:` field. Path
chosen.

### Option C — Add `closure_caveat:` field to `done` status only
Preserves single-status `done` but creates a "soft-done" / "hard-done"
distinction that doesn't surface in the FSM. Audit-v2 found this is
exactly the sandbagging pattern Session 67 already fell into.

### Option D — Status quo (sandbagging in `done`)
Rejected by audit-v2 verdict.

## Decision

**Option B.**

1. **Add `refused` status** to `_LEGAL_STATUSES`. Terminal. Requires
   `refused_adr: ADR-NNN` + `refused_at: <date>` frontmatter fields.
   Used for principled refusal documented in an ADR (e.g. PLAN-057
   refused via ADR-084).
2. **Add `done → executing` re-open transition** to
   `_ALLOWED_TRANSITIONS`. Gated by hook validator: post-edit content
   must contain `reopen_via: ADR-092` AND `reopen_trigger:` fields.
3. **Migrate PLAN-057** from `abandoned + abandoned_via: ADR-084` to
   `refused + refused_adr: ADR-084 + refused_at: 2026-04-27`.
4. **Re-open 5 sandbagged plans** (PLAN-015/052/056/058/059) from
   `done` to `executing` with `reopen_via: ADR-092` + plan-specific
   `reopen_trigger:` field documenting the external signal.
5. **Close-criteria document.** Each re-opened plan adds a
   `## Reopen criteria` body section listing the EXACT signals that
   move it back to `done` (so future closures are auditable).

## Per-plan re-open assignments

| Plan | Reopen trigger | Estimated re-close |
|---|---|---|
| PLAN-015 | "First external adopter-1 signal — install + 1 hour dogfood with audit-log evidence" | TBD external |
| PLAN-052 | "26 additional MCP adversarial fixtures shipped + Phase 6 soak harness empirical run (50 total)" | ~150k tokens follow-up |
| PLAN-056 | "Phase 2 SDK compat empirical validation against current Claude Agent SDK + AutoGen v0.7" | ~120k tokens follow-up |
| PLAN-058 | "Remaining C-P0 cluster (audit consensus.md residuals: C-P0-01 G4 verified post-merge of Wave B + C-P0-04 Phase 6 integration test)" | ~80k tokens follow-up |
| PLAN-059 | "Phase 4 dogfood automated FPR alarm wiring (CI weekly OR SessionEnd) — make ADR-091's 'passive observation' active" | ~140k tokens follow-up |

## Consequences

**Positive (+):**
- Framework's own audit-trail becomes honest. Closure-honesty
  ratio measurable + improvable.
- Future Session 67-style mega-closures cannot hide deferred work
  without leaving an FSM trace.
- PLAN-057's `abandoned_via:` workaround retired in favor of a
  schema-supported field.
- `refused` status enables future principled refusals (e.g.
  PLAN-XX-multi-cloud) without forcing them into `abandoned`.

**Negative (-):**
- Adopter migration: legacy `abandoned + abandoned_via:` plans need
  migration if the workaround was used. PLAN-057 is the only known
  instance (migrated in Wave C).
- New transition `done → executing` adds FSM complexity. Mitigation:
  hook validator enforces ADR + trigger preconditions; transitions
  are auditable.
- The 5 re-opened plans go from CHANGELOG-clean `done` to
  CHANGELOG-noisy `executing`. The audit-trail honesty gain
  outweighs the cosmetic noise.

**Neutral (~):**
- PLAN-051 §3.1 cap of ≤2/5 refused per plan — separate decision in
  ADR-093 (60-day refused-ADR moratorium). This ADR (092) does not
  change the cap.

## Blast radius

L3+. Touches:
- `.claude/hooks/check_plan_edit.py` (FSM definition)
- `.claude/plans/PLAN-SCHEMA.md` (documentation)
- 6 plan files (PLAN-015, 052, 056, 057, 058, 059) — frontmatter
- New body section `## Reopen criteria` in each re-opened plan
- `.claude/scripts/validate-governance.sh` no changes (refused
  status already counted as terminal)

## Dependencies + interactions

- ADR-093 (Wave C R3) — establishes 60-day refused-ADR moratorium;
  governs how often `refused` status can be used per period.
- audit-v2 verdict.md — primary motivation document.
- audit-v2 triage.md C1 cluster — closure dishonesty findings.

## Reopen + close discipline

Per audit-v2: a future plan re-flipping from `done` to `executing`
under this ADR's framework MUST cite this ADR (`reopen_via: ADR-092`)
and a concrete trigger. CEO is responsible for the trigger language
being SPECIFIC enough that reasonable maintainers can later determine
"has the trigger fired yet?" Vague triggers (e.g. "when ready")
should be rejected by the validator (future enhancement; current
Wave C check verifies presence of the field, not specificity).

## Naming honesty

`reopen_trigger:` is preferred over `reopen_when:` or
`reopen_condition:` because "trigger" is operationally specific —
something has to FIRE for the plan to re-open. Conditions can be
ambient ("when CI is green"); triggers are observable events.
