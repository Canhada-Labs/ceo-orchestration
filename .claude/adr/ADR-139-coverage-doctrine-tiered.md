---
id: ADR-139
title: Tiered coverage doctrine — subprocess capture + per-module Tier-1 gate
status: ACCEPTED
proposed_at: 2026-05-23
proposing_session: S157
related_plans: [PLAN-112, PLAN-093, PLAN-019]
related_adrs: [ADR-002, ADR-115]
risk_tier: B
debate_required: true
vote_trigger:
  # ADR-095 doctrine: event/data-volume gate — NO calendar dates
  # Promotion to ACCEPTED requires ALL of:
  # (1) Tier-1 per-module gate measured green (≥86% line coverage) for ≥2
  #     consecutive CI runs on main branch
  # (2) Repo floor (--fail-under=67) also green on the same runs
  # (3) Completed Tier-B debate round with zero VETO
  trigger_type: event_and_data_volume
  tier1_green_consecutive_runs_min: 2
  repo_floor_green: true
  debate_round_required: true
accepted_at: 2026-05-28
accepting_session: S177
authorization: PLAN-117 WS-B sentinel `.claude/plans/PLAN-117/architect/round-4/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
debate_round_satisfied: S177 Wave-A round (qa-architect + security-engineer + performance-engineer -> unanimous ADJUST_PROCEED, 0 VETO)
---

# ADR-139 — Tiered coverage doctrine (subprocess capture + Tier-1 per-module gate)

**Status:** ACCEPTED (S177, 2026-05-28)

**Enforcement commit:** `f719182` (S157 coverage.yml subprocess capture + Tier-1 gate + parse-coverage.py --tier1 mode; CI follow-ups `7d7cfe0` / `2127f0d` / `90c2ee7` / `4a8ebdc`)

**Decision drivers:**
- The repo-wide line-coverage gate has been dishonest since Session 33: it was
  dropped from 86% → 78% as a "post-hardening temporary state" (DYN-TEST-1) and
  then went RED at ~67.66% measured in-process.
- Root cause is a **measurement artifact, not a test-quality regression**: the
  6 governance hooks are exercised via `subprocess.run([sys.executable, hook])`
  (42 test files), so an in-process `coverage run` cannot follow the subprocess
  and under-counts every hook (e.g. `check_read_injection.py` measured 0% line
  despite a 100%-passing dedicated suite).
- A single repo-wide percentage hides per-module reality: some modules are
  genuinely well-tested (≥93%) while one large hook (`check_agent_spawn.py`) has
  real gaps concentrated in fail-open defensive `except` branches.

## Context

`PLAN-112` (framework closure audit, S152) surfaced finding A8: the `Coverage`
workflow was red and the gate had silently slid from its 86% origin to 78%, then
below. `S156` proved (PoC) that writing a `coverage.process_startup()` `.pth`
into a HOME-independent `site-packages` and running with `COVERAGE_PROCESS_START`
+ `parallel = True` + `coverage combine` captures the subprocess hook runs and
lifts the measured numbers to their honest values. The local macOS loop is
blocked because the system `site-packages` is read-only and the user-site is
relocated by `TestEnvContext`'s HOME rewrite; the capture therefore validates on
CI (writable ubuntu site-packages) and via a writable interpreter locally.

Subprocess-captured baseline (full hooks+scripts suite, S157):

| module | line% (capture) | gate |
|---|---|---|
| `check_bash_safety.py` | ~93% | enforcing |
| `check_read_injection.py` | ~98% | enforcing |
| `check_canonical_edit.py` | ~91% | enforcing |
| `check_output_secrets.py` | ~90% | enforcing |
| `audit_log.py` | ~87% | enforcing |
| `check_agent_spawn.py` | ~84% | **advisory** (uplift owner: future plan) |

## Decision drivers

1. Coverage gates must reflect reality, not measurement artifacts.
2. Lowering a gate must never be silent.
3. A coverage-uplift campaign is multi-session; the gate must be able to enforce
   the parts that are ready without waiting for the slowest module.

## Decision

1. **Subprocess capture is the canonical measurement.** `coverage.yml` writes a
   `coverage.process_startup()` `.pth` into the runner's `site-packages`, exports
   `COVERAGE_PROCESS_START=.coveragerc`, runs the hook + script suites with
   `parallel = True`, then `coverage combine`. `.coveragerc` declares
   `relative_files = True` + `[paths]` aliasing so throwaway hook copies built
   under pytest tmp dirs fold back onto the canonical source tree.

2. **Tier-1 per-module enforcing gate.** A NEW `parse-coverage.py --tier1-modules
   '<list>' --tier1-min 86` step reads `coverage.json` `files[].summary.
   percent_covered` and fails if ANY listed Tier-1 module is below 86%. The
   enforcing Tier-1 list is exactly the modules **measured ≥86%** at ship time:
   `check_bash_safety.py`, `check_read_injection.py`, `check_canonical_edit.py`,
   `check_output_secrets.py`, `audit_log.py`. Kill-switch:
   `CEO_TIER1_COVERAGE_ENFORCING=0` (advisory).

3. **Modules below 86% stay advisory with a named uplift owner.**
   `check_agent_spawn.py` (671 stmts; gaps concentrated in fail-open `except`
   branches + the `decide()` core) is NOT in the enforcing list. It is tracked
   for uplift in a follow-on plan. It is never silently lowered or fake-closed.

4. **Branch coverage stays advisory** (unchanged from PLAN-045 F-03-03 /
   ADR-115 anti-churn), reported but non-enforcing until a 3-run stability window.

5. **Repo-wide line floor is an honest measured value**, not the aspirational
   86%. The repo-wide `coverage report --fail-under=<floor>` uses the
   subprocess-captured TOTAL minus a small margin, with a surgical, commented
   `--omit` list (staging copies under `.claude/plans/**` + any no-owner modules),
   each entry annotated with its owner plan + removal trigger.

6. **No-silent-lower clause.** A Tier-1 module's enforcing threshold (86%) may be
   raised but never lowered, and the enforcing list may only shrink via an ADR
   amendment that names the regression and the remediation owner. Adding a module
   to the enforcing list requires only a measured ≥86% (the happy direction).

## Consequences

- **Positive:** the gate enforces the 5 ready modules immediately; the dishonest
  single repo-wide percentage is replaced by per-module truth; the subprocess
  artifact that caused the 86→78→red slide is fixed at the measurement layer.
- **Positive:** new hooks/modules can be promoted to enforcing the moment they
  cross 86% with no ceremony beyond the list edit.
- **Negative / residual:** `check_agent_spawn.py` remains advisory; its
  fail-open `except` branches and `decide()` core need a dedicated uplift cycle.
- **Negative / residual:** the subprocess `.pth` mechanism adds a CI setup step
  and depends on a writable `site-packages` on the runner (true on ubuntu).
- **Cross-ref:** closes the measurement half of DYN-TEST-1 (PLAN-019 uplift
  roadmap); the test-quality half (agent_spawn uplift) carries forward.

## Enforcement

Enforced by `.github/workflows/coverage.yml` (subprocess-capture steps + Tier-1
per-module gate) and `.github/scripts/parse-coverage.py` (`--tier1-modules` /
`--tier1-min` mode). Advisory branch report + repo-wide line floor remain as
belt-and-braces. Kill-switches: `CEO_TIER1_COVERAGE_ENFORCING=0`,
`CEO_BRANCH_COVERAGE_ENFORCING=0`.
