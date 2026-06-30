# ADR-091 — PLAN-059 Phase 4 dogfood validation DEFERRED to passive observation (RETRACTED — see audit-v2 R2 NEW-P0)

## Status

RETRACTED — Wave C ceremony 2026-04-27 — round-3 sentinel — Owner key 0000000000000000000000000000000000000000. (History: this ADR was PROPOSED then RETRACTED before reaching ACCEPTED — RETRACTED is the terminal state per the audit-v2 R2 NEW-P0 finding below. PLAN-113 W2 unstacked the prior `PROPOSED (RETRACTED)` marker, which conflated two orthogonal lifecycle states.)

> **Retracted by:** PLAN-044 audit-v2 R2 NEW-P0 finding that "passive observation" was insufficient — Phase 4 dogfood was sandbagged rather than actively monitored. PLAN-059 is being re-opened in Wave C R2 (per ADR-092) with `reopen_trigger: "Phase 4 dogfood automated FPR alarm wiring (CI weekly OR SessionEnd hook)"`. This ADR is kept on disk as a historical record of the original deferral but its decision is no longer in force. Per ADR-093 §Part 3, this retract demonstrates that refusals are reversible.

## Context

PLAN-059 v3 Phase 4 proposed 5-7 dev-dias of dogfood sessions with
per-flip stratified metrics (tokens-count vs cost-cents vs
time-to-converge), spread over 4-6 weeks, with explicit
KEEP/REVERT/TUNE decisions per flip. Acceptance criterion: 5 of 6
KEEP per QA-P0-04 fix (FPR 11%).

Owner directive 27/04 (close all by 2026-05-01) does not accommodate
4-6 weeks of soak observation. ADR-082 (L7c default-on) already
established precedent for soak override under deadline pressure
(Session 67 D1).

## Decision

**DEFER PLAN-059 Phase 4 dogfood validation** with reason
`(b) cost-exceeds-benefit — calendar-time precondition cannot be
compressed`.

Specifically:

1. Phase 4's 5-session dogfood requirement is a calendar-time
   constraint (sessions happen at human pace). It cannot be
   compressed under any deadline.
2. The 6 default flips (per ADR-090) ship with kill-switch env-vars.
   Each flip is independently revertible without code rollback.
3. Passive observation continues post-deadline via existing
   infrastructure:
   - `audit-telemetry.py` aggregates per-archetype dispatch counts
     + p50/p95 latency + fabrication rate from any session window.
   - `ceo-diagnose` reports current defaults observed.
   - Each flip's kill-switch is documented + audit-traced when
     toggled (`audit_log.py` PostToolUse captures env-var-derived
     dispatch modes).
4. If a flip exhibits >5% fabrication rate or other regression
   signal in passive observation, the kill-switch reverts it
   instantly. Reverting via env-var requires zero code rollback.
5. Future review point: when audit-telemetry shows ≥30 days +
   ≥100 spawns per default-flipped feature, the next CEO session
   evaluates KEEP/REVERT/TUNE per flip and writes a follow-up ADR
   amending ADR-090 with empirical disposition.

## Compensating controls (passive observation surface)

| Question | Tool | Frequency |
|---|---|---|
| Are spawns using the new default rail? | `audit-telemetry.py --window 7d` | weekly |
| Is fabrication rate above threshold? | `audit-telemetry.py` (fabrication_rate_pct field) | weekly |
| Are kill-switches being toggled? | `audit-query.py grep --action veto_triggered --reason kernel_override_used` | monthly |
| Is install-mode correctly set? | `ceo-diagnose` (Install mode probe) | per-session |
| Is governance state clean? | `validate-governance.sh` | per-commit (CI) |

## Consequences

### Positive

- PLAN-059 closure unblocked from 4-6 week calendar dependency.
- Kill-switch infrastructure (per ADR-090) preserves rollback path.
- Audit-telemetry + ceo-diagnose stack already gives passive
  observation surface; no new infrastructure needed.
- Acknowledges the empirical reality that dogfood sessions happen
  at human pace and cannot be fast-forwarded.

### Negative

- The "5 of 6 KEEP" gate from PLAN-059 v3 acceptance criteria
  cannot be evaluated by deadline. Replaced with "kill-switch
  available; passive observation; future ADR amends if regression".
- A regression in default-flipped feature will only be caught after
  it has fired in production (vs. caught pre-flip in 5-session
  dogfood). Mitigation: env-var instant rollback.

### Neutral

- This deferral is non-binding on adopter projects. Adopters who
  want to run their own dogfood validation before flipping defaults
  in their installation can do so via existing kill-switches.

## Alternatives considered

### A. Run 5 dogfood sessions in 4 days (REJECTED)

Mathematically infeasible — sessions at human pace; even back-to-back
sessions don't capture cross-day signal needed for token-economy
detectors (which observe weekly patterns).

### B. Skip Phase 4 entirely (REJECTED)

Equivalent to claiming "no validation needed". This ADR is more
honest: validation is needed, but it happens passively post-deadline,
gated by existing kill-switches.

### C. Ship 6 default flips as opt-in only (REJECTED)

Defeats the purpose of PLAN-059 (close the dormancy gap). 14
features are already opt-in and dormant; flipping defaults is the
wedge.

## Future amendment trigger

This ADR is amended when ANY of the following fires:

- Audit-telemetry shows fabrication rate >5% on default-flipped
  feature for ≥7 consecutive days.
- Adopter reports regression attributed to default flip.
- 30 days + ≥100 spawns elapse with no regression signal → upgrade
  flip to ACCEPTED-LOCKED (still kill-switch reversible).

## Enforcement commit

To be filled in at Session 67 D5 closeout.

## References

- PLAN-059 v3 Phase 4 — original dogfood spec (deferred via this ADR)
- ADR-090 — Framework activation defaults (parent: provides
  kill-switches that make passive observation safe)
- ADR-082 — L7c default-on (precedent for soak override)
- ADR-057 — FPR observation window (canonical observation framework)
- `audit-telemetry.py`, `ceo-diagnose.py` — passive observation tools
