---
name: pre-plan-brainstorm
description: Requirements elicitation checklist run by the CEO or a delegated VP Product/VP Engineering before drafting an L3+ plan. Resolves ambiguity, maps stakeholders, surfaces constraints, enumerates tradeoffs, and emits a `spec.md` artifact that downstream Plan→Debate→Execute consumes via `## SPEC CONTEXT`. Kill-switch `CEO_BRAINSTORM_GATE=0` skips the phase.
owner: CEO (or delegated VP Product / VP Engineering archetype)
trigger: L3+ task with ambiguous requirements OR crossing 3+ modules OR unclear "who benefits" / "why now" / "what success looks like". Skip for L1-L2 patches, typo fixes, log messages, and well-precedented changes.
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 6
risk_class: low
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 6}
  engine: {active: true, priority: 6}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: plan-opened}
  - {event: help-me-invoked, regex: "(?i)brainstorm|plan|new.?task"}
---

# Pre-Plan Brainstorm — SKILL

## Why this exists

Our Plan → Debate → Execute protocol (`PROTOCOL.md` §Session protocol
Gate 3) consumes cycles in **Round 1 debate** resolving ambiguity that
could have been resolved pre-plan. superpowers (MIT framework, 159k
stars) battle-tested the pattern of **9-step brainstorm** as a
prerequisite to drafting the plan itself. superpowers audit BORROW-1
(ADR-058 PROPOSED) adopts this pattern.

**Same-LLM honesty:** this skill does not give the CEO independent
"expertise" it lacks — all agents are the same underlying model. What
it does is **force a checklist pass** that the CEO would otherwise
skip under time pressure, and **produce a durable spec.md artifact**
that survives across sessions and debate rounds.

## When to invoke

**Mandatory** (opt-out via `CEO_BRAINSTORM_GATE=0`):
- L3+ plan (`level: L3` or higher in frontmatter)
- Plan crosses 3+ modules OR 2+ subsystems
- Plan touches a VETO-protected domain (auth, financial, compliance)
- First-of-kind feature (no close precedent in the repo)

**Skip** (L1-L2 or well-precedented):
- Bug fix in 1-2 files
- Typo, log message, config tweak
- Change with an exact precedent already committed
- Mechanical refactoring (rename, extract, inline) with tests green

**Ambiguity smell-tests (any one triggers brainstorm):**
1. The request uses "should" / "probably" / "maybe" / "I think"
2. Success criteria are not enumerable as pass/fail tests
3. The reviewer of the PR cannot be named up-front
4. Rollback procedure is not obvious from the change

## The 9-step methodology (superpowers BORROW-1)

Every step emits a bullet-list into `spec.md`. No step is optional.
Empty-list is an acceptable answer but must be explicitly written
(e.g. "**Stakeholders:** none beyond Owner") so reviewers see the
emptiness, not its absence.

### Step 1 — Stakeholder mapping

List every human or system role affected by the change. For each:
- Name (role, not person — e.g. "Owner", "adopter CTO", "CI runner")
- Concern they will raise
- Signal they need at change-completion

### Step 2 — Success criterion elicitation

For each acceptance test, write a **falsifiable statement** that
would pass green on implementation success. Avoid "works correctly"
— write the `grep | test | assert` that would detect regression.

### Step 3 — Anti-goal elicitation

What are we explicitly NOT doing? Naming the anti-goal prevents
scope creep. Anti-goals are ADR-gate bait: "we considered X, chose
not to do X because Y".

### Step 4 — Constraint surfacing

Four axes, each bullet-listed:
- **Technical:** stdlib-only (ADR-002), Python 3.9+, byte-identity fixtures, etc.
- **Legal:** LGPD, GDPR, license compatibility, CODEOWNERS
- **Time:** deadline, rollback window, RC expiry, tag gate
- **Budget:** cost ceiling, Opus 4.8 vs Sonnet 4.6 eligibility

### Step 5 — Assumption listing

What are we assuming without verification? Each assumption is a
latent bug waiting to fire. Write each one down; mark which ones
are **provable now** vs **accepted-on-faith**.

### Step 6 — Known unknowns listing

What don't we know that we need to find out? Each becomes a
research task or a spike. If the list is empty, you are lying to
yourself.

### Step 7 — Tradeoff mapping (2-axis)

Pick two tradeoff axes most relevant to the change. Examples:
- Latency × correctness
- Velocity × rigor
- Backward-compat × cleanup
- Cost × observability
Plot 3 alternative designs on those axes. Annotate each point with
the residual risk.

### Step 8 — Preferred outcome scenarios (3 alternatives)

Write three concrete futures:
- **Best case:** what does success look like in 3 months?
- **Expected case:** what does the median outcome look like?
- **Worst case:** what is the recoverable failure mode?

Worst-case must be a recoverable failure. If worst-case is
unrecoverable, the plan is out-of-scope for brainstorm → escalate to
Owner before drafting.

### Step 9 — Spec artifact summary

Consolidate steps 1-8 into a single `spec.md` file under the plan's
directory. Required sections:

```
# PLAN-NNN Spec — Pre-Plan Brainstorm Output

## Stakeholders
## Success criteria
## Anti-goals
## Constraints (technical / legal / time / budget)
## Assumptions
## Known unknowns
## Tradeoffs (2-axis mapping)
## Preferred outcomes (best / expected / worst)
## Open questions for Owner
```

## Output artifact

`spec.md` lives at `.claude/plans/PLAN-NNN/spec.md`. The plan file
frontmatter references it via `spec_ref:` per PLAN-SCHEMA §Frontmatter
(amendment ADR-058). The plan's debate Round 1 prompts include
`## SPEC CONTEXT` with the spec content embedded (or referenced via
sha256 for cache efficiency, same pattern as `## SKILL REFERENCE`).

## Integration with PROTOCOL.md Gate 3

PROTOCOL.md §Session protocol Gate 3 (amendment ADR-058):

> **For L3+ plans with ambiguous requirements:** run the
> `pre-plan-brainstorm` skill BEFORE drafting the plan. The spec.md
> artifact it emits is consumed by debate Round 1 prompts via
> `## SPEC CONTEXT`. Kill-switch: `CEO_BRAINSTORM_GATE=0`.

## Anti-patterns (never do)

1. **Never skip Step 3 (anti-goals).** Anti-goals are the scope fence;
   without them, the plan grows under-the-radar.
2. **Never write "obvious" in Step 5 (assumptions).** If it were
   obvious, you wouldn't need the brainstorm.
3. **Never write unrecoverable worst-case.** Escalate to Owner
   instead of proceeding.
4. **Never invoke this skill for L1-L2 patches.** Overhead; use
   `CEO_BRAINSTORM_GATE=0` or skip by level.

## Testable checklist

See `CHECKLIST.md` in this same directory for the per-step
binary-pass rubric used by debate Round 1 to verify brainstorm
compliance.

## References

- superpowers (framework, MIT, 159k stars) — pattern origin
- `.claude/adr/ADR-058-brainstorm-gate-and-two-pass-review.md` — this amendment
- `PROTOCOL.md` §Session protocol Gate 3 — upstream integration
- `PLAN-SCHEMA.md` §Frontmatter — `spec_ref:` field definition
