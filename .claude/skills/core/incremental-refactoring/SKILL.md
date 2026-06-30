---
name: incremental-refactoring
description: Safely evolving existing production codebases through incremental
  refactoring. Focus on minimal-change corrections, backward compatibility,
  and avoiding unnecessary rewrites. Use when modifying existing systems,
  fixing correctness issues, improving architecture, adding features to
  production code, reviewing proposed changes for blast radius, or planning
  multi-step migrations. Also use when the user says "minimal change",
  "don't rewrite", "backward compatible", or "smallest diff possible".
owner: VP Engineering (archetype)
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: medium
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 5}
  trading-readonly: {active: true, priority: 7}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)refactor|cleanup|technical.?debt"}
---

# Incremental Refactoring

## Fail-Fast Rule

If any mandatory invariant, validation, or precondition fails, **stop and
return a structured failure**. Never guess, infer, smooth, approximate,
or "fix" business-critical data.

## Cardinal Rule

Every change must be the **smallest correct diff** that achieves the goal.
If a change can be split into two independent changes, it should be.
Production systems earn trust through small, reversible steps.

## Do Not Touch Hot Path

**Never refactor, optimize, or restructure hot-path logic unless explicitly
instructed by the user.** The hot path is any code that executes on every
incoming request or event (request handlers, normalization, cache update,
response serving, background processors on the critical read/write path).

If the user asks for a general refactor, clarify scope first:
- "Does this include hot-path code?"
- If no explicit confirmation, exclude hot path from the change.

Changes to hot-path code require:
- Explicit user instruction
- Shadow mode validation before cutover
- Rollback plan documented before merge

## Shadow Mode for Critical Logic

For any logic change that affects a **critical computation** (numeric math,
ranking, pricing, eligibility, score calculation — anything where a silent
regression would harm users), a shadow computation **must** exist before
replacing production logic:

```typescript
function computeMetric(input: Input): MetricResult {
  const oldResult = legacyComputeMetric(input);

  if (FLAGS.shadowNewMetric) {
    try {
      const newResult = newComputeMetric(input);
      if (!oldResult.value.eq(newResult.value)) {
        logger.warn('shadow_metric_mismatch', {
          key: input.key,
          old: oldResult.value.toString(),
          new: newResult.value.toString(),
          diff: computeDiff(oldResult.value, newResult.value),
        });
        metrics.increment('shadow.metric_mismatch');
      }
    } catch (err) {
      logger.error('shadow_metric_error', { error: err });
    }
  }

  return oldResult; // always serve old during shadow
}
```

Only switch to new logic after shadow mode shows zero mismatches
(or only expected, documented differences) over a sufficient period.

## Change Classification

Before writing code, classify the change:

| Type | Risk | Approach |
|---|---|---|
| Bug fix (behavior change) | Medium | Fix only the bug. No cleanup. |
| New feature (additive) | Low-Medium | Add new code. Don't modify existing interfaces. |
| Refactor (structure change) | Medium-High | No behavior change. Tests pass before and after. |
| Migration (breaking change) | High | Multi-phase with backward compat period. |
| Cleanup (cosmetic) | Low | Never bundle with behavior changes. |

**Never combine different types in one change.**

## The Minimal Diff Protocol

1. **State the goal** in one sentence.
2. **Identify blast radius**: files, functions, types, consumers affected.
3. **List what does NOT change**: preserved behaviors.
4. **Write the smallest diff**.
5. **Verify**: existing tests pass unmodified. If tests need changes,
   reconsider — blast radius may be larger than expected.

### Blast Radius Checklist

- [ ] No interface changes unless that IS the goal
- [ ] No import changes outside blast radius
- [ ] No renamed variables/functions outside target code
- [ ] No formatting/style changes outside target code
- [ ] No dependency additions unless strictly required
- [ ] Existing tests pass unmodified
- [ ] Hot path is untouched (unless explicitly scoped)

## Backward Compatibility

- New fields are optional with defaults.
- Renamed fields: keep old name as alias during migration.
- Removed functionality: deprecate first (log warning), remove later.
- DB schema: add column → backfill → migrate reads → drop old column.

### Expand-Contract Pattern

```
Phase 1 (Expand): Add new code alongside old. Both work.
Phase 2 (Migrate): Move consumers to new code. Old still works.
Phase 3 (Contract): Remove old code after confirming zero usage.
```

Each phase is a separate deployment.

## Feature Flags

```typescript
const FLAGS = {
  useNewInputValidation: process.env.FF_NEW_INPUT_VALIDATION === 'true',
};

function validateInput(input: Input): boolean {
  if (FLAGS.useNewInputValidation) return newStrictValidation(input);
  return legacyValidation(input);
}
```

- Default = old behavior (flag off = old code).
- Flags are temporary. Remove after stable rollout.
- Track flag state in logs/metrics.

## Migration Playbook

```
Step 1: Write to both old and new format (dual-write)
Step 2: Read from new format, fall back to old
Step 3: Verify all reads from new format (monitor fallback rate → 0)
Step 4: Stop writing old format
Step 5: Clean up old data
```

Each step is a separate deployment with its own rollback plan.

### Rollback Plan

Every change must have a rollback plan before deployment:

- **Feature flag changes**: Turn off the flag.
- **Additive schema changes**: No rollback needed.
- **Code changes**: Revert the commit.
- **Data migrations**: Describe undo (or confirm one-way with backup).

If rollback plan takes more than one sentence, the change is too big.

## Code Review Principles

- **"What doesn't change?"** — answer should be most of the system.
- **Count files touched** — >5 files for a bug fix = something is wrong.
- **Look for hidden behavior changes** — "refactor" that changes test
  expectations is not a refactor.
- **Check for scope creep** — "while I was in here..." = split it out.
- **Verify test coverage** — new behavior needs new tests. Refactors
  pass existing tests unchanged.

## Working with Legacy Code

1. Don't judge, fix. The code works in production.
2. Add tests first for the behavior you're about to change.
3. Make the change within the existing structure.
4. Refactor separately, after the behavior change is stable.

Never use "the code was messy" as justification for a rewrite.

## Estimation Template

| Field | Example |
|---|---|
| Goal | Prevent invalid input from reaching the cache layer |
| Blast radius | `cache/store.ts`, `api/middleware/validate.ts` |
| Files touched | 2 |
| Lines changed | +30 / -5 |
| Risk | Low — additive validation, no behavior change on valid data |
| Hot path affected? | No |
| Rollback | Remove validation middleware |
| Effort | 2-3 hours including tests |
| Dependencies | None |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| "While I'm here" scope creep | Inflates blast radius | Separate PR |
| Bug fix + refactor in one PR | Can't isolate cause | Two changes |
| "Let's rewrite this module" | Loses edge case handling | Incremental improvement |
| Interface change without migration | Breaks all consumers | Expand-contract |
| Skipping tests for small changes | Small changes cause outages | Test proportional to risk |
| Refactoring hot path unprompted | Risks request/event pipeline | Explicit instruction + shadow mode |
| New logic without shadow period | Can't compare old vs new | Shadow first, switch later |
