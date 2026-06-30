---
id: SP-021
kind: skill-patch
proposal_target: .claude/skills/core/ceo-orchestration/SKILL.md
proposal_type: append-section
proposed_at: 2026-04-21T00:00:00Z
status: promoted
promoted_at: 2026-04-22T11:34:21Z
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-22T11:34:21Z
signer: 0000000000000000000000000000000000000000
---

# SP-021 — ceo-orchestration autonomous-loop capability mention

## Motivation

PLAN-017 Phase 5 — cross-reference the new autonomous-loop
capability (`.claude/scripts/swarm/`) in the CEO's self-documentation
so adopter CEOs know when/how to invoke parallel optimization loops.

## Target file content

**Append to `.claude/skills/core/ceo-orchestration/SKILL.md`** inside
or adjacent to the existing `## Decision framework` section, a new
subsection:

```markdown
### Autonomous-loop parallelism (opt-in capability)

For problems with **explorable solution space** (test speed
optimization, bundle size reduction, benchmark tuning, LLM prompt
iteration), the CEO may opt to spawn an **autonomous loop swarm**
via `.claude/scripts/swarm/coordinator.py`.

**Default: OFF.** Activation requires `CEO_SWARM=1` env var.

When to consider:
- Problem is measurable (quantitative outcome per iteration)
- Solution space is explorable (N variant approaches plausible)
- Budget envelope is explicitly set (prevent runaway cost)
- Owner pre-authorized swarm activation for this work

When NOT to use:
- Single deterministic task (no exploration benefit)
- Ambiguous outcome metrics (can't scorer select best-of-N)
- Budget unclear
- Governance-critical path (canonical edits, auth changes)

Loop outputs go through the tournament scorer
(`.claude/scripts/swarm/tournament.py`) for best-of-N promotion.
Losing loops are preserved as `.rejected` in git history.

Kill switches:
- `export CEO_SWARM=0` (env)
- `touch .claude/swarm-kill` (file)
- `python3 .claude/scripts/swarm/coordinator.py --abort <swarm_id>`

See `docs/AUTONOMOUS-LOOP-GUIDE.md` for full workflow.
```

## Pre-authorized

Owner D7 of `.claude/plans/WAR-ROOM/01-OWNER-AUTHORIZATIONS.md`.

## Ship criteria

- Append-only diff
- Cross-link to `docs/AUTONOMOUS-LOOP-GUIDE.md` valid after P06 ships
  that file
- validate-governance ≤ 10 warnings / 0 errors
