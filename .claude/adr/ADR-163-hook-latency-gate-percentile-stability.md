# ADR-163 — Hook-latency CI gate: percentile stability (N=200) + capped fail-closed retry

- **Status:** accepted
- **Date:** 2026-07-15
- **Plan:** PLAN-159
- **Blast radius:** L3 (CI release gate semantics; `.github/workflows/validate.yml` guarded edit)
- **Debate:** PLAN-159 round-1 (3 critics, 3× ADJUST → consensus PROCEED, `design-coherent`) — `.claude/plans/PLAN-159/debate/round-1/consensus.md`

## Context

The hard CI gate "Run profile-opus-4-7.py --hook-latency (p95/p99 gate)"
(job `opus-4-7-profiler-smoke`, `validate.yml`) ran **N=20 warm
iterations** with ceilings p95<120 ms / p99<160 ms. It flaked **8 times
across S272/S273** on doc/shell-only commits (no hook or `_lib/` change),
blocking the v1.1.0 release train's final ceremonies (PLAN-157 data-ml,
PLAN-158 GA).

Measured root cause (`.claude/plans/PLAN-159/measurements.md`):

1. **Percentile-index collapse.** `profile-opus-4-7.py::_pct_of_sorted`
   computes `idx = int((n-1)*p/100)`. At n=20: `idx_p95 = idx_p99 = 18` —
   **p95 and p99 both gate the 2nd-largest sample**, the p99 ceiling can
   never fire independently (dead code), and 2 contended iterations out of
   20 fail the gate. Every one of the 6 archived failure reports shows
   `p95 == p99` for every corpus entry — the exact signature. Indices
   first separate at n=22; at n=200 p95 (rank 190) tolerates 10 outliers
   and p99 (rank 198) tolerates 2.
2. **Bursty runner contention.** In every failing run the first corpus
   entry stayed at 45–70 ms while a later entry hit 159–698 ms; the same
   commit passed on another attempt with everything ≤ 81 ms.
3. **Near-max sampling flakes everywhere.** Even on an unloaded
   workstation, N=200 sampling shows single-sample spikes of 144–207 ms
   while p95/p99 stay at 55–76/64–98 ms. CI-side confirmation from the
   contended S273 window itself (hook-profiler N=1000 artifacts,
   `ubuntu-latest`): p95 sits 4–10% above p50 and a 414 ms max spike
   (3.3× p50) does not move p95/p99 — high-N percentiles are stable on
   the exact infrastructure where the N=20 gate flaked.

The gate exists to catch **gross regressions** (PLAN-120 WS-J class:
2.27× p99 from an eager live-import), not to police single-sample spikes.

## Decision

1. **N: 20 → 200** in the CI gate step (`--latency-iterations 200`), and
   the profiler default follows (200). Consistent with the advisory
   sibling `test_hook_latency.py`, which already samples N=200.
2. **Machine-enforced percentile precondition** (debate must-fix):
   `run_hook_latency` returns `passed=False` with error
   `percentile_indices_collapsed` — BEFORE spawning any subprocess —
   whenever `int((n-1)·0.95) == int((n-1)·0.99)` (all n<22). A future
   edit lowering N can never silently re-create the collapsed gate. The
   `_pct_of_sorted` formula itself is deliberately UNCHANGED (changing
   percentile semantics for every consumer is a wider blast radius than
   this fix warrants; the precondition covers the defect class).
3. **Single deterministic in-step retry, fail-closed by construction**
   — the retry contract is an **invariant**: *exactly 2 attempts, never
   more, never unbounded*. `if ! run_gate`-form under `set -euo
   pipefail`; per-attempt wall-cap `timeout 420` (coreutils; ≈5.5× the
   measured 76.6 s local N=200 cost — a pathologically contended
   attempt-1 is killed in time for attempt-2 to run in a fresh scheduler
   window); explicit `exit 1` on double failure (never implicit `$?`);
   attempt-1 failure `::warning`-logged. No third-party retry action
   (zero new supply-chain surface: the job keeps SHA-pinned
   checkout/setup-python and `permissions: contents: read`); NOT
   `continue-on-error`. The wrapper truth table (pass@1→0,
   fail@1+pass@2→0+warning, fail-both→1, cap-kill-without-report→noted)
   is proven by the repeatable artifact
   `.claude/plans/PLAN-159/wave1-wrapper-matrix-proof.sh`, which
   extracts the run-block from the STAGED patch and mocks only
   `run_gate`; the land ceremony runs it as a hard gate.
4. **Job `timeout-minutes: 5 → 16`** — sized for the CONTENDED case
   (2×420 s attempts + `--smoke` + `--floor` + checkout/setup), not the
   nominal one. (Debate consensus C1: a timeout sized for the clean
   runner makes the retry inert in exactly the scenario it defends
   against, converting a fast flake into a slow timeout-fail.)
5. **Ceilings unchanged** (p95<120 ms / p99<160 ms). Measured N=200
   baselines (local p95 55–76 ms / p99 64–98 ms) leave ample margin.
6. **Drift stays visible through the retry** (consensus C3): per-attempt
   per-entry p50/p95/p99/max are appended to `$GITHUB_STEP_SUMMARY`
   whenever the attempt produced a parseable report; an attempt that
   left none (e.g. killed by the 420 s cap mid-write) is noted
   EXPLICITLY in the summary ("NO parseable report") rather than
   silently skipped. A rising attempt-1-failure rate on unregressed
   code is the drift signal; recurring `::warning` lines on changed
   hook code are a review flag
   (`gh run view --log | grep 'attempt 1 FAILED'`).
7. **`subprocess.TimeoutExpired` folds into the fail-closed
   `hook_failed` sink** — a >10 s hook stall reads as a clean gate
   failure, not an opaque traceback (N=200 multiplies subprocess count
   ~10×, raising the odds of one stall).
8. **Anti-vacuity invariant:** the S254 positive control's
   `on_rows >= iterations` assertion **must never be relaxed** to a
   capped form (`>= min(iterations, cap)`). Confirmed armed at N=200:
   rows=201, paired_rows=201, negative arms 0 (measurements §3b).

## Citation fix (drift repair)

`validate.yml` (old step comment) and `test_hook_latency.py` attributed
"N≥200 percentile stability" to **ADR-071**. ADR-071
(benchmark-comparison-methodology) mandates **N ≥ 10 runs per benchmark
task** and says nothing about hook-latency percentile sampling; N≥200
appears in ADR-104-AMEND-1 / ADR-019-AMEND-1 /
docs/measurement-protocols.md in *event-count calibration* contexts.
**This ADR is now the canonical source of the N≥200
percentile-stability rule for hook-latency gating** (minimum 22,
enforced in code), on the evidence in
`.claude/plans/PLAN-159/measurements.md`. Both stale citations are
updated to point here.

## Detection contract (honest scope)

- Detection is **per-entry against the absolute ceiling**, hence
  non-uniform: ≈**1.6×** of baseline on the slowest entry
  (`check_output_secrets`, ~76 ms) up to ≈**2.2×** on the fastest
  (`check_agent_spawn`, ~55 ms). A clean 2.0× regression on the fastest
  entry (55→110 ms) stays under 120 ms and is NOT caught — this was
  equally true at N=20 and is a property of the fixed ceiling, not of
  this change (per-entry relative ceilings are out of scope for a flake
  fix). What N=200 changes: the ceiling that DOES exist now fires on a
  stable statistic, and the p99 ceiling gates independently for the
  first time.
- The Wave-2 acceptance criterion is therefore worded as: **an injected
  over-ceiling regression still RED-flags THROUGH the retry wrapper**
  (both attempts fail ⇒ job RED), proven by
  `.claude/plans/PLAN-159/wave2-regression-proof.sh` before this ADR's
  acceptance boxes are ticked. Load-flakes pass on attempt 2 with a
  visible `::warning` — auditable, bounded, never silent.
- **This gate is not a malicious-behaviour detector.** Its corpus is
  fixed and benign; its security value is the observe-rail write-path
  controls (S254 positive + MF-SEC-5 negative) and gross-regression
  detection on governance hooks — not input-dependent leak detection.

## Operational notes

- **`CEO_SOTA_DISABLE=1` is never a sanctioned flake workaround** — it
  kills the whole profiler job (smoke + floor included); the sanctioned
  response to a flake in this gate is this ADR's mechanism or a revert.
- **Runner constraint:** perf gates stay on GitHub-hosted
  `ubuntu-latest`. Do NOT route this job to the self-hosted `Ceo` runner
  (billing-window queued-eternal incidents; see memory
  `feedback-larger-runner-setup-gotchas`). N=200's statistical
  robustness is the correct lever GIVEN shared-runner contention.
- **Cost:** gate step ~9 s → ~2–3 min nominal per push/PR (capped at
  2×7 min contended). Accepted as the price of a meaningful percentile;
  `validate.yml`'s top-level `concurrency:` group already cancels
  superseded runs.
- **Bootstrapping (PLAN-159 OQ2):** the landing commit passes through
  the OLD flaky gate; one bounded, documented rerun is pre-authorized
  for that single landing. The gate's colour is not the edit's
  authorization — the Owner-signed sentinel is.

## Options considered

| Option | Verdict | Why |
|--------|---------|-----|
| N=200 + capped fail-closed retry (this ADR) | **ADOPTED** | Root fix + burst insurance; detection preserved; every failure mode of the retry itself closed by construction |
| N=200 only | rejected as sole fix | Sustained whole-window contention (observed cold_ms up to 456 ms) needs the fresh-window relocation only a retry gives |
| Retry only (keep N=20) | rejected | Leaves p99 dead + gate keyed to the 2nd-largest sample |
| Fix `_pct_of_sorted` formula | rejected (this plan) | Wider percentile-semantics blast radius; precondition covers the defect class (debate D4) |
| Demote p99 to advisory / N=500 | deferred | p99 hard-gating restores a dead contract; revisit with Wave-2 data (debate D2) |
| Trimmed/winsorized percentile at lower N | deferred | Post-land data may motivate; raw N=200 keeps semantics (debate D1) |
| Loosen ceilings | rejected (no evidence) | Only lever that reduces sensitivity |
| `CEO_SOTA_DISABLE=1` | rejected | Kill-switch, not a fix |
| `continue-on-error` | rejected | Silent demotion of a hard gate |
| Third-party retry action | rejected | New supply-chain surface for a 10-line shell loop |

## Rollback

Single revert of the Wave-1 ceremony commit restores N=20 + no retry +
`timeout-minutes: 5` + old comments (and removes this ADR + the
profiler hardening + its tests). No data migration; no consumer depends
on the gate's sampling parameters. The revert path needs no second
ceremony design — it is the pre-recorded back-out for a wrong-N
surprise.
