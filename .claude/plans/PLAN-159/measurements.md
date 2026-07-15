# PLAN-159 Wave 0 — measurements

> Collected S274 (2026-07-15). Sources: GitHub Actions job logs (job ids below),
> local profiler runs on the maintainer workstation (macOS, Darwin 25.5.0).
> All values are per-corpus-entry WARM percentiles from
> `.claude/scripts/profile-opus-4-7.py --hook-latency` (cold run discarded).

## 1. The percentile-index defect (structural root cause)

`profile-opus-4-7.py:325` computes nearest-rank as:

```python
idx = int((len(lst) - 1) * p / 100.0)
```

| Warm N | p95 index (0-based) | p99 index | Consequence |
|--------|---------------------|-----------|-------------|
| 20 | `int(19×0.95)` = **18** | `int(19×0.99)` = **18** | p95 == p99 == 2nd-largest sample. The p99 ceiling (160 ms) can NEVER fire independently — it gates the identical sample the p95 ceiling (120 ms) already gates. **2 contended iterations out of 20 fail the gate.** |
| 22 | 19 | 20 | first N where p95/p99 separate (`int(21×0.95)=19`, `int(21×0.99)=20`; N=21 still collapses at 19/19). *Corrected S274 — this file first said N=26; debate round-1 caught the slip (consensus K7).* |
| 100 | 94 | 98 | p99 = 2nd-largest again (fragile p99) |
| 200 | 189 | 197 | p95 tolerates 10 outliers, p99 tolerates 2 |

Observed confirmation: **every one of the 6 CI failure reports below has
p95 == p99 for every corpus entry** — exactly the N=20 index collapse.

## 2. CI failure distribution (S272/S273 flake, 6 failed job logs)

Failing commits are doc/shell-only (`f83f74a`, `5f116f2`, `a8838d4c` era) —
no hook or `_lib/` change. Job ids → run/attempt:

| Job id | Run (sha, attempt) | Entry that breached | p95=p99 (ms) | max (ms) | cold (ms) |
|--------|--------------------|---------------------|--------------|----------|-----------|
| 87092662107 | 29335223888 (`a8838d4c`, a1) | output_secrets[observe=unset] / [observe=1] | 174.6 / 183.2 | 179.1 / 205.5 | 87.9 / 72.3 |
| 87375268390 | 29422184444 (`f83f74a`, a1) | output_secrets[observe=1] | 394.0 | 452.9 | 55.9 |
| 87380675705 | 29422184444 (`f83f74a`, a2) | anti_ceo[unset] / output_secrets[unset] / [1] | 186.0 / 645.8 / 697.8 | 417.8 / 747.1 / 938.7 | 439.1 / 242.4 / 131.7 |
| 87381620573 | 29422184444 (`f83f74a`, a3) | — SUCCESS | 63.5–81.1 | ≤81.9 | 63.2–158.4 |
| 87388397461 | 29425989783 (`5f116f2`, a1) | output_secrets[observe=1] | 159.6 | 195.9 | 61.2 |
| 87392971298 | 29425989783 (`5f116f2`, a2) | anti_ceo[unset] / output_secrets[unset] / [1] | 301.7 / 208.3 / 182.8 | 315.8 / 226.4 / 261.2 | 237.7 / 159.7 / 63.1 |

Signal shape: **bursty, not uniform** — `check_agent_spawn` stayed at
45–70 ms p95 in every failing run while a later corpus entry blew past
150–700 ms. Contention arrives in bursts that hit whichever entry is
executing; the same commit's attempt 3 (87381620573) passed with all
entries ≤ 81 ms. `5f116f2` is still RED on main: BOTH attempts flaked.

Corollary: a **bounded step-retry** relocates the whole measurement to a
different scheduling window (works against bursts), and a **larger N**
dilutes the burst inside one window. The two levers are complementary,
not redundant.

## 3. Local baseline (same tree as the failing commits)

### N=20 ×3 runs — all green, p95==p99 as predicted

| Entry | run1 p95 | run2 p95 | run3 p95 |
|-------|----------|----------|----------|
| check_agent_spawn | 51.6 | 56.7 | 51.8 |
| anti_ceo[unset] | 55.2 | 53.5 | 52.7 |
| anti_ceo[1] | 54.1 | 56.5 | 58.2 |
| output_secrets[unset] | 65.3 | 66.8 | 66.1 |
| output_secrets[1] | 67.6 | 69.2 | 64.5 |

### N=200 ×2 runs — stable percentiles, noisy maxima even unloaded

| Entry | r1 p95 / p99 / max | r2 p95 / p99 / max |
|-------|--------------------|--------------------|
| check_agent_spawn | 55.6 / 79.5 / **207.4** | 56.9 / 67.4 / 144.2 |
| anti_ceo[unset] | 60.2 / 80.1 / 139.6 | 57.5 / 63.7 / 92.0 |
| anti_ceo[1] | 63.4 / 82.6 / 104.0 | 58.4 / 95.5 / 142.4 |
| output_secrets[unset] | 72.9 / 92.6 / 150.9 | 67.8 / 76.3 / 98.2 |
| output_secrets[1] | 76.4 / 98.4 / 105.9 | 65.2 / 74.3 / 79.7 |

Key: even on an **unloaded workstation**, individual samples spike to
144–207 ms (OS noise). Any gate keyed to the near-max at small N flakes
*everywhere*; at N=200 the p95 (55–76 ms) and p99 (64–98 ms) sit far
under the 120/160 ceilings with low run-to-run variance.

**Cost of N=200:** 76.6 s wall-clock local (`1:16.62 total`, 96% CPU) vs
~9 s for N=20. CI estimate ≈ 2–3 min. The job also runs `--smoke` (≤30 s)
+ `--floor` (~2 s) + checkout/setup under `timeout-minutes: 5` → N=200
requires bumping the job timeout (pre-debate estimate: 5→10 min —
superseded by the post-debate note below) or choosing N where
p99 remains meaningful (N=200 is the smallest round N with ≥2-outlier
tolerance at p99; N=100 makes p99 the 2nd-largest again).
*Post-debate (consensus C1): the timeout must cover the CONTENDED cost of
TWO capped attempts, not the nominal one — final design: per-attempt
`timeout 420` + job `timeout-minutes: 16`.*

### 3b. Anti-vacuity controls at N=200 (consensus K3 / security must-fix)

Both local N=200 runs, tree WITH the PLAN-154 observe rail:

| Control | run1 | run2 |
|---------|------|------|
| `observe_positive_control` | required=true, **rows=201, paired_rows=201, passed=true** | identical |
| `observe_negative_control` | unset_store_rows=0, pre_side_store_rows=0, passed=true | identical |

The `on_rows >= iterations` assertion scales with N by construction
(parameterized, no store row-cap found in `tool_lifecycle.py`); the
evidence above confirms it ARMS at the new N. ADR-163 forbids relaxing
`>= iterations` to any capped form.

## 4. Citation drift found (must be fixed by the Wave 1 ADR)

`validate.yml:1207` and `.claude/hooks/tests/test_hook_latency.py:33`
both attribute "N≥200 for percentile stability" to **ADR-071**. ADR-071
(benchmark-comparison-methodology) actually mandates **N ≥ 10** runs per
benchmark task; N≥200 appears in ADR-104-AMEND-1 / ADR-019-AMEND-1 /
docs/measurement-protocols.md in *event-count calibration* contexts, not
hook-latency percentiles. The Wave 1 ADR must (a) state the N≥200
percentile rule on its own evidence (this file), and (b) fix both stale
citations.

## 5. OQ3 audit — other perf gates

| Surface | Sampling | Gate? | N=20-class fragility? |
|---------|----------|-------|----------------------|
| validate.yml `--hook-latency` step | N=20 warm | HARD gate | **YES — this plan** |
| validate.yml `--floor` step | p50 of subprocess floor, cap 200 ms | HARD gate | No (p50 is contention-robust; cap has 4× margin) |
| perf-profile.yml | N=1000 weekly | advisory only (`::notice`) | No |
| benchmarks.yml | scenario count/quality gates | no latency percentile gate | No |
| test_hook_latency.py | xfail budget p95 100/p99 150 | advisory (xfail) | No CI risk; carries the same ADR-071 mis-citation (fix in Wave 1) |

## 6. CI-side calibration (consensus K2 / performance must-fix MF3)

A scratch-branch N=200 run of the exact gate is impossible pre-ceremony
(the workflow file is canonical-guarded — the edit IS what the ceremony
authorizes). CI-side evidence instead: `perf-profile.yml` hook-profiler
artifacts (N=1000 warm samples/hook, `ubuntu-latest`, warmup=100),
captured DURING the contended S273 window in which the gate was flaking:

| Hook (run @2026-07-14T13:16Z / 13:00Z) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) |
|---|---|---|---|---|
| check_agent_spawn | 119.7 / 118.8 | 124.9 / 124.7 | 131.7 / 130.7 | 150.9 / **414.0** |
| check_bash_safety | 104.7 / 99.9 | 110.1 / 103.9 | 112.8 / 107.2 | 127.5 / 115.2 |
| check_canonical_edit | 68.2 / 66.6 | 71.2 / 69.0 | 76.6 / 72.5 | 85.8 / 81.4 |
| audit_log | 65.3 / 59.2 | 68.7 / 62.1 | 73.6 / 64.3 | 81.9 / 73.6 |

(Different harness/payloads than the gate — absolute values NOT
comparable to the 120 ms ceiling; check_agent_spawn's ~119 ms p50 here
reflects a heavier payload than the gate's probe.) The calibration
lesson is the SHAPE: on the real runner, during the real contended
window, **high-N p95 sits only 4–10% above p50 and a 414 ms max spike
(3.3× p50) moves p95/p99 not at all.** High-N percentile gating is
stable on the exact infrastructure where the N=20 gate was flaking.
Fresh S274 dispatch (run 29433753166, 2026-07-15T16:53Z) confirms the
shape a third time: p95 within 2.5% of p50, p99 within 5%, a 273 ms max
spike (2.4× p50) absorbed, zero subprocess timeouts across 6 hooks ×
1000 samples. Residual wrong-N risk: covered by the single-revert
rollback recorded in ADR-163 (no second ceremony to back out).

## 7. Final design (post-consensus — ratified mix)

1. **Lever 1 (root):** `--latency-iterations 200` (p99 rank 198 gates
   independently; 10-outlier tolerance at p95) + profiler hardening:
   fail-loud `percentile_indices_collapsed` precondition (min N=22),
   `TimeoutExpired` → fail-closed `hook_failed`, default N 20→200.
2. **Lever 2 (insurance):** single in-step retry, fail-closed by
   construction — `if ! run_gate`-form, exactly 2 attempts, per-attempt
   `timeout 420` wall-cap, explicit `exit 1` on double failure,
   attempt-1 `::warning`, per-attempt percentiles in
   `$GITHUB_STEP_SUMMARY` whenever the attempt left a parseable report
   (explicit no-report note otherwise). Job `timeout-minutes: 16`
   (2×cap + overhead — sized for the contended case, consensus C1).
3. **Lever 3 (ceiling):** NOT exercised — local + clean-runner p95 at
   N=200 is ≤ 76 ms, comfortably under 120. Detection is per-entry vs
   the absolute ceiling (1.6×–2.2× of baseline — consensus C4). Revisit
   only with post-land evidence + ADR amendment.
