---
id: ADR-137
title: Skill-priority-stack decision — spec-kit presets port (SKIP-DEFER)
status: ACCEPTED
proposed_at: 2026-05-20
proposing_session: S147
accepted_at: 2026-06-17
accepting_session: S242
enforcement_commit: 5bff6bb2
related_plans: [PLAN-110]
related_adrs: [ADR-115, ADR-125, ADR-126]
risk_tier: A
debate_required: true
---

# ADR-137 — Skill-priority-stack decision

## Context

GitHub's `spec-kit` ships a **4-tier template/script resolution stack**
(`presets/ARCHITECTURE.md:L248-L268`):

```
.specify/templates/overrides/        (highest priority)
  -> presets/<id>/templates/
    -> extensions/<id>/templates/
      -> .specify/templates/         (canonical fallback)
```

With **4 composition strategies** (`presets/ARCHITECTURE.md:L276-L284`):

- `replace` — override fully replaces canonical.
- `prepend` — override prepended; `{CORE_TEMPLATE}` placeholder injects canonical.
- `append` — override appended; `$CORE_SCRIPT` placeholder injects canonical.
- `wrap` — override wraps canonical (prepend + append).

Command registration writes to 17+ agent directories install-time with
format-specific rendering (`presets/ARCHITECTURE.md:L290-L328`).

ceo-orchestration's `.claude/skills/{core,frontend,domains}/<name>/
SKILL.md` is **flat**:

- No priority stacking.
- No composition mechanism (replace/prepend/append/wrap).
- No override surface at all.

`check_canonical_edit.py` hook enforces byte-identity for skill files
to prevent silent drift.

The doctrinal question Wave G adjudicates: **should `.claude/skills/`
adopt a priority stack + composition strategies, port
`presets/ARCHITECTURE.md:L248-L289`?**

## Decision

**PROPOSED: SKIP-DEFER** (revisit in 6 months OR upon concrete adopter
need).

Rationale:

1. **No current adopter is blocked by the flat hierarchy**. We have not
   received a single field report (S82-S146) of a user needing to
   override a core skill from a domain skill or extension.
2. **Anti-Goal #5 binding**. Any composition strategy that lets a
   domain skill override a core skill's `## SKILL CONTENT` block
   WITHOUT sentinel approval is **REJECTED BY DEFAULT** (PLAN-110 §6
   Anti-Goal #5). The 4-strategy spec-kit pattern would either:
   (a) violate this anti-goal directly (replace strategy), or
   (b) require sentinel approval per composition step (defeating the
   purpose of automated composition).
3. **Cost-benefit unfavorable at v1.39.0**. Adopting the 4-tier stack
   requires major rework of `check_canonical_edit.py`, +30-50 tests,
   new ADR for each composition strategy. The flat hierarchy is a
   feature, not a gap, until adopter evidence says otherwise.
4. **PILOT branch deferred**. If at some future point a concrete need
   surfaces, run a 30-day soak with 1 skill in
   `.claude/plans/PLAN-NNN-PILOT/wave-g-dry-run/` (NOT canonical
   `.claude/skills/`). Decide PROMOTE / RETAIN-PILOT / REVERT based
   on empirical data.

**REVISIT TRIGGERS**:

- 3+ adopter field reports requesting override capability.
- 6-month sunset (default revisit cadence).
- Federation adopters needing cross-machine skill composition.

## Consequences

### Positive

- **Doctrinal purity preserved**. Skill hierarchy remains flat,
  enforceable via byte-identity hook.
- **Anti-Goal #5 holds**. No backdoor for canonical-guard bypass.
- **Zero migration cost** for existing 147 skills.
- **Simpler adopter mental model**. New users see one canonical skill
  per name, no resolution-order confusion.

### Negative

- **No customization without forking**. Adopters who want to override
  a core skill must currently fork the entire framework or write a
  domain skill with a new name.
- **Adopter friction**. spec-kit users may expect a presets system
  and not find one. Mitigated by §References + revisit triggers.

### Neutral

- ADR-137 remains PROPOSED. Promotion to ACCEPTED at a separate
  ceremony OR by amendment if revisit triggers fire.

## Alternatives Considered

### Alternative 1: PILOT (30-day soak with 1 skill)

Pros: empirical data, low risk, reversible. Cons: 1 sprint of soak
overhead with no concrete adopter need motivating it.
**DEFERRED** — re-evaluate at revisit trigger.

Pilot candidate (if eventually run): `task-execution` skill, with
domain override via `prepend` strategy. Soak dir:
`.claude/plans/PLAN-NNN-PILOT/wave-g-dry-run/`.

### Alternative 2: SKIP-DEFER (this ADR's recommendation)

Pros: avoids commitment without evidence of need; preserves option to
adopt later. Cons: doesn't close the question definitively.
**RECOMMENDED**.

### Alternative 3: SKIP-FOREVER (retain flat hierarchy as feature)

Pros: doctrinal purity, simpler enforcement, closes the question.
Cons: forecloses future adoption even with strong adopter evidence.
**REJECTED** — too rigid; SKIP-DEFER is the correct posture.

## References

- spec-kit `presets/ARCHITECTURE.md:L248-L268` — 4-tier resolution stack
- spec-kit `presets/ARCHITECTURE.md:L276-L284` — 4 composition strategies
- spec-kit `presets/ARCHITECTURE.md:L290-L328` — agent dir command registration
- PLAN-110 §6 Anti-Goal #5 (no canonical-guard bypass)
- `.claude/plans/PLAN-110/wave-g-research.md` — full cost analysis
- ADR-125 §A — Tier-A defensibility
- `.claude/hooks/check_canonical_edit.py` — byte-identity enforcement

## Notes

**ACCEPTED (S242, 2026-06-17 — /ceo-boot ADR sweep).** Per S133 + S140 precedent,
promotion to ACCEPTED required Codex MCP R2 ≥3-iter ACCEPT + Owner GPG-signed
sentinel + separate ceremony bundle — all satisfied: Codex R-sweep ACCEPT thread
`019ed788` (S242) accepted the SKIP-DEFER decision's soundness; the Owner-GPG
ceremony commit applying this sweep is the signing artifact (ADR-136-AMEND-1 S228
precedent: Owner directive + ceremony commit in place of a dedicated sentinel path);
the `staged/promote/` bundle + `finish-adr-sweep.sh` is the ceremony bundle.

**Enforcement commit:** `5bff6bb2` (the commit that landed this ADR + PLAN-110
v1.39.0). The SKIP-DEFER is materially in force: `.claude/skills/` stays flat (no
overrides/presets/extensions dirs); `check_canonical_edit.py` enforces SKILL.md
byte-identity; no PILOT branch was ever activated.

If PILOT branch is ever activated, dry-run files MUST live in
`.claude/plans/PLAN-NNN-PILOT/wave-g-dry-run/` ONLY; canonical
`.claude/skills/` MUST remain untouched until promotion ceremony.
