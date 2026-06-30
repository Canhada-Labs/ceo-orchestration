---
id: ADR-112
title: Grandfather-cap scope clarification — individual_skills cap vs domain_bundles cap
status: ACCEPTED
proposed: 2026-05-09
decided: 2026-05-09
deciders: [CEO]
related_plans: [PLAN-080]
related_adrs: [ADR-009, ADR-052, ADR-093, ADR-103, ADR-111]
supersedes: []
superseded_by: []
tags: [governance, grandfather, cap-policy, sunset]
---

# ADR-112 — Grandfather-cap scope clarification

## §1. Status

ACCEPTED — `decided: 2026-05-09` via PLAN-080 Phase 4 Owner GPG sentinel
ceremony. The signed commit landing this ADR alongside the closeout
canonical-path changes IS the acceptance moment per ADR convention.

## §2. Context

PLAN-080 R1 debate (2026-05-09 S98) opened with a **CRITICAL** finding
R-CR-1: "Framework violates ≤10 cap declared in
`.claude/skill-governance-grandfather.yaml`." That premise was empirically
refuted by Sec R2 verification: the YAML cap governs the **5 individual
routable skills** (`pre-plan-brainstorm`, `terse-mode`,
`advanced-evaluation`, `agent-evaluation`, `agentic-actions-auditor`),
NOT the 25-entry `SQUAD_GRANDFATHER` bash array in
`.claude/scripts/validate-governance.sh:284`. The two artifacts were
mechanically unrelated — different schemas, different consumers, different
intent — but informally conflated in framing.

This ADR clarifies the policy explicitly so future debate iterations cannot
re-conflate them.

## §3. Decision

**Two distinct caps** govern grandfathered governance escape valves:

### A) `individual_skills.cap` (legacy individual skills)
- Defined in `.claude/policies/grandfather-cap.policy.yaml` (PLAN-080 Phase 1b)
- Predecessor: `.claude/skill-governance-grandfather.yaml` (DEPRECATED)
- Current value: **5** individual skills (no slack; full)
- Member roster:
  - `pre-plan-brainstorm`
  - `terse-mode`
  - `advanced-evaluation`
  - `agent-evaluation`
  - `agentic-actions-auditor`
- Each entry is a routable skill that exists outside the
  `core/` / `frontend/` / `domains/<d>/skills/` tier discipline.
- New individual-skill grandfathers require an ADR + cap bump.

### B) `domain_bundles.cap` (squad bundle escape valve)
- Defined in `.claude/policies/grandfather-cap.policy.yaml`
- Members: domain names listed in `validate-governance.sh:284`
  `SQUAD_GRANDFATHER` bash array.
- Phase 4 declared cap value (PLAN-080 §6 Q4 default): **15**
  - Alternatives considered: (a) no cap, (c) ≤25; (b) ≤15 selected
    as default to preserve room for 2-3 future grandfathers while
    encouraging Phase 4 sunset trim.
- Current count post-PLAN-074 W4-W10: 25 (over cap; trim plan via Phase 4
  sunset of ~10 zero-traffic domains tracked in `audit-query.py by-domain`).
- Each entry is a domain that ships under ADR-009 squad-bundle 5-artifact
  contract eventually, but currently has partial bundle (or only seed
  SKILL.md + skills/ directory).

### C) Sunset / reopen mechanism
Defined in `grandfather-cap.policy.yaml`:

```yaml
sunset_reopen_window_days: 14
sunset_reopen_requires_hint_match: true
sunset_reopen_unknown_excluded: true  # M2-CDX-7
```

A sunset domain auto-reopens for review when:
- ≥1 spawn within 14 days, AND
- The spawn carries `dispatch_archetype_hint` matching the sunset
  domain's archetype slug

UNKNOWN/`general-purpose` fallback hints **do NOT trigger reopen** — they
are Owner-review evidence only. This prevents adversarial reactivation via
untagged spawns AND honest-but-untagged spawns from falsely triggering
reopen.

## §4. Consequences

**Positive:**

- Eliminates the conceptual conflation that produced R-CR-1 (CRITICAL)
  in PLAN-080 R1 debate.
- Provides a discrete, queryable cap for each escape valve.
- Codifies the sunset reopen criteria as policy data (not as code), enabling
  Owner to update reopen behavior without ceremony for code changes.
- Makes future audits mechanically simple: `grep cap: policy.yaml | wc -l`.

**Negative:**

- One new ADR + one new policy file + one mechanical pre-commit cap test
  to maintain.
- Adopters need to update tooling that referenced the OLD
  `.claude/skill-governance-grandfather.yaml` path (the DEPRECATED stub
  preserves the old key for one transitional release).

**Mechanical:**

- `.claude/scripts/tests/test_squad_grandfather_cap.py` (PLAN-080 Phase 1b)
  asserts `len(SQUAD_GRANDFATHER) ≤ domain_bundles.cap` from policy file.
  CI fails on cap exceedance.
- `audit-query.py by-domain --check-reopen` consumes the sunset_*
  policy fields.

## §5. Alternatives considered

- **(a) Keep one combined cap** — rejected: premise that triggered R-CR-1
  CRITICAL. Conflates two different governance concerns. Sec + QA + CR
  all flagged the conflation in R1 debate.
- **(b) Move both into a single new policy file with explicit subkeys**
  [SELECTED] — simpler operational model than separate files; mechanical
  cap test trivial.
- **(c) Make domain_bundles.cap = 25 (codify status quo)** — rejected per
  PLAN-080 §6 Q4 default reasoning: ≤15 default preserves room for 2-3
  future grandfathers; codifying 25 removes pressure to sunset zero-traffic
  domains.
- **(d) Per-domain caps (e.g., max 3 PII-required, max 5 commercial)** —
  rejected: too many policy knobs; complexity outweighs marginal
  governance benefit.

## §6. Acceptance criteria (per PLAN-080 §4 Phase 4)

- [x] `.claude/policies/grandfather-cap.policy.yaml` declares both
  `individual_skills.cap` AND `domain_bundles.cap` (PLAN-080 Phase 1b
  shipped this file)
- [x] `.claude/scripts/tests/test_squad_grandfather_cap.py` enforces
  domain_bundles.cap mechanically (Phase 1b)
- [x] `.claude/scripts/audit-query.py by-domain --check-reopen` consumes
  `sunset_reopen_*` fields (Phase 1)
- [x] `.claude/skill-governance-grandfather.yaml` preserved as DEPRECATED
  stub for one transitional release
- [ ] CLAUDE.md §6 closeout entry referencing this ADR (Phase 4
  closeout)
- [ ] PLAN-080 status `executing → done` with Phase 4 ship recorded

## §7. Rollback plan

If the two-cap model proves operationally awkward:

1. Revert `.claude/policies/grandfather-cap.policy.yaml` to a single-cap
   schema preserving member rosters but flattening structure.
2. Revert `audit-query.py by-domain --check-reopen` to use a hardcoded
   sunset list (loses configurability).
3. Mark this ADR `RETRACTED` with retracted_at + retracted_by_reason.
4. Recovery time: ~30 min Owner-physical + 1 GPG ceremony.

The DEPRECATED stub at `skill-governance-grandfather.yaml` already
preserves backward-compat for one release; rollback would extend that
window.

## §8. References

- PLAN-080 §1.1 (cap clarification — R-CR-1 closure)
- PLAN-080 §2 (goal item 7)
- PLAN-080 §3 (drop-policy thresholds)
- PLAN-080 §4 Phase 1b (mechanical cap test + policy migration)
- PLAN-080 §4 Phase 4 (sunset + this ADR)
- PLAN-080 §6 Q4 (default ≤15 with decision tree)
- PLAN-080 §8 (reopen criteria with M2-CDX-7 exclusion)
- ADR-009 (squad-bundle 5-artifact contract)
- ADR-052 (VETO floor)
- ADR-093 (canonical-guard moratorium retract)
- ADR-103 (ADR-103 calendar-gate purge — mechanical gates only)
- ADR-111 (PII core promotion — sibling Phase 0a ADR)
- `.claude/skill-governance-grandfather.yaml` (DEPRECATED predecessor)
- `.claude/policies/grandfather-cap.policy.yaml` (NEW canonical-guarded)
- `.claude/scripts/validate-governance.sh:284` (`SQUAD_GRANDFATHER` array)
- `.claude/scripts/audit-query.py by-domain` (consumer)
- `.claude/scripts/tests/test_squad_grandfather_cap.py` (mechanical CI gate)

## §9. Forensic trail

- Drafted: 2026-05-10 S100 Phase 4 (PLAN-080 v2.5)
- R1 driver: R-CR-1 CRITICAL (3/3 REJECT) — refuted by Sec R2 empirical
  verification → reframed via this ADR
- R2 closure: M2-C13 (CR off-by-one closed without plan edit; codified here)
- Codex MCP iter forensic trail: PLAN-080 v2.5 review iters 1-5 (ACCEPT
  iter 5)
- Phase 4 closeout: PLAN-080 status `executing → done` ceremony
- Owner GPG sentinel: pending Phase 4 ceremony
