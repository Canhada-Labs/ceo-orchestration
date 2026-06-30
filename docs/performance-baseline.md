# Performance baseline — CEO Orchestration hooks

> Status: **advisory, measure-only** (ADR-024 state 0).
> Measured: 2026-04-14 on local macOS (Darwin 25.4, Python 3.9, MacBook).
> CI baseline will differ — ubuntu-latest is a shared VM with ±40%
> documented variance on micro-benchmarks. See §Variance.

This document captures the first full-run performance baseline for
every active hook in `.claude/hooks/`. It exists so that Sprint 11 can
decide **whether** to convert the advisory `perf-profile.yml` workflow
into a blocking gate, and if so at **what** threshold — grounded in
real measurements, not in a thin-air 50 ms target.

## Methodology

### What we measure

For each of the six active hooks we run the canonical happy-path
fixture (`.claude/hooks/tests/fixtures/hooks/<hook>/in.json`) through
`subprocess.run([python3, <hook>.py], input=<payload>, env=<isolated>)`.
Wall-clock is captured with `time.perf_counter_ns()` (monotonic, ns
resolution).

- **N = 1000 samples per hook.**
- **First 100 samples discarded as warm-up** (OS page cache, Python
  import cache, CPU frequency scaling all stabilize inside this
  window).
- **Cold start** is measured separately and reported as a distinct
  column (sample #1 of the 1000, representing the very first
  `subprocess.run` after a fresh fork — the worst case a user sees).
- **Percentiles** via nearest-rank on the sorted warm sample set
  (N=900). No interpolation — matches `hey`, `vegeta`, and most
  RED-metrics tooling.
- **IQR** (p75 − p25) reported as a spread indicator independent of
  tail outliers.

### Isolation

Every profiler run builds a fresh tempdir and passes it via
`HOME=<tempdir>` and `CLAUDE_PROJECT_DIR=<tempdir>` to the subprocess
env. The real `~/.claude/projects/ceo-orchestration/audit-log.jsonl`
is **never** appended to during profiling. This is enforced by a test
(`TestIsolation.test_default_tempdir_is_created_and_cleaned_up`)
that snapshots the real file's size before and after.

`CEO_CONFIDENCE_ENFORCE` and `CEO_CONFIDENCE_BYPASS` are explicitly
stripped from the subprocess env so inherited Owner shell state does
not alter measurements.

### Variance source

- **ubuntu-latest GitHub Actions runners** have well-documented
  variance of roughly ±40% on short-running micro-benchmarks, driven
  by noisy-neighbour CPU contention on shared hypervisors. Any single
  CI run is **not** a trustworthy number. ADR-024 requires three
  consecutive weekly runs with stable p99 (within 20% week-over-week)
  before any gate discussion.
- **Local dev machines** have much lower variance (~5–10%) but different
  absolute numbers. Use local for debugging regressions, CI for
  baseline setting.

## Local baseline (2026-04-14, macOS, Python 3.9, N=1000)

| Hook | Cold (ms) | Warm p50 (ms) | Warm p95 (ms) | Warm p99 (ms) | IQR (ms) | N |
|------|-----------|---------------|---------------|---------------|----------|---|
| check_agent_spawn | 139.78 | 38.58 | 40.85 | 43.95 | 1.88 | 900 |
| audit_log | 40.06 | 38.82 | 41.36 | 49.01 | 2.11 | 900 |
| check_bash_safety | 34.54 | 34.24 | 36.78 | 42.75 | 1.93 | 900 |
| check_plan_edit | 40.67 | 39.13 | 41.92 | 48.14 | 1.81 | 900 |
| check_read_injection | 33.82 | 33.59 | 36.22 | 45.30 | 1.68 | 900 |
| check_canonical_edit | 60.73 | 34.11 | 50.85 | 60.99 | 2.28 | 900 |

### Observations

- **Dominant cost is Python import, not logic.** p50 clusters in the
  30–40 ms band across hooks, regardless of complexity. This is
  expected: every invocation pays `python3` startup + `_lib` import
  cost, which dwarfs the ~1 ms of actual decision logic.
- **check_agent_spawn cold start is the anti-outlier at 139.78 ms.**
  Warm is 38.58 ms. The gap is the one-time fixture path resolution +
  `_lib/adapters/claude.py` import. All subsequent invocations benefit
  from the filesystem page cache. On a cold CI runner, expect every
  hook to look "cold" on its first sample — the warm-up discard is
  exactly what filters this.
- **check_canonical_edit p99 (60.99 ms) is the widest tail.** Drill-
  down (Sprint 11): the sentinel-list walker reads several .md files;
  disk cache misses widen the distribution. Still well under the
  hypothetical 200 ms "wedging the session" boundary.
- **IQR is narrow (1.6–2.3 ms) across all hooks** → the distribution
  is tight with a small fat tail. This is the signature of a
  Python-startup-bound workload under a quiet machine. On ubuntu-latest
  IQR will widen.

### Cold start interpretation

Cold start is reported **per profiler invocation**, not **per user
session**. In production a user session may see cold-start latency on
the first hook of each tool-use, then warm cost for subsequent hooks
in the same process family. Neither the framework nor the profiler
can measure the genuine "first hook in a session" latency from a
single-process profiler — that requires a multi-session harness which
is explicit non-goal for Sprint 10.

## CI baseline — pending

The `.github/workflows/perf-profile.yml` workflow will run this profiler
weekly (cron: Monday noon UTC) and on manual `workflow_dispatch`. The
first three runs will populate the CI baseline table below. ADR-024
forbids drawing any threshold conclusions before week 3.

| Week | Commit | check_agent_spawn p99 | audit_log p99 | check_bash_safety p99 | check_plan_edit p99 | check_read_injection p99 | check_canonical_edit p99 |
|------|--------|----|----|----|----|----|----|
| W1   | —      | pending | pending | pending | pending | pending | pending |
| W2   | —      | pending | pending | pending | pending | pending | pending |
| W3   | —      | pending | pending | pending | pending | pending | pending |

## Reproducing locally

```bash
cd /path/to/ceo-orchestration

# Full baseline (~1-2 minutes depending on machine)
python3 .claude/scripts/hook-profiler.py --samples 1000 --warmup 100 --format=table

# JSON for diffing / tooling
python3 .claude/scripts/hook-profiler.py --samples 1000 --warmup 100 --format=json > baseline.json

# Single hook drill-down
python3 .claude/scripts/hook-profiler.py --hook check_canonical_edit --samples 1000 --warmup 100 --format=table
```

The profiler uses a tempdir by default. If you want to inspect what the
subprocess sees, pass `--home /tmp/my-scratch` and poke around after the
run.

## References

- `.claude/scripts/hook-profiler.py` — the measurement tool
- `.claude/scripts/tests/test_hook_profiler.py` — 14 tests covering
  schema, isolation, monotonicity
- `.github/workflows/perf-profile.yml` — weekly CI profiler
- `.claude/adr/ADR-024-perf-baseline-policy.md` — state-0 → state-1
  transition criterion
- `.claude/adr/ADR-019-confidence-gate-enforcement-lifecycle.md` —
  three-state lifecycle precedent (advisory → enforcing)
