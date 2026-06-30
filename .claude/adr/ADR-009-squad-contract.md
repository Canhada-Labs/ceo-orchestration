# ADR-009: Squad bundle contract

## Status: ACCEPTED (2026-04-12)

## Context

PLAN-004 Phase 8 consensus finding C3 + Growth P3: the framework ships
one domain (fintech) today. Adding a second (lgpd-heavy-saas) requires
a repeatable contract so future squads compose cleanly with the
Compliance SPEC v1 and the manifest registry.

Growth specialist argued for 2-3 more squads in 12 weeks (lgpd,
trading-hft, payment-platforms). VP Engineering argued for an explicit
squad.yaml manifest (P4). The squads need to be installable/removable
atomically and must not leak across tier boundaries.

## Decision Drivers

- **Repeatable contract.** Every squad has the same 5-artifact shape so
  adopters know what to expect and validators know what to check.
- **Tier isolation.** Squads live under `.claude/skills/domains/<name>/`
  and MUST NOT reference core/frontend skills as dependencies (only
  core/frontend may be listed as foundational prerequisites in prose).
- **Registry-friendly.** Squad skills are discoverable via
  `registry.py` (Phase 2) like any other skill.
- **Install-CLI stability.** `install.sh --profile core,<squad>`
  continues to work as the single integration point.

## Options Considered

### Option A: 5-artifact minimum + free-form extras (chosen)

Every squad ships exactly:

1. `team-personas.md` — ≥ 5 personas (fictional composites per ADR-007 RC policy + Growth §personas red line)
2. `skills/<skill-id>/SKILL.md` — ≥ 3 domain-specific skills with proper frontmatter (per skill-frontmatter.schema)
3. `pitfalls.yaml` — ≥ 10 pitfalls in the catalog format
4. `task-chains.yaml` — ≥ 2 domain workflows
5. `examples/PLAN-EXAMPLE.md` — one complete example plan showing the squad in use

Optional: `commands/`, `scripts/`, `frontend-team-personas.md`.

- **Pros:** minimal, discoverable, matches existing fintech shape,
  validates cleanly against `check-tier-boundaries.py` and
  `registry.py`.
- **Cons:** 5 artifacts is arbitrary minimum; a lighter squad with
  2 skills would be rejected.

### Option B: squad.yaml manifest (VP Eng P4 original)

A single declarative manifest per squad listing all artifacts.

- **Pros:** machine-readable composition, future-proof.
- **Cons:** redundant with the filesystem layout + registry. The
  manifest would just enumerate what registry.py already discovers.
  Adds a second source of truth → drift risk.

### Option C: No formal contract; each squad ships what it wants

- **Pros:** zero friction to contribute.
- **Cons:** adopters can't predict what a squad provides. Validation
  impossible. Growth red line #9 (no skill bloat) becomes unenforceable.

## Decision

**Option A.**

### Formal contract

```
.claude/skills/domains/<squad-id>/
├── team-personas.md          (≥ 5 personas, fictional composites)
├── skills/
│   ├── <skill-1>/SKILL.md    (≥ 3 skills total)
│   ├── <skill-2>/SKILL.md
│   └── <skill-3>/SKILL.md
├── pitfalls.yaml             (≥ 10 pitfalls)
├── task-chains.yaml          (≥ 2 workflows)
├── examples/
│   └── PLAN-EXAMPLE.md       (one complete example plan)
└── (optional)
    ├── commands/
    ├── scripts/
    ├── frontend-team-personas.md
    └── ORG_CHART.md
```

### Validation rules (enforced by CI)

1. `check-tier-boundaries.py` MUST pass — domain does not leak into core/frontend (already enforced).
2. `registry.py --validate` MUST pass — every archetype in
   team-personas.md with a primary skill references an existing skill.
3. **Minimum counts:**
   - team-personas.md: ≥ 5 `### NN.` or `### <Name>` sections
   - skills/: ≥ 3 subdirectories with SKILL.md
   - pitfalls.yaml: ≥ 10 entries in `pitfalls:`
   - task-chains.yaml: ≥ 2 entries in `task_chains:`
   - examples/: ≥ 1 `.md` file

Minimum-count checks are added to `validate-governance.sh` in Sprint 5
(not blocking today — the lgpd-heavy-saas squad self-validates for now).

### Installation

```
bash scripts/install.sh <target> --profile core,lgpd-heavy-saas
```

Copies only:
- `.claude/skills/domains/lgpd-heavy-saas/` (entire subtree)
- (does NOT add to pitfalls-catalog.yaml — the domain catalog is
  loaded alongside, not merged)

### Positioning invariants (per Growth red lines)

- Squads MUST use fictional composite personas, never real-person names.
- Squads MUST NOT advertise paid tiers.
- Squads SHIP with at least one VETO holder (persona + scope stated in
  team-personas.md header).

### What a squad is NOT

- A general-purpose skill bundle (core tier handles that)
- A marketing label ("enterprise-ready squad" — avoid)
- A wrapper for third-party tools (squads are skill sets, not SDKs)

## Consequences

### Positive

- Every squad is predictable. Adopters know what they get.
- `install.sh --profile core,<squad>` works uniformly.
- Tier-boundary check remains meaningful.
- Registry auto-discovers squad skills like core/frontend ones.
- Growth red lines enforce positioning consistency.

### Negative

- Small squads (2-skill or 1-workflow) don't fit. Accepted: we want
  rigor-heavy squads, not drive-by micro-bundles.
- "≥ 5 personas" excludes minimal roster squads. Accepted: VETO
  coverage (at least Compliance + Security + Domain expert + Eng +
  QA) sets a floor for what a squad should provide.

### Neutral

- Squad installation remains a flag on install.sh; no new CLI.

## Blast Radius

- `.claude/skills/domains/lgpd-heavy-saas/` (NEW, 3 skills + personas + pitfalls + task-chains + example)
- `scripts/install.sh` — **UNCHANGED** (already accepts arbitrary profile names; lgpd-heavy-saas installs by name with no code change)

**Reversibility:** HIGH — delete the squad directory; no other file
references it by hard-coded path.

## References

- PLAN-004 §3 Phase 8
- PLAN-004/debate/round-1/vp-engineering.md §P4
- PLAN-004/debate/round-1/growth-engineer.md §P3
- PLAN-004/debate/round-1/consensus.md §C3
- ADR-006 (registry — validates squad skills against archetypes)

## Enforcement commit

`c958c18c6a62` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
