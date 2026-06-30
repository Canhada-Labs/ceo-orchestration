---
id: SP-018
kind: skill-patch
proposal_target: .claude/skills/core/ceo-orchestration/SKILL.md
proposal_type: regen-auto-block
proposed_at: 2026-04-21T00:00:00Z
status: promoted
promoted_at: 2026-04-22T11:34:21Z
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-22T11:34:21Z
signer: 0000000000000000000000000000000000000000
---

# SP-018 — ceo-orchestration SKILL.md auto-inventory regen

## Motivation

PLAN-045 F-15-05 (partial) + long-standing drift — the auto-generated
skill inventory block in `.claude/skills/core/ceo-orchestration/SKILL.md`
is stale relative to actual filesystem state:

- Missing entry for `pre-plan-brainstorm` (added Session 37 via
  PLAN-031; ADR-058)
- Count should be 20 core (not 19)
- `community` domain entries (3 skills added PLAN-033)

This proposal regenerates the auto-block (BEGIN/END markers) via
`bash .claude/scripts/generate-skill-inventory.sh > /tmp/inv.md` and
replaces the content between `<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->`
and `<!-- END AUTO-GENERATED SKILL INVENTORY -->` with the regen output.

## Target file content

**Replace block** between the two AUTO-GENERATED markers in
`.claude/skills/core/ceo-orchestration/SKILL.md` with the output of:

```bash
bash .claude/scripts/generate-skill-inventory.sh
```

**No other changes to the file.** The CEO narrative prose (Identity,
How I operate, etc.) remains verbatim.

## Rationale for no content diff inline

The inventory block is mechanically generated from frontmatter of each
skill file. Including the exact 150-line output inline would create
churn any time a new skill is added. The promote script reads the
auto-gen output at apply time.

## No behavior change

Inventory is a CEO mental-map; not consumed by any hook or script.
Stale content does not affect governance.

## Pre-authorized

Owner D7 of `.claude/plans/WAR-ROOM/01-OWNER-AUTHORIZATIONS.md`.

## Ship criteria

- Promote writes new inventory block
- Diff shows only AUTO-GENERATED block changed
- validate-governance ≤ 10 warnings / 0 errors
