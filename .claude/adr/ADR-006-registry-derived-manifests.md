# ADR-006: Derived skill + archetype registry (no side-car YAML)

## Status: ACCEPTED (2026-04-12)

## Context

PLAN-004 Phase 2 consensus finding C3 (VP Eng P3, Backend P3, Growth P3):
the framework has 35 skills and ~16 archetypes, but today their existence
is only discoverable via filesystem walk + prose parsing of team.md.
`check_agent_spawn.py` does substring matching against raw team.md text
— a typo'd archetype passes silently, and name collisions between tiers
are unhandled.

VP Engineering proposal P3 recommended `skill.yaml`/`archetype.yaml`
side-car files. Staff Backend P3 wanted the registry as part of the
Compliance SPEC contract. Growth P3 needed enumeration for squad bundles.

## Decision Drivers

- **Additivity.** Adding side-car YAML files to 35 skills + archetypes
  is a large touch that inflates the commit surface and invites drift
  (side-car vs SKILL.md content diverging).
- **Single source of truth.** The existing `name:`, `description:`,
  `owner:` fields in SKILL.md frontmatter + the archetype tables in
  team.md are already SoT. Duplicating into YAML invites drift.
- **Stdlib-only.** No PyYAML dependency. Minimal frontmatter parser
  (stdlib regex).
- **Stable identifiers.** Frontend skills carry display names in `name:`
  ("Code Quality & TypeScript"); the directory slug
  (`code-quality-and-typescript`) is the stable ID.

## Options Considered

### Option A: Derived registry (chosen)

- A `registry.py` parses existing frontmatter + team.md tables at load
  time into a typed in-memory `Registry(skills={}, archetypes={})`.
- No new YAML files. No bulk edits to 35 skills.
- Directory slug = stable skill ID. Frontmatter `name:` = display label.
- Archetype parsing: regex over table rows (`| **Title** | … | \`skill\` |`).
- Cross-validation: every archetype's `primary_skill` must exist in
  the skills set; validation errors are data (not exceptions).

### Option B: Side-car YAML (original proposal)

- Ship `skill.yaml` for each skill, `archetype.yaml` for each archetype.
- Pros: explicit schema; clean field separation.
- Cons: 35+ file creations; 2 SoTs (frontmatter + YAML) with drift risk;
  PyYAML dependency (violates stdlib-only) OR custom YAML parser (larger).

### Option C: Frontmatter extension (hybrid)

- Extend SKILL.md frontmatter with `id:`, `scope_tags:`, `tier:`, `requires:`.
- Pros: one file per skill.
- Cons: touches 35 files; `tier:` is redundant with filesystem path;
  `id:` is redundant with directory name; `scope_tags` not used by any
  consumer in v1.

## Decision

**Option A.** The registry is computed at load time from existing
sources. If the registry needs new fields in the future (e.g.
`scope_tags`, `requires`), they can be added incrementally with ADR-006
extensions.

### Registry contract

```python
from .claude.scripts.registry import load_registry

reg = load_registry(repo_root=Path("."))
reg.skills          # Dict[str, SkillEntry] — 35 entries
reg.archetypes      # Dict[str, ArchetypeEntry] — 41 entries
reg.errors          # List[str] — cross-validation failures
reg.summary()       # Dict[str, int] — counts by tier
```

### Skill ID rule

`skill_id = skill_md.parent.name` (the directory slug). Frontmatter
`name:` is the display label and may differ. When a skill name collides
across tiers, the second occurrence is prefixed with `<tier>:<name>`.

### Archetype detection rule

```
| **<Title>** | <anything> | `<skill-id>` | ...
```

The first backticked token on the row is the primary skill. Tier is
derived from the source file (team.md = backend, frontend-team.md =
frontend, domains/*/team-personas.md = domain).

### Validation semantics

`registry --validate` exits 1 if any archetype's primary_skill does
not resolve to a known skill (by id OR by display name). This is
advisory for now; hook enforcement (making unknown archetypes block
spawn) is Sprint 5 (paired with manifest extension for scope_tags).

## Consequences

### Positive

- Zero side-car files. Zero touch to 35 skills. Zero PyYAML dep.
- Single SoT preserved. Drift impossible by construction.
- `registry.py --list` is a 200ms operation (no I/O beyond skill file reads).
- Hook Adapter Layer (Phase 4) has a stable archetype list to validate
  against without re-parsing team.md.
- Squad contract (Phase 8) has a registry-backed skill enumeration.

### Negative

- Some metadata we'd like (e.g. `scope_tags`, `requires`) is not
  available without future frontmatter additions. Accepted: Sprint 5
  revisits if real demand appears.
- Frontend skills have display names in `name:` (inconsistent with
  core's slug-in-`name:`). Not fixed here (would touch 8 files for
  cosmetics). Registry resolves via directory slug.

### Neutral

- `check_agent_spawn.py` continues using its current substring match
  today. Sprint 5 (or a Phase 4 follow-up) wires the hook to query
  the registry; swap is additive behind a flag.

## Blast Radius

- `.claude/scripts/registry.py` (NEW, 350 LOC)
- `.claude/scripts/tests/test_registry.py` (NEW, 20 tests)
- `.claude/skills/*/SKILL.md` — **UNCHANGED**
- `.claude/team.md` — **UNCHANGED**

**Reversibility:** HIGH — pure additive file. Rolling back = `rm`.

## References

- PLAN-004 §3 Phase 2
- PLAN-004/debate/round-1/vp-engineering.md §P3
- PLAN-004/debate/round-1/consensus.md §C3
- ADR-005 (event stream v2) — future consumers read registry

## Enforcement commit

`c8d4275b3497` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
