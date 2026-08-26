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
3. **Bounded deterministic in-step retry, fail-closed by construction**
   *(rewritten in place by the PLAN-161 C4 amendment below; the
   original invariant read "exactly 2 attempts, never more")* — the
   retry contract is an **invariant**: *2 unconditional attempts +
   inter-attempt backoff `B = CEO_PERF_GATE_BACKOFF_S` (default 60 s) +
   AT MOST one 3rd attempt gated on an explicit contention pre-probe +
   a fail-fast still-contended path — never unbounded.* `if !
   run_gate`-form under `set -euo pipefail`; per-attempt wall-cap
   `timeout 420` (coreutils; ≈5.5× the measured 76.6 s local N=200
   cost — a pathologically contended attempt is killed in time for the
   next one to run in a fresh scheduler window); the backoff sleeps
   between windows so SUSTAINED contention cannot defeat back-to-back
   attempts (the S27x failure mode: two doc-only commits failed both
   attempts under sustained load); after a double failure a 30 s-capped
   `--floor` contention pre-probe decides — still-contended ⇒ explicit
   `exit 1` with a distinct infrastructure label and NO 3rd attempt;
   uncontended ⇒ exactly one probe-gated 3rd attempt whose failure IS
   the regression verdict (explicit `exit 1`, never implicit `$?`);
   attempt-1 failure and the probe-gated grant are `::warning`-logged.
   No third-party retry action (zero new supply-chain surface: the job
   keeps SHA-pinned checkout/setup-python and `permissions: contents:
   read`); NOT `continue-on-error`. The extended truth table is proven
   by the repeatable artifact
   `.claude/plans/PLAN-161/proof-retry-matrix.sh` (see Amendment); the
   original 2-attempt table remains archived at
   `.claude/plans/PLAN-159/wave1-wrapper-matrix-proof.sh`.
4. **Job `timeout-minutes: 5 → 16`** — sized for the CONTENDED case
   (2×420 s attempts + `--smoke` + `--floor` + checkout/setup), not the
   nominal one. (Debate consensus C1: a timeout sized for the clean
   runner makes the retry inert in exactly the scenario it defends
   against, converting a fast flake into a slow timeout-fail.)
   *Superseded by the PLAN-161 C4 amendment: 16 → 28, re-sized for the
   extended worst case — see Amendment.*
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

## Amendment (PLAN-161 C4, 2026-07-27)

**Trigger:** two doc-only commits failed the gate on BOTH attempts
under *sustained* runner load (S276 "2ª falha both-attempts"), the
exact scenario the back-to-back 2-attempt shape cannot defend against:
when contention outlasts both 420 s windows, relocation to an adjacent
scheduler window relocates *into the same load*. Debate CF-2 + codex
pair-rail r1 F7 / r2 F5 / r3 F4 / r4 F4.

**Amended retry invariant** (rewrites Decision item 3 in place):
*2 unconditional attempts + inter-attempt backoff
`B = CEO_PERF_GATE_BACKOFF_S` (default **60 s**, env-fakeable to 0 in
proofs) + AT MOST one 3rd attempt gated on an explicit contention
pre-probe + a fail-fast still-contended path — never unbounded.*

**Contention verdict definition:** the pre-probe wraps
`timeout 30 python3 .claude/scripts/profile-opus-4-7.py --floor`
(stderr discarded — the floor probe finally gets the explicit wall-cap
it lacked). CONTENDED iff **any** of: nonzero probe exit — the **exit
status OVERRIDES apparently-uncontended JSON** (codex r4 F4; covers
`timeout` rc 124) — or unparseable/malformed floor JSON (fail-safe).
Otherwise UNCONTENDED iff `subprocess_floor_ms.p50 <= 200` ms parsed
from the floor JSON (threshold is `<=`: boundary p50 == 200 is
UNCONTENDED; same 200 ms bound as the long-standing floor sanity
step). A CONTENDED verdict fail-fasts with a distinctly-labeled
infrastructure outcome ("still-contended VM … NOT a regression
verdict") and burns NO 3rd 420 s attempt; an UNCONTENDED verdict
grants exactly one `::warning`-logged 3rd attempt whose failure is the
final real-regression verdict.

**Back-compat marker:** the literal `FAILED on BOTH attempts (rc1=`
survives in EVERY both-attempts-failed outcome (still-contended AND
uncontended-fail@3) — `PLAN-159/wave2-regression-proof.sh:134` greps
it; the 3rd-attempt markers are ADDITIVE.

**Job budget** (supersedes Decision item 4): `timeout-minutes: 16 →
28`, pinned worst-case inequality: 3×420 s (capped attempts) + 2×60 s
(backoffs) + 30 s (probe cap) + 30 s (floor sanity) + ~180 s
(checkout/setup/smoke headroom) ≈ 1620 s ≈ 27 min → 28. Both 30 s
terms are ENFORCED wall-caps — the pre-probe AND the floor-sanity step
each wrap the profiler in `timeout 30` (codex r3 F4), and a cap-killed
floor-sanity run fails with a distinct infrastructure label, never a
floor-regression verdict — so the inequality holds by construction,
not by assumption.

**Executable proof:** the extended truth table (pass@1;
flake+pass@2; both-fail+contended fail-fast; both-fail+uncontended
pass@3; both-fail+uncontended fail@3; malformed probe JSON; probe
timeout rc 124; nonzero probe rc overriding below-threshold JSON;
boundary p50==200; non-numeric p50 JSON — boolean `true` and string
`"-1"` — treated as CONTENDED) is proven by
`.claude/plans/PLAN-161/proof-retry-matrix.sh` — the script's
`run_case` list is the canonical case inventory — which extracts the
run-block from the staged/landed `validate.yml`, mocks ONLY `run_gate`
and `probe_floor_raw`, and runs the `contention_probe` parser REAL. It
**supersedes the PLAN-159 wave1 matrix for the extended contract**
(`wave1-wrapper-matrix-proof.sh` stays archived as the 2-attempt-era
proof).

**Reconciled acceptance:** the gate never requires a manual re-run for
a probe-UNCONTENDED failure — that path always gets its 3rd attempt
in-job. A still-contended fail-fast is an **accepted,
distinctly-labeled infrastructure outcome** (the probe runs only after
≥900 s of elapsed job time — 2×420 s attempts + 60 s backoff — so a
still-contended verdict means sustained multi-window load, rare by
construction); its remedy is a re-run when quiet, and its label
explicitly disclaims a regression verdict. N=200 percentile semantics
(Decision items 1, 2, 5) are untouched by this amendment.


## Amendment (PLAN-169 W2.2, 2026-08-09) — test probes join the N-adequacy rule; MEDIAN-on-CI re-evaluated and KEPT

The original decision covered the CI profiler gate. The TEST probes of
the same family sat outside it: `test_case_a_p99_under_5ms` gated the
MEDIAN on CI (a p99 of N=100 was one preemption spike from failing —
S297: 5.25 ms vs 5 ms) and `test_emit_pair_end_to_end_loop_p95_within_budget`
had COLLAPSED indices (`int(19*.95) == int(19*.99) == 18`) — the exact
class this ADR names.

Decision (implemented in the free test surfaces by PLAN-169 W2.2):

1. N=200 (Case-A) / N_TRIALS=40 (end-to-end loop); indices ALWAYS
   derived from the constant via the `_pct_of_sorted` nearest-rank
   truncation (`int((n-1)*p/100)`) — never hardcoded.
2. The collapse precondition (`i95 != i99`) is ASSERTED inside each
   test before the timed loop — lowering N can never silently
   re-create a collapsed gate.
3. On CI/loaded machines the MEDIAN gate STAYS — re-evaluated and KEPT
   with live evidence. The p95-on-CI attempt flaked on its FIRST real
   run (validate run 31288404989: p95=6.31 ms vs median=3.83 ms
   against the 5 ms budget): a loaded shared runner shifts the WHOLE
   distribution (~6x the local median), so any real tail percentile
   prices the runner, not the code. The median is stable under that
   shift and still catches the ~8x regression the probe exists for.
   Quiet local machines keep the strict p99. Budgets unchanged.

The PLAN-112-FOLLOWUP median switch therefore graduates from
flake-intuition to a decision WITH evidence (the run above). Any new
percentile probe is born with: an N satisfying the precondition,
derived indices, the median in shared-load environments, and a real
percentile only where the environment is controlled.


## Amendment (PLAN-169 S318, 2026-08-20) — p99 demoted to advisory; p95 recalibrated 120 → 180 with evidence

**Trigger:** validate run 32408847458 (commit `908707e`, 2026-08-20)
failed all three attempts and was stamped a "real regression" verdict
that was FALSE — the local N=200 baseline held at 70.6 ms. The attempt
series is the whole diagnosis:

- attempt 1 (19:54Z): `check_output_secrets[observe=1]` p95=110.6 ms
  (**within** the 120 ms ceiling, an 8% margin) / p99=177.0 ms — the
  attempt failed **on p99 alone**;
- attempt 2 (19:56Z): whole distribution shifted (p95 302–320 ms) — a
  contention burst no reasonable ceiling survives;
- the contention probe ran AFTER the 60 s backoff, the burst had
  passed, it read UNCONTENDED and granted the 3rd attempt on a
  still-warm runner: p95=162.1 / p99=198.0 → final "regression"
  verdict on unregressed code.

**Longitudinal evidence** (perf-profile N=1000 artifacts,
ubuntu-latest, runs 32185964567 / 32234091647 / 32322055888,
2026-08-18..20): the same hook measured warm p50 120 → 118 → 79 ms
and p95 126 → 123 → **178 ms** across three days — the runner's whole
distribution moves 1.5–2.3× between scheduler windows. A tail
percentile on a shared runner prices the runner, not the code — the
same finding the W2.2 amendment above already accepted for the test
probes (run 31288404989). The "Demote p99 to advisory" option this
ADR deferred in 2026-07 ("revisit with Wave-2 data") now has its
data. "Loosen ceilings" was rejected then as "(no evidence)"; the
evidence condition is now met for the heaviest entry.

**Decision (amends Decision item 5):**

1. **p95 ceiling 120 → 180 ms, HARD** (CI argv + profiler default).
   Sized from the 2026-08 runner reality: heaviest-entry p95 ≈110 ms
   on an unloaded runner × the ~1.6× detection factor this ADR's
   §Detection contract already names. The gate still catches the
   gross-regression class it exists for (PLAN-120 WS-J, 2.27×:
   110 → 250 ms ≫ 180) and today's attempt-3 (162 ms, warm runner)
   passes instead of minting a false verdict.
2. **p99 demoted to ADVISORY in the CI gate** (`--p99-advisory`, new
   profiler flag): each entry reports `p99_within`, breaches are
   echoed as a `WARN:` stderr line and land in the step summary, but
   the exit code never keys on p99. The flag is opt-in — without it
   the profiler keeps the hard-p99 contract (back-compat for local
   runs and adopters).
3. **N=200, the retry wrapper, the contention probe and both
   controls are UNTOUCHED.** The `FAIL: hook latency gate —` marker
   and the `FAILED on BOTH attempts (rc1=` back-compat literal
   survive unchanged.
4. **Proof updates:** `wave2-regression-proof.sh` breach literals
   120.0 → 180.0 (the injected ~215 ms regression stays over-ceiling,
   so the proof's detection claim is preserved);
   `proof-retry-matrix.sh` is unaffected (it mocks `run_gate` and
   extracts the run-block from the live `validate.yml`).

**Honest scope:** the fixed-ceiling non-uniformity this ADR already
declared gets wider — on the fastest entry the factor grows to
≈2.3–3.3×, so a clean 2× regression there stays invisible (it already
was at 120). Per-entry relative ceilings remain the named successor
if that ever bites; this amendment deliberately keeps the shared
single-ceiling shape.

**Authorization:** Owner ratified the route via AskUserQuestion
(S318, 2026-08-20): "Emenda ADR-163 (Recomendado) — p99 hard→advisory
+ p95 120→180 com a evidência de hoje". Landed by the SENT-S318 pack
ceremony (this file + `validate.yml` + `profile-opus-4-7.py` +
`wave2-regression-proof.sh` + profiler tests, one signed commit).


## Amendment (PLAN-169 S328, 2026-08-25) — runner-normalized second key; the spawn probe is blind by construction

**Trigger:** validate run `32866209415` (commit `a16ac96`, started
2026-08-25 15:30:23Z) failed with `check_output_secrets` p95
**361.4 / 424.8 / 229.1 ms** across the three attempts, against the
180 ms hard ceiling the amendment above had just recalibrated with
evidence. The verdict was FALSE again. Three legs prove it:

- **The probe said the runner was fine.** The PLAN-161-C4 contention
  pre-probe read UNCONTENDED at a **7.76 ms** spawn floor (its own
  threshold is 200 ms), granted the 3rd attempt, and that attempt's
  failure became the "real regression" verdict.
- **The same bytes are fast elsewhere.** The identical invocation
  measured **70–77 ms** locally (77.3 ms `observe=unset` / 70.2 ms
  `observe=1`; the 2026-08-20 baseline in the amendment above was
  70.6 ms).
- **The same bytes PASSED three hours earlier.** Run `32845976838`
  (`6304f66`, started 12:08:32Z) was green — **3 h 22 min** before
  the failing run started — and `git diff 6304f66..a16ac96 --
  .claude/hooks/` touches **zero files**. `check_output_secrets.py`
  itself is unchanged since 2026-07-02 (`7df843d`). Identical hook
  bytes: PASS, then FAIL.

Not one bad window. On `56f050c` (run `32758192634`, 2026-08-24) the
same entry went from p95 209 ms in its first attempt series to
**435 ms in a rerun of the identical commit**, with the probe
UNCONTENDED throughout (floor p50 6.6–8.6 ms).

**Why the probe cannot see this — the structural finding.**
`python3 -c pass` prices process CREATION. The entry that breaches
does something else: its module-level imports are stdlib-only, but
its measured path lazily imports `_lib.output_scan`,
`_lib.output_scan_dedup`, `_lib.audit_emit`, `_lib.tool_lifecycle`
and `_lib.payload` (`check_output_secrets.py:223/236/231/328/376`),
whose static transitive `_lib` closure is **12 modules / 21,448
lines** (dominated by `audit_emit`, 14,068) — and then it takes a
locked, fsynced write. How much of that closure executes per call
depends on the path; NONE of it is priced by `python3 -c pass`. A
runner that is slow-but-UNCONTENDED once execution starts (SKU
drift, throttling, a cold page cache) moves that work several-fold
while leaving the spawn floor flat. The probe is blind **by
construction**, not by miscalibration — so no re-tuning of its
200 ms threshold could have caught any of these runs.

**Decision.**

1. **The 180 ms absolute ceiling STAYS, hard — no third
   recalibration.** The amendment above already moved it 120 → 180
   with evidence. Moving it again would answer a MEASUREMENT problem
   with a threshold, and the spread documented here (209 → 435 ms on
   one commit) admits no ceiling that both survives the runner and
   still detects a regression.
2. **A SECOND, RELATIVE key**, measured in the same scheduler
   window: `hook_p50 <= K_e × ref_p50`, **p50 on BOTH sides** — the
   W2.2 amendment's median-on-shared-load doctrine, for its own
   reason. The p95/p50 ratio of the longitudinal series in the
   amendment above is 1.05 / 1.04 / **2.25** (120/126, 118/123,
   79/178), so any p95-over-p50 key would swing 2× on unregressed
   code.
3. **The reference is a 6th corpus entry, `ref_exec`:** a frozen,
   stdlib-only, 3-term script (cold `json`/`re`/`hashlib`/`pathlib`
   imports plus a fixed `re.compile` set; a fixed CPU hash loop;
   M × `open`/append/`flock`/`fsync`/rename on the same filesystem
   as that entry's audit dir), source-pinned by `ref_source_sha256`
   in the report, **ROUND-ROBIN interleaved inside each entry's own
   loop**, `_REF_SAMPLES_PER_ENTRY = 40`.
   - *Interleaving is load-bearing.* §Context of this ADR already
     records one entry at 45–70 ms while a later entry hit
     159–698 ms in the SAME run; the three attempts in the trigger
     above (361 → 425 → 229 ms) move the same way. A reference
     sampled once before the loop would price a different machine
     than the hook it normalizes.
   - *The reference MUST NOT import `_lib` or `.claude/hooks`.* The
     regression class this gate exists for (PLAN-120 WS-J) IS an
     eager framework import; a reference that shared it would
     inflate numerator AND denominator and blind the ratio to its
     own reason to exist.
   - *The IO term is mandatory.* A 7.76 ms spawn floor beside a
     361 ms hook is a disk/page-cache signature; a CPU-only
     reference would be exactly as blind as the probe it succeeds.
4. **Four named outcomes**, a closed set every consumer DERIVES
   rather than recalls (`_OUTCOME_LABELS`): `pass` → exit 0,
   `advisory_slow_runner` → 0, `real_regression` → 1,
   `infrastructure_contended` → 5. A non-finite / non-positive /
   bool / str `ref_p50`, a reference split-half p50 drift above
   `_REF_DRIFT_MAX = 1.5`, or the profiler's own wall self-cap
   (0.9 × `--wall-budget-seconds`) yield `infrastructure_contended`
   — an explicitly NON-regression verdict, the same shape the
   still-contended fail-fast introduced in the PLAN-161 C4
   amendment.
5. **PHASE 1 IS WHAT SHIPS: advisory, exit codes byte-identical to
   today.** The CI step gains exactly two argv flags
   (`--exec-reference --relative-advisory`) and one step-summary
   line. Without a `K_e` there is no `rel_ok`, so the label mirrors
   the absolute key and even a broken reference leaves the exit
   alone. `run_gate`'s retry contract, `BACKOFF_S`, the contention
   probe and the `FAILED on BOTH attempts (rc1=` back-compat
   literal are **untouched**, so `proof-retry-matrix.sh` (which
   mocks `run_gate`) and `wave2-regression-proof.sh` (which extracts
   the run-block by indentation and runs it for real) both stay
   proven. Named cost: because wave2 runs `run_gate` unmocked, its
   attempts now also sample 5 × 40 reference points.
6. **K is NOT set here; the PROCEDURE is the deliverable.** K is not
   derivable today — zero paired `(hook, reference)` samples exist
   anywhere, and every local measurement taken while writing this
   amendment was self-declared contaminated. Phase 1 publishes
   `R_e = hook_p50 / ref_p50` per entry; after **≥10 green CI runs
   over ≥3 days**, `K_e = 1.25 × max(R_e)`, admitted only if
   `K_e < (baseline_p50_e + 150) / max(ref_p50)` — the bound that
   mechanically preserves the detection criterion, i.e. the +150 ms
   positive control still fails at the WORST observed reference.
   - **The bound is STRICT, and that is not cosmetic** (pair-rail
     round 3). The relative rule at item 2 is `hook_p50 <= K_e ×
     ref_p50` — it ACCEPTS equality, as an absolute ceiling does. So
     at `K_e = (baseline_p50_e + 150) / max(ref_p50)` exactly, the
     planted control has `hook_p50 = baseline_p50_e + 150 = K_e ×
     max(ref_p50)`, `rel_ok` is TRUE, and the control **PASSES** —
     the precise opposite of what admitting that K is supposed to
     guarantee. One boundary point, and it is exactly the point the
     formula selects when the interval is tight. A non-strict bound
     here would make the whole admissibility argument decorative.
   - **The implementation matches, and the strictness lives in
     exactly ONE of the two comparisons.** `profile-opus-4-7.py`
     rejects `K >= admissibility_max_K` — the cap is **EXCLUSIVE**,
     so a K landing exactly ON it is inadmissible, not admitted —
     while `_classify_entry` keeps `rel_ok = hook_p50 <= K_e ×
     ref_p50`, which accepts equality the way an absolute ceiling
     does. That asymmetry is the design, not an oversight: making
     *both* strict would close the interval twice and reject a K
     that is in fact admissible. An earlier draft of this amendment
     asserted the opposite — that the cap admitted `K == cap` and
     the code therefore disagreed with this ADR; that was true of an
     earlier profiler and is **no longer the case**. The rule to
     preserve, stated once: **the cap is exclusive; the gate
     comparison is inclusive.** Changing either side alone
     re-opens the hole.

   An **EMPTY** admissibility interval means the reference is
   mis-shaped and the design is REJECTED: **never widen K**. That is
   the "bump the number" move this ADR already declined at the
   amendment above, and it would be worse here, because widening K
   silently deletes the detection the second key exists to provide.
   Any K written into a ceremony package before that window is
   INVENTED.
7. **The spawn probe stays, vestigial.** Removing it buys nothing
   and grows the canonical diff; it keeps gating the 3rd attempt
   exactly as the PLAN-161 C4 amendment specifies. This amendment
   demotes it in DOCTRINE, not in code: it is now understood to
   answer "is this machine oversubscribed right now?", never "is
   this machine fast?".

**Detection contract (what would falsify this).**

- **Positive control:** a planted +150 ms on the hook, with the
  reference held at baseline, must yield `real_regression` — asserted
  at the predicate level via the injected sampler, never on
  wall-clock luck, plus a live plant through the real wrapper. A
  `time.sleep` plant is NOT sufficient on its own: sleep is IO wait
  and misses the WS-J eager-import shape, so an import-shaped plant
  is required too.
- **Negative control:** synthetic load (CPU and IO arms) on
  unregressed code must NEVER yield `real_regression`, AND
  `R_loaded / R_quiet` must stay in `[0.7, 1.4]`. The ratio half is
  the anti-vacuity check: a CPU burner against an IO-bound hook
  starves the REFERENCE harder, the ratio FALLS, and the control
  would otherwise pass for the wrong reason.
- **Declared residual:** an IO-slow runner remains indistinguishable
  from an IO regression by any reference that also performs IO. This
  is accepted, not solved.
- **Known defect, RECORDED not cured — and the self-cap does NOT
  remove it.** The retry wrapper's failure branches capture *any*
  non-zero rc: after an UNCONTENDED probe, a third failing attempt is
  stamped `::error::… treating as a real regression` and `exit 1`,
  whatever the profiler returned (`validate.yml:1352-1376`). The
  420 s cap-kill (rc 124) has always been mislabeled that way. The
  wall self-cap does not make that mislabel unreachable — it
  **RENAMES** it: the cap now exits 5 (`infrastructure_contended`),
  which lands in the *same* branch and is published under the *same*
  "real regression" text. An earlier draft of this amendment claimed
  the self-cap "already removes" the case; that reasoning was wrong
  and is corrected here.
  - **Unreachable in PHASE 1, by construction.** Phase 1 keeps
    `exit_class == (0 if passed else 1)`, so the profiler never
    returns 5 while this package is what ships — asserted, not
    assumed, by `test_auto_cap_in_phase1_keeps_a_nonzero_exit`, which
    drives the most aggressive cap available
    (`--wall-budget-seconds 0`) and requires **rc 1**. Nothing in
    this canonical diff creates a path to the mislabel.
  - **It becomes REQUIRED work for phase 2.** Phase 2 is the only
    state that can return 5, so the phase-2 ceremony must either
    teach the wrapper to distinguish rc 5 (an explicitly
    NON-regression verdict, the shape the PLAN-161 C4 amendment
    already introduced for the still-contended path) or change the
    outcome contract so 5 is not produced. That is a named
    precondition of phase 2, not an optional cleanup — and the
    reason it is not done here is scope, not harmlessness.

**Resolved by synthesis (three critics, recorded so they are not
relitigated):** `n_ref = 40` (the ≥22 index-separation rule binds on
p95; the relative key gates on p50, where collapse cannot arise);
`K = 1.25 × max(R_e)` **plus** the admissibility bound, chosen over
`1.6 × median` because it is the only form that mechanically proves
the +150 ms control still fails at the worst observed reference; the
`abs_ok ∧ ¬rel_ok` cell (which would close the blind spot the
amendment above explicitly declares — a clean 2× regression on the
fastest entry stays invisible under 180 ms) is implemented and
unit-tested but **default OFF**, behind the `strict_relative`
parameter, which has **no CLI flag** and is therefore unreachable
from the workflow until a later decision wires it.

**Open questions — NOT decided here.** Six questions this amendment
deliberately leaves to the Owner (the `abs_ok ∧ ¬rel_ok` cell; the
evidence-free 600 ms absolute backstop; accepting a phase-1 window in
which no relative key gates; the fallback branch if the admissibility
interval comes back empty; whether the two ADR-144 inheritors travel
in this package; and that `test_hook_latency.py` — both tests
`xfail(strict=False)`, corpus `check_agent_spawn` + `audit_log` — is
NOT a safety net for `check_output_secrets`, the entry that actually
fails) are recorded as **PLAN-169 §Open questions OQ-7..OQ-12**.
