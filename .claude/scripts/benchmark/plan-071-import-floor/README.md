# PLAN-071 Phase 0.5 — Import-floor benchmark

Pre-implementation baseline that makes Phase 1 acceptance gate
(`p95 < 200ms` per §5.3) mechanically falsifiable.

## Modes — advisory vs gate (P1-08 + R3-03 closure)

The benchmark runs in **two modes**:

| Mode       | Behavior                                                     | Wrapper exit code             |
|------------|--------------------------------------------------------------|-------------------------------|
| `advisory` (default) | record + print results; verdict is informational | **`0` ALWAYS** regardless of gate verdict |
| `gate`     | compare against recorded baseline; fail on regression       | `0` on PASS, `1` on FAIL      |

**R3-03 closure (Codex 2026-05-04):** The wrapper `run_bench.sh`
previously read `acceptance_gates.overall` from the JSON envelope and
exited 1 on FAIL **regardless of mode**, violating advisory semantics.
Fixed: the wrapper now reads the top-level `mode` field from the JSON
envelope and exits 0 unconditionally when `mode == "advisory"`. Gate
mode preserves PASS=0 / FAIL=1.

**Why advisory by default?** macOS Python 3.9 cold interpreter floor is
~22ms; the absolute aspirational thresholds in
`fixtures/expected_quantiles.json` (p50 ≤ 5ms, p99 ≤ 10ms) are below
that floor. Hard-fail on absolute thresholds would block CI on the
floor, not on a regression. Advisory captures the actual baseline so
gate-mode can detect regression deltas later.

### Verifying advisory vs gate exit semantics

```bash
# Advisory (default) — always exits 0 even when gates would FAIL
bash run_bench.sh --n 5
echo $?  # expect: 0

# Gate (no baseline recorded yet → absolute thresholds → FAIL on macOS)
bash run_bench.sh --n 5 --mode=gate
echo $?  # expect: 1

# Gate with recorded baseline — exits 0 if no >5%/>10%/>15% regression
BASELINE_JSON=fixtures/baseline.json bash run_bench.sh --n 5
echo $?  # expect: 0 (or 1 if regression detected)
```

## How to run

```bash
# Advisory (default, N=200, ~5-15s wall-clock)
python3 import_floor_bench.py
python3 import_floor_bench.py --report                  # markdown

# Convenience wrapper — defaults to advisory
bash run_bench.sh
bash run_bench.sh --report

# Record an empirical baseline first (one-time, on each runner class)
python3 import_floor_bench.py \
    --mode=advisory \
    --write-baseline=fixtures/baseline.json

# Gate mode (after baseline is recorded)
python3 import_floor_bench.py \
    --mode=gate \
    --baseline=fixtures/baseline.json

# Wrapper opts into gate mode via env var
BASELINE_JSON=fixtures/baseline.json bash run_bench.sh
```

Exit codes:

- Advisory mode: `0` always (unless CLI/subprocess error returns `2`)
- Gate mode: `0` on PASS, `1` on any gate fail, `2` on CLI error

## Delta-mode thresholds (gate mode)

| Metric         | Tolerance vs baseline      |
|----------------|----------------------------|
| `p50_ms`       | +5%                        |
| `p99_ms`       | +10%                       |
| `p99_9_ms`     | +15%                       |
| `rss_delta_kib`| +25%                       |
| `gc_events`    | == 0 (hard invariant)      |

## RSS measurement (P1-07 closure + R3-bis tighten)

Imports happen in the CHILD subprocess. The parent harness CANNOT
observe child memory growth via its own `getrusage(RUSAGE_SELF)` —
that returns parent's RSS. The probe scripts now sample
`getrusage(RUSAGE_SELF).ru_maxrss` BEFORE and AFTER the under-test
imports IN THE CHILD and emit a JSON envelope:

```
{"ok": true,
 "interpreter_startup_rss_kib": <float>,  # RSS at probe-entry (Python bootstrap dominant)
 "rss_after_kib":              <float>,   # RSS after under-test imports
 "rss_delta_kib":              <float>}   # rss_after - interpreter_startup
```

**R3-bis tighten (Codex 2026-05-04):** the field formerly named
`rss_before_kib` was renamed to `interpreter_startup_rss_kib` to make
explicit that this sample is the high-water RSS AT PROBE ENTRY — i.e.
*after* Python interpreter bootstrap completed but *before* any
under-test imports run. `ru_maxrss` is a high-water mark; the very
first sample inside the probe body cannot precede the interpreter's
own bootstrap. The probe script restructures sampling order so:

1. Step 1: import the minimal trio needed for measurement
   (`sys`, `json`, `resource`) — keeps bootstrap floor as low as possible.
2. Step 2: sample `interpreter_startup_rss` IMMEDIATELY (no further
   imports above this line).
3. Step 3: run the under-test imports.
4. Step 4: sample `rss_after`.
5. Step 5: emit envelope with both absolute values and the delta.

`rss_delta_kib` isolates the import RSS attributable to the under-test
imports ONLY IF the interpreter bootstrap fully stabilized before the
first sample. Both absolute values are disclosed for transparency so
reviewers can sanity-check the bootstrap floor against documented
baselines (~10-12 MiB on macOS Python 3.9; ~8-10 MiB on Linux).

Parent reads the envelope and reports the median per-iteration delta
as `full.rss_kib_delta` (and `full.rss_kib_delta_p95`). Median absolute
values are surfaced as `full.interpreter_startup_rss_kib` and
`full.rss_after_kib`. The legacy parent-side measurement is retained
as `rss_kib_delta_parent` (diagnostic only).

## Methodology

- **Subprocess-per-iter (cold).** Every iteration spawns a fresh
  `sys.executable` interpreter. Rationale: ADR-081 token-as-time-unit
  + PLAN-020 Sprint 32 measured ~23 ms macOS interpreter floor;
  CEO will invoke `task-route.py` once per task (R-PERF1 / S1) so cold
  is the operational path.
- **`time.perf_counter_ns()`** for ns-precision wall-clock.
- **N=200** per condition (ADR-071 §3 — N≥10 minimum; 200 brings
  p99 / p99.9 into trustable range).
- **Two probes**: (a) stdlib-only baseline; (b) baseline + import
  `tier_policy._constants` + `tier_policy._types`. Delta isolates
  Phase 1 module cost.
- **RSS** via `getrusage(RUSAGE_SELF).ru_maxrss`, platform-normalized
  (macOS returns BYTES → divide by 1024; Linux returns KiB as-is —
  Codex S82 P1 fix, mirrors `ceo-boot.py:1083`).
- **GC** counts pre/post (`gc.get_count()`). Hard invariant
  `gc_events == 0` enforces zero allocation pressure during import.
- **Env hardened**: `PYTHONDONTWRITEBYTECODE=1` + `PYTHONHASHSEED=0`;
  strip `PYTHONSTARTUP` / `PYTHONSITECUSTOMIZE` to remove user-site
  contamination.
- **NOT instrumented**: `task-route.py`. Phase 0.5 measures the floor
  BEFORE Phase 1 implementation.

## Acceptance thresholds (`fixtures/expected_quantiles.json`)

| Gate                 | Threshold | Rationale                                  |
|----------------------|-----------|--------------------------------------------|
| `p50_ms`             | ≤ 5.0     | warm-OS floor budget for full probe         |
| `p99_ms`             | ≤ 10.0    | tail budget; 200 ms Phase 1 has 20× slack   |
| `p99_9_ms`           | ≤ 50.0    | extreme-tail; CI cold-disk variance bound   |
| `rss_delta_kib`      | ≤ 2048    | 2 MiB import-time RSS ceiling               |
| `gc_events`          | == 0      | hard: no GC during import                   |
| `full_failures`      | ≤ 5       | tolerate ≤ 2.5% subprocess flakes           |

## Failure interpretation

| Symptom                          | Likely cause                                  |
|----------------------------------|-----------------------------------------------|
| `p99_ms` > 10                    | import-cost regression in `tier_policy/`      |
| `p50_ms` > 5                     | warning: floor degrading; investigate         |
| `gc_events` > 0                  | allocation pressure in module-level code      |
| `full_failures` > 5              | subprocess crash — check `failures` array     |
| `rss_delta_kib` > 2048           | import-time global blow-up                    |
| `delta.p95_ms` > baseline by 3×  | tier_policy adds disproportionate cold cost   |

## When to re-run

1. Any change to `tier_policy/_constants.py` or `_types.py`.
2. Python minor version upgrade (3.9 → 3.10 etc.).
3. CI runner class change (e.g. `macos-13` → `macos-14`).
4. New module added to the import chain (update probe + fixture).
5. Quarterly drift check (commit refreshed `baseline.json`).

## macOS clock-resolution caveat

`time.perf_counter_ns()` resolution on macOS is ~42 ns; ample for
ms-scale measurements. GitHub Actions macOS runners typically add
40-80 ms cold-start overhead vs local dev (S77 lesson; ADR-071 §3).
The CI budget for Phase 1 (`p95 < 300ms`) bakes this 50% headroom in.

## Output schema

JSON output schema_version=1: top-level keys
`platform / methodology / baseline / full / delta / acceptance_gates /
expected_quantiles_source / n`. `acceptance_gates.overall` is the
pass/fail bool that drives the wrapper exit code.
