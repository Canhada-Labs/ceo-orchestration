# Sprint 32 Head-to-Head Benchmark — Fairness Protocol (Pre-Registration)

**Status:** DRAFT (pre-registration per PLAN-051 Phase 5 / ADR-071)
**Committed:** 2026-04-23 (before any benchmark result collection)
**Version covered:** ceo-orchestration v1.9.0
**Supersedes:** none
**Authorized by:** ADR-071 (PROPOSED; ACCEPT at Phase 5 execute kickoff)

> **THIS DOCUMENT IS PUBLISHED BEFORE RUNNING BENCHMARKS.** Any
> post-hoc modification of the protocol is a scientific misconduct
> signal. Modifications after result collection require a SECOND
> pre-registration file with a new date — the previous protocol is
> preserved in git history as the original contract.

---

## 1. Purpose

Provide a falsifiable, reproducible methodology for comparing
ceo-orchestration with public leaderboard scores of competing agent
frameworks (Devin, Codex, Aider, AutoCodeRover, Karpathy's nanoGPT
harness where applicable). Sprint 32 Phase 5 publishes results
under these constraints; deviations are failures, not features.

## 2. Scope — What this benchmark does and does NOT claim

### What it DOES claim
- % of SWE-bench-lite issues resolved end-to-end by ceo-orchestration
  (measured locally, offline, in sandboxed Docker)
- 3 internal differentiator metrics that vendors don't publish
  comparable numbers for: mutation kill-rate, OWASP LLM Top 10
  block-rate (PLAN-039 rubric), governance overhead % vs raw Claude
- Hardware + version + seed disclosure for reproducibility

### What it explicitly does NOT claim
- That the framework is "SOTA of performance" (category error —
  performance has no SOTA absolute; see ADR-071 rationale)
- That the framework beats any specific vendor in any absolute sense
- That SWE-bench-lite measures the framework's differentiator
  (governance + multi-agent orchestration) — it does not; this is
  disclosed in results header
- Numbers from competing vendors (all sourced from their published
  materials; we never run their systems)

## 3. Methodology — mandatory for every result cell

### 3.1 Sample size
- **N ≥ 10** runs per task per adapter (minimum)
- Cell with **N < 10** is **OMITTED** from the public results table
  with footnote "insufficient samples for honest reporting"
- No "best of 3" reporting — all N runs in the JSON artifact

### 3.2 Statistics reported
- Median (primary)
- p50, p95, p99 (tail behavior)
- stddev (spread)
- NOT average/mean alone (hides tails)

### 3.3 Cold vs warm separation
- **Cold run:** first execution per task on a fresh Docker container
  (no pip cache, no git clone cache, no model warm-up)
- **Warm runs:** runs 2..N with caches primed
- Reported separately — combining them is misleading

### 3.4 Latency decomposition
- `work_latency_ms`: time actually doing the task
- `git_overhead_ms`: time managing worktree / checkpoint
- Separation preserved from `_benchmark_replay.py` C4 SLA
- Reporting combined is acceptable only alongside the decomposition

### 3.5 Hardware + environment disclosure
Every result table header MUST include:
- CPU model (e.g. Apple M2 Pro 12-core)
- RAM (e.g. 32 GB)
- Disk (e.g. NVMe 1TB)
- Network (e.g. residential fiber 500/500 — only relevant if Claude
  API used; local-only runs note "network offline")
- OS (e.g. Darwin 25.4.0)
- Python version (e.g. 3.11.15 Docker image)
- Git version (e.g. 2.45)
- Claude model(s) used (e.g. Opus 4.7 for CEO, Sonnet 4.6 for workers)

### 3.6 Seed discipline
- Fixed seed per task (documented in `manifest.schema.json` per task)
- Random exploration seeded via `random.seed(<task_seed>)` at CEO boot
- Sub-agent exploration inherits seed determinism via temperature=0
  where applicable (Claude API supports this)

### 3.7 Competitor number sourcing
- Devin/Cognition: https://cognition.ai/blog/ + press releases, cite
  date + commit of the score snapshot
- Aider: https://aider.chat/docs/leaderboards/, cite date + commit
- AutoCodeRover: GitHub repo README, cite commit SHA
- Karpathy's nanoGPT: N/A (not an agent framework — excluded)
- SWE-bench leaderboard: https://www.swebench.com/, note snapshot date
- **Freshness rule:** any competitor score > 90 days old is labeled
  `stale` in results table (SWE-bench versions rotate; Aider ships
  weekly)

## 4. Sandbox requirements (per ADR-071 + Security Risk #3)

All SWE-bench-lite task execution happens inside:

- Ephemeral Docker container (destroyed post-task)
- `--network=none` by default (no egress; Claude API calls gated via
  explicit `--network=host` subrun with manifest allowlist check)
- RO source mount (`/repo` read-only)
- tmpfs `/workspace` (destroyed on container exit)
- No `pip install` at benchmark time — all deps pre-installed in
  the pinned Docker image (digest-pinned per SWE-bench maintainers)
- SWE-bench-lite Docker images pulled by digest, NEVER built locally
- JSON Schema validation of the benchmark manifest (PLAN-051 Phase 5
  `docs/benchmarks/manifest.schema.json`) BEFORE any exec

Results artifact redacted via `_lib.redact` before publish
(defense-in-depth, even though SWE-bench is public data).

## 5. Independent verifier step (QA Risk #3)

Before publishing the results table:

1. A second CEO spawn (or `general-purpose` agent with identical
   skill load) re-runs **1 task × 3 seeds** from the original run
   using the same manifest + seeds
2. Results must match within **±5% on p95** to the original
3. If >5% divergence: investigate before publishing. Possible causes
   include: non-determinism in Claude API (temperature drift),
   flaky task environment, seed mismatch
4. Verifier output (3 runs per 1 task) is committed alongside the
   results doc as `docs/benchmarks/sprint-32-verifier-trace.json`
5. No verifier step → no public results (hard gate per ADR-071)

## 6. Failure modes → refused-via-ADR

If any of these occur, Phase 5 closes `refused via ADR` per
PLAN-051 §3.1 taxonomy reason (a) technical-infeasibility:

- Independent verifier diverges >5% persistently across 3 rounds
- Sandbox requirement cannot be met (e.g. SWE-bench-lite Docker
  images deprecated and no pinned-digest alternative)
- Claude API cost exceeds $1000 for the run (budget blowout)
- SWE-bench-lite not downloadable (dataset access broken)
- Any task in the pre-registered task list fails to parse/load

Refused outcome is HONEST — better than publishing unreliable
numbers.

## 7. Task list (pre-registered)

**NOT YET SELECTED.** Selection happens at Phase 5 execute kickoff;
will be committed as an amendment to this document BEFORE any run.
Candidate criteria:

- 3-5 tasks from SWE-bench-lite (300-issue subset)
- Covers distinct issue types (bug fix / feature add / refactor)
- Reasonable wall-clock (each task < 20 min on median Opus 4.7 call)
- No task requires internet inside the sandbox

## 8. Scoring rules

### 8.1 Task pass criteria
- SWE-bench test suite green post-framework-patch
- Framework's patch within the task's `FAIL_TO_PASS` + `PASS_TO_PASS`
  test coverage (standard SWE-bench evaluator)

### 8.2 NaN/Inf/timeout handling
- Task timeout (> 30 min): counted as FAIL (not NaN)
- Claude API error (rate limit / outage): counted as FAIL, flagged
  with error code in JSON artifact
- NaN/Inf from scorer: treated as FAIL per `_replay_tournament.py`
  defensive zeroing convention (Session 55)
- Framework crash: counted as FAIL, stack trace in artifact

### 8.3 Tie-breaking
- Primary: % issues resolved (headline score)
- Secondary: cost per task ($ Claude API)
- Tertiary: wall-clock median

## 9. Publication timing

Per PLAN-051 open-question #9 (Owner default: post-tag follow-up
commit):

- Results doc publishes **after** v1.9.0 GA tag, as separate commit
- NOT as v1.9.0 release artifact attached to GitHub Release
- Timing: within 30 days of v1.9.0 tag; late publication means
  `refused via ADR` and the entire Phase 5 closes without numbers

## 10. Supersession

This protocol is **immutable for v1.9.0 reporting**. A second
pre-registration file (`sprint-33-fairness-protocol.md` etc.) can
supersede it for future versions but cannot rewrite the v1.9.0
contract.

Each future report must cite the pre-registration version it uses:

```
Reported under: docs/benchmarks/sprint-32-fairness-protocol.md
                (committed 2026-04-23, v1.9.0 baseline)
```

## 11. Checklist before any benchmark run

Before Phase 5 execute launches, ALL must be true:

- [ ] This document committed to git (we are here)
- [ ] ADR-071 canonical (round-19 promote complete)
- [ ] ADR-071 status flipped PROPOSED → ACCEPTED
- [ ] `docs/benchmarks/manifest.schema.json` committed + schema test
      green
- [ ] SWE-bench-lite Docker image digest pinned in this document
- [ ] Task list selected + committed as amendment
- [ ] Claude API cost estimate < $1000 for full run
- [ ] Independent verifier agent identified (different CEO spawn)
- [ ] Budget approved explicitly by Owner

---

## References

- **ADR-071** benchmark-comparison-methodology (gate per Phase 2.5)
- **PLAN-051 §Phase 5 Acceptance** (8 mandatory items)
- **PLAN-051 Round 1 debate consensus Cluster 4** (4-agent agreement
  on pre-registration + sandbox + percentile reporting + no
  internal-disclaimer fallback)
- **`_benchmark_replay.py`** — Session 54 scaffold
- **`_replay_tournament.py`** — Session 55 bridge (NaN/Inf zeroing)
- **`tournament.py`** — PLAN-032 Wave B best-of-N selector
- **SWE-bench**: https://www.swebench.com/
- **PLAN-039** OWASP LLM Top 10 rubric (1 of 3 internal metrics)
