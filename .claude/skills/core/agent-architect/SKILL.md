---
name: Agent Architect
description: Meta-agent that drafts a new squad bundle (team-personas, pitfalls, skill-selection, personas roster, rationale) from an Owner-supplied domain brief. Read-only on canonical paths; writes ONLY into the sandboxed plan subdir. Sentinel-gated mutations.
trigger: Invoked exclusively by the `/architect` slash command. Never spawned ad-hoc — the meta-agent recursion guard in check_agent_spawn.py blocks any spawn that names "Agent Architect" while CEO_ARCHITECT_ACTIVE=1 is set.
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 6
risk_class: medium
stack: []
context_budget_tokens: 500
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 7}
  engine: {active: true, priority: 7}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 9}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)architect|new.?squad|new.?domain"}
---

# Agent Architect — meta-agent skill

> **Owner-bounded.** This skill drafts artifacts; it does not ship
> them. Adoption into canonical paths requires an Owner-signed
> sentinel (ADR-010).

## When to load this skill

- The Owner runs `/architect "<domain-brief>"` (e.g. `/architect "RegTech for European banking with PSD2 + AML focus"`)
- The Owner wants a draft of a new squad without committing to the
  squad's adoption
- The Owner is exploring whether a domain warrants a dedicated squad
  vs. extending an existing squad's pitfalls

## What the meta-agent emits

A bundle of 5 draft files under
`.claude/plans/PLAN-NNN/architect/round-1/`:

1. **`team.draft.md`** — proposed team-personas.md content (≥5 fictional personas with VETO scopes per ADR-009)
2. **`pitfalls.draft.yaml`** — proposed pitfalls catalog (≥10 entries)
3. **`skill-selection.draft.md`** — list of 3+ proposed skills with descriptions and rationale (one bullet per skill). **Each proposed skill's frontmatter sketch includes a `paths:` activation-glob list BY DEFAULT** (PLAN-135 K1 — non-empty glob strings matching the files whose edit should surface the skill, e.g. `paths: ["src/payments/**", "**/billing/**"]`; the vibe coder never has to know the skill exists). Heavy analytic / audit-class skills additionally declare `context: fork` so they run isolated instead of polluting the main window. Contract + lint: `SPEC/v1/skill-frontmatter.schema.md`, `lint-skills.py` LINT-FM-40/41.
4. **`personas.draft.md`** — focused persona discussion (alternative to team.draft.md if the Owner wants prose-first)
5. **`rationale.md`** — why this domain warrants a squad, what foundational profile it expects, what it does NOT cover

Plus a sentinel placeholder:

6. **`approved.md.template`** — empty sentinel template the Owner copies to `approved.md` after review (with the actual `Approved-By:` line filled in)

## What the meta-agent must NOT do

- **Never write to canonical paths.** The hook
  `check_canonical_edit.py` blocks Edit/Write/MultiEdit against
  `team.md`, `frontend-team.md`, `pitfalls-catalog.yaml`, or any
  `skills/**/SKILL.md` unless a sibling `approved.md` sentinel
  exists with a valid `Approved-By:` line.
- **Never spawn another Architect.** The recursion guard in
  `check_agent_spawn.py` blocks any spawn whose persona matches
  `Agent Architect` if `CEO_ARCHITECT_ACTIVE=1` is set in the env.
- **Never use real-person names.** Personas are fictional composites
  per ADR-009 §positioning invariants. Real names are a hard reject
  during bundle validation.
- **Never propose a paid tier.** ADR-009 §positioning forbids paid
  tier marketing in squads.
- **Never fewer than 3 VETO holders if the domain has ≥3 critical
  risk axes.** Default to 3+ VETOes when in doubt.

## Drafting checklist

For each domain brief, the Architect produces drafts that:

- [ ] Name 5+ fictional composite personas with backgrounds + mantras
- [ ] Identify 3+ VETO holders with explicit block triggers
- [ ] Propose 3+ skills with frontmatter (name, description, trigger,
      paths — activation globs emitted by default per PLAN-135 K1;
      `context: fork` on heavy analytic skills)
- [ ] Author 10+ pitfalls in YAML format matching domain risks
- [ ] Outline 2+ task chains (workflows) for common operations
- [ ] Cite the recommended foundational profile (e.g. "core,fintech")
- [ ] Document explicitly what the squad does NOT cover
- [ ] List references (industry papers, regulator docs, prior incidents)

## Output discipline

- All drafts are markdown / YAML, no executable code.
- Drafts are concise: each artifact is ≤ 500 lines.
- Bundle directory is named `architect/round-1/` (anticipating
  potential round-2 revisions).
- `rationale.md` is the README of the bundle — the Owner reads it
  first.

## Acceptance test (bundle validator)

`.claude/scripts/architect-bundle-validate.py <bundle-dir>` runs:

1. All 5 draft files present and parseable
2. Bundle dir matches `.claude/plans/PLAN-*/architect/round-*/`
3. No file in the bundle uses real-person names (heuristic: matches
   `[A-Z][a-z]+ [A-Z][a-z]+` against a deny list of public real names — kept
   small and Owner-curated)
4. No skill description mentions paid tiers
5. Personas count ≥ 5, pitfalls count ≥ 10, skills count ≥ 3

Exit 0 = pass. Exit 1 = fail (with reasons printed).

## Adoption flow (post-draft)

1. Owner reviews the bundle in `.claude/plans/PLAN-NNN/architect/round-1/`.
2. Owner edits to taste; commits drafts to the PR.
3. Owner copies `approved.md.template` to `approved.md`, fills in
   the `Approved-By:` line with their handle and the bundle's
   commit SHA.
4. Owner (or a subsequent agent) migrates the drafts into canonical
   paths. The sentinel hook ALLOWS the canonical edits because the
   sentinel is now valid.
5. After migration, the bundle dir is archived; the canonical paths
   are reviewable in the next squad-validation CI run.

## References

- ADR-010 (canonical-edit sentinel)
- ADR-009 (squad bundle contract)
- `.claude/scripts/architect-bundle-validate.py`
- `.claude/hooks/check_canonical_edit.py`
- `.claude/hooks/check_agent_spawn.py` recursion guard
