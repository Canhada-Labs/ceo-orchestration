# Wave B.1 — R-032 coverage gate `--fail-under=78 → 85` deferral

## Disposition: DEFER raise 78 → 85 to PLAN-093

**Rationale.**

The line-coverage on `origin/main` as measured at the PLAN-091 base
SHA (`8b5d307`) sits in the ~78-79% band per
`docs/coverage-baseline.md` (Session 33 post-hardening
measurement; comment block in
`.github/workflows/coverage.yml:90-98`). Raising `--fail-under` from
78 → 85 in this v1.22.1 HOTFIX tag would block every subsequent PR
into `main` until a coverage-uplift sprint closes the ~7pp gap.

PLAN-091 is, per its frontmatter `inspiration_origin` block + §3
thesis, a HOTFIX tag — **NO behavior change beyond what v1.22.0
promised**. Raising the enforcing gate is a behavior change with
adopter-facing CI blast radius, and therefore falls outside hotfix
scope per ADR-115 §maintenance-mode anti-churn discipline.

The bump is **deferred to PLAN-093** (Tier-5 R-035 branch coverage
enforcing + R-036 property-based testing comprehensive). PLAN-093
will own the dedicated coverage-uplift sprint that closes:

1. Line coverage uplift to ≥85% (close the ~7pp gap)
2. Branch coverage flip `continue-on-error: false` (R-035)
3. Property-based test corpus (R-036)

The TODO marker in `.github/workflows/coverage.yml:107` already
references PLAN-091 but will be re-targeted to PLAN-093 in the
ceremony commit that lands this deferral document. Pre-existing
comment text is preserved per ADR-115 minimal-churn discipline.

## R1 QA-architect P1 fold corroboration

Per PLAN-091 §14 R1 fold log, QA-architect P1 finding "R-032 branch
coverage gate non-enforcing in PLAN-091 → PLAN-093 closes" is
FOLDED into §4 B.1 — this disposition document is the mechanical
realization of that fold.

Combining line + branch uplift in a single PLAN-093 ceremony also
keeps adopter-facing churn minimal: ONE coverage-uplift ceremony
instead of TWO disjoint bumps in v1.22.1 + v1.23.x.

## Closure roadmap

| Step | Plan | Wave | Notes |
|---|---|---|---|
| 1 | PLAN-093 | uplift-line | Close ~7pp gap so corpus hits ≥85% |
| 2 | PLAN-093 | uplift-branch | Stabilize branch baseline (3-run window) |
| 3 | PLAN-093 | flip-line | Flip `coverage.yml:31/83/98` 78 → 85 |
| 4 | PLAN-093 | flip-branch | Flip `coverage.yml:107` continue-on-error false |
| 5 | PLAN-093 | property-tests | Land hypothesis-driven corpus for hot paths |

## Mechanical verification

PLAN-091 §5 AC4 acceptance is satisfied via this disposition file
**without modifying the enforcing gate** — the acceptance criterion
is explicitly worded "PASSES current main OR explicit deferral with
closure roadmap". This document is that explicit deferral.

CI behavior on `origin/main` post-Wave-B.1 ceremony commit:

- `.github/workflows/coverage.yml` line 31/83/98 `--fail-under=78`
  unchanged (still 78%, still enforcing) — no PR breakage.
- TODO at `.github/workflows/coverage.yml:107` re-targeted from
  "PLAN-091 R-032" → "PLAN-093 R-035".
- This file (`wave-b-coverage-gap.md`) committed under
  `.claude/plans/PLAN-091/` — auditable trace of the deferral
  decision.

## Audit emit (advisory, deferred-to-execution per R1 SE P1 fold)

R1 security-engineer P1 finding "R-032 deferral path needs
`coverage_gate_deferral_recorded` audit emit" is DEFERRED to a
later execution-time pass. Anti-churn (ADR-115) takes precedence
over advisory audit emit for a STATIC deferral document — the
disposition is mechanical (this file is the audit trail). When
PLAN-093 ships, the eventual flip will fire
`coverage_gate_threshold_raised` (new action; registered at that
ceremony).
