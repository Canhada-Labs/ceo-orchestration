# ADR-024: Hook performance baseline policy (measure-only Sprint 10, gate Sprint 11)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 10 (PLAN-010 Phase 2)
**Related:** ADR-019 (confidence-gate enforcement lifecycle — three-state precedent), ADR-017 SUPERSEDED (pruning measure-then-gate pattern), ADR-014 (hook migration batch policy)

## Context

Sprint 6 migrated all six hooks (`check_agent_spawn`, `audit_log`,
`check_bash_safety`, `check_plan_edit`, `check_read_injection`,
`check_canonical_edit`) onto the Hook Adapter Layer (ADR-008, ADR-014).
We have hook byte-fidelity fixtures and unit tests, but **zero
empirical data on invocation latency**. That gap means:

1. We cannot answer the question "is hook X too slow?" — we can't even
   define "too slow" without a baseline distribution.
2. A future dep bump (`_lib` refactor, Python version change, adapter
   rewrite) could regress per-spawn latency by 2× and we'd notice
   only via user annoyance reports.
3. Any gate we ship today would have a **thin-air threshold** — the
   exact failure mode PLAN-010 debate C1 explicitly called out. The
   DevOps skill's MANTRA ("if CI is advisory forever, CI is a vibe —
   set the conversion date when you add it") reinforces that advisory
   without a transition plan is worse than no CI at all.

## Options considered

### Option A — Ship gate now with a guessed threshold (e.g. 50 ms p99)

Pros: single-PR simplicity; forces "do something" discipline.

Cons:
- **Thin-air threshold.** 50 ms p99 is not derived from any measurement.
  PLAN-010 debate C1 rejects this pattern.
- Ubuntu-latest variance is ±40% on short-running benchmarks. A single
  noisy run would flag a regression that doesn't exist.
- No rollback signal: if the gate false-positives, the Owner must
  hand-edit the YAML to bump the threshold, leaking "vibes tuning"
  into the baseline.

Rejected.

### Option B — Measure forever, never gate

Pros: zero false positives; easy to run; no Owner-facing knobs.

Cons:
- Violates the DevOps skill's MANTRA directly.
- Lessons from ADR-017 / ADR-020 pruning lifecycle: advisory-forever
  creates a data graveyard. Artifacts accumulate in S3, nobody looks
  at them, regressions are discovered weeks late.
- No gate → no pressure on future PRs to care about hook latency.

Rejected.

### Option C (CHOSEN) — Three-state lifecycle: measure → accumulate → gate

Mirrors ADR-019's confidence-gate pattern. States:

- **State 0 (Sprint 10, this sprint)** — advisory profiler runs weekly
  + on `.claude/hooks/**` pushes. Artifact retained 90 days. Summary
  posted to `$GITHUB_STEP_SUMMARY`. No thresholds. No blocking.
- **State 1 (Sprint 11, conditional)** — advisory-with-floor. A
  regression vs. the 3-week rolling median p99 > 2× triggers a
  GitHub Actions warning (`::warning::`), still non-blocking. Owner
  reviews and either acknowledges (noise) or files a perf bug.
- **State 2 (Sprint 12+, conditional)** — blocking gate. Threshold
  = rolling-median × 2× with a 90-day lookback. Fails the workflow.
  Regression PR must either fix the perf cost or land a threshold bump
  with Owner sign-off (same pattern as coverage gate).

## Decision

### 1. Ship State 0 in Sprint 10

`.github/workflows/perf-profile.yml`:
- Triggers: `schedule` (cron Monday noon UTC) + `workflow_dispatch` +
  `push` on `.claude/hooks/**` or `.claude/scripts/hook-profiler.py`.
- Runs `.claude/scripts/hook-profiler.py --samples 1000 --warmup 100`.
- Uploads JSON artifact `hook-profile-<run_id>` (retention 90 days).
- Posts Markdown summary to step summary via the profiler's built-in
  `GITHUB_STEP_SUMMARY` emission.
- **Never fails the workflow** (debate C1 enforcement).

`docs/performance-baseline.md` captures:
- The methodology (N, warm-up, percentile method, isolation).
- The first local baseline (reproducible).
- A **pending** table for CI weekly runs W1–W3.

### 2. State-0 → State-1 transition criterion

> **Transition to State 1 after three consecutive weekly CI runs show
> p99 stable within 20% variance per hook.**

Concretely: for each of the six hooks, compute
`max(p99_w1, p99_w2, p99_w3) / min(p99_w1, p99_w2, p99_w3) ≤ 1.2`.
If all six satisfy this, the baseline is considered "observable" and
Sprint 11 writes an ADR-025 (or amends this one) that adds the
advisory floor.

If a hook fails the 20%-variance test, Sprint 11 holds State 0 for
that hook and investigates the source of variance (runner flakiness,
fixture instability, Python version drift).

### 3. Threshold placement (State 2, later)

When State 2 ships:
- Threshold = rolling-median-p99(90-day) × 2.0 for each hook.
- The 2× multiplier is the conventional perf-regression sensitivity
  used by Chromium and Firefox perf bots. It absorbs ubuntu-latest's
  ±40% noise while still catching real 2-orders-of-magnitude regressions.
- The threshold is computed from CI history, not guessed. The perf-
  profile workflow's artifact retention (90 days) is the source of
  truth.

### 4. Rollback signal

Revert State 1 → State 0 (or State 2 → State 1) if:
- **>1 false-positive regression flag per month.** Either the threshold
  is too tight or the variance model is wrong.
- **Any incident where perf-profile blocks a legitimate emergency fix.**
  Same escape-hatch principle as ADR-019: fixing prod is never gated
  by a perf assertion.

### 5. Explicit non-goals for Sprint 10

- No multi-session harness. The profiler measures single-process cold
  + warm, not "first hook after fresh session" latency. Sprint 12+
  if signal demands.
- No p99.9 or higher percentiles. N=900 warm samples supports p99
  (nearest-rank rank 891) with reasonable fidelity; p99.9 would need
  N=10,000 and is not actionable.
- No cross-Python-version matrix. Runner uses Python 3.12 (matches
  validate.yml). Sprint 11 may add 3.9 + 3.12 matrix if we suspect
  Python-version-dependent regressions.
- No flamegraphs / cProfile integration. Separate tool; out of scope.

## Consequences

### Positive

- Zero thin-air thresholds shipped in Sprint 10.
- Weekly cadence matches Dependabot window — a bad dep bump surfaces
  in perf data within 7 days.
- Three-state pattern is legible (matches ADR-019). Sprint 11/12 ADRs
  have a named predecessor to supersede.
- Owner can run the profiler locally (`--home /tmp/x --samples 1000`)
  and reproduce CI numbers modulo ubuntu-variance.
- 90-day artifact retention = 12 weekly data points = enough for any
  reasonable regression-detection algorithm Sprint 11 might choose.

### Negative

- **No regression signal for the first three weeks.** A regression
  landing on 2026-04-15 is invisible until W3 completes on ~2026-05-04.
  Tradeoff: false-positive risk of early gating > false-negative risk
  of late detection, given how infrequent hook edits are (adapter
  migration is done; ADR-014 batch policy gates new hook work).
- **Transition criterion is conservative.** A hook with 21% variance
  across three weeks blocks the whole framework from State 1 — some
  hooks may never stabilize enough on ubuntu-latest's shared hypervisor.
  Sprint 11 may need to carve out per-hook State-0 exceptions or
  switch to a self-hosted runner for perf-only.
- **Artifact storage cost.** 90-day retention × 6 hooks × JSON ~= 1 KB/run.
  Negligible (< 1 MB/year).

### Neutral

- The profiler script itself stays in `.claude/scripts/` and is
  Owner-runnable; CI is the canonical baseline source but not the
  only one.
- No new Owner-facing env vars. Unlike ADR-019 there's no "enforce"
  switch — the workflow's behaviour is entirely driven by its YAML.

## Blast radius

**L2** — one new workflow, one new script (~250 LOC), one test file
(~200 LOC, 14 tests), one doc, this ADR. No existing files modified.
No env-var knobs added.

**Reversibility:** HIGH. Delete `.github/workflows/perf-profile.yml`,
delete `.claude/scripts/hook-profiler.py`, delete the doc. The hooks
themselves are untouched.

## Transition timeline

| State | Date (target) | Trigger |
|-------|---------------|---------|
| 0 (advisory)   | Sprint 10 ship (2026-04-14) | This ADR |
| 0 → 1 decision | 2026-05-04 (3 weekly runs complete) | Variance test per §2 |
| 1 (advisory-with-floor) | Sprint 11 IFF variance test passes | New ADR-025 amendment |
| 1 → 2 decision | 30 days of clean W-over-W data | Owner sign-off |
| 2 (blocking gate) | Sprint 12+ IFF stable | New ADR amendment |

No schedule is committed; all dates are *earliest possible*.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |

## References

- PLAN-010 Phase 2 — hook profiler spec
- PLAN-010/debate/round-1/consensus.md §C1 (no thin-air thresholds),
  §C7 (profiler isolation mandatory)
- ADR-019 — confidence-gate three-state lifecycle (this ADR's pattern parent)
- ADR-017 SUPERSEDED — pruning measure-then-gate precedent
- `.claude/scripts/hook-profiler.py` — the measurement tool
- `.github/workflows/perf-profile.yml` — State 0 workflow
- `docs/performance-baseline.md` — methodology + baseline numbers
- `.claude/skills/core/devops-ci-cd/SKILL.md` MANTRA — "if CI is
  advisory forever, CI is a vibe"

## Enforcement commit

`f9cc2e36f207` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
