# ADR-037: Chaos + load testing methodology (thread-PR, process-nightly, weapon-locked)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 10)
**Related:** ADR-005 (fail-open hook contract), ADR-008 (hook adapter
layer), ADR-014 (hook migration batch policy), ADR-019 (confidence-gate
three-state lifecycle — this ADR's pattern parent), ADR-021 (e2e
integration harness), ADR-024 (perf baseline three-state lifecycle)

## Context

Through Phase 9 of PLAN-011 the framework has:

- 856 unit + integration tests (Sprint 10 baseline).
- Byte-identity fixtures for 6 active hooks.
- An advisory perf profiler (ADR-024) that measures median-of-3
  single-process p50/p95/p99.
- An e2e harness (ADR-021) that invokes hooks via subprocess but only
  serially.

**What is still missing:**

1. **Concurrency signal.** The advisory profiler runs one invocation at
   a time. We have zero data on what happens when 100 concurrent
   `decide()` calls race on `audit-log.jsonl` (our only shared writeable
   resource). GIL contention, `fcntl.flock` unfairness, and the
   `rotate_if_needed` rename race are all theoretical; Sprint 11 needs
   them measured.
2. **Failure-injection signal.** ADR-005 mandates that hooks NEVER
   block the user session on infrastructure bugs. We have the rule but
   no test that verifies the framework continues to return
   `{"decision":"allow"}` when a hook exits 99, spits garbage on stdout,
   hangs past its timeout, etc. A silent regression of the fail-open
   path would be catastrophic: the user's entire session would grind
   to a halt.
3. **No chaos weapon.** Phase 10 must ship a chaos-injection utility
   (`chaos-inject.py`) that can produce those failure modes on demand.
   That utility is **weaponizable** — an attacker with shell access
   could point it at a real audit log and DOS the framework. It must
   be locked down before it lives on disk.

PLAN-011 debate round 1 consensus §H15 specified the measurement
split (thread-based PR / process-based nightly) and §M4 the lockdown
contract. This ADR captures both so future authors do not drift.

## Decision drivers

- **Fast-signal on PR, real-signal nightly.** Thread-based tests catch
  GIL + filelock contention in ~5s; process-based tests catch issues
  threads mask (separate Python processes with cold JIT state, real
  IPC semantics on the flock) but cost ~30-60s. The former belongs on
  every PR; the latter belongs on a weekly cadence. (Precedent:
  ADR-024's weekly perf-profile runs.)
- **Weapon lockdown.** Any utility that can produce failure modes must
  refuse to run outside a clearly-identifiable test context. A
  single-gate check (e.g. "CEO_CHAOS_ALLOWED=1") is bypassable by
  `export`. We require a **3-gate AND** (env flag + parent process
  `pytest` + `cwd` inside `tests/chaos/`) so each independent failure
  makes abuse harder.
- **Advisory forever is a vibe** (ADR-024 §Option B discussion). The
  chaos workflow MUST have a transition criterion baked into the ADR,
  not deferred to "maybe Sprint 12."
- **Fail-open contract is a behaviour assertion.** The chaos tests
  assert the FRAMEWORK's observable output (`{"decision":"allow"}`
  written to stdout), not implementation details. If we switch
  adapters, hooks, or runtime, the contract survives as long as the
  observable behaviour does.

## Options considered

### Option A — Process-only chaos, no load tests

Pros: one codepath; realistic.
Cons: 30-60s suite per hook blocks PR turnaround; thread-contention
signal is lost (process isolation hides GIL/filelock bugs that only
surface at ~100 concurrent callers inside one Python process — exactly
the scenario a deep-research subagent could produce).
Rejected.

### Option B — Thread-only chaos, skip processes

Pros: fast; runs every PR.
Cons: threads share `fcntl.flock` file descriptors via the same PID —
the lock is a no-op across threads. The load test would green while
real cross-process contention would still explode in prod. Rejected.

### Option C (CHOSEN) — Split: thread load on PR, process chaos nightly

- **PR path (load):** `tests/load/` runs via pytest on every
  `.claude/hooks/**` push. Uses `threading.Thread`; 100 concurrent
  `subprocess.run` calls against each hook. Measures wall-clock p99
  of the batch + asserts zero deadlocks + asserts audit-log JSONL
  line integrity (every line parses).
- **Weekly path (chaos):** `tests/chaos/` runs via
  `.github/workflows/chaos.yml` on a Monday 03:00 UTC cron +
  workflow_dispatch. Uses `multiprocessing.Process` semantics (each
  hook invocation is already a fresh subprocess; the chaos utility
  injects exit-99/garbage-stdout/sleep-then-kill failures). Asserts
  fail-open contract + audit breadcrumb presence.

### Option D — Implement nothing, rely on production telemetry

Rejected. The framework has no production telemetry pipeline, and the
fail-open contract is safety-critical (a silent regression would be
invisible to the Owner and disastrous to adopters).

## Decision

### 1. Ship State 0 in Sprint 11 (Phase 10)

**Load suite** (`tests/load/test_governance_100_parallel.py`):
- 8+ pytest tests. One test per active hook (6) + two all-hooks-racing
  integration tests.
- `--warmup=10` (discard first 10 samples) then `--measure=100`
  recorded; median-of-3 across full run matches hook-profiler v1.
- Assertions: wall-clock ≤ 30s (no deadlock), every audit-log line
  parses as valid JSONL (no torn writes), p99 < 500ms per call,
  survival rate 100% (every `decide()` call returns a valid Decision).
- Runs in `validate.yml` alongside existing test job (no new workflow).

**Chaos suite** (`tests/chaos/test_hook_failure_injection.py`):
- 8+ parametrized pytest tests covering 6 hooks × 5 failure modes.
- Each test spawns the framework-hook subprocess, overrides the inner
  hook binary with a chaos-wrapper, and asserts the framework's
  observable output matches the fail-open contract.
- Runs in `chaos.yml` weekly; never on PR path.

**Chaos utility** (`.claude/scripts/chaos-inject.py`):
- 3-gate lockdown at module entry:
  1. `CEO_CHAOS_ALLOWED=1` set? else exit 2.
  2. Parent process command contains `pytest` (read via `ps -o command=
     -p <ppid>` on macOS, `/proc/<ppid>/cmdline` on Linux)? else exit 2.
  3. `os.getcwd()` contains `"tests/chaos/"` substring? else exit 2.
- ALL three must be true. One false → exit 2 with ERROR.
- If all three open: produces a wrapper script that implements one of
  5 failure modes (exit1 / exit99 / garbage_stdout / stderr_spam /
  timeout). Emits a `chaos_injected` breadcrumb to stderr.
- Unit-tested via `test_chaos_inject_lockdown.py` (each gate tested
  independently + combined positive case).

### 2. Advisory Sprint 11 → enforcing Sprint 12 IFF stable

| State | Trigger | Effect |
|-------|---------|--------|
| **0 (advisory, Sprint 11)** | This ADR | Load tests on every PR (non-failing); chaos tests weekly (non-failing) |
| **1 (soft-gate, Sprint 12 conditional)** | 4 consecutive weekly green chaos runs | Chaos runs emit `::warning::` on fail; PR load still advisory |
| **2 (blocking, Sprint 13+ conditional)** | 8 additional weekly runs with zero fail-open contract violations | Chaos failure fails workflow; load p99 floor at 3× rolling median |

Rollback:
- State 1 → 0 if >1 false-positive per month.
- State 2 → 1 if any incident where chaos blocks a legitimate emergency
  fix (same escape-hatch as ADR-019/024).

### 3. chaos.yml kill-switch and disable flag

- `CEO_SOTA_DISABLE=1` env var → workflow exits 0 with notice. Matches
  the disable pattern established for other Sprint-11 weekly jobs.
- Paths-filter: only runs on changes to `.claude/hooks/**`,
  `.claude/scripts/chaos-inject.py`, `.github/workflows/chaos.yml`,
  `tests/chaos/**`, or `tests/load/**`. Conserves Actions minutes.
- Artifact retention: 30 days (not 90 — chaos data compresses
  poorly and we only need recent runs for State 0 → 1 decision).

### 4. Non-goals for Sprint 11

- No fuzzing. Chaos injects five *named* failure modes, not random
  byte streams. Fuzzing is separate work (Sprint 12+ if demand).
- No Windows coverage. fcntl.flock is POSIX-only (ADR-002); chaos
  assumes POSIX.
- No network chaos. The framework hooks do not make network calls;
  injecting network partitions has no test target.
- No multi-repo or multi-Claude-Code-session chaos. Single-repo
  single-session already covers the attack surface PLAN-011 debate
  C5 identified.

### 5. Fail-open behaviour assertions (precise)

For every (hook, failure_mode) pair the chaos test asserts:

1. **Framework stdout** — the final line contains
   `{"decision": "allow", ...}` (or the equivalent normalized-event
   structure per ADR-014).
2. **Survival rate** — Claude Code receives a parseable JSON decision
   envelope, not an empty stdout or a partial line.
3. **Audit breadcrumb** — for `audit_log` failures specifically, a line
   matching `^\[.*\]` is appended to `audit-log.errors` (best-effort
   breadcrumb per ADR-005 §Safety).
4. **Audit log integrity** — if `audit-log.jsonl` exists, every line
   parses as valid JSON. No partial/torn writes.

## Consequences

### Positive

- Zero thin-air thresholds. Load tests assert **zero deadlock** (hard)
  + **p99 < 500ms** (empirical soft floor, 10× max observed perf-
  baseline p99 <61ms per ADR-024). Chaos tests assert **fail-open
  contract** (hard — existing ADR-005 requirement, no new threshold).
- Weekly cadence matches perf-profile.yml; two weekly advisory jobs
  share Actions quota and reviewer attention (same Monday morning).
- Chaos-inject.py is **Owner-runnable** inside `tests/chaos/` but
  produces an immediate exit-2 from any other context. Test-authors
  get confidence; shell-access attackers get exit 2.
- Three-state lifecycle matches ADR-019 / ADR-024 precedent. Sprint
  12/13 authors have a named predecessor to supersede.

### Negative

- **No chaos signal for the first 4 weeks.** Same tradeoff as ADR-024
  §Consequences: false-positive risk of early gating > false-negative
  risk of late detection. The first chaos run may surface a real bug
  that's been latent since ADR-008; Owner must triage.
- **Chaos weapon lives in the repo.** Anyone with read access can see
  the script. Lockdown depends on the 3-gate AND holding; if any gate
  is bypassable (e.g. a new OS where `/proc/<ppid>/cmdline` format
  changes, breaking Linux parent-process detection) the weapon
  becomes usable. Owner must re-audit the lockdown any time the gate
  implementation changes.
- **Parent-process detection is heuristic.** `pytest` in `ps` output
  catches direct test invocation but would miss exotic launchers
  (tox, nox, conftest-driven subprocess). We accept that false-
  negative rate (unusable chaos utility in esoteric setups) as the
  price of a strict lockdown.

### Neutral

- Adds `tests/load/` and `tests/chaos/` as new top-level test dirs.
  Existing `tests/integration/` unaffected; pytest discovery handles
  new dirs automatically.
- No new Owner-facing env vars beyond `CEO_CHAOS_ALLOWED` and
  `CEO_SOTA_DISABLE`; both default-off.

## Blast radius

**L2** — two new test dirs (~400 LOC total), one utility script (~200
LOC), one workflow (~80 LOC), one test file for the utility (~150 LOC),
one ADR (this), one report doc. Existing hooks, existing `_lib`, and
existing workflows untouched.

**Reversibility:** HIGH. Delete `tests/load/`, `tests/chaos/`,
`.claude/scripts/chaos-inject.py`, `.github/workflows/chaos.yml`,
`.claude/scripts/tests/test_chaos_inject_lockdown.py`, this ADR, and
`docs/chaos-report.md`. The hooks themselves are untouched.

## Transition timeline (earliest possible — no dates committed)

| State | Target window | Trigger |
|-------|---------------|---------|
| 0 (advisory)   | Sprint 11 ship | This ADR |
| 0 → 1 decision | 4 weeks post-ship | 4 consecutive clean chaos runs on main |
| 1 (soft-gate)  | Sprint 12 IFF clean | ADR-038 (future) amendment |
| 1 → 2 decision | 8 more weeks clean | Owner sign-off |
| 2 (blocking)   | Sprint 13+ IFF stable | ADR-038 (future) amendment |

## Flip-criteria table (State transitions, precise)

| From | To | Measurement window | Pass criterion | Fail criterion | Action on fail |
|------|----|--------------------|-----------------|----------------|----------------|
| 0 | 1 | 4 weekly runs | 4/4 runs green (0 fail-open contract violations, 0 torn audit-log lines, 0 chaos-inject script errors) | Any run red | Hold State 0; investigate; document in chaos-report.md |
| 1 | 2 | 8 weekly runs past State 1 ship | 8/8 green + zero false-positive ::warning:: flags | >1 false-positive per month OR any contract violation | Hold State 1; owner re-audits |
| 2 | 1 (rollback) | Any month | 0 production-blocking incidents | ≥1 emergency-fix blocked by chaos gate | Revert workflow YAML; keep tests |
| 1 | 0 (rollback) | Any month | 0 false-positive ::warning:: flags | >1 false-positive per month | Revert chaos.yml `::warning::` emission |

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| 2026-04-15 | 0 (advisory) | 1 (enforcing) | `.claude/scripts/red-team-corpus/v1/fixtures.jsonl.sha256` (frozen corpus 67 fixtures, SHA `a5a62a03a84ef206`) | PLAN-014 Phase D.3 | CEO (automated via PLAN-014 D.1-D.4) |

## References

- PLAN-011 Phase 10 — load + chaos testing deliverables
- PLAN-011 debate round 1 §H15 (thread-PR / process-nightly split)
- PLAN-011 debate round 1 §M4 (chaos-inject 3-gate lockdown)
- PLAN-011 debate round 1 §S4 (CEO_SOTA_DISABLE kill-switch)
- PLAN-011 debate round 1 §S5 (behavior assertions per test)
- ADR-005 — fail-open hook contract (this ADR's constraint source)
- ADR-019 — confidence-gate three-state lifecycle (this ADR's pattern parent)
- ADR-024 — perf baseline three-state lifecycle (sibling)
- `.claude/skills/core/chaos-and-resilience/SKILL.md` — methodology skill
- `.claude/skills/core/testing-strategy/SKILL.md` MANTRA — "Thread on PR. Process at night. Weapon locked."

## Enforcement commit

`d677d1e97329` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
