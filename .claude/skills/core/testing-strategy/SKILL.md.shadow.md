---
name: testing-strategy
description: Testing strategy, patterns, and quality assurance for the project.
  Covers vitest patterns, external integration test design (mocking transport,
  simulating reconnect, checksum validation for streaming sources), domain math
  test design (boundary values, precision edge cases), E2E multi-process testing
  (IPC, worker lifecycle), route testing (auth verification, input validation),
  database test patterns (mocking data layer), chaos test framework design, test
  quality metrics (mutation testing, branch coverage), React component/hook
  testing (RTL query priority, MSW network mocking, axe a11y), test-first TDD
  (RED/GREEN/REFACTOR discipline), and CI integration. Use
  when writing tests, reviewing test quality, designing test strategies, setting
  up CI pipelines, or evaluating test coverage gaps.
owner: QA Architect (archetype)
version: 1.1.0
inspired_by:
  - source: affaan-m/ecc/skills/react-testing@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/tdd-workflow@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
source: affaan-m/ecc@81af4076 skills/react-testing/ + skills/tdd-workflow/
license: MIT
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: low
stack: [pytest, jest]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: file-edit, glob: "**/test_*.py"}
  - {event: file-edit, glob: "**/*.test.{ts,tsx,js,jsx}"}
---

# Testing Strategy

> Examples use vitest, but the patterns apply to Jest, Mocha, pytest, Go testing,
> and any mainstream test runner.

## When to Activate

Read this skill when you are:

- writing or reviewing tests (unit, integration, E2E multi-process, chaos)
  in any mainstream runner;
- designing a test strategy for a new module or auditing coverage gaps;
- setting up or hardening a CI pipeline that gates deploy on tests;
- evaluating test QUALITY (mutation score, planted-bug reviewer evals),
  not just test quantity;
- writing behavior-focused tests for React components, custom hooks, or pages
  (see `references/react-component-testing.md`);
- running a test-first RED/GREEN/REFACTOR cycle for a new feature or bug fix
  (see `references/tdd-red-green-cycle.md`);
- editing files matched by the machine triggers in the frontmatter
  (`**/test_*.py`, `**/*.test.{ts,tsx,js,jsx}`).

The machine-first `activation_triggers` frontmatter remains the canonical
auto-load rule; this section is its human-scannable mirror.

## Current State

| Metric | Value | Assessment |
|--------|-------|-----------|
| Total tests | (measure) | Track passing/failing |
| Test files | (measure) | In `src/__tests__/` or equivalent |
| TypeScript errors | 0 target | `tsc --noEmit` clean |
| Framework | vitest 4.x | Fast, ESM-native |
| E2E multi-process tests | (measure) | Often a gap |
| Stress/chaos tests | (measure) | Often a gap |
| CI test execution | required | Tests must run before deploy |
| Mutation testing | (optional) | Verifies test quality |
| Branch coverage | (measure) | Should be tracked |

### Key Principle

> A passing test suite is not a quality signal unless the tests themselves
> are audited. Happy-path tests without error-path, auth, multi-process, and
> edge-case coverage can give a false sense of safety.

## Reference Files — progressive disclosure (PLAN-153 Wave C)

The deep-dive sections of this skill were extracted VERBATIM into the ten
Wave-C `references/*.md` files listed below — zero content loss (every content
line of the pre-split SKILL.md appears verbatim either in this file or in one
of those ten references; the loader additionally ADDS loader-only sections —
When to Activate, the pointer tables, the changelog). Load on demand:

| Load `references/<file>` | For |
|---|---|
| `vitest-patterns.md` | Runner config, test-file conventions, standard structure, core rules |
| `integration-testing.md` | External-integration tests: mock transport, checksum validation, reconnect simulation |
| `domain-math-and-property-based.md` | Boundary values, decimal-precision edge cases, property-based tests |
| `e2e-multiprocess.md` | E2E multi-process/IPC test design, worker lifecycle |
| `route-testing.md` | Route auth-verification and input-validation tests |
| `database-testing.md` | Mock data layer, RLS/access-control test patterns |
| `chaos-testing.md` | Chaos framework: IPC failure, memory pressure, upstream disconnect, DB outage |
| `test-quality-and-mutation.md` | Mutation testing, branch coverage, planted-bug behavioral evals, quality checklist |
| `ci-integration.md` | Required CI pipeline shape + CI rules |
| `module-test-matrices.md` | Per-module what-to-test priority tables |

### Merged-in references (PLAN-153 Wave G — clean-room ADAPT)

These two references carry knowledge ported clean-room and adapted into our
voice (provenance in the `inspired_by:` frontmatter). They are NOT verbatim extractions, so they do
**not** participate in the Wave-C verbatim-union invariant above — treat them
as first-party framework content authored during the Wave-G merge. Load on
demand:

| Load `references/<file>` | For |
|---|---|
| `react-component-testing.md` | React component & hook tests: RTL query priority, `userEvent`, MSW network mocking, `axe` a11y assertions, snapshot boundaries, and the RTL-vs-Playwright decision line |
| `tdd-red-green-cycle.md` | Test-first RED/GREEN/REFACTOR discipline: the RED-gate proof obligation, test-runner detection, git checkpoints, and the TDD evidence report |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Test only happy path | Misses error handling bugs | Test error paths and edge cases |
| Mock everything | Tests pass but system broken | Integration tests for critical paths |
| Test implementation, not behavior | Breaks on refactor | Test inputs and outputs |
| Shared mutable state between tests | Flaky, order-dependent | Fresh setup per test |
| `expect(true).toBe(true)` | Vacuous truth | Assert specific values from computation |
| Skipping flaky tests | Hidden failures | Fix the flake or delete the test |
| No tests for auth | Privileged routes ship unauthed | Every route MUST have auth test |
| Testing in production only | Typo deploys to prod | CI runs tests before deploy |
| `any` in test types | Hides type mismatches | Use proper types in tests too |
| Testing private methods | Couples to implementation | Test via public interface |
## Adopter Note — Runner Framing + Example Biases (PLAN-044 P0-12)

This skill's top portability note ("Examples use vitest, but
the patterns apply to Jest, Mocha, pytest, Go testing, and
any mainstream test runner") is honest — but several
subsections below carry originating-project biases that are
worth naming explicitly for fresh adopters:

- §Current State table lists `Framework: vitest 4.x`,
  `src/__tests__/` location, and `TypeScript errors: 0
  target / tsc --noEmit clean`. Replace with your runner,
  your test-file location, and your typecheck tool before
  citing in review.
- §External integration test design references `mocking
  transport, simulating reconnect, checksum validation for
  streaming sources` — that is the originating ingestion-
  engine's test shape. Your integration-test shape may be
  HTTP-mocking, fixture-replay, or sandbox-environment.
- §Domain math tests reference `boundary values, precision
  edge cases` — universal when your domain has math, but
  the originating-project examples come from financial-
  instrument pricing. Substitute your own domain's
  boundary cases.
- §E2E multi-process tests (IPC, worker lifecycle) assume
  Node's cluster/worker model. On other runtimes the
  equivalent is different (Python multiprocessing, Go
  goroutine test harnesses, JVM test containers).

- `references/react-component-testing.md` and
  `references/tdd-red-green-cycle.md` are JS/TS-flavored
  (RTL, MSW, `bun test` vs `bun run test`). The *principles*
  — accessible queries, network-seam mocking, the RED-gate
  proof obligation, and the evidence report — transfer to
  any stack; the tool names do not.

The patterns (mocking at the transport seam, asserting on
observable state not private calls, mutation testing to
verify test quality, CI-runs-tests-before-deploy) all
transfer. The tool names and file paths do not.

## Changelog

- **1.1.0** (2026-07-09, PLAN-153 Wave G, SP-026): two clean-room
  ADAPT merges added as NEW references — `react-component-testing.md`
  (React Testing Library / MSW / axe) and `tdd-red-green-cycle.md`
  (test-first RED/GREEN/REFACTOR + evidence report), both ported
  clean-room (provenance in `inspired_by:` frontmatter). Core gains two pointer rows,
  an activation-cue pair, and an adopter-note bullet; no Wave-C content
  changed. Soak: parallel-shadow (OQ3=c) until >= 2026-07-14. Adds zero to
  the skill count (references, not new SKILL.md files).
- **1.0.0** (2026-07-07, PLAN-153 Wave C, SP-022): progressive-disclosure
  restructure — deep-dive sections extracted verbatim to `references/*.md`;
  added `version:` frontmatter, this changelog, and the human-scannable
  `## When to Activate` section. Zero change to the extracted content.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=5dfa88aa074f04d89de90890e26195c737a935d51fb26f99a49c455820fbca3a
