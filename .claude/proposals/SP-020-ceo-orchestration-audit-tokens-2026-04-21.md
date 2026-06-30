---
id: SP-020
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

# SP-020 — ceo-orchestration /audit-tokens routing note

## Motivation

PLAN-047 Phase 4 — cross-reference the new `/audit-tokens` slash
command in the CEO's self-documentation so adopter CEOs know
when/how to invoke detectors.

## Target file content

**Append to `.claude/skills/core/ceo-orchestration/SKILL.md`** just
before the existing `## Anti-patterns (NEVER do)` section, a new
subsection:

```markdown
## Observability tools (self-diagnostic)

### `/audit-tokens`

Run detectors over `audit-log.jsonl` to surface ghost-token-waste
patterns. Available detectors (PLAN-047 Phase 1):

- `retry_churn` — same task × ≥3 spawns / ≤30min / sub-T1 resolution
- `tool_cascade` — ≥5 consecutive exploratory spawns
- `looping` — same subagent_type × ≥3 spawns / overlapping file_assignment
- `wasteful_thinking` — Opus on short non-VETO task
- `weak_model` — Haiku on VETO role (governance violation)
- `overpowered` — non-Haiku on devops boilerplate

Usage (invoked via slash command OR direct CLI):

```
/audit-tokens window=30 format=markdown
# or
python3 .claude/scripts/audit-tokens.py --window 30 --format markdown
```

See `docs/TOKEN-ECONOMY-ADOPTER-GUIDE.md` for interpretation.

### `/terse`

Toggle output-economy mode (PLAN-047 Phase 2). VETO auto-off for
code-review, security-engineer, qa-architect verdict, compliance.

See `.claude/skills/core/terse-mode/SKILL.md`.
```

## Rationale

Cross-reference is adopter-facing. Without this amendment, adopters
reading the CEO skill don't discover `/audit-tokens` or `/terse`
slashes unless they happen to list `.claude/commands/`.

## Pre-authorized

Owner D7 of `.claude/plans/WAR-ROOM/01-OWNER-AUTHORIZATIONS.md`.

## Ship criteria

- Append-only diff (no existing content removed)
- validate-governance ≤ 10 warnings / 0 errors
