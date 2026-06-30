---
name: spec-clarify
description: Disciplined ambiguity reduction for PLAN-NNN. 10-category taxonomy (Functional/Domain/UX/NFQ/Integration/Edge-Cases/Constraints/Terminology/Completion/Misc) with 5-question hard cap per session. Dated write-back into PLAN ## Clarifications section. Manual-only via /spawn spec-clarify <PLAN-NNN>. Port of spec-kit /clarify.
owner: QA + Domain Expert archetype (cross-cut)
domain: core
priority: 2
risk_class: low
context_budget_tokens: 1300
activation_mode: manual-only
inactive_but_retained: false
stack: []
plan_origin: PLAN-110
added_at: 2026-05-20
---

# spec-clarify — disciplined ambiguity reduction for PLAN-NNN

> **Activation**: manual-only via `/spawn spec-clarify PLAN-<NNN>`.
> Typical use: between `/debate round1` and `/debate round2` to reduce
> ambiguity before adversarial round 2.
> Never invoked by `/debate` or `/ceo-boot` by default.

## Purpose

Port of github/spec-kit's `/speckit.clarify` (`templates/commands/clarify.md`).
Implements a sequential 5-question loop across 10 ambiguity categories,
with dated write-back into the plan's `## Clarifications` section.

## 10 categories (taxonomy verbatim from clarify.md:L308-L363)

1. **Functional Scope & Behavior** — what the system DOES.
2. **Domain & Data Model** — entities, relationships, lifecycle.
3. **Interaction & UX Flow** — surfaces, sequencing, defaults.
4. **Non-Functional Quality Attributes** — perf, reliability, scale.
5. **Integration & External Dependencies** — upstream/downstream contracts.
6. **Edge Cases & Failure Handling** — error paths, retries, partial state.
7. **Constraints & Tradeoffs** — non-negotiables + explicit deferrals.
8. **Terminology & Consistency** — vocabulary, naming, definitions.
9. **Completion Signals** — done criteria, acceptance metrics.
10. **Misc / Placeholders** — TBDs, owner-attestation gaps, stale TODOs.

Codex R1 originally missed the 10th category; R2 confirmed all 10 via
`clarify.md:L308-L363`. **DO NOT** truncate to 9 categories.

## Sequential questioning loop

- **Max 5 questions per session** (hard cap per `clarify.md:L432-L433`).
- Present 1 question at a time; await answer; integrate; pick next.
- Stop early if Owner answers "stop" or "no more" or 5 reached.
- Questions framed as: `Q[N/5] <category>: <specific ambiguity question>?`

## Markdown table format

For each question, present:

```
| Option | Description |
|--------|-------------|
| A      | <interpretation A> |
| B      | <interpretation B> |
| Recommended: | <yes/recommended/<short answer>> |
```

Per `clarify.md:L144-L159`.

## Write-back format

After each question is answered, append to PLAN-NNN's `## Clarifications`
section with `### Session YYYY-MM-DD` subheading:

```
## Clarifications

### Session 2026-05-20

- **Functional Scope** (Q1/5): <question summary>
  - **Owner**: <answer>
  - **Rationale**: <if Owner provided>

- **Domain & Data Model** (Q2/5): ...
```

Per `clarify.md:L415-L418`.

When the answer resolves an inline `[NEEDS CLARIFICATION: …]` marker
(PLAN-SCHEMA §14), record the answer under `## Clarifications` as above,
then **delete the inline marker** from the AC/Approach text it qualified —
the resolved decision stays in prose; the open-question token does not.

## Invocation contract

```
/spawn spec-clarify PLAN-NNN
```

## Validation pass post-write

- Max 5 questions: ≤5 entries under today's `### Session YYYY-MM-DD`.
- No duplicates: same category may repeat across sessions but not within.
- Terminology consistency: terms introduced match earlier sections of PLAN.

## Anti-pattern boundary

- Does NOT modify ACs, frontmatter, or any section outside `## Clarifications`.
- Does NOT trigger LLM calls without explicit `/spawn` invocation.
- Does NOT auto-invoke from `/debate` rounds.

## Tests

See `tests/skills/test_spec_clarify_skill.py` — fixture cases:
- 10-category taxonomy covered in skill source (`test_taxonomy_covers_10_categories`).
- 5-question cap honored.
- Write-back format matches `### Session YYYY-MM-DD` regex.
- `activation_mode: manual-only` flag present.

## References

- Port source: github/spec-kit `templates/commands/clarify.md:L308-L363, L432-L433, L415-L418`
- PLAN-110 Wave C acceptance metric
- Wave H activation-mode doctrine
