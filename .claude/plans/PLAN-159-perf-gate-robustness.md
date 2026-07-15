---
id: PLAN-159
title: Perf-gate robustness — kill the opus-4-7-profiler-smoke load-flake
status: done
reviewed_at: 2026-07-15
started_at: 2026-07-15
completed_at: 2026-07-15
related_commits: [a1e6f7d, 1776c95, ed9fa7d, 553d796, 93371c6, 0dc0461, 0e4fb6b]
created: 2026-07-15
owner: CEO
depends_on: []
budget_tokens: 120-180k
budget_sessions: 1
context_risk: medium
external_wait: none
tags: [ci, perf, governance, flake]
---

# PLAN-159 — Perf-gate robustness

## Context

The CI job `opus-4-7-profiler-smoke` (step "Run profile-opus-4-7.py
--hook-latency (p95/p99 gate)", `.github/workflows/validate.yml:1203`)
flaked **8 times in S272** — every failure driven by GitHub shared-runner
CPU contention, never by a code regression. Proof:

- The failing commits (`f83f74a`, `5f116f2`) are **doc + shell only** —
  they touch no hook and no `_lib/` module.
- **Local, same commit:** the two flagged hooks (`check_output_secrets`,
  `check_anti_ceo_overhead`) run at **p95 ≈ 65 ms** — well under the
  120 ms ceiling. On the runner under load they hit **p95 300–697 ms**
  (cold_ms 237–456 ms).
- The profiler ALREADY discards the cold run and measures WARM p95/p99
  (`profile-opus-4-7.py:370,551`), so the blow-up is warm-iteration
  contention, not cold-start.

**Root cause:** the gate runs **N=20 warm iterations**. The step's own
comment claims "ADR-071 N≥200 for percentile-stability; N=20 is
advisory-grade" — **that citation is itself drift** (ADR-071 mandates
N≥10 for benchmark tasks and says nothing about hook-latency
percentiles; measurements §4). The N≥200 rule now stands on ADR-163's
own evidence, and both stale citations are repaired by this plan. At N=20 the p95 is essentially the 2nd-slowest of 20 —
one or two contended iterations dominate it. The ceiling (p95<120 /
p99<160, PLAN-063 DIM-15) is calibrated to a **57–64 ms CI baseline**, so
it has margin against a *clean* runner but none against a *contended* one.

The gate exists to catch **gross regressions** (its comment cites the
PLAN-120 WS-J 2.27× p99 regression). It does NOT need a tight absolute
ceiling on a noisy runner — it needs a **statistically stable percentile**
and a metric robust to transient contention.

## Goal

Drive the gate's load-flake probability to ~zero on an unloaded AND a
contended runner when the code is unregressed (honest wording per debate
R4: shared runners admit no deterministic guarantee — the acceptance is
probabilistic evidence: 3 consecutive greens incl. a busy window), while
an injected over-ceiling regression still RED-flags through the retry
wrapper. Zero blind reruns to land a clean commit.

## Approach (RESOLVED by round-1 debate consensus — 3× ADJUST → PROCEED)

Levers 1+2 adopted with hardening; lever 3 NOT exercised. See
`PLAN-159/debate/round-1/consensus.md` (C1–C4, K1–K8, D1–D4).

1. **N=20 → N=200** (`--latency-iterations 200`) — root fix: at N=20 the
   nearest-rank index collapses (idx_p95==idx_p99==2nd-largest sample;
   p99 ceiling was dead code); at N=200 p95 tolerates 10 outliers and p99
   (rank 198) gates independently. PLUS profiler hardening (consensus K1,
   K6): `run_hook_latency` fail-louds on a collapsed index
   (`percentile_indices_collapsed`, min N=22) BEFORE spawning anything;
   default bumped to 200; `subprocess.TimeoutExpired` folds into the
   fail-closed `hook_failed` sink. 9 unit tests staged + mirror-proven.
2. **Single deterministic in-step retry, fail-closed by construction**
   (consensus C1+C2): `if ! run_gate`-form under `set -euo pipefail`,
   exactly 2 attempts hardcoded, per-attempt `timeout 420` wall-cap
   (≈5.5× the 76.6s local N=200 cost — kills a pathological attempt-1 in
   time for attempt-2), explicit `exit 1` on double failure, attempt-1
   `::warning`-logged, per-attempt percentiles published to
   `$GITHUB_STEP_SUMMARY` whenever the attempt left a parseable report —
   a cap-killed attempt that left none is noted EXPLICITLY in the
   summary, never silently skipped (drift signal, C3 + pair-rail 3b). Job `timeout-minutes:
   5 → 16` (2×cap + smoke + floor + setup — sized for the CONTENDED
   case). Wrapper matrix proven on the real step text (0/0/1 exits).
3. **Ceilings UNCHANGED** (p95<120 / p99<160). Detection is per-entry vs
   the absolute ceiling (~1.6×–2.2× of each baseline — consensus C4;
   recorded in ADR-163). Recalibration only with post-land evidence + ADR
   amendment.

Alternatives considered and rejected: `CEO_SOTA_DISABLE=1` (kill-switch,
not a fix; never a sanctioned flake workaround — ADR-163),
`continue-on-error` (silent demotion), third-party retry action (new
supply-chain surface), `_pct_of_sorted` formula change (wider blast
radius; precondition K1 covers the defect class — consensus D4), demote
p99 / trimmed percentile / retire-the-retry (deferred to post-land data —
D1/D2/D3).

## Waves

### Wave 0 — debate + measure [DONE S274 2026-07-15]
Check: none (design gate)
- [x] Debate L3 (`/debate start PLAN-159`) — 3 critics (performance,
  devops, security), verdicts 3× ADJUST → consensus PROCEED
  (`design-coherent`); all must-fixes resolved mechanically in-session.
  Artifacts: `PLAN-159/debate/round-1/{proposal,performance-engineer,
  devops-engineer,security-engineer,anonymization-map,consensus}.md`.
- [x] Measure: 6 CI failure logs parsed (p95==p99 signature in 100%),
  3× local N=20 + 2× local N=200, N=200 cost timed (76.6s), anti-vacuity
  controls at N=200 captured, CI-side hook-profiler N=1000 artifacts from
  the contended window pulled + fresh dispatch. `PLAN-159/measurements.md`.

### Wave 1 — implement (profiler + workflow) [SENTINEL CEREMONY — STAGED, ready]
Check: bash .claude/plans/PLAN-159/land-plan159.sh --dry-run (green preflight); mirror-clone proof green (unit 9/9 + N=20 fail-loud + N=22 real green)
- [x] `profile-opus-4-7.py` staged (3 changes per consensus K1/K6):
  percentile-precondition fail-loud (min 22), TimeoutExpired → fail-closed
  sink, default N 20→200. + `test_profile_opus47_latency_gate.py` (9
  tests). Mirror-clone: 9/9 green, N=20 CLI exits 1 with clean error,
  N=22 real profile green with both controls armed.
- [x] `validate.yml` patch staged (`staged/wave1/validate-yml.patch`):
  N=200 + capped fail-closed retry wrapper + step-summary publishing +
  job timeout 16min + comment/citation fix. Applies clean; YAML parses;
  wrapper matrix proven (pass@1=0, flake=0+warning, double-fail=1).
- [x] ADR-163 staged (new ADR, not an ADR-071 amendment — ADR-071 never
  contained the N≥200 rule; that citation was drift, now repaired in
  validate.yml + test_hook_latency.py). Records incident, distributions,
  index table, cap basis, invariants (exactly-2 attempts, `>= iterations`
  anti-vacuity, per-entry sensitivity 1.6×–2.2×), rollback.
- [x] **V2 pair-rail**: Codex **VERDICT: GO** (round 5 of 5; rounds 1–4
  surfaced 10 real findings, all fixed + re-verified — arc recorded in
  `PLAN-159/pair-rail-verdict-wave1.md`, anchored to the tracked
  `staged-wave1.sha256` manifest; land script re-verifies the hashes
  fail-closed at preflight).
- [x] **V3 Owner ceremony** (2026-07-15): dry-run green → live green —
  sentinel signed (anchor `a1e6f7d`), bundle applied, gates green (9/9 +
  claims + governance + local N=200 proof), scope asserted, commit
  **`1776c95`** [SENT-PERFGATE], pushed.

### Wave 2 — prove + closeout
Check: gh run list --workflow validate.yml — 3 consecutive green pushes incl. one during a known-busy runner window
- [x] 3 consecutive green Validate pushes with the NEW gate, zero reruns
  (2026-07-15): **`93371c6` → `0dc0461` → `0e4fb6b`, all green** (runs
  29445259754 / 29449190885 / 29450708764), pushes properly serialized
  (each waited for the prior green — the landing-era rapid pushes had
  concurrency-cancelled each other). The OQ2 rerun was never needed
  (push events use the pushed commit's workflow, so the OLD gate never
  ran again); `553d796` failed on an UNRELATED cause (new test file was
  bare `unittest.TestCase` → env-hygiene gate; fixed in `93371c6` by
  converting to `TestEnvContext`). The NEW perf gate ran green on all 4
  post-land runs (first datapoint: `553d796`, 1m49s).
- [x] `bash .claude/plans/PLAN-159/wave2-regression-proof.sh` — injected
  over-ceiling regression RED-flagged THROUGH the retry wrapper: both
  attempts failed on the MEASUREMENT (rc1=1 rc2=1; p95 239–253 ms > 120),
  anti-vacuity confirmed the measured breach on both output_secrets
  entries, macOS shim + no-report note behaved as designed
  (2026-07-15T19:15:26Z). Criterion per consensus C4. Never lands.
- [x] Post-land review (consensus D3): the retry never fired in the
  4-run acceptance window (gate job ~2min each = single attempt).
  Decision: **retirement NOT opened yet** — 4 quiet runs are too thin a
  window to judge a mechanism whose value case is bursty contention;
  re-evaluate `::warning` frequency at the next hygiene sweep / before
  the next release train. Recorded here so the deferral is a decision,
  not an omission.
- [x] Closeout (2026-07-15): plan → done (completed_at +
  related_commits); memory updated (gate now N=200 + capped fail-closed
  retry; root cause = percentile-index collapse; ADR-163 pointer).

## Open questions

- **OQ1 (lever mix) — RATIFIED (Owner, 2026-07-15, AskUserQuestion):**
  selected **"Ratificar o mix (Recomendado)"** — question posed: "N=200 +
  retry fail-closed com cap de 420s/tentativa (exatamente 2) + ceilings
  inalterados (120/160) + hardening do profiler (precondição fail-loud,
  TimeoutExpired fail-closed, default 200) + timeout do job 5→16min.
  Custo aceito: step ~9s → ~2-3min nominal por push/PR."
- **OQ2 (bootstrapping) — RATIFIED (Owner, 2026-07-15, AskUserQuestion):**
  selected **"Sim, 1 rerun documentado (Recomendado)"** — one bounded,
  documented rerun pre-authorized for the single landing push if the OLD
  gate flakes on it; off-peak window preferred but not mandatory.
  (Critic-A: the perf gate's colour is not the edit's authorization —
  the sentinel is.)
- **OQ3 (scope) — RATIFIED (Owner, 2026-07-15, AskUserQuestion):**
  selected **"Ratificar escopo (Recomendado)"** — scope stays: this one
  step + profiler + ADR-163 + citation fixes (`--floor` gates p50 with 4×
  margin; perf-profile is advisory N=1000; benchmarks.yml has no latency
  percentile gate; test_hook_latency.py is xfail-advisory, citation fix
  only). Deferred items (p99-advisory, trimmed percentile, retry
  retirement) go to the post-land review with data.

## How to continue

Read this plan. Wave 0 is DONE; Wave 1 is fully staged. Sequence:
(1) Owner ratifies OQ1–OQ3 → status `draft → reviewed`;
(2) CEO runs the V2 pair-rail on the staged diff → verdict file;
(3) Owner runs `land-plan159.sh` (dry-run first), pushes → `executing`;
(4) Wave 2 proofs → `done`. This plan BLOCKS nothing structurally —
PLAN-157 data-ml + PLAN-158 GA can still land by bounded rerun of the
current gate if the Owner prefers not to wait.

## Success criteria

- [x] 3 consecutive green Validate pushes with zero perf-gate reruns
  (`93371c6`/`0dc0461`/`0e4fb6b`, 2026-07-15). The "busy-runner window"
  sub-criterion cannot be scheduled deterministically; it is covered by
  proxy: the CI-side N=1000 evidence captured DURING the contended
  S273 flake window (measurements §6) shows high-N percentile stability
  on the same infrastructure, and the gate ran green 4/4 post-land in
  the same weekday time band as the original flakes.
- [x] An injected over-ceiling regression still fails the gate THROUGH
  the retry wrapper — both attempts failed on the MEASUREMENT
  (rc1=1 rc2=1, p95 239–253 ms; anti-vacuity confirmed;
  2026-07-15T19:15:26Z).
- [x] ADR-163 records N=200, the 420 s cap, the invariants + measured
  basis; the ADR-071 citation drift is repaired in both call sites
  (landed in `1776c95`).
