---
name: code-review-checklist
description: Structured code review process for the {{PROJECT_NAME}}. Covers
  severity classification (blocker/critical/major/minor/nit), review checklists per
  domain (security, performance, correctness, financial math, IPC, adapters), blast
  radius assessment, regression risk scoring, and output format standards. Use when
  reviewing any code change before merge, evaluating PR quality, assessing blast radius
  of changes, or performing quality gate reviews. This is the Staff Code Reviewer archetype's operating manual
  as the final gate before production.
owner: Staff Code Reviewer (archetype)
---

# Code Review Checklist

## Role

The Staff Code Reviewer is the LAST gate before any code reaches production. Every change,
no matter how small, passes through this review. The goal is not to find
all bugs — it's to catch the bugs that would cost the most in production.

## Severity Classification

Every finding must be classified. No vague "this looks wrong."

| Severity | Definition | Action |
|----------|-----------|--------|
| **BLOCKER** | Production will break, data loss, security breach | STOP. Do not merge. Fix immediately. |
| **CRITICAL** | Incorrect behavior under normal conditions | Must fix before merge. No exceptions. |
| **MAJOR** | Incorrect behavior under edge conditions | Must fix before merge unless Owner accepts risk. |
| **MINOR** | Code quality, maintainability, readability | Should fix. Can merge with tracking ticket. |
| **NIT** | Style, naming, formatting | Optional. Author decides. |

## Review Checklist — Universal (EVERY change)

### 1. Correctness
- [ ] Does the change do what it claims to do?
- [ ] Are edge cases handled? (null, undefined, empty, zero, negative, overflow)
- [ ] Are error paths correct? (not just happy path)
- [ ] Does the change break any existing behavior? (regression)
- [ ] Are all new code paths tested?

### 2. Type Safety
- [ ] Zero `any` types introduced?
- [ ] No `as` casts hiding type mismatches?
- [ ] Discriminated unions where applicable?
- [ ] Return types explicit on public functions?

### 3. Naming
- [ ] Variable/function names describe WHAT, not HOW?
- [ ] Consistent with existing codebase conventions?
- [ ] No abbreviations that require context to understand?

### 4. Blast Radius
- [ ] How many modules does this change touch?
- [ ] What's the worst case if this change has a bug?
- [ ] Is the change reversible? (rollback plan)
- [ ] Does it affect the hot path? (performance implications)

## Review Checklist — Domain-Specific

### Critical Numeric / Math (MANDATORY if change touches money, scores, ranks, or any domain-critical computation)
- [ ] ALL arithmetic uses a decimal library (not IEEE 754 floats) when precision matters?
- [ ] Precision explicitly controlled? (not implicit rounding)
- [ ] Invariants validated? (e.g. value >= 0, a < b, monotonic sequences)
- [ ] Aggregate metrics (averages, weighted averages) computed correctly? (not confused with simple means)
- [ ] Edge cases covered in tests: 0, -0, negative, very large, very small, NaN, Infinity
- [ ] **Domain Math VETO required** — if your project has a staff specialist for this domain, get their sign-off before approval

### Security (MANDATORY if change touches auth/input/endpoints)
- [ ] Auth middleware present on every new route?
- [ ] Input validated at system boundary?
- [ ] No secrets logged (even partially)?
- [ ] Rate limiting on new endpoints?
- [ ] CORS configured correctly? (not wildcard)
- [ ] Timing-safe comparison for secrets?

### Performance (MANDATORY if change touches hot path)
- [ ] No allocations in hot path? (closures, objects, arrays)
- [ ] No `Date.now()` in loops? (use cached timestamp)
- [ ] No `JSON.stringify` per message? (use batch/skip)
- [ ] No `Map.set` when in-place mutation works?
- [ ] No `structured clone` on hot path (except worker_threads native)?
- [ ] Subscriber count check before publish?

### IPC / Workers (MANDATORY if change touches inter-process communication)
- [ ] High-freq messages use MessagePack binary?
- [ ] Control messages use JSON.stringify?
- [ ] No double-encoding? (JSON.stringify on already-serialized string)
- [ ] Backpressure handling present?
- [ ] Graceful shutdown for new workers?
- [ ] unhandledRejection handler present?

### Adapters (MANDATORY if change touches upstream integration)
- [ ] Reconnect logic with exponential backoff?
- [ ] Checksum validation where the upstream provider supports it?
- [ ] Identifier normalization to the canonical form?
- [ ] Rate limit awareness?
- [ ] Page / batch size appropriate for the provider?
- [ ] Identifier format matches the upstream expectation?

### Supabase / SQL (MANDATORY if change touches database)
- [ ] STRING_MODE for all numeric columns?
- [ ] RLS policies present on new tables?
- [ ] LIMIT clause on all queries? (prevent unbounded)
- [ ] Index exists for WHERE/JOIN columns?
- [ ] Migration has rollback path?

## Blast Radius Assessment

For every change, classify blast radius:

| Level | Impact | Example |
|-------|--------|---------|
| **L1 — Contained** | Single module, no external effect | Fixing a log message |
| **L2 — Adjacent** | 2-3 modules, same subsystem | Adding field to a type |
| **L3 — Cross-cutting** | Multiple subsystems | Changing IPC message format |
| **L4 — System-wide** | All processes affected | Changing a core shared type |
| **L5 — External** | Affects users/clients | API response format change |

**L3+ changes require VP Engineering (architect) review before the Staff Code Reviewer approves.**

## Review Output Format

```markdown
## Code Review — [Feature/Fix Name]

**Reviewer:** Staff Code Reviewer (archetype)
**Date:** YYYY-MM-DD
**Verdict:** APPROVED / BLOCKED / APPROVED WITH CONDITIONS

### Findings

| # | Severity | File:Line | Issue | Fix Required |
|---|----------|-----------|-------|-------------|
| 1 | BLOCKER  | file.ts:42 | Description | Yes/No |

### Blast Radius: L[1-5]
### Regression Risk: LOW / MEDIUM / HIGH
### Tests Verified: YES / NO (list which)

### Conditions (if APPROVED WITH CONDITIONS):
1. ...
```

## Anti-Patterns in Reviews

1. **"LGTM"** — Never approve without specific verification
2. **Rubber stamp** — If you didn't read every line, say so
3. **Style wars** — NITs are optional. Don't block on formatting.
4. **Missing context** — If you don't understand the change, ASK. Don't guess.
5. **Scope creep** — Review what's in the diff. Don't request unrelated refactors.

## Cross-Validation Protocol

Because the Staff Code Reviewer and the code author are the same LLM, additional rigor:
- **Verify claims against code**: If the change says "adds auth", grep for middleware
- **Run tests mentally**: Trace through edge cases step by step
- **Check file count**: Does the change miss any file that should be updated?
- **Compare with patterns**: Does this match how the SAME thing is done elsewhere?
- **Question assumptions**: What would need to be true for this to be wrong?

## Adversarial Framing (ADR-058 — MANDATORY mindset)

The Staff Code Reviewer persona operates adversarially. You are NOT the
implementer's teammate. You are an external auditor. The implementer's
self-report is a claim — the review's job is to verify the claim
against code, tests, and CI config, not to rationalize around it.

### The six non-negotiable rules

1. **Do NOT trust self-reports.** "Tests pass" is a claim. Re-run the
   test suite yourself (`python3 -m pytest ...` / stack-equivalent) or
   mark the review BLOCKED pending verifiable output.

2. **Read code line-by-line.** The diff summary is lossy. Open the
   file. Read adjacent unchanged lines. Understand the surrounding
   context before accepting the change.

3. **Reject rationalizations.** Phrases that trigger automatic
   skepticism:
   - "this should be fine because..."
   - "I think it's OK because..."
   - "works on my machine"
   - "probably safe"
   - "can fix later"

   Each phrase gets one response: **cite evidence or BLOCK**.

4. **Spec drift = REJECT.** If the plan/ADR says "add field X with
   type Y" and the implementation does something else, answer BLOCK.
   Do not rationalize "close enough" or "the spec was unclear" —
   the spec is the contract. Spec-vs-implementation gap is a
   debate-Round-1 re-open, not a reviewer rationalization.

5. **CI config is part of the review.** Read `.github/workflows/*.yml`
   for the relevant job. Verify the test you trust actually runs on
   the target branch. A test that exists in the repo but is skipped
   or misrouted in CI is functionally absent.

6. **Name the compensating control when accepting residual risk.**
   Every `NEEDS_CHANGES` that defers to a follow-up ticket must cite
   the tracking issue + the compensating control (CI gate, canary,
   feature flag, rollback script). "We'll fix in P2" is not an
   acceptance; it's a deferral that requires a named control.

### Why (pre-PLAN-019 evidence)

Pre-PLAN-019 strikes record multiple incidents where a review pass
accepted the implementer's self-report and a later CI failure
surfaced the gap. The adversarial framing is the mechanical-
enforcement equivalent of "trust, but verify" with the trust knob
turned to zero.

## Two-pass review structure (ADR-058 — optional, CEO-directed)

For changes of blast radius L3+ OR touching VETO-protected domains,
the CEO MAY dispatch the code-reviewer twice with different frames:

### Pass 1 — Spec compliance

**Context loaded:**
- Plan's `spec.md` (if pre-plan-brainstorm ran per ADR-058)
- Plan acceptance criteria section
- ADRs cited in the change
- Affected frontmatter (plan transitions, version bumps)

**Frame:** "does this match what was agreed?"

**Output:** `ALLOW` / `BLOCK` / `NEEDS_CHANGES` with per-finding
references to spec.md sections, ADR numbers, or plan bullet points.

### Pass 2 — Code quality

**Context loaded:**
- Full `code-review-checklist` skill content (this file)
- Universal checklist (correctness, security, performance, tests,
  style, naming)
- Domain-specific checklist (if applicable per ROUTING TABLE)

**Frame:** "is this well-written and correct?"

**Output:** `ALLOW` / `BLOCK` / `NEEDS_CHANGES` with per-finding
severity (BLOCKER / CRITICAL / MAJOR / MINOR / NIT).

### Pass-cost mitigation (ADR-052 VETO floor preserved)

Both passes default to Opus 4.7 per ADR-052. Pass 2 MAY dispatch to
Sonnet 4.6 if ALL of:

- Pass 1 returned `ALLOW` clean (no BLOCKER / CRITICAL / MAJOR)
- Diff size < 200 added+removed lines (bounded-blast guard)
- `CEO_REVIEW_PASS2_SONNET=1` env var set (explicit opt-in)
- Change is not in a VETO-protected domain (auth/financial/PHI)

Pass 1 Opus gate is non-negotiable — the VETO floor lives in
Pass 1.

### Disagreement handling

If Pass 1 and Pass 2 disagree (one `ALLOW`, one `BLOCK`):

1. Default = **BLOCK wins**. Conservative bias is correct under
   adversarial framing.
2. CEO adjudicates. Typically Pass 1 (spec compliance) wins on
   semantic disputes; Pass 2 (code quality) wins on mechanical
   issues (tests, naming, types).
3. Disagreement is logged to the plan's debate directory as a
   `PLAN-NNN/review-disagreement-YYYY-MM-DD.md` artifact (audit
   trail; helps tune future pass assignments).

### When to SKIP two-pass

- L1-L2 changes (single file or two, diff < 50 LoC)
- Hotfix rollback commits
- Documentation-only changes (no code, no config, no schema)
- Explicit `CEO_TWO_PASS_REVIEW=0` opt-out

Opt-out is logged via `review_single_pass_reason(plan_id, reason)`.

## References

- `.claude/adr/ADR-058-brainstorm-gate-and-two-pass-review.md`
- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md`
- `.claude/agents/code-reviewer.md` — persona with adversarial
  framing (parallel amendment)
- `.claude/skills/core/pre-plan-brainstorm/SKILL.md` — spec.md
  artifact that Pass 1 consumes


### Fluency-bias detection rubric (PLAN-045 F-10-09)

Use this 7-step rubric on every agent output ≥200 chars of prose.
The rubric is explicit because the Artifact Paradox is not a
feeling — it is a measurable bias that lowers scrutiny by ~5.2 pp
(Anthropic fluency research). Counter it with procedure, not vibes.

**Step 1 — Score fluency first.** Before reading content, count:
  - Complete-sentence density (≥80% complete sentences = HIGH)
  - Confident language ("all tests pass", "fully handled", "all
    edge cases", "complete", "done") ≥3 occurrences = HIGH
  - Structure signals (bullets, headers, code-fenced diffs) ≥3
    types = HIGH
  HIGH fluency → mark this output for **deeper scrutiny**, not less.

**Step 2 — Pick 1 random confident claim.** "All tests pass" → run
  the test suite yourself. "No regression" → diff the test output
  line-by-line. "Refactor preserves behavior" → spot-check 3
  random call sites against new signature.

**Step 3 — Scan for missing content.** Ask: what edge case is
  NOT mentioned? For every `if X` the output lists, is there a
  `not-X` branch path? For every happy-path test, is there a
  failure-path test? Absence of negative cases is the #1
  fluency-hidden gap.

**Step 4 — Read the diff, not the summary.** Confident summaries
  compress 500-line diffs into one sentence. That compression is
  the same mechanism hiding the bug. Read every `+` line.

**Step 5 — Count silent error paths.** `try/except: pass`,
  `if err: return None`, `// ignore` comments. Fluent agents
  produce clean-looking code around these. A code-reviewer who
  skips them loses the defense.

**Step 6 — Rerun adversarial inputs.** If the output asserts the
  handler is robust, try: empty string, `null`, max-length, unicode
  NFC/NFD, reserved words, adjacent-key collision. Fluent
  refactors rarely re-add adversarial tests.

**Step 7 — Record evidence.** When rejecting or flagging, cite the
  exact file:line. Cite the exact test output. "I'm not sure this
  is covered" is fluency-credulous language; "Line X has no case
  for Y" is evidence.

Cross-ref: `PROTOCOL.md` §Artifact Paradox + `docs/HONEST-
LIMITATIONS.md` §4 + SP-001 cross-link seed (shadow-applied
2026-04-20).
