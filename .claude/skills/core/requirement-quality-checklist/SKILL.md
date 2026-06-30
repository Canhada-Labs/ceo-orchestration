---
name: requirement-quality-checklist
description: >
  'Unit Tests for English' — validates requirements writing quality, NOT
  implementation. 5 categories
  (Completeness/Clarity/Consistency/Coverage/Edge-Cases). Rejects
  implementation testing language (Verify/Test/Confirm). Writes checklist.md
  artifact with falsifiable items + spec citations. Manual-only via /spawn
  requirement-quality-checklist <PLAN-NNN>. Port of spec-kit /checklist.
owner: QA + Tech Writer archetype (cross-cut)
domain: core
priority: 2
risk_class: low
context_budget_tokens: 1100
activation_mode: manual-only
inactive_but_retained: false
stack: []
plan_origin: PLAN-110
added_at: 2026-05-20
---

# requirement-quality-checklist — "Unit Tests for English"

> **Activation**: manual-only via `/spawn requirement-quality-checklist <PLAN-NNN>`.
> Validates REQUIREMENTS WRITING QUALITY, not implementation.

## Purpose

Port of github/spec-kit's `/speckit.checklist` (`templates/commands/checklist.md:L253-L266`).
Implements "Unit Tests for English" doctrine: checklists validate the
QUALITY OF THE WRITING in the requirements, not the behavior of the system.

## Prohibited patterns (reject at output time)

The following item-starts are REJECTED — they belong in test suites, not
in a requirements-quality checklist:

- `Verify ...` — implementation testing language.
- `Test ...` — implementation testing language.
- `Confirm ...` — implementation testing language.
- `Validate that <code does X>` — implementation testing language.

## Categories (per `checklist.md:L30-34`)

1. **Completeness** — is the requirement fully specified?
2. **Clarity** — is the language unambiguous?
3. **Consistency** — does it agree with other requirements?
4. **Coverage** — does the spec cover all stated functionality?
5. **Edge Cases** — are boundary + failure conditions stated?

## Output format

Writes structured checklist artifact to:

```
.claude/plans/PLAN-NNN/checklist.md
```

Each item:

- Falsifiable (a human can render a yes/no verdict by reading the spec).
- Cites a specific line anchor in PLAN-NNN body (`L<NNN>` or `§<section>`).
- Belongs to one of the 5 categories.

Limit: **50 items max**.

## Example output (falsifiable item)

```
## Completeness

- [ ] §Wave A AC1 specifies skill domain (core/frontend/domains).
  - Spec anchor: PLAN-NNN.md §Wave A AC1 L270
  - Falsifiable: reads "[.claude/skills/core/<name>/SKILL.md]" path = passes.
```

## Anti-pattern boundary

- Does NOT execute tests.
- Does NOT modify PLAN-NNN body (writes its own checklist.md only).
- Does NOT auto-invoke; manual-only.

## Tests

See `tests/skills/test_requirement_quality_checklist.py` — 6 fixture cases:
- Prohibited-pattern detection rejects `Verify .../Test .../Confirm ...` items.
- Falsifiability check passes for each example item.
- Spec-citation requirement: every item cites `§` or `L<NNN>`.
- 5-category coverage emitted in skill source.
- Deterministic ordering.
- `activation_mode: manual-only` flag present.

## References

- Port source: github/spec-kit `templates/commands/checklist.md:L253-L266, L30-34`
- PLAN-110 Wave E acceptance metric
- Wave H activation-mode doctrine
