---
plan: PLAN-159
round: 1
rounds_synthesized: [round-1]
agents_considered: [performance-engineer, devops-engineer, security-engineer]
verdicts: {performance-engineer: ADJUST, devops-engineer: ADJUST, security-engineer: ADJUST}
decisions_revised_in_plan:
  - "§Approach lever 2 — per-attempt 420s cap + if-form + explicit exit 1 + step-summary publishing"
  - "§Approach lever 1 — profiler hardening (index-collapse precondition, TimeoutExpired fold, default N=200)"
  - "§Approach — job timeout 5→16min (contended 2×cap + overhead, not nominal)"
  - "§Goal — 'deterministically' reworded to the honest probabilistic contract"
  - "§Waves W1 — touch set + gates updated (profiler + unit tests + mirror proof)"
  - "§Waves W2 — regression criterion reworded ('over-ceiling', through-wrapper) + retry-retirement review"
  - "§Open questions — OQ1 resolved mix recorded; OQ2/OQ3 answered with critic input"
synthesized_at: 2026-07-15T17:20:00Z
synthesized_by: CEO
round_verdict: PROCEED
---

# PLAN-159 round-1 consensus

Synthesis input: the three critiques anonymized as Critic-A/B/C
(`anonymization-map.md`). All three verdicts: **ADJUST** — zero REJECT,
zero VETO exercised. Every must-fix was resolved mechanically in this
session and verified (mirror clone + wrapper matrix); details below.

## Consensus findings (2+ critics flagged)

1. **C1 — retry × timeout collision (HIGH).** Critic-A (must-fix) +
   Critic-C (must-fix): the 5→10min job timeout was sized for the
   *nominal* N=200 cost; under the 5–10× contended slowdown one attempt is
   6–13min, so two attempts cannot fit — the retry would be inert exactly
   when needed, and the fast flake becomes a slow timeout-fail.
   **Adopted:** per-attempt `timeout 420` wall-cap (≈5.5× the measured
   76.6s local N=200 cost) + job `timeout-minutes: 16` (2×7min + smoke +
   floor + setup). Basis recorded in ADR-163. Lands in the staged
   validate patch.
2. **C2 — retry must fail closed, proven through the wrapper (HIGH).**
   Critic-B (must-fix) + Critic-A (risk): a loose shell wrapper under
   `set -euo pipefail` can silently demote the hard gate
   (`continue-on-error` by accident). **Adopted:** `if ! run_gate`-form,
   exactly 2 attempts hardcoded, explicit `exit 1` on double failure
   (never implicit `$?`), attempt-1 failure `::warning`-logged.
   **Proven:** the wrapper matrix (pass@1 / fail@1+pass@2 / fail-both) was
   executed against the REAL step text extracted from the patched YAML —
   exits 0/0/1 as required. Wave-2 fixture reworked to run THROUGH the
   wrapper (`wave2-regression-proof.sh`).
3. **C3 — green-on-attempt-2 masks drift (MEDIUM).** Critic-A (risk) +
   Critic-C (risk, gray-zone sensitivity): a code drift toward the ceiling
   hides behind a green check. **Adopted:** `publish()` appends per-entry
   p50/p95/p99/max of EVERY attempt to `$GITHUB_STEP_SUMMARY` (advisory
   path, `|| true` allowed there only); rising attempt-1-failure frequency
   on unregressed code is the documented drift signal (ADR-163).
4. **C4 — "catches 2×" is non-uniform under an absolute ceiling.**
   Critic-C (unseen) + Critic-B (unseen): detection threshold is per-entry
   (120/55 ≈ 2.2× on the fastest hook; 120/76 ≈ 1.6× on the slowest); a
   clean 2.0× on `check_agent_spawn` (55→110ms) passes. Pre-existing, not
   introduced here. **Adopted:** success criterion reworded to "an
   injected over-ceiling regression still RED-flags (through the retry
   wrapper)"; the per-entry sensitivity table is recorded in ADR-163;
   per-hook relative ceilings declared out of scope for a flake fix.

## Single-agent insights kept

- **K1 (Critic-C must-fix) — machine-enforce the percentile precondition.**
  Adopted as the critic's own option (b): `run_hook_latency` now
  fail-louds (`percentile_indices_collapsed`, passed=False, BEFORE any
  subprocess) whenever `int((n-1)·0.95) == int((n-1)·0.99)` (true for all
  n<22), and the default N is 200. The formula itself is untouched —
  which resolves the conflict with Critic-B's explicit "do not fix
  `_pct_of_sorted` in this plan". 9 unit tests staged
  (`test_profile_opus47_latency_gate.py`), 9/9 green in the mirror clone.
- **K2 (Critic-C must-fix) — calibrate on the CI runner BEFORE the
  ceremony.** Adopted with an adjusted mechanism: a scratch-branch N=200
  gate run is impossible without editing a guarded workflow (the exact
  edit the ceremony authorizes), so the CI-side evidence comes from the
  `perf-profile.yml` hook-profiler artifacts (N=1000, ubuntu-latest)
  captured DURING the contended S273 window (2026-07-14 13:00/13:16 UTC):
  p95 sits 4–10% above p50 and a 414ms max spike (3.3×p50) is absorbed —
  high-N percentiles are stable on the real runner under the real
  contention. A fresh dispatch was fired for today's datapoint. Residual
  wrong-N risk is covered by the recorded single-revert rollback (no
  second ceremony needed to back out).
- **K3 (Critic-B must-fix) — anti-vacuity control must arm at N=200.**
  Evidence captured: both local N=200 runs show
  `observe_positive_control{required:true, rows:201, paired_rows:201,
  passed:true}` and both negative arms at 0 (measurements.md §3b). ADR-163
  forbids ever relaxing the `>= iterations` row assertion to a cap.
- **K4 (Critic-B advisory) — ADR states the exactly-2-attempts invariant,
  the "this gate is not a malicious-behaviour detector" clarification, and
  that `CEO_SOTA_DISABLE` is never a sanctioned flake workaround.** Adopted.
- **K5 (Critic-A unseen) — record the runner constraint** (perf gates are
  never routed to the self-hosted `Ceo` runner; prior billing-window
  incidents). Adopted in ADR-163.
- **K6 (Critic-B risk/advisory) — fold `subprocess.TimeoutExpired` into the
  fail-closed `hook_failed` sink** (clean report instead of a traceback at
  high N). Adopted; unit-tested.
- **K7 (Critic-C nice-to-have) — measurements.md arithmetic slip.**
  Verified and fixed: p95/p99 indices first separate at **N=22**
  (`int(21·0.95)=19 ≠ int(21·0.99)=20`), not N=26.
- **K8 (Critic-A risk) — concurrency guard for stacked N=200 runs.**
  Verified already present: `validate.yml:11` has a top-level
  `concurrency:` block. No action needed.

## Single-agent insights rejected / deferred

- **D1 (Critic-C) — trimmed/winsorized percentile at lower N.** DEFERRED:
  post-land Wave-2 data may motivate it; raw N=200 keeps the current
  semantics and the change surface minimal now.
- **D2 (Critic-C) — demote p99 to advisory, or N=500.** REJECTED for this
  plan: hard p99 restores a contract that was dead code at N=20 (Critic-B
  counts that reactivation a security positive); the cap+retry+summary
  triad covers the 2-outlier fragility; revisit with Wave-2 evidence.
- **D3 (Critic-A) — retire the retry if Wave-2 shows N=200 alone
  suffices.** DEFERRED to the Wave-2 post-land review, recorded in the
  plan (if the retry never fires across the acceptance window, its removal
  shrinks the drift-masking surface).
- **D4 (Critic-A / Critic-C option a) — fix the `_pct_of_sorted` `int()`
  formula.** REJECTED this plan: Critic-B explicitly scoped it out (wider
  behavioural blast radius); the K1 precondition machine-covers the defect
  class without changing percentile semantics.

## Plan adjustments

Index only — the edits live in the plan file + staged artifacts:
§Approach (levers detailed + profiler hardening + timeout 16), §Goal
(probabilistic wording), §Waves W1 (touch set + gates), §Waves W2
(criterion + through-wrapper + retry review), §Open questions (OQ1 mix,
OQ2/OQ3 with critic input). Staged: `validate-yml.patch` (regenerated),
`profile-opus-4-7.py` (3 changes), `test_profile_opus47_latency_gate.py`
(new), ADR-163 (updated), `land-plan159.sh`, `wave2-regression-proof.sh`.

## Round verdict

**PROCEED** — recorded as `design-coherent` (internal coherence under
forced perspectives; PLAN-134 W1 demotion applies). This does NOT
authorize shipping: V1 (tests/CI) partially in evidence, V2 Codex
pair-rail REQUIRED on the staged diff before the ceremony (the land
script fails closed without a GO verdict), V3 Owner GPG ceremony is the
ship authorization. OQ1–OQ3 go to the Owner for ratification at
`draft → reviewed`.
