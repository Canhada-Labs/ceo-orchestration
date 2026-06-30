---
id: ADR-147
title: Eval-harness doctrine — real-task reward benchmark, nightly/on-demand, quota-capped, no-float reward
status: PROPOSED
enforcement_commit: n/a (PROPOSED — pending PLAN-133 C3 Owner-GPG ceremony)
decision_date: 2026-06-09
proposing_session: S223
authorization: "PLAN-133 (Goose-harvest SOTA evolution) Wave C eval — item C3 [P1] (~10 real-task reward benchmark, Cut 2). 7-archetype Wave-A debate 0-VETO + Codex pair-rail."
owner: qa-architect
plan: PLAN-133-goose-harvest-sota-evolution
amends: none
related: [ADR-021, ADR-030, ADR-063, ADR-071, ADR-081, ADR-141]
---

# ADR-147 — Eval-harness doctrine

**Status:** PROPOSED (S223, 2026-06-09) — the harness (`.claude/eval/`) is built +
green with a FAKE executor (28 tests, zero quota); this ADR codifies the doctrine
the harness embodies and gates the canonical edits (the `eval_task_completed`
closed-enum action + the nightly workflow).
**Enforcement commit:** n/a (PROPOSED) — on acceptance, the enforcing artifacts are
`.claude/eval/runner.py` + `.claude/eval/reporter.py` + `.claude/eval/tasks/` +
the `eval_task_completed` action in `.claude/hooks/_lib/audit_emit.py` +
`.github/workflows/eval-nightly.yml`.
**Blast radius:** L3 (a new eval subsystem + a new audit action + a new CI workflow
that spends real subscription quota)
**Cites:** PLAN-133 item C3 [P1].

## Context

The framework has skill benchmarks (ADR-071) and an agent-eval tournament
(ADR-063), but no **real-task reward benchmark** that measures the end-to-end
orchestration on concrete coding tasks with deterministic verifiers. Goose ships a
harbor-style task/reward eval; PLAN-133 C3 harvests the *idea* (a from-scratch
stdlib re-implementation) as ~10 real tasks, each with a golden solution and a
verifier that scores a reward.

Real-task evals spend real subscription quota (S220: quota IS the cost metric, not
USD). They must NOT run per-push (the S220 17→12min push budget) and must no-op
cleanly when no key is present.

## Decision drivers

- A measurement substrate is needed to catch orchestration regressions that unit
  tests cannot (a falling mean reward / rising flaky count is the signal).
- Real quota spend must be bounded and never on the per-push path.
- The reward must be HMAC-safe (no float in the audit chain).
- Avoid the PLAN-128 §7 "0/0/0 measure-nothing" trap: every task must be
  satisfiable (golden solution scores full reward) AND an untouched setup must
  score below full.

## Options considered

### Option A: Per-push eval in `validate.yml`
Immediate signal, but blows the push-time budget and draws quota unbounded.
Rejected.

### Option B: Nightly / on-demand workflow, quota-capped, `--skip-if-no-key` (chosen)
A dedicated `eval-nightly.yml` (cron + `workflow_dispatch`), serial, worst-of-N
(reuse C1) + flaky detection, with a hard quota cap and a clean no-op when no key
is present. Mirrors the `benchmarks.yml` fork-safety + `CEO_SOTA_DISABLE` parity.

### Option C: No harness
Leaves orchestration regression invisible. Rejected.

## Decision

Adopt **Option B**. The eval-harness doctrine is:

1. **Real-task reward benchmark** — ~10 tasks under `.claude/eval/tasks/`, each
   with a golden solution that scores full reward and a verifier failsafe on an
   empty workdir (no measure-nothing trap).
2. **Nightly / on-demand ONLY** — `eval-nightly.yml` runs on a cron schedule +
   `workflow_dispatch`; NEVER wired into per-push `validate.yml`.
3. **Quota-capped + `--skip-if-no-key`** — a missing key is a clean no-op (never a
   false-RED); the cap blocks an oversized budget unless `--allow-expensive`.
4. **Serial, worst-of-N + flaky** — no thread/process pool; aggregation takes the
   minimum (worst) of N attempts (reuse C1); disagreement across attempts sets the
   `flaky` flag.
5. **No-float reward in the audit chain** — the `eval_task_completed` action encodes
   reward as basis-points (`reward_bps` 0..1000) and `flaky` as 0/1; `status`
   coerces to the closed enum `pass|partial|fail|other`. No-value-echo: only the
   stable task slug + closed-enum/int fields are persisted; routes through the
   Sec MF-3 allowlist scrub.
6. **Default-conservative** — `worst`-of-N, serial, quota-capped, `--skip-if-no-key`;
   a `--floor` hard gate is NOT enabled until the first week's p50/p95 mean-reward
   is published.

## Consequences

- (+) A concrete orchestration-regression signal (mean reward + flaky count) at
  `/ceo-boot`, independent of unit tests.
- (+) Quota spend is bounded and off the push path; a no-key runner is a clean
  no-op, never a false-RED.
- (−) A new subsystem + a new CI workflow that spends real quota; mitigated by the
  cap + nightly cadence + fork-safety guards.
- (~) Adds a closed-enum audit action (`_KNOWN_ACTIONS` +1) — gated by the
  api-contract SHA + count + the no-float / no-value-echo property tests + the
  SPEC audit-log schema row + `check-audit-registry-coverage.py`.

## Promotion criteria (measure-first)

Publish the first week's p50/p95 mean-reward + flaky count before treating any
`--floor` as a hard gate.

## Blast radius

L3 — `.claude/eval/` subsystem, the `eval_task_completed` audit action,
`SPEC/v1/audit-log.schema.md` row, and `eval-nightly.yml`.
