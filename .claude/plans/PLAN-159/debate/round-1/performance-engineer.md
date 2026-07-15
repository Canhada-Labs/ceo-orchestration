---
round: 1
archetype: performance-engineer
skill: performance-engineering
generated_at: 2026-07-15T16:38:23Z
plan: PLAN-159
---

# PLAN-159 round-1 critique — Performance Engineer

Verified every number below against `.claude/scripts/profile-opus-4-7.py`
(lines 321-326 `_pct_of_sorted`, 358-363 `run_hook_latency`, 554-556 the
only three callers), `.github/workflows/validate.yml:1178-1235`, and the
index arithmetic (re-derived, not repeated from the proposal).

## Verdict

ADJUST

## Summary

- Direction is right — N≈200 makes **p95** a well-estimated statistic
  (10-outlier tolerant) and the in-step retry addresses *sustained*
  contention that a larger N cannot dilute. Keeping the 120/160 ceilings
  is correct.
- But the proposal routes **around** the defect its own evidence names the
  "structural root cause" (the `int()` index collapse) by making N a
  *magic constant*. Nothing enforces the precondition, so a future edit
  lowering `--latency-iterations` silently re-collapses p95==p99 and
  reinstates the flake with zero signal. N has quietly become a
  **correctness** knob, not a precision knob.
- Two measurement-methodology gaps: N=200 is calibrated from **local**
  data for a **CI-only** flake, and the `timeout-minutes: 5→10` bump does
  not cover the worst case (contended N=200 gate **× retry**), which can
  convert a flake into a timeout.

## Risks

**R1 — N is an unguarded correctness parameter.** MEDIUM→HIGH.
`_pct_of_sorted` at N<22 puts p95 and p99 on the *same* order statistic
(verified: N=20→idx 18/18, N=21→19/19; they first separate at **N=22**,
not the N=26 that `measurements.md §1` states). The proposal keeps the
truncating formula and compensates with N=200. If anyone later lowers the
iteration count for CI speed, the collapse and the 2-contended-sample
flake both return, and the p99 ceiling silently becomes dead code again —
with no failing test to catch it.
*Mitigation:* machine-enforce the precondition (see Must-fix 1). A doc
comment / "index table" is not enforcement.

**R2 — p99 at N=200 remains the fragile link.** MEDIUM→HIGH. Verified
outlier tolerance: at N=200 p95 tolerates 10 samples but **p99 tolerates
only 2** (idx 197 = 3rd-largest of 200). Local N=200 already shows single
samples spiking to 144–207 ms (`measurements.md §3`). On a *contended*
runner, >2 samples above 160 ms is entirely plausible in bursts — which
breaches the p99 hard gate even at N=200. The N bump "separates" p99 from
p95 but does not make p99 *stable*; estimating a 1-in-100 event from 200
samples is inherently high-variance (this is exactly why `perf-profile.yml`
uses N=1000 for its advisory p99). The gate's real robustness gain lives
in p95, not p99.
*Mitigation:* Nice-to-have 2 (demote p99 to advisory, or raise N so p99
tolerates ≥5 outliers).

**R3 — retry can push the job past its own timeout under load.** MEDIUM.
The gate step spawns ~5 entries × ~201 warm runs ≈ 1000 subprocesses.
Local: 76.6 s at 96% CPU (CPU-bound). Under the *sustained* contention
this plan targets (subprocess floor 237–456 ms observed vs ~65 ms local),
1000 spawns × ~400 ms ≈ 6–7 min for **one** attempt; the retry doubles it
to 12–14 min → exceeds a 10-min timeout. The flake would then re-present
as a timeout failure — same red, new cause.
*Mitigation:* Must-fix 2 (size the timeout for 2× the contended gate +
smoke + floor + setup, or cap per-attempt wall-time).

**R4 — "passes deterministically on a contended runner" is overstated.**
MEDIUM. Neither lever helps if the *whole* runner allocation is slow for
its lifetime (both retry windows land in the same bad allocation).
GitHub-hosted `ubuntu-latest` (confirmed `runs-on` at line 1180 — this is
billed, not the self-hosted `Ceo` runner) gives no such guarantee. The
fix is high-*probability*, not deterministic; the Goal wording and the
"3 consecutive green" acceptance are probabilistic evidence, not proof.
*Mitigation:* restate the Goal as "flake probability driven below X on a
contended runner," and keep the deliberate-regression fixture as the
detection proof.

**R5 — standing CI-time/cost tax.** LOW→MEDIUM. This runs on *every* push
and PR. ~9 s → ~2–3 min nominal (up to ~12–14 min contended+retry),
permanently, on billed minutes. Worth an explicit acceptance rather than a
side-effect of the N bump (proposal OQ1 already asks this — good).

**R6 — retry erodes sensitivity in the 1.5–2× gray zone.** LOW. A
marginal regression that sits right at the ceiling can pass on the luckier
of two windows. Acceptable for a *gross*-regression gate, but state it:
the retry trades gray-zone sensitivity for flake immunity by design.

## Must-fix (blocking)

**MF1 — Enforce the percentile precondition in code, don't document it.**
The proposal's own "Percentile formula" open question defers to "leave the
formula, document the index table." Documentation does not prevent the
regression in R1. Do ONE of:
  (a) fix `_pct_of_sorted` to a proper nearest-rank (round-half-up or
      ceil-based) percentile — and note this is **low** blast radius, not
      wide: I verified only **three** call sites exist (lines 554-556, all
      in this one script; `--floor` uses a *separate* percentile path, so
      the fix touches only this gate's own p50/p95/p99 by ≤1 order
      statistic); OR
  (b) if you keep the truncating formula, add a hard precondition at
      gate-run time: assert that the p95 and p99 indices differ (equiv.
      `iterations ≥ 22`) and fail loudly otherwise, so lowering N can
      never silently re-collapse the gate.
Either way, the p95/p99 separation must be a *checked invariant*, not an
operator convention. This is the difference between "fixed" and "fixed
until the next edit."

**MF2 — Size the timeout for the worst case, not the nominal one.**
`timeout-minutes` must cover `2 × (contended N=200 gate)` + smoke + floor
+ checkout/setup — because the retry (MF-adjacent to lever 2) doubles the
most expensive step under the exact contention scenario being fixed (R3).
`5→10` is derived from nominal ~2–3 min and does not carry the retry.
Either set the timeout from measured contended cost (≈15 min) or bound
each attempt with a per-attempt wall-clock cap so two attempts fit the
budget deterministically.

**MF3 — Calibrate N on the runner before the ceremony, not only locally.**
The flake is a CI-runner phenomenon that does not reproduce locally; every
N=200 number in `measurements.md §3` is from the maintainer workstation.
Choosing the gate parameter of a CI-only flake from local data is the
skill's named anti-pattern ("never profile with small data sets / off the
production surface and claim readiness"). Before spending the sentinel
ceremony, run a scratch-branch push at N=200 (and ideally N=500) on the
actual `ubuntu-latest` runner, preferably during a busy window, and record
the CI-side p95/p99/max distribution. Wave 2 validates the *chosen* N
after landing — move that measurement *before* Wave 1 so a wrong N doesn't
cost a second ceremony. (This also supplies the CI-side evidence the Wave-1
ADR needs to assert an "N≥200 for percentile stability" rule on its own
data, per `measurements.md §4`.)

## Nice-to-have (advisory)

- **NH1 — consider a contention-robust statistic instead of brute-force N.**
  A trimmed/winsorized p95 (drop the top ~5% before ranking) or a
  `median × factor` gate reaches the same burst-immunity at a *fraction*
  of N=200's cost — the `--floor` gate already relies on the
  contention-robust p50 (`measurements.md §5`). N=50-trimmed could give
  ~90% of the robustness at ~25% of the standing CI tax (R5). Worth a
  round-2 comparison before committing to 200 raw iterations forever.
- **NH2 — demote p99 to advisory (`::notice`) and hard-gate on p95 only**,
  given R2 (p99 stays 2-outlier-fragile at N=200). Alternatively raise N
  to ~500 so p99 tolerates ≥5 outliers (verified). Hard-gating on the
  well-estimated statistic (p95) and observing the noisy one (p99) is the
  cleaner methodology than hard-gating both when only one is stable.
- **NH3 — fix the arithmetic slip in `measurements.md §1`:** p95/p99
  indices first separate at **N=22** (`int(21×0.95)=19`, `int(21×0.99)=20`),
  not N=26. The 23/24 indices quoted for N=26 are correct; only the "first
  N where they separate" label is wrong. Minor, but it is percentile-index
  arithmetic in the evidence file and should be right.

## Unseen by the original plan

- **U1 — detection sensitivity is NON-UNIFORM across corpus entries.** The
  ceiling is one absolute (120 ms) but baselines differ: output_secrets
  p95 ≈ 76 ms → detection threshold 120/76 ≈ **1.6×**, while
  check_agent_spawn / anti_ceo p95 ≈ 55 ms → 120/55 ≈ **2.2×**. So "still
  catches a genuine 2× regression" is not uniformly true: a clean 2.0×
  regression on the *lowest-baseline* entry (55→110 ms) slips **under**
  the 120 ms ceiling and passes. The gate catches the cited PLAN-120 WS-J
  2.27× only barely on that entry (55×2.27 ≈ 125 > 120). If uniform 2×
  detection is the real contract, per-entry relative ceilings
  (baseline × 1.8) would deliver it; a single absolute ceiling cannot.
  (Note: the N bump does not *change* this — it was already true at N=20 —
  but the plan claims "detection contract preserved" without acknowledging
  the contract was already non-uniform.)
- **U2 — N is a correctness parameter, not just precision** (drives MF1).
- **U3 — the retry interacts with the timeout** (drives MF2); the plan
  treats the two levers as cost-independent, but lever 2 multiplies
  lever 1's worst-case wall-time.

## What I would NOT change

- **Keep the 120/160 ceilings.** Correct — local + clean-runner p95 at
  N=200 sits ≤ 76 ms; no data justifies loosening, and loosening erodes
  the gross-regression contract. Lever 3 correctly left unexercised.
- **In-step plain-shell retry over a third-party retry action.** Correct:
  no new supply-chain surface, exactly 2 bounded attempts, `::warning`
  logged. My only ask is that its *cost* be carried into the timeout (MF2).
- **N≈200 as the order of magnitude for p95.** Right direction — p95
  becomes 10-outlier tolerant and well-estimated. My adjustments are about
  *guarding* it (MF1), *validating it on the runner* (MF3), and being
  honest that *p99* needs more (R2/NH2) — not about the ~200 target for
  p95 itself.
- **The Wave-2 deliberate-regression fixture as a hard acceptance
  criterion.** Exactly right and non-negotiable: detection survival must
  be *demonstrated* on the new settings, not assumed. This is the
  "measure the distribution, not the anecdote" discipline applied to the
  loosening itself — do not drop it.
