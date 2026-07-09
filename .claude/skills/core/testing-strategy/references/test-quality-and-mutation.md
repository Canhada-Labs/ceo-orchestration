<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## Test Quality Metrics

### Mutation Testing

Mutation testing modifies source code (mutants) and verifies that tests
catch the change. A surviving mutant means tests are too weak.

```bash
# Using Stryker for mutation testing
npx stryker run --mutate "<path/to/domain-math>"  # e.g. lib/pricing.ts
```

Priority targets for mutation testing:
1. Core domain logic (invariant enforcement)
2. Numeric comparison and validation
3. Aggregation / computation functions
4. Signal / decision generation
5. Authentication and authorization logic

**Target mutation score: >= 80% for critical modules.**

### Branch Coverage

```bash
# Generate coverage report
npx vitest run --coverage

# Coverage targets
# Critical/domain modules: >= 90% branch
# External integrations: >= 80% branch
# Routes: >= 70% branch (many are thin wrappers)
# Overall: >= 75% branch
```

### Planted-bug behavioral evals (reviewer / skill validation)

Mutation testing measures whether *unit tests* catch injected faults. The same
idea validates a **reviewer or a skill**: feed it a diff containing a KNOWN,
deliberately-planted bug and assert that the reviewer flags it — at the right
severity. If a "Staff Code Reviewer" skill cannot catch a planted SQL injection
or a plaintext-password store, the skill is not doing its job, no matter how
fluent its prose.

This is a distinct class from coverage/mutation: it tests **judgement quality**,
not code-path coverage. Author the planted-bug set against your real threat
model (for this framework: OWASP LLM Top-10 + A07/A09 — SQLi, plaintext
credentials, secret-in-logs, secret-exfil via audit-log side-channel,
non-constant-time secret compare, LLM01 prompt-injection). Anchor severity to a
PoC: a planted bug with a working exploit path is Critical. Always pair the
positives with a **clean control** (a correct diff) so the eval catches a
reviewer that flags everything (a false-positive-prone reviewer is as useless as
a blind one).

Worked example: `.claude/skills/core/code-review-checklist/benchmarks/code-review-checklist.yaml`
carries planted-bug scenarios (`REVIEW-BENCH-008..013`) plus a clean
`CTRL-REVIEW-004` control, run advisory via
`run-skill-benchmark.py --skip-if-no-key`. Note the scorer has no
"refused-to-approve" verdict — these evals assert the reviewer **flags** the
bug (`must_flag_tags` at Critical); an explicit approval-refusal assertion would
be its own eval-code item with QA + Security sign-off.

### Test Quality Checklist

| Criterion | Description | Target |
|-----------|-------------|--------|
| Mutation score | % of mutants killed | >= 80% (critical modules) |
| Branch coverage | % of code branches tested | >= 75% overall |
| Error path coverage | Tests that verify error handling | >= 50% of try/catch blocks |
| Edge case coverage | Boundary values, empty inputs, max values | Every critical function |
| Negative testing | Tests that verify rejection of bad input | Every public endpoint |
| Determinism | Tests pass/fail consistently (no flaky) | 100% deterministic |

