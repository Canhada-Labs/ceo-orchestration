---
plan: PLAN-159
round: 1
created_at: 2026-07-15T18:30:00Z
---

# PLAN-159 round-1 proposal — kill the opus-4-7-profiler-smoke load-flake

Full plan: `.claude/plans/PLAN-159-perf-gate-robustness.md`
Wave-0 evidence: `.claude/plans/PLAN-159/measurements.md` (READ IT — every
number below is sourced there).

## Thesis

The CI hard gate "Run profile-opus-4-7.py --hook-latency (p95/p99 gate)"
(`.github/workflows/validate.yml:1203`) flaked 8× across S272/S273 on
doc/shell-only commits. It currently blocks the LAST two Owner ceremonies
of the release train (PLAN-157 data-ml graduation + PLAN-158 GA). The
Owner ratified fixing the gate at the root instead of relying on blind
reruns. `5f116f2` (main tip) is RED on this gate right now — both
attempts flaked.

## Root cause (measured, not hypothesized)

1. **Percentile-index collapse at N=20.** `profile-opus-4-7.py:325` uses
   `idx = int((n-1)*p/100)`. With 20 warm samples: p95 idx = p99 idx = 18
   → **p95 == p99 == 2nd-largest sample**. The p99 ceiling is dead code at
   N=20; 2 contended iterations out of 20 fail the gate. All 6 failure
   logs show p95==p99 for every corpus entry — exact signature.
2. **Bursty runner contention.** In every failing run, `check_agent_spawn`
   (first corpus entry) stayed at 45–70 ms while later entries hit
   159–698 ms; the same commit passed on a rerun attempt with all entries
   ≤ 81 ms. Contention arrives in bursts hitting whatever entry is
   running.
3. **Sample spikes are normal even unloaded.** Local N=200: percentiles
   stable (p95 55–76 ms, p99 64–98 ms) but max hits 144–207 ms on an idle
   workstation. Any near-max gate at small N flakes anywhere.

## Proposal (levers 1+2 of the plan; lever 3 NOT exercised)

1. **`--latency-iterations 20 → 200`** in the validate.yml step (root
   fix). At N=200 the p95 tolerates 10 outlier samples and p99 index
   (197) finally separates from p95 (189). Local cost measured: 76.6 s
   wall (vs ~9 s at N=20); CI estimate 2–3 min → **bump the job
   `timeout-minutes: 5 → 10`** (job also runs --smoke ≤30 s + --floor
   ~2 s + checkout/setup).
2. **Single deterministic in-step retry** (plain-shell loop, exactly 2
   attempts, `::warning`-logged on attempt-1 failure; NO third-party
   retry action → no new supply-chain surface). Complements lever 1:
   larger N dilutes a burst *within* a window; the retry relocates the
   measurement to a *different* scheduling window. A genuine ≥2×
   regression shifts the whole distribution and fails BOTH attempts.
3. **Ceilings UNCHANGED** (p95<120 / p99<160). Local + clean-runner
   evidence at N=200 sits ≤ 98 ms — no data justifies loosening.
   Detection contract preserved: the gate exists to catch gross (≥2×)
   regressions like PLAN-120 WS-J.
4. **ADR (new, or ADR-071 amendment)** recording the incident, the
   measured distributions, the chosen N, and fixing a **citation drift**:
   validate.yml:1207 + test_hook_latency.py:33 attribute "N≥200
   percentile stability" to ADR-071, which actually mandates N≥10 for
   benchmark tasks. The N≥200 rule must stand on this plan's own
   evidence.
5. **Deliberate-regression proof (Wave 2):** a scratch-branch fixture
   injecting a sleep into one hook path must still RED-flag the gate at
   the new settings — detection survival is an acceptance criterion, not
   an assumption.

## Touch set (Wave 1 — sentinel ceremony)

- `.github/workflows/validate.yml` (guarded → sentinel + pair-rail): step
  args, retry wrapper, comment fix, job timeout.
- `.claude/scripts/profile-opus-4-7.py`: NO behavioral change required
  (`--latency-iterations` already a CLI knob). Only touched if the debate
  demands trimmed percentiles or index-formula hardening.
- `.claude/hooks/tests/test_hook_latency.py`: comment citation fix only.
- New ADR / ADR-071 amendment.

## Open questions for this round

- **OQ1:** is N=200 + retry the right mix, or is one of them sufficient?
  Is N=200's CI cost (~2–3 min) acceptable for every push/PR?
- **OQ2 (bootstrapping):** the fixing commit must pass the OLD flaky gate
  to land. Accept one documented bounded rerun for that landing?
- **OQ3:** measurements §5 audited the other perf surfaces — only this
  step has the N=20 fragility. Concur with scoping the fix to this step?
- **Percentile formula:** should `_pct_of_sorted`'s `int()` truncation be
  replaced by proper nearest-rank `ceil` (behavioral change, wider blast
  radius) or left alone and compensated by N=200? CEO default: leave the
  formula, document the index table.

## Critique contract

Produce the 7-section format from DEBATE-SCHEMA.md §4 (Verdict / Summary
/ Risks / Must-fix / Nice-to-have / Unseen / What I would NOT change).
Critique from YOUR skill's perspective. Verify claims against
`measurements.md` and the code before repeating them.
