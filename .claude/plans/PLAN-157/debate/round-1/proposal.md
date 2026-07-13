---
plan: PLAN-157
round: 1
created_at: 2026-07-13
---

# PLAN-157 round-1 proposal — Architect Graduation (cap 32→24)

Full plan: `.claude/plans/PLAN-157-architect-graduation.md`

## Thesis

PLAN-153 Wave D imported 15 ecc skills as **8 new domain scaffolds**
(agents-meta, architecture, cpp, data-ml, desktop, dotnet, golang, jvm)
under a grandfather-roster raise 24→32
(`.claude/policies/grandfather-cap.policy.yaml:40-46`, "no headroom by
design"; gate at `validate-governance.sh:284` + policy-matching test
`test_squad_grandfather_cap.py:207`). The deferred obligation
(PLAN-153:425) is to drain those 8 back out, returning `current` to 24.
A squad exits the roster by exactly one of two paths:

- **Graduate** — author the full ADR-009 bundle (≥5 personas + ≥3 skills
  + ≥10 pitfalls + ≥2 task-chains + ≥1 example) via `/architect`, then
  remove from `SQUAD_GRANDFATHER` + policy `members`.
- **Sunset** — retire the scaffold (relocate/archive its skills), then
  remove from both lists.

## Evidence constraint (the headline decision input)

The Owner's original criterion was "telemetry decides". S270 telemetry
dossier (skill-health over 407,932 events, full rotated window): **all 15
imported skills have zero invocations — but so do 155 of 164 catalog
skills**. The instrument is structurally blind to greenfield domain
skills (they earn use in *target repos*, not this meta-repo;
`.claude/commands/skill-health.md:62-69` documents the blindness).
Uniform zero cannot rank the squads. The plan therefore substitutes
**reach/consumer-plausibility** (the same axis PLAN-153:322-323 used to
admit them) with telemetry as a floor observation, and flags the
substitution for Owner ratification (OQ1).

## Proposed disposition (debate this table)

| Squad | Skills | Reach | Disposition |
|---|---|---|---|
| jvm | 2 | High | Graduate (+1 skill to reach ≥3) |
| cpp | 2 | High | Graduate (+1 skill) |
| golang | 1 | High | Graduate (+2 skills) |
| data-ml | 2 | High, heterogeneous pair | Graduate (+1 skill) |
| architecture | 2 | Medium, overlaps core | Fold into core + sunset scaffold |
| agents-meta | 2 | Medium, overlaps core | Fold into core + sunset scaffold |
| dotnet | 1 | Medium, thin | Sunset (relocate or archive csharp-testing) |
| desktop | 1 | Low niche | Sunset |

Alternatives considered: sunset-all-8 (cheapest, discards PLAN-153's
adopt/adapt reasoning); graduate-all-8 (~2x authoring budget, spends it
on low-reach squads).

## Wave structure

- W0 ratification + baseline snapshot
- W1 sunsets + folds (desktop, dotnet, architecture, agents-meta) → current: 28
- W2 graduate jvm + cpp → 26
- W3 graduate golang + data-ml → 24; closeout reconciles counts

Cost honesty: each graduation is real authoring (bundle via `/architect`,
CEO curates; new SKILL.md content rides the SP-NNN pipeline where
required). Budget: 300-450k tokens, ~3 sessions, context_risk high.

## Open questions for this round

- OQ1: ratify the criterion substitution (telemetry → reach), or direct
  sunset-all-8?
- OQ2: relocation target for sunset skills (adjacent domain / core /
  archive)? CEO default: archive.
- OQ3: after reaching 24, lower `cap:` literal 32→24? CEO default: yes.

## What the critics should pressure-test

1. Is the 4/2/2 split defensible with zero usage signal, or is it
   sunk-cost bias toward the PLAN-153 import decision?
2. Does folding architecture/agents-meta into core risk diluting core
   skill quality or creating dedup debt?
3. Is the counts/CI blast radius of W1 (catalog shrink, claims gates,
   skill-inventory regen) fully enumerated?
4. Sequencing: sunsets before graduations — right order?
5. Anything canonical-guarded in the touch set that the plan missed
   (SKILL.md files are guarded; policy YAML + validate-governance.sh —
   check the guard list)?
