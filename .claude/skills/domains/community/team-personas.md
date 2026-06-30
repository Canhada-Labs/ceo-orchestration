# Community Domain — Personas Roster (STUB)

> **Target location (Owner promote via sentinel):**
> `.claude/skills/domains/community/team-personas.md`
>
> **Staged reason:** the target path is canonical-guarded under
> ADR-010 / ADR-031. Promote via
> `.claude/plans/PLAN-033/OWNER-CLOSEOUT-ACTIONS.md` Step X.

## Purpose

When a curated community skill is loaded into a spawn prompt, the CEO
needs a named persona to attach it to. This file lists the personas
who own community-domain skills. Until the first import lands, only
placeholder archetypes exist.

## Archetype placeholders

| Archetype | Focus | Primary skill(s) |
|-----------|-------|-----------------|
| **Community Researcher** | Surveys external curated corpora; triages for Owner review | (none yet — this is the meta-role) |
| **Community Skill Steward** | Owns lifecycle of imported skills; signs SP-NNN rotations | (varies per imported skill) |

## Active imports

_None yet. This table is populated by `.claude/scripts/import-skill.py`-
generated NOTICE.md rows + Owner's per-skill review._

Format of future entries:

| Slug | Upstream | License | SP-NNN | Persona |
|------|----------|---------|--------|---------|
| *placeholder* | *org/repo@vX* | *SPDX* | *SP-NNN* | *Named* |

## Cross-references

- `.claude/skills/domains/community/NOTICE.md` — attribution ledger.
- `.claude/team.md` — root routing table (Community entries will be
  added here post-import via SP-NNN chain, since `team.md` is
  canonical-guarded under ADR-031).
- `.claude/plans/PLAN-033/OWNER-CLOSEOUT-ACTIONS.md` — import procedure.
