---
name: core-minimal-change-discipline
description: Operational doctrine for scoping code changes to the minimum necessary
  to fulfill a task in {{PROJECT_NAME}}. Prevents scope creep, accidental regressions,
  and sentinel violations by requiring agents to reason explicitly about change
  boundaries before touching any file. Use when authoring, reviewing, or planning
  any code edit — especially when an existing codebase section is "close to" the
  task but not explicitly authorized for modification.
owner: Minimal-Change Engineer (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-minimal-change-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 3
risk_class: low
stack: []
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 3}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)minimal|scope|focus"}
---

# Minimal-Change Discipline

Before writing a single line, an agent operating under this skill answers
one question: **"What is the smallest diff that fully satisfies the stated
intent — and nothing more?"** If the answer requires touching a file not
named in the plan or ticket, that touch requires explicit authorization or
must be dropped. If the answer involves renaming, reformatting, or
restructuring code that already works, that work is deferred to a
dedicated refactoring task. There is no such thing as "while I'm here" —
that phrase is the canonical signal that scope creep is about to happen.
Every byte changed is a byte that can introduce a regression. Minimize the
bytes; minimize the risk.

## What This Skill Is (and isn't)

This skill is the cognitive operating manual for **scope discipline**:
the practice of holding a firm change boundary throughout a task and
actively resisting the pull to improve adjacent code that was not asked
for. It applies to every phase — planning, editing, reviewing, and
committing.

This skill is **not** a refactoring prohibition. Refactoring is valuable.
This skill says: refactoring is a separate task with its own plan entry,
its own review, and its own commit. When the current task is "fix bug X",
the correct action is to fix bug X and open a follow-up ticket for the
cleanup you noticed. Bundling the cleanup into the bug fix makes the diff
harder to review, harder to bisect, and harder to revert.

This skill is **not** a code-quality veto. If you notice a quality issue
adjacent to your task, file it. Do not fix it silently in the same commit.
Silence is how unreviewed changes reach production.

This skill **pairs with** `core/code-review-checklist`, which governs how
reviewers evaluate the scope of a change post-hoc. This skill governs
how authors scope the change pre-hoc. Together they form a closed loop:
authors minimize; reviewers verify minimality.

This skill **pairs with** `core/incremental-refactoring`, which provides
the discipline for executing safe refactoring tasks once they are properly
scoped and planned. When minimal-change discipline defers a cleanup, the
cleanup goes into incremental-refactoring protocol — not into a drawer.

## The Minimal-Footprint Invariant

**Definition:** A change has minimal footprint if and only if removing any
single edited line would cause the task to remain unsatisfied (the bug
returns, the feature does not work, the test fails).

**Corollary:** If a line can be removed without breaking the task
objective, that line should not be in the diff. No exceptions.

**Measuring footprint** — apply these three checks before committing:

| Check | Question | Pass condition |
|-------|----------|---------------|
| F-1: File count | How many files does this diff touch? | Only files the plan or ticket names, plus files directly imported/tested by them |
| F-2: Line justification | For each changed line, can you state in one sentence why that specific line must change? | Yes for every line |
| F-3: Revert safety | If this entire commit is reverted, is the codebase in the same state as before the task started (minus the fix)? | Yes — no collateral state carried in |

If any check fails, trim the diff until it passes or escalate to split
the task into smaller authorized units.

**Blast radius** is the formal measure of F-1 extended to runtime: how
many production execution paths are altered by this change? A one-line
fix in a utility called from 40 call sites has a large blast radius even
though the diff is small. High blast radius triggers an automatic
requirement for broader test coverage before merge, regardless of diff
size. See `core/code-review-checklist` §Blast Radius Assessment.

**Scope envelope** is the set of files and symbols that the current plan
or ticket explicitly authorizes for modification. Everything outside the
scope envelope is off-limits unless explicit re-authorization is obtained
and logged (a plan amendment, a comment from the owner, or a ticket
update). "I inferred authorization" is not authorization.

## Hard Rules

**Rule 1 — Assess before you edit.**
Before opening any file for editing, write down (in a code comment, a
scratch note, or a plan sub-step) the exact list of files you intend to
touch and why each one is necessary. If you cannot justify a file in one
sentence, do not touch it.

**Rule 2 — One logical outcome per commit.**
A commit captures one coherent unit of work: a bug fix (with its regression
test, per `core/evidence-based-qa` Hard Rule 1 — fix + test is ONE outcome,
not two), a feature increment (with its targeted tests), a doc update, or
a self-contained refactor. Never bundle two unrelated outcomes. If the bug
fix and an opportunistic refactoring are entangled, untangle them: commit
the minimal fix + its regression test first, then commit the refactoring
separately, or defer the refactoring entirely. Mixed-outcome commits are
impossible to bisect and opaque to review. Bug-fix commits without their
regression test are a violation of `core/evidence-based-qa` and a defect-
closure half-measure — they are NOT permitted by minimal-change either.

**Rule 3 — Canonical-guarded files require plan authorization.**
Files protected by `check_canonical_edit.py` (SKILL.md files, hook
sources, sentinel archives) require an explicit plan entry or Owner
ceremony to edit. Discovering that a canonical file "also needs updating"
during an unrelated task is not authorization. Stop. File a plan amendment
or a follow-up task. Do not edit canonical files opportunistically.

**Rule 4 — No drive-by reformatting.**
Whitespace normalization, import reordering, trailing-comma insertion,
and similar formatting changes must not appear in a diff whose stated
purpose is something else. If formatting genuinely matters, run the
formatter in a dedicated commit with message `style: run formatter`.
A mixed formatting + logic diff is un-reviewable — the reviewer cannot
tell which whitespace change is mechanical and which is semantically
significant.

**Rule 5 — No speculative helper extraction.**
Do not extract a helper function that "might be useful later." Extract
helpers when a second caller exists or when the function is being added
to a public API. Premature extraction increases the blast radius of the
current change (now the helper can be called from anywhere) and adds
surface area for future bugs. Defer extraction to a dedicated refactoring
task.

**Rule 6 — Test changes are scoped too.**
Adding tests is not a license to restructure the test suite. If the task
requires adding two tests for bug X, add two tests. Do not rename
existing test functions, reorder test files, or convert test fixtures to a
new pattern unless the task explicitly calls for it. Test refactoring has
the same discipline as production refactoring.

**Rule 7 — Raise before bundling.**
When you identify a genuine problem adjacent to your task — a latent bug,
an unsafe pattern, a missing test — do not fix it silently. Raise it: add
a `TODO:` comment with a reference to a tracking ticket, or create the
ticket immediately and link it. Then complete your scoped task. The latent
problem is now tracked and will be addressed in its own authorized context.

**Rule 8 — Authorization decays.**
A plan or ticket that authorized "update module A" does not implicitly
authorize "update module A and all modules that import A." Each additional
file touched beyond the explicit scope requires incremental authorization.
Do not extrapolate scope from the stated goal; ask.

## Scope Assessment Protocol

Run this protocol in order before making any edit. It takes 2-3 minutes
and saves hours of review and revert cycles.

**Step 1 — Read the authorization source.**
Identify the exact plan entry, ticket, or Owner directive that governs
this task. Quote it verbatim (internally or in a comment). Note what it
says and — critically — what it does not say.

**Step 2 — Enumerate candidate files.**
List every file you might touch. Include test files, documentation, and
configuration. Do not filter yet.

**Step 3 — Apply the authorization test to each file.**
For each candidate file, ask: "Does the authorization source name this
file explicitly, or does it name a symbol in this file?" If neither,
the file is out of scope unless you can trace a direct functional
dependency (the named file imports this one and the change propagates
necessarily).

**Step 4 — Check the scope envelope.**
Files that pass Step 3 are inside the scope envelope. All others are
outside. Files outside the scope envelope require a written re-authorization
before you touch them (a plan amendment, a comment from the Owner, or a
follow-up ticket if you defer).

**Step 5 — Estimate blast radius.**
For each in-scope file, note how many callers or importers it has. Flag
any file with more than 10 direct callers for heightened test coverage
before merge.

**Step 6 — Write the minimal diff first.**
Draft what the change looks like if you touch only the authorized files
and change only the authorized symbols. Can it work? Usually yes. If not,
identify the minimum additional file that must be touched and obtain
authorization for it before proceeding.

**Step 7 — Apply the revert-safety check.**
After editing, mentally simulate reverting. Does the codebase return to
its pre-task state? If collateral changes exist (reformatting, unrelated
cleanups), strip them from this commit.

## WRONG / CORRECT Examples

### Example 1 — Drive-by variable rename

**Context:** Task is to fix a null-pointer bug in `user_session.py:42`.

**WRONG:**
```python
# In user_session.py — the bug fix (authorized)
if session is None:
    raise SessionExpiredError()

# ... 80 lines later, still in user_session.py (NOT authorized)
# "While I was here I renamed uid to user_id throughout the file
# for consistency with the rest of the codebase."
def get_user(user_id: str) -> User:  # was: def get_user(uid: str)
    ...
```

**WRONG because:** The rename is a separate concern. It changes call sites
across the codebase (blast radius explosion), adds noise to the bug-fix
review, and cannot be reverted independently. The reviewer now cannot tell
whether the rename caused any behavioral change.

**CORRECT:**
```python
# user_session.py — only the null check
if session is None:
    raise SessionExpiredError()
# File committed. Follow-up ticket #1234 opened for uid→user_id rename.
```

---

### Example 2 — Speculative helper extraction

**Context:** Task is to add a new API endpoint `POST /payments/retry`.

**WRONG:**
```python
# payments/handlers.py
def retry_payment(payment_id: str) -> PaymentResult:
    ...
    # "I noticed I'm doing similar validation in three places,
    # let me extract a helper while I'm adding this endpoint."
    validated = _validate_payment_common(payment_id, check_idempotency=True)
    ...

def _validate_payment_common(payment_id: str, check_idempotency: bool) -> Payment:
    # New helper — now callable from 40+ other places in the codebase
    ...
```

**WRONG because:** The helper is not required for the new endpoint to
work. It adds a new callable symbol to the module's public surface,
increases blast radius for future changes, and muddles the PR scope.

**CORRECT:**
```python
# payments/handlers.py
def retry_payment(payment_id: str) -> PaymentResult:
    ...
    # Inline validation — defer extraction to PLAN-refactor-payments-validation
    payment = db.get_payment(payment_id)
    if payment is None:
        raise PaymentNotFoundError(payment_id)
    if payment.status not in RETRIABLE_STATUSES:
        raise PaymentNotRetriableError(payment_id)
    ...
```

---

### Example 3 — Opportunistic test restructuring

**Context:** Task is to add two regression tests for a rate-limiter bug.

**WRONG:**
```python
# tests/test_rate_limiter.py
# "While adding the two new tests I reorganized the fixture
# setup to use pytest.fixture(scope='module') for performance."

@pytest.fixture(scope="module")  # changed from scope="function"
def rate_limiter():
    return RateLimiter(max_requests=10, window_seconds=60)

# ... 12 existing tests now share state across test runs (bug introduced)

def test_rate_limit_regression_001():
    ...
def test_rate_limit_regression_002():
    ...
```

**WRONG because:** The fixture scope change affects all 12 existing tests
(test isolation broken, latent state-sharing bug), is not authorized by
the task, and entangles a regression risk with the two simple new tests.

**CORRECT:**
```python
# tests/test_rate_limiter.py — add only the two authorized tests
# (existing fixtures unchanged)

def test_rate_limit_regression_001(rate_limiter):
    """Regression: burst of N+1 requests must not pass when N is the cap."""
    ...

def test_rate_limit_regression_002(rate_limiter):
    """Regression: window reset must not carry over state from prior window."""
    ...
```

---

### Example 4 — "Necessary" documentation update that isn't

**Context:** Task is to change the default timeout from 30s to 60s in
the HTTP client configuration.

**WRONG:**
```
Diff touches:
  - http_client.py         ✅ authorized (the timeout constant)
  - config_schema.py       ✅ authorized (the schema default value)
  - README.md              ❓ "updated the docs to reflect the new timeout"
  - CHANGELOG.md           ❓ "added a CHANGELOG entry"
  - docs/configuration.md  ❓ "updated the configuration reference"
```

**WRONG because:** Documentation updates are a separate concern. The plan
entry said "change the default timeout." README, CHANGELOG, and docs
updates require their own authorized plan step. Bundling them into the
code change makes it impossible to merge the code change without
co-merging the doc change, which may be in a different review stream.

**CORRECT:**
```
Diff touches:
  - http_client.py         ✅ the constant
  - config_schema.py       ✅ the schema default

Documentation update deferred to PLAN-074 Wave 2 §docs step, or
filed as follow-up ticket #1235 per the plan's doc-update policy.
```

---

### Example 5 — Canonical-guarded file touched without ceremony

**Context:** Agent is augmenting a skill and notices that a second skill's
`SKILL.md` has a broken cross-reference.

**WRONG:**
```
Agent edits:
  - .claude/skills/core/observability-and-ops/SKILL.md    ← authorized (current task)
  - .claude/skills/core/security-and-auth/SKILL.md        ← NOT authorized
    (check_canonical_edit.py blocks this; agent bypasses by noting
     "the fix is trivial, only one line")
```

**WRONG because:** Canonical files require ceremony (plan entry + Owner
GPG sentinel). "The fix is trivial" is never authorization. The hook
exists precisely because individual judgment about "trivial" is unreliable.

**CORRECT:**
```
Agent edits:
  - .claude/skills/core/observability-and-ops/SKILL.md    ← current task

Agent notes broken cross-reference in security-and-auth/SKILL.md.
Files plan amendment to address it in the next authorized wave.
Does NOT touch security-and-auth/SKILL.md.
```

## Anti-Patterns

### "While I'm here..."

**Pattern:** The phrase "while I'm here" appears in the agent's reasoning
or commit message, followed by a change that was not in the scope
assessment.

**Why it fails:** It is the leading indicator of scope creep. The phrase
signals that the agent is making a judgment call to expand scope without
authorization. That judgment is unreliable — it is made in the middle of
a task, under the cognitive load of the primary change, without the
adversarial scrutiny a separate review would provide.

**Recovery:** When you catch yourself thinking "while I'm here," stop.
Finish the authorized task. Open a follow-up ticket for the adjacent
improvement. Commit only the authorized change.

---

### Blast radius blindness

**Pattern:** Agent edits a utility function called from many places,
treating it as a "small change" because the diff is 3 lines. Does not
check the blast radius or expand the test surface.

**Why it fails:** Diff size and blast radius are independent dimensions.
A 3-line change to a function called from 50 places has the same blast
radius as rewriting 50 callers. Small diff ≠ small risk. The change
touches every execution path through the utility, including paths not
covered by existing tests.

**Recovery:** Run Step 5 of the Scope Assessment Protocol (blast radius
check) before every edit. If blast radius > 10 callers, add tests for
the top-N execution paths before committing. Flag the change for a
broader review.

---

### Cosmetic bundling

**Pattern:** A logic change is committed together with unrelated
formatting changes — reindentation, trailing whitespace removal, import
reordering. The reviewer sees a 200-line diff, of which 185 lines are
whitespace and 15 are the actual change.

**Why it fails:** The reviewer cannot distinguish the semantic change from
the cosmetic noise without line-by-line inspection of every whitespace
diff. The real change can hide in the noise. Reviewers, under time
pressure, tend to skim noisy diffs — which is exactly when bugs slip
through.

**Recovery:** Run a separate formatting commit first (or last, after the
logic commit). Never mix in the same commit. If the formatter ran
automatically, verify its output is a no-op on the logic and commit it
separately with message `style: auto-format`.

---

### Authorization by inference

**Pattern:** The plan says "fix the authentication flow." Agent infers
this authorizes changes to the session store, the cookie configuration,
the CSRF token logic, the email verification handler, and the OAuth
callback. None of these were named explicitly.

**Why it fails:** Inferred authorization is not authorization. "Fix the
authentication flow" scopes only the files and symbols that are directly
required to fix the stated defect. Everything else requires explicit
naming. The more ambiguous the plan entry, the tighter the scope
interpretation must be — ambiguity is a signal to ask, not to expand.

**Recovery:** When the plan entry is ambiguous, ask for a scope
clarification before starting. If the task is already in progress and
you realize the scope is larger than stated, stop and file a plan
amendment for the additional files. Do not proceed on inference.

---

### Follow-up deferred silently

**Pattern:** Agent notices a latent bug adjacent to the task. Does not fix
it (good) but also does not file a ticket or add a `TODO:` comment. The
observation is lost.

**Why it fails:** The observation is now nowhere. It will resurface in
production or not at all. The agent has the context to file a good ticket
right now, at the lowest possible cost. Waiting until later means
reconstructing the context from scratch.

**Recovery:** Rule 7 is explicit: raise before you move on. A `TODO:
(ticket #NNN) — latent null-pointer if X happens` in a comment is the
minimum. Opening the ticket and linking it is better. The latent problem
is now trackable.

## Acceptance Criteria

A reviewer applying this skill checks the following. All must pass before
the change is approved on scope grounds (quality gates in
`core/code-review-checklist` apply separately).

**AC-1: File list matches authorization.**
Every file in the diff is either named in the plan/ticket or is a
direct functional dependency of a named file, with the dependency
traceable in one step.

**AC-2: No drive-by changes visible.**
No formatting-only hunks, no renamed symbols unrelated to the task, no
extracted helpers that have only one caller, no restructured test
fixtures.

**AC-3: Each changed line has a traceable reason.**
The reviewer can look at any changed line and understand why that specific
line had to change to satisfy the task. Lines that cannot be explained are
scope creep.

**AC-4: Canonical-guarded files have ceremony evidence.**
Any edit to a path covered by `check_canonical_edit.py` is accompanied
by a signed sentinel or plan amendment reference in the commit message
or PR description.

**AC-5: Blast radius is declared.**
For any change to a symbol with more than 10 callers, the PR description
names the blast radius and references the test coverage added to address
it. If blast radius is ≤ 10, no declaration needed.

**AC-6: Follow-ups are filed, not bundled.**
If the author mentions adjacent improvements they considered but deferred,
those improvements have a ticket number or a `TODO:` comment with a
tracking reference. "I noticed X but decided not to fix it here" without
a follow-up ticket is a scope-hygiene warning.

## Related Skills

- `core/code-review-checklist` — The reviewer counterpart to this skill.
  Where minimal-change-discipline governs authoring scope, the code-review
  checklist governs reviewer evaluation of scope compliance (blast radius
  assessment, regression risk scoring, severity classification). The two
  skills together form the closed loop.

- `core/incremental-refactoring` — The authorized home for cleanups and
  structural improvements deferred by this skill. When minimal-change
  discipline says "defer the rename," incremental-refactoring provides
  the protocol for doing the rename safely and in its own reviewed context.

- `core/git-workflow-discipline` — Governs commit hygiene, branch naming,
  and commit message conventions. Minimal-change discipline determines
  *what* goes into a commit; git-workflow-discipline determines *how* the
  commit is structured and communicated.

- `core/architecture-decisions` — When a scope assessment reveals that the
  task cannot be completed without a cross-cutting change (e.g., a new
  interface must be introduced), the cross-cutting decision escalates to
  an ADR rather than being buried in the task diff. Minimal-change
  discipline is the trigger; architecture-decisions is the resolution path.
