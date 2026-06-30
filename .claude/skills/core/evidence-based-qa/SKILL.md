---
name: core-evidence-based-qa
description: Evidence-based quality assurance doctrine for {{PROJECT_NAME}}. Teaches
  the reasoning behind test-signal discipline — when a defect may be declared fixed,
  how to interpret coverage numbers without coverage-washing, why mutation score
  outranks line coverage as a quality signal, and how to produce reviewer-trusted
  sign-offs that cite verifiable evidence rather than assertions. Use when performing
  QA review, classifying regressions, evaluating test quality, interpreting CI output,
  or any time an agent claims "tests pass" or "bug fixed" and must back that claim.
owner: QA Architect (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/testing/testing-evidence-collector.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-reality-checker.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-test-results-analyzer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: low
stack: []
context_budget_tokens: 1000
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 4}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)evidence|qa|verify"}
---

# Evidence-Based QA

No claim about software quality is accepted without a verifiable test signal.
"Should work" is not evidence. "I checked it manually" is not a finding.
"Tests pass" without citing which tests, on which branch, against which commit, is
a self-report — and self-reports are the single largest source of phantom QA
sign-offs in multi-agent systems.

This skill encodes the reasoning discipline that sits **behind** the CI coverage
gate and `mutation-gate.yml`. The mechanical gates enforce thresholds; this skill
teaches why those thresholds exist, what they fail to catch, and how a QA agent
produces a sign-off that survives adversarial scrutiny.

---

## What This Skill Is (and isn't)

**Is:** A reasoning doctrine. A set of hard rules for interpreting test output,
classification heuristics for regression types, and a WRONG/CORRECT vocabulary
for common QA errors. It applies whenever an agent evaluates whether a change is
correct, safe to merge, or genuinely fixed.

**Is not:** A test-runner manual. It does not prescribe which test framework to
use, how to structure test files, or how to configure CI pipelines. That lives in
`core/testing-strategy`. This skill is about the *judgment layer* that interprets
the output of whatever runner {{PROJECT_NAME}} uses.

**Is not:** A replacement for the mechanical gates. The CI coverage gate,
`mutation-gate.yml`, and the hook-enforced test count are the load-bearing
enforcement. This skill makes those gates interpretable. When a gate is green, this
skill prevents the agent from concluding "therefore quality is sufficient." When a
gate is red, this skill provides the vocabulary for a precise finding.

**Scope:** Applies to any agent that produces QA-adjacent output — test authorship,
regression triage, defect closure, release-readiness assessment, inter-rater scoring,
or any claim of the form "X is fixed" / "Y is safe to ship."

---

## The Evidence Hierarchy

Each claim type requires a specific evidence layer. A lower-layer artifact does not
substitute for a higher-layer requirement.

| Claim | Minimum required evidence | Typical artifact |
|-------|--------------------------|-----------------|
| "This function works correctly" | Unit tests with assertion-level coverage of branches | Passing test output with test names visible |
| "This property holds for all inputs" | Property-based test suite with seeded shrinking | fast-check / Hypothesis run log with seed |
| "This refactor did not break behavior" | Mutation score ≥ threshold on touched modules | `mutation-gate` report, kill-rate per mutant class |
| "This service integration is correct" | Contract test that exercises the actual protocol boundary | PACT / consumer-driven contract output |
| "This system behaves under failure" | Integration or chaos test with fault injection and recovery assertion | Test output from `chaos-*` test suite |
| "This change is safe to ship" | All applicable layers GREEN, zero known flakes on touched tests | CI run URL, branch, commit SHA, passing job list |
| "This defect is fixed" | Failing test that specifically targets the defect → passes after fix | Before/after test output, test name, defect ID |
| "Inter-rater agreement reached" | ≥ 80% pairwise agreement across ≥ 2 raters on the same rubric | Scoring sheet with per-rater columns |

**The hierarchy is not additive by default.** Passing unit tests does not imply
a passing mutation gate. A passing mutation gate does not imply a passing contract
test. Each layer answers a different question. An agent who produces a sign-off
without specifying which layer was exercised has not produced evidence; they have
produced an assertion.

---

## Hard Rules

1. **Never mark a defect closed without a failing → passing test.** The test must
   have been failing on the defective code and passing on the fixed code, in the same
   test run or in two reproducible runs. "I believe the fix addresses the root cause"
   is not closure. A defect is closed when a test says it is closed.

2. **Mutation score below the project threshold means quality is insufficient,
   regardless of line coverage.** A 95% line-coverage module with a 60% mutation kill
   rate has 40% of its mutants surviving undetected. Those surviving mutants are
   untested logic paths. The mutation score is the authoritative quality signal when
   the two metrics conflict.

3. **Flakes must be disclosed, not hidden.** If a test failure is attributable to
   non-determinism (timing, ordering, network, random seed without fixed value), the
   finding is filed as a FLAKE with the flake rate measured over the last N CI runs.
   A flaking test is NOT treated as "green with noise" — it is treated as an
   unreliable sentinel that must be fixed or deleted before it is cited in a
   sign-off.

4. **Coverage numbers without branch coverage are misleading.** Line coverage reports
   the fraction of source lines executed by at least one test. A line may be executed
   without any test asserting on its result. Branch coverage narrows the gap but still
   does not guarantee assertion power. Any sign-off that cites only line coverage must
   note the branch coverage separately; if branch coverage is unavailable, state so
   explicitly.

5. **Inter-rater agreement threshold is ≥ 80% before scoring consensus is declared.**
   When two or more reviewers score the same artifact (test output, QA finding,
   release readiness), pairwise agreement must reach ≥ 80% before the consensus score
   is accepted. When agreement is below 80%, the disagreement is logged as a finding,
   not averaged away.

6. **Self-report is a claim, not evidence.** When an agent says "I ran the tests and
   they pass," that is a self-report. A QA reviewer treats it with the same skepticism
   as any other unverified claim: ask for the test output, the branch, the commit SHA.
   If the output is not producible, the claim is unverified.

7. **A test that does not assert on the behavior under test is not a test; it is
   scaffolding.** Tests that call the function-under-test but do not assert on
   return values, side effects, or exceptions provide zero mutation-killing power.
   Such tests count toward line coverage but not toward quality. When reviewing a
   test, ask: "What mutant would this test kill?" If the answer is none, the test
   is scaffolding.

8. **Green CI on a PR branch does not imply green CI post-merge.** The target branch
   may have diverged. A release-readiness sign-off must cite the CI run on the
   **test-merge commit (the result of merging the PR into the target HEAD —
   GitHub's `refs/pull/N/merge`), the merge-queue result, or the post-merge
   commit on the target branch.** The merge-base commit is the target branch
   BEFORE the PR's changes — it does NOT prove the merged result is green and
   citing it as evidence is a finding.

9. **Regression classification is mandatory before closure.** Every defect is one of:
   behavioral regression (code changed behavior it should preserve), boundary failure
   (code failed at a legal input boundary), integration drift (third-party contract
   changed), flake (non-deterministic), or design gap (spec never covered this case).
   The classification determines the fix category and the regression test that must
   be added. Closing without classification allows the same defect class to recur.

10. **A QA sign-off that omits the mutation kill rate on touched modules is
    incomplete.** The sign-off must state: (a) test pass/fail counts, (b) branch
    coverage delta on touched files, (c) mutation kill rate on touched files, and
    (d) any known flakes in the touched test paths. Missing items must be explicitly
    noted as `NOT MEASURED` — not silently omitted.

11. **Evidence must be reproducible at the time of sign-off.** A sign-off citing a
    local test run that cannot be reproduced from the cited commit SHA is not
    evidence. The CI run URL, branch, and commit SHA form the minimum reproducibility
    anchor.

12. **Raising the coverage gate without improving mutation score is not a quality
    improvement.** If a PR achieves the coverage gate threshold by adding tests that
    execute code without asserting on results, the gate passes but quality has not
    improved. Coverage-gate gaming is a finding at MAJOR severity.

---

## Test Layer Roles

Each layer answers a different question. No layer substitutes for another.

### Unit tests

**Question answered:** Does this function produce the correct output for specific
known inputs?

**What they prove:** Individual function contracts, happy-path behavior, error-path
behavior for explicitly coded inputs, boundary values at the edges of the input
domain.

**What they do not prove:** That the function behaves correctly for ALL inputs
(that is property testing's role), that integrations across module boundaries work
(that is integration testing's role), or that tests with weak assertions would
survive a logic mutation (that is mutation testing's role).

**Artifacts:** Passing test output with visible test names, branch coverage report
per file.

### Property-based tests

**Question answered:** Does this function satisfy an invariant for any input the
generator can construct?

**What they prove:** That invariants hold structurally — monotonicity, idempotency,
round-trip stability, boundary conditions — across a sampled space of inputs, with
shrinking to a minimal failure case when an invariant is violated.

**What they do not prove:** That the integration points around the function work;
that the function is fast enough; that real-world data distributions don't expose
a bias the generator missed.

**Artifacts:** Run log with seed, number of inputs generated, shrunk failure case
(if any), invariant descriptions.

### Mutation tests

**Question answered:** Do the existing tests have enough assertion power to detect
introduced logic errors?

**What they prove:** The kill rate of the test suite against a catalog of
automatically generated code mutations (boundary flips, operator swaps, statement
deletions). A high kill rate means tests would catch many categories of logic error.
A surviving mutant is a logic change the tests cannot see.

**What they do not prove:** That the mutation catalog covers all real-world bug
classes; that a killed mutant means the fix is correct (killing a mutant shows
observability, not correctness of the observable behavior).

**Artifacts:** Kill rate per module, list of surviving mutants by mutant class,
delta vs prior baseline.

### Contract tests

**Question answered:** Does this component honor the protocol boundary agreed with
its collaborators?

**What they prove:** That the consumer's expectations of a provider (API shape,
error codes, field presence) are met, independently of the provider's internal
implementation. Especially critical at integration seams that cross process or
service boundaries.

**What they do not prove:** That the system works end-to-end under real load;
that the provider's side of the contract is correct in isolation.

**Artifacts:** PACT broker output, consumer test pass/fail, provider verification
pass/fail, contract version pinned.

### Integration tests

**Question answered:** Do two or more components work together correctly across
their real (not mocked) interfaces?

**What they prove:** That the integration seam works: data flows, protocol messages
are formatted correctly, error propagation crosses the boundary, state is consistent
on both sides.

**What they do not prove:** System-wide behavior under failure injection, or that
individual components are correct in isolation.

**Artifacts:** Test output with real infrastructure (database, message broker, etc.)
started, IPC messages logged, state verified across both sides.

### Smoke tests

**Question answered:** Is the deployed system alive and minimally functional?

**What they prove:** That the most critical user-facing paths work after a deploy
— not correctness at depth, but basic liveness.

**What they do not prove:** Correctness, performance, edge-case behavior. A passing
smoke suite is not a QA sign-off; it is a deploy-liveness check.

**Artifacts:** HTTP status codes, response shape checks, latency within SLO, health
endpoint returning OK.

---

## Mutation Score Anchoring

Line coverage is a proxy metric. It counts execution, not assertion. A test suite
that executes every line without asserting on any return value will report 100% line
coverage and 0% mutation kill rate. These two facts are not contradictory — they
expose the proxy metric's flaw.

Mutation testing injects small code changes (mutants) and checks whether any
existing test fails. If no test fails on a mutant, the test suite cannot see that
category of logic error. The kill rate — the fraction of mutants killed — is the
authoritative signal of assertion power.

### Why mutation outranks line coverage

| Scenario | Line coverage | Mutation kill rate | What it means |
|----------|-------------|-------------------|---------------|
| All lines hit, no assertions | 100% | 0% | Tests are scaffolding; code is unverified |
| All lines hit, meaningful assertions | 100% | 70% | Tests catch most mutations but 30% survive |
| Not all lines hit, strong assertions | 80% | 85% | Uncovered lines are lower risk than assertion gaps |
| Partial coverage, weak assertions | 80% | 40% | High-risk: coverage gate passes, quality is low |

In case 4, the coverage gate at 80% passes while quality is severely inadequate.
Mutation score at 40% would correctly flag this as failing the quality threshold.

### Framework gate

The framework's `mutation-gate.yml` enforces a kill rate floor on modules nominated
for mutation testing. The floor is defined per project in `.claude/settings.local.json`
and defaults to **>= 80% for critical modules** (security, domain math, financial
logic) — aligned with `core/testing-strategy` §791 — and **>= 70% for general
application code**. A project may set higher thresholds (e.g. 85% critical / 75%
general) but never lower than the parent-skill floor without an Owner-signed ADR
amendment to `core/testing-strategy`.

A QA sign-off for any change touching a nominated module must include the mutation
kill rate delta. A drop in kill rate — even if the absolute rate remains above the
floor — is a finding. Quality debt introduced by a PR must be named in the sign-off;
it may not be silently absorbed by a still-passing gate.

### Surviving mutant classification

When reviewing mutation output, classify surviving mutants:

| Mutant class | Example | Implication |
|---|---|---|
| Boundary flip | `>` → `>=`, `<` → `<=` | Off-by-one bug class uncaught; add boundary tests |
| Operator swap | `+` → `-`, `&&` → `\|\|` | Logic inversion uncaught; add negative-case tests |
| Statement deletion | Entire `if` block removed | Dead-code risk or missing guard; audit the block |
| Return mutation | Return value changed to constant | Return value never asserted; add return-value tests |
| String literal swap | Error message changed | Error paths untested; add error-message-exact-match tests |

A sign-off that lists surviving mutant classes and their test gaps is actionable.
A sign-off that reports only "kill rate = 72%" is not — it does not tell a developer
where to write the missing tests.

---

## WRONG / CORRECT Examples

### Coverage-washing

**WRONG**

```text
QA sign-off: Coverage at 93% — passes threshold. APPROVED.
```

Coverage-washing hides the assertion gap. 93% line coverage with 55% mutation kill
rate means 45% of logic mutations are invisible to the test suite. The sign-off
passes the gate and misrepresents quality.

**CORRECT**

```text
QA sign-off:
- Line coverage: 93% (threshold: 85%) — PASS
- Branch coverage: 81% (threshold: 80%) — PASS
- Mutation kill rate: 55% (threshold: 75%) — FAIL
  Surviving mutants: 11 boundary flips, 7 operator swaps.
  Largest gap: auth/session.py lines 44-67 (no negative-path assertion on token
  expiry boundary).
Verdict: BLOCKED pending mutation gate repair.
```

The correct sign-off names the metric, the threshold, the gap, and where to write
the missing tests.

---

### Coincidental test passage

**WRONG**

A test asserts that a function returns without raising an exception:

```python
def test_compute_fee():
    result = compute_fee(order_value=1000, tier="premium")
    assert result is not None  # passes even if result is 0.0
```

The test passes regardless of whether the fee computation is correct. Any mutation
to the fee formula will survive because the only assertion is `is not None`. This
is coincidental passage — the test runs the code but verifies nothing meaningful.

**CORRECT**

```python
def test_compute_fee_premium_tier():
    # Known fixture: premium fee = 0.15% of order value
    result = compute_fee(order_value=Decimal("1000.00"), tier="premium")
    assert result == Decimal("1.50"), f"Expected 1.50, got {result}"

def test_compute_fee_zero_value_returns_zero():
    result = compute_fee(order_value=Decimal("0"), tier="premium")
    assert result == Decimal("0")

def test_compute_fee_rejects_negative_value():
    with pytest.raises(ValueError, match="order_value must be non-negative"):
        compute_fee(order_value=Decimal("-1"), tier="premium")
```

Three tests, three distinct mutation targets. The happy-path test pins the exact
computed value; the boundary test pins the zero case; the error-path test pins the
rejection behavior. Together they kill boundary-flip, operator-swap, and
return-mutation classes on this function.

---

### Claim-without-evidence sign-off

**WRONG**

```text
Agent output: I ran the tests and confirmed the fix works. The bug with the session
token expiry is resolved. I'm confident this is correct. LGTM.
```

No branch. No commit SHA. No test names. No before/after output. The claim is
self-referential — it is the agent saying the agent verified the agent's own work.
Under adversarial QA framing, this sign-off is indistinguishable from no sign-off.

**CORRECT**

```text
QA sign-off — defect closure: SESSION-EXPIRY-BUG

Defect reproduction (before fix):
  Branch: bugfix/session-expiry — commit d3a8f72
  Run: pytest tests/auth/test_session.py::test_expired_token_rejected -v
  Result: FAILED — AssertionError: expected 401, got 200

Fix applied: auth/session.py line 118 — added expiry check before token comparison.

Regression test (after fix):
  Branch: bugfix/session-expiry — commit 9f2c1ab (fix applied)
  Run: pytest tests/auth/test_session.py::test_expired_token_rejected -v
  Result: PASSED

Mutation kill rate delta on auth/session.py: 71% → 79% (added 3 tests; boundary
flip on expiry comparison now killed).

Verdict: DEFECT CLOSED. Regression test confirmed failing → passing.
```

The correct sign-off gives a reproducible before-state, a named fix location, a
reproducible after-state, and a mutation delta. A reviewer can reproduce every step
from this artifact.

---

## Anti-Patterns

### Green-build-equals-good

A passing CI build means: the tests that exist, on the branch that was tested,
passed. It does not mean:
- The tests are comprehensive.
- The mutation score is acceptable.
- The post-merge state is green.
- No flakes were hiding failures.
- The correct tests were included in the CI job.

The "green build means done" anti-pattern is the root cause of most phantom
sign-offs. Green CI is a necessary condition for a sign-off, not a sufficient one.

### Test-flake tolerance

A flaking test is not "usually green, ignore the noise." A flaking test is a
sentinel that fires randomly — it provides no reliable signal in either direction.
An agent that accepts a flaking test into the sign-off has accepted an unreliable
input into their quality conclusion. The correct disposition is:

- Fix the flake (root-cause the non-determinism and eliminate it), OR
- Delete the test (if the behavior it tests cannot be made deterministic), OR
- Quarantine the test with an explicit `@flaky` annotation + a tracking issue,
  and exclude it from the CI gate until fixed.

A flake is never resolved by re-running until green. Re-run-until-green is the
anti-pattern; it converts a quality sentinel into a retry mechanism.

### Coverage-gate-only (no mutation layer)

Some projects enforce line or branch coverage gates but do not run mutation testing.
This is better than nothing but creates a false ceiling: once the coverage gate
is green, quality feels certified. The certification is incomplete. A coverage-only
gate will not catch assertion-free tests, scaffolding tests, or tests that execute
dead code.

The correct posture: coverage gate as the entry-level floor, mutation gate as the
quality ceiling. A project that cannot yet run mutation testing should record this
as a quality debt item with an explicit severity, not treat the coverage gate as
equivalent to the full quality picture.

### Inter-rater override without justification

When two raters disagree on a QA finding, the correct response is:
1. Measure agreement rate (pairwise, per rubric item).
2. If ≥ 80%: take the majority position.
3. If < 80%: log the disagreement as a finding and escalate to a third rater or to
   the CEO for adjudication.

The anti-pattern: the senior rater overrides the junior rater's score without
documenting the justification. This produces apparent consensus that hides a
systematic disagreement. If the override is correct, documenting it takes thirty
seconds and makes the final score defensible. If the override is incorrect, the
undocumented version will never surface the error.

### Regression-test omission on defect closure

A defect is closed when a test says it is closed (Hard Rule 1). When a defect is
closed without a new regression test, the defect class may recur with no detection
mechanism. The correct pattern: fix the code AND add a regression test that would
have caught the original defect, **in the same commit**. The regression test is
part of the fix, not an optional follow-up. This is consistent with
`core/minimal-change-discipline` Rule 2 (one logical outcome per commit) — fix
+ regression test is ONE outcome, not two.

---

## Acceptance Criteria

A QA review or sign-off produced using this skill is complete when:

- [ ] Every "X is fixed" claim cites a failing → passing test, with test name,
  branch, and commit SHA.
- [ ] Coverage report includes both line coverage and branch coverage; mutation kill
  rate on touched modules is stated or explicitly flagged as `NOT MEASURED`.
- [ ] Any surviving mutants from the mutation gate are classified by mutant class,
  not reported only as an aggregate kill rate.
- [ ] Flakes in the touched test paths are disclosed with measured flake rates, not
  omitted.
- [ ] Inter-rater agreement is calculated and reported where ≥ 2 raters score the
  same artifact; disagreements below the 80% threshold are escalated, not averaged.
- [ ] The CI run cited in the sign-off is on the **test-merge commit
  (`refs/pull/N/merge`), the merge-queue result, or the post-merge commit on
  the target branch** — NOT the PR-branch-only run and NOT the merge-base
  commit (which is the target branch baseline before the PR's changes).
- [ ] Coverage-gate gaming (new tests that increase line coverage without assertion
  power) is explicitly checked: at minimum, one mutation killed per new test added
  should be demonstrable.
- [ ] Regression classification is stated for each closed defect (behavioral
  regression / boundary failure / integration drift / flake / design gap).
- [ ] The sign-off distinguishes which test layer was exercised (unit / property /
  mutation / contract / integration / smoke) for each claim made.
- [ ] For release-readiness assessments: all applicable layers are listed as
  GREEN / YELLOW / RED / NOT MEASURED, not summarized as a single composite.

---

## Related Skills

- `core/testing-strategy` — Test runner configuration, test file conventions, mock
  patterns, CI pipeline structure, and test patterns by module type. Consult for HOW
  to write and organize tests; consult THIS skill for HOW to evaluate and certify them.
- `core/code-review-checklist` — The Staff Code Reviewer's adversarial framing and
  quality-metric rubric (mutation kill rate, coverage delta, flake rate) that governs
  how code-review findings are filed. The evidence requirements in that skill and the
  evidence requirements in this skill are designed to be consistent: a QA sign-off
  that meets this skill's acceptance criteria will satisfy the code-reviewer's
  quality-metric rubric.
