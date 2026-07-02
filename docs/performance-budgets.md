# Performance budgets — ceo-orchestration

> Status: **PLAN-019 Phase 2 Wave 2A** (Perf-P1-004). Expands the single-
> dimension `performance-baseline.md` into an N-dimension budget table so
> that every class of perf risk has a named target, a named measurement,
> and a named gate (or an honest "doc-only" marker).

## Why N dimensions

Historical framework budgets lived entirely in `docs/performance-baseline.md`
and covered **one** dimension only: per-hook p99 latency. That single
number hides five real performance risks the adopter has already asked
about:

1. A single `Edit` tool call chains **thirteen** hooks — 10 PreToolUse
   (`check_plan_edit`, `check_canonical_edit`, `check_pair_rail`, plus
   7 more) + 3 PostToolUse (`check_output_secrets`,
   `check_skill_bootstrap_post`, `accel_dispatch`). The p99 of each
   alone does not capture the distributed stall the agent actually
   experiences.
2. `audit-query.py` was built on `list(read_entries(...))` and degrades
   from imperceptible to seconds-long as the log grows past 100k entries.
3. `audit-dashboard.py` loaded the whole log into RAM on every SSE
   connect. Four concurrent connections at 100 MB log meant ~400 MB
   resident memory for a "read-only" dashboard.
4. `install.sh` wall-clock is part of the install experience; large
   target trees (1000+ files) spent most of the time in the skills copy.
5. Test-suite wall-clock gates whether CI stays green — when hooks add
   100 ms each, 3000 tests compound.

This document tabulates those five + three supporting dimensions so
Sprint 15+ perf work, and any PR that touches a measurable path, can
reason about which dimension they moved.

## Budget table (N = 8)

| Dimension | Target | Measurement | Gate |
|-----------|--------|-------------|------|
| Per-hook p99 latency | **<20 ms** | `hook-profiler.py` (default `--mode=per-hook`) single-hook warm p99 | ADR-024 (advisory state 0; state-flip criteria documented) |
| Distributed chain (Edit → 13 hooks, spawn → 9, etc.) | **<600 ms** p99 aggregate on `Edit`/`Write` | `hook-profiler.py --mode=per-tool-call` — aggregate row | proposal — ADR deferred, target v1.0.2+ (see Distributed-chain note) |
| `audit-query.py` materialization (100 k events) | **<500 ms** wall-clock for streamable subcommands | `test_audit_query.TestStreamingPerformance.test_100k_summary_streams_under_500ms` | PR-gate (Python-tests step of `validate.yml`) |
| `audit-query.py` large-log warn threshold | 100 k entries emit `[audit-query] NOTE:` to stderr | `test_audit_query.TestMaterializationWarning` | PR-gate |
| `audit-dashboard.py` SSE connect RAM | **<5 MB** additional resident memory at 50 MB log | `test_audit_dashboard.TestSSEMemoryFootprint.test_50mb_log_tail_under_5mb` | PR-gate |
| `install.sh` wall-clock (clean target) | **<10 s** | existing smoke-install | smoke (post-merge) |
| `install.sh` at-scale (1000-file target) | **<30 s** | none yet | doc-only |
| Full test suite wall-clock (hooks + scripts + integration) | **<4 min** | `validate.yml` Python-tests step duration | wall-clock gate (CI failure at >5 min) |
| Memory ceiling per hook invocation | **<50 MB** peak RSS | none yet | doc-only |

### Row-by-row notes

- **Per-hook p99.** Owned by ADR-024 already. `hook-profiler.py` runs
  the legacy per-hook distribution by default; nothing about the
  per-tool-call addition changes that contract. Only state-flip via
  ADR-024 can turn this advisory gate into a blocking one.
- **Distributed chain.** This is the one the adopter *feels*. A
  `check_plan_edit` p99 of 18 ms, a `check_canonical_edit` p99 of
  20 ms and a `check_pair_rail` p99 of 15 ms each look fine, but the
  sequential chain an `Edit` triggers can sit at ~200 ms p99 on a
  laptop and ~400–500 ms p99 on a warm `ubuntu-latest` runner. The
  <600 ms target assumes a 50% headroom over laptop-measured p99 and
  is intentionally generous — the budget is there to catch
  ~10× regressions, not to micro-tune.
  *Deferral note (PLAN-152 Wave E, v1.0.1):* the aggregate
  per-tool-call latency gate still has no owning ADR. That deferral is
  recorded here deliberately — no new ADR file ships in v1.0.1; target
  v1.0.2+ for promoting this row from "proposal" to a gated ADR.
- **audit-query streaming.** `audit-query summary` on a synthetic
  100 k-entry log takes <500 ms after Perf-P1-002. Subcommands that
  genuinely need full context (median / percentile / debate-grouping)
  still materialize, but now emit a stderr hint and are covered under
  the warn-threshold row above.
- **Dashboard RAM.** Previous behaviour: `log.read_text().splitlines()`
  loaded 100 MB into 100+ MB resident; four concurrent connections →
  ~400 MB. New behaviour: bounded reverse-scan reads 64 KiB chunks from
  EOF until `n` lines found. Additional RAM per connect is O(n ×
  avg_line_size), not O(file_size).
- **install.sh.** The clean-target measurement is part of the
  smoke-install workflow. At-scale (1000 files) is documentation only —
  an adopter with a monorepo needs an expectation, but we do not
  currently have a dedicated CI job for it.
- **Full-suite wall-clock.** `validate.yml` emits the Python-tests step
  duration; any PR that pushes it past 5 min fails. Current baseline
  (Session 29, 2 424 tests) sits around 2–3 min depending on runner.
- **Per-hook memory.** `_build_env` uses an allowlist so nothing
  about the hook subprocess should retain more than its own parse +
  emit path. This is currently doc-only because the subprocess
  tear-down masks peak-RSS sampling — adding a meaningful gate would
  require the `resource` module with OS-specific code paths.

## How to measure locally

```bash
# Per-hook (legacy default)
python3 .claude/scripts/hook-profiler.py --samples 500 --warmup 50 \
    --format table

# Per-tool-call (Perf-P1-001)
python3 .claude/scripts/hook-profiler.py --mode=per-tool-call \
    --samples 500 --warmup 50 --format table

# audit-query streaming performance
python3 -m pytest .claude/scripts/tests/test_audit_query.py \
    -k TestStreamingPerformance -q

# audit-dashboard SSE memory footprint
python3 -m pytest .claude/scripts/tests/test_audit_dashboard.py \
    -k TestSSEMemoryFootprint -q
```

## Revisit conditions

Upgrade a "doc-only" row to a PR-gate row when:

- the row has a recurring-regression history (≥2 PRs in 3 months
  that violated the target unnoticed), OR
- Sprint 16 (SOTA polish) explicitly slots it for graduation, OR
- an adopter in Sprint 15 surfaces a friction note anchored on the row.

Downgrade a gate to doc-only only via an ADR that records what changed
and why the guarantee no longer holds.

## Related

- `docs/performance-baseline.md` — the single-dimension per-hook
  baseline this table extends.
- `.claude/adr/ADR-024-perf-profile-gate-evolution.md` — state machine
  governing the per-hook gate.
- `.claude/scripts/hook-profiler.py` — measurement tool for rows 1 & 2.
- `.claude/scripts/audit-query.py` — measurement tool for row 3 & 4.
- `.claude/scripts/audit-dashboard.py` — measurement tool for row 5.
