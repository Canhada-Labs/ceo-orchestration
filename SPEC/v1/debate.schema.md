# SPEC v1 — debate.schema

> **Normative source:** `.claude/plans/DEBATE-SCHEMA.md`
> **Spec version:** 1.0.0-rc.1

## Summary (normative)

Multi-round debate artifacts on disk at
`.claude/plans/PLAN-<NNN>/debate/round-N/`:

- `proposal.md` (round 1 only)
- `<archetype-slug>.md` (one per participating archetype)
- `consensus.md` per round
- `synthesis.md` for a round-3 terminal synthesis

Each critique file has frontmatter (`round`, `archetype`, `skill`,
`agent_persona`, `generated_at`) + 7 required body sections (`Verdict`,
`Summary`, `Risks`, `Must-fix`, `Nice-to-have`, `Unseen`, `What I would
NOT change`).

Consensus files have frontmatter (`plan`, `round`, `rounds_synthesized`,
`agents_considered`, `decisions_revised_in_plan`, `synthesized_at`,
`synthesized_by`) + body sections enumerating consensus findings,
single-agent insights kept, insights deferred, plan adjustments, and
a round verdict (`PROCEED` | `RUN-ANOTHER-ROUND` | `ESCALATE-TO-OWNER`).

For the full contract including the 3-round maximum and the
same-LLM-forced-perspective rationale, read
`.claude/plans/DEBATE-SCHEMA.md`.

## Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | Sprint 4 opening | Initial published contract; default 3 archetypes per round, with exceptional 6-archetype round 1 permitted for maximally cross-cutting plans (see PLAN-004/debate/round-1/consensus.md) |
