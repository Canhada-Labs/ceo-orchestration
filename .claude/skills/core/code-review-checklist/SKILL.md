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
inspired_by:
  - source: msitarzewski/agency-agents/testing/testing-reality-checker.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-evidence-collector.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-test-results-analyzer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-tool-evaluator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 3
risk_class: low
stack: []
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 3}
activation_triggers:
  - {event: plan-opened}
  - {event: help-me-invoked, regex: "(?i)code.?review|cr"}
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

The reviewer publishes one document per review using the structure below.
The document lives in the PR description or alongside the plan as
`PLAN-NNN/review-YYYY-MM-DD.md`.

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

Both passes default to Opus 4.8 per ADR-052. Pass 2 MAY dispatch to
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

## Default-BLOCKED Posture (verdict-flip discipline)

The reviewer's verdict starts at `BLOCKED`. Approval requires
flipping it. Approval is never the default state of the document
that has not yet been read.

This rule exists because the inverse posture — start at `APPROVED`,
flip to `BLOCKED` only when something obvious shows up — produced
~35% phantom-approval rate across pre-PLAN-058 review cycles
(Round-23 burn-down inventory). When the floor of "no findings yet"
maps to APPROVED, every unread file path silently votes for the
change. When the floor maps to BLOCKED, every unread file path
demands evidence.

### The flip rule

Three conditions, all required, before flipping `BLOCKED → APPROVED`:

1. **Every domain checklist applicable to the diff has been walked
   end-to-end.** Not skimmed. Not "the relevant ones." Every box that
   the diff intersects gets a tick or a finding. An un-walked box is a
   missing finding, not an implicit pass.

2. **At least one finding has been recorded** — even at NIT severity.
   A diff non-trivial enough to merit review has at least one thing
   the reviewer noticed. "Zero findings" on a non-trivial diff is a
   review-quality red flag and triggers a self-restart (re-read the
   diff colder).

3. **The CI run cited in the PR has been opened and the failing-job
   list confirmed empty.** Not "CI was green when I started." The
   actual current state of the actual current branch.

Missing any of the three → verdict stays `BLOCKED`. The PR description
is then updated with the specific missing condition, not a vague "needs
more work" note.

### `APPROVED WITH CONDITIONS` — the middle band

`APPROVED WITH CONDITIONS` is a verdict, not a softer approval. It
exists for residual risk that is acceptable *with a named control*.
Every condition cites:

- The control: feature flag, canary stage, follow-up ticket, post-
  deploy monitor, rollback script
- The owner: a person, not a team
- The trigger that closes the condition: a deploy gate, a CI hook, a
  date

A condition that reads "fix in a follow-up" with no control, no owner,
or no trigger is not a condition — it is the reviewer rationalizing.
Such a condition fails the verdict and the review returns to `BLOCKED`.

### Phantom-approval auto-trigger

If the reviewer notices any of the following self-statements while
drafting the verdict, the verdict snaps back to `BLOCKED` for one more
self-check pass:

- "I think this is fine"
- "Looks reasonable"
- "Probably correct"
- "Author has done this kind of thing before"
- "Small change, low risk"

Each of those is fluency-credulous language. Evidence-based language —
"line X handles Y because Z is enforced at A" — is required to clear
the auto-trigger.

## Evidence Requirement (file:line + reproduction artifact)

Every finding above NIT severity carries two attachments: a precise
location and a reproduction artifact. "I think the input handler is
broken" is not a finding. It is a hunch, and hunches do not make it
into the review document.

### What counts as evidence

| Finding type           | Required artifact                                                                    |
|------------------------|--------------------------------------------------------------------------------------|
| Behavioral regression  | Failing test output (full traceback) OR a runnable repro snippet pasted into the PR  |
| Missing test coverage  | Coverage report excerpt showing the line range with 0% AND a proposed test signature |
| Spec drift             | Quoted spec.md line + quoted implementation line, side-by-side                       |
| Performance regression | Before/after benchmark with sample size n≥10, p95 + p99 reported, fixed seed cited   |
| Security finding       | Attack input + path through the code that fails to neutralize it                     |
| Type-safety finding    | TypeScript / mypy / pyright output line + the offending source line                  |
| Dependency finding     | Lockfile diff + advisory ID (CVE / GHSA) where applicable                            |
| Config finding         | Workflow file path + line + the asserted-vs-observed behavior                        |

The artifact is part of the review document. Comments like "see CI"
or "you can find it in the logs" do not satisfy the requirement —
the reviewer copies the relevant excerpt into the finding so the
author and any later auditor can read the review without leaving it.

### CORRECT vs WRONG — finding evidence

```markdown
# CORRECT — Finding 3 (CRITICAL)
File: src/auth/session.ts:118
Issue: Session token compared with non-constant-time `===`
Repro:
  Input: token differing in byte 0 vs token differing in byte 31
  Observed: timing delta ~120ns / ~3800ns (n=1000, taskset -c 0)
  Expected: ≤2× timing variance under timing-safe comparison
Fix: Use `crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b))`
     Cross-check `core/security-and-auth` §Timing-Safe Comparisons.

# WRONG — Finding 3
The session comparison looks unsafe. Should probably use a
timing-safe equality check. Auth code is sensitive so let's be
careful here.
```

The wrong version offers a hunch and a vibe. The correct version
offers a location, a reproduction, an observation, an expectation,
and a fix that is auditable on its own.

### Reproduction-budget escape hatch

When reproducing a finding would consume more than 30 minutes of
diagnostic time (e.g., a flake that surfaces 1-in-200 runs), the
reviewer DOES NOT skip the finding and DOES NOT downgrade it. The
reviewer files it with severity `MAJOR` minimum, attaches the
partial signal that prompted the suspicion (one stack trace, one
log excerpt, one observed metric), and notes `repro_pending: true`.
The author then carries the reproduction load. The verdict stays
`BLOCKED` until the artifact lands.

### Visual-proof carve-out for UI / dashboard / report changes

Changes that affect rendered output — dashboards, generated reports,
CLI banners with structured output — additionally carry a before/after
artifact: a screenshot, a terminal transcript, or a saved-HTML diff.
A reviewer who cannot describe what the change LOOKS LIKE has not
reviewed the change. "The CSS diff is small" is not a substitute for
opening the page.

## Quality-Metric Findings (treat numbers as findings)

Coverage delta, mutation kill-rate, flake-rate, p95 latency drift,
binary-size delta, dependency-tree depth — these are not background
telemetry. When they move adversely on a PR, they are findings, with
severity, location, and fix-required just like any code finding.

### The quality-metric rubric

Each metric has an empirical threshold. When a PR crosses the threshold,
a finding is filed with the indicated severity:

| Metric                            | Threshold for finding                                          | Default severity |
|-----------------------------------|----------------------------------------------------------------|------------------|
| Line coverage delta               | ≥1.0 pp drop on touched files                                  | MAJOR            |
| Branch coverage delta             | ≥2.0 pp drop on touched files                                  | MAJOR            |
| Mutation kill-rate                | <85% on touched-file mutants OR ≥3 pp drop                     | CRITICAL         |
| Flake-rate (last 50 CI runs)      | ≥2% on a test added or modified by the PR                      | CRITICAL         |
| p95 latency on benchmarked path   | ≥10% regression with n≥10, fixed seed, same hardware class     | MAJOR            |
| Binary / bundle size delta        | ≥5% increase OR ≥250 KiB absolute, whichever is smaller        | MAJOR            |
| Dependency tree depth delta       | ≥+5 transitive deps OR introduces a non-MIT/Apache/BSD license | MAJOR            |
| New `try/except: pass` constructs | ≥1 introduction without an inline rationale comment            | MAJOR            |
| New `console.log` / `print` debug | ≥1 in non-test, non-CLI source                                 | MINOR            |
| New `TODO` / `FIXME` without ID   | ≥1 new TODO not linked to a tracking ticket                    | MINOR            |

The thresholds are defaults. A project's `.claude/settings.local.json`
or per-skill override may tighten them, never loosen them without an
ADR. "We don't track mutation kill-rate" is itself a finding with
severity MAJOR — the absence of the metric is a quality-process gap.

### Trend over snapshot

A single absolute value is less load-bearing than a trend. If the PR
holds the metric flat at a value that is already adverse (e.g.,
coverage frozen at 71% while the project floor is 80%), the finding
fires regardless of delta. The frozen-bad state is the finding.

The reviewer pulls the trend from the last 10 closed PRs on the same
file paths where possible. A directional move that the reviewer
flags only at the extreme threshold misses the leading indicator.

### CORRECT vs WRONG — quality-metric finding

```markdown
# CORRECT — Finding 7 (CRITICAL)
Metric: mutation kill-rate on _lib/audit_emit.py
Observed: 78.4% (this PR) vs 89.1% (last 10 PRs touching this file)
Threshold: <85% on touched-file mutants
Cause: 4 new branches added in `_normalize_action_label`; only
       happy-path covered. Mutants surviving:
         - boundary off-by-one in slice index
         - identity vs equality on action-name compare
         - early-return on empty string short-circuits validator
Fix: Add 4 negative-path tests; re-run `make mutation` and confirm
     ≥85% kill rate before re-review.

# WRONG — Finding 7
Mutation testing showed some surviving mutants. Should add more
tests.
```

The wrong version is impossible to act on without re-doing the
reviewer's work. The correct version names the file, the threshold,
the trend, the surviving mutants, and the closing condition.

### Metric-finding interaction with verdict

Quality-metric findings count toward the verdict at their assigned
severity. A clean code review with a `mutation kill-rate < 85%`
CRITICAL finding does NOT round to `APPROVED` — the metric finding
holds the verdict at `BLOCKED` until the fix lands. This is the
mechanism that prevents "the code looks fine" from rationalizing
around adverse trend signals.

## Tool-Introduction Scoring (libraries, services, vendors)

When a PR introduces a new runtime dependency, replaces an existing
one, or adopts a new SaaS / managed service, the reviewer applies a
weighted scoring matrix BEFORE evaluating the integration code. The
choice itself is the load-bearing decision; the integration is
downstream.

### The 7-axis matrix

Each axis scores 0-10. Weights sum to 1.00. A weighted score below
6.5 maps to a `BLOCKED` verdict on the tool choice independent of
the integration code's quality.

| Axis                          | Weight | What scores 10                                                                  | What scores 0                                                                       |
|-------------------------------|--------|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Security posture              | 0.20   | Active CVE response, signed releases, SBOM published, security contact listed   | Unsigned releases, no CVE history because nobody's looked, no contact               |
| Maintenance signal            | 0.18   | ≥1 commit / week from ≥2 maintainers across last 12 months; issues closed monthly | Last commit ≥18 months ago; sole maintainer; issue tracker abandoned                |
| Ecosystem fit                 | 0.15   | Used by ≥3 projects already in the framework's stack with no friction reports   | Single-project deployment; stack mismatch; transitive licensing conflict            |
| Lock-in / exit cost           | 0.12   | Open data format, runs locally, contracts terminable on 30-day notice           | Proprietary data format with no export, vendor-required cloud, 1-year contract lock |
| Operational complexity        | 0.10   | One-line install; zero config defaults; logs to stdout; no daemons              | Multi-host install; 200-line YAML config; custom log format; required sidecar       |
| Total cost of integration     | 0.10   | Replaces existing manual work with quantified ROI; fits inside current budget   | Adds new line item without offsetting savings; usage-based billing without cap      |
| Documentation completeness    | 0.15   | Public API docs, runnable quickstart, troubleshooting page, changelog up-to-date | "Docs coming soon"; only blog posts; changelog is the git log                       |

Weighted score = Σ (axis_score × axis_weight). A score in
[6.5, 7.5) is `APPROVED WITH CONDITIONS`; ≥7.5 is `APPROVED`.

### When the matrix applies

The matrix runs when the PR diff includes any of:

- A new entry in `package.json`, `requirements.txt`, `Cargo.toml`,
  `go.mod`, or equivalent
- A version bump that changes the major version of an existing entry
- A new `Dockerfile FROM` base image
- A new external service URL in config (a SaaS endpoint, a managed
  database, a third-party auth provider)
- A new GitHub Action `uses:` reference at a tag the project has
  not previously pinned
- A new MCP server registration or a new external tool wired into a
  hook

Bug-fix-version bumps and patch-version bumps inside an already-
approved tool DO NOT re-trigger the matrix. They run through the
universal checklist as ordinary code changes.

### CORRECT vs WRONG — tool-introduction finding

```markdown
# CORRECT — Tool-introduction review for `fast-json-stringify@5.x`
Replaces: `JSON.stringify` on hot-path serializer

Axis scores (0-10):
- Security posture: 7  (signed npm releases; one CVE in 2024 with 11-day patch; no SBOM)
- Maintenance: 9       (weekly commits, 4 maintainers, 92% issue close rate over 12mo)
- Ecosystem fit: 8     (used by Fastify; matches our Node 22 line; MIT license)
- Lock-in: 9           (drop-in API; revert via 1-line code change; no data format change)
- Operational: 10      (zero config; no daemons; pure library)
- Cost: 8              (replaces existing serializer; ~12% p95 throughput improvement on benchmark)
- Documentation: 8     (full API docs, benchmark page, changelog current)

Weighted score: 8.36 → APPROVED
Conditions: pin to exact patch version; subscribe to repo security advisories.

# WRONG — Tool-introduction review
Adding fast-json-stringify, it's faster than the built-in. Looks
well-maintained, lots of users. Approving.
```

The wrong version makes a recommendation without an audit trail; if
the library is later compromised or abandoned, the review record
gives no signal about WHAT the reviewer evaluated. The correct
version is auditable and re-runnable next year when the same library
needs to be re-evaluated for a major-version bump.

### Why it sits inside code review

Tool selection is sometimes treated as a separate "RFC" exercise
that lives outside the PR review. The framework rejects that split:
the PR that introduces the tool IS the moment the choice becomes
load-bearing. Routing the matrix anywhere else loses the gate. A
PR that adds a dependency without a matrix score is the same shape
of finding as a PR that adds an unauthenticated endpoint — a missing
mandatory artifact, severity MAJOR minimum, verdict `BLOCKED` until
the matrix lands inline in the review document.
